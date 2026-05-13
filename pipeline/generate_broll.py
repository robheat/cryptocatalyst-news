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
Given an article title, tags, summary, body excerpt, and 4 narration beats, write exactly 4 cinematic image prompts.
Write the prompts in the same order as the beats so the visuals can track the narration.

Each prompt must:
- Be 15-30 words, purely visual and highly descriptive
- Visualize the specific beat it corresponds to, not a generic crypto wallpaper
- Relate to a different aspect or angle of the news story
- Prefer concrete objects and settings from the story: payment terminals, wallets, server racks, congressional documents, market screens, mining rigs, data centers, apps, or infrastructure
- Use photography/cinematography terms (golden hour, bokeh, wide angle, aerial, close-up)
- Vary shot type: one aerial/wide, one medium, one close-up, one atmospheric/mood shot
- Avoid text, logos, or recognizable human faces

Return ONLY a JSON array of 4 strings, no other text:
["prompt 1", "prompt 2", "prompt 3", "prompt 4"]
"""


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _beat_texts(item: dict) -> list[str]:
    script = item.get("script", {})
    beats = [script.get("hook", "")] + script.get("narration_lines", [])
    beats = [beat.strip() for beat in beats if beat.strip()]
    fallback = item.get("articleSummary") or item.get("title", "")
    while len(beats) < 4 and fallback:
        beats.append(fallback)
    return beats[:4]


def _generate_prompts(item: dict) -> list[str]:
    """Ask Venice AI LLM to produce 4 cinematic image prompts for this article."""
    tags = item.get("tags", [])
    beats = _beat_texts(item)

    user_msg = json.dumps({
        "title": item["title"],
        "tags": tags[:6],
        "summary": item.get("articleSummary", item.get("title", ""))[:300],
        "body_excerpt": item.get("articleBody", "")[:800],
        "beats": beats,
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

    # Fallback: keep prompts tied to the first four script beats so visuals still track the narration
    beat1, beat2, beat3, beat4 = (beats + [item.get("title", "")])[:4]
    return [
        f"Aerial wide editorial scene illustrating {beat1}, dramatic golden hour lighting, cinematic realism, no text, no faces",
        f"Medium shot illustrating {beat2}, realistic devices and infrastructure, shallow depth of field, moody editorial style",
        f"Close-up editorial image illustrating {beat3}, detailed textures, bokeh highlights, realistic finance-tech environment",
        f"Atmospheric mood shot illustrating {beat4}, cinematic shadows, story-specific setting, realistic editorial photography",
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
