"""Bank-Scale B4: question_reviews table for human reviewer rubric assessments.

Revision ID: z2a3b4c5d6e7
Revises: y1z2a3b4c5d6
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "z2a3b4c5d6e7"
down_revision = "y1z2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("question_id", UUID(as_uuid=True),
                  sa.ForeignKey("mcq_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("realism",               sa.Integer(), nullable=False),
        sa.Column("clinical_accuracy",     sa.Integer(), nullable=False),
        sa.Column("key_correct",           sa.Integer(), nullable=False),
        sa.Column("rationale_quality",     sa.Integer(), nullable=False),
        sa.Column("distractors_plausible", sa.Integer(), nullable=False),
        sa.Column("language_clarity",      sa.Integer(), nullable=False),
        sa.Column("category_correct",      sa.Integer(), nullable=False),
        sa.Column("comment",       sa.Text(),        nullable=True),
        sa.Column("decision",      sa.String(30),    nullable=False),
        sa.Column("edits",         JSONB(),          nullable=True),
        sa.Column("reject_reason", sa.String(50),    nullable=True),
        sa.Column("created_at",    sa.DateTime(),    nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_question_reviews_question_id", "question_reviews", ["question_id"])
    op.create_index("ix_question_reviews_reviewer",    "question_reviews", ["reviewer_user_id"])
    op.create_index("ix_question_reviews_decision",    "question_reviews", ["decision"])
    op.create_index("ix_question_reviews_created",     "question_reviews", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_question_reviews_created",     "question_reviews")
    op.drop_index("ix_question_reviews_decision",    "question_reviews")
    op.drop_index("ix_question_reviews_reviewer",    "question_reviews")
    op.drop_index("ix_question_reviews_question_id", "question_reviews")
    op.drop_table("question_reviews")
