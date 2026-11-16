"""Golden Koi Ramen -- giant golden koi bursting out of a ramen bowl.

Drawn at 2048x2048 on the Canvas, then downsampled to 1024x1024 by
main.py: the 2x supersample is what makes every edge crisp (the HD
lever) while the final image stays inside the 1024x1024 / 1 MiB gate.

Composition (winner formula): mundane container (ramen bowl on a
wooden table) + giant creature bursting out (golden koi on a strong
diagonal) + splash energy (broth plumes, droplet spray, broth crown,
flying chopsticks, steam, warm bokeh restaurant light).

Everything is drawn with the pure-stdlib rasterizer in render.py.
No PIL, no numpy, no downloaded images. Deterministic.
"""

import math
import random

from render import Canvas, clamp, mix

W = 2048
H = 2048

BG_TOP = (24, 13, 7)
BG_BOT = (80, 45, 21)
TABLE = (40, 25, 15)


def bg_at(y):
    """Background gradient colour at height y (same as the vgrad)."""
    return mix(BG_TOP, BG_BOT, clamp(y / (H - 1), 0.0, 1.0))


def _lerp_profile(profile, t):
    """Piecewise-linear profile: list of (t, value), t in [0, 1]."""
    if t <= profile[0][0]:
        return profile[0][1]
    for (t0, v0), (t1, v1) in zip(profile, profile[1:]):
        if t <= t1:
            f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            if isinstance(v0, tuple):
                return mix(v0, v1, f)
            return v0 + (v1 - v0) * f
    return profile[-1][1]


# Koi spine: cubic bezier, tail in the bowl -> head upper right.
SPINE = ((950.0, 1560.0), (830.0, 1180.0), (1150.0, 720.0), (1600.0, 400.0))
RADIUS_PROFILE = [(0.0, 70.0), (0.15, 150.0), (0.40, 205.0),
                  (0.65, 195.0), (0.85, 175.0), (1.0, 150.0)]
COLOR_PROFILE = [(0.0, (206, 100, 28)), (0.30, (232, 138, 44)),
                 (0.60, (246, 166, 58)), (1.0, (238, 148, 52))]
BELLY_PROFILE = [(0.0, (250, 232, 196)), (1.0, (246, 212, 166))]


def spine_samples(n=160):
    """Sample the spine: (x, y, tx, ty, t) with unit tangent."""
    pts = []
    p0, p1, p2, p3 = SPINE
    for i in range(n + 1):
        t = i / n
        mt = 1.0 - t
        x = (mt ** 3) * p0[0] + 3 * (mt ** 2) * t * p1[0] + \
            3 * mt * (t ** 2) * p2[0] + (t ** 3) * p3[0]
        y = (mt ** 3) * p0[1] + 3 * (mt ** 2) * t * p1[1] + \
            3 * mt * (t ** 2) * p2[1] + (t ** 3) * p3[1]
        # derivative of the cubic
        dx = 3 * (mt ** 2) * (p1[0] - p0[0]) + 6 * mt * t * (p2[0] - p1[0]) + \
            3 * (t ** 2) * (p3[0] - p2[0])
        dy = 3 * (mt ** 2) * (p1[1] - p0[1]) + 6 * mt * t * (p2[1] - p1[1]) + \
            3 * (t ** 2) * (p3[1] - p2[1])
        L = math.hypot(dx, dy) or 1.0
        pts.append((x, y, dx / L, dy / L, t))
    return pts


def draw(c):
    rng = random.Random(20261116)

    # ---- background -------------------------------------------------
    c.vgrad(BG_TOP, BG_BOT)

    # warm bokeh, soft glowing discs (pre-mixed toward the local bg)
    bokeh = [
        (300, 300, 150, 0.16), (700, 220, 110, 0.13), (1150, 180, 140, 0.15),
        (1600, 260, 120, 0.12), (1950, 420, 160, 0.15), (200, 700, 130, 0.13),
        (1850, 800, 110, 0.12), (150, 1100, 100, 0.11),
        (1950, 1150, 130, 0.12), (900, 300, 80, 0.10),
    ]
    for x, y, r, a in bokeh:
        c.soft_disc(x, y, r, (216, 140, 64), bg_at(y), alpha_max=a)

    # sparkles
    for x, y, s in [(830, 210, 18), (1760, 160, 20), (990, 560, 13),
                    (1640, 1020, 16), (1550, 1080, 12), (1900, 1280, 18),
                    (180, 1180, 15), (900, 960, 12), (1330, 1240, 14),
                    (420, 760, 13)]:
        c.plus(x, y, s, (232, 200, 140), width=5)

    # ---- table ------------------------------------------------------
    c.poly([(0, 1740), (W, 1740), (W, H), (0, H)], TABLE)
    c.tube([(0, 1742), (W, 1742)], 3, 3, (92, 58, 32))
    for y, col in [(1800, (30, 18, 10)), (1865, (58, 36, 20)),
                   (1925, (30, 18, 10)), (1990, (58, 36, 20)),
                   (2030, (30, 18, 10))]:
        pts = c.bezier2((0, y), (700, y - 14), (1400, y + 10), steps=24)
        pts += c.bezier2((1400, y + 10), (1750, y - 6), (W, y + 4), steps=12)
        c.tube(pts, 5, 5, col)

    # soft shadow under the bowl
    c.soft_disc(1024, 1790, 520, (8, 5, 3), TABLE, alpha_max=0.40)

    # ---- bowl -------------------------------------------------------
    c.ellipse(1024, 1640, 600, 120, (150, 44, 30))          # bowl base
    c.ellipse(1024, 1600, 680, 200, (172, 50, 36))          # red rim
    c.ellipse_arc_tube(1024, 1600, 665, 192, 15, 165, 12, (220, 88, 58))
    c.ellipse(1024, 1592, 618, 166, (178, 120, 46))         # broth
    c.ellipse_arc_tube(1024, 1592, 600, 152, 195, 345, 18, (138, 86, 30))
    c.ellipse_arc_tube(1024, 1592, 560, 140, 25, 120, 16, (222, 166, 86))

    # noodles: thin pale strands across the broth
    noodle_rows = [
        ((520, 1560), (900, 1520), (1500, 1570)),
        ((560, 1640), (1000, 1610), (1520, 1650)),
        ((600, 1700), (980, 1670), (1440, 1700)),
        ((700, 1490), (1050, 1470), (1380, 1500)),
        ((480, 1600), (820, 1580), (1180, 1610)),
        ((1100, 1540), (1350, 1520), (1560, 1560)),
        ((900, 1720), (1200, 1700), (1480, 1720)),
    ]
    for a, b, d in noodle_rows:
        c.tube(c.bezier2(a, b, d, steps=28), 8, 8, (236, 200, 128))

    # egg: white + yolk
    c.rellipse(1330, 1660, 80, 50, 8, (244, 238, 222))
    c.disc(1330, 1655, 36, (240, 178, 60))
    c.disc(1318, 1642, 10, (255, 214, 120))

    # green onion rings
    for x, y in [(700, 1560), (820, 1680), (1080, 1700), (1500, 1560),
                 (1420, 1700), (620, 1640)]:
        c.disc(x, y, 16, (96, 164, 92))
        c.disc(x, y, 8, (178, 120, 46))

    # ---- steam ------------------------------------------------------
    steam_paths = [
        ((720, 1500), (680, 1300), (760, 1120), (720, 950)),
        ((830, 1500), (800, 1280), (870, 1080), (830, 920)),
        ((930, 1490), (900, 1290), (960, 1100), (920, 960)),
        ((640, 1520), (600, 1340), (670, 1180), (630, 1030)),
        ((1010, 1500), (990, 1320), (1040, 1160), (1000, 1000)),
    ]
    for p0, p1, p2, p3 in steam_paths:
        pts = c.bezier3(p0, p1, p2, p3, steps=40)
        c.tube(pts, 24, 28, mix(bg_at(1250), (215, 185, 145), 0.18))
        c.tube(pts, 12, 16, mix(bg_at(1250), (220, 192, 152), 0.30))

    # ---- tail fin (in the broth) ------------------------------------
    c.poly([(950, 1560), (860, 1660), (980, 1640)], (208, 102, 30))
    c.poly([(950, 1560), (1060, 1650), (940, 1660)], (208, 102, 30))

    # ---- splash plumes (behind the koi) -----------------------------
    plumes = [
        (((950, 1560), (760, 1360), (660, 1140), (640, 1030)), 60, 10),
        (((985, 1570), (880, 1320), (830, 1100), (810, 980)), 50, 8),
        (((920, 1580), (720, 1470), (580, 1400), (520, 1330)), 42, 8),
    ]
    for (p0, p1, p2, p3), r0, r1 in plumes:
        pts = c.bezier3(p0, p1, p2, p3, steps=48)
        c.tube(pts, r0, r1, (240, 176, 72))
        c.tube(pts, int(r0 * 0.55), max(3, int(r1 * 0.7)), (252, 204, 110))

    # ---- koi body ---------------------------------------------------
    sp = spine_samples(160)
    for x, y, tx, ty, t in sp:
        r = _lerp_profile(RADIUS_PROFILE, t)
        col = _lerp_profile(COLOR_PROFILE, t)
        c.disc(int(round(x)), int(round(y)), max(1, int(round(r))), col)

    # belly: narrow cream underside (offset toward down-right)
    for x, y, tx, ty, t in sp:
        r = _lerp_profile(RADIUS_PROFILE, t)
        bx, by = -ty, tx  # down-right side
        col = _lerp_profile(BELLY_PROFILE, t)
        c.disc(int(round(x + bx * 0.62 * r)), int(round(y + by * 0.62 * r)),
               max(1, int(round(0.38 * r))), col)

    # scales: overlapping elliptical plates across the back, 3 rows
    for row, off, tshift in [(0, 0.22, 0.0), (1, 0.48, 0.017),
                             (2, 0.72, 0.008)]:
        t = 0.10 + tshift
        while t <= 0.78:
            for (x, y, tx, ty, tt) in sp:
                if abs(tt - t) < 0.004:
                    r = _lerp_profile(RADIUS_PROFILE, t)
                    bx, by = ty, -tx
                    sx = x + bx * off * r
                    sy = y + by * off * r
                    ang = math.degrees(math.atan2(ty, tx))
                    c.rellipse(int(round(sx)), int(round(sy)), 38, 26, ang,
                               (226, 122, 40))
                    c.disc(int(round(sx + bx * 9)), int(round(sy + by * 9)), 7,
                           (244, 164, 76))
                    break
            t += 0.035

    # dorsal fin: zigzag along the back, t 0.12..0.58
    base_pts = []
    for x, y, tx, ty, t in sp:
        if 0.12 <= t <= 0.58:
            r = _lerp_profile(RADIUS_PROFILE, t)
            bx, by = ty, -tx
            base_pts.append((x + bx * 0.95 * r, y + by * 0.95 * r, t, r, bx, by))
    fin = []
    tips = []
    for i, (bx0, by0, t, r, ux, uy) in enumerate(base_pts):
        fin.append((bx0, by0))
        if i < len(base_pts) - 1:
            nx, ny, nt, nr, _, _ = base_pts[i + 1]
            mx, my = (bx0 + nx) / 2, (by0 + ny) / 2
            tips.append((mx + ux * 0.72 * r, my + uy * 0.72 * r))
    poly_pts = []
    for i, b in enumerate(fin):
        poly_pts.append(b)
        if i < len(tips):
            poly_pts.append(tips[i])
    for b in reversed(fin):
        poly_pts.append(b)
    c.poly(poly_pts, (186, 84, 22))
    edge = []
    for i, b in enumerate(fin):
        edge.append(b)
        if i < len(tips):
            edge.append(tips[i])
    c.tube(edge, 6, 6, (226, 120, 40))

    # pectoral fin under the head
    for (x, y, tx, ty, t) in sp:
        if abs(t - 0.88) < 0.004:
            r = _lerp_profile(RADIUS_PROFILE, t)
            bx, by = -ty, tx
            ang = math.degrees(math.atan2(ty, tx)) + 55
            c.rellipse(int(round(x + bx * 0.7 * r)),
                       int(round(y + by * 0.7 * r)), 95, 42, ang,
                       (212, 106, 32))
            break

    # silhouette edges: thin darker outline top and bottom of the body
    for x, y, tx, ty, t in sp:
        if 0.06 <= t <= 0.96:
            r = _lerp_profile(RADIUS_PROFILE, t)
            bx, by = ty, -tx
            c.disc(int(round(x + bx * 0.99 * r)), int(round(y + by * 0.99 * r)),
                   6, (178, 82, 22))
    for x, y, tx, ty, t in sp:
        if 0.06 <= t <= 0.96:
            r = _lerp_profile(RADIUS_PROFILE, t)
            bx, by = -ty, tx
            c.disc(int(round(x + bx * 0.99 * r)), int(round(y + by * 0.99 * r)),
                   6, (178, 82, 22))

    # ---- broth crown around the exit point --------------------------
    c.ellipse_arc_tube(950, 1560, 215, 72, 0, 360, 16, (238, 172, 66))
    c.ellipse_arc_tube(950, 1560, 215, 72, 20, 160, 9, (255, 202, 112))

    # ---- head -------------------------------------------------------
    c.rellipse(1630, 390, 270, 215, -38, (240, 156, 54))
    c.rellipse(1570, 320, 130, 95, -38, (246, 172, 88))
    # eye
    c.disc(1745, 300, 48, (255, 250, 240))
    c.disc(1745, 300, 33, (28, 18, 12))
    c.disc(1745, 300, 17, (8, 6, 4))
    c.disc(1731, 286, 11, (255, 255, 255))
    c.disc(1758, 314, 5, (255, 240, 200))
    # mouth: slight smile arc
    c.tube(c.bezier2((1540, 450), (1610, 510), (1700, 500), steps=24),
           8, 8, (120, 58, 20))
    # barbels
    c.tube(c.bezier2((1670, 490), (1740, 545), (1770, 590), steps=20),
           8, 4, (178, 94, 30))
    c.tube(c.bezier2((1700, 480), (1770, 525), (1810, 565), steps=20),
           7, 4, (178, 94, 30))
    # gill arc
    c.tube(c.bezier2((1545, 300), (1510, 385), (1545, 475), steps=24),
           7, 7, (198, 94, 26))

    # rim light: bright thin tube along the body's top edge
    rim_pts = []
    for x, y, tx, ty, t in sp:
        if 0.08 <= t <= 0.95:
            r = _lerp_profile(RADIUS_PROFILE, t)
            bx, by = ty, -tx
            rim_pts.append((x + bx * 0.88 * r, y + by * 0.88 * r))
    c.tube(rim_pts, 9, 9, (255, 216, 140))

    # ---- chopsticks -------------------------------------------------
    for (x0, y0, x1, y1) in [(620, 880, 1140, 1670), (770, 850, 1210, 1690)]:
        c.tube([(x0, y0), (x1, y1)], 15, 8, (58, 30, 18))
        tx, ty = x1 - x0, y1 - y0
        sx, sy = x0 + tx * 0.72, y0 + ty * 0.72
        c.tube([(sx, sy), (x1, y1)], 9, 7, (150, 30, 24))
    # one faint motion streak
    c.tube([(700, 900), (1150, 1640)], 2, 2, (140, 116, 90))

    # ---- droplet spray: tight arc above the broth, left of the exit --
    for i in range(36):
        a = rng.uniform(1.1, 2.9)
        d = rng.uniform(80, 330)
        x = 950 + int(d * math.cos(a))
        y = 1560 - int(d * math.sin(a) * 0.8) - rng.randint(0, 80)
        if y > 1520:
            continue
        r = rng.randint(6, 22)
        c.disc(x, y, r, (236, 170, 64))
        c.disc(x - 3, y - 3, max(2, r // 4), (255, 226, 160))

    # a few bright highlights on the broth
    for x, y, r in [(820, 1500, 14), (1180, 1660, 12), (980, 1680, 10)]:
        c.disc(x, y, r, (255, 214, 130))
