"""AI tutor routes."""
import uuid
import json
from datetime import datetime
from typing import List, Optional, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.core.database import get_db
from app.models.models import User, AIConversation, AIConversationMessage, UserProgress, Module, Lesson
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
    "free": 5,         # 5 questions/day (per TZ spec)
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

    try:
        redis = await get_redis()
    except Exception:
        return  # Redis unavailable → allow request (fail open)
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


@router.get("/conversations/{conversation_id}/export-pdf")
async def export_conversation_pdf(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export a conversation as a formatted PDF study summary."""
    import io
    import re as _re
    from datetime import timezone
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    # Verify ownership
    conv_result = await db.execute(
        select(AIConversation).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == user.id,
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs_result = await db.execute(
        select(AIConversationMessage)
        .where(AIConversationMessage.conversation_id == conversation_id)
        .order_by(AIConversationMessage.created_at)
    )
    messages = msgs_result.scalars().all()

    # ── Build PDF ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    RED   = colors.HexColor("#C0392B")
    GRAY  = colors.HexColor("#6B7280")
    LGRAY = colors.HexColor("#F3F4F6")
    DGRAY = colors.HexColor("#1F2937")
    BLUE  = colors.HexColor("#2563EB")

    styles = getSampleStyleSheet()
    title_style  = ParagraphStyle("title",  fontSize=18, fontName="Helvetica-Bold", textColor=DGRAY, spaceAfter=4)
    meta_style   = ParagraphStyle("meta",   fontSize=9,  fontName="Helvetica",      textColor=GRAY,  spaceAfter=2)
    label_style  = ParagraphStyle("label",  fontSize=8,  fontName="Helvetica-Bold", textColor=GRAY,  spaceBefore=8, spaceAfter=2)
    user_style   = ParagraphStyle("user",   fontSize=10, fontName="Helvetica",      textColor=DGRAY, leading=14)
    ai_style     = ParagraphStyle("ai",     fontSize=10, fontName="Helvetica",      textColor=DGRAY, leading=14)
    ref_style    = ParagraphStyle("ref",    fontSize=8,  fontName="Helvetica",      textColor=BLUE,  spaceAfter=2)
    footer_style = ParagraphStyle("footer", fontSize=8,  fontName="Helvetica-Oblique", textColor=GRAY, alignment=TA_CENTER)

    def clean_md(text: str) -> str:
        """Strip markdown to plain text for PDF."""
        text = _re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = _re.sub(r'\*(.+?)\*',     r'\1', text)
        text = _re.sub(r'#{1,6}\s*',     '',    text)
        text = _re.sub(r'`(.+?)`',       r'\1', text)
        text = _re.sub(r'^\s*[-*]\s+',   '• ',  text, flags=_re.MULTILINE)
        return text.strip()

    story = []

    # Header
    story.append(Paragraph("MedMind AI", ParagraphStyle("brand", fontSize=11, fontName="Helvetica-Bold", textColor=RED)))
    story.append(Spacer(1, 4))
    title = conv.title or "AI Tutor Session"
    story.append(Paragraph(title[:120], title_style))

    date_str = conv.created_at.strftime("%B %d, %Y") if conv.created_at else ""
    mode_str = (conv.mode or "tutor").replace("_", " ").title()
    spec_str = f" · {conv.specialty}" if conv.specialty else ""
    story.append(Paragraph(f"{date_str} · {mode_str}{spec_str}", meta_style))
    story.append(HRFlowable(width="100%", thickness=1, color=RED, spaceAfter=12))

    # Messages
    all_refs: list[dict] = []
    for msg in messages:
        if msg.role == "user":
            story.append(Paragraph("YOU", label_style))
            story.append(
                Table(
                    [[Paragraph(clean_md(msg.content), user_style)]],
                    colWidths=["100%"],
                    style=TableStyle([
                        ("BACKGROUND", (0,0), (-1,-1), LGRAY),
                        ("ROUNDEDCORNERS", (0,0), (-1,-1), [6,6,6,6]),
                        ("TOPPADDING",    (0,0), (-1,-1), 8),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                        ("LEFTPADDING",   (0,0), (-1,-1), 10),
                        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
                    ]),
                )
            )
        else:
            story.append(Paragraph("MEDMIND AI", label_style))
            story.append(
                Table(
                    [[Paragraph(clean_md(msg.content), ai_style)]],
                    colWidths=["100%"],
                    style=TableStyle([
                        ("BACKGROUND", (0,0), (-1,-1), colors.white),
                        ("BOX",        (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                        ("TOPPADDING",    (0,0), (-1,-1), 8),
                        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
                        ("LEFTPADDING",   (0,0), (-1,-1), 10),
                        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
                    ]),
                )
            )
            if msg.pubmed_refs:
                all_refs.extend(msg.pubmed_refs)
        story.append(Spacer(1, 6))

    # References
    seen_pmids: set = set()
    unique_refs = [r for r in all_refs if r.get("pmid") not in seen_pmids and not seen_pmids.add(r["pmid"])]
    if unique_refs:
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceBefore=8, spaceAfter=8))
        story.append(Paragraph("REFERENCES", label_style))
        for ref in unique_refs[:8]:
            story.append(Paragraph(
                f"• {ref.get('title','?')} ({ref.get('year','')}) — PMID {ref.get('pmid','')}",
                ref_style,
            ))

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY, spaceAfter=6))
    story.append(Paragraph(
        "Educational content only — not for clinical decisions. Always verify with a licensed clinician. "
        f"Generated by MedMind AI · medmind.pro · {date_str}",
        footer_style,
    ))

    doc.build(story)
    buf.seek(0)

    safe_title = _re.sub(r'[^a-zA-Z0-9_-]', '_', (conv.title or "session")[:40])
    filename = f"medmind_{safe_title}.pdf"

    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
# LESSON MCQ GENERATION
# ============================================================

class GeneratedMCQ(BaseModel):
    question: str
    options: dict  # {"A": ..., "B": ..., "C": ..., "D": ...}
    correct: str   # "A" | "B" | "C" | "D"
    explanation: str

class LessonQuizResponse(BaseModel):
    lesson_id: str
    lesson_title: str
    questions: List[GeneratedMCQ]
    model: Optional[str] = None


@router.post("/lessons/{lesson_id}/generate-quiz", response_model=LessonQuizResponse)
async def generate_lesson_quiz(
    lesson_id: UUID,
    difficulty: str = "medium",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate 5 USMLE-style MCQ questions from a lesson's content using Claude Haiku."""
    from app.prompts.tutor_prompts import lesson_mcq_prompt, LESSON_MCQ_SYSTEM
    from app.services.content_sanitizer import sanitize_for_llm_context

    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"

    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    await check_ai_rate_limit(user, db)

    # Extract plain text from lesson content (blocks or legacy dict)
    lesson_text = sanitize_for_llm_context(lesson.content, max_chars=3000)

    prompt = lesson_mcq_prompt(lesson.title or "Medical Lesson", lesson_text, difficulty)

    # MCQ generation: full key cascade (Claude → Gemini → Cerebras → SambaNova → Groq → Ollama)
    from app.services.ai_router import call_generation_ai
    try:
        raw, model_label = await call_generation_ai(
            system=LESSON_MCQ_SYSTEM,
            user_message=prompt,
            max_tokens=2500,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    # Parse JSON response
    try:
        # Strip any accidental markdown fences
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed = json.loads(clean)
        questions_raw = parsed.get("questions", [])
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=502, detail="AI returned malformed response. Please try again.")

    questions = []
    for q in questions_raw[:5]:
        try:
            questions.append(GeneratedMCQ(
                question=str(q.get("question", "")),
                options={k: str(v) for k, v in q.get("options", {}).items()},
                correct=str(q.get("correct", "A")),
                explanation=str(q.get("explanation", "")),
            ))
        except Exception:
            continue

    if not questions:
        raise HTTPException(status_code=502, detail="AI returned no valid questions. Please try again.")

    return LessonQuizResponse(
        lesson_id=str(lesson_id),
        lesson_title=lesson.title or "",
        questions=questions,
        model=model_label,
    )


# ============================================================
# CASE DISCUSSION
# ============================================================
class CaseDiscussRequest(BaseModel):
    user_decision: str
    discussion_point: Optional[str] = None


# ============================================================
# DOCUMENT / IMAGE ANALYSIS
# ============================================================

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
SUPPORTED_TYPES = SUPPORTED_IMAGE_TYPES | {"application/pdf", "text/plain"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _extract_pdf_text(data: bytes) -> str:
    """Extract plain text from a PDF using pypdf."""
    import io
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages[:20]]
        return "\n\n".join(p for p in pages if p.strip())
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {e}")


@router.post("/analyze-document")
async def analyze_document(
    file: UploadFile = File(...),
    question: str = Form(default="Please analyze this medical document and explain the key findings for educational purposes."),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Analyze a medical document (PDF, image, text) using AI.
    Educational tool — teaches interpretation of lab results, ECGs, imaging reports, etc.
    """
    from app.prompts.tutor_prompts import DOCUMENT_ANALYSIS_SYSTEM
    from app.services.ai_router import call_claude_structured, call_claude_vision

    await check_ai_rate_limit(user, db)

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type}. Supported: images (JPEG/PNG/WEBP), PDF, plain text.",
        )

    # Read file data
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10 MB.")
    if len(data) == 0:
        raise HTTPException(status_code=422, detail="File is empty.")

    # Sanitize question
    question = sanitize_ai_message(question, "question")

    # Select model — Sonnet for pro/clinic (better at medical images), Haiku otherwise
    model = "claude-sonnet-4-6" if user.subscription_tier in ("pro", "clinic", "lifetime") else "claude-haiku-4-5-20251001"

    try:
        if content_type in SUPPORTED_IMAGE_TYPES:
            # Vision path
            analysis, model_used = await call_claude_vision(
                system=DOCUMENT_ANALYSIS_SYSTEM,
                image_data=data,
                media_type=content_type,
                question=question,
                model=model,
                max_tokens=3000,
            )
        elif content_type == "application/pdf":
            # PDF text extraction path
            text = _extract_pdf_text(data)
            if not text.strip():
                raise HTTPException(
                    status_code=422,
                    detail="Could not extract text from PDF. The file may be scanned/image-based. Try uploading as an image instead.",
                )
            prompt = f"Document content:\n\n{text[:6000]}\n\n---\nUser question: {question}"
            analysis, model_used = await call_claude_structured(
                system=DOCUMENT_ANALYSIS_SYSTEM,
                user_message=prompt,
                model=model,
                max_tokens=3000,
            )
        else:
            # Plain text
            text = data.decode("utf-8", errors="replace")
            prompt = f"Document content:\n\n{text[:6000]}\n\n---\nUser question: {question}"
            analysis, model_used = await call_claude_structured(
                system=DOCUMENT_ANALYSIS_SYSTEM,
                user_message=prompt,
                model=model,
                max_tokens=3000,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")

    await audit(db, "ai_document_analysis", user_id=user.id, resource_type="user", resource_id=user.id)

    return {
        "analysis": analysis,
        "filename": file.filename,
        "file_type": content_type,
        "model": model_used,
        "disclaimer": "Educational analysis only — not a clinical report. Always review with a qualified clinician.",
    }


# ============================================================
# DIFFERENTIAL DIAGNOSIS
# ============================================================

class DifferentialRequest(BaseModel):
    case_description: str
    language: Optional[str] = "en"


class DifferentialItem(BaseModel):
    diagnosis: str
    icd: Optional[str] = None
    reasoning: str
    next_steps: Optional[str] = None


class CantMissItem(BaseModel):
    diagnosis: str
    icd: Optional[str] = None
    urgency: str
    red_flags: str
    action: str


class ExpandedItem(BaseModel):
    diagnosis: str
    icd: Optional[str] = None
    reasoning: str


class DifferentialResponse(BaseModel):
    reasoning: str
    most_likely: List[DifferentialItem]
    expanded: List[ExpandedItem]
    cant_miss: List[CantMissItem]
    recommended_workup: List[str]
    pubmed_refs: Optional[List[dict]] = None
    model: Optional[str] = None


@router.post("/differential", response_model=DifferentialResponse)
async def differential_diagnosis(
    data: DifferentialRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a structured differential diagnosis from a clinical case description."""
    from app.prompts.tutor_prompts import DIFFERENTIAL_SYSTEM, differential_prompt
    from app.services.ai_router import call_claude_structured, call_generation_ai

    data.case_description = sanitize_ai_message(data.case_description)
    await check_ai_rate_limit(user, db)

    # Use Sonnet for pro/clinic, Haiku for student/free
    model = "claude-sonnet-4-6" if user.subscription_tier in ("pro", "clinic", "lifetime") else "claude-haiku-4-5-20251001"
    prompt = differential_prompt(data.case_description, data.language or "en")

    try:
        # Try Claude first (highest quality for differential diagnosis)
        raw, model_label = await call_claude_structured(
            system=DIFFERENTIAL_SYSTEM,
            user_message=prompt,
            model=model,
            max_tokens=2500,
        )
    except Exception:
        # Fall back to full provider cascade if Claude is unavailable/out of credits
        try:
            raw, model_label = await call_generation_ai(
                system=DIFFERENTIAL_SYSTEM,
                user_message=prompt,
                max_tokens=2500,
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    # Parse JSON
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed = json.loads(clean)
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=502, detail="AI returned malformed response. Please try again.")

    # PubMed refs for paid users
    pubmed_refs = None
    if user.subscription_tier != "free":
        try:
            pubmed_refs = await search_pubmed(data.case_description)
        except Exception:
            pass

    await audit(db, "ai_differential", user_id=user.id, resource_type="user", resource_id=user.id)

    return DifferentialResponse(
        reasoning=parsed.get("reasoning", ""),
        most_likely=[DifferentialItem(**d) for d in parsed.get("most_likely", [])],
        expanded=[ExpandedItem(**d) for d in parsed.get("expanded", [])],
        cant_miss=[CantMissItem(**d) for d in parsed.get("cant_miss", [])],
        recommended_workup=parsed.get("recommended_workup", []),
        pubmed_refs=pubmed_refs,
        model=model_label,
    )


# ============================================================
# PATIENT HANDOUT GENERATOR
# ============================================================

class HandoutRequest(BaseModel):
    condition: str
    language: Optional[str] = "en"


class PatientHandoutResponse(BaseModel):
    condition: str
    what_is_it: str
    how_common: Optional[str] = None
    causes: List[str]
    symptoms: List[str]
    diagnosis: Optional[str] = None
    treatment_overview: str
    lifestyle_tips: List[str]
    when_to_see_doctor: List[str]
    warning_signs: List[str]
    model: Optional[str] = None


@router.post("/handout", response_model=PatientHandoutResponse)
async def generate_handout(
    data: HandoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a plain-language patient education handout for a medical condition."""
    from app.prompts.tutor_prompts import HANDOUT_SYSTEM, handout_prompt

    data.condition = sanitize_ai_message(data.condition, "condition")
    await check_ai_rate_limit(user, db)

    prompt = handout_prompt(data.condition, data.language or "en")

    from app.services.ai_router import call_generation_ai
    try:
        raw, model_label = await call_generation_ai(
            system=HANDOUT_SYSTEM,
            user_message=prompt,
            max_tokens=2000,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed = json.loads(clean)
    except (json.JSONDecodeError, AttributeError):
        raise HTTPException(status_code=502, detail="AI returned malformed response. Please try again.")

    await audit(db, "ai_handout", user_id=user.id, resource_type="user", resource_id=user.id)

    return PatientHandoutResponse(
        condition=parsed.get("condition", data.condition),
        what_is_it=parsed.get("what_is_it", ""),
        how_common=parsed.get("how_common"),
        causes=parsed.get("causes", []),
        symptoms=parsed.get("symptoms", []),
        diagnosis=parsed.get("diagnosis"),
        treatment_overview=parsed.get("treatment_overview", ""),
        lifestyle_tips=parsed.get("lifestyle_tips", []),
        when_to_see_doctor=parsed.get("when_to_see_doctor", []),
        warning_signs=parsed.get("warning_signs", []),
        model=model_label,
    )


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


