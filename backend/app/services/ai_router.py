"""AI request router — selects model and checks cache/rate limits.

Routing strategy (per TZ):
  Free tier   → Ollama (local, zero cost, Qwen/Llama/Mistral) → Gemini Flash → Groq → reject
  Paid tiers  → Simple questions: Ollama → Gemini → Groq (free, fast, saves cost)
              → Complex questions: Claude Haiku (student) or Sonnet (pro/clinic/lifetime)

Ollama setup (recommended — truly free, local, no API key):
  brew install ollama
  ollama pull qwen3:8b       # 8B, hybrid thinking, best quality (needs ~6GB RAM)
  ollama pull qwen3:4b       # 4B, fast on CPU/low-RAM machines
  ollama pull llama3.2       # 3B, fast on CPU
  ollama pull deepseek-r1    # reasoning model
  ollama serve               # starts on http://localhost:11434
"""
import asyncio
import hashlib
import json
import logging
import re
from typing import Optional, AsyncGenerator
from uuid import UUID

import anthropic
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import get_redis  # used for cache
from app.models.models import User
from app.prompts.tutor_prompts import SYSTEM_PROMPTS

logger = logging.getLogger(__name__)

claude_client = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    timeout=30.0,   # seconds — prevents worker hang if Anthropic API stalls
    max_retries=2,
)

# Keywords that indicate a complex medical question → use Claude
COMPLEX_KEYWORDS = [
    "mechanism", "pathophysiology", "differential", "management", "treatment",
    "guidelines", "evidence", "study", "trial", "protocol", "algorithm",
    "diagnosis", "prognosis", "complications", "pharmacokinetics",
    "contraindication", "interaction", "epidemiology", "etiology",
]


def _is_complex_query(message: str) -> bool:
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in COMPLEX_KEYWORDS)


def _select_claude_model(user: User, message: str) -> str:
    """Which Claude model to use for complex paid-tier queries."""
    if user.subscription_tier in ("pro", "clinic", "lifetime"):
        return "claude-sonnet-4-6"
    return "claude-haiku-4-5-20251001"


def _use_free_ai(user: User, message: str) -> bool:
    """Returns True if request should go to Groq/Ollama instead of Claude."""
    # Free tier: always use free AI
    if user.subscription_tier == "free":
        return True
    # Paid tiers: simple questions → free AI to save costs
    return not _is_complex_query(message)


def _cache_key(message: str, specialty: str, mode: str) -> str:
    raw = f"{message}|{specialty}|{mode}"
    return "ai_cache:" + hashlib.sha256(raw.encode()).hexdigest()


def _to_gemini_contents(messages: list) -> list:
    """Convert OpenAI-format messages to Gemini 'contents' format."""
    contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    return contents


async def _call_gemini(messages: list, system_prompt: str) -> str:
    """Call Google Gemini Flash (FREE tier — aistudio.google.com). Returns text."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("No GEMINI_API_KEY configured")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": _to_gemini_contents(messages),
        "generationConfig": {"maxOutputTokens": 1200, "temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _stream_gemini(messages: list, system_prompt: str):
    """Stream from Google Gemini Flash via SSE. Yields text chunks."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.GEMINI_MODEL}:streamGenerateContent"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": _to_gemini_contents(messages),
        "generationConfig": {"maxOutputTokens": 1200, "temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=60) as http:
        async with http.stream(
            "POST",
            url,
            params={"key": settings.GEMINI_API_KEY, "alt": "sse"},
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if not data_str or data_str == "[DONE]":
                    continue
                try:
                    chunk = json.loads(data_str)
                    text = chunk["candidates"][0]["content"]["parts"][0].get("text", "")
                    if text:
                        yield text
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass


async def _call_groq(messages: list, system_prompt: str) -> str:
    """Call Groq API (OpenAI-compatible). Returns text response."""
    if not settings.GROQ_API_KEY:
        raise ValueError("No GROQ_API_KEY configured")

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 1200,
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def _call_ollama(messages: list, system_prompt: str) -> str:
    """Call local Ollama API. Returns text response (think tags stripped)."""
    ollama_messages = [{"role": "system", "content": system_prompt}] + messages
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": ollama_messages,
                "stream": False,
                "think": False,
                "options": {"num_predict": 800},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["message"]["content"]
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()


async def _stream_ollama(messages: list, system_prompt: str):
    """Async generator — streams chunks from Ollama (think tags stripped)."""
    ollama_messages = [{"role": "system", "content": system_prompt}] + messages
    buffer = ""
    async with httpx.AsyncClient(timeout=120) as http:
        async with http.stream(
            "POST",
            f"{settings.OLLAMA_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": ollama_messages,
                "stream": True,
                "think": False,
                "options": {"num_predict": 800},
            },
        ) as resp:
            resp.raise_for_status()
            in_think = False
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if not chunk:
                        continue
                    # Strip think tags that may still appear despite think:False
                    buffer += chunk
                    if "<think>" in buffer:
                        in_think = True
                    if in_think:
                        if "</think>" in buffer:
                            in_think = False
                            buffer = buffer[buffer.find("</think>") + len("</think>"):]
                        else:
                            buffer = ""
                            continue
                    if buffer and not in_think:
                        yield buffer
                        buffer = ""
                except Exception:
                    continue


async def _call_free_ai(messages: list, system_prompt: str) -> tuple[str, str]:
    """Try Ollama (local) → Gemini Flash → Groq → raise. Returns (text, model_label)."""
    # 1. Try Ollama first — local, completely free, no API key needed
    #    Supports Qwen2.5, Llama3.2, DeepSeek, Mistral and hundreds of others
    try:
        text = await _call_ollama(messages, system_prompt)
        return text, f"ollama/{settings.OLLAMA_MODEL}"
    except Exception as e:
        logger.debug("Ollama not available (not installed or not running): %s", e)

    # 2. Try Gemini Flash (free tier via aistudio.google.com — requires API key)
    if settings.GEMINI_API_KEY:
        try:
            text = await _call_gemini(messages, system_prompt)
            return text, f"gemini/{settings.GEMINI_MODEL}"
        except Exception as e:
            logger.warning("Gemini failed, trying Groq: %s", e)

    # 3. Try Groq (free tier — console.groq.com, requires API key, 14400 req/day)
    if settings.GROQ_API_KEY:
        try:
            text = await _call_groq(messages, system_prompt)
            return text, f"groq/{settings.GROQ_MODEL}"
        except Exception as e:
            logger.warning("Groq failed: %s", e)

    raise RuntimeError(
        "No free AI backend available. "
        "Run Ollama locally (recommended: ollama pull qwen2.5) "
        "or set GEMINI_API_KEY / GROQ_API_KEY."
    )


async def _stream_groq(messages: list, system_prompt: str):
    """Async generator yielding text chunks from Groq streaming API."""
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 1200,
        "temperature": 0.7,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=60) as http:
        async with http.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass


async def route_ai_request(
    user: User,
    message: str,
    conversation_history: list,
    specialty: str,
    mode: str,
    pubmed_context: str = "",
    progress_context: str = "",
    db: Optional[AsyncSession] = None,
    conversation_id: Optional[UUID] = None,
) -> dict:
    """Main AI routing logic. Returns dict with reply, model, from_cache."""

    redis = await get_redis()

    # Check cache (only for simple non-conversational queries)
    cache_key = None
    if not conversation_history:
        cache_key = _cache_key(message, specialty, mode)
        cached = await redis.get(cache_key)
        if cached:
            return {"reply": cached, "model": "cache", "from_cache": True}

    # ── Long-term memory context ──────────────────────────────────────────────
    memory_context = ""
    species: Optional[str] = None
    if db is not None and user.subscription_tier != "free":
        try:
            from app.services.memory_service import (
                retrieve_relevant_memories,
                format_memory_context,
            )
            # Detect species context from message for vet queries
            species: Optional[str] = None
            msg_lower = message.lower()
            for sp in ("canine", "dog", "feline", "cat", "equine", "horse", "bovine"):
                if sp in msg_lower:
                    species = sp if sp not in ("dog", "cat", "horse") else {
                        "dog": "canine", "cat": "feline", "horse": "equine"
                    }[sp]
                    break

            memories = await retrieve_relevant_memories(
                db=db,
                user_id=user.id,
                query=message,
                specialty=specialty,
                species_context=species,
                limit=4,
            )
            memory_context = format_memory_context(memories)
        except Exception as _e:
            logger.warning("Memory retrieval error: %s", _e)

    # Build system prompt
    mode_instruction = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["tutor"])
    system_prompt = (
        f"You are MedMind AI, an expert medical education assistant specializing in {specialty}.\n\n"
        f"{mode_instruction}\n\n"
        "Format with markdown headers (###) and bullets. Keep responses educational and precise."
    )
    if memory_context:
        system_prompt += memory_context
    if progress_context:
        system_prompt += progress_context
    if pubmed_context:
        system_prompt += f"\n\nRecently retrieved PubMed articles for context:\n{pubmed_context}\nReference these where relevant."

    # ── Veterinary mode context injection ────────────────────────────────────
    prefs = user.preferences or {}
    if prefs.get("vet_mode"):
        vet_species_list: list[str] = prefs.get("vet_species", [])
        species_str = ", ".join(vet_species_list) if vet_species_list else "all companion and large animal species"
        system_prompt += (
            f"\n\n🐾 VETERINARY MODE ACTIVE — This user is a veterinary student or practitioner. "
            f"Preferred species: {species_str}.\n"
            "Adjust your responses accordingly:\n"
            "• Use veterinary terminology (owner/client instead of patient, animal names)\n"
            "• Highlight species-specific drug metabolism differences (cats lack glucuronidation, "
            "MDR1 mutation in Collies, allometric scaling in birds/horses)\n"
            "• Warn explicitly when drugs are contraindicated/toxic for specific species "
            "(paracetamol → cats, permethrin → cats, ivermectin → MDR1 dogs, NSAIDs → cats)\n"
            "• Reference Plumb's Veterinary Drug Handbook and BSAVA formulary where relevant\n"
            "• For drug dosing questions: always note that dosing differs from human medicine "
            "and species-specific formulary must be consulted\n"
        )
        if vet_species_list:
            # Add species-specific highlights for selected species
            species_notes = {
                "Cat": "Cats: glucuronidation deficiency → NSAIDs/paracetamol toxic; permethrin FATAL; q72h aspirin max.",
                "Dog": "Dogs: check MDR1/ABCB1 mutation (Collies, Shelties, Aussies) before ivermectin/loperamide.",
                "Horse": "Horses: oral amoxicillin <10% bioavailability — use IV/IM; normal HR 28-44 bpm.",
                "Rabbit": "Rabbits: most antibiotics (penicillins, clindamycin) cause fatal enterotoxaemia — use enrofloxacin/TMP-SMX.",
                "Bird": "Birds: allometric scaling — most drugs need q8-12h due to fast metabolism.",
            }
            selected_notes = [species_notes[s] for s in vet_species_list if s in species_notes]
            if selected_notes:
                system_prompt += "Key reminders for selected species:\n" + "\n".join(f"  - {n}" for n in selected_notes) + "\n"
    elif species:
        # Non-vet mode but message contains animal species reference
        system_prompt += f"\n\nNote: This question involves {species} pharmacology. Include relevant species-specific considerations where applicable."

    messages = list(conversation_history) + [{"role": "user", "content": message}]

    reply = ""
    model_used = ""

    # Route: free/simple → Groq/Ollama; complex paid → Claude
    if _use_free_ai(user, message):
        try:
            reply, model_used = await _call_free_ai(messages, system_prompt)
        except Exception as e:
            logger.warning("Free AI unavailable, falling back: %s", e)
            if user.subscription_tier == "free":
                return {
                    "reply": (
                        "AI service is temporarily unavailable. "
                        "Please try again later, or explore our evidence-based modules and flashcards. "
                        "Upgrade to Student plan for reliable AI access powered by Claude."
                    ),
                    "model": "unavailable",
                    "from_cache": False,
                }
            # Paid tier: fall back to Claude Haiku
            model_used = "claude-haiku-4-5-20251001"
    else:
        model_used = _select_claude_model(user, message)

    # Call Claude if needed
    if not reply:
        try:
            response = await claude_client.messages.create(
                model=model_used,
                max_tokens=1200,
                system=system_prompt,
                messages=messages,
            )
            reply = response.content[0].text if response.content else "No response generated."
        except Exception as e:
            logger.error("Claude request failed: %s", e)
            return {
                "reply": "AI service temporarily unavailable. Please try again.",
                "model": model_used,
                "from_cache": False,
                "error": str(e),
            }

    # Cache single-turn responses
    if cache_key:
        await redis.setex(cache_key, settings.AI_CACHE_TTL, reply)

    # ── Background memory extraction (non-blocking) ───────────────────────────
    if db is not None and conversation_id is not None and user.subscription_tier != "free":
        try:
            from app.services.memory_service import extract_and_save_memories
            from app.core.database import AsyncSessionLocal

            async def _run_memory_extraction():
                async with AsyncSessionLocal() as bg_db:
                    try:
                        await extract_and_save_memories(
                            db=bg_db,
                            user_id=user.id,
                            message=message,
                            ai_reply=reply,
                            specialty=specialty,
                            conversation_id=conversation_id,
                            species_context=species or "human",
                        )
                    except Exception as _inner:
                        logger.warning("Memory extraction failed: %s", _inner)

            asyncio.create_task(_run_memory_extraction())
        except Exception as _e:
            logger.warning("Failed to schedule memory extraction: %s", _e)

    return {
        "reply": reply,
        "model": model_used,
        "from_cache": False,
    }


async def route_ai_stream(
    user: User,
    message: str,
    conversation_history: list,
    specialty: str,
    mode: str,
    pubmed_context: str = "",
    progress_context: str = "",
):
    """Async generator that yields SSE chunks.

    Routing: free/simple → Groq stream; complex paid → Claude stream.
    Falls back gracefully if primary backend unavailable.
    """
    mode_instruction = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["tutor"])
    system_prompt = (
        f"You are MedMind AI, an expert medical education assistant specializing in {specialty}.\n\n"
        f"{mode_instruction}\n\n"
        "Format with markdown headers (###) and bullets. Keep responses educational and precise."
    )
    if progress_context:
        system_prompt += progress_context
    if pubmed_context:
        system_prompt += f"\n\nRecently retrieved PubMed articles:\n{pubmed_context}"

    messages = list(conversation_history) + [{"role": "user", "content": message}]

    use_free = _use_free_ai(user, message)

    # --- Free AI path: Ollama (local) → Gemini → Groq ---
    if use_free:
        # 1. Ollama first — local, zero cost, works with Qwen3 / Llama3.2 / DeepSeek
        yield {"type": "model", "model": f"ollama/{settings.OLLAMA_MODEL}"}
        try:
            got_chunk = False
            async for chunk in _stream_ollama(messages, system_prompt):
                if chunk:
                    yield {"type": "text", "text": chunk}
                    got_chunk = True
            if got_chunk:
                await _increment_rate_limit(user)
                return
        except Exception as e:
            logger.debug("Ollama stream failed: %s", e)

        # 2. Try Gemini Flash streaming (free API tier)
        if settings.GEMINI_API_KEY:
            yield {"type": "model", "model": f"gemini/{settings.GEMINI_MODEL}"}
            try:
                async for chunk in _stream_gemini(messages, system_prompt):
                    yield {"type": "text", "text": chunk}
                await _increment_rate_limit(user)
                return
            except Exception as e:
                logger.warning("Gemini stream failed, trying Groq: %s", e)

        # 3. Try Groq streaming (free API tier fallback)
        if settings.GROQ_API_KEY:
            yield {"type": "model", "model": f"groq/{settings.GROQ_MODEL}"}
            try:
                async for chunk in _stream_groq(messages, system_prompt):
                    yield {"type": "text", "text": chunk}
                await _increment_rate_limit(user)
                return
            except Exception as e:
                logger.warning("Groq stream failed: %s", e)

        # No free AI available
        if user.subscription_tier == "free":
            yield {
                "type": "text",
                "text": (
                    "\u26a0\ufe0f No AI service is available right now.\n\n"
                    "**To enable free AI:** Run Ollama locally:\n"
                    "```\nbrew install ollama && ollama pull qwen3:8b && ollama serve\n```\n\n"
                    "Or explore our evidence-based modules and flashcards."
                ),
            }
            yield {"type": "model", "model": "unavailable"}
            return
        # Paid tier: fall through to Claude

    # --- Claude path (paid tier complex questions) ---
    model = _select_claude_model(user, message)
    yield {"type": "model", "model": model}
    try:
        async with claude_client.messages.stream(
            model=model,
            max_tokens=1200,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "text", "text": text}

        await _increment_rate_limit(user)

    except Exception as e:
        logger.error("Claude stream failed: %s", e)
        yield {"type": "error", "detail": "AI service temporarily unavailable. Please try again."}


async def _increment_rate_limit(user: User):
    """Increment per-user daily AI request counter in Redis."""
    from datetime import datetime
    redis = await get_redis()
    now = datetime.utcnow()
    seconds_till_midnight = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
    rate_key = f"ai_requests:{user.id}"
    await redis.incr(rate_key)
    await redis.expire(rate_key, seconds_till_midnight)
