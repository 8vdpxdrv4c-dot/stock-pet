"""Extract the supplied eating clip into a fixed-canvas transparent animation.

Run with Python 3.12 and the existing build/video-tools dependencies; pass
--ffmpeg with the path to an ffmpeg executable. No runtime video dependency.
For the current opaque cat clip, preserve the reviewed loop and leg repair:
    python scripts/build_eating_video.py --end-frame 103 --stabilize-alpha --solid-interior
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build/video-tools"))
os.environ["U2NET_HOME"] = str(ROOT / "build/video-models")
os.environ["OMP_NUM_THREADS"] = "2"

from PIL import Image
import numpy as np
from scipy.ndimage import binary_erosion, binary_fill_holes
from rembg import new_session, remove


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--source", type=Path, default=ROOT / "assets/cat/videos/eating-source-v7.mp4")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/cat/eating-video-v7")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--original-filename", default="10月3日(2).mp4")
    parser.add_argument("--end-frame", type=int, help="Exclusive source frame at the loop cut")
    parser.add_argument("--stabilize-alpha", action="store_true",
                        help="Suppress isolated alpha-mask changes using adjacent frames")
    parser.add_argument("--solid-interior", action="store_true",
                        help="Restore opaque cat/bowl interiors and their original source colours")
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error("Pass --ffmpeg with an ffmpeg executable path")
    if args.fps <= 0:
        parser.error("--fps must be positive")
    source = args.source.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    work = ROOT / "build" / ("eating-video-" + digest[:12] + f"-{args.fps}fps")
    raw, matted = work / "raw", work / "matted"
    output = args.output.resolve()
    for folder in (raw, matted, output):
        folder.mkdir(parents=True, exist_ok=True)
    manifest = output / "animation.json"
    if manifest.exists() and json.loads(manifest.read_text(encoding="utf-8"))["source_sha256"] != digest:
        raise RuntimeError("Output belongs to another source; use a new versioned output directory")
    subprocess.run([args.ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(source),
                    "-an", "-vf", f"fps={args.fps}", "-start_number", "0", "-y",
                    str(raw / "frame_%03d.png")], check=True)
    paths = sorted(raw.glob("frame_*.png"))
    if not paths:
        raise RuntimeError("No video frames extracted")
    source_frame_count = len(paths)
    if args.end_frame is not None:
        if not 1 <= args.end_frame <= source_frame_count:
            parser.error("--end-frame must be within the extracted source frames")
        paths = paths[:args.end_frame]
    session = new_session("u2netp", providers=["CPUExecutionProvider"])
    for i, path in enumerate(paths):
        destination = matted / path.name
        if not destination.exists():
            with Image.open(path) as frame:
                remove(frame, session=session).save(destination)
        if i % 16 == 0 or i == len(paths) - 1:
            print(f"Background removed: {i + 1}/{len(paths)}", flush=True)
    rendered = matted
    if args.stabilize_alpha or args.solid_interior:
        rendered = work / (f"processed-alpha-{len(paths)}"
                           f"-median{int(args.stabilize_alpha)}-solid{int(args.solid_interior)}")
        rendered.mkdir(parents=True, exist_ok=True)
        for i, path in enumerate(paths):
            # Filter only transparency; retain each source frame's RGB and motion.
            # Wrap neighbours at the chosen loop cut so its edges stay stable too.
            with Image.open(matted / path.name) as frame:
                alpha = np.array(frame.getchannel("A"))
            if args.stabilize_alpha:
                neighbours = []
                for index in ((i - 1) % len(paths), (i + 1) % len(paths)):
                    with Image.open(matted / paths[index].name) as frame:
                        neighbours.append(np.array(frame.getchannel("A")))
                previous, following = neighbours
                alpha = np.maximum(np.minimum(previous, alpha),
                                   np.minimum(np.maximum(previous, alpha), following))
            if args.solid_interior:
                # The cat and bowl are opaque. The model sometimes cuts holes
                # in pale legs for many consecutive frames, which a median
                # cannot repair. Fill the enclosed silhouette and solidify its
                # interior, leaving three source pixels of soft outer edging.
                interior = binary_erosion(binary_fill_holes(alpha >= 20), iterations=3)
                alpha = np.where(interior, 255, alpha).astype(np.uint8)
            # Recover actual source colours as well as opacity: the rembg RGBA
            # can have darkened RGB where it incorrectly removed a pale leg.
            with Image.open(path) as source_frame:
                frame = source_frame.convert("RGBA")
                frame.putalpha(Image.fromarray(alpha))
                frame.save(rendered / path.name)
            if i % 16 == 0 or i == len(paths) - 1:
                print(f"Alpha mask repaired: {i + 1}/{len(paths)}", flush=True)
    bounds = []
    for i, path in enumerate(paths):
        with Image.open(rendered / path.name) as frame:
            box = frame.getchannel("A").point(lambda alpha: 255 if alpha > 20 else 0).getbbox()
            if box is None:
                raise RuntimeError(f"Empty foreground at frame {i}")
            bounds.append(box)
            width, height = frame.size
    # One crop and one scale for the entire clip preserve its real movement.
    crop = (max(0, min(b[0] for b in bounds) - 4), max(0, min(b[1] for b in bounds) - 4),
            min(width, max(b[2] for b in bounds) + 4), min(height, max(b[3] for b in bounds) + 4))
    size, padding = 360, 8
    for i, path in enumerate(paths):
        with Image.open(rendered / path.name) as frame:
            foreground = frame.convert("RGBA").crop(crop)
            foreground.thumbnail((size - 2 * padding, size - 2 * padding), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size))
            canvas.alpha_composite(foreground, ((size - foreground.width) // 2,
                                               size - padding - foreground.height))
            canvas.save(output / f"idle_{i:03d}.png")
    # A shorter loop must not leave stale tail frames for the runtime to load.
    for stale in output.glob("idle_*.png"):
        if int(stale.stem.removeprefix("idle_")) >= len(paths):
            stale.unlink()
    manifest.write_text(json.dumps({
        "source": os.path.relpath(source, output).replace("\\", "/"), "source_sha256": digest,
        "original_filename": args.original_filename, "frame_count": len(paths),
        "source_frame_count": source_frame_count, "source_frame_range": [0, len(paths)],
        "fps": args.fps, "timer_interval_ms": round(1000 / args.fps), "canvas_size": [size, size],
        "shared_crop": crop, "padding": padding,
        "alpha_stabilization": "loop-aware three-frame median" if args.stabilize_alpha else "none",
        "solid_interior": args.solid_interior,
        "interior_repair": "filled silhouette; opaque interior; 3px soft outer edge; original source RGB"
                           if args.solid_interior else "none",
        "processing": "u2netp alpha mask; shared crop/scale; source frame order; no generated in-between frames",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(paths)} transparent frames to {output}", flush=True)


if __name__ == "__main__":
    main()
