#!/usr/bin/env python3
"""
MedMind AI — "NCLEX en español": bilingual Shorts for the Spanish channel
Question + options in ENGLISH (the NCLEX is sat in English), explanation in SPANISH.

Audience: nurses from Latin America, Spain and Puerto Rico preparing for the US NCLEX-RN.
Funnel: channel → medmind.pro/es/nclex (Spanish landing) → NCLEX question bank / Pro plan.

Data:
  question / options / correct  ← mcq_questions (original English, NCLEX-tagged)
  Spanish explanation           ← nclex_shorts_translations.key_takeaway (lang='es')

Video (1080×1920, ~40-55 s), same pipeline + animated backgrounds as the AR Gulf Shorts:
  [ES hook] → [EN question, EN voice] → ["Piensa… 5"] → [answer, ES explanation, ES voice] → [ES CTA]

Metadata: Spanish title with English search terms ("NCLEX", topic), Spanish-first
description with the English question, English localization, defaultLanguage=es.

Tracking: /opt/medmind/youtube_shorts_nclex_es_bilingual_uploaded.json (separate from the
old fully-Spanish Shorts, so a question can come back in the new format).

Usage:
    python3 youtube_shorts_nclex_es_bilingual.py --dry-run
    python3 youtube_shorts_nclex_es_bilingual.py --limit 2
    python3 youtube_shorts_nclex_es_bilingual.py --demo --no-tts --out /tmp/es_demo.mp4
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

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import nclex_to_shorts  # noqa: E402
from nclex_to_shorts import (  # noqa: E402
    W, H, BG_CARD, ACCENT, PINK, GREEN, AMBER, TEXT_W, TEXT_M,
    fb, fr, tw, wrap, _base_canvas, _db_conn,
)
from nclex_practice_session import _encode, _ffprobe_dur  # noqa: E402
from youtube_shorts_gulf_ar_daily import _opts, say  # noqa: E402  shared option cards + TTS

DAILY_LIMIT  = 2
WAIT_BETWEEN = 45
EN_VOICE     = os.environ.get("TTS_VOICE_EN", "en-US-EmmaMultilingualNeural")
ES_VOICE     = os.environ.get("TTS_VOICE_ES", "es-MX-DaliaNeural")   # Latin American Spanish
EN_RATE, ES_RATE = "-5%", "-5%"
THINK_SECS   = 5
BADGE        = "NCLEX-RN"
SITE_ES      = "https://medmind.pro/es/nclex"
SITE_EN      = "https://medmind.pro/nclex"

TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token_account2.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_account2_web.json"))
TRACKING_FILE = Path(os.environ.get("YT_ES_BILINGUAL_TRACKING",
                                    "/opt/medmind/youtube_shorts_nclex_es_bilingual_uploaded.json"))

# English module / NCLEX category → Spanish label for titles (fallback: English as is)
TOPIC_ES = {
    # NCLEX client needs categories (full names — matched by substring)
    "pharmacological and parenteral": "Farmacología",
    "basic care and comfort":         "Cuidados básicos",
    "reduction of risk potential":    "Reducción de riesgos",
    "physiological adaptation":       "Adaptación fisiológica",
    "safety and infection control":   "Seguridad e infecciones",
    "health promotion and maintenance": "Promoción de la salud",
    "psychosocial integrity":         "Integridad psicosocial",
    "management of care":             "Gestión del cuidado",
    # Module / specialty keywords (order: longer keys first for substring matching)
    "pharmacology":    "Farmacología",
    "cardiovascular":  "Cardiovascular",
    "cardiac":         "Cardiología",
    "endocrine":       "Endocrinología",
    "diabetes":        "Diabetes",
    "respiratory":     "Respiratorio",
    "pediatric":       "Pediatría",
    "maternity":       "Materno-infantil",
    "obstetric":       "Obstetricia",
    "gynecol":         "Ginecología",
    "mental health":   "Salud mental",
    "psychiatric":     "Salud mental",
    "neurology":       "Neurología",
    "renal":           "Renal",
    "kidney":          "Renal",
    "gastrointestinal":"Gastrointestinal",
    "infection":       "Infecciones",
    "sepsis":          "Sepsis",
    "hematology":      "Hematología",
    "oncology":        "Oncología",
    "orthopedic":      "Ortopedia",
    "dermatology":     "Dermatología",
    "nutrition":       "Nutrición",
    "fundamentals":    "Fundamentos",
    "emergency":       "Urgencias",
    "critical care":   "Cuidados críticos",
    "surgical":        "Quirúrgico",
    "safety":          "Seguridad del paciente",
    "management":      "Gestión del cuidado",
}

DEMO = [{
    "id": "demo-es-1", "module_title": "Pharmacology", "correct": "C",
    "question": "Before giving digoxin to an adult client, the nurse counts an apical pulse of 54 "
                "beats per minute. What should the nurse do?",
    "options": {"A": "Give the dose and document", "B": "Give half the dose",
                "C": "Hold the dose and notify the prescriber", "D": "Give the dose with food"},
    "explanation_es": "Se debe suspender la digoxina si el pulso apical del adulto es menor de 60 "
                      "por minuto e informar al médico. Vigila también náuseas y alteraciones visuales.",
}]


def topic_es(q: dict) -> str:
    raw = (q.get("nclex_category") or q.get("module_title") or "").strip()
    low = raw.lower()
    for k, v in TOPIC_ES.items():
        if k in low:
            return v
    return raw[:30] or "Enfermería"


# ── Frames (9:16) ─────────────────────────────────────────────────────────────

def _center(d, y, text, font, fill):
    d.text(((W - tw(d, text, font)) // 2, y), text, font=font, fill=fill)


def f_hook(q: dict) -> Image.Image:
    img, d = _base_canvas(BADGE)
    _center(d, 640, "¿Puedes responder", fb(80), TEXT_W)
    _center(d, 740, "esta pregunta?", fb(80), TEXT_W)
    _center(d, 880, "NCLEX-RN Practice Question", fb(46), ACCENT)
    _center(d, 960, "Pregunta en inglés • Explicación en español", fr(38), AMBER)
    _center(d, 1040, topic_es(q), fr(36), TEXT_M)
    return img


def f_question(q: dict) -> Image.Image:
    img, d = _base_canvas(BADGE)
    PAD = 40
    size = 40 if len(wrap(d, q["question"], fb(40), W - PAD * 2 - 40)) <= 8 else 32
    lines = wrap(d, q["question"], fb(size), W - PAD * 2 - 40)[:11]
    card_h = 60 + len(lines) * (size + 14)
    y0 = max(90, (H - (card_h + 30 + 4 * 190)) // 2 - 80)
    d.rounded_rectangle([PAD, y0, W - PAD, y0 + card_h], radius=20, fill=BG_CARD)
    y = y0 + 30
    for line in lines:
        d.text((PAD + 20, y), line, font=fb(size), fill=TEXT_W)
        y += size + 14
    _opts(d, q["options"], None, y0 + card_h + 30)
    return img


def f_think(base: Image.Image, secs: int) -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([W // 2 - 260, 1460, W // 2 + 260, 1600], radius=30,
                        fill=PINK if secs <= 2 else AMBER)
    _center(d, 1492, f"Piensa... {secs}", fb(60), (10, 14, 20))
    return img


def f_answer(q: dict) -> Image.Image:
    img, d = _base_canvas(BADGE)
    d.rounded_rectangle([30, 80, W - 30, 190], radius=18, fill=GREEN)
    _center(d, 104, f"Respuesta correcta: {q['correct']}", fb(52), (10, 14, 20))
    _opts(d, q["options"], q["correct"], 220, h=130, gap=14)
    y0 = 220 + 4 * 144 + 20
    lines = wrap(d, q["explanation_es"], fr(38), W - 140)[:10]
    box_h = 90 + len(lines) * 54
    d.rounded_rectangle([30, y0, W - 30, y0 + box_h], radius=16,
                        fill=(40, 32, 10), outline=AMBER, width=3)
    d.text((70, y0 + 18), "Explicación", font=fb(40), fill=AMBER)
    y = y0 + 80
    for line in lines:
        d.text((70, y), line, font=fr(38), fill=(251, 229, 163))
        y += 54
    return img


def f_cta() -> Image.Image:
    img, d = _base_canvas()
    _center(d, 680, "Practica preguntas", fb(76), TEXT_W)
    _center(d, 780, "NCLEX gratis", fb(76), PINK)
    _center(d, 900, "con explicaciones en español", fb(44), ACCENT)
    _center(d, 1020, "medmind.pro/es/nclex", fb(52), ACCENT)
    _center(d, 1140, "Suscríbete: una pregunta nueva cada día", fr(40), TEXT_M)
    return img


async def build(q: dict, out: str, use_tts: bool, bg: str | None = None):
    nclex_to_shorts.CANVAS_TRANSPARENT = bg is not None
    try:
        o = q["options"]
        spoken_q = q["question"] + " " + " ".join(f"{L}: {o[L]}." for L in "ABCD" if o.get(L))
        spoken_ans = f"The correct answer is {q['correct']}: {o.get(q['correct'], '')}."
        with tempfile.TemporaryDirectory() as tmp:
            p = lambda n: f"{tmp}/{n}"  # noqa: E731
            qd = await say(spoken_q, p("q.mp3"), EN_VOICE, use_tts, EN_RATE)
            ad = await say(spoken_ans, p("a.mp3"), EN_VOICE, use_tts, EN_RATE)
            ed = await say(q["explanation_es"], p("e.mp3"), ES_VOICE, use_tts, ES_RATE)
            f_hook(q).save(p("hook.png"))
            base = f_question(q); base.save(p("q.png"))
            f_answer(q).save(p("ans.png"))
            f_cta().save(p("cta.png"))
            parts = [(p("hook.png"), 2.5, None), (p("q.png"), qd + 0.5, p("q.mp3"))]
            for s in range(THINK_SECS, 0, -1):
                f_think(base, s).save(p(f"t{s}.png"))
                parts.append((p(f"t{s}.png"), 1.0, None))
            parts += [(p("ans.png"), ad + 0.3, p("a.mp3")),
                      (p("ans.png"), ed + 1.2, p("e.mp3")),
                      (p("cta.png"), 3.5, None)]
            _encode(parts, out, bg=bg)
    finally:
        nclex_to_shorts.CANVAS_TRANSPARENT = False


# ── Data ──────────────────────────────────────────────────────────────────────

def _tracking() -> dict:
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except Exception:
            pass
    return {"uploaded": [], "details": {}}


def fetch(limit: int) -> list[dict]:
    """NCLEX-tagged English questions that have a finished Spanish translation."""
    done = _tracking()["uploaded"]
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.id::text AS id, q.question, q.options, q.correct, q.difficulty,
                   q.nclex_client_needs AS nclex_category,
                   t.key_takeaway AS explanation_es, m.title AS module_title
            FROM mcq_questions q
            JOIN nclex_shorts_translations t
                 ON t.question_id = q.id::text AND t.lang = 'es' AND t.status = 'done'
            LEFT JOIN modules m ON m.id = q.module_id
            WHERE q.question_type = 'mcq'
              AND (q.nclex_client_needs IS NOT NULL
                   OR q.exam_slugs @> '["nclex_rn"]'::jsonb
                   OR m.code LIKE 'NURSE-%%')
              AND q.question ~ '^[A-Za-z]'
              AND t.key_takeaway IS NOT NULL
              AND NOT (q.id::text = ANY(%s))
            ORDER BY q.created_at ASC
            LIMIT %s
            """,
            (done, limit),
        )
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if not isinstance(r["options"], dict):
            r["options"] = json.loads(r["options"])
        if isinstance(r.get("nclex_category"), (list, dict)):
            v = r["nclex_category"]
            r["nclex_category"] = (v[0] if isinstance(v, list) and v else
                                   next(iter(v.values()), "") if isinstance(v, dict) else "")
    return rows


# ── Metadata ──────────────────────────────────────────────────────────────────

_HASHTAGS_ES = (
    "#NCLEX #NCLEXenEspañol #NCLEXRN #Enfermería #Enfermera "
    "#EnfermeríaUSA #EnfermeríaHispana #ExamenNCLEX #PrepararNCLEX "
    "#EnfermeraLatina #MedMindAI #Shorts"
)

_BASE_TAGS_ES = [
    "nclex", "nclex rn", "nclex en español", "nclex-rn en español",
    "preguntas nclex", "examen nclex", "preparación nclex", "nclex prep",
    "enfermería", "enfermera", "enfermería usa", "enfermería hispana",
    "enfermera latina", "nclex study", "medmind",
]


def meta(q: dict) -> dict:
    year = datetime.date.today().year
    t_es = topic_es(q)
    t_en = (q.get("nclex_category") or q.get("module_title") or "Nursing")[:30]
    o = q["options"]
    opts = "\n".join(f"{L}) {o[L]}" for L in "ABCD" if o.get(L))
    correct_txt = o.get(q["correct"], "")

    # Title: NCLEX-RN keyword first — matches how nurses actually search
    title_es = f"🩺 NCLEX-RN en español {year} | {t_es} | #Enfermería #Shorts"[:100]
    title_en = f"🩺 NCLEX-RN Practice {year} | {t_en} | Spanish explanation #Shorts"[:100]

    desc_es = (
        f"Pregunta NCLEX-RN {year} — {t_es} | ¡Escribe tu respuesta antes de ver la solución! 👇\n"
        f"Pregunta en inglés (igual que en el examen real) + explicación en español.\n\n"
        f"❓ {q['question'][:200]}\n{opts}\n\n"
        f"✅ Respuesta correcta: {q['correct']}) {correct_txt}\n"
        f"💡 {q['explanation_es']}\n\n"
        f"📝 Practica más de 1,000 preguntas NCLEX gratis con explicaciones en español:\n"
        f"🔗 {SITE_ES}\n"
        f"🔗 English: {SITE_EN}\n\n"
        f"Pregunta original basada en el plan oficial del NCLEX-RN; no es una pregunta real del examen. "
        f"Solo con fines educativos, no es consejo médico. Voz generada por IA.\n"
        f"⚠️ ¿Eres profesional de la salud y encontraste un error? Coméntalo abajo o repórtalo en medmind.pro — la precisión es nuestra prioridad.\n\n"
        f"{_HASHTAGS_ES}"
    )
    desc_en = (
        f"NCLEX-RN practice ({year}) — {t_en}. English question with a Spanish explanation.\n\n"
        f"❓ {q['question'][:200]}\n{opts}\n\n"
        f"✅ Answer: {q['correct']}) {correct_txt}\n\n"
        f"📝 Free NCLEX practice: {SITE_EN}\n\n"
        f"Original practice question based on the NCLEX test plan — not an actual exam item. "
        f"Education only, not medical advice. AI-generated voice.\n"
        f"⚠️ Healthcare professional? Found an error? Please comment below or report at medmind.pro — accuracy is our priority."
    )
    tags = (_BASE_TAGS_ES + [f"nclex {year}", t_es.lower()])[:20]
    return {"title": title_es, "description": desc_es,
            "localizations": {"en": {"title": title_en, "description": desc_en}},
            "tags": tags}


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
    clean = lambda s: s.replace("<", "＜").replace(">", "＞")  # noqa: E731
    body = {
        "snippet": {"title": clean(m["title"]), "description": clean(m["description"])[:4900],
                    "tags": m["tags"], "categoryId": "27",
                    "defaultLanguage": "es", "defaultAudioLanguage": "es"},
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
    ap = argparse.ArgumentParser(description="NCLEX en español — EN question / ES explanation Shorts")
    ap.add_argument("--limit", type=int, default=DAILY_LIMIT)
    ap.add_argument("--dry-run", action="store_true", help="render + write metadata, no upload")
    ap.add_argument("--demo", action="store_true", help="built-in question, no DB")
    ap.add_argument("--no-tts", action="store_true", help="silent audio (layout test)")
    ap.add_argument("--out", default=None, help="output path (single video)")
    ap.add_argument("--bg", default="auto",
                    help="animated background: aurora|ecg|molecules|cells|auto (per question)|none")
    a = ap.parse_args()

    qs = DEMO if a.demo else fetch(a.limit)
    if not qs:
        print("⚠ No NCLEX questions with a finished Spanish translation "
              "(nclex_shorts_translations lang='es'). Run translate_nclex_shorts.py --lang es.")
        sys.exit(2)

    for i, q in enumerate(qs, 1):
        name = f"nclex_{q['id'][:8]}_en-es.mp4"
        out = a.out or str(Path(tempfile.gettempdir()) / name)
        print(f"\n[{i}/{len(qs)}] {q['question'][:70]}…  →  {name}")
        bg = None
        if a.bg != "none":
            from video_backgrounds import bg_loop, pick_theme, THEMES
            theme = a.bg if a.bg in THEMES else pick_theme(q["id"])
            bg = bg_loop(theme, W, H)
            print(f"  🎨 background: {theme}")
        await build(q, out, use_tts=not a.no_tts, bg=bg)
        m = meta(q)
        print(f"  Title (es): {m['title']}\n  Title (en): {m['localizations']['en']['title']}"
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
        tr["uploaded"].append(q["id"]); tr.setdefault("details", {})[q["id"]] = {"yt_id": vid}
        TRACKING_FILE.write_text(json.dumps(tr, indent=2))
        os.remove(out)
        if i < len(qs):
            time.sleep(WAIT_BETWEEN)


if __name__ == "__main__":
    asyncio.run(main())
