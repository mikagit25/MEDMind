"""Add lay_summary and lay_glossary to lessons

Revision ID: 0028
Revises: 0027
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "lessons",
        sa.Column("lay_summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "lessons",
        sa.Column("lay_glossary", JSONB(), nullable=True),
    )


def downgrade():
    op.drop_column("lessons", "lay_glossary")
    op.drop_column("lessons", "lay_summary")
