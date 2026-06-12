"""V4 Phase 1: content verification pipeline fields.

Adds verification_report, reviewed_by, reviewed_at to articles.
Migrates verification_status enum to V4 values (pending/passed/failed/human_reviewed).
Adds full verification fields to news_articles.
Adds content_feedback table.

Revision ID: 0032
Revises: 0031
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade():
    # ── articles: add V4 verification fields ─────────────────────────────────
    op.add_column("articles", sa.Column("verification_report", JSONB, nullable=True))
    op.add_column("articles", sa.Column("reviewed_by", sa.String(200), nullable=True))
    op.add_column("articles", sa.Column("reviewed_at", sa.DateTime, nullable=True))
    op.add_column("articles", sa.Column("verified_at", sa.DateTime, nullable=True))

    # Migrate old status values to V4 enum
    op.execute("""
        UPDATE articles SET verification_status =
          CASE verification_status
            WHEN 'ai_verified'     THEN 'passed'
            WHEN 'expert_verified' THEN 'human_reviewed'
            ELSE 'pending'
          END
    """)

    op.execute("""
        ALTER TABLE articles
          ALTER COLUMN verification_status SET DEFAULT 'pending'
    """)

    op.create_index("ix_articles_verification_status", "articles", ["verification_status"])

    # ── news_articles: add V4 verification fields ─────────────────────────────
    op.add_column("news_articles", sa.Column(
        "verification_status", sa.String(30), nullable=False, server_default="pending"
    ))
    op.add_column("news_articles", sa.Column("verification_report", JSONB, nullable=True))
    op.add_column("news_articles", sa.Column("verified_at", sa.DateTime, nullable=True))
    op.add_column("news_articles", sa.Column("reviewed_by", sa.String(200), nullable=True))
    op.add_column("news_articles", sa.Column("reviewed_at", sa.DateTime, nullable=True))
    op.add_column("news_articles", sa.Column("sources_v4", JSONB, nullable=True))

    op.create_index("ix_news_verification_status", "news_articles", ["verification_status"])

    # ── content_feedback table ─────────────────────────────────────────────────
    op.create_table(
        "content_feedback",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("content_type", sa.String(20), nullable=False),   # "article" | "news"
        sa.Column("content_id", sa.String(100), nullable=False),     # UUID or slug
        sa.Column("problem_type", sa.String(50), nullable=False),    # "factual_error"|"outdated"|"missing_source"|"other"
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("reporter_email", sa.String(200), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_content_feedback_content", "content_feedback", ["content_type", "content_id"])


def downgrade():
    op.drop_table("content_feedback")

    op.drop_index("ix_news_verification_status", table_name="news_articles")
    for col in ("verification_status", "verification_report", "verified_at",
                "reviewed_by", "reviewed_at", "sources_v4"):
        op.drop_column("news_articles", col)

    op.drop_index("ix_articles_verification_status", table_name="articles")
    for col in ("verification_report", "reviewed_by", "reviewed_at", "verified_at"):
        op.drop_column("articles", col)

    op.execute("""
        UPDATE articles SET verification_status =
          CASE verification_status
            WHEN 'passed'          THEN 'ai_verified'
            WHEN 'human_reviewed'  THEN 'expert_verified'
            ELSE 'unverified'
          END
    """)
    op.execute("ALTER TABLE articles ALTER COLUMN verification_status SET DEFAULT 'unverified'")
