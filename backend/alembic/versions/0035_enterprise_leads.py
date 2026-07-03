"""Add enterprise_leads table.

Revision ID: 0035_enterprise_leads
Revises: 0034_v4_reviewers
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0035_enterprise_leads"
down_revision = "d195a0dac7ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enterprise_leads",
        sa.Column("id",         UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name",  sa.String(100), nullable=False),
        sa.Column("email",      sa.String(320), nullable=False),
        sa.Column("company",    sa.String(200), nullable=False),
        sa.Column("job_title",  sa.String(200), nullable=False),
        sa.Column("team_size",  sa.String(20),  nullable=False),
        sa.Column("use_case",   sa.String(100), nullable=False),
        sa.Column("message",    sa.Text,        nullable=True),
        sa.Column("ip_hash",    sa.String(64),  nullable=True),
        sa.Column("status",     sa.String(20),  nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime,    nullable=True),
        sa.Column("updated_at", sa.DateTime,    nullable=True),
    )
    op.create_index("ix_enterprise_leads_status",     "enterprise_leads", ["status"])
    op.create_index("ix_enterprise_leads_created_at", "enterprise_leads", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_enterprise_leads_created_at", table_name="enterprise_leads")
    op.drop_index("ix_enterprise_leads_status",     table_name="enterprise_leads")
    op.drop_table("enterprise_leads")
