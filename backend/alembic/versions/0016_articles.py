"""Articles — SEO public medical content

Revision ID: 0016
Revises: 0015_lesson_translations
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision = "0016"
down_revision = "0015_lesson_translations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "articles",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(300), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("body", JSONB, nullable=False),             # array of {type, content} blocks
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("subcategory", sa.String(100), nullable=True),
        sa.Column("keywords", ARRAY(sa.Text), nullable=True), # for meta keywords + internal search
        sa.Column("reading_time_minutes", sa.Integer, nullable=False, server_default="5"),
        sa.Column("schema_type", sa.String(50), nullable=False, server_default="MedicalWebPage"),
        # schema_type: MedicalWebPage | Drug | MedicalCondition | MedicalProcedure
        sa.Column("faq", JSONB, nullable=True),               # [{question, answer}, ...]
        sa.Column("sources", JSONB, nullable=True),           # [{title, url, pmid}, ...]
        sa.Column("related_module_code", sa.String(50), nullable=True),  # link to platform module
        sa.Column("og_title", sa.String(200), nullable=True),
        sa.Column("og_description", sa.String(300), nullable=True),
        sa.Column("is_published", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("generated_by", sa.String(50), nullable=True),  # claude-haiku | claude-sonnet | manual
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_articles_slug", "articles", ["slug"])
    op.create_index("ix_articles_category", "articles", ["category"])
    op.create_index("ix_articles_is_published", "articles", ["is_published"])
    op.create_index("ix_articles_published_at", "articles", ["published_at"])


def downgrade() -> None:
    op.drop_table("articles")
