"""Add verification columns to news_articles

Revision ID: 0004_add_news_verification
Revises: 0003_add_missing_columns
Create Date: 2026-06-13

Adds V4 verification columns that exist in the NewsArticle model but were never
migrated to the DB. Uses server_default='passed' for verification_status so all
existing news articles remain visible (PUBLISHED_STATUSES = {"passed", "human_reviewed"}).
Only ADD COLUMN — no drops, no destructive changes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0004_add_news_verification'
down_revision: Union[str, None] = '0003_add_missing_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    def col_exists(table: str, col: str) -> bool:
        res = conn.execute(sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ), {"t": table, "c": col})
        return res.fetchone() is not None

    # ── news_articles ─────────────────────────────────────────────────────────────
    # server_default='passed' so all existing articles remain visible in the news feed
    if not col_exists("news_articles", "verification_status"):
        op.add_column("news_articles", sa.Column(
            "verification_status", sa.String(30), nullable=False, server_default="passed"
        ))
    if not col_exists("news_articles", "sources_v4"):
        op.add_column("news_articles", sa.Column("sources_v4", postgresql.JSONB(), nullable=True))
    if not col_exists("news_articles", "verified_at"):
        op.add_column("news_articles", sa.Column("verified_at", sa.DateTime(), nullable=True))
    if not col_exists("news_articles", "verification_report"):
        op.add_column("news_articles", sa.Column("verification_report", postgresql.JSONB(), nullable=True))
    if not col_exists("news_articles", "reviewed_by"):
        op.add_column("news_articles", sa.Column("reviewed_by", sa.String(200), nullable=True))
    if not col_exists("news_articles", "reviewed_at"):
        op.add_column("news_articles", sa.Column("reviewed_at", sa.DateTime(), nullable=True))

    # Add index on verification_status for query performance
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_news_articles_verification_status "
        "ON news_articles (verification_status)"
    ))


def downgrade() -> None:
    op.drop_index("ix_news_articles_verification_status", table_name="news_articles")
    for col in ("verification_status", "sources_v4", "verified_at", "verification_report", "reviewed_by", "reviewed_at"):
        op.drop_column("news_articles", col)
