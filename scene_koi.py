"""Scene 1 — GOLDEN KOI RAMEN.

A giant golden koi bursting out of a ramen bowl on a wooden table:
broth splashing in arcs, chopsticks flying, steam curling, warm
restaurant light, chili-oil reds against koi gold.

Draws onto a render.Canvas. Pure standard library.
"""

import math

from render import Canvas


def _radius_profile(t):
    """Koi body radius along the spine: thin tail, fat belly, round head."""
    keys = [(0.00, 26), (0.15, 68), (0.45, 102), (0.65, 94),
            (0.85, 74), (1.00, 58)]
    for i in range(len(keys) - 1):
        t0, r0 = keys[i]
        t1, r1 = keys[i + 1]
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0)
            return r0 + (r1 - r0) * f
    return keys[-1][1]


def draw(c):
    W, H = c.w, c.h

    # -- warm restaurant background ------------------------------------
    c.vgrad((46, 26, 12), (122, 60, 20))
    c.glow(560, 380, 520, (255, 170, 60), 0.50)
    c.glow(180, 160, 200, (255, 120, 40), 0.35)
    c.glow(880, 140, 170, (255, 90, 30), 0.30)
    # bokeh lanterns
    for (x, y, r, col, a) in [
            (150, 150, 46, (255, 150, 60), 0.55),
            (880, 130, 36, (255, 110, 50), 0.55),
            (90, 430, 30, (255, 140, 70), 0.45),
            (935, 470, 40, (255, 120, 45), 0.45),
            (820, 60, 18, (255, 180, 90), 0.6),
            (240, 60, 14, (255, 160, 80), 0.6)]:
        c.circle(x, y, r, col, a)
        c.circle(x, y, int(r * 0.45), (255, 210, 130), a * 0.8)

    # -- wooden table ---------------------------------------------------
    c.poly([(0, 760), (W, 760), (W, H), (0, H)], (107, 66, 38))
    for y in (832, 906, 978):
        c.line(0, y, W, y, 5, (74, 44, 23), 0.9)
    # grain strokes
    c.curve((60, 800), (300, 812), (600, 798), (980, 820), 3,
            (90, 54, 30), 0.7)
    c.curve((40, 880), (350, 868), (700, 884), (1000, 872), 3,
            (90, 54, 30), 0.6)
    c.curve((80, 950), (400, 962), (750, 948), (1010, 962), 3,
            (82, 48, 26), 0.6)
    # soft shadow under the bowl
    c.ellipse(512, 905, 330, 42, (40, 20, 8), 0.35)

    # -- ramen bowl ------------------------------------------------------
    # outer lacquer body
    c.ellipse(512, 806, 300, 88, (138, 31, 18), 1.0, feather=2)
    # bowl wall: a crescent of lighter lacquer below the broth
    c.ellipse(512, 824, 282, 66, (168, 40, 26), 1.0)
    # foot ring
    c.ellipse(512, 888, 118, 16, (90, 18, 10), 1.0)
    # gold rim (ellipse band, follows the bowl)
    c.ellipse_ring(512, 800, 292, 76, 6, (232, 176, 84), 0.95)
    # broth
    c.ellipse(512, 798, 262, 60, (193, 68, 14), 1.0)
    c.ellipse(512, 792, 200, 44, (224, 106, 31), 1.0)
    # chili-oil swirls
    c.ellipse(430, 792, 46, 12, (138, 31, 10), 0.85)
    c.ellipse(610, 800, 52, 13, (138, 31, 10), 0.85)
    c.ellipse(520, 786, 30, 8, (160, 40, 12), 0.8)
    # noodle waves
    for (y0, amp, x0) in [(786, 7, 330), (798, 8, 360), (808, 6, 340),
                          (792, 7, 560), (804, 8, 590)]:
        c.curve((x0, y0), (x0 + 60, y0 - amp), (x0 + 130, y0 + amp),
                (x0 + 190, y0), 7, (242, 211, 138), 0.95)
    # narutomaki
    c.circle(400, 800, 26, (250, 246, 236), 1.0)
    c.ring(400, 800, 20, 5, (232, 120, 140), 1.0)
    c.circle(400, 800, 7, (232, 120, 140), 1.0)
    # soft egg
    c.ellipse(624, 802, 34, 22, (250, 238, 210), 1.0)
    c.circle(624, 802, 11, (245, 166, 38), 1.0)
    # green onion rings
    for (x, y) in [(350, 788), (470, 812), (560, 786), (680, 812),
                   (440, 780), (590, 816)]:
        c.ring(x, y, 9, 4, (90, 143, 60), 1.0)
        c.circle(x, y, 3, (120, 180, 80), 1.0)

    # -- koi spine --------------------------------------------------------
    spine = c.bezier((430, 775), (360, 520), (545, 360), (665, 250), 26)
    radii = [_radius_profile(i / 26) for i in range(27)]

    # tail fins first (body overlaps their roots): curved fan lobes
    # sweeping sideways along the broth surface
    t1 = c.bezier((430, 775), (370, 790), (320, 810), (300, 835), 12)
    t2 = c.bezier((300, 835), (340, 855), (400, 845), (434, 812), 12)
    c.poly(t1 + t2[1:], (250, 175, 80), 0.8)
    t3 = c.bezier((430, 775), (490, 790), (540, 810), (560, 835), 12)
    t4 = c.bezier((560, 835), (520, 855), (460, 845), (426, 812), 12)
    c.poly(t3 + t4[1:], (250, 175, 80), 0.8)
    c.curve((430, 775), (380, 800), (340, 820), (306, 834), 3,
            (230, 140, 40), 0.8)
    c.curve((430, 775), (480, 800), (520, 820), (554, 834), 3,
            (230, 140, 40), 0.8)

    # body: orange tube
    c.tube(spine, radii, (240, 138, 29), 1.0)
    # belly: cream tube offset down-right, slimmer
    belly = [(x + 16, y + 24) for (x, y) in spine]
    bradii = [r * 0.60 for r in radii]
    c.tube(belly, bradii, (255, 243, 214), 1.0)
    # top sheen: pale gold along the upper edge
    sheen = [(x - 12, y - 16) for (x, y) in spine]
    sradii = [r * 0.34 for r in radii]
    c.tube(sheen, sradii, (255, 196, 107), 0.85)
    # scales: darker rings along the upper side of the body
    for i in range(2, 25, 3):
        x, y = spine[i]
        c.ring(int(x) - 8, int(y) - 14, 10, 3, (217, 111, 14), 0.5)
    for i in range(3, 25, 4):
        x, y = spine[i]
        c.circle(int(x), int(y) - 20, 4, (217, 111, 14), 0.55)

    # dorsal fin: curved leaf hugging the orange back (not the belly seam)
    d1 = c.bezier((470, 480), (440, 400), (460, 350), (510, 340), 14)
    d2 = c.bezier((510, 340), (525, 410), (515, 470), (500, 520), 12)
    c.poly(d1 + d2[1:], (235, 145, 45), 0.95)
    # pectoral fin: curved leaf sweeping back-down from the belly
    p1 = c.bezier((530, 570), (470, 620), (430, 670), (415, 700), 12)
    p2 = c.bezier((415, 700), (470, 690), (520, 650), (545, 600), 12)
    c.poly(p1 + p2[1:], (250, 165, 70), 0.95)

    # -- koi head ---------------------------------------------------------
    c.ellipse(665, 245, 66, 58, (240, 138, 29), 1.0, feather=2)
    c.ellipse(700, 232, 34, 26, (255, 243, 214), 1.0)
    # eye
    c.circle(648, 222, 17, (255, 255, 255), 1.0)
    c.circle(650, 224, 8, (20, 12, 6), 1.0)
    c.circle(647, 220, 3, (255, 255, 255), 1.0)
    # mouth + barbels
    c.curve((700, 258), (712, 252), (720, 246), (726, 238), 5,
            (122, 45, 8), 1.0)
    c.curve((706, 254), (724, 268), (738, 286), (746, 306), 3,
            (232, 163, 76), 1.0)
    c.curve((700, 262), (712, 280), (720, 298), (724, 318), 3,
            (232, 163, 76), 1.0)

    # -- broth splash ------------------------------------------------------
    # foam crescents on the rim
    c.ellipse(268, 742, 60, 16, (255, 217, 160), 0.95)
    c.ellipse(756, 742, 60, 16, (255, 217, 160), 0.95)
    c.ellipse(512, 726, 52, 15, (255, 217, 160), 0.9)
    # splash plumes arcing up from the rim beside the koi: curved
    # broth-orange crescents, cream tip droplets
    s1 = c.bezier((290, 745), (255, 690), (258, 640), (285, 615), 12)
    s2 = c.bezier((285, 615), (305, 650), (315, 700), (320, 745), 12)
    c.poly(s1 + s2[1:], (224, 106, 31), 0.95)
    s3 = c.bezier((734, 745), (769, 690), (766, 640), (739, 615), 12)
    s4 = c.bezier((739, 615), (719, 650), (709, 700), (704, 745), 12)
    c.poly(s3 + s4[1:], (224, 106, 31), 0.95)
    c.droplet(285, 610, 8, (255, 217, 160))
    c.droplet(739, 610, 8, (255, 217, 160))
    # droplet arcs flying off the rim
    for (x, y, r, col) in [
            (232, 700, 14, (224, 106, 31)), (206, 660, 10, (193, 68, 14)),
            (188, 614, 8, (224, 106, 31)), (792, 700, 14, (224, 106, 31)),
            (818, 656, 10, (193, 68, 14)), (838, 610, 8, (224, 106, 31)),
            (300, 668, 9, (255, 217, 160)), (724, 668, 9, (255, 217, 160)),
            (262, 640, 7, (255, 217, 160)), (762, 640, 7, (255, 217, 160)),
            (350, 700, 12, (224, 106, 31)), (674, 700, 12, (224, 106, 31))]:
        c.droplet(x, y, r, col)
    # droplets clinging to the koi
    for (x, y, r) in [(560, 470, 7), (600, 420, 6), (520, 540, 8),
                      (470, 620, 6), (640, 330, 7)]:
        c.droplet(x, y, r, (255, 217, 160))

    # -- flying chopsticks ---------------------------------------------------
    c.line(150, 120, 330, 300, 14, (58, 36, 16), 1.0)
    c.line(185, 95, 345, 275, 14, (58, 36, 16), 1.0)
    c.line(300, 268, 330, 300, 15, (178, 40, 24), 1.0)
    c.line(315, 243, 345, 275, 15, (178, 40, 24), 1.0)
    c.line(120, 150, 190, 205, 4, (255, 255, 255), 0.45)
    c.line(140, 110, 205, 165, 4, (255, 255, 255), 0.4)
    c.line(165, 70, 225, 125, 4, (255, 255, 255), 0.35)

    # -- steam ---------------------------------------------------------------
    # soft translucent curls: low alpha, discs compound so keep it faint
    c.curve((400, 690), (380, 580), (410, 500), (388, 420), 20,
            (255, 255, 255), 0.05)
    c.curve((520, 680), (545, 570), (515, 490), (540, 410), 20,
            (255, 255, 255), 0.05)
    c.curve((640, 690), (665, 590), (640, 520), (662, 450), 18,
            (255, 255, 255), 0.045)

    # -- sparkles ---------------------------------------------------------------
    c.sparkle(560, 380, 12)
    c.sparkle(300, 760, 9)
    c.sparkle(700, 180, 10)
    c.sparkle(180, 560, 8)
