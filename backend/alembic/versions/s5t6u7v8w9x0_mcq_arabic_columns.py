"""Add Arabic rationale columns to mcq_questions for Gulf exam Arabic layer.

Revision ID: s5t6u7v8w9x0
Revises: r4s5t6u7v8w9
Create Date: 2026-07-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "s5t6u7v8w9x0"
down_revision = "r4s5t6u7v8w9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mcq_questions", sa.Column("explanation_ar", sa.Text(), nullable=True))
    op.add_column("mcq_questions", sa.Column("rationales_ar", JSONB(), nullable=True))
    op.add_column("mcq_questions", sa.Column("key_takeaway_ar", sa.Text(), nullable=True))
    op.add_column("mcq_questions", sa.Column("test_taking_tip_ar", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("mcq_questions", "test_taking_tip_ar")
    op.drop_column("mcq_questions", "key_takeaway_ar")
    op.drop_column("mcq_questions", "rationales_ar")
    op.drop_column("mcq_questions", "explanation_ar")
