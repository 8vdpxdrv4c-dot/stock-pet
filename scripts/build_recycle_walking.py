import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'build' / 'video-tools'))
os.environ['U2NET_HOME'] = str(ROOT / 'build' / 'video-models')
os.environ['OMP_NUM_THREADS'] = '2'
from PIL import Image
from rembg import new_session, remove

session = new_session('u2netp', providers=['CPUExecutionProvider'])
paths = sorted((ROOT / 'build' / 'recycle-video-frames').glob('frame_*.png'))
raw_dir = ROOT / 'build' / 'recycle-matted'
raw_dir.mkdir(exist_ok=True)
for index, path in enumerate(paths):
    output = raw_dir / path.name
    if not output.exists():
        remove(Image.open(path), session=session).save(output)
    if index % 12 == 0:
        print(f'Matted {index + 1}/{len(paths)}', flush=True)
    if '--sample' in sys.argv:
        break

if '--sample' not in sys.argv:
    frames = [Image.open(raw_dir / p.name).convert('RGBA') for p in paths]
    bounds = [im.getchannel('A').point(lambda a: 255 if a > 100 else 0).getbbox() for im in frames]
    crop = (max(0, min(b[0] for b in bounds)-4), max(0, min(b[1] for b in bounds)-4),
            min(640, max(b[2] for b in bounds)+4), min(360, max(b[3] for b in bounds)+4))
    output_dir = ROOT / 'assets' / 'cat' / 'recycle-walking-video'
    output_dir.mkdir(exist_ok=True)
    for index, im in enumerate(frames):
        im = im.crop(crop)
        im.thumbnail((360, 260), Image.Resampling.LANCZOS)
        im.save(output_dir / f'walk_{index:03}.png')
    print(f'Saved {len(frames)} frames, fixed crop {crop}', flush=True)
