"""abyss_fx.py - the Schlund: a huge maw seen from above while Noah falls through it, and the hell at the bottom (about 10 s from `tau` = 0).

Layers of rock rush outwards past the camera (ledges with lava in the cracks, faces and hands pressed out of the stone), the shaft glows red
towards its far end; from tau 4.6 the bottom opens: a lava sea with fire columns and drifting souls; at tau 8.6 Noah lands in the middle
(a fire pillar, a shock ring, a roar). AbyssScene.draw(cv, tau, dt, noah_cb) is used inside noah_burns; AbyssDemo is the same on its own.
python3 play.py --mika-ending --only abyss
"""
import math

import noah_gore_fx as G
from noah_gore_fx import Fire, Particles, add, darken, fire_rgb, flash, glow, jolt, mix, mul, shake_at, smooth, _hash

FACES = (["(o o)", " (_) ", " \\^/ "], ["_._ _", "(O O)", " ^^^ "], [" .-. ", "(; ;)", " ~o~ "])
HANDS = (["\\|/|/", " \\|/ ", "  |  "], [" \\ | ", " \\\\|/", "  ||  "])
LAND = 8.6


class AbyssScene:
    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.cx, self.cy = w // 2, int(h * 0.44)
        self.R = h * 0.62
        self.rad, self.ang = [], []
        for y in range(h):
            for x in range(w):
                self.rad.append(math.hypot((x - self.cx) / 2.0, y - self.cy) / self.R)
                self.ang.append(math.atan2(y - self.cy, (x - self.cx) / 2.0))
        self.parts = Particles(rng, 1200)
        self.fire = Fire(max(0, self.cx - 60), min(120, w), h, rng, decay=0.06)
        self.landed = False
        self.rings = []

    def wall(self, cv, tau, speed):
        w, h = self.w, self.h
        for i, r in enumerate(self.rad):
            z = 0.9 / (r + 0.06) - tau * speed                                          # depth of the rock at this pixel (grows towards the centre)
            f = z % 1.0
            ab = int(((self.ang[i] + 3.1416) / 6.2832) * 40)
            n = _hash(ab, int(z) + 1000)
            lava = min(1.0, 0.18 + z * 0.05) * max(0.0, 1.15 - r) ** 1.6                 # the far end of the shaft glows
            rock = mul((44, 28, 26), 0.35 + 0.9 * n) if f > 0.14 else (150, 52, 18)      # a ledge: the lit edge of the rock
            if f > 0.14 and n > 0.86:
                rock, ch = (230, 80, 20), "/\\~"[ab % 3]                                  # a crack with lava
            else:
                ch = "%#:'"[int(n * 4)] if f > 0.14 else "="
            c = add(mul(rock, max(0.25, min(1.0, 1.5 - r))), fire_rgb(0.25 + 0.6 * lava), lava * 1.1)
            cv.bg[i], cv.fg[i], cv.ch[i] = mul(c, 0.6), mul(c, 1.25), ch

    def reliefs(self, cv, tau, speed):
        for L in range(0, 14):
            z = L - (tau * speed) % 1.0 + 0.2
            if z < 0.5:
                continue
            rho = 0.9 / z - 0.06
            if not 0.08 < rho < 1.05:
                continue
            idx = L + int(tau * speed)
            for j in range(3):
                if _hash(idx, j, 7) > 0.6:
                    continue
                th = _hash(idx, j, 8) * 6.2832
                x, y = int(self.cx + math.cos(th) * rho * self.R * 2.0), int(self.cy + math.sin(th) * rho * self.R)
                spr = (FACES if _hash(idx, j, 9) < 0.55 else HANDS)[int(_hash(idx, j, 10) * 2)]
                if rho < 0.2:
                    cv.put(x, y, "o", (160, 130, 120))
                    continue
                for k, row in enumerate(spr):
                    for m, c in enumerate(row):
                        if c != " ":
                            cv.put(x - 2 + m, y - 1 + k, c, mul((190, 160, 148), min(1.0, rho + 0.3)), (40, 22, 20))
                cv.light(x, y, (255, 70, 10), 0.18 * rho, 0.0)

    def hell(self, cv, tau, dt, noah_xy):
        """The bottom of the shaft: a lava sea in the middle, fire columns, rising souls."""
        k = smooth((tau - 4.6) / 3.0)
        if k <= 0:
            return
        w, h, rng = self.w, self.h, self.rng
        rf = k * 0.55
        for i, r in enumerate(self.rad):
            if r < rf:
                x, y = i % w, i // w
                d = r / max(0.01, rf)
                v = 0.30 + 0.5 * (1 - d) + 0.12 * math.sin(x * 0.45 + y * 0.9 + tau * 5 + _hash(x, y) * 3)
                if _hash(x // 3, y, int(tau * 4)) > 0.93:
                    v = min(1.0, v + 0.3)
                col = fire_rgb(min(1.0, v))
                cv.bg[i], cv.fg[i], cv.ch[i] = mul(col, 0.7), mul(col, 1.2), "~^*:"[(x + y + int(tau * 6)) % 4] if v > 0.5 else "."
        for j in range(7):                                                              # fire columns standing on the lava
            a = j * 0.9 + 0.3
            x, y = int(self.cx + math.cos(a) * rf * self.R * 1.5), int(self.cy + math.sin(a) * rf * self.R * 0.4 + 2)
            if 0 <= x < w and 0 <= y < h:
                for dx in range(-1, 2):
                    self.fire.inject(x + dx, y, 0.95 * k)
        for _ in range(int(14 * k)):                                                    # souls drift up out of the lava, in slow spirals
            a = rng.uniform(0, 6.28)
            rr = rng.uniform(0.05, rf)
            self.parts.add(self.cx + math.cos(a) * rr * self.R * 2, self.cy + math.sin(a) * rr * self.R * 0.5, rng.uniform(-2, 2), -rng.uniform(2, 7), rng.uniform(2.0, 4.0), "soul", -0.5)
        for q in self.parts.p:
            if q[6] == "soul":
                q[2] += math.sin(q[0] * 0.3 + tau * 2.0) * 6 * dt
        for j in range(5):                                                              # a few bigger, screaming souls
            t0 = j * 1.3
            a = (tau - 5.0 - t0) / 3.5
            if 0 < a < 1:
                x = int(self.cx + (j - 2) * self.R * 0.55 + math.sin(tau * 2 + j) * 3)
                y = int(self.cy + 2 - a * h * 0.5)
                for r, row in enumerate((" .-. ", "(O O)", " \\O/ ", " | | ")):
                    cv.text(x - 2, y + r, row, mul((190, 215, 255), math.sin(math.pi * a)), None)

    def draw(self, cv, tau, dt, noah_cb=None):
        w, h, rng = self.w, self.h, self.rng
        cv.clear()
        speed = 1.2 + 0.25 * tau
        self.wall(cv, tau, speed)
        self.reliefs(cv, tau, speed)
        self.fire.step()
        self.hell(cv, tau, dt, None)
        # Noah, shrinking towards the middle
        size = math.exp(-0.62 * tau)
        if tau >= LAND:
            size = 0.0
        if noah_cb and size > 0:
            noah_cb(cv, self.cx, self.cy, size, tau)
            if size < 0.1:
                self.fire.inject(self.cx, self.cy, 0.9)
        if tau >= LAND and not self.landed:
            self.landed = True
            self.rings.append(tau)
            self.parts.burst(self.cx, self.cy, 70, "ember", 30, 1.6, 8.0, up=14)
        if self.landed:
            a = tau - LAND
            for x in range(self.cx - 2, self.cx + 3):                                   # the pillar
                for yy in range(0, int(4 + a * 40)):
                    self.fire.inject(x, self.cy - yy // 2, 1.0)
            for t0 in self.rings:
                r = (tau - t0) * 26
                if r < 70:
                    for a2 in range(0, 360, 3):
                        cv.put(int(self.cx + math.cos(math.radians(a2)) * r * 2), int(self.cy + math.sin(math.radians(a2)) * r * 0.5), "O", mul((255, 190, 120), 1 - r / 70.0))
        self.fire.draw(cv, 0.14, solid=0.62)
        self.parts.step(dt)
        self.parts.draw(cv, 0.4)
        # embers stream up the shaft
        for _ in range(int(40 + 8 * tau)):
            if rng.random() < 0.5:
                self.parts.add(rng.randrange(w), h - 1, rng.uniform(-2, 2), -rng.uniform(8, 26), rng.uniform(0.8, 2.0), "ember", -2.0)
        if tau >= LAND:
            flash(cv, (255, 200, 140), 0.8 * math.exp(-(tau - LAND) / 0.1))
        amp = (shake_at(tau, [(LAND, 3.0)], 1.0, 0.5)) + 0.5
        return jolt(rng, amp)


class AbyssDemo:
    """The abyss on its own (~11 s): a burnt Noah falls into it. python3 play.py --mika-ending --only abyss"""
    END = 11.5

    def __init__(self, w, h, rng):
        self.ab = AbyssScene(w, h, rng)
        self.body = G.Body(max(10, int(h * 0.5)), rng)

    def draw(self, cv, t, dt):
        grid = self.body.render(25.0)

        def noah(cv, cx, cy, size, tau):
            ow, oh = self.body.wf * size, self.body.hf * size
            G.blit_grid(cv, grid, int(cx - ow / 2), int(cy - oh / 2), size, size)
        r = self.ab.draw(cv, t, dt, noah)
        if t > self.END - 0.8:
            darken(cv, max(0.0, (self.END - t) / 0.8))
        return r


ABYSS_CUES = [(0.1, "scream-falling-1"), (0.3, "fall-wind"), (2.2, "scream-falling-2"), (4.6, "hell-roar"), (6.0, "growl-demon"), (8.5, "impact-boom-huge"), (8.6, "fire-roar"), (9.6, "sub-drop")]    # audio agent: tune
