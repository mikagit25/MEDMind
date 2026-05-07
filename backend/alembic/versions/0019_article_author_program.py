"""article author program — add view_count and revenue_share_pct to articles

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "articles",
        sa.Column("revenue_share_pct", sa.Integer(), nullable=False, server_default="70"),
    )


def downgrade() -> None:
    op.drop_column("articles", "revenue_share_pct")
    op.drop_column("articles", "view_count")
