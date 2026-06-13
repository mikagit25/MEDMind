"""Add missing model columns — articles verification, users leaderboard, article_translations QA

Revision ID: 0003_add_missing_columns
Revises: 2b5112c7bd74
Create Date: 2026-06-13

Adds columns that exist in SQLAlchemy models but were never migrated to the DB.
Only ADD COLUMN / ADD INDEX — no drops, no destructive changes.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0003_add_missing_columns'
down_revision: Union[str, None] = '2b5112c7bd74'
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

    # ── articles ─────────────────────────────────────────────────────────────────
    if not col_exists("articles", "verified_at"):
        op.add_column("articles", sa.Column("verified_at", sa.DateTime(), nullable=True))
    if not col_exists("articles", "verification_report"):
        op.add_column("articles", sa.Column("verification_report", postgresql.JSONB(), nullable=True))
    if not col_exists("articles", "reviewed_by"):
        op.add_column("articles", sa.Column("reviewed_by", sa.String(200), nullable=True))
    if not col_exists("articles", "reviewed_at"):
        op.add_column("articles", sa.Column("reviewed_at", sa.DateTime(), nullable=True))

    # ── article_translations ──────────────────────────────────────────────────────
    if not col_exists("article_translations", "translation_verification_status"):
        op.add_column("article_translations", sa.Column(
            "translation_verification_status", sa.String(20), nullable=True
        ))
    if not col_exists("article_translations", "translation_qa_report"):
        op.add_column("article_translations", sa.Column(
            "translation_qa_report", postgresql.JSONB(), nullable=True
        ))
    if not col_exists("article_translations", "translation_qa_checked_at"):
        op.add_column("article_translations", sa.Column(
            "translation_qa_checked_at", sa.DateTime(), nullable=True
        ))

    # ── users — leaderboard & streak ─────────────────────────────────────────────
    if not col_exists("users", "longest_streak"):
        op.add_column("users", sa.Column("longest_streak", sa.Integer(), nullable=True, server_default="0"))
    if not col_exists("users", "leaderboard_opt_in"):
        op.add_column("users", sa.Column(
            "leaderboard_opt_in", sa.Boolean(), nullable=False, server_default="false"
        ))
    if not col_exists("users", "leaderboard_display_name"):
        op.add_column("users", sa.Column("leaderboard_display_name", sa.String(100), nullable=True))


def downgrade() -> None:
    # All operations are additive — safe to reverse by dropping what we added
    for col in ("verified_at", "verification_report", "reviewed_by", "reviewed_at"):
        op.drop_column("articles", col)
    for col in ("translation_verification_status", "translation_qa_report", "translation_qa_checked_at"):
        op.drop_column("article_translations", col)
    for col in ("longest_streak", "leaderboard_opt_in", "leaderboard_display_name"):
        op.drop_column("users", col)
