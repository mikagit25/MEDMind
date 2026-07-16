"""0042 — Nurse vertical: nursing specialty + is_nursing module flag + NCLEX question types

Revision ID: 0042_nurse_vertical
Revises: 0041_certificates
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0042_nurse_vertical"
down_revision = "0041_certificates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add nursing specialty
    op.execute("""
        INSERT INTO specialties (id, code, name, module_count, is_veterinary)
        VALUES (gen_random_uuid(), 'nursing', 'Сестринское дело', 0, false)
        ON CONFLICT (code) DO NOTHING
    """)

    # 2. Add is_nursing flag to modules
    op.add_column("modules", sa.Column("is_nursing", sa.Boolean(), nullable=False, server_default="false"))

    # 3. Extend mcq_questions with NCLEX-style question types
    op.add_column("mcq_questions", sa.Column(
        "question_type", sa.String(20), nullable=False, server_default="mcq"
    ))
    # SATA: list of correct option keys, e.g. ["A", "C", "D"]
    op.add_column("mcq_questions", sa.Column(
        "correct_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True
    ))
    # ordered: correct sequence of option keys, e.g. ["B", "D", "A", "C"]
    op.add_column("mcq_questions", sa.Column(
        "correct_order", postgresql.JSONB(astext_type=sa.Text()), nullable=True
    ))
    # calculation: exact numeric answer
    op.add_column("mcq_questions", sa.Column("numeric_answer", sa.Float(), nullable=True))
    op.add_column("mcq_questions", sa.Column(
        "numeric_tolerance", sa.Float(), nullable=False, server_default="0.01"
    ))
    op.add_column("mcq_questions", sa.Column("numeric_unit", sa.String(50), nullable=True))

    # 4. partial_scoring flag for SATA (false = all-or-nothing as per NCLEX default)
    op.add_column("mcq_questions", sa.Column(
        "partial_scoring", sa.Boolean(), nullable=False, server_default="false"
    ))


def downgrade() -> None:
    op.drop_column("mcq_questions", "partial_scoring")
    op.drop_column("mcq_questions", "numeric_unit")
    op.drop_column("mcq_questions", "numeric_tolerance")
    op.drop_column("mcq_questions", "numeric_answer")
    op.drop_column("mcq_questions", "correct_order")
    op.drop_column("mcq_questions", "correct_answers")
    op.drop_column("mcq_questions", "question_type")
    op.drop_column("modules", "is_nursing")
    op.execute("DELETE FROM specialties WHERE code = 'nursing'")
