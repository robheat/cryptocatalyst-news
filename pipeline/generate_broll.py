"""
generate_broll.py — Generate Venice AI B-roll background images for YouTube Shorts.

For each queue entry without brollImages: uses Venice AI LLM to craft 4 cinematic
image prompts from the article's title/tags/script, then generates those images
via Venice AI image generation. Images are saved per-slug in the cache directory.

Input:  content/.youtube-queue.json (entries without brollImages set)
Output: pipeline/cache/youtube/<slug>_bg_0.jpg .. _bg_3.jpg
        Updates queue item with "brollImages" list (status unchanged).

Usage:
  python generate_broll.py               # only process scripted/tts_done items
  python generate_broll.py --all         # process everything missing brollImages
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from venice_client import chat, generate_image

QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
CACHE_DIR  = Path(__file__).parent / "cache" / "youtube"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BROLL_SYSTEM_PROMPT = """\
You are a cinematographer creating image-generation prompts for YouTube Shorts B-roll.
Given an article title, tags, and short summary, write exactly 4 cinematic image prompts.

Each prompt must:
- Be 15-30 words, purely visual and highly descriptive
- Relate to a different aspect or angle of the news story
- Use photography/cinematography terms (golden hour, bokeh, wide angle, aerial, close-up)
- Vary shot type: one aerial/wide, one medium, one close-up, one atmospheric/mood shot
- Avoid text, logos, or human faces

Return ONLY a JSON array of 4 strings, no other text:
["prompt 1", "prompt 2", "prompt 3", "prompt 4"]
"""


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _generate_prompts(item: dict) -> list[str]:
    """Ask Venice AI LLM to produce 4 cinematic image prompts for this article."""
    script    = item.get("script", {})
    narration = " ".join(script.get("narration_lines", [])[:3])
    tags      = item.get("tags", [])

    user_msg = json.dumps({
        "title":   item["title"],
        "tags":    tags[:6],
        "summary": (narration or item.get("title", ""))[:300],
    }, ensure_ascii=False)

    try:
        response = chat(
            [
                {"role": "system", "content": BROLL_SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=512,
            disable_thinking=True,
        )
        response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
        m = re.search(r"\[.*\]", response, re.DOTALL)
        if m:
            prompts = json.loads(m.group(0))
            if isinstance(prompts, list) and len(prompts) >= 2:
                return [str(p) for p in prompts[:4]]
    except Exception as exc:
        print(f"  [WARN] LLM prompt generation failed: {exc}")

    # Fallback: generic prompts from tags
    tag1 = tags[0] if tags else "artificial intelligence"
    tag2 = tags[1] if len(tags) > 1 else "technology"
    return [
        f"Aerial wide shot of {tag1} infrastructure at golden hour, cinematic lighting, 8k",
        f"Close-up of {tag2} circuit patterns, glowing blue tones, shallow depth of field",
        f"Futuristic cityscape at night, {tag1} technology visible, neon reflections, moody",
        f"Dramatic wide angle of data center server rows, cool blue lighting, deep shadows",
    ]


def generate_broll_for(item: dict) -> list[str] | None:
    """Generate and save 4 B-roll images for one queue item. Returns saved paths."""
    slug = item["slug"]

    # Check if all 4 already exist
    existing = [str(CACHE_DIR / f"{slug}_bg_{i}.jpg") for i in range(4)]
    if all(Path(p).exists() for p in existing):
        print(f"  [CACHED] All 4 B-roll images already exist")
        return existing

    print(f"  Generating image prompts...")
    prompts = _generate_prompts(item)

    saved = []
    for i, prompt in enumerate(prompts):
        out_path = CACHE_DIR / f"{slug}_bg_{i}.jpg"
        if out_path.exists():
            saved.append(str(out_path))
            continue

        print(f"  [IMG {i + 1}/4] {prompt[:70]}...")
        try:
            image_bytes = generate_image(prompt)
            # Detect format and always save as jpg
            out_path.write_bytes(image_bytes)
            saved.append(str(out_path))
            print(f"    -> {out_path.name} ({len(image_bytes) // 1024}KB)")
        except Exception as exc:
            print(f"  [ERROR] Image {i + 1} failed: {exc}")

    return saved if saved else None


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Generate Venice AI B-roll images for YouTube Shorts")
    parser.add_argument(
        "--all", action="store_true",
        help="Process all items missing brollImages (including rendered/failed)",
    )
    args = parser.parse_args()

    if not QUEUE_FILE.exists():
        print("ERROR: .youtube-queue.json not found.")
        sys.exit(1)

    queue = load_queue()

    if args.all:
        pending = [item for item in queue["queue"] if not item.get("brollImages")]
    else:
        pending = [
            item for item in queue["queue"]
            if item["status"] in ("scripted", "tts_done") and not item.get("brollImages")
        ]

    if not pending:
        print("No items need B-roll images.")
        return

    print(f"Generating B-roll for {len(pending)} item(s)...")
    done = 0
    for item in pending:
        print(f"\n  -> {item['slug'][:64]}")
        paths = generate_broll_for(item)
        if paths:
            item["brollImages"] = paths
            done += 1

    save_queue(queue)
    print(f"\nB-roll generated for {done} item(s)")


if __name__ == "__main__":
    main()
