"""
app/services/audit_service.py - Production-Oriented Enterprise Audit Logging Service.

Ensures:
- Comprehensive logging of authentication events, user admin actions, ticket lifecycle, and security events.
- Never logs plaintext passwords, raw tokens, hashes, or secrets.
- Records actor_id, action, entity_type, entity_id, old_values, new_values, timestamps, and correlation_ids.
- Supports paginated querying and date range filtering strictly for administrators.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit_log import AuditLog

# Sensitive fields to sanitize aggressively before writing to audit records
SENSITIVE_FIELD_NAMES = {
    "password",
    "password_hash",
    "token",
    "token_hash",
    "refresh_token",
    "reset_token",
    "access_token",
    "secret",
    "jwt_secret",
}


def sanitize_payload(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Recursively redact any sensitive credentials from audit entries."""
    if not payload:
        return None
    cleaned = {}
    for key, value in payload.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELD_NAMES):
            cleaned[key] = "[REDACTED]"
        elif isinstance(value, dict):
            cleaned[key] = sanitize_payload(value)
        else:
            cleaned[key] = value
    return cleaned


def record_audit_event(
    db: Session,
    action: str,
    actor_id: Optional[int],
    entity_type: str = "ticket",
    entity_id: Optional[int] = None,
    ticket_id: Optional[int] = None,
    old_values: Optional[Dict[str, Any]] = None,
    new_values: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> AuditLog:
    """Write an immutable audit log entry to the database."""
    # Ensure ticket_id is set if entity is ticket
    if entity_type == "ticket" and not ticket_id and entity_id:
        ticket_id = entity_id

    audit = AuditLog(
        action=action,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        ticket_id=ticket_id,
        old_values=sanitize_payload(old_values),
        new_values=sanitize_payload(new_values),
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


def get_audit_logs_paginated(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Tuple[List[AuditLog], int, int]:
    """Retrieve filtered, paginated audit logs for administrators."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    total = query.count()
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    items = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return items, total, total_pages
