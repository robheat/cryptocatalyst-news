"""
post_twitter.py — Post today's AI digest as a Twitter/X thread.
Uses Twitter API v2 (OAuth 1.0a User Context).

Requires env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET,
  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
"""
import hashlib
import hmac
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"
IMAGES_DIR = Path(__file__).parent.parent / "public" / "images" / "articles"
TWEETED_FILE = Path(__file__).parent.parent / "content" / ".tweeted.json"

# Twitter API endpoints
TWEET_URL = "https://api.twitter.com/2/tweets"
MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"

# Env vars
API_KEY = os.environ.get("TWITTER_API_KEY", "")
API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET", "")

DRY_RUN = os.environ.get("TWITTER_DRY_RUN", "false").lower() == "true"

# Seconds between standalone tweets (default 5 minutes)
TWEET_INTERVAL = int(os.environ.get("TWEET_INTERVAL_SECS", "300"))
# Seconds between tweets within a thread (default 30s)
THREAD_INTERVAL = int(os.environ.get("THREAD_INTERVAL_SECS", "30"))


def _percent_encode(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def _oauth_signature(method: str, url: str, params: dict) -> str:
    """Generate OAuth 1.0a signature."""
    sorted_params = "&".join(
        f"{_percent_encode(k)}={_percent_encode(v)}"
        for k, v in sorted(params.items())
    )
    base_string = f"{method}&{_percent_encode(url)}&{_percent_encode(sorted_params)}"
    signing_key = f"{_percent_encode(API_SECRET)}&{_percent_encode(ACCESS_SECRET)}"
    signature = hmac.new(
        signing_key.encode(), base_string.encode(), hashlib.sha1
    ).digest()
    import base64
    return base64.b64encode(signature).decode()


def _oauth_header(method: str, url: str, extra_params: dict | None = None) -> str:
    """Build the OAuth Authorization header."""
    oauth_params = {
        "oauth_consumer_key": API_KEY,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": ACCESS_TOKEN,
        "oauth_version": "1.0",
    }
    all_params = {**oauth_params, **(extra_params or {})}
    oauth_params["oauth_signature"] = _oauth_signature(method, url, all_params)

    header_parts = ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


def upload_media(image_path: str) -> str | None:
    """
    Upload an image to Twitter via the v1.1 media/upload endpoint.
    Returns media_id_string on success, None on failure.
    """
    import base64 as b64mod

    file_path = Path(image_path)
    if not file_path.exists():
        print(f"  [MEDIA] Image not found: {image_path}")
        return None

    image_data = file_path.read_bytes()
    b64_data = b64mod.b64encode(image_data).decode("ascii")

    # Use multipart/form-data for media upload
    # OAuth signature must NOT include any body params for multipart uploads
    boundary = uuid.uuid4().hex
    body_parts = []
    # media_data field
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"media_data\"\r\n\r\n{b64_data}\r\n")
    # media_category field
    body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"media_category\"\r\n\r\ntweet_image\r\n")
    body_parts.append(f"--{boundary}--\r\n")
    form_body = "".join(body_parts).encode("utf-8")

    # No extra params in OAuth signature for multipart uploads
    auth_header = _oauth_header("POST", MEDIA_UPLOAD_URL)

    req = urllib.request.Request(
        MEDIA_UPLOAD_URL,
        data=form_body,
        headers={
            "Authorization": auth_header,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            media_id = data.get("media_id_string")
            print(f"  [MEDIA] Uploaded: {media_id}")
            return media_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [MEDIA ERROR] Twitter API {e.code}: {error_body[:300]}")
        return None


def get_article_image_path(article: dict) -> str | None:
    """Return the local image path for an article, or None."""
    image_url = article.get("imageUrl")
    if not image_url:
        return None
    # imageUrl is like /images/articles/slug.webp
    filename = image_url.split("/")[-1]
    path = IMAGES_DIR / filename
    if path.exists():
        return str(path)
    return None


def post_tweet(text: str, reply_to: str | None = None, media_id: str | None = None) -> str | None:
    """
    Post a single tweet. Returns tweet ID on success, None on failure.
    """
    payload: dict = {"text": text}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}

    body = json.dumps(payload).encode("utf-8")
    auth_header = _oauth_header("POST", TWEET_URL)

    req = urllib.request.Request(
        TWEET_URL,
        data=body,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            tweet_id = data.get("data", {}).get("id")
            return tweet_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  [ERROR] Twitter API {e.code}: {error_body[:300]}")
        return None


def post_thread(tweets: list[str], first_media_id: str | None = None) -> list[str]:
    """Post a thread (list of tweet texts). Returns list of tweet IDs."""
    if not tweets:
        return []

    ids: list[str] = []
    prev_id: str | None = None
    for i, text in enumerate(tweets):
        print(f"  Tweet {i+1}/{len(tweets)}: {text[:60]}...")
        if DRY_RUN:
            print("    [DRY RUN] Would post tweet")
            ids.append(f"dry-run-{i}")
            continue

        # Attach image only to the first tweet of the thread
        media = first_media_id if i == 0 else None
        tweet_id = post_tweet(text, reply_to=prev_id, media_id=media)
        if tweet_id:
            ids.append(tweet_id)
            prev_id = tweet_id
            print(f"    → Posted: {tweet_id}")
        else:
            print(f"    → FAILED. Stopping thread.")
            break

        # Space out thread tweets for a natural cadence
        if i < len(tweets) - 1:
            print(f"    Waiting {THREAD_INTERVAL}s before next thread tweet...")
            time.sleep(THREAD_INTERVAL)

    return ids


def _load_tweeted_slugs() -> set[str]:
    """Load the set of article slugs we've already tweeted."""
    if TWEETED_FILE.exists():
        try:
            return set(json.loads(TWEETED_FILE.read_text()))
        except Exception:
            pass
    return set()


def _save_tweeted_slugs(slugs: set[str]) -> None:
    """Persist tweeted slugs to disk (committed to repo)."""
    TWEETED_FILE.write_text(json.dumps(sorted(slugs), indent=2))


def get_todays_articles() -> list[dict]:
    """Load today's article JSONs that haven't been tweeted yet, newest first."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tweeted = _load_tweeted_slugs()
    articles = []
    if not CONTENT_DIR.exists():
        return articles
    for f in sorted(CONTENT_DIR.iterdir(), reverse=True):  # newest first
        if f.suffix == ".json" and f.name.startswith(today):
            art = json.loads(f.read_text())
            if art.get("slug") not in tweeted:
                articles.append(art)
    # Only tweet the most recent batch (up to 8)
    return articles[:8]


def main():
    if not API_KEY:
        print("Twitter credentials not set. Skipping Twitter posting.")
        return

    articles = get_todays_articles()
    if not articles:
        print("No new articles to tweet today.")
        return

    tweeted_slugs = _load_tweeted_slugs()
    print(f"Found {len(articles)} new articles to tweet (already tweeted: {len(tweeted_slugs)}).")

    # Post thread for top article (first one, which is usually highest scored)
    top = articles[0]
    thread_tweets = top.get("twitterThread", [])

    if not thread_tweets:
        # Fallback: generate a simple thread from the article
        thread_tweets = [
            f"💰 {top['title']}\n\n{top['summary']}",
            f"Read more → https://cryptocatalyst.news/articles/{top['slug']}",
        ]
    else:
        # Fix LLM-generated URLs: replace any ainformed.dev or cryptocatalyst.news URLs
        # with the correct slug
        correct_url = f"https://cryptocatalyst.news/articles/{top['slug']}"
        fixed = []
        for t in thread_tweets:
            t = re.sub(r"https?://cryptocatalyst\.news/articles/[\w.-]+", correct_url, t)
            t = re.sub(r"https?://cryptocatalyst\.news(?!/articles/)(?:\s|$)", correct_url + " ", t).rstrip()
            t = re.sub(r"https?://ainformed\.dev/articles/[\w.-]+", correct_url, t)
            t = re.sub(r"https?://ainformed\.dev(?!/articles/)(?:\s|$)", correct_url + " ", t).rstrip()
            fixed.append(t)
        thread_tweets = fixed

    # Upload image for top article thread
    top_media_id = None
    top_image_path = get_article_image_path(top)
    if top_image_path and not DRY_RUN:
        print(f"\nUploading image for thread: {top_image_path}")
        top_media_id = upload_media(top_image_path)

    print(f"\nPosting thread for: {top['title'][:70]}")
    if DRY_RUN:
        print("[DRY RUN MODE]")

    # Cap at 3 tweets per run to minimise pay-per-use API costs
    thread_tweets = thread_tweets[:3]

    # Strip https:// links from all tweets except the last — X charges $0.20/post with a link
    def _strip_links(text: str) -> str:
        return re.sub(r"https?://\S+", "", text).strip()

    if len(thread_tweets) > 1:
        thread_tweets = [_strip_links(t) for t in thread_tweets[:-1]] + [thread_tweets[-1]]

    ids = post_thread(thread_tweets, first_media_id=top_media_id)
    print(f"\nThread posted: {len(ids)} tweets")
    if ids and not DRY_RUN:
        tweeted_slugs.add(top["slug"])

    # Persist which articles we've tweeted
    if not DRY_RUN:
        _save_tweeted_slugs(tweeted_slugs)
        print(f"\nSaved {len(tweeted_slugs)} tweeted slugs.")


if __name__ == "__main__":
    main()
