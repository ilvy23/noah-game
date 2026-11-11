"""cine_fx.py - the cinematic scenes of the boss fight and its endings (frame-based, deterministic, headless-testable, built on noah_gore_fx.play).

    IntroNoise   (2.0 s)  the boss intro breaks: Noah's sweet portrait glitches, cracks, splits, red light behind it, the red one steps out.
    PhaseMerge   (3.8 s)  one of the three personality changes: ghosts of the earlier personalities converge, the morph frames play, a ring leaves.
    DefeatScene  (11 s)   Noah is beaten: the fusion falls apart into green, yellow and red, a small green Noah is left in the light.
    DecisionScene (7 s)   the quiet before the choice (the 30 s timer runs after it, untouched): the hall, the beams, Noah, two lights.
    EndingLet / EndingSlaughter / EndingThree (14 s each)  dawn and a walk away; the castle burning and Noah to ash; a candle that burns down.
NAMED maps every scene to (factory, seconds, caption key, cues); run_named(ctx, name) plays one.   python3 play.py --mika-ending --only intro|phase2|phase3|phase4|defeat|decision|ending-let|ending-slaughter|ending-3
"""
import json
import math
import os
import re

import noah_gore_fx as G
from noah_gore_fx import (BLACK, Body, Canvas, Fire, Particles, add, anim_sprite, walk, blit, blit_grid, darken, fire_rgb, flash, glow, jolt, mix, morph_sprite, mul,
                          portrait_cells, ramp, shake_at, smooth, _hash)

G_HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ("green", "yellow", "red", "fusion")
HUE = {"green": (90, 235, 120), "yellow": (245, 215, 70), "red": (255, 60, 60), "fusion": (255, 130, 130)}


def size_for(w, h):
    return "big" if h >= 32 and w >= 62 else "small" if h >= 17 and w >= 32 else None


def static(cv, rng, density, col, region=None):
    x0, y0, x1, y1 = region or (0, 0, cv.w, cv.h)
    for _ in range(int((x1 - x0) * (y1 - y0) * density)):
        cv.put(rng.randrange(x0, x1), rng.randrange(y0, y1), rng.choice("#%@&$?!/\\|<>~^+=:;"), mul(col, rng.uniform(0.3, 1.0)))


def crack_cells(cx, cy, rng, branches, length, aspect=2.0):
    out = []
    for _ in range(branches):
        a, x, y = rng.uniform(0, 6.28), float(cx), float(cy)
        for _ in range(length):
            a += rng.uniform(-0.6, 0.6)
            x, y = x + math.cos(a) * aspect, y + math.sin(a)
            out.append((int(x), int(y), "/\\|-"[int((a / 1.5708) % 4)]))
    return out


class IntroNoise:
    END = 2.0

    def __init__(self, w, h, rng, backdrop=None):
        self.w, self.h, self.rng = w, h, rng
        self.backdrop = [l for l in (backdrop or [])][-(h - 3):]                          # the text that was on screen: the place distorts first
        self.size = size_for(w, h)
        self.a = portrait_cells("noah_green", self.size) if self.size else None
        self.b = portrait_cells("noah_red", self.size) if self.size else None
        self.W, self.H = (len(self.a[0]), len(self.a)) if self.a else (0, 0)
        self.crack = crack_cells(w // 2, h // 2, rng, 6, 40)
        self.hits = [(0.0, 3.0), (1.35, 2.5)]

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((6, 0, 0) if t > 1.3 else BLACK)
        if t < 1.1:                                                                       # the old screen, text rows tearing sideways, colours bleeding to red
            gg = smooth(t / 0.9)
            for y, line in enumerate(self.backdrop):
                dx = rng.randint(-int(2 + 14 * gg), int(2 + 14 * gg)) if rng.random() < 0.15 + 0.6 * gg else 0
                for x, c in enumerate(line[:w]):
                    if c != " ":
                        cv.put(x + dx, y + 1, rng.choice("#%@&$?/\\") if rng.random() < 0.25 * gg else c, mix((210, 210, 200), (255, 40, 30), gg))
        ox, oy = (w - self.W) // 2, max(0, (h - 1 - self.H) // 2)
        g = smooth((t - 0.1) / 1.0)
        if self.a and t < 1.5:
            split = smooth((t - 1.2) / 0.3) * (self.W // 3 + 4)
            for y in range(self.H):
                shift = rng.randint(-8, 8) if rng.random() < 0.35 * g else 0
                for x in range(self.W):
                    ch, fg, bg = self.a[y][x]
                    dx = (-split if x < self.W // 2 else split) + shift
                    if rng.random() < 0.05 * g:
                        ch, fg = rng.choice("#%@&$?!/\\|"), (255, 70, 70)
                    cv.put(ox + x + int(dx), oy + y, ch, mix(fg, (255, 40, 40), 0.5 * g), mul(bg, 1 - 0.5 * g))
            if split > 0:                                                               # red light in the gap
                for y in range(self.H):
                    for x in range(int(self.W // 2 - split), int(self.W // 2 + split)):
                        cv.put(ox + x, oy + y, rng.choice("#%@&/\\|"), (255, 200, 160), (200, 10, 10))
        elif self.b and t >= 1.3:
            k = smooth((t - 1.3) / 0.4)
            for y in range(self.H):
                for x in range(self.W):
                    ch, fg, bg = self.b[y][x]
                    cv.put(ox + x, oy + y, ch, mul(fg, 0.3 + 0.7 * k), mul(bg, 0.3 + 0.7 * k))
        if t > 0.5:
            p = smooth((t - 0.5) / 0.7)
            for x, y, c in self.crack[:int(len(self.crack) * p)]:
                cv.put(x, y, c, (255, 230, 220), (150, 0, 0))
        static(cv, rng, 0.02 + 0.25 * g * (1 if t < 1.5 else 0.5), (255, 60, 50))
        if not self.a and t > 0.3:
            static(cv, rng, 0.3, (255, 60, 50))
        flash(cv, (255, 255, 255), max(0.0, 1 - t / 0.15) * 0.9)
        flash(cv, (255, 40, 30), math.exp(-(t - 1.35) / 0.12) * 0.7 if 1.35 <= t < 1.8 else 0.0)
        if t > self.END - 0.35:
            darken(cv, max(0.0, (self.END - t) / 0.35))
        return jolt(rng, shake_at(t, self.hits, 1.0, 0.25))


INTRO_CUES = [(0.0, "impact-boom-huge"), (0.2, "static-burst"), (0.7, "glitch-burst"), (1.3, "glass-crack"), (1.35, "scream-distorted-1")]     # audio agent: tune


class PhaseMerge:
    END = 3.8

    def __init__(self, w, h, rng, to=2):
        self.w, self.h, self.rng, self.to = w, h, rng, int(to); to = int(to)
        self.size = "big" if h >= 31 and w >= 120 else "small" if h >= 16 and w >= 32 else None
        self.old, self.new = KINDS[to - 2], KINDS[to - 1]
        self.hue = HUE[self.new]
        self.ghosts = [anim_sprite(k, "idle", 0, self.size) for k in KINDS[:to - 1]] if self.size else []
        self.ghosts = [g for g in self.ghosts if g]
        self.parts = Particles(rng, 400)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        hue = self.hue
        cv.clear(mul(hue, 0.04))
        dens = 0.02 + 0.2 * math.sin(min(1.0, t / 2.6) * 3.1416)
        static(cv, rng, dens, hue)
        for y in range(0, h, 2):                                                        # scanlines drifting up
            if (y + int(t * 20)) % 6 == 0:
                for x in range(w):
                    cv.light(x, y, mul(hue, 0.05), 1.0, 0.0)
        cx = w // 2
        if self.size:
            sh = 28 if self.size == "big" else 14
            top = max(0, (h - 1 - sh) // 2)
            sep = (60 if self.size == "big" else 30)
            k = smooth((t - 0.3) / 1.8)
            n = len(self.ghosts) + 1
            for i, g in enumerate(self.ghosts):                                         # the earlier personalities converge on the middle
                side = (i - (n - 2) / 2.0) * 1.6 - 0.8 * (1 if n == 2 else 0)
                x = cx + int(side * sep * (1 - k))
                blit(cv, g, x, top, 1.0, 1.0, 0.35 + 0.65 * k, None, BLACK)
            if t < 1.8:
                spr = anim_sprite(self.old, "idle", int(t * 6), self.size)
                if spr:
                    blit(cv, spr, cx, top, 1.0, 1.0, 0.4 + 0.5 * k, lambda i: int(math.sin(t * 30 + i) * (1 + 3 * k)), BLACK)
            elif t < 2.7:
                spr = morph_sprite(self.old, self.new, min(7, int((t - 1.8) / 0.9 * 8)), self.size)
                if spr:
                    blit(cv, spr, cx, top, 1.0, 1.0, 1.0, lambda i: int(math.sin(t * 40 + i) * 2), BLACK)
            else:
                spr = anim_sprite(self.new, "idle", int(t * 6), self.size)
                if spr:
                    pop = 1.0 + 0.12 * math.exp(-(t - 2.7) / 0.2)
                    blit(cv, spr, cx, top - int(sh * (pop - 1) / 2), pop, pop, 1.0, None, BLACK)
        if t >= 2.7:                                                                    # the change goes out as a ring
            r = (t - 2.7) * 55
            for a in range(0, 360, 2):
                cv.put(int(cx + math.cos(math.radians(a)) * r * 2), int(h / 2 + math.sin(math.radians(a)) * r * 0.6), "O", mul(hue, max(0.0, 1 - r / 60.0)))
            if t < 2.8:
                self.parts.burst(cx, h // 2, 40, "spark", 24, 1.0, 6.0)
        self.parts.step(dt)
        self.parts.draw(cv, 0.3)
        flash(cv, mix(hue, (255, 255, 255), 0.6), math.exp(-abs(t - 2.65) / 0.08) * 0.8)
        if t > self.END - 0.3:
            darken(cv, max(0.0, (self.END - t) / 0.3))
        return jolt(rng, shake_at(t, [(1.8, 0.6), (2.65, 2.0)], 1.0, 0.3) + 0.3)


PHASE_CUES = [(0.0, "phase-shift"), (1.8, "glitch-burst"), (2.65, "impact-boom-huge"), (2.7, "scream-distorted-2")]     # audio agent: tune


def _group_grid(spr, g):
    """The cells of a sprite that belong to colour band g (0 left, 1 middle, 2 right) as a None-padded grid."""
    out = []
    for row in spr:
        n = len(row)
        out.append([c if ((0 if x < n * 0.4 else 1 if x < n * 0.6 else 2) == g) else None for x, c in enumerate(row)])
    return out


class DefeatScene:
    END = 11.0

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.size = "big" if h >= 31 and w >= 60 else "small" if h >= 16 and w >= 32 else None
        self.parts = Particles(rng, 800)
        self.fire = Fire(0, w, h, rng, decay=0.1)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((6, 4, 9))
        for x in range(0, w, max(12, w // 8)):                                           # the hall: columns in the dark
            for y in range(h):
                cv.put(x, y, "|", (24, 20, 30))
        cx = w // 2
        sh = 28 if self.size == "big" else 14
        top = max(0, (h - 1 - sh) // 2)
        k = smooth((t - 3.8) / 2.8)                                                        # 'It stops': everything freezes at 0.8 s; 'they come apart' 3.8-6.6; 'what is left' 7.4+
        if self.size and t < 7.8:
            spr = anim_sprite("fusion", "collapse", int(min(t, 0.8) * 3), self.size)
            if spr:
                for g, kind in enumerate(("pg", "py", "pr")):                            # the three break apart and go out, each in its colour
                    dx = int((g - 1) * k * (28 if self.size == "big" else 14))
                    grid = _group_grid(spr, g)
                    blit_grid(cv, [[(c if c is None else (c[0], mul(c[1], 1 - k * 0.85), mul(c[2], 1 - k * 0.85))) for c in r] for r in grid], cx - len(spr[0]) // 2 + dx, top)
                    if t > 3.8 and rng.random() < 0.9 * (1 - k * 0.6):
                        for _ in range(3):
                            self.parts.add(cx + dx + (g - 1) * len(spr[0]) // 4 + rng.randint(-4, 4), top + rng.randint(2, sh), rng.uniform(-3, 3), -rng.uniform(3, 10), rng.uniform(1.5, 3.5), kind, -1.0)
        a = smooth((t - 7.4) / 1.8)
        if self.size and a > 0:                                                          # a small green Noah in a cone of light
            for y in range(h):
                half = int(3 + (y / float(h)) * 14)
                for x in range(cx - half, cx + half + 1):
                    cv.light(x, y, (60, 70, 50), 0.35 * a * (1 - abs(x - cx) / float(half + 1)), 0.0)
            spr = anim_sprite("green", "hurt", int(t * 2), "small")
            if spr:
                blit(cv, spr, cx, h - 2 - 14 - 1, 1.0, 1.0, a, None, BLACK)
        self.parts.step(dt)
        self.parts.draw(cv, 0.2)
        if t < 0.5:
            flash(cv, (255, 255, 255), 1 - t / 0.5)
        if t > self.END - 1.4:
            darken(cv, max(0.0, (self.END - t) / 1.4))
        return jolt(rng, shake_at(t, [(0.0, 3.0), (3.8, 1.0)], 1.0, 0.4))


DEFEAT_CUES = [(0.0, "impact-boom-huge"), (0.6, "glass-crack"), (3.8, "scream-reverse"), (5.2, "sob-small"), (7.4, "lake-whispers")]     # audio agent: tune


class DecisionScene:
    END = 7.0

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.size = "big" if h >= 31 and w >= 60 else "small" if h >= 16 and w >= 32 else None
        self.parts = Particles(rng, 300)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((5, 5, 10))
        cx = w // 2
        narrow = 1.0 - 0.6 * smooth(t / 6.0)
        for y in range(h):                                                               # the moonlight comes down from a high window onto Noah
            half = int((w * 0.16 + (y / float(h)) * w * 0.10) * narrow)
            for x in range(cx - half, cx + half + 1):
                cv.light(x, y, (60, 70, 110), 0.28 * (1 - abs(x - cx) / float(half + 1)) * smooth(t / 1.5), 0.2)
        sh = 28 if self.size == "big" else 14
        spr = anim_sprite("green", "collapse", int(t * 2), self.size) if self.size else None
        if spr:
            blit(cv, spr, cx, h - 2 - sh, 1.0, 1.0, 0.4 + 0.6 * smooth(t / 2.0), None, BLACK)
        for ci, ox in enumerate((-0.30, -0.17, 0.17, 0.30)):                                  # the candles: so quiet you can hear them think (slow breathing flames)
            kx_, ky_ = int(w * (0.5 + ox * 0.9)), int(h * 0.74)
            for yy in range(ky_, ky_ + 4):
                cv.put(kx_, yy, "|", (226, 214, 190), (150, 130, 110))
            br = 0.5 + 0.5 * math.sin(t * 1.3 + ci * 1.7)
            for q in range(2 + int(2 * br)):
                cv.put(kx_, ky_ - 1 - q, "^'*"[min(2, q)], (255, 190 - 40 * q, 70))
            glow(cv, kx_, ky_ - 2, 14, 5, (255, 150, 60), 0.18 + 0.10 * br)
        pulse = 0.5 + 0.5 * math.sin(t * 3)
        lx, rx, ly = int(w * 0.15), int(w * 0.70), int(h * 0.55)
        glow(cv, lx, ly, 20, 8, (255, 40, 30), 0.35 * smooth((t - 3.4) / 1.5) * (0.7 + 0.3 * pulse))      # the red one
        glow(cv, rx, ly, 20, 8, (240, 235, 210), 0.30 * smooth((t - 3.4) / 1.5) * (0.7 + 0.3 * (1 - pulse)))   # the quiet one
        for k, row in enumerate(("   /|   ", "  / |   ", " /  |   ", "====|===", "   ||   ")):    # a blade on the left
            cv.text(lx - 4, ly - 2 + k, row, mul((255, 130, 120), smooth((t - 3.6) / 1.4)))
        for k, row in enumerate(("  _|_|_ ", " | | | |", " |     |", "  \\___/ ")):             # an open hand on the right
            cv.text(rx - 4, ly - 2 + k, row, mul((240, 235, 215), smooth((t - 3.6) / 1.4)))
        for _ in range(2):
            self.parts.add(cx + rng.randint(-20, 20), rng.randint(0, h // 2), rng.uniform(-1, 1), rng.uniform(1, 3), 4.0, "dust")
        self.parts.step(dt)
        self.parts.draw(cv, 0.1)
        if t > self.END - 0.5:
            darken(cv, max(0.0, (self.END - t) / 0.5))
        return 0, 0


DECISION_CUES = [(0.0, "lake-whispers"), (3.0, "sob-small")]


def _pxput(cv, x, y, c):
    import photo_fx
    photo_fx.put_pixel(cv, int(x), int(y), c)


def _shade_ell(cv, cx, cy, rx, ry, base, light=(-0.5, -0.7), rim=None):
    """A shaded ellipse in half-block pixels: a light from the upper left, a soft terminator, an optional rim colour."""
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            u, v = (x - cx) / float(rx), (y - cy) / float(ry)
            d = u * u + v * v
            if d <= 1.0:
                lit = max(0.0, -(u * light[0] + v * light[1]) * 0.9 + 0.35)
                c = mul(base, 0.45 + 0.75 * min(1.0, lit))
                if rim and d > 0.82:
                    c = mix(c, rim, 0.35)
                _pxput(cv, x, y, c)


def _draw_cup(cv, cx, cy, tilt, t):
    """A white porcelain cup in pixels (24 wide): rim, tea surface, shaded body, a handle; tilt sinks and tips it."""
    cx, cy = cx + int(tilt * 5), cy + int(tilt * 7)
    for y in range(0, 14):
        half = 12 - y // 3 - (1 if y > 10 else 0)
        for x in range(-half, half + 1):
            u = x / float(half + 1)
            c = mul((236, 232, 222), 0.62 + 0.38 * (0.5 - 0.5 * u) - 0.18 * (y / 14.0))
            _pxput(cv, cx + x, cy + y, c)
    for x in range(-12, 13):                                                                    # the rim and the tea inside it
        _pxput(cv, cx + x, cy - 1, (250, 246, 236))
        if abs(x) < 11:
            _pxput(cv, cx + x, cy, mix((120, 62, 26), (170, 98, 44), 0.5 + 0.5 * math.sin(x * 0.6 + t * 3)))
    for k in range(7):                                                                           # the handle: a ring on the right
        a = -1.4 + k * 0.45
        _pxput(cv, cx + 13 + int(math.cos(a) * 4), cy + 5 + int(math.sin(a) * 4), (214, 208, 198))
        _pxput(cv, cx + 14 + int(math.cos(a) * 4), cy + 5 + int(math.sin(a) * 4), (176, 170, 162))


def _draw_hand(cv, cx, cy, thumb_ang, skin=(214, 160, 128), scale=1.0, fingers_to=1):
    """An open right hand, palm up, lying to the right (drawn in pixels): shaded palm, four fingers with joints and nails, a thumb at thumb_ang (rad)."""
    s = scale
    _shade_ell(cv, cx, cy, 13 * s, 8 * s, skin, (-0.3, -0.8), mul(skin, 0.7))
    for f in range(4):
        y0 = cy - 6 * s + f * 4 * s
        ln = (11, 14, 15, 12)[f] * s
        for q in range(int(ln)):
            for d in range(int(3 * s)):
                c = mix(mul(skin, 0.8), skin, 0.5 + 0.5 * (1 - d / (3.0 * s)))
                if q in (int(ln * 0.4), int(ln * 0.75)):
                    c = mul(c, 0.7)                                                               # a joint
                _pxput(cv, cx + 11 * s + q, y0 + d, c)
        for d in range(int(2 * s)):                                                              # the nail
            _pxput(cv, cx + 11 * s + ln - 2, y0 + d, (236, 214, 204))
    for q in range(int(14 * s)):
        px, py = cx - 9 * s - math.cos(thumb_ang) * q, cy - 5 * s - math.sin(thumb_ang) * q
        for d in range(int(3 * s)):
            _pxput(cv, px, py + d, mix(mul(skin, 0.8), skin, 0.6))
    _shade_ell(cv, cx - 9 * s - math.cos(thumb_ang) * 14 * s, cy - 5 * s - math.sin(thumb_ang) * 14 * s, 2.2 * s, 2 * s, (240, 222, 210))


def _draw_kettle(cv, kx, ky, glow_k, t):
    """A dented enamel kettle on the stove: shaded body, lid with a knob, a curved spout, a bail handle, the flame ring under it."""
    _shade_ell(cv, kx, ky - 2, 11, 8, (96, 118, 148), (-0.5, -0.7), (60, 70, 90))
    _shade_ell(cv, kx, ky - 10, 6, 2.2, (124, 140, 164))
    _shade_ell(cv, kx, ky - 13, 1.6, 1.6, (30, 30, 36))
    for q in range(10):                                                                          # the spout
        _pxput(cv, kx + 9 + q, ky - 4 - int(q * 0.8) - (1 if q > 6 else 0), (130, 150, 176))
        _pxput(cv, kx + 9 + q, ky - 3 - int(q * 0.8), (96, 112, 138))
    for a in range(-20, 21):                                                                     # the bail
        ang = a / 20.0 * 1.4
        _pxput(cv, kx + math.sin(ang) * 11, ky - 11 - math.cos(ang) * 6, (40, 40, 48))
    for dx in range(-9, 10, 2):
        h = int(3 * glow_k * (0.6 + 0.4 * math.sin(t * 17 + dx)))
        for yy in range(h):
            _pxput(cv, kx + dx, ky + 6 - yy, mix((255, 120, 30), (120, 190, 255), 0.5 * (dx % 4 == 0)))


def _draw_knife(cv, x0, y0, x1, y1, grip):
    """A kitchen knife from tip (x0, y0) to the end of the handle (x1, y1): beveled blade with a bright edge and a glint, a wooden handle with two rivets."""
    import mika_fx
    L = math.hypot(x1 - x0, y1 - y0) or 1.0
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    for q in range(int(L * 0.7)):
        wdt = 1.0 + 2.6 * min(1.0, q / (L * 0.3))
        for d in range(-int(wdt), int(wdt) + 1):
            f = abs(d) / (wdt + 0.1)
            c = mix((246, 248, 255), (130, 136, 150), f)
            if d == 0 and q % 11 == 4:
                c = (255, 255, 255)                                                               # the glint running along the blade
            _pxput(cv, x0 + ux * q + nx * d, y0 + uy * q + ny * d, c)
    for q in range(int(L * 0.7), int(L)):
        for d in range(-2, 3):
            _pxput(cv, x0 + ux * q + nx * d, y0 + uy * q + ny * d, mix((70, 40, 24), (140, 90, 52), 0.5 + 0.5 * (1 - abs(d) / 3.0)))
    for r in (0.78, 0.9):
        _pxput(cv, x0 + ux * L * r, y0 + uy * L * r, (210, 200, 180))


class EndingLet:
    """let-it-live, as the text tells it: dawn, Noah and you walk away from the castle (0-5.5), the Nook and the tea (5.5-10: the cup, the steam, the smile,
    the arm that will not lift, the knife), the lake and the bench with the contented man in the hoodie (10-14)."""
    END = 19.0

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.body = Body(max(9, int(h * 0.3)), rng)
        self.parts = Particles(rng, 300)
        self.birds = [(rng.uniform(0, w), rng.uniform(2, h * 0.35), rng.uniform(3, 8)) for _ in range(9)]
        self.size = size_for(w, h)
        self.face = portrait_cells("noah_green", "small" if self.size else None) if self.size else None
        import mika_fx
        self.bench = mika_fx.BenchScene(w, h, rng, "intro")

    def dawn(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        hz = int(h * 0.62)
        k = smooth(t / 5.5)
        top = ramp([(0, (30, 20, 60)), (0.5, (150, 80, 100)), (1.0, (255, 190, 120))], k)
        low = ramp([(0, (70, 40, 70)), (1.0, (255, 220, 150))], k)
        for y in range(h):
            c = mix(top, low, min(1.0, y / float(hz))) if y < hz else mix((20, 26, 30), (60, 70, 60), (y - hz) / float(h - hz))
            for x in range(w):
                cv.ch[y * w + x], cv.fg[y * w + x], cv.bg[y * w + x] = " ", c, c
        sx, sy = int(w * 0.62), hz - int(2 + 10 * smooth(t / 5.5))
        for y in range(max(0, sy - 6), min(hz, sy + 6)):
            for x in range(sx - 14, sx + 15):
                if ((x - sx) / 2.0) ** 2 + (y - sy) ** 2 < 25:
                    cv.put(x, y, "@", (255, 245, 200), (255, 220, 140))
        glow(cv, sx, sy, 40, 14, (255, 190, 100), 0.35 * k)
        for x in range(w):
            top_y = hz - 1 - int(2 + 2 * math.sin(x * 0.07) + 1.5 * math.sin(x * 0.19))
            for y in range(top_y, hz + 1):
                cv.put(x, y, "A^"[(x + y) % 2], mix((18, 24, 22), (50, 58, 48), k * 0.4), (14, 18, 16))
        cx0 = int(w * 0.10)
        for i in range(24):                                                                # the castle, left behind
            for y in range(hz - 12 + (3 if i % 6 < 2 else 0), hz):
                cv.put(cx0 + i, y, "#", mix((12, 10, 16), (60, 50, 60), k * 0.5), (10, 8, 12))
        for tower in (0, 23):
            for y in range(hz - 20, hz - 11):
                for xx in range(cx0 + tower - 2, cx0 + tower + 3):
                    cv.put(xx, y, "#", mix((12, 10, 16), (60, 50, 60), k * 0.5), (10, 8, 12))
        for x in range(w // 3, w, 9):                                                      # the dark windows of Luenen
            cv.put(x, hz - 3, "o", (30, 30, 40))
        nx = int(cx0 + 14 + smooth(t / 5.5) * (w * 0.55 - cx0))
        grid = self.body.render(0.0)
        blit_grid(cv, grid, nx - self.body.wf // 2, hz + 1 - self.body.hf)                 # Noah, held up beside you, clinging
        for bx, by, sp in self.birds:
            x, y = int((bx + t * sp) % w), int(by + math.sin(t * 2 + bx) * 1.5)
            cv.put(x, y, "v^"[int(t * 6 + bx) % 2], (30, 24, 34))

    def kitchen(self, cv, t, dt):
        """5.5-9.8: the Nook. The kettle goes on and steams (5.5-7), Noah hands the cup over (7-8.3) and smiles over the rim, the arm will not lift it (8.3-9.8)."""
        import photo_fx
        w, h, rng = self.w, self.h, self.rng
        tt = t - 5.5
        cv.clear((10, 8, 6))
        for y in range(2 * h):                                                              # warm wall, the table top
            for x in range(w):
                base = mix((34, 24, 18), (22, 14, 12), y / float(2 * h)) if y < 1.3 * h else mix((70, 44, 28), (46, 28, 18), (y - 1.3 * h) / (0.7 * h))
                photo_fx.put_pixel(cv, x, y, mul(base, 0.85 + 0.25 * _hash(x // 3, y // 2, 4)))
        glow(cv, int(w * 0.35), int(h * 0.50), 46, 16, (255, 190, 100), 0.20)               # one lamp
        kx, ky = int(w * 0.14), int(h * 0.58)                                               # the kettle on the stove: it goes on, it begins to steam
        _draw_kettle(cv, kx, 2 * ky, smooth(tt / 0.8), t)
        glow(cv, kx, ky + 2, 14, 3, (255, 120, 40), 0.35 * smooth(tt / 0.8))
        if tt > 0.8 and rng.random() < 0.9:
            self.parts.add(kx + 11, ky - 5, rng.uniform(1, 3), -rng.uniform(3, 8), 2.0, "smoke", -0.3)
        hand = smooth((tt - 1.5) / 1.3)                                                       # Noah's arm hands the cup across the table
        cx0, cy = int(w * 0.62 - hand * w * 0.30), int(h * 0.64)
        tilt = smooth((tt - 2.8) / 1.5)                                                       # after the third sip the arm will not lift the cup: it sinks, tips
        for q in range(int(w * 0.80) - cx0):                                                  # the arm: a shaded sleeve and wrist coming from the right
            top = 2 * cy + 2 + int(q * 0.02)
            for d in range(7):
                _pxput(cv, cx0 + 14 + q, top + d, mix((84, 110, 80), (40, 60, 44), d / 7.0) if q > 10 else mix((222, 168, 138), (150, 104, 84), d / 7.0))
        _draw_cup(cv, cx0, 2 * cy, tilt, t)
        for k in range(2 + int(tilt * 3)):
            if rng.random() < 0.6:
                self.parts.add(cx0 + rng.randint(-3, 3), cy - 1, rng.uniform(-1, 1), -rng.uniform(1, 3), 2.0, "smoke", -0.3)
        if tilt > 0.4:                                                                        # the tea runs over the table and the edge
            for x in range(cx0 - 10, cx0 + 12):
                _pxput(cv, x, 2 * cy + 18 + (x % 2), (150, 90, 40))
        if self.face:                                                                         # his small shy smile over the rim; the picture goes soft as the legs go
            H, W = len(self.face), len(self.face[0])
            ox, oy = int(w * 0.58), max(0, (h - 1 - H) // 2)
            soft = smooth((tt - 2.8) / 2.5)
            for y in range(H):
                for x in range(W):
                    ch, fg, bg = self.face[y][x]
                    cv.put(ox + x + int(math.sin(t * 3 + y) * 2 * soft), oy + y, ch, mul(fg, 0.9 - 0.4 * soft), mul(bg, 0.9 - 0.4 * soft))

    def floor(self, cv, t, dt):
        """9.8-15: you slide off the chair (the picture drops), the floor is warm; he kneels, takes your hand and bends the thumb back until it snaps (11.4);
        the knife comes out from under the blanket (12.2), the click (12.7), and he takes his time: the shadow of his arm rises and falls on the wall."""
        import photo_fx
        w, h, rng = self.w, self.h, self.rng
        fall = smooth((t - 9.8) / 0.7)
        if fall < 1.0:
            self.kitchen(cv, min(t, 9.7), dt)
            ch, fg, bg = cv.snapshot()
            dy = int(h * fall)
            for y in range(h):                                                               # everything slides up out of the frame, the floor boards come in
                src = y + dy
                for x in range(w):
                    i = y * w + x
                    if src < h:
                        j = src * w + x
                        cv.ch[i], cv.fg[i], cv.bg[i] = ch[j], fg[j], bg[j]
                    else:
                        cv.ch[i], cv.fg[i], cv.bg[i] = " ", (60, 40, 28), mix((44, 28, 20), (70, 46, 30), _hash(x // 5, y, 2))
            return
        cv.clear((10, 7, 5))
        for y in range(2 * h):                                                                # floor planks, warm against your cheek
            plank = (y // 9) % 2
            for x in range(w):
                c = mul(mix((88, 56, 34), (60, 38, 24), y / float(2 * h)), 0.85 + 0.3 * _hash(x // 7, y, 6 + plank))
                if y % 9 == 0:
                    c = mul(c, 0.5)
                photo_fx.put_pixel(cv, x, y, c)
        glow(cv, int(w * 0.3), int(h * 0.3), 50, 16, (255, 190, 100), 0.16)
        cx, cy = int(w * 0.38), int(h * 0.52)
        bend = smooth((t - 10.8) / 0.6)                                                       # the thumb is bent back, slowly, then it snaps
        ang = 0.5 + 2.1 * bend + (0.25 * math.sin(t * 40) if 10.8 < t < 11.4 else 0.0)
        _draw_hand(cv, cx, 2 * cy, ang)                                                       # your hand open on the boards
        hx, hy = cx - 9 - math.cos(ang) * 14, 2 * cy - 5 - math.sin(ang) * 14
        _shade_ell(cv, hx - 3, hy - 2, 6, 4, (232, 200, 180), (-0.4, -0.8))                    # his small hand closes round the thumb
        for k in range(3):
            _pxput(cv, hx + 2 + k, hy + 1, (206, 170, 150))
        if self.face:                                                                         # he kneels beside you: the small face in the corner, close
            H, W = len(self.face), len(self.face[0])
            ox, oy = int(w * 0.66), max(0, (h - H) // 2 - 2)
            for y in range(H):
                for x in range(W):
                    ch, fg, bg = self.face[y][x]
                    cv.put(ox + x, oy + y, ch, mul(fg, 0.85), mul(bg, 0.85))
        if 11.4 <= t < 11.8:                                                                  # the snap
            flash(cv, (255, 255, 255), 0.5 * (1 - (t - 11.4) / 0.4))
            for q in range(4):
                cv.put(cx - 18 + q * 3, cy - 6, "/\\"[q % 2], (255, 255, 255))
        if t >= 12.2:                                                                         # the knife comes out from under the blanket: one white streak, then it rests in his hand
            a = smooth((t - 12.2) / 0.2)
            kx0, ky0 = int(w * 0.52), int(h * 1.5)
            _draw_knife(cv, kx0 - 34 * a + 20, ky0 - 14 * a - 10, kx0 + 18 + 10 * a, ky0 + 4 - 8 * a, 1.0)
            flash(cv, (255, 255, 255), max(0.0, 1 - (t - 12.2) / 0.15) * 0.5)
        if t >= 12.7:                                                                         # click. then he takes his time: his shadow, careful, up and down the wall
            if t < 12.9:
                flash(cv, (255, 255, 255), 0.35)
            k = (t - 12.9) * 0.7
            for i in range(3):
                ph = (t * 1.3 + i * 0.7) % 1.0
                x = int(w * (0.12 + 0.22 * i)) + int(math.sin(ph * 6.28) * 3)
                for q in range(int(10 * abs(math.sin(ph * 3.14)))):
                    cv.put(x, int(h * 0.25) + q, "|", (14, 8, 6), (6, 4, 4))
            for i in range(int(max(0.0, k) * 12)):
                x = int(w * (0.1 + 0.8 * _hash(i, 3))) % w
                cv.put(x, int(h * (0.55 + 0.35 * _hash(i, 5))), "~", (130, 10, 14), (60, 4, 8))

    def draw(self, cv, t, dt):
        w, h = self.w, self.h
        if t < 5.5:
            self.dawn(cv, t, dt)
        elif t < 15.0:
            self.floor(cv, t, dt) if t >= 9.8 else self.kitchen(cv, t, dt)
        else:                                                                              # three days later: the lake, the double bench, a man in a hoodie in the sun
            r = self.bench.draw(cv, 3.0 + (t - 15.0) * 0.5, dt)
            if t > 17.4:                                                                   # he sighs with contentment: a long breath of smoke
                if self.rng.random() < 0.5:
                    self.parts.add(w // 2 + 8, int(h * 0.45), 4, -2, 3.0, "smoke", -0.2)
        self.parts.step(dt)
        self.parts.draw(cv, 0.0)
        if 5.3 < t < 5.8 or 14.8 < t < 15.3:
            darken(cv, 0.0)                                                                # a cut to black on each time jump
        if t > self.END - 1.0:
            darken(cv, max(0.0, self.END - t))
        return 0, 0


LET_CUES = [(0.0, "night-crickets"), (4.0, "lake-calm"), (6.0, "lake-calm"), (9.0, "glass-crack"), (11.4, "bone-crack-1"), (12.2, "knife-draw"), (12.7, "bone-crack-1"), (15.3, "lake-whispers")]


class EndingSlaughter:
    """slaughter-it, as the text tells it: the cellar, Noah on his knees with his head bowed, the iron bar, eleven blows (shadows on the wall, blood, the
    ring of iron on bone), the head comes away and rolls; then the town, every window light goes out at once."""
    END = 15.0

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.body = Body(max(9, int(h * 0.42)), rng)
        self.parts = Particles(rng, 900)
        self.blows = [2.2 + 0.62 * k for k in range(11)]
        self.windows = [(rng.randrange(4, w - 4), rng.randrange(int(h * 0.3), h - 4)) for _ in range(w // 3)]

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        n = sum(1 for b in self.blows if b <= t)
        if t >= 10.8:                                                                      # the town: every candle goes out at once
            cv.clear((4, 4, 10))
            out = t >= 12.0
            for x, y in self.windows:
                if not out or (t < 12.4 and rng.random() < 0.3):
                    cv.put(x, y, "o", (255, 200, 90))
            if out:
                flash(cv, (0, 0, 0), 0.0)
            cv.text(w // 2 - 12, 2, "", (200, 200, 200))
            self.parts.step(dt)
            self.parts.draw(cv, 0.0)
            if t > self.END - 1.0:
                darken(cv, max(0.0, self.END - t))
            return 0, 0
        cv.clear((12, 10, 14))
        for y in range(h):                                                                  # the cellar: cold stone, one lamp
            for x in range(w):
                cv.bg[y * w + x] = mix((14, 12, 18), (34, 30, 38), 0.4 + 0.3 * math.sin(x * 0.2) * math.sin(y * 0.5))
                if (x // 14 + y // 4) % 2 == 0 and x % 14 == 0:
                    cv.put(x, y, "|", (30, 26, 34))
        glow(cv, w // 2, int(h * 0.4), 50, 16, (190, 200, 255), 0.18)
        grid = self.body.render(0.0)
        cut = int(len(grid) * 0.58)                                                         # on his knees: the legs are folded under him
        grid = grid[:cut] + grid[cut::2]
        hf = len(grid)
        nx, ny = w // 2 - (int(w * 0.08) if w >= 160 else 0), h - 2 - hf - (6 if w < 160 else 0)      # keeps the right speech column / the bottom strip free
        head_rows = int(self.body.hf * 11 / 36.0)
        hit = max([math.exp(-(t - b) / 0.12) for b in self.blows if b <= t] + [0.0])
        nod = 0.6 * max(0.0, math.sin((t - 0.2) * 5.0)) if 0.2 < t < 1.0 else 0.0               # he looks at the bar, at you, and nods very slowly
        sh_ = int(round(3.4 * smooth((t - 1.0) / 1.0) + nod))                                     # then he bows his head to make it easy
        if sh_ > 0 and t < self.blows[-1] + 0.15:
            for yy in range(head_rows - 1, sh_ - 1, -1):
                grid[yy] = grid[yy - sh_]
            for yy in range(sh_):
                grid[yy] = [None] * len(grid[0])
        if t < self.blows[-1] + 0.15:                                                              # the iron bar in your hands: held low, then raised for every blow
            raised = smooth((t - 1.6) / 0.5)
            bx0, by0 = nx + 22 + int(8 * raised), ny + hf - 6 - int(16 * raised)
            swing = 0.0
            for b in self.blows:
                if b <= t < b + 0.35:
                    swing = math.sin((t - b) / 0.35 * 3.14)
            for x, y in walk(bx0, by0, bx0 - 12 - int(10 * swing), by0 - 14 + int(10 * swing)):
                cv.put(x, y, "#", (150, 150, 162), (60, 60, 70))
        # eleven blows: the shadow of the bar swings down the wall, blood, sparks where it skids off bone
        for i, b in enumerate(self.blows):
            if b <= t < b + 0.35:
                f = (t - b) / 0.35
                ang = -1.1 + 2.0 * f
                x0, y0 = nx + int(math.cos(ang) * 50), ny - 5 + int(math.sin(ang) * 30) - 30
                for x, y in walk(x0, y0, nx + 2, ny + head_rows - 2):
                    cv.put(x, y, "#", (6, 4, 8), (3, 2, 4))
            if t >= b and not getattr(self, "_b%d" % i, False):
                setattr(self, "_b%d" % i, True)
                self.parts.burst(nx, ny + head_rows, 18 + 4 * i, "blood", 20, 1.0, 22.0, up=6)
                if i in (2, 4, 6):
                    self.parts.burst(nx, ny + head_rows, 10, "spark", 18, 0.5, 10.0)       # iron on bone
        stains = n / 11.0
        for y, row in enumerate(grid):
            for x, c in enumerate(row):
                if c is not None and y < head_rows + 5 and _hash(x, y, 4) < stains * 0.5:
                    row[x] = ("#", (190, 20, 24), (90, 4, 8))
        torn = t >= self.blows[-1] + 0.15
        if torn:                                                                            # the head comes away and rolls once
            hg = grid[:head_rows]
            body_grid = [[None] * len(grid[0]) for _ in range(head_rows)] + grid[head_rows:]
            f = min(1.0, (t - self.blows[-1]) / 1.4)
            blit_grid(cv, body_grid, nx - self.body.wf // 2, ny)
            blit_grid(cv, hg, nx - self.body.wf // 2 + int(f * 24), ny + int((hf - head_rows) * (f ** 2)) + int(math.sin(f * 9) * 2))
        else:
            sh = int(hit * 3)
            blit_grid(cv, grid, nx - self.body.wf // 2 + int(rng.uniform(-1, 1) * sh), ny + (1 if hit > 0.3 else 0))
        # the pool spreads
        for x in range(nx - int(3 + 22 * stains), nx + int(3 + 22 * stains)):
            cv.put(x, h - 2, "~", (150, 10, 14), (70, 4, 8))
        self.parts.step(dt)
        self.parts.draw(cv, 0.2)
        flash(cv, (255, 255, 255), hit * 0.25)
        return jolt(rng, hit * 3.0)


SLAUGHTER_CUES = [(2.2, "iron-bar-hit"), (2.9, "bone-crack-1"), (3.5, "iron-bar-hit"), (4.1, "bone-crack-2"), (4.7, "iron-bar-hit"), (5.4, "bone-crack-1"),
                  (6.0, "iron-bar-hit"), (6.6, "bone-crack-2"), (7.3, "iron-bar-hit"), (7.9, "bone-crack-1"), (8.5, "iron-bar-hit"), (9.1, "blood-spurt"),
                  (10.8, "lake-calm"), (12.0, "sob-small")]     # eleven blows; the iron rings on the bone; then the town goes quiet


class EndingThree:
    """ending-3, as the text tells it: three people kill each other inside one small body (the three colours fight, claw, die one after the other, the quiet
    one last); what is left sits with red holes for eyes and says only 'ah'."""
    END = 15.0
    VOICES = ["MINE!", "No, MINE!", "Let me OUT!", "mine", "LET ME OUT", "no", "MINE"]

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.size = "big" if h >= 31 and w >= 60 else "small" if h >= 16 and w >= 32 else None
        self.parts = Particles(rng, 900)
        self.words = []

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((8, 4, 8))
        cx = w // 2
        sh = 28 if self.size == "big" else 14
        top = max(0, (h - 1 - sh) // 2)
        deaths = {0: 5.0, 1: 7.0, 2: 9.0}                                                     # red, yellow, green die (green = the quiet one, last)
        spr = anim_sprite("fusion", ("strike", "hurt", "windup")[int(t * 9) % 3] if t < 9.8 else "collapse", int(t * 8), self.size) if self.size else None
        shake = 0.0
        if spr and t < 10.0:
            for g in (0, 1, 2):
                dead = t >= deaths[2 - g] if False else t >= {0: 9.0, 1: 7.0, 2: 5.0}[g]
                grid = _group_grid(spr, g)
                a = 0.15 if dead else 1.0
                dx = int(rng.uniform(-2, 2) * (0 if dead else 1 + 1.5 * smooth(t / 3.0)))
                blit_grid(cv, [[(c if c is None else (c[0], mul(c[1], a), mul(c[2], a))) for c in r] for r in grid], cx - len(spr[0]) // 2 + dx, top + (2 if dead else 0))
            shake = 1.2 + 1.4 * smooth(t / 4.0)
            for _ in range(3):                                                                # the fingernails: red strokes down his own face
                if rng.random() < 0.4 * smooth((t - 2.0) / 2.0):
                    x = cx + rng.randint(-8, 8)
                    for k in range(rng.randint(3, 8)):
                        cv.put(x, top + 6 + k, "|", (200, 20, 20))
            if rng.random() < 0.6 * smooth((t - 3.0) / 2.0):
                self.parts.burst(cx + rng.randint(-6, 6), top + 8 + rng.randint(0, 6), 5, "blood", 12, 0.9, 20.0)
            ey_, exs = top + int(sh * 0.30), (cx - 3, cx + 3)
            if t >= 3.6:                                                                      # his thumbs go into his own eyes, a soft pop, a second: red holes stay
                for j, ex in enumerate(exs):
                    pop = 3.9 + 0.5 * j
                    if t < pop:
                        for q in range(3):
                            cv.put(ex + (-q if j == 0 else q) * 1 - (1 if j == 0 else -1) * 2, ey_ + 1, "=", (226, 190, 170))
                    else:
                        cv.put(ex, ey_, "O", (255, 40, 30), (110, 0, 0))
                        cv.put(ex, ey_ + 1, "|", (200, 20, 20))
                        if pop <= t < pop + 0.1:
                            flash(cv, (255, 60, 40), 0.35)
                            self.parts.burst(ex, ey_, 8, "blood", 10, 0.8, 16.0)
            for tk in (5.0, 7.0, 9.0):                                                         # a death: a ring in its colour
                if tk <= t < tk + 0.6:
                    col = {5.0: (255, 70, 70), 7.0: (245, 215, 70), 9.0: (90, 235, 120)}[tk]
                    r = (t - tk) * 40
                    for a2 in range(0, 360, 3):
                        cv.put(int(cx + math.cos(math.radians(a2)) * r * 2), int(top + sh // 2 + math.sin(math.radians(a2)) * r * 0.6), "O", mul(col, 1 - (t - tk) / 0.6))
                    flash(cv, col, 0.25 * (1 - (t - tk) / 0.6))
            if rng.random() < 0.18 * min(1.0, t / 2.0) and t < 9.0:                           # the voices, all over each other
                self.words.append([rng.randrange(max(1, w - 12)), rng.randrange(1, max(2, h - 5)), t, rng.choice(self.VOICES), rng.choice([(255, 70, 70), (245, 215, 70), (90, 235, 120)])])
            for x, y, t0, text, col in self.words:
                if 0 <= t - t0 < 1.0:
                    cv.text(x, y, text, mul(col, 1 - (t - t0)))
        else:                                                                              # silence: a small shape with holes where the eyes were
            k = smooth((t - 10.0) / 1.2)
            sm = anim_sprite("green", "collapse", 0, "small" if self.size else None) if self.size else None
            if sm:
                bx = cx - len(sm[0]) // 2
                by = h - 2 - len(sm)
                blit_grid(cv, [[(c if c is None else (c[0], mul(c[1], 0.45 * k), mul(c[2], 0.45 * k))) for c in r] for r in sm], bx, by)
                ey = by + int(len(sm) * 0.40)
                for ex in (bx + int(len(sm[0]) * 0.36), bx + int(len(sm[0]) * 0.60)):
                    for dx in (0, 1, 2):
                        cv.put(ex + dx, ey, " ", None, (120 * k, 0, 0))
                        cv.put(ex + dx, ey + 1, " ", None, (80 * k, 0, 0))
                for j in range(int(6 * k)):
                    cv.put(bx + int(len(sm[0]) * 0.48), ey + 2 + j, "|", (150, 10, 14))
                for q in range(3):
                    mx, my = cx + int(math.sin(t * 6 + q * 2) * 8) + (q - 1) * 6, by + len(sm) - 3 + int(math.cos(t * 7 + q) * 2)
                    cv.put(mx, my, "\\/"[q % 2], (130, 130, 140))
            if t > 11.5:
                cv.text(cx - 6, h - 4, "ah.  ah.  ah." if int(t * 1.5) % 2 else "ah.  ah.", mul((190, 190, 200), min(1.0, (t - 11.5) / 1.0)))
        self.parts.step(dt)
        self.parts.draw(cv, 0.3)
        if t > self.END - 1.2:
            darken(cv, max(0.0, (self.END - t) / 1.2))
        return jolt(rng, shake + shake_at(t, [(5.0, 3.0), (7.0, 3.0), (9.0, 3.5)], 1.0, 0.3))


THREE_CUES = [(0.0, "scream-distorted-1"), (1.5, "scream-choir"), (3.5, "bone-crack-1"), (4.4, "blood-spurt"), (5.0, "scream-fire"), (7.0, "scream-distorted-2"),
              (9.0, "scream-falling-2"), (10.0, "sob-small"), (11.5, "gurgle-breath")]      # three die inside one body; then he says ah


def beat_scene(which):
    """The 50% / 20% beats as 3.5 s scenes: Noah's portrait cracks (a hairline at 50%, a shattering with red veins at 20%) and the colour tips."""
    return lambda w, h, r: Beat(w, h, r, which)


class Beat:
    END = 3.5

    def __init__(self, w, h, rng, which=50):
        self.w, self.h, self.rng, self.which = w, h, rng, int(which)
        self.size = size_for(w, h)
        self.p = portrait_cells("noah_red" if self.which == 20 else "noah_yellow", self.size) if self.size else None
        self.cr = crack_cells(w // 2, h // 2, rng, 5 if self.which == 50 else 14, 30 if self.which == 50 else 60)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((8, 2, 2))
        k = smooth((t - 0.3) / 1.6)
        if self.p:
            H, W = len(self.p), len(self.p[0])
            ox, oy = (w - W) // 2, max(0, (h - 1 - H) // 2)
            for y in range(H):
                for x in range(W):
                    ch, fg, bg = self.p[y][x]
                    dx = int(_hash(x // 6, y // 4) * 4 * k * (1 if self.which == 20 else 0.3)) - 1
                    cv.put(ox + x + dx, oy + y, ch, mix(fg, (255, 50, 50), 0.3 * k), mul(bg, 1 - 0.3 * k))
        for x, y, c in self.cr[:int(len(self.cr) * k)]:
            cv.put(x, y, c, (255, 240, 230), (170, 10, 10))
        if self.which == 20:
            for j in range(int(40 * k)):
                cv.put(rng.randrange(w), rng.randrange(h), rng.choice("|/\\"), (255, 40, 40))
        flash(cv, (255, 255, 255), max(0.0, 1 - t / 0.12) * 0.9)
        if t > self.END - 0.4:
            darken(cv, max(0.0, (self.END - t) / 0.4))
        return jolt(rng, shake_at(t, [(0.0, 3.0), (1.9, 1.5 if self.which == 20 else 0.6)], 1.0, 0.25))


BEAT_CUES = [(0.0, "impact-boom-huge"), (0.1, "glass-crack"), (1.9, "bone-crack-1")]     # audio agent: tune


NAMED = {   # name: (factory, seconds, caption key or None, cues)
    "intro": (IntroNoise, IntroNoise.END, None, INTRO_CUES),
    "phase2": (lambda w, h, r: PhaseMerge(w, h, r, 2), PhaseMerge.END, None, PHASE_CUES),
    "phase3": (lambda w, h, r: PhaseMerge(w, h, r, 3), PhaseMerge.END, None, PHASE_CUES),
    "phase4": (lambda w, h, r: PhaseMerge(w, h, r, 4), PhaseMerge.END, None, PHASE_CUES),
    "beat50": (beat_scene(50), Beat.END, None, BEAT_CUES),
    "beat20": (beat_scene(20), Beat.END, None, BEAT_CUES),
    "defeat": (DefeatScene, DefeatScene.END, "cine.defeat.lines", DEFEAT_CUES),
    "decision": (DecisionScene, DecisionScene.END, "cine.decision.lines", DECISION_CUES),
    "ending-let": (EndingLet, EndingLet.END, "cine.ending_let.lines", LET_CUES),
    "ending-slaughter": (EndingSlaughter, EndingSlaughter.END, "cine.ending_slaughter.lines", SLAUGHTER_CUES),
    "ending-3": (EndingThree, EndingThree.END, "cine.ending_3.lines", THREE_CUES),
}


ENDING_SID = {"ending-let": "k7.ending_let", "ending-slaughter": "k7.ending_slaughter", "ending-3": "k7.ending_3"}
ENDING_ANCHORS = {   # scene time of every block of the ending text, in order: the picture shows what the block says at exactly that moment
    "ending-let": [2.5, 5.6, 7.0, 7.9, 9.0, 10.9, 11.5, 11.9, 12.4, 12.8, 14.0, 15.4, 16.2, 17.6],
    "ending-slaughter": [1.0, 1.5, 1.9, 2.3, 2.35, 2.7, 2.95, 3.3, 3.5, 3.55, 4.3, 5.2, 6.8, 9.3, 10.2, 11.0, 12.2],
    "ending-3": [0.6, 1.3, 2.0, 2.6, 3.0, 3.4, 4.3, 6.0, 10.0, 11.0, 11.6, 12.1, 12.6, 13.6]}
ENDING_NOAH_AT = {"ending-let": (0.74, 0.40), "ending-slaughter": (0.5, 0.50), "ending-3": (0.5, 0.42)}
SPEAKER = {"NOAH": "noah", "NOAH (sweet)": "noah", "NOAH (cold)": "noah2", "NOAH (dark)": "noah3"}


def ending_boxes(name, text, default_who="noah"):
    """The ending's story text as speech boxes: (who, text, anchor); stage directions '(...)', narration and '{{sound}}' words go on the caption strip."""
    out = []
    for blk in [b.strip() for b in text.split("\n\n") if b.strip()]:
        m = re.match(r"^(NOAH(?: \((?:sweet|cold|dark)\))?):\s*(.*)$", blk, re.S)
        if m:
            who = SPEAKER[m.group(1)] if m.group(1) != "NOAH" else ("noah3" if name != "ending-let" else default_who)
            out.append((who, m.group(2).strip(), ENDING_NOAH_AT[name]))
            continue
        blk = re.sub(r"\{\{(.+?)\}\}", lambda g: g.group(1).upper(), blk)
        if blk.startswith("(") and blk.endswith(")"):
            blk = blk[1:-1]
        out.append(("narrator", blk, None))
    return out


def run_ending(ctx, name, seed=1):
    """An ending: the whole story text as bubbles and captions ON its animation, each block at the scene time where the picture shows it (ENDING_ANCHORS)."""
    factory, seconds, key, cues = NAMED[name]
    with open(os.path.join(G_HERE, "story", "story.json"), encoding="utf-8") as fh:
        text = json.load(fh)[ENDING_SID[name]]["text"]
    boxes = ending_boxes(name, text)
    anchors = ENDING_ANCHORS[name]
    if len(anchors) != len(boxes):
        anchors = [0.5 + (seconds - 1.5) * i / max(1, len(boxes) - 1) for i in range(len(boxes))]
    pending = sorted(cues)
    frames = 0
    for (who, txt, anc), t0 in zip(boxes, anchors):
        while pending and pending[0][0] <= t0:
            ctx.sfx(pending.pop(0)[1])
        frames += 1
        ctx.dialog(factory, [(who, txt, anc)], t0, 1.4, seed=seed)
    for _, cue in pending:
        ctx.sfx(cue)
    return frames


def run_named(ctx, name, seed=1):
    """Play one of the NAMED scenes on ctx (a mika_ending.Ctx-like object: size, out, sleep, sfx, fps, lines). Returns the frames drawn."""
    if name in ENDING_SID and hasattr(ctx, "dialog"):
        return run_ending(ctx, name, seed)
    factory, seconds, key, cues = NAMED[name]
    lines = ctx.lines(key) if key else []
    lines = [l for l in lines if l]
    return G.play(ctx, factory, seconds, G.spread(lines, 0.8, seconds - 0.8) if lines else [], cues, seed=seed)
