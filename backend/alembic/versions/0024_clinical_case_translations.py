"""clinical case translations table

Revision ID: 0024_clinical_case_translations
Revises: 0023_course_discovery
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "clinical_case_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinical_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(300), nullable=True),
        sa.Column("presentation", sa.Text, nullable=True),
        sa.Column("teaching_points", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("management", postgresql.ARRAY(sa.Text), nullable=True),
        sa.Column("status", sa.String(20), server_default="done"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("case_id", "locale", name="uq_case_translation"),
    )
    op.create_index("idx_cct_case_locale", "clinical_case_translations", ["case_id", "locale"])

    # Also add FSM columns to clinical_cases if missing (already in model but may not be in DB)
    op.execute("""
        ALTER TABLE clinical_cases
        ADD COLUMN IF NOT EXISTS steps JSONB,
        ADD COLUMN IF NOT EXISTS initial_step_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS ideal_path JSONB,
        ADD COLUMN IF NOT EXISTS max_score INTEGER DEFAULT 100,
        ADD COLUMN IF NOT EXISTS specialty VARCHAR(100),
        ADD COLUMN IF NOT EXISTS difficulty VARCHAR(20) DEFAULT 'medium'
    """)


def downgrade():
    op.drop_table("clinical_case_translations")
