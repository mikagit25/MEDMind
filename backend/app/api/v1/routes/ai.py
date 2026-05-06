"""AI tutor routes."""
import uuid
import json
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.core.database import get_db
from app.models.models import User, AIConversation, AIConversationMessage, UserProgress, Module
from app.schemas.schemas import AIAskRequest, AIAskResponse, ConversationOut, MessageOut
from app.api.deps import get_current_user
from app.services.ai_router import route_ai_request, route_ai_stream
from app.services.prompt_guard import sanitize_ai_message
from app.core.audit import audit
from app.core.redis_client import get_redis
from app.services.pubmed_service import search_pubmed, build_pubmed_context
from sqlalchemy import func

router = APIRouter(prefix="/ai", tags=["ai"])

LEVEL_NAMES = {1: "Beginner", 2: "Learner", 3: "Resident", 4: "Specialist", 5: "Expert", 6: "Master"}


async def _build_progress_context(user: User, db: AsyncSession) -> str:
    """Build a short learner-profile string injected into every AI system prompt."""
    try:
        prog_result = await db.execute(
            select(UserProgress).where(UserProgress.user_id == user.id)
        )
        all_progress = prog_result.scalars().all()
        if not all_progress:
            return ""

        total_lessons = sum(len(p.lessons_completed or []) for p in all_progress)
        modules_started = sum(1 for p in all_progress if (p.completion_percent or 0) > 0)

        # Find weak modules (started but < 50% completion)
        weak = [p for p in all_progress if 0 < float(p.completion_percent or 0) < 50]
        weak_ids = [p.module_id for p in weak[:3]]
        weak_titles: list[str] = []
        if weak_ids:
            mods = (await db.execute(
                select(Module.title).where(Module.id.in_(weak_ids))
            )).scalars().all()
            weak_titles = list(mods)

        level = user.level or 1
        xp = user.xp or 0
        streak = user.streak_days or 0
        level_name = LEVEL_NAMES.get(level, "Learner")

        lines = [
            f"\n\n## Learner Profile",
            f"- Level: {level} ({level_name}) | {xp} XP | {streak} day streak",
            f"- Lessons completed: {total_lessons} | Modules in progress: {modules_started}",
        ]
        if weak_titles:
            lines.append(f"- Needs reinforcement: {', '.join(weak_titles)}")
        lines.append(
            "Tailor your explanation to this learner's level. "
            "For beginners: use analogies, avoid jargon. "
            "For advanced: use precise terminology and cite guidelines."
        )
        return "\n".join(lines)
    except Exception:
        return ""

# Daily request limits per subscription tier
TIER_DAILY_LIMITS: dict[str, int | None] = {
    "free": 20,        # 20 questions/day — enough for casual learning
    "student": 100,    # 100/day — full study sessions
    "pro": None,       # unlimited
    "clinic": None,
    "lifetime": None,
}

# Hourly burst limits — prevents API cost spikes from automated abuse
TIER_HOURLY_LIMITS: dict[str, int | None] = {
    "free": 10,        # max 10/hour burst
    "student": 40,     # max 40/hour burst
    "pro": None,
    "clinic": None,
    "lifetime": None,
}


async def check_ai_rate_limit(user: User, db: AsyncSession) -> None:
    """Check daily + hourly AI request limits atomically via Redis pipeline.

    Two counters per user:
    - ai_daily:{user_id}  — resets at midnight UTC
    - ai_hourly:{user_id} — resets every hour

    Uses INCR+EXPIRE pipeline so check+increment is atomic (no race condition).
    On limit breach, the counter is rolled back so it reflects completed requests.
    """
    daily_limit = TIER_DAILY_LIMITS.get(user.subscription_tier, 20)
    hourly_limit = TIER_HOURLY_LIMITS.get(user.subscription_tier, 10)

    if daily_limit is None and hourly_limit is None:
        return  # unlimited tier — no checks needed

    redis = await get_redis()
    now = datetime.utcnow()
    seconds_till_midnight = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
    seconds_till_next_hour = 3600 - (now.minute * 60 + now.second)

    daily_key = f"ai_daily:{user.id}"
    hourly_key = f"ai_hourly:{user.id}"

    # One pipeline: increment both counters atomically
    pipe = redis.pipeline()
    if daily_limit is not None:
        await pipe.incr(daily_key)
        await pipe.expire(daily_key, seconds_till_midnight)
    if hourly_limit is not None:
        await pipe.incr(hourly_key)
        await pipe.expire(hourly_key, seconds_till_next_hour)
    results = await pipe.execute()

    idx = 0
    if daily_limit is not None:
        daily_count = results[idx]
        idx += 2  # INCR + EXPIRE = 2 results
        if daily_count > daily_limit:
            await redis.decr(daily_key)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Daily AI limit reached ({daily_limit} questions/day on "
                    f"{user.subscription_tier} plan). Resets at midnight UTC. "
                    "Upgrade for more access."
                ),
                headers={"Retry-After": str(seconds_till_midnight)},
            )

    if hourly_limit is not None:
        hourly_count = results[idx]
        if hourly_count > hourly_limit:
            await redis.decr(hourly_key)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Hourly AI limit reached ({hourly_limit} requests/hour). "
                    f"Resets in {seconds_till_next_hour // 60} minutes."
                ),
                headers={"Retry-After": str(seconds_till_next_hour)},
            )


@router.post("/ask", response_model=AIAskResponse)
async def ask_ai(
    data: AIAskRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data.message = sanitize_ai_message(data.message)
    await check_ai_rate_limit(user, db)
    # Get or create conversation
    conversation = None
    if data.conversation_id:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == data.conversation_id,
                AIConversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = AIConversation(
            user_id=user.id,
            specialty=data.specialty,
            mode=data.mode,
            title=data.message[:80],
        )
        db.add(conversation)
        await db.flush()

    # Load conversation history (last 10 messages — only role+content, skip heavy JSONB fields)
    msgs_result = await db.execute(
        select(AIConversationMessage)
        .options(load_only(AIConversationMessage.role, AIConversationMessage.content))
        .where(AIConversationMessage.conversation_id == conversation.id)
        .order_by(AIConversationMessage.created_at.desc())
        .limit(10)
    )
    recent_msgs = list(reversed(msgs_result.scalars().all()))
    history = [{"role": m.role, "content": m.content} for m in recent_msgs]

    # PubMed search
    pubmed_refs = []
    pubmed_context = ""
    if data.search_pubmed and user.subscription_tier != "free":
        pubmed_refs = await search_pubmed(data.message)
        pubmed_context = build_pubmed_context(pubmed_refs)

    # AI routing (db + conversation_id enable long-term memory)
    result = await route_ai_request(
        user=user,
        message=data.message,
        conversation_history=history,
        specialty=data.specialty,
        mode=data.mode,
        pubmed_context=pubmed_context,
        db=db,
        conversation_id=conversation.id,
    )

    # Save messages
    user_msg = AIConversationMessage(
        conversation_id=conversation.id,
        role="user",
        content=data.message,
    )
    ai_msg = AIConversationMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=result["reply"],
        pubmed_refs=pubmed_refs if pubmed_refs else None,
        model_used=result.get("model"),
        from_cache=result.get("from_cache", False),
        tokens_used=result.get("tokens", 0),
    )
    db.add(user_msg)
    db.add(ai_msg)

    # Update conversation stats
    conversation.model_used = result.get("model")
    if result.get("from_cache"):
        conversation.cached_responses += 1

    await audit(db, "ai_ask", user_id=user.id,
                resource_type="conversation", resource_id=conversation.id)
    await db.commit()

    return AIAskResponse(
        reply=result["reply"],
        conversation_id=conversation.id,
        model_used=result.get("model") or "system",
        from_cache=result.get("from_cache", False),
        pubmed_refs=pubmed_refs if pubmed_refs else None,
        xp_earned=2 if not result.get("error") else 0,
    )


@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIConversation)
        .where(AIConversation.user_id == user.id)
        .order_by(AIConversation.updated_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.post("/ask/stream")
async def ask_ai_stream(
    data: AIAskRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Server-Sent Events streaming endpoint for AI responses."""
    data.message = sanitize_ai_message(data.message)
    await check_ai_rate_limit(user, db)

    # Get or create conversation
    conversation = None
    if data.conversation_id:
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.id == data.conversation_id,
                AIConversation.user_id == user.id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        conversation = AIConversation(
            user_id=user.id,
            specialty=data.specialty,
            mode=data.mode,
            title=data.message[:80],
        )
        db.add(conversation)
        await db.flush()
        await db.commit()
        await db.refresh(conversation)

    # Load history (only role+content, skip heavy JSONB fields)
    msgs_result = await db.execute(
        select(AIConversationMessage)
        .options(load_only(AIConversationMessage.role, AIConversationMessage.content))
        .where(AIConversationMessage.conversation_id == conversation.id)
        .order_by(AIConversationMessage.created_at.desc())
        .limit(10)
    )
    recent_msgs = list(reversed(msgs_result.scalars().all()))
    history = [{"role": m.role, "content": m.content} for m in recent_msgs]

    # PubMed search
    pubmed_refs = []
    pubmed_context = ""
    if data.search_pubmed and user.subscription_tier != "free":
        pubmed_refs = await search_pubmed(data.message)
        pubmed_context = build_pubmed_context(pubmed_refs)

    # Build learner profile context
    progress_context = await _build_progress_context(user, db)

    conv_id = str(conversation.id)

    async def event_stream() -> AsyncGenerator[str, None]:
        full_reply = ""
        model_used = None

        try:
            # Send conversation_id first so frontend knows where to save
            yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id})}\n\n"

            async for chunk in route_ai_stream(
                user=user,
                message=data.message,
                conversation_history=history,
                specialty=data.specialty,
                mode=data.mode,
                pubmed_context=pubmed_context,
                progress_context=progress_context,
                language=data.language,
            ):
                if chunk.get("type") == "text":
                    text = chunk["text"]
                    full_reply += text
                    yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"
                elif chunk.get("type") == "model":
                    model_used = chunk["model"]
                elif chunk.get("type") == "error":
                    yield f"data: {json.dumps({'type': 'error', 'detail': chunk['detail']})}\n\n"
                    return

            # Save to DB after stream completes
            import uuid as _uuid
            ai_msg_uuid = _uuid.uuid4()
            user_msg = AIConversationMessage(
                conversation_id=conversation.id,
                role="user",
                content=data.message,
            )
            ai_msg = AIConversationMessage(
                id=ai_msg_uuid,
                conversation_id=conversation.id,
                role="assistant",
                content=full_reply,
                pubmed_refs=pubmed_refs if pubmed_refs else None,
                model_used=model_used,
                from_cache=False,
            )
            db.add(user_msg)
            db.add(ai_msg)
            await db.commit()

            yield f"data: {json.dumps({'type': 'done', 'model': model_used or 'system', 'message_id': str(ai_msg_uuid)})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership
    conv_result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == user.id,
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    result = await db.execute(
        select(AIConversationMessage)
        .where(AIConversationMessage.conversation_id == conversation_id)
        .order_by(AIConversationMessage.created_at)
    )
    return result.scalars().all()


@router.post("/feedback")
async def submit_feedback(
    message_id: UUID,
    rating: int,  # 1 = thumbs up, -1 = thumbs down
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if rating not in (1, -1):
        raise HTTPException(status_code=400, detail="Rating must be 1 or -1")

    result = await db.execute(
        select(AIConversationMessage)
        .join(AIConversation)
        .where(
            AIConversationMessage.id == message_id,
            AIConversation.user_id == user.id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.feedback = rating
    await db.commit()
    return {"status": "ok"}


# ============================================================
# CONCEPT EXPLANATION
# ============================================================
class ExplainRequest(BaseModel):
    level: Optional[str] = "intermediate"  # beginner | intermediate | expert
    context: Optional[str] = None           # optional module/lesson context


@router.post("/explain/{concept}")
async def explain_concept(
    concept: str,
    data: ExplainRequest = ExplainRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a structured explanation of a medical concept."""
    from app.prompts.tutor_prompts import explain_concept_prompt
    await check_ai_rate_limit(user, db)

    concept = sanitize_ai_message(concept, "concept")
    if data.context:
        data.context = sanitize_ai_message(data.context, "context")
    prompt = explain_concept_prompt(concept, data.level or "intermediate", data.context)
    response = await route_ai_request(
        message=prompt,
        user=user,
        db=db,
        conversation_id=None,
        specialty=None,
        mode="explain",
    )
    return {"concept": concept, "explanation": response.get("response", ""), "model": response.get("model")}


# ============================================================
# QUIZ MODE
# ============================================================
class QuizRequest(BaseModel):
    difficulty: Optional[str] = "medium"
    num_questions: int = 3
    previous_mistakes: Optional[list[str]] = None


@router.post("/quiz/{topic}")
async def quiz_mode(
    topic: str,
    data: QuizRequest = QuizRequest(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate oral exam questions on a medical topic."""
    from app.prompts.tutor_prompts import quiz_mode_prompt
    await check_ai_rate_limit(user, db)

    topic = sanitize_ai_message(topic, "topic")
    prompt = quiz_mode_prompt(topic, data.difficulty or "medium", data.previous_mistakes or [])
    response = await route_ai_request(
        message=prompt,
        user=user,
        db=db,
        conversation_id=None,
        specialty=topic,
        mode="quiz",
    )
    return {"topic": topic, "quiz": response.get("response", ""), "model": response.get("model")}


# ============================================================
# CASE DISCUSSION
# ============================================================
class CaseDiscussRequest(BaseModel):
    user_decision: str
    discussion_point: Optional[str] = None


@router.post("/case-discuss/{case_id}")
async def discuss_case(
    case_id: UUID,
    data: CaseDiscussRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Discuss a clinical case with the AI tutor."""
    from app.models.models import ClinicalCase
    from app.prompts.tutor_prompts import case_discussion_prompt
    await check_ai_rate_limit(user, db)

    data.user_decision = sanitize_ai_message(data.user_decision, "user_decision")
    if data.discussion_point:
        data.discussion_point = sanitize_ai_message(data.discussion_point, "discussion_point")

    case_result = await db.execute(select(ClinicalCase).where(ClinicalCase.id == case_id))
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Clinical case not found")

    case_data = {
        "title": case.title,
        "presentation": case.presentation,
        "diagnosis": case.diagnosis,
        "management": case.management,
    }
    prompt = case_discussion_prompt(case_data, data.user_decision, data.discussion_point)
    response = await route_ai_request(
        message=prompt,
        user=user,
        db=db,
        conversation_id=None,
        specialty=case.specialty,
        mode="case",
    )
    return {
        "case_id": str(case_id),
        "discussion": response.get("response", ""),
        "model": response.get("model"),
    }


