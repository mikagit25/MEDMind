"""Symptom checker — public endpoint, rate-limited by IP."""
import json
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/symptoms", tags=["symptoms"])

HOURLY_LIMIT = 10  # per IP

SYSTEM_PROMPT = """\
You are a clinical decision-support assistant inside MedMind AI.

Given a patient's self-reported symptoms, produce a structured differential to help them \
understand their situation and choose the right level of care.

RULES:
- Never give a definitive diagnosis — present possibilities with likelihoods
- For ANY emergency signal (chest pain + radiation, stroke signs, difficulty breathing, \
  uncontrolled bleeding, loss of consciousness, severe allergic reaction) set urgency = "emergency"
- Be evidence-based, concise, non-alarmist
- Respond in the SAME LANGUAGE the user used — do not switch to English
- Output ONLY valid JSON, no markdown fences, no preamble

Output this EXACT JSON schema:
{
  "urgency": "emergency|urgent|routine|self-care",
  "urgency_reason": "one sentence",
  "possible_conditions": [
    {"name": "...", "likelihood": "high|moderate|low", "description": "1-2 sentences"}
  ],
  "red_flags": ["watch for this", "..."],
  "recommended_action": "actionable advice — where to go, what to do now",
  "disclaimer": "..."
}

Limit possible_conditions to 3-5, ordered by likelihood descending.
The disclaimer must always be: \
"This analysis is for informational purposes only and does not replace professional medical advice. \
Consult a qualified healthcare professional for diagnosis and treatment."
"""


class SymptomRequest(BaseModel):
    symptoms: str = Field(..., min_length=5, max_length=2000)
    age: Optional[int] = Field(None, ge=0, le=120)
    sex: Optional[str] = None   # "male" | "female" | "other"
    lang: str = "en"


class ConditionItem(BaseModel):
    name: str
    likelihood: str
    description: str


class SymptomResponse(BaseModel):
    urgency: str
    urgency_reason: str
    possible_conditions: list[ConditionItem]
    red_flags: list[str]
    recommended_action: str
    disclaimer: str


async def _check_rate_limit(ip: str) -> None:
    try:
        redis = await get_redis()
        key = f"symptom_check:{ip}"
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 3600)
        results = await pipe.execute()
        count = results[0]
        if count > HOURLY_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Limit: {HOURLY_LIMIT} checks per hour.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # if Redis is down, allow the request


def _build_user_message(req: SymptomRequest) -> str:
    parts = [f"Symptoms: {req.symptoms}"]
    if req.age:
        parts.append(f"Patient age: {req.age}")
    if req.sex:
        parts.append(f"Sex: {req.sex}")
    parts.append(f"Language: {req.lang}")
    return "\n".join(parts)


@router.post("/check", response_model=SymptomResponse)
async def check_symptoms(req: SymptomRequest, request: Request) -> SymptomResponse:
    ip = request.client.host if request.client else "unknown"
    await _check_rate_limit(ip)

    user_msg = _build_user_message(req)

    try:
        raw = await _call_groq(user_msg)
        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        data = json.loads(raw)
        return SymptomResponse(**data)
    except json.JSONDecodeError as e:
        logger.error("Symptom checker JSON parse error: %s", e)
        raise HTTPException(status_code=502, detail="AI returned malformed response")
    except Exception as e:
        logger.error("Symptom checker error: %s", e)
        raise HTTPException(status_code=502, detail="AI service unavailable")


async def _call_groq(user_message: str) -> str:
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 1200,
        "temperature": 0.3,
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
        return resp.json()["choices"][0]["message"]["content"]
