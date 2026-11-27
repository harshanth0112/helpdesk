"""add_login_tracking_to_users

Revision ID: a1b2c3d4e5f6
Revises: 58ef887e8c67
Create Date: 2026-11-26

Adds two columns to the ``users`` table to support brute-force lockout:

- ``failed_login_attempts`` (INTEGER, NOT NULL, DEFAULT 0):
  Incremented on each failed login; reset to 0 on success.

- ``locked_until`` (TIMESTAMP WITH TIME ZONE, NULLABLE):
  When set and in the future, the account refuses login attempts.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "58ef887e8c67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
