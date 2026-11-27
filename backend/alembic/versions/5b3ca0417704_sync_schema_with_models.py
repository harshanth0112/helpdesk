"""sync schema with models

Revision ID: 5b3ca0417704
Revises: a1b2c3d4e5f6
Create Date: 2026-11-26 14:23:29.339784

The initial Alembic migration drifted from the SQLAlchemy models.  This
revision brings the database in line with the models that the application
actually queries:

* ``notifications`` table was never created.
* ``audit_logs`` was missing ``entity_type`` / ``entity_id`` /
  ``correlation_id`` and incorrectly required ``ticket_id`` (auth events are
  not tied to a ticket).
* ``tickets`` was missing ``resolution_notes``.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5b3ca0417704"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. notifications — in-app notifications created on ticket events
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_notifications_created_at", "notifications", ["created_at"], unique=False
    )
    op.create_index(
        "idx_notifications_is_read", "notifications", ["is_read"], unique=False
    )
    op.create_index(
        "idx_notifications_user_id", "notifications", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_notifications_ticket_id"), "notifications", ["ticket_id"], unique=False
    )

    # 2. audit_logs — generic entity auditing (not just tickets)
    op.add_column(
        "audit_logs", sa.Column("entity_type", sa.String(length=50), nullable=True)
    )
    op.execute("UPDATE audit_logs SET entity_type = 'ticket' WHERE entity_type IS NULL")
    op.alter_column("audit_logs", "entity_type", nullable=False)
    op.add_column("audit_logs", sa.Column("entity_id", sa.Integer(), nullable=True))
    op.add_column(
        "audit_logs", sa.Column("correlation_id", sa.String(length=64), nullable=True)
    )
    op.alter_column("audit_logs", "ticket_id", existing_type=sa.INTEGER(), nullable=True)
    op.create_index(
        "idx_audit_entity", "audit_logs", ["entity_type", "entity_id"], unique=False
    )

    # 3. tickets — resolution notes captured when resolving
    op.add_column("tickets", sa.Column("resolution_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "resolution_notes")
    op.drop_index("idx_audit_entity", table_name="audit_logs")
    op.alter_column("audit_logs", "ticket_id", existing_type=sa.INTEGER(), nullable=False)
    op.drop_column("audit_logs", "correlation_id")
    op.drop_column("audit_logs", "entity_id")
    op.drop_column("audit_logs", "entity_type")
    op.drop_index(op.f("ix_notifications_ticket_id"), table_name="notifications")
    op.drop_index("idx_notifications_user_id", table_name="notifications")
    op.drop_index("idx_notifications_is_read", table_name="notifications")
    op.drop_index("idx_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
