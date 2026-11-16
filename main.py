"""Entrypoint: render the Golden Koi Ramen scene deterministically.

Writes entry.png next to this file and to $MAKEFUN_OUTPUT_DIR (default
/output) — the bytes are identical in both places, and two runs produce
byte-identical PNGs. Standard library only.
"""

import os

from scene_koi import render_scene


def main():
    png = render_scene()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "entry.png"), "wb") as f:
        f.write(png)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "entry.png"), "wb") as f:
            f.write(png)
    except OSError:
        pass


if __name__ == "__main__":
    main()
