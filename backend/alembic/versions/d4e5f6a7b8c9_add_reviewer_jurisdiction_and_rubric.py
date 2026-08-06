"""add_reviewer_jurisdiction_and_rubric

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-06

Phase L5: add jurisdiction fields to reviewers, and local rubric fields
to question_reviews (locally_correct, scope_ok, culturally_appropriate,
local_note, jurisdiction_slug).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reviewer: jurisdiction authorization
    op.add_column("reviewers",
        sa.Column("jurisdictions", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("reviewers",
        sa.Column("license_country", sa.String(100), nullable=True))
    op.add_column("reviewers",
        sa.Column("license_number", sa.String(100), nullable=True))

    # QuestionReview: L5 rubric extension
    op.add_column("question_reviews",
        sa.Column("locally_correct", sa.String(10), nullable=True))
    op.add_column("question_reviews",
        sa.Column("scope_ok", sa.String(5), nullable=True))
    op.add_column("question_reviews",
        sa.Column("culturally_appropriate", sa.String(20), nullable=True))
    op.add_column("question_reviews",
        sa.Column("local_note", sa.Text(), nullable=True))
    op.add_column("question_reviews",
        sa.Column("jurisdiction_slug", sa.String(30), nullable=True))
    op.create_index("ix_question_reviews_jurisdiction",
                    "question_reviews", ["jurisdiction_slug"])


def downgrade() -> None:
    op.drop_index("ix_question_reviews_jurisdiction", table_name="question_reviews")
    op.drop_column("question_reviews", "jurisdiction_slug")
    op.drop_column("question_reviews", "local_note")
    op.drop_column("question_reviews", "culturally_appropriate")
    op.drop_column("question_reviews", "scope_ok")
    op.drop_column("question_reviews", "locally_correct")
    op.drop_column("reviewers", "license_number")
    op.drop_column("reviewers", "license_country")
    op.drop_column("reviewers", "jurisdictions")
