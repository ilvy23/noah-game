"""setpieces.py - the dramatic moments of the Noah fight as pure frame generators (no curses, no I/O, deterministic).

    begin1..begin4   - the start of each phase: a silent beat, then the hit and a title card (begin4, the fusion, is the huge one)
    thr50, thr20     - Noah's life crosses 50% / 20%: a slam, a line of text, and his portrait in front of the screen
A piece is a dict(seconds, frame(t, w, h, text) -> cells, quakes, tremor, flash, sfx, art(t) -> (state, frame) or None, col).
Cells are (x, y, text, colour) exactly like ultra_fx (same PALETTE indices); CursesScreen.setpiece plays them.
"""
import math
import random

import fx
import ultra_fx as U

LETTERS = dict(U.LETTERS)
LETTERS.update({
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"], "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "H": ["█   █", "█   █", "█████", "█   █", "█   █"], "I": ["█████", "  █  ", "  █  ", "  █  ", "█████"],
    "B": ["████ ", "█   █", "████ ", "█   █", "████ "],
})
TINT = {1: U.GREEN, 2: U.YELLOW, 3: U.RED, 4: U.WHITE}
DEFAULT_TEXT = {   # drafts: the owner's boss_texts.json overrides every one of them (key boss.beat.<piece>)
    "begin1": "...I don't want to do this.",
    "begin2": "You're still standing. How lovely.",
    "begin3": "Now you'll see what is under the floor.",
    "begin4": "We are done taking turns.",
    "thr50.2": "Hm. You hit harder than you look.",
    "thr50.3": "Is that all you've got? Come on. COME ON.",
    "thr50.4": "Three voices. One mouth. Still not enough?",
    "thr20.3": "I can still hear her. Louder. LOUDER.",
    "thr20.4": "Almost. Almost. Don't look away.",
}


def big(word, scale=1):
    """The word in block letters: list of 5*scale strings; scale 2 doubles every cell in both directions."""
    rows = ["  ".join(LETTERS.get(c, LETTERS[" "])[r] for c in word) for r in range(5)]
    if scale == 1:
        return rows
    return [("".join(ch * scale for ch in row)) for row in rows for _ in range(scale)]


def title_cells(word, w, y, col, f=1.0, scale=1, colfn=None):
    """Centred block-letter title, revealed left to right by f (0..1); too narrow for the block font: plain spaced letters."""
    rows = big(word, scale)
    if len(rows[0]) + 2 > w:
        rows = big(word, 1)
        if len(rows[0]) + 2 > w:
            txt = " ".join(word)
            return [(max(0, (w - len(txt)) // 2), y, txt[:int(len(txt) * f + 0.5)], col)]
    x0, shown = (w - len(rows[0])) // 2, int(f * (len(rows[0]) + 1))
    out = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch != " " and c < shown:
                out.append((x0 + c, y + r, ch, colfn(c, r, len(row)) if colfn else col))
    return out


def typed_line(text, w, y, t, t0, col, cps=32.0):
    if t < t0 or not text:
        return []
    s = text[:int((t - t0) * cps) + 1]
    return [(max(0, (w - len(text)) // 2), y, s, col)]


def _quake(t, quakes, tremor):
    return U.shake_amp(t, quakes, tremor)


def _cracks(w, h, f, seed=5, col=U.RED):
    """Cracks that grow out of the middle: random walks, longer with f (0..1)."""
    rng, out = random.Random(seed), []
    for k in range(9):
        x, y, a = w / 2.0, h / 2.0, rng.uniform(0, 2 * math.pi)
        for i in range(int(f * 40)):
            a += rng.uniform(-0.5, 0.5)
            x, y = x + math.cos(a) * 2.0, y + math.sin(a) * 0.9
            out.append((int(x), int(y), "/\\|-"[int((a / (math.pi / 2)) % 4)], col))
    return out


def _heart(cx, cy, size, col):
    rows = [" ██ ██ ", "███████", " █████ ", "  ███  ", "   █   "] if size else ["♥"]
    return [(cx - len(r) // 2, cy - 2 + i, r, col) for i, r in enumerate(rows)] if size else [(cx, cy, "♥", col)]


def _finish(cells, t, w, h, quakes, tremor):
    return U.shaken(U._clip(cells, w, h), t, w, h, _quake(t, quakes, tremor))


# ---------------------------------------------------------------- the phase openings
def _begin1(t, w, h, text):
    out = fx.ambient(1, t, w, h, rng_seed=1, n=30)
    out = [(x, y, c, U.GREEN) for x, y, c in out] if t > 0.4 else []
    if t > 0.8:
        out += title_cells("NOAH", w, h // 2 - 4, U.GREEN, f=min(1.0, (t - 0.8) / 1.0))
    out += typed_line(text, w, h // 2 + 4, t, 2.2, U.WHITE)
    return _finish(out, t, w, h, *Q["begin1"])


def _begin2(t, w, h, text):
    out = []
    if t < 1.0:                                                   # a thin line draws itself out of the dark
        half = int(w * 0.5 * min(1.0, t / 0.9))
        out += [(w // 2 - half, h // 2, "─" * (2 * half), U.YELLOW)]
    if t >= 1.0:                                                  # bars slam down like a cell door
        reach = h if t > 1.25 else int(h * (t - 1.0) / 0.25)
        for x in range(2, w, 6):
            out += [(x, y, "║", U.YELLOW) for y in range(min(reach, h))]
    if t >= 1.5 and t < 3.9:
        out += title_cells("LISTEN", w, h // 2 - 2, U.YELLOW, f=min(1.0, (t - 1.5) / 0.5))
    if t >= 3.9:
        out += title_cells("LISTEN", w, h // 2 - 2, U.YELLOW, f=max(0.0, 1.0 - (t - 3.9) / 0.4))
    out += typed_line(text, w, h // 2 + 5, t, 2.4, U.WHITE)
    return _finish(out, t, w, h, *Q["begin2"])


def _begin3(t, w, h, text):
    out = []
    beats = (0.5, 0.78, 1.5, 1.74, 2.2, 2.38, 2.56)               # ba-dum ... ba-dum ... ba-dum-dum, getting faster
    pulse = max([0.0] + [1.0 - (t - b) / 0.2 for b in beats if 0 <= t - b < 0.2])
    if t < 3.0:
        out += _heart(w // 2, h // 2, pulse > 0.3, U.RED)
        out += _cracks(w, h, min(1.0, t / 2.8), col=U.RED if t < 2.4 else U.ORANGE)
    elif t < 3.25:
        out += U.whiteout(w, h, (t - 3.0) / 0.25)
    else:
        rng = random.Random(int(t * 12))
        out += [(rng.randint(0, w - 1), h - 1 - int((t * 9 + i * 3) % h), "^", U.ORANGE if i % 3 else U.RED) for i in range(60)]
        out += title_cells("BURN", w, h // 2 - 3, U.RED, f=min(1.0, (t - 3.25) / 0.4), colfn=lambda c, r, n: U.ORANGE if r < 2 else U.RED)
    out += typed_line(text, w, h // 2 + 4, t, 3.7, U.WHITE)
    return _finish(out, t, w, h, *Q["begin3"])


def _begin4(t, w, h, text):
    out = []
    cx, cy = w // 2, h // 2
    if t < 1.8:                                                   # three hearts, one from each side, run into each other
        f = t / 1.8
        for (sx, sy, col) in ((2, cy, U.GREEN), (w - 3, cy, U.YELLOW), (cx, 1, U.RED)):
            x, y = sx + (cx - sx) * f * f, sy + (cy - sy) * f * f
            out.append((int(x), int(y), "♥", col))
            out += [(int(sx + (cx - sx) * g * g), int(sy + (cy - sy) * g * g), "·", col) for g in (f * k / 10 for k in range(10))]
    elif t < 3.0:
        u = t - 1.8
        out += [(x, y, c, (U.GREEN, U.YELLOW, U.RED)[max(0, min(2, x * 3 // max(1, w)))]) for x, y, c, _ in U.shockwave(u, w, h, u * 18)]
    elif t < 3.4:
        out += U.whiteout(w, h, (t - 3.0) / 0.4)
    else:
        colfn = lambda c, r, n: (U.GREEN, U.YELLOW, U.RED)[min(2, c * 3 // max(1, n))]
        if t > 5.4 and int(t * 10) % 2:                           # at the end the three keep flickering past each other
            colfn = lambda c, r, n: (U.RED, U.GREEN, U.YELLOW)[min(2, c * 3 // max(1, n))]
        out += title_cells("ALL", w, max(0, h // 2 - 7), U.WHITE, f=min(1.0, (t - 3.4) / 0.4), scale=2, colfn=colfn)
    out += typed_line(text, w, h // 2 + 6, t, 4.2, U.WHITE, cps=24.0)
    return _finish(out, t, w, h, *Q["begin4"])


# ---------------------------------------------------------------- HP thresholds
def _thr(pct):
    def frame(t, w, h, text, phase=3):
        col, out = TINT.get(phase, U.RED), []
        y = h - 5
        if t >= 0.25:
            grow = min(1.0, (t - 0.25) / 0.15)
            out += [(0, y + dy, ("▓" if dy == 0 else "░") * int(w * grow), col) for dy in (-1, 0, 1)]
            out += [(max(0, (w - len(text)) // 2) - 1, y, " " * (len(text) + 2), U.WHITE)]
            out += typed_line(text, w, y, t, 0.45, U.WHITE, cps=40.0)
        if t < 0.25 and int(t * 20) % 2:
            out += [(0, h // 2, "─" * w, col)]
        if pct == 20 and t >= 0.25 and int(t * 12) % 4 == 0:      # near the end the picture stutters
            out += [(random.Random(int(t * 12)).randint(0, w - 1), random.Random(int(t * 12) + 1).randint(0, h - 1), "#", col) for _ in range(30)]
        return _finish(out, t, w, h, *Q["thr%d" % pct])
    return frame


Q = {   # (quakes, tremor) per piece
    "begin1": (((2.6, 0.25, 0.3),), None),
    "begin2": (((1.5, 0.9, 0.45), (1.9, 0.35, 0.3)), None),
    "begin3": (((0.5, 0.15, 0.1), (1.5, 0.2, 0.1), (3.0, 1.0, 0.55), (3.4, 0.5, 0.4)), (2.2, 3.0, 0.05, 0.4)),
    "begin4": (((1.8, 0.5, 0.3), (3.0, 1.0, 0.7), (3.45, 0.8, 0.5), (4.2, 0.45, 0.5)), (1.2, 3.0, 0.03, 0.5)),
    "thr50": (((0.25, 0.7, 0.35),), None),
    "thr20": (((0.25, 0.95, 0.5), (0.9, 0.4, 0.3)), None),
}
PIECES = {
    "begin1": dict(seconds=3.8, frame=_begin1, flash=(2.6,), sfx=[(2.6, "slam")], art=None),
    "begin2": dict(seconds=4.4, frame=_begin2, flash=(1.5,), sfx=[(1.0, "warning"), (1.5, "slam")], art=None),
    "begin3": dict(seconds=5.0, frame=_begin3, flash=(3.0,), sfx=[(0.5, "heartbeat"), (1.5, "heartbeat"), (2.2, "heartbeat"), (3.0, "slam"), (3.3, "noah-roar")], art=None),
    "begin4": dict(seconds=6.8, frame=_begin4, flash=(1.8, 3.0), sfx=[(1.0, "warning"), (1.8, "slam"), (3.0, "slam"), (3.4, "noah-roar")], art=None),
    "thr50": dict(seconds=2.6, frame=_thr(50), flash=(0.25,), sfx=[(0.25, "slam"), (0.4, "noah-roar")],
                  art=lambda t: ("hurt", min(2, int(t * 6))) if t < 0.9 else ("strike", int(t * 8) % 3)),
    "thr20": dict(seconds=3.0, frame=_thr(20), flash=(0.25, 0.9), sfx=[(0.25, "slam"), (0.4, "noah-roar")],
                  art=lambda t: ("hurt", min(2, int(t * 6))) if t < 0.9 else ("strike", int(t * 8) % 3)),
}
for _n, _p in PIECES.items():
    _p["quakes"], _p["tremor"] = Q[_n]


def get(name):
    return PIECES[name]


def text_key(name, phase=None):
    """The id of the owner's text for a piece: boss.beat.begin2, boss.beat.thr50.3 ..."""
    return "boss.beat.%s" % (name if name.startswith("begin") else "%s.%d" % (name, phase))


def default_text(name, phase=None):
    return DEFAULT_TEXT.get(name if name.startswith("begin") else "%s.%d" % (name, phase), "")


def amp(name, t):
    p = PIECES[name]
    return U.shake_amp(t, p["quakes"], p["tremor"])
