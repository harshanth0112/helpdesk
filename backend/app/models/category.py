from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Soft delete metadata — added Phase 15
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="category"
    )

    __table_args__ = (
        Index("idx_categories_name", "name"),
        Index("idx_categories_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}')>"
