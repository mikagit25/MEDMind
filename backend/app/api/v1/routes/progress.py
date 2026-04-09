"""Progress & spaced repetition routes."""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models.models import (
    User, UserProgress, FlashcardReview, Flashcard, Lesson,
    Module, MCQQuestion, ClinicalCase, CMECredit
)
from app.schemas.schemas import (
    LessonCompleteRequest, LessonCompleteResponse,
    FlashcardReviewRequest, FlashcardReviewResponse,
    MCQAnswerRequest, MCQAnswerResponse, ProgressStats,
    CaseCompleteRequest, CaseCompleteResponse, ProgressHistoryItem,
)
from app.api.deps import get_current_user

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


async def add_xp(user: User, xp: int, db: AsyncSession):
    """Add XP to user, level up if needed, and update streak."""
    from datetime import date as _date
    user.xp += xp
    # Level thresholds: 0, 500, 2000, 5000, 12000, 25000
    thresholds = [0, 500, 2000, 5000, 12000, 25000]
    for i, threshold in enumerate(thresholds):
        if user.xp >= threshold:
            user.level = i + 1

    # Streak: if last_active_date is yesterday or earlier today, bump streak
    today = _date.today()
    last = user.last_active_date.date() if user.last_active_date else None
    if last is None or last < today:
        from datetime import timedelta
        if last == today - timedelta(days=1):
            user.streak_days = (user.streak_days or 0) + 1
        elif last != today:
            # Gap > 1 day — reset streak
            user.streak_days = 1
    user.last_active_date = datetime.utcnow()


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

    # Get or create user_progress record
    prog_result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user.id,
            UserProgress.module_id == lesson.module_id,
        )
    )
    progress = prog_result.scalar_one_or_none()

    if not progress:
        progress = UserProgress(user_id=user.id, module_id=lesson.module_id)
        db.add(progress)
        await db.flush()

    # Mark lesson as completed (idempotent)
    completed = list(progress.lessons_completed or [])
    if lesson.id not in completed:
        completed.append(lesson.id)
        progress.lessons_completed = completed
        progress.last_activity_at = datetime.utcnow()

        # Award XP
        await add_xp(user, XP_LESSON, db)

    # Recalculate module completion
    lessons_result = await db.execute(select(Lesson).where(Lesson.module_id == lesson.module_id))
    all_lessons = lessons_result.scalars().all()
    total = len(all_lessons)
    done = len(completed)
    completion_pct = (done / total * 100) if total > 0 else 0
    progress.completion_percent = completion_pct

    # CME credit for doctors — 0.5 AMA PRA Category 1 credit per lesson (idempotent)
    if user.role in ("doctor", "resident") and lesson.id not in (progress.lessons_completed or [])[:-1]:
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

    return LessonCompleteResponse(
        xp_earned=XP_LESSON,
        total_xp=user.xp,
        level=user.level,
        module_completion_percent=float(completion_pct),
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
        )
        db.add(review)

    # Apply SM-2
    new_ef, new_interval = calculate_sm2(
        float(review.ease_factor),
        review.interval_days,
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
        await add_xp(user, xp_earned, db)

    await db.commit()

    return FlashcardReviewResponse(
        flashcard_id=data.flashcard_id,
        next_review_at=review.next_review_at,
        interval_days=new_interval,
        ease_factor=new_ef,
        xp_earned=xp_earned,
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

    is_correct = data.selected_option.upper() == question.correct.upper()
    xp = XP_MCQ_HARD_CORRECT if (is_correct and question.difficulty == "hard") else (XP_MCQ_CORRECT if is_correct else 0)

    if xp:
        await add_xp(user, xp, db)
        await db.commit()

    return MCQAnswerResponse(
        correct=is_correct,
        correct_answer=question.correct,
        explanation=question.explanation or "",
        xp_earned=xp,
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

    return ProgressStats(
        total_xp=user.xp,
        level=user.level,
        streak_days=user.streak_days,
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
    await add_xp(user, xp, db)
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
        User.level,
        User.xp,
        User.streak_days,
    ).where(User.is_active == True)

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
        entry = {
            "rank": i,
            "user_id": str(row.id),
            "name": f"{row.first_name or ''} {(row.last_name or '')[:1]}.".strip(),
            "level": row.level,
            "xp": row.xp,
            "streak_days": row.streak_days or 0,
            "is_me": str(row.id) == str(user.id),
        }
        if entry["is_me"]:
            my_rank = i
        board.append(entry)

    return {
        "period": period,
        "my_rank": my_rank,
        "total_shown": len(board),
        "leaderboard": board,
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
