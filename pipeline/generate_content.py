"""
generate_content.py — Use Venice AI to write full article JSON from curated stories.
Input:  pipeline/cache/curated_stories.json
Output: content/articles/<slug>.json (one per story, committed to repo)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from venice_client import chat, json_chat, generate_image

CACHE_DIR = Path(__file__).parent / "cache"
INPUT_FILE = CACHE_DIR / "curated_stories.json"
CONTENT_DIR = Path(__file__).parent.parent / "content" / "articles"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR = Path(__file__).parent.parent / "public" / "images" / "articles"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = ["bitcoin", "ethereum", "defi", "nft", "policy", "web3", "general"]

ARTICLE_SYSTEM_PROMPT = """\
You are a senior crypto journalist writing for CryptoCatalyst.news, a daily crypto and blockchain news digest.
Your readers are mostly curious newcomers — people excited about crypto but not necessarily technical experts.
Given a raw story (title, description, source), write a complete article in JSON format.

Requirements:
- title: Crisp, informative headline (max 120 chars). Not clickbait.
- summary: Two concise sentences explaining the key takeaway in plain English. (~50 words)
    Write as if explaining to a smart friend who doesn't follow crypto closely.
    Include the strongest concrete detail available when one exists: a number, company name, product, date, quote, or policy change.
- body: Three clear paragraphs (~250 words total), or 4-5 paragraphs when the source has enough detail:
    Paragraph 1: What happened — the core news in plain language. Avoid jargon; briefly explain any technical terms.
    Paragraph 2: The most important supporting details — preserve names, figures, dates, products, and notable claims from the source.
    Paragraph 3: Why it matters to everyday people — what does this change, enable, or affect for regular users?
    Paragraph 4 or final paragraph: What to do or watch next — be concrete. Name the trigger, risk, timeline, audience, or next step.
  Separate paragraphs with \\n\\n.
- category: One of: bitcoin, ethereum, defi, nft, policy, web3, general
- tags: 3-6 lowercase single-word or hyphenated tags
- twitterThread: An array of EXACTLY 3 tweet strings (each ≤260 chars).
    Style: punchy, conversational, specific.
    Avoid repetitive stock openers like "In plain English" or "Here's what this means for you" unless they feel truly natural.
    Tweet 1: A strong hook about the user-facing consequence, plus one specific fact when available.
    Tweet 2: The key explanation in plain English, including at least one concrete supporting detail.
    Tweet 3: A practical takeaway, warning, or next step, and it must end with: "Read more → ARTICLE_URL"
    IMPORTANT: tweets 1 and 2 must contain NO URLs or links. Only tweet 3 may have a link.
    Do NOT use hashtags.
    Do NOT be generic.
    Do NOT waste a tweet repeating the headline.

- standaloneTweet: A single catchy tweet (≤280 chars) that could go viral on its own.
  Lead with what this means for everyday crypto users, not industry insiders.
    Make a non-expert feel like they just learned something useful.
    Include one concrete fact when available.
  Do NOT include any URLs or links.
  No hashtags.

Write factually. Do not hallucinate details not present in the input.
If the description is thin, stay close to what's stated.
Preserve the strongest available specifics instead of flattening them into generic summaries.
If the source is thin or uncertain, say that plainly rather than padding with filler.
Avoid vague endings like "keep an eye on this" unless you say exactly what to watch for.
If a "full_content" field is provided, use it as your primary source:
  - Extract ALL notable facts, figures, names, statistics, and announcements
  - Cover more ground in the body — expand to 4-5 paragraphs (~350 words) if the content warrants it
  - Paragraph 1: What happened — the core news in plain language.
  - Paragraph 2: Key details and supporting facts drawn from the full content.
  - Paragraph 3: Why it matters to everyday people.
  - Paragraph 4 (if applicable): Additional notable points or sub-stories from the article.
  - Final paragraph: How you can use it or what to watch — concrete, actionable angle.

Respond with ONLY valid JSON matching this schema:
{
  "title": string,
  "summary": string,
  "body": string,
  "category": string,
  "tags": string[],
  "twitterThread": string[],
  "standaloneTweet": string
}
"""

HASHTAG_RE = re.compile(r"(?<!\w)#\w+")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def _clean_text(text: str) -> str:
    text = HASHTAG_RE.sub("", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_thread(tweets: list[str], correct_url: str) -> list[str]:
    cleaned = [_clean_text(t) for t in tweets if _clean_text(t)]

    first = cleaned[0] if cleaned else ""
    second = cleaned[1] if len(cleaned) > 1 else ""
    third = cleaned[2] if len(cleaned) > 2 else "Read more"

    third = third.replace("ARTICLE_URL", correct_url)
    third = re.sub(r"https?://\S+", correct_url, third)
    if correct_url not in third:
        third = f"{third.rstrip('. ')} Read more → {correct_url}".strip()

    normalized = [tweet for tweet in [first, second, third] if tweet]
    return normalized[:3]


def generate_article(story: dict) -> dict | None:
    """Generate a full article JSON from a curated story using Venice AI."""
    user_payload: dict = {
        "title": story["title"],
        "description": story.get("description", ""),
        "source_name": story["source_name"],
        "source_url": story["url"],
        "category_hint": story.get("category_hint", "general"),
        "pub_date": story.get("pub_date", ""),
    }
    if story.get("full_content"):
        user_payload["full_content"] = story["full_content"]

    messages = [
        {"role": "system", "content": ARTICLE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(user_payload, ensure_ascii=False),
        },
    ]

    try:
        max_tok = 3000 if story.get("full_content") else 2048
        result = json_chat(messages, temperature=0.4, max_tokens=max_tok)
    except Exception as exc:
        print(f"  [ERROR] Venice AI call failed: {exc}")
        return None

    # Validate and normalize
    if not isinstance(result, dict) or "title" not in result:
        print(f"  [ERROR] Invalid response shape")
        return None

    category = result.get("category", story.get("category_hint", "general"))
    if category not in CATEGORIES:
        category = "general"

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = f"{today}-{slugify(result['title'])}"
    correct_url = f"https://cryptocatalyst.news/articles/{slug}"

    def _fix_urls(text: str) -> str:
        """Replace any cryptocatalyst.news article URL (including LLM-guessed slugs with dots)
        with the authoritative URL for this article."""
        text = text.replace("ARTICLE_URL", correct_url)
        text = re.sub(r"https?://cryptocatalyst\.news/articles/[\w.-]+", correct_url, text)
        text = re.sub(r"https?://cryptocatalyst\.news(?!/articles/)(?:\s|$)", correct_url + " ", text).rstrip()
        # Also catch any lingering ainformed.dev URLs from LLM output
        text = re.sub(r"https?://ainformed\.dev/articles/[\w.-]+", correct_url, text)
        text = re.sub(r"https?://ainformed\.dev(?!/articles/)(?:\s|$)", correct_url + " ", text).rstrip()
        return text

    fixed_thread = _normalize_thread([_fix_urls(t) for t in result.get("twitterThread", [])], correct_url)
    fixed_standalone = _clean_text(_fix_urls(result.get("standaloneTweet", "")))

    article = {
        "slug": slug,
        "title": result["title"],
        "summary": result.get("summary", ""),
        "body": result.get("body", ""),
        "sourceUrl": story["url"],
        "sourceName": story["source_name"],
        "category": category,
        "tags": result.get("tags", [])[:6],
        "publishedAt": datetime.now(timezone.utc).isoformat(),
        "imageUrl": None,
        "twitterThread": fixed_thread,
        "standaloneTweet": fixed_standalone,
    }

    # Generate article image
    image_url = generate_article_image(article)
    if image_url:
        article["imageUrl"] = image_url

    return article


IMAGE_PROMPT_SYSTEM = """\
You are a visual editor creating story-specific hero image prompts for a crypto news site.
Given an article title, summary, tags, and body excerpt, write one concise cinematic prompt
(max 220 chars) for a compelling editorial image.
Prefer concrete scenes, objects, locations, documents, devices, market screens, payment flows,
server rooms, or legislative settings that fit the story.
Do NOT default to generic glowing coins, abstract blockchain grids, or random cyberpunk cityscapes
unless the story is truly about those visuals.
Do NOT include any text, letters, logos, or recognizable faces.
Respond with ONLY the image prompt text, nothing else."""


def generate_article_image(article: dict) -> str | None:
    """Generate a hero image for the article using Venice AI image generation."""
    try:
        # Use LLM to craft a good image prompt from the article
        image_prompt = chat(
            [
                {"role": "system", "content": IMAGE_PROMPT_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Title: {article['title']}\n"
                        f"Summary: {article['summary']}\n"
                        f"Tags: {', '.join(article.get('tags', []))}\n"
                        f"Body excerpt: {article.get('body', '')[:450]}"
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=100,
            disable_thinking=True,
        )
        # Strip any residual thinking blocks and quotes
        image_prompt = re.sub(r"<think>.*?</think>", "", image_prompt, flags=re.DOTALL).strip().strip('"')
        print(f"  [IMG] Prompt: {image_prompt[:80]}...")

        # Generate image via Venice AI
        image_bytes = generate_image(image_prompt)

        # Save to public/images/articles/ — detect format from magic bytes
        ext = "png"
        if image_bytes[:4] == b"RIFF":
            ext = "webp"
        elif image_bytes[:3] == b"\xff\xd8\xff":
            ext = "jpg"
        image_filename = f"{article['slug']}.{ext}"
        image_path = IMAGES_DIR / image_filename
        image_path.write_bytes(image_bytes)
        print(f"  [IMG] Saved: {image_filename} ({len(image_bytes)//1024}KB)")

        return f"/images/articles/{image_filename}"
    except Exception as exc:
        print(f"  [IMG ERROR] {exc}")
        return None


def generate_all():
    if not INPUT_FILE.exists():
        print("ERROR: curated_stories.json not found. Run curate.py first.")
        sys.exit(1)

    curated: list[dict] = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    print(f"Generating articles for {len(curated)} stories...")

    # Build set of source URLs that already have articles
    existing_urls: set[str] = set()
    for f in CONTENT_DIR.iterdir():
        if f.suffix == ".json":
            try:
                existing_urls.add(json.loads(f.read_text(encoding="utf-8")).get("sourceUrl", ""))
            except Exception:
                pass

    written = 0
    skipped = 0
    for i, story in enumerate(curated):
        print(f"\n[{i+1}/{len(curated)}] {story['title'][:80]}")

        # Skip if we already have an article for this source URL
        if story["url"] in existing_urls:
            print("  → Skipped (article already exists for this URL)")
            skipped += 1
            continue

        article = generate_article(story)
        if article is None:
            print("  → Skipped (generation failed)")
            continue

        out_path = CONTENT_DIR / f"{article['slug']}.json"
        out_path.write_text(json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  → Saved: {out_path.name}")
        existing_urls.add(story["url"])
        written += 1

    print(f"\nDone. Generated {written}/{len(curated)} articles ({skipped} skipped as duplicates).")
    return written


if __name__ == "__main__":
    generate_all()
