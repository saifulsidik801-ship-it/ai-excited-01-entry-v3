"""Golden Koi Ramen — realistic rendering of the winning scene.

A giant golden koi bursting diagonally out of a ramen bowl: broth splash
plumes, flying chopsticks, steam, warm bokeh restaurant light. 1024x1024.

Same composition as the reference image; the realism comes from shading:
layered gradients instead of flat fills, specular highlights, scale rows,
translucent fins, wood grain, broth texture, soft shadows, bokeh depth.
Pure stdlib; rendered by render.py.
"""

import math

from render import Canvas, mix, shade, vnoise

# -- palette ------------------------------------------------------------
BG_TOP = (34, 17, 4)
BG_BOT = (74, 36, 8)
GLOW = (138, 74, 18)
TABLE = (72, 42, 16)
TABLE_DARK = (42, 22, 7)
BOWL_RED = (156, 22, 8)
BOWL_RED_LT = (192, 40, 16)
BOWL_RIM = (232, 104, 48)
BROTH = (192, 90, 16)
BROTH_LT = (232, 130, 26)
BROTH_HI = (248, 176, 80)
KOI_DEEP = (206, 82, 8)
KOI_MID = (240, 140, 24)
KOI_LT = (245, 158, 32)
KOI_GOLD = (248, 176, 48)
BELLY = (251, 238, 200)
FIN = (224, 112, 8)
WHITE = (255, 250, 240)


# -- helpers ------------------------------------------------------------
def _catmull(points, per_seg=22):
    """Catmull-Rom spline through points -> dense sample list."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        for j in range(per_seg):
            t = j / per_seg
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(points[-1])
    return out


def _profile(t, stops):
    """Piecewise-linear interpolation over (t, value) stops."""
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        t0, v0 = stops[i]
        t1, v1 = stops[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0)
            if isinstance(v0, tuple):
                return mix(v0, v1, f)
            return v0 + (v1 - v0) * f
    return stops[-1][1]


def _wavy_hline(c, ybase, x0, x1, step, amp, scale, seed, width, color, alpha):
    """Horizontal line whose y wobbles with deterministic noise."""
    xs = list(range(int(x0), int(x1) + 1, step))
    pts = [(x, ybase + (vnoise(x / scale, seed, seed) - 0.5) * amp)
           for x in xs]
    for a, b in zip(pts, pts[1:]):
        c.line(a[0], a[1], b[0], b[1], width, color, alpha)


# -- scene passes -------------------------------------------------------
def _background(c):
    c.vgrad(BG_TOP, BG_BOT)
    c.radial_glow(560, 420, 520, GLOW, 0.50)
    c.radial_glow(300, 200, 260, (120, 60, 14), 0.35)
    # warm bokeh: soft discs, varying size and brightness
    bokeh = [
        (150, 150, 46, (255, 150, 48), 0.28, 14),
        (880, 130, 34, (232, 96, 32), 0.35, 12),
        (905, 470, 42, (255, 140, 40), 0.22, 16),
        (95, 430, 30, (220, 110, 30), 0.25, 12),
        (830, 60, 22, (255, 180, 90), 0.30, 8),
        (250, 60, 18, (255, 170, 80), 0.28, 8),
        (640, 90, 26, (240, 120, 40), 0.22, 10),
        (60, 700, 24, (200, 100, 26), 0.18, 10),
        (960, 700, 20, (230, 120, 40), 0.20, 8),
        (700, 480, 16, (255, 160, 70), 0.25, 8),
    ]
    for x, y, r, col, a, soft in bokeh:
        c.disc(x, y, r, col, a, soft=soft)
    # bright cores inside a few bokeh discs
    c.disc(150, 150, 14, (255, 190, 110), 0.50, soft=6)
    c.disc(880, 130, 11, (255, 170, 100), 0.45, soft=5)
    c.disc(250, 60, 8, (255, 200, 130), 0.45, soft=4)
    c.grain_region(0, 0, 1024, 800, 7.0, 0.05, seed=3)


def _table(c):
    c.poly([(0, 800), (1024, 800), (1024, 1024), (0, 1024)], TABLE)
    c.line(0, 800, 1024, 800, 3, (106, 58, 24), 0.6)
    # plank separations, gently wavy
    for ybase, seed in ((858, 21), (918, 22), (978, 23)):
        _wavy_hline(c, ybase, 0, 1024, 64, 7, 90, seed, 3, TABLE_DARK, 0.40)
    # wood grain: thin wavy darker lines
    for k in range(14):
        ybase = 812 + k * 15 + int((vnoise(k * 3.7, 0, 31) - 0.5) * 8)
        _wavy_hline(c, ybase, 0, 1024, 32, 6, 140, 40 + k, 2.5,
                    shade(TABLE, 0.55), 0.25)
    c.grain_region(0, 800, 1024, 1024, 5.0, 0.06, seed=5)


def _bowl(c):
    # soft drop shadow on the table
    c.soft_ellipse(512, 905, 335, 52, (16, 8, 2), 0.55)
    c.soft_ellipse(512, 898, 300, 40, (24, 12, 4), 0.50)
    # ceramic body: red with a lighter upper glaze and dark base curve
    c.ellipse(512, 828, 305, 92, BOWL_RED)
    c.ellipse(512, 818, 300, 82, BOWL_RED_LT, 0.55)
    c.soft_ellipse(512, 862, 290, 52, (90, 10, 4), 0.50)
    # gold-red rim + glaze specular streak along the front rim
    c.ellipse_ring(512, 826, 303, 90, 7, BOWL_RIM, 0.85)
    c.bezier((280, 880), (400, 908), (620, 908), (740, 878),
             6, (248, 160, 96), 0.55)
    c.bezier((330, 892), (430, 912), (580, 912), (690, 888),
             3, (255, 200, 140), 0.35)
    # pale broth pools spilled on the table beside the bowl
    c.ellipse(298, 868, 58, 13, (240, 210, 160), 0.55)
    c.ellipse(726, 864, 52, 12, (240, 210, 160), 0.55)


def _broth(c):
    c.ellipse(512, 822, 272, 76, BROTH)
    c.radial_glow(480, 798, 200, BROTH_LT, 0.70)
    c.radial_glow(560, 845, 150, (160, 70, 10), 0.40)
    c.bezier((330, 790), (450, 772), (600, 788), (700, 778),
             5, BROTH_HI, 0.45)
    c.ellipse_ring(512, 822, 268, 73, 4, (120, 50, 8), 0.50)
    # oil sheen swirls on the surface
    c.bezier((360, 800), (480, 780), (600, 810), (700, 795),
             5, BROTH_HI, 0.30)
    c.bezier((380, 840), (500, 825), (600, 848), (690, 832),
             4, BROTH_HI, 0.25)
    c.bezier((420, 790), (520, 775), (600, 792), (660, 782),
             3, (255, 200, 110), 0.30)
    # fine broth texture
    c.grain_region(250, 750, 775, 900, 4.0, 0.07, seed=7)
    # green onion rings
    for x, y, r in ((430, 815, 10), (600, 845, 9), (380, 845, 8),
                    (660, 810, 9), (520, 850, 8), (350, 800, 7)):
        c.ring(x, y, r, 3.5, (58, 122, 32), 0.9)
        c.disc(x, y, 2.5, (90, 160, 50), 0.8)
    # halved egg, right side
    c.ellipse(648, 838, 44, 17, (250, 244, 225))
    c.disc(648, 838, 13, (248, 184, 48))
    c.disc(644, 834, 4, WHITE, 0.8)
    # noodle strands, short and wavy
    c.bezier((330, 828), (420, 818), (500, 836), (580, 824),
             4, (240, 208, 144), 0.75)
    c.bezier((560, 842), (620, 832), (670, 848), (710, 838),
             3.5, (240, 208, 144), 0.6)
    c.bezier((300, 846), (380, 838), (440, 852), (500, 844),
             3.5, (240, 208, 144), 0.55)


def _steam(c):
    # soft wavy wisps rising above the bowl, behind the koi
    c.bezier((385, 770), (360, 690), (405, 610), (375, 525),
             13, WHITE, 0.07)
    c.bezier((585, 760), (610, 675), (570, 595), (602, 515),
             14, WHITE, 0.08)
    c.bezier((690, 755), (672, 685), (702, 615), (680, 550),
             11, WHITE, 0.06)
    c.bezier((405, 760), (388, 685), (412, 615), (392, 545),
             8, WHITE, 0.05)
    c.bezier((600, 750), (618, 675), (588, 605), (614, 535),
             8, WHITE, 0.06)


def _tapered_bezier(c, p0, p1, p2, p3, w0, w1, color, alpha=1.0):
    """Cubic bezier whose stroke width tapers from w0 to w1."""
    approx = (math.hypot(p1[0] - p0[0], p1[1] - p0[1]) +
              math.hypot(p2[0] - p1[0], p2[1] - p1[1]) +
              math.hypot(p3[0] - p2[0], p3[1] - p2[1]))
    steps = max(6, int(approx / 6) + 1)
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] +
             3 * mt * t * t * p2[0] + t ** 3 * p3[0])
        y = (mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] +
             3 * mt * t * t * p2[1] + t ** 3 * p3[1])
        c.disc(x, y, w0 + (w1 - w0) * t, color, alpha)


def _splash_behind(c):
    # tall tapering broth plumes flanking the koi, breaking into spray
    _tapered_bezier(c, (410, 805), (360, 720), (335, 655), (325, 595),
                    11, 3, BROTH_LT, 0.90)
    _tapered_bezier(c, (410, 805), (368, 725), (343, 663), (333, 605),
                    5, 1.5, BROTH_HI, 0.70)
    _tapered_bezier(c, (525, 805), (575, 720), (605, 660), (620, 600),
                    10, 3, BROTH_LT, 0.90)
    _tapered_bezier(c, (525, 805), (568, 725), (597, 668), (611, 610),
                    4.5, 1.5, BROTH_HI, 0.70)
    # spray droplets at the plume tips
    for x, y, r in ((318, 585, 7), (330, 565, 5), (305, 600, 5),
                    (628, 590, 7), (638, 570, 5), (612, 600, 5),
                    (345, 640, 6), (605, 645, 6)):
        c.disc(x, y, r, BROTH_LT, 0.85)
        c.disc(x - r * 0.3, y - r * 0.3, r * 0.35, WHITE, 0.85)


def _koi(c):
    spine = [(452, 838), (428, 705), (442, 565),
             (515, 425), (608, 322), (688, 252)]
    pts = _catmull(spine, 22)
    n = len(pts)
    r_stops = [(0.0, 40), (0.18, 66), (0.42, 108),
               (0.62, 104), (0.82, 86), (1.0, 70)]
    col_stops = [(0.0, KOI_DEEP), (0.35, (232, 120, 16)),
                 (0.7, KOI_MID), (1.0, (238, 132, 20))]

    def frame(i):
        """Spine point, tangent and belly-side perpendicular at index i."""
        x, y = pts[i]
        x0, y0 = pts[max(0, i - 1)]
        x1, y1 = pts[min(n - 1, i + 1)]
        tx, ty = x1 - x0, y1 - y0
        L = math.hypot(tx, ty) or 1.0
        tx, ty = tx / L, ty / L
        # spine runs up-right; (-ty, tx) points right-down = belly side
        return (x, y), (tx, ty), (-ty, tx)

    # contact shadow where the koi exits the broth
    c.soft_ellipse(465, 800, 95, 24, (90, 40, 6), 0.45)
    # tail lobes, half-submerged in the broth
    c.poly([(452, 838), (398, 872), (428, 896)], FIN, 0.55)
    c.poly([(452, 838), (512, 876), (482, 900)], FIN, 0.55)
    # body: dense discs along the spine, radius + color profiled
    for i in range(n):
        t = i / (n - 1)
        (x, y), _, _ = frame(i)
        c.disc(x, y, _profile(t, r_stops), _profile(t, col_stops), 1.0)
    # cream belly as a narrower band on the lower-right side
    for i in range(0, n, 2):
        t = i / (n - 1)
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        c.disc(x + px * 0.50 * r, y + py * 0.50 * r,
               0.50 * r, mix(BELLY, KOI_GOLD, 0.18 * (1.0 - t)), 0.92)
    # soft orange tint along the belly edge
    for i in range(0, n, 2):
        t = i / (n - 1)
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        c.disc(x + px * 0.95 * r, y + py * 0.95 * r, 3.5, KOI_LT, 0.50)
    # warm back highlight on the upper-left side
    for i in range(0, n, 2):
        t = i / (n - 1)
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        c.disc(x - px * 0.45 * r, y - py * 0.45 * r,
               0.42 * r, KOI_GOLD, 0.45)
    # scale rows: small subtle arcs on the orange back half
    for i in range(6, n - 8, 6):
        t = i / (n - 1)
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        c.ring(x - px * 0.45 * r, y - py * 0.45 * r,
               0.10 * r + 3, 2.0, mix(KOI_DEEP, KOI_LT, 0.35), 0.38)
    for i in range(9, n - 8, 6):
        t = i / (n - 1)
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        c.ring(x - px * 0.30 * r, y - py * 0.30 * r,
               0.09 * r + 2.5, 1.8, mix(KOI_DEEP, KOI_GOLD, 0.55), 0.32)
    # strong specular rim light along the back edge
    for i in range(8, n - 6):
        t = i / (n - 1)
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        c.disc(x - px * 0.98 * r, y - py * 0.98 * r,
               5.5, (255, 208, 128), 0.50)
    # dorsal fin: low translucent ridge along the back, t 0.30..0.55
    edge = []
    ridge = []
    for t in (0.30, 0.36, 0.42, 0.48, 0.55):
        i = int(t * (n - 1))
        (x, y), _, (px, py) = frame(i)
        r = _profile(t, r_stops)
        edge.append((x - px * 0.92 * r, y - py * 0.92 * r))
        ridge.append((x - px * 1.08 * r, y - py * 1.08 * r))
    c.poly([edge[0], ridge[1], ridge[2], ridge[3], edge[4]],
           (226, 118, 16), 0.35)
    for a, b in ((edge[0], ridge[1]), (edge[2], ridge[2]),
                 (edge[3], ridge[3])):
        c.line(a[0], a[1], b[0], b[1], 2.5, shade(FIN, 0.75), 0.4)
    # pectoral fin on the belly side, t ~0.62 — a soft curved leaf
    i = int(0.62 * (n - 1))
    (bx, by), (tx, ty), (px, py) = frame(i)
    base_top = (bx - tx * 30, by - ty * 30)
    base_bot = (bx + tx * 42, by + ty * 42)
    mid = (bx + px * 48 + tx * 6, by + py * 48 + ty * 6)
    tip = (bx + px * 68 + tx * 12, by + py * 68 + ty * 12)
    c.poly([base_top, mid, tip, base_bot], (232, 128, 20), 0.48)
    c.disc(tip[0], tip[1], 6, (232, 128, 20), 0.48)
    for f in (0.4, 0.7):
        mx = base_top[0] + (base_bot[0] - base_top[0]) * f
        my = base_top[1] + (base_bot[1] - base_top[1]) * f
        c.line(mx, my, tip[0], tip[1], 2.0, shade(FIN, 0.75), 0.4)
    # head, slightly tapered toward the snout
    c.disc(688, 252, 68, KOI_MID)
    c.disc(736, 240, 36, KOI_LT)
    c.disc(662, 232, 26, KOI_GOLD, 0.50)
    c.soft_ellipse(700, 285, 50, 26, (190, 90, 10), 0.40)
    # eye: smaller, white, dark iris, pupil, sharp catchlight
    c.disc(712, 222, 14, WHITE)
    c.disc(715, 224, 8.5, (40, 20, 8))
    c.disc(717, 225, 4.5, (10, 5, 2))
    c.disc(708, 217, 4, WHITE, 0.95)
    c.disc(721, 231, 2, WHITE, 0.70)
    # mouth + barbels
    c.bezier((742, 268), (758, 262), (772, 252), (780, 240),
             5, (122, 42, 8), 0.90)
    c.bezier((748, 262), (770, 285), (782, 305), (788, 325),
             4, (214, 112, 16), 0.85)
    c.bezier((738, 268), (752, 292), (758, 312), (760, 330),
             4, (214, 112, 16), 0.85)


def _splash_front(c):
    # droplets with a soft shadow, a broth body and a highlight dot
    drops = [
        (330, 700, 7), (355, 655, 5), (300, 760, 6), (640, 690, 7),
        (665, 640, 5), (700, 720, 6), (290, 830, 5), (730, 800, 6),
        (410, 620, 4), (590, 600, 4), (350, 780, 5), (690, 770, 5),
        (315, 725, 4), (675, 700, 4), (450, 600, 5), (545, 585, 4),
    ]
    for x, y, r in drops:
        c.disc(x + r * 0.2, y + r * 0.3, r * 0.7, (120, 50, 8), 0.30)
        c.disc(x, y, r, BROTH_LT, 0.90)
        c.disc(x - r * 0.3, y - r * 0.3, r * 0.35, WHITE, 0.90)
    # bright broth arcs curling off the exit point
    c.bezier((420, 800), (400, 760), (395, 720), (400, 690),
             6, BROTH_HI, 0.70)
    c.bezier((520, 800), (540, 760), (545, 720), (540, 690),
             6, BROTH_HI, 0.70)


def _chopsticks(c):
    # pair flying up-left, dark lacquer with red tips + motion streaks
    c.line(138, 108, 318, 288, 13, (42, 22, 8))
    c.line(278, 248, 318, 288, 13, (192, 24, 8))
    c.line(150, 112, 300, 262, 3, (120, 70, 30), 0.70)
    c.line(168, 92, 348, 272, 13, (42, 22, 8))
    c.line(308, 232, 348, 272, 13, (192, 24, 8))
    c.line(180, 96, 330, 246, 3, (120, 70, 30), 0.70)
    c.line(120, 150, 180, 210, 3, WHITE, 0.30)
    c.line(200, 80, 250, 130, 3, WHITE, 0.25)


def _sparkles(c):
    for x, y, r, a in ((700, 200, 12, 0.85), (185, 545, 10, 0.80),
                       (355, 790, 9, 0.75), (560, 380, 8, 0.70),
                       (95, 95, 8, 0.60), (880, 330, 8, 0.65),
                       (640, 620, 7, 0.60), (260, 660, 7, 0.55)):
        c.star4(x, y, r, WHITE, a)


def render_scene():
    """Compose the full 1024x1024 scene and return PNG bytes."""
    c = Canvas()
    _background(c)
    _table(c)
    _bowl(c)
    _broth(c)
    _steam(c)
    _splash_behind(c)
    _koi(c)
    _splash_front(c)
    _chopsticks(c)
    _sparkles(c)
    c.vignette(0.24)
    return c.to_png_bytes()
