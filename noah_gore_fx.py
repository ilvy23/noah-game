"""noah_gore_fx.py - the full-screen cinematics of Mika's ending, drawn in truecolor ASCII and sent as diffs (no curses, no input).

    play(ctx, scene, seconds, captions, cues)  - the frame loop every scene uses: scene.draw(cv, t) paints a Canvas, the runner adds the
                                                 caption bar, the shake and the sound cues, then writes ONLY the changed cells.
    SlashScene   (25 s)  Noah lunges and cuts; the cuts heal; fury -> disbelief -> fear; the last strike bounces off a faint glow.
    AwakenScene  (32 s)  one faint dot becomes the whole screen: teal/white/green grade, rising pulse, edge motes, the floor starts to crack.
    BurnScene    (38 s)  the floor opens, Noah burns (fire automaton, blisters, bone, hair, eyes, jaw, hands), the ground takes him, he falls.
Judge one quickly:  python3 play.py --mika-ending --only slash|awake|burn   (needs a truecolor terminal, 120x40 or bigger is best; Ctrl-C leaves).
Everything is a pure function of t and the seed (random.Random), so a test can run a scene headless with a fake sleep.
Content: stylised but explicit gore on a monster; nothing here sexualises Noah, nothing executes anything or touches a file.
"""
import chain
import math
import random
import textwrap
import time

import portraits

FPS = 15
BLACK = (0, 0, 0)
SYNC_ON, SYNC_OFF = "\033[?2026h", "\033[?2026l"          # synchronized output: no tearing where supported, ignored elsewhere


# ---------------------------------------------------------------- colour helpers
def clamp(v):
    return 0 if v < 0 else 255 if v > 255 else int(v)


def mix(a, b, t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def mul(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def ramp(stops, t):
    """Piecewise linear colour ramp: stops = [(pos, rgb), ...] sorted by pos."""
    if t <= stops[0][0]:
        return stops[0][1]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            return mix(c0, c1, (t - p0) / (p1 - p0))
    return stops[-1][1]


def smooth(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


def _q(v):
    return min(255, (clamp(v) + 3) // 6 * 6)               # 43 levels per channel: far fewer changed cells and shorter escape codes


FIRE_STOPS = [(0.0, (0, 0, 0)), (0.12, (50, 0, 0)), (0.30, (150, 15, 0)), (0.50, (235, 70, 0)), (0.70, (255, 150, 20)),
              (0.88, (255, 225, 110)), (1.0, (255, 255, 225))]
FIRE_PAL = [ramp(FIRE_STOPS, i / 63.0) for i in range(64)]


def fire_rgb(h):
    return FIRE_PAL[max(0, min(63, int(h * 63)))]


# ---------------------------------------------------------------- canvas with diff rendering
class Canvas:
    """w x h cells, three flat lists (glyph, foreground rgb, background rgb). put() clips, so a scene can never write off screen."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.clear()

    def clear(self, bg=BLACK):
        n = self.w * self.h
        self.ch, self.fg, self.bg = [" "] * n, [bg] * n, [bg] * n

    def put(self, x, y, ch, fg=None, bg=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.ch[i] = ch
            if fg is not None:
                self.fg[i] = fg
            if bg is not None:
                self.bg[i] = bg

    def text(self, x, y, s, fg, bg=None):
        for k, c in enumerate(s):
            if c != " " or bg is not None:
                self.put(x + k, y, c, fg, bg)

    def light(self, x, y, rgb, a=1.0, fg_too=0.5):
        """Add coloured light to a cell (background fully, the glyph colour partly)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.bg[i] = add(self.bg[i], rgb, a)
            self.fg[i] = add(self.fg[i], rgb, a * fg_too)

    def tint(self, x, y, rgb, a):
        """Blend the cell towards a colour."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.bg[i] = mix(self.bg[i], rgb, a)
            self.fg[i] = mix(self.fg[i], rgb, a)

    def snapshot(self):
        return self.ch[:], self.fg[:], self.bg[:]

    def shifted(self, dx, dy):
        """The same picture moved by whole cells (a shake); the uncovered edge is black."""
        if not dx and not dy:
            return self
        o = Canvas(self.w, self.h)
        w, h = self.w, self.h
        for y in range(h):
            sy = y - dy
            if not 0 <= sy < h:
                continue
            a, b = max(0, dx), min(w, w + dx)
            if b <= a:
                continue
            s0, d0 = sy * w + a - dx, y * w + a
            n = b - a
            o.ch[d0:d0 + n], o.fg[d0:d0 + n], o.bg[d0:d0 + n] = self.ch[s0:s0 + n], self.fg[s0:s0 + n], self.bg[s0:s0 + n]
        return o

    def cells(self):
        return list(zip(self.ch, [(_q(c[0]), _q(c[1]), _q(c[2])) for c in self.fg], [(_q(c[0]), _q(c[1]), _q(c[2])) for c in self.bg]))

    def diff(self, prev, truecolor=True):
        """Escape codes that turn the previous cell list into this canvas (prev None = everything). Returns (text, cells)."""
        cur, w = self.cells(), self.w
        out = [SYNC_ON]
        fg_s = bg_s = None
        for y in range(self.h):
            base = y * w
            row = cur[base:base + w]
            if prev is not None and row == prev[base:base + w]:
                continue
            old = prev[base:base + w] if prev is not None else None
            x = 0
            while x < w:
                if old is not None and row[x] == old[x]:
                    x += 1
                    continue
                out.append("\033[%d;%dH" % (y + 1, x + 1))
                gap = 0
                while x < w and gap <= 3:                          # bridge up to 3 unchanged cells instead of a new cursor jump
                    if old is not None and row[x] == old[x]:
                        gap += 1
                    else:
                        gap = 0
                    ch, f, b = row[x]
                    if f != fg_s:
                        out.append(("\033[38;2;%d;%d;%dm" % f) if truecolor else "\033[38;5;%dm" % portraits._256(*f))
                        fg_s = f
                    if b != bg_s:
                        out.append(("\033[48;2;%d;%d;%dm" % b) if truecolor else "\033[48;5;%dm" % portraits._256(*b))
                        bg_s = b
                    out.append(ch)
                    x += 1
        out.append("\033[0m" + SYNC_OFF)
        return "".join(out), cur


# ---------------------------------------------------------------- particles
KINDS = {  # kind: (colour at birth, colour at death, glyphs)
    "blood": ((215, 12, 18), (70, 0, 8), ",.'`;:*o"),
    "spark": ((255, 235, 170), (200, 20, 10), ".+*'`"),
    "ember": ((255, 190, 70), (110, 20, 5), ".'`*,"),
    "steel": ((235, 240, 255), (110, 120, 140), "/\\-|+*"),
    "debris": ((150, 120, 100), (40, 30, 30), "#%&@o"),
    "ash": ((150, 140, 135), (30, 28, 28), ".,'`:"),
    "mote": ((200, 255, 235), (20, 120, 110), ".'`*+"),
    "fat": ((250, 225, 150), (140, 70, 20), "o.:,"),
    "bone": ((240, 232, 205), (120, 100, 85), "/\\-|l"),
    "wax": ((235, 140, 120), (130, 40, 30), ".:,o"),
    "pg": ((120, 255, 140), (10, 60, 20), ".*'+"), "py": ((255, 230, 90), (70, 50, 0), ".*'+"), "pr": ((255, 80, 80), (60, 0, 0), ".*'+"),
    "dust": ((235, 225, 190), (40, 40, 56), ".'`,"),
    "gold": ((255, 228, 150), (110, 70, 24), ".'*`,"),
    "smoke": ((200, 200, 208), (36, 38, 48), "~'`.,"),
    "bubble": ((200, 235, 255), (60, 100, 140), "o.O"),
    "soul": ((190, 215, 255), (40, 50, 90), ".*'o"),
    "spray": ((215, 235, 255), (70, 100, 150), ".,'`"),
}


class Particles:
    def __init__(self, rng, cap=900):
        self.rng, self.p, self.cap = rng, [], cap

    def add(self, x, y, vx, vy, life, kind, g=0.0, drag=0.0, ch=None):
        if len(self.p) < self.cap:
            c = ch or self.rng.choice(KINDS[kind][2])
            self.p.append([x, y, vx, vy, life, life, kind, c, g, drag])

    def burst(self, x, y, n, kind, speed=14.0, life=0.9, g=18.0, up=0.0, drag=0.0):
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            s = speed * self.rng.uniform(0.25, 1.0)
            self.add(x, y, math.cos(a) * s * 2.0, math.sin(a) * s - up, life * self.rng.uniform(0.5, 1.0), kind, g, drag)

    def step(self, dt):
        keep = []
        for q in self.p:
            q[4] -= dt
            if q[4] <= 0:
                continue
            q[3] += q[8] * dt
            if q[9]:
                k = max(0.0, 1.0 - q[9] * dt)
                q[2] *= k
                q[3] *= k
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            keep.append(q)
        self.p = keep

    def draw(self, cv, lit=0.0):
        for x, y, vx, vy, life, mx, kind, ch, g, d in self.p:
            c0, c1, _ = KINDS[kind]
            f = life / mx
            col = mix(c1, c0, f)
            xi, yi = int(round(x)), int(round(y))
            cv.put(xi, yi, ch, col)
            if lit and kind in ("spark", "ember"):
                cv.light(xi, yi, mul(col, 0.35), lit, 0.0)


# ---------------------------------------------------------------- fire cellular automaton
class Fire:
    """Doom-style fire in true colour on a band of columns [x0, x0+w) x all rows: heat is injected, drifts up and cools."""

    def __init__(self, x0, w, h, rng, decay=0.07):
        self.x0, self.w, self.h, self.rng, self.decay = x0, max(1, w), h, rng, decay
        self.g = [[0.0] * self.w for _ in range(h)]

    def inject(self, x, y, v):
        x -= self.x0
        if 0 <= x < self.w and 0 <= y < self.h and self.g[y][x] < v:
            self.g[y][x] = v

    def step(self, decay=None, wind=0):
        g, rnd, w = self.g, self.rng.random, self.w
        dec = self.decay if decay is None else decay
        for y in range(self.h - 1):
            row, below = g[y], g[y + 1]
            for x in range(w):
                sx = x + int(rnd() * 3) - 1 + wind
                v = below[sx if 0 <= sx < w else x] - dec * (0.4 + rnd() * 1.2)
                row[x] = v if v > 0 else 0.0
        last = g[self.h - 1]
        for x in range(w):
            last[x] *= 0.8

    def draw(self, cv, thresh=0.16, y_max=None, solid=0.62):
        g, rng = self.g, self.rng
        for y in range(min(self.h, y_max if y_max is not None else self.h)):
            row = g[y]
            for xi in range(self.w):
                v = row[xi]
                if v < thresh:
                    continue
                col = fire_rgb(v)
                if v > solid:
                    ch = "@#%&"[int(rng.random() * 4)] if v > 0.75 else "*%;"[int(rng.random() * 3)]
                    cv.put(self.x0 + xi, y, ch, col, mul(col, 0.50 if v > 0.75 else 0.38))
                else:                                                               # thin flame: only light, so what is behind stays visible
                    cv.put(self.x0 + xi, y, ".:,'`"[int(rng.random() * 5)], col)
                    cv.light(self.x0 + xi, y, col, 0.22, 0.0)


# ---------------------------------------------------------------- sprites
def anim_sprite(kind, state, i, size="big"):
    """One Noah animation frame as rows of (glyph, fg, bg) cells (the personality's colours), or None without art."""
    fr = portraits.anim_frame(kind, state, i, size)
    if not fr:
        return None
    return _rows(fr, kind)


def morph_sprite(old, new, i, size="big"):
    fr = portraits.morph_frame(old, new, i, size)
    return _rows(fr, new) if fr else None


def _rows(fr, kind):
    out = []
    for rows, fg, bg in zip(fr["rows"], fr["fg"], fr["bg"]):
        w = len(rows)
        out.append([(ch, portraits.tone_rgb(portraits.band(kind, x, w), int(fg[x])), portraits.tone_rgb(portraits.band(kind, x, w), int(bg[x])))
                    for x, ch in enumerate(rows)])
    return out


def blit(cv, spr, cx, y, sx=1.0, sy=1.0, bright=1.0, dx_rows=None, key=None, tint=None, tint_a=0.0):
    """Draw a sprite (list of rows of (ch, fg, bg)) centred on column cx, top at row y, scaled (nearest) by sx, sy. dx_rows(i) shifts a row."""
    sh, sw = len(spr), len(spr[0])
    ow, oh = max(1, int(round(sw * sx))), max(1, int(round(sh * sy)))
    x0 = int(round(cx - ow / 2.0))
    for i in range(oh):
        yy = y + i
        if not 0 <= yy < cv.h:
            continue
        row = spr[min(sh - 1, int(i / sy))]
        dx = dx_rows(i) if dx_rows else 0
        for j in range(ow):
            xx = x0 + j + dx
            if not 0 <= xx < cv.w:
                continue
            ch, fg, bg = row[min(sw - 1, int(j / sx))]
            if key and bg == key:                                  # a transparent background: keep the canvas under the glyph
                if ch != " ":
                    cv.ch[yy * cv.w + xx], cv.fg[yy * cv.w + xx] = ch, (mul(fg, bright) if bright != 1.0 else fg)
                continue
            if bright != 1.0:
                fg, bg = mul(fg, bright), mul(bg, bright)
            if tint_a:
                fg, bg = mix(fg, tint, tint_a), mix(bg, tint, tint_a)
            k = yy * cv.w + xx
            cv.ch[k], cv.fg[k], cv.bg[k] = ch, fg, bg
    return x0, y, ow, oh


def portrait_cells(name, size):
    """A portrait (art/portraits.json) as rows of (ch, fg, bg) in its real colours, or None."""
    p = (portraits._load("portraits").get(name) or {}).get(size)
    if not p:
        return None
    rows = []
    for y, row in enumerate(p["rows"]):
        fg, bg, r = p["fg"][y], p["bg"][y], []
        for x, ch in enumerate(row):
            f = (int(fg[6 * x:6 * x + 2], 16), int(fg[6 * x + 2:6 * x + 4], 16), int(fg[6 * x + 4:6 * x + 6], 16))
            b = (int(bg[6 * x:6 * x + 2], 16), int(bg[6 * x + 2:6 * x + 4], 16), int(bg[6 * x + 4:6 * x + 6], 16))
            r.append((ch, f, b))
        rows.append(r)
    return rows


# ---------------------------------------------------------------- lines
def line_glyph(dx, dy):
    """The slash character for a direction in cell coordinates."""
    if dx == 0:
        return "|"
    s = dy / float(dx)
    return "-" if abs(s) < 0.35 else "|" if abs(s) > 3 else ("\\" if s > 0 else "/")


def walk(x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    return [(int(round(x0 + (x1 - x0) * i / n)), int(round(y0 + (y1 - y0) * i / n))) for i in range(n + 1)]


def jagged(x0, y0, x1, y1, rng, amp=2.0, step=3):
    """A rough line between two points: a list of cells."""
    pts, n = [(x0, y0)], max(1, int(abs(x1 - x0) / step))
    for i in range(1, n):
        f = i / n
        pts.append((x0 + (x1 - x0) * f + rng.uniform(-1, 1), y0 + (y1 - y0) * f + rng.uniform(-amp, amp)))
    pts.append((x1, y1))
    cells = []
    for a, b in zip(pts, pts[1:]):
        cells += walk(a[0], a[1], b[0], b[1])
    return cells


# ---------------------------------------------------------------- captions + frame loop
def caption(cv, text, f=1.0, rows=4):
    """The text bar at the bottom: wrapped, typed out (f 0..1), ALL-CAPS words in red, over a darkened strip."""
    width = max(10, min(cv.w - 6, 108))
    lines = textwrap.wrap(text, width)[:rows]
    if not lines:
        return
    y0 = cv.h - len(lines) - 1
    for y in range(max(0, y0 - 1), cv.h):
        for x in range(cv.w):
            i = y * cv.w + x
            cv.bg[i] = mul(cv.bg[i], 0.18)
            cv.fg[i] = mul(cv.fg[i], 0.25)
            cv.ch[i] = " "                                                   # the spaces between the words must not show what is behind them
    total, shown = sum(len(l) for l in lines), int(f * sum(len(l) for l in lines) + 0.999)
    for k, l in enumerate(lines):
        x = (cv.w - len(l)) // 2
        for word_x, word in _words(l):
            col = (255, 70, 60) if len(word) >= 3 and word.isupper() and any(c.isalpha() for c in word) else (236, 232, 226)
            take = min(len(word), max(0, shown - word_x))
            if take > 0:
                cv.text(x + word_x, y0 + k, word[:take], col)
        shown -= len(l)
    return total


def _words(line):
    out, i = [], 0
    for w in line.split(" "):
        out.append((i, w))
        i += len(w) + 1
    return out


def caption_at(captions, t):
    for t0, t1, text in captions:
        if t0 <= t < t1:
            return text, min(1.0, (t - t0) * 55.0 / max(1, len(text)))
    return None, 0.0


def plain(ctx, seconds, captions, cues):
    """Too small a terminal for a picture: only the captions and the sounds, as timed cards."""
    t, cues = 0.0, sorted(cues)
    for t0, t1, text in captions:
        while cues and cues[0][0] <= t0:
            ctx.sfx(cues.pop(0)[1])
        ctx.card(text, max(0.5, min(t1 - t0, 3.0)))
        t = t1
    for _, name in cues:
        ctx.sfx(name)
    ctx.wait(max(0.0, seconds - t))


def play(ctx, scene_factory, seconds, captions=(), cues=(), seed=1, truecolor=None):
    """Run one scene: scene_factory(w, h, rng) -> object with draw(cv, t, dt) -> (shake_x, shake_y). Returns the number of frames drawn.
    Time is the frame number (not the wall clock), so the picture is the same on every run; ctx.sleep paces it (fake in tests)."""
    cols, rows = ctx.size()
    w, h = cols, rows - 1                                  # never touch the last line: no scrolling
    cues, fired = sorted(cues), 0
    for _, t1, text in captions:
        ctx.log.append(("card", text))
    if w < 40 or h < 14:
        plain(ctx, seconds, list(captions), list(cues))
        return 0
    if truecolor is None:
        try:
            import ascii_art
            truecolor = ascii_art.has_truecolor()
        except Exception:
            truecolor = True
    fps = getattr(ctx, "fps", FPS)
    scene = scene_factory(w, h, random.Random(seed))
    cv, prev, frames = Canvas(w, h), None, int(seconds * fps)
    ctx.out.write("\033[?25l\033[0m\033[2J")
    try:
        for i in range(frames):
            started = time.monotonic()
            t = i / float(fps)
            while fired < len(cues) and cues[fired][0] <= t:
                ctx.sfx(cues[fired][1])
                fired += 1
            dx, dy = scene.draw(cv, t, 1.0 / fps)
            text, f = caption_at(captions, t)
            if text:
                caption(cv, text, f)
            shown = cv.shifted(int(dx), int(dy))
            s, prev = shown.diff(prev, truecolor)
            ctx.out.write(s)
            ctx.out.flush()
            ctx.sleep(max(0.0, 1.0 / fps - (time.monotonic() - started)))
        while fired < len(cues):
            ctx.sfx(cues[fired][1])
            fired += 1
    finally:
        chain.leave(ctx.out)
        ctx.out.flush()
    return frames


def spread(lines, t0, t1, gap=0.15):
    """Captions for a list of lines spread evenly (longer lines get a little longer) over [t0, t1)."""
    if not lines:
        return []
    wts = [len(l) + 30 for l in lines]
    tot, t, out = float(sum(wts)), t0, []
    for l, wt in zip(lines, wts):
        d = (t1 - t0) * wt / tot
        out.append((t, t + d - gap, l))
        t += d
    return out


def glow(cv, cx, cy, rx, ry, rgb, k):
    """A soft elliptical light: cells inside get rgb * k * (1 - d)^2."""
    for y in range(max(0, int(cy - ry)), min(cv.h, int(cy + ry) + 1)):
        for x in range(max(0, int(cx - rx)), min(cv.w, int(cx + rx) + 1)):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d < 1:
                cv.light(x, y, rgb, k * (1 - d) ** 2, 0.6)


def darken(cv, f):
    if f >= 1.0:
        return
    cv.fg = [mul(c, f) for c in cv.fg]
    cv.bg = [mul(c, f) for c in cv.bg]


def flash(cv, rgb, a):
    if a <= 0.01:
        return
    cv.fg = [mix(c, rgb, a) for c in cv.fg]
    cv.bg = [mix(c, rgb, a * 0.9) for c in cv.bg]


def push_in(cv, z, fx=0.5, fy=0.5):
    """A slow camera move: the picture is enlarged by z (1 = nothing) around the point (fx, fy) given as fractions of the screen (nearest cell)."""
    if z <= 1.002:
        return
    w, h = cv.w, cv.h
    ch, fg, bg = cv.snapshot()
    cx, cy = fx * w, fy * h
    xs = [min(w - 1, max(0, int(cx + (x - cx) / z))) for x in range(w)]
    for y in range(h):
        sy = min(h - 1, max(0, int(cy + (y - cy) / z))) * w
        d = y * w
        for x in range(w):
            i = sy + xs[x]
            cv.ch[d + x], cv.fg[d + x], cv.bg[d + x] = ch[i], fg[i], bg[i]


class Scaled:
    """Runs a scene `k` times slower or faster (k > 1 = longer): the scene's own time is t / k. `overlay(cv, t)` is drawn on top in real scene time (lyrics)."""

    def __init__(self, inner, k, overlay=None):
        self.inner, self.k, self.overlay = inner, k, overlay

    def draw(self, cv, t, dt):
        r = self.inner.draw(cv, t / self.k, dt / self.k)
        if self.overlay:
            o = self.overlay(cv, t)
            if o:                                                                       # the overlay (lyric word hits) may add to the screen jolt
                r = (r[0] + o[0], r[1] + o[1])
        return r


def scale_captions(caps, k):
    return [(a * k, b * k, text) for a, b, text in caps]


def scale_cues(cues, k):
    return [(a * k, name) for a, name in cues]


def shake_at(t, hits, amp=3.0, decay=0.22):
    """Cell shake from a list of (time, strength) hits: each one a quake that dies away."""
    a = 0.0
    for te, s in hits:
        if te <= t:
            a += s * math.exp(-(t - te) / decay)
    return a * amp


def jolt(rng, a):
    a = min(a, 9.0)
    return (int(round(rng.uniform(-a, a) * 2.0)), int(round(rng.uniform(-a, a) * 0.6))) if a > 0.15 else (0, 0)


_CV = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
_CE = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]


def draw_cube(cv, cx, cy, r, t, rgb=(140, 255, 235), a=1.0):
    """The tesseract's cube as a small rotating wireframe (r rows high, twice as wide); a = brightness 0..1. Used wherever the cube is 'in the room'."""
    ay, ax = t * 0.9, t * 0.55
    pts = []
    for x, y, z in _CV:
        x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
        y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
        pts.append((cx + x * r * 1.0, cy + y * r * 0.5 * 1.0, z))
    for i, j in _CE:
        (x0, y0, z0), (x1, y1, z1) = pts[i], pts[j]
        for px, py in walk(x0 * 1.0, y0, x1, y1):
            cv.put(int(round(cx + (px - cx) * 2.0)), int(py), "#" if z0 + z1 > 0 else ":", mul(rgb, a * (1.0 if z0 + z1 > 0 else 0.55)))
    cv.light(int(cx), int(cy), rgb, 0.25 * a, 0.0)


# ================================================================ 1. SLASHES
SEAM = (255, 250, 245)


class Slash:
    """One cut: a bright streak that crosses the screen in `dur` s, a black gap that opens along it, then closes and seals with a white glint."""

    def __init__(self, w, h, t0, cx, cy, theta, off=0.0, gap=1.5, dur=0.09, seal=0.6, kind="slash"):
        th = math.radians(theta)
        self.d, self.n = (math.cos(th), math.sin(th)), (-math.sin(th), math.cos(th))
        self.A = (cx / 2.0 + self.n[0] * off, cy + self.n[1] * off)            # visual coordinates: x halved so a cell is square
        self.t0, self.gap, self.dur, self.seal, self.kind = t0, gap, dur, seal, kind
        self.theta, self.w, self.h = theta, w, h
        us = [u * 0.5 for u in range(-160, 161) if self.inside(self.A[0] + self.d[0] * u * 0.5, self.A[1] + self.d[1] * u * 0.5)]
        self.lo, self.hi = (us[0], us[-1]) if us else (-1.0, 1.0)
        self.te = t0 + dur * (0 - self.lo) / max(0.5, self.hi - self.lo)            # the head passes the player's glow
        self.hit = (int(round(self.A[0] * 2)), int(round(self.A[1])))
        self.glyph = line_glyph(self.d[0] * 2, self.d[1])

    def inside(self, px, py):
        return -2 <= px * 2 < self.w + 2 and -2 <= py < self.h + 2

    def gap_at(self, tau):
        if tau < 0.05:
            return self.gap * tau / 0.05
        return self.gap * max(0.0, 1.0 - (tau - 0.05) / (self.seal - 0.05)) ** 1.4

    def draw(self, cv, t, rng):
        tau = t - self.t0
        if tau < 0 or tau > self.seal + 0.45:
            return
        hf = min(1.0, tau / self.dur)
        u_head = self.lo + (self.hi - self.lo) * hf
        g, b = self.gap_at(tau), math.exp(-tau / 0.24) + 0.12
        rim = g + 0.7
        u = self.lo
        while u <= u_head:
            px, py = self.A[0] + self.d[0] * u, self.A[1] + self.d[1] * u
            if self.inside(px, py):
                j = -(rim + 0.7)
                while j <= rim + 0.7:
                    x, y = int(round((px + self.n[0] * j) * 2)), int(round(py + self.n[1] * j))
                    a = abs(j)
                    if a < g:
                        cv.put(x, y, " ", None, (9, 0, 3))
                    elif a < rim:
                        cv.put(x, y, self.glyph, mul(SEAM, min(1.0, b + 0.3)), mix(cv.bg[y * cv.w + x] if 0 <= x < cv.w and 0 <= y < cv.h else BLACK, SEAM, 0.55 * b))
                    elif 0 <= x < cv.w and 0 <= y < cv.h:
                        cv.light(x, y, (110, 110, 135), 0.22 * b, 0.0)
                    j += 0.5
                if hf < 1.0 and u > u_head - 3:                           # the sharp bright head of the streak
                    cv.put(int(round(px * 2)), int(round(py)), "*", (255, 255, 255), (255, 120, 100))
            u += 0.5
        if self.seal - 0.15 < tau < self.seal + 0.4:                      # it heals: glints of cool white along the closed seam
            for _ in range(7):
                u = rng.uniform(self.lo, self.hi)
                px, py = self.A[0] + self.d[0] * u, self.A[1] + self.d[1] * u
                cv.put(int(round(px * 2)), int(round(py)), "+*"[rng.randint(0, 1)], (190, 255, 240), None)


def _bump(dt, rise=0.1, fall=0.2):
    """0 before, 0..1 over `rise` s, then a decay: the shape of a lunge."""
    if dt < -rise:
        return 0.0
    return (dt + rise) / rise if dt < 0 else math.exp(-dt / fall)


class SlashScene:
    LAST, CUT_END = 20.6, 25.0

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.cx, self.cy = w // 2, int(h * 0.80)                                 # the player's faint glow
        self.big = h >= 34 and w >= 70
        self.size = "big" if self.big else "small"
        self.parts = Particles(rng)
        self.nums = []                                                           # floating "0": the damage the cut did
        self.rings = []                                                          # (time, radius speed, strength)
        self.hits = []                                                           # (time, strength) for the shake
        self.slashes = []
        c = (self.cx, self.cy)
        S = lambda t, th, off=0.0, **k: self.slashes.append(Slash(w, h, t, c[0], c[1], th, off, **k))
        S(1.6, 28, -1.0)
        S(3.2, -36, 1.0)
        S(4.7, 0, -3.0, gap=1.2)
        S(6.1, 90, 0.0, gap=0.9, dur=0.06)                                       # the stab
        t, k = 8.2, 0
        while t < 15.0:                                                          # the flurry accelerates
            S(t, rng.uniform(-80, 80), rng.uniform(-7, 7), gap=rng.uniform(0.9, 1.6), dur=0.07, seal=0.45)
            if k % 3 == 0:
                S(t + 0.04, rng.uniform(-80, 80), rng.uniform(-7, 7), gap=1.0, dur=0.07, seal=0.4)
            t += max(0.1, 0.55 * 0.9 ** k)
            k += 1
        S(self.LAST, 90, 0.0, gap=3.2, dur=0.5, seal=1.7, kind="final")
        self.slashes.sort(key=lambda s: s.te)
        self.fired = 0
        self.dust = [(rng.randrange(w), rng.randrange(h), rng.random()) for _ in range(w * h // 90)]

    # -- what Noah looks like
    def noah(self, t, lunge):
        n = int(t * 7)
        if t < 6.4:
            return anim_sprite("red", "strike" if lunge > 0.35 else "windup", n, self.size)
        if t < 7.4:
            return morph_sprite("yellow", "red", 7 - min(7, int((t - 6.4) * 8)), self.size)
        if t < 13.2:
            return anim_sprite("yellow", "strike" if lunge > 0.4 else ("hurt" if n % 2 else "idle"), n, self.size)
        if t < 14.2:
            return morph_sprite("green", "yellow", 7 - min(7, int((t - 13.2) * 8)), self.size)
        if t < self.LAST - 0.1:
            return anim_sprite("green", "windup" if t > 17.5 else "hurt", n, self.size)
        return anim_sprite("green", "strike" if t < self.LAST + 0.5 else "collapse", n, self.size)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        cv.clear((5, 5, 9))
        for x, y, r in self.dust:
            cv.put(x, y, ".", (28 + int(r * 30),) * 3)
        for s in self.slashes:                                                   # new hits: sparks, rings, shake, "0"
            if s.te <= t and s.te >= t - dt - 1e-9 and s.kind != "ghost":
                big = s.kind == "final"
                self.parts.burst(s.hit[0], s.hit[1], 60 if big else 14, "steel" if big else "spark", 26 if big else 15, 1.1 if big else 0.6)
                if not big:
                    self.parts.burst(s.hit[0], s.hit[1], 6, "blood", 9, 0.5)
                self.rings.append((s.te, 38.0 if big else 20.0, 1.0 if big else 0.5))
                self.hits.append((s.te, 4.0 if big else 1.0))
                self.nums.append((s.te, s.hit[0] + rng.randint(-5, 5), s.hit[1] - 2))
        lunge = max([_bump(t - (s.te - 0.1)) for s in self.slashes if abs(s.te - t) < 1.0] or [0.0])
        spr = self.noah(t, lunge)
        thrown = smooth((t - self.LAST - 0.45) / 0.5)
        if spr:
            zoom = 1.0 + 0.30 * lunge - 0.45 * thrown + (-0.06 if self.LAST - 3 < t < self.LAST else 0.0)
            sw, sh = len(spr[0]), len(spr)
            ow, oh = sw * zoom, sh * zoom
            top = int(1 + (sh - oh) / 2 + 2.5 * lunge - 6 * thrown + (self.h * 0.03 if t < 1.2 else 0))
            trem = (lambda i: int(round(math.sin(t * 40 + i) * 1.4))) if 14.2 < t < self.LAST else None
            dim = 1.0 if t < self.LAST - 3 else 1.0 - 0.55 * smooth((t - (self.LAST - 3)) / 2.5)
            sx = zoom * (0.55 + 0.45 * smooth(t / 1.1)) if t < 1.1 else zoom
            blit(cv, spr, w // 2, top, sx, zoom, dim * (0.35 + 0.65 * min(1, t / 0.8)), trem, key=BLACK)
        # the glow that cannot be cut
        pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        flare = max([math.exp(-(t - s.te) / 0.18) for s in self.slashes if s.te <= t < s.te + 1.0] or [0.0])
        glow(cv, self.cx, self.cy, 15 + 6 * flare, 5 + 2 * flare, (215, 225, 255), 0.16 + 0.07 * pulse + 0.5 * flare)
        cv.put(self.cx, self.cy, "o", (255, 255, 255))
        for s in self.slashes:
            s.draw(cv, t, rng)
        # rings, "0", particles
        for te, sp, st in self.rings:
            r = (t - te) * sp
            if 0 <= r < 70:
                col = mul((225, 235, 255), st * max(0.0, 1 - r / 70.0))
                for k in range(0, 360, 4 if sp < 30 else 2):
                    a = math.radians(k)
                    cv.put(int(self.cx + math.cos(a) * r * 2), int(self.cy + math.sin(a) * r), "O" if sp > 30 else "o", col)
        for te, x, y in self.nums:
            if 0 <= t - te < 1.1:
                cv.text(x, int(y - (t - te) * 5), "0", mul((190, 190, 200), 1 - (t - te) / 1.1))
        self.parts.step(dt)
        self.parts.draw(cv, 0.4)
        # light of the hits, the end fade
        amp = shake_at(t, self.hits, 1.0, 0.22)
        fl = max([math.exp(-(t - s.te) / 0.07) * (0.9 if s.kind == "final" else 0.22) for s in self.slashes if s.te <= t < s.te + 0.5] or [0.0])
        flash(cv, (255, 245, 240), fl)
        if t > self.CUT_END - 1.6:
            darken(cv, 1 - 0.8 * smooth((t - (self.CUT_END - 1.6)) / 1.5))
            glow(cv, self.cx, self.cy, 12, 4, (215, 225, 255), 0.22)
        return jolt(rng, amp)


def slash_captions(lines):
    """The 8 lines of mika.slash.lines on their cuts; another number of lines is spread evenly."""
    beats = [(1.2, 3.1), (3.2, 5.0), (5.1, 7.9), (8.0, 11.0), (11.1, 14.4), (14.5, 18.0), (18.1, 22.0), (22.1, 24.8)]
    return [(a, b, l) for (a, b), l in zip(beats, lines)] if len(lines) == len(beats) else spread(lines, 1.2, 24.6)


SLASH_CUES = [(0.0, "knife-draw"), (1.6, "blade-block"), (3.2, "blade-block"), (4.7, "glass-crack"), (6.1, "stab-flesh"), (7.4, "sob-small"),
              (8.2, "blade-block"), (9.0, "stab-flesh"), (9.8, "blade-block"), (10.5, "stab-flesh"), (11.2, "blade-block"),
              (11.7, "bone-crack-1"), (12.2, "stab-flesh"), (12.7, "blade-block"), (13.3, "stab-flesh"), (13.9, "bone-crack-2"),
              (14.4, "blade-block"), (20.5, "shield-hit"), (20.6, "blade-shatter"), (21.0, "glass-crack"), (23.0, "sob-small")]


# ================================================================ the crack in the floor (scenes 2 and 3 share it)
class Crack:
    """A jagged crack across the whole width at row `ay`: yc[x] is its centre row, lip[x] a fixed random edge, forks the side cracks."""

    def __init__(self, w, h, ay, seed=11, forks=9):
        rng = random.Random(seed)
        self.w, self.h, self.ay = w, h, ay
        y, self.yc = float(ay), []
        nxt = 0
        for x in range(w):
            if x >= nxt:
                y += rng.choice((-1, 0, 0, 1))
                nxt = x + rng.randint(3, 8)
            y = min(max(y, ay - 3), ay + 3)
            self.yc.append(int(round(y)))
        self.lip = [rng.random() for _ in range(w)]
        self.forks = []
        for _ in range(forks):
            x0 = rng.randrange(int(w * 0.12), int(w * 0.88))
            sx, sy = rng.choice((-1, 1)) * rng.randint(10, 34), rng.choice((-1, 1)) * rng.randint(3, 9)
            self.forks.append((x0, jagged(x0, self.yc[x0], x0 + sx, self.yc[x0] + sy, rng, 1.6, 3)))

    def reach(self, p):
        return p * self.w / 2.0                                         # the crack opens from the middle outwards

    def hairline(self, cv, p, t, rng, col=(230, 255, 240), leak=(120, 255, 215), rise=6.0):
        """Scene 2: a thin bright line with light leaking upwards out of it."""
        half = self.reach(p)
        prev = None
        for x in range(self.w):
            if abs(x - self.w / 2.0) > half:
                continue
            y, k = self.yc[x], 1.0 - abs(x - self.w / 2.0) / max(1.0, half) * 0.5
            ys = range(min(y, prev), max(y, prev) + 1) if prev is not None else (y,)
            for yy in ys:
                cv.put(x, yy, "/\\_|"[(x + yy) % 4], mul(col, k), mix(cv.bg[yy * cv.w + x] if 0 <= yy < cv.h else BLACK, col, 0.8 * k))
            prev = y
            hgt = rise * (0.4 + 0.6 * math.sin(x * 0.7 + t * 9) ** 2) * p
            for dy in range(1, int(hgt) + 1):
                cv.light(x, y - dy, leak, 0.55 * (1 - dy / (hgt + 1)) ** 2 * k, 0.8)
        for x0, cells in self.forks:                                    # side cracks follow once the main one is wide enough
            if abs(x0 - self.w / 2.0) < half - 4:
                n = int(len(cells) * min(1.0, (half - abs(x0 - self.w / 2.0)) / 25.0))
                for x, y in cells[:n]:
                    cv.put(x, y, "/\\"[(x + y) % 2], mul(col, 0.8), mix(cv.bg[y * cv.w + x] if 0 <= y < cv.h and 0 <= x < cv.w else BLACK, col, 0.5))


# ================================================================ 2. MIKA AWAKENS
GLOW_STOPS = [(0.0, (0, 0, 0)), (0.12, (0, 38, 50)), (0.4, (14, 125, 135)), (0.7, (110, 225, 205)), (1.0, (230, 255, 238)), (1.5, (255, 255, 255))]
WHISPERS = [(2.0, 0.12, 0.30, "hum."), (4.5, 0.82, 0.22, "..."), (6.5, 0.20, 0.62, "warm."), (8.5, 0.74, 0.58, "it is warm"), (10.5, 0.10, 0.18, "do you hear it"),
            (12.0, 0.86, 0.40, "nine years"), (14.0, 0.28, 0.80, "the lake"), (15.5, 0.70, 0.12, "hi"), (17.0, 0.06, 0.48, "i'm here"),
            (18.5, 0.88, 0.72, "almost"), (20.0, 0.34, 0.10, "hey"), (21.5, 0.62, 0.84, "wake up"), (23.0, 0.16, 0.74, "mmm"),
            (24.5, 0.78, 0.30, "there you are"), (26.0, 0.40, 0.06, "man.")]


class AwakenScene:
    """~32 s. A faint dot (the glow from the last scene) grows into the whole screen; the colours drift to teal/white/green."""
    END = 31.4

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.cx, self.cy = w // 2, int(h * 0.80)
        self.size = "big" if h >= 34 and w >= 70 else "small"
        self.crack = Crack(w, h, int(h * 0.90), seed=11)
        self.phase, self.rings, self.last_beat = 0.0, [], -1
        self.motes = []
        for _ in range(60 + w // 2):
            t0 = 26.0 * rng.random() ** 1.7
            side = rng.random()
            sx, sy = (rng.choice((0, w - 1)), rng.randrange(h)) if side < 0.6 else (rng.randrange(w), rng.choice((0, h - 1)))
            self.motes.append((t0, sx, sy, rng.uniform(0, 6.28), rng.uniform(5.0, 9.0), "*+.'`"[rng.randrange(5)]))
        self.noise = [rng.random() for _ in range(w * h)]
        self.hits = []
        import mika_fx                                                                 # (imports this module: so only here)
        self.mika = mika_fx.MikaFigure(int(h * 0.62))

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        u = min(1.0, t / 27.0)
        cv.clear((2, 4, 7))
        hz = 0.5 + 3.5 * u * u
        self.phase += hz * dt
        beat = int(self.phase)
        if beat != self.last_beat:
            self.last_beat = beat
            self.rings.append(t)
        pulse = math.exp(-5.0 * (self.phase % 1.0))
        # Noah, washed out by the light
        spr = anim_sprite("green", "collapse" if t > 21 else "hurt", int(t * 5), self.size)
        if spr:
            sh = len(spr)
            top = 1 + int(3 * smooth((t - 21) / 4.0))
            tr = (lambda i: int(round(math.sin(t * 33 + i * 1.3) * (0.6 + 1.5 * u)))) if t > 2 else None
            nx = w // 2 + int(smooth((t - 5.0) / 8.0) * w * 0.24)                 # Noah shrinks away to the right as the light grows
            x0, y0, ow, oh = blit(cv, spr, nx, top, 1.0, 1.0, 0.25 + 0.75 * smooth(t / 3.0) if t < 3 else 1.0, tr, key=BLACK)
            a = 0.85 * smooth((t - 6) / 20.0)
            for yy in range(max(0, y0), min(h, y0 + oh)):
                for xx in range(max(0, x0 - 3), min(w, x0 + ow + 3)):
                    i = yy * w + xx
                    lf, lb = sum(cv.fg[i]) / 3.0, sum(cv.bg[i]) / 3.0
                    cv.fg[i] = mix(cv.fg[i], (lf * 0.7 + 60, lf * 1.0 + 110, lf * 0.95 + 95), a)
                    cv.bg[i] = mix(cv.bg[i], (lb * 0.7 + 30, lb * 1.0 + 70, lb * 0.95 + 60), a)
        # the glow
        ry = 0.9 + h * 1.35 * u ** 2.4
        rx = ry * 2.0
        inten = 0.14 + 0.9 * u ** 1.25
        k = inten * (1.0 + 0.55 * pulse)
        x0, x1 = max(0, int(self.cx - rx * 2.2)), min(w, int(self.cx + rx * 2.2) + 1)
        y0, y1 = max(0, int(self.cy - ry * 2.2)), min(h, int(self.cy + ry * 2.2) + 1)
        for y in range(y0, y1):
            dy2 = ((y - self.cy) / ry) ** 2
            for x in range(x0, x1):
                d2 = ((x - self.cx) / rx) ** 2 + dy2
                v = k * math.exp(-2.2 * d2)
                if v < 0.03:
                    continue
                i = y * w + x
                col = ramp(GLOW_STOPS, v)
                n = self.noise[i]
                if cv.ch[i] == " ":
                    cv.bg[i] = add(cv.bg[i], col)
                    if v < 0.6 and n < 0.07 + 0.2 * v:
                        cv.ch[i], cv.fg[i] = ".:'*+"[int(n * 40) % 5], ramp(GLOW_STOPS, v + 0.35)
                else:
                    cv.bg[i], cv.fg[i] = add(cv.bg[i], col, 0.8), add(cv.fg[i], col, 0.5)
        draw_cube(cv, self.cx, self.cy - 1, 2.0 + 4.0 * u, t * (1.0 + 2.5 * u), (170, 255, 240), 0.5 + 0.5 * (0.4 * u + 0.6 * pulse))      # the cube in the pocket: the hum is its light
        if t > 12.5:                                                                  # Mika forms in the light: dissolves in, the coat and the hair drift as if under water
            mk = self.mika
            grid, _ = mk.cells(t, eyes=smooth((t - 21.0) / 4.0), aura=0.2 + 0.8 * u, reveal=smooth((t - 12.5) / 9.0), tint=((225, 255, 245), 0.30 * smooth((t - 12.5) / 12.0)))
            blit_grid(cv, grid, self.cx - mk.wf // 2, self.cy + 2 - mk.hf)
            if t > 21.0:
                ex = (6.6 * mk.s)
                for sx in (-1, 1):
                    glow(cv, self.cx + sx * 1.4 * 2 * mk.s, self.cy + 2 - mk.hf + ex, 5, 2, (120, 255, 225), 0.7 * smooth((t - 21.0) / 4.0))
        # a ring leaves the light with every beat
        for t0 in self.rings[-6:]:
            r = (t - t0) * (14 + 40 * u)
            if 0 < r < w and (t - t0) < 1.6:
                col = mul(ramp(GLOW_STOPS, 0.8), 0.55 * (1 - (t - t0) / 1.6) * (0.4 + u))
                for a in range(0, 360, 3):
                    ar = math.radians(a)
                    cv.put(int(self.cx + math.cos(ar) * r * 2), int(self.cy + math.sin(ar) * r), "o", col)
        # edge motes drift in to the light
        for t0, sx, sy, ph, life, ch in self.motes:
            age = t - t0
            if 0 <= age < life:
                s = age / life
                e = s * s * (3 - 2 * s)
                x = sx + (self.cx - sx) * e + math.sin(age * 2.5 + ph) * 5 * (1 - e)
                y = sy + (self.cy - sy) * e + math.cos(age * 2.1 + ph) * 2 * (1 - e)
                cv.put(int(x), int(y), ch, mul((200, 255, 235), min(1.0, 3 * (1 - s)) * min(1.0, 4 * s + 0.3)))
        for t0, fx, fy, text in WHISPERS:                                      # tiny text, fading in and out
            age = t - t0
            if 0 <= age < 3.2:
                cv.text(int(fx * (w - len(text))), int(fy * (h - 6)), text, mul((130, 225, 210), math.sin(math.pi * age / 3.2) * 0.9))
        # the floor starts to split
        shake = 0.0
        if t > 26.0:
            p = smooth((t - 26.0) / 5.2)
            self.crack.hairline(cv, p, t, rng, rise=3 + 8 * p)
            shake = 0.5 + 2.2 * p
        elif t > 20.0:
            shake = 0.25 * smooth((t - 20.0) / 6.0)
        if t > self.END - 0.9:
            flash(cv, (235, 255, 245), smooth((t - (self.END - 0.9)) / 0.9))
        return jolt(rng, shake)


AWAKEN_CUES = [(0.0, "lake-whispers"), (0.6, "glow-hum-rising"), (19.5, "ground-rumble"), (26.0, "stone-split"), (29.0, "ground-rumble"), (30.4, "electric-surge")]


# ================================================================ 3. NOAH BURNS
CLOTH = {"c": (176, 170, 164), "a": (150, 146, 142), "t": (44, 48, 74), "b": (28, 24, 30)}
SKIN, HAIR, BONE, CHAR = (214, 172, 150), (46, 36, 52), (238, 230, 206), (26, 17, 16)
EMBER = (255, 120, 30)


def region(tx, ty):
    """Noah's body in template units (36 tall): 'h' hair, 'f' face, 'e' eye, 'm' mouth, 'n' neck, 'c' shirt, 'a' sleeve, 'p' hand, 't' trousers,
    'b' shoes, or None. tx is in visual units (half a column)."""
    ax = abs(tx)
    if ty < 11:
        if (tx / 4.4) ** 2 + ((ty - 4.8) / 5.5) ** 2 < 1:
            if (tx / 3.1) ** 2 + ((ty - 6.7) / 4.0) ** 2 < 1 and ty >= 5.8:
                if 0.8 < ax < 2.0 and 6.9 < ty < 7.9:
                    return "e"
                if ax < 1.2 and 9.6 < ty < 10.4:
                    return "m"
                return "f"
            return "h"
    if 10.0 <= ty < 12.4 and ax < 1.15:
        return "n"
    if 12.0 <= ty < 24.0:
        hw0 = 4.7 - (ty - 12) * 0.083
        hw = hw0 - max(0.0, 13.8 - ty) * 0.9
        if ax < hw:
            return "t" if ty >= 22.6 else "c"
        xc = hw0 + 1.35 + (ty - 12) * 0.07
        if abs(ax - xc) < 1.2 and 12.6 <= ty < 22.6:
            return "a"
        if abs(ax - xc) < 1.1 and 22.6 <= ty < 26.2:
            return "p"
    if 24.0 <= ty < 34.0:
        xc, hw = 1.55 + (ty - 24) * 0.05, 2.15 - (ty - 24) * 0.05
        if abs(ax - xc) < hw:
            return "t"
        if abs(ax - (4.7 - 12 * 0.083 + 1.35 + 0.84)) < 1.1 and ty < 26.2:
            return "p"
    if 34.0 <= ty < 36.0 and abs(ax - (1.9 + (ty - 34) * 0.5)) < 2.5:
        return "b"
    return None


class Body:
    """Noah standing, rasterised for `hf` rows of height; render(t) -> rows of None | (glyph, fg, bg) and the heat to feed the fire."""

    def __init__(self, hf, rng):
        self.hf = max(8, hf)
        self.s = self.hf / 36.0
        self.wf = int(2 * 2 * 7.6 * self.s) + 2
        self.cells = []
        for yy in range(self.hf):
            ty = (yy + 0.5) / self.s
            for xx in range(self.wf):
                tx = (xx - self.wf / 2.0 + 0.5) * 0.5 / self.s
                code = region(tx, ty)
                if code:
                    t_ign = self.ignition(code, ty) + rng.random() * 0.7
                    self.cells.append((xx, yy, code, rng.random(), rng.random(), t_ign, ty))
        self.mask = {(c[0], c[1]) for c in self.cells}
        self.cx = self.wf // 2

    @staticmethod
    def ignition(code, ty):
        if code in "tb":
            return 4.6 + (36 - ty) * 0.30 if ty >= 24 else 8.6 + (24 - ty) * 0.2
        if code in "cn":
            return 9.0 + (24 - ty) * 0.45
        if code in "ap":
            return 11.0 + abs(ty - 12) * 0.25
        return 12.6 if code == "h" else 14.0

    def look(self, code, a, n1, n2, t, ty):
        """The cell for a burn age a (seconds since it ignited; negative = not yet)."""
        cloth = code in CLOTH
        base = CLOTH[code] if cloth else (HAIR if code == "h" else SKIN)
        if a < 0:
            ch = "▒▓#%"[int(n1 * 4)] if cloth else ("|/\\'`"[int(n1 * 5)] if code == "h" else ".,:'"[int(n1 * 4)])
            fg, bg = mul(base, 0.8 + 0.3 * n2), mul(base, 0.35 if code == "h" else 0.55 if cloth else 0.75)
            w = 0.6 * smooth((a + 0.9) / 0.9)
            return ch, mix(fg, EMBER, w), mix(bg, (160, 50, 10), w), 0.0
        flick = 0.5 + 0.5 * math.sin(t * 17 + n1 * 40)
        if code == "h":
            if a < 0.8:
                return "*#%"[int(n1 * 3)], (255, 205, 90), (190, 70, 10), 1.0
            if a < 3.0:
                if n1 < 0.55:
                    return "\"'`"[int(n1 * 5.4) % 3], (80, 52, 38), mul((60, 20, 8), flick), 0.5
                return "`", (50, 40, 35), mul(EMBER, 0.15 * flick), 0.5
            return "`'"[int(n1 * 2)], (52, 42, 38), (14, 8, 8), 0.0
        if cloth:
            if a < 0.9:
                k = a / 0.9
                return "#%&@"[int(n1 * 4)], mix(base, (255, 200, 80), k), mix(mul(base, 0.4), (150, 40, 5), k), 0.95
            if n1 < 0.75 - (a - 0.9) * 0.5:                                           # scraps of cloth hang on a little longer
                return "%", (46, 34, 30), (20, 14, 12), 0.5
        elif a < 0.9:
            k = a / 0.9
            return ":", mix(SKIN, (230, 80, 50), k), mix(mul(SKIN, 0.7), (150, 30, 25), k), 0.5
        # skin from here on (under cloth too)
        if a < 1.9:
            k = a - 0.9
            return ":;"[int(n1 * 2)], mix((230, 80, 50), (200, 40, 36), k), (120, 22, 20), 0.5
        if a < 3.6:
            if n2 < 0.5:                                                              # blisters
                if (a * 1.7 + n1 * 5) % 1.0 > 0.82:
                    return "*", (255, 232, 130), (205, 35, 22), 0.5                    # one bursts
                return "oO0@"[int(n1 * 4)], (255, 205, 175), (150, 46, 36), 0.35
            return "▓", (190, 42, 36), (112, 20, 18), 0.3
        k = smooth((a - 3.6) / 1.6)
        if code in "tbp" and ty > 27 and a > 5.2 + n1 and n2 > 0.28:                   # shins, feet and hands: down to the bone
            return "Il|!"[int(n1 * 4)], BONE, (112, 36, 28), 0.2
        if n2 > 0.80:
            return "/\\~"[int(n1 * 3)], (255, 100 + 70 * flick, 20), (70, 16, 6), 0.3
        if a > 5.0 and n1 > 0.9:
            return "#", (176, 22, 22), (84, 8, 8), 0.2
        return "%#▓&"[int(n1 * 4)], mix((190, 42, 36), (62, 42, 38), k), mix((112, 20, 18), CHAR, k), (0.25 if a < 5.5 else 0.0)

    def render(self, t, fire=None, bx=0, by=0, rng=None, parts=None):
        grid = [[None] * self.wf for _ in range(self.hf)]
        for xx, yy, code, n1, n2, ti, ty in self.cells:
            a = t - ti
            ch, fg, bg, heat = self.look(code, a, n1, n2, t, ty)
            if code == "e" and a < 0:
                ch, fg, bg = "@", (22, 14, 26), (236, 224, 214)
            elif code == "m" and a < 0:
                ch, fg, bg = "=", (110, 30, 36), (170, 110, 100)
            elif code == "e" and t > 15.8:
                ch, fg, bg = "o", (255, 120, 30), (6, 0, 0)
            elif code == "e" and a >= 0:
                ch, fg, bg = "O", (255, 255, 240), (150, 30, 30)
            elif code == "m" and t > 9.8:
                ch, fg, bg = ("O", (255, 140, 40), (10, 0, 0)) if t < 19 else (" ", (0, 0, 0), (8, 0, 0))
            k = 0.62 + 0.38 * (yy / self.hf)                                          # lit from below by the fire
            grid[yy][xx] = (ch, mul(fg, k), add(mul(bg, k), (28, 6, 0), 1 - k))
            if heat and fire is not None and heat * (0.5 + 0.5 * (n1 + n2) / 2) > 0.35:
                fire.inject(bx + xx, by + yy, min(1.0, heat * (0.75 + 0.35 * n2)))
        return grid


def blit_grid(cv, grid, x0, y0, sx=1.0, sy=1.0, dx_rows=None, clip_y=None):
    """Draw rows of None | (ch, fg, bg) (nearest-scaled), skipping None; cells at or below clip_y are not drawn."""
    sh, sw = len(grid), len(grid[0])
    ow, oh = max(1, int(round(sw * sx))), max(1, int(round(sh * sy)))
    for i in range(oh):
        yy = y0 + i
        if not 0 <= yy < cv.h or (clip_y is not None and yy >= clip_y):
            continue
        row = grid[min(sh - 1, int(i / sy))]
        dx = dx_rows(i) if dx_rows else 0
        for j in range(ow):
            c = row[min(sw - 1, int(j / sx))]
            xx = x0 + j + dx
            if c is None or not 0 <= xx < cv.w:
                continue
            k = yy * cv.w + xx
            cv.ch[k], cv.fg[k], cv.bg[k] = c


def thick_line(p0, p1, r, step=0.5):
    """Cells (x, y, d) within r (visual units) of the segment p0-p1 (cell coordinates), d = distance from the axis."""
    (x0, y0), (x1, y1) = p0, p1
    vx, vy = (x1 - x0) / 2.0, y1 - y0                                              # visual coordinates
    L = math.hypot(vx, vy) or 1.0
    nx, ny = -vy / L, vx / L
    out, n = {}, int(L / step) + 1
    for i in range(n + 1):
        px, py = x0 / 2.0 + vx * i / n, y0 + vy * i / n
        j = -r
        while j <= r:
            c = (int(round((px + nx * j) * 2)), int(round(py + ny * j)))
            if c not in out or abs(j) < out[c]:
                out[c] = abs(j)
            j += step
    return [(x, y, d) for (x, y), d in out.items()]


class Stage:
    """The arena: a dark hall, a stone floor, a crack that tears open into a pit. The same crack is used for the whole scene."""

    def __init__(self, w, h, rng):
        self.w, self.h = w, h
        A = max(12, h - 5)
        self.A, self.horizon, self.feet, self.cy = A, int(A * 0.52), int(A * 0.80), int(A * 0.90)
        self.cx = w // 2
        self.crack = Crack(w, h, self.cy, seed=21, forks=12)
        n = w * h
        self.ch, self.fg, self.bg = [" "] * n, [(70, 55, 62)] * n, [BLACK] * n
        pillars = [self.cx + k for k in (-96, -62, -31, 31, 62, 96)]
        for y in range(h):
            for x in range(w):
                i = y * w + x
                if y < self.horizon:
                    c = mix((3, 2, 6), (30, 8, 10), (y / float(self.horizon)) ** 2)
                    if any(abs(x - p) < 3 for p in pillars):
                        c = mul(c, 0.35)
                        if min(abs(x - p) for p in pillars) in (2,):
                            self.ch[i], self.fg[i] = "|", mul(c, 3)
                    self.bg[i] = c
                else:
                    d = (y - self.horizon) / float(h - self.horizon)
                    self.bg[i] = mix((13, 10, 15), (30, 22, 28), d)
                    seam = int(self.horizon + (h - self.horizon) * (((y - self.horizon) // 3) * 3 / float(h - self.horizon)))
                    tile = int(8 + d * 22)
                    if (y - self.horizon) % 4 == 0:
                        self.ch[i], self.fg[i] = "_", mix((44, 34, 42), (80, 64, 72), d)
                    elif (x - self.cx) % tile == 0:
                        self.ch[i], self.fg[i] = "|", mix((40, 30, 38), (70, 56, 64), d)
                    elif rng.random() < 0.04:
                        self.ch[i], self.fg[i] = ".,'`"[rng.randrange(4)], (60, 48, 56)

    def paint(self, cv, lit=0.0):
        cv.ch, cv.fg, cv.bg = self.ch[:], self.fg[:], self.bg[:]
        if lit > 0.01:                                                              # red light from the pit on the hall and the floor
            for y in range(max(0, self.horizon - 12), self.h):
                k = lit * (math.exp(-abs(y - self.cy) / 6.0) * 0.55 + (0.12 if y < self.horizon else 0.0) * (y / float(self.horizon)))
                if k < 0.02:
                    continue
                col = (255, 70, 12)
                for x in range(self.w):
                    cv.light(x, y, col, k, 0.55)

    def pit(self, cv, t, p, gap, rng, glow_k=1.0, fall=0.0):
        """The crack opened to `gap` rows: p = how much of the width is torn open, glow_k = brightness, fall = 0..1 how far the whole floor has dropped."""
        cr, half = self.crack, self.crack.reach(p)
        for x in range(self.w):
            dist = abs(x - self.cx)
            if dist > half:
                continue
            edge = 1.0 - dist / max(1.0, self.w / 2.0) * 0.8
            hg = gap * edge * (0.7 + 0.6 * cr.lip[x]) + fall * (self.h * 0.6)
            yc = cr.yc[x]
            y0, y1 = int(yc - hg), int(yc + hg * 1.25)
            if hg < 0.6:
                cv.put(x, yc, "/\\_|"[(x + yc) % 4], (255, 190, 90), (190, 60, 12))
                continue
            for y in range(max(0, y0), min(self.h, y1 + 1)):
                dd = abs(y - yc) / max(1.0, hg)
                v = (0.30 + 0.62 * (1 - min(1.0, dd)) ** 1.3) * glow_k * (0.9 + 0.2 * math.sin(x * 0.8 + y * 1.3 + t * 7))
                col = fire_rgb(v)
                ch = "~^*:"[int(((x * 7 + y * 13 + t * 9) % 4))] if v > 0.45 else " "
                cv.put(x, y, ch, mul(col, 1.15), mul(col, 0.62))
            for y in (y0 - 1, y1 + 1):                                               # glowing, ragged rims
                cv.put(x, y, "#%"[(x + y) % 2], (255, 160, 50), (140, 40, 8))
            lip = int(2 + 3 * cr.lip[x] * glow_k)                                    # flames licking over the upper lip
            for k in range(lip):
                f = 0.9 * (1 - k / float(lip)) * (0.6 + 0.4 * math.sin(x * 0.9 - t * 11 + k))
                if f > 0.1:
                    cv.put(x, y0 - 2 - k, "*;:'"[min(3, k)], fire_rgb(f))
                    cv.light(x, y0 - 2 - k, fire_rgb(f), 0.3, 0.0)

    def scorch(self, cv, body, ox, oy, k):
        """What stays on the floor: Noah's outline burned into the stone (k 0..1 = how much is still glowing)."""
        for xx, yy in body.mask:
            x, y = ox + xx, oy + yy
            cv.put(x, y, "▓%#"[(xx + yy) % 3], mix((14, 10, 11), (230, 80, 15), k * 0.22), mix((6, 5, 6), (70, 20, 5), k * 0.25))


FACE_CUT = 9.5          # the camera goes to his face here (full body shots: 4.6-9.5, 20.5-31)


class Face:
    """Noah's red portrait (art/portraits.json) as the close-up: burns from the chin up, hair flares, eyes swell and pop, the skin peels to
    bone, the jaw drops. Landmarks are fractions of the picture; every effect is a function of the scene time t."""
    EYES = ((0.38, 0.49), (0.625, 0.49))
    MOUTH, NOSE, CHIN = (0.50, 0.69), (0.50, 0.60), 0.92

    def __init__(self, w, h, rng):
        self.size = "big" if h >= 34 and w >= 64 else "small" if h >= 22 and w >= 34 else None
        self.P = portrait_cells("noah_red", self.size) if self.size else None
        if not self.P:
            self.P = None
            return
        self.H, self.W = len(self.P), len(self.P[0])
        self.n = [[(rng.random(), rng.random()) for _ in range(self.W)] for _ in range(self.H)]
        self.kind = [[self.classify(x, y) for x in range(self.W)] for y in range(self.H)]

    def classify(self, x, y):
        u, v = x / float(self.W), y / float(self.H)
        if ((u - 0.505) / 0.215) ** 2 + ((v - 0.66) / 0.30) ** 2 < 1:
            return "f"
        lum = sum(self.P[y][x][2]) / 3.0
        return "h" if v < 0.62 and 0.17 < u < 0.83 and lum < 70 else None

    def lm(self, pt):
        return int(pt[0] * self.W), int(pt[1] * self.H)

    def render(self, t, rng, parts, fire, ox, oy):
        """The face as rows of (ch, fg, bg) for time t; sparks/blood go to `parts`, flame heat to `fire` (screen coordinates ox, oy)."""
        W, H, g = self.W, self.H, []
        peel = (t - 17.5) / 1.7 * H * 0.62 if t >= 17.5 else -1
        face_top = int(0.34 * H)
        for y in range(H):
            row = []
            for x in range(W):
                base = self.P[y][x]
                k = self.kind[y][x]
                n1, n2 = self.n[y][x]
                if k == "f":
                    a = (t - FACE_CUT) + (y / float(H) - 0.3) * 1.8 + n1 * 0.3
                    if a >= 0:
                        base = Body.look(None, "f", a, n1, n2, t, 20)[:3]
                        base = (base[0], base[1], base[2])
                    if peel >= 0 and y - face_top < peel:                                  # skin peeled away: bone
                        sh = 0.78 + 0.22 * math.sin(x * 0.6) * n1
                        base = ("▒░:'"[int(n1 * 4)], mul(BONE, sh), mul((150, 138, 115), sh))
                    elif peel >= 0 and y - face_top < peel + 1.6:                           # the flap curling at the front of the peel
                        base = ("(~)"[x % 3], (255, 110, 90), (110, 12, 16))
                elif k == "h":
                    a = (t - 12.5) + n1 * 0.9
                    if a >= 0:
                        ch, fg, bg, heat = Body.look(None, "h", a, n1, n2, t, 2)
                        base = (ch, fg, bg)
                        if heat and a < 1.8 and rng.random() < 0.25:
                            fire.inject(ox + x, oy + y - 1, 0.95)
                else:
                    if t > FACE_CUT:                                                   # the fire in the picture's own corners flares
                        f = 0.15 + 0.12 * math.sin(t * 9 + x * 0.4)
                        base = (base[0], mix(base[1], (255, 150, 40), f), mix(base[2], (255, 90, 10), f * 0.6))
                row.append(base)
            g.append(row)
        self.features(g, t)
        if t >= 18.4:
            g = self.jaw(g, t)
        return g

    def disc(self, g, cx, cy, rx, ry, fn):
        for y in range(max(0, int(cy - ry)), min(self.H, int(cy + ry) + 1)):
            for x in range(max(0, int(cx - rx)), min(self.W, int(cx + rx) + 1)):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d < 1:
                    c = fn(x, y, d)
                    if c:
                        g[y][x] = c

    def features(self, g, t):
        W, H = self.W, self.H
        sc = W / 60.0
        mx, my = self.lm(self.MOUTH)
        if FACE_CUT <= t:                                                              # the mouth tears wider and wider
            o = smooth((t - FACE_CUT) / 3.0)
            self.disc(g, mx, my, (4 + 5 * o) * sc, (1.2 + 2.6 * o) * sc,
                      lambda x, y, d: ("O" if d > 0.5 else "@", fire_rgb(0.55 - 0.4 * d + 0.1 * math.sin(t * 12 + x)), mul(fire_rgb(0.5 - 0.35 * d), 0.5)) if d < 0.82 else
                      ("|", (240, 232, 215), (60, 10, 10)))
        for k, e in enumerate(self.EYES):
            ex, ey = self.lm(e)
            if 15.0 <= t < 16.1:                                                       # the eyes swell
                s = smooth((t - 15.0) / 1.1)
                self.disc(g, ex, ey, (2.2 + 2.6 * s) * sc, (1.1 + 1.3 * s) * sc,
                          lambda x, y, d, s=s: (("-", (200, 20, 30), (236, 190, 180)) if (x * 5 + y * 3) % 7 == 0 else
                                                ("O", (255, 255, 255), mix((236, 210, 200), (255, 170, 160), s * (1 - d)))))
            elif t >= 16.1:                                                            # popped: a black socket with an ember in it
                self.disc(g, ex, ey, 3.1 * sc, 1.9 * sc,
                          lambda x, y, d: (".", (255, 110 + int(60 * math.sin(t * 9 + x)), 30), (12, 0, 0)) if d < 0.15 else (" ", BLACK, (9, 0, 0)))
                n = int(min(8, (t - 16.1) * 4) * sc)                                    # the jelly runs down the cheeks
                for j in range(n):
                    g[min(H - 1, ey + 2 + j)][min(W - 1, ex + (j // 3) % 2)] = (":|"[j % 2], (232, 228, 200), (95, 40, 35))
        if t >= 17.5:                                                                  # the skull: nose hole, cheek shadow
            nx, ny = self.lm(self.NOSE)
            self.disc(g, nx, ny, 2.3 * sc, 1.6 * sc, lambda x, y, d: ("^", (60, 20, 15), (14, 2, 3)) if y > ny - 0.6 * sc else ("v", (60, 20, 15), (14, 2, 3)))
        for ear in (0.30, 0.70):                                                       # the ears curl up black
            if t > 12.6:
                ex, ey = int(ear * W), int(0.56 * H)
                for j in range(int(3 * sc)):
                    g[min(H - 1, ey + j)][min(W - 1, ex)] = (")(J~"[j % 4] if ear < 0.5 else "()L~"[j % 4], (60, 40, 34), (24, 10, 8))

    def jaw(self, g, t):
        """From t = 18.4 the lower jaw drops: everything below the mouth line moves down and the gap is a dark cavity with flames in it."""
        mx, my = self.lm(self.MOUTH)
        dj = int(min(6, (t - 18.4) * 3.2) * self.W / 60.0 + 0.5 * math.sin(t * 20))
        if dj < 1:
            return g
        out = [r[:] for r in g]
        for y in range(my + 1, self.H):
            src = y - dj
            out[y] = g[src][:] if src > my else out[y]
        for y in range(my + 1, min(self.H, my + 1 + dj)):
            for x in range(int(mx - 0.2 * self.W), int(mx + 0.2 * self.W)):
                d = abs(x - mx) / (0.2 * self.W)
                k = (y - my) / float(dj + 1)
                out[y][x] = ("^" if (x + y) % 2 else "*", fire_rgb(0.55 + 0.3 * math.sin(t * 15 + x * 0.7) - 0.3 * d), (12 + int(40 * (1 - k)), 0, 0)) if d < 1 - 0.15 * k else out[y][x]
        for x in range(int(mx - 0.19 * self.W), int(mx + 0.19 * self.W)):
            if my + 1 < self.H:
                out[my + 1][x] = ("|", (240, 232, 215), (30, 4, 4))                     # upper teeth
            if my + dj < self.H:
                out[my + dj][x] = ("|", (232, 222, 200), (30, 4, 4))                    # lower teeth
        return out


def _hash(x, y, k=0):
    return ((x * 73856093) ^ (y * 19349663) ^ (k * 83492791)) % 1000 / 1000.0


class Hand:
    """A charred, half-skeletal hand reaching at the camera. Three fingers snap off at HAND_SNAPS (scene time)."""
    FINGERS = [(-1.2, 10, (-15, 2)), (-0.30, 15, (-9, -6)), (-0.06, 17, (-3, -7)), (0.17, 15, (3, -6)), (0.42, 11, (9, -4))]    # angle, length, base
    SNAPS = {2: 26.3, 1: 26.9, 3: 27.5}
    T0 = 24.5

    def draw(self, cv, t, cx, cy, sc, rng, reach=None, snaps=True, up=False):
        reach = smooth((t - self.T0) / 1.6) if reach is None else reach
        k = (0.55 + 0.5 * reach) * sc
        trem = math.sin(t * 31) * 0.7
        px, py = cx + trem, cy + (1 - reach) * 6
        # the arm comes in from the bottom left
        for x, y, d in thick_line(*(((px, py + 6 * k), (px, cv.h + 4)) if up else ((px - 26 * k, py + 12 * k), (px - 60 * k, cv.h + 4))), 3.2 * k):
            self.flesh(cv, x, y, t, 0.8 - d / (3.2 * k + 1))
        # palm
        ry = 7.5 * k
        for y in range(int(py - ry), int(py + ry) + 1):
            half = 15 * k * math.sqrt(max(0.0, 1 - ((y - py) / ry) ** 2))
            for x in range(int(px - half), int(px + half) + 1):
                self.flesh(cv, x, y, t, 1.0 - abs(x - px) / (half + 1))
        for i, (ang, ln, (bx, by)) in enumerate(self.FINGERS):
            snapped = snaps and i in self.SNAPS and t >= self.SNAPS[i]
            x, y = px + bx * k, py + by * k
            a = ang + math.sin(t * 25 + i) * 0.03
            fracs = (0.0, 0.42, 0.72, 1.0)
            joints = [(x, y)]
            for seg in range(3):
                a += 0.16 * (1 + reach)                                                # the fingers curl as they grasp
                step = ln * k * (fracs[seg + 1] - fracs[seg])
                x, y = x + math.sin(a) * 2.0 * step, y - math.cos(a) * step
                joints.append((x, y))
            for seg in range(3 - (1 if snapped else 0)):
                bone = seg == 2 or (seg == 1 and _hash(i, 7) > 0.45)
                for xx, yy, d in thick_line(joints[seg], joints[seg + 1], (1.5 - 0.25 * seg) * k):
                    if bone:
                        cv.put(xx, yy, "|Il!"[(xx + yy) % 4], mul(BONE, 0.85 + 0.15 * _hash(xx, yy)), (126, 40, 30))
                    else:
                        self.flesh(cv, xx, yy, t, 0.5)
            for j in range(1, 3 + (0 if snapped else 1)):                              # knuckle bones
                cv.put(int(joints[j][0]), int(joints[j][1]), "O", BONE, (96, 30, 24))
            if snapped:
                jx, jy = int(joints[2][0]), int(joints[2][1])
                cv.put(jx, jy, "o", (255, 90, 30), (60, 0, 0))
                if snaps and t < self.SNAPS[i] + 0.8:
                    cv.light(jx, jy, (255, 60, 20), 0.5 * (1 - (t - self.SNAPS[i]) / 0.8), 0.3)
        return px, py

    def snap_points(self, t, cx, cy, sc):
        """Where the pieces that broke off in this frame start (for particles): list of (x, y)."""
        reach = smooth((t - self.T0) / 1.6)
        k = (0.55 + 0.5 * reach) * sc
        out = []
        for i in self.SNAPS:
            ang, ln, (bx, by) = self.FINGERS[i]
            x, y, a = cx + bx * k, cy + by * k + (1 - reach) * 6, ang
            for seg in range(3):
                a += 0.16 * (1 + reach)
                step = ln * k * ((0.42, 0.3, 0.28)[seg])
                x, y = x + math.sin(a) * 2.0 * step, y - math.cos(a) * step
                if seg == 1:
                    out.append((i, x, y))
        return out

    @staticmethod
    def flesh(cv, x, y, t, k):
        n = _hash(x, y)
        if n > 0.84:
            cv.put(x, y, "/\\~"[int(n * 30) % 3], (255, 100 + 70 * math.sin(t * 6 + n * 20) ** 2, 20), (70, 16, 6))
        elif n < 0.07:
            cv.put(x, y, "#", (176, 24, 24), (84, 10, 10))
        else:
            cv.put(x, y, "%#▓&"[int(n * 40) % 4], mix((70, 46, 40), (36, 24, 22), n), mix((26, 16, 14), (12, 8, 8), n))


HATE = ["liar", "freak", "burn", "monster", "worthless", "ugly", "why are you alive", "nobody wants you", "disgusting", "you ruin everything",
        "creep", "filth", "die", "weak", "pathetic", "no one will come", "crybaby", "stupid", "you're nothing", "BURN", "FREAK", "LIAR", "go away",
        "shut up", "useless", "mistake", "rotten", "hateful", "we never wanted you", "dirty", "wrong", "WHY ARE YOU STILL HERE"]
FORGIVE = ["sorry", "please", "forgive me", "I didn't mean to", "I'll be good", "don't leave", "it hurts", "mama", "I'm sorry", "please stop", "I can change",
           "I'll try harder", "take me back", "stay", "I was scared", "I didn't know", "don't go", "say something", "I'll be quiet", "I promise",
           "please please", "it wasn't me", "I'm here", "hold on to me", "is it my fault", "sorry sorry sorry", "just once", "look at me"]
SPOKEN = [  # (from, to, text, hate?, y fraction): lines in the middle, spaced out big; his voice, then theirs
    (12.6, 14.4, "m a m a ?", False, 0.10), (14.5, 16.0, "I DIDN'T MEAN TO", True, 0.10), (16.6, 18.2, "i'll be good. i'll be good.", False, 0.12),
    (21.0, 22.6, "DON'T LEAVE ME", False, 0.10), (23.0, 24.6, "WHY ARE YOU ALIVE", True, 0.10), (25.0, 26.6, "it hurts it hurts it hurts", False, 0.12),
    (28.4, 30.0, "forgive me", False, 0.12)]
GLITCH = "#%@&$?!/\\|<>~^"


class WordRain:
    """A wall of words around the burning Noah: hate words fall like hard red and white rain, forgiveness-seeking words rise like pale blue sparks.
    The rate climbs from 5 s to 29 s; letters glitch word by word; the words only fill empty cells, so they stay behind the picture."""

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng, self.words, self.acc = w, h, rng, [], [0.0, 0.0]

    def level(self, t):
        return smooth((t - 4.8) / 24.0) * (1 - smooth((t - 32.0) / 2.0)) if 4.8 < t < 34.2 else 0.0

    def step(self, t, dt):
        lv, rng = self.level(t), self.rng
        for k, (rate, kind) in enumerate(((2.0 + 30 * lv, "h"), (1.0 + 16 * lv, "f"))):
            if lv <= 0:
                self.acc[k] = 0.0
                continue
            self.acc[k] += rate * dt
            while self.acc[k] >= 1 and len(self.words) < 260:
                self.acc[k] -= 1
                text = rng.choice(HATE if kind == "h" else FORGIVE)
                if kind == "h" and rng.random() < 0.2:
                    text = text.upper()
                x = rng.randrange(max(1, self.w - len(text)))
                if kind == "h":
                    self.words.append(dict(k="h", x=x, y=-1.0, vy=rng.uniform(14, 30) * (1 + lv), life=9.0, text=text, age=0.0, hard=rng.random() < 0.45))
                else:
                    self.words.append(dict(k="f", x=x, y=rng.uniform(self.h * 0.55, self.h * 0.95), vy=-rng.uniform(2.0, 7.0) * (1 + lv), life=rng.uniform(3.0, 5.5),
                                           text=text, age=0.0, ph=rng.uniform(0, 6.28)))
        keep = []
        for wd in self.words:
            wd["age"] += dt
            wd["y"] += wd["vy"] * dt
            if wd["k"] == "f":
                wd["x"] += math.sin(wd["age"] * 1.7 + wd["ph"]) * 4 * dt
            if wd["age"] < wd["life"] and -2 < wd["y"] < self.h + 1:
                keep.append(wd)
        self.words = keep

    def put(self, cv, x, y, ch, fg, bg=None):
        if 0 <= x < cv.w and 0 <= y < cv.h:
            i = y * cv.w + x
            if cv.ch[i] in " .,'`:":
                cv.ch[i], cv.fg[i] = ch, fg
                if bg is not None:
                    cv.bg[i] = mix(cv.bg[i], bg, 0.7)

    def draw(self, cv, t):
        rng, lv = self.rng, self.level(t)
        for wd in self.words:
            text, y, x = wd["text"], int(wd["y"]), int(wd["x"])
            if wd["k"] == "h":
                glitch = 0.04 + 0.25 * lv
                shown = "".join((rng.choice(GLITCH) if c != " " and rng.random() < glitch else c) for c in text)
                col = (255, 255, 255) if wd["hard"] else (255, 40, 36)
                for k, c in enumerate(shown):
                    self.put(cv, x + k, y, c, col, (70, 0, 0) if not wd["hard"] else (150, 10, 10))
                    for tr in (1, 2, 3):                                                   # the rain's streak above the word
                        if c != " ":
                            self.put(cv, x + k, y - tr, "|:."[tr - 1], mul((200, 30, 30), 1 - tr * 0.28))
            else:
                a = math.sin(math.pi * wd["age"] / wd["life"])
                shown = "".join((" " if rng.random() < 0.03 + 0.1 * lv else c) for c in text)       # the letters drop out, like a bad connection
                if rng.random() < 0.004:
                    shown = text[0] + "-" + text
                col = mul(mix((150, 175, 255), (225, 215, 255), (x % 7) / 7.0), 0.35 + 0.65 * a)
                for k, c in enumerate(shown):
                    self.put(cv, x + k, y, c, col)
        for t0, t1, text, hate, fy in SPOKEN:                                              # the lines in the middle, large and slow
            if t0 <= t < t1:
                a = math.sin(math.pi * (t - t0) / (t1 - t0)) ** 0.5
                spaced = " ".join(text) if len(text) * 2 < cv.w - 4 else text
                x, y = (cv.w - len(spaced)) // 2, int(fy * cv.h) + (rng.randint(-1, 1) if hate else 0)
                col = mul((255, 60, 50), a) if hate else mul((205, 220, 255), a)
                for k, c in enumerate(spaced):
                    if 0 <= x + k < cv.w and c != " ":
                        cv.put(x + k, y, c, col, (60, 0, 0) if hate else None)
                        if hate:
                            cv.put(x + k, y + 1, c, mul(col, 0.4))


GORE_WORDS = [  # (from, to, text, x fraction, y fraction, colour): what Noah gets out, plain and fast
    (6.9, 7.9, "no.", 0.30, 0.30, (255, 120, 100)), (7.9, 8.9, "it HURTS", 0.66, 0.28, (255, 90, 70)),
    (14.0, 15.0, "MY HAIR", 0.14, 0.30, (255, 80, 60)), (16.2, 17.2, "MY EYES", 0.78, 0.38, (255, 60, 50)),
    (18.6, 20.4, "MIKA", 0.5, 0.10, (255, 255, 255)), (22.0, 23.0, "please", 0.30, 0.45, (255, 150, 130)),
    (24.8, 25.6, "STOP", 0.20, 0.40, (255, 70, 60)),
]


class BurnScene:
    """~38 s: the floor tears open (0-4.6), his feet ignite and the fire climbs (4.6-9.5), face close-ups (9.5-20.5: blisters and the voice splits,
    hair, eyes, skin to bone and the dropped jaw), the torso (20.5-24.5: the belly splits, the veins stand out and burst), the hand (24.5-28),
    the floor takes him (28-31.2), the fall through the abyss and the hell below (31.2-41.6, abyss_fx.py), silence and a last ember, the scorch mark (43-45)."""
    CUTS = (9.5, 20.5, 24.5, 28.0, 34.0, 37.5, 41.4, 49.5, 50.9)
    END = 52.9

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.st = Stage(w, h, rng)
        self.body = Body(self.st.feet - 1, rng)
        self.bx, self.by = self.st.cx - self.body.wf // 2, 1
        x0 = max(0, self.st.cx - 45)
        self.fire = Fire(x0, min(90, w - x0), h, rng)
        self.parts = Particles(rng, 1200)
        self.face = Face(w, h, rng)
        self.hand = Hand()
        self.hits = [(c, 1.6) for c in self.CUTS] + [(0.0, 1.5), (16.1, 1.2), (18.4, 1.0), (23.6, 1.2), (26.3, 0.6), (26.9, 0.6), (27.5, 0.6), (38.15, 1.2), (40.5, 2.2), (41.4, 0.6), (48.3, 3.0), (50.9, 1.4)]
        self.veins = self.vein_paths()
        self.popped = self.burst = False
        self.snapped = set()
        self.rad = [math.hypot((x - self.st.cx) / 2.0, y - h * 0.46) / (h * 0.6) for y in range(h) for x in range(w)]
        self.last_t = 0.0
        import abyss_fx
        self.ab = abyss_fx.AbyssScene(w, h, random.Random(9))
        self.rain = WordRain(w, h, random.Random(17))

    # -- helpers
    def vein_paths(self):
        b, s, out = self.body, self.body.s, []
        def cell(tx, ty):
            return int(tx * 2 * s + b.wf / 2.0 - 0.5), int(ty * s - 0.5)
        for sd in (-1, 1):
            out.append([cell(sd * (4.7 - (ty - 12) * 0.083 + 1.35 + (ty - 12) * 0.07), ty) for ty in [13 + i * 0.5 for i in range(20)]])
            out.append([cell(sd * (1.55 + (ty - 24) * 0.05), ty) for ty in [24 + i * 0.5 for i in range(20)]])
            out.append([cell(sd * 1.9, ty) for ty in [13.5 + i * 0.5 for i in range(18)]])
        out.append([cell(0.3, ty) for ty in [10 + i * 0.5 for i in range(5)]])
        return out

    def light_up(self, cv, t):
        return smooth(t / 2.5)

    def embers(self, t, dt, rate, spread=1.0):
        w, h, cr = self.w, self.h, self.st.crack
        for _ in range(int(rate * dt + self.rng.random())):
            x = self.rng.randrange(w)
            self.parts.add(x, self.rng.choice((cr.yc[x], h - 1)), self.rng.uniform(-3, 3), -self.rng.uniform(5, 18) * spread, self.rng.uniform(1.2, 3.0), "ember", -2.0)

    def shout(self, cv, t):
        for t0, t1, text, fx, fy, col in GORE_WORDS:
            if t0 <= t < t1:
                x, y = int(fx * (self.w - len(text))) + self.rng.randint(-1, 1), int(fy * self.st.A) + self.rng.randint(0, 1)
                cv.text(x, y, text, col)

    def draw(self, cv, t, dt):
        w, h, rng, st = self.w, self.h, self.rng, self.st
        self.parts.step(dt)
        self.fire.step()
        if t < FACE_CUT:
            self.shot_body(cv, t, dt)
        elif t < 20.5:
            self.shot_face(cv, t, dt)
        elif t < 24.5:
            self.shot_body(cv, t, dt, gore=True)
        elif t < 28.0:
            self.shot_hand(cv, t, dt)
        elif t < 34.0:
            self.shot_angel(cv, t, dt)                                                 # the sky opens: a mourning marble angel comes down (nobody else looks up)
        elif t < 37.5:
            self.shot_eyes(cv, t, dt)                                                  # extreme close-up of his eyes
        elif t < 40.7:
            self.shot_body(cv, t, dt, yank=t - 37.5)                                   # the hand from the pit yanks him in (3.2 s)
        elif t < 41.4:
            cv.clear()                                                                 # torn away: silence, black
        elif t < 49.5:
            self.shot_fall(cv, t, dt)
        else:
            self.shot_end(cv, t, dt)
        if t < 9.5:                                                                   # slow camera moves: push-in on the standing figure, a drift on the face,
            push_in(cv, 1 + 0.10 * t / 9.5, 0.5, 0.45)                                # a push-in on the torso, a long push-in on the reaching hand
        elif t < 20.5:
            push_in(cv, 1 + 0.06 * smooth((t - 9.5) / 11.0), 0.5 + 0.03 * math.sin(t * 0.6), 0.5)
        elif t < 24.5:
            push_in(cv, 1 + 0.12 * smooth((t - 20.5) / 4.0), 0.5, 0.35)
        elif t < 28.0:
            push_in(cv, 1 + 0.16 * smooth((t - 24.5) / 3.5), 0.55, 0.45)
        self.shout(cv, t)
        self.rain.step(t, dt)
        self.rain.draw(cv, t)
        fl = max([math.exp(-(t - c) / 0.09) for c in self.CUTS if c <= t < c + 0.6] + [0.0])
        flash(cv, (255, 200, 150) if t < 31 else (255, 120, 60), 0.85 * fl)
        if t > self.END - 0.7:
            darken(cv, max(0.0, (self.END - t) / 0.7))
        amp = shake_at(t, self.hits, 1.0, 0.28)
        if t < 4.5:
            amp += 1.2 * (1 - t / 4.5)
        if 4.6 < t < 31 and not (24.5 <= t < 28):
            amp += 0.22
        return jolt(rng, amp)

    # -- shots
    def shot_body(self, cv, t, dt, gore=False, sink=0.0, yank=None):
        w, h, rng, st, b = self.w, self.h, self.rng, self.st, self.body
        lit = smooth(t / 2.2) * (1.0 if t < 28 else 1.0 + sink)
        st.paint(cv, lit)
        if yank is not None:                                                            # the golden beam closes behind the angel
            import angel_fx
            angel_fx.sky_gold(cv, t, max(0.0, 1.0 - yank / 2.6), self.rng, st.horizon, st.cx, st.feet)
            angel_fx.god_ray(cv, t, max(0.0, 1.0 - yank / 2.2), st.cx, 0, st.feet + 2, self.rng)
        p, gap = smooth(t / 2.2), 3.3 * smooth((t - 0.5) / 3.8) * (1 + 0.7 * sink + (0.6 if yank is not None else 0.0))
        if t < 3.4:                                                                   # stone and rock are thrown up at the edge of the tear
            reach = st.crack.reach(p)
            for _ in range(3):
                side = rng.choice((-1, 1))
                x = st.cx + side * rng.uniform(0, reach)
                self.parts.add(x, st.cy, side * rng.uniform(1, 9), -rng.uniform(5, 22), rng.uniform(0.7, 1.6), "debris", 26.0)
        st.crack.hairline(cv, p, t, rng, col=(255, 180, 90), leak=(255, 70, 15), rise=0.0) if gap < 0.6 else None
        st.pit(cv, t, p, gap, rng, glow_k=0.55 + 0.45 * smooth(t / 3.0))
        self.embers(t, dt, 14 + 40 * lit)
        by = self.by + int(sink * b.hf * 0.55)
        clip = st.feet + 2 if sink else None
        grid = b.render(5.2, None, self.bx, by, rng) if yank is not None else b.render(t, self.fire, self.bx, by, rng)   # when the hand takes him he is still a boy: head, arms, torso, legs
        if 4.6 < t < 31:                                                                # shins run off the bone like wax
            if rng.random() < 0.5:
                cell = rng.choice([c for c in b.cells if c[2] in "tb" and c[6] > 26] or [None])
                if cell and t - cell[5] > 2.4:
                    self.parts.add(self.bx + cell[0], by + cell[1], rng.uniform(-1, 1), 3.0, rng.uniform(0.6, 1.4), "wax", 14.0)
        if gore:
            self.torso_gore(grid, t, by, dt)
        amp = 0.0 if t < 4.6 else min(1.3, 0.4 + (t - 4.6) * 0.1)
        trem = (lambda i: int(round(math.sin(i * 0.9 + t * 8) * amp + (math.sin(t * 40 + i) * 0.7 if t > 6 else 0))))
        if yank is not None:
            self.yank_body(cv, t, dt, grid, yank, trem)
        else:
            blit_grid(cv, grid, self.bx, by, 1.0, 1.0, trem, clip)
        if sink:
            self.teeth(cv, t, clip, sink)
        self.fire.draw(cv, 0.12, y_max=None)
        if yank is not None:
            self.yank_hand(cv, t, dt, yank)
        self.parts.draw(cv, 0.5)
        if sink:
            for y in range(clip, min(h, clip + 3)):                                    # the stone closes over him
                for x in range(self.bx - 6, self.bx + b.wf + 6):
                    cv.put(x, y, "▓#"[(x + y) % 2], (62, 46, 52), (26, 18, 22))

    def yank_body(self, cv, t, dt, grid, tau, trem):
        """28.0-31.2: a hand rises out of the pit and takes his ankle; he claws at the edge, the fingers slip one by one; he is torn away. ~3 s, abrupt."""
        b, st, rng = self.body, self.st, self.rng
        slips = (1.9, 2.15, 2.4, 2.6, 2.75)
        feet = self.by + b.hf
        pull = 0.03 * abs(math.sin(tau * 17)) * (1 if 0.6 <= tau < 1.9 else 0) + sum(0.09 * smooth((tau - sl) / 0.12) for sl in slips) + 1.3 * smooth((tau - 2.8) / 0.3) ** 2
        s = 1 - 0.6 * min(1.0, pull)
        bottom = feet + (st.cy + 2 - feet) * min(1.3, pull)
        top = int(bottom - b.hf * s)
        if tau < 3.1:
            blit_grid(cv, grid, self.bx + int(b.wf * (1 - s) / 2), top, s, s, trem if pull < 0.2 else None, st.cy + 3)
            import angel_fx                                                                   # the angel does not let go of him: wing and arm are pulled down with him
            ax, ay, wc = self.angel_pose(6.0)
            angel_fx.draw_angel_statue(cv, ax + int(wc * (1 - s) / 2), ay + (top - self.by), int(wc * s), max(0.2, 1.0 - 0.7 * tau / 3.1), 0.6)
        self._y = (bottom, top, s, slips)

    def yank_hand(self, cv, t, dt, tau):
        """The hand and the clawing arms, drawn over the flames."""
        b, st, rng = self.body, self.st, self.rng
        bottom, top, s, slips = self._y
        cx = self.bx + b.wf // 2
        for sd in (-1, 1):                                                              # his arms stretch out to the lip; the fingers slip one by one
            lx, ly = cx + sd * (b.wf // 2 + 5), st.feet + 1
            if 0.7 <= tau < 2.9:
                sx, sy = cx + sd * int(6 * b.s * s * 2), top + int(13 * b.s * s)
                for x, y, d in thick_line((sx, sy), (lx, ly), 1.1):
                    Hand.flesh(cv, x, y, t, 0.5)
                for i in range(5):
                    if tau < slips[i] + 0.02 * sd:
                        for k in range(3):
                            cv.put(lx - sd * k, ly - 2 + i, "=", (214, 190, 170), (90, 30, 24))
                    elif tau < slips[i] + 0.9:                                          # a slipped finger leaves a scrape and sparks
                        d = int((tau - slips[i]) * 12)
                        cv.put(lx + sd * d, ly - 2 + i, "_", (255, 140, 40))
                        if tau - slips[i] < dt * 1.5:
                            self.parts.burst(lx, ly - 2 + i, 6, "spark", 10, 0.5, 18.0)
        if 0.0 <= tau < 3.15:                                                           # the hand from the pit: the same charred, half-skeletal hand as the reaching one
            reach = smooth(tau / 0.5)
            hx = cx - 2
            wy = int(st.cy + 7 - (st.cy + 7 - (bottom - 1)) * reach)
            self.grip_hand(cv, t, tau, cx - 5, 2 * (wy - 1), reach, slips)
            if tau > 0.5:
                self.fire.inject(cx - 5, wy - 3, 0.5)
        if 2.8 <= tau < 2.8 + dt * 1.5:
            self.parts.burst(cx, st.cy, 40, "blood", 22, 1.0, 20.0, up=8)
            self.parts.burst(cx, st.cy, 20, "spark", 24, 0.8, 10.0)

    def grip_hand(self, cv, t, tau, ax, ay, reach, slips):
        """The hand from the abyss round his ankle, drawn in half-block pixels (ay = pixel row of the grip, ax = column of the ankle): forearm up from the pit, the back
        of the hand with four knuckles, four fingers wrapped across the leg (joint creases, bone and a burnt nail at the tips), a thumb over the top. Charred, cracked
        skin with embers glowing in the cracks; the leg is pinched pale under every finger; the fingers slip one by one (slips[0..3], the thumb slips[4]) and let go."""
        import photo_fx
        lw, bh = 4, 4                                                                        # half width of the ankle in px; height of one finger band
        K = 2                                                                                # one logical pixel = K x K screen pixels: a big, finely drawn hand
        up = int(2 * (1 - reach) * 14)                                                       # rises out of the pit
        base = ay // K + up // K

        def put(x, y, c):
            for qy in range(K):
                for qx in range(K):
                    photo_fx.put_pixel(cv, ax + (int(x) - ax) * K + qx, ay + up + (int(y) - base) * K + qy, c)
        flick = 0.75 + 0.25 * math.sin(t * 23)
        def skin(x, y, lit=1.0):
            n1, n2 = _hash(int(x), int(y), 3), _hash(int(x) // 2, int(y) // 2, 9)
            c = mix((30, 20, 18), (96, 78, 70), n1 * 0.55 + 0.25 * lit)
            if n2 > 0.88:                                                                    # a crack, an ember in it
                return mix((255, 90, 18), (255, 190, 70), n1) if (int(t * 6) + int(x) + int(y)) % 4 else (214, 70, 14)
            if n2 > 0.80:
                return mul(c, 0.5)
            return c
        # forearm: from the bottom edge up to the wrist, wide, slightly slanted
        for yy in range(base + 8, base + 8 + (2 * cv.h - ay) // K + 6):
            wx = ax - lw - 6 - (yy - base - 8) // 5
            for dx in range(-4, 5):
                put(wx + dx, yy, skin(wx + dx, yy, 1.0 - abs(dx) / 5.0))
        # back of the hand: a rounded block left of the leg, four knuckle bumps on its upper-right edge
        for yy in range(base - 8, base + 9):
            half = 4 if abs(yy - base) < 6 else 3
            for dx in range(-half, half + 1):
                x = ax - lw - 5 + dx
                put(x, yy, skin(x, yy, 1.0 - abs(dx) / 7.0 + 0.2))
        for i in range(4):                                                                    # tendons on the back of the hand
            for yy in range(base - 6 + i * 3, base + 8):
                put(ax - lw - 8 + i * 2, yy, mul(skin(ax - lw - 8 + i * 2, yy), 0.55))
        # the leg is pinched: pale, indented rings above and below each finger
        for i in range(4):
            y0 = base - 7 + i * (bh + 1)
            if tau < slips[min(i, 3)] + 0.15:
                for dx in range(-lw, lw + 1):
                    put(ax + dx, y0 - 1, (214, 170, 150))
                    put(ax + dx, y0 + bh, (176, 122, 108))
        # four fingers across the leg
        for i in range(4):
            sl = slips[i]
            released = tau - sl
            if released > 0.9:
                continue
            y0 = base - 7 + i * (bh + 1) + (int(released * 24) if released > 0 else 0)                 # a slipping finger drags down
            ln = 2 * lw + 7 - (int(max(0.0, released) * 14) if released > 0 else 0)
            x0 = ax - lw - 3
            for yy in range(bh):
                for k in range(ln):
                    x = x0 + k
                    edge = yy == 0 or yy == bh - 1
                    tip = k >= ln - 3
                    if tip:                                                                    # bone at the tip, a burnt nail on the far end
                        c = (226, 214, 188) if yy < bh - 1 else (150, 130, 112)
                        if k == ln - 1 and yy in (1, 2):
                            c = (60, 52, 50)
                    else:
                        c = skin(x, y0 + yy, 1.0 if yy < 2 else 0.4)
                        if k in (ln // 3, (2 * ln) // 3):                                      # joint creases
                            c = mul(c, 0.4)
                        if k < 3 and yy in (1, 2):                                             # the knuckle: a pale bump
                            c = mix(c, (190, 176, 156), 0.55)
                    if edge:
                        c = mix(c, (255, 120, 40), 0.18 * flick) if yy == bh - 1 else mul(c, 1.15)
                    put(x, y0 + yy, c)
            if 0.0 < released < 0.12:
                self.parts.burst(ax + lw * K, (ay + (y0 - base) * K) // 2, 3, "spark", 9, 0.4, 14.0)
        # the thumb over the top: from the back of the hand diagonally across the leg's edge, a bony tip with a nail
        rt = tau - slips[4]
        if rt < 0.9:
            drag = int(rt * 20) if rt > 0 else 0
            for k in range(11):
                x, y = ax - lw - 3 + k, base - 9 - k // 3 + drag
                for q in range(bh - 1):
                    c = skin(x, y + q) if k < 8 else ((226, 214, 188) if q < 2 else (70, 58, 52))
                    put(x, y + q, c)
        glow(cv, ax, ay // 2 + up // 2 - 2, 16, 8, (255, 90, 20), 0.22 * flick)

    @staticmethod
    def pale(cv, x, y, t):
        """The abyss hand: grey, dead skin with black cracks and a hot glow in them."""
        n = _hash(x, y)
        if n > 0.86:
            cv.put(x, y, "/\\~"[int(n * 30) % 3], (255, 120, 40), (40, 6, 2))
        else:
            cv.put(x, y, "%#:▒"[int(n * 40) % 4], mix((228, 222, 236), (150, 142, 162), n), mix((120, 112, 134), (60, 54, 72), n))

    def teeth(self, cv, t, y, sink):
        b = self.body
        for k, x in enumerate(range(self.bx - 14, self.bx + b.wf + 14)):
            hgt = int((1 + 3 * sink) * (0.5 + 0.5 * _hash(x, 3)) * (1 if k % 2 else 0.6))
            for j in range(hgt):
                cv.put(x, y - 1 - j, "^" if j == hgt - 1 else "#", (255, 150, 60) if j == hgt - 1 else (96, 76, 84), (44, 30, 36))

    def torso_gore(self, grid, t, by, dt):
        b, rng = self.body, self.rng
        hf, wf, s = b.hf, b.wf, b.s
        # the belly splits (20.6 -> 22.4) and what is inside boils
        o = smooth((t - 20.6) / 1.4)
        if o > 0:
            xc = wf // 2
            for yy in range(int(16 * s), int(23.4 * s)):
                half = int(o * (1 + 3 * s) * (0.6 + 0.4 * math.sin(yy * 1.1)))
                for x in range(xc - half - 1, xc + half + 2):
                    if 0 <= x < wf and 0 <= yy < hf:
                        edge = abs(x - xc) >= half
                        n = _hash(x, yy)
                        if edge:
                            grid[yy][x] = ("#", (190, 30, 28), (90, 10, 10))
                        else:
                            bub = (t * 5 + n * 9 + yy * 0.4) % 1.0 < 0.3
                            grid[yy][x] = ("oO°0"[int(n * 4)] if bub else "~", (255, 235, 140) if bub else fire_rgb(0.6 + 0.3 * n), mul(fire_rgb(0.5 + 0.3 * n), 0.55))
            if rng.random() < 0.55:
                self.parts.add(self.bx + xc, by + int(19 * s), rng.uniform(-8, 8), -rng.uniform(8, 20), rng.uniform(0.5, 1.2), "fat", 30.0)
        # the veins stand out like wire (21.4 -> 23.6), then burst all at once
        if 21.4 <= t < 23.6:
            k = smooth((t - 21.4) / 1.2)
            for path in self.veins:
                for x, y in path:
                    if 0 <= y < hf and 0 <= x < wf and grid[y][x] is not None:
                        thr = 0.5 + 0.5 * math.sin(t * 16 + x * 0.3)
                        grid[y][x] = ("|!I"[(x + y) % 3], mix(grid[y][x][1], (255, 70 + 90 * thr, 70), k), mix(grid[y][x][2], (170, 20, 24), k))
        if t >= 23.6:
            if not self.burst:
                self.burst = True
                for path in self.veins:
                    for x, y in path[::2]:
                        self.parts.burst(self.bx + x, by + y, 4, "blood", 18, 1.1, 24.0)
            for path in self.veins:
                for x, y in path:
                    if 0 <= y < hf and 0 <= x < wf and grid[y][x] is not None:
                        grid[y][x] = (":", (120, 10, 12), (28, 2, 4))
            if t < 24.2 and rng.random() < 0.8:
                for path in rng.sample(self.veins, 3):
                    x, y = rng.choice(path)
                    self.parts.burst(self.bx + x, by + y, 5, "blood", 14, 0.9, 24.0)

    def shot_face(self, cv, t, dt):
        w, h, rng, st, f = self.w, self.h, self.rng, self.st, self.face
        cv.clear((20, 3, 3))
        for y in range(h):
            for x in range(w):
                v = 0.10 + 0.55 * (y / float(h)) ** 2.2 + 0.05 * math.sin(x * 0.2 + t * 3)
                cv.bg[y * w + x] = mul(fire_rgb(v), 0.55)
        self.embers(t, dt, 60)
        if f.P is None:                                                               # a terminal too small for the portrait: fire and screaming only
            self.fire.inject(self.st.cx, h - 1, 1.0)
            for x in range(self.fire.x0, self.fire.x0 + self.fire.w):
                self.fire.inject(x, h - 1, 0.9)
            self.fire.draw(cv, 0.12)
            cv.text(w // 2 - 8, h // 2 - 2, "A" * 16 if int(t * 8) % 2 else "AAAAAAAAAAAAAH", (255, 90, 70))
            return
        ox, oy = (w - f.W) // 2, max(0, (st.A - f.H) // 2)
        for x in range(self.fire.x0, self.fire.x0 + self.fire.w):                     # a wall of fire behind and beside the head
            if abs(x - w // 2) > f.W // 2 - 4 or t < 12.5:
                self.fire.inject(x, h - 1, 0.55 + 0.4 * rng.random())
        g = f.render(t, rng, self.parts, self.fire, ox, oy)
        trem = (lambda i: int(round(math.sin(t * 37 + i) * (1.0 if t > 9.8 else 0))))
        blit_grid(cv, g, ox, oy, 1.0, 1.0, trem)
        if FACE_CUT + 0.8 <= t < 12.5:                                                # his voice splits in two: a second, wrong face flickers over his
            for y in range(f.H):
                for x in range(f.W):
                    if _hash(x, y, int(t * 12)) < 0.22:
                        c = g[y][x]
                        cv.put(ox + x + 4, oy + y - 1, c[0], mix(c[1], (170, 60, 255), 0.65), mul(c[2], 0.5))
        if 15.0 <= t < 15.2 or (16.1 <= t < 16.18):
            pass
        if 16.1 <= t and not self.popped:
            self.popped = True
            for e in f.EYES:
                ex, ey = f.lm(e)
                self.parts.burst(ox + ex, oy + ey, 40, "fat", 24, 1.0, 20.0, drag=0.5)
                self.parts.burst(ox + ex, oy + ey, 14, "blood", 16, 1.0, 24.0)
        if 17.5 <= t < 18.8:                                                          # skin comes off in strips
            if rng.random() < 0.7:
                self.parts.add(ox + rng.randint(f.W // 3, 2 * f.W // 3), oy + int(0.5 * f.H), rng.uniform(-6, 6), -rng.uniform(2, 9), 1.0, "blood", 20.0, ch="~")
        self.fire.draw(cv, 0.10)
        self.parts.draw(cv, 0.5)
        if 9.8 <= t < 12.5 or 18.4 <= t < 20.5:                                       # the scream, as text, on both sides
            txt = "".join(rng.choice("AAAAAAH") for _ in range(22))
            col = (255, 80 + int(60 * rng.random()), 70)
            cv.text(max(0, ox - 24), oy + f.H // 2 + rng.randint(-1, 1), txt[:max(2, ox - 2)], col)
            cv.text(min(w - 1, ox + f.W + 2), oy + f.H // 2 + rng.randint(-1, 1), txt[:max(0, w - ox - f.W - 3)], col)

    def sky_light(self, cv, p):
        """The light that pours out of the torn sky tints the whole hall."""
        for y in range(0, self.st.horizon):
            for x in range(self.w):
                cv.light(x, y, (180, 160, 130), 0.10 * p, 0.2)

    def cult_watch(self, cv, t):
        """The congregation stands round the pit in the dark and watches him burn. They do not look up, they do not see the angel."""
        st = self.st
        for x in range(8, self.w - 8, 13):
            if abs(x - st.cx) < 24:
                continue
            y = st.horizon + 3 + int(_hash(x, 2) * 4)
            sway = int(math.sin(t * 1.3 + x) * 0.7 + 0.5)
            cv.put(x + sway, y - 2, "o", (60, 50, 56), (10, 6, 8))
            cv.put(x + sway, y - 1, "A", (92, 80, 88), (10, 6, 8))
            cv.put(x + sway, y, "M", (74, 64, 72), (10, 6, 8))
            cv.light(x, y - 1, (160, 70, 20), 0.18, 0.3)

    def lyric_zones(self, t):
        """Where the big lyric letters may stand: next to Noah's face, never on it (left/right, high/low; the eye close-up: above and below the eyes)."""
        w, h, cx = self.w, self.h, self.st.cx
        if 34.0 <= t < 37.5:                                                                  # the eyes fill the width: the gap between them is the only free place
            ew = int(min(w * 0.17, 44) * 1.28)
            g = max(10, int((1.45 * ew - ew) - 2))
            return [(w // 2 - g, 1, w // 2 + g, h // 2), (w // 2 - g, h // 2 - 3, w // 2 + g, h - 6)]
        m = 17 + int(w * 0.02)                                                                # left and right of the standing boy, full height; never in the speech column
        try:
            import speech
            right = w - 2 - ((speech.panel_width(w) + 2) if w >= speech.PANEL_MIN_COLS else 0)
        except ImportError:
            right = w - 2
        return [(2, 1, cx - m, h - 6), (cx + m, 1, right, h - 6)]

    def angel_pose(self, tau):
        """Where the angel is (x, y, width in cells) at angel time tau: it comes down through the ray like snowfall and comes to rest on Noah."""
        b = self.body
        wc = int(b.wf * 2.5)
        rest_x = self.bx + b.wf // 2 - int(wc * 0.13)
        rest_y = self.by + 4
        d = smooth((tau - 1.6) / 3.2)
        y = int(-wc * 0.5 + (rest_y + wc * 0.5) * d + math.sin(tau * 1.1) * 1.5 * (1 - d))
        x = int(rest_x + math.sin(tau * 0.9) * 5 * (1 - d))
        return x, y, wc

    def shot_angel(self, cv, t, dt):
        """28-34: golden clouds gather and break open, a god-ray falls; the angel (the Angel of Grief, from the photo) comes down through it like snowfall and comes to
        rest on Noah, draped over him as it lies on the grave. It is his guardian angel, it could not keep him. Its shoulders shake, one marble tear. The cult does not see it."""
        import angel_fx
        st, rng, b, h, w = self.st, self.rng, self.body, self.h, self.w
        tau = t - 28.0
        st.paint(cv, 1.0)
        angel_fx.sky_gold(cv, t, smooth(tau / 1.6), rng, st.horizon, st.cx, st.feet)
        st.pit(cv, t, 1.0, 3.6, rng, glow_k=0.8)
        self.embers(t, dt, 40)
        ray = smooth((tau - 1.0) / 1.0)
        angel_fx.god_ray(cv, t, ray, st.cx, 0, st.feet + 2, rng)
        self.cult_watch(cv, t)
        grid = b.render(t, self.fire, self.bx, self.by, rng)
        trem = lambda i: int(round(math.sin(i * 0.9 + t * 8) * 0.9 + math.sin(t * 40 + i) * 0.5))
        blit_grid(cv, grid, self.bx, self.by, 1.0, 1.0, trem)
        self.fire.draw(cv, 0.14, solid=0.62)
        x, y, wc = self.angel_pose(tau)
        shake = (math.sin(tau * 19) * 0.7) if tau > 4.4 else 0.0                       # its shoulders shake once it lies on him
        angel_fx.draw_angel_statue(cv, x + int(round(shake)), y, wc, 0.65 + 0.45 * ray, 0.5)
        for _ in range(int(2 + 6 * ray)):                                                 # golden dust in the beam
            self.parts.add(st.cx + rng.uniform(-14, 14), rng.uniform(0, h * 0.5), rng.uniform(-1, 1), rng.uniform(1, 4), 3.0, "gold")
        if 4.2 < tau < 5.9:                                                                # one marble tear falls into the fire
            ty = int(y + wc * 0.2 + (tau - 4.2) * 13)
            cv.put(x + int(wc * 0.18), ty, "o", (250, 248, 240), (190, 190, 200))
            if ty >= self.by + int(b.hf * 0.5):
                self.parts.burst(x + int(wc * 0.18), ty, 6, "smoke", 5, 0.8, -4.0)
        self.parts.draw(cv, 0.5)
        push_in(cv, 1.0 + 0.08 * smooth(tau / 6.0), 0.5, 0.4)

    def shot_eyes(self, cv, t, dt):
        import angel_fx
        angel_fx.draw_eyes(cv, t - 34.0, smooth((t - 34.0) / 3.5), self.rng)

    def shot_hand(self, cv, t, dt):
        w, h, rng, st = self.w, self.h, self.rng, self.st
        st.paint(cv, 1.0)
        st.pit(cv, t, 1.0, 3.6, rng, glow_k=0.9)
        grid = self.body.render(t, None, 0, 0, rng)                                   # he is still standing in the dark behind it
        blit_grid(cv, grid, self.bx, self.by, 1.0, 1.0)
        darken(cv, 0.4)
        self.embers(t, dt, 40)
        sc = min(1.4, max(0.5, h / 40.0))
        cx, cy = st.cx + 4, int(st.A * 0.55)
        for i, x, y in self.hand.snap_points(t, cx, cy, sc):
            if t >= self.hand.SNAPS[i] and i not in self.snapped:
                self.snapped.add(i)
                self.parts.burst(x, y, 10, "bone", 12, 1.3, 26.0)
                self.parts.burst(x, y, 6, "ember", 9, 0.8, 5.0)
        self.hand.draw(cv, t, cx, cy, sc, rng)
        self.parts.draw(cv, 0.5)
        for i, tt in self.hand.SNAPS.items():                                         # tick.
            if tt <= t < tt + 0.35:
                cv.text(cx + 6 + 8 * i, int(st.A * 0.2) + i, "tick", (255, 255, 255))

    def abyss(self, cv, t, k=1.0, speed=1.0):
        w, h = self.w, self.h
        for i, r in enumerate(self.rad):
            v = (0.10 + 0.55 * math.exp(-(r / 0.55) ** 2) + 0.05) * k
            band = 0.5 + 0.5 * math.sin(r * 30 - t * 11 * speed)
            v *= 0.65 + 0.5 * band
            if r > 0.75:
                v *= max(0.0, 1 - (r - 0.75) * 1.5)
            c = fire_rgb(v)
            cv.bg[i] = mul(c, 0.55)
            if band > 0.8 and v > 0.12:
                cv.ch[i], cv.fg[i] = "~:"[i % 2], mul(c, 1.1)
            else:
                cv.fg[i] = c

    def shot_fall(self, cv, t, dt):
        """31.9-40.0: the maw seen from above, a speck of burning Noah falls through it (abyss_fx) and lands in the hell at the bottom. No screams: he is far away."""
        b, rng = self.body, self.rng
        grid = b.render(t, None, 0, 0, rng)

        def noah(cv, cx, cy, size, tau):
            size *= 0.45                                                                 # he is already far below
            ow, oh = b.wf * size, b.hf * size
            x0, y0 = int(cx + math.sin(tau * 2.2) * 3 * (1 - size) - ow / 2), int(cy - oh / 2)
            for yy in range(0, b.hf, max(1, int(1 / max(size, 0.08)))):                  # the fire follows him up the shaft
                for xx in range(0, b.wf, max(1, int(1 / max(size, 0.08)))):
                    if grid[yy][xx] is not None and rng.random() < 0.5:
                        self.ab.fire.inject(int(x0 + xx * size), int(y0 + yy * size), 0.95)
            if ow >= 1.5:
                blit_grid(cv, grid, x0, y0, size, size)
            else:
                cv.put(int(cx), int(cy), "@", (255, 220, 120), (230, 80, 10))
            n = int(26 * size)                                                            # the scream falls away
            if n > 1:
                cv.text(int(cx + ow / 2) + 3, int(cy) - 1, "aaaaaaaaaaaaaaaaaaaaaaaaaah"[:n], mul((255, 130, 100), 0.4 + size))
        self.shake_fall = self.ab.draw(cv, (t - 41.4) * 1.25, dt, noah)

    def shot_end(self, cv, t, dt):
        w, h, rng, st = self.w, self.h, self.rng, self.st
        if t < 50.9:                                                                  # silence: the shaft goes dark, one ember
            cv.clear()
            k = max(0.0, 1.0 - (t - 49.5) / 0.6)
            self.abyss(cv, t, 0.5 * k, 0.2)
            darken(cv, 0.15 + 0.85 * k)
            tt = t - 49.5
            ey = int(h * 0.50 - tt * 2.0)
            if 0.5 < tt < 1.15:                                                       # one last glint of the cube, far down
                draw_cube(cv, st.cx, int(h * 0.50 - tt * 2.0) + 3, 2.2, t * 2, (120, 255, 225), 0.9 * math.sin(math.pi * (tt - 0.5) / 0.65))
            if tt < 1.3 and (tt < 0.8 or int(tt * 18) % 2 == 0):
                cv.put(st.cx, ey, "*" if tt < 0.5 else ".", (255, 150 - int(70 * tt), 40), (60, 10, 0))
                cv.light(st.cx, ey, (160, 50, 10), 0.4, 0.0)
        else:                                                                         # the floor is closed; a scorch mark in the shape of a boy
            tt = t - 50.9
            st.paint(cv, 0.35 * max(0.0, 1 - tt / 1.2))
            self.body_scorch(cv, tt)
            if tt < 0.9:
                self.parts.add(self.bx + self.body.wf // 2, st.feet - 2, 0, -3, 1.2, "ember", -1.0, ch="*")
            self.parts.draw(cv, 0.3)

    def body_scorch(self, cv, tt):
        b = self.body
        self.st.scorch(cv, b, self.bx, self.st.feet + 2 - b.hf + 6, max(0.0, 1 - tt / 1.3))


BURN_CUES = [(0.0, "ground-rumble"), (0.4, "stone-split"), (1.6, "hell-roar"), (3.6, "growl-demon"), (4.4, "fire-ignite"), (5.2, "flesh-burn"),
             (6.2, "fire-roar"), (7.0, "scream-distorted-1"), (8.4, "blood-boil"), (9.5, "scream-fire"), (10.4, "growl-demon"),
             (12.5, "fire-ignite"), (13.4, "fire-roar"), (15.2, "bubbles-gurgle"), (16.1, "blood-spurt"), (17.5, "bone-crack-2"),
             (18.4, "scream-distorted-2"), (20.5, "flesh-burn"), (21.2, "blood-boil"), (22.4, "bubbles-gurgle"), (23.6, "blood-spurt"),
             (24.6, "gurgle-breath"), (26.3, "bone-crack-1"), (26.9, "bone-crack-2"), (27.5, "bone-crack-1"),
             (28.6, "riser-reverse"), (29.6, "electric-surge"), (31.5, "lake-whispers"), (33.0, "sub-drop"),                    # the sky opens, the angel comes down
             (34.2, "sob-small"), (34.7, "bubbles-gurgle"), (35.2, "fire-ignite"), (36.0, "gurgle-breath"),                     # his eyes
             (38.0, "stone-split"), (38.2, "bone-crack-1"), (39.1, "growl-demon"), (39.5, "stone-split"), (40.4, "scream-falling-1"),   # the hand: grab, slip, torn away
             (41.5, "fall-wind"), (45.1, "hell-roar"), (46.7, "growl-demon"), (48.3, "impact-boom-huge"), (48.5, "fire-roar"),         # (40.7-41.4: silence)
             (49.3, "sub-drop"), (50.9, "impact-boom-huge"),
             (12.0, "lake-whispers"), (16.8, "static-burst"), (23.0, "lake-whispers")]    # the word rain: the soft voices come and go (an audio agent will tune)


class AngelDemo:
    """The angel and the eyes on their own (9.5 s): python3 play.py --mika-ending --only angel"""
    END = 9.5

    def __init__(self, w, h, rng):
        self.bs = BurnScene(w, h, rng)

    def draw(self, cv, t, dt):
        bs = self.bs
        bs.parts.step(dt)
        bs.fire.step()
        if t < 6.0:
            bs.shot_angel(cv, 28.0 + t, dt)
        else:
            bs.shot_eyes(cv, 34.0 + (t - 6.0), dt)
        return 0, 0


ANGEL_CUES = [(0.6, "riser-reverse"), (1.6, "electric-surge"), (3.5, "lake-whispers"), (5.0, "sub-drop"), (6.2, "sob-small"), (6.7, "bubbles-gurgle"), (7.2, "fire-ignite")]


def burn_captions(lines):
    """The 14 lines of mika.burn.lines on their beats; any other number of lines is spread evenly over the scene."""
    beats = [(0.3, 3.0), (3.0, 4.9), (5.0, 9.3), (9.6, 12.4), (12.6, 17.4), (20.6, 22.3), (22.4, 24.4), (24.6, 26.3), (26.4, 28.1), (28.8, 33.6), (37.6, 40.5),
             (41.6, 44.5), (45.0, 49.0), (51.0, 52.7)]
    if len(lines) == len(beats):
        return [(a, b, l) for (a, b), l in zip(beats, lines)]
    return spread(lines, 0.3, 52.7)
