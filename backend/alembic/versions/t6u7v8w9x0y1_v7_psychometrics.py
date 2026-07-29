"""V7 Phase 1: question_attempts and question_stats tables for psychometrics.

Revision ID: t6u7v8w9x0y1
Revises: s5t6u7v8w9x0
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "t6u7v8w9x0y1"
down_revision = "fba8536a7302"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # question_attempts: one row per user answer, only first attempt counts for psychometrics
    op.create_table(
        "question_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", UUID(as_uuid=True), sa.ForeignKey("mcq_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_slug", sa.String(100), nullable=True),
        sa.Column("selected", JSONB(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("time_seconds", sa.Float(), nullable=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("session_type", sa.String(20), nullable=False, server_default="practice"),
        sa.Column("is_first_attempt", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_qa_question_first", "question_attempts", ["question_id", "is_first_attempt"])
    op.create_index("ix_qa_user_question", "question_attempts", ["user_id", "question_id"])
    op.create_index("ix_qa_session", "question_attempts", ["session_id"])

    # question_stats: one row per (question, optional exam_slug), recomputed nightly
    op.create_table(
        "question_stats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("question_id", UUID(as_uuid=True), sa.ForeignKey("mcq_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_slug", sa.String(100), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("option_distribution", JSONB(), nullable=True),
        sa.Column("discrimination", sa.Float(), nullable=True),
        sa.Column("avg_time_seconds", sa.Float(), nullable=True),
        sa.Column("sample_size_ok", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("computed_difficulty", sa.String(20), nullable=True),
        sa.Column("health", sa.String(50), nullable=False, server_default="'ok'"),
        sa.Column("last_computed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("question_id", "exam_slug", name="uq_question_stats_q_exam"),
    )
    op.create_index("ix_qs_health", "question_stats", ["health"])
    op.create_index("ix_qs_sample_disc", "question_stats", ["sample_size_ok", "discrimination"])

    # Add status + follow_up_count to mcq_questions for Phase 2 & 4
    op.add_column("mcq_questions", sa.Column("status", sa.String(20), nullable=False, server_default="'active'"))
    op.add_column("mcq_questions", sa.Column("follow_up_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("mcq_questions", sa.Column("pending_regeneration", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("mcq_questions", sa.Column("replaces_question_id", UUID(as_uuid=True), nullable=True))
    op.create_index("ix_mcq_status", "mcq_questions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_mcq_status", "mcq_questions")
    op.drop_column("mcq_questions", "replaces_question_id")
    op.drop_column("mcq_questions", "pending_regeneration")
    op.drop_column("mcq_questions", "follow_up_count")
    op.drop_column("mcq_questions", "status")
    op.drop_index("ix_qs_sample_disc", "question_stats")
    op.drop_index("ix_qs_health", "question_stats")
    op.drop_table("question_stats")
    op.drop_index("ix_qa_session", "question_attempts")
    op.drop_index("ix_qa_user_question", "question_attempts")
    op.drop_index("ix_qa_question_first", "question_attempts")
    op.drop_table("question_attempts")
