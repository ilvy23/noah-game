"""proc_art.py - pictures drawn in code (no photo, no file): photo_fx.image() falls back to these when a name is not in art/photos.json.

    angel()   a cloaked, kneeling stone mourner (hood, forearm over the face, one folded wing, a hanging hand) on a low plinth, standing in fog; RGBA 160 x 180,
              grey marble light (photo_fx paints it through the scene's gold/dusk grade).
    aerial()  the valley from above, RGB 512 x 342, in the coordinates valley_fx expects (the 1024 x 683 plan halved): a dark blue lake in the middle, forest round it,
              fields and a village in the north-west, a track along the west shore, roofs where valley_fx puts its houses.
Pure python, deterministic, built once on first use (~0.3 s each).  Each returns (w, h, channels, bytes) like photo_fx.image().
"""
import math


def _hash(x, y, s=0):
    n = (x * 374761393 + y * 668265263 + s * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class _Noise:
    """Value noise: a coarse random grid, bilinear with smoothstep; sample(x, y) in pixels, cell = grid spacing in pixels."""

    def __init__(self, cell, seed):
        self.c, self.s = float(cell), seed

    def sample(self, x, y):
        fx, fy = x / self.c, y / self.c
        ix, iy = int(math.floor(fx)), int(math.floor(fy))
        u, v = _smooth(fx - ix), _smooth(fy - iy)
        a, b = _hash(ix, iy, self.s), _hash(ix + 1, iy, self.s)
        c, d = _hash(ix, iy + 1, self.s), _hash(ix + 1, iy + 1, self.s)
        return (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v


def _poly(pts):
    ys = [p[1] for p in pts]
    out = {}
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        for (xa, ya), (xb, yb) in zip(pts, pts[1:] + pts[:1]):
            if ya != yb and (ya <= y + 0.5 < yb or yb <= y + 0.5 < ya):
                xs.append(xa + (y + 0.5 - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        out[y] = list(zip(xs[0::2], xs[1::2]))
    return out


def _ellipse(cx, cy, rx, ry, n=28):
    return [(cx + rx * math.cos(6.2832 * i / n), cy + ry * math.sin(6.2832 * i / n)) for i in range(n)]


def _capsule(a, b, r0, r1=None):
    """A limb: a quad along a-b plus a round cap at each end (returned as polygons, all painted with one id)."""
    r1 = r0 if r1 is None else r1
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / L, dx / L
    return [[(a[0] + nx * r0, a[1] + ny * r0), (b[0] + nx * r1, b[1] + ny * r1), (b[0] - nx * r1, b[1] - ny * r1), (a[0] - nx * r0, a[1] - ny * r0)],
            _ellipse(a[0], a[1], r0, r0, 14), _ellipse(b[0], b[1], r1, r1, 14)]


# (id, base brightness, outlines) painted back to front: wing, cloak, plinth, hood, the shadow where the face hides, arms
_ANGEL = [
    ("W", 0.58, [[(76, 56), (98, 38), (122, 46), (142, 76), (151, 112), (147, 148), (133, 170), (122, 150), (116, 122), (104, 98), (88, 84)]]),
    ("C", 0.50, [[(38, 62), (58, 52), (82, 56), (98, 72), (112, 102), (126, 134), (136, 160), (128, 168), (60, 168), (30, 166), (26, 148), (32, 118), (34, 90)]]),
    ("P", 0.38, [[(12, 166), (152, 166), (152, 180), (12, 180)]]),
    ("H", 0.66, [[(40, 44), (52, 22), (74, 28), (86, 58), (46, 64)], _ellipse(56, 43, 18, 20)]),
    ("S", 0.14, [_ellipse(48, 52, 12, 11)]),
    ("B", 0.70, _capsule((94, 80), (100, 124), 5.5, 4.0) + [_ellipse(100, 131, 5.5, 8)]),
    ("A", 0.76, _capsule((84, 76), (34, 80), 6.5, 6.0)),
    ("A", 0.80, _capsule((34, 80), (62, 52), 6.0, 5.0)),
]


def angel():
    """The statue as RGBA bytes (alpha = coverage, faded into fog towards the feet)."""
    W, H, S = 160, 180, 2
    ids = [[None] * (W * S) for _ in range(H * S)]
    base = {}
    for sid, lum, polys in _ANGEL:
        base[sid] = lum
        for pts in polys:
            for y, spans in _poly([(x * S, y * S) for x, y in pts]).items():
                if 0 <= y < H * S:
                    row = ids[y]
                    for xa, xb in spans:
                        for x in range(max(0, int(round(xa))), min(W * S, int(round(xb)))):
                            row[x] = sid
    warp, fog = _Noise(11, 5), _Noise(9, 7)
    out = bytearray()
    for y in range(H):
        for x in range(W):
            cov = sum(1 for sy in range(S) for sx in range(S) if ids[y * S + sy][x * S + sx])
            sid = ids[y * S + 1][x * S + 1] or next((ids[y * S + sy][x * S + sx] for sy in range(S) for sx in range(S) if ids[y * S + sy][x * S + sx]), None)
            if not sid:
                out += b"\x00\x00\x00\x00"
                continue
            d = 6                                                                      # distance to the nearest other part (<= 6 px): rounds every part into a volume
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                for k in range(1, 6):
                    X, Y = (x + dx * k) * S, (y + dy * k) * S
                    if not (0 <= X < W * S and 0 <= Y < H * S) or ids[Y][X] != sid:
                        d = min(d, k)
                        break
            lum = base[sid] + 0.24 * (1 - x / float(W)) + 0.08 * (1 - y / float(H)) - 0.10
            lum *= 0.62 + 0.38 * min(1.0, d / 5.0)
            wv = warp.sample(x, y)
            if sid == "C":
                lum += 0.12 * math.sin((x - 0.16 * y) * 0.42 + 4.0 * wv) + 0.05 * math.sin(y * 0.21 + x * 0.05)                 # drapery folds
            elif sid == "W":
                along, across = (x - 80) * 0.5 + (y - 60) * 0.86, (x - 80) * 0.86 - (y - 60) * 0.5
                lum += 0.12 * math.sin((along + 1.1 * math.sin(across * 0.45)) * 0.75)                                         # scalloped feather rows
            lum += 0.09 * (_hash(x, y, 3) - 0.5)                                                                               # stone grain
            L = max(0.0, min(1.0, lum))
            mist = _smooth((y - 105) / 70.0) * (0.45 + 0.4 * fog.sample(x, y * 1.6))                                          # fog gathers round the feet and plinth
            a = cov / float(S * S) * (1.0 - min(0.85, mist))
            g = int(255 * L)
            out += bytes((g, g, min(255, int(g * 1.03)), int(255 * a)))
    return W, H, 4, bytes(out)


def aerial():
    """The valley from above as RGB bytes (coordinates of valley_fx's plan halved)."""
    W, H = 512, 342
    w2, h2 = W // 2, H // 2                                                             # computed at half size, every pixel doubled
    big, mid, fine, shore = _Noise(40, 1), _Noise(14, 2), _Noise(4, 3), _Noise(11, 4)
    houses = [(68, 100), (40, 165), (52, 188), (125, 160), (78, 140), (60, 125), (150, 72), (232, 35), (282, 38), (345, 33), (615, 82), (128, 25), (30, 215), (160, 215), (100, 195)]
    track = [(70, 232), (82, 300), (118, 352), (170, 405), (222, 448), (275, 470)]
    px = [[None] * w2 for _ in range(h2)]
    for y in range(h2):
        for x in range(w2):
            X, Y = x * 2, y * 2
            lake = math.hypot((X - 180) / 95.0, (Y - 150) / 88.0) + 0.16 * (shore.sample(X, Y) - 0.5) * 2 + 0.05 * (fine.sample(X, Y) - 0.5)
            f = fine.sample(X, Y)
            if lake < 1.0:
                depth = 1.0 - lake
                px[y][x] = (int(24 + 10 * f + 8 * (1 - depth)), int(44 + 12 * f + 14 * (1 - depth)), int(74 + 14 * f + 10 * (1 - depth)))
                continue
            wood = big.sample(X, Y) * 0.7 + mid.sample(X, Y) * 0.3 + (0.35 if lake < 1.35 else 0.0) + (0.15 if X > 230 or Y > 300 else 0.0) - (0.30 if X < 150 and Y < 140 else 0.0)
            if wood > 0.55:                                                             # forest: dark crowns, lighter speckle
                k = 0.6 + 0.8 * f
                px[y][x] = (int(26 + 16 * k), int(54 + 26 * k), int(28 + 12 * k))
            else:                                                                       # fields: ochre and straw, stripes
                k = 0.7 + 0.5 * f + 0.15 * math.sin(X * 0.5 + Y * 0.12 + big.sample(X, Y) * 6)
                px[y][x] = (int(98 + 34 * k), int(88 + 30 * k), int(54 + 16 * k))
    def dot(x, y, col):
        if 0 <= x < w2 and 0 <= y < h2:
            px[y][x] = col
    for (ax, ay), (bx, by) in zip(track, track[1:]):                                   # the track along the west shore: pale dirt
        for i in range(int(max(abs(bx - ax), abs(by - ay)) / 2) + 1):
            t = i / float(max(1, int(max(abs(bx - ax), abs(by - ay)) / 2)))
            cx, cy = (ax + (bx - ax) * t) / 4.0, (ay + (by - ay) * t) / 4.0
            for dx in (0, 1):
                dot(int(cx) + dx, int(cy), (176, 160, 118))
    for hx, hy in houses:                                                               # roofs (valley_fx draws the lit windows): terracotta and slate
        for dy in range(2):
            for dx in range(4):
                tone = _hash(hx, hy, 9)
                dot(hx // 4 + dx, hy // 4 + dy, (150, 66, 52) if tone < 0.6 else (96, 92, 100))
    rows = bytearray()
    for y in range(H):
        row = px[y // 2]
        for x in range(W):
            rows += bytes(row[x // 2])
    return W, H, 3, bytes(rows)
