"""Add student_memories and memory_relations tables for long-term AI memory

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_memories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(30), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("search_tokens", sa.Text),
        sa.Column("specialty", sa.String(100)),
        sa.Column("competency_level", sa.String(20)),
        sa.Column("species_context", sa.String(20)),
        sa.Column("source_conversation_id", UUID(as_uuid=True),
                  sa.ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("confidence", sa.Float, server_default="0.7"),
        sa.Column("verified", sa.Boolean, server_default="false"),
        sa.Column("deprecated", sa.Boolean, server_default="false"),
        sa.Column("importance_score", sa.Float, server_default="0.5"),
        sa.Column("access_count", sa.Integer, server_default="0"),
        sa.Column("last_accessed", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_student_memories_user_id", "student_memories", ["user_id"])
    op.create_index("ix_student_memories_deprecated", "student_memories", ["deprecated"])
    op.create_index("ix_student_memories_specialty", "student_memories", ["specialty"])
    # Full-text search index on search_tokens (PostgreSQL GIN)
    op.execute(
        "CREATE INDEX ix_student_memories_fts ON student_memories "
        "USING gin(to_tsvector('english', coalesce(search_tokens, '')))"
    )

    op.create_table(
        "memory_relations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_memory_id", UUID(as_uuid=True),
                  sa.ForeignKey("student_memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_memory_id", UUID(as_uuid=True),
                  sa.ForeignKey("student_memories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("species_context", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_relations_source", "memory_relations", ["source_memory_id"])


def downgrade() -> None:
    op.drop_table("memory_relations")
    op.drop_index("ix_student_memories_fts", table_name="student_memories")
    op.drop_table("student_memories")
