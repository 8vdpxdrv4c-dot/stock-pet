"""Build the reviewed playing loop from the user's video.

Use Python 3.12 with the existing build/video-tools matting dependencies.
Requires ffmpeg on PATH. Intermediate files stay under ignored build/.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/video-tools"))
from PIL import Image

REVIEWED_SOURCE_SHA256 = "79153325a30eeb4bce05d69e9c9e2f1e71f0b8b32981fe463aab59d840578239"
REVIEWED_SHARED_CROP = [14, 0, 948, 720]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "assets/cat/videos/playing-source.mp4")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--preview", action="store_true", help="Also refresh preview-playing-idle.gif")
    args = parser.parse_args()
    extracted = ROOT / "build/playing-extracted"
    output = ROOT / "assets/cat/playing-idle"
    reviewed_source = hashlib.sha256(args.source.read_bytes()).hexdigest() == REVIEWED_SOURCE_SHA256
    cleanup_args = (["--ground-alpha-band", "620", "640", "--shared-crop",
                     *map(str, REVIEWED_SHARED_CROP)] if reviewed_source else [])
    # Keep every source action, including the final raised paw.
    subprocess.run([sys.executable, str(ROOT / "scripts/build_eating_video.py"),
                    "--source", str(args.source), "--output", str(extracted),
                    "--fps", "24", "--solid-interior",
                    "--original-filename", "猫顽皮舔屏视频生成.mp4",
                    "--ffmpeg", args.ffmpeg, *cleanup_args], check=True)
    paths = sorted(extracted.glob("idle_*.png"))
    frames = []
    for path in paths:
        with Image.open(path) as image:
            frames.append(image.convert("RGBA"))
    # Returning through the actual source frames makes a clean loop without
    # ghosted crossfades. Do not duplicate either endpoint (which would pause).
    loop = frames + frames[-2:0:-1]
    output.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(loop):
        frame.save(output / f"idle_{index:03d}.png")
    for stale in output.glob("idle_*.png"):
        if int(stale.stem.removeprefix("idle_")) >= len(loop):
            stale.unlink()
    manifest = json.loads((extracted / "animation.json").read_text(encoding="utf-8"))
    manifest.update(source="../videos/playing-source.mp4", frame_count=len(loop),
                    playback="ping-pong without duplicated endpoints",
                    processing=manifest["processing"].replace("source frame order", "forward then reverse source frames"))
    if reviewed_source:
        manifest["ground_reflection_cleanup"] = {
            "method": "original-matte confidence gate after opaque-interior repair",
            "source_y_band": [620, 640], "confidence_range": [195, 245],
            "preserve": "source RGB, original crop/scale, 145 source frames, timing and ping-pong order",
        }
    (output / "animation.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.preview:
        subprocess.run([
            args.ffmpeg, "-hide_banner", "-loglevel", "error", "-framerate", "24",
            "-i", str(output / "idle_%03d.png"), "-filter_complex",
            "color=c=0xe9edf3:s=360x360:r=24[bg];"
            "[bg][0:v]overlay=shortest=1:format=auto,split[a][b];"
            "[a]palettegen=max_colors=256:stats_mode=full[p];"
            "[b][p]paletteuse=dither=sierra2_4a",
            "-loop", "0", "-y", str(ROOT / "preview-playing-idle.gif"),
        ], check=True)
    print(f"Saved playing loop: {len(loop)} frames, 24 fps", flush=True)


if __name__ == "__main__":
    main()
