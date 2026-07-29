"""V7 Phase 3: exam_outcomes table for post-exam survey loop.

Revision ID: v8w9x0y1z2a3
Revises: u7v8w9x0y1z2
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "v8w9x0y1z2a3"
down_revision = "u7v8w9x0y1z2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_plan_id", UUID(as_uuid=True), sa.ForeignKey("exam_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("exam_slug", sa.String(60), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        # Readiness snapshot captured by cron the day before exam_date
        sa.Column("readiness_at_exam", sa.Float(), nullable=True),
        # User-reported outcome
        sa.Column("result", sa.String(20), nullable=True),  # passed|failed|postponed|no_answer
        sa.Column("self_reported_score", sa.String(50), nullable=True),
        # Step 2: blueprint feedback (list of category slugs)
        sa.Column("harder_topics", sa.JSON(), nullable=True),
        sa.Column("weaker_topics", sa.JSON(), nullable=True),
        sa.Column("feedback_note", sa.Text(), nullable=True),
        # Step 3: NPS
        sa.Column("nps_score", sa.Integer(), nullable=True),
        # Survey lifecycle
        sa.Column("survey_sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_survey_sent_at", sa.DateTime(), nullable=True),
        sa.Column("unsubscribed_from_survey", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reported_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_exam_outcomes_user", "exam_outcomes", ["user_id"])
    op.create_index("ix_exam_outcomes_exam_date", "exam_outcomes", ["exam_date"])
    op.create_index("ix_exam_outcomes_exam_slug", "exam_outcomes", ["exam_slug"])


def downgrade() -> None:
    op.drop_index("ix_exam_outcomes_exam_slug", "exam_outcomes")
    op.drop_index("ix_exam_outcomes_exam_date", "exam_outcomes")
    op.drop_index("ix_exam_outcomes_user", "exam_outcomes")
    op.drop_table("exam_outcomes")
