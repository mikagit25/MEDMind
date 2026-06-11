"""Phase 4: public_quizzes + shared_decks tables.

Revision ID: 0029
Revises: 0028
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "public_quizzes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=False, server_default="general"),
        sa.Column("questions", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("play_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_public_quizzes_slug", "public_quizzes", ["slug"])
    op.create_index("ix_public_quizzes_category", "public_quizzes", ["category"])

    op.create_table(
        "shared_decks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("token", sa.String(20), nullable=False, unique=True),
        sa.Column("cards", JSONB, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("view_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_shared_decks_token", "shared_decks", ["token"])
    op.create_index("ix_shared_decks_owner_id", "shared_decks", ["owner_id"])


def downgrade():
    op.drop_table("shared_decks")
    op.drop_table("public_quizzes")
