"""Phase 7: i18n foundation — add language field to modules.

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "modules",
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
    )
    op.create_index("ix_modules_language", "modules", ["language"])


def downgrade():
    op.drop_index("ix_modules_language", table_name="modules")
    op.drop_column("modules", "language")
