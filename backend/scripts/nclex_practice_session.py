#!/usr/bin/env python3
"""
MedMind AI — Long-form exam practice session (16:9, 15-30 min)

Turns N questions from the MCQ bank into one YouTube practice video:

  [Intro]  →  for each question:
              [Question + options, narrated] → [Countdown timer] → [Answer + rationale, narrated]
           →  [Outro / CTA]

The description gets YouTube chapters (one per question), so viewers can jump
around and YouTube shows the topics in search.

Rendering is plain PIL + ffmpeg (one MP4 segment per question, then a lossless
concat), so memory stays flat even for 30+ questions on the 15 GB server.

Usage:
    # Render a 25-question DHA session (no upload)
    python3 nclex_practice_session.py --exam dha --count 25

    # Only one topic, upload as PRIVATE for review (default privacy)
    python3 nclex_practice_session.py --exam snle --topic pharmacology --count 20 --upload

    # Offline smoke test: 3 built-in demo questions, silent audio, no DB / network
    python3 nclex_practice_session.py --demo --no-tts --out /tmp/demo_session.mp4

Videos are uploaded PRIVATE by default: check the answers before making them
public (--public skips that, only use it for already-reviewed question sets).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from nclex_to_shorts import fb, fr, tw, wrap, _db_conn  # noqa: E402  (shared fonts + DB)

# ── Config ────────────────────────────────────────────────────────────────────

W, H        = 1920, 1080
FPS         = 24
# EmmaNeural = Microsoft Copilot-grade voice (2024), much more natural than Jenny/Aria.
# Override with --voice or TTS_VOICE env var.
VOICE       = os.environ.get("TTS_VOICE", "en-US-EmmaMultilingualNeural")
RATE        = "-5%"
THINK_SECS  = 8          # countdown length per question
INTRO_SECS  = 7
OUTRO_SECS  = 10

# OpenAI TTS (tts-1-hd) — best quality, ~$0.75 per 25-question video.
# Set OPENAI_API_KEY in backend/.env to enable. Use --tts-provider openai.
OPENAI_TTS_MODEL  = "tts-1-hd"
OPENAI_TTS_VOICES = {
    "female": "nova",   # warm, professional
    "male":   "onyx",   # deep, authoritative
}
_OPENAI_KEY: str | None = None


def _load_openai_key() -> str | None:
    global _OPENAI_KEY
    if _OPENAI_KEY:
        return _OPENAI_KEY
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    _OPENAI_KEY = key or None
    return _OPENAI_KEY

BG_DARK  = (10, 14, 20)
BG_CARD  = (18, 26, 38)

# Animated background (video_backgrounds.py). None → classic flat dark background.
BG_PATH: str | None = None
BG_LOOP_SECS = 12


def _card():
    """Card fill: slightly see-through over an animated background, solid otherwise."""
    return BG_CARD + (226,) if BG_PATH else BG_CARD
ACCENT   = (99, 179, 237)
PINK     = (236, 72, 153)
GREEN    = (52, 211, 153)
AMBER    = (251, 191, 36)
TEXT_W   = (230, 237, 243)
TEXT_M   = (148, 163, 184)
LETTER_COLORS = {"A": (99, 179, 237), "B": (167, 139, 250), "C": (52, 211, 153), "D": (251, 191, 36)}

TOKEN_FILE  = Path(os.environ.get("YT_TOKEN", "/opt/medmind/youtube_token.json"))
SECRET_FILE = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_web.json"))
TRACKING    = Path(os.environ.get("YT_SESSION_TRACKING", "/opt/medmind/youtube_practice_sessions.json"))

EXAMS = {  # slug → (display name, extra tags)
    "snle":   ("Saudi SNLE (SCFHS)", ["snle", "scfhs exam", "saudi nursing exam"]),
    "dha":    ("DHA Dubai",          ["dha exam", "dha nursing exam", "dubai nurse"]),
    "haad":   ("DOH Abu Dhabi",      ["haad exam", "doh exam", "abu dhabi nursing exam"]),
    "mohuae": ("MOH UAE",            ["moh exam", "moh uae nursing exam"]),
    "qchp":   ("QCHP Qatar",         ["qchp exam", "qatar nursing exam"]),
    "omsb":   ("OMSB Oman",          ["omsb exam", "oman nursing exam"]),
    "nhra":   ("NHRA Bahrain",       ["nhra exam", "bahrain nursing exam"]),
    "moh_kw": ("Kuwait MOH",         ["kuwait nursing exam"]),
}
BASE_TAGS = ["prometric exam", "prometric nursing questions", "nursing exam questions",
             "gulf nursing exam", "nursing mcq", "nursing exam practice", "medmind"]

DEMO_QUESTIONS = [
    {"id": "demo-1", "module_title": "Endocrine",
     "question": "A conscious adult client with diabetes has a capillary glucose of 3.2 mmol/L "
                 "(58 mg/dL) and is sweaty and shaky. What is the nurse's first action?",
     "options": {"A": "Give 15 g of fast-acting oral carbohydrate",
                 "B": "Administer the scheduled insulin dose",
                 "C": "Recheck the glucose in 1 hour",
                 "D": "Give a high-protein snack only"},
     "correct": "A",
     "key_takeaway": "Conscious hypoglycemia: 15 g fast-acting carbohydrate, recheck in 15 minutes, "
                     "repeat if still low, then a snack or meal."},
    {"id": "demo-2", "module_title": "Pharmacology",
     "question": "A prescription reads potassium chloride 20 mmol IV. "
                 "Which method of administration is unsafe?",
     "options": {"A": "Diluted in IV fluid via infusion pump",
                 "B": "IV push over 1 minute",
                 "C": "Infused through a central line per protocol",
                 "D": "Infused with cardiac monitoring per protocol"},
     "correct": "B",
     "key_takeaway": "Never give potassium chloride by IV push: it can cause fatal arrhythmias. "
                     "Always dilute and infuse with a pump."},
    {"id": "demo-3", "module_title": "Cardiovascular",
     "question": "Before giving digoxin to an adult client, the nurse counts an apical pulse of 54 "
                 "beats per minute. What should the nurse do?",
     "options": {"A": "Give the dose and document",
                 "B": "Give half the dose",
                 "C": "Hold the dose and notify the prescriber",
                 "D": "Give the dose with food"},
     "correct": "C",
     "key_takeaway": "Hold digoxin when the adult apical pulse is below 60 per minute "
                     "and report it; also watch for nausea and visual changes."},
]

# ── Question selection ────────────────────────────────────────────────────────

def _load_tracking() -> dict:
    if TRACKING.exists():
        return json.loads(TRACKING.read_text())
    return {"sessions": []}


def fetch_questions(exam: str | None, topic: str | None, count: int,
                    allow_reuse: bool = False) -> list[dict]:
    """Questions with key_takeaway, optionally filtered by exam slug and module title.

    Questions already used in a previous practice session are skipped unless allow_reuse.
    (Re-using a question that was a Short is fine — different format and audience.)
    """
    used = sorted({qid for s in _load_tracking()["sessions"] for qid in s["question_ids"]})
    where, params = [], []
    if exam:
        where.append("q.exam_slugs @> %s::jsonb")
        params.append(json.dumps([exam]))
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
            SELECT q.id::text AS id, q.question, q.options, q.correct, q.key_takeaway,
                   q.difficulty, m.title AS module_title
            FROM mcq_questions q
            LEFT JOIN modules m ON m.id = q.module_id
            WHERE q.key_takeaway IS NOT NULL
              AND q.question_type = 'mcq'
              AND q.question ~ '^[A-Za-z]'
              AND q.question !~ '[А-яЁё]'
              {extra}
            ORDER BY m.title NULLS LAST, q.created_at ASC
            LIMIT %s
            """,
            params,
        )
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if not isinstance(r["options"], dict):
            r["options"] = json.loads(r["options"])
    return rows


# ── Frames (16:9) ─────────────────────────────────────────────────────────────

def _canvas(badge: str, progress: tuple[int, int] | None = None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if BG_PATH else Image.new("RGB", (W, H), BG_DARK)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=PINK)
    d.text((60, 34), "MedMind", font=fb(40), fill=TEXT_W)
    bb = d.textbbox((60, 34), "MedMind", font=fb(40))
    d.text((bb[2] + 8, 34), "AI", font=fb(40), fill=ACCENT)
    bw = tw(d, badge, fb(28)) + 36
    d.rounded_rectangle([W - bw - 60, 30, W - 60, 82], radius=14, fill=PINK)
    d.text((W - bw - 42, 38), badge, font=fb(28), fill=(255, 255, 255))
    if progress:
        i, n = progress
        d.rectangle([0, H - 10, W, H], fill=_card())
        d.rectangle([0, H - 10, int(W * i / n), H], fill=ACCENT)
    return img, d


def _centered(d, y, text, font, fill):
    d.text(((W - tw(d, text, font)) // 2, y), text, font=font, fill=fill)


def frame_intro(exam_name: str, topic: str | None, n: int) -> Image.Image:
    img, d = _canvas(exam_name)
    _centered(d, 300, f"{n} Practice Questions", fb(96), TEXT_W)
    _centered(d, 420, f"{exam_name} Nursing Exam" if exam_name != "Gulf Nursing Exams"
              else "Gulf Nursing Licensing Exams", fb(64), ACCENT)
    if topic:
        _centered(d, 510, topic.title(), fr(48), TEXT_M)
    _centered(d, 640, f"Read each question  •  {THINK_SECS} seconds to answer  •  Rationale after",
              fr(38), TEXT_M)
    _centered(d, 720, "Keep score in the comments!", fb(40), PINK)
    return img


def frame_question(q: dict, i: int, n: int, exam_name: str) -> Image.Image:
    img, d = _canvas(exam_name, (i - 1, n))
    d.text((60, 110), f"Question {i} of {n}", font=fb(36), fill=AMBER)
    if q.get("module_title"):
        d.text((60 + tw(d, f"Question {i} of {n}", fb(36)) + 30, 114),
               f"·  {q['module_title'][:60]}", font=fr(32), fill=TEXT_M)
    # question card
    # card leaves room on the right for the countdown timer
    d.rounded_rectangle([60, 170, W - 240, 470], radius=22, fill=_card())
    lines = wrap(d, q["question"], fb(42), W - 380)
    size = 42 if len(lines) <= 5 else 34
    lines = wrap(d, q["question"], fb(size), W - 380)
    y = 200
    for line in lines[:6]:
        d.text((100, y), line, font=fb(size), fill=TEXT_W)
        y += size + 14
    # options, 2 x 2 grid
    _options(d, q["options"], correct=None)
    return img


def _options(d, options: dict, correct: str | None, y0: int = 500, ch: int = 230):
    cw = (W - 60 * 2 - 40) // 2
    for k, letter in enumerate(["A", "B", "C", "D"]):
        text = options.get(letter, "")
        if not text:
            continue
        x = 60 + (k % 2) * (cw + 40)
        y = y0 + (k // 2) * (ch + 30)
        if correct is None:
            fill, outline, col, tcol = _card(), None, LETTER_COLORS[letter], TEXT_W
        elif letter == correct:
            fill, outline, col, tcol = (20, 60, 40), GREEN, GREEN, TEXT_W
        else:
            fill, outline, col, tcol = (22, 27, 38), (50, 60, 75), (70, 80, 95), TEXT_M
        d.rounded_rectangle([x, y, x + cw, y + ch], radius=18, fill=fill,
                            outline=outline, width=3 if outline else 0)
        cx, cy = x + 60, y + ch // 2
        d.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=col)
        d.text((cx - tw(d, letter, fb(40)) // 2, cy - 25), letter, font=fb(40), fill=BG_DARK)
        ol = wrap(d, text, fr(36), cw - 150)[:4 if ch >= 200 else 2]
        ty = y + (ch - len(ol) * 46) // 2
        for line in ol:
            d.text((x + 120, ty), line, font=fr(36), fill=tcol)
            ty += 46


def frame_countdown(base: Image.Image, secs_left: int) -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    r = 76
    cx, cy = W - 140, 320            # right of the question card
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PINK if secs_left <= 3 else AMBER)
    t = str(secs_left)
    d.text((cx - tw(d, t, fb(76)) // 2, cy - 46), t, font=fb(76), fill=BG_DARK)
    return img


def frame_answer(q: dict, i: int, n: int, exam_name: str) -> Image.Image:
    img, d = _canvas(exam_name, (i, n))
    d.rounded_rectangle([60, 110, W - 60, 200], radius=18, fill=GREEN)
    banner = f"✓  Correct answer: {q['correct']}  —  {q['options'].get(q['correct'], '')}"
    lines = wrap(d, banner, fb(40), W - 200)
    d.text((100, 130), lines[0], font=fb(40), fill=BG_DARK)
    # rationale card
    kt = wrap(d, q["key_takeaway"], fr(40), W - 260)[:6]
    box_h = 90 + len(kt) * 54
    d.rounded_rectangle([60, 240, W - 60, 240 + box_h], radius=20,
                        fill=(40, 32, 10), outline=AMBER, width=3)
    d.text((100, 262), "Rationale", font=fb(38), fill=AMBER)
    y = 320
    for line in kt:
        d.text((100, y), line, font=fr(40), fill=(251, 229, 163))
        y += 54
    # options again, correct one highlighted, others dimmed
    _options(d, q["options"], correct=q["correct"], y0=240 + box_h + 30, ch=150)
    return img


def frame_outro(exam: str | None, exam_name: str) -> Image.Image:
    img, d = _canvas(exam_name)
    _centered(d, 280, "How many did you get right?", fb(84), TEXT_W)
    _centered(d, 400, "Tell us your score in the comments", fr(48), TEXT_M)
    _centered(d, 540, "Free full-length practice test:", fb(56), PINK)
    url = f"medmind.pro/exams/{exam}" if exam else "medmind.pro/exams/gulf"
    _centered(d, 630, url, fb(64), ACCENT)
    _centered(d, 780, "Subscribe for a new practice session every week", fr(40), TEXT_M)
    return img


# ── Audio / encoding helpers ──────────────────────────────────────────────────

def _ffprobe_dur(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


async def tts(text: str, path: str, enabled: bool,
              provider: str = "edge", voice_gender: str = "female") -> float:
    """Narrate text to MP3; returns duration.

    provider: "edge" (free, EmmaNeural) | "openai" (tts-1-hd, ~$0.03/1k chars)
    With enabled=False writes silence of estimated length.
    """
    if enabled:
        if provider == "openai":
            key = _load_openai_key()
            if key:
                try:
                    import httpx as _hx
                    voice_id = OPENAI_TTS_VOICES.get(voice_gender, "nova")
                    r = _hx.post(
                        "https://api.openai.com/v1/audio/speech",
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": OPENAI_TTS_MODEL, "input": text[:4096],
                              "voice": voice_id, "response_format": "mp3"},
                        timeout=60,
                    )
                    if r.status_code == 200:
                        Path(path).write_bytes(r.content)
                        dur = _ffprobe_dur(path)
                        if dur > 0:
                            return dur
                    else:
                        print(f"    [openai-tts] {r.status_code} — falling back to edge-tts")
                except Exception as e:
                    print(f"    [openai-tts] {e} — falling back to edge-tts")
            else:
                print("    [openai-tts] OPENAI_API_KEY not set — using edge-tts")
        # edge-tts (default / fallback)
        import edge_tts
        await edge_tts.Communicate(text[:1500], VOICE, rate=RATE).save(path)
        dur = _ffprobe_dur(path)
        if dur > 0:
            return dur
    est = max(3.0, len(text.split()) / 150 * 60)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", f"{est:.2f}", "-q:a", "9", path], check=True)
    return est


def _encode(parts: list[tuple[str, float, str | None]], out: str,
            bg: str | None = None, bg_offset: float = 0.0):
    """parts: [(png, seconds, audio_or_None)] → one MP4 segment with continuous AAC track.

    bg: looping background MP4 (video_backgrounds.bg_loop); the PNGs are then RGBA and are
    overlaid on it. bg_offset = time of this segment inside the whole video, so the motion
    continues smoothly across segments instead of restarting."""
    bg = bg if bg is not None else BG_PATH
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for png, secs, _ in parts:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{secs:.3f}", "-i", png]
    audio_inputs = []
    for png, secs, audio in parts:
        if audio:
            cmd += ["-i", audio]
        else:
            cmd += ["-f", "lavfi", "-t", f"{secs:.3f}", "-i", "anullsrc=r=24000:cl=mono"]
        audio_inputs.append(secs)
    n = len(parts)
    filt = []
    for k, (_, secs, _) in enumerate(parts):
        # pad/trim each audio piece to exactly its picture length
        filt.append(f"[{n + k}:a]aresample=44100,apad,atrim=0:{secs:.3f}[a{k}]")
    if bg:
        cmd += ["-stream_loop", "-1", "-ss", f"{bg_offset % BG_LOOP_SECS:.3f}", "-i", bg]
        vcat = ("".join(f"[{k}:v]" for k in range(n)) + f"concat=n={n}:v=1:a=0,format=rgba[fg];"
                f"[{2 * n}:v]scale={_wh(parts)}:force_original_aspect_ratio=increase,"
                f"crop={_wh(parts)},setsar=1,fps={FPS}[bgv];"
                f"[bgv][fg]overlay=0:0:shortest=1:format=auto,format=yuv420p[v]")
    else:
        vcat = "".join(f"[{k}:v]" for k in range(n)) + f"concat=n={n}:v=1:a=0,format=yuv420p[v]"
    acat = "".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[a]"
    filt += [vcat, acat]
    tune = [] if bg else ["-tune", "stillimage"]
    cmd += ["-filter_complex", ";".join(filt), "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", *tune, "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", out]
    subprocess.run(cmd, check=True)


def _wh(parts) -> str:
    """'W:H' of the PNGs being encoded (16:9 sessions and 9:16 Shorts share _encode)."""
    with Image.open(parts[0][0]) as im:
        return f"{im.width}:{im.height}"


def _fmt_ts(sec: float) -> str:
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ── Build ─────────────────────────────────────────────────────────────────────

async def build_session(questions: list[dict], exam: str | None, topic: str | None,
                        out_path: str, use_tts: bool,
                        tts_provider: str = "edge") -> list[tuple[float, str]]:
    """Render the whole session. Returns chapters [(start_sec, label)]."""
    exam_name = EXAMS[exam][0] if exam else "Gulf Nursing Exams"
    n = len(questions)
    chapters: list[tuple[float, str]] = []
    t = 0.0
    with tempfile.TemporaryDirectory() as tmp:
        segs = []

        # intro
        p = f"{tmp}/intro.png"; frame_intro(exam_name, topic, n).save(p)  # noqa: E702
        a = f"{tmp}/intro.mp3"
        intro_text = (f"Welcome to MedMind. Here are {n} practice questions for the {exam_name} "
                      f"nursing exam. You have {THINK_SECS} seconds for each question. Let's begin.")
        a_dur = await tts(intro_text, a, use_tts, provider=tts_provider)
        dur = max(INTRO_SECS, a_dur + 0.8)
        seg = f"{tmp}/s000.mp4"; _encode([(p, dur, a)], seg, bg_offset=0.0); segs.append(seg)
        chapters.append((0.0, "Introduction")); t += dur

        for i, q in enumerate(questions, 1):
            print(f"  [{i}/{n}] {q['question'][:70]}…")
            opts = q["options"]
            spoken_q = (f"Question {i}. {q['question']} "
                        + " ".join(f"{L}: {opts.get(L, '')}." for L in "ABCD" if opts.get(L)))
            spoken_a = (f"The correct answer is {q['correct']}: {opts.get(q['correct'], '')}. "
                        f"{q['key_takeaway']}")
            qa, aa = f"{tmp}/q{i}.mp3", f"{tmp}/a{i}.mp3"
            qd = await tts(spoken_q, qa, use_tts, provider=tts_provider)
            ad = await tts(spoken_a, aa, use_tts, provider=tts_provider)

            base = frame_question(q, i, n, exam_name)
            qp = f"{tmp}/q{i}.png"; base.save(qp)
            parts = [(qp, qd + 0.6, qa)]
            for s in range(THINK_SECS, 0, -1):
                cp = f"{tmp}/c{i}_{s}.png"; frame_countdown(base, s).save(cp)
                parts.append((cp, 1.0, None))
            ap = f"{tmp}/a{i}.png"; frame_answer(q, i, n, exam_name).save(ap)
            parts.append((ap, ad + 1.2, aa))

            seg = f"{tmp}/s{i:03d}.mp4"; _encode(parts, seg, bg_offset=t); segs.append(seg)
            label = f"Q{i}" + (f" — {q['module_title'][:40]}" if q.get("module_title") else "")
            chapters.append((t, label))
            t += sum(x[1] for x in parts)

        # outro
        p = f"{tmp}/outro.png"; frame_outro(exam, exam_name).save(p)
        a = f"{tmp}/outro.mp3"
        a_dur = await tts("How many did you get right? Tell us your score in the comments, "
                          "and try the free full practice test on MedMind. Good luck on your exam!",
                          a, use_tts, provider=tts_provider)
        seg = f"{tmp}/s999.mp4"; _encode([(p, max(OUTRO_SECS, a_dur + 1), a)], seg, bg_offset=t); segs.append(seg)
        chapters.append((t, "Your score & free practice test"))

        lst = f"{tmp}/list.txt"
        Path(lst).write_text("".join(f"file '{s}'\n" for s in segs))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", lst, "-c", "copy", "-movflags", "+faststart", out_path], check=True)
    return chapters


def make_meta(questions: list[dict], exam: str | None, topic: str | None,
              chapters: list[tuple[float, str]]) -> tuple[str, str, list[str]]:
    exam_name = EXAMS[exam][0] if exam else "Gulf"
    n = len(questions)
    topic_part = f" | {topic.title()}" if topic else ""
    title = f"{n} {exam_name} Nursing Exam Practice Questions with Rationales{topic_part}"[:100]
    link = f"https://medmind.pro/exams/{exam}" if exam else "https://medmind.pro/exams/gulf"
    chap = "\n".join(f"{_fmt_ts(s)} {label}" for s, label in chapters)
    desc = (
        f"{n} practice questions for the {exam_name} nursing licensing exam (Prometric format), "
        f"each with a {THINK_SECS}-second timer and a short rationale. Pause any time, "
        f"keep score, and share it in the comments.\n\n"
        f"📝 Free practice test: {link}\n\n"
        f"Chapters:\n{chap}\n\n"
        f"Original practice questions written to the official exam blueprint — not actual exam items. "
        f"For exam preparation and education only; not medical advice. Always follow your local "
        f"protocols and current guidelines. Narration: AI-generated voice.\n\n"
        f"#PrometricExam #NursingExam #GulfNurse #MedMindAI"
    )
    tags = BASE_TAGS + (EXAMS[exam][1] if exam else []) + ([topic.lower()] if topic else [])
    return title, desc, tags


def upload(mp4: str, title: str, desc: str, tags: list[str], public: bool) -> str | None:
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
    body = {"snippet": {"title": title, "description": desc[:4900], "tags": tags[:30],
                        "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": "public" if public else "private",
                       "selfDeclaredMadeForKids": False}}
    media = googleapiclient.http.MediaFileUpload(mp4, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp.get("id")


# ── CLI ───────────────────────────────────────────────────────────────────────

async def main():
    ap = argparse.ArgumentParser(description="Long-form exam practice session video")
    ap.add_argument("--exam", choices=sorted(EXAMS), default=None)
    ap.add_argument("--topic", default=None, help="filter by module title, e.g. pharmacology")
    ap.add_argument("--count", type=int, default=25)
    ap.add_argument("--out", default=None)
    ap.add_argument("--upload", action="store_true", help="upload to YouTube (private by default)")
    ap.add_argument("--public", action="store_true", help="upload as public (reviewed sets only)")
    ap.add_argument("--allow-reuse", action="store_true", help="allow questions from earlier sessions")
    ap.add_argument("--no-tts", action="store_true", help="silent audio (layout test)")
    ap.add_argument("--demo", action="store_true", help="3 built-in questions, no database")
    ap.add_argument("--tts-provider", choices=["edge", "openai"], default="edge",
                    help="edge = free EmmaNeural (default) | openai = tts-1-hd (requires OPENAI_API_KEY)")
    ap.add_argument("--voice", default=None,
                    help="Override edge-tts voice, e.g. en-US-AvaNeural (edge only)")
    ap.add_argument("--bg", default="auto",
                    help="animated background: aurora|ecg|molecules|cells|auto (per exam)|random|none")
    a = ap.parse_args()
    if a.voice:
        global VOICE
        VOICE = a.voice
    if a.bg != "none":
        global BG_PATH
        from video_backgrounds import bg_loop, pick_theme, THEMES
        theme = (a.bg if a.bg in THEMES else
                 pick_theme(None) if a.bg == "random" else pick_theme(f"{a.exam}-{a.topic}"))
        print(f"🎨 Background: {theme}")
        BG_PATH = bg_loop(theme, W, H, secs=BG_LOOP_SECS)

    if not shutil.which("ffmpeg"):
        sys.exit("[error] ffmpeg not found")

    qs = DEMO_QUESTIONS if a.demo else fetch_questions(a.exam, a.topic, a.count, a.allow_reuse)
    if len(qs) < 3:
        sys.exit(f"[error] only {len(qs)} matching questions (exam={a.exam}, topic={a.topic}) — need ≥3")
    if not a.demo and len(qs) < a.count:
        print(f"⚠ only {len(qs)} questions available, making a {len(qs)}-question session")

    out = a.out or f"/tmp/practice_{a.exam or 'gulf'}_{a.topic or 'mixed'}_{len(qs)}q.mp4".replace(" ", "_")
    print(f"🎬 Rendering {len(qs)} questions → {out}")
    chapters = await build_session(qs, a.exam, a.topic, out, use_tts=not a.no_tts,
                                    tts_provider=a.tts_provider)
    title, desc, tags = make_meta(qs, a.exam, a.topic, chapters)
    Path(out).with_suffix(".txt").write_text(f"{title}\n\n{desc}\n\nTAGS: {', '.join(tags)}\n")
    print(f"✅ Video: {out} ({_fmt_ts(_ffprobe_dur(out))})\n   Title: {title}\n   Meta:  {Path(out).with_suffix('.txt')}")

    if a.upload and not a.demo:
        vid = upload(out, title, desc, tags, a.public)
        if not vid:
            sys.exit("[error] upload failed")
        print(f"📤 Uploaded ({'public' if a.public else 'PRIVATE — review, then publish'}): https://youtu.be/{vid}")
        tr = _load_tracking()
        tr["sessions"].append({"yt_id": vid, "exam": a.exam, "topic": a.topic,
                               "question_ids": [q["id"] for q in qs]})
        TRACKING.write_text(json.dumps(tr, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
