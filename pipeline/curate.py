"""
curate.py — Use Venice AI to score, rank, and select the top AI stories.
Input:  pipeline/cache/raw_stories.json
Output: pipeline/cache/curated_stories.json
"""
import json
import re
import sys
from pathlib import Path

from venice_client import json_chat

CACHE_DIR = Path(__file__).parent / "cache"
INPUT_FILE = CACHE_DIR / "raw_stories.json"
OUTPUT_FILE = CACHE_DIR / "curated_stories.json"
ARTICLES_DIR = Path(__file__).parent.parent / "content" / "articles"

TARGET_STORIES = int(__import__("os").environ.get("TARGET_STORIES", "8"))


def _load_recent_titles() -> list[str]:
    """Load titles of recently published articles to avoid topic repetition."""
    titles: list[str] = []
    if not ARTICLES_DIR.exists():
        return titles
    for f in sorted(ARTICLES_DIR.iterdir(), reverse=True):
        if f.suffix == ".json":
            try:
                titles.append(json.loads(f.read_text()).get("title", ""))
            except Exception:
                pass
        if len(titles) >= 50:  # last 50 articles is enough context
            break
    return titles

SCORE_SYSTEM_PROMPT = """\
You are a senior crypto journalist and editor for CryptoCatalyst.news, a daily crypto and blockchain news digest.
Your job is to evaluate news story candidates and select the most newsworthy for today's edition.

Scoring criteria (each 0-10):
- relevance: Is it genuinely about crypto, blockchain, DeFi, Bitcoin, Ethereum, or Web3? (0 = unrelated, 10 = core crypto story)
- novelty: Is it new, surprising, or a genuine development? (0 = stale/obvious, 10 = major scoop)
- significance: Does it matter to investors, developers, or the industry? (0 = trivial, 10 = major impact)
- readability: Is the title clear and informative? (0 = clickbait/vague, 10 = precise and informative)

Exclude: duplicates, non-crypto stories, pure opinion pieces, press releases with no substance.
Strongly penalize stories that cover the same topic as recently published articles (listed below).
Favor DIVERSE topics — spread coverage across Bitcoin, Ethereum, DeFi, NFTs, Web3, policy, and broader blockchain.

Respond ONLY with a valid JSON array. Each element must have:
  "index": <int, same as input index>,
  "relevance": <int 0-10>,
  "novelty": <int 0-10>,
  "significance": <int 0-10>,
  "readability": <int 0-10>,
  "include": <bool>
"""

DEDUPE_SYSTEM_PROMPT = """\
You are an editor deduplicating a crypto news list. 
Given a list of stories (with index, title, url), identify groups of stories that are about 
the exact same event or announcement. For each duplicate group, keep only the best-sourced story.
Respond ONLY with a valid JSON array of index integers to KEEP (remove duplicates, keep originals).
"""


def score_batch(stories: list[dict], recent_titles: list[str]) -> list[dict]:
    """Score a batch of up to 40 stories with a single Venice AI call."""
    candidates = [
        {"index": i, "title": s["title"], "description": s["description"], "source": s["source_name"]}
        for i, s in enumerate(stories)
    ]
    recent_context = ""
    if recent_titles:
        recent_context = "\n\nRecently published articles (penalize similar topics):\n" + "\n".join(
            f"- {t}" for t in recent_titles[:30]
        )
    messages = [
        {"role": "system", "content": SCORE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Score these {len(candidates)} story candidates:\n\n{json.dumps(candidates, ensure_ascii=False)}{recent_context}",
        },
    ]
    scores = json_chat(messages, temperature=0.1, max_tokens=4096)
    return scores


def deduplicate(stories: list[dict]) -> list[dict]:
    """Remove near-duplicate stories using Venice AI."""
    candidates = [
        {"index": i, "title": s["title"], "url": s["url"]}
        for i, s in enumerate(stories)
    ]
    messages = [
        {"role": "system", "content": DEDUPE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Deduplicate this story list:\n\n{json.dumps(candidates, ensure_ascii=False)}",
        },
    ]
    keep_indices = json_chat(messages, temperature=0.0, max_tokens=512)
    if not isinstance(keep_indices, list):
        return stories  # fallback: keep all
    return [stories[i] for i in keep_indices if i < len(stories)]


def curate() -> list[dict]:
    if not INPUT_FILE.exists():
        print("ERROR: raw_stories.json not found. Run fetch_feeds.py first.")
        sys.exit(1)

    raw: list[dict] = json.loads(INPUT_FILE.read_text())
    print(f"Loaded {len(raw)} raw stories")

    if not raw:
        return []

    recent_titles = _load_recent_titles()
    print(f"Recent articles for topic diversity: {len(recent_titles)}")

    # Score in batches of 40
    all_scores: list[dict] = []
    batch_size = 40
    for i in range(0, len(raw), batch_size):
        batch = raw[i : i + batch_size]
        print(f"Scoring batch {i}\u2013{i+len(batch)-1} ...")
        scored = score_batch(batch, recent_titles)
        # Adjust indices for global list
        for s in scored:
            s["index"] = i + s["index"]
        all_scores.extend(scored)

    # Build score map
    score_map = {s["index"]: s for s in all_scores}

    # Filter to included stories and compute composite score
    included = []
    for i, story in enumerate(raw):
        sc = score_map.get(i)
        if not sc or not sc.get("include", False):
            continue
        composite = (
            sc.get("relevance", 0) * 3
            + sc.get("novelty", 0) * 2
            + sc.get("significance", 0) * 3
            + sc.get("readability", 0) * 1
        ) / 9
        included.append({**story, "_composite_score": round(composite, 2)})

    print(f"Included after scoring: {len(included)}")

    # Sort by composite score descending
    included.sort(key=lambda s: s["_composite_score"], reverse=True)

    # Deduplicate top 30
    top_pool = included[:30]
    deduped = deduplicate(top_pool)
    print(f"After deduplication: {len(deduped)}")

    # Take top N
    selected = deduped[:TARGET_STORIES]
    print(f"Selected {len(selected)} stories for today")
    return selected


if __name__ == "__main__":
    selected = curate()
    OUTPUT_FILE.write_text(json.dumps(selected, indent=2, ensure_ascii=False))
    print(f"Saved to {OUTPUT_FILE}")
