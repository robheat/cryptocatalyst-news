"""
run_youtube.py — YouTube Shorts pipeline orchestrator.

Runs all five phases in sequence:
  1. generate_shorts_script.py — select articles, generate scripts via Venice AI
  2. generate_tts.py           — synthesize audio with Kokoro ONNX
  3. generate_broll.py         — generate Venice AI B-roll background images
  4. render_short.py           — render 1080x1920 MP4 videos with Ken Burns motion
  5. upload_youtube.py         — upload to YouTube (dry run by default)

Usage:
  # Dry run (default — generates everything but does not upload):
  python run_youtube.py

  # Real upload:
  $env:YT_DRY_RUN = "0"
  python run_youtube.py

  # Generate scripts only:
  $env:YT_STOP_AFTER = "script"
  python run_youtube.py

Environment variables:
  YT_DRY_RUN         = "1" (default) | "0"  — skip actual YouTube upload when "1"
  YT_SCRIPTS_PER_RUN = "2" (default)         — how many new scripts to generate
  YT_STOP_AFTER      = "script"|"tts"|"broll"|"render" — stop pipeline after named phase
  XTTS_SPEAKER_WAV   = /path/to/voice.wav    — custom voice reference (optional)
  XTTS_SPEAKER       = "Claribel Dervla"     — built-in XTTS speaker name
  YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN — for upload
"""
import os
import subprocess
import sys
from pathlib import Path

PIPELINE_DIR = Path(__file__).parent

PHASES = [
    ("script", "generate_shorts_script.py"),
    ("tts",    "generate_tts.py"),
    ("broll",  "generate_broll.py"),
    ("render", "render_short.py"),
    ("upload", "upload_youtube.py"),
]


def run_step(script_name: str) -> None:
    result = subprocess.run(
        [sys.executable, str(PIPELINE_DIR / script_name)],
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        print(f"\n[FAIL] {script_name} exited with code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    stop_after = os.environ.get("YT_STOP_AFTER", "").lower()
    dry_run = os.environ.get("YT_DRY_RUN", "1")

    print("=== CryptoCatalyst YouTube Shorts Pipeline ===")
    if dry_run == "1":
        print("  Mode: DRY RUN (set YT_DRY_RUN=0 to upload for real)")
    print()

    for phase_name, script_name in PHASES:
        print(f"--- Phase: {phase_name} ({script_name}) ---")
        run_step(script_name)
        print()

        if stop_after and phase_name == stop_after:
            print(f"Stopped after phase '{phase_name}' as requested.")
            break

    print("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
