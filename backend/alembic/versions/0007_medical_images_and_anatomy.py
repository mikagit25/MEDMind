"""Add medical_images and anatomy_viewers tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medical_images",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("modality", sa.String(50), nullable=False),
        sa.Column("anatomy_region", sa.String(100), nullable=True),
        sa.Column("specialty", sa.String(100), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(100), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("view_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_medical_images_modality", "medical_images", ["modality"])
    op.create_index("ix_medical_images_anatomy_region", "medical_images", ["anatomy_region"])
    op.create_index("ix_medical_images_specialty", "medical_images", ["specialty"])
    op.create_index("ix_medical_images_modality_region", "medical_images", ["modality", "anatomy_region"])

    op.create_table(
        "anatomy_viewers",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("organ_system", sa.String(100), nullable=True),
        sa.Column("anatomy_region", sa.String(100), nullable=True),
        sa.Column("embed_type", sa.String(50), default="sketchfab"),
        sa.Column("embed_id", sa.String(200), nullable=False),
        sa.Column("embed_url", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(100), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("sort_order", sa.Integer(), default=0),
    )
    op.create_index("ix_anatomy_viewers_organ_system", "anatomy_viewers", ["organ_system"])
    op.create_index("ix_anatomy_viewers_anatomy_region", "anatomy_viewers", ["anatomy_region"])


def downgrade() -> None:
    op.drop_table("anatomy_viewers")
    op.drop_table("medical_images")
