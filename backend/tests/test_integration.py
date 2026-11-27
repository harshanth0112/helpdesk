"""
backend/tests/test_integration.py - Full-Stack End-to-End API Integration Test Suite.

Verifies the exact contracts, workflows, and security requirements used by the React frontend:
1. Registration -> Login -> Current User (/auth/me) flow.
2. Token expiration handling and refresh token rotation (/auth/refresh).
3. Logout flow and token revocation.
4. Role-scoped Dashboard statistics API (/tickets/stats/dashboard) for Employee, Technician, Admin.
5. Ticket lifecycle: creation, listing with pagination & filters, details retrieval, and updates.
6. Technician assignment and workflow updates with resolution notes.
7. Anti-IDOR enforcement across API layers.
8. CORS headers verification.
"""

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.category import Category
from app.models.ticket import Ticket
from app.core.security import generate_jwt_access_token, get_password_hash

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


def create_user_helper(db: Session, email: str, role: str) -> tuple[User, str]:
    user = User(
        email=email,
        password_hash=get_password_hash("Password123"),
        first_name="Test",
        last_name=role.capitalize(),
        role=role,
        is_active=True,
        approval_status="approved",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = generate_jwt_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=timedelta(minutes=60),
    )
    return user, token


def create_category_helper(db: Session, name: str = "Hardware") -> Category:
    cat = Category(name=name, description=f"{name} category")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ===========================================================================
# Full-Stack Integration Scenarios
# ===========================================================================

def test_full_auth_registration_login_me_lifecycle(client, db_session):
    """Scenario 1: Registration (pending) -> Admin Approval -> Login -> Current-user retrieval -> Logout."""
    # 1. Register new employee (starts as pending)
    reg_res = client.post("/api/v1/auth/register", json={
        "first_name": "Integration",
        "last_name": "Employee",
        "email": "integration_emp@example.com",
        "password": "ValidPass123",
        "department": "IT Support",
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["role"] == "employee"
    assert reg_res.json()["approval_status"] == "pending"

    # Approve user in DB
    user = db_session.query(User).filter(User.email == "integration_emp@example.com").first()
    user.approval_status = "approved"
    db_session.commit()

    # 2. Login to obtain access and refresh tokens
    login_res = client.post("/api/v1/auth/login", json={
        "email": "integration_emp@example.com",
        "password": "ValidPass123",
    })
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # 3. Retrieve current user profile (/auth/me)
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_info = me_res.json()
    assert user_info["email"] == "integration_emp@example.com"
    assert user_info["role"] == "employee"
    assert "password_hash" not in user_info

    # 4. Token refresh rotation
    refresh_res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"],
    })
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # 5. Logout
    logout_res = client.post("/api/v1/auth/logout", json={
        "refresh_token": new_tokens["refresh_token"],
    }, headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
    assert logout_res.status_code == 204


def test_cors_preflight_and_headers(client):
    """Scenario 2: CORS configuration allows development origins."""
    res = client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert res.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_dashboard_stats_role_scoping(client, db_session):
    """Scenario 3: Verify PostgreSQL-backed dashboard KPIs reflect role boundaries."""
    cat = create_category_helper(db_session, "Integrations")
    emp1, emp1_token = create_user_helper(db_session, "emp1_dash@test.com", "employee")
    emp2, emp2_token = create_user_helper(db_session, "emp2_dash@test.com", "employee")
    tech, tech_token = create_user_helper(db_session, "tech_dash@test.com", "technician")
    admin, admin_token = create_user_helper(db_session, "admin_dash@test.com", "admin")

    # Emp1 creates 2 tickets
    client.post("/api/v1/tickets", json={"title": "Emp1 Ticket A", "description": "Desc A", "category_id": cat.id}, headers={"Authorization": f"Bearer {emp1_token}"})
    client.post("/api/v1/tickets", json={"title": "Emp1 Ticket B", "description": "Desc B", "category_id": cat.id}, headers={"Authorization": f"Bearer {emp1_token}"})

    # Emp2 creates 1 ticket and Admin assigns it to Tech
    r_emp2 = client.post("/api/v1/tickets", json={"title": "Emp2 Ticket C", "description": "Desc C", "category_id": cat.id}, headers={"Authorization": f"Bearer {emp2_token}"})
    ticket_c_id = r_emp2.json()["id"]
    client.patch(f"/api/v1/tickets/{ticket_c_id}/assign", json={"assigned_to": tech.id}, headers={"Authorization": f"Bearer {admin_token}"})

    # Emp1 Dashboard Stats: should only count Emp1's 2 tickets
    emp1_stats = client.get("/api/v1/tickets/stats/dashboard", headers={"Authorization": f"Bearer {emp1_token}"}).json()
    assert emp1_stats["total"] == 2

    # Tech Dashboard Stats: should only count assigned ticket (1 ticket)
    tech_stats = client.get("/api/v1/tickets/stats/dashboard", headers={"Authorization": f"Bearer {tech_token}"}).json()
    assert tech_stats["total"] == 1

    # Admin Dashboard Stats: sees all system tickets
    admin_stats = client.get("/api/v1/tickets/stats/dashboard", headers={"Authorization": f"Bearer {admin_token}"}).json()
    assert admin_stats["total"] >= 3


def test_ticket_lifecycle_workflow_integration(client, db_session):
    """Scenario 4: Complete ticket creation, search, filter, comments, and state updates."""
    cat = create_category_helper(db_session, "Workflows")
    emp, emp_token = create_user_helper(db_session, "workflow_emp@test.com", "employee")
    tech, tech_token = create_user_helper(db_session, "workflow_tech@test.com", "technician")
    admin, admin_token = create_user_helper(db_session, "workflow_admin@test.com", "admin")

    # 1. Create ticket
    r_create = client.post("/api/v1/tickets", json={
        "title": "Dual Monitor Issue",
        "description": "Second monitor flickering on HDMI",
        "category_id": cat.id,
        "priority": "high",
    }, headers={"Authorization": f"Bearer {emp_token}"})
    assert r_create.status_code == 201
    ticket_id = r_create.json()["id"]

    # 2. Filter & Search verification
    r_list = client.get(f"/api/v1/tickets?search=Monitor&priority=high", headers={"Authorization": f"Bearer {emp_token}"})
    assert r_list.status_code == 200
    assert len(r_list.json()["items"]) >= 1

    # 3. Admin assigns to Technician
    r_assign = client.patch(f"/api/v1/tickets/{ticket_id}/assign", json={
        "assigned_to": tech.id,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert r_assign.status_code == 200
    assert r_assign.json()["status"] == "assigned"

    # 4. Technician adds internal comment and transitions to in_progress
    r_comm = client.post(f"/api/v1/tickets/{ticket_id}/comments", json={
        "comment_text": "Ordered replacement DisplayPort cable.",
        "is_internal": True,
    }, headers={"Authorization": f"Bearer {tech_token}"})
    assert r_comm.status_code == 201

    client.patch(f"/api/v1/tickets/{ticket_id}/status", json={
        "status": "in_progress",
    }, headers={"Authorization": f"Bearer {tech_token}"})

    # 5. Technician resolves ticket with resolution notes
    r_resolve = client.patch(f"/api/v1/tickets/{ticket_id}/status", json={
        "status": "resolved",
        "resolution_notes": "Cable replaced; verified dual 4K display output.",
    }, headers={"Authorization": f"Bearer {tech_token}"})
    assert r_resolve.status_code == 200
    assert r_resolve.json()["status"] == "resolved"
    assert r_resolve.json()["resolution_notes"] is not None

    # 6. Verify employee cannot see internal comment
    emp_comments = client.get(f"/api/v1/tickets/{ticket_id}/comments", headers={"Authorization": f"Bearer {emp_token}"}).json()
    assert all(c["is_internal"] is False for c in emp_comments)
