"""Lifecycle email campaign engine — V6 Phase 5.

All sends are idempotent: the (user_id, campaign, step) unique constraint on
lifecycle_sends prevents any campaign step from being delivered twice.

Campaigns
---------
onboarding_d1   Day 1 after sign-up — "get started" with role-specific tips
onboarding_d3   Day 3 — prompt to try the AI tutor or dose calc
onboarding_d7   Day 7 — first-week stats recap
reactivation_7d  7 days inactive — "you were 40% through module X"
reactivation_21d 21 days inactive — new content digest
reactivation_45d 45 days inactive — last-chance email (then silence)
streak_risk     Evening, streak ≥3 and no activity today — email variant
readiness_weekly Weekly for active NCLEX users — readiness delta
exam_countdown_7d Plan exists, exam in 7 days
exam_countdown_1d Plan exists, exam in 1 day
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.email import _base_template, _send_smtp
from app.models.models import (
    AnalyticsEvent,
    ExamPlan,
    LifecycleSend,
    User,
    UserProgress,
)

logger = logging.getLogger(__name__)

# ── Unsubscribe token ─────────────────────────────────────────────────────────

_TOKEN_SECRET = (settings.JWT_SECRET_KEY or "lifecycle-dev-secret").encode()


def make_unsub_token(user_id: str, campaign: str) -> str:
    msg = f"{user_id}:{campaign}".encode()
    return hmac.new(_TOKEN_SECRET, msg, hashlib.sha256).hexdigest()


def verify_unsub_token(user_id: str, campaign: str, token: str) -> bool:
    expected = make_unsub_token(user_id, campaign)
    return hmac.compare_digest(expected, token)


# ── Unsubscribe helpers ───────────────────────────────────────────────────────

def is_unsubscribed(user: User, campaign: str) -> bool:
    prefs: dict = user.preferences or {}
    unsubs: list = prefs.get("email_unsubscribes", [])
    if "all" in unsubs or campaign in unsubs:
        return True
    # Respect top-level email_notifications flag
    if prefs.get("email_notifications") is False:
        return True
    return False


def _unsub_url(user_id: str, campaign: str) -> str:
    token = make_unsub_token(str(user_id), campaign)
    return (
        f"{settings.FRONTEND_URL}/api/lifecycle/unsubscribe"
        f"?uid={user_id}&campaign={campaign}&token={token}"
    )


# ── Core send helper ──────────────────────────────────────────────────────────

async def _try_send(
    db: AsyncSession,
    user: User,
    campaign: str,
    subject: str,
    html: str,
    text: str,
    step: str = "email",
) -> bool:
    """Attempt to send one lifecycle email. Returns True if sent, False if skipped."""
    if is_unsubscribed(user, campaign):
        return False

    # Idempotency check via unique constraint
    send_row = LifecycleSend(user_id=user.id, campaign=campaign, step=step)
    db.add(send_row)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return False  # already sent

    # Inject real unsubscribe URL
    unsub = _unsub_url(str(user.id), campaign)
    html_final = html.replace("{unsub_url}", unsub)
    text_final = text + f"\n\nUnsubscribe: {unsub}"

    try:
        _send_smtp(user.email, subject, html_final, text_final)
    except Exception as exc:
        logger.error("lifecycle send failed [%s → %s]: %s", campaign, user.email, exc)
        await db.rollback()
        return False

    # Analytics event
    db.add(AnalyticsEvent(
        user_id=user.id,
        event_type="email_sent",
        entity_type="lifecycle_campaign",
        entity_id=campaign,
        meta={"step": step, "subject": subject[:120]},
        platform="email",
    ))
    await db.commit()
    logger.info("lifecycle sent [%s] → %s", campaign, user.email)
    return True


# ── Email content helpers ─────────────────────────────────────────────────────

def _unsub_footer(campaign: str) -> str:
    return (
        f'<a href="{{unsub_url}}" style="color:#8a8278;font-size:11px;">'
        f"Unsubscribe from this campaign</a>"
    )


def _build(title: str, body: str, cta_text: str, cta_url: str, campaign: str) -> tuple[str, str]:
    unsub = _unsub_footer(campaign)
    extra = f'<p style="margin:24px 0 0;text-align:center;">{unsub}</p>'
    html = _base_template(title, body + extra, cta_text, cta_url)
    text = f"{title}\n\n{cta_url}\n\nUnsubscribe: {{unsub_url}}"
    return html, text


# ── Campaigns ─────────────────────────────────────────────────────────────────

async def _run_onboarding_d1(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=1)
    upper = now - timedelta(hours=20)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.created_at >= cutoff,
            User.created_at < upper,
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/dashboard"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, your MedMind AI account is ready. Here's the fastest way to start:
          </p>
          <ul style="color:#4a453e;font-size:14px;line-height:2;margin:0 0 16px;padding-left:20px;">
            <li>Open a <strong>module</strong> to start learning</li>
            <li>Ask the <strong>AI Tutor</strong> anything about your topic</li>
            <li>Build your first <strong>flashcard deck</strong></li>
          </ul>"""
        html, text = _build(
            f"Welcome, {name} — here's how to start", body,
            "Open Dashboard", url, "onboarding_d1",
        )
        if await _try_send(db, u, "onboarding_d1", "Your MedMind AI account is ready", html, text):
            sent += 1
    return sent


async def _run_onboarding_d3(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=3)
    upper = now - timedelta(days=2, hours=20)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.created_at >= cutoff,
            User.created_at < upper,
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/ai-tutor"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, it's day 3 — have you tried the AI Tutor yet?
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Ask it to explain any medical concept, quiz you, or walk through a clinical case.
            It adapts to your level and specialty.
          </p>"""
        html, text = _build(
            "Try something new today", body,
            "Open AI Tutor", url, "onboarding_d3",
        )
        if await _try_send(db, u, "onboarding_d3", "Day 3: have you tried the AI Tutor?", html, text):
            sent += 1
    return sent


async def _run_onboarding_d7(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=7)
    upper = now - timedelta(days=6, hours=20)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.created_at >= cutoff,
            User.created_at < upper,
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/progress"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, you've been with MedMind AI for a week!
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Check your progress page to see what you've covered and what to tackle next.
            Consistency is everything in medical learning.
          </p>"""
        html, text = _build(
            "Your first week on MedMind AI", body,
            "View My Progress", url, "onboarding_d7",
        )
        if await _try_send(db, u, "onboarding_d7", "Your first week on MedMind AI 🎉", html, text):
            sent += 1
    return sent


async def _run_reactivation_7d(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=7)
    upper = now - timedelta(days=6, hours=20)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.last_active_date >= cutoff,
            User.last_active_date < upper,
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/dashboard"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, it's been 7 days since you last studied on MedMind AI.
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Your modules and flashcards are waiting. Even 10 minutes today keeps your streak alive
            and your knowledge fresh.
          </p>"""
        html, text = _build(
            "Your studies are waiting", body,
            "Continue Learning", url, "reactivation_7d",
        )
        if await _try_send(db, u, "reactivation_7d", "We miss you — come back to MedMind AI", html, text):
            sent += 1
    return sent


async def _run_reactivation_21d(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=21)
    upper = now - timedelta(days=20, hours=20)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.last_active_date >= cutoff,
            User.last_active_date < upper,
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/modules"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, it's been three weeks. We've added new modules and content since you last visited.
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Browse what's new — you might find exactly the topic you need right now.
          </p>"""
        html, text = _build(
            "New content added since you left", body,
            "Explore New Modules", url, "reactivation_21d",
        )
        if await _try_send(db, u, "reactivation_21d", "New content on MedMind AI since your last visit", html, text):
            sent += 1
    return sent


async def _run_reactivation_45d(db: AsyncSession, now: datetime) -> int:
    cutoff = now - timedelta(days=45)
    upper = now - timedelta(days=44, hours=20)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.last_active_date >= cutoff,
            User.last_active_date < upper,
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/dashboard"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, it's been 45 days.
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            We won't keep sending emails if you're not using MedMind AI — but your account and all your
            progress are still here whenever you're ready to come back.
          </p>"""
        html, text = _build(
            "Your account is here whenever you're ready", body,
            "Return to MedMind AI", url, "reactivation_45d",
        )
        if await _try_send(db, u, "reactivation_45d", "One last note from MedMind AI", html, text):
            sent += 1
    return sent


async def _run_streak_risk(db: AsyncSession, now: datetime) -> int:
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.streak_days >= 3,
            (User.last_active_date == None) | (User.last_active_date < today_start),
        )
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/dashboard"
        streak = u.streak_days
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, your <strong>{streak}-day streak</strong> is at risk!
          </p>
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Study anything for just a few minutes before midnight to keep it alive.
          </p>"""
        html, text = _build(
            f"Your {streak}-day streak ends tonight", body,
            "Keep My Streak", url, "streak_risk",
        )
        # step = today's date so it fires daily but only once per day per user
        step = f"email_{today_start.strftime('%Y%m%d')}"
        if await _try_send(db, u, "streak_risk", f"Don't lose your {streak}-day streak!", html, text, step=step):
            sent += 1
    return sent


async def _run_readiness_weekly(db: AsyncSession, now: datetime) -> int:
    from app.services.readiness import get_cached_readiness
    # Run on Mondays only
    if now.weekday() != 0:
        return 0

    today_step = f"email_{now.strftime('%Y_w%W')}"

    result = await db.execute(
        select(User).where(User.is_active == True)
    )
    users = result.scalars().all()
    sent = 0
    for u in users:
        try:
            rdns = await get_cached_readiness(str(u.id), db)
        except Exception:
            continue
        if not rdns or not rdns.get("threshold_met") or rdns.get("score") is None:
            continue

        score = rdns["score"]
        level_label = rdns.get("level_label", "")
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/nurses/nclex"
        color = "#27ae60" if score >= 75 else "#e67e22" if score >= 62 else "#c0392b"
        body = f"""
          <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
            Hi {name}, here's your weekly NCLEX readiness update:
          </p>
          <div style="text-align:center;margin:20px 0;">
            <span style="font-size:64px;font-weight:900;color:{color};">{score}%</span><br>
            <span style="font-size:14px;color:#8a8278;">{level_label}</span>
          </div>
          <p style="color:#4a453e;font-size:14px;line-height:1.6;margin:0 0 16px;">
            Keep practising to improve your score. Focus on your weakest categories.
          </p>"""
        html, text = _build(
            "Your NCLEX Readiness This Week", body,
            "View Full Breakdown", url, "readiness_weekly",
        )
        if await _try_send(db, u, "readiness_weekly", f"NCLEX Readiness: {score}% this week", html, text, step=today_step):
            sent += 1
    return sent


async def _run_exam_countdown(db: AsyncSession, now: datetime, days_out: int) -> int:
    target = now.date() + timedelta(days=days_out)
    # Find active plans with exam on target date
    result = await db.execute(
        select(ExamPlan).where(
            ExamPlan.status == "active",
            ExamPlan.exam_date >= datetime.combine(target, datetime.min.time()),
            ExamPlan.exam_date < datetime.combine(target + timedelta(days=1), datetime.min.time()),
        )
    )
    plans = result.scalars().all()
    sent = 0
    for plan in plans:
        u_result = await db.execute(select(User).where(User.id == plan.user_id))
        u = u_result.scalar_one_or_none()
        if not u or not u.is_active:
            continue
        name = u.first_name or "there"
        url = f"{settings.FRONTEND_URL}/nurses/nclex"
        campaign = f"exam_countdown_{days_out}d"
        if days_out == 7:
            body = f"""
              <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
                Hi {name}, your NCLEX exam is in <strong>7 days</strong>.
              </p>
              <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
                This week: focus on weak categories, take one more mock exam, and get your rest.
                You've prepared for this.
              </p>"""
            subject = "7 days to your NCLEX exam"
        else:
            body = f"""
              <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
                Hi {name}, your NCLEX exam is <strong>tomorrow</strong>.
              </p>
              <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
                No heavy studying tonight. Rest well, eat a good breakfast, and trust your preparation.
                Good luck!
              </p>"""
            subject = "Your NCLEX exam is tomorrow — good luck!"
        html, text = _build(
            subject, body,
            "View Study Plan", url, campaign,
        )
        if await _try_send(db, u, campaign, subject, html, text):
            sent += 1
    return sent


# ── Main daily runner ─────────────────────────────────────────────────────────

async def run_all_campaigns(now: datetime | None = None) -> dict[str, int]:
    """Run all lifecycle campaigns. Returns dict of {campaign: emails_sent}."""
    now = now or datetime.utcnow()
    results: dict[str, int] = {}

    async with AsyncSessionLocal() as db:
        results["onboarding_d1"]    = await _run_onboarding_d1(db, now)
        results["onboarding_d3"]    = await _run_onboarding_d3(db, now)
        results["onboarding_d7"]    = await _run_onboarding_d7(db, now)
        results["reactivation_7d"]  = await _run_reactivation_7d(db, now)
        results["reactivation_21d"] = await _run_reactivation_21d(db, now)
        results["reactivation_45d"] = await _run_reactivation_45d(db, now)
        results["streak_risk"]      = await _run_streak_risk(db, now)
        results["readiness_weekly"] = await _run_readiness_weekly(db, now)
        results["exam_countdown_7d"] = await _run_exam_countdown(db, now, 7)
        results["exam_countdown_1d"] = await _run_exam_countdown(db, now, 1)

    total = sum(results.values())
    logger.info("Lifecycle campaigns complete: %d emails sent — %s", total, results)
    return results
