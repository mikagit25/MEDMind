"""Article generation service — creates SEO medical articles via Claude AI.

Output structure per article:
  - slug: URL-safe identifier
  - title: H1
  - og_title: shorter for social/search (≤60 chars)
  - og_description: meta description (≤155 chars)
  - excerpt: 2-3 sentence summary
  - body: [{type, content}] — h2 / p / ul / callout / table blocks
  - faq: [{question, answer}] — for FAQ schema.org
  - sources: [{title, url, pmid}] — PubMed / WHO / UpToDate refs
  - keywords: [str]
  - reading_time_minutes: int
  - subcategory: str | None
  - related_module_code: str | None
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Any, Dict

logger = logging.getLogger(__name__)

SCHEMA_HINTS: Dict[str, str] = {
    "MedicalCondition": "Include: definition, epidemiology, causes/risk factors, symptoms, diagnosis criteria, treatment options, prognosis, prevention.",
    "Drug": "Include: mechanism of action, indications, dosage (adult & pediatric), contraindications, side effects, drug interactions, monitoring.",
    "MedicalProcedure": "Include: indication, contraindications, preparation, step-by-step technique, complications, post-procedure care.",
    "MedicalWebPage": "Include: overview, key facts, clinical relevance, when to seek medical attention, evidence-based recommendations.",
}

LANGUAGE_HINTS: Dict[str, str] = {
    "en": "Write in clear, professional medical English. Target audience: medical students, residents, and practising doctors.",
    "ru": "Пиши на профессиональном медицинском русском языке. Аудитория: студенты-медики, ординаторы, практикующие врачи.",
    "de": "Schreibe auf professionellem medizinischem Deutsch.",
    "fr": "Écris en français médical professionnel.",
    "es": "Escribe en español médico profesional.",
    "ar": "اكتب باللغة الطبية العربية المهنية.",
    "tr": "Profesyonel tıbbi Türkçe ile yaz.",
}


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


def _system_prompt(schema_type: str, language: str) -> str:
    hints = SCHEMA_HINTS.get(schema_type, SCHEMA_HINTS["MedicalWebPage"])
    lang = LANGUAGE_HINTS.get(language, LANGUAGE_HINTS["en"])
    return f"""You are a medical writer for MedMind AI, an AI-powered medical education platform.
{lang}

Your task: write a comprehensive, evidence-based medical article.
Schema type: {schema_type}
Content requirements: {hints}

Return ONLY a valid JSON object — no markdown, no prose outside the JSON.

JSON structure:
{{
  "title": "Full article title (50-80 chars, includes medical term + context)",
  "og_title": "Shorter title for SEO (≤60 chars)",
  "og_description": "Meta description (120-155 chars, includes main keyword)",
  "excerpt": "2-3 sentence summary of the article",
  "subcategory": "specific sub-area or null",
  "keywords": ["keyword1", "keyword2", ...],  // 5-10 relevant medical keywords
  "reading_time_minutes": 7,
  "body": [
    {{"type": "h2", "content": "Section title"}},
    {{"type": "p", "content": "Paragraph text..."}},
    {{"type": "ul", "items": ["item 1", "item 2", "item 3"]}},
    {{"type": "callout", "variant": "warning|info|tip", "content": "Important note..."}},
    {{"type": "table", "headers": ["Col1", "Col2"], "rows": [["A", "B"], ["C", "D"]]}}
  ],
  "faq": [
    {{"question": "Common question?", "answer": "Clear answer."}},
    {{"question": "Another question?", "answer": "Answer."}}
  ],
  "sources": [
    {{"title": "Source title", "url": "https://...", "pmid": "12345678 or null"}}
  ],
  "related_module_code": "MODULE-CODE or null"
}}

Rules:
- body must have 6-12 sections
- faq must have 3-5 questions
- sources must have 2-4 real references (use PubMed, WHO, UpToDate, clinical guidelines)
- All content must be evidence-based and medically accurate
- Do NOT include legal disclaimers — the platform adds its own
- Do NOT wrap JSON in markdown code fences"""


async def generate_medical_article(
    topic: str,
    category: str,
    schema_type: str = "MedicalWebPage",
    language: str = "en",
    model: str = "haiku",
) -> Dict[str, Any]:
    """Generate a medical article. model: haiku | sonnet | ollama"""
    from app.core.config import settings

    system = _system_prompt(schema_type, language)
    user_msg = f"Write a comprehensive medical article about: {topic}\nCategory: {category}"

    if model == "ollama":
        raw = await _call_ollama(system, user_msg, settings)
    else:
        raw = await _call_claude(system, user_msg, model, settings)
    return _parse_response(raw, topic, category, language)


async def _call_claude(system: str, user_msg: str, model: str, settings) -> str:
    """Call Claude API. haiku for speed/cost, sonnet for quality."""
    import anthropic

    model_id = "claude-haiku-4-5-20251001" if model == "haiku" else "claude-sonnet-4-6"

    if not settings.ANTHROPIC_API_KEY:
        return await _call_ollama(system, user_msg, settings)

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = await client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return message.content[0].text


async def _call_ollama(system: str, user_msg: str, settings) -> str:
    """Call local Ollama via /api/chat (supports system prompt properly)."""
    import httpx

    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
        "stream": False,
        "options": {"num_predict": 4096, "temperature": 0.3},
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(f"{settings.OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"]


def _parse_response(raw: str, topic: str, category: str, language: str) -> Dict[str, Any]:
    """Extract and validate JSON from Claude response."""
    # Strip possible markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            raise ValueError(f"Claude did not return valid JSON for topic: {topic}")
        data = json.loads(match.group())

    # Build slug from title or topic
    slug_base = _slugify(data.get("title", topic))
    data["slug"] = slug_base

    # Ensure required fields have sensible defaults
    data.setdefault("excerpt", data.get("og_description", ""))
    data.setdefault("keywords", [topic.lower()])
    data.setdefault("reading_time_minutes", _estimate_reading_time(data.get("body", [])))
    data.setdefault("faq", [])
    data.setdefault("sources", [])
    data.setdefault("related_module_code", None)
    data.setdefault("subcategory", None)

    logger.info("Generated article: %s (slug: %s, language: %s)", data.get("title"), data["slug"], language)
    return data


def _estimate_reading_time(body: list) -> int:
    """Estimate reading time based on word count in body blocks."""
    words = 0
    for block in body:
        if isinstance(block.get("content"), str):
            words += len(block["content"].split())
        elif isinstance(block.get("items"), list):
            words += sum(len(str(i).split()) for i in block["items"])
    return max(3, round(words / 200))  # ~200 words/minute
