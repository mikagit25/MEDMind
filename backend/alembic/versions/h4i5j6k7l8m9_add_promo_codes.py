"""add_promo_codes

Revision ID: h4i5j6k7l8m9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-18 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id",             sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("code",           sa.String(50),  unique=True, nullable=False),
        sa.Column("description",    sa.String(255), nullable=True),
        sa.Column("discount_type",  sa.String(20),  nullable=False, server_default="trial"),
        sa.Column("discount_value", sa.Float(),     nullable=True),
        sa.Column("trial_tier",     sa.String(20),  nullable=True),
        sa.Column("trial_days",     sa.Integer(),   nullable=True),
        sa.Column("max_uses",       sa.Integer(),   nullable=True),
        sa.Column("used_count",     sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("one_per_user",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("is_active",      sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("expires_at",     sa.DateTime(),  nullable=True),
        sa.Column("created_at",     sa.DateTime(),  nullable=False),
        sa.Column("created_by_id",  sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"])

    op.create_table(
        "promo_code_uses",
        sa.Column("id",            sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("code_id",       sa.UUID(as_uuid=True), sa.ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id",       sa.UUID(as_uuid=True), sa.ForeignKey("users.id",       ondelete="CASCADE"), nullable=False),
        sa.Column("used_at",       sa.DateTime(), nullable=False),
        sa.Column("granted_tier",  sa.String(20), nullable=True),
        sa.Column("granted_until", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_promo_uses_user", "promo_code_uses", ["user_id"])
    op.create_index("ix_promo_uses_code", "promo_code_uses", ["code_id"])


def downgrade() -> None:
    op.drop_index("ix_promo_uses_code", table_name="promo_code_uses")
    op.drop_index("ix_promo_uses_user", table_name="promo_code_uses")
    op.drop_table("promo_code_uses")
    op.drop_index("ix_promo_codes_code", table_name="promo_codes")
    op.drop_table("promo_codes")
