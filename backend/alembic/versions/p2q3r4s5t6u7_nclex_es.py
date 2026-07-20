"""G2 — Spanish rationale columns on mcq_questions

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-07-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "p2q3r4s5t6u7"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mcq_questions", sa.Column("explanation_es",   sa.Text(), nullable=True))
    op.add_column("mcq_questions", sa.Column("rationales_es",    postgresql.JSONB(), nullable=True))
    op.add_column("mcq_questions", sa.Column("key_takeaway_es",  sa.Text(), nullable=True))
    op.add_column("mcq_questions", sa.Column("test_taking_tip_es", sa.Text(), nullable=True))


def downgrade() -> None:
    for col in ("explanation_es", "rationales_es", "key_takeaway_es", "test_taking_tip_es"):
        op.drop_column("mcq_questions", col)
