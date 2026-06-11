"""
refresh_twitter_token.py - Refresh X/Twitter OAuth2 token only.

This script rotates the OAuth2 refresh token and stores the latest pair in:
  pipeline/cache/.twitter_oauth2_token.json

Required env vars:
  TWITTER_CLIENT_ID
  TWITTER_CLIENT_SECRET
  TWITTER_REFRESH_TOKEN (used as fallback if no cached token exists)
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("TWITTER_REFRESH_TOKEN", "")

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
TOKEN_CACHE = CACHE_DIR / ".twitter_oauth2_token.json"


def refresh_access_token(refresh_token: str) -> dict:
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()

    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    req = urllib.request.Request(
        "https://api.twitter.com/2/oauth2/token",
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
        print("ERROR: Missing TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, or TWITTER_REFRESH_TOKEN")
        return 1

    current_refresh = REFRESH_TOKEN
    if TOKEN_CACHE.exists():
        try:
            cached = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
            current_refresh = cached.get("refresh_token", REFRESH_TOKEN)
        except Exception:
            current_refresh = REFRESH_TOKEN

    try:
        tokens = refresh_access_token(current_refresh)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"ERROR refreshing token: {exc.code} {body}")
        return 1
    except Exception as exc:
        print(f"ERROR refreshing token: {exc}")
        return 1

    if "refresh_token" not in tokens or "access_token" not in tokens:
        print("ERROR: Token response missing refresh_token or access_token")
        return 1

    TOKEN_CACHE.write_text(
        json.dumps(
            {
                "refresh_token": tokens["refresh_token"],
                "access_token": tokens["access_token"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"OK: Refreshed and saved token cache at {TOKEN_CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
