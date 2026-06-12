"""Background scheduler — daily tasks for streak updates, XP resets, and notifications."""
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, func, text

from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def _daily_streak_update():
    """
    Run every day at midnight UTC:
    - Reset streak to 0 for users who didn't study yesterday
    - This is idempotent — safe to run multiple times
    """
    try:
        async with AsyncSessionLocal() as db:
            # Reset streak for users whose last activity was >1 day ago
            result = await db.execute(
                text("""
                    UPDATE users
                    SET streak_days = 0
                    WHERE is_active = true
                      AND streak_days > 0
                      AND (
                        last_active_date IS NULL
                        OR last_active_date < NOW() - INTERVAL '1 day 6 hours'
                      )
                """)
            )
            await db.commit()
            rows = result.rowcount
            if rows:
                logger.info("Daily streak reset: %d users lost their streak", rows)
    except Exception as e:
        logger.error("Daily streak update failed: %s", e)


async def _weekly_stats_snapshot():
    """
    Run every Monday at 2am UTC:
    - Log aggregate stats for monitoring
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (WHERE is_active) AS active_users,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') AS new_users_7d,
                        AVG(xp) AS avg_xp,
                        MAX(streak_days) AS max_streak
                    FROM users
                """)
            )
            row = result.fetchone()
            if row:
                logger.info(
                    "Weekly stats: active=%s new_7d=%s avg_xp=%.0f max_streak=%s",
                    row[0], row[1], row[2] or 0, row[3],
                )
    except Exception as e:
        logger.error("Weekly stats snapshot failed: %s", e)


async def _daily_flashcard_reminders():
    """
    Run daily at 09:00 UTC — notify users who have flashcards due but haven't studied today.
    Creates one notification per qualifying user.
    """
    from app.models.models import User, FlashcardReview, Notification
    from app.services.notification_service import notify_flashcards_due

    try:
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Find users with due flashcards who haven't been active today
            rows = await db.execute(
                select(
                    FlashcardReview.user_id,
                    func.count(FlashcardReview.flashcard_id).label("due_count"),
                )
                .join(User, User.id == FlashcardReview.user_id)
                .where(
                    FlashcardReview.next_review_at <= now,
                    User.is_active == True,
                    # Not already active today
                    (User.last_active_date == None) | (User.last_active_date < today_start),
                )
                .group_by(FlashcardReview.user_id)
                .having(func.count(FlashcardReview.flashcard_id) > 0)
            )

            notified = 0
            for user_id, due_count in rows.all():
                # Skip if already sent a flashcard notification today
                existing = await db.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.type == "flashcard_due",
                        Notification.created_at >= today_start,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                await notify_flashcards_due(db, user_id, due_count)
                notified += 1

            if notified:
                await db.commit()
                logger.info("Flashcard reminders sent to %d users", notified)
    except Exception as e:
        logger.error("Daily flashcard reminders failed: %s", e)


async def _nightly_plan_refresh():
    """
    Run nightly at 03:00 UTC — invalidate cached study plans for active users
    so their next request gets a freshly computed adaptive plan.
    """
    from app.core.redis_client import get_redis
    try:
        redis = await get_redis()
        # Scan for all study_plan:* keys and delete them
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="study_plan:*", count=100)
            if keys:
                await redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        if deleted:
            logger.info("Nightly plan refresh: invalidated %d cached study plans", deleted)
    except Exception as e:
        logger.error("Nightly plan refresh failed: %s", e)


async def _evening_streak_reminder():
    """
    Run daily at 20:00 UTC — warn users with an active streak who haven't
    studied yet today, giving them time to maintain it before midnight reset.
    """
    from app.models.models import User, Notification
    try:
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

            # Users with streak > 0 who haven't been active today
            at_risk = await db.execute(
                select(User).where(
                    User.is_active == True,
                    User.streak_days > 0,
                    (User.last_active_date == None) | (User.last_active_date < today_start),
                )
            )
            users_at_risk = at_risk.scalars().all()

            notified = 0
            for u in users_at_risk:
                # Avoid duplicate evening notifications
                existing = await db.execute(
                    select(Notification).where(
                        Notification.user_id == u.id,
                        Notification.type == "streak_reminder",
                        Notification.created_at >= today_start,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                db.add(Notification(
                    user_id=u.id,
                    type="streak_reminder",
                    title="Don't lose your streak!",
                    body=f"You have a {u.streak_days}-day streak — study something today to keep it going.",
                ))
                notified += 1

            if notified:
                await db.commit()
                logger.info("Evening streak reminders sent to %d users", notified)
    except Exception as e:
        logger.error("Evening streak reminder failed: %s", e)


async def _news_pipeline_job():
    """Run every 6 hours — fetch and translate new medical news."""
    try:
        from app.services.news_pipeline import run_news_pipeline
        count = await run_news_pipeline(days_back=2)
        logger.info("News pipeline job done: %d new articles", count)
    except Exception as e:
        logger.error("News pipeline job failed: %s", e)


async def _weekly_reviewer_digest():
    """Send weekly digest to all users with role='reviewer'.
    Reports: queue depth (passed articles awaiting review) + unresolved content feedback.
    """
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal
    from app.models.models import Article, ContentFeedback, User
    from app.services.email_service import send_reviewer_digest

    try:
        async with AsyncSessionLocal() as db:
            # Count articles in the queue
            queue_count = await db.scalar(
                select(func.count(Article.id)).where(
                    Article.is_published == True,
                    Article.review_status == "published",
                    Article.verification_status == "passed",
                )
            ) or 0

            # Count unresolved feedback
            feedback_count = await db.scalar(
                select(func.count(ContentFeedback.id)).where(
                    ContentFeedback.resolved == False
                )
            ) or 0

            # Fetch all active reviewers
            reviewers = (await db.execute(
                select(User).where(User.role == "reviewer", User.is_active == True)
            )).scalars().all()

            if not reviewers:
                logger.info("Reviewer digest: no active reviewers to notify")
                return

            for reviewer in reviewers:
                try:
                    await send_reviewer_digest(
                        to_email=reviewer.email,
                        reviewer_name=f"{reviewer.first_name or ''} {reviewer.last_name or ''}".strip() or reviewer.email,
                        queue_count=queue_count,
                        feedback_count=feedback_count,
                    )
                except Exception as e:
                    logger.warning("Reviewer digest email failed for %s: %s", reviewer.email, e)

            logger.info(
                "Reviewer digest sent to %d reviewers (queue=%d, feedback=%d)",
                len(reviewers), queue_count, feedback_count,
            )
    except Exception as e:
        logger.error("Weekly reviewer digest job failed: %s", e)


def start_scheduler():
    """Start the background scheduler. Call from lifespan startup."""
    if scheduler.running:
        return

    # Daily at midnight UTC — streak reset
    scheduler.add_job(
        _daily_streak_update,
        trigger=CronTrigger(hour=0, minute=5, timezone="UTC"),
        id="daily_streak_reset",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily 09:00 UTC — flashcard reminders
    scheduler.add_job(
        _daily_flashcard_reminders,
        trigger=CronTrigger(hour=9, minute=0, timezone="UTC"),
        id="daily_flashcard_reminders",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly Monday 02:00 UTC — stats snapshot
    scheduler.add_job(
        _weekly_stats_snapshot,
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0, timezone="UTC"),
        id="weekly_stats",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Nightly 03:00 UTC — invalidate study plan caches so plans refresh
    scheduler.add_job(
        _nightly_plan_refresh,
        trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="nightly_plan_refresh",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily 20:00 UTC — evening streak reminders
    scheduler.add_job(
        _evening_streak_reminder,
        trigger=CronTrigger(hour=20, minute=0, timezone="UTC"),
        id="evening_streak_reminder",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Every 6 hours — fetch new medical news from PubMed, WHO, medRxiv
    scheduler.add_job(
        _news_pipeline_job,
        trigger=CronTrigger(hour="*/6", minute=30, timezone="UTC"),
        id="news_pipeline",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly Monday 08:00 UTC — reviewer digest email
    scheduler.add_job(
        _weekly_reviewer_digest,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="UTC"),
        id="weekly_reviewer_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info("Background scheduler started (daily streak reset, weekly stats, news pipeline)")


def stop_scheduler():
    """Stop the scheduler. Call from lifespan shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
