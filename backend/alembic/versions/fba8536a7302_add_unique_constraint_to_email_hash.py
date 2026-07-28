"""add unique constraint to email_hash

Revision ID: fba8536a7302
Revises: s5t6u7v8w9x0
Create Date: 2026-07-28 05:38:08.594553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'fba8536a7302'
down_revision: Union[str, None] = 's5t6u7v8w9x0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old non-unique index and replace with a partial unique index.
    # Duplicates were cleaned up manually before this migration.
    op.drop_index('idx_users_email_hash', table_name='users')
    op.create_index(
        'idx_users_email_hash',
        'users',
        ['email_hash'],
        unique=True,
        postgresql_where=sa.text('email_hash IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_users_email_hash', table_name='users')
    op.create_index('idx_users_email_hash', 'users', ['email_hash'], unique=False)
