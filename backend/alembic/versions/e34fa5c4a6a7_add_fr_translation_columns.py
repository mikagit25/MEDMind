"""add_fr_translation_columns

Revision ID: e34fa5c4a6a7
Revises: d4e5f6a7b8c9
Create Date: 2026-09-15 18:47:26.242499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'e34fa5c4a6a7'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mcq_questions', sa.Column('explanation_fr', sa.Text(), nullable=True))
    op.add_column('mcq_questions', sa.Column('rationales_fr', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('mcq_questions', sa.Column('key_takeaway_fr', sa.Text(), nullable=True))
    op.add_column('mcq_questions', sa.Column('test_taking_tip_fr', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('mcq_questions', 'test_taking_tip_fr')
    op.drop_column('mcq_questions', 'key_takeaway_fr')
    op.drop_column('mcq_questions', 'rationales_fr')
    op.drop_column('mcq_questions', 'explanation_fr')
