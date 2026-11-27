"""
app/routes/tickets.py - Comprehensive Secure Ticket CRUD and Workflow APIs.
"""

from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.attachment import Attachment
from app.models.category import Category
from app.core.dependencies import get_current_user, require_role
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError
from app.core.permissions import check_ticket_comment_permission, check_ticket_access
from app.services import ticket_service, attachment_service, notification_service
from app.services.email_service import dispatch_email
from app.services import soft_delete_service
from app.schemas.ticket import (
    TicketCreate,
    TicketResponse,
    TicketPutUpdate,
    TicketStatusUpdate,
    TicketPriorityUpdate,
    TicketAssignUpdate,
    PaginatedTicketResponse,
    TicketHistoryResponse,
    CommentCreate,
    CommentResponse,
    AttachmentResponse,
    CategoryResponse,
    SoftDeleteRequest,
)

router = APIRouter(prefix="/api/v1/tickets", tags=["Tickets"])


@router.get("/stats/dashboard")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregated dashboard KPIs and state distributions from PostgreSQL/SQLAlchemy.
    Scoped securely by role:
    - Employee: queries scoped to requester_id == user.id
    - Technician: queries scoped to assigned_to == user.id
    - Admin: queries across all tickets in database
    """
    query = db.query(Ticket).filter(Ticket.deleted_at.is_(None))
    if current_user.role == "employee":
        query = query.filter(Ticket.requester_id == current_user.id)
    elif current_user.role == "technician":
        query = query.filter(Ticket.assigned_to == current_user.id)

    total = query.count()
    open_count = query.filter(Ticket.status.in_(["open", "assigned"])).count()
    in_progress_count = query.filter(Ticket.status.in_(["in_progress", "pending"])).count()
    resolved_count = query.filter(Ticket.status.in_(["resolved", "closed"])).count()

    # Priorities breakdown
    low_prio = query.filter(Ticket.priority == "low").count()
    medium_prio = query.filter(Ticket.priority == "medium").count()
    high_prio = query.filter(Ticket.priority == "high").count()
    critical_prio = query.filter(Ticket.priority == "critical").count()

    pending_users = 0
    if current_user.role == "admin":
        pending_users = db.query(User).filter(User.approval_status == "pending", User.deleted_at.is_(None)).count()

    return {
        "total": total,
        "open": open_count,
        "in_progress": in_progress_count,
        "resolved": resolved_count,
        "pending_users": pending_users,
        "priorities": {
            "low": low_prio,
            "medium": medium_prio,
            "high": high_prio,
            "critical": critical_prio,
        },
    }


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new ticket."""
    return ticket_service.create_ticket(db, payload, current_user)


@router.get("", response_model=PaginatedTicketResponse)
def list_tickets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title or description"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned technician"),
    requester_id: Optional[int] = Query(None, description="Filter by requester ID"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, updated_at, priority, status, title)"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List tickets with server-side pagination, search, filtering, and sorting.
    Global visibility: all active/approved users can view all tickets.
    """
    items, total, total_pages = ticket_service.list_tickets_paginated(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status,
        priority_filter=priority,
        category_id=category_id,
        assigned_to=assigned_to,
        requester_id=requester_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedTicketResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single ticket by ID. Enforces ownership / anti-IDOR."""
    return ticket_service.get_ticket_by_id(db, ticket_id, current_user)


@router.put("/{ticket_id}", response_model=TicketResponse)
def put_update_ticket(
    ticket_id: int,
    payload: TicketPutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full update of ticket title and description."""
    return ticket_service.put_update_ticket(db, ticket_id, payload, current_user)


@router.patch("/{ticket_id}", response_model=TicketResponse)
def patch_ticket_general(
    ticket_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Backwards-compatible PATCH /api/v1/tickets/{id} for general ticket modifications:
    - If 'assigned_to' provided -> routes through assign_ticket
    - If 'status' provided -> routes through update_ticket_status
    - If 'priority' provided -> routes through update_ticket_priority
    - If 'title'/'description' provided -> routes through put_update_ticket
    """
    # 1. Ownership & existence check must always happen first to guarantee 404 on IDOR
    ticket = ticket_service.get_ticket_by_id(db, ticket_id, current_user)

    if "assigned_to" in payload:
        ticket = ticket_service.assign_ticket(
            db, ticket_id, TicketAssignUpdate(assigned_to=payload["assigned_to"]), current_user
        )
        if "status" in payload:
            ticket = ticket_service.update_ticket_status(
                db, ticket_id, TicketStatusUpdate(status=payload["status"]), current_user
            )
        return ticket
    if "status" in payload:
        if current_user.role == "technician" and "priority" in payload:
            raise PermissionDeniedError("Technicians cannot change priority.")
        return ticket_service.update_ticket_status(
            db, ticket_id, TicketStatusUpdate(status=payload["status"], resolution_notes=payload.get("resolution_notes")), current_user
        )
    if "priority" in payload:
        return ticket_service.update_ticket_priority(
            db, ticket_id, TicketPriorityUpdate(priority=payload["priority"]), current_user
        )
    # Title / description update
    new_title = payload.get("title", ticket.title)
    new_desc = payload.get("description", ticket.description)
    return ticket_service.put_update_ticket(
        db, ticket_id, TicketPutUpdate(title=new_title, description=new_desc), current_user
    )


@router.get("/categories", response_model=List[CategoryResponse])
def list_active_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticated endpoint: list all active, non-deleted categories for ticket creation/filtering."""
    return (
        db.query(Category)
        .filter(Category.is_active.is_(True), Category.deleted_at.is_(None))
        .order_by(Category.name.asc())
        .all()
    )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    payload: Optional[SoftDeleteRequest] = None,
    request: Request = None,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Soft delete a ticket (Admin-only, closed/resolved tickets)."""
    reason = payload.deletion_reason if payload else None
    ip_addr = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    soft_delete_service.soft_delete_ticket(
        db=db,
        ticket_id=ticket_id,
        actor=current_admin,
        reason=reason,
        ip_address=ip_addr,
        user_agent=user_agent,
    )
    return None


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
def patch_status(
    ticket_id: int,
    payload: TicketStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update ticket status with state machine transitions."""
    ticket = ticket_service.update_ticket_status(db, ticket_id, payload, current_user)
    # Email: notify requester of status change (fire-and-forget)
    requester = db.get(User, ticket.requester_id)
    if requester:
        background_tasks.add_task(
            dispatch_email,
            requester.email,
            "ticket_status_update",
            recipient_name=(f"{requester.first_name} {requester.last_name}".strip() or requester.email.split("@")[0]),
            template_data={
                "ticket_id": ticket.ticket_number,
                "ticket_title": ticket.title,
                "new_status": ticket.status,
            },
        )
    return ticket


@router.patch("/{ticket_id}/priority", response_model=TicketResponse)
def patch_priority(
    ticket_id: int,
    payload: TicketPriorityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update ticket priority (Admin-only)."""
    return ticket_service.update_ticket_priority(db, ticket_id, payload, current_user)


@router.patch("/{ticket_id}/assign", response_model=TicketResponse)
def patch_assign(
    ticket_id: int,
    payload: TicketAssignUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign or reassign ticket to a technician (Admin-only)."""
    ticket = ticket_service.assign_ticket(db, ticket_id, payload, current_user)
    # Email: notify assigned technician (fire-and-forget)
    if payload.assigned_to is not None:
        technician = db.get(User, payload.assigned_to)
        if technician:
            background_tasks.add_task(
                dispatch_email,
                technician.email,
                "ticket_assignment",
                recipient_name=(f"{technician.first_name} {technician.last_name}".strip() or technician.email.split("@")[0]),
                template_data={
                    "ticket_id": ticket.ticket_number,
                    "ticket_title": ticket.title,
                    "ticket_priority": ticket.priority,
                },
            )
    return ticket


@router.get("/{ticket_id}/history", response_model=List[TicketHistoryResponse])
def get_ticket_history(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve ticket audit trail / history."""
    return ticket_service.get_ticket_history(db, ticket_id, current_user)


# ---------------------------------------------------------------------------
# Comments endpoints
# ---------------------------------------------------------------------------

@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a comment to an accessible ticket."""
    ticket = ticket_service.get_ticket_by_id(db, ticket_id, current_user)
    check_ticket_comment_permission(current_user, ticket, is_internal=payload.is_internal)

    comment = Comment(
        ticket_id=ticket.id,
        user_id=current_user.id,
        comment_text=payload.comment_text,
        is_internal=payload.is_internal,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{ticket_id}/comments", response_model=List[CommentResponse])
def get_comments(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List comments for a ticket."""
    ticket = ticket_service.get_ticket_by_id(db, ticket_id, current_user)

    query = db.query(Comment).filter(
        Comment.ticket_id == ticket.id,
        Comment.deleted_at.is_(None),
    )
    if current_user.role == "employee":
        query = query.filter(Comment.is_internal.is_(False))

    return query.order_by(Comment.created_at.asc()).all()


@router.delete("/{ticket_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    ticket_id: int,
    comment_id: int,
    payload: Optional[SoftDeleteRequest] = None,
    request: Request = None,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: soft delete a comment."""
    reason = payload.deletion_reason if payload else None
    ip_addr = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    soft_delete_service.soft_delete_comment(
        db=db,
        ticket_id=ticket_id,
        comment_id=comment_id,
        actor=current_admin,
        reason=reason,
        ip_address=ip_addr,
        user_agent=user_agent,
    )
    return None

# ---------------------------------------------------------------------------
# Attachments endpoints (Module 3)
# ---------------------------------------------------------------------------

@router.post("/{ticket_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Secure attachment upload with MIME and extension allowlist verification."""
    attachment = await attachment_service.save_attachment(db, ticket_id, file, current_user)
    return {
        "id": attachment.id,
        "ticket_id": attachment.ticket_id,
        "file_name": attachment.file_name,
        "file_size_bytes": attachment.file_size_bytes,
        "mime_type": attachment.mime_type,
        "created_at": attachment.created_at,
    }


@router.get("/{ticket_id}/attachments", response_model=List[AttachmentResponse])
def list_attachments(
    ticket_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active attachments for a ticket."""
    ticket = ticket_service.get_ticket_by_id(db, ticket_id, current_user)
    return (
        db.query(Attachment)
        .filter(Attachment.ticket_id == ticket.id, Attachment.deleted_at.is_(None))
        .order_by(Attachment.created_at.asc())
        .all()
    )


@router.delete("/{ticket_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    ticket_id: int,
    attachment_id: int,
    payload: Optional[SoftDeleteRequest] = None,
    request: Request = None,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: soft delete an attachment (preserves file on disk)."""
    reason = payload.deletion_reason if payload else None
    ip_addr = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    soft_delete_service.soft_delete_attachment(
        db=db,
        attachment_id=attachment_id,
        actor=current_admin,
        ticket_id=ticket_id,
        reason=reason,
        ip_address=ip_addr,
        user_agent=user_agent,
    )
    return None


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Secure file download with path traversal prevention and ticket authorization."""
    attachment, file_path = attachment_service.get_attachment_for_download(db, attachment_id, current_user)
    return FileResponse(
        path=str(file_path),
        filename=attachment.file_name,
        media_type=attachment.mime_type,
    )


# ---------------------------------------------------------------------------
# Notifications endpoints (Module 5)
# ---------------------------------------------------------------------------

@router.get("/user/notifications")
def get_my_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get in-app notifications for the authenticated user."""
    notifs = notification_service.get_user_notifications(db, current_user.id, unread_only=unread_only)
    return [
        {
            "id": n.id,
            "ticket_id": n.ticket_id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifs
    ]


@router.patch("/user/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    notif = notification_service.mark_notification_as_read(db, notification_id, current_user.id)
    if not notif:
        raise ResourceNotFoundError("Notification not found.")
    return {"status": "success", "is_read": True}
