"""Render candidate 2: bathtub whale. Usage: python3 whale.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render import Canvas
import scene_whale

c = Canvas()
scene_whale.draw(c)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "candidates", "whale.png")
c.save(out)
print("wrote", out, os.path.getsize(out), "bytes")
