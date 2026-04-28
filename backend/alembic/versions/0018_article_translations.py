"""Article translations — multilingual article content

Revision ID: 0018
Revises: 0017
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_translations",
        sa.Column("article_id", UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, primary_key=True),
        sa.Column("locale", sa.String(10), nullable=False, primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("body", JSONB, nullable=False, server_default="[]"),
        sa.Column("faq", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("translated_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_article_translations_article_id", "article_translations", ["article_id"])
    op.create_index("ix_article_translations_status", "article_translations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_article_translations_status", "article_translations")
    op.drop_index("ix_article_translations_article_id", "article_translations")
    op.drop_table("article_translations")
