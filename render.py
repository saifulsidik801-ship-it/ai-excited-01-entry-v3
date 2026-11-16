"""Pure-stdlib 2D rasterizer for the ai-excited-01 v3 entry.

Draws 1024x1024 images with no third-party libraries: the grading
container runs main.py with the standard library only, so this module
uses nothing beyond math / os / random / struct / zlib.

Deterministic: fixed seeds, fixed zlib level, no timestamps anywhere.
Run the program twice and the PNG bytes are identical.
"""

import math
import os
import random
import struct
import sys
import zlib

W = 1024
H = 1024


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(c0, c1, t):
    return (
        int(lerp(c0[0], c1[0], t)),
        int(lerp(c0[1], c1[1], t)),
        int(lerp(c0[2], c1[2], t)),
    )


class Canvas:
    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    # -- low level -----------------------------------------------------
    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i] = rgb[0]
            self.px[i + 1] = rgb[1]
            self.px[i + 2] = rgb[2]

    def blend(self, x, y, rgb, a):
        if a <= 0.0:
            return
        if a >= 1.0:
            self.set(x, y, rgb)
            return
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i] = int(rgb[0] * a + self.px[i] * (1.0 - a))
            self.px[i + 1] = int(rgb[1] * a + self.px[i + 1] * (1.0 - a))
            self.px[i + 2] = int(rgb[2] * a + self.px[i + 2] * (1.0 - a))

    def _span(self, y, x0, x1, rgb, a=1.0):
        """Fill one horizontal run on row y (inclusive)."""
        if y < 0 or y >= self.h:
            return
        x0 = int(max(0, x0))
        x1 = int(min(self.w - 1, x1))
        if x1 < x0:
            return
        if a >= 1.0:
            i = self._idx(x0, y)
            n = x1 - x0 + 1
            self.px[i:i + n * 3] = bytes(rgb) * n
        else:
            for x in range(x0, x1 + 1):
                self.blend(x, y, rgb, a)

    # -- fills ---------------------------------------------------------
    def fill(self, rgb):
        self.px[:] = bytes(rgb) * (self.w * self.h)

    def vgrad(self, top, bottom):
        for y in range(self.h):
            c = lerp_rgb(top, bottom, y / (self.h - 1))
            self._span(y, 0, self.w - 1, c)

    def hgrad(self, left, right):
        for y in range(self.h):
            for x in range(self.w):
                pass  # replaced by row-wise spans below (kept simple)
        for x in range(self.w):
            c = lerp_rgb(left, right, x / (self.w - 1))
            i0 = x * 3
            for y in range(self.h):
                i = (y * self.w + x) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def radial(self, cx, cy, r, inner, outer):
        """Radial gradient disc: inner colour at centre, outer at edge."""
        r = int(r)
        for y in range(max(0, cy - r), min(self.h, cy + r + 1)):
            dy = (y - cy) / r
            dx = math.sqrt(max(0.0, 1.0 - dy * dy))
            x0 = int(cx - dx * r)
            x1 = int(cx + dx * r)
            for x in range(max(0, x0), min(self.w - 1, x1) + 1):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
                self.blend(x, y, lerp_rgb(inner, outer, min(1.0, d)), 1.0)

    def glow(self, cx, cy, r, rgb, peak=0.55):
        """Soft light pool: alpha falls off quadratically to the edge."""
        r = int(r)
        for y in range(max(0, cy - r), min(self.h, cy + r + 1)):
            for x in range(max(0, cx - r), min(self.w - 1, cx + r + 1)):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
                if d < 1.0:
                    self.blend(x, y, rgb, peak * (1.0 - d) * (1.0 - d))

    # -- shapes --------------------------------------------------------
    def ellipse(self, cx, cy, rx, ry, rgb, alpha=1.0, feather=0):
        rx = int(rx)
        ry = int(ry)
        if rx <= 0 or ry <= 0:
            return
        if feather > 0:
            self.ellipse(cx, cy, rx + feather, ry + feather, rgb,
                         alpha * 0.30)
        for y in range(max(0, cy - ry), min(self.h, cy + ry + 1)):
            dy = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self._span(y, cx - dx, cx + dx, rgb, alpha)

    def circle(self, cx, cy, r, rgb, alpha=1.0, feather=0):
        self.ellipse(cx, cy, r, r, rgb, alpha, feather)

    def ring(self, cx, cy, r, w, rgb, alpha=1.0):
        """Circle outline of width w."""
        for k in range(int(w)):
            rr = r - k
            if rr <= 0:
                break
            self._circle_outline(cx, cy, rr, rgb, alpha)

    def _circle_outline(self, cx, cy, r, rgb, alpha):
        steps = max(24, int(2 * math.pi * r))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            self.blend(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)),
                       rgb, alpha)

    def ellipse_ring(self, cx, cy, rx, ry, w, rgb, alpha=1.0):
        """Ellipse outline of width w (sampled perimeter)."""
        steps = max(48, int(2 * math.pi * max(rx, ry)))
        for k in range(int(w)):
            for i in range(steps):
                a = 2 * math.pi * i / steps
                self.blend(int(cx + (rx - k) * math.cos(a)),
                           int(cy + (ry - k) * math.sin(a)), rgb, alpha)

    def poly(self, pts, rgb, alpha=1.0):
        """Scanline polygon fill (even-odd). pts: list of (x, y)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                self._span(y, xs[k], xs[k + 1], rgb, alpha)

    def line(self, x0, y0, x1, y1, w, rgb, alpha=1.0):
        """Thick line with round caps, drawn as a chain of discs."""
        dx = x1 - x0
        dy = y1 - y0
        dist = math.hypot(dx, dy)
        steps = max(2, int(dist / max(1.0, w * 0.45)) + 1)
        r = w / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.circle(int(x0 + dx * t), int(y0 + dy * t), int(math.ceil(r)),
                        rgb, alpha)

    def bezier(self, p0, p1, p2, p3, n=40):
        pts = []
        for i in range(n + 1):
            t = i / n
            mt = 1.0 - t
            x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0]
                 + 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
            y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1]
                 + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
            pts.append((x, y))
        return pts

    def curve(self, p0, p1, p2, p3, w, rgb, alpha=1.0, n=40):
        pts = self.bezier(p0, p1, p2, p3, n)
        for i in range(len(pts) - 1):
            self.line(int(pts[i][0]), int(pts[i][1]),
                      int(pts[i + 1][0]), int(pts[i + 1][1]),
                      w, rgb, alpha)

    def tube(self, spine, radii, rgb, alpha=1.0):
        """A tapering body along a polyline spine: overlapping discs."""
        for (x, y), r in zip(spine, radii):
            self.circle(int(x), int(y), int(max(1, r)), rgb, alpha)

    # -- small details -------------------------------------------------
    def droplet(self, x, y, r, rgb, hl=True):
        self.circle(x, y, r, rgb, 1.0)
        if hl and r >= 4:
            self.circle(x - int(r * 0.3), y - int(r * 0.35),
                        max(1, int(r * 0.28)), (255, 255, 255), 0.85)

    def bubble(self, x, y, r, alpha=0.55):
        self.circle(x, y, r, (255, 255, 255), alpha * 0.35)
        self.ring(x, y, r, 2, (255, 255, 255), alpha)
        self.circle(x - int(r * 0.35), y - int(r * 0.35),
                    max(1, int(r * 0.22)), (255, 255, 255), alpha * 0.9)

    def sparkle(self, x, y, r, rgb=(255, 255, 255), alpha=0.9):
        self.line(x - r, y, x + r, y, 2, rgb, alpha)
        self.line(x, y - r, x, y + r, 2, rgb, alpha)
        self.circle(x, y, max(1, r // 3), rgb, alpha)

    def speckle(self, count, x0, x1, y0, y1, rgb, rmin=1, rmax=3, seed=7,
                alpha=1.0):
        rnd = random.Random(seed)
        for _ in range(count):
            self.circle(rnd.randint(x0, x1), rnd.randint(y0, y1),
                        rnd.randint(rmin, rmax), rgb, alpha)

    # -- output --------------------------------------------------------
    def png_bytes(self):
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.px[y * stride:(y + 1) * stride]
        comp = zlib.compress(bytes(raw), 6)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", comp) + chunk(b"IEND", b""))

    def save(self, path):
        d = os.path.dirname(os.path.abspath(path))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.png_bytes())
        return path


def output_path(name="entry.png"):
    """Where the program writes its image: MAKEFUN_OUTPUT_DIR, else
    /output when writable, else beside the script."""
    env = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env:
        os.makedirs(env, exist_ok=True)
        return os.path.join(env, name)
    for cand in ("/output",
                 os.path.dirname(os.path.abspath(sys.argv[0] or "main.py"))):
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".wtest")
            with open(probe, "wb") as f:
                f.write(b"")
            os.remove(probe)
            return os.path.join(cand, name)
        except OSError:
            continue
    return os.path.join(
        os.path.dirname(os.path.abspath(sys.argv[0] or "main.py")), name)
