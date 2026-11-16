"""Render candidate 1: golden koi ramen. Usage: python3 koi.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render import Canvas
import scene_koi

c = Canvas()
scene_koi.draw(c)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "candidates", "koi.png")
c.save(out)
print("wrote", out, os.path.getsize(out), "bytes")
