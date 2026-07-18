"""add_dose_calc_stats

Revision ID: f3a4b5c6d7e8
Revises: 2b5112c7bd74
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "0043_nclex_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dose_calc_stats",
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category", sa.String(50), primary_key=True),
        sa.Column("total_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_correct",  sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak",    sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_dose_calc_stats_user", "dose_calc_stats", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_dose_calc_stats_user", table_name="dose_calc_stats")
    op.drop_table("dose_calc_stats")
