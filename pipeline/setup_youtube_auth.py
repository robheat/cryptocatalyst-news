"""
setup_youtube_auth.py — One-time local YouTube OAuth2 authorization.

Run this ONCE on your local machine to generate pipeline/cache/youtube_token.json.
After this, the CI pipeline uses YOUTUBE_REFRESH_TOKEN from the output.

Prerequisites:
  1. Go to Google Cloud Console → APIs & Services → Credentials
  2. Create an OAuth 2.0 Client ID for "Desktop App"
  3. Enable "YouTube Data API v3" on your project
  4. Set env vars YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET
  5. Run: python setup_youtube_auth.py

Usage:
  $env:YOUTUBE_CLIENT_ID = "your-client-id"
  $env:YOUTUBE_CLIENT_SECRET = "your-client-secret"
  python setup_youtube_auth.py
"""
import json
import os
from pathlib import Path

TOKEN_FILE = Path(__file__).parent / "cache" / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: google-auth-oauthlib not installed.")
        print("Run: pip install -r requirements-youtube.txt")
        return

    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("ERROR: Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET env vars first.")
        print()
        print("Steps:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create OAuth 2.0 Client ID → Application type: Desktop App")
        print("  3. Enable YouTube Data API v3 at:")
        print("     https://console.cloud.google.com/apis/library/youtube.googleapis.com")
        print("  4. Set the env vars and re-run this script.")
        return

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    print("Opening browser for YouTube authorization...")
    print("Sign in with the Google account that owns your YouTube channel.")
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        json.dumps(
            {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes or []),
            }
        )
    )

    print(f"\n✓ Credentials saved to: {TOKEN_FILE}")
    print()
    print("Next steps — add these to GitHub Actions repository secrets:")
    print(f"  YOUTUBE_CLIENT_ID     = {client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET = {client_secret}")
    print(f"  YOUTUBE_REFRESH_TOKEN = {creds.refresh_token}")
    print()
    print("The pipeline/cache/youtube_token.json file stays LOCAL only (in .gitignore).")


if __name__ == "__main__":
    main()
