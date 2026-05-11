"""Course discovery — is_public, enrollment_type, access requests."""
from alembic import op
import sqlalchemy as sa

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    # Extend courses table
    op.add_column("courses", sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("courses", sa.Column("enrollment_type", sa.String(20), nullable=False, server_default="invite"))
    op.add_column("courses", sa.Column("difficulty", sa.String(20), nullable=True))
    op.add_column("courses", sa.Column("specialty_tag", sa.String(100), nullable=True))
    op.add_column("courses", sa.Column("thumbnail_emoji", sa.String(10), nullable=True))
    op.add_column("courses", sa.Column("estimated_hours", sa.Numeric(5, 1), nullable=True))

    # Access requests table
    op.create_table(
        "course_access_requests",
        sa.Column("id", sa.UUID(), nullable=False, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("course_id", sa.UUID(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("course_id", "user_id", name="uq_course_access_request"),
    )
    op.create_index("idx_course_access_requests_user", "course_access_requests", ["user_id"])
    op.create_index("idx_course_access_requests_course", "course_access_requests", ["course_id"])
    op.create_index("idx_courses_public", "courses", ["is_public", "is_active"])


def downgrade():
    op.drop_index("idx_courses_public", "courses")
    op.drop_table("course_access_requests")
    op.drop_column("courses", "estimated_hours")
    op.drop_column("courses", "thumbnail_emoji")
    op.drop_column("courses", "specialty_tag")
    op.drop_column("courses", "difficulty")
    op.drop_column("courses", "enrollment_type")
    op.drop_column("courses", "is_public")
