"""add rationales, key_takeaway, test_taking_tip, is_flagged, flag_reason to mcq_questions

Revision ID: k7l8m9n0o1p2
Revises: j6k7l8m9n0o1
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "k7l8m9n0o1p2"
down_revision = "j6k7l8m9n0o1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mcq_questions", sa.Column("rationales", JSONB, nullable=True))
    op.add_column("mcq_questions", sa.Column("key_takeaway", sa.Text, nullable=True))
    op.add_column("mcq_questions", sa.Column("test_taking_tip", sa.Text, nullable=True))
    op.add_column("mcq_questions", sa.Column("is_flagged", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("mcq_questions", sa.Column("flag_reason", sa.Text, nullable=True))
    op.create_index("ix_mcq_questions_is_flagged", "mcq_questions", ["is_flagged"])


def downgrade():
    op.drop_index("ix_mcq_questions_is_flagged", table_name="mcq_questions")
    op.drop_column("mcq_questions", "flag_reason")
    op.drop_column("mcq_questions", "is_flagged")
    op.drop_column("mcq_questions", "test_taking_tip")
    op.drop_column("mcq_questions", "key_takeaway")
    op.drop_column("mcq_questions", "rationales")
