"""mika_fx.py - Mika (male, slow, stoned, hooded, long coat) as an animated figure drawn like the Noah figure, and the bench scene.

    MikaFigure(hf, sit).cells(t, ...)   rows of None | (glyph, fg, bg): standing (awakening, shore) or sitting on the bench with a joint.
        the coat, the hair and the hood move as if under water (every row is displaced by a slow wave, more towards the hem and the hair);
        the eyes can glow; `inhale` (0..1) brightens the joint's ember and lights the face.
    BenchScene(w, h, rng, mode)         mode "intro" (9 s: dusk, the lake, the lighter) or "end" (16 s: the joint, the inhale, the smoke over the lake).
Pure frame functions on noah_gore_fx.Canvas: deterministic, headless-testable, no input, nothing outside the screen.
"""
import math

from noah_gore_fx import (BLACK, Canvas, Particles, add, blit_grid, clamp, darken, draw_cube, fire_rgb, flash, glow, mix, mul, push_in, ramp, smooth, _hash)

COAT, COAT_HI, HOOD, SKIN_M, HAIR_M, SHIRT = (44, 60, 64), (70, 96, 98), (36, 50, 56), (206, 168, 146), (122, 98, 68), (176, 170, 150)
WOOD = (92, 64, 44)
TEAL = (140, 255, 230)


def region_stand(tx, ty):
    ax = abs(tx)
    if ty < 11.5:
        o = (tx / 4.9) ** 2 + ((ty - 5.2) / 5.6) ** 2
        if o < 1:
            if (tx / 2.8) ** 2 + ((ty - 6.5) / 3.6) ** 2 < 1:
                if 0.8 < ax < 1.8 and 6.1 < ty < 7.0:
                    return "e"
                if ax < 1.0 and 9.0 < ty < 9.6:
                    return "m"
                return "h" if ty < 4.2 else "f"
            return "H"
    if 7.5 < ty < 17 and 3.9 < ax < 5.6 and ((ax - 3.9) < (ty - 7.0) * 0.4):
        return "h"                                             # long hair over the shoulders
    if 10.5 <= ty < 12.3 and ax < 2.3:
        return "s"
    if 11.5 <= ty < 33:
        hw = 4.9 + (ty - 12) * 0.085 if ty > 14 else 4.9 - max(0.0, 13.2 - ty) * 0.8
        if ax < hw:
            return "r" if (ax < 0.7 and 12.5 < ty < 28) else "c"
        xc = hw + 1.3
        if abs(ax - xc) < 1.25 and 13.0 <= ty < 25.5:
            return "a"
        if abs(ax - xc) < 1.1 and 25.5 <= ty < 28.5:
            return "p"
    if 33.0 <= ty < 36 and abs(ax - 2.1) < 2.3 and ax > 0.2:
        return "b" if ty > 34.4 else "t"
    return None


def region_sit(tx, ty):
    """Sitting on a bench, seen from the front: knees forward (the lower rows), the right hand with the joint at his mouth."""
    ax = abs(tx)
    c = region_stand(tx, ty)
    if ty < 11.5 or c in ("p", "a"):
        if c == "a" and tx > 0:
            return None
        if tx > 0 and 9.5 <= ty < 12.0 and 2.9 < tx < 4.4:
            return "p"                                         # the hand at the mouth
        return c if c not in ("a", "p") else (c if tx < 0 and ty < 24.0 else None)
    if 11.5 <= ty < 24:
        hw = 4.9 + (ty - 12) * 0.12
        if ax < hw:
            return "r" if (ax < 0.7 and ty < 20) else "c"
        if tx > 0 and 3.8 < tx < 6.0 and 11.5 <= ty < 20:
            return "a"                                         # upper arm; the forearm goes up to the face
        if tx < 0 and abs(ax - (hw + 1.2)) < 1.2:
            return "a"
    if 24 <= ty < 30:
        if abs(ax - 2.6) < 2.6 and ty < 29:
            return "t"                                         # the thighs/knees
        if ax < 6.6:
            return "c"                                         # coat over the lap
    if 30 <= ty < 33.5 and abs(ax - 2.7) < 2.0:
        return "b" if ty > 31.5 else "t"
    return None


class MikaFigure:
    def __init__(self, hf, sit=False, width_units=8.0):
        self.hf, self.sit = max(8, hf), sit
        self.s = self.hf / 36.0
        self.wf = int(2 * 2 * width_units * self.s) + 2

    def sway(self, ty, t):
        return math.sin(ty * 0.33 - t * 1.5) * 0.9 * (ty / 36.0) ** 1.4 * (1.0 if not self.sit else 0.3)

    def cells(self, t, eyes=0.0, inhale=0.0, aura=0.0, reveal=1.0, tint=None, ember_at=None):
        """reveal 0..1 dissolves him in (noise); eyes 0..1 glow; inhale 0..1 ember; aura 0..1 teal light on the cloth; tint = (rgb, amount)."""
        fn = region_sit if self.sit else region_stand
        grid = [[None] * self.wf for _ in range(self.hf)]
        fn_s = self.s
        joint = None
        for yy in range(self.hf):
            ty = (yy + 0.5) / fn_s
            dx = self.sway(ty, t)
            for xx in range(self.wf):
                tx = (xx - self.wf / 2.0 + 0.5) * 0.5 / fn_s
                code = fn(tx + dx + (math.sin(ty * 0.9 - t * 2.1) * 0.35 if code_hair(tx, ty) else 0), ty)
                if code is None or _hash(xx, yy, 5) > reveal:
                    continue
                n1, n2 = _hash(xx, yy, 1), _hash(xx, yy, 2)
                base = {"c": COAT, "a": COAT, "H": HOOD, "r": SHIRT, "s": (150, 70, 70), "f": SKIN_M, "p": SKIN_M, "h": HAIR_M,
                        "t": (52, 56, 70), "b": (24, 20, 22), "e": SKIN_M, "m": (120, 70, 70)}[code]
                chs = {"c": "▒▓#%", "a": "▒#%&", "H": "▓%#&", "r": ":;':", "s": "~%~%", "f": ".,:'", "p": ".:,.", "h": "|/\\)(", "t": "#%#%", "b": "▓▓▓▓", "e": "oooo", "m": "----"}[code]
                ch = chs[int(n1 * len(chs)) % len(chs)]
                fg, bg = mul(base, 0.75 + 0.35 * n2), mul(base, 0.42 if code not in "fp" else 0.7)
                if code in "caH" and aura:
                    fg = mix(fg, COAT_HI, aura * (0.4 + 0.6 * n1))
                    fg = add(fg, (30, 90, 80), aura * 0.6)
                if code == "e":
                    if eyes > 0:
                        ch, fg, bg = "@", mix(fg, TEAL, eyes), mix((20, 20, 20), (40, 170, 150), eyes)
                    else:
                        ch, fg, bg = "-", (60, 40, 40), mul(SKIN_M, 0.7)             # half-closed, slow
                if inhale and code in "fpH" and tx > -1:
                    fg, bg = add(fg, (110, 40, 6), inhale * 0.6), add(bg, (70, 22, 2), inhale * 0.6)
                if tint:
                    fg, bg = mix(fg, tint[0], tint[1]), mix(bg, tint[0], tint[1])
                grid[yy][xx] = (ch, fg, bg)
        if self.sit:                                                                  # the joint: held by the hand at the mouth
            jx, jy = int(self.wf / 2 + 2.4 * 2 * fn_s), int(9.9 * fn_s)
            for k in range(4):
                if 0 <= jy < self.hf and 0 <= jx + k < self.wf:
                    grid[jy][jx + k] = ("-=~"[min(2, k // 2 + (1 if k == 3 else 0))] if k < 3 else "*", (235, 230, 215) if k < 3 else mix((200, 70, 10), (255, 235, 130), inhale), (60, 50, 40))
            joint = (jx + 3, jy)
        return grid, joint


def code_hair(tx, ty):
    return 7.5 < ty < 17 and 3.9 < abs(tx) < 5.6


# ------------------------------------------------------------------ the bench scene
AUTUMN = [(176, 36, 28), (214, 92, 28), (236, 164, 44), (198, 60, 30), (112, 128, 40), (150, 140, 40), (232, 130, 36), (96, 52, 28)]    # red, orange, yellow, green, brown crowns


def blend_px(cv, x, ypx, col, a):
    """Mix one half-block pixel towards col by a (0..1)."""
    y = ypx // 2
    if a <= 0.01 or not (0 <= x < cv.w and 0 <= y < cv.h):
        return
    i = y * cv.w + x
    if cv.ch[i] == "▀":
        cur = cv.fg[i] if ypx % 2 == 0 else cv.bg[i]
    else:
        cur = cv.bg[i]
    import photo_fx
    photo_fx.put_pixel(cv, x, ypx, mix(cur, col, a))


def fill_poly(pts, colour_at, put):
    """Fill the polygon pts (pixel coordinates) scanline by scanline; colour_at(x, y) -> colour."""
    ys = [p[1] for p in pts]
    for y in range(int(min(ys)), int(max(ys)) + 1):
        xs = []
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / float(y1 - y0))
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            for x in range(int(round(a)), int(round(b)) + 1):
                put(x, y, colour_at(x, y))


class _BenchBase:
    """What the bench scene needs besides the picture: Mika's right-arm poses over time and the smoke puffs (the scene itself is BenchScene)."""

    POSES = {"rest": (12, -4, 9, 0, 0, 0), "pocket": (15, -1, 14, 3, 0, 0), "mouth": (13, -14, 8, -24, 6, -1), "toast": (19, -24, 23, -37, 4, -5), "open": (19, -13, 27, -19, 0, 0)}

    def pose(self, t, end):
        """Mika's right arm in the story's order. intro: hand to the other pocket (2-3.2), out with the joint to the mouth (3.2-4.4), the lighter (4.8-6.2).
        end: he holds the joint up to the sunset like a toast (0.4-2.4, held to 4.0), brings it to his mouth (4.0-5.0), inhales, exhales; from 12 s he opens his hand."""
        P = self.POSES
        if not end:
            keys = [(0.0, "rest"), (2.0, "rest"), (3.2, "pocket"), (3.6, "pocket"), (4.6, "mouth"), (99.0, "mouth")]
        else:
            keys = [(0.0, "mouth"), (0.4, "mouth"), (2.4, "toast"), (4.0, "toast"), (5.0, "mouth"), (11.8, "mouth"), (13.2, "open"), (99.0, "open")]
        for (t0, a), (t1, b) in zip(keys, keys[1:]):
            if t0 <= t < t1:
                k = smooth((t - t0) / float(t1 - t0)) if a != b else 0.0
                return tuple(P[a][i] + (P[b][i] - P[a][i]) * k for i in range(6))
        return P[keys[-1][1]]

    def puff(self, x, ypx, vx, vy, life, r0, r1, a=1.0):
        self.puffs.append([x, ypx, vx, vy, 0.0, life, r0, r1, self.rng.uniform(0, 6.28), a])


class BenchScene(_BenchBase):
    """The bench scene rebuilt on the user's own photos of the Cappenberger See (docs/ref/lake/, composited and graded to an autumn dusk by tools/photo_cells.py into
    art/photos.json "lake"): the wide lake and autumn forest of lake-06 as the view, the golden reeds, the path and the white benches of lake-02 in front, branches
    overhead. Mika and the player sit on the right white bench (seen from behind at eye height), the camera pulls out slowly from them to the whole shore; the sun
    sets over the forest with its path of glints on the mirror water, mist, rings where something breaks the surface, reeds that sway, drifting leaves, the smoke
    and the ember. The photo layer is graded once; every frame only samples a window of it and draws the moving layers on top."""
    SQ = 0.85                                                                  # the panorama is squeezed a little vertically so that sky, lake and bench fit the wide screen
    BENCH = (380, 436, 284)                                                    # (Mika's x, the player's x, the backrest's top row) in the composite, of the right bench

    def __init__(self, w, h, rng, mode="end"):
        import photo_fx
        self.w, self.h, self.rng, self.mode = w, h, rng, mode
        W, H, ch, raw = photo_fx.image("lake")
        self.GW, self.GH = W, H
        self.hz = int(photo_fx._load()["lake"]["horizon"])
        self.G = [[(raw[(y * W + x) * 4], raw[(y * W + x) * 4 + 1], raw[(y * W + x) * 4 + 2]) for x in range(W)] for y in range(H)]
        self.A = [[raw[(y * W + x) * 4 + 3] for x in range(W)] for y in range(H)]          # 255 water, 140 reeds, 60 sky, else 0
        self.puffs, self.ripples, self.last_exh, self.next_ring, self.fig = [], [], -1.0, 1.0, None
        self.glints = [(rng.random(), rng.random(), rng.uniform(1.5, 5.0), rng.uniform(0, 6.28)) for _ in range(int(150 * w / 245.0) + 40)]
        self.leaves = [(rng.uniform(0, w), rng.uniform(0, h * 2), rng.uniform(2.0, 5.0), rng.uniform(0, 6.28)) for _ in range(16)]

    def figures_at(self, mx, px_, yb, k):
        """The two seated figures (same shapes as before) at screen position: mx / px_ = their centres (columns), yb = the backrest's top row (pixel rows), k = size."""
        K = lambda v: int(round(v * k))
        m, p = [], []
        def ell(x0, y0, rx, ry, tag, out):
            for y in range(int(y0 - ry), int(y0 + ry) + 1):
                for x in range(int(x0 - rx), int(x0 + rx) + 1):
                    if ((x - x0) / float(max(1, rx))) ** 2 + ((y - y0) / float(max(1, ry))) ** 2 <= 1:
                        out.append((x, y, tag))
        def trap(x0, ya, yb_, hwa, hwb, tag, out):
            for y in range(int(ya), int(yb_)):
                hw = hwa + (hwb - hwa) * (y - ya) / float(max(1, yb_ - ya))
                for x in range(int(x0 - hw), int(x0 + hw) + 1):
                    out.append((x, y, tag))
        trap(mx, yb - K(14), yb + 1, K(10), K(15), "coat", m)
        ell(mx + 1, yb - K(23), K(8), K(10), "hood", m)
        trap(mx + 1, yb - K(35), yb - K(27), 1, K(5), "hood", m)
        trap(mx, yb - K(16), yb - K(13), K(8), K(9), "collar", m)
        ell(mx + K(7), yb - K(21), K(2), K(4), "face", m)
        trap(px_, yb - K(11), yb + 1, K(8), K(12), "jacket", p)
        ell(px_ + 1, yb - K(20), K(6), K(7), "hair", p)
        ell(px_ + 2, yb - K(14), K(3), K(2), "neck", p)
        ell(px_ + K(6), yb - K(18), K(1) + 1, K(3), "cheek", p)
        trap(px_ + 1, yb - K(14), yb - K(10), K(6), K(7), "hoodfold", p)
        return m, p

    def draw(self, cv, t, dt):
        import photo_fx
        w, h, rng = self.w, self.h, self.rng
        end = self.mode == "end"
        T = 16.0 if end else 9.0
        # --- the window into the composite: starts close on the two on the bench, pulls out to the whole shore
        e = smooth(t / T)
        z = 1.0 + 1.15 * (1 - e)
        ww = 0.92 * self.GW / z
        sx_ = ww / w
        sy_ = sx_ / self.SQ
        wh = sy_ * 2 * h
        cx_c, cy_c = 409 - 52 * e, 262 - 74 * e
        x0 = max(0.0, min(self.GW - ww, cx_c - ww / 2))
        y0 = max(0.0, min(self.GH - wh, cy_c - wh / 2))
        G, A = self.G, self.A
        rows = []
        for j in range(2 * h):
            sy = min(self.GH - 1, max(0, int(y0 + (j + 0.5) * sy_)))
            Gr, Ar = G[sy], A[sy]
            wob = (math.sin(sy * 0.55 - t * 1.3) * 1.3 + math.sin(sy * 0.17 + t * 0.6)) if sy > self.hz else 0.0
            sway = math.sin(t * 1.6 + sy * 0.12) * 1.1
            row = []
            for i in range(w):
                sx = int(x0 + (i + 0.5) * sx_)
                a_ = Ar[min(self.GW - 1, sx)]
                if a_ == 255:
                    sx += int(wob)
                elif a_ == 140:
                    sx += int(sway)
                row.append(Gr[min(self.GW - 1, max(0, sx))])
            rows.append(row)
        cv.clear()
        photo_fx.paint(cv, rows, 0, 0)
        inv_x = lambda gx: (gx - x0) / sx_
        inv_y = lambda gy: (gy - y0) / sy_
        wet = lambda gx, gy: 0 <= gy < 2 * h and 0 <= gx < w and A[min(self.GH - 1, max(0, int(y0 + gy * sy_)))][min(self.GW - 1, max(0, int(x0 + gx * sx_)))] == 255
        sky = lambda gx, gy: 0 <= gy < 2 * h and 0 <= gx < w and A[min(self.GH - 1, max(0, int(y0 + gy * sy_)))][min(self.GW - 1, max(0, int(x0 + gx * sx_)))] == 60
        hzs = int(inv_y(self.hz))
        sun_sx = int(inv_x(0.62 * self.GW))
        # --- the sun disc low over the forest (only in the sky gaps) and its glow
        R = max(4, int(11 / sx_ * 1.0 + 3))
        for yy in range(hzs - 2 * R, hzs + R):
            for xx in range(sun_sx - 2 * R, sun_sx + 2 * R + 1):
                d = math.hypot((xx - sun_sx) / 2.0, yy - (hzs - R // 2))
                if d < R + 2 and sky(xx, yy):
                    blend_px(cv, xx, yy, (255, 244, 205) if d < R * 0.7 else (255, 200, 120), 0.9 if d < R else 0.4)
        # --- mist on the water, glints on the sun path, rings and jumping fish
        for yy in range(hzs + 3, hzs + 3 + max(6, int(30 / sy_))):
            for xx in range(0, w, 2):
                if wet(xx, yy):
                    n = 0.5 + 0.5 * math.sin(xx * 0.045 + t * 0.25 + yy * 0.3) * math.sin(xx * 0.017 - t * 0.12)
                    a_ = 0.16 * n
                    blend_px(cv, xx, yy, (255, 214, 184), a_)
                    blend_px(cv, xx + 1, yy, (255, 214, 184), a_)
        lo = hzs + 6
        hi = int(inv_y(self.GH * 0.58))
        for fx, fy, rate, ph in self.glints:
            gy = lo + int(fy * max(1, hi - lo))
            gx = int(sun_sx + (fx - 0.5) * (22 + 1.2 * (gy - lo)))
            tw = max(0.0, math.sin(t * rate + ph)) ** 6
            if tw > 0.25 and wet(gx, gy):
                blend_px(cv, gx, gy, (255, 238, 190), min(1.0, tw * 1.1))
                if tw > 0.7:
                    for ox, oy in ((1, 0), (-1, 0), (0, -1)):
                        blend_px(cv, gx + ox, gy + oy, (255, 226, 160), 0.6)
        if t >= self.next_ring:
            self.next_ring = t + rng.uniform(0.9, 2.2)
            gy = rng.randrange(lo + 2, max(lo + 4, hi))
            self.ripples.append([rng.uniform(0.15, 0.85) * w, gy, 0.0, rng.random() < 0.5])
        for rp in self.ripples:
            rp[2] += dt * 6.0
            for a in range(0, 360, 5):
                px_, py_ = rp[0] + math.cos(math.radians(a)) * rp[2] * 2.4, rp[1] + math.sin(math.radians(a)) * rp[2] * 0.55
                if wet(int(px_), int(py_)):
                    blend_px(cv, int(px_), int(py_), (255, 214, 160), 0.7 * max(0.0, 1 - rp[2] / 10.0))
            if rp[3] and rp[2] < 1.6:
                for q in range(5):
                    blend_px(cv, int(rp[0] + (q - 2) * 1.5), int(rp[1] - 6 * math.sin(rp[2] / 1.6 * 3.1) * (1 - abs(q - 2) * 0.25)), (255, 240, 210), 0.9)
        self.ripples = [r for r in self.ripples if r[2] < 10.0]
        # --- Mika and the player on the right white bench (their size follows the zoom), the backrest hides their lower bodies
        mxs, pxs, ybs = int(inv_x(self.BENCH[0])), int(inv_x(self.BENCH[1])), int(inv_y(self.BENCH[2]))
        k = 1.19 / sx_ * 0.95
        mpts, ppts = self.figures_at(mxs, pxs, ybs, k)
        K = lambda v: int(round(v * k))
        inh = smooth((t - 4.6) / 0.8) * (1 - smooth((t - 6.8) / 0.8)) if end else 0.0
        mx, yb = mxs, ybs
        def put_c(x, y, c):
            if y <= yb:
                photo_fx.put_pixel(cv, x, y, c)
        def shade(pts, base_of):
            occ = {(x, y) for x, y, _ in pts}
            ys = [y for _, y, _ in pts]
            ymin, ymax = min(ys), max(ys)
            for x, y, tag in pts:
                e_ = 2 if (x + 1, y) not in occ else (1 if ((x + 2, y) not in occ or (x, y - 1) not in occ) else (-1 if (x - 1, y) not in occ else 0))
                c = base_of(tag, x, y, (y - ymin) / float(max(1, ymax - ymin)))
                if e_ > 0:
                    c = add(c, (222, 126, 58), 0.30 * e_ + 0.12)
                    if inh and x >= mx:
                        c = add(c, (255, 130, 40), 0.35 * inh)
                elif e_ < 0:
                    c = mul(c, 0.7)
                put_c(x, y, c)
        def clothes(tag, x, y, vg):
            n = _hash(x, y, 12)
            if tag == "coat":
                c = mul((44, 44, 60), 0.62 + 0.55 * (1 - vg))
                if (x - mx) % max(3, K(6)) in (0, 1) and vg > 0.3: c = mul(c, 0.72)
                if x == mx: c = mul(c, 0.55)
                return mul(c, 0.94 + 0.12 * n)
            if tag == "hood":
                c = mul((52, 50, 70), 0.7 + 0.5 * (1 - vg))
                if (x + y // 3) % 7 == 0: c = mul(c, 0.7)
                return mul(c, 0.94 + 0.12 * n)
            if tag == "collar": return mul((60, 58, 80), 0.9 + 0.2 * n)
            if tag == "face": return mix((70, 46, 40), (150, 96, 70), 0.3 + 0.5 * n)
            if tag == "jacket":
                c = mul((70, 64, 84), 0.65 + 0.5 * (1 - vg))
                if (x - pxs) % max(3, K(8)) == 0: c = mul(c, 0.75)
                return mul(c, 0.94 + 0.12 * n)
            if tag == "hoodfold": return mul((60, 54, 74), 0.85 + 0.25 * n)
            if tag == "hair":
                c = mix((70, 46, 30), (30, 20, 16), vg)
                if _hash(x, y // 2, 4) > 0.8: c = mul(c, 0.6)
                if _hash(x, y, 5) > 0.93: c = add(c, (150, 90, 40), 0.5)
                return c
            if tag == "neck": return mul((138, 96, 78), 0.8 + 0.3 * n)
            if tag == "cheek": return mix((176, 118, 90), (236, 170, 120), n)
            return (40, 40, 50)
        shade(mpts, clothes)
        shade(ppts, clothes)
        ex, ey, hx, hy_, jdx, jdy = self.pose(t, end)
        S = (mx + K(9), yb - K(12))
        E = (mx + K(ex), yb + K(ey))
        H = (mx + K(hx), yb + K(hy_))
        for A_, B_, rad in ((S, E, 2.3), (E, H, 1.9)):
            nstep = int(max(abs(B_[0] - A_[0]), abs(B_[1] - A_[1])) * 1.5) + 1
            for q in range(nstep + 1):
                px_, py_ = A_[0] + (B_[0] - A_[0]) * q / nstep, A_[1] + (B_[1] - A_[1]) * q / nstep
                r_ = max(1, K(rad))
                for dy in range(-r_, r_ + 1):
                    for dx in range(-r_, r_ + 1):
                        if dx * dx + dy * dy <= r_ * r_:
                            c = mul((44, 44, 60), 0.75 + 0.4 * (1 - (dy + r_) / float(2 * r_ + 1)))
                            if dx > r_ * 0.4: c = add(c, (222, 126, 58), 0.35)
                            put_c(int(px_) + dx, int(py_) + dy, c)
        hr = max(1, K(2))
        if end or t > 3.0:
            for dy in range(-hr, hr + 1):
                for dx in range(-hr, hr + 1):
                    if dx * dx + dy * dy <= hr * hr + 1:
                        put_c(H[0] + dx, H[1] + dy, mix((96, 66, 54), (222, 150, 104), 0.5 + 0.5 * (dx / float(hr + 1))))
        joint_on = end or t > 3.5
        tipx, tipy = int(H[0] + K(jdx)), int(H[1] + K(jdy))
        if joint_on:
            for q in range(0, max(2, K(6))):
                put_c(int(H[0] + K(jdx) * q / float(max(1, K(6)))), int(H[1] + K(jdy) * q / float(max(1, K(6)))), (240, 234, 220) if q < K(5) else (206, 190, 170))
        lit = end or t > 5.6
        flick = 0.8 + 0.2 * math.sin(t * 17)
        if not end and 4.7 <= t < 6.3:
            fl_ = 0.6 + 0.4 * math.sin(t * 31)
            lx_, ly_ = tipx - 1, tipy + K(2)
            for r in range(max(2, K(3))):
                photo_fx.put_pixel(cv, lx_, ly_ - r, (255, int(240 - 30 * r), int(160 - 40 * r)))
            glow(cv, lx_, ly_ // 2, 12, 5, (255, 170, 60), 0.45 * fl_)
        if joint_on and lit:
            if inh > 0.02:
                glow(cv, tipx, tipy // 2, 10 + 8 * inh, 4 + 3 * inh, (255, 120, 30), 0.25 + 0.75 * inh)
                glow(cv, mx, tipy // 2 + 3, 18, 9, (255, 130, 50), 0.12 * inh)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        photo_fx.put_pixel(cv, tipx + dx, tipy + dy, (255, int(170 + 80 * inh), 80) if abs(dx) + abs(dy) < 2 else (255, 120, 40))
            else:
                photo_fx.put_pixel(cv, tipx, tipy, (240, 100, 34))
                glow(cv, tipx, tipy // 2, 4, 2, (255, 110, 30), (0.22 + 0.1 * math.sin(t * 5)) * flick)
        # --- smoke
        if joint_on and lit and inh > 0.4 and rng.random() < 0.6:
            self.puff(tipx, tipy - 1, rng.uniform(-1, 1), -rng.uniform(3, 7), 1.4, 1.2, 3.5, 0.8)
        if end and 7.0 < t < 8.6 and t - self.last_exh > 0.04:
            self.last_exh = t
            for _ in range(4):
                self.puff(H[0] - K(1), H[1] + K(1), rng.uniform(2, 9), -rng.uniform(1.0, 5.0), rng.uniform(3.5, 5.5), 2.0, 8.5, 1.0)
        if end and 8.6 < t < 12.6 and t - self.last_exh > 0.05:
            self.last_exh = t
            for _ in range(3):
                self.puff(H[0], H[1], rng.uniform(5, 11) * 1.6, -rng.uniform(0.4, 2.6), rng.uniform(4.5, 7.5), 1.8, 7.0, 0.9)
        if joint_on and lit and rng.random() < 0.5:
            self.puff(tipx, tipy - 1, rng.uniform(-0.5, 0.5), -rng.uniform(4, 7), 3.2, 0.8, 3.6, 0.7)
        for q in self.puffs:
            q[4] += dt
            q[0] += (q[2] + math.sin(q[4] * 2.1 + q[8]) * 3.2) * dt
            q[1] += q[3] * dt
            q[3] *= 0.994
            kk = min(1.0, q[4] / q[5])
            r = q[6] + (q[7] - q[6]) * math.sqrt(kk)
            a = q[9] * 0.85 * (1 - kk) ** 0.8 * min(1.0, q[4] * 5)
            litc = mix((214, 210, 214), (255, 226, 190), 0.6 * (q[0] / float(w)))
            for dy in range(-int(r) - 1, int(r) + 2):
                for dx in range(-int(r * 2) - 1, int(r * 2) + 2):
                    d = math.hypot(dx / 2.0, dy)
                    if d < r:
                        blend_px(cv, int(q[0]) + dx, int(q[1]) + dy, mix(litc, (150, 146, 156), d / r * 0.5), a * (1 - 0.6 * d / r))
        self.puffs = [q for q in self.puffs if q[4] < q[5]]
        for lx, ly, sp, ph in self.leaves:
            x, y = int((lx + math.sin(t * 0.8 + ph) * 8 + t * 2.2) % w), int((ly + t * sp) % (2 * h))
            c = AUTUMN[int(ph * 2) % 4]
            photo_fx.put_pixel(cv, x, y, c)
            if int(t * 3 + ph) % 2:
                photo_fx.put_pixel(cv, x + 1, y, mul(c, 0.8))
        photo_fx.finish(cv, t, 0.04, 0.28)
        fade = smooth(t) if t < 1.0 else 1.0
        if not end and t > T - 1.0:
            fade = max(0.0, T - t)
        scene = fade * (1.0 if not end else 1.0 - 0.3 * smooth((t - 6) / 8.0))
        if end and t > 12.0:                                                                  # everything goes dark but the cube that floats over his open hand
            ka = smooth((t - 12.4) / 2.2)
            scene *= 1 - ka
            darken(cv, scene)
            ox, oy = H[0], H[1] // 2 - max(5, int(h * 0.16))
            draw_cube(cv, ox, oy, 5, t, (150, 230, 255), ka)
            glow(cv, ox, oy, 18, 8, (110, 150, 255), 0.3 * ka)
            glow(cv, H[0], H[1] // 2, 6, 2, (120, 190, 255), 0.35 * ka)
            return 0, 0
        darken(cv, scene)
        return 0, 0




BENCH_CUES = {"intro": [], "end": []}                      # no joint sounds (the user has none yet): only the music plays; the scene is silent


class MikaDemo:
    """Mika on his own (14 s): he forms in teal light and opens his eyes (standing, coat and hair drifting), then the bench at dusk with the joint
    and the smoke. python3 play.py --mika-ending --only mika"""
    END = 14.0

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.fig = MikaFigure(int(h * 0.74))
        self.bench = BenchScene(w, h, rng, "end")
        self.parts = Particles(rng, 300)

    def draw(self, cv, t, dt):
        w, h, rng = self.w, self.h, self.rng
        if t >= 7.0:
            r = self.bench.draw(cv, t - 7.0 + 0.0, dt)
            flash(cv, (200, 255, 240), max(0.0, 1 - (t - 7.0) / 0.4) * 0.8)
            return r
        cv.clear((2, 4, 7))
        cx, cy = w // 2, int(h * 0.62)
        k = smooth(t / 5.0)
        glow(cv, cx, cy, w * 0.3, h * 0.55, (40, 170, 160), 0.5 * k)
        glow(cv, cx, cy, w * 0.12, h * 0.4, (200, 255, 235), 0.4 * k)
        grid, _ = self.fig.cells(t, eyes=smooth((t - 3.5) / 2.0), aura=0.3 + 0.7 * k, reveal=smooth(t / 4.0), tint=((225, 255, 245), 0.15 * k))
        blit_grid(cv, grid, cx - self.fig.wf // 2, int(h * 0.12))
        if t > 3.5:
            for sx in (-1, 1):
                glow(cv, cx + sx * 1.2 * 2 * self.fig.s, int(h * 0.12) + 6.6 * self.fig.s, 5, 2, (120, 255, 225), 0.7 * smooth((t - 3.5) / 2.0))
        for _ in range(2):
            self.parts.add(rng.randrange(w), h - 1, rng.uniform(-1, 1), -rng.uniform(2, 6), 3.0, "mote", -0.3)
        self.parts.step(dt)
        self.parts.draw(cv, 0.2)
        if t < 0.8:
            darken(cv, smooth(t / 0.8))
        return 0, 0


MIKA_CUES = [(0.0, "glow-hum-rising"), (3.5, "lake-whispers")]
