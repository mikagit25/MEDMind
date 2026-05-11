"""medical image translations table

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "medical_image_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("image_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("medical_images.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("image_id", "locale", name="uq_image_translation"),
    )
    op.create_index("idx_mit_image_locale", "medical_image_translations", ["image_id", "locale"])


def downgrade():
    op.drop_table("medical_image_translations")
