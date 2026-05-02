"""add medical/vet credibility fields and preview token to lessons

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    # Fix default status: new teacher lessons start as draft, not published
    op.alter_column("lessons", "status", server_default="draft")

    # Medical / veterinary credibility columns
    op.add_column(
        "lessons",
        sa.Column(
            "species_applicability",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{human}",
        ),
    )
    op.add_column("lessons", sa.Column("cross_species_warning", sa.Text(), nullable=True))
    op.add_column(
        "lessons",
        sa.Column("clinical_risk_level", sa.String(20), nullable=False, server_default="low"),
    )
    op.add_column(
        "lessons",
        sa.Column(
            "requires_clinical_supervision",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column("lessons", sa.Column("guideline_version", sa.String(100), nullable=True))
    op.add_column("lessons", sa.Column("last_expert_review", sa.DateTime(), nullable=True))
    op.add_column("lessons", sa.Column("next_review_due", sa.DateTime(), nullable=True))

    # Preview token for sharing drafts
    op.add_column("lessons", sa.Column("preview_token", sa.String(64), nullable=True))
    op.add_column("lessons", sa.Column("preview_expires_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_lessons_preview_token", "lessons", ["preview_token"])
    op.create_index("ix_lessons_preview_token", "lessons", ["preview_token"])

    # GIN index for species array filtering
    op.create_index(
        "ix_lessons_species_applicability",
        "lessons",
        ["species_applicability"],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_index("ix_lessons_species_applicability", table_name="lessons")
    op.drop_index("ix_lessons_preview_token", table_name="lessons")
    op.drop_constraint("uq_lessons_preview_token", "lessons", type_="unique")
    op.drop_column("lessons", "preview_expires_at")
    op.drop_column("lessons", "preview_token")
    op.drop_column("lessons", "next_review_due")
    op.drop_column("lessons", "last_expert_review")
    op.drop_column("lessons", "guideline_version")
    op.drop_column("lessons", "requires_clinical_supervision")
    op.drop_column("lessons", "clinical_risk_level")
    op.drop_column("lessons", "cross_species_warning")
    op.drop_column("lessons", "species_applicability")
    op.alter_column("lessons", "status", server_default="published")
