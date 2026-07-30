"""Bank-Scale B2: source_documents table for open-source corpus.

Revision ID: x0y1z2a3b4c5
Revises: w9x0y1z2a3b4
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "x0y1z2a3b4c5"
down_revision = "w9x0y1z2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_slug", sa.String(80),
                  sa.ForeignKey("content_sources.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("nclex_category", sa.String(60), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("url", sa.String(600), nullable=True),
        sa.Column("section", sa.String(300), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("doc_metadata", sa.JSON(), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_source_documents_source_slug", "source_documents", ["source_slug"])
    op.create_index("ix_source_documents_nclex_category", "source_documents", ["nclex_category"])
    op.create_index("ix_source_documents_text_hash", "source_documents", ["text_hash"])


def downgrade() -> None:
    op.drop_index("ix_source_documents_text_hash", "source_documents")
    op.drop_index("ix_source_documents_nclex_category", "source_documents")
    op.drop_index("ix_source_documents_source_slug", "source_documents")
    op.drop_table("source_documents")
