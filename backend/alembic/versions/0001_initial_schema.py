"""Initial schema — all tables (aligned with SQLAlchemy models)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _updated_at_trigger(table: str) -> None:
    op.execute(f"""
        CREATE TRIGGER trg_{table}_updated_at
        BEFORE UPDATE ON {table}
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
    """)


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ── extensions ──────────────────────────────────────────────────────────
    conn = op.get_bind()
    for ext in ("pg_trgm", "uuid-ossp"):
        try:
            conn.execute(sa.text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
        except Exception:
            pass
    try:
        conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS vector'))
    except Exception:
        pass  # pgvector not available on all PostgreSQL versions

    # ── updated_at helper ───────────────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # ── SM-2 algorithm SQL function ──────────────────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION calculate_next_review(
            p_ease_factor FLOAT,
            p_interval    INTEGER,
            p_quality     INTEGER
        ) RETURNS TABLE(new_ease_factor FLOAT, new_interval INTEGER, next_review TIMESTAMP) AS $$
        DECLARE
            ef FLOAT   := p_ease_factor;
            iv INTEGER := p_interval;
        BEGIN
            ef := ef + (0.1 - (5 - p_quality) * (0.08 + (5 - p_quality) * 0.02));
            IF ef < 1.3 THEN ef := 1.3; END IF;

            IF p_quality < 3 THEN
                iv := 1;
            ELSIF iv = 0 THEN
                iv := 1;
            ELSIF iv = 1 THEN
                iv := 6;
            ELSE
                iv := ROUND(iv * ef);
            END IF;

            RETURN QUERY SELECT ef, iv, NOW() + (iv || ' days')::INTERVAL;
        END;
        $$ LANGUAGE plpgsql
    """)

    # ── specialties ─────────────────────────────────────────────────────────
    op.create_table(
        "specialties",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code",         sa.String(50),  nullable=False, unique=True),
        sa.Column("name",         sa.String(200), nullable=False),
        sa.Column("name_en",      sa.String(200)),
        sa.Column("icon",         sa.String(10)),
        sa.Column("description",  sa.Text),
        sa.Column("is_veterinary",sa.Boolean, server_default="false"),
        sa.Column("is_active",    sa.Boolean, server_default="true"),
        sa.Column("module_count", sa.Integer, server_default="0"),
        sa.Column("created_at",   sa.DateTime, server_default=sa.func.now()),
    )

    # ── modules ─────────────────────────────────────────────────────────────
    op.create_table(
        "modules",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code",               sa.String(50),  nullable=False, unique=True),
        sa.Column("specialty_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("specialties.id")),
        sa.Column("title",              sa.String(300), nullable=False),
        sa.Column("title_en",           sa.String(300)),
        sa.Column("description",        sa.Text),
        sa.Column("level",              sa.Integer,  server_default="1"),
        sa.Column("level_label",        sa.String(50)),
        sa.Column("module_order",       sa.Integer,  server_default="0"),
        sa.Column("duration_hours",     sa.Numeric(4, 1), server_default="0"),
        sa.Column("is_fundamental",     sa.Boolean, server_default="false"),
        sa.Column("is_veterinary",      sa.Boolean, server_default="false"),
        sa.Column("is_published",       sa.Boolean, server_default="false"),
        sa.Column("prerequisite_codes", postgresql.ARRAY(sa.String)),
        sa.Column("prerequisites",      postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("used_in",            postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("embedding",          postgresql.JSONB),   # fallback; pgvector uses vector(1536)
        sa.Column("content",            postgresql.JSONB),
        sa.Column("created_at",         sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",         sa.DateTime, server_default=sa.func.now()),
    )

    # ── lessons ─────────────────────────────────────────────────────────────
    op.create_table(
        "lessons",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_code",        sa.String(50)),
        sa.Column("title",              sa.String(300), nullable=False),
        sa.Column("lesson_order",       sa.Integer, server_default="0"),
        sa.Column("content",            postgresql.JSONB, nullable=False),
        sa.Column("embedding",          postgresql.JSONB),
        sa.Column("estimated_minutes",  sa.Integer, server_default="20"),
        sa.Column("created_at",         sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",         sa.DateTime, server_default=sa.func.now()),
    )

    # ── flashcards ──────────────────────────────────────────────────────────
    op.create_table(
        "flashcards",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question",   sa.Text, nullable=False),
        sa.Column("answer",     sa.Text, nullable=False),
        sa.Column("difficulty", sa.String(20), server_default="medium"),
        sa.Column("category",   sa.String(100)),
        sa.Column("tags",       postgresql.ARRAY(sa.String)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── mcq_questions ────────────────────────────────────────────────────────
    op.create_table(
        "mcq_questions",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question",    sa.Text, nullable=False),
        sa.Column("options",     postgresql.JSONB, nullable=False),
        sa.Column("correct",     sa.String(5), nullable=False),
        sa.Column("explanation", sa.Text),
        sa.Column("difficulty",  sa.String(20), server_default="medium"),
        sa.Column("tags",        postgresql.ARRAY(sa.String)),
        sa.Column("created_at",  sa.DateTime, server_default=sa.func.now()),
    )

    # ── clinical_cases ───────────────────────────────────────────────────────
    op.create_table(
        "clinical_cases",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("module_id",             postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",                 sa.String(300), nullable=False),
        sa.Column("specialty",             sa.String(100)),
        sa.Column("presentation",          sa.Text, nullable=False),
        sa.Column("vitals",                postgresql.JSONB),
        sa.Column("diagnosis",             sa.String(300)),
        sa.Column("differential_diagnosis",postgresql.ARRAY(sa.String)),
        sa.Column("management",            postgresql.ARRAY(sa.String)),
        sa.Column("teaching_points",       postgresql.ARRAY(sa.String)),
        sa.Column("content",               postgresql.JSONB),
        sa.Column("difficulty",            sa.String(20), server_default="medium"),
        sa.Column("created_at",            sa.DateTime, server_default=sa.func.now()),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email",                sa.String(255), nullable=False, unique=True),
        sa.Column("email_hash",           sa.String(64)),
        sa.Column("password_hash",        sa.String(255)),
        sa.Column("role",                 sa.String(50),  server_default="student"),
        sa.Column("first_name",           sa.String(100)),
        sa.Column("last_name",            sa.String(100)),
        sa.Column("avatar_url",           sa.Text),
        sa.Column("subscription_tier",    sa.String(50),  server_default="free"),
        sa.Column("subscription_expires", sa.DateTime),
        sa.Column("stripe_customer_id",   sa.String(100)),
        sa.Column("profile_data",         postgresql.JSONB, server_default="{}"),
        sa.Column("preferences",          postgresql.JSONB, server_default="{}"),
        sa.Column("ai_requests_today",    sa.Integer, server_default="0"),
        sa.Column("ai_requests_reset_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("xp",                   sa.Integer, server_default="0"),
        sa.Column("level",                sa.Integer, server_default="1"),
        sa.Column("streak_days",          sa.Integer, server_default="0"),
        sa.Column("last_active_date",     sa.DateTime),
        sa.Column("onboarding_completed", sa.Boolean, server_default="false"),
        sa.Column("is_active",            sa.Boolean, server_default="true"),
        sa.Column("is_verified",          sa.Boolean, server_default="false"),
        sa.Column("oauth_provider",       sa.String(50)),
        sa.Column("oauth_id",             sa.String(200)),
        sa.Column("created_at",           sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime, server_default=sa.func.now()),
    )

    # ── refresh_tokens ───────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("is_revoked", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── user_progress ────────────────────────────────────────────────────────
    op.create_table(
        "user_progress",
        sa.Column("user_id",             postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("module_id",           postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lessons_completed",   postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("flashcards_mastered", postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column("mcq_score",           sa.Numeric(5, 2), server_default="0"),
        sa.Column("mcq_attempts",        sa.Integer, server_default="0"),
        sa.Column("completion_percent",  sa.Numeric(5, 2), server_default="0"),
        sa.Column("next_review_at",      sa.DateTime),
        sa.Column("ease_factor",         sa.Numeric(4, 2), server_default="2.5"),
        sa.Column("interval_days",       sa.Integer, server_default="1"),
        sa.Column("started_at",          sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_activity_at",    sa.DateTime, server_default=sa.func.now()),
    )

    # ── flashcard_reviews ────────────────────────────────────────────────────
    op.create_table(
        "flashcard_reviews",
        sa.Column("user_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("flashcard_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("flashcards.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ease_factor",    sa.Numeric(4, 2), server_default="2.5"),
        sa.Column("interval_days",  sa.Integer, server_default="1"),
        sa.Column("repetitions",    sa.Integer, server_default="0"),
        sa.Column("next_review_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_reviewed_at", sa.DateTime),
        sa.Column("last_quality",   sa.Integer),
    )

    # ── ai_conversations ─────────────────────────────────────────────────────
    op.create_table(
        "ai_conversations",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",            sa.String(200)),
        sa.Column("specialty",        sa.String(100)),
        sa.Column("mode",             sa.String(50),  server_default="tutor"),
        sa.Column("model_used",       sa.String(100)),
        sa.Column("cached_responses", sa.Integer, server_default="0"),
        sa.Column("total_tokens",     sa.Integer, server_default="0"),
        sa.Column("created_at",       sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime, server_default=sa.func.now()),
    )

    # ── ai_conversation_messages ─────────────────────────────────────────────
    op.create_table(
        "ai_conversation_messages",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role",            sa.String(20),  nullable=False),
        sa.Column("content",         sa.Text,        nullable=False),
        sa.Column("pubmed_refs",     postgresql.JSONB),
        sa.Column("model_used",      sa.String(100)),
        sa.Column("tokens_used",     sa.Integer, server_default="0"),
        sa.Column("from_cache",      sa.Boolean, server_default="false"),
        sa.Column("feedback",        sa.Integer),
        sa.Column("created_at",      sa.DateTime, server_default=sa.func.now()),
    )

    # ── drugs ────────────────────────────────────────────────────────────────
    op.create_table(
        "drugs",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name",                sa.String(200), nullable=False),
        sa.Column("generic_name",        sa.String(200)),
        sa.Column("drug_class",          sa.String(100)),
        sa.Column("mechanism",           sa.Text),
        sa.Column("indications",         postgresql.ARRAY(sa.String)),
        sa.Column("contraindications",   postgresql.ARRAY(sa.String)),
        sa.Column("dosing",              postgresql.JSONB),
        sa.Column("adverse_effects",     postgresql.JSONB),
        sa.Column("interactions",        postgresql.ARRAY(sa.String)),
        sa.Column("monitoring",          postgresql.ARRAY(sa.String)),
        sa.Column("black_box_warning",   sa.Text),
        sa.Column("is_high_yield",       sa.Boolean, server_default="false"),
        sa.Column("is_nti",              sa.Boolean, server_default="false"),
        sa.Column("is_veterinary",       sa.Boolean, server_default="false"),
        sa.Column("content",             postgresql.JSONB),
        sa.Column("created_at",          sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",          sa.DateTime, server_default=sa.func.now()),
    )

    # ── user_notes ───────────────────────────────────────────────────────────
    op.create_table(
        "user_notes",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("lessons.id")),
        sa.Column("module_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id")),
        sa.Column("content",    sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # ── user_bookmarks ───────────────────────────────────────────────────────
    op.create_table(
        "user_bookmarks",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_id",   postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at",   sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "content_type", "content_id", name="uq_user_bookmark"),
    )

    # ── user_achievements ────────────────────────────────────────────────────
    op.create_table(
        "user_achievements",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_code", sa.String(100), nullable=False),
        sa.Column("unlocked_at",      sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "achievement_code", name="uq_user_achievement"),
    )

    # ── stripe_events ────────────────────────────────────────────────────────
    op.create_table(
        "stripe_events",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("stripe_event_id", sa.String(200), nullable=False, unique=True),
        sa.Column("event_type",      sa.String(100), nullable=False),
        sa.Column("user_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("data",            postgresql.JSONB),
        sa.Column("processed",       sa.Boolean, server_default="false"),
        sa.Column("created_at",      sa.DateTime, server_default=sa.func.now()),
    )

    # ── user_consents (GDPR) ─────────────────────────────────────────────────
    op.create_table(
        "user_consents",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(100), nullable=False),
        sa.Column("version",      sa.String(50)),
        sa.Column("given_at",     sa.DateTime, server_default=sa.func.now()),
        sa.Column("ip_address",   sa.String(45)),
        sa.UniqueConstraint("user_id", "consent_type", name="uq_user_consent"),
    )

    # ── audit_log (GDPR) ─────────────────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id",            postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action",        sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100)),
        sa.Column("resource_id",   postgresql.UUID(as_uuid=True)),
        sa.Column("ip_address",    sa.String(45)),
        sa.Column("user_agent",    sa.Text),
        sa.Column("created_at",    sa.DateTime, server_default=sa.func.now()),
    )

    # ── courses ──────────────────────────────────────────────────────────────
    op.create_table(
        "courses",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("teacher_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",       sa.String(300), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("invite_code", sa.String(16), nullable=False, unique=True),
        sa.Column("is_active",   sa.Boolean, server_default="true"),
        sa.Column("starts_at",   sa.DateTime),
        sa.Column("ends_at",     sa.DateTime),
        sa.Column("created_at",  sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime, server_default=sa.func.now()),
    )

    # ── course_modules ───────────────────────────────────────────────────────
    op.create_table(
        "course_modules",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_order", sa.Integer, server_default="0"),
        sa.Column("added_at",     sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("course_id", "module_id", name="uq_course_module"),
    )

    # ── course_enrollments ───────────────────────────────────────────────────
    op.create_table(
        "course_enrollments",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("status",      sa.String(20), server_default="active"),
        sa.UniqueConstraint("course_id", "student_id", name="uq_course_enrollment"),
    )

    # ── course_assignments ───────────────────────────────────────────────────
    op.create_table(
        "course_assignments",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("course_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",       sa.String(300)),
        sa.Column("description", sa.Text),
        sa.Column("due_date",    sa.DateTime),
        sa.Column("max_score",   sa.Integer, server_default="100"),
        sa.Column("created_at",  sa.DateTime, server_default=sa.func.now()),
    )

    # ── indexes ──────────────────────────────────────────────────────────────
    op.create_index("ix_modules_specialty_id",    "modules",           ["specialty_id"])
    op.create_index("ix_modules_code",            "modules",           ["code"])
    op.create_index("ix_modules_is_published",    "modules",           ["is_published"])
    op.create_index("ix_lessons_module_id",       "lessons",           ["module_id"])
    op.create_index("ix_flashcards_module_id",    "flashcards",        ["module_id"])
    op.create_index("ix_mcq_module_id",           "mcq_questions",     ["module_id"])
    op.create_index("ix_cases_module_id",         "clinical_cases",    ["module_id"])
    op.create_index("ix_users_email",             "users",             ["email"])
    op.create_index("ix_users_email_hash",        "users",             ["email_hash"])
    op.create_index("ix_user_progress_user",      "user_progress",     ["user_id"])
    op.create_index("ix_fc_reviews_next",         "flashcard_reviews", ["next_review_at"])
    op.create_index("ix_ai_conv_user",            "ai_conversations",  ["user_id"])
    op.create_index("ix_ai_msg_conv",             "ai_conversation_messages", ["conversation_id"])
    op.create_index("ix_refresh_tokens_user",     "refresh_tokens",    ["user_id"])
    op.create_index("ix_user_notes_user",         "user_notes",        ["user_id"])
    op.create_index("ix_user_bookmarks_user",     "user_bookmarks",    ["user_id"])
    op.create_index("ix_user_achievements_user",  "user_achievements", ["user_id"])

    # ── updated_at triggers ──────────────────────────────────────────────────
    for table in ["modules", "lessons", "users", "ai_conversations", "drugs", "user_notes", "courses"]:
        _updated_at_trigger(table)

    # ── seed specialties ─────────────────────────────────────────────────────
    op.execute("""
        INSERT INTO specialties (id, code, name, is_veterinary, is_active) VALUES
        (gen_random_uuid(), 'cardiology',     'Cardiology',              false, true),
        (gen_random_uuid(), 'neurology',      'Neurology',               false, true),
        (gen_random_uuid(), 'surgery',        'Surgery',                 false, true),
        (gen_random_uuid(), 'obstetrics',     'Obstetrics & Gynecology', false, true),
        (gen_random_uuid(), 'pediatrics',     'Pediatrics',              false, true),
        (gen_random_uuid(), 'therapy',        'Internal Medicine',       false, true),
        (gen_random_uuid(), 'pharmacology',   'Pharmacology',            false, true),
        (gen_random_uuid(), 'lab_diagnostics','Laboratory Diagnostics',  false, true),
        (gen_random_uuid(), 'respiratory',    'Respiratory Medicine',    false, true),
        (gen_random_uuid(), 'veterinary',     'Veterinary',              true,  true)
        ON CONFLICT (code) DO NOTHING
    """)


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    tables = [
        "course_assignments", "course_enrollments", "course_modules", "courses",
        "audit_log", "user_consents", "stripe_events",
        "user_achievements", "user_bookmarks", "user_notes", "drugs",
        "ai_conversation_messages", "ai_conversations",
        "flashcard_reviews", "user_progress",
        "refresh_tokens", "users",
        "clinical_cases", "mcq_questions", "flashcards", "lessons",
        "modules", "specialties",
    ]
    for table in tables:
        op.drop_table(table)

    op.execute("DROP FUNCTION IF EXISTS calculate_next_review")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
