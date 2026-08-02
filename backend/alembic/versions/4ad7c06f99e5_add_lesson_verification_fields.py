"""add_lesson_verification_fields

Revision ID: 4ad7c06f99e5
Revises: z2a3b4c5d6e7
Create Date: 2026-08-02

Add sources, verification_status, and verified_at to the lessons table
so lesson content can go through the same PubMed-enrich → LLM-verify
pipeline as articles.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4ad7c06f99e5"
down_revision: Union[str, None] = "z2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("sources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "verification_status",
            sa.String(length=30),
            server_default="unverified",
            nullable=False,
        ),
    )
    op.add_column(
        "lessons",
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_lessons_verification_status",
        "lessons",
        ["verification_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_lessons_verification_status", table_name="lessons")
    op.drop_column("lessons", "verified_at")
    op.drop_column("lessons", "verification_status")
    op.drop_column("lessons", "sources")
