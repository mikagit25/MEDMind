"""add composite indexes on student_memories for hybrid search

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-15
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_student_memories_user_specialty",
        "student_memories",
        ["user_id", "specialty", "deprecated"],
    )
    op.create_index(
        "ix_student_memories_user_importance",
        "student_memories",
        ["user_id", "importance_score", "deprecated"],
    )
    op.create_index(
        "ix_student_memories_user_type",
        "student_memories",
        ["user_id", "memory_type"],
    )


def downgrade():
    op.drop_index("ix_student_memories_user_specialty", table_name="student_memories")
    op.drop_index("ix_student_memories_user_importance", table_name="student_memories")
    op.drop_index("ix_student_memories_user_type", table_name="student_memories")
