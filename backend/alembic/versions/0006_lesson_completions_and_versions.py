"""Add lesson_completions and lesson_versions tables.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lesson_completions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", sa.UUID(as_uuid=True), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("time_spent_seconds", sa.Integer(), default=0),
        sa.Column("quiz_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("quiz_attempts", sa.Integer(), default=0),
        sa.Column("completed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("lesson_id", "user_id", name="uq_lesson_completion"),
    )
    op.create_index("ix_lesson_completions_lesson_id", "lesson_completions", ["lesson_id"])
    op.create_index("ix_lesson_completions_user_id", "lesson_completions", ["user_id"])
    op.create_index("ix_lesson_completions_completed_at", "lesson_completions", ["completed_at"])

    op.create_table(
        "lesson_versions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", sa.UUID(as_uuid=True), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("saved_by", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("saved_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("note", sa.String(200), nullable=True),
    )
    op.create_index("ix_lesson_versions_lesson_id", "lesson_versions", ["lesson_id"])


def downgrade() -> None:
    op.drop_table("lesson_versions")
    op.drop_table("lesson_completions")
