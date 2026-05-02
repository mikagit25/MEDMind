"""add row_version to lessons for optimistic locking

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("lessons", sa.Column("row_version", sa.Integer(), nullable=False, server_default="0"))

def downgrade():
    op.drop_column("lessons", "row_version")
