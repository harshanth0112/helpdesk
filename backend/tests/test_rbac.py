"""
backend/tests/test_rbac.py — Comprehensive Phase 5 Role-Based Access Control test suite.

Test cases required:
1. Employee A attempts to access Employee B's ticket (IDOR prevention, expect 404).
2. Employee attempts admin API access (expect 403).
3. Technician attempts to assign themselves to an unauthorized ticket (expect 403).
4. Employee attempts role escalation (expect 403).
5. Unauthenticated user attempts protected access (expect 401).

Additional checks:
- Employee can create ticket and view own ticket.
- Technician can update status on assigned ticket.
- Technician cannot update status on unassigned ticket.
- Admin can access all tickets, reassign tickets, and view analytics/audit logs.
- Comment visibility (internal vs public).
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
from app.models.comment import Comment
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


def create_user_and_token(db: Session, email: str, role: str) -> tuple[User, str]:
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


def create_category(db: Session) -> Category:
    cat = Category(name="IT Support", description="Hardware and software support")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ===========================================================================
# RBAC Test Suite
# ===========================================================================

def test_unauthenticated_user_attempts_protected_access(client):
    """Test Case 5: Unauthenticated user attempts protected access (401)."""
    r1 = client.get("/api/v1/tickets")
    assert r1.status_code == 401

    r2 = client.post("/api/v1/tickets", json={"title": "Test", "description": "Need help", "category_id": 1})
    assert r2.status_code == 401

    r3 = client.get("/api/v1/admin/users")
    assert r3.status_code == 401


def test_employee_attempts_admin_api_access(client, db_session):
    """Test Case 2: Employee attempts admin API access (403)."""
    _, emp_token = create_user_and_token(db_session, "emp_admin_test@test.com", "employee")
    headers = {"Authorization": f"Bearer {emp_token}"}

    r1 = client.get("/api/v1/admin/users", headers=headers)
    assert r1.status_code == 403

    r2 = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert r2.status_code == 403

    r3 = client.get("/api/v1/admin/analytics", headers=headers)
    assert r3.status_code == 403


def test_employee_a_attempts_to_access_employee_b_ticket(client, db_session):
    """Test Case 1: Employee A can view Employee B's ticket (global visibility), but cannot modify it (403)."""
    cat = create_category(db_session)
    emp_a, token_a = create_user_and_token(db_session, "emp_a@test.com", "employee")
    emp_b, token_b = create_user_and_token(db_session, "emp_b@test.com", "employee")

    # Employee B creates a ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Laptop broken", "description": "Screen is flickering", "category_id": cat.id},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r_create.status_code == 201
    ticket_id = r_create.json()["id"]

    # Employee A can view Employee B's ticket (Global Ticket Visibility)
    r_get = client.get(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert r_get.status_code == 200
    assert r_get.json()["id"] == ticket_id

    # Employee A attempts to PUT/modify Employee B's ticket -> Forbidden (403)
    r_put = client.put(
        f"/api/v1/tickets/{ticket_id}",
        json={"title": "Hacked title", "description": "Hacked desc"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r_put.status_code == 403


def test_technician_attempts_unauthorized_ticket_assignment(client, db_session):
    """Test Case 3: Technician can view unassigned ticket (global visibility), but cannot assign (403)."""
    cat = create_category(db_session)
    emp, emp_token = create_user_and_token(db_session, "emp_owner@test.com", "employee")
    tech, tech_token = create_user_and_token(db_session, "tech_assign@test.com", "technician")

    # Employee creates ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Printer issue", "description": "Cannot connect to wifi printer", "category_id": cat.id},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    ticket_id = r_create.json()["id"]

    # Technician can view ticket even when not assigned (Global Visibility)
    r_access = client.get(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": f"Bearer {tech_token}"})
    assert r_access.status_code == 200

    # Technician cannot assign ticket (Admin only -> 403)
    r_assign = client.patch(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_to": tech.id},
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert r_assign.status_code == 403


def test_employee_attempts_role_escalation(client, db_session):
    """Test Case 4: Employee attempts role escalation (403)."""
    emp, emp_token = create_user_and_token(db_session, "emp_escalate@test.com", "employee")

    # Employee tries to hit role update endpoint directly
    r_escalate = client.patch(
        f"/api/v1/admin/users/{emp.id}/role",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert r_escalate.status_code == 403


def test_admin_full_ticket_and_user_management(client, db_session):
    """Admin can view, assign, update priority/status, and change user roles."""
    cat = create_category(db_session)
    emp, _ = create_user_and_token(db_session, "emp_manage@test.com", "employee")
    tech, _ = create_user_and_token(db_session, "tech_manage@test.com", "technician")
    admin, admin_token = create_user_and_token(db_session, "admin_manage@test.com", "admin")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin creates ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Server outage", "description": "Rack A down", "category_id": cat.id, "priority": "critical"},
        headers=admin_headers,
    )
    assert r_create.status_code == 201
    ticket_id = r_create.json()["id"]

    # Admin assigns ticket to technician and changes status
    r_update = client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"assigned_to": tech.id, "status": "assigned"},
        headers=admin_headers,
    )
    assert r_update.status_code == 200
    assert r_update.json()["assigned_to"] == tech.id
    assert r_update.json()["status"] == "assigned"

    # Admin changes user role
    r_role = client.patch(
        f"/api/v1/admin/users/{emp.id}/role",
        json={"role": "technician"},
        headers=admin_headers,
    )
    assert r_role.status_code == 200
    assert r_role.json()["role"] == "technician"

    # Admin gets analytics
    r_analytics = client.get("/api/v1/admin/analytics", headers=admin_headers)
    assert r_analytics.status_code == 200
    assert r_analytics.json()["total_tickets"] >= 1


def test_technician_can_update_status_and_comment_on_assigned_ticket(client, db_session):
    """Technician can update status and comment on assigned tickets, but cannot assign or change priority."""
    cat = create_category(db_session)
    emp, _ = create_user_and_token(db_session, "emp_assigned@test.com", "employee")
    tech, tech_token = create_user_and_token(db_session, "tech_assigned@test.com", "technician")
    admin, admin_token = create_user_and_token(db_session, "admin_assigner@test.com", "admin")

    # Admin creates and assigns ticket to tech
    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Network issue", "description": "Slow Wi-Fi", "category_id": cat.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    ticket_id = r_create.json()["id"]
    client.patch(
        f"/api/v1/tickets/{ticket_id}",
        json={"assigned_to": tech.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    # Tech views ticket
    r_get = client.get(f"/api/v1/tickets/{ticket_id}", headers=tech_headers)
    assert r_get.status_code == 200

    # Tech updates status to in_progress
    r_status = client.patch(f"/api/v1/tickets/{ticket_id}", json={"status": "in_progress"}, headers=tech_headers)
    assert r_status.status_code == 200
    assert r_status.json()["status"] == "in_progress"

    # Tech adds internal comment
    r_comment = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={"comment_text": "Investigating access point firmware.", "is_internal": True},
        headers=tech_headers,
    )
    assert r_comment.status_code == 201

    # Tech attempts to change priority (forbidden)
    r_priority = client.patch(f"/api/v1/tickets/{ticket_id}", json={"priority": "critical"}, headers=tech_headers)
    assert r_priority.status_code == 403


def test_global_ticket_visibility_for_all_roles(client, db_session):
    """
    Verify:
    - Employee sees tickets created by other employees.
    - Employee sees tickets assigned to different technicians.
    - Technician sees all tickets, including unassigned tickets.
    - Admin sees all tickets.
    - Employees cannot edit other users' tickets.
    - Technicians cannot edit tickets outside their permitted modification scope.
    """
    cat = create_category(db_session)
    emp1, emp1_token = create_user_and_token(db_session, "emp1_global@test.com", "employee")
    emp2, emp2_token = create_user_and_token(db_session, "emp2_global@test.com", "employee")
    tech1, tech1_token = create_user_and_token(db_session, "tech1_global@test.com", "technician")
    tech2, tech2_token = create_user_and_token(db_session, "tech2_global@test.com", "technician")
    admin, admin_token = create_user_and_token(db_session, "admin_global@test.com", "admin")

    # Emp1 creates ticket
    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Global Vis Ticket 1", "description": "Created by emp1", "category_id": cat.id},
        headers={"Authorization": f"Bearer {emp1_token}"},
    )
    assert r_create.status_code == 201
    ticket_id = r_create.json()["id"]

    # Assign ticket to tech1
    r_assign = client.patch(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_to": tech1.id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r_assign.status_code == 200

    # 1. Emp2 (different employee) can view Emp1's ticket in list and details
    r_emp2_list = client.get("/api/v1/tickets", headers={"Authorization": f"Bearer {emp2_token}"})
    assert r_emp2_list.status_code == 200
    assert any(t["id"] == ticket_id for t in r_emp2_list.json()["items"])

    r_emp2_get = client.get(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": f"Bearer {emp2_token}"})
    assert r_emp2_get.status_code == 200
    assert r_emp2_get.json()["id"] == ticket_id

    # Emp2 cannot edit Emp1's ticket (403)
    r_emp2_edit = client.put(
        f"/api/v1/tickets/{ticket_id}",
        json={"title": "Unauthorized modification", "description": "Hacked"},
        headers={"Authorization": f"Bearer {emp2_token}"},
    )
    assert r_emp2_edit.status_code == 403

    # 2. Tech2 (different technician) can view the ticket
    r_tech2_get = client.get(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": f"Bearer {tech2_token}"})
    assert r_tech2_get.status_code == 200

    # Tech2 cannot update status because ticket is assigned to Tech1 (403)
    r_tech2_status = client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {tech2_token}"},
    )
    assert r_tech2_status.status_code == 403

    # Tech1 (assigned technician) CAN update status
    r_tech1_status = client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {tech1_token}"},
    )
    assert r_tech1_status.status_code == 200
    assert r_tech1_status.json()["status"] == "in_progress"

    # Tech1 resolves ticket
    r_tech1_res = client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "resolved", "resolution_notes": "All fixed"},
        headers={"Authorization": f"Bearer {tech1_token}"},
    )
    assert r_tech1_res.status_code == 200

    # Emp2 cannot close ticket (not requester) -> 403
    r_emp2_close = client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {emp2_token}"},
    )
    assert r_emp2_close.status_code == 403

    # Emp1 (requester) can close own resolved ticket -> 200
    r_emp1_close = client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "closed"},
        headers={"Authorization": f"Bearer {emp1_token}"},
    )
    assert r_emp1_close.status_code == 200
    assert r_emp1_close.json()["status"] == "closed"
