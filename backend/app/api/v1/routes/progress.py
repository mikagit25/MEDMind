"""Progress & spaced repetition routes."""
from datetime import datetime
from typing import List
from uuid import UUID
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.database import get_db
from app.models.models import (
    User, UserProgress, FlashcardReview, Flashcard, Lesson,
    Module, MCQQuestion, ClinicalCase, CMECredit, XPEvent, Specialty, ExamSession
)
from app.schemas.schemas import (
    LessonCompleteRequest, LessonCompleteResponse,
    FlashcardReviewRequest, FlashcardReviewResponse,
    MCQAnswerRequest, MCQAnswerResponse, ProgressStats,
    CaseCompleteRequest, CaseCompleteResponse, ProgressHistoryItem,
)
from app.api.deps import get_current_user
from app.core.cache import invalidate
from app.api.v1.routes.achievements import run_achievement_check

router = APIRouter(prefix="/progress", tags=["progress"])

# XP values
XP_LESSON = 50
XP_FLASHCARD_CORRECT = 5
XP_MCQ_CORRECT = 10
XP_MCQ_HARD_CORRECT = 20


def calculate_sm2(ease_factor: float, interval: int, quality: int) -> tuple[float, int]:
    """SM-2 algorithm. Returns (new_ease_factor, new_interval_days)."""
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, new_ef)

    if quality < 3:
        new_interval = 1
    elif interval <= 1:
        new_interval = 6
    else:
        new_interval = round(interval * new_ef)

    return new_ef, new_interval


import math as _math


def _calc_level(xp: int) -> int:
    """Level formula: floor(sqrt(xp / 100)). Min level 1."""
    return max(1, _math.isqrt(max(0, xp) // 100))


async def add_xp(user: User, xp: int, db: AsyncSession, source: str = "lesson", reference_id: str | None = None):
    """Add XP to user, level up if needed, update streak, record XP event."""
    from datetime import date as _date, timedelta
    user.xp = (user.xp or 0) + xp
    user.level = _calc_level(user.xp)

    # Streak update
    today = _date.today()
    raw = user.last_active_date
    last = raw.date() if isinstance(raw, datetime) else raw
    if last is None or last < today:
        if last == today - timedelta(days=1):
            user.streak_days = (user.streak_days or 0) + 1
        elif last != today:
            user.streak_days = 1
        # Update longest_streak
        if (user.streak_days or 0) > (user.longest_streak or 0):
            user.longest_streak = user.streak_days
    user.last_active_date = datetime.utcnow()

    # Audit trail
    db.add(XPEvent(
        user_id=user.id,
        source=source,
        amount=xp,
        reference_id=reference_id,
    ))


@router.post("/lesson/{lesson_id}/complete", response_model=LessonCompleteResponse)
async def complete_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Get or create user_progress record — SELECT FOR UPDATE prevents double-XP
    # if two requests race (e.g. network retry, double-tap).
    prog_result = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.module_id == lesson.module_id,
        )
        .with_for_update()
    )
    progress = prog_result.scalar_one_or_none()

    if not progress:
        progress = UserProgress(user_id=user.id, module_id=lesson.module_id)
        db.add(progress)
        await db.flush()

    # Mark lesson as completed (idempotent).
    completed = [str(x) for x in (progress.lessons_completed or [])]
    lesson_id_str = str(lesson.id)
    is_new_completion = lesson_id_str not in completed
    if is_new_completion:
        completed.append(lesson_id_str)
        progress.lessons_completed = completed
        progress.last_activity_at = datetime.utcnow()

        # Award XP
        await add_xp(user, XP_LESSON, db, source="lesson", reference_id=str(lesson_id))

    # Recalculate module completion
    lessons_result = await db.execute(select(Lesson).where(Lesson.module_id == lesson.module_id))
    all_lessons = lessons_result.scalars().all()
    total = len(all_lessons)
    done = len(completed)
    completion_pct = (done / total * 100) if total > 0 else 0
    progress.completion_percent = completion_pct

    # CME credit for doctors — 0.5 AMA PRA Category 1 credit per lesson (idempotent)
    if user.role in ("doctor", "resident") and is_new_completion:
        mod_result = await db.execute(select(Module).where(Module.id == lesson.module_id))
        mod = mod_result.scalar_one_or_none()
        cme = CMECredit(
            user_id=user.id,
            module_id=lesson.module_id,
            credit_type="AMA_PRA_1",
            credits_earned=0.5,
            activity_title=f"{mod.title if mod else 'Module'}: {lesson.title}",
            completion_date=datetime.utcnow(),
        )
        db.add(cme)

    await db.commit()
    await invalidate(f"student_dashboard:{user.id}")

    xp_for_response = XP_LESSON if is_new_completion else 0
    newly_unlocked = await run_achievement_check(user, db) if is_new_completion else []

    return LessonCompleteResponse(
        xp_earned=xp_for_response,
        total_xp=user.xp,
        level=user.level,
        module_completion_percent=float(completion_pct),
        newly_unlocked=newly_unlocked,
    )


@router.get("/flashcards/due")
async def get_due_flashcards(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return all flashcards due for review for the current user (mobile SM-2 queue)."""
    now = datetime.utcnow()

    # Cards that have a review record with next_review_at <= now
    reviewed_result = await db.execute(
        select(Flashcard, FlashcardReview)
        .join(FlashcardReview, FlashcardReview.flashcard_id == Flashcard.id)
        .where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= now,
        )
        .limit(limit)
    )
    reviewed_rows = reviewed_result.all()

    # Cards never reviewed (no FlashcardReview row) — take from modules user has started
    started_module_ids_result = await db.execute(
        select(UserProgress.module_id).where(UserProgress.user_id == user.id)
    )
    started_module_ids = [r[0] for r in started_module_ids_result.all()]

    new_cards: list = []
    if started_module_ids and len(reviewed_rows) < limit:
        already_reviewed_ids = [r.FlashcardReview.flashcard_id for r in reviewed_rows]
        new_result = await db.execute(
            select(Flashcard)
            .where(
                Flashcard.module_id.in_(started_module_ids),
                Flashcard.id.notin_(already_reviewed_ids) if already_reviewed_ids else True,
            )
            .limit(limit - len(reviewed_rows))
        )
        new_cards = new_result.scalars().all()

    cards_out = []
    for row in reviewed_rows:
        fc = row.Flashcard
        rev = row.FlashcardReview
        cards_out.append({
            "id": str(fc.id),
            "module_id": str(fc.module_id),
            "question": fc.question,
            "answer": fc.answer,
            "difficulty": fc.difficulty,
            "next_review_at": rev.next_review_at.isoformat() if rev.next_review_at else None,
            "interval": rev.interval_days,
            "ease_factor": float(rev.ease_factor),
            "repetitions": rev.repetitions,
        })
    for fc in new_cards:
        cards_out.append({
            "id": str(fc.id),
            "module_id": str(fc.module_id),
            "question": fc.question,
            "answer": fc.answer,
            "difficulty": fc.difficulty,
            "next_review_at": None,
            "interval": 1,
            "ease_factor": 2.5,
            "repetitions": 0,
        })

    return cards_out


@router.post("/flashcard/review", response_model=FlashcardReviewResponse)
async def review_flashcard(
    data: FlashcardReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.quality < 0 or data.quality > 5:
        raise HTTPException(status_code=400, detail="Quality must be 0-5")

    result = await db.execute(select(Flashcard).where(Flashcard.id == data.flashcard_id))
    flashcard = result.scalar_one_or_none()
    if not flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    # Get or create review state
    rev_result = await db.execute(
        select(FlashcardReview).where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.flashcard_id == data.flashcard_id,
        )
    )
    review = rev_result.scalar_one_or_none()

    if not review:
        review = FlashcardReview(
            user_id=user.id,
            flashcard_id=data.flashcard_id,
            ease_factor=2.5,
            interval_days=1,
            repetitions=0,
        )
        db.add(review)

    # Apply SM-2
    new_ef, new_interval = calculate_sm2(
        float(review.ease_factor) if review.ease_factor is not None else 2.5,
        review.interval_days or 1,
        data.quality,
    )
    review.ease_factor = new_ef
    review.interval_days = new_interval
    review.repetitions += 1
    review.last_quality = data.quality
    review.last_reviewed_at = datetime.utcnow()

    from datetime import timedelta
    review.next_review_at = datetime.utcnow() + timedelta(days=new_interval)

    # XP for correct answer (quality >= 3)
    xp_earned = XP_FLASHCARD_CORRECT if data.quality >= 3 else 0
    if xp_earned:
        await add_xp(user, xp_earned, db, source="flashcard", reference_id=str(data.flashcard_id))

    await db.commit()

    newly_unlocked = await run_achievement_check(user, db)

    return FlashcardReviewResponse(
        flashcard_id=data.flashcard_id,
        next_review_at=review.next_review_at,
        interval_days=new_interval,
        ease_factor=new_ef,
        xp_earned=xp_earned,
        newly_unlocked=newly_unlocked,
    )


@router.post("/mcq/{question_id}/answer", response_model=MCQAnswerResponse)
async def answer_mcq(
    question_id: UUID,
    data: MCQAnswerRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(MCQQuestion).where(MCQQuestion.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    qtype = getattr(question, "question_type", "mcq") or "mcq"
    is_correct = False
    partial_score: float | None = None
    correct_answer_display = question.correct

    if qtype == "sata":
        selected = sorted(s.upper() for s in data.selected_options)
        correct = sorted(s.upper() for s in (question.correct_answers or []))
        correct_answer_display = ",".join(correct)
        if question.partial_scoring:
            total = len(correct)
            right = len(set(selected) & set(correct))
            wrong = len(set(selected) - set(correct))
            raw = max(0, right - wrong) / total if total else 0
            partial_score = round(raw, 2)
            is_correct = partial_score >= 1.0
        else:
            is_correct = selected == correct

    elif qtype == "ordered":
        submitted = [s.upper() for s in data.ordered_options]
        correct = [s.upper() for s in (question.correct_order or [])]
        correct_answer_display = ",".join(correct)
        is_correct = submitted == correct

    elif qtype == "calculation":
        if data.numeric_value is not None and question.numeric_answer is not None:
            tol = question.numeric_tolerance or 0.01
            is_correct = abs(data.numeric_value - question.numeric_answer) <= tol
        correct_answer_display = (
            f"{question.numeric_answer} {question.numeric_unit or ''}".strip()
        )

    else:  # mcq
        is_correct = data.selected_option.upper() == question.correct.upper()

    xp = XP_MCQ_HARD_CORRECT if (is_correct and question.difficulty == "hard") else (XP_MCQ_CORRECT if is_correct else 0)

    if xp:
        await add_xp(user, xp, db, source="mcq", reference_id=str(question.id))
    await db.commit()

    newly_unlocked = await run_achievement_check(user, db)

    return MCQAnswerResponse(
        correct=is_correct,
        correct_answer=correct_answer_display,
        explanation=question.explanation or "",
        xp_earned=xp,
        newly_unlocked=newly_unlocked,
        partial_score=partial_score,
        rationales=question.rationales,
        key_takeaway=question.key_takeaway,
        explanation_es=question.explanation_es,
        rationales_es=question.rationales_es,
        key_takeaway_es=question.key_takeaway_es,
        explanation_ar=question.explanation_ar,
        rationales_ar=question.rationales_ar,
        key_takeaway_ar=question.key_takeaway_ar,
        source_refs=question.source_refs or [],
        verification_status=question.verification_status,
    )


@router.get("/stats", response_model=ProgressStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # All user progress records
    prog_result = await db.execute(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )
    progressions = prog_result.scalars().all()
    modules_in_progress = sum(1 for p in progressions if 0 < float(p.completion_percent or 0) < 100)
    modules_completed = sum(1 for p in progressions if float(p.completion_percent or 0) >= 100)
    modules_started = sum(1 for p in progressions if float(p.completion_percent or 0) > 0)

    # Total lessons completed (sum of all completed lesson lists)
    lessons_completed = sum(len(p.lessons_completed or []) for p in progressions)

    # MCQ stats
    mcqs_answered = sum(int(p.mcq_attempts or 0) for p in progressions)
    # Weighted average MCQ score
    total_weighted = sum(
        float(p.mcq_score or 0) * int(p.mcq_attempts or 0) for p in progressions
    )
    correct_rate = round(total_weighted / mcqs_answered, 1) if mcqs_answered > 0 else 0.0

    # Count flashcard reviews
    cards_result = await db.execute(
        select(func.count()).select_from(FlashcardReview).where(
            FlashcardReview.user_id == user.id
        )
    )
    cards_reviewed = cards_result.scalar() or 0

    # Count mastered cards (quality >= 4 last review)
    mastered_result = await db.execute(
        select(func.count()).select_from(FlashcardReview).where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.last_quality >= 4,
        )
    )
    flashcards_mastered = mastered_result.scalar() or 0

    # Total sessions ≈ number of unique activity days (from UserProgress records)
    total_sessions = len([p for p in progressions if p.last_activity_at is not None])

    today = datetime.utcnow().date()
    studied_today = bool(
        user.last_active_date and
        (user.last_active_date.date() if hasattr(user.last_active_date, "date") else user.last_active_date) >= today
    )

    return ProgressStats(
        total_xp=user.xp,
        level=user.level,
        streak_days=user.streak_days or 0,
        longest_streak=user.longest_streak or 0,
        studied_today=studied_today,
        lessons_completed=lessons_completed,
        flashcards_mastered=flashcards_mastered,
        mcq_accuracy=correct_rate,
        modules_in_progress=modules_in_progress,
        modules_completed=modules_completed,
        modules_started=modules_started,
        cards_reviewed=cards_reviewed,
        mcqs_answered=mcqs_answered,
        correct_rate=correct_rate,
        total_sessions=total_sessions,
    )


@router.get("/history", response_model=List[ProgressHistoryItem])
async def get_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return last N days of activity for the progress chart."""
    from datetime import timedelta, date as _date
    from sqlalchemy import cast, Date as SADate

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)

    # Flashcard reviews per day
    card_rows = await db.execute(
        select(
            cast(FlashcardReview.last_reviewed_at, SADate).label("day"),
            func.count().label("cnt"),
        )
        .where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.last_reviewed_at >= datetime.combine(start_date, datetime.min.time()),
        )
        .group_by(cast(FlashcardReview.last_reviewed_at, SADate))
    )
    cards_by_day: dict[str, int] = {str(r.day): r.cnt for r in card_rows}

    # Build output — use last_activity_at from UserProgress for lesson activity
    activity_rows = await db.execute(
        select(
            cast(UserProgress.last_activity_at, SADate).label("day"),
            func.count().label("cnt"),
        )
        .where(
            UserProgress.user_id == user.id,
            UserProgress.last_activity_at >= datetime.combine(start_date, datetime.min.time()),
        )
        .group_by(cast(UserProgress.last_activity_at, SADate))
    )
    lessons_by_day: dict[str, int] = {str(r.day): r.cnt for r in activity_rows}

    result = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_str = str(day)
        result.append(ProgressHistoryItem(
            date=day_str,
            xp_gained=0,
            lessons=lessons_by_day.get(day_str, 0),
            cards=cards_by_day.get(day_str, 0),
        ))
    return result


# ============================================================
# CLINICAL CASES
# ============================================================
@router.post("/cases/{case_id}/complete", response_model=CaseCompleteResponse)
async def complete_case(
    case_id: UUID,
    data: CaseCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(ClinicalCase).where(ClinicalCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Simple keyword match: if answer contains key diagnosis words → correct
    expected = (case.diagnosis or "").lower()
    user_ans = data.answer.lower()
    keywords = [w for w in expected.split() if len(w) > 4]
    match_count = sum(1 for kw in keywords if kw in user_ans)
    is_correct = (match_count / max(len(keywords), 1)) >= 0.4

    xp = 15 if is_correct else 5
    await add_xp(user, xp, db, source="case", reference_id=str(case_id))
    await db.commit()

    # Build explanation from teaching_points or diagnosis
    teaching = case.teaching_points or []
    explanation = (
        ". ".join(teaching) if teaching
        else (case.diagnosis or "Review the case carefully.")
    )
    return CaseCompleteResponse(
        correct=is_correct,
        explanation=explanation,
        xp_gained=xp,
    )


# ============================================================
# WEAKNESSES
# ============================================================
@router.get("/weaknesses")
async def get_weaknesses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return modules where user performance is weakest (low completion or poor flashcard scores)."""
    # Flashcard reviews with low average quality
    rev_result = await db.execute(
        select(
            Flashcard.module_id,
            func.avg(FlashcardReview.last_quality).label("avg_quality"),
            func.count(FlashcardReview.flashcard_id).label("review_count"),
        )
        .join(FlashcardReview, Flashcard.id == FlashcardReview.flashcard_id)
        .where(FlashcardReview.user_id == user.id)
        .group_by(Flashcard.module_id)
        .having(func.avg(FlashcardReview.last_quality) < 3.5)
        .order_by(func.avg(FlashcardReview.last_quality))
        .limit(5)
    )
    weak_flashcard_modules = rev_result.all()

    # Modules with low completion
    prog_result = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.completion_percent < 50,
            UserProgress.completion_percent > 0,
        )
        .order_by(UserProgress.completion_percent)
        .limit(5)
    )
    low_completion = prog_result.scalars().all()

    # Gather module details
    module_ids = list({str(r.module_id) for r in weak_flashcard_modules} |
                      {str(p.module_id) for p in low_completion})

    modules_result = await db.execute(
        select(Module).where(Module.id.in_(module_ids))
    )
    modules_map = {str(m.id): m for m in modules_result.scalars().all()}

    weaknesses = []
    seen = set()

    for row in weak_flashcard_modules:
        mid = str(row.module_id)
        if mid not in seen and mid in modules_map:
            m = modules_map[mid]
            weaknesses.append({
                "module_id": mid,
                "module_title": m.title,
                "reason": "low_flashcard_score",
                "avg_quality": round(float(row.avg_quality), 2),
                "review_count": row.review_count,
            })
            seen.add(mid)

    for prog in low_completion:
        mid = str(prog.module_id)
        if mid not in seen and mid in modules_map:
            m = modules_map[mid]
            weaknesses.append({
                "module_id": mid,
                "module_title": m.title,
                "reason": "low_completion",
                "completion_percent": float(prog.completion_percent),
            })
            seen.add(mid)

    return {"weaknesses": weaknesses}


# ============================================================
# QUIZ PERFORMANCE BY SPECIALTY
# ============================================================
@router.get("/quiz/performance")
async def get_quiz_performance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return MCQ accuracy broken down by specialty, plus per-module detail."""
    # Join UserProgress → Module → Specialty to get per-module MCQ stats
    rows = await db.execute(
        select(
            Specialty.code.label("specialty_code"),
            Specialty.name.label("specialty_name"),
            Specialty.icon.label("specialty_icon"),
            func.sum(UserProgress.mcq_attempts).label("total_attempts"),
            func.sum(
                func.round(UserProgress.mcq_score * UserProgress.mcq_attempts / 100.0)
            ).label("total_correct"),
        )
        .join(Module, Module.id == UserProgress.module_id)
        .join(Specialty, Specialty.id == Module.specialty_id)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.mcq_attempts > 0,
        )
        .group_by(Specialty.code, Specialty.name, Specialty.icon)
        .order_by(func.sum(UserProgress.mcq_attempts).desc())
    )
    specialties = []
    for r in rows.all():
        attempts = int(r.total_attempts or 0)
        correct = int(r.total_correct or 0)
        accuracy = round(correct / attempts * 100, 1) if attempts > 0 else 0.0
        specialties.append({
            "specialty_code": r.specialty_code,
            "specialty_name": r.specialty_name,
            "specialty_icon": r.specialty_icon or "📚",
            "total_attempts": attempts,
            "total_correct": correct,
            "accuracy_pct": accuracy,
        })

    # Per-module breakdown (top 10 by attempts)
    mod_rows = await db.execute(
        select(
            Module.title.label("module_title"),
            Module.code.label("module_code"),
            Specialty.name.label("specialty_name"),
            UserProgress.mcq_attempts,
            UserProgress.mcq_score,
        )
        .join(Module, Module.id == UserProgress.module_id)
        .outerjoin(Specialty, Specialty.id == Module.specialty_id)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.mcq_attempts > 0,
        )
        .order_by(UserProgress.mcq_attempts.desc())
        .limit(10)
    )
    modules = []
    for r in mod_rows.all():
        modules.append({
            "module_title": r.module_title,
            "module_code": r.module_code,
            "specialty_name": r.specialty_name or "General",
            "attempts": int(r.mcq_attempts or 0),
            "accuracy_pct": float(r.mcq_score or 0),
        })

    return {"by_specialty": specialties, "by_module": modules}


@router.get("/quiz/weekly-trend")
async def get_quiz_weekly_trend(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return quiz/NCLEX accuracy trend by ISO week for the last 8 weeks."""
    from datetime import timedelta

    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)

    rows = await db.execute(
        select(
            func.date_trunc("week", ExamSession.created_at).label("week_start"),
            func.coalesce(func.sum(ExamSession.correct), 0).label("total_correct"),
            func.coalesce(func.sum(ExamSession.total_questions), 0).label("total_questions"),
            func.count(ExamSession.id).label("session_count"),
        )
        .where(
            ExamSession.user_id == user.id,
            ExamSession.status == "completed",
            ExamSession.created_at >= eight_weeks_ago,
            ExamSession.correct.isnot(None),
        )
        .group_by(func.date_trunc("week", ExamSession.created_at))
        .order_by(func.date_trunc("week", ExamSession.created_at))
    )

    weeks = []
    for row in rows.all():
        total_q = int(row.total_questions or 0)
        total_c = int(row.total_correct or 0)
        accuracy = round((total_c / total_q) * 100, 1) if total_q > 0 else 0.0
        ws = row.week_start
        # PostgreSQL returns datetime; SQLite (tests) returns an ISO string
        if hasattr(ws, "date"):
            week_date = ws.date().isoformat()
        else:
            week_date = str(ws)[:10]
        weeks.append({
            "week_start": week_date,
            "accuracy_pct": accuracy,
            "total_questions": total_q,
            "session_count": int(row.session_count),
        })

    return {"weeks": weeks}


# ============================================================
# MODULE PROGRESS LIST  (Task 4.5)
# ============================================================
@router.get("/modules")
async def get_modules_progress(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return all modules the user has started, with progress details."""
    prog_result = await db.execute(
        select(UserProgress)
        .where(UserProgress.user_id == user.id)
        .order_by(UserProgress.last_activity_at.desc())
    )
    progressions = prog_result.scalars().all()

    if not progressions:
        return []

    module_ids = [p.module_id for p in progressions]
    mod_result = await db.execute(
        select(Module).where(Module.id.in_(module_ids))
    )
    modules_map = {str(m.id): m for m in mod_result.scalars().all()}

    output = []
    for p in progressions:
        mid = str(p.module_id)
        mod = modules_map.get(mid)
        if not mod:
            continue
        output.append({
            "module_id": mid,
            "module_code": mod.code,
            "module_title": mod.title,
            "completion_percent": float(p.completion_percent or 0),
            "lessons_completed": len(p.lessons_completed or []),
            "mcq_attempts": int(p.mcq_attempts or 0),
            "mcq_score": float(p.mcq_score or 0),
            "ease_factor": float(p.ease_factor or 2.5),
            "next_review_at": p.next_review_at.isoformat() if p.next_review_at else None,
            "started_at": p.started_at.isoformat() if p.started_at else None,
            "last_activity_at": p.last_activity_at.isoformat() if p.last_activity_at else None,
        })
    return output


@router.get("/modules/{module_id}")
async def get_module_progress(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return progress for a single module, including completed lesson IDs."""
    progress = (await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user.id,
            UserProgress.module_id == module_id,
        )
    )).scalar_one_or_none()

    if not progress:
        return {
            "module_id": str(module_id),
            "completion_percent": 0.0,
            "lessons_completed_ids": [],
            "mcq_score": 0.0,
            "mcq_attempts": 0,
        }

    return {
        "module_id": str(module_id),
        "completion_percent": float(progress.completion_percent or 0),
        "lessons_completed_ids": [str(lid) for lid in (progress.lessons_completed or [])],
        "mcq_score": float(progress.mcq_score or 0),
        "mcq_attempts": int(progress.mcq_attempts or 0),
    }


# ============================================================
# LEADERBOARD
# ============================================================

@router.get("/leaderboard")
async def get_leaderboard(
    period: str = Query("week", pattern="^(week|month|all)$"),
    limit: int = Query(50, ge=5, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Global leaderboard by XP."""
    from datetime import timedelta

    q = select(
        User.id,
        User.first_name,
        User.last_name,
        User.leaderboard_display_name,
        User.level,
        User.xp,
        User.streak_days,
        User.longest_streak,
    ).where(User.is_active == True, User.leaderboard_opt_in == True)

    if period == "week":
        since = datetime.utcnow() - timedelta(days=7)
        q = q.where(User.last_active_date >= since)
    elif period == "month":
        since = datetime.utcnow() - timedelta(days=30)
        q = q.where(User.last_active_date >= since)

    q = q.order_by(User.xp.desc()).limit(limit)
    rows = (await db.execute(q)).all()

    my_rank = None
    board = []
    for i, row in enumerate(rows, 1):
        is_me = str(row.id) == str(user.id)
        display = (
            row.leaderboard_display_name
            or f"{row.first_name or ''} {(row.last_name or '')[:1]}.".strip()
        )
        entry = {
            "rank": i,
            "user_id": str(row.id),
            "name": display,
            "level": row.level,
            "xp": row.xp,
            "streak_days": row.streak_days or 0,
            "longest_streak": row.longest_streak or 0,
            "is_me": is_me,
        }
        if is_me:
            my_rank = i
        board.append(entry)

    # Always include current user's rank even if not on the shown list
    my_entry = None
    if my_rank is None and user.leaderboard_opt_in:
        count_above = (await db.execute(
            select(func.count()).where(
                User.is_active == True,
                User.leaderboard_opt_in == True,
                User.xp > user.xp,
            )
        )).scalar() or 0
        my_rank = count_above + 1
        my_entry = {
            "rank": my_rank,
            "user_id": str(user.id),
            "name": user.leaderboard_display_name or f"{user.first_name or ''} {(user.last_name or '')[:1]}.".strip(),
            "level": user.level,
            "xp": user.xp,
            "streak_days": user.streak_days or 0,
            "longest_streak": user.longest_streak or 0,
            "is_me": True,
        }

    return {
        "period": period,
        "my_rank": my_rank,
        "opted_in": user.leaderboard_opt_in,
        "total_shown": len(board),
        "leaderboard": board,
        "my_entry": my_entry,
    }


@router.get("/leaderboard/specialty/{specialty_id}")
async def get_specialty_leaderboard(
    specialty_id: UUID,
    limit: int = Query(50, ge=5, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Leaderboard filtered by users who have studied a given specialty."""
    from app.models.models import Specialty

    # Users who have progress in modules of this specialty
    specialty_result = await db.execute(
        select(Module.id).where(Module.specialty_id == specialty_id)
    )
    module_ids = [r[0] for r in specialty_result.all()]
    if not module_ids:
        return {"specialty_id": str(specialty_id), "leaderboard": []}

    user_ids_result = await db.execute(
        select(UserProgress.user_id)
        .where(UserProgress.module_id.in_(module_ids))
        .distinct()
    )
    user_ids = [r[0] for r in user_ids_result.all()]
    if not user_ids:
        return {"specialty_id": str(specialty_id), "leaderboard": []}

    rows = (await db.execute(
        select(User.id, User.first_name, User.last_name, User.level, User.xp)
        .where(User.id.in_(user_ids), User.is_active == True)
        .order_by(User.xp.desc())
        .limit(limit)
    )).all()

    board = [
        {
            "rank": i,
            "user_id": str(row.id),
            "name": f"{row.first_name or ''} {(row.last_name or '')[:1]}.".strip(),
            "level": row.level,
            "xp": row.xp,
            "is_me": str(row.id) == str(user.id),
        }
        for i, row in enumerate(rows, 1)
    ]
    return {"specialty_id": str(specialty_id), "leaderboard": board}


@router.patch("/leaderboard/settings")
async def update_leaderboard_settings(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Opt in/out of leaderboard and set display name."""
    if "leaderboard_opt_in" in data:
        user.leaderboard_opt_in = bool(data["leaderboard_opt_in"])
    if "leaderboard_display_name" in data:
        name = (data["leaderboard_display_name"] or "").strip()[:100]
        user.leaderboard_display_name = name or None
    await db.commit()
    return {
        "leaderboard_opt_in": user.leaderboard_opt_in,
        "leaderboard_display_name": user.leaderboard_display_name,
    }


@router.get("/gamification/me")
async def get_gamification_me(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return gamification stats for the current user."""
    import math as _math
    xp = user.xp or 0
    level = max(1, _math.isqrt(max(0, xp) // 100))
    xp_for_next = ((level + 1) ** 2) * 100
    # Level 1 spans 0-399 (levels 0 and 1 both map to display level 1)
    xp_for_current = 0 if level == 1 else (level ** 2) * 100
    pct = max(0, round(((xp - xp_for_current) / max(1, xp_for_next - xp_for_current)) * 100))
    return {
        "xp": xp,
        "level": level,
        "streak_days": user.streak_days or 0,
        "longest_streak": user.longest_streak or 0,
        "xp_for_next_level": xp_for_next,
        "xp_progress_pct": pct,
        "leaderboard_opt_in": user.leaderboard_opt_in,
        "leaderboard_display_name": user.leaderboard_display_name,
    }


# ============================================================
# CPD / CME PROGRESS PDF EXPORT
# ============================================================

@router.get("/export/pdf")
async def export_progress_pdf(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Generate a PDF CPD/CME progress report for the authenticated user.
    Suitable for submission to medical councils and licensing bodies.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )

    # ── Collect data ──────────────────────────────────────────────────────────
    prog_result = await db.execute(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )
    progressions = prog_result.scalars().all()

    module_ids = [p.module_id for p in progressions]
    modules_map: dict = {}
    if module_ids:
        mod_result = await db.execute(select(Module).where(Module.id.in_(module_ids)))
        modules_map = {str(m.id): m for m in mod_result.scalars().all()}

    cme_result = await db.execute(
        select(CMECredit)
        .where(CMECredit.user_id == user.id)
        .order_by(CMECredit.completion_date.desc())
    )
    cme_credits = cme_result.scalars().all()
    total_cme = sum(float(c.credits_earned) for c in cme_credits)

    cards_result = await db.execute(
        select(func.count()).select_from(FlashcardReview).where(FlashcardReview.user_id == user.id)
    )
    total_cards = cards_result.scalar() or 0

    mastered_result = await db.execute(
        select(func.count()).select_from(FlashcardReview).where(
            FlashcardReview.user_id == user.id, FlashcardReview.last_quality >= 4
        )
    )
    cards_mastered = mastered_result.scalar() or 0

    lessons_completed = sum(len(p.lessons_completed or []) for p in progressions)
    modules_completed = sum(1 for p in progressions if float(p.completion_percent or 0) >= 100)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    BLUE = colors.HexColor("#1e40af")
    LIGHT_BLUE = colors.HexColor("#dbeafe")

    title_style = ParagraphStyle("title", parent=styles["Title"], textColor=BLUE, fontSize=22)
    h2_style = ParagraphStyle("h2", parent=styles["Heading2"], textColor=BLUE, fontSize=13, spaceBefore=14)
    normal = styles["Normal"]
    small = ParagraphStyle("small", parent=normal, fontSize=9, textColor=colors.grey)

    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Unknown"
    now = datetime.utcnow()

    story = [
        Paragraph("MedMind AI", ParagraphStyle("brand", parent=normal, fontSize=10, textColor=BLUE)),
        Paragraph("Continuing Professional Development Report", title_style),
        Spacer(1, 0.3 * cm),
        HRFlowable(width="100%", thickness=2, color=BLUE),
        Spacer(1, 0.4 * cm),

        # Learner info
        Paragraph("<b>Learner Information</b>", h2_style),
        Table(
            [
                ["Name", full_name],
                ["Email", user.email or ""],
                ["Role", (user.role or "").capitalize()],
                ["Subscription", (user.subscription_tier or "free").capitalize()],
                ["Report generated", now.strftime("%d %B %Y, %H:%M UTC")],
            ],
            colWidths=[4 * cm, 13 * cm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 0.5 * cm),

        # Summary statistics
        Paragraph("<b>Learning Summary</b>", h2_style),
        Table(
            [
                ["Metric", "Value"],
                ["Modules completed", str(modules_completed)],
                ["Lessons completed", str(lessons_completed)],
                ["Flashcards reviewed", str(total_cards)],
                ["Flashcards mastered (≥ 80%)", str(cards_mastered)],
                ["XP earned", str(user.xp)],
                ["Current level", str(user.level)],
                ["Learning streak", f"{user.streak_days or 0} days"],
                ["Total CME credits (AMA PRA 1)", f"{total_cme:.1f}"],
            ],
            colWidths=[9 * cm, 8 * cm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 0.5 * cm),
    ]

    # Module detail table
    if progressions:
        story.append(Paragraph("<b>Module Progress Detail</b>", h2_style))
        rows = [["Module", "Completion %", "Lessons", "Last Activity"]]
        for p in sorted(progressions, key=lambda x: float(x.completion_percent or 0), reverse=True):
            mod = modules_map.get(str(p.module_id))
            rows.append([
                mod.title if mod else str(p.module_id)[:8],
                f"{float(p.completion_percent or 0):.0f}%",
                str(len(p.lessons_completed or [])),
                p.last_activity_at.strftime("%d %b %Y") if p.last_activity_at else "—",
            ])
        story.append(Table(
            rows,
            colWidths=[8 * cm, 3 * cm, 3 * cm, 3 * cm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]),
        ))
        story.append(Spacer(1, 0.5 * cm))

    # CME credits table
    if cme_credits:
        story.append(Paragraph("<b>CME Credits Log</b>", h2_style))
        cme_rows = [["Activity", "Type", "Credits", "Date"]]
        for c in cme_credits[:30]:  # cap at 30 rows to avoid giant PDFs
            cme_rows.append([
                c.activity_title or "",
                c.credit_type or "",
                f"{float(c.credits_earned):.1f}",
                c.completion_date.strftime("%d %b %Y") if c.completion_date else "—",
            ])
        story.append(Table(
            cme_rows,
            colWidths=[9 * cm, 3 * cm, 2 * cm, 3 * cm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ]),
        ))
        story.append(Spacer(1, 0.5 * cm))

    # Footer
    story += [
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#bfdbfe")),
        Spacer(1, 0.2 * cm),
        Paragraph(
            "This report was generated automatically by MedMind AI (medmind.pro). "
            "CME credits awarded as AMA PRA Category 1 credits™ equivalent. "
            "Please verify credit requirements with your local licensing body.",
            small,
        ),
    ]

    doc.build(story)
    buf.seek(0)

    filename = f"medmind_cpd_{full_name.replace(' ', '_')}_{now.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Daily Goal & Streak ──────────────────────────────────────────────────────

_DEFAULT_DAILY_GOAL_XP = 50  # XP needed to "complete" a day


@router.get("/daily")
async def get_daily_streak(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return today's XP, streak info, and daily goal progress."""
    from datetime import date as _date
    from sqlalchemy import cast, Date as _Date

    today = _date.today()

    # XP earned today (sum of XP events created today)
    xp_today_row = await db.execute(
        select(func.coalesce(func.sum(XPEvent.amount), 0))
        .where(
            XPEvent.user_id == user.id,
            cast(XPEvent.created_at, _Date) == today,
        )
    )
    xp_today = int(xp_today_row.scalar() or 0)

    goal_xp = int((user.preferences or {}).get("daily_goal_xp", _DEFAULT_DAILY_GOAL_XP))
    pct = min(100, round(xp_today / max(goal_xp, 1) * 100))

    return {
        "streak_days":    user.streak_days or 0,
        "longest_streak": user.longest_streak or 0,
        "xp_today":       xp_today,
        "daily_goal_xp":  goal_xp,
        "goal_pct":       pct,
        "goal_met":       xp_today >= goal_xp,
        "xp_total":       user.xp or 0,
        "level":          user.level or 1,
    }


@router.patch("/daily-goal")
async def set_daily_goal(
    goal_xp: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set user's daily XP goal (10–500 XP)."""
    goal_xp = max(10, min(500, goal_xp))
    prefs = dict(user.preferences or {})
    prefs["daily_goal_xp"] = goal_xp
    user.preferences = prefs
    await db.commit()
    return {"daily_goal_xp": goal_xp}
