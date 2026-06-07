"""
backfill_images.py — Generate missing hero images for articles that have no imageUrl.

Finds all articles in content/articles/ where imageUrl is null/empty, generates
an image via Venice AI, saves it, and updates the article JSON.

Usage:
  python backfill_images.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_content import generate_article_image

CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"
IMAGES_DIR = Path(__file__).parent.parent / "public" / "images" / "articles"


def main():
    articles = sorted(CONTENT_DIR.glob("*.json"))
    missing = [
        f for f in articles
        if not json.loads(f.read_text(encoding="utf-8")).get("imageUrl")
    ]
    print(f"Found {len(missing)} articles missing images (out of {len(articles)} total)")

    ok = 0
    failed = 0
    for i, path in enumerate(missing):
        article = json.loads(path.read_text(encoding="utf-8"))
        print(f"\n[{i+1}/{len(missing)}] {article['slug'][:70]}")
        image_url = generate_article_image(article)
        if image_url:
            article["imageUrl"] = image_url
            path.write_text(json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  → Updated: {path.name}")
            ok += 1
        else:
            print(f"  → FAILED — imageUrl stays null")
            failed += 1

    print(f"\nDone. {ok} images generated, {failed} failed.")


if __name__ == "__main__":
    main()
