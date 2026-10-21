#!/usr/bin/env python3
"""
MedMind AI — Bilingual Gulf exam Shorts for the Arabic channel
Question + options in ENGLISH (as on the real Prometric exam), explanation in ARABIC.

Why: Gulf nursing licensing exams (SNLE, DHA, DOH, MOH, QCHP, OMSB, NHRA, Kuwait)
are sat in English. A fully translated question does not prepare an Arabic-speaking
nurse for the exam; an English question with an Arabic explanation does.

Data:
  question / options / correct  ← mcq_questions (original English)
  Arabic explanation            ← nclex_shorts_translations.key_takeaway (lang='ar')
  Questions without a finished Arabic translation are skipped.

Video (1080×1920, ~40-60 s):
  [Arabic hook] → [EN question + options, EN voice] → [Arabic "think" card]
  → [Answer: letter + EN option, Arabic explanation, AR voice] → [Arabic CTA]

YouTube metadata:
  title         Arabic phrase + English exam keyword ("DHA") + English topic
  description   Arabic intro → English question & options → Arabic explanation → links
  language      defaultLanguage=ar (title/description), defaultAudioLanguage=ar
  localizations English title/description for viewers with an English UI
  local file    gulf_<exam>_<qid8>_en-ar.mp4 (YouTube ignores the file name; it is for logs)

Tracking: /opt/medmind/youtube_shorts_gulf_ar_uploaded.json (separate from the old
fully-Arabic NCLEX Shorts, so the same question can appear in the new format).

Usage:
    python3 youtube_shorts_gulf_ar_daily.py --exam dha --dry-run
    python3 youtube_shorts_gulf_ar_daily.py --exam snle --limit 2
    python3 youtube_shorts_gulf_ar_daily.py --demo --no-tts --out /tmp/ar_demo.mp4   # offline layout test

Cron idea (one exam per weekday, after the EN Gulf Shorts):
    40 13 * * 1  python3 .../youtube_shorts_gulf_ar_daily.py --exam snle --limit 2
    40 13 * * 2  python3 .../youtube_shorts_gulf_ar_daily.py --exam dha  --limit 2   (etc.)
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, features

# With libraqm, Pillow shapes and orders Arabic itself; pre-shaping it again breaks the
# letters (isolated forms, reversed). Without raqm we must reshape + bidi ourselves.
RAQM = features.check("raqm")

sys.path.insert(0, str(Path(__file__).parent))
from nclex_to_shorts import (  # noqa: E402  shared brand, fonts, DB
    W, H, BG_CARD, ACCENT, PINK, GREEN, AMBER, TEXT_W, TEXT_M,
    fb, fr, tw, wrap, _base_canvas, _db_conn,
)
import nclex_to_shorts as _nts  # noqa: E402  needed to toggle CANVAS_TRANSPARENT
from nclex_practice_session import _encode, _ffprobe_dur  # noqa: E402  ffmpeg pipeline

DAILY_LIMIT  = 2
WAIT_BETWEEN = 45
EN_VOICE     = os.environ.get("TTS_VOICE_EN", "en-US-EmmaMultilingualNeural")
AR_VOICE     = os.environ.get("TTS_VOICE_AR", "ar-SA-ZariyahNeural")  # Saudi Arabic: best for Gulf audience
EN_RATE      = "-5%"
AR_RATE      = "-15%"   # Arabic needs more breathing room: longer words, medical terms
THINK_SECS   = 5

TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token_ar.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_account3_web.json"))
TRACKING_FILE = Path(os.environ.get("YT_GULF_AR_TRACKING",
                                    "/opt/medmind/youtube_shorts_gulf_ar_uploaded.json"))

# slug → (display name EN, Arabic long name, description hashtags)
EXAMS = {
    "snle":   ("Saudi SNLE",    "هيئة التخصصات الصحية SNLE",
               "#SNLE #SCFHS #هيئة_التخصصات_الصحية #تمريض_السعودية #برومترك_السعودية #اسئلة_SNLE"),
    "dha":    ("DHA Dubai",     "هيئة الصحة دبي DHA",
               "#DHA #DHAExam #تمريض_دبي #برومترك_دبي #اسئلة_DHA #تمريض_الإمارات"),
    "haad":   ("DOH Abu Dhabi", "دائرة الصحة أبوظبي DOH",
               "#DOH #HAAD #HAADExam #تمريض_أبوظبي #برومترك_أبوظبي #اسئلة_HAAD"),
    "mohuae": ("MOH UAE",       "وزارة الصحة الإماراتية MOH",
               "#MOH #MOHUAE #تمريض_الإمارات #برومترك_الإمارات #اسئلة_MOH"),
    "qchp":   ("QCHP Qatar",    "قطر QCHP",
               "#QCHP #QCHPExam #تمريض_قطر #برومترك_قطر #اسئلة_QCHP"),
    "omsb":   ("OMSB Oman",     "سلطنة عُمان OMSB",
               "#OMSB #OMSBExam #تمريض_عمان #برومترك_عمان #اسئلة_OMSB"),
    "nhra":   ("NHRA Bahrain",  "البحرين NHRA",
               "#NHRA #NHRAExam #تمريض_البحرين #برومترك_البحرين #اسئلة_NHRA"),
    "moh_kw": ("Kuwait MOH",    "الكويت MOH",
               "#تمريض_الكويت #برومترك_الكويت #اسئلة_التمريض"),
}

# Short acronym for title — what nurses actually type in search
_EXAM_SHORT = {
    "snle": "SNLE", "dha": "DHA", "haad": "DOH/HAAD", "mohuae": "MOH UAE",
    "qchp": "QCHP", "omsb": "OMSB", "nhra": "NHRA", "moh_kw": "MOH",
}

# Per-exam YouTube API tags (prepended before base tags)
_EXAM_YT_TAGS: dict[str, list[str]] = {
    "snle":   ["snle exam", "scfhs nursing", "saudi nursing exam", "تمريض السعودية", "اسئلة SNLE"],
    "dha":    ["dha exam", "dha nursing exam", "dubai nursing", "تمريض دبي", "اسئلة DHA"],
    "haad":   ["haad exam", "doh nursing", "abu dhabi nursing", "تمريض أبوظبي", "اسئلة HAAD"],
    "mohuae": ["moh uae nursing", "uae nursing exam", "تمريض الإمارات", "اسئلة MOH"],
    "qchp":   ["qchp exam", "qatar nursing exam", "تمريض قطر", "اسئلة QCHP"],
    "omsb":   ["omsb exam", "oman nursing exam", "تمريض عمان", "اسئلة OMSB"],
    "nhra":   ["nhra exam", "bahrain nursing exam", "تمريض البحرين", "اسئلة NHRA"],
    "moh_kw": ["kuwait nursing exam", "تمريض الكويت", "اسئلة التمريض الكويت"],
}
_BASE_YT_TAGS = [
    "prometric nursing", "برومترك تمريض", "اسئلة تمريض",
    "شرح بالعربي", "gulf nursing exam", "تمريض الخليج", "medmind",
]

BASE_TAGS_AR = (
    "#برومترك #امتحان_التمريض #تمريض #ممرضة "
    "#شرح_بالعربي #اسئلة_تمريض #تمريض_الخليج #MedMindAI #Shorts"
)

# Arabic module name lookup — partial, case-insensitive
_AR_MODULE: dict[str, str] = {
    "pharmacology":    "الدوائيات",
    "cardiovascular":  "القلب والأوعية",
    "cardiac":         "أمراض القلب",
    "respiratory":     "الجهاز التنفسي",
    "endocrine":       "الغدد الصماء",
    "diabetes":        "السكري",
    "neurology":       "الجهاز العصبي",
    "renal":           "أمراض الكلى",
    "kidney":          "أمراض الكلى",
    "gastrointestinal":"الجهاز الهضمي",
    "pediatric":       "طب الأطفال",
    "obstetric":       "التوليد",
    "gynecol":         "أمراض النساء",
    "psychiatric":     "الطب النفسي",
    "mental":          "الصحة النفسية",
    "orthopedic":      "جراحة العظام",
    "hematology":      "أمراض الدم",
    "oncology":        "الأورام",
    "infection":       "الأمراض المعدية",
    "sepsis":          "الإنتان",
    "nutrition":       "التغذية",
    "fundamentals":    "أساسيات التمريض",
    "critical":        "العناية المركزة",
    "emergency":       "الطوارئ",
    "surgical":        "الجراحة",
    "dermatology":     "الجلدية",
}


def _module_ar(title: str) -> str:
    """Return Arabic module name if known; keep English if not (nurses search both)."""
    if not title:
        return "تمريض"
    tl = title.lower()
    for key, ar in _AR_MODULE.items():
        if key in tl:
            return ar
    return title

DEMO = [{
    "id": "demo-ar-1", "module_title": "Pharmacology", "correct": "B",
    "question": "A prescription reads potassium chloride 20 mmol IV. "
                "Which method of administration is unsafe?",
    "options": {"A": "Diluted in IV fluid via infusion pump", "B": "IV push over 1 minute",
                "C": "Infused through a central line per protocol",
                "D": "Infused with cardiac monitoring per protocol"},
    "explanation_ar": "لا يُعطى كلوريد البوتاسيوم أبداً بالحقن الوريدي المباشر لأنه قد يسبب "
                      "اضطراباً قاتلاً في نظم القلب. يجب تخفيفه دائماً وإعطاؤه بمضخة تسريب.",
}]


# ── Arabic text helpers ───────────────────────────────────────────────────────

def _ar_line(text: str) -> str:
    if RAQM:
        return text
    import arabic_reshaper
    from bidi.algorithm import get_display
    return get_display(arabic_reshaper.reshape(text))


def ar_lines(draw, text: str, font, max_w: int) -> list[str]:
    """Wrap Arabic in LOGICAL order first, then shape + reorder each line.
    (Shaping the whole paragraph first and wrapping afterwards — as the old AR Shorts
    do — reverses the order of lines on multi-line text.)"""
    measure = (lambda t: t) if RAQM else __import__("arabic_reshaper").reshape
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if tw(draw, measure(test), font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return [_ar_line(l) for l in lines]


def draw_rtl(draw, lines: list[str], right_x: int, y: int, font, fill, step: int) -> int:
    for line in lines:
        draw.text((right_x - tw(draw, line, font), y), line, font=font, fill=fill)
        y += step
    return y


def ar_center(draw, y: int, text: str, font, fill):
    t = _ar_line(text)
    draw.text(((W - tw(draw, t, font)) // 2, y), t, font=font, fill=fill)


# ── Frames (9:16) ─────────────────────────────────────────────────────────────

def f_hook(exam: str, module: str | None) -> Image.Image:
    en, ar, _ = EXAMS[exam]
    img, d = _base_canvas(en)
    ar_center(d, 650, "هل تستطيع حل", fb(84), TEXT_W)
    ar_center(d, 760, "سؤال امتحان التمريض؟", fb(76), TEXT_W)
    t = en + " Nursing Exam"
    d.text(((W - tw(d, t, fb(46))) // 2, 900), t, font=fb(46), fill=ACCENT)
    ar_center(d, 990, "السؤال بالإنجليزية • الشرح بالعربية", fr(40), AMBER)
    if module:
        d.text(((W - tw(d, module[:40], fr(34))) // 2, 1070), module[:40], font=fr(34), fill=TEXT_M)
    return img


def f_question(q: dict, exam: str) -> Image.Image:
    img, d = _base_canvas(EXAMS[exam][0])
    PAD = 40
    size = 40 if len(wrap(d, q["question"], fb(40), W - PAD * 2 - 40)) <= 8 else 32
    lines = wrap(d, q["question"], fb(size), W - PAD * 2 - 40)[:11]
    card_h = 60 + len(lines) * (size + 14)
    # centre the whole block (question + 4 options) vertically
    y0 = max(90, (H - (card_h + 30 + 4 * 190)) // 2 - 80)
    d.rounded_rectangle([PAD, y0, W - PAD, y0 + card_h], radius=20, fill=BG_CARD)
    y = y0 + 30
    for line in lines:
        d.text((PAD + 20, y), line, font=fb(size), fill=TEXT_W)
        y += size + 14
    _opts(d, q["options"], None, y0 + card_h + 30)
    return img


def _opts(d, options: dict, correct: str | None, y0: int, h: int = 170, gap: int = 20):
    colors = {"A": (99, 179, 237), "B": (167, 139, 250), "C": (52, 211, 153), "D": (251, 191, 36)}
    PAD = 40
    for i, L in enumerate("ABCD"):
        text = options.get(L, "")
        if not text:
            continue
        y = y0 + i * (h + gap)
        if correct is None:
            fill, outline, col, tcol = BG_CARD, None, colors[L], TEXT_W
        elif L == correct:
            fill, outline, col, tcol = (20, 60, 40), GREEN, GREEN, TEXT_W
        else:
            fill, outline, col, tcol = (25, 30, 42), (50, 60, 75), (70, 80, 95), TEXT_M
        d.rounded_rectangle([PAD, y, W - PAD, y + h], radius=16, fill=fill,
                            outline=outline, width=3 if outline else 0)
        cx, cy = PAD + 46, y + h // 2
        d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], fill=col)
        d.text((cx - tw(d, L, fb(34)) // 2, cy - 21), L, font=fb(34), fill=(10, 14, 20))
        ol = wrap(d, text, fr(30), W - PAD * 2 - 120)[:3]
        ty = y + (h - len(ol) * 38) // 2
        for line in ol:
            d.text((PAD + 96, ty), line, font=fr(30), fill=tcol)
            ty += 38


def f_think(base: Image.Image, secs: int) -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W // 2 - 260, 1460, W // 2 + 260, 1600], radius=30,
                        fill=PINK if secs <= 2 else AMBER)
    t = _ar_line(f"فكّر... {secs}")
    d.text(((W - tw(d, t, fb(60))) // 2, 1492), t, font=fb(60), fill=(10, 14, 20))
    return img


def f_answer(q: dict, exam: str) -> Image.Image:
    img, d = _base_canvas(EXAMS[exam][0])
    d.rounded_rectangle([30, 80, W - 30, 190], radius=18, fill=GREEN)
    head = _ar_line(f"الإجابة الصحيحة: {q['correct']}")
    d.text(((W - tw(d, head, fb(52))) // 2, 104), head, font=fb(52), fill=(10, 14, 20))
    _opts(d, q["options"], q["correct"], 220, h=130, gap=14)
    # Arabic explanation, right-aligned
    y0 = 220 + 4 * 144 + 20
    lines = ar_lines(d, q["explanation_ar"], fr(38), W - 140)[:10]
    box_h = 90 + len(lines) * 54
    d.rounded_rectangle([30, y0, W - 30, y0 + box_h], radius=16,
                        fill=(40, 32, 10), outline=AMBER, width=3)
    t = _ar_line("الشرح")
    d.text((W - 70 - tw(d, t, fb(40)), y0 + 18), t, font=fb(40), fill=AMBER)
    draw_rtl(d, lines, W - 70, y0 + 80, fr(38), (251, 229, 163), 54)
    return img


def f_cta(exam: str) -> Image.Image:
    img, d = _base_canvas()
    ar_center(d, 680, "تدرّب على أسئلة", fb(76), TEXT_W)
    ar_center(d, 780, "امتحان التمريض مجاناً", fb(76), PINK)
    ar_center(d, 900, EXAMS[exam][1], fb(48), ACCENT)
    url = "medmind.pro/ar/gulf"
    d.text(((W - tw(d, url, fb(52))) // 2, 1020), url, font=fb(52), fill=ACCENT)
    ar_center(d, 1140, "اشترك لسؤال جديد كل يوم", fr(42), TEXT_M)
    return img


# ── TTS (voice per call: EN for the question, AR for the explanation) ─────────

async def say(text: str, path: str, voice: str, enabled: bool, rate: str = EN_RATE) -> float:
    import subprocess
    if enabled:
        import edge_tts
        await edge_tts.Communicate(text[:1500], voice, rate=rate).save(path)
        dur = _ffprobe_dur(path)
        if dur > 0:
            return dur
    est = max(3.0, len(text.split()) / 140 * 60)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", f"{est:.2f}", "-q:a", "9", path], check=True)
    return est


async def build(q: dict, exam: str, out: str, use_tts: bool, bg: str | None = None):
    _nts.CANVAS_TRANSPARENT = bg is not None
    try:
        o = q["options"]
        spoken_q = q["question"] + " " + " ".join(f"{L}: {o[L]}." for L in "ABCD" if o.get(L))
        spoken_ans = f"The correct answer is {q['correct']}: {o.get(q['correct'], '')}."
        with tempfile.TemporaryDirectory() as tmp:
            p = lambda n: f"{tmp}/{n}"  # noqa: E731
            qd = await say(spoken_q,           p("q.mp3"), EN_VOICE, use_tts, EN_RATE)
            ad = await say(spoken_ans,         p("a.mp3"), EN_VOICE, use_tts, EN_RATE)
            ed = await say(q["explanation_ar"], p("e.mp3"), AR_VOICE, use_tts, AR_RATE)
            f_hook(exam, q.get("module_title")).save(p("hook.png"))
            base = f_question(q, exam); base.save(p("q.png"))
            f_answer(q, exam).save(p("ans.png"))
            f_cta(exam).save(p("cta.png"))
            parts = [(p("hook.png"), 2.5, None), (p("q.png"), qd + 0.5, p("q.mp3"))]
            for s in range(THINK_SECS, 0, -1):
                f_think(base, s).save(p(f"t{s}.png"))
                parts.append((p(f"t{s}.png"), 1.0, None))
            parts += [(p("ans.png"), ad + 0.3, p("a.mp3")),
                      (p("ans.png"), ed + 1.2, p("e.mp3")),
                      (p("cta.png"), 3.5, None)]
            _encode(parts, out, bg=bg)
    finally:
        _nts.CANVAS_TRANSPARENT = False


# ── Data ──────────────────────────────────────────────────────────────────────

def _tracking() -> dict:
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except Exception:
            pass
    return {"uploaded": [], "details": {}}


def fetch(exam: str, limit: int) -> list[dict]:
    done = _tracking()["uploaded"]
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.id::text AS id, q.question, q.options, q.correct, q.difficulty,
                   t.key_takeaway AS explanation_ar, m.title AS module_title
            FROM mcq_questions q
            JOIN nclex_shorts_translations t
                 ON t.question_id = q.id::text AND t.lang = 'ar' AND t.status = 'done'
            LEFT JOIN modules m ON m.id = q.module_id
            WHERE q.question_type = 'mcq'
              AND q.exam_slugs @> %s::jsonb
              AND q.question ~ '^[A-Za-z]'
              AND t.key_takeaway IS NOT NULL
              AND NOT (q.id::text = ANY(%s))
            ORDER BY q.created_at ASC
            LIMIT %s
            """,
            (json.dumps([exam]), done, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if not isinstance(r["options"], dict):
            r["options"] = json.loads(r["options"])
    return rows


# ── Metadata ──────────────────────────────────────────────────────────────────

def meta(q: dict, exam: str) -> dict:
    en, ar_name, hashtags = EXAMS[exam]
    short       = _EXAM_SHORT[exam]
    topic_en    = (q.get("module_title") or "Nursing")[:30]
    topic_ar    = _module_ar(topic_en)
    year        = datetime.date.today().year
    o           = q["options"]
    opts        = "\n".join(f"{L}) {o[L]}" for L in "ABCD" if o.get(L))
    correct_txt = o.get(q["correct"], "")

    # Title: exam acronym + year + Arabic module name — matches actual search queries
    title_ar = f"🩺 امتحان {short} تمريض {year} | {topic_ar} | برومترك شرح #Shorts"[:100]
    title_en = f"🩺 {en} Nursing Exam {year} | {topic_en} | Prometric Practice #Shorts"[:100]

    desc_ar = (
        f"سؤال برومترك تمريض {ar_name} {year} — السؤال بالإنجليزية كما في الامتحان، والشرح بالعربية.\n"
        f"✍️ اكتب إجابتك في التعليقات! هل أجبت صح؟ 👇\n\n"
        f"📚 الموضوع: {topic_ar}\n\n"
        f"❓ {q['question']}\n{opts}\n\n"
        f"✅ الإجابة الصحيحة: {q['correct']}) {correct_txt}\n"
        f"💡 الشرح: {q['explanation_ar']}\n\n"
        f"📝 تدرّب مجاناً على أسئلة {ar_name}:\n🔗 https://medmind.pro/ar/gulf\n"
        f"🌐 English: https://medmind.pro/exams/{exam}\n\n"
        f"سؤال تدريبي مبني على مخطط الامتحان الرسمي — ليس من الأسئلة الفعلية للامتحان. "
        f"للتعليم والتحضير فقط، وليس نصيحة طبية. الصوت: ذكاء اصطناعي.\n"
        f"⚠️ هل أنت متخصص صحي ووجدت خطأً؟ أخبرنا في التعليقات أو على medmind.pro — الدقة أولويتنا.\n\n"
        f"{hashtags} {BASE_TAGS_AR}"
    )
    desc_en = (
        f"{en} nursing exam practice (Prometric format, {year}). "
        f"Question in English as in the real exam — explanation in Arabic.\n\n"
        f"📚 Topic: {topic_en}\n\n"
        f"❓ {q['question']}\n{opts}\n\n"
        f"✅ Answer: {q['correct']}) {correct_txt}\n\n"
        f"📝 Free {en} practice: https://medmind.pro/exams/{exam}\n\n"
        f"Original practice question based on the official blueprint — not an actual exam item. "
        f"Education only, not medical advice. AI-generated voice.\n"
        f"⚠️ Healthcare professional? Found an error? Please comment below or report at medmind.pro — accuracy is our priority."
    )

    tags = (_EXAM_YT_TAGS.get(exam, []) + _BASE_YT_TAGS + [topic_en.lower()])[:20]

    return {
        "title":         title_ar,
        "description":   desc_ar,
        "localizations": {"en": {"title": title_en, "description": desc_en}},
        "tags":          tags,
    }


def upload(mp4: str, m: dict) -> str | None:
    import google.oauth2.credentials
    import googleapiclient.discovery
    import googleapiclient.http
    data = json.loads(TOKEN_FILE.read_text())
    cid, csec = data.get("client_id"), data.get("client_secret")
    if (not cid or not csec) and SECRET_FILE.exists():
        raw = json.loads(SECRET_FILE.read_text()); sec = raw.get("web") or raw.get("installed") or {}
        cid, csec = cid or sec.get("client_id"), csec or sec.get("client_secret")
    creds = google.oauth2.credentials.Credentials(
        token=data.get("access_token") or data.get("token"), refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=cid, client_secret=csec)
    yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    clean = lambda s: s.replace("<", "＜").replace(">", "＞")  # noqa: E731  (API rejects < >)
    body = {
        "snippet": {"title": clean(m["title"]), "description": clean(m["description"])[:4900],
                    "tags": m["tags"], "categoryId": "27",
                    "defaultLanguage": "ar", "defaultAudioLanguage": "ar"},
        "localizations": {k: {"title": clean(v["title"]), "description": clean(v["description"])[:4900]}
                          for k, v in m["localizations"].items()},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status,localizations", body=body,
                             media_body=googleapiclient.http.MediaFileUpload(
                                 mp4, chunksize=-1, resumable=True, mimetype="video/mp4"))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    if creds.token and creds.token != (data.get("access_token") or data.get("token")):
        data["access_token"], data["expires_at"] = creds.token, time.time() + 3600
        TOKEN_FILE.write_text(json.dumps(data, indent=2))
    return resp.get("id")


# ── CLI ───────────────────────────────────────────────────────────────────────

async def main():
    ap = argparse.ArgumentParser(description="Bilingual (EN question / AR explanation) Gulf Shorts")
    ap.add_argument("--exam", choices=sorted(EXAMS), default="dha")
    ap.add_argument("--limit", type=int, default=DAILY_LIMIT)
    ap.add_argument("--dry-run", action="store_true", help="render + print metadata, no upload")
    ap.add_argument("--demo", action="store_true", help="built-in question, no DB")
    ap.add_argument("--no-tts", action="store_true", help="silent audio (layout test)")
    ap.add_argument("--out", default=None, help="output path (single video)")
    ap.add_argument("--bg", default="auto", metavar="THEME|auto|none",
                    help="animated background: auto (deterministic per question), a theme name, or none")
    a = ap.parse_args()

    bg_fn = None
    if a.bg != "none":
        from video_backgrounds import bg_loop, pick_theme
        bg_fn = lambda qid: bg_loop(a.bg if a.bg != "auto" else pick_theme(qid), W, H)  # noqa: E731

    qs = DEMO if a.demo else fetch(a.exam, a.limit)
    if not qs:
        print(f"⚠ No questions for exam={a.exam} with a finished Arabic translation "
              f"(nclex_shorts_translations lang='ar'). Run translate_nclex_shorts.py or pick another exam.")
        sys.exit(2)

    for i, q in enumerate(qs, 1):
        name = f"gulf_{a.exam}_{q['id'][:8]}_en-ar.mp4"
        out = a.out or str(Path(tempfile.gettempdir()) / name)
        bg = bg_fn(q["id"]) if bg_fn else None
        print(f"\n[{i}/{len(qs)}] {q['question'][:70]}…  →  {name}")
        await build(q, a.exam, out, use_tts=not a.no_tts, bg=bg)
        m = meta(q, a.exam)
        print(f"  Title (ar): {m['title']}\n  Title (en): {m['localizations']['en']['title']}"
              f"\n  Length: {_ffprobe_dur(out):.0f}s")
        if a.dry_run or a.demo:
            Path(out).with_suffix(".txt").write_text(
                f"{m['title']}\n\n{m['description']}\n\n--- en ---\n"
                f"{m['localizations']['en']['title']}\n\n{m['localizations']['en']['description']}\n")
            continue
        vid = upload(out, m)
        if not vid:
            print("  ✗ upload failed"); continue
        print(f"  ✅ https://youtu.be/{vid}")
        tr = _tracking()
        tr["uploaded"].append(q["id"]); tr.setdefault("details", {})[q["id"]] = {"yt_id": vid, "exam": a.exam}
        TRACKING_FILE.write_text(json.dumps(tr, indent=2))
        os.remove(out)
        if i < len(qs):
            time.sleep(WAIT_BETWEEN)


if __name__ == "__main__":
    asyncio.run(main())
