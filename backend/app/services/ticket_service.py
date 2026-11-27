"""
app/services/ticket_service.py - Core Service and Data Access for Tickets.

Handles:
- CRUD logic with audit log tracking (ticket history).
- Scoped querying for Employee, Technician, and Admin.
- Full text / substring search across title and description.
- Filtering by status, priority, category_id, assigned_to.
- Whitelisted field sorting (asc/desc) with SQL injection prevention.
- Safe pagination with enforced upper bounds (max page size: 100).
- State transitions via validate_status_transition.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, desc, asc

from app.models.user import User
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.core.permissions import check_ticket_access
from app.core.ticket_state import validate_status_transition, VALID_PRIORITIES
from app.schemas.ticket import (
    TicketCreate,
    TicketPutUpdate,
    TicketStatusUpdate,
    TicketPriorityUpdate,
    TicketAssignUpdate,
)

ALLOWED_SORT_FIELDS = {
    "created_at": Ticket.created_at,
    "updated_at": Ticket.updated_at,
    "priority": Ticket.priority,
    "status": Ticket.status,
    "title": Ticket.title,
    "ticket_number": Ticket.ticket_number,
}


def log_audit(
    db: Session,
    ticket_id: int,
    actor_id: Optional[int],
    action: str,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
) -> None:
    audit = AuditLog(
        ticket_id=ticket_id,
        actor_id=actor_id,
        action=action,
        old_values=old_values,
        new_values=new_values,
    )
    db.add(audit)


def create_ticket(db: Session, payload: TicketCreate, user: User) -> Ticket:
    ticket_number = f"TICK-{uuid.uuid4().hex[:8].upper()}"
    ticket = Ticket(
        ticket_number=ticket_number,
        title=payload.title,
        description=payload.description,
        status="open",
        priority=payload.priority,
        category_id=payload.category_id,
        requester_id=user.id,
        assigned_to=None,
    )
    db.add(ticket)
    db.flush()

    tagged_names = []
    if payload.tagged_user_ids:
        from app.services.notification_service import create_notification
        from app.models.comment import Comment

        tagged_users = (
            db.query(User)
            .filter(
                User.id.in_(payload.tagged_user_ids),
                User.is_active.is_(True),
                User.approval_status == "approved",
                User.deleted_at.is_(None),
            )
            .all()
        )
        for tu in tagged_users:
            if tu.id != user.id:
                create_notification(
                    db=db,
                    user_id=tu.id,
                    ticket_id=ticket.id,
                    title=f"Tagged in Ticket #{ticket.ticket_number}",
                    message=f"{user.first_name} {user.last_name} tagged you in ticket '{ticket.title}'.",
                    notification_type="mention",
                )
                tagged_names.append(f"@{tu.first_name} {tu.last_name}")

        if tagged_names:
            comment_text = f"Tagged team members: {', '.join(tagged_names)}"
            tag_comment = Comment(
                ticket_id=ticket.id,
                user_id=user.id,
                comment_text=comment_text,
                is_internal=False,
            )
            db.add(tag_comment)

    log_audit(
        db,
        ticket_id=ticket.id,
        actor_id=user.id,
        action="ticket_created",
        new_values={
            "title": ticket.title,
            "status": ticket.status,
            "priority": ticket.priority,
            "category_id": ticket.category_id,
            "tagged_users": tagged_names,
        },
    )
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_by_id(db: Session, ticket_id: int, user: User) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.deleted_at is not None:
        raise ResourceNotFoundError("Ticket not found.")
    check_ticket_access(user, ticket)
    return ticket


def list_tickets_paginated(
    db: Session,
    user: User,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    category_id: Optional[int] = None,
    assigned_to: Optional[int] = None,
    requester_id: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[Ticket], int, int]:
    """
    Paginated, searched, filtered, and sorted ticket listing with global visibility.
    All active/approved roles (Employee, Technician, Admin) can view all tickets.
    Optional requester_id and assigned_to filters allow scoped views (e.g. 'My Tickets').
    Excludes soft-deleted tickets.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)  # Bound between 1 and 100

    query = db.query(Ticket).filter(Ticket.deleted_at.is_(None))

    # 1. Search query (title and description)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(Ticket.title.ilike(term), Ticket.description.ilike(term)))

    # 2. Filters
    if status_filter:
        query = query.filter(Ticket.status == status_filter.lower())
    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter.lower())
    if category_id is not None:
        query = query.filter(Ticket.category_id == category_id)
    if assigned_to is not None:
        query = query.filter(Ticket.assigned_to == assigned_to)
    if requester_id is not None:
        query = query.filter(Ticket.requester_id == requester_id)

    # 3. Total count
    total = query.count()

    # 4. Sorting (allowlist validated to prevent SQL injection)
    sort_col = ALLOWED_SORT_FIELDS.get(sort_by, Ticket.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # 5. Pagination
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return items, total, total_pages


def put_update_ticket(db: Session, ticket_id: int, payload: TicketPutUpdate, user: User) -> Ticket:
    """
    PUT /api/v1/tickets/{id} - Full update of title/description/category.
    - Employee: can only update own tickets and only if ticket is still in 'open' or 'assigned' state.
    - Technician: forbidden (technicians update status/resolution notes).
    - Admin: can update any ticket.
    """
    ticket = get_ticket_by_id(db, ticket_id, user)

    if user.role == "technician":
        raise PermissionDeniedError("Technicians cannot edit general ticket details directly.")

    if user.role == "employee":
        if ticket.requester_id != user.id:
            raise PermissionDeniedError("Employees can only modify their own tickets.")
        if ticket.status in ("resolved", "closed"):
            raise PermissionDeniedError("Cannot modify a resolved or closed ticket.")

    old_values = {"title": ticket.title, "description": ticket.description, "category_id": ticket.category_id}

    ticket.title = payload.title
    ticket.description = payload.description
    if payload.category_id is not None:
        ticket.category_id = payload.category_id

    new_values = {"title": ticket.title, "description": ticket.description, "category_id": ticket.category_id}

    log_audit(db, ticket.id, user.id, "ticket_updated", old_values, new_values)
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket_status(db: Session, ticket_id: int, payload: TicketStatusUpdate, user: User) -> Ticket:
    """
    PATCH /api/v1/tickets/{id}/status - Change ticket status according to state machine.
    - Employee: can only close own resolved ticket.
    - Technician: can change status on assigned tickets (e.g. assigned -> in_progress -> resolved).
    - Admin: can change status on any ticket.
    """
    ticket = get_ticket_by_id(db, ticket_id, user)

    # Permission check for status update
    if user.role == "employee":
        if ticket.requester_id != user.id:
            raise PermissionDeniedError("Employees can only close their own tickets.")
        if payload.status != "closed":
            raise PermissionDeniedError("Employees can only close their own tickets.")

    if user.role == "technician":
        if ticket.assigned_to != user.id:
            raise PermissionDeniedError("Technicians can only update tickets assigned to them.")

    # State machine transition check
    validate_status_transition(ticket.status, payload.status, user.role)

    old_values = {"status": ticket.status, "resolution_notes": ticket.resolution_notes}

    ticket.status = payload.status
    if payload.resolution_notes is not None:
        ticket.resolution_notes = payload.resolution_notes

    now = datetime.now(timezone.utc)
    if payload.status in ("resolved", "closed") and not ticket.resolved_at:
        ticket.resolved_at = now
    if payload.status == "closed" and not ticket.closed_at:
        ticket.closed_at = now
    if payload.status in ("open", "in_progress", "assigned") and ticket.status in ("resolved", "closed"):
        # Reopening
        ticket.resolved_at = None
        ticket.closed_at = None

    new_values = {"status": ticket.status, "resolution_notes": ticket.resolution_notes}

    log_audit(db, ticket.id, user.id, "status_changed", old_values, new_values)
    db.commit()
    db.refresh(ticket)

    # In-app Notification dispatch for status updates (Module 5)
    from app.services.notification_service import create_notification
    create_notification(
        db,
        user_id=ticket.requester_id,
        ticket_id=ticket.id,
        title="Ticket Status Updated",
        message=f"Ticket {ticket.ticket_number} status updated to {ticket.status.upper()}.",
        notification_type="status_change",
    )
    return ticket


def update_ticket_priority(db: Session, ticket_id: int, payload: TicketPriorityUpdate, user: User) -> Ticket:
    """
    PATCH /api/v1/tickets/{id}/priority - Admin-only priority modification.
    """
    if user.role != "admin":
        raise PermissionDeniedError("Only administrators can change ticket priority.")

    ticket = get_ticket_by_id(db, ticket_id, user)
    old_values = {"priority": ticket.priority}
    ticket.priority = payload.priority
    new_values = {"priority": ticket.priority}

    log_audit(db, ticket.id, user.id, "priority_changed", old_values, new_values)
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_ticket(db: Session, ticket_id: int, payload: TicketAssignUpdate, user: User) -> Ticket:
    """
    PATCH /api/v1/tickets/{id}/assign - Admin-only technician assignment / reassignment.
    """
    if user.role != "admin":
        raise PermissionDeniedError("Only administrators can assign or reassign technicians.")

    ticket = get_ticket_by_id(db, ticket_id, user)

    # Validate that assigned_to is actually a technician or admin
    if payload.assigned_to is not None:
        tech = db.get(User, payload.assigned_to)
        if not tech or tech.role not in ("technician", "admin") or not tech.is_active or tech.deleted_at is not None:
            raise PermissionDeniedError("Target assignee must be an active technician or administrator.")

    old_values = {"assigned_to": ticket.assigned_to, "status": ticket.status}
    ticket.assigned_to = payload.assigned_to

    # Automatically move from 'open' to 'assigned' if being assigned
    if payload.assigned_to is not None and ticket.status == "open":
        ticket.status = "assigned"
    # Move back to open if unassigned while in 'assigned'
    elif payload.assigned_to is None and ticket.status == "assigned":
        ticket.status = "open"

    new_values = {"assigned_to": ticket.assigned_to, "status": ticket.status}

    log_audit(db, ticket.id, user.id, "assignment_changed", old_values, new_values)
    db.commit()
    db.refresh(ticket)

    # In-app Notification dispatch (Module 1 & 5)
    from app.services.notification_service import create_notification
    if payload.assigned_to is not None:
        create_notification(
            db,
            user_id=payload.assigned_to,
            ticket_id=ticket.id,
            title="Ticket Assigned",
            message=f"You have been assigned to ticket {ticket.ticket_number}: {ticket.title}",
            notification_type="assignment",
        )
    # Also notify requester
    create_notification(
        db,
        user_id=ticket.requester_id,
        ticket_id=ticket.id,
        title="Technician Assigned",
        message=f"A technician has been assigned to your ticket {ticket.ticket_number}.",
        notification_type="assignment",
    )
    return ticket


def delete_or_archive_ticket(db: Session, ticket_id: int, user: User) -> None:
    """
    DELETE /api/v1/tickets/{id} - Admin-only deletion or archiving according to retention rules.
    Retention rules:
    - Active tickets ('open', 'assigned', 'in_progress', 'pending') cannot be deleted without archiving or closing first.
    - Only administrators can delete tickets.
    """
    if user.role != "admin":
        raise PermissionDeniedError("Only administrators can delete tickets.")

    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise ResourceNotFoundError("Ticket not found.")

    if ticket.status not in ("closed", "resolved"):
        raise PermissionDeniedError("Cannot delete an active ticket. Please close or resolve the ticket first.")

    db.delete(ticket)
    db.commit()


def get_ticket_history(db: Session, ticket_id: int, user: User) -> List[AuditLog]:
    """
    Retrieve audit history for a ticket.
    - Employee / Technician: only for accessible tickets.
    - Admin: all tickets.
    """
    ticket = get_ticket_by_id(db, ticket_id, user)
    return db.query(AuditLog).filter(AuditLog.ticket_id == ticket.id).order_by(AuditLog.created_at.desc()).all()
