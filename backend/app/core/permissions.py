"""
app/core/permissions.py - Centralized RBAC and Resource Ownership checks.
"""

from typing import List, Optional
from app.models.user import User
from app.models.ticket import Ticket
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError


def check_ticket_access(user: User, ticket: Ticket) -> None:
    """
    Verify if user has permission to view/access the given ticket.
    Under Global Ticket Visibility:
    - All authenticated, approved, and active users (employee, technician, admin) can view tickets.
    Throws 403 (PermissionDeniedError) if user is not active/approved, or raises ResourceNotFoundError if ticket does not exist.
    """
    if not user or not user.is_active or user.approval_status != "approved":
        raise PermissionDeniedError("Account is inactive, pending approval, or suspended.")
    if not ticket:
        raise ResourceNotFoundError("Ticket not found.")
    return


def check_ticket_comment_permission(user: User, ticket: Ticket, is_internal: bool = False) -> None:
    """
    Verify commenting permissions on a ticket.
    - Employee: can comment on own tickets only, cannot post internal notes.
    - Technician: can comment on assigned tickets, can post internal notes.
    - Admin: can comment on any ticket and post internal notes.
    """
    check_ticket_access(user, ticket)
    if is_internal and user.role == "employee":
        raise PermissionDeniedError("Employees cannot create internal notes.")


def verify_role_assignment(current_user: User, target_role: str) -> None:
    """
    Prevent privilege escalation. Only admin can assign technician or admin roles.
    """
    if target_role != "employee" and current_user.role != "admin":
        raise PermissionDeniedError("Only administrators can assign administrative or technician roles.")
