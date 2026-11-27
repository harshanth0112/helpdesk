"""
app/routes/admin.py - Admin-only endpoints for user management, audit logs, and analytics.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken
from app.core.dependencies import require_role
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError
from app.schemas.auth import UserMeResponse
from app.schemas.ticket import (
    UserRoleUpdate,
    UserApproveRequest,
    UserRejectRequest,
    UserStatusUpdate,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    SoftDeleteRequest,
    PaginatedRecycleBinResponse,
    RestoreResponse,
)
from app.models.category import Category
from app.services import audit_service
from app.services import analytics_service
from app.services.email_service import dispatch_email
from app.services.soft_delete_service import (
    soft_delete_user,
    soft_delete_category,
    list_recycle_bin,
    restore_entity,
)

router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])


def _revoke_user_refresh_tokens(db: Session, user_id: int) -> None:
    """Revoke all active refresh tokens for a user upon suspension or rejection."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked.is_(False),
    ).update(
        {"is_revoked": True, "revoked_at": datetime.now(timezone.utc)},
        synchronize_session=False,
    )


def _count_active_admins(db: Session) -> int:
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


@router.get("/users/pending", response_model=List[UserMeResponse], dependencies=[Depends(require_role("admin"))])
def list_pending_users(db: Session = Depends(get_db)):
    """Admin-only: list all users awaiting approval."""
    return (
        db.query(User)
        .filter(User.approval_status == "pending", User.deleted_at.is_(None))
        .order_by(User.created_at.asc())
        .all()
    )


@router.get("/users", response_model=List[UserMeResponse], dependencies=[Depends(require_role("admin"))])
def list_users(
    approval_status: Optional[str] = Query(None, description="Optional filter by approval_status"),
    db: Session = Depends(get_db),
):
    """Admin-only: list all users with optional approval_status filter."""
    query = db.query(User).filter(User.deleted_at.is_(None))
    if approval_status:
        query = query.filter(User.approval_status == approval_status.lower())
    return query.order_by(User.id.asc()).all()


@router.patch("/users/{user_id}/approve", response_model=UserMeResponse)
def approve_user(
    user_id: int,
    payload: UserApproveRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: approve a pending/rejected registration and assign an initial role (employee or technician)."""
    user = db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise ResourceNotFoundError("User not found.")

    if user.approval_status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is already approved.",
        )

    old_values = {
        "approval_status": user.approval_status,
        "role": user.role,
        "is_active": user.is_active,
    }

    user.role = payload.role
    user.approval_status = "approved"
    user.is_active = True
    user.approved_by = current_admin.id
    user.approved_at = datetime.now(timezone.utc)
    user.rejection_reason = None
    db.commit()
    db.refresh(user)

    audit_service.record_audit_event(
        db=db,
        action="user_approval",
        actor_id=current_admin.id,
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values={
            "approval_status": user.approval_status,
            "role": user.role,
            "is_active": user.is_active,
            "approved_by": current_admin.id,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Email: notify user their account has been approved (fire-and-forget)
    background_tasks.add_task(
        dispatch_email,
        user.email,
        "account_approval",
        recipient_name=(f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]),
        template_data={"role": user.role},
    )
    return user


@router.patch("/users/{user_id}/reject", response_model=UserMeResponse)
def reject_user(
    user_id: int,
    payload: UserRejectRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: reject a pending user registration."""
    user = db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise ResourceNotFoundError("User not found.")

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an administrator account.",
        )

    old_values = {
        "approval_status": user.approval_status,
        "is_active": user.is_active,
    }

    user.approval_status = "rejected"
    user.is_active = False
    user.approved_by = current_admin.id
    user.approved_at = datetime.now(timezone.utc)
    user.rejection_reason = payload.rejection_reason.strip() if payload.rejection_reason else None
    _revoke_user_refresh_tokens(db, user.id)
    db.commit()
    db.refresh(user)

    audit_service.record_audit_event(
        db=db,
        action="user_rejection",
        actor_id=current_admin.id,
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values={
            "approval_status": user.approval_status,
            "is_active": user.is_active,
            "rejection_reason": user.rejection_reason,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Email: notify user their registration was not approved (fire-and-forget)
    background_tasks.add_task(
        dispatch_email,
        user.email,
        "account_rejection",
        recipient_name=(f"{user.first_name} {user.last_name}".strip() or user.email.split("@")[0]),
        template_data={"rejection_reason": user.rejection_reason or ""},
    )
    return user


@router.patch("/users/{user_id}/role", response_model=UserMeResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    request: Request,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: change a user's role and record an audit log event."""
    user = db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise ResourceNotFoundError("User not found.")

    if user.role == "admin" and payload.role != "admin":
        if _count_active_admins(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last active administrator.",
            )

    old_role = user.role
    user.role = payload.role
    db.commit()
    db.refresh(user)

    audit_service.record_audit_event(
        db=db,
        action="user_role_changed",
        actor_id=current_admin.id,
        entity_type="user",
        entity_id=user.id,
        old_values={"role": old_role},
        new_values={"role": user.role},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return user


@router.patch("/users/{user_id}/status", response_model=UserMeResponse)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    request: Request,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: suspend or reactivate a user account."""
    user = db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise ResourceNotFoundError("User not found.")

    old_values = {
        "approval_status": user.approval_status,
        "is_active": user.is_active,
    }

    if payload.action == "suspend":
        if user.role == "admin" and _count_active_admins(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot suspend the last active administrator.",
            )
        user.approval_status = "suspended"
        user.is_active = False
        _revoke_user_refresh_tokens(db, user.id)
        audit_action = "user_suspended"
    else:
        user.approval_status = "approved"
        user.is_active = True
        user.rejection_reason = None
        audit_action = "user_reactivated"

    db.commit()
    db.refresh(user)

    audit_service.record_audit_event(
        db=db,
        action=audit_action,
        actor_id=current_admin.id,
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values={
            "approval_status": user.approval_status,
            "is_active": user.is_active,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return user


@router.get("/audit-logs", dependencies=[Depends(require_role("admin"))])
def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    start_date: Optional[datetime] = Query(None, description="Start timestamp ISO-8601"),
    end_date: Optional[datetime] = Query(None, description="End timestamp ISO-8601"),
    db: Session = Depends(get_db),
):
    """
    Admin-only: view paginated audit logs with optional action, entity_type, and date range filters.
    """
    items, total, total_pages = audit_service.get_audit_logs_paginated(
        db=db,
        page=page,
        page_size=page_size,
        action=action,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "items": [
            {
                "id": log.id,
                "ticket_id": log.ticket_id,
                "actor_id": log.actor_id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "correlation_id": log.correlation_id,
                "created_at": log.created_at,
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/technicians/workload", dependencies=[Depends(require_role("admin"))])
def get_technicians_workload(db: Session = Depends(get_db)):
    """Module 1: Display technician workload and active ticket queues."""
    techs = db.query(User).filter(User.role.in_(["technician", "admin"]), User.deleted_at.is_(None)).all()
    workload = []
    for tech in techs:
        active_tickets = db.query(Ticket).filter(
            Ticket.assigned_to == tech.id,
            Ticket.deleted_at.is_(None),
            Ticket.status.in_(["assigned", "in_progress", "pending"])
        ).count()
        resolved_tickets = db.query(Ticket).filter(
            Ticket.assigned_to == tech.id,
            Ticket.deleted_at.is_(None),
            Ticket.status.in_(["resolved", "closed"])
        ).count()
        workload.append({
            "technician_id": tech.id,
            "name": f"{tech.first_name} {tech.last_name}",
            "email": tech.email,
            "role": tech.role,
            "active_tickets": active_tickets,
            "resolved_tickets": resolved_tickets,
        })
    return workload


@router.get("/analytics", dependencies=[Depends(require_role("admin"))])
def get_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """
    Admin-only: enterprise analytics with date range filtering.
    """
    return analytics_service.get_system_analytics(
        db=db,
        start_date=start_date,
        end_date=end_date,
        user_id=current_admin.id,
        role="admin",
    )


# ---------------------------------------------------------------------------
# Category Management Endpoints (Admin-only)
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=List[CategoryResponse], dependencies=[Depends(require_role("admin"))])
def list_categories(db: Session = Depends(get_db)):
    """Admin-only: list all support categories."""
    return db.query(Category).filter(Category.deleted_at.is_(None)).order_by(Category.id.asc()).all()


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role("admin"))])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    """Admin-only: create a new support category."""
    existing = db.query(Category).filter(
        Category.name.ilike(payload.name.strip()),
        Category.deleted_at.is_(None)
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category with this name already exists.")
    category = Category(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        is_active=payload.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryResponse, dependencies=[Depends(require_role("admin"))])
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    """Admin-only: update or activate/deactivate a category."""
    category = db.get(Category, category_id)
    if not category or category.deleted_at is not None:
        raise ResourceNotFoundError("Category not found.")
    if payload.name is not None:
        conflict = db.query(Category).filter(
            Category.name.ilike(payload.name.strip()),
            Category.id != category_id,
            Category.deleted_at.is_(None)
        ).first()
        if conflict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Another category has this name.")
        category.name = payload.name.strip()
    if payload.description is not None:
        category.description = payload.description.strip()
    if payload.is_active is not None:
        category.is_active = payload.is_active
    db.commit()
    db.refresh(category)
    return category


# ---------------------------------------------------------------------------
# Soft Delete & Recycle Bin Endpoints (Admin-only)
# ---------------------------------------------------------------------------

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    payload: Optional[SoftDeleteRequest] = None,
    request: Request = None,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: soft delete a user account with safeguards."""
    reason = payload.deletion_reason if payload else None
    ip_addr = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    try:
        soft_delete_user(
            db=db,
            user_id=user_id,
            actor=current_admin,
            reason=reason,
            ip_address=ip_addr,
            user_agent=user_agent,
        )
    except Exception:
        db.rollback()
        raise
    return None


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    payload: Optional[SoftDeleteRequest] = None,
    request: Request = None,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: soft delete a category (verifies no active tickets)."""
    reason = payload.deletion_reason if payload else None
    ip_addr = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    try:
        soft_delete_category(
            db=db,
            category_id=category_id,
            actor=current_admin,
            reason=reason,
            ip_address=ip_addr,
            user_agent=user_agent,
        )
    except Exception:
        db.rollback()
        raise
    return None


@router.get("/recycle-bin/{entity}", response_model=PaginatedRecycleBinResponse, dependencies=[Depends(require_role("admin"))])
def get_recycle_bin(
    entity: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    sort_by: str = Query("deleted_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
):
    """Admin-only: list soft-deleted records for a given entity."""
    return list_recycle_bin(
        db=db,
        entity=entity,
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/recycle-bin/{entity}/{record_id}/restore", response_model=RestoreResponse)
def restore_deleted_record(
    entity: str,
    record_id: int,
    request: Request = None,
    current_admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Admin-only: restore a soft-deleted record without altering activation/approval status."""
    ip_addr = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    return restore_entity(
        db=db,
        entity=entity,
        record_id=record_id,
        current_admin=current_admin,
        ip_address=ip_addr,
        user_agent=user_agent,
    )


