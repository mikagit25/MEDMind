"""add_mcq_jurisdiction_fields

Revision ID: b2c3d4e5f6a7
Revises: f6e5d4c3b2a1
Create Date: 2026-08-06

Phase L2: add jurisdiction_sensitive, jurisdiction_verified_for, origin,
jurisdiction_audit_at, jurisdiction_audit_notes to mcq_questions.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f6e5d4c3b2a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mcq_questions",
        sa.Column("origin", sa.String(20), nullable=True),
    )
    op.add_column(
        "mcq_questions",
        sa.Column("jurisdiction_sensitive", sa.Boolean(), nullable=False,
                  server_default="false"),
    )
    op.add_column(
        "mcq_questions",
        sa.Column("jurisdiction_verified_for",
                  postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "mcq_questions",
        sa.Column("jurisdiction_audit_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "mcq_questions",
        sa.Column("jurisdiction_audit_notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_mcq_jurisdiction_sensitive",
                    "mcq_questions", ["jurisdiction_sensitive"])
    op.create_index("ix_mcq_origin", "mcq_questions", ["origin"])


def downgrade() -> None:
    op.drop_index("ix_mcq_origin", table_name="mcq_questions")
    op.drop_index("ix_mcq_jurisdiction_sensitive", table_name="mcq_questions")
    op.drop_column("mcq_questions", "jurisdiction_audit_notes")
    op.drop_column("mcq_questions", "jurisdiction_audit_at")
    op.drop_column("mcq_questions", "jurisdiction_verified_for")
    op.drop_column("mcq_questions", "jurisdiction_sensitive")
    op.drop_column("mcq_questions", "origin")
