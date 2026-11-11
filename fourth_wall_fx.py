"""fourth_wall_fx.py - the 4th-wall cinematic of Mika's ending (46 s), drawn in truecolor ASCII and sent as diffs by noah_gore_fx.play().

    FourthScene  the tesseract spins up faster and faster and gets brighter until it bleeds white, the screen shakes, the window frame
                 cracks like glass and the shards peel off and fall away to a different layer (a "real" terminal), game text spills out,
                 the cube talks to the player with data it can read in-process, fake kernel / process / file / hex output scrolls,
                 a fake "rm -rf" is PRINTED, then signal lost, static and a hard cut to black.
    sysinfo()    the only reads: getpass.getuser(), socket.gethostname(), the clock, the terminal size, os.getcwd() and the read-only
                 files /proc/uptime and /proc/loadavg.
    run(ctx)     what mika_ending.fourth_wall calls.
Strictly cosmetic: it writes escape sequences and text to ctx.out and nothing else - no subprocess, no file writes, no network, no
notify-send, nothing printed here is ever executed. The window title is changed with OSC 2 and set back to "FOLK" at the end
(the original cannot be read back); the window shake is the existing best-effort ultra_fx.WindowShake (xterm window ops, FOLK_WINSHAKE=0 opts out).
Everything on screen is a pure function of the scene time t and the seed, so a test can run it headless with a fake sleep.
"""
import chain
import atexit
import bisect
import getpass
import json
import math
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import time

import noah_gore_fx as G
import ultra_fx

_T0 = time.time()                             # the game process starts about here: "you have been playing for ..."
FADE_IN = 1.8                                 # seconds the window frame and stars need to come up around the cube that hangs over the lake
CRACK_T, FALL_T, B_T = 11.0, 14.0, 13.0       # cracks start, first shard falls, the terminal layer underneath exists
LOST_T, STATIC_T, OFF_T, BLACK_T = 39.5, 41.2, 43.2, 43.4
WHITE, ICE, CYAN, GREEN, AMBER, RED = (255, 255, 255), (200, 240, 255), (90, 235, 255), (110, 255, 150), (255, 190, 80), (255, 70, 60)
SPEEDS = (0.31, 0.23, 0.9, 0.41, 0.63, 0.77)
HUES = [(-1.5, (130, 70, 255)), (-0.5, (60, 120, 255)), (0.5, (60, 230, 255)), (1.5, (255, 120, 240))]

# (time, centre x, centre y, scale, brightness) of the cube; spin speed in rad/s; everything else as (time, value)
CUBE = [(0, .5, .45, .35, .55), (4, .5, .5, .55, .55), (8, .5, .5, .8, .6), (10.8, .5, .5, 1.0, .95), (11.0, .5, .5, 1.1, 1.0), (13.5, .5, .5, 1.0, 1.0),
        (17, .5, .5, .9, .9), (19.5, .82, .34, .42, .7), (33, .82, .34, .5, .75), (36, .82, .34, .6, .9), (38.5, .5, .5, 1.1, 1.0),
        (39.4, .5, .5, 1.5, 1.0), (39.5, .5, .5, .25, .6), (41.0, .5, .5, .1, .3), (41.2, .5, .5, .0, .0)]
SPIN = [(0, .5), (4, 1.4), (8, 3.5), (10.8, 6.5), (13.5, 8), (17, 6), (19.5, 4), (33, 5), (36, 6), (38.5, 11), (39.4, 18), (41, 8)]
SPLIT = [(0, 0), (7.5, 0), (9, 1), (11, 1), (14, 2), (18, 1), (19.5, 0), (24.9, 0), (25.3, 2), (26, 0), (27, 0), (29, 1), (31, 0), (33, 1),
         (35.6, 2), (36.2, 0), (38, 2), (39.4, 4), (41, 3), (41.2, 0)]
TEAR = [(0, 0), (8, 0), (8.4, .4), (9, .1), (10.4, .6), (11, .5), (13, .15), (14.5, .4), (17, .2), (19.5, 0), (20.6, .5), (21, 0), (25.2, .8), (26, 0), (28.5, .3),
        (29.8, 0), (32.8, .6), (35.6, .9), (36.2, .1), (38, .3), (39.4, 1), (41.2, .6), (43, .8)]
FLASH = [(0, 0), (8, 0), (10.8, .85), (11.0, 1.0), (11.15, .9), (12.2, 0), (13.55, 0), (13.6, .35), (14.0, 0), (25.3, .25), (25.5, 0), (38.0, 0),
         (39.3, .5), (39.45, 1.0), (39.55, 1.0), (40.3, 0)]
TREMOR = [(0, 0), (5.5, 0), (8, .25), (10.9, 1.0), (14, .8), (17, .3), (19, .1), (33, .1), (35.6, .5), (38, 1.0), (39.4, 1.8), (39.5, 0), (41.2, 0)]
HITS = [(11.0, 1.2), (13.6, .7), (14.4, .5), (15.3, .5), (16.2, .4), (25.3, .5), (33.0, .4), (35.6, .6), (39.5, 1.4)]
INVERT = [(10.9, 11.1), (25.2, 25.4), (35.6, 35.9), (39.45, 39.65)]
BELLS = (11.0, 25.3, 39.5)
TITLES = [(0, "FOLK"), (11.0, "FOLK (not responding)"), (13.5, "tesseract"), (17.5, "tesseract - {user}@{host}"), (22.0, "i can see you, {user}"),
          (28.0, "kernel panic - not syncing"), (31.0, "{user}@{host}: ~"), (36.0, "???"), (39.0, "SIGNAL LOST")]
CUES = [(0.0, "tesseract-spin-up"), (3.2, "riser-reverse"), (6.0, "electric-surge"), (8.2, "glitch-burst"), (10.2, "riser-reverse"), (11.0, "impact-boom-huge"),
        (11.05, "glass-crack"), (13.6, "glass-crack"), (14.2, "static-burst"), (15.4, "glass-crack"), (16.0, "sub-drop"), (16.6, "glitch-burst"),
        (17.2, "typing-fast"), (21.0, "system-error-beep"), (25.2, "electric-surge"), (25.6, "system-error-beep"), (26.6, "glitch-burst"),
        (27.4, "typing-fast"), (29.0, "system-error-beep"), (31.0, "typing-fast"), (31.5, "glitch-burst"), (33.0, "electric-surge"), (33.8, "typing-fast"),
        (35.6, "static-burst"), (36.2, "riser-reverse"), (38.0, "electric-surge"), (39.4, "glitch-burst"), (39.5, "impact-boom-huge"),
        (40.2, "static-burst"), (41.8, "system-error-beep")]       # nothing at the switch-off: it is silent
CUES += [(STATIC_T + dt_, n_) for dt_, n_ in ((3.0, "electric-surge"), (8.0, "glitch-burst"), (12.5, "static-burst"), (16.0, "system-error-beep"),
                                              (19.5, "electric-surge"), (22.5, "glitch-burst"))]      # low-level hum under the error screen
CAPTION_TIMES = [(0.5, 3.5), (3.6, 6.2), (6.4, 9.0), (9.2, 11.0), (11.2, 13.6), (13.8, 16.8), (37.0, 39.2), (41.4, 43.0)]


STATIC_LEN = 25.0                             # the static / error screen: no music (Mika's song is gone), only hum and glitches
D, K = 8.0, 27.0                              # the middle (talk) part is stretched: everything from K on happens D seconds later


def S(t):
    return t + D if t >= K else t


def _st(tab):
    return [(S(r[0]),) + tuple(r[1:]) for r in tab]


CUBE, SPIN, SPLIT, TEAR, FLASH, TREMOR, HITS, TITLES, CUES = (_st(x) for x in (CUBE, SPIN, SPLIT, TEAR, FLASH, TREMOR, HITS, TITLES, CUES))
INVERT = [(S(a), S(b)) for a, b in INVERT]
BELLS = tuple(S(x) for x in BELLS)
CAPTION_TIMES = [(S(a), S(b)) for a, b in CAPTION_TIMES]
LOST_T, STATIC_T = S(39.5), S(41.2)
OFF_T = STATIC_T + STATIC_LEN                        # the classic CRT switch-off: a white band squeezes to a line, the line shrinks to a dot ...
BLACK_T = OFF_T + 0.7                         # ... and then an abrupt black, no sound; the credits follow
SECONDS = BLACK_T + 0.3
FULL_ENV = "FOLK_FULLSCREEN"                  # =0: no automatic fullscreen


def captions(lines):
    return [(a, b, t) for (a, b), t in zip(CAPTION_TIMES, lines)]


def kf(keys, t):
    """Smoothstep interpolation through [(time, v...)] keyframes; one value or a tuple."""
    if t <= keys[0][0]:
        return keys[0][1:] if len(keys[0]) > 2 else keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            f = G.smooth((t - a[0]) / (b[0] - a[0])) if b[0] > a[0] else 1.0
            v = tuple(x + (y - x) * f for x, y in zip(a[1:], b[1:]))
            return v if len(v) > 1 else v[0]
    return keys[-1][1:] if len(keys[-1]) > 2 else keys[-1][1]


# ---------------------------------------------------------------- what the cube may know (all read-only, in-process)
def _clean(s, n=20, default="you"):
    return re.sub(r"[^A-Za-z0-9._-]", "", str(s))[:n] or default           # never let a name inject control characters


def _read(path):
    try:
        with open(path, "r") as fh:
            return fh.read(256)
    except (OSError, ValueError):
        return ""


def sysinfo(size, now=None):
    try:
        user = getpass.getuser()
    except Exception:
        user = "you"
    try:
        host = socket.gethostname()
    except OSError:
        host = "this-machine"
    try:
        up = float(_read("/proc/uptime").split()[0])
    except (IndexError, ValueError):
        up = 0.0
    d, h, m = int(up // 86400), int(up // 3600 % 24), int(up // 60 % 60)
    cwd = ""
    try:
        cwd = os.path.basename(os.getcwd())
    except OSError:
        pass
    load = " ".join(_read("/proc/loadavg").split()[:3]) or "?"
    t = time.localtime(now)
    return {"user": _clean(user), "host": _clean(host, 30, "this-machine"), "time": time.strftime("%H:%M:%S", t),
            "cols": size[0], "rows": size[1], "cwd": _clean(cwd, 30, "somewhere"), "uptime": ("%dd " % d if d else "") + "%dh %02dm" % (h, m),
            "load": re.sub(r"[^0-9. ]", "", load)[:20] or "?", "up_s": up,
            "mon": time.strftime("%b %d", t), "greeting": greeting(t.tm_hour), "session": span(time.time() - _T0)}


def greeting(hour):
    return "good morning" if 5 <= hour < 12 else "good afternoon" if 12 <= hour < 18 else "good evening" if 18 <= hour < 23 else "it is very late"


def span(sec):
    sec = int(max(0, sec))
    return ("%dh " % (sec // 3600) if sec >= 3600 else "") + ("%dm " % (sec // 60 % 60) if sec >= 60 else "") + "%ds" % (sec % 60)


def fill(s, info):
    return re.sub(r"\{(\w+)\}", lambda m: str(info.get(m.group(1), m.group(0))), s)


# ---------------------------------------------------------------- the terminal layer underneath: scripted lines, pure function of t
def build_script(info, texts, rng):
    """[(time, text, rgb, chars/second or 0)] sorted by time. Typed lines grow, streamed lines just appear."""
    ev = []

    def lines(key):
        return [fill(x, info) for x in (texts.get(key) or []) if x]

    def stream(t0, t1, items, rgb=None):
        for k, x in enumerate(items):
            col = rgb or (RED if (x.isupper() and any(c.isalpha() for c in x)) else (205, 210, 215))
            ev.append((t0 + (t1 - t0) * k / max(1, len(items)), x, col, 0))

    def typed(t, x, rgb, cps=40):
        ev.append((t, x, rgb, cps))
    prompt = "%s@%s:~$ " % (info["user"], info["host"])
    stream(13.0, 17.0, lines("mika.fourth.spill"))
    talk = lines("mika.fourth.talk")
    t, avail = 17.4, S(K) - 0.8 - 17.4                                      # the cube talks until the fake system output starts
    cps = max(40.0, min(75.0, sum(len(x) for x in talk) / max(1.0, avail - 0.35 * len(talk))))
    for x in talk:
        typed(t, x, CYAN if x.startswith("tesseract") else WHITE, cps)
        t += len(x) / cps + 0.35
    base = info.get("up_s", 0.0) + 4000.0
    kern, ts = [], base
    for k in range(40):
        ts += rng.uniform(0.0002, 0.9)
        x = lines("mika.fourth.kernel")
        if x:
            kern.append("[%12.6f] %s" % (ts, x[k % len(x)]))
    stream(S(27.0), S(29.5), kern, AMBER)
    stream(S(29.5), S(31.0), [prompt + "ps aux | grep " + info["user"]] + lines("mika.fourth.procs"), GREEN)
    names = lines("mika.fourth.files") or ["file"]
    stream(S(31.0), S(33.0), ["-rw-r--r-- 1 %s %s %7d %s %s" % (info["user"], info["user"], rng.randrange(120, 9999999), info["mon"], "/home/%s/%s" % (info["user"], names[k % len(names)]))
                              for k in range(48)], (150, 175, 160))
    rm = fill((texts.get("mika.fourth.rm") or "rm -rf /home/{user}/*"), info)
    typed(S(33.0), prompt + rm, (255, 255, 255), 28)
    stream(S(34.3), S(35.6), ["removed '/home/%s/%s'" % (info["user"], names[k % len(names)]) for k in range(42)], RED)
    ev.append((S(35.7), "rm: 0 files remaining. goodbye, %s." % info["user"], RED, 0))
    for k, x in enumerate(lines("mika.fourth.joke")):
        typed(S(36.3 + 0.7 * k), x, WHITE, 35)
    secret = " %s@%s %s " % (info["user"], info["host"], info["cwd"])
    hexl = []
    for k in range(60):
        row = bytes(rng.randrange(256) for _ in range(16))
        if rng.random() < 0.35:
            o = rng.randrange(len(secret))
            chunk = (secret * 3)[o:o + 10].encode("ascii", "replace")
            row = row[:3] + chunk + row[3 + len(chunk):]
        row = row[:16]
        hexl.append("0x%08x  %s  |%s|" % (0x7ffd0000 + 16 * k, " ".join("%02x" % b for b in row), "".join(chr(b) if 32 <= b < 127 else "." for b in row)))
    stream(S(37.6), S(39.4), hexl, (130, 255, 190))
    for k, x in enumerate(lines("mika.fourth.lost")):
        ev.append((LOST_T + 0.2 + 0.5 * k, x, RED, 0))
    ev.sort(key=lambda e: e[0])
    return ev


# ---------------------------------------------------------------- the scene
class FourthScene:
    def __init__(self, w, h, rng, info=None, texts=None, out=None, wind=None):
        self.w, self.h, self.rng = w, h, rng
        self.info = info or sysinfo((w, h + 1))
        self.out, self.wind = out, wind
        self.err = [fill(x, self.info) for x in ((texts or {}).get("mika.fourth.err") or []) if x] + self.lost_lines_of(texts or {})
        self.script = build_script(self.info, texts or {}, random.Random(5))
        self.times = [e[0] for e in self.script]
        self.phase, self.last_t = 0.0, 0.0
        self.trail = {}
        self.title_i, self.bell_i = -1, 0
        self.scale = min(h * 0.46, w * 0.23)
        self.build_world(texts or {})

    # -- the "game" layer A (frame, stars, story text) and the glass: shards, facets, crack lines
    def build_world(self, texts):
        w, h, rng = self.w, self.h, random.Random(11)
        cv = G.Canvas(w, h)
        for _ in range(w * h // 70):
            cv.put(rng.randrange(w), rng.randrange(h), rng.choice(".·'`"), (50, 55, 75))
        spill = [x for x in (texts.get("mika.fourth.spill") or [])][:5]
        for k, x in enumerate(spill):
            cv.text(max(2, w // 2 - 30), max(2, h // 2 - 12 + k * 2), x[:w - 4], (120, 125, 140))
        cv.text(2, 0, " FOLK  -  chapter 7 ", (230, 230, 240), (36, 36, 48))
        for x in range(w):
            cv.put(x, 0, cv.ch[x] if x < 22 else " ", (230, 230, 240), (36, 36, 48))
            cv.put(x, h - 1, "=", (70, 70, 90), (8, 8, 12))
        cv.text(w - 8, 0, "_ [] x ", (230, 230, 240), (36, 36, 48))
        for y in range(1, h - 1):
            cv.put(0, y, "|", (70, 70, 90), (8, 8, 12))
            cv.put(w - 1, y, "|", (70, 70, 90), (8, 8, 12))
        self.A = cv
        n = max(14, min(46, w * h // 230))
        seeds = [(w / 2.0 * (1 + math.cos(a) * r), h / 2.0 * (1 + math.sin(a) * r)) for a, r in
                 ((rng.uniform(0, 6.2832), 1.05 * rng.random() ** 1.4) for _ in range(n))]
        seeds += [(x, y) for x in (0, w / 2.0, w - 1) for y in (0, h / 2.0, h - 1)]
        cx, cy = w / 2.0, h / 2.0
        self.shard = [0] * (w * h)
        for y in range(h):
            rows = [4 * (y - sy) ** 2 for _, sy in seeds]
            for x in range(0, w, 2):
                best = min(range(len(seeds)), key=lambda s: (x + 1 - seeds[s][0]) ** 2 + rows[s])
                self.shard[y * w + x] = best
                if x + 1 < w:
                    self.shard[y * w + x + 1] = best
        k = len(seeds)
        self.members = [[] for _ in range(k)]
        for i, s in enumerate(self.shard):
            self.members[s].append(i)
        lift = [rng.randrange(6, 30) for _ in range(k)]
        self.F = G.Canvas(w, h)
        self.F.ch, self.F.fg = cv.ch[:], cv.fg[:]
        self.F.bg = [(lift[self.shard[i]], lift[self.shard[i]] + 2, lift[self.shard[i]] + 7) if cv.bg[i] == (0, 0, 0) else cv.bg[i] for i in range(w * h)]
        self.maxd = math.hypot(cx, 2 * cy)
        borders, self.bglyph = [], {}
        for i, s in enumerate(self.shard):
            x, y = i % w, i // w
            r = x + 1 < w and self.shard[i + 1] != s
            d = y + 1 < h and self.shard[i + w] != s
            if r or d:
                self.bglyph[i] = "|" if r and not d else ("-" if d and not r else rng.choice("/\\"))
                borders.append((math.hypot(x - cx, 2 * (y - cy)) * rng.uniform(0.88, 1.12), i))
        borders.sort()
        self.borders, self.bd = borders, [b[0] for b in borders]
        self.crack_speed = self.maxd / 2.8
        order = sorted(range(k), key=lambda s: math.hypot(seeds[s][0] - cx, 2 * (seeds[s][1] - cy)))
        self.start, self.vel = {}, {}
        for rank, s in enumerate(order):
            self.start[s] = FALL_T + 2.6 * rank / max(1, k - 1) + rng.uniform(0, 0.4)
            self.vel[s] = (rng.uniform(-7, 7), rng.uniform(-0.8, 0.8), seeds[s][1], min(self.members[s]) // w if self.members[s] else 0)
        self.sorted_t = sorted(self.start.values())

    # -- the cube
    def cube_cells(self, cx, cy, scale):
        ang = [self.phase * s for s in SPEEDS]
        pts = []
        for v in ultra_fx.VERTS:
            x, y, z, u = ultra_fx.rot4(v, ang)
            k = 1.0 / (2.7 - u * 0.6)
            x, y, z = x * k, y * k, z * k
            k2 = 1.0 / (3.4 - z * 0.7)
            pts.append((x * k2, y * k2, u))
        ext = max(max(abs(p[0]) for p in pts), max(abs(p[1]) for p in pts)) or 1.0
        R = self.scale * scale / ext
        out = []
        for i, j in ultra_fx.EDGES:
            (x1, y1, u1), (x2, y2, u2) = pts[i], pts[j]
            u = (u1 + u2) / 2
            ax, ay, bx, by = cx + x1 * 2 * R, cy + y1 * R, cx + x2 * 2 * R, cy + y2 * R
            if max(abs(ax), abs(bx), abs(ay), abs(by)) > 4000:
                continue
            gl = G.line_glyph(bx - ax, by - ay)
            for x, y in G.walk(ax, ay, bx, by):
                out.append((x, y, gl, u))
        for x1, y1, u1 in pts:                                              # the 16 corners
            out.append((int(round(cx + x1 * 2 * R)), int(round(cy + y1 * R)), "@", u1 + 0.6))
        return out

    def plot(self, x, y, ch, fg, bgadd=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            o = self.trail.get(i)
            self.trail[i] = (ch, fg, G.add(o[2], bgadd) if (o and bgadd and o[2]) else (bgadd or (o[2] if o else (0, 0, 0))))

    def draw_cube(self, t, rng, fx):
        cx_f, cy_f, sc, b = kf(CUBE, t)
        if sc <= 0.01:
            return
        cx, cy = cx_f * self.w, cy_f * self.h
        cells = self.cube_cells(cx, cy, sc)
        bl = G.smooth((b - 0.85) / 0.15)
        for n, (x, y, gl, u) in enumerate(cells):
            hue = G.ramp(HUES, u)
            col = G.mix(G.mul(hue, 0.55 + 0.45 * b), WHITE, min(1.0, b ** 2.2))
            self.plot(x, y, gl, col, G.mul(col, 0.07 * bl) if bl > 0 else None)
            if bl > 0 and n % 2 == 0:
                g = G.mul(col, 0.05 * bl)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    self.plot(x + dx, y + dy, " ", (0, 0, 0), g)
                if bl > 0.5 and n % 3 == 0:
                    for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2), (3, 0), (-3, 0)):
                        self.plot(x + dx, y + dy, " ", (0, 0, 0), G.mul(col, 0.03 * bl))
        if 6.0 <= t < 11.0 or S(36.5) <= t < LOST_T:                         # electric arcs from corners of the cube to the edge of the screen
            for _ in range(1 + rng.randrange(3)):
                x0, y0, _, _ = cells[rng.randrange(len(cells))]
                ex, ey = rng.choice([(0, rng.randrange(self.h)), (self.w - 1, rng.randrange(self.h)), (rng.randrange(self.w), 1), (rng.randrange(self.w), self.h - 2)])
                for x, y in G.jagged(x0, y0, ex, ey, rng, 2.5, 4):
                    self.plot(int(x), int(y), rng.choice("~=-*"), G.mul(ICE, 0.6), (10, 20, 30))

    # -- layers
    def render_B(self, t):
        w, h = self.w, self.h
        cv = G.Canvas(w, h)
        cv.bg = [(0, 9, 6)] * (w * h)
        n = bisect.bisect_right(self.times, t)
        ev = self.script[max(0, n - h):n]
        for r, (t0, txt, col, cps) in enumerate(ev):
            if cps and r == len(ev) - 1:
                k = int((t - t0) * cps)
                txt = txt[:k] + ("_" if int(t * 4) % 2 == 0 else " ")
            cv.text(1, r, txt[:w - 2], col)
        return cv

    def compose(self, cv, t, rng):
        w, h = self.w, self.h
        src = self.F if t >= CRACK_T else self.A
        ch, fg, bg = src.ch[:], src.fg[:], src.bg[:]
        if t >= CRACK_T:
            R = (t - CRACK_T) * self.crack_speed
            for d, i in self.borders[:bisect.bisect(self.bd, R)]:
                f = min(1.0, (R - d) / (0.25 * self.maxd))
                ch[i], fg[i] = self.bglyph[i], G.mix(WHITE, (150, 190, 255), f)
                bg[i] = G.mix((130, 150, 190), bg[i], f * 0.8)
        if t >= B_T:
            B = self.render_B(t)
            fall = []
            for s, st in self.start.items():
                if t >= st:
                    for i in self.members[s]:
                        ch[i], fg[i], bg[i] = B.ch[i], B.fg[i], B.bg[i]
                    fall.append(s)
            # the shards: drawn after all of the reveal so one falling piece never erases another
            snap = G.Canvas(w, h)
            snap.ch, snap.fg, snap.bg = ch[:], fg[:], bg[:]                  # the lit cracks fall with the shards
            for s in fall:
                tau = t - self.start[s]
                vx, rot, sy0, miny = self.vel[s]
                oy = int(0.5 * 62 * tau * tau)
                if miny + oy >= h:
                    continue
                ox = vx * tau
                for i in self.members[s]:
                    x, y = i % w, i // w
                    nx, ny = x + int(ox + rot * tau * (y - sy0)), y + oy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        ch[j], fg[j], bg[j] = snap.ch[i], snap.fg[i], snap.bg[i]
        if t < FADE_IN:                                                       # the bench ends on black + the hanging cube: the window and stars come up around it
            f = G.smooth(t / FADE_IN)
            fg, bg = [G.mul(c, f) for c in fg], [G.mul(c, f) for c in bg]
        cv.ch, cv.fg, cv.bg = ch, fg, bg
        for i, (c, f, b) in self.trail.items():
            if c != " ":
                cv.ch[i], cv.fg[i] = c, f
            cv.bg[i] = G.add(cv.bg[i], b)

    def post(self, cv, t, rng, fx):
        w, h = self.w, self.h
        tear = fx["tear"]
        if tear > 0.02:
            for _ in range(int(tear * h * 0.35)):
                y = rng.randrange(h)
                s = int(rng.uniform(-1, 1) * tear * w * 0.18)
                self.shift_row(cv, y, s)
            if rng.random() < tear:                                       # a whole band slides
                y0, n, s = rng.randrange(h), rng.randrange(3, 8), int(rng.uniform(-1, 1) * tear * w * 0.3)
                for y in range(y0, min(h, y0 + n)):
                    self.shift_row(cv, y, s)
        sp = fx["split"]
        if sp and t < LOST_T + 1.8:
            for a in (cv.fg, cv.bg):
                old = a[:]
                a[:] = [G.mix(old[i], (old[i - sp if i - sp >= 0 else i][0], old[i][1], old[i + sp if i + sp < len(old) else i][2]), 0.6) for i in range(len(old))]
        if t >= B_T:                                                          # faint scanlines on the "real" layer
            for y in range(1, h, 2):
                a, b = y * w, y * w + w
                cv.bg[a:b] = [G.mul(c, 0.7) for c in cv.bg[a:b]]
        if fx["invert"]:
            cv.fg = [(255 - c[0], 255 - c[1], 255 - c[2]) for c in cv.fg]
            cv.bg = [(255 - c[0], 255 - c[1], 255 - c[2]) for c in cv.bg]
        G.flash(cv, WHITE, fx["flash"])

    def shift_row(self, cv, y, s):
        if not s:
            return
        w = self.w
        for a in (cv.ch, cv.fg, cv.bg):
            row = a[y * w:(y + 1) * w]
            a[y * w:(y + 1) * w] = row[-s:] + row[:-s]                      # a rotation: what leaves one side comes in on the other

    def static(self, cv, t, rng):
        w, h = self.w, self.h
        lv = [rng.random() for _ in range(w * h)]
        band = (t * 14) % h
        glyphs = " .:-=+*#%@"
        cv.ch = [glyphs[int(v * v * 9.99)] for v in lv]
        cv.fg = [(int(60 + 195 * v), int(60 + 195 * v), int(70 + 185 * v)) for v in lv]
        cv.bg = [(int(35 * v * v),) * 3 for v in lv]
        for y in range(h):
            if abs(y - band) < 2.5:
                for x in range(w):
                    i = y * w + x
                    cv.bg[i] = G.add(cv.bg[i], (50, 50, 55))
        u = t - STATIC_T
        if u > 1.0 and u % 7.0 < 0.35:                                         # a flash of colour bars, like a TV that lost its signal
            bars = [(190, 190, 190), (190, 190, 0), (0, 190, 190), (0, 190, 0), (190, 0, 190), (190, 0, 0), (0, 0, 190)]
            cv.ch, cv.fg = [" "] * (w * h), [(0, 0, 0)] * (w * h)
            cv.bg = [bars[min(6, x * 7 // w)] for _ in range(h) for x in range(w)]
        for _ in range(int(2 + u % 5)):
            self.shift_row(cv, rng.randrange(h), rng.randrange(-w // 6, w // 6))
        msgs = self.err or ["SIGNAL LOST"]
        msg = msgs[int(u / 2.2) % len(msgs)]
        if int(t * 5) % 4:
            box = "  %s  " % msg
            x0, y0 = max(0, (w - len(box)) // 2), h // 2 - 1
            for k in range(-1, 4):
                for x in range(x0 - 2, x0 + len(box) + 2):
                    cv.put(x, y0 + k, " ", (0, 0, 0), (0, 0, 0))
            cv.text(x0, y0, " E R R O R ".center(len(box)), (0, 0, 0), (255, 60, 50))
            cv.text(x0, y0 + 2, box, (255, 60, 50), (0, 0, 0))

    def lost_lines_of(self, texts):
        return [fill(x, self.info) for x in (texts.get("mika.fourth.lost") or []) if x][-1:]

    def lost_lines(self):
        return [e[1] for e in self.script if e[0] >= LOST_T + 0.2 and e[2] == RED and e[1].isupper()]

    def crt_off(self, cv, t):
        """Classic tube switch-off: a white band squeezes to one line, the line shrinks to a dot (the caller then cuts to black)."""
        f = (t - OFF_T) / (BLACK_T - OFF_T)
        cv.clear()
        w, h = self.w, self.h
        if f < 0.45:
            hh, half = int(((1 - f / 0.45) ** 2) * h / 2), w // 2
        else:
            hh, half = 0, max(1, int(w * 0.5 * (1 - (f - 0.45) / 0.55) ** 2))
        for y in range(h // 2 - hh, h // 2 + hh + 1):
            for x in range(w // 2 - half, w // 2 + half):
                cv.put(x, y, " ", (255, 255, 255), (255, 255, 255) if hh or f < 0.9 else (170, 170, 170))

    def events(self, t):
        if self.out is None:
            return
        while self.title_i + 1 < len(TITLES) and TITLES[self.title_i + 1][0] <= t:
            self.title_i += 1
            self.out.write("\033]2;%s\007" % fill(TITLES[self.title_i][1], self.info))
        while self.bell_i < len(BELLS) and BELLS[self.bell_i] <= t:
            self.bell_i += 1
            self.out.write("\a")

    def draw(self, cv, t, dt):
        w, h = self.w, self.h
        self.events(t)
        steps = max(1, int(dt * 60))                                          # integrate the spin so the cube really accelerates
        for k in range(steps):
            self.phase += kf(SPIN, t - dt + dt * (k + 1) / steps) * dt / steps
        rng = random.Random(int(t * 1000) * 7919 + 3)
        fx = {"split": int(round(kf(SPLIT, t))), "tear": kf(TEAR, t), "flash": kf(FLASH, t),
              "invert": any(a <= t < b for a, b in INVERT) or (S(38.6) <= t < LOST_T and int(t * 20) % 2 == 0)}
        a = kf(TREMOR, t) * 1.6 + G.shake_at(t, HITS, 2.0, 0.28)
        a *= min(4.0, 1.0 + w / 90.0) / 2.0
        if self.wind is not None and a > 0.3:
            self.wind.move(*ultra_fx.window_offset(t, min(1.0, a / 4.0)))
        shake = (int(round(rng.uniform(-1, 1) * a * 2.0)), int(round(rng.uniform(-1, 1) * a))) if t < BLACK_T else (0, 0)
        if t >= BLACK_T:
            cv.clear()
            return 0, 0
        if t >= OFF_T:
            self.crt_off(cv, t)
            return 0, 0
        k = 0.22
        self.trail = {i: (c, G.mul(f, k), G.mul(b, k)) for i, (c, f, b) in self.trail.items() if max(f) + max(b) > 24}
        if t < STATIC_T:
            self.draw_cube(t, rng, fx)
        if t >= STATIC_T:
            self.trail = {}
            self.static(cv, t, rng)
            G.flash(cv, WHITE, fx["flash"])
            return shake
        self.compose(cv, t, rng)
        self.post(cv, t, rng, fx)
        return shake


# ---------------------------------------------------------------- run
class _QuietTty:
    """While the scene runs: no echo of typed keys (and of the window-op reply), keys typed meanwhile are dropped. Only for a real tty."""

    def __init__(self, on):
        self.fd = self.old = None
        try:
            import termios
            import tty
            if on and sys.stdin.isatty():
                self.fd = sys.stdin.fileno()
                self.old = termios.tcgetattr(self.fd)
                tty.setcbreak(self.fd)                                   # no echo, no line buffer; Ctrl+C still raises KeyboardInterrupt
                self.termios = termios
                termios.tcflush(self.fd, termios.TCIFLUSH)               # keys typed before the scene must not leak into it
        except Exception:
            self.fd = self.old = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        if self.fd is not None and self.old is not None:
            try:
                self.termios.tcflush(self.fd, self.termios.TCIFLUSH)
                self.termios.tcsetattr(self.fd, self.termios.TCSADRAIN, self.old)
            except Exception:
                pass


KDE_ARGV = ["busctl", "--user", "call", "org.kde.kglobalaccel", "/component/kwin", "org.kde.kglobalaccel.Component", "invokeShortcut", "s", "Window Fullscreen"]
ALLOWED_ARGV = (KDE_ARGV, ["hyprctl", "activewindow", "-j"], ["hyprctl", "dispatch", "fullscreen", "0"], ["swaymsg", "-t", "get_tree"],
                ["swaymsg", "fullscreen", "enable"], ["swaymsg", "fullscreen", "disable"])


def _run(argv):
    """The ONLY subprocess use: one of ALLOWED_ARGV, no shell, 2 s timeout, errors ignored. Returns stdout or ''."""
    if list(argv) not in ALLOWED_ARGV:
        return ""
    try:
        return subprocess.run(list(argv), capture_output=True, text=True, timeout=2, check=False).stdout or ""
    except Exception:
        return ""


def _focused_fullscreen(node):
    if isinstance(node, dict):
        if node.get("focused") and "fullscreen_mode" in node:
            return bool(node.get("fullscreen_mode"))
        for k in ("nodes", "floating_nodes"):
            for c in node.get(k) or []:
                r = _focused_fullscreen(c)
                if r is not None:
                    return r
    return None


class Fullscreen:
    """Best-effort: put the terminal window into fullscreen and back. Order: xterm window ops (CSI 10;1 t, then CSI 9;1 t - counts only if the terminal
    size really changes), Hyprland (hyprctl, only if the window is not fullscreen already), sway (swaymsg), else nothing. stop() undoes exactly what start() did."""

    def __init__(self, env=None, write=None, run=None):
        self.env = os.environ if env is None else env
        self.write = write or (lambda s: None)
        self.run = run or _run
        self.did = None

    def _wait_change(self, sleep, size, before, n=8):
        for _ in range(n):
            sleep(0.1)
            if tuple(size()) != tuple(before):
                return True
        return False

    def start(self, sleep, size):
        e, before = self.env, tuple(size())
        if e.get(FULL_ENV, "1") == "0":
            return False
        if "kde" in e.get("XDG_CURRENT_DESKTOP", "").lower() and e.get("WAYLAND_DISPLAY"):
            # KWin: the shortcut TOGGLES the active window, so it is invoked once and only counts if the terminal size really changes
            self.run(KDE_ARGV)
            if self._wait_change(sleep, size, before, 12):
                self.did = "kde"
                atexit.register(self.stop)                                  # a crash must not leave the window fullscreen
                return True
            return False                                                    # nothing changed: it did not work or was already fullscreen - never toggle blindly
        if "xterm" in e.get("TERM", "") and not e.get("TMUX") and not e.get("STY"):
            for how, seq in (("xterm10", "\033[10;1t"), ("xterm9", "\033[9;1t")):
                self.write(seq)
                if self._wait_change(sleep, size, before, 5):
                    self.did = how
                    return True
        if e.get("HYPRLAND_INSTANCE_SIGNATURE"):
            try:
                j = json.loads(self.run(["hyprctl", "activewindow", "-j"]) or "{}")
            except ValueError:
                j = {}
            if j.get("fullscreen"):
                return False                                                # already fullscreen: leave it alone
            self.run(["hyprctl", "dispatch", "fullscreen", "0"])
            self.did = "hypr"
        elif e.get("SWAYSOCK"):
            try:
                tree = json.loads(self.run(["swaymsg", "-t", "get_tree"]) or "{}")
            except ValueError:
                tree = {}
            if _focused_fullscreen(tree):
                return False
            self.run(["swaymsg", "fullscreen", "enable"])
            self.did = "sway"
        else:
            return False
        self._wait_change(sleep, size, before)
        return True

    def stop(self):
        did, self.did = self.did, None
        if did in ("xterm10", "xterm9"):
            self.write("\033[%s;0t" % did[5:])
        elif did == "kde":
            self.run(KDE_ARGV)
        elif did == "hypr":
            self.run(["hyprctl", "dispatch", "fullscreen", "0"])
        elif did == "sway":
            self.run(["swaymsg", "fullscreen", "disable"])


def run(ctx):
    real = (ctx.out is sys.stdout or ctx.out is sys.__stdout__) and sys.stdout.isatty()
    fs = getattr(ctx, "fullscreen", None)
    if fs is None and real and getattr(ctx, "fullscreen_enabled", True):
        fs = Fullscreen(write=lambda x: (ctx.out.write(x), ctx.out.flush()))
    wind = getattr(ctx, "winshake", None)
    ctx.out.write("" if chain.active else "\033[?1049h\033[?25l")                                   # alternate screen + hidden cursor: nothing else of the terminal shows
    ctx.out.flush()
    with _QuietTty(real):                                                    # input lock: keys do nothing (flushed before and after); Ctrl+C still aborts
        try:
            full = bool(fs and fs.start(ctx.sleep, ctx.size))
            cols, rows = ctx.size()                                          # the NEW size after the fullscreen switch
            info = getattr(ctx, "info", None) or sysinfo((cols, rows))
            if wind is None and real and not full:
                wind = ultra_fx.WindowShake()
            shaking = bool(wind and not full and cols >= 40 and rows >= 15 and wind.start())
            scene = []

            def factory(w, h, rng):
                scene.append(FourthScene(w, h, rng, info, ctx.texts, ctx.out, wind if shaking else None))
                return scene[0]
            try:
                G.play(ctx, factory, SECONDS, captions(ctx.lines("mika.fourth.lines")), CUES, seed=4)
            finally:
                if scene:
                    ctx.out.write("\033]2;FOLK\007")                       # the original title cannot be read back: leave the game's own
                    ctx.out.flush()
                if wind is not None:
                    wind.stop()
        finally:
            if fs is not None:
                fs.stop()
            if not chain.active:
                ctx.out.write("\033[?1049l\033[?25h")
            ctx.out.flush()
