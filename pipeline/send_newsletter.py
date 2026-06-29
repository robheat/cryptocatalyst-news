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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html import escape

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
RESEND_AUDIENCE_ID = os.environ["RESEND_AUDIENCE_ID"]
NEWSLETTER_SECRET = os.environ["NEWSLETTER_SECRET"]
SITE_URL = os.environ.get("SITE_URL", "https://cryptocatalyst.news")
FROM_EMAIL = "CryptoCatalyst <digest@cryptocatalyst.news>"
ARTICLES_DIR = Path(__file__).resolve().parent.parent / "content" / "articles"


class PermanentSendError(Exception):
    """Non-retryable send failure for a specific recipient."""


def fetch_digest() -> dict:
    """Fetch rendered digest HTML + subject from the site API."""
    url = f"{SITE_URL}/api/newsletter/digest?secret={NEWSLETTER_SECRET}&days=7"
    req = urllib.request.Request(url, headers={"User-Agent": "CryptoCatalyst-Pipeline/1.0"})
    resp = urllib.request.urlopen(req, timeout=30)
    if resp.status != 200:
        raise RuntimeError(f"Digest API returned {resp.status}")
    return json.loads(resp.read().decode())


def parse_published_at(value: str) -> datetime:
    # Handle ISO strings with trailing Z and timezone offsets.
    normalized = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def load_recent_articles(days: int) -> list[dict]:
    if not ARTICLES_DIR.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []
    for path in ARTICLES_DIR.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                article = json.load(f)
            published_at = parse_published_at(article.get("publishedAt", ""))
            if published_at >= cutoff:
                articles.append(article)
        except Exception:
            continue

    articles.sort(key=lambda a: a.get("publishedAt", ""), reverse=True)
    return articles


def render_local_digest_email(articles: list[dict], week_end: str) -> str:
    rows = []
    for article in articles[:15]:
        summary = article.get("summary", "")
        summary_text = f"{escape(summary[:200])}{'...' if len(summary) > 200 else ''}"
        rows.append(
            f"""
        <tr>
            <td style=\"padding:16px 0;border-bottom:1px solid #1f2937\">
                <a href=\"{SITE_URL}/articles/{escape(article.get('slug', ''))}\"
                     style=\"color:#a78bfa;text-decoration:none;font-size:16px;font-weight:600;line-height:1.4\">
                    {escape(article.get('title', 'Untitled'))}
                </a>
                <div style=\"margin-top:4px\">
                    <span style=\"display:inline-block;background:#1f2937;color:#9ca3af;font-size:11px;padding:2px 8px;border-radius:99px;text-transform:uppercase;letter-spacing:0.5px\">
                        {escape(article.get('category', 'general'))}
                    </span>
                </div>
                <p style=\"color:#9ca3af;font-size:14px;line-height:1.5;margin:8px 0 0 0\">{summary_text}</p>
            </td>
        </tr>"""
        )

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
    <meta name=\"color-scheme\" content=\"dark\">
    <title>CryptoCatalyst Weekly Digest</title>
</head>
<body style=\"margin:0;padding:0;background:#0a0a0a;color:#ededed;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif\">
    <div style=\"max-width:600px;margin:0 auto;padding:32px 20px\">
        <div style=\"text-align:center;padding-bottom:24px;border-bottom:1px solid #1f2937\">
            <h1 style=\"margin:0;font-size:24px;font-weight:700\">
                <span style=\"color:#ffffff\">Crypto</span><span style=\"color:#f59e0b\">Catalyst</span><span style=\"color:#6b7280;font-size:14px\">.news</span>
            </h1>
            <p style=\"margin:8px 0 0;color:#6b7280;font-size:13px\">Weekly Crypto Digest - {escape(week_end)}</p>
        </div>

        <div style=\"padding:24px 0\">
            <p style=\"margin:0;color:#d1d5db;font-size:15px;line-height:1.6\">
                Here are the top {len(articles)} crypto and blockchain stories from this week. Click any headline to read the full article on CryptoCatalyst.
            </p>
        </div>

        <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" style=\"border-collapse:collapse\">{''.join(rows)}
        </table>

        <div style=\"text-align:center;padding:32px 0\">
            <a href=\"{SITE_URL}\" style=\"display:inline-block;background:#d97706;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:12px 24px;border-radius:8px\">
                Read all stories on CryptoCatalyst ->
            </a>
        </div>

        <div style=\"border-top:1px solid #1f2937;padding-top:20px;text-align:center\">
            <p style=\"margin:0;color:#6b7280;font-size:12px;line-height:1.6\">
                You received this because you subscribed to the CryptoCatalyst weekly digest.<br>
                <a href=\"{SITE_URL}/api/newsletter/unsubscribe?id={{{{CONTACT_ID}}}}\" style=\"color:#f59e0b;text-decoration:none\">Unsubscribe</a>
                &nbsp;.&nbsp;
                <a href=\"{SITE_URL}\" style=\"color:#f59e0b;text-decoration:none\">CryptoCatalyst.news</a>
                &nbsp;.&nbsp;
                <a href=\"https://twitter.com/CryptoCatalystN\" style=\"color:#f59e0b;text-decoration:none\">@CryptoCatalystN</a>
            </p>
        </div>
    </div>
</body>
</html>"""


def build_local_digest(days: int) -> dict:
    articles = load_recent_articles(days)
    if not articles:
        raise FileNotFoundError("No local articles found for the selected period")

    week_end = datetime.now(timezone.utc).strftime("%B %d, %Y")
    subject = f"CryptoCatalyst Weekly: {len(articles)} crypto stories - {week_end}"
    html = render_local_digest_email(articles, week_end)
    return {
        "html": html,
        "subject": subject,
        "articleCount": len(articles),
    }


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
    try:
        resp = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        message = f"Resend email API {e.code}: {body}"
        if e.code in (400, 401, 403, 404, 409, 410, 422):
            raise PermanentSendError(message) from e
        raise RuntimeError(message) from e
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
        if e.code == 401:
            print("Digest API unauthorized. Falling back to local digest generation...")
            digest = build_local_digest(days=7)
            print("  Using local digest from content/articles")
        else:
            raise
    except urllib.error.URLError:
        print("Digest API unreachable. Falling back to local digest generation...")
        digest = build_local_digest(days=7)

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
    skipped = 0
    failed = 0
    for contact in contacts:
        email = contact["email"]
        contact_id = contact["id"]
        try:
            email_id = send_email(email, digest["subject"], digest["html"], contact_id)
            print(f"  ✓ {email} → {email_id}")
            sent += 1
        except PermanentSendError as e:
            print(f"  ⚠ {email} → skipped ({e})")
            skipped += 1
        except Exception as e:
            print(f"  ✗ {email} → {e}")
            failed += 1

    print(f"\nDone: {sent} sent, {skipped} skipped, {failed} failed out of {len(contacts)} subscribers.")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
