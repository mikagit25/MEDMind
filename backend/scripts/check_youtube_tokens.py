#!/usr/bin/env python3
"""
YouTube OAuth token health monitor — sends Telegram alert when tokens are near expiry.

Cron: 0 8 * * *  (08:00 UTC daily)
Run:  python3 backend/scripts/check_youtube_tokens.py
"""
from __future__ import annotations
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

BOT_TOKEN     = "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
ADMIN_CHAT_ID = os.environ.get("TG_ADMIN_CHAT_ID", "209381269")
WARN_DAYS     = 3   # alert when refresh_token expires in ≤ N days
CALLBACK_URL  = "https://medmind.pro/api/v1/auth/youtube/callback"

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

ACCOUNTS = [
    {
        "label":   "🇬🇧 MedMind EN (account1)",
        "token":   "/opt/medmind/youtube_token.json",
        "secret":  "/opt/medmind/client_secret_web.json",
        "state":   "en",
        "account": "Google аккаунт EN канала",
    },
    {
        "label":   "🇪🇸 MedMind ES (account2)",
        "token":   "/opt/medmind/youtube_token_account2.json",
        "secret":  "/opt/medmind/client_secret_account2_web.json",
        "state":   "es",
        "account": "Google аккаунт ES канала",
    },
    {
        "label":   "🇸🇦 MedMind AR (account3)",
        "token":   "/opt/medmind/youtube_token_ar.json",
        "secret":  "/opt/medmind/client_secret_account3_web.json",
        "state":   "ar",
        "account": "Google аккаунт AR канала",
    },
]


def build_auth_url(secret_path: str, state: str) -> str | None:
    try:
        with open(secret_path) as f:
            raw = json.load(f)
        creds = raw.get("web") or raw.get("installed") or {}
        client_id = creds.get("client_id")
        if not client_id:
            return None
        import urllib.parse
        params = {
            "client_id":     client_id,
            "redirect_uri":  CALLBACK_URL,
            "response_type": "code",
            "scope":         " ".join(SCOPES),
            "access_type":   "offline",
            "prompt":        "consent",
            "state":         state,
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    except Exception:
        return None


def curl_tg(msg: str) -> bool:
    payload = json.dumps({
        "chat_id": ADMIN_CHAT_ID, "text": msg,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    })
    r = subprocess.run(
        ["curl", "-s", "--max-time", "10", "-X", "POST",
         f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
         "-H", "Content-Type: application/json", "-d", payload],
        capture_output=True, text=True, timeout=12,
    )
    try:
        return json.loads(r.stdout).get("ok", False)
    except Exception:
        return False


def try_refresh_access_token(acc: dict) -> bool:
    """Try to refresh the access token using refresh_token. Returns True if successful."""
    token_path = Path(acc["token"])
    secret_path = Path(acc.get("secret", ""))

    if not token_path.exists() or token_path.stat().st_size == 0:
        return False

    with open(token_path) as f:
        token = json.load(f)

    refresh_token = token.get("refresh_token")
    if not refresh_token:
        return False

    # Try self-contained (token has client_id/secret embedded)
    client_id     = token.get("client_id")
    client_secret = token.get("client_secret")

    # Fallback to secret file
    if not client_id and secret_path.exists():
        try:
            raw = json.load(open(secret_path))
            creds = raw.get("web") or raw.get("installed") or {}
            client_id     = creds.get("client_id")
            client_secret = creds.get("client_secret")
        except Exception:
            pass

    if not client_id or not client_secret:
        return False

    form = "&".join(f"{k}={v}" for k, v in {
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    }.items())

    r = subprocess.run(
        ["curl", "-s", "--max-time", "15", "-X", "POST",
         "https://oauth2.googleapis.com/token",
         "-d", form, "-H", "Content-Type: application/x-www-form-urlencoded"],
        capture_output=True, text=True, timeout=18,
    )
    try:
        resp = json.loads(r.stdout)
    except Exception:
        return False

    if "access_token" not in resp:
        return False

    # Save updated token
    token["access_token"] = resp["access_token"]
    token["expires_at"]   = time.time() + resp.get("expires_in", 3600)
    if "refresh_token" in resp:
        token["refresh_token"] = resp["refresh_token"]
    if "refresh_token_expires_in" in resp:
        token["refresh_token_expires_in"] = resp["refresh_token_expires_in"]
        token["refresh_token_absolute_expiry"] = time.time() + resp["refresh_token_expires_in"]

    with open(token_path, "w") as f:
        json.dump(token, f, indent=2)

    return True


def check_account(acc: dict) -> dict:
    """Return status dict for one account."""
    now = time.time()
    path = Path(acc["token"])
    result = {"label": acc["label"], "status": "ok", "message": ""}

    if not path.exists() or path.stat().st_size == 0:
        result["status"] = "dead"
        result["message"] = "Token file missing or empty — needs re-auth"
        return result

    try:
        token = json.load(open(path))
    except Exception as e:
        result["status"] = "dead"
        result["message"] = f"Token file corrupt: {e}"
        return result

    # Check refresh_token absolute expiry (Google Testing mode apps)
    rt_abs = token.get("refresh_token_absolute_expiry")
    if rt_abs:
        days_left = (rt_abs - now) / 86400
        if days_left <= 0:
            result["status"] = "dead"
            result["message"] = "Refresh token EXPIRED — needs immediate re-auth"
            return result
        elif days_left <= WARN_DAYS:
            result["status"] = "expiring"
            result["message"] = f"Refresh token expires in {days_left:.1f} days — re-auth needed!"
            return result

    # Check access token — try to refresh
    access_expired = now > token.get("expires_at", 0)
    if access_expired:
        refreshed = try_refresh_access_token(acc)
        if not refreshed:
            result["status"] = "dead"
            result["message"] = "Access token expired and refresh failed — re-auth needed"
            return result
        result["message"] = "Access token refreshed successfully"
    else:
        exp = datetime.fromtimestamp(token["expires_at"])
        result["message"] = f"Access token valid until {exp.strftime('%H:%M')}"

    if rt_abs:
        days_left = (rt_abs - now) / 86400
        result["message"] += f" | Refresh token: {days_left:.0f}d left"

    return result


def main():
    now_str = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    alerts = []
    ok_list = []

    for acc in ACCOUNTS:
        s = check_account(acc)
        if s["status"] in ("dead", "expiring"):
            icon = "🔴" if s["status"] == "dead" else "🟡"
            auth_url = build_auth_url(acc["secret"], acc["state"])
            if auth_url:
                link_line = (
                    f'   <a href="{auth_url}">👉 Авторизовать {acc["label"]}</a>\n'
                    f'   Войди как: <b>{acc["account"]}</b>'
                )
            else:
                link_line = "   ⚠️ Не удалось построить ссылку (нет client_secret)"
            alerts.append(
                f"{icon} <b>{s['label']}</b>\n"
                f"   {s['message']}\n"
                f"{link_line}"
            )
        else:
            ok_list.append(f"✅ {s['label']}: {s['message']}")

        print(f"[{s['status'].upper()}] {s['label']}: {s['message']}")

    if alerts:
        msg = (
            f"⚠️ <b>YouTube Token Alert</b> — {now_str}\n\n"
            + "\n\n".join(alerts)
            + "\n\n<i>Нажми ссылку → войди в нужный аккаунт → Разрешить → токен сохранится автоматически.</i>"
        )
        ok = curl_tg(msg)
        print(f"\nTelegram alert sent: {'✅' if ok else '❌'}")
    else:
        # Send a silent daily OK only on Mondays to avoid spam
        from datetime import date
        if date.today().weekday() == 0:  # Monday
            msg = f"✅ <b>YouTube tokens OK</b> — {now_str}\n\n" + "\n".join(ok_list)
            curl_tg(msg)
        print("\nAll tokens healthy — no alert needed")


if __name__ == "__main__":
    main()
