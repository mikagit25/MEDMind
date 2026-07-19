"""billing hardening — webhook idempotency, billing_events, affiliate anti-fraud fields

Revision ID: n0o1p2q3r4s5
Revises: m9n0o1p2q3r4
Create Date: 2026-07-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "n0o1p2q3r4s5"
down_revision = "m9n0o1p2q3r4"
branch_labels = None
depends_on = None


def upgrade():
    # ── stripe_webhook_events ─────────────────────────────────────────────────
    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(100), unique=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ok"),
        sa.Column("error_msg", sa.Text, nullable=True),
        sa.Column("processed_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_stripe_webhook_event_id", "stripe_webhook_events", ["event_id"])

    # ── billing_events ────────────────────────────────────────────────────────
    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("old_tier", sa.String(30), nullable=True),
        sa.Column("new_tier", sa.String(30), nullable=True),
        sa.Column("amount", sa.Float, nullable=True),
        sa.Column("stripe_invoice_id", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("meta", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_billing_events_user", "billing_events", ["user_id"])
    op.create_index("ix_billing_events_type_created", "billing_events", ["event_type", "created_at"])

    # ── affiliate_conversions — anti-fraud columns ────────────────────────────
    op.add_column("affiliate_conversions",
        sa.Column("commission_status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("affiliate_conversions",
        sa.Column("is_suspicious", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("affiliate_conversions",
        sa.Column("clearance_date", sa.DateTime, nullable=True))

    # ── promo_code_uses — unique (code_id, user_id) ───────────────────────────
    # Add only if it doesn't already exist (idempotent via try/except in app startup)
    try:
        op.create_unique_constraint(
            "uq_promo_one_use_per_user", "promo_code_uses", ["code_id", "user_id"]
        )
    except Exception:
        pass  # constraint already exists


def downgrade():
    op.drop_table("billing_events")
    op.drop_table("stripe_webhook_events")
    op.drop_column("affiliate_conversions", "commission_status")
    op.drop_column("affiliate_conversions", "is_suspicious")
    op.drop_column("affiliate_conversions", "clearance_date")
    try:
        op.drop_constraint("uq_promo_one_use_per_user", "promo_code_uses")
    except Exception:
        pass
