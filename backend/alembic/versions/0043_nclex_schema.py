"""NCLEX full schema: tagging + NGN types + persistent exam sessions

Revision ID: 0043_nclex_schema
Revises: 0042_nurse_vertical
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0043_nclex_schema"
down_revision = "0042_nurse_vertical"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. NCLEX tagging columns on mcq_questions ─────────────────────────
    op.add_column("mcq_questions",
        sa.Column("nclex_client_needs", sa.String(60), nullable=True))
    op.add_column("mcq_questions",
        sa.Column("cjmm_skill", sa.String(60), nullable=True))
    # null = standard question; "bowtie"|"matrix"|"trend"|"cloze" = NGN
    op.add_column("mcq_questions",
        sa.Column("ngn_type", sa.String(20), nullable=True))
    # bow-tie payload:
    # {condition_options:[str], action_options:[str], parameter_options:[str],
    #  correct_condition:str, correct_actions:[str,str], correct_parameters:[str,str]}
    op.add_column("mcq_questions",
        sa.Column("bowtie_data", postgresql.JSONB, nullable=True))
    # matrix/grid payload:
    # {rows:[str], columns:[str], correct_cells:[[bool]], partial_credit:bool}
    op.add_column("mcq_questions",
        sa.Column("matrix_data", postgresql.JSONB, nullable=True))

    op.create_index("ix_mcq_nclex_client_needs", "mcq_questions",
                    ["nclex_client_needs"], postgresql_where=sa.text("nclex_client_needs IS NOT NULL"))
    op.create_index("ix_mcq_cjmm_skill", "mcq_questions",
                    ["cjmm_skill"], postgresql_where=sa.text("cjmm_skill IS NOT NULL"))
    op.create_index("ix_mcq_ngn_type", "mcq_questions",
                    ["ngn_type"], postgresql_where=sa.text("ngn_type IS NOT NULL"))

    # ── 2. Persistent exam sessions table ────────────────────────────────
    op.create_table(
        "exam_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode_id", sa.String(50), nullable=False),
        sa.Column("mode_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        # ordered list of question IDs
        sa.Column("question_ids", postgresql.JSONB, nullable=False, server_default="[]"),
        # question_index -> {selected_option, selected_options, ordered_options, numeric_value}
        sa.Column("answers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("total_questions", sa.Integer, nullable=False),
        sa.Column("duration_min", sa.Integer, nullable=False),
        sa.Column("starts_at", sa.DateTime, nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("ends_at", sa.DateTime, nullable=False),
        # filled on submit
        sa.Column("correct", sa.Integer, nullable=True),
        sa.Column("wrong", sa.Integer, nullable=True),
        sa.Column("score_pct", sa.Float, nullable=True),
        sa.Column("passed", sa.Boolean, nullable=True),
        sa.Column("time_taken_min", sa.Float, nullable=True),
        # per-question results [{index, correct, score_delta, cjmm_skill, nclex_client_needs}]
        sa.Column("per_question", postgresql.JSONB, nullable=True),
        # CAT difficulty progression
        sa.Column("current_difficulty", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("cat_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_exam_sessions_user_id", "exam_sessions", ["user_id"])
    op.create_index("ix_exam_sessions_status", "exam_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_exam_sessions_status", table_name="exam_sessions")
    op.drop_index("ix_exam_sessions_user_id", table_name="exam_sessions")
    op.drop_table("exam_sessions")

    op.drop_index("ix_mcq_ngn_type", table_name="mcq_questions")
    op.drop_index("ix_mcq_cjmm_skill", table_name="mcq_questions")
    op.drop_index("ix_mcq_nclex_client_needs", table_name="mcq_questions")
    op.drop_column("mcq_questions", "matrix_data")
    op.drop_column("mcq_questions", "bowtie_data")
    op.drop_column("mcq_questions", "ngn_type")
    op.drop_column("mcq_questions", "cjmm_skill")
    op.drop_column("mcq_questions", "nclex_client_needs")
