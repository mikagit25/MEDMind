"""Clinical algorithms table for Point-of-Care mode (V5 Phase 3).

Revision ID: 0038_clinical_algorithms
Revises: 0037_analytics_events
Create Date: 2026-07-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0038_clinical_algorithms"
down_revision = "0037_analytics_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.create_table(
        "clinical_algorithms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("specialty", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("steps", JSONB, nullable=False),   # [{id, type, text, children, note}]
        sa.Column("tags", sa.Text, nullable=True),    # comma-separated
        sa.Column("source", sa.Text, nullable=True),  # guideline reference
        sa.Column("is_veterinary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("verification_status", sa.String(30), nullable=False, server_default="passed"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_algo_specialty", "clinical_algorithms", ["specialty"])
    op.create_index("ix_algo_vet", "clinical_algorithms", ["is_veterinary"])


def downgrade() -> None:
    op.drop_index("ix_algo_vet", "clinical_algorithms")
    op.drop_index("ix_algo_specialty", "clinical_algorithms")
    op.drop_table("clinical_algorithms")
