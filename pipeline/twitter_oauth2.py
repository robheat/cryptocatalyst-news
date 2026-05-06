"""
twitter_oauth2.py — One-time script to get OAuth 2.0 refresh token for Twitter/X.
Required for Bookmarks API access.

Usage:
  1. Set TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET env vars
     (from Twitter Developer Portal → App → Keys and tokens → OAuth 2.0)
  2. Run: python twitter_oauth2.py
  3. A browser window opens — authorize the app
  4. Copy the refresh_token and store it as a GitHub secret

Requires: Twitter app with OAuth 2.0 enabled, redirect URL set to http://localhost:9876/callback
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET", "")

if not CLIENT_ID:
    print("ERROR: Set TWITTER_CLIENT_ID environment variable")
    sys.exit(1)

REDIRECT_URI = "http://localhost:9876/callback"
SCOPES = "tweet.read users.read bookmark.read bookmark.write offline.access"

# PKCE challenge
code_verifier = secrets.token_urlsafe(64)
code_challenge = (
    base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
    .rstrip(b"=")
    .decode()
)
state = secrets.token_urlsafe(16)

auth_code = None
server_done = threading.Event()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if params.get("state", [None])[0] != state:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State mismatch - possible CSRF. Try again.")
            return

        if "error" in params:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Error: {params['error'][0]}".encode())
            server_done.set()
            return

        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html><body style="font-family:system-ui;text-align:center;padding:60px;background:#0a0a0a;color:#ededed">
            <h2>Authorization successful!</h2>
            <p>You can close this tab and go back to the terminal.</p>
            </body></html>
        """)
        server_done.set()

    def log_message(self, *args):
        pass  # suppress logs


def main():
    # Build authorization URL
    auth_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"https://twitter.com/i/oauth2/authorize?{auth_params}"

    # Start local server to catch the callback
    server = http.server.HTTPServer(("localhost", 9876), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("Opening browser for Twitter authorization...")
    print(f"If it doesn't open, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    server_done.wait(timeout=120)
    server.shutdown()

    if not auth_code:
        print("ERROR: No authorization code received.")
        sys.exit(1)

    print("Got authorization code. Exchanging for tokens...")

    # Exchange code for tokens
    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }).encode()

    # Basic auth header with client_id:client_secret
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    req = urllib.request.Request(
        "https://api.twitter.com/2/oauth2/token",
        data=token_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        method="POST",
    )

    resp = urllib.request.urlopen(req)
    tokens = json.loads(resp.read().decode())

    print("\n=== SUCCESS ===")
    print(f"Access Token:  {tokens['access_token'][:20]}...")
    print(f"Refresh Token: {tokens['refresh_token']}")
    print(f"Expires in:    {tokens.get('expires_at', tokens.get('expires_in', '?'))} seconds")
    print(f"\nStore this as TWITTER_REFRESH_TOKEN in GitHub secrets and Vercel env vars:")
    print(f"\n  {tokens['refresh_token']}\n")


if __name__ == "__main__":
    main()
