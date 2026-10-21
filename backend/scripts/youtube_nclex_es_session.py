#!/usr/bin/env python3
"""
MedMind AI — NCLEX en español: bilingual practice session (16:9, ~13 min)

EN question + options narrated by EmmaNeural (as in the real exam),
ES explanation narrated by es-MX-DaliaNeural.
Audience: Latin American / Spanish-speaking nurses preparing for NCLEX-RN.
Funnel: video → medmind.pro/es/nclex

Data:
  question / options / correct  ← mcq_questions (NCLEX-tagged)
  explanation_es                ← nclex_shorts_translations (lang='es', status='done')

Format (16:9, DAILY_COUNT questions per session):
  [Intro ES] → for each question:
    [EN question + options, EN voice] → [Countdown 8s]
    → [Answer: EN letter+text, then ES explanation, ES voice]
  → [Outro ES / CTA]

Chapters in description let viewers jump per question.

Tracking:  /opt/medmind/youtube_nclex_es_sessions.json
Token:     youtube_token_account2.json (ES channel, account2)
Cron:      0 14 * * *  (14:00 UTC, after Shorts at 12:10)

Usage:
    python3 youtube_nclex_es_session.py --dry-run
    python3 youtube_nclex_es_session.py --public
    python3 youtube_nclex_es_session.py --demo --no-tts --out /tmp/demo_es.mp4
    python3 youtube_nclex_es_session.py --count 10 --topic pharmacology --public
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import nclex_practice_session as _ps                        # noqa: E402  BG_PATH + _card()
from nclex_practice_session import (                        # noqa: E402
    W, H, FPS, BG_LOOP_SECS, THINK_SECS,
    ACCENT, PINK, GREEN, AMBER, TEXT_W, TEXT_M, BG_DARK,
    _encode, _ffprobe_dur, _fmt_ts,
    _canvas, _centered, _options, frame_countdown,
)
from nclex_to_shorts import fb, fr, tw, wrap, _db_conn, _emt  # noqa: E402
from youtube_shorts_gulf_ar_daily import say                 # noqa: E402  bilingual TTS
from youtube_shorts_nclex_es_bilingual import TOPIC_ES, topic_es  # noqa: E402

DAILY_COUNT  = 15
EN_VOICE     = os.environ.get("TTS_VOICE_EN", "en-US-EmmaMultilingualNeural")
ES_VOICE     = os.environ.get("TTS_VOICE_ES", "es-MX-DaliaNeural")
EN_RATE, ES_RATE = "-5%", "-5%"

TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token_account2.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_account2_web.json"))
TRACKING_FILE = Path(os.environ.get("YT_ES_SESSION_TRACKING",
                                    "/opt/medmind/youtube_nclex_es_sessions.json"))

DEMO_QUESTIONS = [
    {"id": "demo-es-s1", "module_title": "Pharmacology", "correct": "C",
     "nclex_category": None,
     "question": "Before giving digoxin to an adult client, the nurse counts an apical pulse of "
                 "54 bpm. What should the nurse do?",
     "options": {"A": "Give the dose and document", "B": "Give half the dose",
                 "C": "Hold the dose and notify the prescriber", "D": "Give the dose with food"},
     "explanation_es": "Se debe suspender la digoxina si el pulso apical del adulto es menor de "
                       "60 por minuto e informar al médico. Vigila también náuseas y alteraciones visuales."},
    {"id": "demo-es-s2", "module_title": "Cardiovascular", "correct": "A",
     "nclex_category": None,
     "question": "A client is prescribed 40 mEq potassium chloride IV. Which action is safest?",
     "options": {"A": "Dilute in 100 mL NS and infuse via pump over 1 hour",
                 "B": "Give by IV push over 5 minutes",
                 "C": "Mix with D5W at 200 mEq/hour",
                 "D": "Administer undiluted via peripheral IV"},
     "explanation_es": "El cloruro de potasio IV siempre debe diluirse e infundirse lentamente "
                       "con bomba. Nunca se administra en bolo directo porque puede causar arritmias fatales."},
    {"id": "demo-es-s3", "module_title": "Endocrine", "correct": "B",
     "nclex_category": None,
     "question": "A conscious type 1 diabetic client has a capillary glucose of 3.1 mmol/L "
                 "(56 mg/dL) and is sweaty. What is the nurse's first action?",
     "options": {"A": "Administer the scheduled insulin",
                 "B": "Give 15 g of fast-acting oral carbohydrate",
                 "C": "Start an IV and give 50% dextrose",
                 "D": "Recheck glucose in 30 minutes without treatment"},
     "explanation_es": "En hipoglucemia leve en paciente consciente, la primera acción es "
                       "administrar 15 g de carbohidratos de acción rápida por vía oral y revalorar en 15 min."},
]


# ── Frames (16:9, Spanish bilingual) ──────────────────────────────────────────

def frame_intro_es(topic: str | None, n: int) -> Image.Image:
    img, d = _canvas("NCLEX-RN")
    _centered(d, 280, f"{n} Preguntas de Práctica", fb(96), TEXT_W)
    _centered(d, 400, "NCLEX-RN en español", fb(64), ACCENT)
    if topic:
        _centered(d, 500, topic, fr(48), TEXT_M)
    _centered(d, 628, f"Lee cada pregunta  •  {THINK_SECS} s para responder  •  Explicación después",
              fr(38), TEXT_M)
    _cta_es = "¡Comenta cuántas acertaste! 👇"
    _emt(img, ((W - tw(d, _cta_es, fb(40))) // 2, 712), _cta_es, fb(40), PINK)
    return img


def frame_question_es(q: dict, i: int, n: int) -> Image.Image:
    img, d = _canvas("NCLEX-RN", (i - 1, n))
    d.text((60, 110), f"Pregunta {i} de {n}", font=fb(36), fill=AMBER)
    if q.get("module_title"):
        d.text((60 + tw(d, f"Pregunta {i} de {n}", fb(36)) + 30, 114),
               f"·  {q['module_title'][:60]}", font=fr(32), fill=TEXT_M)
    d.rounded_rectangle([60, 170, W - 240, 470], radius=22, fill=_ps._card())
    size = 42 if len(wrap(d, q["question"], fb(42), W - 380)) <= 5 else 34
    lines = wrap(d, q["question"], fb(size), W - 380)
    y = 200
    for line in lines[:6]:
        d.text((100, y), line, font=fb(size), fill=TEXT_W)
        y += size + 14
    _options(d, q["options"], correct=None)
    return img


def frame_answer_es(q: dict, i: int, n: int) -> Image.Image:
    img, d = _canvas("NCLEX-RN", (i, n))
    d.rounded_rectangle([60, 110, W - 60, 200], radius=18, fill=GREEN)
    banner = f"✓  Respuesta correcta: {q['correct']}  —  {q['options'].get(q['correct'], '')}"
    lines = wrap(d, banner, fb(40), W - 200)
    d.text((100, 130), lines[0], font=fb(40), fill=BG_DARK)
    kt = wrap(d, q["explanation_es"], fr(40), W - 260)[:6]
    box_h = 90 + len(kt) * 54
    d.rounded_rectangle([60, 240, W - 60, 240 + box_h], radius=20,
                        fill=(40, 32, 10), outline=AMBER, width=3)
    d.text((100, 262), "Explicación", font=fb(38), fill=AMBER)
    y = 320
    for line in kt:
        d.text((100, y), line, font=fr(40), fill=(251, 229, 163))
        y += 54
    _options(d, q["options"], correct=q["correct"], y0=240 + box_h + 30, ch=150)
    return img


def frame_outro_es() -> Image.Image:
    img, d = _canvas("NCLEX-RN")
    _centered(d, 280, "¿Cuántas acertaste?", fb(84), TEXT_W)
    _centered(d, 398, "Cuéntanos tu puntuación en los comentarios", fr(48), TEXT_M)
    _centered(d, 538, "Practica más preguntas NCLEX gratis:", fb(56), PINK)
    _centered(d, 628, "medmind.pro/es/nclex", fb(64), ACCENT)
    _centered(d, 778, "Suscríbete: un nuevo simulacro cada semana", fr(40), TEXT_M)
    return img


# ── Data ──────────────────────────────────────────────────────────────────────

def _tracking() -> dict:
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except Exception:
            pass
    return {"sessions": []}


def fetch_questions(count: int, topic: str | None, allow_reuse: bool) -> list[dict]:
    used = sorted({qid for s in _tracking()["sessions"] for qid in s.get("question_ids", [])})
    where, params = [], []
    if topic:
        where.append("m.title ILIKE %s")
        params.append(f"%{topic}%")
    if used and not allow_reuse:
        where.append("NOT (q.id::text = ANY(%s))")
        params.append(used)
    extra = ("AND " + " AND ".join(where)) if where else ""
    params.append(count)
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
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
              {extra}
            ORDER BY q.created_at ASC
            LIMIT %s
            """,
            params,
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


# ── Build ─────────────────────────────────────────────────────────────────────

async def build_session_es(questions: list[dict], topic: str | None,
                           out_path: str, use_tts: bool) -> list[tuple[float, str]]:
    n = len(questions)
    chapters: list[tuple[float, str]] = []
    t = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        segs: list[str] = []

        # ── intro ──────────────────────────────────────────────────────────────
        p = f"{tmp}/intro.png"
        frame_intro_es(topic, n).save(p)
        a = f"{tmp}/intro.mp3"
        intro_text = (
            f"Bienvenido a MedMind. Aquí tienes {n} preguntas de práctica para el examen "
            f"NCLEX-RN. La pregunta está en inglés, igual que en el examen real, y la explicación "
            f"es en español. Tienes {THINK_SECS} segundos por pregunta. ¡Empezamos!"
        )
        dur = await say(intro_text, a, ES_VOICE, use_tts, ES_RATE)
        dur = max(7.0, dur + 0.8)
        seg = f"{tmp}/s000.mp4"; _encode([(p, dur, a)], seg, bg_offset=0.0); segs.append(seg)
        chapters.append((0.0, "Introducción")); t += dur

        # ── questions ─────────────────────────────────────────────────────────
        for i, q in enumerate(questions, 1):
            print(f"  [{i}/{n}] {q['question'][:70]}…")
            opts = q["options"]
            spoken_q = (f"Question {i}. {q['question']} "
                        + " ".join(f"{L}: {opts.get(L, '')}." for L in "ABCD" if opts.get(L)))
            spoken_a = f"The correct answer is {q['correct']}: {opts.get(q['correct'], '')}."

            qa = f"{tmp}/q{i}.mp3"
            aa = f"{tmp}/a{i}.mp3"
            ea = f"{tmp}/e{i}.mp3"
            qd = await say(spoken_q,             qa, EN_VOICE, use_tts, EN_RATE)
            ad = await say(spoken_a,             aa, EN_VOICE, use_tts, EN_RATE)
            ed = await say(q["explanation_es"],  ea, ES_VOICE, use_tts, ES_RATE)

            base = frame_question_es(q, i, n)
            qp = f"{tmp}/q{i}.png"; base.save(qp)
            ap = f"{tmp}/a{i}.png"; frame_answer_es(q, i, n).save(ap)

            parts: list[tuple[str, float, str | None]] = [(qp, qd + 0.6, qa)]
            for s in range(THINK_SECS, 0, -1):
                cp = f"{tmp}/c{i}_{s}.png"; frame_countdown(base, s).save(cp)
                parts.append((cp, 1.0, None))
            # answer frame: EN letter+text first, then ES explanation
            parts += [(ap, ad + 0.3, aa), (ap, ed + 1.2, ea)]

            seg = f"{tmp}/s{i:03d}.mp4"; _encode(parts, seg, bg_offset=t); segs.append(seg)
            label = f"P{i}" + (f" — {q['module_title'][:40]}" if q.get("module_title") else "")
            chapters.append((t, label))
            t += sum(x[1] for x in parts)

        # ── outro ──────────────────────────────────────────────────────────────
        p = f"{tmp}/outro.png"; frame_outro_es().save(p)
        a = f"{tmp}/outro.mp3"
        outro_text = ("¿Cuántas preguntas acertaste? Escríbelo en los comentarios y practica "
                      "más gratis en MedMind. ¡Mucho éxito en tu examen NCLEX!")
        dur = await say(outro_text, a, ES_VOICE, use_tts, ES_RATE)
        dur = max(10.0, dur + 1.0)
        seg = f"{tmp}/s999.mp4"; _encode([(p, dur, a)], seg, bg_offset=t); segs.append(seg)
        chapters.append((t, "Tu puntuación y práctica gratuita"))

        # ── concat ─────────────────────────────────────────────────────────────
        lst = f"{tmp}/list.txt"
        Path(lst).write_text("".join(f"file '{s}'\n" for s in segs))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", "-movflags", "+faststart", out_path], check=True)
    return chapters


# ── Metadata ──────────────────────────────────────────────────────────────────

_HASHTAGS_SESSION_ES = (
    "#NCLEX #NCLEXenEspañol #NCLEXRN #Enfermería #Enfermera "
    "#EnfermeríaUSA #EnfermeríaHispana #SimulacroNCLEX #PrepararNCLEX "
    "#EnfermeraLatina #MedMindAI"
)
_BASE_TAGS_SESSION_ES = [
    "nclex", "nclex rn", "nclex en español", "nclex-rn en español",
    "preguntas nclex", "simulacro nclex", "examen nclex con respuestas",
    "preparación nclex", "nclex prep", "enfermería", "enfermera",
    "enfermería usa", "enfermería hispana", "enfermera latina",
    "nclex study", "medmind",
]


def make_meta_es(questions: list[dict], topic: str | None,
                 chapters: list[tuple[float, str]]) -> tuple[str, str, list[str], dict]:
    year = datetime.date.today().year
    n = len(questions)
    t_es = topic or (topic_es(questions[0]) if questions else "Preguntas mixtas")
    t_en = (questions[0].get("nclex_category") or
            questions[0].get("module_title") or "Mixed")[:30] if questions else "Mixed"
    # Chapters: P1/P2... for Spanish viewers, Q1/Q2... for English viewers
    chap_es = "\n".join(f"{_fmt_ts(s)} {label}" for s, label in chapters)
    chap_en = "\n".join(
        f"{_fmt_ts(s)} {label.replace('P', 'Q', 1) if label.startswith('P') else label}"
        for s, label in chapters
    )

    title_es = f"🩺 {n} Preguntas NCLEX-RN en español {year} | {t_es} | Con Explicaciones"[:100]
    title_en = f"🩺 {n} NCLEX-RN Practice Questions {year} | {t_en} | Spanish Explanations"[:100]

    desc_es = (
        f"{n} preguntas de práctica NCLEX-RN {year} — {t_es}.\n"
        f"Pregunta en inglés (como en el examen real) + explicación en español.\n"
        f"¡Comenta cuántas acertaste! 👇\n\n"
        f"📝 Practica más de 1,000 preguntas NCLEX gratis con explicaciones en español:\n"
        f"🔗 https://medmind.pro/es/nclex\n\n"
        f"⏱ Capítulos:\n{chap_es}\n\n"
        f"Preguntas originales basadas en el plan oficial del NCLEX-RN; no son preguntas reales "
        f"del examen. Solo con fines educativos, no son consejo médico. Voz generada por IA.\n"
        f"⚠️ ¿Eres profesional de la salud y encontraste un error? Coméntalo abajo o repórtalo en medmind.pro — la precisión es nuestra prioridad.\n\n"
        f"{_HASHTAGS_SESSION_ES}"
    )
    desc_en = (
        f"{n} NCLEX-RN practice questions ({year}) — {t_en}.\n"
        f"Questions in English (as in the real exam), explanations in Spanish.\n\n"
        f"📝 Free NCLEX practice: https://medmind.pro/nclex\n"
        f"🔗 En español: https://medmind.pro/es/nclex\n\n"
        f"Chapters:\n{chap_en}\n\n"
        f"Original practice questions based on the NCLEX test plan — not actual exam items. "
        f"Education only, not medical advice. AI-generated voice.\n"
        f"⚠️ Healthcare professional? Found an error? Please comment below or report at medmind.pro — accuracy is our priority."
    )
    tags = (_BASE_TAGS_SESSION_ES + [f"nclex {year}", t_es.lower()])[:20]
    return title_es, desc_es, tags, {"en": {"title": title_en, "description": desc_en}}


# ── Upload ─────────────────────────────────────────────────────────────────────

def upload(mp4: str, title: str, desc: str, tags: list[str],
           localizations: dict, public: bool) -> str | None:
    import time as _time
    import google.oauth2.credentials
    import googleapiclient.discovery
    import googleapiclient.http
    data = json.loads(TOKEN_FILE.read_text())
    cid, csec = data.get("client_id"), data.get("client_secret")
    if (not cid or not csec) and SECRET_FILE.exists():
        raw = json.loads(SECRET_FILE.read_text())
        sec = raw.get("web") or raw.get("installed") or {}
        cid, csec = cid or sec.get("client_id"), csec or sec.get("client_secret")
    creds = google.oauth2.credentials.Credentials(
        token=data.get("access_token") or data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=cid, client_secret=csec)
    yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    clean = lambda s: s.replace("<", "＜").replace(">", "＞")   # noqa: E731
    body = {
        "snippet": {
            "title": clean(title), "description": clean(desc)[:4900],
            "tags": tags[:20], "categoryId": "27",
            "defaultLanguage": "es", "defaultAudioLanguage": "es",
        },
        "localizations": {
            k: {"title": clean(v["title"]), "description": clean(v["description"])[:4900]}
            for k, v in localizations.items()
        },
        "status": {"privacyStatus": "public" if public else "private",
                   "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(
        part="snippet,status,localizations", body=body,
        media_body=googleapiclient.http.MediaFileUpload(
            mp4, chunksize=-1, resumable=True, mimetype="video/mp4"))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    if creds.token and creds.token != (data.get("access_token") or data.get("token")):
        data["access_token"], data["expires_at"] = creds.token, _time.time() + 3600
        TOKEN_FILE.write_text(json.dumps(data, indent=2))
    return resp.get("id")


# ── CLI ───────────────────────────────────────────────────────────────────────

async def main():
    ap = argparse.ArgumentParser(description="NCLEX en español — bilingual practice session (16:9)")
    ap.add_argument("--count", type=int, default=DAILY_COUNT, help="questions per session")
    ap.add_argument("--topic", default=None, help="filter by module title, e.g. pharmacology")
    ap.add_argument("--out", default=None, help="output MP4 path")
    ap.add_argument("--upload", action="store_true", help="upload to YouTube (private by default)")
    ap.add_argument("--public", action="store_true", help="upload as public (already-reviewed sets)")
    ap.add_argument("--allow-reuse", action="store_true", help="allow questions from prior sessions")
    ap.add_argument("--no-tts", action="store_true", help="silent audio (layout test)")
    ap.add_argument("--demo", action="store_true", help="3 built-in demo questions, no DB")
    ap.add_argument("--dry-run", action="store_true", help="render + print metadata, no upload")
    ap.add_argument("--bg", default="auto",
                    help="animated background: aurora|ecg|molecules|cells|auto|none")
    a = ap.parse_args()

    if a.bg != "none":
        from video_backgrounds import bg_loop, pick_theme, THEMES
        theme = a.bg if a.bg in THEMES else pick_theme(f"es-session-{a.topic or 'mixed'}")
        print(f"🎨 Background: {theme}")
        _ps.BG_PATH = bg_loop(theme, W, H, secs=BG_LOOP_SECS)

    qs = DEMO_QUESTIONS if a.demo else fetch_questions(a.count, a.topic, a.allow_reuse)
    if len(qs) < 3:
        print(f"[error] only {len(qs)} matching NCLEX questions with ES translations — need ≥3")
        sys.exit(1)
    if not a.demo and len(qs) < a.count:
        print(f"⚠ only {len(qs)} questions available, making a {len(qs)}-question session")

    topic_label = (a.topic.title() if a.topic else topic_es(qs[0])) if qs else None
    out = a.out or f"/tmp/nclex_es_{len(qs)}q_{(a.topic or 'mixed').replace(' ','_')}.mp4"
    print(f"🎬 Rendering {len(qs)} questions → {out}")
    chapters = await build_session_es(qs, topic_label, out, use_tts=not a.no_tts)

    title, desc, tags, localizations = make_meta_es(qs, topic_label, chapters)
    meta_txt = Path(out).with_suffix(".txt")
    meta_txt.write_text(
        f"{title}\n\n{desc}\n\n--- en ---\n"
        f"{localizations['en']['title']}\n\n{localizations['en']['description']}\n")
    print(f"✅ {out} ({_fmt_ts(_ffprobe_dur(out))})\n   Title:  {title}\n   Meta:   {meta_txt}")

    if (a.upload or a.public) and not a.demo and not a.dry_run:
        if not TOKEN_FILE.exists():
            print(f"[error] token not found: {TOKEN_FILE}"); sys.exit(1)
        vid = upload(out, title, desc, tags, localizations, public=a.public)
        if vid:
            print(f"  ✅ https://youtu.be/{vid}")
            tr = _tracking()
            tr["sessions"].append({
                "yt_id": vid,
                "question_ids": [q["id"] for q in qs],
                "topic": topic_label,
                "count": len(qs),
                "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })
            TRACKING_FILE.write_text(json.dumps(tr, indent=2))
        else:
            print("  ✗ upload failed")
    elif a.dry_run:
        print("  [dry-run] upload skipped")


if __name__ == "__main__":
    asyncio.run(main())
