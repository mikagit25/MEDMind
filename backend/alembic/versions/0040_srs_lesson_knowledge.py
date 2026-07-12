"""0040 — SRS knowledge items for lessons and articles

Revision ID: 0040
Revises: 0039
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0040_srs_lesson_knowledge"
down_revision = "0039_social_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lesson_srs_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),   # "lesson" | "article"
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ease_factor", sa.Numeric(4, 2), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer, nullable=False, server_default="1"),
        sa.Column("next_review_at", sa.DateTime, nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime, nullable=True),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_lesson_srs_item"),
    )
    op.create_index("ix_lesson_srs_items_user_next", "lesson_srs_items", ["user_id", "next_review_at"])

    op.create_table(
        "lesson_mcq_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("questions", postgresql.JSONB, nullable=False),
        sa.Column("generated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_lesson_mcq_cache"),
    )


def downgrade() -> None:
    op.drop_table("lesson_mcq_cache")
    op.drop_index("ix_lesson_srs_items_user_next", table_name="lesson_srs_items")
    op.drop_table("lesson_srs_items")
