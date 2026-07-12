"""Product analytics events table (Phase 1 V5).

Revision ID: 0037_analytics_events
Revises: 0036_fix_vet_dosing_columns
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0037_analytics_events"
down_revision = "0036_fix_vet_dosing_columns"
branch_labels = None
depends_on = None

VALID_EVENTS = (
    "signup", "onboarding_step", "onboarding_completed",
    "lesson_started", "lesson_completed",
    "module_started", "module_completed",
    "flashcard_review", "ai_question", "quiz_completed",
    "public_page_view", "search", "app_open",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "analytics_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("anon_id", sa.String(64), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", sa.String(128), nullable=True),
        # metadata: structured only — no free-form user text
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("locale", sa.String(8), nullable=True),
        sa.Column("platform", sa.String(16), nullable=True, server_default="web"),
        sa.Column("created_at", sa.DateTime(timezone=False),
                  nullable=False, server_default=sa.text("now()")),
    )

    # Composite indexes for dashboard queries
    op.create_index("ix_ae_event_type_created", "analytics_events",
                    ["event_type", "created_at"])
    op.create_index("ix_ae_user_created", "analytics_events",
                    ["user_id", "created_at"])

    # Daily aggregates for retention (populated by cron after 12 months)
    op.create_table(
        "analytics_daily_agg",
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("event_type", sa.String(64), primary_key=True),
        sa.Column("platform", sa.String(16), primary_key=True),
        sa.Column("event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("unique_users", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("analytics_daily_agg")
    op.drop_index("ix_ae_user_created", "analytics_events")
    op.drop_index("ix_ae_event_type_created", "analytics_events")
    op.drop_table("analytics_events")
