from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", index=True)

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True
    )
    requester_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True
    )
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True
    )

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Soft delete metadata — added Phase 15
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="tickets"
    )
    requester: Mapped["User"] = relationship(
        "User",
        back_populates="requested_tickets",
        foreign_keys=[requester_id]
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_tickets",
        foreign_keys=[assigned_to]
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Comment.created_at.asc()"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="ticket",
        cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="AuditLog.created_at.asc()"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'assigned', 'in_progress', 'pending', 'resolved', 'closed')",
            name="chk_tickets_status"
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="chk_tickets_priority"
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= created_at",
            name="chk_tickets_resolution_order"
        ),
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= created_at",
            name="chk_tickets_closed_order"
        ),
        Index("idx_tickets_ticket_number", "ticket_number"),
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_priority", "priority"),
        Index("idx_tickets_requester", "requester_id"),
        Index("idx_tickets_assigned_to", "assigned_to"),
        Index("idx_tickets_category", "category_id"),
        Index("idx_tickets_created_at", "created_at"),
        Index("idx_tickets_composite_queue", "status", "priority", "assigned_to"),
    )

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, ticket_number='{self.ticket_number}', status='{self.status}')>"
