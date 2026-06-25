#!/usr/bin/env python3
"""
Re-authorize YouTube OAuth tokens for MedMind channels.

Run this when refresh tokens expire (Google revokes them every 7 days
for unverified OAuth apps in testing mode).

Usage:
    python3 reauth_youtube.py           # Account 1 (EN channel)
    python3 reauth_youtube.py --account2  # Account 2 (ES channel)

After running, paste the localhost redirect URL from your browser.
The new token is saved and all upload scripts will use it automatically.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
from pathlib import Path

import httpx

MEDMIND_DIR = Path("/opt/medmind")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def do_auth_flow(secret_path: Path, token_path: Path, account_label: str) -> None:
    raw_secret = load_json(secret_path)
    secret = raw_secret.get("installed") or raw_secret.get("web") or raw_secret

    client_id = secret["client_id"]
    client_secret = secret["client_secret"]

    auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        "?response_type=code"
        f"&client_id={urllib.parse.quote(client_id)}"
        "&redirect_uri=http://localhost"
        "&scope=https://www.googleapis.com/auth/youtube.upload"
        "%20https://www.googleapis.com/auth/youtube"
        "&access_type=offline"
        "&prompt=consent"
    )

    print(f"\n{'=' * 65}")
    print(f"  YouTube Re-Authorization — {account_label}")
    print(f"{'=' * 65}")
    print("\nSTEP 1: Open this URL in your browser (any device):")
    print(f"\n{auth_url}\n")
    print("STEP 2: Log in with the Google account that owns this channel")
    print("STEP 3: Click Allow — browser redirects to localhost (error is OK)")
    print("STEP 4: Copy the FULL URL from the browser address bar")
    print("        It looks like: http://localhost/?code=4/0AX...&scope=...\n")

    raw = input("Paste the full redirect URL (or just the code): ").strip()

    if raw.startswith("http"):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        code = params.get("code", [None])[0]
        if not code:
            print("❌ No 'code' parameter found in URL. Try again.")
            sys.exit(1)
    else:
        code = raw

    print("\nExchanging code for token…")
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  "http://localhost",
            "grant_type":    "authorization_code",
        },
        timeout=15,
    )

    if resp.status_code != 200:
        print(f"❌ Token exchange failed ({resp.status_code}):")
        print(resp.text)
        print("\nCommon reasons:")
        print("  • Code already used (each code is one-time only)")
        print("  • 'http://localhost' not in Google Cloud Console authorized redirect URIs")
        print("    → Go to console.cloud.google.com → Credentials → OAuth client → add http://localhost")
        sys.exit(1)

    token = resp.json()
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    save_json(token_path, token)

    print(f"\n✅ Token saved to {token_path}")
    print(f"   Access token expires in: {token.get('expires_in', '?')}s")
    print(f"   Refresh token: {'present' if token.get('refresh_token') else 'MISSING — re-auth again'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-authorize YouTube OAuth tokens")
    parser.add_argument("--account2", action="store_true", help="Re-auth account 2 (ES channel)")
    parser.add_argument("--account3", "--ar", action="store_true", help="Re-auth account 3 (AR channel)")
    args = parser.parse_args()

    if args.account3:
        secret_path = MEDMIND_DIR / "client_secret_account3_web.json"
        token_path  = MEDMIND_DIR / "youtube_token_ar.json"
        label       = "Account 3 — AR Channel"
    elif args.account2:
        secret_path = MEDMIND_DIR / "client_secret_account2_web.json"
        token_path  = MEDMIND_DIR / "youtube_token_account2.json"
        label       = "Account 2 — ES Channel"
    else:
        # Use _web variant — same client the cron uses
        secret_path = MEDMIND_DIR / "client_secret_web.json"
        token_path  = MEDMIND_DIR / "youtube_token.json"
        label       = "Account 1 — EN Channel"

    if not secret_path.exists():
        print(f"❌ Client secret not found: {secret_path}")
        sys.exit(1)

    do_auth_flow(secret_path, token_path, label)


if __name__ == "__main__":
    main()
