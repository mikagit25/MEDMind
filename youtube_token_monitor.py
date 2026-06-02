"""
YouTube Token Monitor — checks token expiry and sends Telegram alert.
Run daily via cron. If either token expires within 48h, sends auth URL to admin.

Cron: 0 8 * * * python3 /opt/medmind/youtube_token_monitor.py >> /opt/medmind/logs/yt_token_monitor.log 2>&1
"""
import json
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Config ────────────────────────────────────────────────────────────────────
CALLBACK_BASE = "https://medmind.pro/api/v1/auth/youtube/callback"
ALERT_HOURS   = 48          # send alert when token expires in < 48h
BOT_TOKEN     = "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
ADMIN_CHAT_ID = os.environ.get("TG_ADMIN_CHAT_ID", "")  # set in crontab

ACCOUNTS = {
    "en": {
        "label":       "🇬🇧 MedMind EN",
        "token_file":  "/opt/medmind/youtube_token.json",
        "secret_file": "/opt/medmind/client_secret_web.json",
    },
    "es": {
        "label":       "🇪🇸 MedMind ES",
        "token_file":  "/opt/medmind/youtube_token_account2.json",
        "secret_file": "/opt/medmind/client_secret_account2_web.json",
    },
    "ar": {
        "label":       "🇸🇦 MedMind AR",
        "token_file":  "/opt/medmind/youtube_token_ar.json",
        "secret_file": "/opt/medmind/client_secret_account3_web.json",
    },
}

YT_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload"
    " https://www.googleapis.com/auth/youtube"
    " https://www.googleapis.com/auth/youtube.force-ssl"
)


def token_expires_in(token_file: str) -> float | None:
    """Return seconds until refresh_token expiry, or None if unknown."""
    try:
        with open(token_file) as f:
            t = json.load(f)
        # refresh_token_expires_in is set at token creation time (relative)
        # We store the absolute expiry ourselves below when token is saved via callback
        abs_expiry = t.get("refresh_token_absolute_expiry")
        if abs_expiry:
            return float(abs_expiry) - time.time()
        # Fallback: use the value from last refresh call
        rte = t.get("refresh_token_expires_in")
        if rte:
            created = t.get("expires_at", time.time())
            return float(created) + float(rte) - time.time()
    except Exception:
        pass
    return None


def build_auth_url(secret_file: str, account: str) -> str | None:
    try:
        with open(secret_file) as f:
            s = json.load(f)
        web = s.get("web") or {}
        client_id = web.get("client_id", "")
        if not client_id:
            return None
        # state carries account id; redirect_uri stays clean (no query params)
        return (
            "https://accounts.google.com/o/oauth2/auth"
            f"?client_id={urllib.parse.quote(client_id)}"
            f"&redirect_uri={urllib.parse.quote(CALLBACK_BASE)}"
            f"&scope={urllib.parse.quote(YT_SCOPES)}"
            f"&state={account}"
            "&response_type=code"
            "&access_type=offline"
            "&prompt=consent"
        )
    except Exception:
        return None


def send_telegram(chat_id: str, text: str) -> bool:
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception:
        return False


def main():
    now = datetime.now(timezone.utc)
    print(f"[{now.strftime('%Y-%m-%d %H:%M UTC')}] Checking YouTube token expiry…")

    if not ADMIN_CHAT_ID:
        print("  ⚠️  TG_ADMIN_CHAT_ID not set — cannot send Telegram alerts")
        print("  Set it in crontab: TG_ADMIN_CHAT_ID=YOUR_ID 0 8 * * * python3 ...")

    alerts = []
    for account, cfg in ACCOUNTS.items():
        expires_in = token_expires_in(cfg["token_file"])
        if expires_in is None:
            print(f"  {cfg['label']}: expiry unknown (token saved before monitor)")
            # Try to refresh and check
            expires_in = 7 * 86400  # assume 7 days if unknown
        hours_left = expires_in / 3600
        print(f"  {cfg['label']}: expires in {hours_left:.1f}h")

        if expires_in < ALERT_HOURS * 3600:
            auth_url = build_auth_url(cfg["secret_file"], account)
            alerts.append((cfg["label"], hours_left, auth_url))

    if not alerts:
        print("  ✅ All tokens are healthy")
        return

    # Build Telegram message
    msg_lines = ["🔑 <b>YouTube Token Renewal Required</b>\n"]
    for label, hours_left, auth_url in alerts:
        msg_lines.append(f"<b>{label}</b> — expires in <b>{hours_left:.0f}h</b>")
        if auth_url:
            msg_lines.append(f"👉 <a href=\"{auth_url}\">Tap to renew (opens Google)</a>")
        else:
            msg_lines.append("⚠️ Auth URL unavailable — run auth script manually")
        msg_lines.append("")

    msg_lines.append("After tapping: log in → Allow → token saves automatically.")
    message = "\n".join(msg_lines)

    if ADMIN_CHAT_ID:
        ok = send_telegram(ADMIN_CHAT_ID, message)
        print(f"  📱 Telegram alert sent: {'✅' if ok else '❌'}")
    else:
        print("\n" + "="*60)
        print("TELEGRAM MESSAGE (would be sent if TG_ADMIN_CHAT_ID set):")
        print(message)
        print("="*60)


if __name__ == "__main__":
    main()
