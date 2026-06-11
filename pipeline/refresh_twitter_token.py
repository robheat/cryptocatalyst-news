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


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


ENV_FILE = Path(__file__).parent / ".env"
load_env_file(ENV_FILE)


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

    candidates: list[str] = []
    if current_refresh:
        candidates.append(current_refresh)
    if REFRESH_TOKEN and REFRESH_TOKEN not in candidates:
        candidates.append(REFRESH_TOKEN)

    tokens = None
    last_error = ""
    for idx, candidate in enumerate(candidates):
        try:
            tokens = refresh_access_token(candidate)
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()
            last_error = f"{exc.code} {body}"
            if idx < len(candidates) - 1:
                print("Warning: Cached refresh token failed, retrying with fallback token...")
                continue
        except Exception as exc:
            last_error = str(exc)
            if idx < len(candidates) - 1:
                print("Warning: Cached refresh token failed, retrying with fallback token...")
                continue

    if tokens is None:
        print(f"ERROR refreshing token: {last_error}")
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
