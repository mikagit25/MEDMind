"""Enhance student_memories: source metadata, species applicability, audit trail.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "student_memories",
        sa.Column("source_hint", sa.String(200), nullable=True),
    )
    op.add_column(
        "student_memories",
        sa.Column("requires_verification", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column(
        "student_memories",
        sa.Column("species_applicability", sa.JSON(), nullable=True),
    )
    op.add_column(
        "student_memories",
        sa.Column("misconception_severity", sa.String(10), nullable=True),
    )
    op.add_column(
        "student_memories",
        sa.Column("prompt_version", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("student_memories", "prompt_version")
    op.drop_column("student_memories", "misconception_severity")
    op.drop_column("student_memories", "species_applicability")
    op.drop_column("student_memories", "requires_verification")
    op.drop_column("student_memories", "source_hint")
