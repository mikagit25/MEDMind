#!/usr/bin/env python3
"""
MedMind AI — animated, seamlessly looping backgrounds for Shorts and practice videos.

Pure code (numpy + PIL + ffmpeg), no stock footage, no AI images, no licences.
Every motion is periodic over the loop length, so the loop has no visible seam and
can play under a video of any length (ffmpeg -stream_loop -1).

Themes (all calm, mid-dark, so white text and cards stay readable):
  aurora     slowly breathing teal → indigo gradient with drifting soft light blobs
  ecg        deep blue gradient with a faint heartbeat trace sweeping across
  molecules  slow floating molecule network (nodes + bonds), teal on navy
  cells      soft "microscope" cells drifting, purple → teal tint

Usage:
    from video_backgrounds import bg_loop, pick_theme
    path = bg_loop("ecg", 1920, 1080)          # cached MP4, rendered once per theme/size
    python3 video_backgrounds.py --theme all --w 1920 --h 1080 --preview /tmp/bg   # look at them
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

THEMES = ("aurora", "ecg", "molecules", "cells")
CACHE_DIR = Path(os.environ.get("MEDMIND_BG_CACHE", "/opt/medmind/bg_cache"))
LOOP_SECS = 12
FPS = 24
SCALE = 2          # render at 1/SCALE resolution, ffmpeg upscales (soft visuals → no visible loss)
VERSION = "v2"     # bump to invalidate the cache after changing a theme


def pick_theme(key: str | None = None) -> str:
    """Deterministic theme per key (e.g. question id or exam), random if key is None."""
    if key is None:
        return random.choice(THEMES)
    return THEMES[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(THEMES)]


# ── helpers ───────────────────────────────────────────────────────────────────

def _lerp(a, b, t):
    return a + (b - a) * t


def _gradient(w, h, c1, c2, angle):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (xx / w) * math.cos(angle) + (yy / h) * math.sin(angle)
    t = (t - t.min()) / (t.max() - t.min() + 1e-6)
    return _lerp(np.array(c1, np.float32), np.array(c2, np.float32), t[..., None])


def _blob(img, cx, cy, r, color, strength):
    h, w, _ = img.shape
    yy, xx = np.ogrid[0:h, 0:w]
    g = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))).astype(np.float32)
    img += g[..., None] * np.array(color, np.float32) * strength


def _vignette(img):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - 0.35 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return img * np.clip(v, 0.55, 1)[..., None]


# ── themes: frame(i, n, w, h, rng_state) → uint8 HxWx3 ──────────────────────────

def _aurora(i, n, w, h, P):
    ph = 2 * math.pi * i / n
    c1 = (_lerp(6, 14, 0.5 + 0.5 * math.sin(ph)), 40, 58)
    c2 = (36, _lerp(22, 34, 0.5 + 0.5 * math.cos(ph)), 74)
    img = _gradient(w, h, c1, c2, 0.6 + 0.15 * math.sin(ph))
    for (fx, fy, px, py, r, col) in P["blobs"]:
        cx = w * (0.5 + 0.38 * math.sin(fx * ph + px))
        cy = h * (0.5 + 0.38 * math.sin(fy * ph + py))
        _blob(img, cx, cy, r * min(w, h), col, 0.55)
    return np.clip(_vignette(img), 0, 255).astype(np.uint8)


def _ecg_wave(x):
    """One heartbeat on x∈[0,1): P wave, QRS spike, T wave."""
    p = 0.10 * math.exp(-((x - 0.20) / 0.035) ** 2)
    q = -0.12 * math.exp(-((x - 0.36) / 0.010) ** 2)
    r = 1.00 * math.exp(-((x - 0.40) / 0.012) ** 2)
    s = -0.25 * math.exp(-((x - 0.44) / 0.012) ** 2)
    t = 0.22 * math.exp(-((x - 0.65) / 0.060) ** 2)
    return p + q + r + s + t


def _ecg(i, n, w, h, P):
    ph = 2 * math.pi * i / n
    img = _gradient(w, h, (8, 22, 48), (14, 46, 70), 0.9 + 0.1 * math.sin(ph))
    _blob(img, w * 0.8, h * 0.2, 0.45 * min(w, h), (40, 90, 120), 0.35)
    base = Image.fromarray(np.clip(_vignette(img), 0, 255).astype(np.uint8))
    beats = 3                                   # beats across the screen
    head = (i / n) * w                          # sweep position, one sweep per loop
    pts = []
    for x in range(0, w, 2):
        # low in the frame and modest height, so it never runs through centred text
        y = h * 0.86 - _ecg_wave(((x / w) * beats) % 1) * h * 0.12
        pts.append((x, y))
    trace = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(trace)
    for k in range(len(pts) - 1):
        x = pts[k][0]
        # brightness: strongest just behind the sweep head, fading over half a screen
        age = (head - x) % w
        a = int(110 * max(0.0, 1 - age / (w * 0.55)))
        if a > 6:
            d.line([pts[k], pts[k + 1]], fill=(110, 231, 183, a), width=max(2, w // 480))
    glow = trace.filter(ImageFilter.GaussianBlur(4))
    base = Image.alpha_composite(base.convert("RGBA"), glow)
    base = Image.alpha_composite(base, trace)
    return np.array(base.convert("RGB"))


def _molecules(i, n, w, h, P):
    ph = 2 * math.pi * i / n
    img = _gradient(w, h, (10, 20, 44), (8, 44, 60), 0.4 + 0.1 * math.sin(ph))
    base = Image.fromarray(np.clip(_vignette(img), 0, 255).astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    nodes = []
    for (bx, by, ax, ay, fx, fy, px, py, r) in P["nodes"]:
        nodes.append((w * (bx + ax * math.sin(fx * ph + px)),
                      h * (by + ay * math.sin(fy * ph + py)), r))
    lim = min(w, h) * 0.28
    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            dx, dy = nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1]
            dist = math.hypot(dx, dy)
            if dist < lim:
                al = int(90 * (1 - dist / lim))
                d.line([nodes[a][:2], nodes[b][:2]], fill=(94, 234, 212, al), width=max(1, w // 640))
    for (x, y, r) in nodes:
        rr = r * min(w, h)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(94, 234, 212, 110))
    layer = Image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.2)), layer)
    return np.array(Image.alpha_composite(base, layer).convert("RGB"))


def _cells(i, n, w, h, P):
    ph = 2 * math.pi * i / n
    img = _gradient(w, h, (30, 18, 58), (10, 42, 58), 1.1 + 0.12 * math.sin(ph))
    base = Image.fromarray(np.clip(_vignette(img), 0, 255).astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (bx, by, ax, ay, fx, fy, px, py, r, col) in P["cells"]:
        x = w * (bx + ax * math.sin(fx * ph + px))
        y = h * (by + ay * math.sin(fy * ph + py))
        rr = r * min(w, h) * (1 + 0.06 * math.sin(2 * ph + px))   # gentle "breathing"
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col + (38,), outline=col + (90,),
                  width=max(2, w // 400))
        nr = rr * 0.32
        d.ellipse([x - nr + rr * 0.15, y - nr, x + nr + rr * 0.15, y + nr], fill=col + (60,))
    layer = layer.filter(ImageFilter.GaussianBlur(max(1, w // 300)))
    return np.array(Image.alpha_composite(base, layer).convert("RGB"))


def _params(theme: str, seed: int) -> dict:
    """Random layout, but integer frequencies so every path closes over the loop."""
    r = random.Random(seed)
    if theme == "aurora":
        cols = [(40, 160, 170), (90, 80, 200), (60, 140, 220), (150, 70, 170)]
        return {"blobs": [(r.choice([1, 2]), r.choice([1, 2, 3]), r.uniform(0, 6.3), r.uniform(0, 6.3),
                           r.uniform(0.18, 0.32), r.choice(cols)) for _ in range(5)]}
    if theme == "molecules":
        return {"nodes": [(r.uniform(0.05, 0.95), r.uniform(0.05, 0.95), r.uniform(0.02, 0.06),
                           r.uniform(0.02, 0.06), r.choice([1, 2]), r.choice([1, 2]),
                           r.uniform(0, 6.3), r.uniform(0, 6.3), r.uniform(0.006, 0.012))
                          for _ in range(26)]}
    if theme == "cells":
        cols = [(167, 139, 250), (94, 234, 212), (125, 211, 252), (244, 114, 182)]
        return {"cells": [(r.uniform(0.08, 0.92), r.uniform(0.08, 0.92), r.uniform(0.03, 0.08),
                           r.uniform(0.03, 0.08), r.choice([1, 2]), r.choice([1, 2]),
                           r.uniform(0, 6.3), r.uniform(0, 6.3), r.uniform(0.05, 0.11), r.choice(cols))
                          for _ in range(11)]}
    return {}


_RENDER = {"aurora": _aurora, "ecg": _ecg, "molecules": _molecules, "cells": _cells}


# ── public ────────────────────────────────────────────────────────────────────

def bg_loop(theme: str, w: int, h: int, secs: int = LOOP_SECS, fps: int = FPS,
            seed: int = 7, cache_dir: Path | None = None) -> str:
    """Render (once) and return the path of a seamless looping MP4 background."""
    if theme not in _RENDER:
        raise ValueError(f"unknown theme {theme!r}; choose from {THEMES}")
    cache = Path(cache_dir or CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / f"bg_{theme}_{w}x{h}_{secs}s_{seed}_{VERSION}.mp4"
    if out.exists() and out.stat().st_size > 0:
        return str(out)
    lw, lh = w // SCALE, h // SCALE
    n = secs * fps
    P = _params(theme, seed)
    tmp = out.with_suffix(".part.mp4")
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{lw}x{lh}", "-r", str(fps), "-i", "-",
         "-vf", f"scale={w}:{h}:flags=bicubic", "-c:v", "libx264", "-preset", "medium",
         "-crf", "20", "-pix_fmt", "yuv420p", "-an", "-f", "mp4", str(tmp)],
        stdin=subprocess.PIPE)
    for i in range(n):
        proc.stdin.write(_RENDER[theme](i, n, lw, lh, P).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"ffmpeg failed rendering background {theme}")
    tmp.rename(out)
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Render / preview MedMind animated backgrounds")
    ap.add_argument("--theme", default="all", help=f"one of {THEMES} or 'all'")
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--preview", default=None, help="dir: also save a still frame per theme")
    a = ap.parse_args()
    for th in (THEMES if a.theme == "all" else [a.theme]):
        p = bg_loop(th, a.w, a.h)
        print(f"{th:10} → {p}")
        if a.preview:
            Path(a.preview).mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", p,
                            "-frames:v", "1", f"{a.preview}/{th}.png"], check=True)
