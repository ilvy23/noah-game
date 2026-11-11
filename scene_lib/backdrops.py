"""scene_lib/backdrops.py - the pictures behind the figures of the story scenes, all alive: fog drifting, rain, lamp and candle flicker, particles.

make(kind, w, h, chapter, seed) -> Backdrop with draw(cv, t, dt), `ground` (pixel row of the floor), `marks` (x fractions where figures stand: left, mid, right),
`tint` (colour multiplier for the figures), `lights` (point lights for the figures) and `seat` (True when sitting figures need a stool).
PHOTO kinds (wald, schloss, see: the owner's own photos) use the baked cell pictures of art/*.json, panned slowly; every other kind is painted procedurally (silhouettes, moon,
windows, lamps) once into a cached base picture and animated on top. Chapter grading is the one of ascii_art.GRADE for both.
"""
import math
import random

import ascii_art
import noah_gore_fx as G
from noah_gore_fx import Particles, add, glow, mix, mul

PHOTO = ("wald", "schloss", "see")
KINDS = ("street", "haus", "nook", "keller", "schule", "wohnzimmer", "kirche", "dachboden", "ritual", "berg", "haus_aussen", "baeckerei", "see_bench", "black") + PHOTO
# place / scene hints -> kind (scene_play.pick_backdrop uses it)
PLACE_KIND = {"lunuen": "street", "nook": "nook", "haus": "haus", "gymnasium": "schule", "wald": "wald", "see": "see", "schloss": "schloss", "keller": "keller"}


class Pix:
    """Pixel rows (two per cell row), rgb tuples."""

    def __init__(self, w, hp, bg=(0, 0, 0)):
        self.w, self.hp = w, hp
        self.a = [[bg] * w for _ in range(hp)]

    def rect(self, x0, y0, x1, y1, col):
        for y in range(max(0, int(y0)), min(self.hp, int(y1))):
            row = self.a[y]
            for x in range(max(0, int(x0)), min(self.w, int(x1))):
                row[x] = col

    def vgrad(self, y0, y1, c0, c1, x0=0, x1=None):
        x1 = self.w if x1 is None else x1
        for y in range(max(0, int(y0)), min(self.hp, int(y1))):
            c = mix(c0, c1, (y - y0) / max(1.0, y1 - y0))
            self.rect(x0, y, x1, y + 1, c)

    def disc(self, cx, cy, r, col, a=1.0):
        for y in range(max(0, int(cy - r)), min(self.hp, int(cy + r) + 1)):
            for x in range(max(0, int(cx - r)), min(self.w, int(cx + r) + 1)):
                d = math.hypot(x - cx, y - cy)
                if d <= r:
                    self.a[y][x] = mix(self.a[y][x], col, a * (1.0 if d < r - 1 else 0.6))

    def poly(self, pts, col):
        ys = [p[1] for p in pts]
        for y in range(max(0, int(min(ys))), min(self.hp, int(max(ys)) + 1)):
            xs = []
            for i in range(len(pts)):
                (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % len(pts)]
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(xa + (y - ya) * (xb - xa) / float(yb - ya))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(xs[i], y, xs[i + 1] + 1, y + 1, col)

    def dot(self, x, y, col):
        if 0 <= int(y) < self.hp and 0 <= int(x) < self.w:
            self.a[int(y)][int(x)] = col

    def noise(self, y0, y1, amount, seed=1):
        for y in range(max(0, int(y0)), min(self.hp, int(y1))):
            for x in range(self.w):
                k = 1.0 + amount * (G._hash(x, y, seed) - 0.5) * 2
                c = self.a[y][x]
                self.a[y][x] = (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))

    def to_cells(self, chapter):
        ch, fg, bg = [], [], []
        for y in range(self.hp // 2):
            top, bot = self.a[2 * y], self.a[2 * y + 1]
            for x in range(self.w):
                ch.append("▀")
                fg.append(ascii_art.grade(top[x], chapter))
                bg.append(ascii_art.grade(bot[x], chapter))
        return ch, fg, bg


def fog(cv, t, y0, y1, dens, col, speed=1.0, seed=0.0):
    y0, y1 = max(0, int(y0)), min(cv.h, int(y1))
    for y in range(y0, y1):
        fade = math.sin(math.pi * (y - y0 + 0.5) / max(1, y1 - y0))
        for x in range(cv.w):
            n = 0.5 + 0.5 * math.sin(x * 0.085 + t * speed + y * 0.35 + seed) * math.sin(x * 0.031 - t * speed * 0.7 + seed * 2)
            cv.tint(x, y, col, dens * fade * (0.35 + 0.65 * n))


class Backdrop:
    ground_frac = 0.78

    def __init__(self, kind, w, h, chapter=1, seed=1):
        self.kind, self.w, self.h, self.chapter = kind, w, h, chapter
        self.rng = random.Random(seed)
        self.hp = 2 * h
        self.ground = int(self.hp * self.ground_frac)
        self.marks = {"left": 0.26, "mid": 0.5, "right": 0.72, "far": 0.86}
        self.tint = (0.85, 0.9, 1.1)
        self.lights = []                     # (x px, y px, radius px, rgb) for the figures
        self.seat = False
        self.glows = []                      # (cx, cy, rx, ry, rgb, k, flicker speed) in cells
        self.fogs = []                       # (y0 frac, y1 frac, density, rgb, speed)
        self.rain = 0
        self.part = None                     # (kind, rate per second, region y0 frac, y1 frac, vy, vx)
        self.parts = Particles(self.rng, 260)
        self.pan = 0.0
        self.flick = []                      # cells region (x0, y0, x1, y1, rgb, k, hz): window lights that flicker
        self.base = None
        self.drops = [[self.rng.uniform(0, w), self.rng.uniform(0, h), self.rng.uniform(0.7, 1.4)] for _ in range(0)]
        getattr(self, "paint_" + kind)()

    # ---------------------------------------------------------------- the cache
    def _bake(self, pix):
        self.base = pix.to_cells(self.chapter)

    # ---------------------------------------------------------------- drawing
    def draw(self, cv, t, dt):
        if self.kind in PHOTO:
            self._photo(cv, t)
        else:
            cv.ch[:], cv.fg[:], cv.bg[:] = self.base[0][:], self.base[1][:], self.base[2][:]
        for (cx, cy, rx, ry, rgb, k, hz) in self.glows:
            f = 0.82 + 0.18 * math.sin(t * hz + cx) * math.sin(t * hz * 0.61 + 1.3) if hz else 1.0
            glow(cv, cx, cy, rx, ry, rgb, k * f)
        for (x0, y0, x1, y1, rgb, k, hz) in self.flick:
            f = k * (0.55 + 0.45 * math.sin(t * hz) * math.sin(t * hz * 0.43 + x0))
            for y in range(y0, y1):
                for x in range(x0, x1):
                    cv.light(x, y, rgb, f, 0.4)
        for (y0, y1, dens, rgb, sp) in self.fogs:
            fog(cv, int(t * 3) / 3.0, y0 * cv.h, y1 * cv.h, dens, rgb, sp, y0 * 7)           # three steps a second: far fewer cells change, the drift is slow anyway
        if self.rain:
            self._rain(cv, t)
        if self.part:
            self._particles(cv, t, dt)

    def _rain(self, cv, t):
        n = self.rain
        for i in range(n):
            sp = 18 + (i * 7) % 11
            x = (G._hash(i, 3, 1) * (cv.w + cv.h)) - t * 6 % (cv.w + cv.h)
            y = (G._hash(i, 5, 2) * cv.h + t * sp) % cv.h
            cv.put(int(x - y * 0.25) % cv.w, int(y), "'" if i % 2 else "|", (110, 130, 170))

    def _particles(self, cv, t, dt):
        kind, rate, y0, y1, vy, vx = self.part
        if self.rng.random() < rate * dt:
            self.parts.add(self.rng.uniform(0, cv.w), cv.h * self.rng.uniform(y0, y1), vx + self.rng.uniform(-1, 1), vy, 4.0 + self.rng.random() * 4, kind, 0.0)
        self.parts.step(dt)
        self.parts.draw(cv, 0.0)

    # ---------------------------------------------------------------- photos
    def _photo(self, cv, t):
        if self.base is None:
            self.base = _photo_grid(self.kind, cv.w, cv.h, self.chapter)
        grid, gw, gh, extra = self.base
        off = int((0.5 + 0.5 * math.sin(t * 0.07)) * extra)
        for y in range(cv.h):
            row = grid[y]
            i = y * cv.w
            for x in range(cv.w):
                c, f, b = row[x + off]
                cv.ch[i + x], cv.fg[i + x], cv.bg[i + x] = c, f, b

    # ---------------------------------------------------------------- painters
    def sky(self, pix, y1, c0, c1, moon=None, stars=40):
        pix.vgrad(0, y1, c0, c1)
        for _ in range(stars):
            pix.a[self.rng.randrange(0, max(1, int(y1 * 0.6)))][self.rng.randrange(self.w)] = (200, 205, 230)
        if moon:
            mx, my, r = moon
            pix.disc(mx, my, r * 2.2, (60, 70, 100), 0.18)
            pix.disc(mx, my, r, (232, 232, 214))
            pix.disc(mx + r * 0.3, my - r * 0.2, r * 0.8, (240, 240, 226), 0.5)

    def houses(self, pix, base, hmin, hmax, col, lit=0.3, x0=0, x1=None, warm=(255, 190, 90)):
        x = x0
        x1 = pix.w if x1 is None else x1
        while x < x1:
            bw = self.rng.randint(14, 26)
            bh = self.rng.randint(hmin, hmax)
            pix.rect(x, base - bh, x + bw, base, col)
            pix.poly([(x - 2, base - bh), (x + bw // 2, base - bh - self.rng.randint(5, 9)), (x + bw + 2, base - bh)], mul(col, 0.9))
            for wy in range(int(base - bh + 4), int(base - 4), 8):
                for wx in range(x + 3, x + bw - 3, 7):
                    if self.rng.random() < lit:
                        pix.rect(wx, wy, wx + 3, wy + 4, warm)
                        self.glows.append((wx + 1, (wy + 2) // 2, 4, 2, warm, 0.12, 0))
            x += bw + self.rng.randint(1, 4)

    def lamp(self, pix, x, y_top, y_base, col=(255, 200, 110)):
        pix.rect(x, y_top, x + 1, y_base, (30, 30, 36))
        pix.rect(x - 1, y_top - 1, x + 2, y_top + 1, col)
        self.glows.append((x, y_top // 2, 14, 7, col, 0.35, 9.0))
        self.lights.append((x, y_top, 40, col))

    def floor(self, pix, y0, c0, c1, plank=0):
        pix.vgrad(y0, pix.hp, c0, c1)
        if plank:
            for x in range(0, pix.w, plank):
                pix.rect(x, y0, x + 1, pix.hp, mul(c0, 0.7))

    def paint_street(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        self.sky(pix, hp * 0.62, (6, 8, 20), (30, 36, 60), (int(w * 0.78), int(hp * 0.16), 6))
        self.houses(pix, int(hp * 0.62), 14, 30, (16, 18, 26), 0.25)
        cx = int(w * 0.9)                                                        # the little church at the end of the street
        pix.rect(cx - 10, hp * 0.62 - 34, cx + 10, hp * 0.62, (14, 14, 22))
        pix.poly([(cx - 12, hp * 0.62 - 34), (cx, hp * 0.62 - 58), (cx + 12, hp * 0.62 - 34)], (12, 12, 20))
        pix.rect(cx - 3, hp * 0.62 - 26, cx + 3, hp * 0.62 - 12, (250, 205, 90))
        self.glows.append((cx, int(hp * 0.62 / 2) - 10, 14, 8, (255, 200, 90), 0.3, 3.0))
        self.floor(pix, hp * 0.62, (34, 34, 42), (20, 20, 26))
        pix.rect(0, hp * 0.62, w, hp * 0.62 + 3, (52, 52, 60))
        for k in range(0, w, 11):
            pix.rect(k, hp * 0.82, k + 5, hp * 0.82 + 1, (60, 60, 66))
        for lx in (int(w * 0.08), int(w * 0.5), int(w * 0.93)):
            self.lamp(pix, lx, int(hp * 0.4), int(hp * 0.64))
        pix.noise(hp * 0.6, hp, 0.08)
        self.fogs = [(0.52, 0.86, 0.34, (150, 160, 180), 0.5), (0.7, 0.95, 0.22, (130, 140, 160), 0.8)]
        self.part = ("dust", 5.0, 0.3, 0.9, 1.0, -2.0)
        self.tint = (0.82, 0.88, 1.1)
        self._bake(pix)

    def paint_haus_aussen(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        self.sky(pix, hp * 0.6, (4, 6, 16), (24, 30, 52), (int(w * 0.2), int(hp * 0.14), 5), 60)
        for x0, hgt in ((0.05, 36), (0.33, 30), (0.7, 40)):                      # trees, autumn black
            tx = int(w * x0)
            pix.rect(tx, hp * 0.6 - hgt, tx + 3, hp * 0.62, (14, 12, 14))
            pix.disc(tx + 1, hp * 0.6 - hgt, 12, (36, 22, 16))
        hx = int(w * 0.55)
        pix.rect(hx - 22, hp * 0.6 - 34, hx + 22, hp * 0.62, (22, 20, 26))
        pix.poly([(hx - 26, hp * 0.6 - 34), (hx, hp * 0.6 - 56), (hx + 26, hp * 0.6 - 34)], (16, 14, 20))
        pix.rect(hx - 4, hp * 0.62 - 18, hx + 4, hp * 0.62, (60, 38, 24))                 # the door; the key in the lock
        pix.rect(hx + 2, hp * 0.62 - 9, hx + 3, hp * 0.62 - 8, (220, 190, 90))
        pix.rect(hx - 16, hp * 0.62 - 26, hx - 9, hp * 0.62 - 18, (255, 196, 96))
        self.glows.append((hx - 12, int(hp * 0.62 / 2) - 11, 12, 6, (255, 190, 90), 0.3, 4.0))
        self.floor(pix, hp * 0.62, (60, 38, 24), (30, 22, 18))                                  # leaves, red and yellow
        for _ in range(int(w * 1.6)):
            pix.a[self.rng.randrange(int(hp * 0.62), hp)][self.rng.randrange(w)] = self.rng.choice([(190, 60, 30), (210, 150, 40), (140, 50, 30)])
        self.fogs = [(0.55, 0.85, 0.25, (150, 160, 180), 0.4)]
        self.part = ("ember", 3.0, 0.1, 0.3, 4.0, 1.0)
        self._bake(pix)

    def paint_haus(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.7, (66, 52, 46), (54, 42, 38))
        for x in range(0, w, 6):
            pix.rect(x, 0, x + 1, hp * 0.7, (58, 46, 41))
        self.floor(pix, hp * 0.7, (46, 34, 28), (28, 20, 18), 9)
        pix.rect(w * 0.43, hp * 0.7, w * 0.57, hp, (58, 46, 40))                                  # the clean stripe down the middle
        dx = int(w * 0.84)
        pix.rect(dx - 9, hp * 0.7 - 38, dx + 9, hp * 0.7, (30, 22, 20))                         # the door, a finger-width open, warm light coming out
        pix.rect(dx - 1, hp * 0.7 - 38, dx + 1, hp * 0.7, (255, 190, 100))
        self.glows.append((dx, int(hp * 0.7 / 2) - 10, 20, 12, (255, 180, 90), 0.4, 6.0))
        self.lights.append((dx, int(hp * 0.55), 80, (255, 180, 90)))
        sx = int(w * 0.1)
        for i in range(9):                                                                          # stairs going up on the left
            pix.rect(sx + i * 3, hp * 0.7 - 4 * i - 4, sx + 40, hp * 0.7 - 4 * i, mul((74, 56, 46), 0.9 + 0.02 * i))
        for fx, fy in ((0.3, 0.3), (0.62, 0.34)):                                                 # frames with faces rubbed out
            pix.rect(w * fx, hp * fy, w * fx + 10, hp * fy + 14, (20, 16, 14))
            pix.rect(w * fx + 1, hp * fy + 1, w * fx + 9, hp * fy + 13, (96, 86, 70))
        self.lamp(pix, int(w * 0.5), int(hp * 0.2), int(hp * 0.22), (255, 214, 140))
        pix.noise(0, hp, 0.05)
        self.tint = (1.1, 0.95, 0.85)
        self.part = ("dust", 3.0, 0.1, 0.7, 0.6, 0.2)
        self._bake(pix)

    def paint_nook(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.7, (70, 48, 34), (58, 38, 28))
        for y in range(0, int(hp * 0.7), 7):
            pix.rect(0, y, w, y + 1, (44, 28, 20))
        self.floor(pix, hp * 0.7, (62, 42, 30), (34, 22, 16), 10)
        wx = int(w * 0.2)                                                                           # window with the night and the moon
        pix.rect(wx - 14, hp * 0.18, wx + 14, hp * 0.46, (50, 30, 20))
        pix.vgrad(hp * 0.2, hp * 0.44, (8, 12, 28), (24, 34, 58), wx - 12, wx + 12)
        pix.disc(wx + 5, hp * 0.27, 3, (230, 230, 214))
        pix.rect(wx - 1, hp * 0.2, wx + 1, hp * 0.44, (50, 30, 20))
        self.glows.append((wx, int(hp * 0.16), 22, 10, (130, 150, 220), 0.12, 0))
        sx = int(w * 0.8)                                                                           # the stove, glowing
        pix.rect(sx - 8, hp * 0.7 - 22, sx + 8, hp * 0.7, (30, 28, 30))
        pix.rect(sx - 4, hp * 0.7 - 12, sx + 4, hp * 0.7 - 5, (255, 140, 40))
        self.glows.append((sx, int(hp * 0.7 / 2) - 4, 26, 12, (255, 140, 50), 0.45, 11.0))
        self.lights.append((sx, int(hp * 0.62), 90, (255, 150, 60)))
        pix.rect(w * 0.45, hp * 0.18, w * 0.45 + 22, hp * 0.2, (50, 30, 20))                  # a shelf with mugs
        for k in range(4):
            pix.rect(w * 0.45 + 2 + k * 5, hp * 0.2 - 4, w * 0.45 + 5 + k * 5, hp * 0.2, (200 - k * 20, 190, 170))
        pix.rect(w * 0.44, hp * 0.7 - 4, w * 0.66, hp * 0.7, (80, 54, 36))                      # a small table
        pix.rect(w * 0.45, hp * 0.7 - 10, w * 0.65, hp * 0.7 - 7, (96, 66, 44))
        self.lamp(pix, int(w * 0.5), int(hp * 0.1), int(hp * 0.12), (255, 200, 120))
        pix.noise(0, hp, 0.05)
        self.tint = (1.18, 0.95, 0.78)
        self.seat = True
        self.part = ("ember", 2.0, 0.55, 0.7, -2.0, 0.0)
        self.marks.update(left=0.3, mid=0.5, right=0.66)
        self._bake(pix)

    def paint_keller(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        for y in range(0, int(hp * 0.72)):
            for x in range(w):
                brick = ((x // 9) + (y // 4) * 4 + (4 if (y // 4) % 2 else 0)) % 9
                c = mix((22, 18, 20), (46, 38, 36), G._hash(x // 9, y // 4, brick))
                if x % 9 == 0 or y % 4 == 0:
                    c = mul(c, 0.6)
                pix.a[y][x] = c
        self.floor(pix, hp * 0.72, (24, 24, 30), (12, 12, 18))
        for lx in (0.2, 0.5, 0.8):
            x = int(w * lx)
            pix.rect(x, hp * 0.72 - 7, x + 2, hp * 0.72, (230, 220, 195))
            self.glows.append((x, int(hp * 0.72 / 2) - 4, 22, 10, (255, 150, 60), 0.3, 12.0 + lx * 5))
            self.lights.append((x, int(hp * 0.72) - 8, 70, (255, 150, 60)))
        self.tint = (0.8, 0.82, 1.0)
        self.fogs = [(0.6, 0.9, 0.18, (110, 130, 170), 0.3)]
        self.part = ("dust", 3.0, 0.1, 0.9, 0.5, 0.2)
        self._bake(pix)

    def paint_schule(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.7, (88, 94, 92), (70, 76, 76))
        for lx in range(0, w, 14):                                                                   # lockers
            pix.rect(lx, hp * 0.3, lx + 12, hp * 0.7, (60, 78, 86))
            pix.rect(lx + 11, hp * 0.3, lx + 12, hp * 0.7, (40, 54, 60))
            pix.rect(lx + 8, hp * 0.5, lx + 10, hp * 0.5 + 3, (170, 170, 176))
        pix.rect(0, 0, w, hp * 0.3, (96, 100, 98))
        self.floor(pix, hp * 0.7, (112, 106, 92), (70, 66, 58))
        for lx in (0.2, 0.55, 0.9):
            pix.rect(w * lx - 9, hp * 0.18, w * lx + 9, hp * 0.2, (236, 240, 232))
            self.flick.append((int(w * lx) - 9, int(hp * 0.1) - 1, int(w * lx) + 9, int(hp * 0.1) + 5, (200, 220, 210), 0.12, 29.0 + lx * 10))
        self.tint = (0.9, 1.0, 1.0)
        self.part = ("dust", 2.0, 0.2, 0.7, 0.5, 0.2)
        self._bake(pix)

    def paint_wohnzimmer(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.72, (58, 50, 56), (46, 38, 44))
        self.floor(pix, hp * 0.72, (40, 28, 30), (24, 18, 20), 14)
        wx = int(w * 0.78)
        pix.rect(wx - 12, hp * 0.18, wx + 12, hp * 0.5, (30, 24, 28))
        pix.vgrad(hp * 0.2, hp * 0.48, (8, 12, 28), (30, 38, 64), wx - 10, wx + 10)
        pix.disc(wx + 4, hp * 0.3, 3, (232, 232, 214))
        pix.rect(w * 0.12, hp * 0.52, w * 0.4, hp * 0.72, (92, 56, 56))                              # sofa
        pix.rect(w * 0.12, hp * 0.44, w * 0.4, hp * 0.52, (110, 66, 64))
        tvx = int(w * 0.5)
        pix.rect(tvx - 10, hp * 0.4, tvx + 10, hp * 0.58, (14, 14, 18))                               # a TV that glows blue
        pix.rect(tvx - 8, hp * 0.42, tvx + 8, hp * 0.56, (60, 90, 130))
        self.glows.append((tvx, int(hp * 0.25), 30, 14, (110, 150, 230), 0.35, 17.0))
        self.lights.append((tvx, int(hp * 0.5), 90, (110, 150, 230)))
        self.lamp(pix, int(w * 0.62), int(hp * 0.36), int(hp * 0.72), (255, 200, 130))
        self.tint = (1.0, 0.95, 1.05)
        self.seat = True
        self.part = ("dust", 3.0, 0.1, 0.7, 0.5, 0.2)
        self._bake(pix)

    def paint_kirche(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.7, (30, 26, 34), (40, 34, 36))
        cx = w // 2
        pix.poly([(cx - 14, hp * 0.6), (cx - 14, hp * 0.22), (cx, hp * 0.08), (cx + 14, hp * 0.22), (cx + 14, hp * 0.6)], (250, 204, 96))     # the tall yellow glass window
        for k in (-9, 0, 9):
            pix.rect(cx + k - 1, hp * 0.12, cx + k, hp * 0.6, (150, 110, 40))
        self.glows.append((cx, int(hp * 0.2), 36, 16, (255, 200, 90), 0.5, 2.5))
        self.lights.append((cx, int(hp * 0.3), 140, (255, 200, 90)))
        self.floor(pix, hp * 0.7, (46, 38, 36), (22, 18, 18), 12)
        for row, y in enumerate((0.74, 0.84, 0.94)):                                                  # pews, rows of dark benches
            for px in (0.06, 0.26, 0.64, 0.84):
                pix.rect(w * px, hp * y - 6, w * px + w * 0.14, hp * y, mul((50, 36, 28), 0.9 - 0.1 * row))
        self.tint = (1.1, 1.0, 0.85)
        self.seat = True
        self.part = ("gold", 3.0, 0.1, 0.6, 0.5, 0.0)
        self._bake(pix)

    def paint_dachboden(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.75, (30, 24, 22), (44, 34, 30))
        pix.poly([(0, hp * 0.75), (w // 2, 0), (w, hp * 0.75)], (36, 28, 24))
        for k in range(1, 6):
            pix.rect(w * k / 6 - 1, hp * 0.05 * k * 0.5, w * k / 6 + 1, hp * 0.75, (24, 16, 14))
        self.floor(pix, hp * 0.75, (50, 38, 30), (26, 20, 16), 8)
        for bx in (0.12, 0.7, 0.8):
            pix.rect(w * bx, hp * 0.75 - 14, w * bx + 14, hp * 0.75, (80, 62, 44))
        wx = int(w * 0.35)
        pix.rect(wx - 6, hp * 0.2, wx + 6, hp * 0.4, (200, 210, 240))
        pix.poly([(wx - 6, hp * 0.4), (wx + 6, hp * 0.4), (wx + 30, hp * 0.75), (wx - 14, hp * 0.75)], (70, 76, 92))      # light shaft
        self.glows.append((wx, int(hp * 0.15), 26, 12, (160, 180, 255), 0.25, 0))
        self.lights.append((wx, int(hp * 0.4), 110, (150, 170, 240)))
        self.tint = (0.95, 0.98, 1.1)
        self.part = ("dust", 8.0, 0.2, 0.75, 0.4, 0.1)
        self._bake(pix)

    def paint_ritual(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.65, (20, 10, 12), (34, 16, 18))
        self.floor(pix, hp * 0.65, (36, 22, 20), (16, 10, 10), 10)
        cx, cy = w // 2, int(hp * 0.82)
        rr = min(34, w * 0.3)
        for ang in range(0, 360, 3):                                                                 # a circle burnt into the boards
            a = math.radians(ang)
            pix.dot(cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.27, (150, 30, 24))
        for k in range(5):
            a = math.radians(72 * k - 90)
            x, y = int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr * 0.27)
            pix.rect(x - 1, y - 5, x + 1, y, (230, 210, 190))
            self.glows.append((x, (y - 6) // 2, 14, 7, (255, 70, 50), 0.35, 13.0 + k))
        self.lights.append((cx, int(hp * 0.7), 100, (255, 80, 60)))
        self.tint = (1.2, 0.8, 0.8)
        self.part = ("ember", 4.0, 0.7, 0.9, -3.0, 0.0)
        self.fogs = [(0.7, 0.95, 0.15, (160, 40, 40), 0.3)]
        self._bake(pix)

    def paint_berg(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        self.sky(pix, hp * 0.6, (14, 8, 12), (96, 40, 30), None, 20)
        pts = [(0, hp * 0.62)] + [(x, hp * 0.62 - 28 * max(0.0, math.sin(x / w * math.pi)) ** 1.6 - 4 * math.sin(x * 0.2)) for x in range(0, w + 6, 6)] + [(w, hp * 0.62), (w, hp), (0, hp)]
        pix.poly(pts, (18, 14, 14))
        self.floor(pix, hp * 0.72, (28, 22, 20), (14, 12, 12))
        for k in range(7):                                                                           # burnt stakes
            x = int(w * (0.12 + 0.13 * k)) + self.rng.randint(-3, 3)
            pix.rect(x, hp * 0.72 - self.rng.randint(8, 16), x + 2, hp * 0.74, (10, 8, 8))
        self.glows.append((w // 2, int(hp * 0.3), 80, 12, (255, 90, 40), 0.18, 2.0))
        self.fogs = [(0.45, 0.8, 0.2, (110, 70, 60), 0.4)]
        self.part = ("ash", 12.0, 0.0, 0.3, 3.0, 1.5)
        self.tint = (1.1, 0.85, 0.8)
        self._bake(pix)

    def paint_baeckerei(self):
        w, hp = self.w, self.hp
        pix = Pix(w, hp)
        pix.vgrad(0, hp * 0.7, (20, 22, 34), (34, 30, 38))
        self.houses(pix, int(hp * 0.7), 20, 36, (22, 20, 28), 0.15)
        bx = int(w * 0.5)
        pix.rect(bx - 28, hp * 0.3, bx + 28, hp * 0.7, (76, 52, 36))
        pix.rect(bx - 22, hp * 0.4, bx + 22, hp * 0.66, (255, 206, 130))                           # the shop window, warm, bread on the shelves
        for k in range(5):
            pix.disc(bx - 16 + k * 8, hp * 0.6, 3, (190, 130, 70))
        self.glows.append((bx, int(hp * 0.27), 34, 12, (255, 190, 100), 0.4, 5.0))
        self.lights.append((bx, int(hp * 0.5), 100, (255, 190, 100)))
        self.floor(pix, hp * 0.7, (36, 34, 40), (20, 20, 24))
        self.fogs = [(0.6, 0.9, 0.2, (150, 160, 180), 0.5)]
        self.tint = (1.05, 0.95, 0.9)
        self._bake(pix)

    def paint_see_bench(self):
        self.paint_street()

    def paint_black(self):
        pix = Pix(self.w, self.hp, (4, 4, 8))
        self.part = ("dust", 3.0, 0.0, 1.0, 0.3, 0.1)
        self._bake(pix)

    def _photo_painter(self):
        self.seat = self.kind in ("see", "wald")
        self.marks.update(left=0.24, mid=0.5, right=0.74)
        self.ground = int(self.hp * 0.8)
        self.tint = (0.85, 0.9, 1.05)

    def paint_wald(self):
        self._photo_painter()
        self.fogs = [(0.55, 0.95, 0.3, (150, 165, 175), 0.5)]
        self.part = ("dust", 5.0, 0.2, 0.9, 1.0, 0.5)

    def paint_schloss(self):
        self._photo_painter()
        self.fogs = [(0.6, 0.98, 0.3, (160, 150, 150), 0.4)]
        self.part = ("ash", 4.0, 0.0, 0.4, 2.0, 0.5)

    def paint_see(self):
        self._photo_painter()
        self.fogs = [(0.5, 0.95, 0.4, (160, 170, 185), 0.35), (0.7, 1.0, 0.2, (140, 150, 170), 0.6)]
        self.glows = [(int(self.w * 0.74), int(self.h * 0.56), 12, 4, (230, 120, 70), 0.0, 4.0)]
        self.part = ("dust", 3.0, 0.3, 0.9, 0.5, 0.3)


def _photo_grid(name, w, h, chapter):
    """(rows of (glyph, fg, bg) cells, width, height, spare columns): the baked picture cover-fitted to w x h with room to pan."""
    data = ascii_art.load(name) or {}
    best = None
    for key in ("ultra", "wide", "small", "cred", "tiny", "mini"):
        if key in data:
            g = data[key]
            ratio = (g["w"] / 2.0) / g["h"]                       # visual aspect (cells are twice as high as wide)
            score = abs(math.log(ratio / (w / 2.0 / h)))
            if best is None or score < best[0]:
                best = (score, g)
    if best is None:
        return [[(" ", (0, 0, 0), (0, 0, 0))] * (w + 1) for _ in range(h)], w, h, 0
    g = best[1]
    sw, sh = g["w"], g["h"]
    scale = max(h / float(sh), (w * 1.1) / float(sw))
    ow = int(sw * scale)
    grid = []
    for y in range(h):
        sy = min(sh - 1, int(y / scale))
        row = g["rows"][sy]
        px = g["rgb"][sy]
        out = []
        for x in range(ow):
            sx = min(sw - 1, int(x / scale))
            c = ascii_art.grade((px[3 * sx], px[3 * sx + 1], px[3 * sx + 2]), chapter)
            fall = 0.55 + 0.45 * (1.0 - max(0.0, (y / float(h) - 0.7)) / 0.3 * 0.5)            # darker at the bottom, where the figures stand
            out.append((row[sx], mul(c, fall), mul(c, 0.4 * fall)))
        grid.append(out)
    return grid, w, h, max(0, ow - w)


def make(kind, w, h, chapter=1, seed=1):
    if kind not in KINDS:
        kind = "street"
    return Backdrop(kind, w, h, chapter, seed)
