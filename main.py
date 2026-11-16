"""Golden Koi Ramen -- entrypoint for make.fun ai-excited-01.

Renders the scene at 2048x2048 (supersampled), downsamples to
1024x1024 for crisp anti-aliased edges, and writes entry.png.

Writes to $MAKEFUN_OUTPUT_DIR/entry.png when set, else
/output/entry.png when /output exists, else beside this file.
Pure standard library only. Deterministic: two runs write identical
bytes.
"""

import os
import time

from render import Canvas
from scene_koi import draw

SUPER = 2048
FINAL = 1024


def main():
    t0 = time.time()
    big = Canvas(SUPER, SUPER)
    draw(big)
    small = big.downsample()
    assert small.w == FINAL and small.h == FINAL
    data = small.png_bytes()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not outdir:
        outdir = "/output" if os.path.isdir("/output") else \
            os.path.dirname(os.path.abspath(__file__))
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes, %dx%d) in %.1fs"
          % (path, len(data), FINAL, FINAL, time.time() - t0))


if __name__ == "__main__":
    main()
