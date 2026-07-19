#!/usr/bin/env python3
"""
MedMind uptime monitor — checks /health on frontend and backend every 5 minutes.
Sends Telegram alert if any endpoint is down.

Cron (add via: crontab -e):
    */5 * * * * /usr/bin/python3 /opt/medmind/scripts/ops/uptime_check.py >> /var/log/medmind_uptime.log 2>&1

Required env vars (read from /opt/medmind/backend/.env):
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""
import os
import sys
import time
import datetime
import urllib.request
import urllib.error

# ── Config ─────────────────────────────────────────────────────────────────────

# Load .env from backend if available
ENV_FILE = "/opt/medmind/backend/.env"
if os.path.exists(ENV_FILE):
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

ENDPOINTS = [
    {"name": "Backend /health",  "url": "http://localhost:8000/health"},
    {"name": "Frontend /",       "url": "http://localhost:3000"},
]

TIMEOUT = 10
STATE_FILE = "/tmp/medmind_uptime_state.txt"


# ── Helpers ────────────────────────────────────────────────────────────────────

def check(url: str) -> tuple[bool, int | None, str]:
    """Returns (ok, status_code, error_msg)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MedMind-Uptime/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return True, r.status, ""
    except urllib.error.HTTPError as e:
        return False, e.code, str(e)
    except Exception as e:
        return False, None, str(e)


def send_telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[uptime] Telegram not configured, would send: {msg}", flush=True)
        return
    import json
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}).encode()
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[uptime] Telegram send failed: {e}", flush=True)


def load_state() -> dict:
    """Load previous down-state (endpoint name → was_down bool)."""
    state: dict = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                state[k] = v == "1"
    return state


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        for k, v in state.items():
            f.write(f"{k}={'1' if v else '0'}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prev_state = load_state()
    new_state: dict = {}

    for ep in ENDPOINTS:
        name = ep["name"]
        url = ep["url"]
        ok, code, err = check(url)
        was_down = prev_state.get(name, False)
        new_state[name] = not ok

        status_label = f"{code}" if code else "timeout/error"
        print(f"[{now}] {name} — {'OK' if ok else 'DOWN'} ({status_label}) {err}", flush=True)

        if not ok and not was_down:
            # Transition: up → down
            send_telegram(
                f"🔴 <b>MedMind DOWN</b>\n"
                f"Endpoint: {name}\n"
                f"URL: {url}\n"
                f"Status: {status_label}\n"
                f"Error: {err or '—'}\n"
                f"Time: {now}"
            )
        elif ok and was_down:
            # Transition: down → up
            send_telegram(
                f"🟢 <b>MedMind RECOVERED</b>\n"
                f"Endpoint: {name}\n"
                f"URL: {url}\n"
                f"Time: {now}"
            )

    save_state(new_state)
    any_down = any(new_state.values())
    sys.exit(1 if any_down else 0)


if __name__ == "__main__":
    main()
