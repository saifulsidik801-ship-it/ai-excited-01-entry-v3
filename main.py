"""ai-excited-01 entry: GOLDEN KOI RAMEN.

A giant golden koi bursting out of a ramen bowl on a wooden table —
broth splashing in arcs, chopsticks flying, steam curling, warm
restaurant light. Pure standard library: the program draws the image
pixel by pixel with the rasterizer in render.py and the scene in
scene_koi.py, then writes it to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png when set).

Deterministic: fixed seeds, fixed compression level, no timestamps.
Run it twice and the PNG bytes are identical.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render import Canvas, output_path
import scene_koi


def main():
    canvas = Canvas()
    scene_koi.draw(canvas)
    path = output_path("entry.png")
    canvas.save(path)
    print("wrote", path)


if __name__ == "__main__":
    main()
