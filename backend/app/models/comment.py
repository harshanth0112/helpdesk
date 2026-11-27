from datetime import datetime
from typing import Optional
from sqlalchemy import Text, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Comment(Base, TimestampMixin):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tickets.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
        index=True
    )
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Soft delete metadata — added Phase 15
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="comments")
    user: Mapped["User"] = relationship(
        "User",
        back_populates="comments",
        foreign_keys=[user_id]
    )

    __table_args__ = (
        CheckConstraint("LENGTH(TRIM(comment_text)) > 0", name="chk_comments_non_empty"),
        Index("idx_comments_ticket_id", "ticket_id"),
        Index("idx_comments_user_id", "user_id"),
        Index("idx_comments_created_at", "ticket_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, ticket_id={self.ticket_id}, user_id={self.user_id})>"
