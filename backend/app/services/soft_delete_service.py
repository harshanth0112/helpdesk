"""
app/services/soft_delete_service.py — Centralized Soft Delete & Admin Recycle Bin Service.

Enforces:
- Permanent protection for h641191@gmail.com (normalized trim + lowercase comparison).
- Admin-only authorization for all deletion and restoration operations.
- Self-deletion prevention and last-active-admin protection.
- Refresh token revocation on user soft deletion.
- Parent-child independence on restoration (restoring a ticket does not restore
  independently deleted comments/attachments).
- Complete audit trail for all *_SOFT_DELETED and *_RESTORED events.
"""

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.models.attachment import Attachment
from app.models.category import Category
from app.models.comment import Comment
from app.models.refresh_token import RefreshToken
from app.models.ticket import Ticket
from app.models.user import User
from app.services import audit_service

PROTECTED_ADMIN_EMAIL = "h641191@gmail.com"

ENTITY_MODEL_MAP = {
    "users": User,
    "tickets": Ticket,
    "comments": Comment,
    "attachments": Attachment,
    "categories": Category,
}

RESTORE_AUDIT_ACTIONS = {
    "users": "USER_RESTORED",
    "tickets": "TICKET_RESTORED",
    "comments": "COMMENT_RESTORED",
    "attachments": "ATTACHMENT_RESTORED",
    "categories": "CATEGORY_RESTORED",
}

ENTITY_SINGULAR = {
    "users": "user",
    "tickets": "ticket",
    "comments": "comment",
    "attachments": "attachment",
    "categories": "category",
}


def normalize_email(email: Optional[str]) -> str:
    """Normalize an email address for case-insensitive, whitespace-trimmed comparison."""
    return (email or "").strip().lower()


def is_protected_account(user_or_email: Union[User, str]) -> bool:
    """Return True if the user or email is the permanently protected administrator account."""
    if isinstance(user_or_email, str):
        return normalize_email(user_or_email) == PROTECTED_ADMIN_EMAIL
    return normalize_email(getattr(user_or_email, "email", None)) == PROTECTED_ADMIN_EMAIL


def count_active_admins(db: Session) -> int:
    """Count active, approved, non-deleted administrator accounts."""
    return (
        db.query(User)
        .filter(
            User.role == "admin",
            User.is_active.is_(True),
            User.approval_status == "approved",
            User.deleted_at.is_(None),
        )
        .count()
    )


def _clean_reason(reason: Optional[str]) -> Optional[str]:
    if reason and reason.strip():
        return reason.strip()[:500]
    return None


def _require_admin(actor: User) -> None:
    if not actor or actor.role != "admin":
        raise PermissionDeniedError("Only administrators can perform this action.")


def _revoke_user_refresh_tokens(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked.is_(False),
    ).update(
        {"is_revoked": True, "revoked_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )


def soft_delete_user(
    db: Session,
    user_id: int,
    actor: Optional[User] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    current_admin: Optional[User] = None,
    deletion_reason: Optional[str] = None,
) -> User:
    """Soft-delete a user account with protected-account, self-delete, and last-admin checks."""
    effective_admin = actor or current_admin
    effective_reason = reason if reason is not None else deletion_reason
    _require_admin(effective_admin)

    user = db.get(User, user_id)
    if not user:
        raise ResourceNotFoundError("User not found.")

    if is_protected_account(user):
        raise PermissionDeniedError(
            "This administrator account is permanently protected and cannot be deleted."
        )

    if user.id == effective_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account.",
        )

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User account is already deleted.",
        )

    if user.role == "admin" and user.is_active and user.approval_status == "approved":
        if count_active_admins(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last active administrator.",
            )

    now = datetime.now(timezone.utc)
    cleaned_reason = _clean_reason(effective_reason)
    try:
        user.deleted_at = now
        user.deleted_by = effective_admin.id
        user.deletion_reason = cleaned_reason
        _revoke_user_refresh_tokens(db, user.id)
        db.commit()
        db.refresh(user)

        audit_service.record_audit_event(
            db=db,
            action="USER_SOFT_DELETED",
            actor_id=effective_admin.id,
            entity_type="user",
            entity_id=user.id,
            old_values={"deleted_at": None},
            new_values={
                "deleted_at": now.isoformat(),
                "deleted_by": effective_admin.id,
                "deletion_reason": cleaned_reason,
                "email": user.email,
                "role": user.role,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return user
    except Exception:
        db.rollback()
        raise


def soft_delete_ticket(
    db: Session,
    ticket_id: int,
    actor: User,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Ticket:
    """Soft-delete a closed/resolved ticket (Admin-only) without cascading to child rows."""
    _require_admin(actor)

    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise ResourceNotFoundError("Ticket not found.")

    if ticket.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticket is already deleted.",
        )

    if ticket.status not in ("closed", "resolved"):
        raise PermissionDeniedError(
            "Cannot delete an active ticket. Please close or resolve the ticket first."
        )

    now = datetime.now(timezone.utc)
    cleaned_reason = _clean_reason(reason)
    ticket.deleted_at = now
    ticket.deleted_by = actor.id
    ticket.deletion_reason = cleaned_reason
    db.commit()
    db.refresh(ticket)

    audit_service.record_audit_event(
        db=db,
        action="TICKET_SOFT_DELETED",
        actor_id=actor.id,
        entity_type="ticket",
        entity_id=ticket.id,
        ticket_id=ticket.id,
        old_values={"deleted_at": None},
        new_values={
            "deleted_at": now.isoformat(),
            "deleted_by": actor.id,
            "deletion_reason": cleaned_reason,
            "ticket_number": ticket.ticket_number,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return ticket


def soft_delete_comment(
    db: Session,
    ticket_id: int,
    comment_id: int,
    actor: User,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Comment:
    """Admin-only soft deletion of a comment."""
    _require_admin(actor)

    comment = db.get(Comment, comment_id)
    if not comment or comment.ticket_id != ticket_id:
        raise ResourceNotFoundError("Comment not found.")

    if comment.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Comment is already deleted.",
        )

    now = datetime.now(timezone.utc)
    cleaned_reason = _clean_reason(reason)
    comment.deleted_at = now
    comment.deleted_by = actor.id
    comment.deletion_reason = cleaned_reason
    db.commit()
    db.refresh(comment)

    audit_service.record_audit_event(
        db=db,
        action="COMMENT_SOFT_DELETED",
        actor_id=actor.id,
        entity_type="comment",
        entity_id=comment.id,
        ticket_id=comment.ticket_id,
        old_values={"deleted_at": None},
        new_values={
            "deleted_at": now.isoformat(),
            "deleted_by": actor.id,
            "deletion_reason": cleaned_reason,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return comment


def soft_delete_attachment(
    db: Session,
    attachment_id: int,
    actor: User,
    ticket_id: Optional[int] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Attachment:
    """Admin-only soft deletion of an attachment. Physical file on disk is preserved."""
    _require_admin(actor)

    attachment = db.get(Attachment, attachment_id)
    if not attachment or (ticket_id is not None and attachment.ticket_id != ticket_id):
        raise ResourceNotFoundError("Attachment not found.")

    if attachment.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attachment is already deleted.",
        )

    now = datetime.now(timezone.utc)
    cleaned_reason = _clean_reason(reason)
    attachment.deleted_at = now
    attachment.deleted_by = actor.id
    attachment.deletion_reason = cleaned_reason
    db.commit()
    db.refresh(attachment)

    audit_service.record_audit_event(
        db=db,
        action="ATTACHMENT_SOFT_DELETED",
        actor_id=actor.id,
        entity_type="attachment",
        entity_id=attachment.id,
        ticket_id=attachment.ticket_id,
        old_values={"deleted_at": None},
        new_values={
            "deleted_at": now.isoformat(),
            "deleted_by": actor.id,
            "deletion_reason": cleaned_reason,
            "file_name": attachment.file_name,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return attachment


def soft_delete_category(
    db: Session,
    category_id: int,
    actor: Optional[User] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    current_admin: Optional[User] = None,
    deletion_reason: Optional[str] = None,
) -> Category:
    """Admin-only soft deletion of a category, blocked if active tickets depend on it."""
    effective_admin = actor or current_admin
    effective_reason = reason if reason is not None else deletion_reason
    _require_admin(effective_admin)

    category = db.get(Category, category_id)
    if not category:
        raise ResourceNotFoundError("Category not found.")

    if category.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category is already deleted.",
        )

    active_tickets = (
        db.query(Ticket)
        .filter(Ticket.category_id == category_id, Ticket.deleted_at.is_(None))
        .count()
    )
    if active_tickets > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete category because {active_tickets} active ticket(s) depend on it.",
        )

    now = datetime.now(timezone.utc)
    cleaned_reason = _clean_reason(effective_reason)
    try:
        category.deleted_at = now
        category.deleted_by = effective_admin.id
        category.deletion_reason = cleaned_reason
        db.commit()
        db.refresh(category)

        audit_service.record_audit_event(
            db=db,
            action="CATEGORY_SOFT_DELETED",
            actor_id=effective_admin.id,
            entity_type="category",
            entity_id=category.id,
            old_values={"deleted_at": None},
            new_values={
                "deleted_at": now.isoformat(),
                "deleted_by": effective_admin.id,
                "deletion_reason": cleaned_reason,
                "name": category.name,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return category
    except Exception:
        db.rollback()
        raise


def _validate_entity(entity: str) -> str:
    key = (entity or "").strip().lower()
    if key not in ENTITY_MODEL_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity '{entity}'. Must be one of: {', '.join(ENTITY_MODEL_MAP.keys())}.",
        )
    return key


def _serialize_deleted_record(
    entity: str,
    record: Any,
    actor_map: Dict[int, User],
) -> Dict[str, Any]:
    actor = actor_map.get(record.deleted_by) if record.deleted_by else None
    deleted_by_name = (
        f"{actor.first_name} {actor.last_name}".strip() or actor.email
        if actor
        else None
    )

    if entity == "users":
        title = f"{record.first_name} {record.last_name}".strip()
        subtitle = record.email
        identifier = f"USR-{record.id}"
        status_label = f"{record.approval_status} ({'active' if record.is_active else 'inactive'})"
    elif entity == "tickets":
        title = record.title
        subtitle = f"Status: {record.status} | Priority: {record.priority}"
        identifier = record.ticket_number
        status_label = record.status
    elif entity == "comments":
        preview = (record.comment_text or "")[:100]
        title = preview + ("..." if len(record.comment_text or "") > 100 else "")
        subtitle = f"Ticket #{record.ticket_id} | {'Internal' if record.is_internal else 'Public'}"
        identifier = f"CMT-{record.id}"
        status_label = "internal" if record.is_internal else "public"
    elif entity == "attachments":
        title = record.file_name
        subtitle = f"Ticket #{record.ticket_id} | {record.mime_type}"
        identifier = f"ATT-{record.id}"
        status_label = f"{round((record.file_size_bytes or 0) / 1024, 1)} KB"
    else:  # categories
        title = record.name
        subtitle = record.description or "No description"
        identifier = f"CAT-{record.id}"
        status_label = "active" if record.is_active else "inactive"

    return {
        "id": record.id,
        "entity": entity,
        "identifier": identifier,
        "title": title,
        "subtitle": subtitle,
        "status": status_label,
        "deletion_status": "soft_deleted",
        "deleted_at": record.deleted_at,
        "deleted_by": record.deleted_by,
        "deleted_by_name": deleted_by_name,
        "deleted_by_email": actor.email if actor else None,
        "deletion_reason": record.deletion_reason,
    }


def list_recycle_bin(
    db: Session,
    entity: str,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "deleted_at",
    sort_order: str = "desc",
) -> Dict[str, Any]:
    """List soft-deleted records for a given entity with search, filter, sort, and pagination."""
    entity_key = _validate_entity(entity)
    model = ENTITY_MODEL_MAP[entity_key]

    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = db.query(model).filter(model.deleted_at.isnot(None))

    if search and search.strip():
        term = f"%{search.strip()}%"
        if entity_key == "users":
            query = query.filter(
                or_(
                    User.email.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                )
            )
        elif entity_key == "tickets":
            query = query.filter(
                or_(
                    Ticket.ticket_number.ilike(term),
                    Ticket.title.ilike(term),
                    Ticket.description.ilike(term),
                )
            )
        elif entity_key == "comments":
            query = query.filter(Comment.comment_text.ilike(term))
        elif entity_key == "attachments":
            query = query.filter(Attachment.file_name.ilike(term))
        elif entity_key == "categories":
            query = query.filter(
                or_(Category.name.ilike(term), Category.description.ilike(term))
            )

    if status_filter and status_filter.strip():
        sf = status_filter.strip().lower()
        if entity_key == "users":
            query = query.filter(User.approval_status == sf)
        elif entity_key == "tickets":
            query = query.filter(Ticket.status == sf)
        elif entity_key == "categories":
            if sf in ("active", "true"):
                query = query.filter(Category.is_active.is_(True))
            elif sf in ("inactive", "false"):
                query = query.filter(Category.is_active.is_(False))

    total = query.count()

    sort_col_map = {
        "deleted_at": model.deleted_at,
        "id": model.id,
    }
    if entity_key == "users":
        sort_col_map["name"] = User.email
    elif entity_key == "tickets":
        sort_col_map["name"] = Ticket.title
    elif entity_key == "attachments":
        sort_col_map["name"] = Attachment.file_name
    elif entity_key == "categories":
        sort_col_map["name"] = Category.name

    sort_col = sort_col_map.get(sort_by, model.deleted_at)
    query = query.order_by(asc(sort_col) if sort_order.lower() == "asc" else desc(sort_col))

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    actor_ids = {r.deleted_by for r in rows if r.deleted_by is not None}
    actor_map: Dict[int, User] = {}
    if actor_ids:
        actors = db.query(User).filter(User.id.in_(actor_ids)).all()
        actor_map = {a.id: a for a in actors}

    items = [_serialize_deleted_record(entity_key, r, actor_map) for r in rows]
    return {
        "entity": entity_key,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def restore_entity(
    db: Session,
    entity: str,
    record_id: int,
    actor: Optional[User] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    current_admin: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Admin-only restoration of a soft-deleted record.
    - Clears only deletion metadata (deleted_at, deleted_by, deletion_reason).
    - Never modifies user approval_status or is_active.
    - Never auto-restores independently deleted child comments/attachments.
    """
    effective_admin = actor or current_admin
    _require_admin(effective_admin)
    entity_key = _validate_entity(entity)
    model = ENTITY_MODEL_MAP[entity_key]

    record = db.get(model, record_id)
    if not record:
        raise ResourceNotFoundError(f"{ENTITY_SINGULAR[entity_key].capitalize()} not found.")

    if record.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{ENTITY_SINGULAR[entity_key].capitalize()} is not deleted.",
        )

    old_values = {
        "deleted_at": record.deleted_at.isoformat(),
        "deleted_by": record.deleted_by,
        "deletion_reason": record.deletion_reason,
    }

    try:
        record.deleted_at = None
        record.deleted_by = None
        record.deletion_reason = None
        db.commit()
        db.refresh(record)

        ticket_id = None
        if entity_key == "tickets":
            ticket_id = record.id
        elif entity_key in ("comments", "attachments"):
            ticket_id = record.ticket_id

        audit_service.record_audit_event(
            db=db,
            action=RESTORE_AUDIT_ACTIONS[entity_key],
            actor_id=effective_admin.id,
            entity_type=ENTITY_SINGULAR[entity_key],
            entity_id=record.id,
            ticket_id=ticket_id,
            old_values=old_values,
            new_values={"deleted_at": None, "restored_by": effective_admin.id},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "status": "restored",
            "entity": entity_key,
            "id": record.id,
            "restored_by": effective_admin.id,
        }
    except Exception:
        db.rollback()
        raise
