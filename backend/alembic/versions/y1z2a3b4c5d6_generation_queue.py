"""Bank-Scale B3: generation_queue table for gap-driven generation tasks.

Revision ID: y1z2a3b4c5d6
Revises: x0y1z2a3b4c5
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "y1z2a3b4c5d6"
down_revision = "x0y1z2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_queue",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("exam_slug", sa.String(60), nullable=False),
        sa.Column("nclex_category", sa.String(60), nullable=False),
        sa.Column("question_type", sa.String(20), nullable=False, server_default="mcq"),
        sa.Column("target_difficulty", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("count_requested", sa.Integer(), nullable=False),
        sa.Column("count_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("generation_report", JSONB(), nullable=True),
    )
    op.create_index("ix_genqueue_status", "generation_queue", ["status"])
    op.create_index("ix_genqueue_exam_cat", "generation_queue", ["exam_slug", "nclex_category"])


def downgrade() -> None:
    op.drop_index("ix_genqueue_exam_cat", "generation_queue")
    op.drop_index("ix_genqueue_status", "generation_queue")
    op.drop_table("generation_queue")
