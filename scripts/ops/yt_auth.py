#!/usr/bin/env python3
"""
Two-step YouTube OAuth for headless server.

Step 1 — get URL:
    python3 yt_auth.py url

Step 2 — exchange code (paste full redirect URL or just the code):
    python3 yt_auth.py code "http://localhost/?code=4/0AX4XfW..."
    # or just the code:
    python3 yt_auth.py code "4/0AX4XfW..."
"""
import json, sys, time, urllib.parse, httpx

SECRET_FILE = "/opt/medmind/client_secret.json"
TOKEN_FILE  = "/opt/medmind/youtube_token.json"

with open(SECRET_FILE) as f:
    d = json.load(f)
secret = d.get("installed") or d.get("web") or d

CLIENT_ID     = secret["client_id"]
CLIENT_SECRET = secret["client_secret"]
REDIRECT_URI  = "http://localhost"
SCOPE         = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube"

if len(sys.argv) < 2 or sys.argv[1] == "url":
    url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?response_type=code"
        f"&client_id={urllib.parse.quote(CLIENT_ID)}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={urllib.parse.quote(SCOPE)}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    print("\n" + "="*70)
    print("Open this URL in your browser:")
    print("="*70)
    print(url)
    print("="*70)
    print("\nAfter clicking Allow, browser shows 'localhost refused to connect'")
    print("— that's OK! Copy the FULL URL from the address bar, then run:")
    print(f'\npython3 yt_auth.py code "PASTE_FULL_URL_HERE"\n')

elif sys.argv[1] == "code":
    raw = sys.argv[2] if len(sys.argv) > 2 else ""
    if raw.startswith("http"):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        code = params.get("code", [None])[0]
    else:
        code = raw.split("&")[0]  # strip scope part if present

    if not code:
        print("❌ Could not find code in:", raw)
        sys.exit(1)

    print(f"Exchanging code for token...")
    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "code":          code,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    })

    if resp.status_code != 200:
        print(f"❌ Failed: {resp.status_code} {resp.text}")
        sys.exit(1)

    token = resp.json()
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=2)

    print(f"✅ Token saved to {TOKEN_FILE}")
    print(f"   Scopes: {token.get('scope','')}")
    print(f"\nNow run:")
    print("python3 backend/scripts/youtube_uploader.py --batch --limit 10 --lang en")

else:
    print("Usage: python3 yt_auth.py url  |  python3 yt_auth.py code 'http://...'")
