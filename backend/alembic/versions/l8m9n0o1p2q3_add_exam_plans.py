"""add exam_plans and exam_plan_completions

Revision ID: l8m9n0o1p2q3
Revises: k7l8m9n0o1p2
Create Date: 2026-07-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "l8m9n0o1p2q3"
down_revision = "k7l8m9n0o1p2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "exam_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exam_type", sa.String(50), nullable=False, server_default="nclex"),
        sa.Column("exam_date", sa.DateTime, nullable=False),
        sa.Column("daily_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("plan_cache", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "exam_type", "status",
                            name="uq_exam_plans_one_active_per_type"),
    )
    op.create_index("ix_exam_plans_user", "exam_plans", ["user_id"])

    op.create_table(
        "exam_plan_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("exam_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_date", sa.DateTime, nullable=False),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("plan_id", "task_date", name="uq_epc_one_per_day"),
    )
    op.create_index("ix_epc_plan", "exam_plan_completions", ["plan_id"])


def downgrade():
    op.drop_table("exam_plan_completions")
    op.drop_table("exam_plans")
