"""lettering.py - the heavy blood-red display lettering of the lyric scene (photo_fx font "font2", Noto Serif Display 900, baked by tools/photo_cells.py).

    Word(text, scale)     one word's bitmap, built ONCE (cached): ragged chipped edges, edge distance for the shading, cracks, drips, a burn order
    draw(cv, wd, x, y, wa, t, burn, alpha, power)   draw it (cell x, cell row y = top): slam from above with squash and stretch, white-hot at the hit and bright
                                                    edge, deep blood red inside with ember cracks, drips growing, a shake; burn > 0: it burns through and flakes off as ash
    measure(text, scale)  width in columns
Everything in half-block pixels (two per cell row); a word costs only its set pixels. No input, nothing printed.
"""
import math

import photo_fx

PAD = 5                                                                      # side padding inside the baked glyphs (not part of the advance)
GAP = 3                                                                      # extra blank columns after every letter: the heavy face needs air to be read
TOP, BOT = 5, 34                                                             # the used pixel rows of the baked glyphs
_words = {}


def _glyphs():
    return (photo_fx._load().get("font2") or {}).get("glyphs") or {}


def has():
    return bool(_glyphs())


def _h(a, b, c=0):
    return ((a * 73856093) ^ (b * 19349663) ^ (c * 83492791)) & 0xFFFF


def measure(text, scale=1.0):
    g = _glyphs()
    return int(sum(max(2, len((g.get(c) or g.get(" ") or ["......"])[0]) - PAD) + GAP for c in text) * scale)


class Word:
    def __init__(self, text, scale=1.0):
        g = _glyphs()
        s = max(0.2, min(1.4, scale))
        self.text, self.scale = text, s
        cols = []                                                            # compose the glyph columns at full size
        for ch in text:
            rows = g.get(ch) or g.get(" ")
            if rows is None:
                continue
            adv = max(2, len(rows[0]) - PAD)
            for c in range(adv):
                cols.append([rows[r][c + PAD // 2] == "#" for r in range(TOP, BOT)])
            for _ in range(GAP):
                cols.append([False] * (BOT - TOP))
            for k in range(1, min(3, PAD) + 1 if False else 1):
                pass
        W, H = len(cols), BOT - TOP
        w, h = max(1, int(W * s)), max(2, int(H * s))
        mask = [[False] * w for _ in range(h)]
        if W:
            for y in range(h):                                               # area sampling: thin stems survive the shrinking instead of aliasing away
                ya, yb = int(y / s), max(int(y / s) + 1, int((y + 1) / s))
                for x in range(w):
                    xa, xb = int(x / s), max(int(x / s) + 1, int((x + 1) / s))
                    tot = on = 0
                    for yy in range(ya, min(H, yb)):
                        for xx in range(xa, min(W, xb)):
                            tot += 1
                            on += cols[xx][yy]
                    mask[y][x] = tot > 0 and on * 100 >= tot * 42
        inside = lambda x, y: 0 <= x < w and 0 <= y < h and mask[y][x]
        for y in range(h):                                                   # ragged edges: chip some edge pixels away, add a few chips and spurs outside
            for x in range(w):
                if mask[y][x]:
                    if not (inside(x - 1, y) and inside(x + 1, y) and inside(x, y - 1) and inside(x, y + 1)) and _h(x, y, 3) % 100 < 0:
                        mask[y][x] = False
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if not mask[y][x] and (inside(x - 1, y) or inside(x, y + 1)) and _h(x, y, 4) % 100 < 0:
                    mask[y][x] = True
        dist = [[0] * w for _ in range(h)]                                   # distance from the edge (0 = edge pixel), a two-pass chamfer capped at 5
        for y in range(h):
            for x in range(w):
                if mask[y][x]:
                    d = 5
                    for dx, dy in ((-1, 0), (0, -1), (-1, -1), (1, -1)):
                        xx, yy = x + dx, y + dy
                        d = min(d, (dist[yy][xx] + 1) if inside(xx, yy) else 0)
                    if not (inside(x - 1, y) and inside(x + 1, y) and inside(x, y - 1) and inside(x, y + 1)):
                        d = 0
                    dist[y][x] = d
        for y in range(h - 1, -1, -1):
            for x in range(w - 1, -1, -1):
                if mask[y][x] and dist[y][x]:
                    d = dist[y][x]
                    for dx, dy in ((1, 0), (0, 1), (1, 1), (-1, 1)):
                        xx, yy = x + dx, y + dy
                        d = min(d, (dist[yy][xx] + 1) if inside(xx, yy) else 0)
                    dist[y][x] = d
        cracks = set()                                                       # a few jagged cracks running through the strokes
        inner = [(x, y) for y in range(h) for x in range(w) if mask[y][x] and dist[y][x] >= 2]
        for k in range(max(1, w // 90)):
            if not inner:
                break
            x, y = inner[_h(k, w, 5) % len(inner)]
            for step in range(6 + _h(k, 6) % 9):
                if inside(x, y):
                    cracks.add((x, y))
                x += (_h(k, step, 7) % 3) - 1
                y += 1 if _h(k, step, 8) % 3 else 0
        self.w, self.h = w, h
        self.pix = [(x, y, dist[y][x], (x, y) in cracks, (_h(x, y, 9) % 1000) / 1000.0, (_h(x, y, 10) % 1000) / 1000.0) for y in range(h) for x in range(w) if mask[y][x]]
        bottoms = [(x, max(yy for yy in range(h) if mask[yy][x])) for x in range(2, w - 2, 1) if any(mask[yy][x] for yy in range(h)) and _h(x, 11) % 100 < 9]
        self.drips = [(x, y, 3 + _h(x, 12) % int(max(3, 9 * s)), 3.0 + (_h(x, 13) % 40) / 10.0) for x, y in bottoms[:5]]    # x, y, length in px, seconds to grow


def get(text, scale):
    key = (text, round(scale, 2))
    if key not in _words:
        _words[key] = Word(text, scale)
    return _words[key]


def draw(cv, wd, x, y, wa, t, burn=0.0, alpha=1.0, power=1.0, sparks=None, hold=0.0, ghost=1.0, max_sx=1.38):
    """wa = seconds since this word hit (negative: not yet), burn 0..1 = it is burning away, power > 1 = a heavier hit (the climax), hold 0..1 = how far a held / screamed
    word has been sung (it stretches wide, a long 'I' also tall, trembles harder and glows), ghost < 1 = a quiet echo (dim, no slam). Every word has a dark outline
    and shadow first, so the red reads against fire and flesh alike."""
    if wa < 0 or alpha <= 0.02:
        return
    put = photo_fx.put_pixel
    if ghost < 1.0:
        power, wa = 0.4, max(wa, 0.5)
    if wa < 0.07:                                                            # the slam: squashed flat as it lands, then a stretch, then it settles
        sx, sy = 1.0 + 0.30 * power * (wa / 0.07), 1.0 - 0.32 * power * (wa / 0.07)
    elif wa < 0.22:
        k = (wa - 0.07) / 0.15
        sx, sy = 1.0 + 0.30 * power * (1 - k) - 0.06 * k * (1 - k) * 4, 1.0 - 0.32 * power * (1 - k) + 0.16 * power * k * (1 - k) * 4
    else:
        sx = sy = 1.0
    if hold > 0.0:
        sx *= min(max_sx, 1.0 + 0.38 * hold)
        if wd.text == "I":
            sy *= 1.0 + 0.32 * hold
    drop = -int(round((22.0 * wd.scale) * max(0.0, 1.0 - wa / 0.07))) if ghost >= 1.0 else 0
    hot = max(math.exp(-wa / (0.30 * power)) if ghost >= 1.0 else 0.0, 0.3 * hold)
    shake_amp = (2.4 * power * math.exp(-wa / (0.28 * power)) + 0.5) + 2.6 * hold * (0.6 + 0.4 * math.sin(t * 40))
    fr = int(t * 18)
    sh_x = int(round(((_h(fr, 1) % 100) / 50.0 - 1.0) * shake_amp * (1 if wa < 0.8 * power or hold > 0 else 0.4)))
    sh_y = int(round(((_h(fr, 2) % 100) / 50.0 - 1.0) * shake_amp * 0.5))
    base_y = 2 * y + wd.h                                                    # squash/stretch about the baseline, the middle of the word
    mid_x = x + wd.w // 2
    flick = 0.9 + 0.1 * math.sin(t * 15.0)
    ash = []
    cells = []
    for (px, py, d, crack, n, b) in wd.pix:
        if burn > 0.0 and b < burn:
            if b > burn - 0.10 and n > 0.55:                                  # the line is just burning through: an ember, and a flake of ash that falls off
                put(cv, x + px, 2 * y + py + sh_y, (255, 140 + int(80 * n), 40))
                ash.append((px, py, n, burn - b))
            continue
        c = _color(d, crack, n, hot, flick, t, burn, b, wd.scale >= 0.6)
        k = alpha * (ghost if ghost < 1.0 else 1.0)
        if k < 0.97:
            c = tuple(int(v * k) for v in c)
        X = mid_x + int(math.floor((px - wd.w // 2) * sx)) + sh_x
        Y = base_y + int(math.floor((py - wd.h) * sy)) + drop + sh_y
        cells.append((X, Y, c, d, ghost >= 1.0))
    ox = int(math.ceil(sx)) if sx > 1.02 else 1
    oy = int(math.ceil(sy)) if sy > 1.02 else 1
    dark = (6, 0, 2)
    for X, Y, c, d, solid in cells:                                          # the outline and the shadow, under the letters
        if d == 0 and solid:
            for dx, dy in ((-1, 0), (ox, 0), (0, -1), (0, oy), (ox, oy), (ox + 1, oy + 1)):
                put(cv, X + dx, Y + dy, dark)
    for X, Y, c, d, solid in cells:
        put(cv, X, Y, c)
        if ox > 1 or oy > 1:                                                  # stretched: fill the gaps so the letters do not tear
            for a_ in range(ox):
                for b_ in range(oy):
                    if a_ or b_:
                        put(cv, X + a_, Y + b_, c)
    if wa > 0.5 and ghost >= 1.0:                                             # blood drips from the lower edge, growing slowly, a bright bead at the end
        for (dx, dy, mx, secs) in wd.drips:
            ln = min(mx, int((wa - 0.5) / secs * mx))
            for q in range(ln):
                put(cv, x + dx, 2 * y + dy + 1 + q, (170 - q * 4, 10, 12))
            if ln:
                put(cv, x + dx, 2 * y + dy + 1 + ln, (255, 90, 80))
    for px, py, n, age in ash:                                               # ash flakes falling away, grey, drifting
        fy = 2 * y + py + int(age * 90 * (0.5 + n)) + 2
        fx = x + px + int(math.sin(age * 9 + n * 6) * 3)
        put(cv, fx, fy, (96, 90, 88) if n > 0.8 else (60, 56, 56))
    if sparks is not None and wa < 0.35 and wd.pix and ghost >= 1.0:           # a burst of sparks at the hit
        for _ in range(int(7 * power)):
            px, py = wd.pix[_h(int(t * 100), len(sparks), 3) % len(wd.pix)][:2]
            sparks.append([x + px, 2 * y + py, ((_h(px, py, int(t * 30)) % 100) - 50) / 8.0, -3.0 - (_h(py, px, 5) % 70) / 10.0, 0.0, 0.5 + (_h(px, 7) % 50) / 100.0])


def _color(d, crack, n, hot, flick, t, burn, b, sc_big=True):
    if crack:                                                                # a crack: dark, with an ember glowing in it that breathes
        glow = 0.5 + 0.5 * math.sin(t * 5.0 + n * 12.0)
        return (int(150 + 60 * glow), int(20 + 40 * glow), 10)
    if d == 0:                                                               # the bright core edge: hot orange-red
        c = (255, int(120 + 50 * n), 70)
    elif d == 1:
        c = (244, int(56 + 16 * n), 40)
    else:
        k = min(1.0, (d - 2) / 3.0)
        c = (int(214 - 50 * k + 14 * n), int(26 - 8 * k), int(24 - 6 * k))
    c = (int(c[0] * flick), int(c[1] * flick), int(c[2] * flick))
    if burn > 0.0 and b < burn + 0.16:                                       # about to burn: it glows orange
        c = (255, int(120 + 80 * n), 40)
    if hot > 0.02:                                                           # white-hot at the hit, strongest on the edges
        k = hot * (0.95 if d == 0 else 0.6 if d == 1 else 0.3)
        c = (int(c[0] + (255 - c[0]) * k), int(c[1] + (236 - c[1]) * k), int(c[2] + (214 - c[2]) * k))
    return c


def step_sparks(cv, sparks, dt):
    """Move and draw the spark/ember list (each [x, y_px, vx, vy_px/s, age, life])."""
    put = photo_fx.put_pixel
    keep = []
    for sp in sparks:
        sp[4] += dt
        if sp[4] >= sp[5]:
            continue
        sp[0] += sp[2] * dt
        sp[1] += sp[3] * dt
        sp[3] += 6.0 * dt
        k = 1.0 - sp[4] / sp[5]
        put(cv, sp[0], sp[1], (255, int(90 + 140 * k), int(30 + 40 * k)))
        keep.append(sp)
    sparks[:] = keep[-90:]
