"""add FSM fields to clinical_cases and create clinical_case_sessions

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    # FSM fields on clinical_cases
    op.add_column("clinical_cases", sa.Column("steps", JSONB(), nullable=True))
    op.add_column("clinical_cases", sa.Column("initial_step_id", sa.String(50), nullable=True))
    op.add_column("clinical_cases", sa.Column("ideal_path", JSONB(), nullable=True))
    op.add_column("clinical_cases", sa.Column("max_score", sa.Integer(), server_default="100"))

    # clinical_case_sessions table
    op.create_table(
        "clinical_case_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("clinical_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_step_id", sa.String(50), nullable=True),
        sa.Column("path_taken", JSONB(), server_default="[]"),
        sa.Column("score", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(20), server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("debriefing", JSONB(), nullable=True),
    )
    op.create_index("ix_case_sessions_user", "clinical_case_sessions", ["user_id", "status"])


def downgrade():
    op.drop_index("ix_case_sessions_user", table_name="clinical_case_sessions")
    op.drop_table("clinical_case_sessions")
    op.drop_column("clinical_cases", "max_score")
    op.drop_column("clinical_cases", "ideal_path")
    op.drop_column("clinical_cases", "initial_step_id")
    op.drop_column("clinical_cases", "steps")
