"""add_jurisdiction_profiles_and_rules

Revision ID: a1b2c3d4e5f6
Revises: 4ad7c06f99e5
Create Date: 2026-08-06

Phase L1: jurisdiction-aware content layer.
Creates jurisdiction_profiles and jurisdiction_rules tables.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6e5d4c3b2a1"
down_revision: Union[str, None] = "4ad7c06f99e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jurisdiction_profiles",
        sa.Column("slug", sa.String(30), primary_key=True),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("regulator", sa.String(100), nullable=False),
        sa.Column("exam_slugs", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default="[]"),
        sa.Column("locale_primary", sa.String(10), nullable=False, server_default="ar"),
        sa.Column("emergency_numbers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("units_system", sa.String(10), nullable=False, server_default="SI"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_jurisdiction_profiles_status", "jurisdiction_profiles", ["status"])

    op.create_table(
        "jurisdiction_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_slug", sa.String(30),
                  sa.ForeignKey("jurisdiction_profiles.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("domain", sa.String(60), nullable=False),
        sa.Column("rule_key", sa.String(80), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(300), nullable=True),
        sa.Column("source_url", sa.String(600), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("verified_by", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="needs_human"),
        sa.Column("divergence_from_us", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_unique_constraint(
        "uq_jurisdiction_rules_profile_domain_key",
        "jurisdiction_rules",
        ["profile_slug", "domain", "rule_key"],
    )
    op.create_index("ix_jurisdiction_rules_profile_domain",
                    "jurisdiction_rules", ["profile_slug", "domain"])
    op.create_index("ix_jurisdiction_rules_status", "jurisdiction_rules", ["status"])
    op.create_index("ix_jurisdiction_rules_domain", "jurisdiction_rules", ["domain"])


def downgrade() -> None:
    op.drop_table("jurisdiction_rules")
    op.drop_table("jurisdiction_profiles")
