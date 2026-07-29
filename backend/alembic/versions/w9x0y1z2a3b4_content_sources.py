"""Bank-Scale B1: content_sources registry table.

Revision ID: w9x0y1z2a3b4
Revises: v8w9x0y1z2a3
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "w9x0y1z2a3b4"
down_revision = "v8w9x0y1z2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_sources",
        sa.Column("slug", sa.String(80), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("publisher", sa.String(200), nullable=False),
        sa.Column("url", sa.String(600), nullable=False),
        sa.Column("license", sa.String(100), nullable=False),
        sa.Column("license_url", sa.String(600), nullable=True),
        sa.Column("text_reuse_allowed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attribution_template", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("verified_at", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_content_sources_type", "content_sources", ["source_type"])
    op.create_index("ix_content_sources_text_reuse", "content_sources", ["text_reuse_allowed"])


def downgrade() -> None:
    op.drop_index("ix_content_sources_text_reuse", "content_sources")
    op.drop_index("ix_content_sources_type", "content_sources")
    op.drop_table("content_sources")
