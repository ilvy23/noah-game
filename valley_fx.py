"""valley_fx.py - valley_burns(): the town of Luenen at night from above, the cult in procession, and everything burns (about 40 s).

Shots: WIDE (the valley: houses, church tower, forest edge, the lake, a procession of tiny robed figures with torches, Mika at the shore),
FACES (four hooded faces chant in the torchlight, then catch fire), WIDE again (the whole valley ignites in a wave from the shore, the figures burn
and run, then an invisible pull drags them over the ground into the lake), WATER (a height-field water simulation: splashes, ripples, a whirlpool, bodies
orbiting down into it, bubbles, last hands), the AFTERMATH (steam over the lake, the town burns down) and the SETTLED lake with Mika standing at the shore.
Pure function of t and the seed; no input; nothing outside the screen.   python3 play.py --mika-ending --only valley
"""
import math

import photo_fx
import noah_gore_fx as G
from noah_gore_fx import Canvas, Fire, draw_cube, Particles, add, blit_grid, darken, fire_rgb, flash, glow, jolt, mix, mul, ramp, shake_at, smooth, _hash
from mika_fx import MikaFigure

T_FACES, T_IGN, T_WIDE2, T_PULL, T_WATER, T_AFTER, T_CALM, END = 6.5, 10.2, 12.0, 16.5, 20.0, 27.0, 33.0, 40.5
LAKE_MAX = 0.55                                                    # the water simulation is as wide as the screen and this high (fraction of h)


SRC_W, SRC_H = 1024.0, 683.0                                        # the aerial picture (proc_art.aerial(), half this size); positions below are pixels of that plan
SRC_HOUSES = [(68, 100), (40, 165), (52, 188), (125, 160), (78, 140), (60, 125), (150, 72), (232, 35), (282, 38), (345, 33), (615, 82), (128, 25), (30, 215), (160, 215), (100, 195)]
SRC_PATH = [(70, 232), (82, 300), (118, 352), (170, 405), (222, 448), (275, 470)]       # the procession: from the houses down the west shore to the bench corner
SRC_WHIRL, SRC_MIKA = (330, 300), (338, 505)
ZOOM = 0.70                                                          # < 1: zoomed out, a wider surrounding
SOUTH_SHORE = (292, 462)                                                 # where Connor wades in


def night(r, g, b, x=0, y=0):
    """Moonlit night grade: dark blue-black, a little green kept in the trees, the lake a dark mirror."""
    L = (r * 0.3 + g * 0.59 + b * 0.11) / 255.0
    k = min(1.0, L ** 1.55 * 1.5)
    gr = max(0.0, (g - r) / 255.0)
    return (int(6 + 44 * k + 4 * gr * 60 * 0.2), int(10 + 62 * k + gr * 40), int(22 + 96 * k))


class Water:
    """A 2D wave equation on a grid (gw x gh): impulses make rings, damping settles it, the whirlpool is an extra spin and a dent."""

    def __init__(self, gw, gh):
        self.gw, self.gh = gw, gh
        self.a = [[0.0] * gw for _ in range(gh)]
        self.b = [[0.0] * gw for _ in range(gh)]
        self.vx, self.vy, self.vort = gw * 0.5, gh * 0.5, 0.0

    def poke(self, x, y, amp, r=2):
        for dy in range(-r, r + 1):
            for dx in range(-2 * r, 2 * r + 1):
                xi, yi = int(x) + dx, int(y) + dy
                if 0 < xi < self.gw - 1 and 0 < yi < self.gh - 1:
                    self.a[yi][xi] += amp * max(0.0, 1.0 - math.hypot(dx / 2.0, dy) / (r + 0.5))

    def step(self, damp=0.994, c=0.24):
        a, b, gw, gh = self.a, self.b, self.gw, self.gh
        if self.vort > 0.01:                                                   # the whirlpool digs a hole in the middle
            for dy in range(-6, 7):
                for dx in range(-14, 15):
                    xi, yi = int(self.vx) + dx, int(self.vy) + dy
                    if 0 < xi < gw - 1 and 0 < yi < gh - 1:
                        a[yi][xi] -= 0.012 * self.vort * max(0.0, 1 - (dx / 14.0) ** 2 - (dy / 6.0) ** 2)
        for y in range(1, gh - 1):
            ra, rb, up, dn = a[y], b[y], a[y - 1], a[y + 1]
            for x in range(1, gw - 1):
                v = (2 * ra[x] - rb[x] + c * (ra[x - 1] + ra[x + 1] + up[x] + dn[x] - 4 * ra[x])) * damp
                rb[x] = 2.0 if v > 2.0 else -2.0 if v < -2.0 else v
        self.a, self.b = b, a


def cult_region(tx, ty):
    """A hooded face for the close-up (14 units tall): 'H' hood, 'f' face, 'e' eye, 'm' mouth."""
    ax = abs(tx)
    if (tx / 5.4) ** 2 + ((ty - 6.4) / 6.8) ** 2 < 1:
        if (tx / 3.0) ** 2 + ((ty - 7.1) / 4.3) ** 2 < 1:
            if 0.9 < ax < 1.9 and 5.7 < ty < 6.7:
                return "e"
            if ax < 1.5 and 9.2 < ty < 10.6:
                return "m"
            return "f"
        return "H"
    if 12.2 < ty < 14 and ax < 6.2:
        return "H"
    return None


def water_px(h0, slope, fire_k, x, y, w, photo):
    """One pixel of lake: dark mirror with the shore reflections of the photo, the moon glitter on the ripples, foam on the steep ones, the fire's red on top."""
    base = mix((5, 10, 22), (14, 30, 56), max(0.0, min(1.0, 0.4 + h0 * 0.25)))
    base = mix(base, photo, 0.22)
    sh = max(0.0, min(1.0, slope * 0.55))
    c = add(base, (120, 150, 205), sh * 0.45 * (0.5 + 0.5 * math.exp(-((x - w * 0.55) / (w * 0.22)) ** 2)))
    c = add(c, (255, 80, 14), fire_k * (0.10 + 0.45 * sh) * (1.0 - 0.6 * x / float(w)))
    if slope > 1.1:
        c = mix(c, (225, 235, 245), min(0.7, (slope - 1.1) * 0.5))                # foam
    return c


class ValleyScene:
    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.parts = Particles(rng, 1400)
        self.fire = Fire(0, w, h, rng, decay=0.09)
        self.wsrc = SRC_W / ZOOM                                            # the camera sees more than the photo: the picture is zoomed out, the rim is the photo mirrored
        self.hsrc = self.wsrc * 2.0 * h / w
        self.x0src = (SRC_W - self.wsrc) / 2.0
        self.y0src = 305 - self.hsrc / 2.0
        self.build_base()
        self.gt = 0
        self.water = Water(w, 2 * h)
        self.close = Water(w, 2 * h)
        lx, ly = self.P(*SRC_WHIRL)
        self.lake = (int(lx), int(ly), int(w * 0.14), int(h * 0.3))
        self.water.vx, self.water.vy = lx, ly * 2
        self.path = [self.P(*p) for p in SRC_PATH]
        self.houses = []
        for (sx, sy) in SRC_HOUSES:
            x, y = self.P(sx, sy)
            if 2 <= x < w - 8 and 1 <= y < h - 3:
                self.houses.append(dict(x=int(x), y=int(y), ww=max(3, int(w * 0.014)), win=_hash(int(x), int(y), 3) < 0.8, ign=0.0))
        self.first = min(self.houses, key=lambda hs: hs["x"] + 3 * hs["y"]) if self.houses else None
        self.churches = []
        self.add_town()
        n = max(20, min(56, w // 4))
        self.cult = []
        for i in range(n):
            u = 0.02 + 0.93 * i / float(n) + rng.uniform(-0.008, 0.008)
            self.cult.append(dict(u=u, off=rng.uniform(-4.0, 4.0), sp=rng.uniform(0.006, 0.010), torch=rng.random() < 0.45, st="walk", x=0.0, y=0.0,
                                  pull=T_PULL + rng.random() * 1.8, ign=T_IGN + 2.0 + rng.random() * 1.2, vx=0.0, vy=0.0, tin=0.0, ang=rng.uniform(0, 6.28), ph=rng.random() * 6.28))
        self.cult[0].update(connor=True, u=0.55, off=0.0, torch=False, ign=T_IGN + 6.0, pull=T_PULL + 1.0)         # Connor leads the procession, calm
        for c in self.cult:
            c["x"], c["y"] = self.at(c["u"], c["off"])
        self.mika_sit, self.mika_st = MikaFigure(max(8, int(h * 0.20)), True), MikaFigure(max(8, int(h * 0.20)), False)
        self.mika_big = MikaFigure(int(h * 0.74), False)
        self.cnt_in, self.flash_t = 0, []
        self.faces_n = max(2, min(4, w // 40))
        self.hands = [(rng.uniform(0.15, 0.85), rng.uniform(0.2, 0.8), 24.8 + rng.random() * 1.6) for _ in range(9)]
        self.hits = [(T_WIDE2, 1.6), (T_IGN + 0.2, 1.0), (T_PULL, 1.4), (T_WATER, 1.0), (T_AFTER, 0.8)]
        self.last_t = 0.0
        self.burnt = set()
        sx0 = self.P(*SRC_PATH[-1])
        self.trees = []                                                          # forest cells that can burn, each with the time it catches (a wave from the houses)
        src = [(hs["x"], hs["y"]) for hs in self.houses] or [(0, 0)]
        for y in range(0, h, 1):
            for x in range(0, w, 1):
                if self.tree[y * w + x] and _hash(x, y, 31) < 0.45:
                    d = min(math.hypot((x - hx) / 2.0, y - hy) for hx, hy in src)
                    self.trees.append((x, y, T_WIDE2 + 1.0 + d / 5.5 + 1.5 * _hash(x, y, 32)))
        self.trees.sort(key=lambda c: c[2])

    def add_town(self):
        """The world beyond the photo: villages of procedural houses (night roofs, lit windows) and church towers in the rim of the zoomed-out picture and in the woods, so
        the town sprawls around the lake. They are part of the static backdrop; they ignite like the real houses."""
        w, h, rng = self.w, self.h, self.rng
        bx0, bx1 = self.P(0, 0)[0], self.P(SRC_W, 0)[0]
        by0, by1 = self.P(0, 0)[1], self.P(0, SRC_H)[1]
        cv = self.cvbase
        for i in range(w * h):                                                         # the rim is the photo mirrored: dim it towards the edges
            x, y = i % w, i // w
            d = max(0.0, bx0 - x, x - bx1, by0 - y, y - by1) / (0.12 * w)
            if d > 0:
                k = max(0.55, 1.0 - 0.45 * min(1.0, d))
                cv.fg[i], cv.bg[i] = mul(cv.fg[i], k), mul(cv.bg[i], k)
        centres = [(0.07, 0.30), (0.05, 0.75), (0.93, 0.25), (0.95, 0.72), (0.5, 0.04), (0.45, 0.96), (0.2, 0.92), (0.78, 0.9), (0.28, 0.06)]
        for ci, (fx, fy) in enumerate(centres):
            cx, cy = fx * w, fy * h
            if self.in_lake(cx, cy):
                continue
            n = 4 + int(rng.random() * 5)
            for k in range(n):
                x = int(cx + rng.gauss(0, w * 0.045))
                y = int(cy + rng.gauss(0, h * 0.14))
                ww = 4 + int(rng.random() * 3)
                if not (1 <= x < w - ww - 1 and 3 <= y < h - 3) or any(self.in_lake(x + q, y) for q in (0, ww)):
                    continue
                if any(abs(x - o["x"]) < ww + 2 and abs(y - o["y"]) < 3 for o in self.houses):
                    continue
                self.houses.append(dict(x=x, y=y, ww=ww, win=_hash(x, y, 3) < 0.85, ign=0.0))
                tone = 0.8 + 0.4 * _hash(x, y, 5)
                for q in range(ww):                                                    # roof: two pixel rows with a lit ridge, wall below
                    photo_fx.put_pixel(cv, x + q, 2 * y, mul((96, 52, 52), tone))
                    photo_fx.put_pixel(cv, x + q, 2 * y + 1, mul((66, 36, 40), tone))
                    photo_fx.put_pixel(cv, x + q, 2 * y + 2, mul((44, 38, 48), tone))
                photo_fx.put_pixel(cv, x + ww // 2, 2 * y - 1, mul((120, 70, 64), tone))
            if ci % 3 == 0 and ci < 7:                                                 # a church: nave, tower with a spire and a lit belfry
                x, y = int(cx), int(cy)
                if 6 <= x < w - 12 and 8 <= y < h - 3 and not self.in_lake(x, y):
                    for q in range(8):
                        for r in range(3):
                            photo_fx.put_pixel(cv, x + 3 + q, 2 * y + r, (84, 78, 92) if r else (110, 66, 62))
                    for r in range(14):
                        for q in range(3 if r > 5 else max(1, (r + 1) // 2)):
                            photo_fx.put_pixel(cv, x + 1 - (q - 1) + (0 if r > 5 else 0), 2 * y - 12 + r, (96, 90, 106) if r > 5 else (120, 70, 66))
                    photo_fx.put_pixel(cv, x + 1, 2 * y - 5, (255, 200, 100))
                    photo_fx.put_pixel(cv, x + 1, 2 * y - 14, (230, 220, 160))
                    self.churches.append((x + 1, y))
                    self.houses.append(dict(x=x + 3, y=y, ww=8, win=True, ign=0.0))

    # -- the real geography
    def P(self, sx, sy):
        """Photo pixel -> screen cell (float)."""
        return (sx - self.x0src) / self.wsrc * self.w, (sy - self.y0src) / self.hsrc * self.h

    def build_base(self):
        """The aerial picture as half-block pixels, night-graded; the lake mask (the dark blue region connected to the lake's middle) and the tree mask."""
        w, h = self.w, self.h
        crop = (self.x0src / 2.0, self.y0src / 2.0, (self.x0src + self.wsrc) / 2.0, (self.y0src + self.hsrc) / 2.0)
        raw = photo_fx.fit("aerial", w, 2 * h, crop, reflect=True)
        wet = [[(r_ - 0 < b_ - 8 and g_ < b_ + 22 and (r_ * 0.3 + g_ * 0.59 + b_ * 0.11) < 92 and r_ < 70) for (r_, g_, b_) in row] for row in raw]
        lx, ly = self.P(*SRC_WHIRL)
        seed = (int(lx), int(ly * 2))
        mask, todo = {seed}, [seed]
        while todo:
            x, y = todo.pop()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < 2 * h and (nx, ny) not in mask and wet[ny][nx]:
                    mask.add((nx, ny))
                    todo.append((nx, ny))
        self.mask = mask
        self.raw = raw
        self.px = [[night(*c) for c in row] for row in raw]
        self.cvbase = Canvas(w, h)
        photo_fx.paint(self.cvbase, self.px, 0, 0)
        self.wcells = sorted({(x, y // 2) for x, y in mask})
        self.tree = [False] * (w * h)
        for y in range(h):
            for x in range(w):
                r_, g_, b_ = raw[2 * y][x]
                if (x, 2 * y) not in mask and g_ > r_ + 3 and g_ > b_ and (r_ + g_ + b_) < 420:
                    self.tree[y * w + x] = True

    def in_lake(self, x, y):
        return (int(x), int(y * 2)) in self.mask

    def draw_house(self, cv, hs, t):
        a = t - hs["ign"]
        x, y, ww = hs["x"], hs["y"], hs["ww"]
        if a < 0:                                                                    # the lit windows, small and warm
            if hs["win"]:
                for k in range(1, ww - 1, 2):
                    photo_fx.put_pixel(cv, x + k, 2 * y + 1, (255, 196, 96))
                    photo_fx.put_pixel(cv, x + k, 2 * y + 2, (255, 170, 70))
                for k in range(ww):
                    cv.light(x + k, y, (255, 150, 50), 0.10, 0.0)
                    cv.light(x + k, y + 1, (255, 150, 50), 0.16, 0.0)
        else:                                                                        # charred: the roof goes black from the middle out
            f = smooth(a / 4.0)
            for k in range(ww):
                for dy in (0, 1):
                    i = (y + dy) * cv.w + x + k
                    if 0 <= x + k < cv.w and 0 <= y + dy < cv.h:
                        cv.bg[i] = mix(cv.bg[i], (22, 12, 10), f * 0.9)
                        cv.fg[i] = mix(cv.fg[i], (30, 14, 10), f * 0.9)

    def at(self, u, off):
        pts, n = self.path, len(self.path) - 1
        u = min(0.999, max(0.0, u))
        i = int(u * n)
        f = u * n - i
        x = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f
        y = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f
        return x + off * 2.0, y + off * 0.6

    # -- figures
    def step_cult(self, t, dt):
        rng = self.rng
        lx, ly = self.lake[0], self.lake[1]
        for c in self.cult:
            st = c["st"]
            if st == "walk":
                c["u"] = min(0.96, c["u"] + c["sp"] * dt)
                c["x"], c["y"] = self.at(c["u"], c["off"] + math.sin(t * 1.7 + c["ph"]) * 0.4)
                if t >= c["ign"] or (not c.get("connor") and t >= T_IGN + 0.0 and c["u"] > 0.5 and t > T_IGN + 1.5):
                    c["st"] = "burn"
                    c["vx"], c["vy"] = rng.uniform(-8, 8), rng.uniform(-3, 3)
            elif st == "burn" and c.get("connor"):                                          # Connor: no panic; he walks into the lake of his own will
                tx, ty = self.P(*SOUTH_SHORE)
                if math.hypot((tx - c["x"]) / 2.0, ty - c["y"]) < 2.5:
                    c["wade"] = True
                if c.get("wade"):
                    tx, ty = lx, ly
                dx, dy = tx - c["x"], ty - c["y"]
                d = math.hypot(dx / 2.0, dy) or 1.0
                c["x"], c["y"] = c["x"] + dx / 2.0 / d * 5.0 * 2.0 * dt, c["y"] + dy / d * 5.0 * dt
                if self.in_lake(c["x"], c["y"]):
                    c["st"], c["tin"] = "in", t
                    self.cnt_in += 1
                    self.water.poke(c["x"], c["y"] * 2, 0.5, 3)
            elif st == "burn":
                if t < c["pull"]:                                                   # panic: running every which way
                    c["vx"] += rng.uniform(-30, 30) * dt
                    c["vy"] += rng.uniform(-12, 12) * dt
                    c["vx"], c["vy"] = max(-14, min(14, c["vx"])), max(-6, min(6, c["vy"]))
                else:                                                               # the pull: straight at the lake, harder and harder
                    k = 8 + 40 * (t - c["pull"]) ** 1.2
                    dx, dy = lx - c["x"], ly - c["y"]
                    d = math.hypot(dx / 2.0, dy) or 1.0
                    c["vx"], c["vy"] = dx / 2.0 / d * k * 2.0, dy / d * k
                c["x"] = max(1, min(self.w - 2, c["x"] + c["vx"] * dt))
                c["y"] = max(1, min(self.h - 2, c["y"] + c["vy"] * dt))
                if self.in_lake(c["x"], c["y"]) and t > c["pull"]:
                    c["st"], c["tin"] = "in", t
                    self.cnt_in += 1
                    self.parts.burst(c["x"], c["y"], 8, "spray", 8, 0.8, 22.0, up=6)
                    self.water.poke(c["x"], c["y"] * 2, 1.0, 3)

    def figure(self, cv, x, y, t, mode, ph, torch, connor=False):
        """A cult figure in half-block pixels (3 px wide, 7 high at 245 columns, bigger on wider screens): hood, robe, torch; burning: flames, arms up."""
        s = max(1, int(self.w / 200.0 + 0.5))
        top = 2 * y - 6 * s
        robe, hood = ((60, 70, 96), (200, 190, 175)) if connor else ((52, 44, 58), (20, 16, 22))
        if mode == "walk":
            rim = (170, 90, 40) if torch else (60, 56, 70)
            for r in range(6 * s):
                half = (0 if r < 2 * s else 1) * s if r < 5 * s else 1 * s
                for dx in range(-half, half + 1):
                    c = hood if r < 2 * s else robe
                    photo_fx.put_pixel(cv, x + dx, top + r, mix(c, rim, 0.35) if dx == (half if torch else -half) and r >= 2 * s else c)
            if connor:
                photo_fx.put_pixel(cv, x, top + s, (232, 200, 170))
            if torch:
                for r in range(4 * s):
                    photo_fx.put_pixel(cv, x + 2 * s, top + 2 * s + r, (96, 66, 40))
                f = int(t * 9 + ph * 3) % 3
                for r, col in enumerate(((255, 235, 140), (255, 170, 50), (210, 80, 20))):
                    for dx in range(2):
                        photo_fx.put_pixel(cv, x + 2 * s + dx - 1 + (f == 1) * (r & 1), top + 2 * s - 1 - r * s + (f == 2), col)
                cv.light(x + 2 * s, y - 3 * s, (255, 150, 40), 0.35, 0.0)
        else:                                                                       # burning: a charred robe with small flames on head and shoulders (person sized), arms up
            fl = int(t * 12 + ph * 4)
            for r in range(6 * s):
                half = (s if r >= 2 * s else 0) + (s if r > 4 * s else 0)
                for dx in range(-half, half + 1):
                    k = _hash(x + dx, top + r, fl)
                    photo_fx.put_pixel(cv, x + dx, top + r, mix((40, 24, 22), (190, 80, 24), 0.25 + 0.5 * k * (1.0 - r / (6.0 * s)) if k > 0.55 else 0.12))
            if mode == "up":
                for r in range(3 * s):
                    photo_fx.put_pixel(cv, x - 2 * s - r // 2, top + r, (120, 60, 30))
                    photo_fx.put_pixel(cv, x + 2 * s + r // 2, top + r, (120, 60, 30))
            for q in range(-1, 2):                                                   # three small flames licking up: 2-4 px tall, flickering
                hgt = 2 + int(2 * _hash(x + q, fl, 3))
                for r in range(hgt):
                    photo_fx.put_pixel(cv, x + q * s, top - 1 - r, fire_rgb(0.9 - 0.7 * r / float(hgt)))
            for q in (-2 * s, 2 * s):
                if mode == "up":
                    photo_fx.put_pixel(cv, x + q + (q // abs(q)) * s, top - 1, fire_rgb(0.6 + 0.3 * _hash(x, fl, 4)))
            cv.light(x, y - 2, (255, 120, 30), 0.12, 0.0)

    def draw_cult(self, cv, t):
        for c in self.cult:
            x, y, st = int(c["x"]), int(c["y"]), c["st"]
            if st == "in":
                continue
            if st == "walk":
                self.figure(cv, x, y, t, "walk", c["ph"], c["torch"], bool(c.get("connor")))
            else:
                if c.get("connor"):
                    glow(cv, x, y - 1, 5, 2, (255, 140, 40), 0.18)
                    self.figure(cv, x, y, t, "burn", c["ph"], False, True)
                    continue
                if _hash(x, y, int(t * 3)) < 0.35:
                    self.fire.inject(x, y - 2, 0.25)                                    # a hint of heat above the head, no more
                self.figure(cv, x, y, t, "up" if t >= c["pull"] else "burn", c["ph"], False)
                if self.rng.random() < 0.3:
                    self.parts.add(x, y - 1, self.rng.uniform(-3, 3), -self.rng.uniform(2, 8), 1.0, "ember", -2.0)

    # -- water views
    def render_lake(self, cv, t, fire_k):
        """The lake pixels of the photo replaced by the simulated water (two pixels per cell, true colour)."""
        a, w = self.water.a, self.w
        mask = self.mask
        for (x, y) in self.wcells:
            cols = []
            for ypx in (2 * y, 2 * y + 1):
                if (x, ypx) in mask and 0 < x < w - 1 and 0 < ypx < 2 * self.h - 1:
                    row = a[ypx]
                    sl = abs(row[x + 1] - row[x - 1]) + abs(a[ypx + 1][x] - a[ypx - 1][x])
                    cols.append(water_px(row[x], sl, fire_k, x, ypx, w, self.px[ypx][x]))
                else:
                    cols.append(self.px[ypx][x] if ypx < 2 * self.h else (0, 0, 0))
            i = y * w + x
            cv.ch[i], cv.fg[i], cv.bg[i] = "▀", cols[0], cols[1]

    def render_close(self, cv, t, fire_k, whirl):
        """The close-up of the water: the whole screen is lake, shaded from the wave heights (a light from the burning shore, moon glitter, foam)."""
        a, w, h = self.close.a, self.w, self.h
        for y in range(h):
            r0, r1 = a[2 * y], a[2 * y + 1]
            u0, d0 = a[max(0, 2 * y - 1)], a[2 * y + 1]
            for x in range(w):
                cols = []
                for ypx, row in ((2 * y, r0), (2 * y + 1, r1)):
                    if 0 < x < w - 1 and 0 < ypx < 2 * h - 1:
                        sl = abs(row[x + 1] - row[x - 1]) * 1.6 + abs(a[ypx + 1][x] - a[ypx - 1][x]) * 1.6
                        hh = row[x]
                    else:
                        sl = hh = 0.0
                    base = mix((8, 18, 38), (30, 62, 104), 0.3 + 0.3 * math.sin(x * 0.05 + ypx * 0.11 + t * 0.4))
                    c = water_px(hh, sl, fire_k, x, ypx, w, base)
                    cols.append(c)
                i = y * w + x
                cv.ch[i], cv.fg[i], cv.bg[i] = "▀", cols[0], cols[1]

    def hand_sprite(self, cv, x, ytop, rise, t):
        """A drowning hand reaching out of the water: forearm, palm, five spread fingers with knuckle joints, charred with an ember rim; a foam ring and drips round the wrist."""
        base = 2 * ytop + 30                                                       # water line (pixel rows)
        top = base - int(30 * rise)
        flesh = lambda k: mix((236, 156, 116), (70, 34, 28), k)
        for ypx in range(top + 10, base):                                          # forearm, tapering to the wrist
            half = 1 if ypx < base - 6 else 2
            for dx in range(-half, half + 1):
                photo_fx.put_pixel(cv, x + dx, ypx, flesh(0.25 + 0.5 * abs(dx) / (half + 1) + 0.2 * _hash(x + dx, ypx, 4)))
        for ypx in range(top + 5, top + 11):                                       # palm
            half = 3 if ypx > top + 6 else 2
            for dx in range(-half, half + 1):
                photo_fx.put_pixel(cv, x + dx, ypx, flesh(0.2 + 0.4 * abs(dx) / (half + 1) + 0.2 * _hash(x + dx, ypx, 5)))
        for j, ang in enumerate((-0.75, -0.36, 0.0, 0.34, 0.62)):                    # fingers fan out and curl; the thumb is short
            ln = (7, 11, 13, 11, 8)[j] * (0.4 + 0.6 * rise) + math.sin(t * 6 + j) * 0.6
            fx0, fy0 = x + int((j - 2) * 1.4), top + 6
            for q in range(int(ln)):
                a_ = ang * (1 + 0.04 * q)
                px, py = fx0 + math.sin(a_) * q * 1.1, fy0 - math.cos(a_) * q
                bone = q >= int(ln) - 2
                for ox in (0, 1):
                    photo_fx.put_pixel(cv, int(round(px)) + ox, int(round(py)), (226, 214, 190) if bone else flesh(0.3 + 0.03 * q))
        for k in range(-6, 7):                                                     # the ring of foam and the drips
            if _hash(k, int(t * 8), 7) > 0.3:
                cv.put(x + k * 1, ytop + 14, "~o'-"[abs(k) % 4], (225, 238, 250))
        for k in range(3):
            photo_fx.put_pixel(cv, x + int(math.sin(t * 5 + k) * 4), base - 4 + (int(t * 12) + k * 3) % 8, (200, 225, 250))

    def orbit_bodies(self, cv, t, whirl):
        wt = self.close
        vx, vy = wt.vx, wt.vy / 2.0
        for c in self.cult:
            if c["st"] != "in":
                continue
            tau = t - c["tin"]
            dur = 6.5 if c.get("connor") else 3.2
            if tau > dur:
                continue
            r0 = 14 + (c["ph"] * 5)
            r = r0 * max(0.0, 1 - tau / dur) ** 1.2 + 0.5
            ang = c["ang"] + tau * (1.6 + 2.5 * tau / 3.2)
            x, y = int(vx + math.cos(ang) * r * 2.4), int(vy + math.sin(ang) * r * 0.6)
            k = 1 - tau / dur
            for dy in range(-2, 3):                                                   # a drowning body: a burning robe, flailing arms, a trail of foam
                for dx in range(-2, 3):
                    if abs(dx) + abs(dy) < 4:
                        photo_fx.put_pixel(cv, x + dx, 2 * y + dy, mix(fire_rgb(0.3 + 0.5 * _hash(x + dx, y + dy, int(t * 10))), (20, 24, 40), 1 - k))
            ax = int(2 * math.sin(t * 9 + c["ph"]))
            photo_fx.put_pixel(cv, x - 3 + ax, 2 * y - 3, (255, 180, 90)); photo_fx.put_pixel(cv, x + 3 - ax, 2 * y - 3, (255, 180, 90))
            cv.light(x, y, (255, 90, 20), 0.3 * k, 0.0)
            if self.rng.random() < 0.4:
                self.parts.add(x, y, self.rng.uniform(-2, 2), -self.rng.uniform(3, 8), 1.2, "bubble", -3.0)
            if tau > dur - 0.3 and not c.get("popped"):
                c["popped"] = True
                self.parts.burst(x, y, 8, "bubble", 6, 1.0, -6.0)
                self.close.poke(x, 2 * y, 0.8, 3)

    # -- shots
    def paint_base(self, cv):
        cv.ch, cv.fg, cv.bg = self.cvbase.ch[:], self.cvbase.fg[:], self.cvbase.bg[:]

    def shot_wide(self, cv, t, dt, k_fire, mika=True):
        self.paint_base(cv)
        w, h = self.w, self.h
        lx, ly = self.lake[0], self.lake[1]
        self.render_lake(cv, t, k_fire)
        hx, hy = self.at(1.0, 0)
        for hs in self.houses:
            hs["ign"] = 2.4 if hs is self.first else T_WIDE2 + 0.5 + math.hypot((hs["x"] - hx) / 2.0, hs["y"] - hy) / 22.0 + 0.8 * _hash(hs["x"], hs["y"])
            self.draw_house(cv, hs, t)
            a = t - hs["ign"]
            if 0 <= a < (30 if hs is self.first else 14):
                for k in range(hs["ww"]):
                    self.fire.inject(hs["x"] + k, hs["y"], min(0.7, 0.2 + a * 0.3) * (1 - a / 16.0))
                    self.fire.inject(hs["x"] + k, hs["y"] + 1, min(0.5, 0.1 + a * 0.2) * (1 - a / 16.0))
        for (cx, cy) in self.churches:                                                 # the church towers burn like torches, a little after the houses
            if t > T_WIDE2 + 2.4 + 0.15 * math.hypot((cx - hx) / 2.0, cy - hy) / 4.0:
                for q in range(-1, 2):
                    self.fire.inject(cx + q, cy - 6, 0.8)
                    self.fire.inject(cx + q, cy - 3, 0.6)
        if t > T_WIDE2 + 1.0:                                                        # the forest catches from the houses, a wave through the real woods
            for (x, y, ti) in self.trees:
                if ti > t:
                    break
                a = t - ti
                if a < 7.0 and _hash(x, y, int(t * 4)) < 0.10:
                    self.fire.inject(x, y, 0.55 * (1 - a / 8.0) + 0.1)
                if (x, y) not in self.burnt and a > 0.4:
                    self.burnt.add((x, y))
                    i = y * w + x
                    for buf in (self.cvbase.fg, self.cvbase.bg):
                        buf[i] = mix(buf[i], (18, 9, 8), 0.5)
        if mika:                                                                      # Mika at the bench corner: a silhouette with two pale-teal points for eyes, stands up slowly
            mx, my = self.P(*SRC_MIKA)
            mx, my = int(mx), min(h - 1, int(my))
            up = smooth((t - 1.5) / 2.5)
            for fig, rv in ((self.mika_sit, 1 - up), (self.mika_st, up)):
                if rv > 0.02:
                    grid, _ = fig.cells(t, eyes=min(1.0, max(0.0, (t - 3.0) / 3.0)), reveal=rv, tint=((0, 0, 8), 0.7 - 0.4 * k_fire))
                    blit_grid(cv, grid, mx - fig.wf // 2, my - fig.hf)
            if t > 3.0:
                glow(cv, mx, my - 6, 10, 5, (60, 220, 190), 0.12 * smooth((t - 3) / 3.0))
        self.step_cult(t, dt)
        self.draw_cult(cv, t)
        if 0.3 <= t < 3.2:                                                              # the cube drops into the lake from the sky (the consequence of the tesseract scene)
            if t < 1.5:
                cy_ = int(-3 + (ly + 3) * smooth((t - 0.3) / 1.2))
                draw_cube(cv, lx, cy_, 2.0, t * 4, (150, 255, 235), 1.0)
                for k in range(3):
                    cv.put(lx + self.rng.randint(-1, 1), cy_ - 2 - k, "|", (120, 220, 210))
            else:
                if not getattr(self, "_splash", False):
                    self._splash = True
                    self.water.poke(lx, ly * 2, 1.4, 4)
                    self.parts.burst(lx, ly, 14, "spray", 10, 0.9, 20.0, up=8)
                r = (t - 1.5) * 16
                for a in range(0, 360, 4):
                    cv.put(int(lx + math.cos(math.radians(a)) * r * 2), int(ly + math.sin(math.radians(a)) * r * 0.5), "o", mul((150, 255, 235), max(0.0, 1 - r / 28.0)))
        if t > T_WIDE2:
            self.fire.draw(cv, 0.14, solid=0.6)
        if mika and t >= T_WIDE2:                                                      # the first wave: a ring leaves Mika
            mx, my = self.P(*SRC_MIKA)
            r = (t - T_WIDE2) * 55
            if r < 140:
                for a in range(0, 360, 3):
                    cv.put(int(mx + math.cos(math.radians(a)) * r * 2), int(my - 6 + math.sin(math.radians(a)) * r * 0.55), "o", mul((120, 255, 230), 1 - r / 140.0))

    def shot_faces(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((10, 4, 4))
        for y in range(h):
            for x in range(w):
                cv.bg[y * w + x] = mix((14, 6, 6), (70, 26, 8), (x / float(w)) * 0.3 + 0.2 * math.sin(t * 7 + x * 0.1) * (y / float(h)))
        n = self.faces_n
        hf = int(h * 0.62)
        s = hf / 14.0
        wf = int(2 * 2 * 6.2 * s)
        for i in range(n):
            cx = int(w * (i + 0.5) / n)
            age = t - (T_IGN + 0.18 * i) - (1.6 if i == n - 1 else 0.0)                 # Connor burns later and slower
            grid = []
            for yy in range(hf):
                row = []
                ty = (yy + 0.5) / s
                for xx in range(wf):
                    tx = (xx - wf / 2.0 + 0.5) * 0.5 / s + math.sin(t * 2.5 + i) * 0.25 * (ty / 14.0)
                    code = cult_region(tx, ty)
                    if code is None:
                        row.append(None)
                        continue
                    n1, n2 = _hash(xx, yy, i), _hash(yy, xx, i)
                    cn = i == n - 1                                                                  # Connor: hair instead of a hood, a calm smile, eyes shut
                    if code == "H" and cn:
                        base, ch = (112, 88, 62), "|/\\)("[int(n1 * 5)]
                        fg, bg = mul(base, 0.6 + 0.4 * n2), mul(base, 0.3)
                    elif code == "e" and cn:
                        ch, fg, bg = "^", (30, 20, 20), (200, 156, 132)
                    elif code == "m" and cn:
                        ch, fg, bg = ("_" if abs(tx) < 1.0 else ("\\" if tx < 0 else "/")), (120, 40, 40), (200, 156, 132)
                    elif code == "H":
                        base, ch = (176, 168, 150), "▒▓#%"[int(n1 * 4)]
                        fg, bg = mul(base, 0.5 + 0.4 * n2), mul(base, 0.25)
                    elif code == "e":
                        ch, fg, bg = ("@", (255, 255, 255), (30, 20, 20)) if t < T_IGN - 0.5 else ("O", (255, 255, 255), (30, 10, 10))
                    elif code == "m":
                        o = (0.5 + 0.5 * math.sin(t * (3 + i) + i)) if t < T_IGN else 1.0
                        ch, fg, bg = ("O", (30, 0, 0), (12, 0, 0)) if o > 0.4 else ("-", (60, 20, 20), (150, 100, 90))
                    else:
                        base = (200, 156, 132)
                        ch, fg, bg = ".,:'"[int(n1 * 4)], mul(base, 0.8 + 0.3 * n2), mul(base, 0.7)
                    lit = 0.45 + 0.6 * (0.5 + 0.5 * math.sin(t * 9 + i * 2 + xx * 0.05))      # torchlight flickering from the side
                    fg, bg = mix(mul(fg, lit), (255, 130, 40), 0.18), mix(mul(bg, lit), (120, 40, 8), 0.2)
                    if age >= 0:
                        ccode = {"H": "c", "f": "f"}.get(code)
                        if ccode:
                            c4 = G.Body.look(None, ccode, age - 0.4 * n1, n1, n2, t, 8)
                            ch, fg, bg = c4[:3]
                            if c4[3]:
                                self.fire.inject(cx - wf // 2 + xx, h - hf + yy - 1 + (h - hf) // 2, min(1.0, c4[3]))
                        elif code in "em" and age > 0.3:
                            ch, fg, bg = ("O", (255, 140, 40), (10, 0, 0)) if code == "m" else ("o", (255, 90, 30), (8, 0, 0))
                    row.append((ch, fg, bg))
                grid.append(row)
            blit_grid(cv, grid, cx - wf // 2, (h - hf) // 2 + 1)
            by0 = (h - hf) // 2 + 1 + hf - 2                                                   # robe: shoulders widening under the hood, a raised arm with a torch
            for yy in range(by0, h):
                half = int(wf * 0.30 + (yy - by0) * 1.3)
                for xx in range(cx - half, cx + half + 1):
                    k = 0.5 + 0.5 * _hash(xx, yy, i)
                    cv.put(xx, yy, "|!/\\"[int(k * 4) % 4] if (xx + yy) % 3 == 0 else " ", mul((86, 70, 66), 0.4 + 0.4 * k), mul((24, 18, 18), 0.6 + 0.4 * k))
            if i != n - 1:
                ax_, ay_ = cx + int(wf * 0.42), by0 + 2
                tx_, ty_ = ax_ + 8, int(h * 0.20)
                for xx, yy, d in G.thick_line((ax_, ay_), (tx_, ty_), 1.5):
                    cv.put(xx, yy, "=", (96, 78, 70), (34, 26, 24))
                for yy in range(ty_ - 2, ty_ + 5):
                    cv.put(tx_ + 1, yy, "|", (110, 78, 46), (40, 24, 12))
                for dx in range(-2, 4):
                    for dy in range(0, 7):
                        self.fire.inject(tx_ + dx, ty_ - dy + 1, 0.85 - dy * 0.1)
                cv.light(tx_, ty_, (255, 150, 40), 0.5, 0.0)
            if age > 0 and rng.random() < 0.25:
                self.parts.burst(cx, (h - hf) // 2 + hf * 0.5, 2, "spark", 14, 0.7, 10.0, up=6)
        if t > T_IGN - 0.5:
            for x in range(0, w):
                self.fire.inject(x, h - 1, 0.7 * _hash(x, 8) + 0.3)
            self.fire.draw(cv, 0.14, solid=0.6)

    def shot_water(self, cv, t, dt, k_fire):
        w, h = self.w, self.h
        whirl = smooth((t - T_WATER - 0.5) / 3.0) * (1 - smooth((t - T_AFTER - 2) / 6.0))
        self.close.vort = whirl
        self.close.vx, self.close.vy = w * 0.5, h
        if int(t * 10) % 3 == 0 and t < T_AFTER:                                       # the shore is still burning: the water is restless
            self.close.poke(self.rng.uniform(4, w - 4), self.rng.uniform(4, 2 * h - 4), 0.12, 2)
        self.close.step()
        self.render_close(cv, t, k_fire + 0.2, whirl)
        if whirl > 0.02:                                                              # the whirlpool: spiral arms of foam, brighter at the rim
            for k in range(int(1800 * whirl)):
                r = (k / 1800.0) ** 0.8 * 34 * whirl
                ang = r * 0.5 - t * 3.0 + (k % 3) * 2.09
                xx, yy = int(w * 0.5 + math.cos(ang) * r * 2), int(h * 0.5 + math.sin(ang) * r * 0.5 * h / 22.0)
                c_ = mix((70, 100, 150), (235, 244, 255), 1 - r / 34.0)
                photo_fx.put_pixel(cv, xx, 2 * yy, c_)
                photo_fx.put_pixel(cv, xx, 2 * yy + 1, c_)
        self.orbit_bodies(cv, t, whirl)
        for fx, fy, th in self.hands:                                                 # the last hands
            a = t - th
            if 0 <= a < 1.8:
                x, y = int(fx * w), int(fy * h)
                rise = min(1.0, a * 3) * (1 - smooth((a - 1.3) / 0.5))
                if rise > 0.1:
                    self.hand_sprite(cv, x, y, rise, t)
                if 1.3 < a < 1.4:
                    self.parts.burst(x, y + 6, 8, "bubble", 6, 1.0, -5.0)
                    self.close.poke(x, 2 * y + 12, 0.8, 3)

    def shot_calm(self, cv, t, dt):
        w, h = self.w, self.h
        left = max(0.0, 1 - (t - T_CALM) / 6.0)
        self.shot_wide(cv, t, dt, 0.12 * max(0.0, 1 - (t - T_CALM) / 5.0), mika=False)
        for x in range(0, w, 3):                                                       # the far shore still burns down, embers
            if _hash(x, 6) < 0.5 * left:
                self.fire.inject(x, int(h * 0.15 + 4 * _hash(x, 2)), 0.5)
        fig = self.mika_big
        mx = int(w * 0.14)
        grid, _ = fig.cells(t, eyes=0.35 + 0.15 * math.sin(t * 0.8), aura=0.2, tint=((0, 0, 6), 0.35))
        blit_grid(cv, grid, mx - fig.wf // 2, h - 2 - fig.hf)
        glow(cv, mx, h - 2 - fig.hf // 2, 24, 14, (40, 160, 140), 0.07)
        if 35.4 <= t < 36.4:                                                          # one bubble
            bx, by = int(w * 0.30), int(h * 0.40 - (t - 35.4) * 6)
            cv.put(bx, by, "o", (210, 235, 255))
            if t > 36.3:
                cv.put(bx - 1, by - 1, "'", (210, 235, 255)); cv.put(bx + 1, by - 1, "'", (210, 235, 255))
                self.water.poke(bx, int(h * 0.40) * 2, 0.6, 3)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        self.fire.step()
        self.water.step()
        self.parts.step(dt)
        burn_k = smooth((t - T_WIDE2) / 3.0) * (1 - 0.7 * smooth((t - T_CALM) / 5.0))
        if t < T_FACES:
            self.shot_wide(cv, t, dt, 0.0)
        elif t < T_WIDE2:
            self.shot_faces(cv, t, dt)
        elif t < T_WATER:
            self.shot_wide(cv, t, dt, burn_k)
        elif t < T_AFTER:
            self.shot_water(cv, t, dt, burn_k)
        elif t < T_CALM:
            self.shot_water(cv, t, dt, burn_k) if t < T_AFTER + 3.0 else self.shot_wide(cv, t, dt, burn_k)
            for k in range(int(30 * smooth((t - T_AFTER) / 3.0)) + 1):               # steam over the lake
                if rng.random() < 0.5 and self.wcells:
                    x, y = self.wcells[rng.randrange(len(self.wcells))]
                    self.parts.add(x, y, rng.uniform(-1, 1), -rng.uniform(1, 3), 3.0, "smoke", -0.3)
        else:
            self.shot_calm(cv, t, dt)
        self.parts.draw(cv, 0.4)
        photo_fx.finish(cv, t, 0.035, 0.3)
        if t < 1.0:
            darken(cv, smooth(t))
        if t > END - 1.2:
            darken(cv, max(0.0, (END - t) / 1.2))
        fl = max([math.exp(-(t - c) / 0.09) for c in (T_WIDE2, T_WATER, T_CALM) if c <= t < c + 0.5] + [0.0])
        flash(cv, (255, 190, 130), 0.6 * fl)
        amp = shake_at(t, self.hits, 1.0, 0.3)
        if T_WIDE2 <= t < T_AFTER:
            amp += 0.35
        return jolt(rng, amp)


def valley_captions(lines):
    beats = [(1.0, 5.4), (5.6, 9.8), (10.2, 14.6), (14.8, 18.2), (18.4, 22.4), (22.6, 27.4), (28.0, 35.0), (36.0, 39.6)]
    return [(a, b, l) for (a, b), l in zip(beats, lines)] if len(lines) == len(beats) else G.spread(lines, 1.0, 39.6)


VALLEY_CUES = [(0.4, "church-bell-toll"),             # the bell, then the chanting starts
               (3.0, "church-bell-toll"), (6.6, "crowd-scream-distant"),      # faces: the crowd noise swells (placeholder for chant)
               (T_IGN, "fire-ignite"), (T_IGN + 0.6, "scream-choir"), (T_WIDE2, "fire-roar"), (T_WIDE2 + 0.1, "fire-ignite"),
               (13.5, "church-bell-toll"), (14.6, "scream-choir"), (T_PULL, "ground-rumble"), (T_PULL + 0.6, "scream-reverse"),
               (19.0, "water-pull-splash"), (T_WATER, "water-pull-splash"), (21.5, "bubbles-gurgle"), (24.0, "scream-reverse"),
               (25.5, "bubbles-gurgle"), (T_AFTER, "lake-calm"), (T_CALM, "lake-calm"), (35.4, "bubbles-gurgle")]    # an audio agent will tune these
