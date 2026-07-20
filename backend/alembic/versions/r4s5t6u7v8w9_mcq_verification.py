"""MCQ question verification + source_refs columns

Revision ID: r4s5t6u7v8w9
Revises: q3r4s5t6u7v8
Create Date: 2026-07-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r4s5t6u7v8w9"
down_revision = "q3r4s5t6u7v8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mcq_questions", sa.Column(
        "source_refs", postgresql.JSONB(), nullable=True
    ))
    op.add_column("mcq_questions", sa.Column(
        "verification_status", sa.String(30), nullable=False,
        server_default="pending"
    ))
    op.add_column("mcq_questions", sa.Column(
        "verification_report", postgresql.JSONB(), nullable=True
    ))
    op.create_index(
        "ix_mcq_questions_verification_status",
        "mcq_questions", ["verification_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_mcq_questions_verification_status", "mcq_questions")
    for col in ("source_refs", "verification_status", "verification_report"):
        op.drop_column("mcq_questions", col)
