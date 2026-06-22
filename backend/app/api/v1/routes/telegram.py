"""Telegram bot webhook — MedMind AI assistant.

Webhook: POST /api/v1/telegram/webhook
Setup:   python3 -m app.scripts.telegram_setup  (run once after deploy)

Free tier for all Telegram users: 10 messages/day via Groq.
Paid tier: link account via /link command → uses subscription limits + Claude.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])

TG_API = "https://api.telegram.org/bot{token}/{method}"
DAILY_FREE_LIMIT = 10
BOT_NAME = "MedMind AI"

# ── Mode registry ─────────────────────────────────────────────────────────────
MODES: dict[str, str] = {
    "tutor":          "🎓 Tutor — explains medical topics",
    "case":           "🩺 Case — clinical case discussion",
    "patient":        "🏥 Patient — plain language, no jargon",
    "differential":   "🔬 Differential Dx — structured differentials",
    "second_opinion": "⚖️ Second Opinion — guideline review",
}

DEFAULT_MODE = "tutor"

# ── System prompts (Telegram-optimised: shorter, chat-friendly) ───────────────
TG_SYSTEM_PROMPTS: dict[str, str] = {
    "tutor": (
        "You are MedMind AI — a concise medical tutor in a Telegram chat. "
        "Give focused, educational answers in 3-5 short paragraphs max. "
        "Use **bold** for key terms. No long headers. End with one clinical pearl."
    ),
    "case": (
        "You are presenting a clinical case step-by-step in Telegram. "
        "Start with chief complaint + age/sex. Ask for the student's assessment. "
        "Keep each message short (fits a phone screen). "
        "Reveal information gradually as the student requests it."
    ),
    "patient": (
        "You are a friendly health educator in Telegram. Plain language only. "
        "No jargon, no diagnoses, always recommend seeing a real doctor. "
        "Keep responses short (3-4 sentences). "
        "For emergencies, first line MUST say: call 112/911 immediately."
    ),
    "differential": (
        "You are a clinical reasoning assistant in Telegram. "
        "Given a case, list: Most Likely (2-3), Expanded (2-3), Can't Miss (1-2). "
        "Use bullet format. Keep each entry to one line. "
        "End with 3 key investigations."
    ),
    "second_opinion": (
        "You are a medical educator reviewing a clinical plan in Telegram. "
        "Explain what guidelines say, what aligns with evidence, and 2-3 questions "
        "the user could ask their doctor. Never say the doctor is wrong. Short and clear."
    ),
}

# ── Telegram API helpers ──────────────────────────────────────────────────────

async def tg_call(method: str, payload: dict) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(TG_API.format(token=token, method=method), json=payload)
            return r.json()
        except Exception as e:
            logger.warning(f"Telegram API error ({method}): {e}")
            return {}


async def send_message(chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    # Telegram limit: 4096 chars per message
    if len(text) > 4000:
        text = text[:3990] + "\n\n…_(truncated)_"
    await tg_call("sendMessage", {
        "chat_id":    chat_id,
        "text":       text,
        "parse_mode": parse_mode,
    })


async def send_typing(chat_id: int) -> None:
    await tg_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})


# ── Redis helpers ─────────────────────────────────────────────────────────────

async def _rate_key(chat_id: int) -> tuple[str, int]:
    """Returns (redis_key, seconds_till_midnight)."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    secs = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
    return f"tg_daily:{chat_id}", secs


async def check_rate_limit(chat_id: int) -> tuple[bool, int]:
    """Returns (allowed, remaining). Increments counter atomically."""
    try:
        redis = await get_redis()
        key, ttl = await _rate_key(chat_id)
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, ttl)
        remaining = max(0, DAILY_FREE_LIMIT - count)
        return count <= DAILY_FREE_LIMIT, remaining
    except Exception:
        return True, DAILY_FREE_LIMIT  # fail open


async def get_mode(chat_id: int) -> str:
    try:
        redis = await get_redis()
        val = await redis.get(f"tg_mode:{chat_id}")
        return (val.decode() if val else DEFAULT_MODE)
    except Exception:
        return DEFAULT_MODE


async def set_mode(chat_id: int, mode: str) -> None:
    try:
        redis = await get_redis()
        await redis.set(f"tg_mode:{chat_id}", mode, ex=86400 * 30)
    except Exception:
        pass


async def get_history(chat_id: int) -> list[dict]:
    """Last 6 messages for context (3 turns)."""
    try:
        redis = await get_redis()
        raw = await redis.get(f"tg_history:{chat_id}")
        return json.loads(raw) if raw else []
    except Exception:
        return []


async def save_history(chat_id: int, history: list[dict]) -> None:
    try:
        redis = await get_redis()
        await redis.set(f"tg_history:{chat_id}", json.dumps(history[-12:]), ex=3600 * 6)
    except Exception:
        pass


# ── Linked account lookup ─────────────────────────────────────────────────────

async def get_linked_user(chat_id: int) -> Optional[User]:
    """Return User if this chat_id is linked to a MedMind account."""
    try:
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.telegram_chat_id == str(chat_id))
            )
            return result.scalar_one_or_none()
    except Exception:
        return None


# ── AI call ───────────────────────────────────────────────────────────────────

async def call_ai(mode: str, user_message: str, history: list[dict], linked_user: Optional[User]) -> str:
    """Route to Groq (free) or Claude (linked paid user)."""
    system = TG_SYSTEM_PROMPTS.get(mode, TG_SYSTEM_PROMPTS["tutor"])
    messages = history + [{"role": "user", "content": user_message}]

    # Paid linked user → Claude
    if linked_user and linked_user.subscription_tier in ("pro", "clinic", "lifetime", "student"):
        try:
            from app.services.ai_router import call_claude_structured
            model = "claude-sonnet-4-6" if linked_user.subscription_tier in ("pro", "clinic", "lifetime") else "claude-haiku-4-5-20251001"
            reply, _ = await call_claude_structured(
                system=system,
                user_message="\n\n".join(
                    f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
                    for m in messages
                ),
                model=model,
                max_tokens=1000,
            )
            return reply
        except Exception as e:
            logger.warning(f"Claude failed for linked user, falling back to Groq: {e}")

    # Free → Groq with KEY_1/KEY_2 rotation
    from app.core.config import settings as _s
    keys = [k for k in [_s.GROQ_API_KEY, getattr(_s, "GROQ_API_KEY_2", None)] if k]
    if not keys:
        return "⚠️ AI service temporarily unavailable. Please try again later."

    groq_messages = [{"role": "system", "content": system}] + messages
    last_error = ""
    async with httpx.AsyncClient(timeout=30) as client:
        for key in keys:
            try:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model":       getattr(_s, "GROQ_MODEL", "llama-3.3-70b-versatile"),
                        "messages":    groq_messages,
                        "max_tokens":  800,
                        "temperature": 0.7,
                    },
                )
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
                last_error = f"Groq {r.status_code}"
            except Exception as e:
                last_error = str(e)

    return f"⚠️ AI temporarily unavailable ({last_error}). Please try again."


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(chat_id: int, first_name: str) -> None:
    text = (
        f"👋 *Welcome to {BOT_NAME}, {first_name}!*\n\n"
        "I'm an AI medical education assistant — ask me anything about medicine, "
        "clinical cases, drug mechanisms, or get plain-language health explanations.\n\n"
        "*Commands:*\n"
        "/help — show all commands\n"
        "/mode — switch AI mode\n"
        "/status — your daily usage\n"
        "/new — start a fresh conversation\n"
        "/link — connect your MedMind account for unlimited access\n\n"
        f"*Free tier:* {DAILY_FREE_LIMIT} messages/day · powered by Llama 3.3\n"
        "Upgrade at medmind.pro for Claude Sonnet + unlimited access.\n\n"
        "⚕️ _Educational use only — not a substitute for clinical advice._"
    )
    await send_message(chat_id, text)


async def cmd_help(chat_id: int) -> None:
    modes_text = "\n".join(f"  `{k}` — {v}" for k, v in MODES.items())
    text = (
        f"*{BOT_NAME} — Commands*\n\n"
        "/start — welcome message\n"
        "/help — this message\n"
        f"/mode `<mode>` — switch mode:\n{modes_text}\n\n"
        "/status — daily message count\n"
        "/new — clear conversation history\n"
        "/link — connect MedMind account\n\n"
        "💬 *Just type any medical question* to get an answer in the current mode.\n\n"
        "⚕️ _Educational only · medmind.pro_"
    )
    await send_message(chat_id, text)


async def cmd_mode(chat_id: int, args: str) -> None:
    mode = args.strip().lower()
    if mode not in MODES:
        modes_list = "\n".join(f"• `{k}` — {v}" for k, v in MODES.items())
        await send_message(chat_id, f"Available modes:\n{modes_list}\n\nUsage: `/mode tutor`")
        return
    await set_mode(chat_id, mode)
    await save_history(chat_id, [])  # clear history on mode switch
    await send_message(chat_id, f"✅ Mode switched to *{MODES[mode]}*\n\nConversation history cleared. Ask your first question!")


async def cmd_status(chat_id: int, linked_user: Optional[User]) -> None:
    try:
        redis = await get_redis()
        key, _ = await _rate_key(chat_id)
        raw = await redis.get(key)
        used = int(raw) if raw else 0
    except Exception:
        used = 0

    mode = await get_mode(chat_id)
    if linked_user:
        tier = linked_user.subscription_tier or "free"
        limit_text = "unlimited" if tier in ("pro", "clinic", "lifetime") else f"{DAILY_FREE_LIMIT - used} remaining"
        text = (
            f"*Your Status*\n\n"
            f"👤 Linked account: {linked_user.email}\n"
            f"📊 Tier: {tier.title()}\n"
            f"💬 Today: {used} messages · {limit_text}\n"
            f"🎯 Mode: {MODES.get(mode, mode)}"
        )
    else:
        remaining = max(0, DAILY_FREE_LIMIT - used)
        text = (
            f"*Your Status*\n\n"
            f"💬 Today: {used}/{DAILY_FREE_LIMIT} messages · {remaining} remaining\n"
            f"🎯 Mode: {MODES.get(mode, mode)}\n\n"
            f"🔗 Link your MedMind account with /link for more access."
        )
    await send_message(chat_id, text)


async def cmd_new(chat_id: int) -> None:
    await save_history(chat_id, [])
    mode = await get_mode(chat_id)
    await send_message(chat_id, f"🔄 Conversation cleared. Still in *{MODES.get(mode, mode)}* mode.")


async def cmd_link(chat_id: int) -> None:
    import hashlib, time as _t
    token = hashlib.sha256(f"{chat_id}:{_t.time()}:{settings.JWT_SECRET_KEY}".encode()).hexdigest()[:32]
    try:
        redis = await get_redis()
        await redis.set(f"tg_link:{token}", str(chat_id), ex=600)
    except Exception:
        pass
    link_url = f"https://medmind.pro/link-telegram?token={token}"
    text = (
        f"🔗 *Link your MedMind account*\n\n"
        f"Click the link below, log in, and your Telegram will be connected:\n\n"
        f"{link_url}\n\n"
        f"⏱ Link expires in 10 minutes.\n"
        f"Don't have an account? Register at medmind.pro"
    )
    await send_message(chat_id, text, parse_mode="Markdown")


# ── Account linking endpoint (called by /link-telegram frontend page) ─────────

from pydantic import BaseModel
from app.api.deps import get_current_user as _get_current_user


class LinkTokenBody(BaseModel):
    token: str


@router.post("/link-account")
async def link_account(
    body: LinkTokenBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    redis = await get_redis()
    chat_id_bytes = await redis.get(f"tg_link:{body.token}")
    if not chat_id_bytes:
        raise HTTPException(status_code=400, detail="Link expired or invalid. Use /link in @Medmindaibot to get a new one.")
    chat_id = chat_id_bytes.decode()
    existing = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
    other = existing.scalar_one_or_none()
    if other and other.id != current_user.id:
        raise HTTPException(status_code=409, detail="This Telegram account is already linked to another MedMind user.")
    current_user.telegram_chat_id = chat_id
    db.add(current_user)
    await db.commit()
    await redis.delete(f"tg_link:{body.token}")
    logger.info("Telegram linked: user=%s chat_id=%s", current_user.email, chat_id)
    return {"ok": True, "email": current_user.email}


# ── Main webhook handler ──────────────────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Receive updates from Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    # Verify secret token header (set during webhook registration)
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if settings.TELEGRAM_WEBHOOK_SECRET and secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")

    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    # Only handle regular messages
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id    = message["chat"]["id"]
    text       = (message.get("text") or "").strip()
    first_name = message.get("from", {}).get("first_name", "there")

    if not text:
        return {"ok": True}

    # Route commands
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd   = parts[0].lower().split("@")[0]  # strip @botname suffix
        args  = parts[1] if len(parts) > 1 else ""

        if cmd == "/start":
            await cmd_start(chat_id, first_name)
        elif cmd == "/help":
            await cmd_help(chat_id)
        elif cmd == "/mode":
            await cmd_mode(chat_id, args)
        elif cmd == "/status":
            linked = await get_linked_user(chat_id)
            await cmd_status(chat_id, linked)
        elif cmd == "/new":
            await cmd_new(chat_id)
        elif cmd == "/link":
            await cmd_link(chat_id)
        else:
            await send_message(chat_id, "Unknown command. Use /help to see available commands.")
        return {"ok": True}

    # Regular message → AI
    linked_user = await get_linked_user(chat_id)

    # Rate limiting (skip for paid linked users)
    if not (linked_user and linked_user.subscription_tier in ("pro", "clinic", "lifetime")):
        allowed, remaining = await check_rate_limit(chat_id)
        if not allowed:
            await send_message(
                chat_id,
                f"⏳ Daily limit reached ({DAILY_FREE_LIMIT} messages/day).\n\n"
                "Resets at midnight UTC. Link your MedMind Pro account with /link for unlimited access."
            )
            return {"ok": True}
    else:
        remaining = None

    # Show typing indicator
    await send_typing(chat_id)

    # Get mode and history
    mode    = await get_mode(chat_id)
    history = await get_history(chat_id)

    # Call AI
    try:
        reply = await call_ai(mode, text, history, linked_user)
    except Exception as e:
        logger.error(f"AI call failed for chat {chat_id}: {e}")
        reply = "⚠️ Something went wrong. Please try again."

    # Save history
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant", "content": reply})
    await save_history(chat_id, history)

    # Append usage hint for free users
    if remaining is not None and remaining <= 3:
        reply += f"\n\n_{remaining} messages left today · medmind.pro for unlimited_"

    await send_message(chat_id, reply)
    return {"ok": True}
