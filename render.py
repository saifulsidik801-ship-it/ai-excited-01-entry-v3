"""Pure-stdlib rasterizer for the ai-excited-01 entry.

The scene is rendered at 2x (2048x2048) and downsampled to 1024x1024
with a 2x2 box average, so every edge is crisp and anti-aliased --
the "HD" lever, inside the competition's 1024x1024 / 1 MiB gate.

Standard library only: a bytearray framebuffer, scanline fills
(C-speed slice assignment), bezier tubes, and a zlib PNG encoder.
No PIL, no numpy, no network. Deterministic: fixed seeds, no
hash-order dependence, zlib output is byte-stable.
"""

import math
import random
import zlib


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def mix(c1, c2, t):
    """Linear blend of two RGB tuples."""
    return (
        int(round(c1[0] + (c2[0] - c1[0]) * t)),
        int(round(c1[1] + (c2[1] - c1[1]) * t)),
        int(round(c1[2] + (c2[2] - c1[2]) * t)),
    )


def shade(c, f):
    """Multiply an RGB tuple by a scalar factor."""
    return (
        int(clamp(c[0] * f, 0, 255)),
        int(clamp(c[1] * f, 0, 255)),
        int(clamp(c[2] * f, 0, 255)),
    )


class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    # -- fills ---------------------------------------------------------
    def fill(self, color):
        pat = bytes(color)
        self.buf[:] = pat * (self.w * self.h)

    def vgrad(self, c_top, c_bot):
        """Vertical gradient, top color to bottom color."""
        w3 = self.w * 3
        for y in range(self.h):
            t = y / (self.h - 1)
            self.buf[y * w3:(y + 1) * w3] = bytes(mix(c_top, c_bot, t)) * self.w

    def _row_fill(self, y, x0, x1, pat):
        """Fill pixels x0..x1 (inclusive) on row y with 3-byte pattern."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        n = x1 - x0 + 1
        s = (y * self.w + x0) * 3
        self.buf[s:s + n * 3] = pat * n

    # -- shapes --------------------------------------------------------
    def disc(self, cx, cy, r, color):
        """Filled circle, integer centre/radius."""
        if r <= 0:
            return
        pat = bytes(color)
        r2 = r * r
        y0 = max(0, cy - r)
        y1 = min(self.h - 1, cy + r)
        for y in range(y0, y1 + 1):
            dy = y - cy
            dx = math.isqrt(r2 - dy * dy)
            self._row_fill(y, cx - dx, cx + dx, pat)

    def ellipse(self, cx, cy, rx, ry, color):
        if rx <= 0 or ry <= 0:
            return
        pat = bytes(color)
        y0 = max(0, cy - ry)
        y1 = min(self.h - 1, cy + ry)
        for y in range(y0, y1 + 1):
            dy = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1.0 - dy * dy)))
            self._row_fill(y, cx - dx, cx + dx, pat)

    def rellipse(self, cx, cy, rx, ry, angle_deg, color):
        """Filled ellipse rotated by angle_deg (clockwise, degrees)."""
        if rx <= 0 or ry <= 0:
            return
        pat = bytes(color)
        th = math.radians(angle_deg)
        u, v = math.cos(th), math.sin(th)
        a = u * u / (rx * rx) + v * v / (ry * ry)
        bcoef = 2.0 * u * v * (1.0 / (rx * rx) - 1.0 / (ry * ry))
        ccoef = v * v / (rx * rx) + u * u / (ry * ry)
        span = int(max(rx, ry)) + 1
        y0 = max(0, cy - span)
        y1 = min(self.h - 1, cy + span)
        for y in range(y0, y1 + 1):
            dy = y - cy
            b = bcoef * dy
            c = ccoef * dy * dy - 1.0
            disc = b * b - 4.0 * a * c
            if disc < 0:
                continue
            sq = math.sqrt(disc)
            x_lo = int((-b - sq) / (2.0 * a)) + cx
            x_hi = int((-b + sq) / (2.0 * a)) + cx
            self._row_fill(y, x_lo, x_hi, pat)

    def poly(self, pts, color):
        """Filled polygon, even-odd scanline."""
        if len(pts) < 3:
            return
        pat = bytes(color)
        ys = [p[1] for p in pts]
        ymin = max(0, int(min(ys)))
        ymax = min(self.h - 1, int(max(ys)))
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self._row_fill(y, int(xs[j]), int(xs[j + 1]), pat)

    def plus(self, cx, cy, s, color, width=3):
        """Small '+' sparkle."""
        pat = bytes(color)
        hw = width // 2
        self._row_fill(cy, cx - s, cx + s, pat)
        for y in range(cy - s, cy + s + 1):
            self._row_fill(y, cx - hw, cx + hw, pat)

    # -- strokes / tubes ----------------------------------------------
    def tube(self, pts, r0, r1, color, step=2.0):
        """Polyline stroke with radius tapering r0 -> r1."""
        if len(pts) < 2:
            return
        segs = []
        total = 0.0
        for a, b in zip(pts, pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            segs.append((a, b, L))
            total += L
        if total <= 0:
            return
        n = max(2, int(total / step))
        si = 0
        acc = 0.0
        for i in range(n + 1):
            d = total * i / n
            while si < len(segs) - 1 and d > acc + segs[si][2]:
                acc += segs[si][2]
                si += 1
            a, b, L = segs[si]
            t = 0.0 if L == 0 else (d - acc) / L
            t = clamp(t, 0.0, 1.0)
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            r = r0 + (r1 - r0) * (d / total)
            self.disc(int(round(x)), int(round(y)), max(1, int(round(r))), color)

    def bezier3(self, p0, p1, p2, p3, steps=48):
        """Sample a cubic bezier into a list of points."""
        pts = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1.0 - t
            x = (mt ** 3) * p0[0] + 3 * (mt ** 2) * t * p1[0] + \
                3 * mt * (t ** 2) * p2[0] + (t ** 3) * p3[0]
            y = (mt ** 3) * p0[1] + 3 * (mt ** 2) * t * p1[1] + \
                3 * mt * (t ** 2) * p2[1] + (t ** 3) * p3[1]
            pts.append((x, y))
        return pts

    def bezier2(self, p0, p1, p2, steps=32):
        pts = []
        for i in range(steps + 1):
            t = i / steps
            mt = 1.0 - t
            x = (mt ** 2) * p0[0] + 2 * mt * t * p1[0] + (t ** 2) * p2[0]
            y = (mt ** 2) * p0[1] + 2 * mt * t * p1[1] + (t ** 2) * p2[1]
            pts.append((x, y))
        return pts

    def ellipse_arc_tube(self, cx, cy, rx, ry, a0, a1, width, color, steps=64):
        """Stroke along part of an ellipse outline (angles in degrees)."""
        pts = []
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        self.tube(pts, width, width, color, step=2.0)

    def soft_disc(self, cx, cy, r, glow, bg, alpha_max=0.30):
        """Soft glowing disc: concentric rings pre-mixed toward the local
        background colour, so no per-pixel alpha blending is needed."""
        rings = [(1.00, 0.06), (0.88, 0.12), (0.75, 0.20), (0.62, 0.30),
                 (0.50, 0.42), (0.38, 0.56), (0.26, 0.72), (0.15, 0.90)]
        for frac, afrac in rings:
            col = mix(bg, glow, alpha_max * afrac)
            self.disc(cx, cy, max(1, int(r * frac)), col)

    def speckle(self, rng, n, box, colors, rmin, rmax):
        """Deterministic random dots inside box (x0, y0, x1, y1)."""
        x0, y0, x1, y1 = box
        for _ in range(n):
            x = rng.randint(x0, x1)
            y = rng.randint(y0, y1)
            r = rng.randint(rmin, rmax)
            self.disc(x, y, r, rng.choice(colors))

    # -- output --------------------------------------------------------
    def downsample(self):
        """2x2 box average to half size: the anti-aliasing step."""
        w2, h2 = self.w // 2, self.h // 2
        out = bytearray(w2 * h2 * 3)
        src = self.buf
        W = self.w
        for y in range(h2):
            r0 = (2 * y) * W * 3
            r1 = (2 * y + 1) * W * 3
            o = y * w2 * 3
            for x in range(w2):
                i0 = r0 + x * 6
                i1 = r1 + x * 6
                out[o] = (src[i0] + src[i0 + 3] + src[i1] + src[i1 + 3]) >> 2
                out[o + 1] = (src[i0 + 1] + src[i0 + 4] + src[i1 + 1] + src[i1 + 4]) >> 2
                out[o + 2] = (src[i0 + 2] + src[i0 + 5] + src[i1 + 2] + src[i1 + 5]) >> 2
                o += 3
        c = Canvas(w2, h2)
        c.buf = out
        return c

    def png_bytes(self):
        """Encode the framebuffer as a PNG (filter 0 per row)."""
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.buf[y * stride:(y + 1) * stride]

        def chunk(typ, data):
            out = bytearray()
            out += len(data).to_bytes(4, "big")
            out += typ
            out += data
            crc = zlib.crc32(typ)
            crc = zlib.crc32(data, crc)
            out += (crc & 0xFFFFFFFF).to_bytes(4, "big")
            return bytes(out)

        png = bytearray(b"\x89PNG\r\n\x1a\n")
        ihdr = self.w.to_bytes(4, "big") + self.h.to_bytes(4, "big")
        ihdr += bytes([8, 2, 0, 0, 0])  # 8-bit, RGB, no interlace
        png += chunk(b"IHDR", ihdr)
        png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        png += chunk(b"IEND", b"")
        return bytes(png)
