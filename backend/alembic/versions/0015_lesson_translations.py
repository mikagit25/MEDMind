"""lesson_translations and module_translations tables

Revision ID: 0015_lesson_translations
Revises: 0014
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0015_lesson_translations"
down_revision = "0014"
branch_labels = None
depends_on = None

SUPPORTED_LOCALES = ["ru", "ar", "tr", "de", "fr", "es"]


def upgrade() -> None:
    # ── lesson_translations ────────────────────────────────────────────────────
    op.create_table(
        "lesson_translations",
        sa.Column("lesson_id", UUID(as_uuid=True), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content_json", JSONB, nullable=False),    # translated blocks array
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        # pending | translating | done | failed | reviewed
        sa.Column("translation_quality", sa.Float, nullable=True),  # 0.0-1.0 confidence
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("translated_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("lesson_id", "locale"),
    )
    op.create_index("ix_lesson_translations_lesson_id", "lesson_translations", ["lesson_id"])
    op.create_index("ix_lesson_translations_status", "lesson_translations", ["status"])

    # ── module_translations ────────────────────────────────────────────────────
    op.create_table(
        "module_translations",
        sa.Column("module_id", UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(10), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("translated_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("module_id", "locale"),
    )
    op.create_index("ix_module_translations_module_id", "module_translations", ["module_id"])


def downgrade() -> None:
    op.drop_table("lesson_translations")
    op.drop_table("module_translations")
