"""Add teacher lesson authoring: author_id, status, published_at on lessons and modules.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Lesson: author + workflow fields
    op.add_column("lessons", sa.Column("author_id", sa.UUID(as_uuid=True), nullable=True))
    op.add_column("lessons", sa.Column(
        "status", sa.String(20), nullable=False, server_default="published"
    ))
    op.add_column("lessons", sa.Column("published_at", sa.DateTime(), nullable=True))
    op.add_column("lessons", sa.Column("review_notes", sa.Text(), nullable=True))
    op.create_index("ix_lessons_status", "lessons", ["status"])

    # Module: author field (for teacher-created modules)
    op.add_column("modules", sa.Column("author_id", sa.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_lessons_status", table_name="lessons")
    op.drop_column("lessons", "review_notes")
    op.drop_column("lessons", "published_at")
    op.drop_column("lessons", "status")
    op.drop_column("lessons", "author_id")
    op.drop_column("modules", "author_id")
