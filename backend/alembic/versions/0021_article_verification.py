"""Article verification system — verification_status, verified_sources, last_verified_at

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("articles", sa.Column(
        "verification_status",
        sa.String(30),
        nullable=False,
        server_default="unverified",
    ))
    op.add_column("articles", sa.Column(
        "verified_sources",
        JSONB,
        nullable=True,
    ))
    op.add_column("articles", sa.Column(
        "last_verified_at",
        sa.DateTime,
        nullable=True,
    ))
    op.create_index("ix_articles_verification_status", "articles", ["verification_status"])


def downgrade():
    op.drop_index("ix_articles_verification_status", table_name="articles")
    op.drop_column("articles", "last_verified_at")
    op.drop_column("articles", "verified_sources")
    op.drop_column("articles", "verification_status")
