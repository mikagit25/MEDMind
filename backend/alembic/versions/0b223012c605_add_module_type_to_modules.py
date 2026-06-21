"""add module_type to modules

Revision ID: 0b223012c605
Revises: 0004_add_news_verification
Create Date: 2026-06-20 16:39:16.369729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0b223012c605'
down_revision: Union[str, None] = '0004_add_news_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "modules",
        sa.Column(
            "module_type",
            sa.String(30),
            nullable=False,
            server_default="specialty_module",
        ),
    )


def downgrade() -> None:
    op.drop_column("modules", "module_type")
