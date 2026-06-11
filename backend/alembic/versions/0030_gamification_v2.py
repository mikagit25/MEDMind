"""Phase 5: gamification — longest_streak, leaderboard opt-in, XPEvent table.

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade():
    # Add gamification columns to users
    op.add_column("users", sa.Column("longest_streak", sa.Integer, nullable=False, server_default="0"))
    op.add_column("users", sa.Column("leaderboard_opt_in", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("users", sa.Column("leaderboard_display_name", sa.String(100), nullable=True))

    # XP audit trail table
    op.create_table(
        "xp_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_xp_events_user_id", "xp_events", ["user_id"])
    op.create_index("ix_xp_events_created_at", "xp_events", ["created_at"])


def downgrade():
    op.drop_table("xp_events")
    op.drop_column("users", "leaderboard_display_name")
    op.drop_column("users", "leaderboard_opt_in")
    op.drop_column("users", "longest_streak")
