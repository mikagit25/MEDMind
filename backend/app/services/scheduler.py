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


async def _tg_daily_checkin_job():
    """Run every hour — send daily check-in to opted-in Telegram users whose time matches."""
    from app.core.redis_client import get_redis
    from app.api.v1.routes.telegram import send_checkin_message
    import json
    from datetime import datetime, timezone

    try:
        redis     = await get_redis()
        now_hour  = datetime.now(timezone.utc).strftime("%H")
        cursor    = 0
        sent      = 0
        while True:
            cursor, keys = await redis.scan(cursor, match="tg_checkin:*", count=200)
            for key in keys:
                raw = await redis.get(key)
                if not raw:
                    continue
                data      = json.loads(raw)
                ci_hour   = data.get("time", "08:00").split(":")[0].zfill(2)
                if ci_hour != now_hour:
                    continue
                chat_id   = int(key.decode().split(":")[-1])
                lang      = data.get("lang", "en")
                # Avoid double-sending (check sent-flag with 1h TTL)
                sent_key  = f"tg_ci_sent:{chat_id}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
                if await redis.exists(sent_key):
                    continue
                try:
                    await send_checkin_message(chat_id, lang)
                    await redis.set(sent_key, "1", ex=3600 * 25)
                    sent += 1
                except Exception as e:
                    logger.warning("TG check-in send error for %s: %s", chat_id, e)
            if cursor == 0:
                break
        if sent:
            logger.info("TG daily check-in: sent to %d users", sent)
    except Exception as e:
        logger.error("TG daily check-in job failed: %s", e)


async def _tg_med_reminders_job():
    """Run every 5 minutes — fire medication reminders from sorted-set queue."""
    from app.core.redis_client import get_redis
    from app.api.v1.routes.telegram import send_message
    import json
    from datetime import datetime, timezone, timedelta

    try:
        redis = await get_redis()
        now   = datetime.now(timezone.utc).timestamp()
        # Get all reminders due up to now
        due   = await redis.zrangebyscore("tg_reminder_queue", 0, now)
        if not due:
            return
        fired = 0
        for entry_bytes in due:
            entry = json.loads(entry_bytes)
            chat_id  = entry["chat_id"]
            med      = entry["med"]
            time_str = entry["time"]
            try:
                await send_message(chat_id,
                    f"💊 *Medication reminder*\n\nTime to take: *{med}*\n_{time_str} UTC_")
                fired += 1
            except Exception as e:
                logger.warning("TG reminder send error for %s: %s", chat_id, e)

            # Re-schedule for tomorrow
            await redis.zrem("tg_reminder_queue", entry_bytes)
            h, m = map(int, time_str.split(":"))
            tomorrow = datetime.now(timezone.utc).replace(
                hour=h, minute=m, second=0, microsecond=0
            ) + timedelta(days=1)
            new_entry = json.dumps({"chat_id": chat_id, "med": med, "time": time_str})
            await redis.zadd("tg_reminder_queue", {new_entry: tomorrow.timestamp()})

        if fired:
            logger.info("TG medication reminders fired: %d", fired)
    except Exception as e:
        logger.error("TG medication reminders job failed: %s", e)


async def _tg_weekly_digest_job():
    """Run every Sunday 18:00 UTC — send weekly health summary to active users."""
    from app.core.redis_client import get_redis
    from app.api.v1.routes.telegram import send_message, get_profile, TRACKER_UNITS
    import json
    from datetime import datetime, timezone, timedelta

    try:
        redis   = await get_redis()
        members = await redis.smembers("tg_active_users")
        if not members:
            return

        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        sent   = 0
        for member in members:
            try:
                chat_id = int(member)
                profile = await get_profile(chat_id)
                log     = profile.get("log", [])
                recent  = [e for e in log if e.get("date", "") >= cutoff]
                checkin = [e for e in profile.get("checkin_log", []) if e.get("date", "") >= cutoff]

                if not recent and not checkin:
                    continue

                # Category frequency
                cats: dict[str, int] = {}
                for e in recent:
                    cats[e.get("category", "general")] = cats.get(e.get("category", "general"), 0) + 1
                top = sorted(cats.items(), key=lambda x: -x[1])[:3]

                # Mood stats
                moods = [e.get("mood") for e in checkin if e.get("mood")]
                good_days = sum(1 for m in moods if m == "good")

                lines = ["📊 *Weekly Health Summary*\n"]
                if recent:
                    lines.append(f"🏥 Health check-ins this week: *{len(recent)}*")
                if moods:
                    lines.append(f"😊 Days feeling good: *{good_days}/{len(moods)}*")
                if top:
                    lines.append("\n*Most common concerns:*")
                    for cat, n in top:
                        flag = " ⚠️ *see a doctor if recurring*" if n >= 3 else ""
                        lines.append(f"  • {cat.title()} — {n}×{flag}")

                trackers = profile.get("trackers", {})
                if trackers:
                    lines.append("\n*Latest readings:*")
                    for metric, readings in trackers.items():
                        if readings:
                            r    = readings[-1]
                            unit = TRACKER_UNITS.get(metric, "")
                            lines.append(f"  • {metric.title()}: {r['value']} {unit} ({r['date']})")

                lines.append("\n_/report for full history · medmind.pro_")
                await send_message(chat_id, "\n".join(lines))
                sent += 1
            except Exception as e:
                logger.warning("TG weekly digest error for %s: %s", member, e)

        logger.info("TG weekly digest sent to %d users", sent)
    except Exception as e:
        logger.error("TG weekly digest job failed: %s", e)


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


async def _analytics_retention_job():
    """First of month 03:00 UTC — aggregate analytics_events older than 12 months into
    analytics_daily_agg, then delete the raw events. Keeps dashboard working on old data."""
    try:
        async with AsyncSessionLocal() as db:
            # Aggregate into daily_agg
            await db.execute(text("""
                INSERT INTO analytics_daily_agg (date, event_type, platform, event_count, unique_users)
                SELECT
                    DATE(created_at) AS date,
                    event_type,
                    COALESCE(platform, 'web') AS platform,
                    COUNT(*) AS event_count,
                    COUNT(DISTINCT user_id) AS unique_users
                FROM analytics_events
                WHERE created_at < NOW() - INTERVAL '12 months'
                GROUP BY DATE(created_at), event_type, COALESCE(platform, 'web')
                ON CONFLICT (date, event_type, platform) DO UPDATE
                    SET event_count  = analytics_daily_agg.event_count  + EXCLUDED.event_count,
                        unique_users = analytics_daily_agg.unique_users + EXCLUDED.unique_users
            """))
            result = await db.execute(text("""
                DELETE FROM analytics_events
                WHERE created_at < NOW() - INTERVAL '12 months'
            """))
            await db.commit()
            deleted = result.rowcount if hasattr(result, "rowcount") else "?"
            logger.info("Analytics retention: deleted %s raw events (>12 months)", deleted)
    except Exception as e:
        logger.error("Analytics retention job failed: %s", e)


async def _study_plan_morning_reminder():
    """Daily 08:00 UTC — notify users with an active exam plan about today's task."""
    from app.models.models import ExamPlan, ExamPlanCompletion, Notification, User
    from app.services.study_planner import generate_plan, get_today_task
    try:
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)

            plans_result = await db.execute(
                select(ExamPlan).where(
                    ExamPlan.status == "active",
                    ExamPlan.exam_date >= today_start,
                )
            )
            plans = plans_result.scalars().all()

            notified = 0
            for plan in plans:
                # Skip if already completed today
                comp = await db.execute(
                    select(ExamPlanCompletion).where(
                        ExamPlanCompletion.plan_id == plan.id,
                        ExamPlanCompletion.task_date >= today_start,
                        ExamPlanCompletion.task_date < today_end,
                    )
                )
                if comp.scalar_one_or_none():
                    continue

                tasks = plan.plan_cache or generate_plan(plan.exam_date.date(), plan.daily_minutes)
                today_task = get_today_task(tasks)
                if not today_task or today_task["task_type"] in ("exam_day",):
                    continue

                # Skip if already notified today
                existing = await db.execute(
                    select(Notification).where(
                        Notification.user_id == plan.user_id,
                        Notification.type == "study_plan_reminder",
                        Notification.created_at >= today_start,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                task_label = today_task["task_type"].replace("_", " ").title()
                body = (
                    f"Today's task: {task_label}"
                    + (f" — {today_task['questions']} questions" if today_task["questions"] > 0 else "")
                    + f" ({today_task['days_to_exam']} days to exam)"
                )
                notif = Notification(
                    user_id=plan.user_id,
                    type="study_plan_reminder",
                    title="Study Plan — Today's Task",
                    body=body,
                    data={"link": "/nurses/nclex?tab=plan", "task_type": today_task["task_type"]},
                )
                db.add(notif)
                notified += 1

            await db.commit()
            if notified:
                logger.info("Study plan reminders sent: %d", notified)
    except Exception as e:
        logger.error("Study plan morning reminder failed: %s", e)


async def _enrich_nclex_rationales_job() -> None:
    """Enrich NCLEX questions missing rationales (50 per run)."""
    try:
        from app.scripts.enrich_nclex_rationales import run as enrich_run
        await enrich_run(max_questions=50)
    except Exception as exc:
        logger.error("enrich_nclex_rationales cron error: %s", exc)


async def _translate_nclex_es_job() -> None:
    """Translate enriched NCLEX rationales to Spanish (50 per run)."""
    try:
        from app.scripts.translate_nclex_rationales import run as translate_run
        await translate_run(max_questions=50)
    except Exception as exc:
        logger.error("translate_nclex_rationales cron error: %s", exc)


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

    # Daily 05:00 UTC — dunning check (grace-period emails + downgrades)
    async def _dunning_wrapper():
        from app.services.billing import run_dunning_check
        await run_dunning_check()

    scheduler.add_job(
        _dunning_wrapper,
        trigger=CronTrigger(hour=5, minute=0, timezone="UTC"),
        id="dunning_check",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Weekly Sunday 03:30 UTC — Stripe subscription reconciliation
    async def _reconciliation_wrapper():
        from app.services.billing import run_subscription_reconciliation
        await run_subscription_reconciliation()

    scheduler.add_job(
        _reconciliation_wrapper,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=30, timezone="UTC"),
        id="stripe_reconciliation",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily 06:00 UTC — lifecycle email campaigns
    async def _lifecycle_wrapper():
        from app.services.lifecycle import run_all_campaigns
        await run_all_campaigns()

    scheduler.add_job(
        _lifecycle_wrapper,
        trigger=CronTrigger(hour=6, minute=0, timezone="UTC"),
        id="lifecycle_campaigns",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Daily 08:00 UTC — study plan morning reminder
    scheduler.add_job(
        _study_plan_morning_reminder,
        trigger=CronTrigger(hour=8, minute=0, timezone="UTC"),
        id="study_plan_morning_reminder",
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

    # Hourly — Telegram daily check-in (sends to users whose chosen time matches current hour)
    scheduler.add_job(
        _tg_daily_checkin_job,
        trigger=CronTrigger(minute=0, timezone="UTC"),
        id="tg_daily_checkin",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Every 5 minutes — fire Telegram medication reminders
    from apscheduler.triggers.interval import IntervalTrigger
    scheduler.add_job(
        _tg_med_reminders_job,
        trigger=IntervalTrigger(minutes=5),
        id="tg_med_reminders",
        replace_existing=True,
        misfire_grace_time=120,
    )

    # Sunday 18:00 UTC — Telegram weekly health digest
    scheduler.add_job(
        _tg_weekly_digest_job,
        trigger=CronTrigger(day_of_week="sun", hour=18, minute=0, timezone="UTC"),
        id="tg_weekly_digest",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # 1st of each month 03:00 UTC — aggregate + purge analytics events >12 months
    scheduler.add_job(
        _analytics_retention_job,
        trigger=CronTrigger(day=1, hour=3, minute=0, timezone="UTC"),
        id="analytics_retention",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Every 30 min — enrich NCLEX questions missing rationales (50 per run, all key pools)
    scheduler.add_job(
        _enrich_nclex_rationales_job,
        trigger=CronTrigger(minute="*/30", timezone="UTC"),
        id="enrich_nclex_rationales",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # Every 30 min (offset +15) — translate enriched NCLEX rationales to Spanish
    scheduler.add_job(
        _translate_nclex_es_job,
        trigger=CronTrigger(minute="15,45", timezone="UTC"),
        id="translate_nclex_es",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info("Background scheduler started (daily streak reset, weekly stats, news pipeline)")


def stop_scheduler():
    """Stop the scheduler. Call from lifespan shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
