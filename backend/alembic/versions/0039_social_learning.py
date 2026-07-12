"""Social learning: assignment statuses, Q&A comments, deck collaborators (V5 Phase 4).

Revision ID: 0039_social_learning
Revises: 0038_clinical_algorithms
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0039_social_learning"
down_revision = "0038_clinical_algorithms"
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Assignment statuses (per-student per-assignment tracking) ───────────
    op.create_table(
        "assignment_statuses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("assignment_id", UUID(as_uuid=True),
                  sa.ForeignKey("course_assignments.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("assignment_id", "user_id", name="uq_assignment_status"),
    )
    op.create_index("ix_as_assignment_id", "assignment_statuses", ["assignment_id"])
    op.create_index("ix_as_user_id",       "assignment_statuses", ["user_id"])

    # ── 2. Extend comments: Q&A support for modules/lessons ───────────────────
    # comment_type: "comment" (default) | "question"
    op.add_column("comments", sa.Column("comment_type",
        sa.String(20), nullable=False, server_default="comment"))
    # For module/lesson entity (extend content_type to "module"|"lesson")
    op.add_column("comments", sa.Column("entity_id",
        UUID(as_uuid=True), nullable=True))
    # Accepted answer: FK to another comment row (self-referential)
    op.add_column("comments", sa.Column("accepted_answer_id",
        UUID(as_uuid=True), nullable=True))
    # Upvotes count (denormalized for sort performance)
    op.add_column("comments", sa.Column("upvotes",
        sa.Integer, nullable=False, server_default="0"))
    # Parent comment for threading answers to questions
    op.add_column("comments", sa.Column("parent_id",
        UUID(as_uuid=True), nullable=True))

    op.create_index("ix_comments_entity_id", "comments", ["entity_id"])

    # ── 3. Deck collaborators (co-editors on shared decks) ────────────────────
    op.create_table(
        "deck_collaborators",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("deck_id", UUID(as_uuid=True),
                  sa.ForeignKey("shared_decks.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="editor"),
        sa.Column("added_at", sa.DateTime, server_default=sa.text("now()")),
        sa.UniqueConstraint("deck_id", "user_id", name="uq_deck_collaborator"),
    )
    op.create_index("ix_deck_collab_deck_id", "deck_collaborators", ["deck_id"])


def downgrade():
    op.drop_index("ix_deck_collab_deck_id", table_name="deck_collaborators")
    op.drop_table("deck_collaborators")

    op.drop_index("ix_comments_entity_id", table_name="comments")
    op.drop_column("comments", "parent_id")
    op.drop_column("comments", "upvotes")
    op.drop_column("comments", "accepted_answer_id")
    op.drop_column("comments", "entity_id")
    op.drop_column("comments", "comment_type")

    op.drop_index("ix_as_user_id",       table_name="assignment_statuses")
    op.drop_index("ix_as_assignment_id", table_name="assignment_statuses")
    op.drop_table("assignment_statuses")
