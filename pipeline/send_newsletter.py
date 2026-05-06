"""
send_newsletter.py — Fetch the weekly digest from the API and send via Resend
to all subscribed contacts in the audience.

Environment variables:
  RESEND_API_KEY        — Resend API key
  RESEND_AUDIENCE_ID    — Resend audience ID for subscribers
  NEWSLETTER_SECRET     — Shared secret to authenticate digest API call
  SITE_URL              — Base URL (default: https://cryptocatalyst.news)
"""

import json
import os
import sys
import urllib.request
import urllib.error

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
RESEND_AUDIENCE_ID = os.environ["RESEND_AUDIENCE_ID"]
NEWSLETTER_SECRET = os.environ["NEWSLETTER_SECRET"]
SITE_URL = os.environ.get("SITE_URL", "https://cryptocatalyst.news")
FROM_EMAIL = "CryptoCatalyst <digest@cryptocatalyst.news>"


def fetch_digest() -> dict:
    """Fetch rendered digest HTML + subject from the site API."""
    url = f"{SITE_URL}/api/newsletter/digest?secret={NEWSLETTER_SECRET}&days=7"
    req = urllib.request.Request(url, headers={"User-Agent": "CryptoCatalyst-Pipeline/1.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    if resp.status != 200:
        raise RuntimeError(f"Digest API returned {resp.status}")
    return json.loads(resp.read().decode())


def get_contacts() -> list[dict]:
    """List all non-unsubscribed contacts in the audience."""
    url = f"https://api.resend.com/audiences/{RESEND_AUDIENCE_ID}/contacts"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "CryptoCatalyst-Pipeline/1.0",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Resend contacts API {e.code}: {body}") from e
    data = json.loads(resp.read().decode())
    contacts = data.get("data", [])
    return [c for c in contacts if not c.get("unsubscribed", False)]


def send_email(to: str, subject: str, html: str, contact_id: str):
    """Send a single email via the Resend API."""
    # Replace the unsubscribe placeholder with this contact's actual ID
    personalized_html = html.replace("{{CONTACT_ID}}", contact_id)

    payload = json.dumps({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": personalized_html,
        "headers": {
            "List-Unsubscribe": f"<{SITE_URL}/api/newsletter/unsubscribe?id={contact_id}>",
        },
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "CryptoCatalyst-Pipeline/1.0",
        },
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read().decode())
    return result.get("id")


def main():
    print("=== CryptoCatalyst Weekly Newsletter ===")

    # 1. Fetch digest
    print("Fetching digest...")
    try:
        digest = fetch_digest()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("No articles this week — skipping newsletter.")
            return
        raise
    print(f"  Subject: {digest['subject']}")
    print(f"  Articles: {digest['articleCount']}")

    # 2. Get subscribers
    print("Fetching subscribers...")
    contacts = get_contacts()
    print(f"  Active subscribers: {len(contacts)}")

    if not contacts:
        print("No subscribers yet — skipping send.")
        return

    # 3. Send to each subscriber
    sent = 0
    failed = 0
    for contact in contacts:
        email = contact["email"]
        contact_id = contact["id"]
        try:
            email_id = send_email(email, digest["subject"], digest["html"], contact_id)
            print(f"  ✓ {email} → {email_id}")
            sent += 1
        except Exception as e:
            print(f"  ✗ {email} → {e}")
            failed += 1

    print(f"\nDone: {sent} sent, {failed} failed out of {len(contacts)} subscribers.")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
