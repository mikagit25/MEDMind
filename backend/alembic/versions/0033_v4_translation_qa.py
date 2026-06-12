"""V4 Phase 2 — Translation QA fields on article_translations.

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "article_translations",
        sa.Column("translation_verification_status", sa.String(20), nullable=True, server_default="pending"),
    )
    op.add_column(
        "article_translations",
        sa.Column("translation_qa_report", JSONB, nullable=True),
    )
    op.add_column(
        "article_translations",
        sa.Column("translation_qa_checked_at", sa.DateTime, nullable=True),
    )
    op.create_index(
        "ix_article_translations_qa_status",
        "article_translations",
        ["translation_verification_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_article_translations_qa_status", table_name="article_translations")
    op.drop_column("article_translations", "translation_qa_checked_at")
    op.drop_column("article_translations", "translation_qa_report")
    op.drop_column("article_translations", "translation_verification_status")
