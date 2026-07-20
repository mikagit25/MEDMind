"""exam registry — ExamDefinition table + exam_slugs on mcq_questions

Revision ID: o1p2q3r4s5t6
Revises: n0o1p2q3r4s5
Create Date: 2026-07-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "o1p2q3r4s5t6"
down_revision = "n0o1p2q3r4s5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_definitions",
        sa.Column("slug",                 sa.String(60),  primary_key=True),
        sa.Column("name",                 sa.String(200), nullable=False),
        sa.Column("country",              sa.String(100), nullable=False),
        sa.Column("regulatory_body",      sa.String(200), nullable=False),
        sa.Column("question_count",       sa.Integer(),   nullable=False),
        sa.Column("duration_min",         sa.Integer(),   nullable=False),
        sa.Column("pass_threshold",       sa.Integer(),   nullable=False),
        sa.Column("passing_score_label",  sa.String(30),  nullable=False, server_default="65%"),
        sa.Column("blueprint_source",     sa.String(500), nullable=False),
        sa.Column("blueprint_verified_at",sa.String(20),  nullable=True),
        sa.Column("status",               sa.String(20),  nullable=False, server_default="draft"),
        sa.Column("locale",               sa.String(10),  nullable=False, server_default="en"),
        sa.Column("family",               sa.String(50),  nullable=False, server_default="gulf"),
        sa.Column("options_per_question", sa.Integer(),   nullable=False, server_default="4"),
        sa.Column("categories",           postgresql.JSONB(), nullable=True),
        sa.Column("exam_date_fixed",      sa.String(20),  nullable=True),
        sa.Column("disclaimer",           sa.Text(),      nullable=True),
        sa.Column("created_at",           sa.DateTime(),  nullable=True),
        sa.Column("updated_at",           sa.DateTime(),  nullable=True),
    )

    # exam_slugs on mcq_questions — GIN index for fast contains queries
    op.add_column(
        "mcq_questions",
        sa.Column("exam_slugs", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "ix_mcq_questions_exam_slugs",
        "mcq_questions",
        ["exam_slugs"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_mcq_questions_exam_slugs", table_name="mcq_questions")
    op.drop_column("mcq_questions", "exam_slugs")
    op.drop_table("exam_definitions")
