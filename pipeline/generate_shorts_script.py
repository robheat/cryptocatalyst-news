"""
generate_shorts_script.py — Select recent articles and generate YouTube Shorts scripts.

Input:  content/articles/*.json
Output: Updates content/.youtube-queue.json with new scripted entries
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venice_client import json_chat

CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"
QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
CACHE_DIR = Path(__file__).parent / "cache" / "youtube"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# How many NEW scripts to generate per run (1-2 to maintain weekly cadence)
MAX_NEW_SCRIPTS = int(os.environ.get("YT_SCRIPTS_PER_RUN", "2"))

# Categories preferred for Shorts (visual, high-interest topics)
PREFERRED_CATEGORIES = {"bitcoin", "ethereum", "defi"}

SCRIPT_SYSTEM_PROMPT = """\
You are a scriptwriter for CryptoCatalyst.news, a crypto news brand making YouTube Shorts.
Your audience is people new to crypto — curious, non-technical, want to know what this means for them.
Given an article (title, summary, body, tags, source), write a punchy 45-60 second narration script.

Requirements:
- Target: exactly 110-140 words total (maps to 45-60 seconds at ~150wpm TTS)
- hook: One bold opening sentence to grab attention instantly.
    Start with what just changed for everyday people — not the headline, not insider jargon.
    Use a surprise, warning, opportunity, deadline, or myth-buster angle.
    Do NOT start with "Imagine", "What if", or a rhetorical question.
- narration_lines: 4-6 short lines. Each line is one natural speech pause.
    Cover: what happened in plain English, why a normal person should care,
    a concrete example or analogy they can picture, and what they can do or try.
    Include at least one concrete fact from the article: a number, company, product, date, dollar amount, or policy detail.
    Explain any jargon in plain English.
    Include one specific consequence for a user, investor, customer, or builder.
    Keep each line under 20 words.
    Avoid generic filler and avoid repeating the title.
    Vary sentence openings so the script does not sound templated.
- cta: One closing line such as "For more crypto news made simple, visit cryptocatalyst dot news."
- Do NOT use hashtags, emojis, or markdown formatting.
- Use plain spoken language — this will be read aloud by a voice synthesizer.
- Say "cryptocurrency" (not "crypto") on first use so TTS sounds natural.
- Avoid abbreviations the listener may not recognise.

Respond with ONLY valid JSON:
{
  "hook": string,
  "narration_lines": [string, ...],
  "cta": string,
  "total_words": number
}
"""


def load_queue() -> dict:
    if QUEUE_FILE.exists():
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    return {"queue": []}


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def already_queued_slugs(queue: dict) -> set:
    return {item["slug"] for item in queue.get("queue", [])}


def score_article(article: dict) -> int:
    """Higher score = better candidate for a Short."""
    score = 0
    if article.get("category") in PREFERRED_CATEGORIES:
        score += 3
    if len(article.get("tags", [])) >= 4:
        score += 1
    published = article.get("publishedAt", "")
    if published:
        try:
            age_days = (
                datetime.now(timezone.utc) - datetime.fromisoformat(published)
            ).days
            if age_days <= 3:
                score += 5
            elif age_days <= 7:
                score += 2
        except Exception:
            pass
    return score


def generate_script(article: dict) -> dict | None:
    messages = [
        {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "title": article["title"],
                    "summary": article.get("summary", ""),
                    "body": article.get("body", "")[:1400],
                    "tags": article.get("tags", [])[:6],
                    "source_name": article.get("sourceName", ""),
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        result = json_chat(messages, temperature=0.5, max_tokens=512)
    except Exception as exc:
        print(f"  [ERROR] Script generation failed: {exc}")
        return None

    if not isinstance(result, dict) or "hook" not in result:
        print("  [ERROR] Invalid script shape from Venice AI")
        return None

    return result


def main() -> None:
    queue = load_queue()
    queued = already_queued_slugs(queue)

    articles: list[dict] = []
    for f in sorted(CONTENT_DIR.glob("*.json"), reverse=True):
        try:
            article = json.loads(f.read_text(encoding="utf-8"))
            slug = article.get("slug", "")
            if slug and slug not in queued:
                articles.append(article)
        except Exception:
            pass

    articles.sort(key=score_article, reverse=True)
    candidates = articles[:MAX_NEW_SCRIPTS]

    if not candidates:
        print("No new articles to script. Queue is up to date.")
        return

    print(f"Generating scripts for {len(candidates)} article(s)...")

    new_count = 0
    for article in candidates:
        slug = article["slug"]
        print(f"\n  → {slug[:70]}")

        script = generate_script(article)
        if not script:
            continue

        full_text = " ".join(
            [script["hook"]]
            + script.get("narration_lines", [])
            + [script.get("cta", "")]
        )
        script_hash = hashlib.sha256(full_text.encode()).hexdigest()[:16]

        entry = {
            "slug": slug,
            "title": article["title"],
            "category": article.get("category", "general"),
            "tags": article.get("tags", []),
            "articleSummary": article.get("summary", ""),
            "articleBody": article.get("body", "")[:1400],
            "imageUrl": article.get("imageUrl", ""),
            "articleUrl": f"https://cryptocatalyst.news/articles/{slug}",
            "script": script,
            "scriptHash": script_hash,
            "scriptText": full_text,
            "audioFile": None,
            "videoFile": None,
            "status": "scripted",
            "youtubeVideoId": None,
            "youtubeUrl": None,
            "privacy": "unlisted",
            "error": None,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "uploadedAt": None,
        }
        queue["queue"].append(entry)
        words = script.get("total_words", 0)
        print(f"  [OK] Scripted — {words} words (~{words // 2}s estimated)")
        new_count += 1

    save_queue(queue)
    print(f"\n✓ Added {new_count} script(s) to .youtube-queue.json")


if __name__ == "__main__":
    main()
