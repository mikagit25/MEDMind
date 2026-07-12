"""0041 — Module completion certificates

Revision ID: 0041_certificates
Revises: 0040_srs_lesson_knowledge
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0041_certificates"
down_revision = "0040_srs_lesson_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_code", sa.String(32), unique=True, nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("issued_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("hide_name", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("user_id", "module_id", name="uq_certificate_user_module"),
    )
    op.create_index("ix_certificates_user_id", "certificates", ["user_id"])
    op.create_index("ix_certificates_verification_code", "certificates", ["verification_code"])


def downgrade() -> None:
    op.drop_index("ix_certificates_verification_code", table_name="certificates")
    op.drop_index("ix_certificates_user_id", table_name="certificates")
    op.drop_table("certificates")
