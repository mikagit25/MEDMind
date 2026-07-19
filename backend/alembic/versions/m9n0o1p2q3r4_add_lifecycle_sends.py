"""add lifecycle_sends table

Revision ID: m9n0o1p2q3r4
Revises: l8m9n0o1p2q3
Create Date: 2026-07-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m9n0o1p2q3r4"
down_revision = "l8m9n0o1p2q3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "lifecycle_sends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign", sa.String(60), nullable=False),
        sa.Column("step", sa.String(60), nullable=False, server_default="email"),
        sa.Column("sent_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "campaign", "step",
                            name="uq_lifecycle_one_per_step"),
    )
    op.create_index("ix_lifecycle_user", "lifecycle_sends", ["user_id"])
    op.create_index("ix_lifecycle_campaign", "lifecycle_sends", ["campaign"])


def downgrade():
    op.drop_table("lifecycle_sends")
