"""add health profiles and metrics

Revision ID: d195a0dac7ff
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24 16:23:45.125243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd195a0dac7ff'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'health_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('metric', sa.String(length=50), nullable=False),
        sa.Column('value', sa.String(length=50), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_health_metrics_recorded_at', 'health_metrics', ['recorded_at'], unique=False)
    op.create_index('ix_health_metrics_user_id', 'health_metrics', ['user_id'], unique=False)
    op.create_index('ix_health_metrics_user_metric', 'health_metrics', ['user_id', 'metric'], unique=False)

    op.create_table(
        'health_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('birth_year', sa.Integer(), nullable=True),
        sa.Column('sex', sa.String(length=10), nullable=True),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('medications', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('allergies', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('health_log', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('checkin_log', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('trackers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('telegram_chat_id', sa.String(length=50), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_health_profiles_telegram_chat_id', 'health_profiles', ['telegram_chat_id'], unique=False)
    op.create_index('ix_health_profiles_user_id', 'health_profiles', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_health_profiles_user_id', table_name='health_profiles')
    op.drop_index('ix_health_profiles_telegram_chat_id', table_name='health_profiles')
    op.drop_table('health_profiles')
    op.drop_index('ix_health_metrics_user_metric', table_name='health_metrics')
    op.drop_index('ix_health_metrics_user_id', table_name='health_metrics')
    op.drop_index('ix_health_metrics_recorded_at', table_name='health_metrics')
    op.drop_table('health_metrics')
