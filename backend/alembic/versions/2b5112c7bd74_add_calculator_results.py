"""add_calculator_results

Revision ID: 2b5112c7bd74
Revises: afb63dd2fe0d
Create Date: 2026-06-12 16:14:12.935549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '2b5112c7bd74'
down_revision: Union[str, None] = 'afb63dd2fe0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'calculator_results',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('inputs', postgresql.JSONB(), nullable=False),
        sa.Column('score', sa.String(50), nullable=True),
        sa.Column('risk_level', sa.String(50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_calc_results_user_id',    'calculator_results', ['user_id'])
    op.create_index('ix_calc_results_user_slug',  'calculator_results', ['user_id', 'slug'])
    op.create_index('ix_calc_results_created_at', 'calculator_results', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_calc_results_created_at', table_name='calculator_results')
    op.drop_index('ix_calc_results_user_slug',  table_name='calculator_results')
    op.drop_index('ix_calc_results_user_id',    table_name='calculator_results')
    op.drop_table('calculator_results')
