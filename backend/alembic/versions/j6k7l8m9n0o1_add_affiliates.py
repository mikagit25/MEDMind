"""add affiliates tables and referred_by_affiliate_id on users

Revision ID: j6k7l8m9n0o1
Revises: h4i5j6k7l8m9
Create Date: 2026-07-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "j6k7l8m9n0o1"
down_revision = "h4i5j6k7l8m9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "affiliates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("commission_type", sa.String(20), nullable=False, server_default="percent"),
        sa.Column("commission_value", sa.Float, nullable=False, server_default="20"),
        sa.Column("payout_info", JSONB, nullable=True),
        sa.Column("cookie_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("total_clicks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_signups", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_conversions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_earned", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_paid", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_affiliates_code", "affiliates", ["code"])

    op.create_table(
        "affiliate_clicks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("affiliate_id", UUID(as_uuid=True), sa.ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("referrer", sa.String(500), nullable=True),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("clicked_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_aff_clicks_affiliate", "affiliate_clicks", ["affiliate_id"])
    op.create_index("ix_aff_clicks_at", "affiliate_clicks", ["clicked_at"])

    op.create_table(
        "affiliate_conversions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("affiliate_id", UUID(as_uuid=True), sa.ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("tier", sa.String(20), nullable=True),
        sa.Column("amount_paid", sa.Float, nullable=True),
        sa.Column("commission_amount", sa.Float, nullable=True),
        sa.Column("is_paid_out", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("stripe_invoice_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_aff_conv_affiliate", "affiliate_conversions", ["affiliate_id"])
    op.create_index("ix_aff_conv_user", "affiliate_conversions", ["user_id"])

    op.add_column("users", sa.Column("referred_by_affiliate_id", UUID(as_uuid=True), nullable=True))
    op.create_index("ix_users_referred_by_affiliate", "users", ["referred_by_affiliate_id"])


def downgrade():
    op.drop_index("ix_users_referred_by_affiliate", table_name="users")
    op.drop_column("users", "referred_by_affiliate_id")
    op.drop_table("affiliate_conversions")
    op.drop_table("affiliate_clicks")
    op.drop_table("affiliates")
