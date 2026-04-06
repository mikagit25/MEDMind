"""Background scheduler — daily tasks for streak updates and XP resets."""
import logging
from datetime import datetime, date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

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

    # Weekly Monday 02:00 UTC — stats snapshot
    scheduler.add_job(
        _weekly_stats_snapshot,
        trigger=CronTrigger(day_of_week="mon", hour=2, minute=0, timezone="UTC"),
        id="weekly_stats",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.start()
    logger.info("Background scheduler started (daily streak reset, weekly stats)")


def stop_scheduler():
    """Stop the scheduler. Call from lifespan shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
