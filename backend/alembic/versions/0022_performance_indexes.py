"""Performance indexes — quiz_attempts, notifications, medical_images search.

Revision ID: 0022_performance_indexes
Revises: 0021_article_verification
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # lesson_completions — leaderboard / user stats queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_lesson_completions_user_created
        ON lesson_completions (user_id, completed_at DESC)
    """)

    # notifications — per-user unread queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
        ON notifications (user_id, is_read, created_at DESC)
    """)

    # medical_images — full-text search on title + description
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_medical_images_fts
        ON medical_images
        USING gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'')))
    """)

    # medical_images — specialty+modality composite for veterinary page
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_medical_images_specialty_modality
        ON medical_images (specialty, modality)
        WHERE is_active = true
    """)

    # article_translations — locale + status for body translation queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_article_translations_locale_status
        ON article_translations (locale, status)
    """)

    # user_progress — composite for complete_lesson lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_progress_user_module
        ON user_progress (user_id, module_id)
    """)

    # flashcard_reviews — user spaced-repetition stats
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_flashcard_reviews_user
        ON flashcard_reviews (user_id, last_reviewed_at DESC)
    """)

    # clinical_case_sessions — user history
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_case_sessions_user_started
        ON clinical_case_sessions (user_id, started_at DESC)
    """)

    # ai_conversations — user conversation list
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ai_conversations_user_created
        ON ai_conversations (user_id, created_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_lesson_completions_user_created")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_unread")
    op.execute("DROP INDEX IF EXISTS idx_medical_images_fts")
    op.execute("DROP INDEX IF EXISTS idx_medical_images_specialty_modality")
    op.execute("DROP INDEX IF EXISTS idx_article_translations_locale_status")
    op.execute("DROP INDEX IF EXISTS idx_user_progress_user_module")
    op.execute("DROP INDEX IF EXISTS idx_flashcard_reviews_user")
