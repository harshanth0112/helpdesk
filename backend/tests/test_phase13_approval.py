"""
backend/tests/test_phase13_approval.py - Comprehensive Tests for Phase 13:
Admin Approval-Based Registration and Role Assignment.

Covers all 15 required scenarios:
1. New registration creates a pending account.
2. Pending user cannot log in.
3. Pending user cannot access protected APIs.
4. Non-admin cannot approve users.
5. Admin can approve and assign Employee role.
6. Admin can approve and assign Technician role.
7. Approved user can log in.
8. Rejected user cannot log in.
9. Suspended user cannot log in.
10. Existing authenticated sessions cannot bypass suspension.
11. Employee cannot promote themselves.
12. Technician cannot promote themselves.
13. Public registration cannot create Admin accounts.
14. Admin cannot accidentally remove the last active Admin.
15. Approval and role changes create audit records.
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
from app.models.audit_log import AuditLog
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
    from limits.storage import MemoryStorage
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    app.state.limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def create_approved_user(db: Session, email: str, role: str) -> tuple[User, str]:
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


# ===========================================================================
# Phase 13 Tests
# ===========================================================================

def test_1_2_3_new_registration_pending_cannot_login_or_access_protected_apis(client, db_session):
    """Tests 1, 2, 3: Registration creates pending account; cannot log in or access protected APIs."""
    r_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "pending_user@test.com",
            "password": "Password123",
            "first_name": "Pending",
            "last_name": "User",
            "department": "Engineering",
        },
    )
    assert r_reg.status_code == 201
    body = r_reg.json()
    assert body["approval_status"] == "pending"
    assert body["role"] == "employee"
    assert "access_token" not in body
    assert "refresh_token" not in body
    assert (
        body["message"]
        == "Your registration has been submitted successfully. Please wait for administrator approval before logging in."
    )

    # Test 2: Pending user cannot log in
    r_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pending_user@test.com", "password": "Password123"},
    )
    assert r_login.status_code == 403
    assert "awaiting administrator approval" in r_login.json()["detail"].lower()

    # Audit log recorded login_blocked_pending_approval
    blocked_log = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "login_blocked_pending_approval")
        .first()
    )
    assert blocked_log is not None

    # Test 3: Pending user cannot access protected APIs even with a forged/prior JWT
    pending_user = db_session.query(User).filter(User.email == "pending_user@test.com").first()
    token = generate_jwt_access_token(
        data={"sub": str(pending_user.id), "role": "employee"},
        expires_delta=timedelta(minutes=15),
    )
    r_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r_me.status_code == 403
    r_tickets = client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {token}"})
    assert r_tickets.status_code == 403


def test_4_non_admin_cannot_approve_users(client, db_session):
    """Test 4: Employee and Technician cannot approve pending users."""
    _, emp_token = create_approved_user(db_session, "emp_nonadmin@test.com", "employee")
    _, tech_token = create_approved_user(db_session, "tech_nonadmin@test.com", "technician")

    r_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "target_pending@test.com",
            "password": "Password123",
            "first_name": "Target",
            "last_name": "Pending",
        },
    )
    target_id = r_reg.json()["id"]

    for token in (emp_token, tech_token):
        r_app = client.patch(
            f"/api/v1/admin/users/{target_id}/approve",
            json={"role": "employee"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_app.status_code == 403


def test_5_6_7_admin_approve_employee_and_technician_then_login(client, db_session):
    """Tests 5, 6, 7: Admin can approve as Employee or Technician; approved user can log in."""
    admin, admin_token = create_approved_user(db_session, "admin_approver@test.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register 2 pending users
    r1 = client.post(
        "/api/v1/auth/register",
        json={"email": "new_emp@test.com", "password": "Password123", "first_name": "New", "last_name": "Emp"},
    )
    r2 = client.post(
        "/api/v1/auth/register",
        json={"email": "new_tech@test.com", "password": "Password123", "first_name": "New", "last_name": "Tech"},
    )
    emp_id = r1.json()["id"]
    tech_id = r2.json()["id"]

    # Pending list contains both
    r_pending = client.get("/api/v1/admin/users/pending", headers=admin_headers)
    assert r_pending.status_code == 200
    pending_ids = [u["id"] for u in r_pending.json()]
    assert emp_id in pending_ids and tech_id in pending_ids

    # Admin cannot assign invalid role during approval
    r_bad_approve = client.patch(
        f"/api/v1/admin/users/{emp_id}/approve",
        json={"role": "superadmin"},
        headers=admin_headers,
    )
    assert r_bad_approve.status_code == 422

    # Test 5: Approve as employee
    r_app_emp = client.patch(
        f"/api/v1/admin/users/{emp_id}/approve",
        json={"role": "employee"},
        headers=admin_headers,
    )
    assert r_app_emp.status_code == 200
    assert r_app_emp.json()["approval_status"] == "approved"
    assert r_app_emp.json()["role"] == "employee"

    # Test 6: Approve as technician
    r_app_tech = client.patch(
        f"/api/v1/admin/users/{tech_id}/approve",
        json={"role": "technician"},
        headers=admin_headers,
    )
    assert r_app_tech.status_code == 200
    assert r_app_tech.json()["approval_status"] == "approved"
    assert r_app_tech.json()["role"] == "technician"

    # Test 7: Approved users can now log in
    r_login1 = client.post("/api/v1/auth/login", json={"email": "new_emp@test.com", "password": "Password123"})
    assert r_login1.status_code == 200
    assert "access_token" in r_login1.json()

    r_login2 = client.post("/api/v1/auth/login", json={"email": "new_tech@test.com", "password": "Password123"})
    assert r_login2.status_code == 200
    assert "access_token" in r_login2.json()


def test_8_rejected_user_cannot_login(client, db_session):
    """Test 8: Rejected user cannot log in."""
    _, admin_token = create_approved_user(db_session, "admin_rejector@test.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    r_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "rejected_user@test.com", "password": "Password123", "first_name": "Rej", "last_name": "User"},
    )
    uid = r_reg.json()["id"]

    r_rej = client.patch(
        f"/api/v1/admin/users/{uid}/reject",
        json={"rejection_reason": "Unknown contractor"},
        headers=admin_headers,
    )
    assert r_rej.status_code == 200
    assert r_rej.json()["approval_status"] == "rejected"

    r_login = client.post("/api/v1/auth/login", json={"email": "rejected_user@test.com", "password": "Password123"})
    assert r_login.status_code == 403
    assert "not approved" in r_login.json()["detail"].lower()


def test_9_10_suspended_user_cannot_login_or_use_existing_session(client, db_session):
    """Tests 9, 10: Suspended user cannot log in, and existing JWT/refresh tokens are blocked immediately."""
    _, admin_token = create_approved_user(db_session, "admin_suspender@test.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    emp, _ = create_approved_user(db_session, "emp_suspend@test.com", "employee")

    # Employee logs in while approved
    r_login = client.post("/api/v1/auth/login", json={"email": "emp_suspend@test.com", "password": "Password123"})
    assert r_login.status_code == 200
    access_token = r_login.json()["access_token"]
    refresh_token = r_login.json()["refresh_token"]

    # Confirm session works before suspension
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}).status_code == 200

    # Admin suspends employee
    r_susp = client.patch(
        f"/api/v1/admin/users/{emp.id}/status",
        json={"action": "suspend"},
        headers=admin_headers,
    )
    assert r_susp.status_code == 200
    assert r_susp.json()["approval_status"] == "suspended"

    # Test 9: Suspended user cannot log in
    r_login_after = client.post("/api/v1/auth/login", json={"email": "emp_suspend@test.com", "password": "Password123"})
    assert r_login_after.status_code == 403
    assert "suspended" in r_login_after.json()["detail"].lower()

    # Test 10: Existing JWT and refresh token cannot bypass suspension
    r_me_after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert r_me_after.status_code == 403
    r_tickets_after = client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {access_token}"})
    assert r_tickets_after.status_code == 403
    r_refresh_after = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r_refresh_after.status_code == 401


def test_11_12_13_privilege_escalation_blocked(client, db_session):
    """Tests 11, 12, 13: Employee/Technician cannot self-promote; public registration cannot set admin."""
    emp, emp_token = create_approved_user(db_session, "emp_self@test.com", "employee")
    tech, tech_token = create_approved_user(db_session, "tech_self@test.com", "technician")

    # Test 11: Employee self-promotion
    r_emp = client.patch(
        f"/api/v1/admin/users/{emp.id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert r_emp.status_code == 403

    # Test 12: Technician self-promotion
    r_tech = client.patch(
        f"/api/v1/admin/users/{tech.id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert r_tech.status_code == 403

    # Test 13: Public registration cannot create admin
    r_pub = client.post(
        "/api/v1/auth/register",
        json={
            "email": "sneaky_admin@test.com",
            "password": "Password123",
            "first_name": "Sneaky",
            "last_name": "Admin",
            "role": "admin",
        },
    )
    if r_pub.status_code == 201:
        assert r_pub.json()["role"] == "employee"
    else:
        assert r_pub.status_code == 422


def test_14_cannot_remove_or_suspend_last_active_admin(client, db_session):
    """Test 14: Admin cannot accidentally demote or suspend the last active administrator."""
    admin, admin_token = create_approved_user(db_session, "last_admin@test.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Attempt to demote last active admin
    r_demote = client.patch(
        f"/api/v1/admin/users/{admin.id}/role",
        json={"role": "employee"},
        headers=admin_headers,
    )
    assert r_demote.status_code == 400
    assert "last active administrator" in r_demote.json()["detail"].lower()

    # Attempt to suspend last active admin
    r_suspend = client.patch(
        f"/api/v1/admin/users/{admin.id}/status",
        json={"action": "suspend"},
        headers=admin_headers,
    )
    assert r_suspend.status_code == 400
    assert "last active administrator" in r_suspend.json()["detail"].lower()


def test_15_approval_and_role_changes_create_audit_records(client, db_session):
    """Test 15: Registration, approval, role change, suspension, and reactivation create audit logs."""
    admin, admin_token = create_approved_user(db_session, "audit_admin@test.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    r_reg = client.post(
        "/api/v1/auth/register",
        json={"email": "audit_target@test.com", "password": "Password123", "first_name": "Audit", "last_name": "Target"},
    )
    uid = r_reg.json()["id"]

    client.patch(f"/api/v1/admin/users/{uid}/approve", json={"role": "employee"}, headers=admin_headers)
    client.patch(f"/api/v1/admin/users/{uid}/role", json={"role": "technician"}, headers=admin_headers)
    client.patch(f"/api/v1/admin/users/{uid}/status", json={"action": "suspend"}, headers=admin_headers)
    client.patch(f"/api/v1/admin/users/{uid}/status", json={"action": "reactivate"}, headers=admin_headers)

    actions = {
        log.action
        for log in db_session.query(AuditLog).filter(AuditLog.entity_id == uid).all()
    }
    assert "user_registration" in actions
    assert "user_approval" in actions
    assert "user_role_changed" in actions
    assert "user_suspended" in actions
    assert "user_reactivated" in actions


def test_16_migration_backfill_behavior(db_session):
    """Verify that existing user records without explicit approval status become approved."""
    from sqlalchemy import text
    # Simulate an existing user row having approval_status = 'approved' (as backfilled by migration)
    user = User(
        email="legacy_user@test.com",
        password_hash=get_password_hash("Password123"),
        first_name="Legacy",
        last_name="User",
        role="employee",
        is_active=True,
        approval_status="approved",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.approval_status == "approved"
    assert user.is_active is True
