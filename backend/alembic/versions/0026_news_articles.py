"""news_articles table

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("slug", sa.String(400), nullable=False, unique=True),

        # Source metadata
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("source_doi", sa.String(300), nullable=True),
        sa.Column("source_hash", sa.String(64), nullable=False, unique=True),

        # English content (AI-generated summary of the original)
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=True),

        # Translations: {"ru": {"title": "...", "summary": "..."}, ...}
        sa.Column("translations", postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'")),

        # Dates
        sa.Column("original_published_at", sa.DateTime, nullable=True),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.Column("translated_at", sa.DateTime, nullable=True),

        sa.Column("is_published", sa.Boolean, nullable=False,
                  server_default=sa.text("true")),
    )
    op.create_index("idx_news_category", "news_articles", ["category"])
    op.create_index("idx_news_fetched_at", "news_articles", ["fetched_at"])
    op.create_index("idx_news_published", "news_articles", ["is_published"])


def downgrade():
    op.drop_table("news_articles")
