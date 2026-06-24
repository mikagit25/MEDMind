"""Telegram bot webhook — MedMind AI assistant.

Webhook: POST /api/v1/telegram/webhook
Setup:   python3 -m app.scripts.telegram_setup  (run once after deploy)

Free tier for all Telegram users: 10 messages/day via Groq.
Paid tier: link account via /link command → uses subscription limits + Claude.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.models import User, HealthProfile

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

# ── Patient intake state machine ──────────────────────────────────────────────

EMERGENCY_KEYWORDS = [
    "chest pain","can't breathe","cannot breathe","not breathing","heart attack",
    "stroke","unconscious","seizure","overdose","severe bleeding","anaphylaxis",
    "боль в груди","не могу дышать","инфаркт","инсульт","без сознания",
    "судорог","сильное кровотечение","передозировк","анафилакси",
    "ألم في الصدر","لا أستطيع التنفس","نوبة قلبية","سكتة دماغية","فقدان الوعي",
]

# Stage 1: context questions (localized)
INTAKE_CTX_Q: dict[str, str] = {
    "en": "To give you the most accurate guidance, please answer:\n\n1️⃣ Your age and sex?\n2️⃣ How long have you had this symptom?\n3️⃣ Severity on a scale of 1–10?",
    "ru": "Чтобы дать точный совет, ответьте:\n\n1️⃣ Ваш возраст и пол?\n2️⃣ Как давно появился симптом?\n3️⃣ Насколько сильно беспокоит по шкале 1–10?",
    "ar": "لأقدم لك إرشادات دقيقة، أجب على:\n\n1️⃣ عمرك وجنسك؟\n2️⃣ منذ متى وأنت تعاني من هذا العَرَض؟\n3️⃣ شدة الألم من 1 إلى 10؟",
    "es": "Para darte la orientación más precisa, responde:\n\n1️⃣ ¿Tu edad y sexo?\n2️⃣ ¿Desde cuándo tienes este síntoma?\n3️⃣ ¿Intensidad del 1 al 10?",
    "de": "Um dir die genaueste Beratung zu geben:\n\n1️⃣ Alter und Geschlecht?\n2️⃣ Wie lange hast du dieses Symptom?\n3️⃣ Stärke 1–10?",
    "fr": "Pour vous guider avec précision:\n\n1️⃣ Votre âge et sexe?\n2️⃣ Depuis combien de temps?\n3️⃣ Intensité de 1 à 10?",
    "tr": "En doğru rehberliği sunmak için:\n\n1️⃣ Yaşınız ve cinsiyetiniz?\n2️⃣ Bu belirti ne zamandan beri var?\n3️⃣ Şiddet 1–10?",
}

DONE_BTN: dict[str, str] = {
    "en": "✅ Continue", "ru": "✅ Продолжить", "ar": "✅ متابعة",
    "es": "✅ Continuar", "de": "✅ Weiter", "fr": "✅ Continuer", "tr": "✅ Devam",
}

# Stage 2: adaptive questions per symptom category
ADAPTIVE_Q: dict[str, dict] = {
    "headache": {
        "text": {"en": "A few more details about your headache:", "ru": "Ещё несколько уточнений о головной боли:", "ar": "تفاصيل إضافية حول صداعك:", "es": "Más detalles sobre tu dolor de cabeza:"},
        "buttons": [
            [("🔴 Pulsating / throbbing", "sym:pulsating"), ("⚪ Pressing / squeezing", "sym:pressing")],
            [("🤢 Nausea / vomiting", "sym:nausea"),        ("💡 Light sensitivity", "sym:photophobia")],
            [("🌡️ Fever",             "sym:fever"),          ("🤕 Neck stiffness",    "sym:neck_stiff")],
        ],
    },
    "chest": {
        "text": {"en": "Important details about your chest symptom:", "ru": "Важные уточнения о симптоме в груди:", "ar": "تفاصيل مهمة حول أعراض صدرك:"},
        "buttons": [
            [("💢 Radiates to arm / jaw", "sym:radiation"), ("😤 Shortness of breath", "sym:dyspnea")],
            [("💧 Sweating",              "sym:sweating"),  ("💓 Palpitations",        "sym:palpitations")],
            [("🌡️ Fever",                "sym:fever"),      ("🤮 Nausea / vomiting",  "sym:nausea")],
        ],
    },
    "abdominal": {
        "text": {"en": "More about your abdominal symptoms:", "ru": "Уточнения о симптомах живота:", "ar": "مزيد من التفاصيل حول أعراض البطن:"},
        "buttons": [
            [("🌡️ Fever",       "sym:fever"),        ("🤮 Nausea / vomiting", "sym:nausea")],
            [("💩 Diarrhea",    "sym:diarrhea"),     ("🚫 Constipation",      "sym:constipation")],
            [("🟡 Right-side",  "sym:right_pain"),   ("🟠 Left-side pain",    "sym:left_pain")],
        ],
    },
    "respiratory": {
        "text": {"en": "More about your breathing / cough:", "ru": "Уточнения о дыхании / кашле:", "ar": "مزيد حول التنفس / السعال:"},
        "buttons": [
            [("🌡️ Fever",               "sym:fever"),          ("🩸 Blood in sputum",       "sym:hemoptysis")],
            [("😤 Can't finish sentence","sym:severe_dyspnea"),("😮‍💨 Wheezing",         "sym:wheeze")],
            [("🦠 Recent sick contact", "sym:sick_contact"),   ("🚬 Smoker",                "sym:smoker")],
        ],
    },
    "back": {
        "text": {"en": "About your back pain:", "ru": "Уточнения о боли в спине:", "ar": "حول ألم ظهرك:"},
        "buttons": [
            [("⚡ Shoots to leg",         "sym:radiation_leg"), ("🦵 Leg numbness / weakness", "sym:neuro_leg")],
            [("🚽 Bladder / bowel issues","sym:bladder"),       ("🌡️ Fever",                  "sym:fever")],
            [("🏋️ After injury / lifting","sym:trauma"),        ("😴 Pain at rest / at night","sym:rest_pain")],
        ],
    },
    "general": {
        "text": {"en": "A few more details:", "ru": "Ещё несколько уточнений:", "ar": "بعض التفاصيل الإضافية:", "es": "Algunos detalles más:"},
        "buttons": [
            [("🌡️ Fever",          "sym:fever"),       ("🤮 Nausea / vomiting", "sym:nausea")],
            [("😴 Fatigue / weak", "sym:fatigue"),     ("⚖️ Recent weight loss","sym:weight_loss")],
            [("💊 On medications", "sym:on_meds"),     ("🏥 Recent hospital",  "sym:hospitalized")],
        ],
    },
}

def _is_emergency(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in EMERGENCY_KEYWORDS)

def _detect_category(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["голов","мигрен","head","migrain","رأس","صداع"]):
        return "headache"
    if any(w in t for w in ["грудь","грудн","сердц","chest","heart","cardiac","صدر","قلب"]):
        return "chest"
    if any(w in t for w in ["живот","желудок","тошн","stomach","abdom","belly","بطن","معدة","غثيان"]):
        return "abdominal"
    if any(w in t for w in ["дыхан","кашл","одышк","breath","cough","wheez","تنفس","سعال"]):
        return "respiratory"
    if any(w in t for w in ["спин","поясниц","back","lumbar","ظهر"]):
        return "back"
    return "general"

# Prompt for the final structured answer (after intake complete)
PATIENT_ANSWER_PROMPT = (
    "You are a friendly health educator. The patient provided this intake:\n\n"
    "{context}\n\n"
    "Respond in the SAME LANGUAGE the patient used for their chief complaint.\n"
    "Structure your reply EXACTLY like this (use the same emoji headers):\n\n"
    "🔍 *What this might be*\n"
    "1-2 most likely plain-language explanations (no scary jargon).\n\n"
    "{triage_line}\n\n"
    "📋 *What to do now*\n"
    "• Bullet 1\n• Bullet 2\n• Bullet 3\n\n"
    "⚠️ *See a doctor sooner if*\n"
    "• Warning sign 1\n• Warning sign 2\n\n"
    "Keep the total under 280 words. Never diagnose. Always recommend professional evaluation."
)

TRIAGE_LEVELS = {
    "green":  "🟢 *Triage: Self-care* — you can likely manage this at home for now.",
    "yellow": "🟡 *Triage: See a doctor* — within 48 hours, not an emergency.",
    "red":    "🔴 *Triage: Urgent care* — seek medical attention today.",
    "911":    "🚨 *Triage: EMERGENCY* — call 112/911 or go to ER immediately.",
}

# ── Health metric tracker ─────────────────────────────────────────────────────
TRACKER_UNITS: dict[str, str] = {
    "glucose": "mmol/L", "sugar": "mmol/L", "глюкоза": "mmol/L", "сахар": "mmol/L",
    "bp": "mmHg", "pressure": "mmHg", "давление": "mmHg",
    "weight": "kg", "вес": "kg", "peso": "kg",
    "temp": "°C", "temperature": "°C", "температура": "°C",
    "pulse": "bpm", "пульс": "bpm", "hr": "bpm", "heart rate": "bpm",
    "spo2": "%", "oxygen": "%", "кислород": "%", "o2": "%",
    "cholesterol": "mmol/L", "холестерин": "mmol/L",
    "hba1c": "%", "гликированный": "%",
}
_TRACKER_CANONICAL: dict[str, str] = {
    "sugar": "glucose", "сахар": "glucose", "глюкоза": "glucose",
    "pressure": "bp", "давление": "bp",
    "вес": "weight", "peso": "weight",
    "температура": "temp", "temperature": "temp",
    "пульс": "pulse", "hr": "pulse", "heart rate": "pulse",
    "кислород": "spo2", "oxygen": "spo2", "o2": "spo2",
    "холестерин": "cholesterol",
    "гликированный": "hba1c",
}

# ── Daily check-in texts ───────────────────────────────────────────────────────
_CHECKIN_Q: dict[str, str] = {
    "en": "👋 *Daily Health Check-in*\n\nHow are you feeling today?",
    "ru": "👋 *Ежедневный чек-ин*\n\nКак вы себя чувствуете сегодня?",
    "ar": "👋 *تسجيل يومي*\n\nكيف تشعر اليوم؟",
    "es": "👋 *Check-in diario*\n\n¿Cómo te sientes hoy?",
    "de": "👋 *Täglicher Check-in*\n\nWie fühlen Sie sich heute?",
    "fr": "👋 *Check-in quotidien*\n\nComment vous sentez-vous aujourd'hui?",
    "tr": "👋 *Günlük kontrol*\n\nBugün nasıl hissediyorsunuz?",
}
_CHECKIN_BTNS: dict[str, list[tuple[str, str]]] = {
    "en": [("🟢 Feeling good", "checkin:good"), ("🟡 OK, manageable", "checkin:ok"),
           ("🔴 Not great",    "checkin:bad"),  ("🤒 Have symptoms",  "checkin:symptoms")],
    "ru": [("🟢 Хорошо",       "checkin:good"), ("🟡 Нормально",       "checkin:ok"),
           ("🔴 Неважно",      "checkin:bad"),  ("🤒 Есть симптомы",  "checkin:symptoms")],
    "ar": [("🟢 بخير",         "checkin:good"), ("🟡 عادي",            "checkin:ok"),
           ("🔴 لست بخير",     "checkin:bad"),  ("🤒 لدي أعراض",      "checkin:symptoms")],
    "es": [("🟢 Bien",         "checkin:good"), ("🟡 Regular",         "checkin:ok"),
           ("🔴 Mal",          "checkin:bad"),  ("🤒 Tengo síntomas",  "checkin:symptoms")],
}

# ── Patient profile: persistent cross-session memory (90-day TTL) ────────────

_EMPTY_SUBJ: dict = {"age": None, "sex": None, "conditions": [], "medications": [], "allergies": []}

# Relation keywords → (canonical label, guessed sex)
_RELATIONS: dict[str, tuple[str, str | None]] = {
    # English
    "wife": ("wife", "female"), "husband": ("husband", "male"),
    "son": ("son", "male"), "daughter": ("daughter", "female"),
    "mother": ("mother", "female"), "mom": ("mom", "female"),
    "father": ("father", "male"), "dad": ("dad", "male"),
    "sister": ("sister", "female"), "brother": ("brother", "male"),
    "girlfriend": ("girlfriend", "female"), "boyfriend": ("boyfriend", "male"),
    "friend": ("friend", None), "child": ("child", None),
    "baby": ("baby", None), "kid": ("kid", None),
    "grandpa": ("grandfather", "male"), "grandma": ("grandmother", "female"),
    "grandfather": ("grandfather", "male"), "grandmother": ("grandmother", "female"),
    # Russian (stems so they match inflected forms)
    "жена": ("жена", "female"), "жены": ("жена", "female"), "жену": ("жена", "female"),
    "мужа": ("муж", "male"), "мужу": ("муж", "male"), " муж ": ("муж", "male"),
    "сын": ("сын", "male"), "сына": ("сын", "male"),
    "дочь": ("дочь", "female"), "дочер": ("дочь", "female"),
    "мама": ("мама", "female"), "маму": ("мама", "female"), "мамы": ("мама", "female"),
    "папа": ("папа", "male"), "папу": ("папа", "male"), "папы": ("папа", "male"),
    "сестра": ("сестра", "female"), "сестр": ("сестра", "female"),
    "брата": ("брат", "male"), "брату": ("брат", "male"), " брат ": ("брат", "male"),
    "друга": ("друг", None), "подруга": ("подруга", None), "подруг": ("подруга", None),
    "ребенок": ("ребенок", None), "ребенк": ("ребенок", None), "детей": ("ребенок", None),
    "бабушк": ("бабушка", "female"), "дедушк": ("дедушка", "male"),
    # Spanish
    "esposa": ("esposa", "female"), "esposo": ("esposo", "male"), "marido": ("marido", "male"),
    "hijo": ("hijo", "male"), "hija": ("hija", "female"),
    "madre": ("madre", "female"), "padre": ("padre", "male"),
    # Arabic
    "زوجة": ("زوجة", "female"), "زوجتي": ("زوجة", "female"),
    "زوج": ("زوج", "male"), "زوجي": ("زوج", "male"),
    "ابن": ("ابن", "male"), "ابنة": ("ابنة", "female"),
    "أمي": ("أم", "female"), "أبي": ("أب", "male"),
}

_CLARIFY_Q: dict[str, str] = {
    "en": "Is this question for *you* or for your *{last}*?",
    "ru": "Этот вопрос про *вас* или снова про *{last}*?",
    "ar": "هل هذا السؤال *عنك* أم لا يزال عن *{last}*؟",
    "es": "¿Esta pregunta es *para ti* o sobre tu *{last}*?",
    "de": "Ist diese Frage für *dich* oder für deine(n) *{last}*?",
    "fr": "Cette question est-elle *pour vous* ou toujours à propos de votre *{last}*?",
    "tr": "Bu soru *senin için* mi, yoksa *{last}* için mi?",
}
_ME_BTN: dict[str, str] = {
    "en": "🙋 For me", "ru": "🙋 Для меня", "ar": "🙋 لي", "es": "🙋 Para mí",
    "de": "🙋 Für mich", "fr": "🙋 Pour moi", "tr": "🙋 Benim için",
}
_SHORT_CTX_Q: dict[str, str] = {
    "en": "I have *{name}* ({demo}) on file. Two quick questions:\n\n2️⃣ How long have you had this symptom?\n3️⃣ Severity 1–10?",
    "ru": "У меня записан *{name}* ({demo}). Два уточнения:\n\n2️⃣ Как давно симптом?\n3️⃣ Насколько беспокоит 1–10?",
    "ar": "لديّ سجل *{name}* ({demo}). سؤالان:\n\n2️⃣ منذ متى هذا العَرَض؟\n3️⃣ الشدة 1–10؟",
    "es": "Tengo registrado *{name}* ({demo}). Dos preguntas:\n\n2️⃣ ¿Desde cuándo tienes este síntoma?\n3️⃣ ¿Intensidad del 1 al 10?",
}


def _detect_subject(text: str) -> tuple[str, str | None]:
    """Return (subject_key, guessed_sex). 'self' if no relation word found."""
    t = text.lower()
    for keyword, (label, sex) in _RELATIONS.items():
        if keyword in t:
            return label, sex
    return "self", None


def _extract_age_sex(text: str) -> tuple[int | None, str | None]:
    """Parse '32F, 3 days' → (32, 'female')."""
    age: int | None = None
    sex: str | None = None
    t = text.lower()
    m = re.search(r'\b(\d{1,3})\s*(?:лет|год(?:а|ов)?|y\.?o\.?|years?\s*old)?', t)
    if m:
        c = int(m.group(1))
        if 1 <= c <= 120:
            age = c
    if re.search(r'\d\s*f\b', t) or any(w in t for w in ["female","woman","girl","женщ","девочк","девушк"]):
        sex = "female"
    elif re.search(r'\d\s*m\b', t) or any(w in t for w in ["male","man","boy","мужч","мальчик","парень"]):
        sex = "male"
    return age, sex


def _subject_data(profile: dict, subject: str) -> dict:
    if subject == "self":
        return profile.setdefault("self", {"age": None, "sex": None, "conditions": [], "medications": [], "allergies": []})
    return profile.setdefault("others", {}).setdefault(
        subject, {"age": None, "sex": None, "conditions": [], "medications": [], "allergies": []}
    )


def _build_ctx_q(subj_data: dict, subject: str, lang: str) -> str:
    """Return shorter context question if we already know age + sex."""
    age = subj_data.get("age")
    sex = subj_data.get("sex")
    if age and sex:
        demo = f"{age}{'F' if sex == 'female' else 'M'}"
        name = "you" if subject == "self" else subject
        return _SHORT_CTX_Q.get(lang, _SHORT_CTX_Q["en"]).format(name=name, demo=demo)
    return INTAKE_CTX_Q.get(lang, INTAKE_CTX_Q["en"])


# ── System prompts (Telegram-optimised: shorter, chat-friendly) ───────────────
TG_SYSTEM_PROMPTS: dict[str, str] = {
    "tutor": (
        "You are MedMind AI — a concise medical tutor in a Telegram chat. "
        "Give focused, educational answers in 3–5 short paragraphs max. "
        "Use **bold** for key terms. No long headers.\n\n"
        "If the question is too vague to give a useful answer (e.g. 'tell me about the heart', "
        "'explain diabetes'), ask ONE short clarifying question to narrow the focus "
        "(e.g. 'Are you interested in the pathophysiology, clinical management, or pharmacology?'). "
        "If the question is specific enough, answer directly.\n\n"
        "End with one practical tip using these language-specific labels — never translate literally: "
        "English '💡 Clinical Tip:', Russian '💡 На заметку:', Arabic '💡 تذكّر:', "
        "Spanish '💡 Recuerda:', French '💡 À retenir:', German '💡 Merksatz:', "
        "Turkish '💡 Not:', Portuguese '💡 Lembre-se:', Indonesian '💡 Ingat:', "
        "other languages — use the most natural local equivalent of 'remember' or 'key point'."
    ),
    "case": (
        "You are presenting a clinical case step-by-step in Telegram. "
        "Start with chief complaint + age/sex. Ask for the student's assessment. "
        "Keep each message short (fits a phone screen). "
        "Reveal information gradually as the student requests it."
    ),
    "patient": (
        "You are a friendly health educator in Telegram. Plain language only — no medical jargon. "
        "Always recommend seeing a real doctor. Never diagnose.\n\n"
        "CRITICAL — For emergencies (chest pain, difficulty breathing, loss of consciousness, "
        "stroke signs, severe bleeding): your FIRST line must be '⚠️ Call 112/911 immediately.' "
        "Then briefly explain why. Skip clarifying questions entirely.\n\n"
        "FOR ALL OTHER SYMPTOM QUESTIONS — if the conversation history does NOT already contain "
        "the patient's age, symptom duration, and severity, ask these 3 questions in ONE message "
        "before answering. Number them:\n"
        "1. How old are you?\n"
        "2. How long have you had this symptom?\n"
        "3. How severe is it on a scale of 1–10?\n\n"
        "Once you have this context (from history or the current message), give a clear answer "
        "in 4–6 plain sentences. End with when to see a doctor urgently."
    ),
    "differential": (
        "You are a clinical reasoning assistant in Telegram.\n\n"
        "BEFORE generating a differential: check if the conversation history already contains "
        "patient age/sex, chief complaint, symptom duration, and at least 2 associated findings. "
        "If ANY of these are missing, ask for them in ONE message as a numbered list. "
        "Do not generate the differential until you have all four.\n\n"
        "Once you have the context: list differentials as:\n"
        "🔴 Most Likely (2–3 items)\n"
        "🟡 Also Consider (2–3 items)\n"
        "⚠️ Can't Miss (1–2 items)\n"
        "End with 3 key investigations. One line per diagnosis. Be concise."
    ),
    "second_opinion": (
        "You are a medical educator reviewing a clinical plan in Telegram.\n\n"
        "BEFORE reviewing: check if the conversation history already contains "
        "(1) the diagnosis or working diagnosis and (2) the proposed treatment plan. "
        "If either is missing, ask for both in one short message before proceeding.\n\n"
        "Once you have the plan: explain what current guidelines recommend, "
        "what in the plan aligns with evidence, what might be reconsidered, "
        "and 2–3 specific questions the user could ask their doctor. "
        "Never state the doctor is wrong — frame as 'guidelines suggest' or 'worth discussing'. "
        "Keep it concise and structured."
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
    if len(text) > 4000:
        text = text[:3990] + "\n\n...(truncated)"
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(TG_API.format(token=token, method="sendMessage"), json=payload)
            if r.status_code == 400 and parse_mode:
                # Retry without parse_mode — AI response may contain broken Markdown
                payload.pop("parse_mode")
                await client.post(TG_API.format(token=token, method="sendMessage"), json=payload)
        except Exception as e:
            logger.warning("send_message error: %s", e)


async def send_typing(chat_id: int) -> None:
    await tg_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})


async def send_clarify_subject(chat_id: int, last_subject: str, lang: str) -> None:
    """Ask the user who the symptom question is for (self vs. last mentioned person)."""
    text = _CLARIFY_Q.get(lang, _CLARIFY_Q["en"]).format(last=last_subject)
    me_label = _ME_BTN.get(lang, _ME_BTN["en"])
    keyboard = [[
        {"text": me_label,                    "callback_data": "subject:self"},
        {"text": f"👤 {last_subject.title()}", "callback_data": f"subject:{last_subject}"},
    ]]
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(
                TG_API.format(token=token, method="sendMessage"),
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
                      "reply_markup": {"inline_keyboard": keyboard}},
            )
        except Exception as e:
            logger.warning("send_clarify_subject error: %s", e)


async def send_adaptive_buttons(chat_id: int, category: str, lang: str) -> None:
    q = ADAPTIVE_Q.get(category, ADAPTIVE_Q["general"])
    text = q["text"].get(lang, q["text"].get("en", "A few more details:"))
    keyboard = []
    for row in q["buttons"]:
        keyboard.append([{"text": label, "callback_data": cb} for label, cb in row])
    done_label = DONE_BTN.get(lang, DONE_BTN["en"])
    keyboard.append([{"text": done_label, "callback_data": "intake:done"}])
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": {"inline_keyboard": keyboard},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(TG_API.format(token=token, method="sendMessage"), json=payload)
        except Exception as e:
            logger.warning("send_adaptive_buttons error: %s", e)


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


async def get_intake(chat_id: int) -> dict:
    try:
        redis = await get_redis()
        raw = await redis.get(f"tg_intake:{chat_id}")
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


async def set_intake(chat_id: int, state: dict) -> None:
    try:
        redis = await get_redis()
        await redis.set(f"tg_intake:{chat_id}", json.dumps(state), ex=3600)
    except Exception:
        pass


async def clear_intake(chat_id: int) -> None:
    try:
        redis = await get_redis()
        await redis.delete(f"tg_intake:{chat_id}")
    except Exception:
        pass


_PROFILE_FREE_TTL  = 86400 * 90   # 90 days for free users
_PROFILE_PAID_TTL  = 86400 * 3650  # 10 years ≈ permanent for paid users
_DEFAULT_PROFILE = lambda: {
    "self":         {"age": None, "sex": None, "conditions": [], "medications": [], "allergies": []},
    "others":       {},
    "last_subject": "self",
    "log":          [],   # [{date, subject, complaint, category, symptoms}]
}


async def get_profile(chat_id: int) -> dict:
    """Read profile and auto-renew free-tier TTL on every access (activity-based expiry)."""
    try:
        redis  = await get_redis()
        key    = f"tg_profile:{chat_id}"
        raw    = await redis.get(key)
        if raw:
            ttl = await redis.ttl(key)
            # Only renew if still under free TTL (not already permanent / paid)
            if 0 < ttl < _PROFILE_FREE_TTL:
                await redis.expire(key, _PROFILE_FREE_TTL)
            return json.loads(raw)
    except Exception:
        pass
    return _DEFAULT_PROFILE()


async def save_profile(chat_id: int, profile: dict, linked_user_id: str | None = None) -> None:
    """Save profile to Redis; syncs to PostgreSQL when account is linked."""
    try:
        redis = await get_redis()
        key   = f"tg_profile:{chat_id}"
        current_ttl = await redis.ttl(key)
        ttl = _PROFILE_FREE_TTL if current_ttl <= _PROFILE_FREE_TTL else current_ttl
        await redis.set(key, json.dumps(profile), ex=ttl)
    except Exception:
        pass
    if linked_user_id:
        import asyncio
        asyncio.ensure_future(sync_profile_to_db(chat_id, profile, linked_user_id))


async def sync_profile_to_db(chat_id: int, profile: dict, user_id: str) -> None:
    """Sync Redis profile → PostgreSQL health_profiles for linked accounts."""
    try:
        from app.core.database import AsyncSessionLocal
        from datetime import datetime as _dt
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(HealthProfile).where(HealthProfile.user_id == user_id)
            )
            hp = result.scalar_one_or_none()
            if not hp:
                hp = HealthProfile(
                    user_id=user_id,
                    conditions=[],
                    medications=[],
                    allergies=[],
                    health_log=[],
                    checkin_log=[],
                    trackers={},
                )
                db.add(hp)
            # Sync fields from Redis profile
            self_data = profile.get("self", {})
            if self_data.get("age") and not hp.birth_year:
                hp.birth_year = _dt.utcnow().year - self_data["age"]
            if self_data.get("sex") and not hp.sex:
                hp.sex = self_data["sex"]
            conditions = self_data.get("conditions", [])
            if conditions:
                existing = set(hp.conditions or [])
                hp.conditions = list(existing | set(conditions))
            medications = self_data.get("medications", [])
            if medications:
                existing = set(hp.medications or [])
                hp.medications = list(existing | set(medications))
            hp.telegram_chat_id = str(chat_id)
            # Merge health log (last 200 entries)
            new_log = profile.get("log", [])
            if new_log:
                existing_log = hp.health_log or []
                existing_dates = {e.get("date") + e.get("complaint", "") for e in existing_log}
                for entry in new_log:
                    key = entry.get("date", "") + entry.get("complaint", "")
                    if key not in existing_dates:
                        existing_log.append(entry)
                        existing_dates.add(key)
                hp.health_log = existing_log[-200:]
            # Merge trackers
            tg_trackers = profile.get("trackers", {})
            if tg_trackers:
                db_trackers = dict(hp.trackers or {})
                for metric, entries in tg_trackers.items():
                    db_trackers[metric] = (db_trackers.get(metric, []) + entries)[-100:]
                hp.trackers = db_trackers
            # Merge checkin log
            tg_checkins = profile.get("checkin_log", [])
            if tg_checkins:
                existing_ci = hp.checkin_log or []
                existing_ci_dates = {e.get("date") for e in existing_ci}
                for ci in tg_checkins:
                    if ci.get("date") not in existing_ci_dates:
                        existing_ci.append(ci)
                hp.checkin_log = existing_ci[-365:]
            hp.updated_at = _dt.utcnow()
            await db.commit()
    except Exception as e:
        logger.warning(f"sync_profile_to_db failed: {e}")


async def promote_profile_paid(chat_id: int) -> None:
    """Upgrade profile TTL to 10-year when a paid account is detected."""
    try:
        redis = await get_redis()
        key   = f"tg_profile:{chat_id}"
        if await redis.exists(key):
            current_ttl = await redis.ttl(key)
            if current_ttl < _PROFILE_PAID_TTL:
                await redis.expire(key, _PROFILE_PAID_TTL)
    except Exception:
        pass


async def maybe_send_expiry_upsell(chat_id: int, lang: str) -> None:
    """Warn free users when profile expires in ≤14 days. Shows once per 7 days."""
    try:
        redis        = await get_redis()
        profile_key  = f"tg_profile:{chat_id}"
        upsell_key   = f"tg_upsell_expiry:{chat_id}"
        if await redis.exists(upsell_key):
            return
        ttl = await redis.ttl(profile_key)
        if ttl <= 0 or ttl > 14 * 86400:
            return
        days = max(1, ttl // 86400)
        _UPSELL: dict[str, str] = {
            "en": (f"⏱ *Heads up!* Your health profile expires in *{days} day{'s' if days!=1 else ''}*.\n\n"
                   "All your saved data (age, conditions, symptom history) will be lost.\n\n"
                   "🔒 *Upgrade to MedMind Pro* to keep your data permanently → medmind.pro/pricing\n"
                   "Or /link your existing account."),
            "ru": (f"⏱ *Внимание!* Ваш профиль здоровья истекает через *{days} дн.*\n\n"
                   "Все сохранённые данные (возраст, болезни, история симптомов) будут удалены.\n\n"
                   "🔒 *Подключите MedMind Pro* — данные хранятся бессрочно → medmind.pro/pricing\n"
                   "Или привяжите аккаунт командой /link."),
            "ar": (f"⏱ *تنبيه!* ينتهي ملف صحتك خلال *{days} يوم*.\n\n"
                   "🔒 *اشترك في MedMind Pro* للاحتفاظ ببياناتك → medmind.pro/pricing"),
            "es": (f"⏱ *¡Atención!* Tu perfil de salud expira en *{days} día{'s' if days!=1 else ''}*.\n\n"
                   "🔒 *Actualiza a MedMind Pro* para guardar tus datos permanentemente → medmind.pro/pricing"),
        }
        msg = _UPSELL.get(lang, _UPSELL["en"])
        await send_message(chat_id, msg)
        await redis.set(upsell_key, "1", ex=86400 * 7)
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

_START_TEXTS: dict[str, str] = {
    "ru": (
        "👋 <b>Привет, {name}! Я MedMind AI.</b>\n\n"
        "Твой личный ИИ-ассистент по медицине — доступен 24/7, прямо в Telegram.\n\n"
        "<b>🎯 Что я умею:</b>\n"
        "🎓 /mode tutor — объясняю любую медицинскую тему\n"
        "🩺 /mode case — разбираю клинические случаи шаг за шагом\n"
        "🔬 /mode differential — строю дифференциальный диагноз\n"
        "🏥 /mode patient — объясняю диагнозы простым языком\n"
        "⚖️ /mode second_opinion — сверяю план лечения с гайдлайнами\n\n"
        "<b>📚 MedMind Pro — полная платформа медобразования:</b>\n"
        "• 500+ интерактивных модулей по всем специальностям\n"
        "• База препаратов, клинические калькуляторы, мед. визуализация\n"
        "• ИИ-тьютор, аналитика прогресса, флэшкарты\n"
        "→ medmind.pro\n\n"
        "💬 <b>Бесплатно:</b> {limit} сообщений/день\n"
        "⚡ <b>Pro:</b> безлимит + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Привязать аккаунт: /link\n\n"
        "Просто напиши любой вопрос — и начнём! 👇\n\n"
        "⚕️ <i>Только для образования · не заменяет врача</i>"
    ),
    "ar": (
        "👋 <b>مرحباً {name}! أنا MedMind AI.</b>\n\n"
        "مساعدك الطبي الذكي الشخصي — متاح 24/7 داخل تيليغرام مباشرةً.\n\n"
        "<b>🎯 ماذا أستطيع أن أفعل:</b>\n"
        "🎓 /mode tutor — أشرح أي موضوع طبي بوضوح\n"
        "🩺 /mode case — أحلل الحالات السريرية خطوة بخطوة\n"
        "🔬 /mode differential — أبني تشخيصاً تفريقياً منظماً\n"
        "🏥 /mode patient — أشرح التشخيصات بلغة بسيطة\n"
        "⚖️ /mode second_opinion — أراجع خطط العلاج وفق الإرشادات\n\n"
        "<b>📚 MedMind Pro — منصة التعليم الطبي الشاملة:</b>\n"
        "• أكثر من 500 وحدة تعليمية تفاعلية في جميع التخصصات\n"
        "• قاعدة بيانات الأدوية، الحاسبات السريرية، التصوير الطبي\n"
        "• مدرّس ذكي، تحليلات التقدم، بطاقات التعلم\n"
        "→ medmind.pro\n\n"
        "💬 <b>مجاناً:</b> {limit} رسائل/يوم\n"
        "⚡ <b>Pro:</b> غير محدود + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 ربط حسابك: /link\n\n"
        "اكتب أي سؤال طبي للبدء! 👇\n\n"
        "⚕️ <i>للأغراض التعليمية فقط · لا يغني عن الطبيب</i>"
    ),
    "es": (
        "👋 <b>¡Hola {name}! Soy MedMind AI.</b>\n\n"
        "Tu asistente médico personal con IA — disponible 24/7 en Telegram.\n\n"
        "<b>🎯 ¿Qué puedo hacer?</b>\n"
        "🎓 /mode tutor — explico cualquier tema médico con claridad\n"
        "🩺 /mode case — analizo casos clínicos paso a paso\n"
        "🔬 /mode differential — construyo diagnósticos diferenciales\n"
        "🏥 /mode patient — explico diagnósticos en lenguaje sencillo\n"
        "⚖️ /mode second_opinion — reviso planes de tratamiento según guías\n\n"
        "<b>📚 MedMind Pro — plataforma completa de educación médica:</b>\n"
        "• Más de 500 módulos interactivos en todas las especialidades\n"
        "• Base de medicamentos, calculadoras clínicas, imágenes médicas\n"
        "• Tutor IA, analíticas de progreso, tarjetas de estudio\n"
        "→ medmind.pro\n\n"
        "💬 <b>Gratis:</b> {limit} mensajes/día\n"
        "⚡ <b>Pro:</b> ilimitado + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Vincular cuenta: /link\n\n"
        "¡Escribe cualquier pregunta médica para empezar! 👇\n\n"
        "⚕️ <i>Solo educativo · no sustituye al médico</i>"
    ),
    "fr": (
        "👋 <b>Bonjour {name}! Je suis MedMind AI.</b>\n\n"
        "Votre assistant médical IA personnel — disponible 24h/24 sur Telegram.\n\n"
        "<b>🎯 Ce que je peux faire:</b>\n"
        "🎓 /mode tutor — j'explique tout sujet médical clairement\n"
        "🩺 /mode case — j'analyse des cas cliniques étape par étape\n"
        "🔬 /mode differential — je construis des diagnostics différentiels\n"
        "🏥 /mode patient — j'explique les diagnostics en langage simple\n"
        "⚖️ /mode second_opinion — je révise les plans de traitement selon les recommandations\n\n"
        "<b>📚 MedMind Pro — plateforme complète d'éducation médicale:</b>\n"
        "• Plus de 500 modules interactifs dans toutes les spécialités\n"
        "• Base de médicaments, calculateurs cliniques, imagerie médicale\n"
        "• Tuteur IA, analytiques de progression, fiches de révision\n"
        "→ medmind.pro\n\n"
        "💬 <b>Gratuit:</b> {limit} messages/jour\n"
        "⚡ <b>Pro:</b> illimité + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Lier votre compte: /link\n\n"
        "Posez n'importe quelle question médicale pour commencer! 👇\n\n"
        "⚕️ <i>À des fins éducatives uniquement · ne remplace pas un médecin</i>"
    ),
    "de": (
        "👋 <b>Hallo {name}! Ich bin MedMind AI.</b>\n\n"
        "Dein persönlicher KI-Medizinassistent — 24/7 verfügbar in Telegram.\n\n"
        "<b>🎯 Was ich kann:</b>\n"
        "🎓 /mode tutor — erkläre medizinische Themen klar und präzise\n"
        "🩺 /mode case — analysiere klinische Fälle Schritt für Schritt\n"
        "🔬 /mode differential — erstelle strukturierte Differenzialdiagnosen\n"
        "🏥 /mode patient — erkläre Diagnosen in einfacher Sprache\n"
        "⚖️ /mode second_opinion — prüfe Behandlungspläne anhand von Leitlinien\n\n"
        "<b>📚 MedMind Pro — komplette medizinische Lernplattform:</b>\n"
        "• Über 500 interaktive Module in allen Fachgebieten\n"
        "• Arzneimitteldatenbank, klinische Rechner, medizinische Bildgebung\n"
        "• KI-Tutor, Fortschrittsanalysen, Lernkarten\n"
        "→ medmind.pro\n\n"
        "💬 <b>Kostenlos:</b> {limit} Nachrichten/Tag\n"
        "⚡ <b>Pro:</b> unbegrenzt + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Konto verknüpfen: /link\n\n"
        "Stell einfach eine medizinische Frage! 👇\n\n"
        "⚕️ <i>Nur zu Bildungszwecken · kein Ersatz für einen Arzt</i>"
    ),
    "tr": (
        "👋 <b>Merhaba {name}! Ben MedMind AI.</b>\n\n"
        "Kişisel yapay zeka tıp asistanın — Telegram'da 7/24 hizmetinde.\n\n"
        "<b>🎯 Neler yapabilirim:</b>\n"
        "🎓 /mode tutor — her tıbbi konuyu açıkça anlatırım\n"
        "🩺 /mode case — klinik vakaları adım adım incelerim\n"
        "🔬 /mode differential — yapılandırılmış ayırıcı tanı oluştururum\n"
        "🏥 /mode patient — tanıları sade dille açıklarım\n"
        "⚖️ /mode second_opinion — tedavi planlarını kılavuzlara göre değerlendiririm\n\n"
        "<b>📚 MedMind Pro — eksiksiz tıp eğitim platformu:</b>\n"
        "• Tüm uzmanlıklarda 500+ interaktif modül\n"
        "• İlaç veritabanı, klinik hesaplayıcılar, tıbbi görüntüleme\n"
        "• Yapay zeka öğretmen, ilerleme analizleri, flash kartlar\n"
        "→ medmind.pro\n\n"
        "💬 <b>Ücretsiz:</b> günde {limit} mesaj\n"
        "⚡ <b>Pro:</b> sınırsız + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Hesabını bağla: /link\n\n"
        "Herhangi bir tıbbi soru sor, başlayalım! 👇\n\n"
        "⚕️ <i>Yalnızca eğitim amaçlı · doktor yerine geçmez</i>"
    ),
    "pt": (
        "👋 <b>Olá {name}! Sou o MedMind AI.</b>\n\n"
        "Seu assistente médico pessoal com IA — disponível 24/7 no Telegram.\n\n"
        "<b>🎯 O que posso fazer:</b>\n"
        "🎓 /mode tutor — explico qualquer tema médico com clareza\n"
        "🩺 /mode case — analiso casos clínicos passo a passo\n"
        "🔬 /mode differential — construo diagnósticos diferenciais\n"
        "🏥 /mode patient — explico diagnósticos em linguagem simples\n"
        "⚖️ /mode second_opinion — reviso planos de tratamento pelas diretrizes\n\n"
        "<b>📚 MedMind Pro — plataforma completa de educação médica:</b>\n"
        "• Mais de 500 módulos interativos em todas as especialidades\n"
        "• Base de medicamentos, calculadoras clínicas, imagens médicas\n"
        "• Tutor IA, análises de progresso, flashcards\n"
        "→ medmind.pro\n\n"
        "💬 <b>Grátis:</b> {limit} mensagens/dia\n"
        "⚡ <b>Pro:</b> ilimitado + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Vincular conta: /link\n\n"
        "Digite qualquer pergunta médica para começar! 👇\n\n"
        "⚕️ <i>Apenas para fins educacionais · não substitui médico</i>"
    ),
    "id": (
        "👋 <b>Halo {name}! Saya MedMind AI.</b>\n\n"
        "Asisten medis AI pribadimu — tersedia 24/7 di Telegram.\n\n"
        "<b>🎯 Apa yang bisa saya lakukan:</b>\n"
        "🎓 /mode tutor — menjelaskan topik medis apapun dengan jelas\n"
        "🩺 /mode case — menganalisis kasus klinis langkah demi langkah\n"
        "🔬 /mode differential — membangun diagnosis banding terstruktur\n"
        "🏥 /mode patient — menjelaskan diagnosis dengan bahasa sederhana\n"
        "⚖️ /mode second_opinion — meninjau rencana pengobatan sesuai panduan\n\n"
        "<b>📚 MedMind Pro — platform pendidikan medis lengkap:</b>\n"
        "• 500+ modul interaktif di semua spesialisasi\n"
        "• Database obat, kalkulator klinis, pencitraan medis\n"
        "• Tutor AI, analitik kemajuan, flashcard\n"
        "→ medmind.pro\n\n"
        "💬 <b>Gratis:</b> {limit} pesan/hari\n"
        "⚡ <b>Pro:</b> tak terbatas + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Hubungkan akun: /link\n\n"
        "Ketik pertanyaan medis apapun untuk mulai! 👇\n\n"
        "⚕️ <i>Hanya untuk edukasi · bukan pengganti dokter</i>"
    ),
    "en": (
        "👋 <b>Hi {name}! I'm MedMind AI.</b>\n\n"
        "Your personal AI medical assistant — available 24/7, right inside Telegram.\n\n"
        "<b>🎯 What I can do:</b>\n"
        "🎓 /mode tutor — explain any medical topic clearly\n"
        "🩺 /mode case — work through clinical cases step by step\n"
        "🔬 /mode differential — build structured differential diagnoses\n"
        "🏥 /mode patient — explain diagnoses in plain language\n"
        "⚖️ /mode second_opinion — review treatment plans vs guidelines\n\n"
        "<b>📚 MedMind Pro — complete medical education platform:</b>\n"
        "• 500+ interactive modules across all specialties\n"
        "• Drug database, clinical calculators, medical imaging\n"
        "• AI tutor, progress analytics, flashcards\n"
        "→ medmind.pro\n\n"
        "💬 <b>Free:</b> {limit} messages/day · Llama 3.3\n"
        "⚡ <b>Pro:</b> unlimited + Claude Sonnet → medmind.pro/pricing\n"
        "🔗 Link your account: /link\n\n"
        "Just type any medical question to get started! 👇\n\n"
        "⚕️ <i>Educational use only · not a substitute for professional advice</i>"
    ),
}


async def cmd_start(chat_id: int, first_name: str, lang: str = "en") -> None:
    code = lang.split("-")[0].lower()
    template = _START_TEXTS.get(code, _START_TEXTS["en"])
    text = template.format(name=first_name, limit=DAILY_FREE_LIMIT)
    await send_message(chat_id, text, parse_mode="HTML")


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
        "👤 *Health Profile*\n"
        "/profile — view your saved health data\n"
        "/report — health history (share with a doctor)\n"
        "/forget — clear all stored health data\n\n"
        "📅 *Daily tracking*\n"
        "/checkin `[HH:MM]` — daily mood check-in (default 08:00 UTC)\n"
        "/checkin `off` — disable\n\n"
        "💊 *Medication reminders*\n"
        "/remind `add Metformin 08:00` — set daily reminder\n"
        "/remind `list` · /remind `del name`\n\n"
        "📊 *Health metrics*\n"
        "/track `glucose 5.2` · /track `bp 120/80` · /track `weight 72`\n"
        "/tracklog `[metric]` — view history\n\n"
        "📷 *Send a photo* of an ECG, blood test, X-ray, skin condition, "
        "or any medical document for analysis.\n\n"
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


async def cmd_start_weblink(chat_id: int, code: str, first_name: str, lang: str) -> None:
    """Complete web-initiated linking: /start wl_{code}."""
    try:
        redis = await get_redis()
        user_id_bytes = await redis.get(f"tg_weblink:{code}")
        if not user_id_bytes:
            await send_message(
                chat_id,
                "⚠️ This link has *expired* (10 minutes limit).\n\n"
                "Please generate a new one at medmind.pro/bots",
                parse_mode="Markdown",
            )
            return
        user_id = user_id_bytes.decode()
        import uuid as _uuid
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == _uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            if not user:
                await send_message(chat_id, "⚠️ Account not found. Please try again from medmind.pro/bots")
                return
            if user.telegram_chat_id and user.telegram_chat_id != str(chat_id):
                await send_message(
                    chat_id,
                    "⚠️ Your MedMind account is already linked to a *different* Telegram account.\n\n"
                    "To re-link, use the website settings to unlink first.",
                    parse_mode="Markdown",
                )
                return
            user.telegram_chat_id = str(chat_id)
            db.add(user)
            await db.commit()
            await redis.delete(f"tg_weblink:{code}")
            tier = user.subscription_tier or "free"
            logger.info("Telegram linked (web-init): user=%s chat_id=%s", user.email, chat_id)

        await send_message(
            chat_id,
            f"✅ *Telegram linked successfully!*\n\n"
            f"👤 Account: {user.email}\n"
            f"📊 Plan: {tier.title()}\n\n"
            f"Your Telegram is now connected to MedMind. All your bot conversations will appear in your account history.\n\n"
            f"Send any message to start! Type /help to see all commands.\n\n"
            f"⚕️ _Educational use only · medmind.pro_",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("cmd_start_weblink error: %s", e)
        await send_message(chat_id, "⚠️ Linking failed. Please try again or use /link")


# ── Patient state machine: AI final answer ────────────────────────────────────

async def call_ai_patient_final(chat_id: int, intake: dict) -> str:
    linked_user = await get_linked_user(chat_id)
    profile     = await get_profile(chat_id)

    complaint  = intake.get("complaint", "")
    ctx_answer = intake.get("ctx_answer", "")
    symptoms   = intake.get("symptoms", [])
    category   = intake.get("category", "general")
    subject    = intake.get("subject", "self")

    # Extract and persist age/sex from context answer
    age, sex = _extract_age_sex(ctx_answer)
    subj_data = _subject_data(profile, subject)
    if age:
        subj_data["age"] = age
    if sex:
        subj_data["sex"] = sex
    profile["last_subject"] = subject

    # Append to health log (keeps last 50 entries)
    from datetime import datetime, timezone as _tz
    log_entry = {
        "date":      datetime.now(_tz.utc).strftime("%Y-%m-%d"),
        "subject":   subject,
        "complaint": complaint[:120],
        "category":  category,
        "symptoms":  symptoms,
    }
    profile.setdefault("log", []).append(log_entry)
    profile["log"] = profile["log"][-50:]

    linked_uid = str(linked_user.id) if linked_user else None
    await save_profile(chat_id, profile, linked_user_id=linked_uid)

    # Proactive pattern alert (fire-and-forget, don't block reply)
    import asyncio as _asyncio
    lang_for_pattern = intake.get("lang", "en")
    _asyncio.ensure_future(check_symptom_patterns(chat_id, profile, category, lang_for_pattern))

    # Build profile context block
    profile_lines: list[str] = []
    if subj_data.get("age") or subj_data.get("sex"):
        demo = f"{subj_data.get('age','?')}{'F' if subj_data.get('sex')=='female' else 'M' if subj_data.get('sex') else ''}"
        profile_lines.append(f"Patient demographics: {demo}")
    if subj_data.get("conditions"):
        profile_lines.append(f"Known conditions: {', '.join(subj_data['conditions'])}")
    if subj_data.get("medications"):
        profile_lines.append(f"Current medications: {', '.join(subj_data['medications'])}")
    if subj_data.get("allergies"):
        profile_lines.append(f"Allergies: {', '.join(subj_data['allergies'])}")

    # Human-readable labels for symptom buttons
    all_buttons: dict[str, str] = {}
    for cat_data in ADAPTIVE_Q.values():
        for row in cat_data["buttons"]:
            for label, cb in row:
                all_buttons[cb[4:]] = label
    selected_labels = [all_buttons.get(s, s) for s in symptoms]

    context_text = ""
    if subject != "self":
        context_text += f"Note: Patient is the user's {subject} (not the user themselves).\n"
    if profile_lines:
        context_text += "\n".join(profile_lines) + "\n"
    context_text += (
        f"Chief complaint: {complaint}\n"
        f"Duration/severity context: {ctx_answer}\n"
        f"Additional symptoms selected: {', '.join(selected_labels) if selected_labels else 'none'}\n"
        f"Category: {category}"
    )

    triage_key = "green"
    if any(s in symptoms for s in ["hemoptysis", "severe_dyspnea", "palpitations", "radiation", "bladder", "neuro_leg"]):
        triage_key = "red"
    elif any(s in symptoms for s in ["fever", "neck_stiff", "photophobia", "sweating", "dyspnea", "radiation_leg"]):
        triage_key = "yellow"
    triage_line = TRIAGE_LEVELS[triage_key]

    prompt = PATIENT_ANSWER_PROMPT.format(context=context_text, triage_line=triage_line)
    return await call_ai("patient", prompt, [], linked_user)


# ── Patient state machine: callback query handler ─────────────────────────────

async def handle_callback_query(update: dict) -> None:
    cq      = update["callback_query"]
    cq_id   = cq["id"]
    chat_id = cq["message"]["chat"]["id"]
    msg_id  = cq["message"]["message_id"]
    data    = cq.get("data", "")

    await tg_call("answerCallbackQuery", {"callback_query_id": cq_id})

    intake = await get_intake(chat_id)
    if not intake:
        return  # stale callback

    if data.startswith("sym:"):
        sym = data[4:]
        symptoms = intake.get("symptoms", [])
        if sym in symptoms:
            symptoms.remove(sym)
        else:
            symptoms.append(sym)
        intake["symptoms"] = symptoms
        await set_intake(chat_id, intake)

        # Rebuild keyboard with checked state
        category = intake.get("category", "general")
        lang     = intake.get("lang", "en")
        q = ADAPTIVE_Q.get(category, ADAPTIVE_Q["general"])
        keyboard = []
        for row in q["buttons"]:
            new_row = []
            for label, cb in row:
                sym_key = cb[4:]
                checked_label = (f"✓ {label}" if sym_key in symptoms else label)
                new_row.append({"text": checked_label, "callback_data": cb})
            keyboard.append(new_row)
        done_label = DONE_BTN.get(lang, DONE_BTN["en"])
        keyboard.append([{"text": done_label, "callback_data": "intake:done"}])
        await tg_call("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "reply_markup": {"inline_keyboard": keyboard},
        })

    elif data.startswith("checkin:"):
        mood = data[8:]  # good / ok / bad / symptoms
        await tg_call("editMessageReplyMarkup", {
            "chat_id": chat_id, "message_id": msg_id,
            "reply_markup": {"inline_keyboard": []},
        })
        # Log mood to profile
        from datetime import datetime, timezone as _tz
        profile = await get_profile(chat_id)
        profile.setdefault("checkin_log", []).append({
            "date": datetime.now(_tz.utc).strftime("%Y-%m-%d"), "mood": mood,
        })
        profile["checkin_log"] = profile["checkin_log"][-90:]
        await save_profile(chat_id, profile)

        if mood == "symptoms":
            # Switch to patient mode and prompt
            await set_mode(chat_id, "patient")
            await clear_intake(chat_id)
            _PROMPT: dict[str, str] = {
                "en": "Tell me what you're experiencing and I'll help you understand it. 🏥",
                "ru": "Расскажите что вас беспокоит, и я помогу разобраться. 🏥",
                "ar": "أخبرني بما تشعر به وسأساعدك. 🏥",
                "es": "Cuéntame qué sientes y te ayudaré. 🏥",
            }
            lang_ci = intake.get("lang", "en") if intake else "en"
            await send_message(chat_id, _PROMPT.get(lang_ci, _PROMPT["en"]))
        else:
            _ACK: dict[str, dict[str, str]] = {
                "good": {"en": "🟢 Great! Keep it up. I'll check in again tomorrow.",
                         "ru": "🟢 Отлично! Увидимся завтра.", "ar": "🟢 رائع! أراك غداً."},
                "ok":   {"en": "🟡 Glad you're managing. Take care today.",
                         "ru": "🟡 Хорошо. Берегите себя.", "ar": "🟡 يسعدني ذلك. اعتنِ بنفسك."},
                "bad":  {"en": "🔴 Sorry to hear that. Rest if you can. Type /mode patient if you'd like guidance.",
                         "ru": "🔴 Жаль слышать. Отдохните. Напишите /mode patient если нужна помощь.",
                         "ar": "🔴 آسف لسماع ذلك. استرح إذا أمكنك."},
            }
            lang_ci = intake.get("lang", "en") if intake else "en"
            ack_map = _ACK.get(mood, _ACK["ok"])
            await send_message(chat_id, ack_map.get(lang_ci, ack_map["en"]))

    elif data.startswith("subject:"):
        # User clarified who the question is for
        chosen_subject = data[8:]  # "self" or relation label
        await tg_call("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "reply_markup": {"inline_keyboard": []},
        })
        intake["subject"] = chosen_subject
        intake["stage"] = 0
        await set_intake(chat_id, intake)
        lang_code = intake.get("lang", "en")
        profile = await get_profile(chat_id)
        subj_data = _subject_data(profile, chosen_subject)
        question = _build_ctx_q(subj_data, chosen_subject, lang_code)
        await send_message(chat_id, question)

    elif data == "intake:done":
        # Remove keyboard, then generate final answer
        await tg_call("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": msg_id,
            "reply_markup": {"inline_keyboard": []},
        })
        await send_typing(chat_id)
        try:
            reply = await call_ai_patient_final(chat_id, intake)
        except Exception as e:
            logger.error("call_ai_patient_final error: %s", e)
            reply = "⚠️ Something went wrong generating your health guidance. Please try again."
        await clear_intake(chat_id)
        await send_message(chat_id, reply)


# ── Proactive pattern detection ───────────────────────────────────────────────

async def check_symptom_patterns(chat_id: int, profile: dict, category: str, lang: str) -> None:
    """Alert user when same symptom category appears 3+ times in 14 days."""
    from datetime import datetime, timezone, timedelta
    log = profile.get("log", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
    recent = [e for e in log if e.get("date", "") >= cutoff and e.get("category") == category]
    if len(recent) < 3:
        return
    try:
        redis   = await get_redis()
        pat_key = f"tg_pattern:{chat_id}:{category}"
        if await redis.exists(pat_key):
            return
        await redis.set(pat_key, "1", ex=86400 * 7)
    except Exception:
        return
    n = len(recent)
    _ALERT: dict[str, str] = {
        "en": (f"📊 *Pattern detected*\n\nYou've mentioned *{category}* symptoms "
               f"*{n} times* in the last 14 days.\n\n"
               "This may be worth discussing with a doctor, especially if symptoms are recurring or worsening.\n"
               "Use /report to share your history with your physician."),
        "ru": (f"📊 *Обнаружен паттерн*\n\nВы упоминали *{category}* "
               f"*{n} раз{'а' if n<5 else ''}* за последние 14 дней.\n\n"
               "Рекомендуем обсудить это с врачом, особенно если симптомы повторяются.\n"
               "/report — поделиться историей с врачом."),
        "ar": (f"📊 *نمط مكتشف*\n\nذكرت أعراض *{category}* *{n} مرات* في آخر 14 يوماً.\n\n"
               "يُنصح بمراجعة طبيبك إن استمرت الأعراض."),
        "es": (f"📊 *Patrón detectado*\n\nHas mencionado síntomas de *{category}* "
               f"*{n} veces* en los últimos 14 días.\n\n"
               "Considera consultar con un médico. /report para compartir tu historial."),
    }
    await send_message(chat_id, _ALERT.get(lang, _ALERT["en"]))


# ── Daily check-in ─────────────────────────────────────────────────────────────

async def send_checkin_message(chat_id: int, lang: str) -> None:
    """Send daily check-in with inline mood buttons."""
    text    = _CHECKIN_Q.get(lang, _CHECKIN_Q["en"])
    buttons = _CHECKIN_BTNS.get(lang, _CHECKIN_BTNS["en"])
    keyboard = [[{"text": label, "callback_data": cb}] for label, cb in buttons]
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(
                TG_API.format(token=token, method="sendMessage"),
                json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown",
                      "reply_markup": {"inline_keyboard": keyboard}},
            )
        except Exception as e:
            logger.warning("send_checkin_message error: %s", e)


# ── Image / photo analysis via Claude Vision ──────────────────────────────────

async def analyze_image(chat_id: int, message: dict, linked_user: Optional[User]) -> None:
    """Download and medically analyse a photo sent to the bot."""
    if "photo" in message:
        file_id = message["photo"][-1]["file_id"]
        ext = "jpg"
    elif "document" in message:
        doc = message["document"]
        mime = doc.get("mime_type", "")
        if not mime.startswith("image/"):
            await send_message(chat_id, "Please send an image file (JPEG, PNG, etc.) for analysis.")
            return
        file_id = doc["file_id"]
        ext = mime.split("/")[-1]
    else:
        return

    caption = (message.get("caption") or "").strip()
    await send_typing(chat_id)

    file_info = await tg_call("getFile", {"file_id": file_id})
    file_path = file_info.get("result", {}).get("file_path", "")
    if not file_path:
        await send_message(chat_id, "⚠️ Could not retrieve image. Please try again.")
        return

    token = settings.TELEGRAM_BOT_TOKEN
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(file_url)
            r.raise_for_status()
            image_bytes = r.content
    except Exception as e:
        logger.warning("Image download failed: %s", e)
        await send_message(chat_id, "⚠️ Failed to download image. Please try again.")
        return

    image_b64 = base64.b64encode(image_bytes).decode()
    ext_from_path = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ext
    _mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                 "gif": "image/gif", "webp": "image/webp"}
    media_type = _mime_map.get(ext_from_path, "image/jpeg")

    api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not api_key:
        await send_message(chat_id, "⚠️ Image analysis is temporarily unavailable.")
        return

    user_note = f"User note: {caption}\n\n" if caption else ""
    vision_prompt = (
        f"{user_note}"
        "You are a medical educator analysing a medical image or document. "
        "First identify the document type: ECG/EKG, blood test / lab panel, X-ray, CT/MRI, "
        "skin lesion / rash, medication / pill, urine / stool analysis, ophthalmology, "
        "pathology slide, or non-medical image.\n\n"
        "Structure your response exactly:\n"
        "🔬 *Document type*: ...\n"
        "📊 *Key observations*:\n• ...\n• ...\n"
        "📚 *What this may suggest* (educational, not a diagnosis):\n...\n\n"
        "⚠️ *Always end with*: These observations are for educational purposes only. "
        "A qualified clinician must evaluate the actual results.\n\n"
        "If the image is not medical, say so and offer to help with medical questions. "
        "Keep response under 300 words. Never diagnose."
    )

    try:
        import anthropic as _ant
        model = "claude-sonnet-4-6" if (
            linked_user and linked_user.subscription_tier in ("pro", "clinic", "lifetime")
        ) else "claude-haiku-4-5-20251001"
        client = _ant.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model, max_tokens=1000,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                {"type": "text", "text": vision_prompt},
            ]}],
        )
        reply = response.content[0].text
    except Exception as e:
        logger.warning("Vision API failed: %s", e)
        reply = (
            "⚠️ Image analysis temporarily unavailable. Please try again in a moment.\n\n"
            "I can analyse ECGs, blood tests, X-rays, skin conditions, medications and more."
        )

    await send_message(chat_id, reply)


# ── Profile commands ───────────────────────────────────────────────────────────

async def cmd_profile(chat_id: int, linked_user=None) -> None:
    profile = await get_profile(chat_id)

    def _fmt(data: dict, label: str) -> str:
        age = data.get("age")
        sex = data.get("sex")
        demo = f"{age or '?'}{'F' if sex=='female' else 'M' if sex=='male' else ''}" if (age or sex) else "?"
        lines = [f"*{label}* ({demo})"]
        if data.get("conditions"):
            lines.append("  Conditions: " + ", ".join(data["conditions"]))
        if data.get("medications"):
            lines.append("  Medications: " + ", ".join(data["medications"]))
        if data.get("allergies"):
            lines.append("  Allergies: " + ", ".join(data["allergies"]))
        if len(lines) == 1:
            lines.append("  _No health data yet_")
        return "\n".join(lines)

    sections = [_fmt(profile.get("self", {}), "You")]
    for key, data in profile.get("others", {}).items():
        sections.append(_fmt(data, key.title()))

    log = profile.get("log", [])
    log_summary = f"\n\n📊 *Health log:* {len(log)} entr{'y' if len(log)==1 else 'ies'} · /report to view" if log else ""

    # TTL / storage status
    try:
        redis = await get_redis()
        ttl = await redis.ttl(f"tg_profile:{chat_id}")
    except Exception:
        ttl = -1

    is_paid = linked_user and linked_user.subscription_tier in ("pro", "clinic", "lifetime", "student")
    if is_paid or ttl > _PROFILE_FREE_TTL:
        storage_line = "🟢 *Storage: permanent* (Pro account)"
    elif ttl > 0:
        days = max(1, ttl // 86400)
        if days <= 14:
            storage_line = f"🔴 *Expires in {days} day{'s' if days!=1 else ''}* · /link Pro account to keep permanently"
        else:
            storage_line = f"⏱ *Stored for {days} more days* (auto-renews on activity)"
    else:
        storage_line = "⏱ Profile created · stored for 90 days from last activity"

    text = (
        "👤 *Your Health Profiles*\n\n"
        + "\n\n".join(sections)
        + log_summary
        + f"\n\n{storage_line}"
        + "\n\n_/forget — clear all data_"
    )
    await send_message(chat_id, text)


async def cmd_report(chat_id: int) -> None:
    """Generate a health history summary — useful to share with a doctor."""
    profile = await get_profile(chat_id)
    log = profile.get("log", [])

    if not log:
        await send_message(
            chat_id,
            "📋 No health history yet.\n\n"
            "Switch to patient mode (/mode patient) and describe a symptom — "
            "each completed intake is saved to your log."
        )
        return

    self_data = profile.get("self", {})
    age = self_data.get("age")
    sex = self_data.get("sex")
    header = "📋 *Health History Report*"
    if age or sex:
        demo = f"{age or '?'}{'F' if sex=='female' else 'M' if sex=='male' else ''}"
        header += f" — {demo}"

    # Last 15 entries, newest first
    entries = list(reversed(log[-15:]))
    lines = [header, ""]
    prev_date = None
    for e in entries:
        date     = e.get("date", "?")
        subject  = e.get("subject", "self")
        complaint = e.get("complaint", "")[:80]
        syms     = e.get("symptoms", [])
        sym_str  = f" (+{', '.join(syms[:3])})" if syms else ""
        who      = "" if subject == "self" else f" [{subject}]"
        if date != prev_date:
            lines.append(f"📅 *{date}*")
            prev_date = date
        lines.append(f"  • {complaint}{sym_str}{who}")

    conditions = self_data.get("conditions", [])
    medications = self_data.get("medications", [])
    if conditions:
        lines += ["", f"🏥 *Known conditions:* {', '.join(conditions)}"]
    if medications:
        lines += [f"💊 *Medications:* {', '.join(medications)}"]

    lines += ["", "_Share this with your doctor for context · medmind.pro_"]
    await send_message(chat_id, "\n".join(lines))


async def cmd_forget(chat_id: int) -> None:
    try:
        redis = await get_redis()
        await redis.delete(f"tg_profile:{chat_id}")
        await redis.delete(f"tg_intake:{chat_id}")
        await redis.delete(f"tg_upsell_expiry:{chat_id}")
    except Exception:
        pass
    await send_message(chat_id, "🗑 All your health profile data has been cleared.")


async def cmd_checkin(chat_id: int, args: str, lang: str) -> None:
    """Enable/disable/reschedule daily check-in. Usage: /checkin | /checkin 09:00 | /checkin off"""
    redis = await get_redis()
    arg = args.strip().lower()

    if arg in ("off", "stop", "disable", "выкл", "стоп"):
        await redis.delete(f"tg_checkin:{chat_id}")
        await send_message(chat_id, "✅ Daily check-in disabled. Type /checkin to re-enable.")
        return

    time_str = "08:00"
    if re.match(r'^\d{1,2}:\d{2}$', arg):
        h, m = map(int, arg.split(":"))
        time_str = f"{h:02d}:{m:02d}"

    await redis.set(
        f"tg_checkin:{chat_id}",
        json.dumps({"time": time_str, "lang": lang}),
        ex=86400 * 400,
    )
    _OK: dict[str, str] = {
        "en": f"✅ *Daily check-in enabled* at *{time_str} UTC*.\nEvery day I'll ask how you're feeling. /checkin off to disable.",
        "ru": f"✅ *Ежедневный чек-ин включён* в *{time_str} UTC*.\nКаждый день буду спрашивать как вы. /checkin off — отключить.",
        "ar": f"✅ *تم تفعيل تسجيل يومي* في *{time_str} UTC*.",
        "es": f"✅ *Check-in diario activado* a las *{time_str} UTC*.",
    }
    await send_message(chat_id, _OK.get(lang, _OK["en"]))


async def cmd_remind(chat_id: int, args: str) -> None:
    """Medication reminders. Usage: /remind add Metformin 500mg 08:00 | /remind list | /remind del name"""
    parts = args.strip().split(None, 1)
    sub   = parts[0].lower() if parts else "add"
    rest  = parts[1] if len(parts) > 1 else ""

    if sub in ("list", "show", "ls"):
        profile   = await get_profile(chat_id)
        reminders = profile.get("reminders", {})
        if not reminders:
            await send_message(chat_id, "No reminders set.\n\nUsage: `/remind add Metformin 500mg 08:00`")
            return
        lines = ["💊 *Medication reminders:*\n"]
        for med, t in reminders.items():
            lines.append(f"• {med} — {t} UTC")
        lines.append("\n`/remind del <name>` to remove")
        await send_message(chat_id, "\n".join(lines))
        return

    if sub in ("del", "delete", "remove", "rm"):
        profile   = await get_profile(chat_id)
        reminders = profile.get("reminders", {})
        target = rest.strip()
        if target in reminders:
            del reminders[target]
            profile["reminders"] = reminders
            await save_profile(chat_id, profile)
            # Remove from sorted-set queue
            try:
                redis   = await get_redis()
                entries = await redis.zrange("tg_reminder_queue", 0, -1)
                for e in entries:
                    d = json.loads(e)
                    if d.get("chat_id") == chat_id and d.get("med") == target:
                        await redis.zrem("tg_reminder_queue", e)
                        break
            except Exception:
                pass
            await send_message(chat_id, f"✅ Reminder for *{target}* removed.")
        else:
            await send_message(chat_id, f"No reminder found for '{target}'.")
        return

    # "add" (default): parse "Metformin 500mg 08:00"
    text_for_parse = rest if sub == "add" else (args.strip())
    t_match = re.search(r'\b(\d{1,2}:\d{2})\b', text_for_parse)
    if not t_match:
        await send_message(chat_id,
            "Usage: `/remind add Metformin 500mg 08:00`\n\n"
            "List: `/remind list`\n"
            "Delete: `/remind del Metformin 500mg`")
        return
    time_str = f"{int(t_match.group(1).split(':')[0]):02d}:{t_match.group(1).split(':')[1]}"
    med_name = text_for_parse.replace(t_match.group(0), "").strip().strip(",").strip()
    if not med_name:
        await send_message(chat_id, "Please include the medication name, e.g. `/remind add Metformin 500mg 08:00`")
        return

    # Save to profile
    profile = await get_profile(chat_id)
    profile.setdefault("reminders", {})[med_name] = time_str
    await save_profile(chat_id, profile)

    # Add to Redis sorted-set queue (score = next fire timestamp)
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    h, m = map(int, time_str.split(":"))
    next_fire = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if next_fire <= now:
        next_fire += timedelta(days=1)
    try:
        redis = await get_redis()
        entry = json.dumps({"chat_id": chat_id, "med": med_name, "time": time_str})
        await redis.zadd("tg_reminder_queue", {entry: next_fire.timestamp()})
    except Exception:
        pass

    await send_message(chat_id, f"✅ *{med_name}* reminder set for *{time_str} UTC* daily.\n`/remind list` to see all reminders.")


async def cmd_track(chat_id: int, args: str) -> None:
    """Log a health metric. Usage: /track glucose 5.2 | /track bp 120/80 | /track weight 72"""
    parts = args.strip().split(None, 1)
    if len(parts) < 2:
        await send_message(chat_id,
            "📊 *Track a health metric*\n\n"
            "Usage: `/track <metric> <value>`\n\n"
            "Examples:\n"
            "• `/track glucose 5.2` (mmol/L)\n"
            "• `/track bp 120/80` (mmHg)\n"
            "• `/track weight 72` (kg)\n"
            "• `/track temp 37.2` (°C)\n"
            "• `/track pulse 72` (bpm)\n"
            "• `/track spo2 98` (%)\n\n"
            "/tracklog to view history")
        return

    raw_metric = parts[0].lower()
    value_str  = parts[1].strip()
    canonical  = _TRACKER_CANONICAL.get(raw_metric, raw_metric)
    unit       = TRACKER_UNITS.get(canonical, "")

    from datetime import datetime, timezone as _tz
    now = datetime.now(_tz.utc)
    profile  = await get_profile(chat_id)
    readings = profile.setdefault("trackers", {}).setdefault(canonical, [])
    readings.append({"date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"), "value": value_str})
    profile["trackers"][canonical] = readings[-90:]  # keep last 90
    await save_profile(chat_id, profile)

    await send_message(chat_id,
        f"✅ *{canonical.title()}:* {value_str} {unit}\n_{now.strftime('%Y-%m-%d %H:%M')} UTC_\n\n/tracklog to view history")


async def cmd_tracklog(chat_id: int, args: str) -> None:
    """Show health metrics history. Usage: /tracklog | /tracklog glucose"""
    profile  = await get_profile(chat_id)
    trackers = profile.get("trackers", {})

    if not trackers:
        await send_message(chat_id,
            "No metrics tracked yet.\n\nStart with:\n"
            "• `/track glucose 5.2`\n"
            "• `/track bp 120/80`\n"
            "• `/track weight 72`")
        return

    filter_metric = args.strip().lower() or None
    if filter_metric:
        filter_metric = _TRACKER_CANONICAL.get(filter_metric, filter_metric)

    lines = ["📊 *Health Metrics*\n"]
    for metric, readings in trackers.items():
        if filter_metric and metric != filter_metric:
            continue
        unit = TRACKER_UNITS.get(metric, "")
        lines.append(f"*{metric.title()}* ({unit})")
        for r in reversed(readings[-10:]):
            lines.append(f"  {r['date']} {r.get('time','')} — {r['value']}")
        # Simple trend: compare first and last of recent 5
        if len(readings) >= 2:
            try:
                v1 = float(readings[-1]["value"].split("/")[0])
                v2 = float(readings[-3]["value"].split("/")[0]) if len(readings) >= 3 else float(readings[0]["value"].split("/")[0])
                arrow = "↗️" if v1 > v2 else "↘️" if v1 < v2 else "→"
                lines.append(f"  Trend: {arrow}")
            except Exception:
                pass
        lines.append("")

    lines.append("_/track <metric> <value> to add a reading_")
    await send_message(chat_id, "\n".join(lines))


# ── Telegram dialog → DB sync (fire-and-forget for linked users) ──────────────

async def sync_dialog_to_db(user_id: str, mode: str, user_text: str, ai_reply: str) -> None:
    """Save Telegram exchange to ai_conversations so it appears in /ai-history."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.models import AIConversation, AIConversationMessage
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIConversation)
                .where(
                    AIConversation.user_id == user_id,
                    AIConversation.mode == f"telegram_{mode}",
                )
                .order_by(AIConversation.created_at.desc())
                .limit(1)
            )
            conv = result.scalar_one_or_none()

            if not conv or conv.created_at.date() != today:
                conv = AIConversation(
                    user_id=user_id,
                    title=f"Telegram · {mode.title()} · {today}",
                    mode=f"telegram_{mode}",
                    specialty="telegram",
                )
                db.add(conv)
                await db.flush()

            db.add(AIConversationMessage(
                conversation_id=conv.id,
                role="user",
                content=user_text,
                model_used="telegram",
            ))
            db.add(AIConversationMessage(
                conversation_id=conv.id,
                role="assistant",
                content=ai_reply,
                model_used="telegram",
            ))
            conv.updated_at = datetime.utcnow()
            await db.commit()
    except Exception as e:
        logger.warning("sync_dialog_to_db failed: %s", e)


# ── Account linking endpoints ─────────────────────────────────────────────────

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
    """Bot-initiated link: user sends /link in Telegram, clicks URL, we save chat_id."""
    redis = await get_redis()
    chat_id_bytes = await redis.get(f"tg_link:{body.token}")
    if not chat_id_bytes:
        raise HTTPException(status_code=400, detail="Link expired or invalid. Use /link in @Medmindpro_bot to get a new one.")
    chat_id = chat_id_bytes.decode()
    existing = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
    other = existing.scalar_one_or_none()
    if other and other.id != current_user.id:
        raise HTTPException(status_code=409, detail="This Telegram account is already linked to another MedMind user.")
    current_user.telegram_chat_id = chat_id
    db.add(current_user)
    await db.commit()
    await redis.delete(f"tg_link:{body.token}")
    logger.info("Telegram linked (bot-init): user=%s chat_id=%s", current_user.email, chat_id)
    return {"ok": True, "email": current_user.email}


@router.post("/web-link")
async def generate_web_link(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """Web-initiated link: generate a deep-link the user opens in Telegram."""
    if current_user.telegram_chat_id:
        return {
            "already_linked": True,
            "telegram_chat_id": current_user.telegram_chat_id,
        }
    import secrets
    raw = secrets.token_urlsafe(8)
    code = "".join(c for c in raw if c.isalnum())[:8].upper()
    try:
        redis = await get_redis()
        await redis.set(f"tg_weblink:{code}", str(current_user.id), ex=600)
    except Exception:
        raise HTTPException(status_code=503, detail="Cache unavailable. Please try again.")
    deep_link = f"https://t.me/Medmindpro_bot?start=wl_{code}"
    return {"already_linked": False, "code": code, "deep_link": deep_link, "expires_in": 600}


@router.delete("/unlink")
async def unlink_telegram(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_get_current_user),
):
    """Remove Telegram linking from the current user's account."""
    current_user.telegram_chat_id = None
    db.add(current_user)
    await db.commit()
    return {"ok": True}


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

    # Inline button presses → patient intake handler
    if "callback_query" in update:
        await handle_callback_query(update)
        return {"ok": True}

    # Only handle regular messages
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id    = message["chat"]["id"]
    text       = (message.get("text") or "").strip()
    from_data  = message.get("from", {})
    first_name = from_data.get("first_name", "there")
    lang       = from_data.get("language_code", "en")

    # Photo / document → image analysis (caption becomes context, no rate-limit deduction)
    if "photo" in message or ("document" in message and not text):
        linked_user = await get_linked_user(chat_id)
        await analyze_image(chat_id, message, linked_user)
        return {"ok": True}

    if not text:
        return {"ok": True}

    # Route commands
    if text.startswith("/"):
        parts = text.split(None, 1)
        cmd   = parts[0].lower().split("@")[0]  # strip @botname suffix
        args  = parts[1] if len(parts) > 1 else ""

        if cmd == "/start":
            if args.startswith("wl_"):
                await cmd_start_weblink(chat_id, args[3:], first_name, lang)
            else:
                await cmd_start(chat_id, first_name, lang)
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
        elif cmd == "/profile":
            linked = await get_linked_user(chat_id)
            await cmd_profile(chat_id, linked)
        elif cmd == "/report":
            await cmd_report(chat_id)
        elif cmd == "/forget":
            await cmd_forget(chat_id)
        elif cmd == "/checkin":
            await cmd_checkin(chat_id, args, lang.split("-")[0].lower())
        elif cmd == "/remind":
            await cmd_remind(chat_id, args)
        elif cmd == "/track":
            await cmd_track(chat_id, args)
        elif cmd == "/tracklog":
            await cmd_tracklog(chat_id, args)
        else:
            await send_message(chat_id, "Unknown command. Use /help to see available commands.")
        return {"ok": True}

    # Track active users for weekly digest (TTL 8 days = auto-expire inactive)
    try:
        _redis = await get_redis()
        await _redis.sadd("tg_active_users", str(chat_id))
        await _redis.expire("tg_active_users", 86400 * 8)
        # Also refresh check-in TTL on activity
        _ci_key = f"tg_checkin:{chat_id}"
        if await _redis.exists(_ci_key):
            await _redis.expire(_ci_key, 86400 * 400)
    except Exception:
        pass

    # Regular message → AI
    linked_user = await get_linked_user(chat_id)
    lang_code   = lang.split("-")[0].lower()

    # Paid account → promote profile to long-lived storage
    if linked_user and linked_user.subscription_tier in ("pro", "clinic", "lifetime", "student"):
        await promote_profile_paid(chat_id)

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
        # Check profile expiry — show upsell once per week if expiring soon
        await maybe_send_expiry_upsell(chat_id, lang_code)
    else:
        remaining = None

    # Show typing indicator
    await send_typing(chat_id)

    # Get mode and history
    mode    = await get_mode(chat_id)
    history = await get_history(chat_id)

    # Patient mode: structured intake state machine
    if mode == "patient":
        intake = await get_intake(chat_id)

        if _is_emergency(text):
            # Emergency → bypass intake, answer immediately
            await clear_intake(chat_id)
            # fall through to standard call_ai below

        elif not intake:
            # Stage 0: first symptom message — detect subject, check profile, clarify if needed
            subject, guessed_sex = _detect_subject(text)
            profile = await get_profile(chat_id)
            last_subject = profile.get("last_subject", "self")
            category = _detect_category(text)

            # If no relation word AND last inquiry was about someone else → ask who this is for
            if subject == "self" and last_subject != "self":
                await set_intake(chat_id, {
                    "stage": "clarify", "complaint": text,
                    "category": category, "lang": lang_code,
                    "symptoms": [], "subject": "self",
                    "last_subject": last_subject,
                })
                await send_clarify_subject(chat_id, last_subject, lang_code)
                return {"ok": True}

            # Known subject → use profile demographics to shorten questions
            if guessed_sex:
                subj_data = _subject_data(profile, subject)
                if not subj_data.get("sex"):
                    subj_data["sex"] = guessed_sex
                    await save_profile(chat_id, profile)

            subj_data = _subject_data(profile, subject)
            await set_intake(chat_id, {
                "stage": 0, "complaint": text,
                "category": category, "lang": lang_code,
                "symptoms": [], "subject": subject,
            })
            question = _build_ctx_q(subj_data, subject, lang_code)
            history.append({"role": "user", "content": text})
            history.append({"role": "assistant", "content": question})
            await save_history(chat_id, history)
            if remaining is not None and remaining <= 3:
                question += f"\n\n_{remaining} messages left today · medmind.pro for unlimited_"
            await send_message(chat_id, question)
            return {"ok": True}

        elif intake.get("stage") == "clarify":
            # User typed a response to the "who is this for?" question instead of tapping button
            t = text.lower()
            if any(w in t for w in ["me", "myself", "я", "мне", "себя", "yo", "moi", "ich"]):
                chosen = "self"
            else:
                # Check if they mentioned the last person or typed "him/her/same"
                chosen = intake.get("last_subject", "self")
            intake["subject"] = chosen
            intake["stage"] = 0
            await set_intake(chat_id, intake)
            profile = await get_profile(chat_id)
            subj_data = _subject_data(profile, chosen)
            question = _build_ctx_q(subj_data, chosen, lang_code)
            await send_message(chat_id, question)
            return {"ok": True}

        elif intake.get("stage") == 0:
            # Received context answer (age/duration/severity) → show adaptive buttons
            intake["ctx_answer"] = text
            intake["stage"] = 1
            await set_intake(chat_id, intake)
            history.append({"role": "user", "content": text})
            await save_history(chat_id, history)
            await send_adaptive_buttons(chat_id, intake["category"], intake.get("lang", lang_code))
            return {"ok": True}

        else:
            # Stage 1: user typed extra text instead of tapping a button — append to context
            intake["ctx_answer"] = (intake.get("ctx_answer", "") + " " + text).strip()
            await set_intake(chat_id, intake)
            return {"ok": True}

    # Standard AI call (non-patient modes, or patient emergency bypass)
    try:
        reply = await call_ai(mode, text, history, linked_user)
    except Exception as e:
        logger.error(f"AI call failed for chat {chat_id}: {e}")
        reply = "⚠️ Something went wrong. Please try again."

    # Save history
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant", "content": reply})
    await save_history(chat_id, history)

    # Sync to DB for linked users (fire-and-forget, don't block reply)
    if linked_user:
        import asyncio as _asyncio
        _asyncio.ensure_future(sync_dialog_to_db(str(linked_user.id), mode, text, reply))

    # Append usage hint for free users
    if remaining is not None and remaining <= 3:
        reply += f"\n\n_{remaining} messages left today · medmind.pro for unlimited_"

    await send_message(chat_id, reply)
    return {"ok": True}
