"""Pure-stdlib rasterizer: framebuffer, shapes, gradients, noise, PNG encoder.

No third-party libraries: the grader runs in a fresh container with the
standard library only. Everything is deterministic (fixed hash noise).
"""

import math
import os
import struct
import zlib

W = H = 1024


def _clamp8(v):
    if v < 0:
        return 0
    if v > 255:
        return 255
    return int(v)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c0, c1, t):
    return (lerp(c0[0], c1[0], t), lerp(c0[1], c1[1], t), lerp(c0[2], c1[2], t))


def _hash_noise(x, y):
    """Deterministic value noise in [0, 1)."""
    h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    h = (h ^ (h >> 13)) & 0xFFFFFFFF
    h = (h * 1274126177) & 0xFFFFFFFF
    h = (h ^ (h >> 16)) & 0xFFFFFFFF
    return ((h >> 8) & 0xFFFF) / 65536.0


class Canvas:
    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    # -- low-level ------------------------------------------------------
    def _solid_row(self, y, x0, x1, r, g, b):
        """Fill row span [x0, x1] with an opaque colour (C-speed slice)."""
        if y < 0 or y >= self.h:
            return
        if x0 < 0:
            x0 = 0
        if x1 >= self.w:
            x1 = self.w - 1
        if x1 < x0:
            return
        i = (y * self.w + x0) * 3
        n = x1 - x0 + 1
        self.px[i:i + n * 3] = bytes((r, g, b)) * n

    def _blend_row(self, y, x0, x1, r, g, b, a):
        """Blend row span [x0, x1] with colour at alpha a (0..1)."""
        if y < 0 or y >= self.h or a <= 0:
            return
        if x0 < 0:
            x0 = 0
        if x1 >= self.w:
            x1 = self.w - 1
        if x1 < x0:
            return
        px = self.px
        ia = 1.0 - a
        base = y * self.w * 3
        for x in range(x0, x1 + 1):
            i = base + x * 3
            px[i] = int(r * a + px[i] * ia)
            px[i + 1] = int(g * a + px[i + 1] * ia)
            px[i + 2] = int(b * a + px[i + 2] * ia)

    def blend_px(self, x, y, r, g, b, a):
        if x < 0 or y < 0 or x >= self.w or y >= self.h or a <= 0:
            return
        px = self.px
        i = (y * self.w + x) * 3
        ia = 1.0 - a
        px[i] = int(r * a + px[i] * ia)
        px[i + 1] = int(g * a + px[i + 1] * ia)
        px[i + 2] = int(b * a + px[i + 2] * ia)

    # -- fills ----------------------------------------------------------
    def vgrad(self, y0, y1, c0, c1):
        """Vertical gradient over the full width, rows y0..y1."""
        if y0 < 0:
            y0 = 0
        if y1 >= self.h:
            y1 = self.h - 1
        span = max(1, y1 - y0)
        for y in range(y0, y1 + 1):
            c = lerp_color(c0, c1, (y - y0) / span)
            self._solid_row(y, 0, self.w - 1, _clamp8(c[0]), _clamp8(c[1]), _clamp8(c[2]))

    def disc(self, cx, cy, rad, color, alpha=1.0, feather=0):
        """Filled circle. feather>0 softens the rim over that many px."""
        if rad <= 0:
            return
        r, g, b = color
        y0 = int(cy - rad - feather)
        y1 = int(cy + rad + feather)
        for y in range(y0, y1 + 1):
            dy = y - cy
            dd = rad * rad - dy * dy
            if dd < 0:
                if feather <= 0:
                    continue
                d = abs(dy) - rad
                if d > feather:
                    continue
                a = alpha * (1.0 - d / feather) * 0.5
                self._blend_row(y, int(cx - 1), int(cx + 1), r, g, b, a)
                continue
            half = math.sqrt(dd)
            x0 = int(cx - half)
            x1 = int(cx + half)
            if alpha >= 0.999 and feather <= 0:
                self._solid_row(y, x0, x1, _clamp8(r), _clamp8(g), _clamp8(b))
            else:
                self._blend_row(y, x0, x1, r, g, b, alpha)
            if feather > 0:
                fa = alpha * 0.45
                self._blend_row(y, x0 - 1, x0, r, g, b, fa)
                self._blend_row(y, x1, x1 + 1, r, g, b, fa)

    def soft_disc(self, cx, cy, rad, color, alpha=1.0):
        """Radial-gradient disc: alpha falls off quadratically to the rim."""
        if rad <= 0:
            return
        r, g, b = color
        y0 = max(0, int(cy - rad))
        y1 = min(self.h - 1, int(cy + rad))
        for y in range(y0, y1 + 1):
            dy = y - cy
            dd = rad * rad - dy * dy
            if dd < 0:
                continue
            half = math.sqrt(dd)
            x0 = int(cx - half)
            x1 = int(cx + half)
            px = self.px
            base = y * self.w * 3
            for x in range(max(0, x0), min(self.w - 1, x1) + 1):
                dx = x - cx
                d = math.sqrt(dx * dx + dy * dy) / rad
                a = alpha * (1.0 - d) * (1.0 - d)
                if a <= 0.003:
                    continue
                i = base + x * 3
                ia = 1.0 - a
                px[i] = int(r * a + px[i] * ia)
                px[i + 1] = int(g * a + px[i + 1] * ia)
                px[i + 2] = int(b * a + px[i + 2] * ia)

    def ellipse(self, cx, cy, rx, ry, color, alpha=1.0, rot=0.0, feather=0):
        """Filled ellipse, optionally rotated by rot radians."""
        if rx <= 0 or ry <= 0:
            return
        r, g, b = color
        u = math.cos(rot)
        v = math.sin(rot)
        bx = math.sqrt((rx * u) ** 2 + (ry * v) ** 2)
        by = math.sqrt((rx * v) ** 2 + (ry * u) ** 2)
        y0 = int(cy - by - feather)
        y1 = int(cy + by + feather)
        for y in range(y0, y1 + 1):
            dy = y - cy
            # (qx/rx)^2 + (qy/ry)^2 <= 1 with qx = u*dx + v*dy, qy = -v*dx + u*dy
            a2 = (u / rx) ** 2 + (v / ry) ** 2
            b2 = 2.0 * dy * (u * v / (rx * rx) - u * v / (ry * ry))
            c2 = (dy * dy) * ((v / rx) ** 2 + (u / ry) ** 2) - 1.0
            disc = b2 * b2 - 4.0 * a2 * c2
            if disc < 0:
                continue
            sq = math.sqrt(disc)
            x0 = int(cx + (-b2 - sq) / (2.0 * a2))
            x1 = int(cx + (-b2 + sq) / (2.0 * a2))
            if alpha >= 0.999 and feather <= 0:
                self._solid_row(y, x0, x1, _clamp8(r), _clamp8(g), _clamp8(b))
            else:
                self._blend_row(y, x0, x1, r, g, b, alpha)

    def ellipse_ring(self, cx, cy, rx, ry, thick, color, alpha=1.0, rot=0.0,
                     a0=None, a1=None):
        """Ellipse outline (optionally a partial arc from a0 to a1 radians)."""
        if rx <= 0 or ry <= 0:
            return
        if a0 is None:
            a0, a1 = 0.0, 2.0 * math.pi
        span = a1 - a0
        steps = max(8, int(span * max(rx, ry) / 3.0))
        dot = max(1.5, thick * 0.5)
        for s in range(steps + 1):
            t = a0 + span * s / steps
            x = cx + rx * math.cos(t)
            y = cy + ry * math.sin(t)
            if rot:
                dx = x - cx
                dy = y - cy
                x = cx + dx * math.cos(rot) - dy * math.sin(rot)
                y = cy + dx * math.sin(rot) + dy * math.cos(rot)
            self.disc(x, y, dot, color, alpha)

    # -- strokes --------------------------------------------------------
    def capsule(self, x1, y1, x2, y2, rad, color, alpha=1.0):
        """Thick line segment (round caps)."""
        if rad <= 0:
            return
        r, g, b = color
        dx = x2 - x1
        dy = y2 - y1
        seg2 = dx * dx + dy * dy
        x0 = int(min(x1, x2) - rad - 1)
        x1b = int(max(x1, x2) + rad + 1)
        y0 = int(min(y1, y2) - rad - 1)
        y1b = int(max(y1, y2) + rad + 1)
        px = self.px
        for y in range(max(0, y0), min(self.h - 1, y1b) + 1):
            base = y * self.w * 3
            for x in range(max(0, x0), min(self.w - 1, x1b) + 1):
                if seg2 == 0:
                    t = 0.0
                else:
                    t = ((x - x1) * dx + (y - y1) * dy) / seg2
                    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
                px_ = x1 + t * dx
                py_ = y1 + t * dy
                d2 = (x - px_) ** 2 + (y - py_) ** 2
                if d2 > rad * rad:
                    continue
                i = base + x * 3
                ia = 1.0 - alpha
                px[i] = int(r * alpha + px[i] * ia)
                px[i + 1] = int(g * alpha + px[i + 1] * ia)
                px[i + 2] = int(b * alpha + px[i + 2] * ia)

    def poly(self, pts, color, alpha=1.0):
        """Filled polygon (scanline, even-odd)."""
        if len(pts) < 3:
            return
        r, g, b = color
        ys = [p[1] for p in pts]
        y0 = int(max(0, min(ys)))
        y1 = int(min(self.h - 1, max(ys)))
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
                xa = int(xs[k])
                xb = int(xs[k + 1])
                if alpha >= 0.999:
                    self._solid_row(y, xa, xb, _clamp8(r), _clamp8(g), _clamp8(b))
                else:
                    self._blend_row(y, xa, xb, r, g, b, alpha)

    def arc(self, cx, cy, rad, a0, a1, color, alpha=1.0, thick=3.0):
        """Circular arc stroke from angle a0 to a1 (radians, screen coords)."""
        span = a1 - a0
        steps = max(4, int(abs(span) * rad / 3.0))
        dot = max(1.2, thick * 0.5)
        for s in range(steps + 1):
            t = a0 + span * s / steps
            self.disc(cx + rad * math.cos(t), cy + rad * math.sin(t),
                      dot, color, alpha)

    # -- curves ---------------------------------------------------------
    @staticmethod
    def bezier(p0, p1, p2, p3, n=40):
        """Cubic bezier sample points."""
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

    @staticmethod
    def bezier_tangent(p0, p1, p2, p3, t):
        """Unit tangent of a cubic bezier at parameter t."""
        mt = 1.0 - t
        dx = (3 * mt * mt * (p1[0] - p0[0])
              + 6 * mt * t * (p2[0] - p1[0])
              + 3 * t * t * (p3[0] - p2[0]))
        dy = (3 * mt * mt * (p1[1] - p0[1])
              + 6 * mt * t * (p2[1] - p1[1])
              + 3 * t * t * (p3[1] - p2[1]))
        ln = math.hypot(dx, dy) or 1.0
        return (dx / ln, dy / ln)

    # -- texture --------------------------------------------------------
    def grain(self, x0, y0, x1, y1, amount=14):
        """Deterministic speckle inside a rectangle (adds realism)."""
        for y in range(max(0, y0), min(self.h, y1)):
            base = y * self.w * 3
            for x in range(max(0, x0), min(self.w, x1)):
                n = (_hash_noise(x, y) - 0.5) * 2.0 * amount
                i = base + x * 3
                self.px[i] = _clamp8(self.px[i] + n)
                self.px[i + 1] = _clamp8(self.px[i + 1] + n)
                self.px[i + 2] = _clamp8(self.px[i + 2] + n)

    # -- output ---------------------------------------------------------
    def save_png(self, path):
        """Write the framebuffer as a PNG (filter 0, zlib level 6)."""
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)
            raw += self.px[y * stride:(y + 1) * stride]
        comp = zlib.compress(bytes(raw), 6)

        def chunk(ctype, data):
            c = struct.pack(">I", len(data)) + ctype + data
            c += struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
            return c

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n"
        png += chunk(b"IHDR", ihdr)
        png += chunk(b"IDAT", comp)
        png += chunk(b"IEND", b"")
        with open(path, "wb") as f:
            f.write(png)
        return path
