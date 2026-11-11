"""patterns.py - the themed attack patterns of the fight (pure logic: no curses, no I/O, deterministic with a seeded rng).

A pattern is a small list of Hazards. Every hazard first shows a harmless GHOST (the telegraph, `warn` seconds), then is
LIVE for `live` seconds and can hurt the heart once. Cells are arena cells (x 0..W-1, y 0..H-1).
    green  (phase 1): teacups, honey, fox, notes     yellow (phase 2): bars, kneel, cuts, smiles
    red    (phase 3): ring, veins, burn, grasp       fusion (phase 4): all of them + the 'trinity' set-piece
"""
import math
import random

W, H = 41, 11
FOX = "<^.^>~"
SMILE = "\\_____/"
NOTES = "\u266a\u266b"


# ---------------------------------------------------------------- DIFFICULTY KNOBS (patterns side; boss.py has DIFFICULTY for the rest)
# tight: set by Boss per phase before a pattern is built. < 1 = narrower gaps, smaller lit circle, faster/sharper orbs; > 1 = kinder.
tight = 1.0


def _g(x, lo=2):
    """A gap/size from its base value, scaled by `tight` (never below lo)."""
    return max(lo, int(round(x * tight)))


class Hazard:
    __slots__ = ("kind", "warn", "live", "dmg", "d", "age", "hit")

    def __init__(self, kind, warn, live, dmg=3, **d):
        self.kind, self.warn, self.live, self.dmg, self.d, self.age, self.hit = kind, warn, live, dmg, d, 0.0, False

    @property
    def harmful(self):
        return self.warn <= self.age < self.warn + self.live

    @property
    def done(self):
        return self.age >= self.warn + self.live

    def cells(self):
        """Harmful cells now: [(x, y, ch)] (empty while only the ghost is shown)."""
        return [c for c in _CELLS[self.kind](self) if 0 <= c[0] < W and 0 <= c[1] < H] if self.harmful else []

    def ghost(self):
        """Telegraph cells: [(x, y, ch)] shown before it goes live."""
        return [c for c in _GHOST[self.kind](self) if 0 <= c[0] < W and 0 <= c[1] < H] if self.age < self.warn else []

    def s(self):
        """Progress through the live part, 0..1."""
        return min(1.0, max(0.0, (self.age - self.warn) / self.live))


# ---------------------------------------------------------------- shapes
def _rect_cells(h):
    d = h.d
    rows = d["h"]
    shown = rows if not d.get("grow") else max(1, int(math.ceil(rows * min(1.0, (h.age - h.warn) / d["grow"]))))
    top = d["y"] + (rows - shown if d.get("up") else 0)
    return [(d["x"] + i, top + j, d["ch"]) for j in range(shown) for i in range(d["w"])]


def _rect_ghost(h):
    d = h.d
    return [(d["x"] + i, d["y"] + j, d["tele"]) for j in range(d["h"]) for i in range(d["w"])]


def _path_cells(h):
    return [(x, y, h.d["ch"]) for x, y in h.d["pts"]]


def _path_ghost(h):
    return [(x, y, h.d["tele"]) for x, y in h.d["pts"]]


def _ring_radius(h):
    d = h.d
    return d["a0"] + (d["a1"] - d["a0"]) * h.s()


def _ring_points(h, a, step=1):
    d = h.d
    out = []
    n = int(a * (9 if d.get("thick") else 5)) + 24
    gap = d["gap"] + d.get("spin", 0) * max(0.0, h.age - h.warn)       # a cage: the gap turns while the ring closes
    for k in range(0, n, step):
        ang = 2 * math.pi * k / n
        diff = abs((math.degrees(ang) - gap + 180) % 360 - 180)
        if diff <= d["gap_w"] / 2:
            continue
        for rr in ((a, a - 1.0) if d.get("thick") and step == 1 else (a,)):      # a thick ring cannot be skipped between two frames
            out.append((int(round(d["cx"] + math.cos(ang) * rr)), int(round(d["cy"] + math.sin(ang) * rr * 0.5)),
                        "\u2720" if k % 2 else "+"))
    return out


def _bar_cells(h):
    d = h.d
    ang = d["a0"] + d["w"] * (h.age - h.warn)
    out = []
    for arm in (0.0, math.pi):
        r = 0.0
        while r <= d["L"]:
            x = d["cx"] + math.cos(ang + arm) * r * 2
            y = d["cy"] + math.sin(ang + arm) * r
            out += [(int(round(x)), int(round(y)), _bar_ch(ang)), (int(round(x)) + 1, int(round(y)), _bar_ch(ang))]
            r += 0.5
    return out


def _bar_ch(ang):
    a = math.degrees(ang) % 180
    return "-" if (a < 22 or a > 158) else ("|" if 68 < a < 112 else ("\\" if a < 68 else "/"))


def _bar_ghost(h):
    d = h.d
    out = []
    for arm in (0.0, math.pi):
        for r in range(0, d["L"] + 1, 2):
            out.append((int(round(d["cx"] + math.cos(d["a0"] + arm) * r * 2)), int(round(d["cy"] + math.sin(d["a0"] + arm) * r)), "."))
    return out


def _cup_pos(h):
    d, s = h.d, h.s()
    return d["x0"] + (d["x1"] - d["x0"]) * s, (H - 1) - d["peak"] * 4 * s * (1 - s)


def _cup_cells(h):
    x, y = _cup_pos(h)
    return [(int(round(x)) + i, int(round(y)), c) for i, c in enumerate("(_)")]


def _cup_ghost(h):
    d = h.d
    from_left = d["x0"] < 0
    return [(d["x1"] + i, H - 1, c) for i, c in enumerate("v v")] + [(0 if from_left else W - 1, H - 2, ">" if from_left else "<")]


def _drip_cells(h):
    y = int((h.age - h.warn) * h.d["speed"]) - 1
    return [(h.d["x"], y, ":"), (h.d["x"], y + 1, "\u25cf")]


def _drip_ghost(h):
    return [(h.d["x"], 0, "\u25cf" if int(h.age * 6) % 2 else ":")]


def _fox_cells(h):
    d = h.d
    x = -len(FOX) + (h.age - h.warn) * d["speed"] if d["dir"] > 0 else W - (h.age - h.warn) * d["speed"]
    txt = FOX if d["dir"] > 0 else FOX[::-1].translate(str.maketrans("<>", "><"))
    return [(int(round(x)) + i, d["y"], c) for i, c in enumerate(txt)]


def _fox_ghost(h):
    d = h.d
    return [(i, d["y"], "\u00b7" if (i + int(h.age * 8)) % 3 else "'") for i in range(0, W, 2)]


def _note_cells(h):
    d = h.d
    y = (h.age - h.warn) * d["speed"] - 1
    return [(int(round(d["x"] + math.sin((h.age + d["ph"]) * 2.2) * 1.6)), int(round(y)), NOTES[d["k"] % 2])]


def _note_ghost(h):
    return [(h.d["x"], 0, "\u00b7")]


def _smile_cells(h):
    d = h.d
    x = -len(SMILE) + (h.age - h.warn) * d["speed"] if d["dir"] > 0 else W - (h.age - h.warn) * d["speed"]
    return [(int(round(x)) + i, d["y"], c) for i, c in enumerate(SMILE)]


def _smile_ghost(h):
    d = h.d
    edge = 0 if d["dir"] > 0 else W - 4
    return [(edge + i, d["y"], ">" if d["dir"] > 0 else "<") for i in range(3)]


# ---- v2 shapes: curtain, orb, split, spiral, comb, beam, box, gravity, dark, pillar
def _curtain_cells(h):
    d = h.d
    y = int((h.age - h.warn) * d["speed"])
    return [(x, yy, d["ch"]) for x in range(W) if not d["g0"] <= x <= d["g1"] for yy in (y - 1, y)]


def _curtain_ghost(h):
    d = h.d
    out = [(x, 0, " " if d["g0"] <= x <= d["g1"] else d["tele"]) for x in range(W)]
    return out + [(x, y, ":") for y in (3, 6, 9) for x in (d["g0"] - 1, d["g1"] + 1)]


def _orb_cells(h):
    d = h.d
    return [(int(round(d["px"])) - 1 + i, int(round(d["py"])), c) for i, c in enumerate("(o)")]


def _orb_ghost(h):
    d = h.d
    return [(int(round(d["px"])) - 1 + i, int(round(d["py"])), c) for i, c in enumerate("(.)")]


def _orb_step(h, dt, b):
    """Homing with a limited turn rate: it follows the heart but cannot follow a sharp change of direction."""
    d = h.d
    want = math.atan2((b.hy - d["py"]) * 2, b.hx - d["px"])
    diff = (want - d["a"] + math.pi) % (2 * math.pi) - math.pi
    lim = math.radians(d["turn"]) * dt
    d["a"] += max(-lim, min(lim, diff))
    d["px"] += math.cos(d["a"]) * d["sp"] * 2 * dt
    d["py"] += math.sin(d["a"]) * d["sp"] * dt


def _split_cells(h):
    d, t = h.d, h.age - h.warn
    if t < d["ts"]:                                              # the big one falls, blinking faster before it bursts
        txt = "(O)" if d["ts"] - t < 0.45 and int(t * 14) % 2 else "(@)"
        return [(d["x"] - 1 + i, int(round(-1 + d["v"] * t)), c) for i, c in enumerate(txt)]
    ys, u, out = -1 + d["v"] * d["ts"], t - d["ts"], []
    for k in range(d["n"]):
        a = d["a0"] + 2 * math.pi * k / d["n"]
        x, y = int(round(d["x"] + math.cos(a) * d["sp"] * 2 * u)), int(round(ys + math.sin(a) * d["sp"] * u))
        out += [(x, y, "*" if k % 2 else "."), (x + 1, y, "*" if k % 2 else ".")]
    return out


def _split_ghost(h):
    d = h.d
    ys = int(-1 + d["v"] * d["ts"])
    return [(d["x"] - 1 + i, 0, c) for i, c in enumerate("(@)")] + [(d["x"], y, ":") for y in range(1, ys + 1)] + [(d["x"], ys, "x")]


def _spiral_pts(d, t, ch=None):
    out = []
    for arm in range(d["arms"]):
        for k in range(d["n"]):
            r = d["sp"] * (t - k * d["dt"])
            if r < 2.5:
                continue                                          # the eye in the middle stays safe
            a = d["a0"] + d["dir"] * k * d["rot"] + arm * 2 * math.pi / d["arms"]
            x, y = int(round(d["cx"] + math.cos(a) * r * 2)), int(round(d["cy"] + math.sin(a) * r))
            c = ch or d["chs"][arm % len(d["chs"])]
            out += [(x, y, c), (x + 1, y, c)]
    return out


def _spiral_ghost(h):
    d = h.d
    return _spiral_pts(d, 3.0, "·") + [(d["cx"] - 1 + i, d["cy"], c) for i, c in enumerate("(@)")]


def _comb_cells(h):
    d, t, out = h.d, h.age - h.warn, []
    for y, dr in d["rows"]:
        x = int(round(-d["L"] + t * d["speed"] if dr > 0 else W - t * d["speed"]))
        out += [(x + i, y, d["ch"]) for i in range(d["L"])]
    return out


def _comb_ghost(h):
    out = []
    for y, dr in h.d["rows"]:
        out += [(i, y, ">") for i in range(3)] if dr > 0 else [(W - 3 + i, y, "<") for i in range(3)]
    return out


def _beam_cells(h):
    return _rect_cells(h)


def _beam_ghost(h):
    d = h.d
    if h.warn - h.age < 0.3:                                      # the last moment: the whole beam flashes where it will fire
        return [(d["x"] + i, d["y"] + j, "#") for j in range(d["h"]) for i in range(d["w"])]
    if d["h"] == 1:
        return [(i, d["y"], "-" if i % 2 else "·") for i in range(0, W)]
    return [(d["x"] + d["w"] // 2, j, "|" if j % 2 else "·") for j in range(H)]


def _box_rect(h):
    """The open part of the arena right now (x0, x1, y0, y1), interpolated between the keyframes."""
    s, keys = h.s(), h.d["keys"]
    for (s0, a), (s1, b) in zip(keys, keys[1:]):
        if s0 <= s <= s1:
            f = (s - s0) / (s1 - s0) if s1 > s0 else 1.0
            return [a[i] + (b[i] - a[i]) * f for i in range(4)]
    return list(keys[-1][1])


def _box_cells(h):
    x0, x1, y0, y1 = _box_rect(h)
    return [(x, y, h.d["ch"]) for y in range(H) for x in range(W) if x < x0 - 0.01 or x > x1 + 0.01 or y < y0 - 0.01 or y > y1 + 0.01]


def _box_ghost(h):
    x0, x1, y0, y1 = h.d["keys"][1][1]                            # the first target box
    x0, x1, y0, y1 = int(x0), int(x1), int(y0), int(y1)
    return [(x, y, h.d["tele"]) for x in range(x0, x1 + 1) for y in (y0, y1)] + [(x, y, h.d["tele"]) for y in range(y0, y1 + 1) for x in (x0, x1)]


def _arrows_ghost(h):
    """Gravity: arrows on the edge it pulls towards (small dots while it is still far away)."""
    d = h.d
    if h.warn - h.age > 1.3:
        return [(W // 2, H // 2, "·")]
    y, ch = (H - 1, "v") if d["dir"] > 0 else (0, "^")
    return [(x, y, ch) for x in range(1, W, 3)]


def _gravity_step(h, dt, b):
    b.gravity = h.d["dir"]


def _dark_step(h, dt, b):
    b.dark = h.d["r"]


def _dark_ghost(h):
    return [(x, y, "·") for x in (0, W - 1) for y in (0, H - 1)] + [(W // 2 + i, H // 2, c) for i, c in enumerate("...")]


def _pillar_cells(h):
    d = h.d
    shown = max(1, int(math.ceil(d["hgt"] * min(1.0, (h.age - h.warn) / d["grow"]))))
    return [(d["x"] + i, H - 1 - j, d["ch"]) for j in range(shown) for i in range(d["w"])]


def _pillar_ghost(h):
    d = h.d
    return [(d["x"] + i, H - 1 - j, "^") for j in range(2) for i in range(d["w"])]


STEP = {"orb": _orb_step, "gravity": _gravity_step, "dark": _dark_step}    # kinds that act on the fight (steppers get (hazard, dt, boss))


_CELLS = {"rect": _rect_cells, "path": _path_cells, "ring": lambda h: _ring_points(h, _ring_radius(h)), "bar": _bar_cells,
          "cup": _cup_cells, "drip": _drip_cells, "fox": _fox_cells, "note": _note_cells, "smile": _smile_cells,
          "curtain": _curtain_cells, "orb": _orb_cells, "split": _split_cells, "spiral": lambda h: _spiral_pts(h.d, h.age - h.warn),
          "comb": _comb_cells, "beam": _beam_cells, "box": _box_cells, "gravity": lambda h: [], "dark": lambda h: [], "pillar": _pillar_cells}
_GHOST = {"rect": _rect_ghost, "path": _path_ghost, "ring": lambda h: _ring_points(h, h.d.get("gr") or (h.d["a0"] if h.d["a0"] < 20 else 17), 3),
          "bar": _bar_ghost, "cup": _cup_ghost, "drip": _drip_ghost, "fox": _fox_ghost, "note": _note_ghost, "smile": _smile_ghost,
          "curtain": _curtain_ghost, "orb": _orb_ghost, "split": _split_ghost, "spiral": _spiral_ghost, "comb": _comb_ghost,
          "beam": _beam_ghost, "box": _box_ghost, "gravity": _arrows_ghost, "dark": _dark_ghost, "pillar": _pillar_ghost}


# ---------------------------------------------------------------- patterns
def _line(x0, y0, x1, y1, thick=2):
    n = int(max(abs(x1 - x0), abs(y1 - y0) * 2)) + 1
    pts = []
    for i in range(n + 1):
        f = i / n
        x, y = int(round(x0 + (x1 - x0) * f)), int(round(y0 + (y1 - y0) * f))
        pts += [(x + k, y) for k in range(thick)]
    return pts


def teacups(rng, hx, hy, power):
    side = rng.choice([-1, 1])
    out = []
    for i in range(3):
        x1 = int(min(W - 4, max(3, hx + rng.randint(-9, 9))))
        out.append(Hazard("cup", 0.9 + 0.5 * i, 1.4, dmg=4, x0=-4 if side > 0 else W + 1, x1=x1, peak=rng.randint(6, 8)))
    return out


def honey(rng, hx, hy, power):
    xs = rng.sample(range(2, W - 2, 3), 5)
    return [Hazard("drip", 1.0 + 0.25 * i, 1.6, dmg=2, x=x, speed=8.0, slow=True) for i, x in enumerate(xs)]


def fox(rng, hx, hy, power):
    y = int(min(H - 2, max(1, round(hy) + rng.choice([-2, -1, 0, 1, 2]))))
    return [Hazard("fox", 1.0, 3.2, dmg=4, y=y, dir=rng.choice([-1, 1]), speed=15.0)]


def notes(rng, hx, hy, power):
    base = rng.randint(3, W - 12)
    out = []
    for i in range(7):
        out.append(Hazard("note", 0.6 + 0.22 * i, 2.6, dmg=3, x=(base + i * 4) % (W - 3) + 1, speed=5.0 + rng.random() * 2, ph=rng.random() * 6, k=i))
    return out


def bars(rng, hx, hy, power):
    return [Hazard("bar", 1.1, 2.6, dmg=4, cx=rng.randint(10, W - 10), cy=H // 2, L=13, a0=rng.uniform(0, math.pi), w=rng.choice([-1, 1]) * 0.85)]


def kneel(rng, hx, hy, power):
    out = []
    for i in range(2):
        x = int(min(W - 9, max(1, hx + rng.randint(-10, 10) - 3)))
        out.append(Hazard("rect", 1.0 + 0.6 * i, 0.4, dmg=4, x=x, y=H - 4, w=7, h=4, ch="\u2593", tele="K"))
    return out


def cuts(rng, hx, hy, power):
    out = []
    for i in range(2):
        left = i % 2 == 0
        y0, y1 = (0, H - 1) if rng.random() < 0.5 else (H - 1, 0)
        x0 = rng.randint(2, 14) if left else rng.randint(26, 38)
        pts = _line(x0, y0, x0 + rng.choice([-9, 9]), y1)
        out.append(Hazard("path", 1.0 + 0.7 * i, 0.35, dmg=4, pts=pts, ch="/", tele="\u00b7"))
    return out


def smiles(rng, hx, hy, power):
    y = rng.randint(1, H - 2)
    return [Hazard("smile", 1.0, 3.0, dmg=3, y=y, dir=1, speed=13.0), Hazard("smile", 1.0, 3.0, dmg=3, y=H - 1 - y if H - 1 - y != y else y - 1, dir=-1, speed=13.0)]


def ring(rng, hx, hy, power):
    cx, cy = W // 2, H // 2
    toward = math.degrees(math.atan2((hy - cy) * 2, hx - cx)) % 360
    gap = (toward + rng.choice([-1, 1]) * rng.uniform(55, 100)) % 360
    return [Hazard("ring", 1.2, 2.6, dmg=4, cx=cx, cy=cy, a0=22, a1=3, gap=gap, gap_w=_g(110, 80))]


def veins(rng, hx, hy, power):
    out = []
    for i, x0 in enumerate(rng.sample([4, 12, 20, 28, 36], 2)):
        ph = rng.random() * 6
        pts = []
        for y in range(H):
            x = int(round(x0 + math.sin(y * 0.8 + ph) * 3 + (y - 5) * rng.choice([-0.4, 0.4]) * 0))
            pts += [(x, y), (x + 1, y)]
        out.append(Hazard("path", 1.1 + 0.4 * i, 0.5, dmg=4, pts=pts, ch="~", tele="\u00b7"))
    return out


def burn(rng, hx, hy, power):
    out = []
    for i in range(3):
        x = int(min(W - 9, max(1, hx + rng.randint(-12, 12) - 2)))
        y = rng.randint(2, H - 3)
        out.append(Hazard("rect", 1.0 + 0.45 * i, 0.5, dmg=4, x=x, y=y - 1, w=4, h=3, ch="^", tele="B"))
    return out


def grasp(rng, hx, hy, power):
    out = []
    for i in range(3):
        x = int(min(W - 3, max(1, hx + rng.randint(-8, 8))))
        out.append(Hazard("rect", 1.0 + 0.5 * i, 0.6, dmg=4, x=x, y=H - 5, w=2, h=5, ch="\u2720", tele="\u2191", grow=0.25, up=True))
    return out


# ---- v2 patterns (green 4, yellow 4, red 5). Each one shows its warning first; none is faster than the old ones.
def _clampi(v, lo, hi):
    return int(max(lo, min(hi, round(v))))


def petal_rain(rng, hx, hy, power):
    """Green: three curtains of petals fall, each with a wide gap that drifts a little."""
    g, out = _clampi(hx + rng.randint(-6, 6), 5, W - 6), []
    for i in range(3):
        out.append(Hazard("curtain", 1.0 + 1.15 * i, 1.5, dmg=3, g0=g - _g(4), g1=g + _g(4), speed=8.5, ch="'", tele="!"))
        g = _clampi(g + rng.choice([-1, 1]) * int(rng.randint(3, 6) / tight), 5, W - 6)
    return out


def _far_corners(hx):
    """Where lights may come from: the top corners that are not right next to the heart (never a light out of nowhere on top of it)."""
    far = [x for x in (2, W - 3) if abs(x - hx) >= 12]
    return far or [2 if hx > W / 2 else W - 3]


def fireflies(rng, hx, hy, power):
    """Green: slow homing lights. They turn slowly, so a sharp change of direction shakes them off."""
    out = []
    for i, x in enumerate(_far_corners(hx)):
        a = math.atan2((hy - 0) * 2, hx - x)
        out.append(Hazard("orb", 1.0 + 0.5 * i, 3.4, dmg=3, px=float(x), py=0.0, a=a, sp=3.6 / tight, turn=70 / tight, snd0="warning"))
    return out


def cookie(rng, hx, hy, power):
    """Green: a big cookie falls, blinks, and bursts into crumbs that fly outwards."""
    out = []
    for i, off in enumerate((rng.randint(-12, -6), rng.randint(6, 12))):
        out.append(Hazard("split", 1.1 + 0.8 * i, 3.1, dmg=3, x=_clampi(hx + off, 4, W - 5), v=3.6, ts=1.5, n=6, sp=4.5, a0=rng.random() * 1.0))
    return out


def musicbox(rng, hx, hy, power):
    """Green: a music box winds up: two notes-arms spiral out of the middle (the eye stays safe)."""
    return [Hazard("spiral", 1.2, 4.4, dmg=2, repeat=True, cx=W // 2, cy=H // 2, arms=2, n=14, dt=0.17, rot=0.34, sp=5.0,
                   a0=rng.random() * 6, dir=rng.choice([-1, 1]), chs="♪♫")]


def mirror(rng, hx, hy, power):
    """Yellow: blocks sweep every row except two; the top half runs right, the bottom half runs left. Find a calm row."""
    s1 = _clampi(hy + rng.choice([-1, 0, 1] if tight >= 1 else [-3, -2, 2, 3]), 1, H - 2)
    far = [y for y in range(H) if abs(y - s1) >= 4]
    safe = {s1, rng.choice(far)}
    rows = [(y, 1 if y < 5 else (-1 if y > 5 else rng.choice([-1, 1]))) for y in range(H) if y not in safe]
    return [Hazard("comb", 1.2, 2.5, dmg=3, repeat=True, rows=rows, L=9, speed=20.0, ch="▓")]


def stare(rng, hx, hy, power):
    """Yellow: beams. A thin warning line, a flash of its full width, then it fires (one hit at most each)."""
    ry, cx = _clampi(hy, 1, H - 2), _clampi(hx, 2, W - 3)
    spec = [("h", ry, 1.3), ("v", cx, 1.9), ("h", _clampi(ry + rng.choice([-4, 4]), 1, H - 2), 2.5), ("v", _clampi(cx + rng.choice([-12, 12]), 2, W - 3), 2.9)]
    out = []
    for kind, pos, warn in spec:
        r = dict(x=0, y=pos, w=W, h=1) if kind == "h" else dict(x=pos - 1, y=0, w=3, h=H)
        out.append(Hazard("beam", warn, 0.4, dmg=4, ch="█", snd0="laser-charge", snd1="laser-fire", **r))
    return out


def squeeze(rng, hx, hy, power):
    """Yellow: the arena shrinks to a box, the box slides sideways, then it opens again. Stay inside it."""
    x0 = _clampi(hx - 13, 1, W - 28)
    x1 = _clampi(x0 + rng.choice([-6, 6]), 1, W - 28)
    wd = _g(26, 16)
    x0, x1 = min(x0, W - wd - 2), min(x1, W - wd - 2)
    box = lambda a: (a, a + wd, 1, H - 2)
    return [Hazard("box", 1.3, 4.2, dmg=3, repeat=True, ch="▒", tele="+", snd0="warning",
                   keys=[(0.0, (0, W - 1, 0, H - 1)), (0.2, box(x0)), (0.4, box(x0)), (0.7, box(x1)), (0.82, box(x1)), (1.0, (0, W - 1, 0, H - 1))])]


def weight(rng, hx, hy, power):
    """Yellow: gravity pulls the heart down while spikes rise from the floor, then it flips and pulls it up into spikes on the ceiling.
    Each spike band has a wide gap to stand in."""
    g1 = _clampi(hx + rng.randint(-5, 5), 6, W - 7)
    g2 = _clampi(g1 + rng.randint(-6, 6), 6, W - 7)
    out = [Hazard("gravity", 0.9, 2.0, dmg=0, dir=1), Hazard("gravity", 2.7, 2.4, dmg=0, dir=-1)]
    for y, h, warn, g, tele in ((H - 3, 3, 2.3, g1, "v"), (0, 3, 4.3, g2, "^")):
        for x, w in ((0, g - _g(5)), (g + _g(5) + 1, W - g - _g(5) - 1)):
            if w > 0:
                out.append(Hazard("rect", warn, 0.5, dmg=4, x=x, y=y, w=w, h=h, ch="▓", tele=tele))
    return out


def heartbeat(rng, hx, hy, power):
    """Red: a heart beats: pairs of rings leave the middle in rhythm (ba-dum ... ba-dum ... ba-dum). A beat shares one gap and the next
    gap is never far from the last one."""
    cx, cy = W // 2, H // 2
    gap = (math.degrees(math.atan2((hy - cy) * 2, hx - cx)) + rng.choice([-1, 1]) * rng.uniform(30, 55)) % 360
    out = []
    for warns in ((1.0, 1.3), (2.8, 3.1), (4.5, 4.8)):
        for wn in warns:
            out.append(Hazard("ring", wn, 1.5, dmg=4, cx=cx, cy=cy, a0=2, a1=22, gap=gap, gap_w=_g(150, 90), gr=17, thick=True, pulse=True, snd1="heartbeat"))
        gap = (gap + rng.choice([-1, 1]) * rng.uniform(25, 45)) % 360
    return out


def cage(rng, hx, hy, power):
    """Red: a cage closes round the arena while its one opening turns."""
    cx, cy = W // 2, H // 2
    toward = math.degrees(math.atan2((hy - cy) * 2, hx - cx)) % 360
    spin = rng.choice([-1, 1]) * 55
    return [Hazard("ring", 1.3, 3.6, dmg=4, cx=cx, cy=cy, a0=20, a1=4, gap=(toward + 25) % 360, gap_w=_g(120, 80), spin=spin, thick=True, snd0="warning")]


def blackout(rng, hx, hy, power):
    """Red: the lights go out: only a small circle round the heart is lit. Claws are still announced before they strike; two slow lights hunt."""
    out = [Hazard("dark", 0.8, 5.2, dmg=0, r=max(2.6, 3.6 * tight), snd0="warning")]
    for i in range(4):
        x = _clampi(hx + rng.randint(-9, 9) - 2, 1, W - 6)
        out.append(Hazard("rect", 1.8 + 0.8 * i, 0.5, dmg=4, x=x, y=_clampi(hy + rng.randint(-2, 2), 1, H - 2) - 1, w=5, h=3, ch="^", tele="B"))
    for i, x in enumerate(_far_corners(hx)):
        out.append(Hazard("orb", 2.0 + 0.6 * i, 3.0, dmg=3, px=float(x), py=0.0, a=math.atan2(hy * 2, hx - x), sp=3.2, turn=60))
    return out


def pillars(rng, hx, hy, power):
    """Red: columns rise from the floor in a wave, apart from two lanes. The wave runs one way so you can read it."""
    g1 = _clampi(hx + rng.choice([-1, 1]) * rng.randint(5, 9), 4, W - 5)
    g2 = _clampi(g1 + rng.choice([-1, 1]) * rng.randint(14, 18), 4, W - 5)
    if abs(g2 - g1) < 12:
        g2 = _clampi(g1 - 16, 4, W - 5) if g1 > 20 else _clampi(g1 + 16, 4, W - 5)
    xs = [x for x in range(0, W - 2, 3) if all(abs(x + 1 - g) > _g(4, 4) for g in (g1, g2))]
    if rng.random() < 0.5:
        xs.reverse()
    return [Hazard("pillar", 1.0 + 0.2 * k, 0.65, dmg=4, x=x, w=3, hgt=5 + (k * 7) % 5, grow=0.25, ch="▓") for k, x in enumerate(xs)]


def sigil(rng, hx, hy, power):
    """Red: a sigil turns out of the middle: three arms of crosses (a bit sparser than it looks)."""
    return [Hazard("spiral", 1.2, 4.0, dmg=3, repeat=True, cx=W // 2, cy=H // 2, arms=3, n=13, dt=0.17, rot=0.30, sp=5.2,
                   a0=rng.random() * 6, dir=rng.choice([-1, 1]), chs="✠+†")]


PATTERNS = {"teacups": teacups, "honey": honey, "fox": fox, "notes": notes, "bars": bars, "kneel": kneel, "cuts": cuts,
            "smiles": smiles, "ring": ring, "veins": veins, "burn": burn, "grasp": grasp,
            "petal_rain": petal_rain, "fireflies": fireflies, "cookie": cookie, "musicbox": musicbox,
            "mirror": mirror, "stare": stare, "squeeze": squeeze, "weight": weight,
            "heartbeat": heartbeat, "cage": cage, "blackout": blackout, "pillars": pillars, "sigil": sigil}
# ---- combos: two patterns layered with an offset (each part keeps its own warning and its own safe gaps)
COMBOS = {   # name: (first, second, seconds the second one starts later)
    "beamstorm": ("stare", "petal_rain", 2.6),     # beams across a falling curtain
    "pincer": ("squeeze", "fireflies", 1.8),       # the walls close while lights hunt inside the box
    "nightfall": ("blackout", "pillars", 1.6),     # the dark, then columns rise in it
    "thump": ("heartbeat", "grasp", 2.4),          # a beating heart, hands reaching up from the floor between the beats
}


def _combo(a, b, offset):
    def make(rng, hx, hy, power):
        first = PATTERNS[a](rng, hx, hy, power)
        second = PATTERNS[b](rng, hx, hy, power)
        for h in second:
            h.warn += offset
        return first + second
    make.__doc__ = "%s + %s (+%.1f s)" % (a, b, offset)
    return make


PATTERNS = {"teacups": teacups, "honey": honey, "fox": fox, "notes": notes, "bars": bars, "kneel": kneel, "cuts": cuts,
            "smiles": smiles, "ring": ring, "veins": veins, "burn": burn, "grasp": grasp,
            "petal_rain": petal_rain, "fireflies": fireflies, "cookie": cookie, "musicbox": musicbox,
            "mirror": mirror, "stare": stare, "squeeze": squeeze, "weight": weight,
            "heartbeat": heartbeat, "cage": cage, "blackout": blackout, "pillars": pillars, "sigil": sigil}
PATTERNS.update({name: _combo(*spec) for name, spec in COMBOS.items()})
BY_PHASE = {1: ["teacups", "honey", "fox", "notes", "petal_rain", "fireflies", "cookie", "musicbox"],
            2: ["bars", "kneel", "cuts", "smiles", "mirror", "stare", "squeeze", "weight", "beamstorm", "pincer"],
            3: ["ring", "veins", "burn", "grasp", "heartbeat", "cage", "blackout", "pillars", "sigil", "nightfall", "thump"],
            4: ["bars", "smiles", "veins", "grasp", "ring", "kneel", "stare", "pillars", "heartbeat", "mirror", "cage", "sigil",
                "nightfall", "thump"]}
# the gentler half of each personality: used for calm turns
CALM = {1: ["teacups", "honey", "fox"], 2: ["mirror", "bars", "kneel", "smiles"], 3: ["pillars", "veins", "burn", "grasp"],
        4: ["pillars", "mirror", "kneel", "veins"]}

# ================================================================ DIFFICULTY KNOBS (the rest of them are boss.DIFFICULTY)
# (first pattern at, base gap between pattern starts): the smaller the gap, the denser the turn
TEMPO = {1: (1.2, 3.1), 2: (0.8, 2.5), 3: (0.7, 2.0), 4: (0.6, 1.5)}
# a pattern may still be running this many seconds when the next one starts (bigger = more layering, less breathing room)
OVERLAP = {1: 1.0, 2: 1.4, 3: 2.0, 4: 2.4}
# seconds before the end of the turn in which no new pattern may still be running (the breather at the end of a turn)
END_MARGIN = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}
# which arc each enemy turn of a phase has: the first turns, then the tail repeats. Red and the fusion have no calm turn.
ARC_PLAN = {1: (("calm", "build", "climax"), ("build", "climax")),
            2: (("calm", "build", "climax"), ("build", "climax")),
            3: (("build", "build", "climax"), ("build", "climax")),
            4: (("build", "trinity", "climax"), ("build", "climax"))}
TRINITY = [(1.0, "veins"), (2.6, "ring"), (2.6, "burn"), (4.8, "cage"), (7.2, "kneel"), (7.6, "grasp")]    # the fusion's set-piece (layered)
# climax choreographies: a short silent beat, then the signature moves of the personality. Same time = layered.
SIGNATURES = {
    1: [[(1.2, "teacups"), (3.2, "cookie")], [(1.2, "cookie"), (3.6, "teacups")], [(1.4, "musicbox")]],
    2: [[(1.3, "stare"), (4.8, "mirror")], [(1.3, "squeeze"), (7.0, "cuts")], [(1.3, "weight"), (5.6, "stare")],
        [(1.3, "mirror"), (3.4, "stare"), (6.0, "kneel")]],
    3: [[(1.3, "nightfall"), (3.4, "ring"), (6.0, "burn"), (7.1, "veins")], [(1.3, "thump"), (6.5, "grasp")],
        [(1.3, "sigil"), (3.0, "pillars"), (6.8, "veins")], [(1.3, "heartbeat"), (3.0, "grasp"), (4.4, "ring"), (6.2, "burn")]],
    4: [[(1.2, "nightfall"), (5.2, "stare"), (6.4, "mirror")], [(1.2, "thump"), (5.3, "cage")],
        [(1.2, "pincer"), (7.0, "kneel")], [(1.2, "sigil"), (2.8, "stare"), (4.4, "pillars"), (6.6, "burn"), (7.4, "kneel")]],
}
# the turn right after a big hit (HP threshold): the arena itself changes, and it is more than a normal climax
RAGE = {2: [(1.2, "squeeze"), (7.0, "cuts")], 3: [(1.2, "cage"), (2.6, "pillars"), (4.6, "ring"), (6.2, "veins")],
        4: [(1.2, "squeeze"), (3.4, "fireflies"), (7.2, "cuts")]}


def arc_for(phase, turn):
    """The arc of an enemy turn (ARC_PLAN): calm, build, climax, trinity or (by Boss, after a big hit) rage."""
    plan, tail = ARC_PLAN[phase]
    return plan[turn] if turn < len(plan) else tail[(turn - len(plan)) % len(tail)]


_dur = {}


def duration(name):
    """How long a pattern lives (warning + effect), from a probe instance."""
    if name not in _dur:
        _dur[name] = max(h.warn + h.live for h in PATTERNS[name](random.Random(0), W // 2, H - 2, 0.0))
    return _dur[name]


def schedule(phase, turn, length, rng, arc=None):
    """[(time, pattern name)] for one enemy turn. calm = gentle patterns, wide gaps; build = the whole set, the gaps shrinking
    from 100% to 80%; climax = one of the choreographed signatures; trinity = the fusion's set-piece; rage = after a big hit."""
    arc = arc or arc_for(phase, turn)
    if arc == "trinity":
        return list(TRINITY)
    if arc == "rage":
        return list(RAGE[phase])
    if arc == "climax":
        return list(rng.choice(SIGNATURES[phase]))
    first, gap = TEMPO[phase]
    pool = CALM[phase] if arc == "calm" else BY_PHASE[phase]
    out, t, last = [], first, None
    while t < length - 1.5:
        ok = [n for n in pool if n != last and t + duration(n) <= length - END_MARGIN[phase]]
        if not ok:
            break
        name = rng.choice(ok)
        out.append((round(t, 2), name))
        shrink = 1.0 - 0.2 * min(1.0, t / length) if arc == "build" else 1.0
        last, t = name, t + max((gap + rng.random() * 0.6) * shrink, duration(name) - OVERLAP[phase])
    return out
