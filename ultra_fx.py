"""ultra_fx.py - the two ULTRA TESSERACT cinematics as pure frame generators (no curses, no I/O, deterministic).

    unlock_frame(t, w, h)  - UNLOCK_SECONDS (8.4 s): the tesseract unfolds into its net of 8 cubes, nested 4D rotations in six planes,
                             a charge-up, a smaller shock with a real shake, white-out, then the title card ULTRA TESSERACT.
    use_frame(t, w, h, noah=None, heart=None, words=(), scene=None) - USE_SECONDS (10.4 s), in five beats: dread (the screen dims,
                             a tiny box speaks in three slow beats, a tremor starts), charge-up (particles spiral in, a circle of 4D
                             projections, a sphere climbing violet -> blue -> white-hot, the shake rises), release (a sphere that covers the
                             whole terminal, a column of light, the screen's own content blown outward, a hard white-out), aftershocks, and
                             an aftermath of ash over a dim crater, then a beat of silence.
A frame is a list of cells (x, y, text, colour): text is one character or a run of characters, colour an index into PALETTE.
The shake moves EVERY cell (HUD, arena, art) by random offsets of up to +-SHAKE_X columns and +-SHAKE_Y rows with an amplitude made of a
rising tremor plus exponentially decaying quakes (shake_amp). WindowShake moves the terminal window itself where xterm window ops work.
render_ansi() turns a frame into text for a plain terminal (gallery), CursesScreen maps the same indices to curses colour pairs.
"""
import math
import os
import random
import re
import select

UNLOCK_SECONDS = 8.4
USE_SECONDS = 10.4
SHAKE_X, SHAKE_Y = 8, 4                  # the whole screen jumps by up to this many columns / rows at full amplitude
WIN_PX = (26, 16)                        # ... and a terminal that obeys xterm window ops moves by up to this many pixels
# name, rgb, curses 8-colour fallback, xterm-256 index
PALETTE = [("white", (255, 255, 255), 7, 231), ("cyan", (80, 240, 255), 6, 51), ("magenta", (255, 90, 240), 5, 207), ("yellow", (255, 230, 90), 3, 227),
           ("green", (110, 255, 140), 2, 83), ("red", (255, 70, 70), 1, 203), ("blue", (90, 130, 255), 4, 69), ("grey", (140, 140, 160), 7, 244),
           ("orange", (255, 160, 60), 3, 214), ("violet", (170, 110, 255), 5, 141)]
RAINBOW = [1, 6, 9, 2, 5, 8, 3, 4]
WHITE, CYAN, MAGENTA, YELLOW, GREEN, RED, BLUE, GREY, ORANGE, VIOLET = range(10)

LETTERS = {  # 5x5 block letters for the title card
    "U": ["█   █", "█   █", "█   █", "█   █", " ███ "], "L": ["█    ", "█    ", "█    ", "█    ", "█████"], "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
    "R": ["████ ", "█   █", "████ ", "█  █ ", "█   █"], "A": [" ███ ", "█   █", "█████", "█   █", "█   █"], "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    "S": [" ████", "█    ", " ███ ", "    █", "████ "], "C": [" ████", "█    ", "█    ", "█    ", " ████"], " ": ["  ", "  ", "  ", "  ", "  "],
}


def title_rows(word="ULTRA TESSERACT"):
    """The word in 5-row block letters; list of 5 strings."""
    return ["  ".join(LETTERS.get(c, LETTERS[" "])[r] for c in word) for r in range(5)]


def _clip(cells, w, h):
    """Keep what is on screen; runs of text are cut at the edges."""
    out = []
    for x, y, ch, c in cells:
        if not 0 <= y < h:
            continue
        if len(ch) > 1:
            if x < 0:
                ch, x = ch[-x:], 0
            ch = ch[:max(0, w - x)]
            if not ch:
                continue
        elif not 0 <= x < w:
            continue
        out.append((x, y, ch, c))
    return out


def _line(x0, y0, x1, y1, ch, col, out):
    n = int(max(abs(x1 - x0) / 2.0, abs(y1 - y0))) + 1
    for i in range(n + 1):
        f = i / n
        out.append((int(round(x0 + (x1 - x0) * f)), int(round(y0 + (y1 - y0) * f)), ch, col))


# ---------------------------------------------------------------- 4D helpers
def rot4(p, angles):
    """Rotate a 4D point in the six coordinate planes; angles = (xy, xz, xw, yz, yw, zw)."""
    p = list(p)
    for (i, j), a in zip(((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), angles):
        c, s = math.cos(a), math.sin(a)
        p[i], p[j] = p[i] * c - p[j] * s, p[i] * s + p[j] * c
    return p


VERTS = [[(i >> k & 1) * 2 - 1 for k in range(4)] for i in range(16)]
EDGES = [(i, j) for i in range(16) for j in range(i + 1, 16) if bin(i ^ j).count("1") == 1]


def tess(t, w, h, scale=1.0, speeds=(0.31, 0.23, 0.9, 0.41, 0.63, 0.77), cx=None, cy=None, col_shift=0):
    """A tesseract rotating in all six planes. Returns cells; colour follows the 4D depth (w coordinate)."""
    ang = [t * s for s in speeds]
    pts = []
    for v in VERTS:
        x, y, z, u = rot4(v, ang)
        k = 1.0 / (2.7 - u * 0.6)
        x, y, z = x * k, y * k, z * k
        k2 = 1.0 / (3.4 - z * 0.7)
        pts.append((x * k2, y * k2, u))
    ext = max(max(abs(p[0]) for p in pts), max(abs(p[1]) for p in pts)) or 1.0
    R = min(h * 0.46, w * 0.23) * scale / ext            # one common unit, so the cube is not squashed (cells are 1:2)
    sx, sy = 2 * R, R
    cx = w / 2.0 if cx is None else cx
    cy = h / 2.0 if cy is None else cy
    out = []
    for i, j in EDGES:
        (x1, y1, u1), (x2, y2, u2) = pts[i], pts[j]
        u = (u1 + u2) / 2
        col = RAINBOW[int((u + 1.5) * 2.6 + col_shift) % len(RAINBOW)]
        ch = "@" if u > 0.3 else ("#" if u > -0.3 else "+")
        _line(cx + x1 * sx, cy + y1 * sy, cx + x2 * sx, cy + y2 * sy, ch, col, out)
    return out


# ---------------------------------------------------------------- the net: 8 cubes
NET = [(0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 3, 0), (-1, 1, 0), (1, 1, 0), (0, 1, -1), (0, 1, 1)]
CUBE_V = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
CUBE_E = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]


def net_cubes(t, w, h, unfold, spin, scale=1.0):
    """The 8 cubes of the tesseract's net. unfold 0 = all stacked in the middle (a folded cube), 1 = the full cross.
    The cross turns with `spin` radians; every cube gets its own colour."""
    out = []
    cx, cy = w / 2.0, h / 2.0
    mid = (0, 1.5, 0)
    ca, sa = math.cos(spin), math.sin(spin)
    k = min(h * 0.72, w * 0.5) * scale
    for n, (gx, gy, gz) in enumerate(NET):
        f = unfold
        ox, oy, oz = (gx - mid[0]) * f, (gy - mid[1]) * f, (gz - mid[2]) * f
        pts = []
        for vx, vy, vz in CUBE_V:
            x, y, z = ox + vx - 0.5, oy + vy - 0.5, oz + vz - 0.5
            # open each cube out of the fold: the further a cube is from the middle, the more it hinges
            x, z = x * ca - z * sa, x * sa + z * ca
            y, z = y * math.cos(0.35) - z * math.sin(0.35), y * math.sin(0.35) + z * math.cos(0.35)
            q = 1.0 / (3.2 - z * 0.45)
            pts.append((cx + x * k * q * 2.0, cy + y * k * q * 0.95 * 1.0, z))
        col = RAINBOW[(n + int(t * 3)) % len(RAINBOW)]
        for a, b in CUBE_E:
            _line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], "#" if pts[a][2] + pts[b][2] > 0 else ":", col, out)
    return out


# ---------------------------------------------------------------- rifts, shockwave, white
def rifts(t, w, h, strength, seed=3):
    """Reality tears: jagged bright lines across the screen with glitch bands next to them."""
    rng = random.Random(seed + int(t * 12))
    out = []
    for r in range(3):
        x = rng.uniform(0.15, 0.85) * w
        y = 0.0
        while y < h:
            nx = x + rng.uniform(-5, 5)
            _line(x, y, nx, y + 1, "|/\\"[rng.randint(0, 2)], WHITE if rng.random() < 0.6 else RAINBOW[rng.randint(0, 7)], out)
            for k in range(int(strength * 10 * rng.random())):
                out.append((int(nx) + rng.randint(-14, 14), int(y), rng.choice("#%@&$?!/\\|<>~^░▒▓"), RAINBOW[rng.randint(0, 7)]))
            x, y = nx, y + 1
    return out


def shockwave(t, w, h, radius, amp=3.5, grid=(4, 2)):
    """A regular grid of dots that is pushed away from a travelling ring: the arena grid bends."""
    out = []
    cx, cy = w / 2.0, h / 2.0
    for gy in range(0, h, grid[1]):
        for gx in range(0, w, grid[0]):
            dx, dy = (gx - cx) / 2.0, gy - cy
            r = math.hypot(dx, dy)
            push = amp * math.exp(-((r - radius) / 3.0) ** 2) if r else 0
            ux, uy = (dx / r, dy / r) if r else (0, 0)
            x, y = int(round(gx + ux * push * 2)), int(round(gy + uy * push))
            near = abs(r - radius) < 2.2
            out.append((x, y, "O" if near else "+", WHITE if near else (CYAN if (gx + gy) % 8 else BLUE)))
    ring = []
    n = int(radius * 14) + 12
    for k in range(n):
        a = 2 * math.pi * k / n
        ring.append((int(round(cx + math.cos(a) * radius * 2)), int(round(cy + math.sin(a) * radius)), "@", WHITE))
    return out + ring


def whiteout(w, h, f, seed=1):
    """f 0..1: the screen fills with white blocks (random order), then everything is white. One run per row when f is 1."""
    if f >= 0.999:
        return [(0, y, "\u2588" * w, WHITE) for y in range(h)]
    rng = random.Random(seed)
    out = []
    for y in range(h):
        x = 0
        while x < w:
            on = rng.random() < f
            n = 1
            while x + n < w and n < 12 and rng.random() < 0.6:
                n += 1
            if on:
                out.append((x, y, ("\u2588" if f > 0.7 else "\u2593") * n, WHITE))
            x += n
    return out


def title_rows(word="ULTRA TESSERACT"):
    """The word in 5-row block letters; list of 5 strings."""
    return ["  ".join(LETTERS.get(c, LETTERS[" "])[r] for c in word) for r in range(5)]


def _clip(cells, w, h):
    """Keep what is on screen; runs of text are cut at the edges."""
    out = []
    for x, y, ch, c in cells:
        if not 0 <= y < h:
            continue
        if len(ch) > 1:
            if x < 0:
                ch, x = ch[-x:], 0
            ch = ch[:max(0, w - x)]
            if not ch:
                continue
        elif not 0 <= x < w:
            continue
        out.append((x, y, ch, c))
    return out


def _line(x0, y0, x1, y1, ch, col, out):
    n = int(max(abs(x1 - x0) / 2.0, abs(y1 - y0))) + 1
    for i in range(n + 1):
        f = i / n
        out.append((int(round(x0 + (x1 - x0) * f)), int(round(y0 + (y1 - y0) * f)), ch, col))


# ---------------------------------------------------------------- 4D helpers
def rot4(p, angles):
    """Rotate a 4D point in the six coordinate planes; angles = (xy, xz, xw, yz, yw, zw)."""
    p = list(p)
    for (i, j), a in zip(((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)), angles):
        c, s = math.cos(a), math.sin(a)
        p[i], p[j] = p[i] * c - p[j] * s, p[i] * s + p[j] * c
    return p


VERTS = [[(i >> k & 1) * 2 - 1 for k in range(4)] for i in range(16)]
EDGES = [(i, j) for i in range(16) for j in range(i + 1, 16) if bin(i ^ j).count("1") == 1]


def tess(t, w, h, scale=1.0, speeds=(0.31, 0.23, 0.9, 0.41, 0.63, 0.77), cx=None, cy=None, col_shift=0):
    """A tesseract rotating in all six planes. Returns cells; colour follows the 4D depth (w coordinate)."""
    ang = [t * s for s in speeds]
    pts = []
    for v in VERTS:
        x, y, z, u = rot4(v, ang)
        k = 1.0 / (2.7 - u * 0.6)
        x, y, z = x * k, y * k, z * k
        k2 = 1.0 / (3.4 - z * 0.7)
        pts.append((x * k2, y * k2, u))
    ext = max(max(abs(p[0]) for p in pts), max(abs(p[1]) for p in pts)) or 1.0
    R = min(h * 0.46, w * 0.23) * scale / ext            # one common unit, so the cube is not squashed (cells are 1:2)
    sx, sy = 2 * R, R
    cx = w / 2.0 if cx is None else cx
    cy = h / 2.0 if cy is None else cy
    out = []
    for i, j in EDGES:
        (x1, y1, u1), (x2, y2, u2) = pts[i], pts[j]
        u = (u1 + u2) / 2
        col = RAINBOW[int((u + 1.5) * 2.6 + col_shift) % len(RAINBOW)]
        ch = "@" if u > 0.3 else ("#" if u > -0.3 else "+")
        _line(cx + x1 * sx, cy + y1 * sy, cx + x2 * sx, cy + y2 * sy, ch, col, out)
    return out


# ---------------------------------------------------------------- the net: 8 cubes
NET = [(0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 3, 0), (-1, 1, 0), (1, 1, 0), (0, 1, -1), (0, 1, 1)]
CUBE_V = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
CUBE_E = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count("1") == 1]


def net_cubes(t, w, h, unfold, spin, scale=1.0):
    """The 8 cubes of the tesseract's net. unfold 0 = all stacked in the middle (a folded cube), 1 = the full cross.
    The cross turns with `spin` radians; every cube gets its own colour."""
    out = []
    cx, cy = w / 2.0, h / 2.0
    mid = (0, 1.5, 0)
    ca, sa = math.cos(spin), math.sin(spin)
    k = min(h * 0.72, w * 0.5) * scale
    for n, (gx, gy, gz) in enumerate(NET):
        f = unfold
        ox, oy, oz = (gx - mid[0]) * f, (gy - mid[1]) * f, (gz - mid[2]) * f
        pts = []
        for vx, vy, vz in CUBE_V:
            x, y, z = ox + vx - 0.5, oy + vy - 0.5, oz + vz - 0.5
            # open each cube out of the fold: the further a cube is from the middle, the more it hinges
            x, z = x * ca - z * sa, x * sa + z * ca
            y, z = y * math.cos(0.35) - z * math.sin(0.35), y * math.sin(0.35) + z * math.cos(0.35)
            q = 1.0 / (3.2 - z * 0.45)
            pts.append((cx + x * k * q * 2.0, cy + y * k * q * 0.95 * 1.0, z))
        col = RAINBOW[(n + int(t * 3)) % len(RAINBOW)]
        for a, b in CUBE_E:
            _line(pts[a][0], pts[a][1], pts[b][0], pts[b][1], "#" if pts[a][2] + pts[b][2] > 0 else ":", col, out)
    return out


# ---------------------------------------------------------------- rifts, shockwave, white
def rifts(t, w, h, strength, seed=3):
    """Reality tears: jagged bright lines across the screen with glitch bands next to them."""
    rng = random.Random(seed + int(t * 12))
    out = []
    for r in range(3):
        x = rng.uniform(0.15, 0.85) * w
        y = 0.0
        while y < h:
            nx = x + rng.uniform(-5, 5)
            _line(x, y, nx, y + 1, "|/\\"[rng.randint(0, 2)], WHITE if rng.random() < 0.6 else RAINBOW[rng.randint(0, 7)], out)
            for k in range(int(strength * 10 * rng.random())):
                out.append((int(nx) + rng.randint(-14, 14), int(y), rng.choice("#%@&$?!/\\|<>~^░▒▓"), RAINBOW[rng.randint(0, 7)]))
            x, y = nx, y + 1
    return out


def shockwave(t, w, h, radius, amp=3.5, grid=(4, 2)):
    """A regular grid of dots that is pushed away from a travelling ring: the arena grid bends."""
    out = []
    cx, cy = w / 2.0, h / 2.0
    for gy in range(0, h, grid[1]):
        for gx in range(0, w, grid[0]):
            dx, dy = (gx - cx) / 2.0, gy - cy
            r = math.hypot(dx, dy)
            push = amp * math.exp(-((r - radius) / 3.0) ** 2) if r else 0
            ux, uy = (dx / r, dy / r) if r else (0, 0)
            x, y = int(round(gx + ux * push * 2)), int(round(gy + uy * push))
            near = abs(r - radius) < 2.2
            out.append((x, y, "O" if near else "+", WHITE if near else (CYAN if (gx + gy) % 8 else BLUE)))
    ring = []
    n = int(radius * 14) + 12
    for k in range(n):
        a = 2 * math.pi * k / n
        ring.append((int(round(cx + math.cos(a) * radius * 2)), int(round(cy + math.sin(a) * radius)), "@", WHITE))
    return out + ring


def whiteout(w, h, f, seed=1):
    """f 0..1: the screen fills with white blocks (random order), then everything is white."""
    rng = random.Random(seed)
    out = []
    for y in range(h):
        for x in range(w):
            if rng.random() < f:
                out.append((x, y, "█" if f > 0.7 else "▓", WHITE))
    return out


def title(w, h, f, subtitle="", lines=(), y_shift=0):
    """The title card, built from block letters, letters appearing left to right (f 0..1) with rainbow colour sweeping over them."""
    rows = title_rows()
    tw = len(rows[0])
    if tw + 2 > w:                                              # too narrow for one line: two lines
        a, b = title_rows("ULTRA"), title_rows("TESSERACT")
        blocks = [a, b]
    else:
        blocks = [rows]
    total_h = sum(5 + 1 for _ in blocks)
    y0 = max(0, h // 2 - total_h // 2 - 2 + y_shift)
    out = []
    shown = int(f * (tw + 8))
    for bi, rows_ in enumerate(blocks):
        bw = len(rows_[0])
        x0 = max(0, (w - bw) // 2)
        for r, row in enumerate(rows_):
            for c, ch in enumerate(row):
                if ch != " " and c < shown:
                    out.append((x0 + c, y0 + bi * 6 + r, ch, RAINBOW[(c // 3 + r + int(f * 20)) % 8]))
    ty = y0 + total_h + 1
    if subtitle and f > 0.6:
        out += [(max(0, (w - len(subtitle)) // 2) + i, ty, ch, YELLOW) for i, ch in enumerate(subtitle)]
    for k, txt in enumerate(lines):
        if f > 0.7 + 0.05 * k:
            out += [(max(0, (w - len(txt)) // 2) + i, ty + 2 + k, ch, CYAN) for i, ch in enumerate(txt)]
    return out


# ---------------------------------------------------------------- the shake
def shake_amp(t, quakes=(), tremor=None):
    """Shake strength 0..1 at time t: a rising tremor (start, end, amp_start, amp_end) plus quakes (time, amp, decay seconds) that
    each hit at once and die away exponentially, so aftershocks are separate bumps."""
    a = 0.0
    for t0, amp, tau in quakes:
        if t >= t0:
            a += amp * math.exp(-(t - t0) / tau)
    if tremor and tremor[0] <= t < tremor[1]:
        a += tremor[2] + (tremor[3] - tremor[2]) * (t - tremor[0]) / (tremor[1] - tremor[0])
    return max(0.0, min(1.0, a))


def shake_offset(t, amp, seed=0):
    """(dx, dy) for the whole screen this frame: random, new every 1/30 s, never more than +-SHAKE_X / +-SHAKE_Y."""
    rng = random.Random(int(t * 30) * 7919 + seed)
    return int(round(rng.uniform(-1, 1) * SHAKE_X * amp)), int(round(rng.uniform(-1, 1) * SHAKE_Y * amp))


def shaken(cells, t, w, h, amp, seed=0):
    """Every cell moves by the frame's offset plus a little per-row jitter (rows tear a bit); what leaves the screen is dropped."""
    if amp <= 0.01:
        return cells
    dx, dy = shake_offset(t, amp, seed)
    rng = random.Random(int(t * 30) * 104729 + seed)
    jit = [int(round(rng.uniform(-1, 1) * 2 * amp)) for _ in range(h + 2 * SHAKE_Y + 2)]
    out = []
    for x, y, ch, c in cells:
        j = max(-SHAKE_X, min(SHAKE_X, dx + jit[(y + SHAKE_Y) % len(jit)]))
        out.append((x + j, y + dy, ch, c))
    return _clip(out, w, h)


def window_offset(t, amp, seed=1):
    """(dx, dy) in pixels for the terminal window itself."""
    rng = random.Random(int(t * 30) * 6151 + seed)
    return int(round(rng.uniform(-1, 1) * WIN_PX[0] * amp)), int(round(rng.uniform(-1, 1) * WIN_PX[1] * amp))


class WindowShake:
    """Best-effort real window shake with the xterm window op CSI 3;x;y t. Opt-out: FOLK_WINSHAKE=0. Only for xterm-compatible TERM,
    never inside tmux/screen; the position is read once (CSI 13 t) and always restored by stop(). If no reply comes nothing is ever moved."""

    def __init__(self, env=None, write=None, read_reply=None):
        self.env = os.environ if env is None else env
        self.write = write or (lambda s: os.write(1, s.encode()))
        self.read_reply = read_reply or self._read_reply
        self.pos = None
        self.moved = False

    def enabled(self):
        e = self.env
        return e.get("FOLK_WINSHAKE", "1") != "0" and "xterm" in e.get("TERM", "") and not e.get("TMUX") and not e.get("STY")

    @staticmethod
    def _read_reply(timeout=0.25):
        """Read the terminal's answer to CSI 13 t (CSI 3;x;y t) straight from the tty, leaving nothing behind."""
        try:
            fd = 0
            buf, end = b"", 0
            import time
            end = time.monotonic() + timeout
            while time.monotonic() < end and not buf.endswith(b"t"):
                if select.select([fd], [], [], 0.05)[0]:
                    buf += os.read(fd, 64)
            return buf.decode(errors="ignore")
        except (OSError, ValueError):
            return ""

    def start(self):
        if not self.enabled():
            return False
        try:
            self.write("\033[13t")
            m = re.search(r"\033\[3;(-?\d+);(-?\d+)t", self.read_reply())
        except (OSError, ValueError):
            m = None
        self.pos = (int(m.group(1)), int(m.group(2))) if m else None
        return self.pos is not None

    def move(self, dx, dy):
        if self.pos is None:
            return
        self.moved = True
        try:
            self.write("\033[3;%d;%dt" % (max(0, self.pos[0] + dx), max(0, self.pos[1] + dy)))
        except OSError:
            self.pos = None

    def stop(self):
        if self.pos is not None and self.moved:
            try:
                self.write("\033[3;%d;%dt" % self.pos)
            except OSError:
                pass
        self.moved = False


# ---------------------------------------------------------------- charge-up and release pieces
def heat(u):
    """Colour climbing violet -> blue -> cyan -> white-hot, u 0..1."""
    return VIOLET if u < 0.3 else (BLUE if u < 0.6 else (CYAN if u < 0.85 else WHITE))


def disc(cx, cy, r, chars=".:oO@", col=WHITE, bands=None):
    """A filled ellipse (cells are 1:2) as runs: one run per row and ring band, denser glyphs towards the middle."""
    out = []
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        dy = (y - cy) / max(r, 0.01)
        if abs(dy) > 1:
            continue
        half = math.sqrt(1 - dy * dy) * r * 2
        n = len(chars)
        for k, ch in enumerate(chars):                     # outer band first, inner bands painted over it
            hw = half * (1 - k / n) if k else half
            if hw >= 1:
                out.append((int(round(cx - hw)), y, ch * int(round(hw * 2)), col if bands is None else bands[k % len(bands)]))
    return out


def particles(t, u, w, h, n=140, seed=2):
    """Sparks that spiral into the middle as u goes 0 -> 1."""
    rng = random.Random(seed)
    cx, cy, out = w / 2.0, h / 2.0, []
    for i in range(n):
        a0, r0, sp = rng.uniform(0, 6.283), rng.uniform(0.5, 1.0) * max(w * 0.5, 30), rng.uniform(0.7, 1.5)
        f = max(0.0, 1 - u * sp) ** 1.6
        a = a0 + (1 - f) * 7 + t * 0.5
        out.append((int(cx + math.cos(a) * r0 * f), int(cy + math.sin(a) * r0 * f * 0.48), "*" if f > 0.25 else "+", heat(min(1, u + (1 - f) * 0.4))))
    return out


def circle(t, w, h, u):
    """A magic circle of 4D projections: three tesseracts at different sizes and speeds plus rings of runes."""
    out = []
    for k, (sc, spd) in enumerate(((0.95, 1.0), (0.62, -1.4), (0.3, 2.0))):
        for c in tess(t * spd * 0.8, w, h, scale=sc * (0.3 + 0.7 * u), col_shift=k * 2):
            out.append((c[0], c[1], c[2], heat(min(1, u * 0.8 + k * 0.1))))
    cx, cy = w / 2.0, h / 2.0
    for ring, (r, n, sp) in enumerate(((0.44, 28, 0.4), (0.3, 18, -0.7))):
        for i in range(n):
            a = 2 * math.pi * i / n + t * sp
            out.append((int(cx + math.cos(a) * r * h * 2 * u), int(cy + math.sin(a) * r * h * u), "◇◆+"[i % 3], heat(min(1, u + 0.2))))
    return out


def typed(beats, t):
    """The speech beats [(start, text, seconds_per_char)] as the text visible at time t (one line, beats separated by gaps)."""
    line = ""
    for start, text, spc in beats:
        if t >= start:
            line += (" " if line else "") + text[:max(0, int((t - start) / spc) + 1)]
    return line


SPEECH = [(0.5, "I...", 0.2), (1.9, "am...", 0.22), (3.5, "every side at once.", 0.04)]


def speech_box(t, w, h):
    txt = typed(SPEECH, t)
    if not txt:
        return []
    bw = max(len(typed(SPEECH, 99)) + 4, 8)
    x0, y0 = (w - bw) // 2, h // 2 - 2
    out = [(x0, y0, "+" + "-" * (bw - 2) + "+", GREY), (x0, y0 + 2, "+" + "-" * (bw - 2) + "+", GREY), (x0, y0 + 1, "|", GREY), (x0 + bw - 1, y0 + 1, "|", GREY)]
    out.append((x0 + 2, y0 + 1, txt, WHITE))
    if int(t * 2) % 2 == 0 and len(txt) < len(typed(SPEECH, 99)):
        out.append((x0 + 2 + len(txt), y0 + 1, "_", WHITE))
    return out


def scene_blown(scene, tau, w, h, seed=7):
    """The screen's own cells (arena, HUD, art) flying outward from the middle tau seconds after the release."""
    cx, cy, out = w / 2.0, h / 2.0, []
    for k, (x, y, ch, c) in enumerate(scene):
        for i, g in enumerate(ch):
            rng = random.Random(seed + (x + i) * 131 + y * 7919)
            dx, dy = (x + i - cx) / 2.0 + rng.uniform(-3, 3), (y - cy) + rng.uniform(-1.5, 1.5)
            d = math.hypot(dx, dy) or 1.0
            sp = rng.uniform(10, 40)
            if tau > 1.9:
                continue
            ch2 = g if tau < 0.5 else (g if rng.random() < 0.6 else rng.choice(".:'`*"))
            out.append((int(x + i + dx / d * sp * tau * 2), int(y + dy / d * sp * tau * 0.8 + 6 * tau * tau), ch2 if tau < 1.2 else ".", WHITE if tau < 0.4 else (ORANGE if tau < 1.2 else GREY)))
    return out


def ash(t, w, h, n=90, seed=4):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        x0, sp = rng.uniform(0, w), rng.uniform(1.5, 5.0)
        y = (rng.uniform(-h, h) + t * sp) % (h + 4) - 2
        out.append((int((x0 + math.sin(t * 0.8 + i) * 3) % w), int(y), rng.choice(".,'`*"), ORANGE if i % 5 == 0 else GREY))
    return out


def crater(w, h, f):
    """A dim crater of glyphs where the blast was (f 0..1 grows it)."""
    cx, cy, out = w / 2.0, h * 0.78, []
    for k, (rx, ry, ch) in enumerate(((0.34, 0.16, "o"), (0.28, 0.12, ":"), (0.2, 0.08, "."))):
        for i in range(80):
            a = 2 * math.pi * i / 80
            out.append((int(cx + math.cos(a) * rx * w * f), int(cy + math.sin(a) * ry * h * 2 * f), ch, GREY))
    return out


# ---------------------------------------------------------------- the unlock cinematic
UNLOCK_QUAKES = ((6.6, 0.7, 0.4), (7.5, 0.3, 0.3))
UNLOCK_TREMOR = (3.4, 6.6, 0.03, 0.35)
USE_QUAKES = ((6.6, 1.0, 0.55), (7.35, 0.6, 0.4), (8.3, 0.35, 0.45), (9.1, 0.2, 0.3))
USE_TREMOR = (3.0, 6.6, 0.04, 0.6)


def unlock_amp(t):
    return shake_amp(t, UNLOCK_QUAKES, UNLOCK_TREMOR)


def use_amp(t):
    return shake_amp(t, USE_QUAKES, USE_TREMOR)


def unlock_frame(t, w, h):
    """The tesseract in the pocket unfolds into the ULTRA TESSERACT. t in seconds, 0..UNLOCK_SECONDS."""
    out, top = [], []
    if t < 1.4:                                                 # a small tesseract, pulsing, in the dark
        out += tess(t * 1.5, w, h, scale=0.28 + 0.06 * math.sin(t * 9))
        if t > 0.5:
            msg = "it is warm."
            out += [(w // 2 - len(msg) // 2, h - 3, msg, GREY)]
    elif t < 3.4:                                               # the hypercube unfolds into its net of eight cubes
        u = (t - 1.4) / 2.0
        e = u * u * (3 - 2 * u)
        out += tess(t * 1.2, w, h, scale=0.28 * (1 - e) + 0.05, col_shift=int(t * 4))
        out += net_cubes(t, w, h, e, spin=t * 1.1, scale=0.45 + 0.55 * e)
        msg = "UNFOLDING  %d / 8" % min(8, 1 + int(e * 8))
        out += [(w // 2 - len(msg) // 2, 1, msg, CYAN)]
    elif t < 5.2:                                               # nested rotations in every plane, with colour trails, the tremor starts
        u = (t - 3.4) / 1.8
        for ghost in range(4, -1, -1):
            out += tess(t - ghost * 0.07, w, h, scale=1.0 - ghost * 0.02, col_shift=int(t * 6) + ghost)
        out += tess(t * 1.6 + 7, w, h, scale=0.55 + 0.1 * math.sin(t * 5), speeds=(0.9, 0.5, 0.3, 1.1, 0.4, 0.8), col_shift=3)
        out += tess(t * 2.1 + 3, w, h, scale=0.28, speeds=(1.3, 0.9, 1.1, 0.5, 0.7, 1.7), col_shift=5)
    elif t < 6.6:                                               # charge-up: sparks spiral in, the circle closes, a sphere grows, violet -> white
        u = (t - 5.2) / 1.4
        out += circle(t, w, h, 1.0 - 0.3 * u)
        out += particles(t, u, w, h)
        out += disc(w / 2.0, h / 2.0, 1 + u * h * 0.22, ".:oO@", heat(u))
        if u > 0.6:
            out += rifts(t, w, h, (u - 0.6) * 1.5)
    elif t < 7.5:                                               # release (a small shock): the grid bends, the world goes white
        u = (t - 6.6) / 0.9
        out += shockwave(t, w, h, radius=4 + u * 40, amp=4.0)
        out += disc(w / 2.0, h / 2.0, 3 + u * h * 1.6, ".:oO@", WHITE if u > 0.5 else CYAN)
        top += whiteout(w, h, u ** 1.5)
    else:                                                       # white, then the title card
        u = min(1.0, (t - 7.5) / 0.9)
        if t < 7.8:
            top += whiteout(w, h, 1.0)
        top += title(w, h, u, subtitle="the tesseract has unfolded", lines=("once per fight:  time stops  -  +12 HP  -  3 s shield  -  half of Noah's life",))
    return _clip(shaken(_clip(out, w, h), t, w, h, unlock_amp(t)) + _clip(top, w, h), w, h)


# ---------------------------------------------------------------- the use cinematic
def _glitch_rows(rows, x0, y0, t, w, h, amount, seed=5):
    rng = random.Random(seed + int(t * 15))
    out = []
    for r, row in enumerate(rows):
        shift = rng.randint(-int(2 + 14 * amount), int(2 + 14 * amount)) if rng.random() < amount else 0
        for c, ch in enumerate(row):
            if ch == " ":
                continue
            if rng.random() < amount * 0.35:
                ch = rng.choice("#%@&$?!/\\|<>~^")
            out.append((x0 + c + shift, y0 + r, ch, RAINBOW[rng.randint(0, 7)] if rng.random() < amount else WHITE))
    return out


def scene_from(noah, heart):
    """A stand-in scene (tests, gallery) from Noah's art rows and the heart."""
    cells = []
    if noah:
        cells += [(noah[0], noah[1] + r, row, GREEN) for r, row in enumerate(noah[2]) if row.strip()]
    if heart:
        cells.append((heart[0], heart[1], "♥", RED))
    return cells


def use_frame(t, w, h, noah=None, heart=None, words=(), scene=None):
    """The ULTRA TESSERACT is used: dread, charge-up, release, aftershocks, aftermath, silence (see the module docstring).
    scene = the cells on screen when it was used (CursesScreen reads them); without it noah/heart make a small one."""
    scene = scene if scene is not None else scene_from(noah, heart)
    cx, cy = w / 2.0, h / 2.0
    out, top = [], []
    T_CHARGE, T_REL = 4.8, 6.6
    if t < T_REL:                                               # the old screen stays, dimmed, until it is torn apart
        k = min(1.0, max(0.0, (t - 0.1) / 0.5))
        out += [(x, y, ch, c if k < 0.5 else GREY) for x, y, ch, c in scene]
    if t < T_CHARGE:                                            # 1. silence and dread
        out += speech_box(t, w, h)
        if t > 3.0:
            out += [(int(cx + math.cos(a) * 6 * (t - 3.0)), int(cy + math.sin(a) * 2.5 * (t - 3.0)), ".", GREY) for a in [i * 0.9 for i in range(7)]]
    elif t < T_REL:                                             # 2. charge-up
        u = (t - T_CHARGE) / (T_REL - T_CHARGE)
        out += circle(t, w, h, 0.25 + 0.75 * u)
        out += particles(t, u, w, h, n=220)
        out += disc(cx, cy, 1 + u * u * h * 0.3, ".:oO@", heat(u))
        if u > 0.7:
            out += rifts(t, w, h, (u - 0.7) * 2)
    elif t < 7.85:                                              # 3. release
        tau = t - T_REL
        out += scene_blown(scene, tau, w, h)
        R = tau * 90
        out += disc(cx, cy, min(R, h * 3), ".:oO@", WHITE if tau > 0.3 else CYAN)
        out += shockwave(t, w, h, radius=tau * 60, amp=4.5)
        col = min(w // 2, int(2 + tau * 60))
        out += [(int(cx - col / 2), y, "█" * col, WHITE) for y in range(h)]              # the column of light
        for word in list(words)[:6]:
            rng = random.Random(len(word))
            ang = rng.uniform(0, 6.283)
            out.append((int(cx + math.cos(ang) * tau * 70), int(cy + math.sin(ang) * tau * 30), word, RAINBOW[len(word) % 8]))
        if tau > 0.6:                                           # the hard white-out, 0.45 s, no shake on it
            top += whiteout(w, h, 1.0)
        elif tau > 0.2 and int(tau * 20) % 2:
            top += whiteout(w, h, 0.5, seed=int(tau * 40))
    else:                                                       # 4./5. aftermath: ash over a crater, aftershocks, silence
        a = t - 7.85
        out += crater(w, h, min(1.0, a / 0.8))
        out += ash(t, w, h, n=int(90 * max(0.0, 1 - (t - 9.8) / 0.6)))
    return _clip(shaken(_clip(out, w, h), t, w, h, use_amp(t), seed=3) + _clip(top, w, h), w, h)




# ---------------------------------------------------------------- plain terminal output
def render_ansi(cells, w, h, truecolor=True):
    """A frame as one string for a plain terminal (cursor home first). Later cells win over earlier ones."""
    grid = {}
    for x, y, ch, col in cells:
        for i, g in enumerate(ch):
            grid[(x + i, y)] = (g, col)
    out = ["\033[H"]
    for y in range(h):
        row, last = [], None
        for x in range(w):
            ch, col = grid.get((x, y), (" ", None))
            if col != last:
                row.append("\033[0m" if col is None else ("\033[1;38;2;%d;%d;%dm" % PALETTE[col][1] if truecolor else "\033[1;38;5;%dm" % PALETTE[col][3]))
                last = col
            row.append(ch)
        out.append("".join(row) + "\033[0m")
    return "\n".join(out)
