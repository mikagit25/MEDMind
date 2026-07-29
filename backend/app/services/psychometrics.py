"""V7 Phase 1: Psychometrics service.

Computes question-bank statistics from real user attempts:
  - p_value (difficulty), option_distribution, discrimination, avg_time
  - computed_difficulty (replaces AI-generated static label when sample_size_ok)
  - health flags: ok | review_low_p | review_high_p | review_low_discrimination
                  | review_dead_distractor | review_key_suspect

Key invariant: only FIRST attempts from exam/mock/practice sessions count.
SRS repetitions and repeat attempts are excluded so p_value doesn't drift up
as students memorise questions.

Usage:
    # nightly cron
    await compute_all_stats(db)

    # manual / partial
    await compute_all_stats(db, question_id=some_uuid, exam_slug="nclex_rn")

    # single question dict or ORM object
    difficulty = get_effective_difficulty(question)
"""
from __future__ import annotations

import json
import logging
import uuid as uuid_lib
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings

log = logging.getLogger(__name__)

_settings = Settings()  # noqa: avoid repeated imports in hot path


# ── Public helper: effective difficulty ───────────────────────────────────────

def get_effective_difficulty(question: Any) -> str:
    """Return computed_difficulty when sample is sufficient, else fall back to
    the AI-generated static ``difficulty`` string.

    Accepts ORM MCQQuestion objects, dicts from session snapshots, or any
    object/dict that has a ``difficulty`` attribute/key.
    """
    # ORM object with stats relationship loaded
    if hasattr(question, "stats") and question.stats is not None:
        stats = question.stats
        if stats.sample_size_ok and stats.computed_difficulty:
            return stats.computed_difficulty

    # Dict from exam snapshot (may carry question_stats inline)
    if isinstance(question, dict):
        inline = question.get("_stats")
        if inline and inline.get("sample_size_ok") and inline.get("computed_difficulty"):
            return inline["computed_difficulty"]
        return question.get("difficulty", "medium") or "medium"

    # ORM object without stats (or stats not loaded)
    return getattr(question, "difficulty", "medium") or "medium"


# ── p_value → computed_difficulty mapping ─────────────────────────────────────

def _p_to_difficulty(p: float) -> str:
    cfg = _settings
    if p > cfg.PSYCHO_P_VERY_EASY:
        return "very_easy"
    if p > cfg.PSYCHO_P_EASY:
        return "easy"
    if p > cfg.PSYCHO_P_MEDIUM:
        return "medium"
    if p > cfg.PSYCHO_P_HARD:
        return "hard"
    return "very_hard"


def _compute_health(
    p: float | None,
    discrimination: float | None,
    option_dist: dict,
    correct_answer: str | None,
    attempts: int,
    sample_ok: bool,
) -> str:
    """Health priority: key_suspect > low_disc(neg) > low_p > high_p > dead_distractor > ok."""
    cfg = _settings

    if p is not None and discrimination is not None and sample_ok:
        # Key suspect: wrong option chosen more than correct
        if correct_answer and isinstance(option_dist, dict):
            correct_count = option_dist.get(correct_answer, 0)
            for opt, cnt in option_dist.items():
                if opt not in ("sets",) and opt != correct_answer and cnt > correct_count:
                    return "review_key_suspect"

        # Negative discrimination = strong students answer wrong more often
        if discrimination < 0:
            return "review_low_discrimination"

        if p < cfg.PSYCHO_HEALTH_LOW_P:
            return "review_low_p"

        if p > cfg.PSYCHO_HEALTH_HIGH_P:
            return "review_high_p"

        # Dead distractor: option never chosen despite sufficient sample
        if isinstance(option_dist, dict) and attempts >= cfg.PSYCHO_SAMPLE_THRESHOLD:
            for opt in ("A", "B", "C", "D"):
                if opt not in (correct_answer or ""):
                    if option_dist.get(opt, 0) == 0:
                        return "review_dead_distractor"

    return "ok"


# ── Core computation ──────────────────────────────────────────────────────────

async def compute_all_stats(
    db: AsyncSession,
    question_id: Optional[str] = None,
    exam_slug: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Recompute question_stats from question_attempts.

    Args:
        db: async database session
        question_id: restrict to one question (UUID string)
        exam_slug: restrict to one exam slice
        dry_run: compute but don't write to DB; return report dict

    Returns:
        {computed: N, skipped: N, health_distribution: {...}}
    """
    from app.models.models import QuestionAttempt, QuestionStats, MCQQuestion

    cfg = _settings

    # ── 1. Fetch first attempts only (not SRS) ──────────────────────────────
    q = (
        select(QuestionAttempt)
        .where(
            QuestionAttempt.is_first_attempt == True,
            QuestionAttempt.session_type.in_(["practice", "exam", "mock"]),
        )
    )
    if question_id:
        q = q.where(QuestionAttempt.question_id == uuid_lib.UUID(question_id))
    if exam_slug:
        q = q.where(QuestionAttempt.exam_slug == exam_slug)

    rows = (await db.execute(q)).scalars().all()

    if not rows:
        log.info("psychometrics: no eligible attempts found")
        return {"computed": 0, "skipped": 0, "health_distribution": {}}

    # ── 2. Fetch session scores for discrimination (upper/lower 27% method) ─
    # We need per-session score_pct to rank sessions.
    # ExamSession.per_question → score_pct already computed on finalize.
    from app.models.models import ExamSession
    sessions_result = await db.execute(
        select(ExamSession.id, ExamSession.score_pct)
        .where(ExamSession.status == "completed", ExamSession.score_pct.isnot(None))
    )
    session_scores: dict[str, float] = {
        str(r.id): r.score_pct for r in sessions_result
    }

    # Compute 27th and 73rd percentile thresholds
    all_scores = sorted(session_scores.values())
    if all_scores:
        n = len(all_scores)
        idx_low = max(0, int(n * 0.27) - 1)
        idx_high = min(n - 1, int(n * 0.73))
        thresh_low = all_scores[idx_low]
        thresh_high = all_scores[idx_high]
    else:
        thresh_low = thresh_high = None

    # ── 3. Aggregate attempts per question ──────────────────────────────────
    # {question_id -> {correct: int, total: int, option_counts: {A:N,...},
    #                   times: [float,...], upper_correct: int, upper_total: int,
    #                   lower_correct: int, lower_total: int}}
    agg: dict[str, dict] = defaultdict(lambda: {
        "correct": 0, "total": 0,
        "option_counts": defaultdict(int),
        "times": [],
        "upper_correct": 0, "upper_total": 0,
        "lower_correct": 0, "lower_total": 0,
    })

    for row in rows:
        qid = str(row.question_id)
        a = agg[qid]
        a["total"] += 1
        if row.is_correct:
            a["correct"] += 1
        if row.time_seconds:
            a["times"].append(row.time_seconds)

        # Option distribution
        sel = row.selected
        if isinstance(sel, str) and sel:
            a["option_counts"][sel.upper()] += 1
        elif isinstance(sel, list):
            key = "+".join(sorted(s.upper() for s in sel))
            a["option_counts"].setdefault("sets", defaultdict(int))
            a["option_counts"]["sets"][key] += 1

        # Discrimination grouping
        sid = str(row.session_id) if row.session_id else None
        if sid and thresh_low is not None and thresh_high is not None:
            score = session_scores.get(sid)
            if score is not None:
                if score >= thresh_high:
                    a["upper_total"] += 1
                    if row.is_correct:
                        a["upper_correct"] += 1
                elif score <= thresh_low:
                    a["lower_total"] += 1
                    if row.is_correct:
                        a["lower_correct"] += 1

    # ── 4. Fetch correct answers for key_suspect check ──────────────────────
    qids = list(agg.keys())
    mcqs_result = await db.execute(
        select(MCQQuestion.id, MCQQuestion.correct)
        .where(MCQQuestion.id.in_([uuid_lib.UUID(q) for q in qids]))
    )
    correct_answers: dict[str, str] = {str(r.id): r.correct for r in mcqs_result}

    # ── 5. Compute stats + upsert question_stats ────────────────────────────
    computed = 0
    health_dist: dict[str, int] = defaultdict(int)

    for qid, a in agg.items():
        total = a["total"]
        correct = a["correct"]
        p = round(correct / total, 4) if total > 0 else None
        sample_ok = total >= cfg.PSYCHO_SAMPLE_THRESHOLD

        # Discrimination
        discrimination: float | None = None
        if a["upper_total"] > 0 and a["lower_total"] > 0:
            p_upper = a["upper_correct"] / a["upper_total"]
            p_lower = a["lower_correct"] / a["lower_total"]
            discrimination = round(p_upper - p_lower, 4)

        avg_time = round(sum(a["times"]) / len(a["times"]), 2) if a["times"] else None
        computed_diff = _p_to_difficulty(p) if (p is not None and sample_ok) else None

        # Flatten option_counts (convert inner defaultdicts to plain dicts)
        opt_dist = {}
        for k, v in a["option_counts"].items():
            if k == "sets":
                opt_dist["sets"] = dict(v)
            else:
                opt_dist[k] = v

        health = _compute_health(
            p, discrimination, opt_dist,
            correct_answers.get(qid), total, sample_ok
        )
        health_dist[health] += 1

        if dry_run:
            computed += 1
            continue

        # Upsert into question_stats (exam_slug=None = aggregate row)
        existing = (await db.execute(
            select(QuestionStats).where(
                QuestionStats.question_id == uuid_lib.UUID(qid),
                QuestionStats.exam_slug == exam_slug,
            )
        )).scalar_one_or_none()

        now = datetime.utcnow()
        if existing:
            existing.attempts = total
            existing.correct_count = correct
            existing.p_value = p
            existing.option_distribution = opt_dist
            existing.discrimination = discrimination
            existing.avg_time_seconds = avg_time
            existing.sample_size_ok = sample_ok
            existing.computed_difficulty = computed_diff
            existing.health = health
            existing.last_computed_at = now
        else:
            db.add(QuestionStats(
                question_id=uuid_lib.UUID(qid),
                exam_slug=exam_slug,
                attempts=total,
                correct_count=correct,
                p_value=p,
                option_distribution=opt_dist,
                discrimination=discrimination,
                avg_time_seconds=avg_time,
                sample_size_ok=sample_ok,
                computed_difficulty=computed_diff,
                health=health,
                last_computed_at=now,
            ))
        computed += 1

    if not dry_run:
        await db.commit()

    log.info("psychometrics: computed=%d health=%s", computed, dict(health_dist))
    return {
        "computed": computed,
        "skipped": len(rows) - computed,
        "health_distribution": dict(health_dist),
    }


# ── Record a new attempt ──────────────────────────────────────────────────────

async def record_attempt(
    db: AsyncSession,
    question_id: str,
    user_id: str,
    is_correct: bool,
    selected: Any,
    session_id: str | None = None,
    session_type: str = "practice",
    exam_slug: str | None = None,
    time_seconds: float | None = None,
) -> None:
    """Insert a QuestionAttempt row. Marks is_first_attempt=False if user has
    already attempted this question (in any session type).
    Called from exam.py on session finalize so we have one batch insert.
    """
    from app.models.models import QuestionAttempt

    # Check if first attempt
    existing = (await db.execute(
        select(QuestionAttempt.id).where(
            QuestionAttempt.question_id == uuid_lib.UUID(question_id),
            QuestionAttempt.user_id == uuid_lib.UUID(user_id),
        ).limit(1)
    )).scalar_one_or_none()

    is_first = existing is None

    db.add(QuestionAttempt(
        question_id=uuid_lib.UUID(question_id),
        user_id=uuid_lib.UUID(user_id),
        exam_slug=exam_slug,
        selected=selected if not callable(selected) else None,
        is_correct=is_correct,
        time_seconds=time_seconds,
        session_id=uuid_lib.UUID(session_id) if session_id else None,
        session_type=session_type,
        is_first_attempt=is_first,
    ))
    # Caller must commit
