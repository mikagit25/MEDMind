"""add image upload fields and image_annotations table

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    # ── Add upload metadata columns to medical_images ─────────────────────
    op.add_column(
        "medical_images",
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "medical_images",
        sa.Column(
            "is_user_upload",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # ── image_annotations table ───────────────────────────────────────────
    op.create_table(
        "image_annotations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "image_id",
            UUID(as_uuid=True),
            sa.ForeignKey("medical_images.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("annotation_type", sa.String(30), nullable=False),
        sa.Column("x", sa.Float(), nullable=True),
        sa.Column("y", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("x2", sa.Float(), nullable=True),
        sa.Column("y2", sa.Float(), nullable=True),
        sa.Column("points", JSONB(), nullable=True),
        sa.Column("label", sa.String(300), nullable=True),
        sa.Column("color", sa.String(20), server_default="#FF0000"),
        sa.Column("stroke_width", sa.Integer(), server_default="2"),
        sa.Column("font_size", sa.Integer(), server_default="14"),
        sa.Column("opacity", sa.Float(), server_default="1.0"),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_image_annotations_image_id", "image_annotations", ["image_id"])


def downgrade():
    op.drop_index("ix_image_annotations_image_id", table_name="image_annotations")
    op.drop_table("image_annotations")
    op.drop_column("medical_images", "is_user_upload")
    op.drop_column("medical_images", "uploaded_by")
