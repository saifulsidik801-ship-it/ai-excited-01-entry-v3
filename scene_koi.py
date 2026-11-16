"""Golden Koi Ramen — a giant golden koi bursting out of a ramen bowl.

Pure-stdlib deterministic render. Scene: warm bokeh restaurant background,
wooden table, a deep red bowl of ramen, and a huge golden koi leaping out
diagonally, broth splashing, chopsticks flying, steam rising.
"""

import math

from render import Canvas, W, H, lerp, lerp_color, _hash_noise

# ---------------------------------------------------------------- geometry
BOWL_CX, BOWL_CY = 512, 845
BROTH_RX, BROTH_RY = 298, 76

# Koi spine: cubic bezier, tail in the broth -> head upper right.
SPINE = ((452, 800), (420, 590), (560, 400), (792, 232))
# Radius profile knots (t, radius): thick muscular mid-body, tapered tail.
RADIUS_KNOTS = ((0.00, 40), (0.15, 62), (0.35, 86), (0.55, 98),
                (0.75, 90), (0.90, 80), (1.00, 78))
# Body colour knots (t, rgb): burnt orange tail -> bright gold head.
COLOR_KNOTS = ((0.00, (196, 88, 18)), (0.50, (232, 122, 26)),
               (1.00, (248, 158, 44)))
BELLY = (252, 232, 190)
HEAD_C = (805, 220)          # head ellipse centre
HEAD_RX, HEAD_RY = 96, 80
HEAD_ROT = -0.67             # radians, matches spine tangent at the head
EYE_C = (838, 190)


def _smooth_knots(knots, t):
    """Cosine-smooth interpolation through (t, value) knots."""
    if t <= knots[0][0]:
        return knots[0][1]
    if t >= knots[-1][0]:
        return knots[-1][1]
    for i in range(len(knots) - 1):
        t0, v0 = knots[i]
        t1, v1 = knots[i + 1]
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0)
            u = 0.5 - 0.5 * math.cos(math.pi * u)
            if isinstance(v0, tuple):
                return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return lerp(v0, v1, u)
    return knots[-1][1]


def spine_samples(n=150):
    """Sample the spine: list of (x, y, tx, ty, t, radius, colour)."""
    pts = Canvas.bezier(SPINE[0], SPINE[1], SPINE[2], SPINE[3], n)
    out = []
    cum = 0.0
    prev = None
    for i, (x, y) in enumerate(pts):
        t = i / n
        if prev is not None:
            cum += math.hypot(x - prev[0], y - prev[1])
        prev = (x, y)
        tx, ty = Canvas.bezier_tangent(SPINE[0], SPINE[1], SPINE[2], SPINE[3], t)
        out.append([x, y, tx, ty, t, _smooth_knots(RADIUS_KNOTS, t),
                    _smooth_knots(COLOR_KNOTS, t), cum])
    return out


def inner_normal(tx, ty, x, y):
    """Unit normal pointing toward the bowl (the koi's belly side)."""
    nx, ny = -ty, tx
    dx, dy = BOWL_CX - x, BOWL_CY - y
    if nx * dx + ny * dy < 0:
        nx, ny = -nx, -ny
    return nx, ny


# ---------------------------------------------------------------- backdrop
def draw_background(cv):
    cv.vgrad(0, 480, (24, 12, 5), (62, 30, 9))
    cv.vgrad(481, 1023, (62, 30, 9), (112, 58, 18))
    # warm bokeh: soft glowing circles, deterministic placement
    bokeh = [
        (120, 130, 62, (255, 170, 80), 0.16), (880, 90, 74, (255, 190, 100), 0.14),
        (930, 300, 52, (240, 150, 60), 0.15), (80, 420, 58, (255, 180, 90), 0.13),
        (160, 700, 44, (230, 140, 55), 0.12), (930, 640, 66, (255, 175, 85), 0.13),
        (300, 120, 40, (255, 200, 120), 0.15), (700, 700, 48, (240, 155, 65), 0.11),
        (60, 820, 54, (220, 130, 50), 0.10), (960, 850, 46, (255, 180, 90), 0.10),
        (420, 90, 34, (255, 205, 130), 0.16), (620, 150, 30, (250, 170, 80), 0.14),
        (210, 300, 36, (255, 185, 95), 0.12), (830, 470, 38, (240, 150, 60), 0.12),
        (110, 560, 30, (255, 195, 110), 0.12), (500, 300, 26, (255, 210, 140), 0.10),
    ]
    for (x, y, r, col, a) in bokeh:
        cv.soft_disc(x, y, r, col, a)
        cv.soft_disc(x, y, r * 0.45, (255, 220, 150), a * 0.8)


def draw_table(cv):
    cv.vgrad(856, 1023, (58, 34, 13), (36, 20, 7))
    # plank seams
    for y in (898, 948, 996):
        cv.capsule(0, y, 1024, y, 2, (24, 13, 5), 0.7)
    # wood grain: wavy darker lines
    for k in range(9):
        yb = 872 + k * 17
        pts = []
        for x in range(0, 1025, 32):
            wob = 4.0 * math.sin(x * 0.011 + k * 1.7)
            pts.append((x, yb + wob))
        for i in range(len(pts) - 1):
            cv.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                       1.5, (30, 16, 6), 0.45)
    # warm light pool under the bowl
    cv.soft_disc(512, 950, 300, (255, 190, 110), 0.10)
    cv.grain(0, 856, 1024, 1024, 9)


# ---------------------------------------------------------------- bowl
def draw_bowl(cv):
    # cast shadow on the table
    cv.soft_disc(500, 918, 330, (12, 6, 2), 0.42)
    cv.ellipse(500, 912, 330, 42, (12, 6, 2), 0.42)
    # bowl outer wall: deep red lacquer
    cv.ellipse(BOWL_CX, BOWL_CY, 335, 92, (108, 26, 16), 1.0)
    cv.ellipse(BOWL_CX, BOWL_CY - 8, 322, 82, (132, 34, 20), 1.0)
    # rim band with glaze highlight on the near edge
    cv.ellipse_ring(BOWL_CX, BOWL_CY - 4, 328, 88, 10, (186, 52, 30), 0.95)
    cv.ellipse_ring(BOWL_CX, BOWL_CY - 4, 328, 88, 5, (255, 140, 80), 0.75,
                    a0=0.15 * math.pi, a1=0.85 * math.pi)
    # broth surface: amber radial glow, darker toward the rim
    cv.ellipse(BOWL_CX, BOWL_CY - 2, BROTH_RX, BROTH_RY, (150, 86, 22), 1.0)
    cv.soft_disc(BOWL_CX - 20, BOWL_CY - 12, 210, (224, 146, 46), 0.85)
    cv.soft_disc(BOWL_CX + 40, BOWL_CY + 6, 150, (238, 168, 62), 0.55)
    # inner wall shadow on the far side of the broth
    cv.ellipse_ring(BOWL_CX, BOWL_CY - 2, BROTH_RX - 8, BROTH_RY - 6, 7,
                    (96, 50, 12), 0.6, a0=1.05 * math.pi, a1=1.95 * math.pi)
    # glossy reflection streak on the broth
    cv.ellipse(BOWL_CX - 90, BOWL_CY - 26, 120, 16, (255, 205, 120), 0.30,
               rot=-0.12)
    # noodles: pale curved strokes in the broth
    noodle_paths = [
        ((250, 838), (330, 862), (430, 848), (500, 862)),
        ((560, 876), (640, 856), (720, 872), (780, 852)),
        ((300, 868), (400, 884), (520, 872), (610, 886)),
        ((640, 830), (700, 846), (760, 834), (800, 844)),
        ((380, 830), (450, 818), (540, 828), (600, 816)),
    ]
    for p0, p1, p2, p3 in noodle_paths:
        pts = Canvas.bezier(p0, p1, p2, p3, 24)
        for i in range(len(pts) - 1):
            cv.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                       3.5, (236, 194, 112), 0.9)
    # soft-boiled egg: white with golden yolk
    cv.ellipse(668, 856, 58, 22, (250, 244, 228), 0.95)
    cv.disc(668, 854, 16, (240, 168, 38), 0.95)
    cv.disc(662, 849, 5, (255, 214, 110), 0.9)
    # green onion rings
    for (x, y) in ((300, 852), (352, 876), (590, 842), (730, 862),
                   (420, 880), (770, 838)):
        cv.ellipse_ring(x, y, 9, 6, 3, (74, 146, 62), 0.9)
    # ripple rings where the koi exits the broth
    cv.ellipse_ring(468, 796, 96, 24, 4, (250, 178, 80), 0.5)
    cv.ellipse_ring(468, 796, 138, 34, 4, (244, 164, 66), 0.35)
    cv.ellipse_ring(468, 796, 182, 44, 4, (238, 152, 56), 0.22)

# ---------------------------------------------------------------- koi
def draw_tail_fin(cv, samples):
    """Forked tail, mostly submerged, lobes rising above the broth."""
    base = samples[0]
    bx, by = base[0], base[1]
    # left lobe sweeping down-left into the broth
    pts = Canvas.bezier((bx, by), (bx - 60, by + 10), (bx - 130, by - 20),
                        (bx - 185, by - 55), 20)
    for i in range(len(pts) - 1):
        w = 16 - 9 * i / (len(pts) - 1)
        cv.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                   w, (222, 108, 22), 0.9)
    # right lobe sweeping down-right
    pts = Canvas.bezier((bx, by), (bx + 40, by + 26), (bx + 110, by + 8),
                        (bx + 165, by - 30), 20)
    for i in range(len(pts) - 1):
        w = 16 - 9 * i / (len(pts) - 1)
        cv.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                   w, (228, 118, 26), 0.9)
    # lighter fin edges
    cv.capsule(bx - 60, by + 8, bx - 180, by - 52, 3, (255, 196, 110), 0.7)
    cv.capsule(bx + 40, by + 24, bx + 160, by - 28, 3, (255, 196, 110), 0.7)


def draw_body(cv, samples):
    # soft drop shadow of the body, offset down-left (light is upper right)
    prev = None
    for (x, y, tx, ty, t, r, col, arc) in samples:
        if prev is not None and arc - prev < 5:
            continue
        prev = arc
        cv.disc(x - 13, y + 12, r * 1.01, (36, 14, 4), 0.30, feather=4)
    # body: overlapping discs along the spine, colour warming toward head
    prev = None
    for (x, y, tx, ty, t, r, col, arc) in samples:
        if prev is not None and arc - prev < 5:
            continue
        prev = arc
        cv.disc(x, y, r, col, 1.0, feather=2)
    # deeper orange koi patches on the back (outer side)
    for (t, off, pr) in ((0.24, 0.42, 34), (0.44, 0.55, 40),
                         (0.62, 0.38, 36), (0.80, 0.50, 30)):
        s = samples[int(t * (len(samples) - 1))]
        x, y, tx, ty, _, r, _, _ = s
        nx, ny = inner_normal(tx, ty, x, y)
        cv.disc(x - nx * off * r, y - ny * off * r, pr, (206, 96, 18),
                0.35, feather=10)
    # belly band: narrower cream underside on the inner (bowl) side
    prev = None
    for (x, y, tx, ty, t, r, col, arc) in samples:
        if prev is not None and arc - prev < 6:
            continue
        prev = arc
        nx, ny = inner_normal(tx, ty, x, y)
        cv.disc(x + nx * 0.55 * r, y + ny * 0.55 * r, r * 0.42, BELLY,
                0.95, feather=7)
    # belly edge shading: a soft gold line where belly meets orange
    prev = None
    for (x, y, tx, ty, t, r, col, arc) in samples:
        if prev is not None and arc - prev < 8:
            continue
        prev = arc
        nx, ny = inner_normal(tx, ty, x, y)
        cv.disc(x + nx * 0.30 * r, y + ny * 0.30 * r, 3.5,
                (255, 205, 120), 0.35)


def draw_scales(cv, samples):
    """Overlapping scale crescents on the orange back of the body."""
    # walk the spine by arc length, placing scale stations
    stations = []
    last = -100.0
    for s in samples:
        if s[7] - last >= 22:
            stations.append(s)
            last = s[7]
    for si, s in enumerate(stations):
        x, y, tx, ty, t, r, col, arc = s
        if t < 0.08 or t > 0.88:
            continue
        nx, ny = inner_normal(tx, ty, x, y)
        # rows across the BACK (outer side); alternate rows offset by half.
        # In this formula a positive offset moves toward the outer side.
        row_off = -0.30 if (si % 2 == 0) else 0.0
        for off in (0.62, 0.30):
            ox = x - nx * (off + row_off * 0.06) * r
            oy = y - ny * (off + row_off * 0.06) * r
            sc = max(6.0, r * 0.13)
            # scale plate: wider than tall, aligned with the body axis
            rot = math.atan2(ty, tx)
            cv.ellipse(ox, oy, sc * 1.5, sc * 0.75, (186, 84, 16), 0.35,
                       rot=rot, feather=2)
            # carve with body colour shifted toward the head: crescent stays
            # on the tail side, like real overlapping scales
            cv.ellipse(ox + tx * 5.5, oy + ty * 5.5, sc * 1.15, sc * 0.55,
                       col, 0.8, rot=rot, feather=2)
            # bright top edge of the crescent
            cv.arc(ox, oy, sc * 0.70, math.pi * 1.05, math.pi * 1.95,
                   (255, 212, 132), 0.45, thick=1.6)


def draw_dorsal_fin(cv, samples):
    """Scalloped dorsal fin along the back edge, mid-body."""
    edge = []
    tips = []
    for s in samples:
        x, y, tx, ty, t, r, col, arc = s
        if t < 0.30 or t > 0.74:
            continue
        nx, ny = inner_normal(tx, ty, x, y)
        ex, ey = x - nx * (r + 2), y - ny * (r + 2)
        edge.append((ex, ey))
        h = 8 + 12 * math.sin((t - 0.30) / 0.44 * math.pi)
        h *= 0.85 + 0.15 * math.sin(arc * 0.35)
        tips.append((ex - nx * h, ey - ny * h))
    if len(edge) < 4:
        return
    poly = edge + tips[::-1]
    cv.poly(poly, (226, 114, 26), 0.88)
    # veins from the body edge out to the fin tips
    for i in range(0, len(edge), 3):
        cv.capsule(edge[i][0], edge[i][1], tips[i][0], tips[i][1],
                   1.6, (168, 68, 12), 0.55)
    # bright fin edge
    for i in range(len(tips) - 1):
        cv.capsule(tips[i][0], tips[i][1], tips[i + 1][0], tips[i + 1][1],
                   2.0, (255, 198, 116), 0.6)


def draw_pectoral_fin(cv, samples):
    """Narrow fan-shaped pectoral fin on the belly side, below the head."""
    s = samples[int(0.74 * (len(samples) - 1))]
    x, y, tx, ty, t, r, col, arc = s
    nx, ny = inner_normal(tx, ty, x, y)
    bx, by = x + nx * r * 0.45, y + ny * r * 0.45
    # narrow fan: tips spread slightly, pointing down along the belly side
    tips = []
    for k, (a, ln) in enumerate(((-0.30, 62), (-0.08, 76), (0.14, 72),
                                (0.34, 56))):
        # direction: mostly along the inner normal, fanned by tangent
        dx = nx + tx * a
        dy = ny + ty * a
        dl = math.hypot(dx, dy) or 1.0
        tips.append((bx + dx / dl * ln, by + dy / dl * ln))
    poly = [(bx, by)] + tips
    cv.poly(poly, (236, 140, 44), 0.72)
    for tip in tips:
        cv.capsule(bx, by, tip[0], tip[1], 1.8, (178, 76, 14), 0.6)
    cv.capsule(bx, by, tips[1][0], tips[1][1], 2.4, (255, 200, 120), 0.6)


def draw_head(cv):
    # neck blend: widen the body into the head so it reads as one fish
    cv.ellipse(762, 258, 78, 66, (242, 142, 38), 1.0, rot=HEAD_ROT)
    # head mass: big distinct ellipse, rotated along the spine tangent
    cv.ellipse(HEAD_C[0], HEAD_C[1], HEAD_RX, HEAD_RY, (238, 132, 34), 1.0,
               rot=HEAD_ROT)
    # warm top light on the head
    cv.ellipse(HEAD_C[0] + 8, HEAD_C[1] - 14, 86, 62, (250, 170, 60), 0.7,
               rot=HEAD_ROT)
    # darker blend where the head meets the body
    cv.ellipse(HEAD_C[0] - 58, HEAD_C[1] + 42, 52, 44, (206, 96, 20), 0.5,
               rot=HEAD_ROT)
    # gill curve
    cv.arc(HEAD_C[0] - 38, HEAD_C[1] + 18, 46, -0.4, 1.5, (170, 72, 14),
           0.6, thick=4)
    # mouth: small dark opening at the front tip, with a lower lip
    mx, my = 888, 174
    cv.ellipse(mx, my, 14, 8, (88, 28, 8), 0.9, rot=HEAD_ROT)
    cv.arc(mx - 2, my + 4, 13, 0.3, 2.6, (150, 66, 16), 0.8, thick=3)
    # barbels: two whiskers curving down from the mouth
    pts = Canvas.bezier((882, 184), (894, 212), (900, 232), (894, 258), 16)
    for i in range(len(pts) - 1):
        cv.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                   4.0, (198, 106, 26), 0.95)
    pts = Canvas.bezier((876, 188), (878, 218), (872, 240), (858, 262), 16)
    for i in range(len(pts) - 1):
        cv.capsule(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                   4.0, (198, 106, 26), 0.95)
    # eye: big and expressive, with a sharp catchlight
    ex, ey = EYE_C
    cv.disc(ex, ey, 18, (250, 246, 236), 1.0)
    cv.disc(ex + 2, ey + 1, 12, (28, 14, 5), 1.0)
    cv.disc(ex + 2, ey + 1, 6.5, (8, 4, 2), 1.0)
    cv.disc(ex - 3, ey - 5, 4.5, (255, 255, 255), 1.0)
    cv.disc(ex + 6, ey + 6, 2.0, (255, 255, 255), 0.85)
    # brow shading above the eye
    cv.ellipse(ex - 2, ey - 20, 20, 7, (214, 104, 22), 0.5, rot=-0.3)


def draw_rim_light(cv, samples):
    """Bright rim light along the koi's top edge (key light upper right)."""
    prev = None
    for (x, y, tx, ty, t, r, col, arc) in samples:
        if t < 0.12 or t > 0.94:
            continue
        nx, ny = inner_normal(tx, ty, x, y)
        lx, ly = x - nx * r * 0.88, y - ny * r * 0.88
        if prev is not None:
            cv.capsule(prev[0], prev[1], lx, ly, 4.5,
                       (255, 216, 134), 0.7)
        prev = (lx, ly)

# ---------------------------------------------------------------- splash
def draw_splash_crown_back(cv):
    """Full broth ring around the exit point (drawn before the koi)."""
    cv.ellipse_ring(462, 792, 130, 34, 9, (240, 164, 62), 0.85)


def draw_splash_crown(cv):
    """Broth crown ringing the koi's exit point (front half after the body)."""
    cv.ellipse_ring(462, 792, 130, 34, 7, (240, 164, 62), 0.85,
                    a0=0.15 * math.pi, a1=0.85 * math.pi)
    cv.ellipse_ring(462, 792, 130, 34, 4, (255, 206, 122), 0.8,
                    a0=0.15 * math.pi, a1=0.85 * math.pi)


def draw_plumes(cv):
    """Tall tapered broth plumes breaking into droplet spray."""
    plumes = [
        ((415, 792), (378, 662), (392, 560), (360, 462), 18, 6),
        ((505, 796), (524, 682), (512, 580), (534, 480), 16, 5),
        ((455, 800), (330, 724), (288, 640), (256, 534), 15, 5),
    ]
    for (p0, p1, p2, p3, w0, w1) in plumes:
        pts = Canvas.bezier(p0, p1, p2, p3, 26)
        for i, (x, y) in enumerate(pts):
            u = i / (len(pts) - 1)
            w = w0 + (w1 - w0) * u
            col = (234, 152, 54) if u < 0.7 else (242, 168, 72)
            cv.disc(x, y, w, col, 0.92, feather=2)
            # faint inner sheen, offset toward the light
            cv.disc(x + 3, y - 2, w * 0.38, (255, 198, 112), 0.30,
                    feather=2)
    # droplet spray: deterministic scatter around the plume tips
    drops = []
    for k in range(46):
        u = _hash_noise(k, 3)
        v = _hash_noise(k, 11)
        plume = plumes[k % 3]
        p0, p1, p2, p3, _, _ = plume
        pts = Canvas.bezier(p0, p1, p2, p3, 10)
        bx, by = pts[int(u * (len(pts) - 1))]
        ox = (v - 0.5) * 90
        oy = -u * 70 - _hash_noise(k, 23) * 40
        drops.append((bx + ox, by + oy, 2.5 + _hash_noise(k, 31) * 5.5))
    for (x, y, r) in drops:
        cv.disc(x, y, r, (240, 166, 62), 0.95)
        cv.disc(x - r * 0.3, y - r * 0.3, max(1.2, r * 0.32),
                (255, 255, 255), 0.9)


def draw_chopsticks(cv):
    """Two chopsticks flying diagonally through the splash at the exit point."""
    sticks = [
        ((262, 468), (522, 852), 12, 5),
        ((322, 448), (582, 822), 11, 5),
    ]
    for ((ax, ay), (bx, by), w0, w1) in sticks:
        dx, dy = bx - ax, by - ay
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln, dx / ln
        # tapered quad: wide at the top, narrow at the tip
        pts = [(ax + nx * w0 / 2, ay + ny * w0 / 2),
               (ax - nx * w0 / 2, ay - ny * w0 / 2),
               (bx - nx * w1 / 2, by - ny * w1 / 2),
               (bx + nx * w1 / 2, by + ny * w1 / 2)]
        cv.poly(pts, (60, 33, 15), 1.0)
        # red lacquer tip: last 70 px of the stick
        tx0, ty0 = ax + dx * 0.82, ay + dy * 0.82
        tw0 = w0 + (w1 - w0) * 0.82
        tip = [(tx0 + nx * tw0 / 2, ty0 + ny * tw0 / 2),
               (tx0 - nx * tw0 / 2, ty0 - ny * tw0 / 2),
               (bx - nx * w1 / 2, by - ny * w1 / 2),
               (bx + nx * w1 / 2, by + ny * w1 / 2)]
        cv.poly(tip, (180, 42, 28), 1.0)
        # wood highlight along the upper edge
        cv.capsule(ax + nx * 3, ay + ny * 3, bx + nx * 2, by + ny * 2,
                   2.0, (140, 88, 44), 0.7)
    # motion streaks trailing the sticks
    for (sx, sy, ex, ey) in ((210, 540, 330, 660), (270, 510, 390, 630),
                             (180, 620, 300, 740)):
        cv.capsule(sx, sy, ex, ey, 3, (255, 235, 200), 0.30)


# ---------------------------------------------------------------- steam
def draw_steam(cv):
    """Soft layered translucent wisps rising from the broth."""
    bases = [(322, 748), (385, 742), (435, 736), (488, 730), (545, 736),
             (596, 744)]
    for wi, (bx, by) in enumerate(bases):
        amp = 16 + 6 * _hash_noise(wi, 5)
        ph = wi * 1.9
        for k in range(14):
            u = k / 13.0
            y = by - u * 300
            x = bx + amp * math.sin(u * 5.2 + ph) - u * 24
            r = 22 + 15 * u + 6 * _hash_noise(wi, k)
            cv.soft_disc(x, y, r, (255, 236, 200), 0.16 + 0.06 * u)


def draw_sparkles(cv):
    """Small white plus-sparkles near the splash and in the background."""
    for k in range(10):
        x = 60 + _hash_noise(k, 7) * 900
        y = 60 + _hash_noise(k, 13) * 700
        # keep sparkles off the koi's face
        if 740 < x < 920 and 120 < y < 300:
            continue
        s = 4 + _hash_noise(k, 19) * 5
        a = 0.30 + _hash_noise(k, 29) * 0.25
        cv.capsule(x - s, y, x + s, y, 1.6, (255, 250, 230), a)
        cv.capsule(x, y - s, x, y + s, 1.6, (255, 250, 230), a)


def draw_vignette(cv):
    for (x, y) in ((-40, -40), (1064, -40), (-40, 1064), (1064, 1064)):
        cv.soft_disc(x, y, 330, (8, 4, 2), 0.16)


# ---------------------------------------------------------------- scene
def draw_scene(cv):
    draw_background(cv)
    draw_table(cv)
    draw_bowl(cv)
    draw_splash_crown_back(cv)
    samples = spine_samples(150)
    draw_tail_fin(cv, samples)
    draw_body(cv, samples)
    draw_scales(cv, samples)
    draw_dorsal_fin(cv, samples)
    draw_head(cv)
    draw_rim_light(cv, samples)
    draw_splash_crown(cv)
    draw_plumes(cv)
    draw_chopsticks(cv)
    draw_steam(cv)
    draw_sparkles(cv)
    draw_vignette(cv)
    return cv
