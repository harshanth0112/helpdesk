"""
app/services/analytics_service.py - Advanced Database Analytics & Performance Aggregation.

Features:
- Total, open, in-progress, resolved, and critical ticket counts.
- Average resolution time calculation.
- Breakdown of tickets by category and priority.
- Historical ticket creation trends over time.
- Technician workload distribution.
- Date range filtering.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.ticket import Ticket
from app.models.category import Category
from app.models.user import User


def get_system_analytics(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[int] = None,
    role: str = "admin",
) -> Dict[str, Any]:
    """
    Role-specific and date-bounded analytics aggregation directly in PostgreSQL.
    """
    query = db.query(Ticket).filter(Ticket.deleted_at.is_(None))

    # Scoping for non-admins
    if role == "employee" and user_id:
        query = query.filter(Ticket.requester_id == user_id)
    elif role == "technician" and user_id:
        query = query.filter(Ticket.assigned_to == user_id)

    # Date range filters
    if start_date:
        query = query.filter(Ticket.created_at >= start_date)
    if end_date:
        query = query.filter(Ticket.created_at <= end_date)

    total_tickets = query.count()
    open_tickets = query.filter(Ticket.status.in_(["open", "assigned"])).count()
    in_progress = query.filter(Ticket.status.in_(["in_progress", "pending"])).count()
    resolved = query.filter(Ticket.status.in_(["resolved", "closed"])).count()
    critical = query.filter(Ticket.priority == "critical").count()

    # Priority distribution
    priorities = {
        "low": query.filter(Ticket.priority == "low").count(),
        "medium": query.filter(Ticket.priority == "medium").count(),
        "high": query.filter(Ticket.priority == "high").count(),
        "critical": critical,
    }

    # Category breakdown
    categories_raw = (
        db.query(Category.name, func.count(Ticket.id))
        .join(Ticket, Ticket.category_id == Category.id)
        .filter(Ticket.deleted_at.is_(None), Category.deleted_at.is_(None))
        .group_by(Category.name)
        .all()
    )
    categories = [{"name": name, "count": count} for name, count in categories_raw]

    # Average resolution time in hours
    resolved_tickets = query.filter(Ticket.resolved_at.isnot(None)).all()
    total_hours = 0.0
    count_resolved = len(resolved_tickets)
    for t in resolved_tickets:
        if t.resolved_at and t.created_at:
            delta = t.resolved_at - t.created_at
            total_hours += max(0.0, delta.total_seconds() / 3600.0)

    avg_resolution_hours = round(total_hours / count_resolved, 2) if count_resolved > 0 else 0.0

    # Technician workload summary (for admin and technician views)
    tech_workload = []
    if role in ("admin", "technician"):
        techs = db.query(User).filter(User.role.in_(["technician", "admin"]), User.deleted_at.is_(None)).all()
        for tech in techs:
            active = db.query(Ticket).filter(
                Ticket.assigned_to == tech.id,
                Ticket.deleted_at.is_(None),
                Ticket.status.in_(["assigned", "in_progress", "pending"])
            ).count()
            tech_workload.append({
                "technician_id": tech.id,
                "name": f"{tech.first_name} {tech.last_name}",
                "active_tickets": active,
            })

    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "in_progress_tickets": in_progress,
        "resolved_tickets": resolved,
        "critical_tickets": critical,
        "avg_resolution_hours": avg_resolution_hours,
        "priorities": priorities,
        "categories": categories,
        "technician_workload": tech_workload,
    }
