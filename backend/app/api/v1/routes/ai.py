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
from app.models.models import User, AIConversation, AIConversationMessage
from app.schemas.schemas import AIAskRequest, AIAskResponse, ConversationOut, MessageOut
from app.api.deps import get_current_user
from app.services.ai_router import route_ai_request, route_ai_stream
from app.services.prompt_guard import sanitize_ai_message
from app.core.audit import audit
from app.core.redis_client import get_redis
from app.services.pubmed_service import search_pubmed, build_pubmed_context

router = APIRouter(prefix="/ai", tags=["ai"])

# Per-tier daily limits (from config: AI_LIMIT_FREE=5, AI_LIMIT_STUDENT=50, AI_LIMIT_PRO=999999)
TIER_DAILY_LIMITS = {
    "free": 5,
    "student": 50,
    "pro": None,      # None = unlimited
    "clinic": None,
    "lifetime": None,
}


async def check_ai_rate_limit(user: User, db: AsyncSession) -> None:
    """Check and atomically increment the daily AI request counter via Redis.

    Uses Redis pipeline (INCR + EXPIRE) so the check and increment are atomic —
    no race condition between concurrent requests.  The counter resets at midnight.
    """
    limit = TIER_DAILY_LIMITS.get(user.subscription_tier, 5)
    if limit is None:
        return  # unlimited tier

    redis = await get_redis()
    rate_key = f"ai_requests:{user.id}"
    now = datetime.utcnow()
    seconds_till_midnight = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)

    # Atomic: increment first, then check — prevents concurrent bypass
    pipe = redis.pipeline()
    await pipe.incr(rate_key)
    await pipe.expire(rate_key, seconds_till_midnight)
    results = await pipe.execute()
    new_count = results[0]

    if new_count > limit:
        # Roll back the increment so the counter reflects actual completed requests
        await redis.decr(rate_key)
        raise HTTPException(
            status_code=429,
            detail=f"Daily AI limit reached ({limit} questions/day on {user.subscription_tier} plan). Upgrade for more.",
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


