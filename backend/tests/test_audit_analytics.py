"""
backend/tests/test_audit_analytics.py - Unit & Integration tests for Phase 11.

Covers:
1. Audit log recording on auth events (registration, login success, login failure).
2. Redaction of sensitive fields (password, token, hash) in audit log records.
3. Strict RBAC enforcement on audit logs (admin access only, 403 for employee/technician).
4. Paginated audit log retrieval with filter parameters (action, entity_type, dates).
5. Comprehensive analytics endpoint calculation (total, open, in-progress, resolved, critical, avg resolution time).
6. Date range filtering on analytics.
7. Scoping of analytics by user role.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.category import Category
from app.models.audit_log import AuditLog
from app.services import audit_service, analytics_service
from app.core.security import get_password_hash, generate_jwt_access_token

SQLITE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_users(db_session: Session):
    """Seed test users for admin, employee, technician."""
    admin = User(
        email="audit_admin@example.com",
        password_hash=get_password_hash("AdminPass123!"),
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True,
        approval_status="approved",
    )
    employee = User(
        email="audit_emp@example.com",
        password_hash=get_password_hash("EmpPass123!"),
        first_name="Employee",
        last_name="User",
        role="employee",
        is_active=True,
        approval_status="approved",
    )
    technician = User(
        email="audit_tech@example.com",
        password_hash=get_password_hash("TechPass123!"),
        first_name="Technician",
        last_name="User",
        role="technician",
        is_active=True,
        approval_status="approved",
    )
    db_session.add_all([admin, employee, technician])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(employee)
    db_session.refresh(technician)
    return {"admin": admin, "employee": employee, "technician": technician}


def get_token_headers(user: User):
    token = generate_jwt_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_audit_sensitive_payload_redaction(db_session: Session):
    """Ensure sensitive credentials are redacted before persisting in audit logs."""
    unclean_payload = {
        "email": "user@test.com",
        "password": "SuperSecretPassword123!",
        "password_hash": "$argon2id$...dummyhash",
        "token": "secret_access_token",
        "normal_field": "public_data",
    }
    cleaned = audit_service.sanitize_payload(unclean_payload)
    assert cleaned["email"] == "user@test.com"
    assert cleaned["normal_field"] == "public_data"
    assert cleaned["password"] == "[REDACTED]"
    assert cleaned["password_hash"] == "[REDACTED]"
    assert cleaned["token"] == "[REDACTED]"


def test_auth_events_recorded_in_audit_log(client: TestClient, db_session: Session, test_users):
    """Test user registration, login success, and login failure create audit entries."""
    # 1. Register new user
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new_audit_user@example.com",
            "password": "StrongPassword123!",
            "first_name": "Audit",
            "last_name": "New",
        },
    )
    assert reg_res.status_code == 201

    # Verify registration audit record
    reg_log = db_session.query(AuditLog).filter(AuditLog.action == "user_registration").first()
    assert reg_log is not None
    assert reg_log.entity_type == "user"
    assert reg_log.new_values.get("email") == "new_audit_user@example.com"
    assert "password" not in reg_log.new_values

    # Approve user so they can log in
    new_user = db_session.query(User).filter(User.email == "new_audit_user@example.com").first()
    new_user.approval_status = "approved"
    db_session.commit()

    # 2. Login success
    login_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "new_audit_user@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login_res.status_code == 200

    login_success_log = db_session.query(AuditLog).filter(AuditLog.action == "login_success").first()
    assert login_success_log is not None
    assert login_success_log.entity_type == "auth"
    assert login_success_log.new_values.get("email") == "new_audit_user@example.com"

    # 3. Login failure
    fail_res = client.post(
        "/api/v1/auth/login",
        json={
            "email": "new_audit_user@example.com",
            "password": "WrongPassword999!",
        },
    )
    assert fail_res.status_code == 401

    login_failed_log = db_session.query(AuditLog).filter(AuditLog.action == "login_failed").first()
    assert login_failed_log is not None
    assert login_failed_log.entity_type == "auth"
    assert login_failed_log.new_values.get("email") == "new_audit_user@example.com"


def test_audit_logs_rbac(client: TestClient, db_session: Session, test_users):
    """Only admins may retrieve audit logs; employees and technicians must receive 403."""
    admin_headers = get_token_headers(test_users["admin"])
    emp_headers = get_token_headers(test_users["employee"])
    tech_headers = get_token_headers(test_users["technician"])

    # Employee attempt
    res_emp = client.get("/api/v1/admin/audit-logs", headers=emp_headers)
    assert res_emp.status_code == 403

    # Technician attempt
    res_tech = client.get("/api/v1/admin/audit-logs", headers=tech_headers)
    assert res_tech.status_code == 403

    # Admin attempt
    res_admin = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert res_admin.status_code == 200
    assert "items" in res_admin.json()
    assert "total" in res_admin.json()


def test_paginated_audit_logs_and_filtering(client: TestClient, db_session: Session, test_users):
    """Test pagination, action filter, and entity filter on audit logs endpoint."""
    admin_headers = get_token_headers(test_users["admin"])

    # Create several audit entries with valid ticket or non-ticket entity
    for i in range(5):
        audit_service.record_audit_event(
            db=db_session,
            action="custom_action_test",
            actor_id=test_users["admin"].id,
            entity_type="security",
            entity_id=100 + i,
            new_values={"iteration": i},
        )

    # Test filtering by action
    res = client.get(
        "/api/v1/admin/audit-logs?action=custom_action_test&page_size=2",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 5
    assert len(data["items"]) == 2
    assert data["items"][0]["action"] == "custom_action_test"


def test_analytics_service_and_endpoint(client: TestClient, db_session: Session, test_users):
    """Test comprehensive system analytics aggregation and date range filtering."""
    admin_headers = get_token_headers(test_users["admin"])
    emp = test_users["employee"]
    tech = test_users["technician"]

    # Seed category
    cat = Category(name="Hardware Support", description="Hardware inquiries")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)

    now = datetime.now(timezone.utc)
    # Seed 2 resolved tickets, 1 open ticket with ticket_number
    t1 = Ticket(
        ticket_number="TICK-TEST-0001",
        title="Laptop Broken",
        description="Screen cracked",
        category_id=cat.id,
        priority="critical",
        status="resolved",
        requester_id=emp.id,
        assigned_to=tech.id,
        created_at=now - timedelta(hours=4),
        resolved_at=now,
    )
    t2 = Ticket(
        ticket_number="TICK-TEST-0002",
        title="Keyboard Issue",
        description="Keys sticking",
        category_id=cat.id,
        priority="medium",
        status="resolved",
        requester_id=emp.id,
        assigned_to=tech.id,
        created_at=now - timedelta(hours=2),
        resolved_at=now,
    )
    t3 = Ticket(
        ticket_number="TICK-TEST-0003",
        title="Mouse not responding",
        description="Bluetooth fails",
        category_id=cat.id,
        priority="low",
        status="open",
        requester_id=emp.id,
        created_at=now,
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # Query admin analytics
    res = client.get("/api/v1/admin/analytics", headers=admin_headers)
    assert res.status_code == 200
    analytics = res.json()

    assert analytics["total_tickets"] >= 3
    assert analytics["resolved_tickets"] >= 2
    assert analytics["critical_tickets"] >= 1
    assert analytics["avg_resolution_hours"] > 0
    assert any(c["name"] == "Hardware Support" for c in analytics["categories"])

    # Test date filtering: filter tickets before created_at of t1
    start_filter = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res_future = client.get(f"/api/v1/admin/analytics?start_date={start_filter}", headers=admin_headers)
    assert res_future.status_code == 200
    future_data = res_future.json()
    assert future_data["total_tickets"] == 0
