"""add soft delete columns to users, tickets, comments, attachments, categories

Revision ID: d4e5f6a7b8c9
Revises: c2d4e6f8a0b1
Create Date: 2026-11-27 14:02:00.000000

Adds nullable soft-delete metadata columns (deleted_at, deleted_by, deletion_reason)
and indexes on deleted_at for all 5 recoverable entities.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c2d4e6f8a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ('users', 'tickets', 'comments', 'attachments', 'categories')


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
            batch_op.add_column(sa.Column('deleted_by', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('deletion_reason', sa.Text(), nullable=True))
            batch_op.create_foreign_key(
                f'fk_{table}_deleted_by_users',
                'users',
                ['deleted_by'],
                ['id'],
                ondelete='SET NULL',
            )
            batch_op.create_index(f'idx_{table}_deleted_at', ['deleted_at'], unique=False)


def downgrade() -> None:
    for table in reversed(TABLES):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_index(f'idx_{table}_deleted_at')
            batch_op.drop_constraint(f'fk_{table}_deleted_by_users', type_='foreignkey')
            batch_op.drop_column('deletion_reason')
            batch_op.drop_column('deleted_by')
            batch_op.drop_column('deleted_at')
