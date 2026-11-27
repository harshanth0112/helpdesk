"""add user approval workflow columns

Revision ID: c2d4e6f8a0b1
Revises: 5b3ca0417704
Create Date: 2026-11-26 16:28:00.000000

Safe migration strategy:
1. Add approval_status with temporary server_default='approved' so existing rows
   receive 'approved'.
2. Backfill any existing records to 'approved'.
3. Set permanent server_default='pending' for new registrations.
4. Add approved_by (FK -> users.id), approved_at, rejection_reason, check
   constraint, and index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d4e6f8a0b1'
down_revision: Union[str, Sequence[str], None] = '5b3ca0417704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add approval_status with temporary server_default='approved'
    op.add_column(
        'users',
        sa.Column(
            'approval_status',
            sa.String(length=20),
            nullable=False,
            server_default='approved',
        ),
    )

    # 2. Explicit backfill for existing records
    op.execute(
        "UPDATE users SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = ''"
    )

    # 3. Set permanent default='pending' & add remaining columns/constraints (batch-safe for SQLite & PostgreSQL)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'approval_status',
            existing_type=sa.String(length=20),
            nullable=False,
            server_default='pending',
        )
        batch_op.add_column(sa.Column('approved_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('rejection_reason', sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            'fk_users_approved_by_users',
            'users',
            ['approved_by'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_check_constraint(
            'chk_users_approval_status',
            "approval_status IN ('pending', 'approved', 'rejected', 'suspended')",
        )
        batch_op.create_index('idx_users_approval_status', ['approval_status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('idx_users_approval_status')
        batch_op.drop_constraint('chk_users_approval_status', type_='check')
        batch_op.drop_constraint('fk_users_approved_by_users', type_='foreignkey')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('approved_at')
        batch_op.drop_column('approved_by')
        batch_op.drop_column('approval_status')
