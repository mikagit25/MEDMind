"""add telegram_chat_id to users

Revision ID: a1b2c3d4e5f6
Revises: 0b223012c605
Create Date: 2026-06-22 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '0b223012c605'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('telegram_chat_id', sa.String(50), nullable=True))
    op.create_index('ix_users_telegram_chat_id', 'users', ['telegram_chat_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_telegram_chat_id', table_name='users')
    op.drop_column('users', 'telegram_chat_id')
