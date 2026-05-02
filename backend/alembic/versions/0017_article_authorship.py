"""Article authorship — teacher-written articles with review workflow

Revision ID: 0017
Revises: 0016
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Author FK — nullable (NULL = AI-generated / MedMind editorial)
    op.add_column("articles", sa.Column(
        "author_id",
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    ))
    # Display name override (teacher may want a pen name / credentials)
    op.add_column("articles", sa.Column("author_display_name", sa.String(200), nullable=True))
    # Short bio / credentials shown on article page
    op.add_column("articles", sa.Column("author_bio", sa.Text, nullable=True))

    # Review workflow: draft | pending_review | published | rejected
    op.add_column("articles", sa.Column(
        "review_status",
        sa.String(30),
        nullable=False,
        server_default="published",  # existing rows (AI-generated) stay published
    ))
    # Admin review note (shown to teacher on rejection)
    op.add_column("articles", sa.Column("review_note", sa.Text, nullable=True))
    # When teacher submitted for review
    op.add_column("articles", sa.Column("submitted_at", sa.DateTime, nullable=True))

    op.create_index("ix_articles_author_id", "articles", ["author_id"])
    op.create_index("ix_articles_review_status", "articles", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_articles_review_status", "articles")
    op.drop_index("ix_articles_author_id", "articles")
    op.drop_column("articles", "submitted_at")
    op.drop_column("articles", "review_note")
    op.drop_column("articles", "review_status")
    op.drop_column("articles", "author_bio")
    op.drop_column("articles", "author_display_name")
    op.drop_column("articles", "author_id")
