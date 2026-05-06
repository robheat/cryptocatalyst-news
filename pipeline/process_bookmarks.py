"""
process_bookmarks.py — End-to-end pipeline for bookmark-sourced articles.
1. Reads bookmark_stories.json (output of fetch_bookmarks.py)
2. Generates full articles via Venice AI (reuses generate_content.py logic)
3. Posts tweets for new articles (reuses post_twitter.py logic)

Run after fetch_bookmarks.py has fetched and saved bookmark stories.
"""

import json
import sys
from pathlib import Path

from generate_content import generate_article, CONTENT_DIR, IMAGES_DIR

CACHE_DIR = Path(__file__).parent / "cache"
INPUT_FILE = CACHE_DIR / "bookmark_stories.json"


def main():
    if not INPUT_FILE.exists():
        print("No bookmark_stories.json found — run fetch_bookmarks.py first.")
        return 0

    stories = json.loads(INPUT_FILE.read_text())
    if not stories:
        print("No bookmark stories to process.")
        return 0

    print(f"=== Processing {len(stories)} bookmarked stories ===")

    # Build set of existing source URLs
    existing_urls: set[str] = set()
    for f in CONTENT_DIR.iterdir():
        if f.suffix == ".json":
            try:
                existing_urls.add(json.loads(f.read_text()).get("sourceUrl", ""))
            except Exception:
                pass

    written = 0
    for i, story in enumerate(stories):
        print(f"\n[{i+1}/{len(stories)}] {story['title'][:80]}")

        if story["url"] in existing_urls:
            print("  → Skipped (article already exists)")
            continue

        article = generate_article(story)
        if article is None:
            print("  → Skipped (generation failed)")
            continue

        out_path = CONTENT_DIR / f"{article['slug']}.json"
        out_path.write_text(json.dumps(article, indent=2, ensure_ascii=False))
        print(f"  → Saved: {out_path.name}")
        existing_urls.add(story["url"])
        written += 1

    print(f"\nDone. Generated {written} article(s) from bookmarks.")
    return written


if __name__ == "__main__":
    count = main()
    if count == 0:
        print("No new articles generated.")
