import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, Session
from app.db.base import Base
from app.models import (
    User,
    Category,
    Ticket,
    Comment,
    Attachment,
    AuditLog,
    RefreshToken,
    PasswordResetToken
)


@pytest.fixture(scope="module")
def db_session():
    # In-memory SQLite engine for fast, isolated integration testing of SQLAlchemy 2.0 models & relationships
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_create_user_and_category(db_session: Session):
    # Create user
    admin = User(
        email="admin@test.com",
        password_hash="hashed_secret",
        first_name="Admin",
        last_name="User",
        role="admin",
        department="IT"
    )
    tech = User(
        email="tech@test.com",
        password_hash="hashed_secret",
        first_name="Tech",
        last_name="Support",
        role="technician",
        department="Helpdesk"
    )
    emp = User(
        email="emp@test.com",
        password_hash="hashed_secret",
        first_name="John",
        last_name="Doe",
        role="employee",
        department="Sales"
    )
    hardware = Category(name="Hardware & Laptops", description="Physical devices")

    db_session.add_all([admin, tech, emp, hardware])
    db_session.commit()

    assert admin.id is not None
    assert tech.id is not None
    assert emp.id is not None
    assert hardware.id is not None


def test_create_ticket_relationships(db_session: Session):
    emp = db_session.execute(select(User).where(User.email == "emp@test.com")).scalar_one()
    tech = db_session.execute(select(User).where(User.email == "tech@test.com")).scalar_one()
    cat = db_session.execute(select(Category).where(Category.name == "Hardware & Laptops")).scalar_one()

    # Create ticket
    ticket = Ticket(
        ticket_number="TICK-TEST-001",
        title="Laptop battery swollen",
        description="Battery chassis expanded overnight.",
        status="in_progress",
        priority="high",
        category=cat,
        requester=emp,
        assignee=tech
    )
    db_session.add(ticket)
    db_session.commit()

    assert ticket.id is not None
    # Relationship verification
    assert ticket.requester.email == "emp@test.com"
    assert ticket.assignee.email == "tech@test.com"
    assert ticket.category.name == "Hardware & Laptops"
    assert len(emp.requested_tickets) == 1
    assert len(tech.assigned_tickets) == 1


def test_comments_attachments_audit_cascade(db_session: Session):
    ticket = db_session.execute(select(Ticket).where(Ticket.ticket_number == "TICK-TEST-001")).scalar_one()
    emp = db_session.execute(select(User).where(User.email == "emp@test.com")).scalar_one()
    tech = db_session.execute(select(User).where(User.email == "tech@test.com")).scalar_one()

    # Add comments
    c1 = Comment(ticket=ticket, user=emp, comment_text="Attached photos of the chassis.")
    c2 = Comment(ticket=ticket, user=tech, comment_text="Scheduled replacement unit.", is_internal=True)

    # Add attachment
    att = Attachment(
        ticket=ticket,
        uploader=emp,
        file_name="battery_photo.jpg",
        file_path="/uploads/battery_photo.jpg",
        file_size_bytes=204800,
        mime_type="image/jpeg"
    )

    # Add audit log
    audit = AuditLog(
        ticket=ticket,
        actor=tech,
        action="status_change",
        old_values={"status": "open"},
        new_values={"status": "in_progress"},
        ip_address="10.0.0.1"
    )

    # Add tokens
    now = datetime.now(timezone.utc)
    refresh = RefreshToken(
        user=emp,
        token_hash="sample_refresh_token_hash_abc123",
        expires_at=now + timedelta(days=7)
    )
    pwd_reset = PasswordResetToken(
        user=emp,
        token_hash="sample_reset_token_hash_xyz789",
        expires_at=now + timedelta(hours=1)
    )

    db_session.add_all([c1, c2, att, audit, refresh, pwd_reset])
    db_session.commit()

    assert len(ticket.comments) == 2
    assert len(ticket.attachments) == 1
    assert len(ticket.audit_logs) == 1
    assert len(emp.refresh_tokens) == 1
    assert len(emp.password_reset_tokens) == 1
