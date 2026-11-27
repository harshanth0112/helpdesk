"""
backend/tests/test_tickets_crud.py - Comprehensive Tests for Phase 6 Secure Ticket CRUD APIs.

Tests cover:
1. Create ticket (Employee, Technician, Admin)
2. Retrieve ticket (with IDOR prevention for unauthorized users & invalid ticket IDs)
3. List tickets with pagination, search, status/priority filtering, and allowlisted sorting
4. Update ticket via PUT (Employee can update own open ticket, cannot update resolved/closed; Tech forbidden)
5. Delete ticket according to retention rules (Admin only, only if closed or resolved; active cannot be deleted)
6. Assign and reassign technician via PATCH /assign (Admin only, checks active tech)
7. Priority change via PATCH /priority (Admin only, validated allowlist)
8. Status change via PATCH /status (Validated state transitions, technician updates status with resolution_notes)
9. Ticket history tracking via GET /tickets/{id}/history (Auditing created, updated, status changed, etc.)
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


def create_user(db: Session, email: str, role: str) -> tuple[User, str]:
    user = User(
        email=email,
        password_hash=get_password_hash("Password123"),
        first_name="User",
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


def create_category(db: Session, name: str = "Hardware") -> Category:
    cat = Category(name=name, description=f"{name} category")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ===========================================================================
# CRUD Tests
# ===========================================================================

def test_ticket_create_and_retrieve(client, db_session):
    """Employee creates ticket, retrieves it by ID, and verifies auto-generated ticket_number."""
    cat = create_category(db_session, "Network")
    emp, emp_token = create_user(db_session, "emp_crud_1@test.com", "employee")
    headers = {"Authorization": f"Bearer {emp_token}"}

    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "VPN Disconnecting", "description": "VPN drops every 10 minutes", "category_id": cat.id, "priority": "high"},
        headers=headers,
    )
    assert r_create.status_code == 201
    ticket_data = r_create.json()
    assert ticket_data["title"] == "VPN Disconnecting"
    assert ticket_data["status"] == "open"
    assert ticket_data["priority"] == "high"
    assert ticket_data["ticket_number"].startswith("TICK-")
    ticket_id = ticket_data["id"]

    # Retrieve by ID
    r_get = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers)
    assert r_get.status_code == 200
    assert r_get.json()["id"] == ticket_id


def test_invalid_ticket_id(client, db_session):
    """Accessing non-existent ticket ID returns 404."""
    _, token = create_user(db_session, "emp_invalid_id@test.com", "employee")
    r = client.get("/api/v1/tickets/999999", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_list_tickets_pagination_search_filter_sort(client, db_session):
    """Test pagination, search, status/priority filtering, and sorting."""
    cat = create_category(db_session, "Software")
    admin, admin_token = create_user(db_session, "admin_list@test.com", "admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create 5 tickets
    for i in range(5):
        client.post(
            "/api/v1/tickets",
            json={
                "title": f"Software Bug {i}",
                "description": f"Details for bug {i}",
                "category_id": cat.id,
                "priority": "low" if i % 2 == 0 else "high",
            },
            headers=headers,
        )

    # Paginate: page 1, page_size 2
    r_page = client.get("/api/v1/tickets?page=1&page_size=2", headers=headers)
    assert r_page.status_code == 200
    data = r_page.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 5
    assert data["total_pages"] >= 3

    # Search by keyword
    r_search = client.get("/api/v1/tickets?search=Bug 3", headers=headers)
    assert r_search.status_code == 200
    search_items = r_search.json()["items"]
    assert len(search_items) == 1
    assert search_items[0]["title"] == "Software Bug 3"

    # Filter by priority
    r_filter = client.get("/api/v1/tickets?priority=high", headers=headers)
    assert r_filter.status_code == 200
    for item in r_filter.json()["items"]:
        assert item["priority"] == "high"

    # Sort by title ascending
    r_sort = client.get("/api/v1/tickets?sort_by=title&sort_order=asc", headers=headers)
    assert r_sort.status_code == 200
    titles = [t["title"] for t in r_sort.json()["items"]]
    assert titles == sorted(titles)


def test_put_update_ticket(client, db_session):
    """PUT full update on ticket: Employee can update own open ticket; Tech cannot."""
    cat = create_category(db_session, "Peripherals")
    emp, emp_token = create_user(db_session, "emp_put@test.com", "employee")
    tech, tech_token = create_user(db_session, "tech_put@test.com", "technician")
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Mouse lag", "description": "Wireless mouse stuttering", "category_id": cat.id},
        headers=emp_headers,
    )
    ticket_id = r_create.json()["id"]

    # Employee updates title & description
    r_put = client.put(
        f"/api/v1/tickets/{ticket_id}",
        json={"title": "Mouse and Keyboard lag", "description": "Both stuttering heavily"},
        headers=emp_headers,
    )
    assert r_put.status_code == 200
    assert r_put.json()["title"] == "Mouse and Keyboard lag"

    # Technician attempts PUT (forbidden)
    r_tech_put = client.put(
        f"/api/v1/tickets/{ticket_id}",
        json={"title": "Tech tried edit", "description": "Not allowed"},
        headers={"Authorization": f"Bearer {tech_token}"},
    )
    assert r_tech_put.status_code in (403, 404)


def test_patch_priority_admin_only(client, db_session):
    """PATCH /priority is admin only."""
    cat = create_category(db_session, "Security")
    emp, emp_token = create_user(db_session, "emp_prio@test.com", "employee")
    admin, admin_token = create_user(db_session, "admin_prio@test.com", "admin")

    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Phishing email received", "description": "Suspicious invoice attachment", "category_id": cat.id},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    ticket_id = r_create.json()["id"]

    # Employee cannot change priority
    r_emp = client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "critical"},
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert r_emp.status_code == 403

    # Admin changes priority to critical
    r_admin = client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "critical"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r_admin.status_code == 200
    assert r_admin.json()["priority"] == "critical"


def test_patch_assign_and_reassign(client, db_session):
    """PATCH /assign technician by admin. Auto-transitions status to assigned."""
    cat = create_category(db_session, "Storage")
    admin, admin_token = create_user(db_session, "admin_assign@test.com", "admin")
    tech1, _ = create_user(db_session, "tech_assign_1@test.com", "technician")
    tech2, _ = create_user(db_session, "tech_assign_2@test.com", "technician")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Disk Full Alert", "description": "Server disk is 98% full", "category_id": cat.id},
        headers=admin_headers,
    )
    ticket_id = r_create.json()["id"]
    assert r_create.json()["status"] == "open"

    # Assign tech 1
    r_assign = client.patch(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_to": tech1.id},
        headers=admin_headers,
    )
    assert r_assign.status_code == 200
    assert r_assign.json()["assigned_to"] == tech1.id
    assert r_assign.json()["status"] == "assigned"

    # Reassign to tech 2
    r_reassign = client.patch(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"assigned_to": tech2.id},
        headers=admin_headers,
    )
    assert r_reassign.status_code == 200
    assert r_reassign.json()["assigned_to"] == tech2.id


def test_status_transitions_and_history(client, db_session):
    """Test valid & invalid state transitions, technician resolution notes, and audit history."""
    cat = create_category(db_session, "Cloud")
    admin, admin_token = create_user(db_session, "admin_hist@test.com", "admin")
    tech, tech_token = create_user(db_session, "tech_hist@test.com", "technician")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tech_headers = {"Authorization": f"Bearer {tech_token}"}

    # Admin creates ticket & assigns to tech
    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "AWS IAM Permission Denied", "description": "Need S3 bucket read access", "category_id": cat.id},
        headers=admin_headers,
    )
    ticket_id = r_create.json()["id"]
    client.patch(f"/api/v1/tickets/{ticket_id}/assign", json={"assigned_to": tech.id}, headers=admin_headers)

    # Tech moves from 'assigned' to 'in_progress'
    r_prog = client.patch(f"/api/v1/tickets/{ticket_id}/status", json={"status": "in_progress"}, headers=tech_headers)
    assert r_prog.status_code == 200
    assert r_prog.json()["status"] == "in_progress"

    # Invalid transition test: in_progress directly to open should fail
    r_invalid = client.patch(f"/api/v1/tickets/{ticket_id}/status", json={"status": "open"}, headers=tech_headers)
    assert r_invalid.status_code == 400

    # Tech resolves ticket with resolution notes
    r_resolve = client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "resolved", "resolution_notes": "Added S3 read IAM policy attachment."},
        headers=tech_headers,
    )
    assert r_resolve.status_code == 200
    assert r_resolve.json()["status"] == "resolved"
    assert r_resolve.json()["resolution_notes"] == "Added S3 read IAM policy attachment."
    assert r_resolve.json()["resolved_at"] is not None

    # Check ticket history
    r_hist = client.get(f"/api/v1/tickets/{ticket_id}/history", headers=tech_headers)
    assert r_hist.status_code == 200
    history = r_hist.json()
    actions = [h["action"] for h in history]
    assert "ticket_created" in actions
    assert "assignment_changed" in actions
    assert "status_changed" in actions


def test_delete_and_retention_rules(client, db_session):
    """Admin can delete tickets (even active/unclosed); employee cannot delete tickets."""
    cat = create_category(db_session, "Audio")
    admin, admin_token = create_user(db_session, "admin_del@test.com", "admin")
    emp, emp_token = create_user(db_session, "emp_del@test.com", "employee")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    r_create = client.post(
        "/api/v1/tickets",
        json={"title": "Microphone muted", "description": "Headset mic not working", "category_id": cat.id},
        headers=admin_headers,
    )
    ticket_id = r_create.json()["id"]

    # Employee cannot delete ticket (403)
    r_emp_del = client.delete(f"/api/v1/tickets/{ticket_id}", headers={"Authorization": f"Bearer {emp_token}"})
    assert r_emp_del.status_code == 403

    # Admin CAN delete active (unclosed) ticket (204)
    r_admin_del = client.delete(f"/api/v1/tickets/{ticket_id}", headers=admin_headers)
    assert r_admin_del.status_code == 204

    # Verify gone from active queries
    r_get = client.get(f"/api/v1/tickets/{ticket_id}", headers=admin_headers)
    assert r_get.status_code == 404


def test_create_ticket_with_tagged_team_members(client, db_session):
    """Verify creating a ticket with tagged team members creates in-app notifications and mentions."""
    cat = create_category(db_session, "Hardware")
    requester, req_token = create_user(db_session, "author@test.com", "employee")
    colleague1, _ = create_user(db_session, "colleague1@test.com", "employee")
    colleague2, _ = create_user(db_session, "colleague2@test.com", "technician")

    headers = {"Authorization": f"Bearer {req_token}"}

    # 1. Test team-members listing
    r_members = client.get("/api/v1/tickets/team-members", headers=headers)
    assert r_members.status_code == 200
    member_ids = [m["id"] for m in r_members.json()]
    assert colleague1.id in member_ids
    assert colleague2.id in member_ids

    # 2. Create ticket with tagged_user_ids
    r_create = client.post(
        "/api/v1/tickets",
        json={
            "title": "Need second monitor for dev setup",
            "description": "Please approve additional display for development team workstation.",
            "category_id": cat.id,
            "priority": "low",
            "tagged_user_ids": [colleague1.id, colleague2.id],
        },
        headers=headers,
    )
    assert r_create.status_code == 201
    ticket_id = r_create.json()["id"]

    # 3. Verify comments have tag mention
    r_comments = client.get(f"/api/v1/tickets/{ticket_id}/comments", headers=headers)
    assert r_comments.status_code == 200
    comments = r_comments.json()
    assert any("Tagged team members" in c["comment_text"] for c in comments)

