"""ultra_bonus.py - the extra animated bonuses of the ULTRA TESSERACT inside the fight (pure frame generators, no curses, no I/O).

    beam(t, src, dst)                        - BEAM_SECONDS: the cube fires a beam onto Noah's picture (grows, burns white, fades, sparks at the target)
    mika(t, sil, wiped, mouth_to_left)       - MIKA_SECONDS: Mika's silhouette fades in, takes a breath, and a wall of smoke sweeps over the arena;
                                               the attacks (`wiped`: the cells that were on screen) vanish where the smoke has passed
    ghost_layers(history)                    - afterimages while time is frozen: older snapshots of the attacks get dimmer glyphs
Cells are (x, y, text, colour) with ultra_fx.PALETTE indices, exactly like the other cinematics.
"""
import math
import random

import ultra_fx as U

BEAM_SECONDS = 1.8
MIKA_SECONDS = 3.6
MIKA = [          # a hood, a long coat, hands in the pockets; the mouth is at row MOUTH
    "   ▄████▄   ",
    "  ████████  ",
    "  ██▀  ▀██  ",
    "  ██    ██  ",
    "  ▀██▄▄██▀  ",
    " ▄████████▄ ",
    "▐██████████▌",
    "▐██████████▌",
    "▐██▌ ██ ▐██▌",
    " ██▌ ██ ▐██ ",
    " ██▌ ██ ▐██ ",
    " ▀▀  ▀▀  ▀▀ ",
]
MOUTH = (3, 3)   # (row, column) of the cigarette tip


def beam(t, src, dst):
    """The cube beam from src to dst (screen cells). t in seconds, 0..BEAM_SECONDS."""
    out = []
    grow = min(1.0, t / 0.45)
    fade = 1.0 if t < 1.2 else max(0.0, 1.0 - (t - 1.2) / 0.6)
    if fade <= 0:
        return out
    x1, y1 = src[0] + (dst[0] - src[0]) * grow, src[1] + (dst[1] - src[1]) * grow
    pts = []
    U._line(src[0], src[1], int(x1), int(y1), "", 0, pts)
    for i, p in enumerate(pts):
        x, y = p[0], p[1]
        core = int(t * 30 + i) % 3
        out.append((x, y, "█" if fade > 0.5 else "▒", U.WHITE if core else U.CYAN))
        out += [(x - 1, y, "░", U.CYAN), (x + 1, y, "░", U.CYAN)]
    rng = random.Random(int(t * 24))
    if grow >= 1.0:                                   # sparks where it lands
        for _ in range(int(14 * fade)):
            a, r = rng.uniform(0, 2 * math.pi), rng.uniform(1, 7)
            out.append((int(dst[0] + math.cos(a) * r * 2), int(dst[1] + math.sin(a) * r), rng.choice("*+.x"), U.WHITE if rng.random() < 0.6 else U.CYAN))
    out.append((src[0] - 1, src[1], "[#]", U.CYAN))
    return out


def mika(t, sil, wiped, front_x):
    """Mika at screen cell `sil` (top-left); `wiped` = [(x, y, ch)] the attacks the smoke clears; front_x(t) = the x the smoke has reached so far
    (cells to its right are clear). t in seconds, 0..MIKA_SECONDS."""
    out = []
    x0, y0 = sil
    f = min(1.0, t / 0.7) if t < 2.9 else max(0.0, 1.0 - (t - 2.9) / 0.7)          # fades in row by row, and out again at the end
    for r in range(int(f * len(MIKA) + 0.999)):
        out.append((x0, y0 + r, MIKA[r], U.GREY))
    mx, my = x0 + MOUTH[1], y0 + MOUTH[0]
    if 0.8 <= t < 1.3:                                # the breath in: the cigarette tip glows
        out.append((mx, my, "●", U.ORANGE))
    elif t >= 1.3 and t < 3.0:
        out.append((mx, my, "•", U.ORANGE))
    fx = front_x(t)
    for (x, y, ch) in wiped:
        if x < fx:                                    # not reached by the smoke yet
            out.append((x, y, ch, U.RED))
    if 1.3 <= t < 3.4:                                # the breath out: smoke rolls to the left, widening
        u = t - 1.3
        rng = random.Random(11)
        for i in range(120):
            age = u - rng.uniform(0, 1.2)
            if age <= 0:
                continue
            x = mx - age * 38 - rng.uniform(0, 3)
            y = my + math.sin(age * 4 + i) * (1 + age * 3) + rng.uniform(-1, 1) * age * 2
            out.append((int(x), int(y), rng.choice("~°oO.:"), U.WHITE if i % 3 else U.GREY))
    return out


def front(mouth_x, t):
    """Where the front of the smoke is at time t (it leaves the mouth at 1.3 s and runs left at 38 cells/s)."""
    return mouth_x - max(0.0, t - 1.3) * 38


def ghost_layers(history):
    """history: list of snapshots [(x, y, ch)] of the attacks, oldest first. Returns cells: the older, the dimmer and plainer."""
    out = []
    n = len(history)
    for i, snap in enumerate(history):
        age = n - 1 - i
        if age == 0:
            continue                                   # the newest one is the real picture
        col, glyph = (U.CYAN, ":") if age == 1 else ((U.BLUE, ".") if age == 2 else (U.GREY, "'"))
        out += [(x, y, glyph, col) for x, y, _ch in snap]
    return out
