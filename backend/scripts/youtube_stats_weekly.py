"""
Weekly YouTube channel stats → Telegram.
Cron: 0 9 * * 1  (Monday 09:00 UTC)
"""
import json, os, time, subprocess
from datetime import datetime, timedelta, timezone

BOT_TOKEN     = "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
ADMIN_CHAT_ID = os.environ.get("TG_ADMIN_CHAT_ID", "209381269")

ACCOUNTS = [
    {
        "label":  "🇬🇧 MedMind EN",
        "secret": "/opt/medmind/client_secret_web.json",
        "token":  "/opt/medmind/youtube_token.json",
    },
    {
        "label":  "🇪🇸 MedMind ES",
        "secret": "/opt/medmind/client_secret_account2_web.json",
        "token":  "/opt/medmind/youtube_token_account2.json",
    },
    {
        "label":  "🇸🇦 MedMind AR",
        "secret": "/opt/medmind/client_secret_account3_web.json",
        "token":  "/opt/medmind/youtube_token_ar.json",
    },
    # ── Happy Bear Kids ──────────────────────────────────────────────────────
    {
        "label":      "🐻 Happy Bear Kids EN",
        "secret":     "/opt/kids_channel/credentials/client_secret_kids_web.json",
        "token":      "/opt/kids_channel/credentials/youtube_token.json",
    },
    {
        "label":      "🐻 Happy Bear Kids AR",
        "token_type": "self_contained",
        "token":      "/opt/kids_channel/credentials/youtube_token_ar.json",
    },
    {
        "label":      "🐻 Happy Bear Kids ID",
        "token_type": "self_contained",
        "token":      "/opt/kids_channel/credentials/youtube_token_id.json",
    },
]


def curl_get(url: str, params: dict, token: str) -> dict | None:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    full_url = f"{url}?{qs}"
    r = subprocess.run(
        ["curl", "-s", "--max-time", "10", full_url,
         "-H", f"Authorization: Bearer {token}"],
        capture_output=True, text=True, timeout=12,
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def curl_post(url: str, data: dict) -> dict | None:
    form = "&".join(f"{k}={v}" for k, v in data.items())
    r = subprocess.run(
        ["curl", "-s", "--max-time", "10", "-X", "POST", url,
         "-d", form, "-H", "Content-Type: application/x-www-form-urlencoded"],
        capture_output=True, text=True, timeout=12,
    )
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def curl_tg(msg: str) -> bool:
    payload = json.dumps({"chat_id": ADMIN_CHAT_ID, "text": msg,
                          "parse_mode": "HTML", "disable_web_page_preview": True})
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


def get_access_token_selfcontained(token_path: str) -> str | None:
    """Get access token from self-contained JSON (client_id/secret embedded in token file)."""
    with open(token_path) as f:
        token = json.load(f)
    if not token.get("refresh_token"):
        return None
    if not token.get("access_token") or time.time() >= token.get("expires_at", 0) - 60:
        new = curl_post("https://oauth2.googleapis.com/token", {
            "client_id":     token["client_id"],
            "client_secret": token["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        if not new or "access_token" not in new:
            return None
        token["access_token"] = new["access_token"]
        token["expires_at"]   = time.time() + new.get("expires_in", 3600)
        with open(token_path, "w") as f:
            json.dump(token, f, indent=2)
    return token["access_token"]


def get_access_token_pickle(token_path: str) -> str | None:
    """Get/refresh access token from google-auth pickle file (kids channel)."""
    import pickle
    try:
        from google.auth.transport.requests import Request
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "wb") as f:
                pickle.dump(creds, f)
        return creds.token if creds.valid else None
    except Exception as e:
        print(f"  Pickle token error: {e}")
        return None


def get_access_token(secret_path: str, token_path: str) -> str | None:
    with open(secret_path) as f:
        s = json.load(f)
    creds = s.get("web") or s.get("installed") or {}

    with open(token_path) as f:
        token = json.load(f)

    if not token.get("refresh_token"):
        return None

    if not token.get("access_token") or time.time() >= token.get("expires_at", 0) - 60:
        new = curl_post("https://oauth2.googleapis.com/token", {
            "client_id":     creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        if not new or "access_token" not in new:
            return None
        token["access_token"] = new["access_token"]
        token["expires_at"]   = time.time() + new.get("expires_in", 3600)
        with open(token_path, "w") as f:
            json.dump(token, f, indent=2)

    return token["access_token"]


def fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def main():
    week = datetime.now(timezone.utc).strftime("%d.%m.%Y")
    lines = [f"📊 <b>YouTube — статистика</b> (неделя до {week})\n"]

    for acc in ACCOUNTS:
        print(f"Fetching {acc['label']}…")
        try:
            if acc.get("token_type") == "pickle":
                token = get_access_token_pickle(acc["token"])
            elif acc.get("token_type") == "self_contained":
                token = get_access_token_selfcontained(acc["token"])
            else:
                token = get_access_token(acc["secret"], acc["token"])
            if not token:
                lines.append(f"{acc['label']}: ❌ нет токена\n")
                continue

            data = curl_get(
                "https://www.googleapis.com/youtube/v3/channels",
                {"part": "snippet,statistics", "mine": "true"}, token,
            )
            items = data.get("items", []) if data else []
            if not items:
                lines.append(f"{acc['label']}: ❌ нет данных\n")
                continue

            st   = items[0]["statistics"]
            cid  = items[0]["id"]
            subs = int(st.get("subscriberCount", 0))
            views= int(st.get("viewCount", 0))
            vids = int(st.get("videoCount", 0))

            # Weekly views via search + video stats
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            sr = curl_get("https://www.googleapis.com/youtube/v3/search", {
                "part": "id", "channelId": cid, "type": "video",
                "publishedAfter": week_ago, "maxResults": "50",
            }, token)
            video_ids = [i["id"]["videoId"] for i in (sr or {}).get("items", []) if i.get("id", {}).get("videoId")]

            wv = 0
            if video_ids:
                vr = curl_get("https://www.googleapis.com/youtube/v3/videos",
                              {"part": "statistics", "id": ",".join(video_ids)}, token)
                wv = sum(int(i.get("statistics", {}).get("viewCount", 0))
                         for i in (vr or {}).get("items", []))

            lines.append(
                f"<b>{acc['label']}</b>\n"
                f"  👥 Подписчики: <b>{fmt(subs)}</b>\n"
                f"  👁 Просмотры всего: <b>{fmt(views)}</b>\n"
                f"  📹 Видео: <b>{vids}</b>\n"
                f"  📈 За 7 дней: <b>+{fmt(wv)}</b> ({len(video_ids)} видео)\n"
            )
            print(f"  subs={subs} views={views} vids={vids} weekly={wv}")

        except Exception as e:
            lines.append(f"{acc['label']}: ❌ {e}\n")
            print(f"  ERROR: {e}")

    msg = "\n".join(lines)
    print("\n" + msg)
    ok = curl_tg(msg)
    print(f"Telegram: {'✅' if ok else '❌'}")


if __name__ == "__main__":
    main()
