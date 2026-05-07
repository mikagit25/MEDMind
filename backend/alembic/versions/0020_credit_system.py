"""credit system — author credit accounts, transactions, llm pricing

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Credit accounts per user ──────────────────────────────────────────────
    op.create_table(
        "author_credit_accounts",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_purchased", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # ── Credit transactions ────────────────────────────────────────────────────
    op.create_table(
        "credit_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("usd_amount", sa.Numeric(10, 4), nullable=True),
        sa.Column("model", sa.String(50), nullable=True),
        sa.Column("actual_cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("article_id", UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_credit_transactions_user_id", "credit_transactions", ["user_id"])

    # ── LLM pricing table ──────────────────────────────────────────────────────
    op.create_table(
        "llm_pricing",
        sa.Column("model", sa.String(50), primary_key=True),
        sa.Column("credits_per_article", sa.Integer(), nullable=False),
        sa.Column("actual_cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("markup_multiplier", sa.Numeric(4, 2), nullable=False, server_default="2.0"),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )

    # Seed LLM pricing
    op.execute("""
        INSERT INTO llm_pricing (model, credits_per_article, actual_cost_usd, markup_multiplier, display_name, description, is_active, updated_at)
        VALUES
          ('ollama',        5,  0.002000, 2.5, 'Ollama (Local AI)',   'Fast, private, runs on our servers',           true, NOW()),
          ('claude-haiku', 10,  0.004000, 2.5, 'Claude Haiku',       'Fast and high-quality medical content',         true, NOW()),
          ('claude-sonnet', 50, 0.050000, 2.0, 'Claude Sonnet',      'Best quality, detailed medical articles',       true, NOW())
        ON CONFLICT (model) DO NOTHING
    """)

    # ── Change revenue_share_pct default from 70 → 40 ─────────────────────────
    op.alter_column("articles", "revenue_share_pct", server_default="40")
    op.execute("UPDATE articles SET revenue_share_pct = 40 WHERE revenue_share_pct = 70")

    # ── Bonus 10 credits to all existing users ────────────────────────────────
    op.execute("""
        INSERT INTO author_credit_accounts (user_id, balance, total_purchased, total_spent)
        SELECT id, 10, 0, 0 FROM users
        ON CONFLICT (user_id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("UPDATE articles SET revenue_share_pct = 70 WHERE revenue_share_pct = 40")
    op.alter_column("articles", "revenue_share_pct", server_default="70")
    op.drop_table("credit_transactions")
    op.drop_table("author_credit_accounts")
    op.drop_table("llm_pricing")
