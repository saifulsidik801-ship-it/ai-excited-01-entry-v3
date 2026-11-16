"""Pure-stdlib rasterizer for the Golden Koi Ramen entry.

Bytearray RGB framebuffer, shapes, layered gradients, deterministic value
noise, and a zlib PNG encoder. Standard library only — no PIL, no numpy,
nothing the grader container lacks. Every output byte is deterministic:
fixed constants + integer-hash noise + zlib at a fixed level.
"""

import math
import struct
import zlib

W = 1024
H = 1024


def clamp255(v):
    v = int(v)
    return 0 if v < 0 else (255 if v > 255 else v)


def mix(c1, c2, t):
    """Linear interpolation between two (r, g, b) colors."""
    return (c1[0] + (c2[0] - c1[0]) * t,
            c1[1] + (c2[1] - c1[1]) * t,
            c1[2] + (c2[2] - c1[2]) * t)


def shade(color, f):
    """Multiply a color's brightness by f."""
    return (color[0] * f, color[1] * f, color[2] * f)


def _hash2(x, y, seed):
    """Deterministic integer hash -> float in [0, 1)."""
    h = (x * 374761393 + y * 668265263 + seed * 974634211) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967295.0


def vnoise(x, y, seed=0):
    """Smooth deterministic value noise in [0, 1)."""
    xi = int(math.floor(x))
    yi = int(math.floor(y))
    xf = x - xi
    yf = y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a = _hash2(xi, yi, seed)
    b = _hash2(xi + 1, yi, seed)
    c = _hash2(xi, yi + 1, seed)
    d = _hash2(xi + 1, yi + 1, seed)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


class Canvas:
    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    # -- core pixel op -------------------------------------------------
    def put(self, x, y, color, alpha=1.0):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            px = self.px
            if alpha >= 1.0:
                px[i] = clamp255(color[0])
                px[i + 1] = clamp255(color[1])
                px[i + 2] = clamp255(color[2])
            elif alpha > 0.0:
                ia = 1.0 - alpha
                px[i] = clamp255(px[i] * ia + color[0] * alpha)
                px[i + 1] = clamp255(px[i + 1] * ia + color[1] * alpha)
                px[i + 2] = clamp255(px[i + 2] * ia + color[2] * alpha)

    def hspan(self, x0, x1, y, color, alpha=1.0):
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        px = self.px
        w = self.w
        r, g, b = color
        if alpha >= 1.0:
            ri, gi, bi = clamp255(r), clamp255(g), clamp255(b)
            for x in range(x0, x1 + 1):
                i = (y * w + x) * 3
                px[i] = ri
                px[i + 1] = gi
                px[i + 2] = bi
        else:
            ia = 1.0 - alpha
            for x in range(x0, x1 + 1):
                i = (y * w + x) * 3
                px[i] = clamp255(px[i] * ia + r * alpha)
                px[i + 1] = clamp255(px[i + 1] * ia + g * alpha)
                px[i + 2] = clamp255(px[i + 2] * ia + b * alpha)

    # -- fills ---------------------------------------------------------
    def vgrad(self, top, bottom):
        """Full-canvas vertical gradient."""
        px = self.px
        w, h = self.w, self.h
        for y in range(h):
            t = y / max(1, h - 1)
            r = clamp255(top[0] + (bottom[0] - top[0]) * t)
            g = clamp255(top[1] + (bottom[1] - top[1]) * t)
            b = clamp255(top[2] + (bottom[2] - top[2]) * t)
            base = y * w * 3
            for x in range(w):
                i = base + x * 3
                px[i] = r
                px[i + 1] = g
                px[i + 2] = b

    def radial_glow(self, cx, cy, radius, color, alpha):
        """Soft radial light pool, alpha falling off as (1-d/r)^2."""
        x0 = max(0, int(cx - radius))
        x1 = min(self.w - 1, int(cx + radius))
        y0 = max(0, int(cy - radius))
        y1 = min(self.h - 1, int(cy + radius))
        r2 = radius * radius
        for y in range(y0, y1 + 1):
            dy = y - cy
            for x in range(x0, x1 + 1):
                dx = x - cx
                d2 = dx * dx + dy * dy
                if d2 < r2:
                    d = math.sqrt(d2) / radius
                    a = alpha * (1.0 - d) * (1.0 - d)
                    if a > 0.004:
                        self.put(x, y, color, a)

    def soft_ellipse(self, cx, cy, rx, ry, color, alpha):
        """Ellipse whose alpha fades to zero at the rim (fake blur)."""
        x0 = max(0, int(cx - rx))
        x1 = min(self.w - 1, int(cx + rx))
        y0 = max(0, int(cy - ry))
        y1 = min(self.h - 1, int(cy + ry))
        for y in range(y0, y1 + 1):
            ny = (y - cy) / ry
            for x in range(x0, x1 + 1):
                nx = (x - cx) / rx
                d2 = nx * nx + ny * ny
                if d2 < 1.0:
                    a = alpha * (1.0 - d2) * (1.0 - d2)
                    if a > 0.004:
                        self.put(x, y, color, a)

    # -- shapes --------------------------------------------------------
    def disc(self, cx, cy, r, color, alpha=1.0, soft=0):
        """Filled circle; soft>0 feathers the edge over that many px."""
        if r <= 0:
            return
        x0 = max(0, int(cx - r - soft))
        x1 = min(self.w - 1, int(cx + r + soft))
        y0 = max(0, int(cy - r - soft))
        y1 = min(self.h - 1, int(cy + r + soft))
        for y in range(y0, y1 + 1):
            dy = (y - cy) / r
            for x in range(x0, x1 + 1):
                dx = (x - cx) / r
                d = math.sqrt(dx * dx + dy * dy)
                if d <= 1.0:
                    a = alpha
                elif soft > 0 and d <= 1.0 + soft / r:
                    a = alpha * (1.0 - (d - 1.0) * r / soft)
                else:
                    continue
                if a > 0.004:
                    self.put(x, y, color, a)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0, soft=0):
        if rx <= 0 or ry <= 0:
            return
        x0 = max(0, int(cx - rx - soft))
        x1 = min(self.w - 1, int(cx + rx + soft))
        y0 = max(0, int(cy - ry - soft))
        y1 = min(self.h - 1, int(cy + ry + soft))
        for y in range(y0, y1 + 1):
            ny = (y - cy) / ry
            for x in range(x0, x1 + 1):
                nx = (x - cx) / rx
                d = math.sqrt(nx * nx + ny * ny)
                if d <= 1.0:
                    a = alpha
                elif soft > 0 and d <= 1.0 + soft / max(rx, ry):
                    a = alpha * (1.0 - (d - 1.0) * max(rx, ry) / soft)
                else:
                    continue
                if a > 0.004:
                    self.put(x, y, color, a)

    def poly(self, points, color, alpha=1.0):
        """Scanline-filled polygon (even-odd)."""
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)))
        n = len(points)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0p = points[i]
                x1, y1p = points[(i + 1) % n]
                if (y0p <= y < y1p) or (y1p <= y < y0p):
                    t = (y - y0p) / (y1p - y0p)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hspan(xs[i], xs[i + 1], y, color, alpha)

    def line(self, x0, y0, x1, y1, width, color, alpha=1.0):
        """Thick line drawn as a chain of discs."""
        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy)
        steps = max(2, int(length / max(1.0, width * 0.35)) + 1)
        r = width / 2.0
        for i in range(steps + 1):
            t = i / steps
            self.disc(x0 + dx * t, y0 + dy * t, r, color, alpha)

    def bezier(self, p0, p1, p2, p3, width, color, alpha=1.0):
        """Thick cubic bezier drawn as a chain of discs."""
        approx = (math.hypot(p1[0] - p0[0], p1[1] - p0[1]) +
                  math.hypot(p2[0] - p1[0], p2[1] - p1[1]) +
                  math.hypot(p3[0] - p2[0], p3[1] - p2[1]))
        steps = max(4, int(approx / max(1.0, width * 0.35)) + 1)
        r = width / 2.0
        for i in range(steps + 1):
            t = i / steps
            mt = 1.0 - t
            x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] +
                 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
            y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] +
                 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
            self.disc(x, y, r, color, alpha)

    def ring(self, cx, cy, r, width, color, alpha=1.0):
        """Circle outline, drawn as small discs around the circumference."""
        steps = max(24, int(2 * math.pi * r / max(2.0, width * 0.6)))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            self.disc(cx + r * math.cos(a), cy + r * math.sin(a),
                      width / 2.0, color, alpha)

    def ellipse_ring(self, cx, cy, rx, ry, width, color, alpha=1.0):
        steps = max(48, int(2 * math.pi * max(rx, ry) / max(2.0, width * 0.6)))
        for i in range(steps):
            a = 2 * math.pi * i / steps
            self.disc(cx + rx * math.cos(a), cy + ry * math.sin(a),
                      width / 2.0, color, alpha)

    def star4(self, cx, cy, r, color, alpha=1.0):
        """Small four-point sparkle (two crossed thin lines)."""
        self.line(cx - r, cy, cx + r, cy, 2.2, color, alpha)
        self.line(cx, cy - r, cx, cy + r, 2.2, color, alpha)
        self.disc(cx, cy, 2.0, color, alpha)

    # -- texture -------------------------------------------------------
    def grain_region(self, x0, y0, x1, y1, scale, amp, seed=0):
        """Per-pixel brightness modulation from deterministic noise."""
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(self.w - 1, int(x1))
        y1 = min(self.h - 1, int(y1))
        px = self.px
        w = self.w
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                n = vnoise(x / scale, y / scale, seed)
                f = 1.0 + (n - 0.5) * 2.0 * amp
                i = (y * w + x) * 3
                px[i] = clamp255(px[i] * f)
                px[i + 1] = clamp255(px[i + 1] * f)
                px[i + 2] = clamp255(px[i + 2] * f)

    def vignette(self, strength=0.30):
        """Darken corners; strength 0..1."""
        cx, cy = self.w / 2.0, self.h / 2.0
        maxd = math.hypot(cx, cy)
        px = self.px
        w, h = self.w, self.h
        for y in range(h):
            for x in range(w):
                d = math.hypot(x - cx, y - cy) / maxd
                f = 1.0 - strength * (d * d * d)
                if f < 1.0:
                    i = (y * w + x) * 3
                    px[i] = clamp255(px[i] * f)
                    px[i + 1] = clamp255(px[i + 1] * f)
                    px[i + 2] = clamp255(px[i + 2] * f)

    # -- output --------------------------------------------------------
    def to_png_bytes(self):
        """Encode as PNG (filter 0, zlib level 6). Deterministic."""
        w, h = self.w, self.h
        raw = bytearray()
        px = self.px
        for y in range(h):
            raw.append(0)
            raw += px[y * w * 3:(y + 1) * w * 3]
        comp = zlib.compress(bytes(raw), 6)

        def chunk(ctype, data):
            c = struct.pack(">I", len(data)) + ctype + data
            c += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
            return c

        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
                chunk(b"IDAT", comp) + chunk(b"IEND", b""))
