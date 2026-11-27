from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Boolean, CheckConstraint, Index, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="employee", index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    # Approval workflow — added Phase 13
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Login security tracking — added Phase 4
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    requested_tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="requester",
        foreign_keys="Ticket.requester_id"
    )
    assigned_tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="assignee",
        foreign_keys="Ticket.assigned_to"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="user"
    )
    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="uploader"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="actor"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[List["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('employee', 'technician', 'admin')",
            name="chk_users_role"
        ),
        CheckConstraint(
            "approval_status IN ('pending', 'approved', 'rejected', 'suspended')",
            name="chk_users_approval_status"
        ),
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_department", "department"),
        Index("idx_users_is_active", "is_active"),
        Index("idx_users_approval_status", "approval_status"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
