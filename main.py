"""Entrypoint: render the Golden Koi Ramen scene to entry.png.

Deterministic (pure stdlib, fixed hash noise): two runs produce a
byte-identical PNG. Writes to $MAKEFUN_OUTPUT_DIR/entry.png when set,
and always to ./entry.png next to this file.
"""

import os

from render import Canvas
from scene_koi import draw_scene


def main():
    cv = Canvas(1024, 1024)
    draw_scene(cv)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    targets = ["entry.png"]
    if out_dir:
        targets.append(os.path.join(out_dir, "entry.png"))
    for path in targets:
        cv.save_png(path)
        print("wrote", path)


if __name__ == "__main__":
    main()
