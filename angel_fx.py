"""angel_fx.py - the Weeping Angel and Noah's eyes, for noah_burns (pure drawing helpers on noah_gore_fx.Canvas, deterministic).

    sky_tear(cv, p, t, rng)          a jagged white-gold tear in the sky, p 0..1 open (it closes again with p back to 0)
    draw_angel(cv, cx, ybase, hf, light, seed)  a big stone angel: wings with cracked feathers, robes with folds, bowed head, both hands over its eyes
    draw_eyes(cv, t, k, rng)         EXTREME close-up of both eyes: iris, reflections of the fire AND of the angel, a pupil that dilates, tears that boil,
                                     lashes that burn, lids that blister.     k = how far the camera has pushed in (0..1)
The cult stands in the scene and never looks up: only Noah and the player see the angel (noah_gore_fx.BurnScene.shot_angel).
"""
import math

import noah_gore_fx as G
import photo_fx
from noah_gore_fx import add, fire_rgb, mix, mul, smooth, thick_line, walk, _hash

STONE_HI, STONE_LO, MOSS = (176, 176, 182), (74, 74, 84), (70, 96, 70)


def sky_tear(cv, p, t, rng, cx=None):
    """A vertical jagged tear from the top down to row p*0.55*h, with light pouring out of it."""
    w, h = cv.w, cv.h
    cx = w // 2 if cx is None else cx
    if p <= 0.01:
        return
    depth = int(h * 0.62 * min(1.0, p * 1.4))
    width = 1 + int(14 * p)
    x = float(cx)
    for y in range(depth):
        x += math.sin(y * 1.7 + 3) * 1.1 + (_hash(y, 1) - 0.5) * 2.0
        half = max(1, int(width * (1 - y / float(depth + 2)) * (0.6 + 0.5 * _hash(y, 2))))
        for dx in range(-half - 3, half + 4):
            xx = int(x) + dx
            a = abs(dx)
            if a <= half:
                cv.put(xx, y, " ", None, mix((255, 240, 200), (255, 250, 235), _hash(xx, y)))
            else:
                cv.light(xx, y, (255, 220, 150), 0.5 * (1 - (a - half) / 3.0), 0.5)
                cv.put(xx, y, "/\\|"[(xx + y) % 3], (255, 255, 235))
    for y in range(depth, min(h, depth + int(h * 0.35))):                                         # the light pours down in a cone
        for dx in range(-int(width * 2 + (y - depth)), int(width * 2 + (y - depth)) + 1):
            cv.light(int(x) + dx, y, (255, 215, 150), 0.10 * p * (1 - (y - depth) / (h * 0.35)), 0.4)


MARBLE_HI, MARBLE_LO = (244, 240, 232), (118, 124, 146)


def draw_angel(cv, cx, ybase, hf, light=1.0, seed=0, open_=0.0, fire=0.6):
    """A mourning marble angel (in the manner of the Angel of Grief): slumped forward, her face hidden in the crook of the left arm, the right arm hanging
    limp with the hand open, one huge wing folded down along the back and side (open_ 0..1 lets it part a little), drapery folds to the ground.
    hf rows tall, feet at ybase, centre column cx. fire = how much firelight from below warms the marble."""
    s = hf / 40.0
    def P(tx, ty):
        return int(cx + tx * 2 * s), int(ybase - (40 - ty) * s)
    def marble(x, y, k, ch=None, tone=0.0):
        n = _hash(x, y, seed)
        lum = max(0.0, min(1.0, 0.52 + 0.55 * k + 0.12 * (n - 0.5))) * light
        col = mix(MARBLE_LO, MARBLE_HI, lum)
        ty = (y - (ybase - hf)) / float(hf)                                                      # warmer towards the feet: the fire
        col = add(col, (110, 50, 12), fire * max(0.0, ty - 0.3) * 0.7)
        if n > 0.965:                                                                            # a vein in the stone
            col = mul(col, 0.6)
        cv.put(x, y, ch or ".:'`"[int(n * 4)], mul(col, 1.05), mul(col, 0.55))
    # the folded wing: feather rows hang from the shoulder blade down past the knee, the tip sweeping out to the right
    for r in range(11):
        f = r / 10.0
        x0, y0 = P(2.0 + 5.2 * f + open_ * 3.5 * f, 8.5 + 4.0 * f)
        x1, y1 = P(6.5 + 7.0 * f + open_ * 6.0 * f, 30 + 10.0 * f)
        for x, y, d in thick_line((x0, y0), (x1, y1), 1.1 + 0.5 * f):
            marble(x, y, 0.55 + 0.4 * (1 - f) - 0.2 * d / 1.6, "(" if (x + y) % 5 else ")")
        for j in range(5):                                                                       # the quills' pale edges
            ex, ey = x0 + (x1 - x0) * (0.2 + 0.18 * j), y0 + (y1 - y0) * (0.2 + 0.18 * j)
            marble(int(ex) + 1, int(ey), 1.0, "|")
    for r in range(5):                                                                           # the other wing's tip, folded behind the head
        a = P(-3.0 - r * 0.6, 9.0)
        b = P(-7.5 - r * 0.8, 1.5 - r * 0.6)
        for x, y, d in thick_line(a, b, 0.9):
            marble(x, y, 0.35 + 0.1 * r, "/")
    # torso, bent forward; the gown below it
    for ty10 in range(100, 400, 2):
        ty = ty10 / 10.0
        lean = -0.9 * max(0.0, 1 - (ty - 10.0) / 14.0)                                          # the chest is leaning forward and to the left
        hw = (4.4 - (ty - 10) * 0.05) if ty < 24 else 3.9 + (ty - 24) * 0.30
        hw *= 1 + 0.05 * math.sin(ty * 1.7)
        x0, y = P(lean - hw, ty)
        x1, _ = P(lean + hw, ty)
        for x in range(x0, x1 + 1):
            u = (x - x0) / float(max(1, x1 - x0))
            fold = 0.5 + 0.5 * math.sin((u * 7.0 + (ty * 0.12 if ty > 24 else 0)) * 3.14159)
            k = 0.35 + 0.55 * fold * (0.7 + 0.3 * (1 - u)) if ty > 22 else 0.5 + 0.35 * (1 - u)
            marble(x, y, k, "|!:"[(x + int(ty)) % 3] if (ty > 22 and fold > 0.55) else None)
    for k in range(5):                                                                           # a swag of cloth across the hip
        a = P(-3.5 + k * 0.4, 21 + k * 0.5)
        b = P(4.8, 27 + k * 0.7)
        for x, y, d in thick_line(a, b, 0.7):
            marble(x, y, 0.9 - 0.12 * k, "~")
    # the bowed head, with carved curls, and the left arm folded over the face
    for ty10 in range(30, 110, 3):
        ty = ty10 / 10.0
        hw = 2.9 * math.sqrt(max(0.0, 1 - ((ty - 6.6) / 3.8) ** 2))
        x0, y = P(-1.6 - hw, ty)
        x1, _ = P(-1.6 + hw, ty)
        for x in range(x0, x1 + 1):
            marble(x, y, 0.85 - 0.3 * (x - x0) / float(max(1, x1 - x0)))
    for k in range(9):
        x, y = P(-4.4 + 0.65 * k, 3.1 + 0.4 * abs(k - 4))
        marble(x, y, 0.95, "@6980"[k % 5])
    for sd in (-4.2, -4.8, -4.2):
        pass
    for a, b, r in ((P(-4.2, 11.5), P(-7.2, 8.0), 1.2), (P(-7.2, 8.0), P(-0.6, 6.4), 1.15)):     # upper arm up and out, forearm across the face
        for x, y, d in thick_line(a, b, r):
            marble(x, y, 0.95 - 0.35 * d / 1.4, "=" if abs(b[1] - a[1]) < 3 else "(")
    for dx in range(0, 4):                                                                       # the fingers resting in the hair
        x, y = P(-0.2 + dx * 0.5, 6.0 - dx * 0.4)
        marble(x, y, 1.0, "/")
    # the right arm hanging limp, the hand open
    for a, b, r in ((P(4.4, 12.3), P(5.6, 19.0), 1.15), (P(5.6, 19.0), P(5.2, 26.0), 1.0)):
        for x, y, d in thick_line(a, b, r):
            marble(x, y, 0.8 - 0.3 * d / 1.3, "|")
    for f in range(4):                                                                           # four fingers hanging, a thumb out
        a = P(4.4 + f * 0.55, 26.0)
        b = P(4.2 + f * 0.7, 30.5 + (f % 2) * 0.8)
        for x, y, d in thick_line(a, b, 0.5):
            marble(x, y, 0.9, "l")


def G_put(cv, x, y, ch, fg, bg):
    cv.put(x, y, ch, fg, bg)


def _eye(cv, cx, cy, ew, eh, t, k, lid, rng, flip):
    """One eye: almond of half-width ew (cells), half-height eh (rows). lid 0..1 how open (1 open)."""
    pd = 0.28 + 0.30 * smooth((t - 0.3) / 2.2)                                                       # the pupil dilates as the light comes
    ri = eh * 0.95
    for y in range(cy - eh - 4, cy + eh + 5):
        for x in range(cx - ew - 6, cx + ew + 7):
            dx, dy = (x - cx) / float(ew), (y - cy) / float(eh)
            if abs(dx) > 1.15:
                continue
            top = -(1 - min(1.0, dx * dx) ** 0.85) * lid
            bot = (1 - min(1.0, dx * dx) ** 0.95) * 0.95
            if top <= dy <= bot and abs(dx) <= 1.0:
                r = math.hypot((x - cx) / 2.0, y - cy)
                if r < ri:                                                                           # iris: radial streaks, a dark limbal ring
                    ang = math.atan2(y - cy, (x - cx) / 2.0)
                    streak = 0.5 + 0.5 * math.sin(ang * 23 + r * 0.5) * math.sin(ang * 7 + 1)
                    base = mix((140, 60, 20), (255, 170, 60), streak) if r > ri * pd else (4, 0, 0)
                    if r > ri * 0.86:
                        base = mul(base, 0.45)
                    flick = 0.5 + 0.5 * math.sin(t * 9 + ang * 3)
                    if dy > 0.1 and r > ri * pd:                                                     # the fire, reflected in the lower half
                        base = add(base, (230, 90, 10), 0.35 * flick * (dy + 0.2))
                    ch = ".:*"[int(streak * 2.9)] if r > ri * pd else " "
                    cv.put(x, y, ch, mul(base, 1.25), mul(base, 0.7))
                else:                                                                                # sclera with veins
                    vein = _hash(x // 2, y, 5) > 0.82 or (_hash(x, y // 2, 6) > 0.93)
                    cv.put(x, y, "-" if vein else " ", (190, 20, 24), (232, 206, 200) if not vein else (214, 150, 146))
            elif -1.15 < dx < 1.15 and (top - 0.32 < dy < top or bot < dy < bot + 0.4):          # the lids: blistered, red, black where the lashes burn
                n = _hash(x, y, 8)
                cv.put(x, y, "oO%#"[int(n * 4)] if n < 0.4 else ":", mix((255, 190, 160), (170, 40, 30), n), mix((150, 50, 40), (80, 14, 12), n))
    # lashes: dark lines up out of the upper lid, ember at the tip, smoke
    for i in range(-ew + 3, ew - 2, 3):
        dx = i / float(ew)
        ly = cy + int((-(1 - min(1.0, dx * dx) ** 0.85) * lid) * eh)
        n = _hash(i, 3, flip)
        L = int(2 + 3 * n)
        for j in range(L):
            ch = "|/\\"[(0 if abs(i) < ew // 3 else 1 if i * (1 if flip else -1) > 0 else 2)]
            cv.put(cx + i + int(j * (0.7 if i > 0 else -0.7)), ly - j - 1, ch, (30, 20, 20) if j < L - 1 else (255, 150, 40))
        if n > 0.5 and rng.random() < 0.3:
            cv.put(cx + i, ly - L - 1 - int(t * 3) % 3, "'`~"[int(rng.random() * 3)], (150, 150, 160))


def draw_eyes(cv, t, k, rng, angel_cb=None):
    """Both eyes, side by side, filling the width like a letterboxed film frame. t = shot time; k = push-in 0..1."""
    w, h = cv.w, cv.h
    cv.clear((16, 4, 4))
    for y in range(h):                                                                               # burnt skin around the eyes, flickering orange
        for x in range(w):
            n = _hash(x // 2, y, 4)
            cv.bg[y * w + x] = mix((52, 14, 12), (96, 30, 18), n * 0.6 + 0.1 * math.sin(t * 7 + x * 0.1))
    ew = int(min(w * 0.17, 44) * (1 + 0.28 * k))
    eh = max(4, int(ew * 0.30))
    sep = int(ew * 1.45)
    lid = 0.55 + 0.45 * smooth(t / 0.8)
    cy = h // 2 - 2
    for i, sx in enumerate((-1, 1)):
        cx = w // 2 + sx * sep + int(math.sin(t * 0.8) * 2)
        _eye(cv, cx, cy, ew, eh, t, k, lid, rng, sx > 0)
        ri = eh * 0.95                                                                               # reflections inside the iris
        hx, hy = cx - int(ri * 0.9), cy - int(ri * 0.45)
        for dx in range(-2, 3):
            cv.put(hx + dx, hy, "=", (255, 255, 255), (255, 255, 255))                               # the window light
        ax, ay = cx + int(ri * 0.9), cy - int(ri * 0.15)                                             # the stone angel, small, in the upper right of the iris
        draw_angel_statue(cv, ax - 7, ay - 5, 14, 1.0, 0.0)                                           # the angel, mirrored small in the iris
        lidy = lambda x: cy + (1 - min(1.0, ((x - cx) / float(ew)) ** 2) ** 0.95) * 0.95 * eh               # the lower lid line (same curve as the eye itself)
        for x in range(cx - int(ew * 0.8), cx + int(ew * 0.8)):                                      # the water line: a wet glint along the lower lid
            if (x * 7 + int(t * 6)) % 5:
                photo_fx.put_pixel(cv, x, int(2 * lidy(x)) + 1, (150, 190, 230) if (x + int(t * 9)) % 4 else (255, 255, 255))
        for j in range(8):                                                                           # tears: wide wet streaks from the lower lid, each ends in a fat drop that runs
            u = (j - 3.5) / 4.6 * 0.62 + 0.04 * math.sin(j * 2.1 + i)
            x0 = cx + int(u * ew)
            wd = 2 + (j + i) % 3                                                                    # 2-4 pixels wide
            ph = (t * 3.4 + j * 2.3 + i * 1.3) % 14.0                                                # how far this tear has run, then it starts again
            y0 = int(2 * lidy(x0)) + 1
            ln = int(min(ph, 11.0) * 3.2)
            if t < 0.4 + 0.25 * j:
                continue
            for k in range(ln):
                xx = x0 + int(math.sin(k * 0.13 + j * 1.7) * 1.4 + k * 0.012 * (j - 3.5) * 2)
                fade = 1.0 - 0.35 * k / float(max(1, ln))
                for q in range(wd):
                    edge = q == 0
                    col = (232, 244, 255) if edge and (k % 7 < 5) else ((150, 188, 226) if q < wd - 1 else (74, 100, 150))
                    photo_fx.put_pixel(cv, xx + q, y0 + k, tuple(int(c * fade) for c in col))
                if k % 11 == 3 and not edge:
                    photo_fx.put_pixel(cv, xx + 1, y0 + k, (255, 255, 255))                          # a glint in the firelight
            dx_ = x0 + int(math.sin(ln * 0.13 + j * 1.7) * 1.4)
            photo_fx.teardrop(cv, dx_ + wd // 2, y0 + ln, 1.0, 2 if wd > 2 else 1)
            if ph > 10.0:                                                                           # the drop hits the hot skin: steam
                for _ in range(2):
                    cv.put(dx_ + rng.randint(-3, 3), (y0 + ln) // 2 - 1 - rng.randint(0, 2), "~;'"[rng.randrange(3)], (225, 225, 235))
        for j in range(5):                                                                           # drops that have come loose and fall free
            ph = (t * 7.0 + j * 5.3 + i * 2.9) % 12.0
            fx = cx + int(((j - 2) / 2.6) * ew * 0.6) + i
            photo_fx.teardrop(cv, fx, int(2 * lidy(fx)) + 6 + int(ph * ph * 0.55), 0.95, 1 + (j % 2))
        for j in range(4):                                                                           # the lashes boil: small bubbles at their tips
            bx = cx + (j - 2) * (ew // 3)
            if rng.random() < 0.5:
                cv.put(bx + rng.randint(-1, 1), cy - eh - 3 - rng.randint(0, 2), "o°"[rng.randrange(2)], (255, 190, 90))
        glow_k = 0.25
        G.glow(cv, hx + 6, cy + eh // 2, ew // 2, eh // 2, (255, 90, 20), glow_k)


_ang = {}


def _gold(light, fire):
    def f(r, g, b, x, y):
        L = max(0.0, min(1.0, ((r * 0.3 + g * 0.59 + b * 0.11) / 255.0 - 0.12) * 1.2 * light)) ** 1.15
        c = G.ramp([(0.0, (36, 22, 16)), (0.42, (176, 126, 74)), (0.78, (250, 216, 152)), (1.0, (255, 247, 220))], L)
        return add(c, (70, 30, 6), fire * 0.35)
    return f


def draw_angel_statue(cv, x, y, w_cols, light=1.0, fire=0.4):
    """The stone mourner of proc_art.angel() (hooded, kneeling, face in the arm, a folded wing down the back, fog at her feet), tinted warm gold.
    (x, y) = top-left cell, w_cols = width in cells. Returns (width, height) in cells."""
    w_cols = max(8, int(w_cols))
    im = photo_fx.image("angel")
    h_px = int(w_cols * im[1] / float(im[0]))
    h_px -= h_px % 2
    key = (w_cols, h_px)
    if key not in _ang:
        _ang[key] = photo_fx.fit("angel", w_cols, h_px)
    photo_fx.paint(cv, _ang[key], int(x), int(y), _gold(light, fire))
    return w_cols, h_px // 2


def sky_gold(cv, t, p, rng, horizon, cx, feet):
    """Golden clouds that gather and break open (p 0..1 gathered, q 0..1 opened) and the god-ray beam that falls through the opening. Returns beam strength."""
    w, h = cv.w, cv.h
    gather = smooth(p)
    for y in range(0, horizon + 2):
        for x in range(w):
            i = y * w + x
            n = 0.5 + 0.25 * math.sin(x * 0.07 + t * 0.4 + y * 0.3) + 0.25 * math.sin(x * 0.19 - t * 0.7 + y * 0.9)
            d = abs(x - cx) / float(w * 0.5)
            cloud = gather * n * (0.55 + 0.45 * (1 - d))
            if cloud > 0.2:
                col = mix((70, 40, 36), (230, 175, 96), min(1.0, cloud * 1.2))
                cv.bg[i] = mix(cv.bg[i], col, min(1.0, cloud))
                cv.fg[i] = mix(cv.fg[i], col, min(1.0, cloud))
    return gather


def god_ray(cv, t, k, cx, y0, y1, rng):
    """A cone of golden light from the opening at (cx, y0) down to y1 with streaks; k 0..1."""
    if k <= 0.01:
        return
    w = cv.w
    for y in range(max(0, y0), min(cv.h, y1)):
        f = (y - y0) / float(max(1, y1 - y0))
        half = int(6 + f * w * 0.16)
        for dx in range(-half, half + 1):
            streak = 0.6 + 0.4 * math.sin(dx * 0.9 + t * 0.7) * math.sin(dx * 0.31 - t * 0.4)
            a = k * (1 - abs(dx) / float(half + 1)) ** 1.4 * (1 - 0.5 * f) * streak * 0.34
            cv.light(cx + dx, y, (255, 215, 140), a, 0.5)
