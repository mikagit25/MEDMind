"""G3 — Regional pricing columns on users

Revision ID: q3r4s5t6u7v8
Revises: p2q3r4s5t6u7
Create Date: 2026-07-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "q3r4s5t6u7v8"
down_revision = "p2q3r4s5t6u7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("billing_country",         sa.String(2),   nullable=True))
    op.add_column("users", sa.Column("billing_region",          sa.String(1),   nullable=True))
    op.add_column("users", sa.Column("billing_region_changed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for col in ("billing_country", "billing_region", "billing_region_changed_at"):
        op.drop_column("users", col)
