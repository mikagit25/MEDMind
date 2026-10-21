#!/usr/bin/env python3
"""
MedMind AI — Gulf bilingual practice session for the Arabic channel (16:9, ~13 min)

EN question + options narrated by EmmaMultilingualNeural (as in the real Prometric exam),
AR explanation narrated by ar-SA-ZariyahNeural.
Audience: Arabic-speaking nurses preparing for Gulf licensing exams (DHA, DOH/HAAD, SNLE, QCHP …)
Funnel: video → medmind.pro/ar/gulf

Data:
  question / options / correct  ← mcq_questions (exam_slugs contains exam)
  Arabic explanation            ← nclex_shorts_translations (lang='ar', status='done')

Format (16:9, DAILY_COUNT questions per session):
  [Intro AR] → for each question:
    [EN question + options, EN voice] → [Countdown 8s]
    → [Answer: EN letter + AR explanation, AR voice]
  → [Outro AR / CTA]

Chapters in description (Arabic + English localization).
Exam rotates by day of week — same rotation as Shorts.

Tracking:  /opt/medmind/youtube_gulf_ar_sessions.json
Token:     youtube_token_ar.json (AR channel, account3)
Cron:      0 15 * * *  (15:00 UTC daily, exam auto-selected by DOW)

Usage:
    python3 youtube_gulf_ar_session.py --dry-run
    python3 youtube_gulf_ar_session.py --public
    python3 youtube_gulf_ar_session.py --exam dha --public
    python3 youtube_gulf_ar_session.py --demo --no-tts --out /tmp/demo_ar.mp4
    python3 youtube_gulf_ar_session.py --exam haad --count 10 --public
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
import nclex_practice_session as _ps
from nclex_practice_session import (
    W, H, FPS, BG_LOOP_SECS, THINK_SECS,
    ACCENT, PINK, GREEN, AMBER, TEXT_W, TEXT_M, BG_DARK,
    _encode, _ffprobe_dur, _fmt_ts,
    _canvas, _centered, _options, frame_countdown,
)
from nclex_to_shorts import fb, fr, tw, wrap, _db_conn
from youtube_shorts_gulf_ar_daily import (
    EXAMS, _EXAM_SHORT, _EXAM_YT_TAGS, _BASE_YT_TAGS, BASE_TAGS_AR,
    _module_ar, _ar_line, ar_lines, draw_rtl, say,
)

DAILY_COUNT  = 15
EN_VOICE     = os.environ.get("TTS_VOICE_EN", "en-US-EmmaMultilingualNeural")
AR_VOICE     = os.environ.get("TTS_VOICE_AR", "ar-SA-ZariyahNeural")
EN_RATE, AR_RATE = "-5%", "-15%"

TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token_ar.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_account3_web.json"))
TRACKING_FILE = Path(os.environ.get("YT_AR_SESSION_TRACKING",
                                    "/opt/medmind/youtube_gulf_ar_sessions.json"))

# Exam by weekday (Mon=0 … Sun=6) — mirrors the Shorts rotation
_EXAM_BY_DOW = {0: "snle", 1: "dha", 2: "haad", 3: "qchp", 4: "mohuae", 5: "omsb", 6: "nhra"}

DEMO_QUESTIONS = [
    {"id": "demo-ar-s1", "module_title": "Pharmacology", "correct": "B",
     "question": "A prescription reads potassium chloride 20 mmol IV. "
                 "Which method of administration is unsafe?",
     "options": {"A": "Diluted in IV fluid via infusion pump",
                 "B": "IV push over 1 minute",
                 "C": "Infused through a central line per protocol",
                 "D": "Infused with cardiac monitoring per protocol"},
     "explanation_ar": "لا يُعطى كلوريد البوتاسيوم أبداً بالحقن الوريدي المباشر لأنه قد يسبب "
                       "اضطراباً قاتلاً في نظم القلب. يجب تخفيفه دائماً وإعطاؤه بمضخة تسريب."},
    {"id": "demo-ar-s2", "module_title": "Cardiovascular", "correct": "A",
     "question": "A nurse receives a client from PACU post-coronary artery bypass graft. "
                 "Which vital sign change requires IMMEDIATE intervention?",
     "options": {"A": "Blood pressure 85/50 mmHg",
                 "B": "Temperature 37.2°C",
                 "C": "Heart rate 88 bpm sinus rhythm",
                 "D": "SpO2 96% on 2 L nasal cannula"},
     "explanation_ar": "انخفاض ضغط الدم إلى 85/50 ملم زئبق بعد جراحة القلب المفتوح يُشير إلى "
                       "صدمة قلبية أو نزيف. يتطلب تدخلاً فورياً بالسوائل الوريدية وإبلاغ الطبيب."},
    {"id": "demo-ar-s3", "module_title": "Respiratory", "correct": "C",
     "question": "A client with COPD has an oxygen saturation of 88%. "
                 "What is the nurse's priority intervention?",
     "options": {"A": "Administer O2 at 10 L/min via non-rebreather mask",
                 "B": "Perform endotracheal intubation",
                 "C": "Administer O2 at 1-2 L/min via nasal cannula",
                 "D": "Place in Trendelenburg position"},
     "explanation_ar": "مرضى الانسداد الرئوي المزمن لديهم تحفيز تنفسي يعتمد على نقص الأكسجين. "
                       "إعطاء أكسجين بتركيز مرتفع قد يُثبط تنفسهم. الهدف الآمن: SpO2 بين 88-92%."},
]


# ── Arabic text helpers for 16:9 canvas (W=1920) ─────────────────────────────

def ar_center_16(draw, y: int, text: str, font, fill):
    """Center Arabic text horizontally in a 1920-wide frame."""
    t = _ar_line(text)
    draw.text(((W - tw(draw, t, font)) // 2, y), t, font=font, fill=fill)


# ── Frames (16:9, Arabic bilingual) ──────────────────────────────────────────

def frame_intro_ar(exam: str, n: int) -> Image.Image:
    en, ar_name, _ = EXAMS[exam]
    img, d = _canvas(en)
    ar_center_16(d, 210, f"{n} أسئلة تدريبية", fb(96), TEXT_W)
    ar_center_16(d, 328, ar_name, fb(64), ACCENT)
    _centered(d, 440, f"{en} Nursing Exam Practice", fr(46), TEXT_M)
    ar_center_16(d, 548, "السؤال بالإنجليزية كما في الامتحان • الشرح بالعربية", fr(40), TEXT_M)
    ar_center_16(d, 626, f"لديك {THINK_SECS} ثوان للتفكير في كل سؤال", fr(38), AMBER)
    ar_center_16(d, 720, "اكتب كم أجبت صح في التعليقات 👇", fb(44), PINK)
    return img


def frame_question_ar(q: dict, exam: str, i: int, n: int) -> Image.Image:
    en = EXAMS[exam][0]
    img, d = _canvas(en, (i - 1, n))
    # Arabic question label — right-aligned
    label = _ar_line(f"سؤال {i} من {n}")
    d.text((W - 60 - tw(d, label, fb(36)), 110), label, font=fb(36), fill=AMBER)
    if q.get("module_title"):
        mod_ar = _module_ar(q["module_title"])
        mt = _ar_line(f"· {mod_ar}")
        d.text((W - 60 - tw(d, label, fb(36)) - 30 - tw(d, mt, fr(32)), 114),
               mt, font=fr(32), fill=TEXT_M)
    # EN question card (LTR)
    d.rounded_rectangle([60, 170, W - 60, 460], radius=22, fill=_ps._card())
    size = 42 if len(wrap(d, q["question"], fb(42), W - 200)) <= 4 else 34
    lines = wrap(d, q["question"], fb(size), W - 200)
    y = 200
    for line in lines[:5]:
        d.text((100, y), line, font=fb(size), fill=TEXT_W)
        y += size + 14
    _options(d, q["options"], correct=None)
    return img


def frame_answer_ar(q: dict, exam: str, i: int, n: int) -> Image.Image:
    en = EXAMS[exam][0]
    img, d = _canvas(en, (i, n))
    # Green banner — Arabic "correct answer"
    d.rounded_rectangle([60, 110, W - 60, 200], radius=18, fill=GREEN)
    correct_txt = q["options"].get(q["correct"], "")
    banner = _ar_line(f"✓  الإجابة الصحيحة: {q['correct']}  —  {correct_txt[:45]}")
    d.text(((W - tw(d, banner, fb(40))) // 2, 130), banner, font=fb(40), fill=BG_DARK)
    # Arabic explanation box
    exp_lines = ar_lines(d, q["explanation_ar"], fr(40), W - 200)[:6]
    box_h = 90 + len(exp_lines) * 56
    d.rounded_rectangle([60, 240, W - 60, 240 + box_h], radius=20,
                        fill=(40, 32, 10), outline=AMBER, width=3)
    lbl = _ar_line("الشرح")
    d.text((W - 120 - tw(d, lbl, fb(38)), 262), lbl, font=fb(38), fill=AMBER)
    draw_rtl(d, exp_lines, W - 100, 320, fr(40), (251, 229, 163), 56)
    # Options with correct highlighted
    _options(d, q["options"], correct=q["correct"], y0=240 + box_h + 20, ch=130)
    return img


def frame_outro_ar(exam: str) -> Image.Image:
    _, ar_name, _ = EXAMS[exam]
    en = EXAMS[exam][0]
    img, d = _canvas(en)
    ar_center_16(d, 210, "كم سؤالاً أجبت صح؟", fb(84), TEXT_W)
    ar_center_16(d, 322, "اكتب نتيجتك في التعليقات", fr(48), TEXT_M)
    ar_center_16(d, 462, f"تدرّب مجاناً على أسئلة {ar_name}:", fb(52), PINK)
    _centered(d, 562, "medmind.pro/ar/gulf", fb(64), ACCENT)
    ar_center_16(d, 692, "اشترك: جلسة تمريض جديدة كل يوم", fr(40), TEXT_M)
    return img


# ── Data ──────────────────────────────────────────────────────────────────────

def _tracking() -> dict:
    if TRACKING_FILE.exists():
        try:
            return json.loads(TRACKING_FILE.read_text())
        except Exception:
            pass
    return {"sessions": []}


def fetch_questions(exam: str, count: int, allow_reuse: bool) -> list[dict]:
    used = sorted({qid for s in _tracking()["sessions"]
                   if s.get("exam") == exam
                   for qid in s.get("question_ids", [])})
    params: list = [json.dumps([exam])]
    extra = ""
    if used and not allow_reuse:
        extra = "AND NOT (q.id::text = ANY(%s))"
        params.append(used)
    params.append(count)
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT q.id::text AS id, q.question, q.options, q.correct,
                   t.key_takeaway AS explanation_ar, m.title AS module_title
            FROM mcq_questions q
            JOIN nclex_shorts_translations t
                 ON t.question_id = q.id::text AND t.lang = 'ar' AND t.status = 'done'
            LEFT JOIN modules m ON m.id = q.module_id
            WHERE q.question_type = 'mcq'
              AND q.exam_slugs @> %s::jsonb
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
    return rows


# ── Build ─────────────────────────────────────────────────────────────────────

async def build_session_ar(questions: list[dict], exam: str,
                           out_path: str, use_tts: bool) -> list[tuple[float, str]]:
    _, ar_name, _ = EXAMS[exam]
    n = len(questions)
    chapters: list[tuple[float, str]] = []
    t = 0.0

    with tempfile.TemporaryDirectory() as tmp:
        segs: list[str] = []

        # ── intro ──────────────────────────────────────────────────────────────
        p = f"{tmp}/intro.png"
        frame_intro_ar(exam, n).save(p)
        a_path = f"{tmp}/intro.mp3"
        intro_text = (
            f"مرحباً بك في MedMind. إليك {n} سؤالاً تدريبياً لامتحان {ar_name}. "
            f"كل سؤال بالإنجليزية كما في الامتحان الحقيقي، والشرح بالعربية. "
            f"لديك {THINK_SECS} ثوان للإجابة. بالتوفيق!"
        )
        dur = await say(intro_text, a_path, AR_VOICE, use_tts, AR_RATE)
        dur = max(8.0, dur + 0.8)
        seg = f"{tmp}/s000.mp4"; _encode([(p, dur, a_path)], seg, bg_offset=0.0); segs.append(seg)
        chapters.append((0.0, "مقدمة")); t += dur

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
            qd = await say(spoken_q,              qa, EN_VOICE, use_tts, EN_RATE)
            ad = await say(spoken_a,              aa, EN_VOICE, use_tts, EN_RATE)
            ed = await say(q["explanation_ar"],   ea, AR_VOICE, use_tts, AR_RATE)

            base = frame_question_ar(q, exam, i, n)
            qp = f"{tmp}/q{i}.png"; base.save(qp)
            ap_img = f"{tmp}/a{i}.png"; frame_answer_ar(q, exam, i, n).save(ap_img)

            parts: list[tuple[str, float, str | None]] = [(qp, qd + 0.6, qa)]
            for s in range(THINK_SECS, 0, -1):
                cp = f"{tmp}/c{i}_{s}.png"; frame_countdown(base, s).save(cp)
                parts.append((cp, 1.0, None))
            parts += [(ap_img, ad + 0.3, aa), (ap_img, ed + 1.2, ea)]

            seg = f"{tmp}/s{i:03d}.mp4"; _encode(parts, seg, bg_offset=t); segs.append(seg)
            topic_ar = _module_ar(q.get("module_title") or "")
            label = f"س{i}" + (f" — {topic_ar[:30]}" if topic_ar != "تمريض" else "")
            chapters.append((t, label))
            t += sum(x[1] for x in parts)

        # ── outro ──────────────────────────────────────────────────────────────
        p = f"{tmp}/outro.png"; frame_outro_ar(exam).save(p)
        a_path = f"{tmp}/outro.mp3"
        outro_text = (
            f"كم سؤالاً أجبت صح؟ اكتب نتيجتك في التعليقات وتدرّب على المزيد مجاناً "
            f"في MedMind. بالتوفيق في امتحان {ar_name}!"
        )
        dur = await say(outro_text, a_path, AR_VOICE, use_tts, AR_RATE)
        dur = max(10.0, dur + 1.0)
        seg = f"{tmp}/s999.mp4"; _encode([(p, dur, a_path)], seg, bg_offset=t); segs.append(seg)
        chapters.append((t, "نتيجتك وتدريب مجاني"))

        # ── concat ─────────────────────────────────────────────────────────────
        lst = f"{tmp}/list.txt"
        Path(lst).write_text("".join(f"file '{s}'\n" for s in segs))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", "-movflags", "+faststart", out_path], check=True)
    return chapters


# ── Metadata ──────────────────────────────────────────────────────────────────

_HASHTAGS_SESSION_AR = (
    "#تمريض #اسئلة_تمريض #برومترك #امتحان_التمريض "
    "#شرح_بالعربي #تمريض_الخليج #MedMindAI"
)
_BASE_TAGS_SESSION_AR = [
    "prometric nursing", "برومترك تمريض", "اسئلة تمريض",
    "شرح بالعربي", "gulf nursing exam", "تمريض الخليج",
    "امتحان التمريض", "اسئلة برومترك", "تمريض", "medmind",
]


def make_meta_ar(questions: list[dict], exam: str,
                 chapters: list[tuple[float, str]]) -> tuple[str, str, list[str], dict]:
    year = datetime.date.today().year
    n = len(questions)
    en, ar_name, exam_hashtags = EXAMS[exam]
    short = _EXAM_SHORT[exam]
    topic_en = (questions[0].get("module_title") or "Nursing")[:30] if questions else "Nursing"
    topic_ar = _module_ar(topic_en)

    # Chapters: Arabic س1/س2 for AR viewers, Q1/Q2 for EN viewers
    chap_ar = "\n".join(f"{_fmt_ts(s)} {label}" for s, label in chapters)
    chap_en = "\n".join(
        f"{_fmt_ts(s)} {label.replace('س', 'Q', 1) if label.startswith('س') else label}"
        for s, label in chapters
    )

    title_ar = f"🩺 {n} سؤال امتحان {short} تمريض {year} | {topic_ar} | شرح بالعربي"[:100]
    title_en = f"🩺 {n} {en} Nursing Exam Questions {year} | {topic_en} | Arabic Explanations"[:100]

    desc_ar = (
        f"{n} سؤالاً تدريبياً لامتحان {ar_name} {year} — {topic_ar}.\n"
        f"السؤال بالإنجليزية كما في الامتحان الحقيقي + الشرح بالعربية.\n"
        f"اكتب كم أجبت صح في التعليقات! 👇\n\n"
        f"📝 تدرّب مجاناً على أسئلة {ar_name}:\n"
        f"🔗 https://medmind.pro/ar/gulf\n"
        f"🌐 English: https://medmind.pro/exams/{exam}\n\n"
        f"⏱ الفصول:\n{chap_ar}\n\n"
        f"أسئلة تدريبية مبنية على مخطط الامتحان الرسمي — ليست من الأسئلة الفعلية للامتحان. "
        f"للتعليم والتحضير فقط، وليست نصيحة طبية. الصوت: ذكاء اصطناعي.\n"
        f"⚠️ هل أنت متخصص صحي ووجدت خطأً؟ أخبرنا في التعليقات أو على medmind.pro — الدقة أولويتنا.\n\n"
        f"{exam_hashtags} {_HASHTAGS_SESSION_AR}"
    )
    desc_en = (
        f"{n} {en} nursing exam practice questions ({year}) — {topic_en}.\n"
        f"Questions in English (as in the real Prometric exam), explanations in Arabic.\n\n"
        f"📝 Free {en} practice: https://medmind.pro/exams/{exam}\n"
        f"🔗 Arabic: https://medmind.pro/ar/gulf\n\n"
        f"Chapters:\n{chap_en}\n\n"
        f"Original practice questions based on the official exam blueprint — not actual exam items. "
        f"Education only, not medical advice. AI-generated voice.\n"
        f"⚠️ Healthcare professional? Found an error? Please comment below or report at medmind.pro — accuracy is our priority."
    )
    tags = (_EXAM_YT_TAGS.get(exam, []) + _BASE_TAGS_SESSION_AR + [topic_en.lower()])[:20]
    return title_ar, desc_ar, tags, {"en": {"title": title_en, "description": desc_en}}


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
    clean = lambda s: s.replace("<", "＜").replace(">", "＞")  # noqa: E731
    body = {
        "snippet": {
            "title": clean(title), "description": clean(desc)[:4900],
            "tags": tags[:20], "categoryId": "27",
            "defaultLanguage": "ar", "defaultAudioLanguage": "ar",
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
    dow = datetime.date.today().weekday()
    default_exam = _EXAM_BY_DOW.get(dow, "dha")

    ap = argparse.ArgumentParser(
        description="Gulf bilingual practice session for Arabic channel (16:9)")
    ap.add_argument("--exam", choices=sorted(EXAMS), default=default_exam,
                    help=f"Gulf exam slug (default: today's rotation = {default_exam})")
    ap.add_argument("--count", type=int, default=DAILY_COUNT, help="questions per session")
    ap.add_argument("--out", default=None, help="output MP4 path")
    ap.add_argument("--upload", action="store_true", help="upload to YouTube (private)")
    ap.add_argument("--public", action="store_true", help="upload as public")
    ap.add_argument("--allow-reuse", action="store_true",
                    help="allow questions used in prior sessions")
    ap.add_argument("--no-tts", action="store_true", help="silent audio (layout test)")
    ap.add_argument("--demo", action="store_true", help="3 built-in demo questions, no DB")
    ap.add_argument("--dry-run", action="store_true",
                    help="render + print metadata, no upload")
    ap.add_argument("--bg", default="auto",
                    help="animated background: aurora|ecg|molecules|cells|auto|none")
    a = ap.parse_args()

    if a.bg != "none":
        from video_backgrounds import bg_loop, pick_theme, THEMES
        theme = a.bg if a.bg in THEMES else pick_theme(f"ar-session-{a.exam}")
        print(f"🎨 Background: {theme}")
        _ps.BG_PATH = bg_loop(theme, W, H, secs=BG_LOOP_SECS)

    qs = DEMO_QUESTIONS if a.demo else fetch_questions(a.exam, a.count, a.allow_reuse)
    if len(qs) < 3:
        print(f"[error] only {len(qs)} questions for exam={a.exam} with AR translations — need ≥3")
        sys.exit(1)
    if not a.demo and len(qs) < a.count:
        print(f"⚠ only {len(qs)} questions available, making a {len(qs)}-question session")

    en_name = EXAMS[a.exam][0]
    out = a.out or f"/tmp/gulf_ar_{a.exam}_{len(qs)}q.mp4"
    print(f"🎬 Rendering {len(qs)} questions ({en_name}) → {out}")
    chapters = await build_session_ar(qs, a.exam, out, use_tts=not a.no_tts)

    title, desc, tags, localizations = make_meta_ar(qs, a.exam, chapters)
    meta_txt = Path(out).with_suffix(".txt")
    meta_txt.write_text(
        f"{title}\n\n{desc}\n\n--- en ---\n"
        f"{localizations['en']['title']}\n\n{localizations['en']['description']}\n")
    print(f"✅ {out} ({_fmt_ts(_ffprobe_dur(out))})\n"
          f"   Title:  {title}\n"
          f"   Meta:   {meta_txt}")

    if (a.upload or a.public) and not a.demo and not a.dry_run:
        if not TOKEN_FILE.exists():
            print(f"[error] token not found: {TOKEN_FILE}"); sys.exit(1)
        vid = upload(out, title, desc, tags, localizations, public=a.public)
        if vid:
            print(f"  ✅ https://youtu.be/{vid}")
            tr = _tracking()
            tr["sessions"].append({
                "yt_id": vid,
                "exam": a.exam,
                "question_ids": [q["id"] for q in qs],
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
