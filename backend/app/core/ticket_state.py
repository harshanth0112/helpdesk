"""
app/core/ticket_state.py - Ticket state machine and transition rules.

Valid statuses:
  - open
  - assigned
  - in_progress
  - pending
  - resolved
  - closed

State Transition Rules:
  - open -> assigned, closed
  - assigned -> in_progress, open (unassign), pending, closed
  - in_progress -> pending, resolved, closed
  - pending -> in_progress, resolved, closed
  - resolved -> closed, in_progress (reopen)
  - closed -> in_progress (reopen by Admin only)
"""

from typing import Dict, Set
from fastapi import HTTPException, status

VALID_STATUSES = {"open", "assigned", "in_progress", "pending", "resolved", "closed"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}

ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "open": {"assigned", "closed", "in_progress"},
    "assigned": {"in_progress", "open", "pending", "closed"},
    "in_progress": {"pending", "resolved", "closed"},
    "pending": {"in_progress", "resolved", "closed"},
    "resolved": {"closed", "in_progress"},
    "closed": {"in_progress", "open"},
}


def validate_status_transition(current_status: str, new_status: str, user_role: str) -> None:
    """
    Validate that transitioning from current_status to new_status is valid.
    Only admin can reopen closed tickets.
    """
    if new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Allowed values: {', '.join(sorted(VALID_STATUSES))}",
        )

    if current_status == new_status:
        return

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition ticket from '{current_status}' to '{new_status}'.",
        )

    # Restriction: only Admin can reopen closed tickets
    if current_status == "closed" and user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can reopen closed tickets.",
        )
