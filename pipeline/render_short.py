"""
render_short.py — Render YouTube Shorts video (1080x1920) with Ken Burns animated backgrounds.

Input:  content/.youtube-queue.json (entries with status == "tts_done" or "rendered")
Output: pipeline/cache/youtube/<slug>.mp4 + updates queue status to "rendered"

Visual style: News ticker / TV chyron with cinematic motion
  - Each caption segment gets its own B-roll background image (or article image fallback)
  - Background animates with Ken Burns pan effect (20% overscan, 6 movement patterns)
  - Fast numpy compositing: gradient + UI overlay pre-computed per segment, one blend per frame
  - CryptoCatalyst.news logo bar top, category badge, article title, bottom chyron, progress bar
"""
import bisect
import json
import os
import sys
import textwrap
from pathlib import Path

QUEUE_FILE = Path(__file__).parent.parent / "content" / ".youtube-queue.json"
CACHE_DIR  = Path(__file__).parent / "cache" / "youtube"
PUBLIC_DIR = Path(__file__).parent.parent / "public"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
FPS          = 30
KB_SCALE     = 1.20  # 20% overscan: ~216px horizontal / ~384px vertical travel

# Palette
INDIGO     = (99, 102, 241)
WHITE      = (255, 255, 255)
NEAR_BLACK = (12, 10, 22)
CHYRON_BG  = (15, 12, 30, 230)   # near-black, semi-opaque

CHYRON_H = 260
CHYRON_Y = VIDEO_HEIGHT - CHYRON_H - 20  # 1640

CAPTION_FONT_SIZE  = 130   # word-highlight karaoke text size
CAPTION_WRAP_W     = 12    # chars per line (~80% video width at 130 px)
CAPTION_MAX_LINES  = 8     # max wrapped lines
CAPTION_LINE_H     = 156   # line spacing
CAPTION_AREA_TOP   = 650   # top of caption zone (below header/title)
CAPTION_AREA_BOT   = 1820  # bottom of caption zone (above CTA)

WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
FONT_BLACK = str(WINDOWS_FONT_DIR / "ariblk.ttf")
FONT_BOLD  = str(WINDOWS_FONT_DIR / "arialbd.ttf")
FONT_REG   = str(WINDOWS_FONT_DIR / "arial.ttf")

# Linux fallbacks (fonts-liberation package, installed in CI)
_FONT_BOLD_LINUX = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_FONT_REG_LINUX  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def load_queue() -> dict:
    return json.loads(QUEUE_FILE.read_text())


def save_queue(data: dict) -> None:
    QUEUE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _font(path: str, size: int):
    from PIL import ImageFont
    for p in [path, FONT_BOLD, FONT_REG, _FONT_BOLD_LINUX, _FONT_REG_LINUX]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


_GRADIENT_PIL = None


def _get_gradient_pil():
    """Lazily build and cache the static gradient overlay (same for every frame)."""
    global _GRADIENT_PIL
    if _GRADIENT_PIL is not None:
        return _GRADIENT_PIL
    from PIL import Image, ImageDraw
    grad = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(grad)
    # Bottom gradient — darkens lower 70% for chyron readability
    grad_start = int(VIDEO_HEIGHT * 0.30)
    steps = VIDEO_HEIGHT - grad_start
    for i in range(steps):
        alpha = int(200 * (i / steps) ** 1.4)
        y = grad_start + i
        d.line([(0, y), (VIDEO_WIDTH, y)], fill=(*NEAR_BLACK, alpha))
    # Top gradient — subtle darkening for logo legibility
    for i in range(220):
        alpha = int(160 * (1 - i / 220) ** 1.2)
        d.line([(0, i), (VIDEO_WIDTH, i)], fill=(0, 0, 0, alpha))
    _GRADIENT_PIL = grad
    return _GRADIENT_PIL


def prepare_broll_image(image_path) -> "np.ndarray":
    """Scale + blur image to KB_SCALE overscan size for Ken Burns movement.

    Returns numpy array of shape (big_h, big_w, 3) uint8.
    """
    import numpy as np
    from PIL import Image

    big_w = int(VIDEO_WIDTH  * KB_SCALE)
    big_h = int(VIDEO_HEIGHT * KB_SCALE)

    path = Path(image_path) if image_path else None
    if path and path.exists():
        img = Image.open(path).convert("RGB")
        ir  = img.width / img.height
        tr  = big_w / big_h
        if ir > tr:
            h, w = big_h, int(big_h * ir)
        else:
            w, h = big_w, int(big_w / ir)
        img  = img.resize((w, h), Image.LANCZOS)
        left = (w - big_w) // 2
        top  = (h - big_h) // 2
        img  = img.crop((left, top, left + big_w, top + big_h))
    else:
        img = Image.new("RGB", (big_w, big_h), NEAR_BLACK)

    return np.array(img)


def apply_kenburns(big: "np.ndarray", t: float, duration: float, direction: int) -> "np.ndarray":
    """Return a VIDEO_WIDTH x VIDEO_HEIGHT crop from the overscan image at time t.

    Linearly interpolates between start/end crop positions — smooth cinematic pan.
    """
    mx = big.shape[1] - VIDEO_WIDTH   # max x offset (pixels)
    my = big.shape[0] - VIDEO_HEIGHT  # max y offset (pixels)
    p  = t / max(duration, 0.001)     # progress 0..1

    # 6 cinematic pan patterns: (x_start, y_start, x_end, y_end)
    patterns = [
        (0,      0,      mx,     my    ),  # 0: top-left  → bottom-right
        (mx,     0,      0,      my    ),  # 1: top-right → bottom-left
        (0,      my,     mx,     0     ),  # 2: bottom-left → top-right
        (mx,     my,     0,      0     ),  # 3: bottom-right → top-left
        (mx//2,  0,      mx//2,  my    ),  # 4: vertical pan down
        (0,      my//2,  mx,     my//2 ),  # 5: horizontal pan right
    ]
    x0, y0, x1, y1 = patterns[direction % len(patterns)]
    x = max(0, min(int(x0 + (x1 - x0) * p), mx))
    y = max(0, min(int(y0 + (y1 - y0) * p), my))
    return big[y : y + VIDEO_HEIGHT, x : x + VIDEO_WIDTH]


def build_ui_overlay(
    title: str,
    category: str,
    caption_lines: list,
    caption_idx: int,
    n_captions: int,
) -> "PIL.Image":
    """Render per-segment UI elements as transparent RGBA PIL Image (no background).

    Called once per caption segment — result reused for every frame of that segment.
    """
    from PIL import Image, ImageDraw

    overlay = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    f_logo    = _font(FONT_BOLD,  48)
    f_tag     = _font(FONT_BOLD,  34)
    f_title   = _font(FONT_BLACK, 72)
    f_cta     = _font(FONT_BOLD,  36)
    PAD = 52

    # ── TOP BAR: logo + indigo accent line ──────────────────────────────────
    bar_h = 110
    bar   = Image.new("RGBA", (VIDEO_WIDTH, bar_h), (0, 0, 0, 0))
    bd    = ImageDraw.Draw(bar)
    bd.rectangle([(0, 0), (8, bar_h)], fill=INDIGO)
    bd.text((PAD + 16, bar_h // 2), "CryptoCatalyst", font=f_logo, fill=WHITE, anchor="lm")
    bd.text(
        (PAD + 16 + int(f_logo.getlength("CryptoCatalyst")), bar_h // 2),
        ".news", font=f_logo, fill=INDIGO, anchor="lm",
    )
    overlay.alpha_composite(bar, (0, 36))

    # ── CATEGORY BADGE ──────────────────────────────────────────────────────
    cat_text = category.upper()
    cat_w    = int(f_tag.getlength(cat_text)) + 40
    cat_h    = 52
    badge    = Image.new("RGBA", (cat_w, cat_h), (*INDIGO, 220))
    bd2      = ImageDraw.Draw(badge)
    bd2.text((cat_w // 2, cat_h // 2), cat_text, font=f_tag, fill=WHITE, anchor="mm")
    overlay.alpha_composite(badge, (PAD, 170))

    # ── ARTICLE TITLE ───────────────────────────────────────────────────────
    title_y = 260
    for line in textwrap.wrap(title, width=18)[:4]:
        draw.text((PAD + 3, title_y + 3), line, font=f_title, fill=(0, 0, 0, 160), anchor="lm")
        draw.text((PAD,     title_y    ), line, font=f_title, fill=WHITE,           anchor="lm")
        title_y += 88

    # ── CTA TEXT (bottom) ───────────────────────────────────────────────────
    cta_y = VIDEO_HEIGHT - 72
    draw.text((VIDEO_WIDTH // 2 + 2, cta_y + 2), "More at cryptocatalyst.news",
              font=f_cta, fill=(0, 0, 0, 180), anchor="mm")
    draw.text((VIDEO_WIDTH // 2, cta_y), "More at cryptocatalyst.news",
              font=f_cta, fill=(*INDIGO, 220), anchor="mm")

    # ── PROGRESS BAR ────────────────────────────────────────────────────────
    prog_y = VIDEO_HEIGHT - 18
    prog_w = int(VIDEO_WIDTH * (caption_idx + 1) / max(n_captions, 1))
    draw.rectangle([(0, prog_y), (VIDEO_WIDTH, VIDEO_HEIGHT)], fill=(30, 30, 50, 255))
    draw.rectangle([(0, prog_y), (prog_w,      VIDEO_HEIGHT)], fill=(*INDIGO, 255))

    return overlay


def _build_chyron_word_slice(
    caption_text: str, highlight_word_idx: int, font
) -> "tuple[np.ndarray, np.ndarray]":
    """Render caption text with one word highlighted as an RGBA chyron slice.

    Returns (premult_rgb, inv_alpha) numpy arrays shaped (CHYRON_H, VIDEO_WIDTH, *)
    for fast per-frame compositing.
    """
    import numpy as np
    from PIL import Image, ImageDraw

    img  = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    lines       = textwrap.wrap(caption_text, width=CAPTION_WRAP_W)[:CAPTION_MAX_LINES]
    space_w     = int(font.getlength(" "))
    block_h     = len(lines) * CAPTION_LINE_H
    cap_y       = (CAPTION_AREA_TOP + CAPTION_AREA_BOT - block_h) // 2 + CAPTION_LINE_H // 2
    word_offset = 0

    for line_text in lines:
        words       = line_text.split()
        word_widths = [int(font.getlength(w)) for w in words]
        total_w     = sum(word_widths) + space_w * max(0, len(words) - 1)
        x           = VIDEO_WIDTH // 2 - total_w // 2

        for j, (word, ww) in enumerate(zip(words, word_widths)):
            gidx = word_offset + j
            if gidx == highlight_word_idx:
                # Indigo pill behind the active word
                draw.rounded_rectangle(
                    [x - 10, cap_y - 70, x + ww + 10, cap_y + 70],
                    radius=20, fill=(*INDIGO, 230),
                )
                color = WHITE
            elif gidx < highlight_word_idx:
                color = (80, 80, 110)    # already spoken — dimmed
            else:
                color = (200, 200, 220)  # not yet spoken — near-white
            # Drop shadow for readability without background scrim
            draw.text((x + 3, cap_y + 3), word, font=font, fill=(0, 0, 0, 200), anchor="lm")
            draw.text((x, cap_y), word, font=font, fill=color, anchor="lm")
            x += ww + (space_w if j < len(words) - 1 else 0)

        word_offset += len(words)
        cap_y       += CAPTION_LINE_H

    arr       = np.array(img).astype(np.float32)
    alpha     = arr[:, :, 3:4] / 255.0
    premult   = arr[:, :, :3] * alpha
    inv_alpha = 1.0 - alpha
    return premult, inv_alpha


def _build_fast_overlay(gradient_pil, ui_pil) -> "tuple[np.ndarray, np.ndarray]":
    """Pre-composite gradient + UI into arrays for fast per-frame numpy blending.

    Returns (premult_rgb, inv_alpha):
      - premult_rgb: float32 (H, W, 3) — pre-multiplied RGB of overlay
      - inv_alpha:   float32 (H, W, 1) — (1 - alpha); weight for background
    Per-frame blend: out = premult_rgb + kenburns_rgb * inv_alpha
    """
    import numpy as np
    from PIL import Image

    combined  = Image.alpha_composite(gradient_pil, ui_pil)
    arr       = np.array(combined).astype(np.float32)   # (H, W, 4) 0-255
    alpha     = arr[:, :, 3:4] / 255.0                  # (H, W, 1) 0-1
    premult   = arr[:, :, :3] * alpha                   # pre-multiplied RGB 0-255
    inv_alpha = 1.0 - alpha
    return premult, inv_alpha


def render_video(item: dict, force: bool = False) -> "Path | None":
    """Render one Short video with Ken Burns animated B-roll backgrounds."""
    import numpy as np
    try:
        from moviepy import VideoClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        print("ERROR: moviepy not installed. Run: pip install -r requirements-youtube.txt")
        sys.exit(1)

    slug        = item["slug"]
    title       = item["title"]
    category    = item.get("category", "general")
    audio_path  = Path(item["audioFile"])
    output_path = CACHE_DIR / f"{slug}.mp4"

    if output_path.exists() and not force:
        print(f"  [CACHED] {output_path.name}")
        return output_path

    # ── Resolve background images ────────────────────────────────────────────
    broll_paths = [Path(p) for p in item.get("brollImages", [])]
    valid_broll = [p for p in broll_paths if p.exists()]

    if valid_broll:
        bg_images = [prepare_broll_image(p) for p in valid_broll]
        print(f"  [BROLL] {len(bg_images)} Venice AI B-roll image(s)")
    else:
        image_url = item.get("imageUrl", "")
        art_img   = (PUBLIC_DIR / image_url.lstrip("/")) if image_url.startswith("/") else None
        bg_images = [prepare_broll_image(art_img)]
        print("  [BG] Article image + Ken Burns pan")

    # ── Caption lines ────────────────────────────────────────────────────────
    script        = item.get("script", {})
    caption_lines = (
        [script.get("hook", "")]
        + script.get("narration_lines", [])
        + [script.get("cta", "")]
    )
    caption_lines = [l for l in caption_lines if l.strip()]

    # ── Audio duration ───────────────────────────────────────────────────────
    try:
        ac       = AudioFileClip(str(audio_path))
        duration = ac.duration
        ac.close()
    except Exception as exc:
        print(f"  [ERROR] Cannot read audio: {exc}")
        return None

    n            = len(caption_lines)
    # Use per-line durations from TTS if available (accurate sync), else equal split
    raw_durations = item.get("audioLineDurations", [])
    if len(raw_durations) == n:
        seg_durations = raw_durations
        print(f"  [SYNC] Using per-line TTS durations: {[round(d,2) for d in seg_durations]}")
    else:
        seg_durations = [duration / n] * n
    gradient_pil = _get_gradient_pil()

    # ── Build animated clips ─────────────────────────────────────────────────
    try:
        clips = []
        for i in range(n):
            big_arr      = bg_images[i % len(bg_images)]
            direction    = i % 6
            caption_text = caption_lines[i]
            seg_duration = seg_durations[i]
            f_cap        = _font(FONT_BOLD, CAPTION_FONT_SIZE)

            # Base overlay: logo, title, chyron box + CTA + progress (no caption words)
            ui_base        = build_ui_overlay(title, category, caption_lines, i, n)
            base_pm, base_ia = _build_fast_overlay(gradient_pil, ui_base)

            # Flatten words across wrapped lines (same wrap used in _build_chyron_word_slice)
            words_flat = [
                w
                for ln in textwrap.wrap(caption_text, width=CAPTION_WRAP_W)[:CAPTION_MAX_LINES]
                for w in ln.split()
            ]
            n_words = max(1, len(words_flat))

            # Pre-render one chyron slice per word (highlight advances each slice)
            chyron_pms  = []
            chyron_ias  = []
            for w_idx in range(n_words):
                cpm, cia = _build_chyron_word_slice(caption_text, w_idx, f_cap)
                chyron_pms.append(cpm)
                chyron_ias.append(cia)

            # Proportional word timing (character-count based) with small onset delay
            # Onset delay accounts for TTS silence at start of each synthesized chunk
            ONSET = 0.12  # seconds before first word highlight appears
            char_counts = [max(1, len(w)) for w in words_flat]
            total_chars = sum(char_counts)
            speech_window = max(0.0, seg_duration - ONSET)
            word_starts = [
                ONSET + speech_window * sum(char_counts[:k]) / total_chars
                for k in range(n_words)
            ]

            def make_frame(
                t,
                big=big_arr, bpm=base_pm, bia=base_ia,
                cpms=chyron_pms, cias=chyron_ias,
                ws=word_starts, dur=seg_duration, d=direction,
            ):
                w_idx = max(0, min(bisect.bisect_right(ws, t) - 1, len(cpms) - 1))
                kb    = apply_kenburns(big, t, dur, d).astype(np.float32)
                out   = bpm + kb * bia
                # Full-screen composite of word-highlight overlay
                out   = cpms[w_idx] + out * cias[w_idx]
                return out.clip(0, 255).astype(np.uint8)

            clips.append(VideoClip(make_frame, duration=seg_duration))

        video = concatenate_videoclips(clips, method="compose")
        audio = AudioFileClip(str(audio_path))
        video = video.with_audio(audio)
        video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            threads=int(os.environ.get("FFMPEG_THREADS", "2")),
            preset="faster",
            logger=None,
        )
        video.close()
        audio.close()
    except Exception as exc:
        print(f"  [ERROR] Render failed: {exc}")
        import traceback
        traceback.print_exc()
        return None

    size_mb = output_path.stat().st_size // (1024 * 1024)
    print(f"  [OK] {output_path.name} — {duration:.1f}s, {size_mb}MB")
    return output_path


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-render even if MP4 already exists")
    args = parser.parse_args()

    if not QUEUE_FILE.exists():
        print("ERROR: .youtube-queue.json not found.")
        sys.exit(1)

    queue = load_queue()
    pending = (
        [item for item in queue["queue"] if item["status"] in ("tts_done", "rendered")]
        if args.force
        else [item for item in queue["queue"] if item["status"] == "tts_done"]
    )

    if not pending:
        print("No TTS-ready entries to render.")
        return

    print(f"Rendering {len(pending)} Short(s){'  [FORCE]' if args.force else ''}...")
    done = 0
    for item in pending:
        print(f"\n  -> {item['slug'][:60]}")
        output = render_video(item, force=args.force)
        if output:
            item["videoFile"] = str(output)
            item["status"]    = "rendered"
            done += 1
        else:
            item["status"] = "failed"

    save_queue(queue)
    print(f"\nRendered {done} Short(s)")


if __name__ == "__main__":
    main()
