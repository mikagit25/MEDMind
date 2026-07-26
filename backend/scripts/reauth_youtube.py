#!/usr/bin/env python3
"""
Re-authorize YouTube OAuth tokens for MedMind channels via Telegram link.

Flow (no copy-paste needed):
  1. Script builds OAuth URL with redirect_uri → medmind.pro/api/v1/auth/youtube/callback
  2. Sends clickable link to Telegram
  3. Admin taps the link → Google consent screen → clicks Allow
  4. Google redirects to the backend callback → token saved automatically
  5. Done — no terminal paste, no localhost tricks

Usage:
    python3 backend/scripts/reauth_youtube.py             # EN channel (account1)
    python3 backend/scripts/reauth_youtube.py --account2  # ES channel
    python3 backend/scripts/reauth_youtube.py --ar        # AR channel
    python3 backend/scripts/reauth_youtube.py --all       # All three channels
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

MEDMIND_DIR  = Path("/opt/medmind")
BOT_TOKEN    = "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
CHAT_ID      = "209381269"
CALLBACK_URL = "https://medmind.pro/api/v1/auth/youtube/callback"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CHANNEL_CFG = {
    "en": {
        "name":    "MedMind EN 🇬🇧",
        "state":   "en",
        "secret":  MEDMIND_DIR / "client_secret_web.json",
        "account": "Google аккаунт EN канала",
    },
    "es": {
        "name":    "MedMind ES 🇪🇸",
        "state":   "es",
        "secret":  MEDMIND_DIR / "client_secret_account2_web.json",
        "account": "Google аккаунт ES канала (account2)",
    },
    "ar": {
        "name":    "MedMind AR 🇸🇦",
        "state":   "ar",
        "secret":  MEDMIND_DIR / "client_secret_account3_web.json",
        "account": "Google аккаунт AR канала (account3)",
    },
}


def send_telegram(text: str) -> bool:
    try:
        payload = json.dumps({
            "chat_id":                  CHAT_ID,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": False,
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("ok", False)
    except Exception as e:
        print(f"  Telegram error: {e}")
        return False


def build_auth_url(client_id: str, state: str) -> str:
    params = {
        "client_id":     client_id,
        "redirect_uri":  CALLBACK_URL,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",   # force new refresh_token
        "state":         state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def reauth_channel(key: str) -> None:
    cfg = CHANNEL_CFG[key]
    secret_path = cfg["secret"]

    if not secret_path.exists():
        print(f"❌ Client secret not found: {secret_path}")
        return

    with open(secret_path) as f:
        raw = json.load(f)
    creds = raw.get("web") or raw.get("installed") or {}
    client_id = creds.get("client_id")
    if not client_id:
        print(f"❌ client_id not found in {secret_path}")
        return

    auth_url = build_auth_url(client_id, cfg["state"])

    print(f"\n{'='*60}")
    print(f"  Reauth: {cfg['name']}")
    print(f"{'='*60}")
    print(f"\nAuth URL:\n{auth_url}\n")

    msg = (
        f"🔑 <b>YouTube токен истекает — {cfg['name']}</b>\n\n"
        f"Войди в <b>{cfg['account']}</b> и нажми:\n\n"
        f'<a href="{auth_url}">👉 Авторизовать {cfg["name"]}</a>\n\n'
        f"После нажатия «Разрешить» токен сохранится автоматически.\n"
        f"Страница покажет ✅ — можно закрыть вкладку."
    )

    ok = send_telegram(msg)
    if ok:
        print(f"✅ Ссылка отправлена в Telegram для {cfg['name']}")
    else:
        print(f"❌ Telegram не ответил — открой ссылку вручную выше")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-authorize YouTube OAuth via Telegram link")
    parser.add_argument("--account2", "--es", action="store_true", help="ES channel (account2)")
    parser.add_argument("--ar",       "--account3", action="store_true", help="AR channel (account3)")
    parser.add_argument("--all",      action="store_true", help="All three channels")
    args = parser.parse_args()

    if args.all:
        for key in ("en", "es", "ar"):
            reauth_channel(key)
    elif args.account2:
        reauth_channel("es")
    elif args.ar:
        reauth_channel("ar")
    else:
        reauth_channel("en")


if __name__ == "__main__":
    main()
