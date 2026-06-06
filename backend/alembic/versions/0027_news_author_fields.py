"""add author and review_status fields to news_articles

Revision ID: 0027
Revises: 0026
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("news_articles",
        sa.Column("author_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True))
    op.add_column("news_articles",
        sa.Column("author_display_name", sa.String(200), nullable=True))
    # draft | submitted | published | rejected
    op.add_column("news_articles",
        sa.Column("review_status", sa.String(20), nullable=False,
                  server_default="published"))
    op.add_column("news_articles",
        sa.Column("review_note", sa.Text, nullable=True))
    op.create_index("idx_news_review_status", "news_articles", ["review_status"])
    op.create_index("idx_news_author_id", "news_articles", ["author_id"])


def downgrade():
    op.drop_index("idx_news_author_id", "news_articles")
    op.drop_index("idx_news_review_status", "news_articles")
    op.drop_column("news_articles", "review_note")
    op.drop_column("news_articles", "review_status")
    op.drop_column("news_articles", "author_display_name")
    op.drop_column("news_articles", "author_id")
