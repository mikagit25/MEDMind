"""add_user_push_token

Revision ID: afb63dd2fe0d
Revises: 0034
Create Date: 2026-06-12 16:06:14.802510

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'afb63dd2fe0d'
down_revision: Union[str, None] = '0034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('push_token', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'push_token')
