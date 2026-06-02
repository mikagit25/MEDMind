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
    "kids": {
        "label":       "🐻 Happy Bear Kids",
        "token_file":  "/opt/kids_channel/credentials/youtube_token.json",
        "secret_file": "/opt/kids_channel/credentials/client_secret_kids_web.json",
    },
}

YT_SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload"
    " https://www.googleapis.com/auth/youtube"
    " https://www.googleapis.com/auth/youtube.force-ssl"
)


def check_pickle_token(token_file: str) -> tuple[bool, str]:
    """Try to refresh pickle token. Returns (is_valid, status_message)."""
    import pickle
    try:
        from google.auth.transport.requests import Request
        with open(token_file, "rb") as f:
            creds = pickle.load(f)
        if creds.valid:
            return True, "действителен"
        if creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, "wb") as f:
                pickle.dump(creds, f)
            return True, "обновлён успешно"
        return False, "нет refresh_token"
    except Exception as e:
        msg = str(e).lower()
        if "invalid_grant" in msg:
            return False, "refresh_token истёк — нужна повторная авторизация"
        return False, f"ошибка: {str(e)[:80]}"


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
        # ── Pickle token (kids channel) ───────────────────────────────────────
        if cfg.get("token_type") == "pickle":
            valid, status = check_pickle_token(cfg["token_file"])
            print(f"  {cfg['label']}: {status}")
            if not valid:
                alerts.append({
                    "label":      cfg["label"],
                    "hours_left": 0,
                    "auth_url":   None,
                    "reauth_cmd": cfg.get("reauth_cmd", ""),
                    "is_pickle":  True,
                })
            continue

        # ── JSON token (MedMind channels) ─────────────────────────────────────
        expires_in = token_expires_in(cfg["token_file"])
        if expires_in is None:
            print(f"  {cfg['label']}: expiry unknown (token saved before monitor)")
            expires_in = 7 * 86400  # assume 7 days if unknown
        hours_left = expires_in / 3600
        print(f"  {cfg['label']}: expires in {hours_left:.1f}h")

        if expires_in < ALERT_HOURS * 3600:
            auth_url = build_auth_url(cfg["secret_file"], account)
            alerts.append({
                "label":      cfg["label"],
                "hours_left": hours_left,
                "auth_url":   auth_url,
                "is_pickle":  False,
            })

    if not alerts:
        print("  ✅ All tokens are healthy")
        return

    # Build Telegram message
    msg_lines = ["🔑 <b>YouTube Token Renewal Required</b>\n"]
    for alert in alerts:
        label     = alert["label"]
        auth_url  = alert.get("auth_url")
        is_pickle = alert.get("is_pickle", False)

        if is_pickle:
            msg_lines.append(f"<b>{label}</b> — ❌ требуется повторная авторизация")
            cmd = alert.get("reauth_cmd", "")
            if cmd:
                msg_lines.append(f"🖥 SSH на сервер и выполни:\n<code>{cmd}</code>")
        else:
            hours_left = alert["hours_left"]
            msg_lines.append(f"<b>{label}</b> — expires in <b>{hours_left:.0f}h</b>")
            if auth_url:
                msg_lines.append(f"👉 <a href=\"{auth_url}\">Tap to renew (opens Google)</a>")
            else:
                msg_lines.append("⚠️ Auth URL unavailable — run auth script manually")
        msg_lines.append("")

    msg_lines.append("MedMind: tap link → log in → Allow → saves automatically.")
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
