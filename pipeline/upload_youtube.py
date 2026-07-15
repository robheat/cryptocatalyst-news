"""
upload_youtube.py — Upload rendered Shorts to YouTube via the Data API v3.

Input:  content/.youtube-queue.json (entries with status == "rendered")
Output: Updates queue entries with youtubeVideoId and status == "uploaded"

Safety: runs in DRY RUN mode by default (prints metadata, no upload).
        Set YT_DRY_RUN=0 to upload for real.

Credentials: set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
             (or run setup_youtube_auth.py to generate a local token file).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
YOUTUBE_CATEGORY_TECH = "28"  # Science & Technology
MAX_TITLE_LEN = 100


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def build_metadata(item: dict) -> dict:
    title = item["title"]
    # Append #Shorts so YouTube places it on the Shorts shelf
    if len(title) <= 91:
        yt_title = title + " #Shorts"
    else:
        yt_title = title[:91] + " #Shorts"

    script_text = item.get("scriptText", "")
    article_url = item.get("articleUrl", "https://www.cryptocatalyst.news")
    description = (
        f"{script_text}\n\n"
        f"Read more: {article_url}\n\n"
        "CryptoCatalyst.news — Daily crypto and blockchain news, curated and explained."
    )

    tags = item.get("tags", []) + [
        "crypto",
        "blockchain",
        "tech news",
        "crypto news",
        "Shorts",
    ]

    requested_privacy = str(item.get("privacy", "public")).strip().lower()
    if requested_privacy != "public":
        # Enforce public visibility for Shorts uploads, even for older queue rows.
        print(f"  [INFO] Overriding queue privacy '{requested_privacy}' -> 'public'.")

    return {
        "title": yt_title[:MAX_TITLE_LEN],
        "description": description[:5000],
        "tags": tags[:500],
        "categoryId": YOUTUBE_CATEGORY_TECH,
        "privacyStatus": "public",
    }


def upload_video(credentials, item: dict) -> str | None:
    """Upload a single video. Returns YouTube video ID or None on failure."""
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        print("ERROR: google-api-python-client not installed.")
        print("Run: pip install -r requirements-youtube.txt")
        sys.exit(1)

    video_path = Path(item["videoFile"])
    if not video_path.exists():
        print(f"  [ERROR] Video file missing: {video_path}")
        return None

    meta = build_metadata(item)
    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta["tags"],
            "categoryId": meta["categoryId"],
        },
        "status": {
            "privacyStatus": meta["privacyStatus"],
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    # Resumable upload with exponential backoff on transient errors
    response = None
    backoff = 2
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"    Uploading... {pct}%", end="\r")
        except Exception as exc:
            if backoff > 64:
                raise
            print(f"\n  [RETRY] Transient error, backing off {backoff}s: {exc}")
            time.sleep(backoff)
            backoff *= 2

    video_id = response.get("id")
    print(f"\n  [OK] https://youtube.com/watch?v={video_id}  ({meta['privacyStatus']})")
    return video_id


def main() -> None:
    dry_run = os.environ.get("YT_DRY_RUN", "1") == "1"

    if not QUEUE_FILE.exists():
        print("ERROR: .youtube-queue.json not found.")
        sys.exit(1)

    queue = load_queue()
    pending = [item for item in queue["queue"] if item["status"] == "rendered"]

    if not pending:
        print("No rendered entries awaiting upload.")
        return

    if dry_run:
        print(f"DRY RUN — {len(pending)} video(s) would be uploaded:")
        for item in pending:
            meta = build_metadata(item)
            print(f"\n  Title:   {meta['title']}")
            print(f"  Privacy: {meta['privacyStatus']}")
            print(f"  Tags:    {', '.join(meta['tags'][:5])}...")
            print(f"  Video:   {item.get('videoFile', 'n/a')}")
        print("\nSet YT_DRY_RUN=0 to upload for real.")
        return

    # Real upload
    sys.path.insert(0, str(Path(__file__).parent))
    from youtube_auth import get_credentials
    credentials = get_credentials()

    print(f"Uploading {len(pending)} Short(s) to YouTube...")
    done = 0
    for item in pending:
        print(f"\n  → {item['slug'][:60]}")
        try:
            video_id = upload_video(credentials, item)
            if video_id:
                item["youtubeVideoId"] = video_id
                item["youtubeUrl"] = f"https://youtube.com/watch?v={video_id}"
                item["privacy"] = "public"
                item["status"] = "uploaded"
                item["uploadedAt"] = datetime.now(timezone.utc).isoformat()
                done += 1
        except Exception as exc:
            print(f"  [ERROR] {exc}")
            item["status"] = "failed"
            item["error"] = str(exc)

    save_queue(queue)
    print(f"\n✓ Uploaded {done} Short(s)")


if __name__ == "__main__":
    main()
