"""
fetch_bookmarks.py — Fetch bookmarked tweets from @CryptoCatalystN,
turn them into raw stories for the article pipeline.

Uses Twitter API v2 Bookmarks (OAuth 2.0).
Outputs: pipeline/cache/bookmark_stories.json

After articles are generated, bookmarks are removed to avoid re-processing.

Requires env vars:
  TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, TWITTER_REFRESH_TOKEN
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("TWITTER_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("TWITTER_REFRESH_TOKEN", "")

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = CACHE_DIR / "bookmark_stories.json"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"

# Bookmarks older than this are skipped (not removed) to avoid processing stale tweets
MAX_BOOKMARK_AGE_DAYS = 1

# File to persist the refreshed token across runs
TOKEN_CACHE = CACHE_DIR / ".twitter_oauth2_token.json"


def refresh_access_token(refresh_token: str) -> dict:
    """Exchange a refresh token for a new access token + refresh token."""
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

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        tokens = json.loads(resp.read().decode())
        # Persist the new refresh token for next run
        TOKEN_CACHE.write_text(json.dumps({
            "refresh_token": tokens["refresh_token"],
            "access_token": tokens["access_token"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }))
        return tokens
    except urllib.error.HTTPError as e:
        print(f"ERROR refreshing token: {e.code} {e.read().decode()}")
        sys.exit(1)


def get_access_token() -> str:
    """Get a valid access token, refreshing if necessary."""
    # Use the persisted refresh token if available (it rotates)
    current_refresh = REFRESH_TOKEN
    if TOKEN_CACHE.exists():
        cached = json.loads(TOKEN_CACHE.read_text())
        current_refresh = cached.get("refresh_token", REFRESH_TOKEN)

    tokens = refresh_access_token(current_refresh)
    return tokens["access_token"]


def get_user_id(access_token: str) -> str:
    """Get the authenticated user's ID."""
    req = urllib.request.Request(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
    return data["data"]["id"]


def fetch_bookmarks(access_token: str, user_id: str) -> list[dict]:
    """Fetch all bookmarks for the authenticated user."""
    url = (
        f"https://api.twitter.com/2/users/{user_id}/bookmarks"
        f"?tweet.fields=created_at,author_id,entities,text,referenced_tweets"
        f"&expansions=author_id"
        f"&user.fields=name,username"
        f"&max_results=100"
    )

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR fetching bookmarks: {e.code} {body}")
        return []

    tweets = data.get("data", [])
    if not tweets:
        return []

    # Build author lookup
    users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

    return [{"tweet": t, "author": users.get(t["author_id"], {})} for t in tweets]


def remove_bookmark(access_token: str, user_id: str, tweet_id: str):
    """Remove a bookmark after processing so it won't be picked up again."""
    req = urllib.request.Request(
        f"https://api.twitter.com/2/users/{user_id}/bookmarks/{tweet_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="DELETE",
    )
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"  Warning: Could not remove bookmark {tweet_id}: {e}")


def extract_urls(tweet: dict) -> list[str]:
    """Extract expanded URLs from tweet entities."""
    urls = []
    for url in tweet.get("entities", {}).get("urls", []):
        expanded = url.get("expanded_url", url.get("url", ""))
        # Skip twitter/x.com self-links
        if expanded and not re.match(r"https?://(twitter\.com|x\.com|t\.co)/", expanded):
            urls.append(expanded)
    return urls


def fetch_url_content(url: str) -> str:
    """Fetch basic text content from a URL for context."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CryptoCatalystBot/1.0)"
        })
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="ignore")[:50000]

        # Extract title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        # Extract meta description
        desc_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            html, re.IGNORECASE
        )
        if not desc_match:
            desc_match = re.search(
                r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
                html, re.IGNORECASE
            )
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract og:description as fallback
        if not description:
            og_match = re.search(
                r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
                html, re.IGNORECASE
            )
            description = og_match.group(1).strip() if og_match else ""

        # Extract some body text as fallback
        if not description:
            body_text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
            body_text = re.sub(r"<style[^>]*>.*?</style>", " ", body_text, flags=re.DOTALL | re.IGNORECASE)
            body_text = re.sub(r"<[^>]+>", " ", body_text)
            body_text = re.sub(r"\s+", " ", body_text).strip()
            description = body_text[:500]

        return f"{title}\n{description}" if title else description
    except Exception as e:
        print(f"  Warning: Could not fetch {url}: {e}")
        return ""


def bookmark_to_story(entry: dict) -> dict:
    """Convert a bookmark into a raw story for the generate_content pipeline."""
    tweet = entry["tweet"]
    author = entry["author"]
    tweet_text = tweet.get("text", "")
    author_name = author.get("name", "Unknown")
    author_handle = author.get("username", "unknown")

    # Extract linked URLs and fetch their content for more context
    urls = extract_urls(tweet)
    linked_content = ""
    source_url = f"https://x.com/{author_handle}/status/{tweet['id']}"

    if urls:
        # Use the first linked URL as the primary source
        source_url = urls[0]
        linked_content = fetch_url_content(urls[0])

    # Build description from tweet text + any fetched content
    description = f"Tweet by @{author_handle} ({author_name}):\n{tweet_text}"
    if linked_content:
        description += f"\n\nLinked article content:\n{linked_content}"

    return {
        "title": tweet_text[:120].split("\n")[0],  # First line of tweet as title hint
        "description": description[:2000],
        "url": source_url,
        "source_name": f"@{author_handle} on X",
        "category_hint": "general",
        "tweet_id": tweet["id"],
        "published": tweet.get("created_at", ""),
    }


def get_existing_source_urls() -> set:
    """Get all source URLs from existing articles to avoid duplicates."""
    urls = set()
    if CONTENT_DIR.exists():
        for f in CONTENT_DIR.iterdir():
            if f.suffix == ".json":
                try:
                    article = json.loads(f.read_text())
                    urls.add(article.get("sourceUrl", ""))
                except Exception:
                    pass
    return urls


def main():
    if not CLIENT_ID or not REFRESH_TOKEN:
        print("ERROR: Set TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET, TWITTER_REFRESH_TOKEN")
        sys.exit(1)

    print("=== Fetch Bookmarks Pipeline ===")

    # Get OAuth 2.0 access token
    print("Refreshing access token...")
    access_token = get_access_token()

    # Get user ID
    user_id = get_user_id(access_token)
    print(f"User ID: {user_id}")

    # Fetch bookmarks
    print("Fetching bookmarks...")
    bookmarks = fetch_bookmarks(access_token, user_id)
    print(f"Found {len(bookmarks)} bookmarks")

    if not bookmarks:
        print("No bookmarks found. Nothing to do.")
        OUTPUT_FILE.write_text("[]")
        return

    # Check for duplicates against existing articles
    existing_urls = get_existing_source_urls()

    # Convert to stories
    stories = []
    processed_tweet_ids = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_BOOKMARK_AGE_DAYS)
    for entry in bookmarks:
        tweet = entry["tweet"]
        created_at_str = tweet.get("created_at", "")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at < cutoff:
                    print(f"  → Skipped (older than {MAX_BOOKMARK_AGE_DAYS} days): {tweet.get('text', '')[:60]}")
                    continue
            except ValueError:
                pass

        story = bookmark_to_story(entry)

        if story["url"] in existing_urls:
            print(f"  → Skipped (already have article): {story['title'][:60]}")
            # Still remove bookmark since we already covered it
            processed_tweet_ids.append(story["tweet_id"])
            continue

        print(f"  + {story['title'][:60]}")
        stories.append(story)
        processed_tweet_ids.append(story["tweet_id"])

    # Save stories for generate_content.py
    OUTPUT_FILE.write_text(json.dumps(stories, indent=2, ensure_ascii=False))
    print(f"\nSaved {len(stories)} new stories to {OUTPUT_FILE}")

    # Remove processed bookmarks
    print("Removing processed bookmarks...")
    for tweet_id in processed_tweet_ids:
        remove_bookmark(access_token, user_id, tweet_id)
    print(f"Removed {len(processed_tweet_ids)} bookmarks")


if __name__ == "__main__":
    main()
