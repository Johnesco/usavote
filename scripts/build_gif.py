"""Build texas-2d-to-3d.gif, shown on why.html and in the README: the flat county map of the 2026 Texas U.S. Senate race tilting
and rising into columns stacked by how each county voted.

Each frame is scripts/gif.html?f=N, drawn by the same code as the site's 3D map (map3d.js) and screenshotted at 900x684 in one
headless Chrome or Edge, which scripts/gif-frames.mjs drives. This serves the repo root itself on a spare port, so nothing else needs to be running. The page loads
three.js, d3-geo, topojson-client and the county shapes from a CDN, so it needs a connection.

Run:  python scripts/build_gif.py            the whole GIF (81 frames, a few minutes)
      python scripts/build_gif.py 0 45 80    only those frames, as PNGs in the frames folder, to look at
      python scripts/build_gif.py spin       texas-senate-2026-spin.gif instead: one turn around the raised columns, from
                                             scripts/spin.html at 800x600 (72 frames). Frame numbers work here too.
Needs Pillow, and Node 22 or later.
"""
import functools
import http.server
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SPIN = sys.argv[1:2] == ["spin"]  # the other GIF: one turn around the raised columns (scripts/spin.html)
if SPIN:
    OUT, PAGE = ROOT / "texas-senate-2026-spin.gif", "spin.html"
    LAST = 71         # scripts/spin.html's FRAMES - 1: the frame after it would match f=0, so the GIF loops
    W, H = 800, 600
    HOLD_FIRST, STEP, HOLD_LAST = 90, 90, 90  # milliseconds: an even turn, about 6.5 seconds round
else:
    OUT, PAGE = ROOT / "texas-2d-to-3d.gif", "gif.html"
    LAST = 80         # scripts/gif.html's FRAMES: f=0 is flat, f=LAST is fully raised
    W, H = 900, 684
    HOLD_FIRST, STEP, HOLD_LAST = 1500, 50, 3500  # milliseconds
BROWSERS = ["chrome", "msedge", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "google-chrome", "chromium"]


def browser():
    for b in BROWSERS:
        if shutil.which(b) or Path(b).is_file(): return shutil.which(b) or b
    sys.exit("No Chrome or Edge found: add its path to BROWSERS.")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}/scripts/{PAGE}"
exe = browser()
only = [int(a) for a in sys.argv[1 + SPIN:]]
frames_dir = Path(tempfile.mkdtemp(prefix="texas-gif-"))
todo = only or list(range(LAST + 1))
subprocess.run(["node", str(ROOT / "scripts" / "gif-frames.mjs"), exe, url, str(frames_dir), str(W), str(H), *map(str, todo)], check=True)
images = [Image.open(frames_dir / f"{f:03d}.png").convert("RGB") for f in todo]
for f, im in zip(todo, images):
    # a frame taken before the map drew would be all background: the map's reds and blues are far from the page's near-black
    assert im.size == (W, H) and sum(1 for r, g, b in im.resize((90, 68)).getdata() if max(r, g, b) > 120) > 200, f"frame {f} is blank"
print(f"{len(images)} frames drawn", flush=True)
if only:
    print(f"frames are in {frames_dir}")
    sys.exit()

# one palette for every frame, taken from the first, middle and last, so colors don't shimmer from frame to frame
strip = Image.new("RGB", (W * 3, H))
for k, im in enumerate((images[0], images[len(images) // 2], images[-1])): strip.paste(im, (W * k, 0))
palette = strip.quantize(255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
frames[0].save(OUT, save_all=True, append_images=frames[1:], loop=0, optimize=False, disposal=1,
               duration=[HOLD_FIRST] + [STEP] * (len(frames) - 2) + [HOLD_LAST])
shutil.rmtree(frames_dir, ignore_errors=True)
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.2f} MB, {len(frames)} frames)")
