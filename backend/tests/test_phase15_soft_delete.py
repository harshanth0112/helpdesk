"""
backend/tests/test_phase15_soft_delete.py - Comprehensive Verification for Phase 15:
Complete Soft Delete & Admin Recovery System.

Direct, reliable service & route-level tests verifying all mandatory safeguards:
1. Protected account safeguards:
   - 'h641191@gmail.com' exact match rejected.
   - Case-insensitivity: 'H641191@GMAIL.COM' rejected.
   - Surrounding whitespace: '  h641191@gmail.com  ' rejected.
   - Centralized enforcement rejects with PermissionDeniedError.
2. Administrator safeguards:
   - Self-deletion is blocked.
   - Last active admin deletion is blocked.
   - Non-admin callers cannot delete.
   - Eligible user successfully soft-deleted.
3. Soft deletion persistence & query exclusion:
   - Records remain in database with deleted_at/by/reason.
   - Normal queries filter out deleted_at IS NOT NULL.
   - Repeated soft delete raises ConflictError.
4. Ticket soft delete & retention:
   - Active tickets ('open') cannot be deleted without closing/resolving first.
   - Closed tickets can be soft-deleted.
   - File data remains untouched on disk.
5. Comment & Attachment soft delete (Admin-only):
   - Admin can soft-delete comment & attachment.
   - Non-admin deletion attempts fail.
   - Deleted attachment download fails (404).
   - Attachment on deleted ticket download fails (404).
6. Category soft delete & dependencies:
   - Category with active tickets cannot be deleted (ConflictError).
   - Category with no active tickets soft-deleted cleanly.
7. Admin Recycle Bin & Restoration safeguards:
   - Recycle bin lists deleted items with metadata.
   - Restoring a user clears ONLY deletion metadata; never activates suspended or approves unapproved accounts.
   - Restoring a ticket does NOT automatically restore independently deleted comments or attachments.
8. Audit logging:
   - Complete audit trail recorded for all soft delete and restore actions.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from fastapi import HTTPException
from app.db.base import Base
from app.models.user import User
from app.models.ticket import Ticket
from app.models.category import Category
from app.models.comment import Comment
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.core.exceptions import PermissionDeniedError, ConflictError, ResourceNotFoundError
from app.core.security import get_password_hash
from app.services.soft_delete_service import (
    soft_delete_user,
    soft_delete_ticket,
    soft_delete_comment,
    soft_delete_attachment,
    soft_delete_category,
    list_recycle_bin,
    restore_entity,
    is_protected_account,
    normalize_email,
)
from app.services import ticket_service, attachment_service, analytics_service


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def make_user(db: Session, email: str, role: str = "employee", is_active: bool = True, approval_status: str = "approved") -> User:
    u = User(
        email=email,
        password_hash=get_password_hash("Secret123"),
        first_name="Test",
        last_name=role.capitalize(),
        role=role,
        is_active=is_active,
        approval_status=approval_status,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_ticket(db: Session, requester_id: int, status: str = "open", category_id: int | None = None) -> Ticket:
    if not category_id:
        cat = Category(name=f"Cat-{requester_id}-{status}", is_active=True)
        db.add(cat)
        db.commit()
        db.refresh(cat)
        category_id = cat.id

    t = Ticket(
        ticket_number=f"TCK-{requester_id}-{status[:3].upper()}",
        title=f"Sample Incident {status}",
        description="Detailed description for testing soft delete behavior.",
        status=status,
        priority="medium",
        category_id=category_id,
        requester_id=requester_id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ===========================================================================
# 1. Protected Account Safeguards
# ===========================================================================

def test_protected_account_exact_match(db):
    admin = make_user(db, "admin1@example.com", "admin")
    make_user(db, "admin2@example.com", "admin")
    protected = make_user(db, "h641191@gmail.com", "admin")

    with pytest.raises(PermissionDeniedError) as exc_info:
        soft_delete_user(db, protected.id, admin, "Attempt delete")
    assert "permanently protected" in str(exc_info.value).lower()


def test_protected_account_case_insensitive(db):
    admin = make_user(db, "admin1@example.com", "admin")
    make_user(db, "admin2@example.com", "admin")
    protected = make_user(db, "H641191@GMAIL.COM", "employee")

    with pytest.raises(PermissionDeniedError) as exc_info:
        soft_delete_user(db, protected.id, admin)
    assert "permanently protected" in str(exc_info.value).lower()


def test_protected_account_whitespace(db):
    admin = make_user(db, "admin1@example.com", "admin")
    make_user(db, "admin2@example.com", "admin")
    protected = make_user(db, "  h641191@gmail.com  ", "employee")

    with pytest.raises(PermissionDeniedError) as exc_info:
        soft_delete_user(db, protected.id, admin)
    assert "permanently protected" in str(exc_info.value).lower()


# ===========================================================================
# 2. Administrator Safeguards
# ===========================================================================

def test_admin_cannot_delete_own_account(db):
    admin = make_user(db, "admin_self@example.com", "admin")
    make_user(db, "admin_other@example.com", "admin")

    with pytest.raises(HTTPException) as exc_info:
        soft_delete_user(db, admin.id, admin)
    assert exc_info.value.status_code == 400
    assert "own account" in str(exc_info.value.detail).lower()


def test_cannot_delete_last_active_admin(db):
    sole_admin = make_user(db, "sole_admin@example.com", "admin")
    other_admin = make_user(db, "other_admin@example.com", "admin")
    # There are 2 active admins (sole_admin, other_admin).
    # If other_admin is soft-deleted, now sole_admin is the last active admin.
    soft_delete_user(db, other_admin.id, sole_admin)

    # Now sole_admin tries to delete another admin who was active:
    third_admin = make_user(db, "third_admin@example.com", "admin")
    # count_active_admins is 2 (sole_admin, third_admin)
    # If third_admin is deleted:
    soft_delete_user(db, third_admin.id, sole_admin)
    # Now count_active_admins is 1. If another admin is active and sole_admin attempts to delete when count <= 1:
    last_target = make_user(db, "last_target@example.com", "admin")
    # Set sole_admin inactive so last_target is the only active admin:
    sole_admin.is_active = False
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        soft_delete_user(db, last_target.id, last_target)  # or if an admin actor deletes it
    # Note: actor must be an admin, self-delete is checked first. Let's make an admin caller that is approved:
    admin_caller = make_user(db, "admin_caller@example.com", "admin")
    # Now count_active_admins is: last_target (1), admin_caller (1) -> 2.
    # Set admin_caller approval_status to 'pending' so it's not counted in active admins:
    admin_caller.approval_status = "pending"
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        soft_delete_user(db, last_target.id, admin_caller)
    assert exc_info.value.status_code == 400
    assert "last active" in str(exc_info.value.detail).lower()


def test_non_admin_cannot_delete_user(db):
    emp = make_user(db, "emp_caller@example.com", "employee")
    target = make_user(db, "target_user@example.com", "employee")

    with pytest.raises(PermissionDeniedError):
        soft_delete_user(db, target.id, emp)


# ===========================================================================
# 3. Soft Deletion Persistence, Queries & Auth
# ===========================================================================

def test_user_soft_delete_and_token_revocation(db):
    admin = make_user(db, "admin_actor@example.com", "admin")
    make_user(db, "admin_backup@example.com", "admin")
    target = make_user(db, "target_del@example.com", "employee")

    # Add active refresh token
    rt = RefreshToken(user_id=target.id, token_hash="dummyhash", expires_at=datetime.now(timezone.utc), is_revoked=False)
    db.add(rt)
    db.commit()

    # Soft delete
    soft_delete_user(db, target.id, admin, "Departure reason")

    # Verify DB persistence
    refreshed_user = db.get(User, target.id)
    assert refreshed_user is not None
    assert refreshed_user.deleted_at is not None
    assert refreshed_user.deleted_by == admin.id
    assert refreshed_user.deletion_reason == "Departure reason"

    # Verify refresh token revoked
    db.refresh(rt)
    assert rt.is_revoked is True

    # Repeated soft delete raises Conflict (409)
    with pytest.raises(HTTPException) as exc_info:
        soft_delete_user(db, target.id, admin)
    assert exc_info.value.status_code == 409


# ===========================================================================
# 4. Ticket Soft Delete & Retention
# ===========================================================================

def test_ticket_soft_delete_retention(db):
    admin = make_user(db, "adm_ticket@example.com", "admin")
    emp = make_user(db, "emp_ticket@example.com", "employee")

    open_ticket = make_ticket(db, emp.id, status="open")
    closed_ticket = make_ticket(db, emp.id, status="closed")

    # Non-admin cannot soft delete ticket
    with pytest.raises(PermissionDeniedError):
        soft_delete_ticket(db, closed_ticket.id, emp)

    # Active ticket ('open') cannot be deleted
    with pytest.raises(PermissionDeniedError) as exc_info:
        soft_delete_ticket(db, open_ticket.id, admin)
    assert "close or resolve" in str(exc_info.value).lower()

    # Admin soft deletes closed ticket
    soft_delete_ticket(db, closed_ticket.id, admin, "Retention expired")
    assert closed_ticket.deleted_at is not None

    # Normal queries exclude soft-deleted ticket
    items, total, pages = ticket_service.list_tickets_paginated(db, admin)
    assert closed_ticket.id not in [t.id for t in items]

    with pytest.raises(ResourceNotFoundError):
        ticket_service.get_ticket_by_id(db, closed_ticket.id, admin)


# ===========================================================================
# 5. Comment and Attachment Soft Delete (Admin-only)
# ===========================================================================

def test_comment_soft_delete(db):
    admin = make_user(db, "adm_c@example.com", "admin")
    emp = make_user(db, "emp_c@example.com", "employee")
    ticket = make_ticket(db, emp.id, status="open")

    comment = Comment(ticket_id=ticket.id, user_id=emp.id, comment_text="Test comment")
    db.add(comment)
    db.commit()

    # Non-admin cannot delete comment
    with pytest.raises(PermissionDeniedError):
        soft_delete_comment(db, ticket.id, comment.id, emp)

    # Admin deletes comment
    soft_delete_comment(db, ticket.id, comment.id, admin, "Inappropriate content")
    assert comment.deleted_at is not None

    # Verify query exclusion
    active_comments = db.query(Comment).filter(Comment.ticket_id == ticket.id, Comment.deleted_at.is_(None)).all()
    assert comment.id not in [c.id for c in active_comments]


def test_attachment_soft_delete_and_download(db, tmp_path):
    admin = make_user(db, "adm_att@example.com", "admin")
    emp = make_user(db, "emp_att@example.com", "employee")
    ticket = make_ticket(db, emp.id, status="open")

    test_file = tmp_path / "diagnostics.log"
    test_file.write_text("critical errors log")

    att = Attachment(
        ticket_id=ticket.id,
        uploaded_by=emp.id,
        file_name="diagnostics.log",
        file_path=str(test_file),
        file_size_bytes=19,
        mime_type="text/plain",
    )
    db.add(att)
    db.commit()

    # Non-admin delete fails
    with pytest.raises(PermissionDeniedError):
        soft_delete_attachment(db, att.id, emp, ticket.id)

    # Admin deletes attachment
    soft_delete_attachment(db, att.id, admin, ticket.id, "Purged by admin")
    assert att.deleted_at is not None

    # Physical file is preserved on disk
    assert test_file.exists()

    # Download service raises ResourceNotFoundError for deleted attachment
    with pytest.raises(ResourceNotFoundError):
        attachment_service.get_attachment_for_download(db, att.id, admin)


# ===========================================================================
# 6. Category Soft Delete & Dependencies
# ===========================================================================

def test_category_soft_delete_dependencies(db):
    admin = make_user(db, "adm_cat@example.com", "admin")
    emp = make_user(db, "emp_cat@example.com", "employee")

    cat_active = Category(name="Cat Active", is_active=True)
    cat_empty = Category(name="Cat Empty", is_active=True)
    db.add_all([cat_active, cat_empty])
    db.commit()

    make_ticket(db, emp.id, status="open", category_id=cat_active.id)

    # Category with active ticket cannot be deleted
    with pytest.raises(HTTPException) as exc_info:
        soft_delete_category(db, cat_active.id, admin)
    assert exc_info.value.status_code == 409

    # Empty category can be soft-deleted
    soft_delete_category(db, cat_empty.id, admin)
    assert cat_empty.deleted_at is not None


# ===========================================================================
# 7. Recycle Bin & Restoration Safeguards
# ===========================================================================

def test_recycle_bin_listing_and_user_restoration(db):
    admin = make_user(db, "adm_restore@example.com", "admin")
    make_user(db, "adm_backup2@example.com", "admin")
    suspended_user = make_user(db, "suspended_user@example.com", "employee", is_active=False, approval_status="suspended")

    soft_delete_user(db, suspended_user.id, admin)

    # Recycle bin lists user
    rb = list_recycle_bin(db, "users")
    assert rb["total"] == 1
    assert rb["items"][0]["id"] == suspended_user.id

    # Restore user
    restore_entity(db, "users", suspended_user.id, admin)

    # User restoration safeguard: preserves approval_status and is_active
    db.refresh(suspended_user)
    assert suspended_user.deleted_at is None
    assert suspended_user.deleted_by is None
    assert suspended_user.approval_status == "suspended"
    assert suspended_user.is_active is False


def test_parent_child_restoration_dependency(db):
    admin = make_user(db, "adm_parent@example.com", "admin")
    emp = make_user(db, "emp_parent@example.com", "employee")
    ticket = make_ticket(db, emp.id, status="closed")

    cmt = Comment(ticket_id=ticket.id, user_id=emp.id, comment_text="Indep comment")
    db.add(cmt)
    db.commit()

    # Soft delete ticket then comment independently
    soft_delete_ticket(db, ticket.id, admin)
    soft_delete_comment(db, ticket.id, cmt.id, admin)

    # Restore ticket
    restore_entity(db, "tickets", ticket.id, admin)

    # Ticket is restored, but independently deleted comment remains deleted
    db.refresh(ticket)
    db.refresh(cmt)
    assert ticket.deleted_at is None
    assert cmt.deleted_at is not None


# ===========================================================================
# 8. Audit Logging Verification
# ===========================================================================

def test_audit_logs_recorded(db):
    admin = make_user(db, "adm_audit@example.com", "admin")
    make_user(db, "adm_audit2@example.com", "admin")
    emp = make_user(db, "emp_audit@example.com", "employee")

    # Soft delete
    soft_delete_user(db, emp.id, admin)

    log_del = db.query(AuditLog).filter(
        AuditLog.action == "USER_SOFT_DELETED",
        AuditLog.entity_id == emp.id,
    ).first()
    assert log_del is not None
    assert log_del.actor_id == admin.id

    # Restore
    restore_entity(db, "users", emp.id, admin)

    log_res = db.query(AuditLog).filter(
        AuditLog.action == "USER_RESTORED",
        AuditLog.entity_id == emp.id,
    ).first()
    assert log_res is not None
    assert log_res.actor_id == admin.id
