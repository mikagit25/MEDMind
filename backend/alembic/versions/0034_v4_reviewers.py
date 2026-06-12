"""V4 Phase 3 — Reviewer profiles table.

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviewers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("credentials", sa.String(500), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("institution", sa.String(300), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("specialties", JSONB, nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_reviewers_slug", "reviewers", ["slug"])
    op.create_index("ix_reviewers_is_active", "reviewers", ["is_active"])


def downgrade() -> None:
    op.drop_index("ix_reviewers_is_active", table_name="reviewers")
    op.drop_index("ix_reviewers_slug", table_name="reviewers")
    op.drop_table("reviewers")
