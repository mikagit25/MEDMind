#!/usr/bin/env python3
"""
MedMind AI — NCLEX Question → YouTube Shorts

Pipeline per question:
  1. Load MCQQuestion with key_takeaway from DB
  2. Render 5 visual segments (1080×1920 9:16)
       [Hook] → [Question + Options] → [Pause] → [Answer Reveal] → [CTA]
  3. Edge TTS narrates question (segment 2) + answer+takeaway (segment 4)
  4. moviepy assembles → MP4
  5. Caller uploads to YouTube as Short

Usage:
    python3 nclex_to_shorts.py --question-id UUID [--out /tmp/output.mp4] [--dry-run]
    python3 nclex_to_shorts.py --list   # print available question IDs
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────

W, H   = 1080, 1920   # 9:16 vertical
FPS    = 24
VOICE  = "en-US-JennyNeural"   # warm, clear voice for nursing content
RATE   = "-5%"                  # slightly slower for comprehension

# Brand palette
BG_DARK  = (10,  14,  20)
BG_CARD  = (18,  26,  38)
ACCENT   = (99,  179, 237)      # sky blue
PINK     = (236, 72,  153)      # nursing pink (CTA / hook)
GREEN    = (52,  211, 153)      # correct answer
RED_DIM  = (80,  40,  40)       # wrong answer background (dimmed)
AMBER    = (251, 191, 36)       # key takeaway
TEXT_W   = (230, 237, 243)
TEXT_M   = (148, 163, 184)
GOLD     = (251, 191, 36)

DB_URL = "postgresql://medmind:medmind_secret@localhost:5432/medmind"

TRACKING_FILE = Path(os.environ.get(
    "YT_NCLEX_TRACKING", "/opt/medmind/youtube_shorts_nclex_uploaded.json"
))

# ── Font helpers ───────────────────────────────────────────────────────────────

_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_REG_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fb(s): return _font(_BOLD_PATHS, s)
def fr(s): return _font(_REG_PATHS,  s)


def tw(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)[2]


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if tw(draw, test, font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ── DB helpers ────────────────────────────────────────────────────────────────

def _db_conn():
    import psycopg2, psycopg2.extras
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def load_question(question_id: str) -> dict | None:
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.id, q.question, q.options, q.correct, q.explanation,
                   q.key_takeaway, q.test_taking_tip, q.difficulty,
                   q.nclex_client_needs, m.title AS module_title
            FROM mcq_questions q
            LEFT JOIN modules m ON m.id = q.module_id
            WHERE q.id = %s AND q.key_takeaway IS NOT NULL
            """,
            (question_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_available_questions(limit: int = 20) -> list[dict]:
    """Return questions with key_takeaway not yet uploaded."""
    uploaded = _load_tracking()
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT q.id::text, q.question, q.difficulty, m.title AS module_title
            FROM mcq_questions q
            LEFT JOIN modules m ON m.id = q.module_id
            WHERE q.key_takeaway IS NOT NULL
              AND q.question_type = 'mcq'
              AND (
                  q.exam_slugs IS NOT NULL
                  OR m.code LIKE 'NURSE-%%'
              )
              AND q.question ~ '^[A-Za-z]'
            ORDER BY q.created_at ASC
            LIMIT %s
            """,
            (limit * 3,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return [r for r in rows if r["id"] not in uploaded][:limit]


# ── Tracking ──────────────────────────────────────────────────────────────────

def _load_tracking() -> set[str]:
    if TRACKING_FILE.exists():
        try:
            data = json.loads(TRACKING_FILE.read_text())
            return set(data.get("uploaded", []))
        except Exception:
            pass
    return set()


def _save_tracking(question_id: str, yt_id: str | None = None):
    data: dict[str, Any] = {"uploaded": [], "details": {}}
    if TRACKING_FILE.exists():
        try:
            data = json.loads(TRACKING_FILE.read_text())
        except Exception:
            pass
    uploaded = list(data.get("uploaded", []))
    if question_id not in uploaded:
        uploaded.append(question_id)
    data["uploaded"] = uploaded
    if yt_id:
        data.setdefault("details", {})[question_id] = {"yt_id": yt_id}
    TRACKING_FILE.write_text(json.dumps(data, indent=2))


# ── Frame renderers ───────────────────────────────────────────────────────────

def _base_canvas(title_bar: str | None = None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)
    # Top accent strip
    draw.rectangle([0, 0, W, 6], fill=PINK)
    # Logo
    draw.text((32, 22), "MedMind", font=fb(30), fill=TEXT_W)
    bb = draw.textbbox((32, 22), "MedMind", font=fb(30))
    draw.text((bb[2] + 6, 22), "AI", font=fb(30), fill=ACCENT)
    # Badge
    if title_bar:
        badge_font = fb(20)
        bw = tw(draw, title_bar, badge_font) + 24
        bx = W - bw - 20
        draw.rounded_rectangle([bx, 16, W - 20, 52], radius=10, fill=PINK)
        draw.text((bx + 12, 16), title_bar, font=badge_font, fill=(255, 255, 255))
    return img, draw


def render_hook(module_title: str, difficulty: str) -> np.ndarray:
    img, draw = _base_canvas("NCLEX")

    # Central hook text
    cy = H // 2 - 80
    lines = [
        "Can you answer",
        "this NCLEX",
        "question?",
    ]
    f_big = fb(88)
    for i, line in enumerate(lines):
        lw = tw(draw, line, f_big)
        draw.text(((W - lw) // 2, cy + i * 100), line, font=f_big, fill=TEXT_W)

    # Difficulty pill
    diff_colors = {"easy": (52, 211, 153), "medium": AMBER, "hard": (239, 68, 68)}
    dc = diff_colors.get(difficulty.lower(), AMBER)
    diff_text = difficulty.upper()
    dw = tw(draw, diff_text, fb(26)) + 30
    dx = (W - dw) // 2
    dy = cy + len(lines) * 100 + 30
    draw.rounded_rectangle([dx, dy, dx + dw, dy + 44], radius=14, fill=dc)
    draw.text((dx + 15, dy + 8), diff_text, font=fb(26), fill=BG_DARK)

    # Module hint
    if module_title:
        mt = module_title[:50]
        mw = tw(draw, mt, fr(28))
        draw.text(((W - mw) // 2, dy + 70), mt, font=fr(28), fill=TEXT_M)

    # Swipe hint
    sh = "👆 Swipe up for more"
    sw = tw(draw, sh, fr(28))
    draw.text(((W - sw) // 2, H - 80), sh, font=fr(28), fill=TEXT_M)

    return np.array(img)


def render_question(question: str, options: dict) -> np.ndarray:
    img, draw = _base_canvas("NCLEX")

    # Question box
    PAD = 40
    BOX_Y = 80
    BOX_H = 560
    draw.rounded_rectangle([PAD, BOX_Y, W - PAD, BOX_Y + BOX_H], radius=20, fill=BG_CARD)

    # Question text
    f_q = fb(34)
    max_w = W - PAD * 2 - 40
    lines = wrap(draw, question, f_q, max_w)
    y = BOX_Y + 30
    for line in lines[:8]:
        draw.text((PAD + 20, y), line, font=f_q, fill=TEXT_W)
        y += 46

    # Options
    OPT_Y = BOX_Y + BOX_H + 30
    f_letter = fb(36)
    f_opt = fr(30)
    LETTER_COLORS = {
        "A": (99, 179, 237),
        "B": (167, 139, 250),
        "C": (52, 211, 153),
        "D": (251, 191, 36),
    }

    for i, letter in enumerate(["A", "B", "C", "D"]):
        text = options.get(letter, "")
        if not text:
            continue

        oy = OPT_Y + i * 190
        col = LETTER_COLORS.get(letter, ACCENT)

        # Option card
        draw.rounded_rectangle([PAD, oy, W - PAD, oy + 170], radius=16, fill=BG_CARD)

        # Letter circle
        cx, cy = PAD + 46, oy + 85
        draw.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], fill=col)
        lw = tw(draw, letter, f_letter)
        draw.text((cx - lw // 2, cy - 22), letter, font=f_letter, fill=BG_DARK)

        # Option text
        opt_lines = wrap(draw, text, f_opt, W - PAD * 2 - 110)
        ty = oy + (170 - len(opt_lines[:3]) * 38) // 2
        for ol in opt_lines[:3]:
            draw.text((PAD + 96, ty), ol, font=f_opt, fill=TEXT_W)
            ty += 38

    return np.array(img)


def render_pause() -> np.ndarray:
    img, draw = _base_canvas("NCLEX")

    cy = H // 2
    lines = ["What's your", "answer?"]
    f_big = fb(100)
    for i, line in enumerate(lines):
        lw = tw(draw, line, f_big)
        draw.text(((W - lw) // 2, cy - 120 + i * 115), line, font=f_big, fill=TEXT_W)

    # Thinking dots
    dot_text = "💭 Think carefully..."
    dw = tw(draw, dot_text, fb(38))
    draw.text(((W - dw) // 2, cy + 140), dot_text, font=fb(38), fill=TEXT_M)

    # Comment CTA
    cta = "⬇ Comment your answer!"
    cw = tw(draw, cta, fb(34))
    draw.text(((W - cw) // 2, cy + 220), cta, font=fb(34), fill=PINK)

    return np.array(img)


def render_reveal(options: dict, correct: str, key_takeaway: str) -> np.ndarray:
    img, draw = _base_canvas("Answer")

    # Correct answer banner
    draw.rounded_rectangle([30, 80, W - 30, 195], radius=18, fill=GREEN)
    banner = f"✓  Correct Answer: {correct}"
    bw = tw(draw, banner, fb(44))
    draw.text(((W - bw) // 2, 112), banner, font=fb(44), fill=BG_DARK)

    # All options
    OPT_Y = 220
    f_letter = fb(34)
    f_opt = fr(28)

    for i, letter in enumerate(["A", "B", "C", "D"]):
        text = options.get(letter, "")
        if not text:
            continue

        oy = OPT_Y + i * 155
        is_correct = letter == correct

        bg_col = (20, 60, 40) if is_correct else (25, 30, 42)
        border  = GREEN       if is_correct else (50, 60, 75)
        lc      = GREEN       if is_correct else TEXT_M
        tc      = TEXT_W      if is_correct else TEXT_M

        draw.rounded_rectangle([30, oy, W - 30, oy + 138], radius=14,
                               fill=bg_col, outline=border, width=2)

        # Letter circle
        cx, cy2 = 30 + 42, oy + 69
        draw.ellipse([cx - 28, cy2 - 28, cx + 28, cy2 + 28], fill=lc)
        lw = tw(draw, letter, f_letter)
        draw.text((cx - lw // 2, cy2 - 20), letter, font=f_letter,
                  fill=BG_DARK if is_correct else BG_DARK)

        opt_lines = wrap(draw, text, f_opt, W - 30 - 90)
        ty = oy + (138 - len(opt_lines[:3]) * 34) // 2
        for ol in opt_lines[:3]:
            draw.text((90, ty), ol, font=f_opt, fill=tc)
            ty += 34

    # Key takeaway box
    KT_Y = OPT_Y + 4 * 155 + 20
    kt_lines = wrap(draw, key_takeaway, fb(30), W - 100)
    KT_H = 40 + len(kt_lines[:4]) * 40 + 20
    draw.rounded_rectangle([30, KT_Y, W - 30, KT_Y + KT_H], radius=16,
                           fill=(40, 32, 10), outline=AMBER, width=2)
    draw.text((60, KT_Y + 14), "💡 Key Takeaway", font=fb(28), fill=AMBER)
    ty = KT_Y + 52
    for line in kt_lines[:4]:
        draw.text((60, ty), line, font=fr(28), fill=(251, 229, 163))
        ty += 38

    return np.array(img)


def render_cta() -> np.ndarray:
    img, draw = _base_canvas()

    cy = H // 2 - 100
    draw.text(((W - tw(draw, "🎓", fb(120))) // 2, cy - 60), "🎓",
              font=fb(120), fill=PINK)

    lines = ["Practice 1,000+", "NCLEX questions", "for FREE"]
    f_big = fb(72)
    for i, line in enumerate(lines):
        lw = tw(draw, line, f_big)
        col = PINK if i == 2 else TEXT_W
        draw.text(((W - lw) // 2, cy + 80 + i * 84), line, font=f_big, fill=col)

    url = "medmind.pro/nclex"
    uw = tw(draw, url, fb(42))
    draw.text(((W - uw) // 2, cy + 380), url, font=fb(42), fill=ACCENT)

    # Underline
    draw.line([(W // 2 - uw // 2, cy + 428), (W // 2 + uw // 2, cy + 428)],
              fill=ACCENT, width=3)

    return np.array(img)


# ── TTS ───────────────────────────────────────────────────────────────────────

async def tts(text: str, path: str) -> float:
    try:
        import edge_tts
    except ImportError:
        print("[error] edge-tts not installed: pip install edge-tts")
        sys.exit(1)
    comm = edge_tts.Communicate(text[:1200], VOICE, rate=RATE)
    await comm.save(path)
    try:
        from moviepy.editor import AudioFileClip as _AFC
        with _AFC(path) as a:
            return max(2.0, a.duration)
    except Exception:
        return max(8.0, len(text.split()) / 140 * 60)


# ── Video assembly ────────────────────────────────────────────────────────────

async def build_video(q: dict, out_path: str, dry_run: bool = False) -> str:
    """Render full NCLEX Short. Returns path to MP4."""
    from moviepy.editor import (
        ImageClip, AudioFileClip, CompositeAudioClip, concatenate_videoclips,
    )

    question  = q["question"]
    options   = q["options"] if isinstance(q["options"], dict) else json.loads(q["options"])
    correct   = q["correct"]
    takeaway  = q["key_takeaway"]
    module    = (q.get("module_title") or "NCLEX Prep")[:48]
    diff      = q.get("difficulty", "medium")
    expl      = q.get("explanation") or ""

    # TTS scripts
    spoken_q = (
        f"Here is your NCLEX question. {question} "
        f"Option A: {options.get('A', '')}. "
        f"Option B: {options.get('B', '')}. "
        f"Option C: {options.get('C', '')}. "
        f"Option D: {options.get('D', '')}."
    )
    spoken_a = (
        f"The correct answer is {correct}. {options.get(correct, '')}. "
        f"{takeaway}"
    )

    print(f"  → Rendering frames…")
    frames = {
        "hook":     render_hook(module, diff),
        "question": render_question(question, options),
        "pause":    render_pause(),
        "reveal":   render_reveal(options, correct, takeaway),
        "cta":      render_cta(),
    }

    if dry_run:
        print(f"  [dry-run] skipping TTS + moviepy assembly")
        return out_path

    with tempfile.TemporaryDirectory() as tmp:
        q_mp3 = f"{tmp}/question.mp3"
        a_mp3 = f"{tmp}/answer.mp3"

        print(f"  → TTS question…")
        q_dur = await tts(spoken_q, q_mp3)
        print(f"  → TTS answer…")
        a_dur = await tts(spoken_a, a_mp3)

        HOOK_DUR  = 3.0
        PAUSE_DUR = 4.0
        CTA_DUR   = 5.0

        hook_clip = ImageClip(frames["hook"]).set_duration(HOOK_DUR)
        q_clip    = ImageClip(frames["question"]).set_duration(q_dur + 1.0)
        pause_clip = ImageClip(frames["pause"]).set_duration(PAUSE_DUR)
        rev_clip  = ImageClip(frames["reveal"]).set_duration(a_dur + 1.5)
        cta_clip  = ImageClip(frames["cta"]).set_duration(CTA_DUR)

        q_audio = AudioFileClip(q_mp3)
        a_audio = AudioFileClip(a_mp3)

        q_start   = HOOK_DUR
        a_start   = HOOK_DUR + q_dur + 1.0 + PAUSE_DUR

        q_audio   = q_audio.set_start(q_start)
        a_audio   = a_audio.set_start(a_start)

        audio_mix = CompositeAudioClip([q_audio, a_audio])

        final = concatenate_videoclips(
            [hook_clip, q_clip, pause_clip, rev_clip, cta_clip], method="compose"
        ).set_audio(audio_mix)

        print(f"  → Writing MP4 ({final.duration:.1f}s)…")
        final.write_videofile(
            out_path,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            logger=None,
        )
        final.close()
        q_audio.close()
        a_audio.close()

    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

async def _main():
    parser = argparse.ArgumentParser(description="NCLEX Question → YouTube Short")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--question-id", help="UUID of MCQQuestion to render")
    g.add_argument("--list", action="store_true", help="List available question IDs")
    parser.add_argument("--out", default=None, help="Output MP4 path")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list:
        questions = list_available_questions(20)
        print(f"{'ID':<40} {'Difficulty':<10} {'Module'}")
        print("-" * 90)
        for q in questions:
            print(f"{q['id']:<40} {q['difficulty']:<10} {q['module_title'] or 'N/A'}")
        return

    q = load_question(args.question_id)
    if not q:
        print(f"[error] Question {args.question_id} not found or has no key_takeaway")
        sys.exit(1)

    out = args.out or f"/tmp/nclex_short_{args.question_id[:8]}.mp4"
    print(f"  Building Short for: {q['question'][:60]}…")
    await build_video(q, out, dry_run=args.dry_run)
    print(f"  ✅ Output: {out}")


if __name__ == "__main__":
    asyncio.run(_main())
