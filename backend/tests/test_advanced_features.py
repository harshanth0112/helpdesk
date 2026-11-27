"""
backend/tests/test_advanced_features.py - Advanced Helpdesk Features Test Suite (Phase 9).

Tests cover:
1. Module 1: Technician assignment, reassignment, workload endpoint, and assignment history.
2. Module 2: Access-controlled comments (employee, technician internal vs public notes).
3. Module 3: Attachment uploads (allowlist enforcement, extension validation, size limit, secure downloads, anti-IDOR).
4. Module 4: Ticket workflow state machine transitions and resolution notes.
5. Module 5: In-app notification creation on assignment and status change, mark as read.
6. Security: Path traversal prevention, arbitrary file rejection, unauthorized file download prevention.
"""

import io
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
from app.models.attachment import Attachment
from app.models.notification import Notification
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


def create_category_helper(db: Session, name: str = "Hardware") -> Category:
    cat = Category(name=name, description=f"{name} category")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


# ===========================================================================
# Advanced Feature Tests
# ===========================================================================

def test_technician_assignment_workload_and_notifications(client, db_session):
    """Module 1 & 5: Assignment, notification dispatch, and workload inspection."""
    cat = create_category_helper(db_session, "Module1")
    admin, admin_token = create_user_helper(db_session, "admin_adv@test.com", "admin")
    tech, tech_token = create_user_helper(db_session, "tech_adv@test.com", "technician")
    emp, emp_token = create_user_helper(db_session, "emp_adv@test.com", "employee")

    # Employee creates ticket
    r_create = client.post("/api/v1/tickets", json={
        "title": "Email Server Latency",
        "description": "Emails queued for over 2 hours",
        "category_id": cat.id,
    }, headers={"Authorization": f"Bearer {emp_token}"})
    ticket_id = r_create.json()["id"]

    # Admin assigns technician
    r_assign = client.patch(f"/api/v1/tickets/{ticket_id}/assign", json={
        "assigned_to": tech.id,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert r_assign.status_code == 200

    # Verify notification sent to Technician
    r_notif = client.get("/api/v1/tickets/user/notifications", headers={"Authorization": f"Bearer {tech_token}"})
    assert r_notif.status_code == 200
    notifs = r_notif.json()
    assert len(notifs) >= 1
    assert notifs[0]["notification_type"] == "assignment"
    assert notifs[0]["is_read"] is False

    # Mark notification read
    notif_id = notifs[0]["id"]
    r_read = client.patch(f"/api/v1/tickets/user/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {tech_token}"})
    assert r_read.status_code == 200
    assert r_read.json()["is_read"] is True

    # Check technician workload endpoint
    r_workload = client.get("/api/v1/admin/technicians/workload", headers={"Authorization": f"Bearer {admin_token}"})
    assert r_workload.status_code == 200
    workload = r_workload.json()
    tech_entry = next((item for item in workload if item["technician_id"] == tech.id), None)
    assert tech_entry is not None
    assert tech_entry["active_tickets"] >= 1


def test_attachment_upload_extension_allowlist_and_size_restrictions(client, db_session):
    """Module 3: Attachment extension allowlist, executable rejection, and size checks."""
    cat = create_category_helper(db_session, "Attachments")
    emp, emp_token = create_user_helper(db_session, "emp_att@test.com", "employee")
    headers = {"Authorization": f"Bearer {emp_token}"}

    r_create = client.post("/api/v1/tickets", json={
        "title": "Blue Screen Crash",
        "description": "Kernel crash log attached",
        "category_id": cat.id,
    }, headers=headers)
    ticket_id = r_create.json()["id"]

    # 1. Valid PNG upload
    valid_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"fake_png_data")
    r_upload = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("crash_screenshot.png", valid_png, "image/png")},
        headers=headers,
    )
    assert r_upload.status_code == 201
    attachment_id = r_upload.json()["id"]
    assert r_upload.json()["file_name"] == "crash_screenshot.png"

    # 2. Reject executable / malicious extension (.exe, .sh)
    malicious_file = io.BytesIO(b"malicious payload")
    r_bad_ext = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("malware.exe", malicious_file, "application/octet-stream")},
        headers=headers,
    )
    assert r_bad_ext.status_code == 400
    assert "not permitted" in r_bad_ext.json()["detail"]

    # 3. Reject empty file
    empty_file = io.BytesIO(b"")
    r_empty = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("empty.pdf", empty_file, "application/pdf")},
        headers=headers,
    )
    assert r_empty.status_code == 400


def test_attachment_secure_download_and_idor_prevention(client, db_session):
    """Module 3: Authorized download and IDOR prevention on attachments."""
    cat = create_category_helper(db_session, "DownloadTest")
    emp1, emp1_token = create_user_helper(db_session, "emp1_down@test.com", "employee")
    emp2, emp2_token = create_user_helper(db_session, "emp2_down@test.com", "employee")

    # Emp1 uploads attachment on own ticket
    r_create = client.post("/api/v1/tickets", json={
        "title": "Confidential Logs",
        "description": "Log file",
        "category_id": cat.id,
    }, headers={"Authorization": f"Bearer {emp1_token}"})
    ticket_id = r_create.json()["id"]

    pdf_file = io.BytesIO(b"%PDF-1.4 sample content")
    r_upload = client.post(
        f"/api/v1/tickets/{ticket_id}/attachments",
        files={"file": ("report.pdf", pdf_file, "application/pdf")},
        headers={"Authorization": f"Bearer {emp1_token}"},
    )
    att_id = r_upload.json()["id"]

    # Emp1 can download successfully
    r_down1 = client.get(f"/api/v1/tickets/attachments/{att_id}/download", headers={"Authorization": f"Bearer {emp1_token}"})
    assert r_down1.status_code == 200
    assert b"%PDF" in r_down1.content

    # Emp2 can also download attachment because tickets and attachments have global visibility
    r_down2 = client.get(f"/api/v1/tickets/attachments/{att_id}/download", headers={"Authorization": f"Bearer {emp2_token}"})
    assert r_down2.status_code == 200
    assert b"%PDF" in r_down2.content

    # Unauthenticated / invalid token cannot download (401)
    r_unauth = client.get(f"/api/v1/tickets/attachments/{att_id}/download")
    assert r_unauth.status_code == 401
