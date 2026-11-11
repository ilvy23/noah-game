"""tools/portrait_art.py - draws the character busts and Noah's animation frames as pixel art (Pillow + numpy, no outside art)
and turns them into coloured ASCII (art/portraits.json, art/noah_anim.json, previews in art/previews/).

Run:  uv run --no-project --with pillow --with numpy python3 tools/portrait_art.py [portraits|anim|previews|all]
Everything is drawn by code at S x S pixels, then converted cell by cell: a cell is 4x8 pixels, its glyph follows the ink
coverage / edge direction, its foreground and background colours come from the two colour clusters inside the cell.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "art")
FONT = "/nix/store/0ll7yhrqgbkmb05wwya0vgjd7y4v2hq5-nerd-fonts-jetbrains-mono-3.4.0+2.304/share/fonts/truetype/NerdFonts/JetBrainsMono/JetBrainsMonoNerdFontMono-Bold.ttf"
S = 960


# ------------------------------------------------------------------ drawing helpers
def new(c=(0, 0, 0, 0)):
    return Image.new("RGBA", (S, S), c)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def spline(pts, closed=True, n=10):
    """Catmull-Rom through the points: smooth hair and faces from a few control points."""
    p = list(pts)
    m = len(p)
    out = []
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0, p1, p2, p3 = (p[(i - 1) % m], p[i], p[(i + 1) % m], p[(i + 2) % m]) if closed else \
            (p[max(i - 1, 0)], p[i], p[i + 1], p[min(i + 2, m - 1)])
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    return out


def mask_of(fn, blur=0):
    m = Image.new("L", (S, S), 0)
    fn(ImageDraw.Draw(m))
    return m.filter(ImageFilter.GaussianBlur(blur)) if blur else m


def poly_mask(pts, closed=True, blur=0):
    return mask_of(lambda d: d.polygon(spline(pts, closed), fill=255), blur)


def paint(img, mask, color, alpha=1.0, clip=None):
    if clip is not None:
        mask = ImageChops.multiply(mask, clip)
    if alpha < 1:
        mask = mask.point(lambda v: int(v * alpha))
    img.paste(Image.new("RGBA", (S, S), tuple(color[:3]) + (255,)), (0, 0), mask)


def grad(img, mask, top, bot, y0, y1, clip=None):
    """Fill `mask` with a vertical gradient."""
    t = np.clip((np.arange(S) - y0) / max(1, y1 - y0), 0, 1)[:, None, None]
    arr = np.array(top, dtype=np.float32) * (1 - t) + np.array(bot, dtype=np.float32) * t
    g = Image.fromarray(np.broadcast_to(arr, (S, S, 3)).astype(np.uint8), "RGB").convert("RGBA")
    if clip is not None:
        mask = ImageChops.multiply(mask, clip)
    img.paste(g, (0, 0), mask)


def glow(img, x, y, r, color, k=1.0):
    yy, xx = np.mgrid[0:S, 0:S]
    d = ((xx - x) ** 2 + (yy - y) ** 2) / (r * r)
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    a += (np.exp(-d * 2.0) * k)[..., None] * np.array(color, dtype=np.float32)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    img.paste(out, (0, 0))


def line(d, pts, w, fill, smooth=True):
    pp = spline(pts, False, 8) if smooth and len(pts) > 2 else pts
    d.line(pp, fill=fill, width=int(w), joint="curve")
    r = w / 2
    for p in (pp[0], pp[-1]):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=fill)


def rot(img, ang, pivot, dx=0, dy=0):
    return img.rotate(ang, resample=Image.BICUBIC, center=pivot, translate=(dx, dy))


# ------------------------------------------------------------------ palettes
PAL = {
    "green": dict(skin=(246, 214, 190), skin_sh=(206, 152, 138), skin_hi=(255, 236, 216), hair=(70, 54, 46), hair_sh=(34, 26, 28), hair_hi=(150, 190, 120),
                  iris_a=(24, 110, 90), iris_b=(140, 235, 170), scarf1=(236, 226, 196), scarf2=(70, 140, 84), shirt=(52, 78, 66), blush=(255, 128, 130),
                  bg_top=(8, 28, 22), bg_bot=(22, 64, 44), glow=(255, 214, 120), rim=(160, 255, 190), lip=(214, 110, 110)),
    "yellow": dict(skin=(240, 214, 186), skin_sh=(184, 150, 120), skin_hi=(255, 240, 210), hair=(226, 190, 80), hair_sh=(120, 88, 24), hair_hi=(255, 244, 170),
                   iris_a=(120, 72, 6), iris_b=(255, 214, 60), scarf1=(214, 168, 36), scarf2=(70, 52, 20), shirt=(58, 50, 36), blush=(230, 160, 120),
                   bg_top=(26, 20, 4), bg_bot=(70, 54, 12), glow=(255, 232, 120), rim=(255, 240, 150), lip=(176, 98, 84)),
    "red": dict(skin=(226, 186, 170), skin_sh=(150, 90, 90), skin_hi=(255, 214, 196), hair=(46, 14, 20), hair_sh=(16, 4, 8), hair_hi=(210, 40, 40),
                iris_a=(110, 0, 8), iris_b=(255, 70, 40), scarf1=(120, 14, 22), scarf2=(40, 8, 12), shirt=(40, 18, 22), blush=(210, 60, 70),
                bg_top=(16, 0, 2), bg_bot=(84, 10, 8), glow=(255, 90, 40), rim=(255, 90, 60), lip=(150, 40, 50)),
    "mika": dict(skin=(226, 200, 180), skin_sh=(160, 130, 126), skin_hi=(248, 226, 206), hair=(30, 40, 52), hair_sh=(10, 14, 22), hair_hi=(110, 160, 190),
                 iris_a=(60, 70, 80), iris_b=(150, 190, 200), scarf1=(150, 160, 170), scarf2=(110, 120, 132), shirt=(128, 138, 150), blush=(220, 130, 120),
                 bg_top=(6, 14, 24), bg_bot=(28, 52, 70), glow=(150, 200, 230), rim=(120, 200, 230), lip=(180, 110, 104)),
    "connor": dict(skin=(236, 206, 184), skin_sh=(176, 134, 118), skin_hi=(255, 232, 208), hair=(150, 146, 150), hair_sh=(70, 68, 76), hair_hi=(228, 226, 232),
                   iris_a=(74, 82, 94), iris_b=(174, 184, 196), scarf1=(236, 230, 218), scarf2=(190, 184, 176), shirt=(44, 38, 44), blush=(220, 140, 130),
                   bg_top=(12, 6, 6), bg_bot=(54, 28, 18), glow=(255, 180, 90), rim=(255, 190, 120), lip=(190, 120, 112)),
}


# ------------------------------------------------------------------ the pieces of a face
FACE = [(338, 330), (332, 440), (356, 540), (414, 616), (480, 646), (546, 616), (604, 540), (628, 440), (622, 330), (590, 236), (480, 206), (370, 236)]
CX, EYE_Y, EYE_DX = 480, 452, 66


def face_mask(dx=0, dy=0):
    return poly_mask([(x + dx, y + dy) for x, y in FACE])


def eye(img, cx, cy, w, h, p, open_=1.0, look=(0.0, 0.0), slit=False, flip=1, lash=1.0, ring=None):
    """One big anime eye: sclera, iris gradient, pupil, highlights, lid and lashes. open_ < 1 lowers the lid."""
    u = np.linspace(-1, 1, 41)
    sq = np.sqrt(1 - u ** 2)
    top = [(cx + ui * w / 2, cy - h / 2 * open_ * s * (1.0 if ui * flip < 0.2 else 0.9)) for ui, s in zip(u, sq)]
    bot = [(cx + ui * w / 2, cy + h / 2 * (0.5 + 0.5 * open_) * s * 0.85) for ui, s in zip(u[::-1], sq[::-1])]
    vis = mask_of(lambda d: d.polygon(top + bot, fill=255))
    layer = new()
    d = ImageDraw.Draw(layer)
    d.rectangle((0, 0, S, S), fill=(238, 236, 240, 255))
    lid = mask_of(lambda dd: dd.rectangle((cx - w, cy - h, cx + w, cy - h * 0.1), fill=255), 12)
    paint(layer, lid, (150, 130, 150), 0.55)
    ix, iy = cx + look[0] * w * 0.12, cy + h * 0.02 + look[1] * h * 0.1
    rx, ry = w * 0.37, h * 0.47
    im = mask_of(lambda dd: dd.ellipse((ix - rx, iy - ry, ix + rx, iy + ry), fill=255))
    grad(layer, im, p["iris_a"], p["iris_b"], iy - ry, iy + ry)
    rim = mask_of(lambda dd: (dd.ellipse((ix - rx, iy - ry, ix + rx, iy + ry), outline=255, width=max(3, int(w * 0.05)))), 2)
    paint(layer, rim, shade(p["iris_a"], 0.4), 0.9)
    if ring:                                                      # a faint second colour ring (a lake demon in disguise)
        rr = mask_of(lambda dd: dd.ellipse((ix - rx * 0.8, iy - ry * 0.8, ix + rx * 0.8, iy + ry * 0.8), outline=255, width=max(3, int(w * 0.04))), 2)
        paint(layer, rr, ring, 0.8)
    prx = rx * (0.16 if slit else 0.45)
    pm = mask_of(lambda dd: dd.ellipse((ix - prx, iy - ry * 0.62, ix + prx, iy + ry * 0.62), fill=255), 1)
    paint(layer, pm, (8, 4, 12))
    for (ox, oy, r, a) in ((-0.38, -0.42, 0.30, 1.0), (0.32, 0.38, 0.14, 0.9), (0.05, 0.62, 0.08, 0.6)):
        hm = mask_of(lambda dd: dd.ellipse((ix + ox * rx - r * rx, iy + oy * ry - r * rx, ix + ox * rx + r * rx, iy + oy * ry + r * rx), fill=255), 1.5)
        paint(layer, hm, (255, 255, 255), a)
    img.paste(layer, (0, 0), vis)
    lw = h * 0.1 * lash
    line(ImageDraw.Draw(img), top[:: 4], lw, (14, 8, 14, 255), False)
    fx, fy = top[-1] if flip > 0 else top[0]
    line(ImageDraw.Draw(img), [top[-3] if flip > 0 else top[2], (fx + flip * w * 0.12, fy - h * 0.1), (fx + flip * w * 0.22, fy - h * 0.2)], lw * 0.8, (14, 8, 14, 255))
    line(ImageDraw.Draw(img), bot[:: 5], max(2, lw * 0.35), shade(p["skin_sh"], 0.55) + (255,), False)
    return top


def brow(img, cx, cy, w, tilt, thick, col, flip=1):
    d = ImageDraw.Draw(img)
    a = [(cx - w / 2 * flip, cy + tilt * flip * -1), (cx, cy - thick * 0.4), (cx + w / 2 * flip, cy + tilt * flip)]
    line(d, a, thick, col + (255,))


def mouth(img, p, kind, y=575, w=44):
    d = ImageDraw.Draw(img)
    dark = (60, 18, 28, 255)
    lipc = p["lip"] + (255,)
    if kind == "smile":
        line(d, [(CX - w, y - 6), (CX - w * 0.4, y + 12), (CX + w * 0.4, y + 12), (CX + w, y - 6)], 7, dark)
        line(d, [(CX - w * 0.35, y + 15), (CX, y + 20), (CX + w * 0.35, y + 15)], 5, lipc)
    elif kind == "open":
        m = mask_of(lambda dd: dd.polygon(spline([(CX - w, y - 8), (CX, y + 8), (CX + w, y - 8), (CX + w * 0.7, y + 36), (CX, y + 48), (CX - w * 0.7, y + 36)]), fill=255), 0.6)
        paint(img, m, (96, 24, 40))
        tm = mask_of(lambda dd: dd.rectangle((CX - w * 0.8, y - 8, CX + w * 0.8, y + 6), fill=255))
        paint(img, tm, (246, 240, 236), 1, m)
        tg = mask_of(lambda dd: dd.ellipse((CX - w * 0.4, y + 26, CX + w * 0.4, y + 56), fill=255))
        paint(img, tg, (200, 80, 92), 1, m)
        line(d, [(CX - w, y - 8), (CX, y + 6), (CX + w, y - 8)], 6, dark)
    elif kind == "grit":                                          # teeth bared
        m = mask_of(lambda dd: dd.polygon(spline([(CX - w, y - 4), (CX, y - 14), (CX + w, y - 4), (CX + w * 0.8, y + 26), (CX, y + 34), (CX - w * 0.8, y + 26)]), fill=255), 0.6)
        paint(img, m, (240, 232, 226))
        for k in range(-4, 5):
            d.line((CX + k * w * 0.2, y - 12, CX + k * w * 0.2, y + 32), fill=(110, 40, 44, 255), width=4)
        d.line((CX - w, y + 10, CX + w, y + 10), fill=(110, 40, 44, 255), width=4)
        line(d, [(CX - w, y - 4), (CX, y - 14), (CX + w, y - 4), (CX + w * 0.8, y + 26), (CX, y + 34), (CX - w * 0.8, y + 26), (CX - w, y - 4)], 6, dark)
    elif kind == "flat":
        line(d, [(CX - w * 0.7, y + 2), (CX, y + 5), (CX + w * 0.7, y + 2)], 7, dark)
    elif kind == "smirk":
        line(d, [(CX - w * 0.7, y + 6), (CX, y + 8), (CX + w * 0.8, y - 6)], 7, dark)
        line(d, [(CX + w * 0.8, y - 6), (CX + w * 0.95, y - 14)], 6, dark)
    elif kind == "soft":
        line(d, [(CX - w * 0.65, y), (CX - w * 0.2, y + 8), (CX + w * 0.2, y + 8), (CX + w * 0.65, y)], 6, dark)
    elif kind == "stitch":                                        # fusion: a thin line, not smiling, not crying
        line(d, [(CX - w, y + 2), (CX + w, y + 2)], 6, dark)
        for k in range(-3, 4):
            d.line((CX + k * w * 0.28, y - 8, CX + k * w * 0.28, y + 12), fill=dark, width=4)


def nose(img, p):
    d = ImageDraw.Draw(img)
    line(d, [(CX + 4, 500), (CX + 12, 530), (CX + 2, 540)], 5, shade(p["skin_sh"], 0.8) + (255,))
    m = mask_of(lambda dd: dd.ellipse((CX - 10, 520, CX + 8, 540), fill=255), 3)
    paint(img, m, p["skin_hi"], 0.5)


def blush(img, p, amount=1.0, clip=None):
    for sx in (-1, 1):
        m = mask_of(lambda d: d.ellipse((CX + sx * 120 - 52, 518, CX + sx * 120 + 52, 566), fill=255), 18)
        paint(img, m, p["blush"], 0.55 * amount, clip)


def scar(img, x, y, s, p, clip=None):
    """A burn scar: shiny, puckered, slightly paler pink with a darker rim."""
    rng = random.Random(7)
    pts = [(x + math.cos(a) * s * (0.7 + rng.random() * 0.5), y + math.sin(a) * s * 1.2 * (0.7 + rng.random() * 0.5)) for a in np.linspace(0, 6.283, 9)[:-1]]
    m = poly_mask(pts, blur=1.2)
    paint(img, m, (190, 100, 100), 0.85, clip)
    inner = poly_mask([(x + (px - x) * 0.6, y + (py - y) * 0.6) for px, py in pts], blur=3)
    paint(img, inner, (240, 170, 160), 0.7, clip)
    d = ImageDraw.Draw(img)
    for k in range(3):
        line(d, [(x - s * 0.5, y - s * 0.4 + k * s * 0.4), (x, y - s * 0.3 + k * s * 0.4), (x + s * 0.5, y - s * 0.5 + k * s * 0.4)], 3, (150, 70, 80, 200))


def lock(img, root, tip, width, col, hi, sh, bend=0.0, hl=True):
    """A pointed hair lock from `root` (x, y) to `tip` with a highlight streak."""
    (xr, yr), (xt, yt) = root, tip
    mx, my = (xr + xt) / 2 + bend, (yr + yt) / 2
    pts = [(xr - width / 2, yr), (mx - width * 0.55, my), (xt, yt), (mx + width * 0.5, my), (xr + width / 2, yr)]
    m = poly_mask(pts, closed=False)
    d = ImageDraw.Draw(img)
    paint(img, m, col)
    sm = mask_of(lambda dd: dd.polygon(spline([(xr + width * 0.1, yr), (mx + width * 0.3, my), (xt, yt), (mx + width * 0.5, my), (xr + width / 2, yr)], False), fill=255), 3)
    paint(img, sm, sh, 0.55, m)
    if hl:
        line(d, [(xr - width * 0.25, yr + 4), (mx - width * 0.15 + bend * 0.1, my), (xr * 0.2 + xt * 0.8 - width * 0.05, yr * 0.2 + yt * 0.8)], max(3, width * 0.11), mix(col, hi, 0.55) + (170,))
    return m


def smoke(img, x, y, rise, color, seed=1, strands=3, alpha=0.5):
    rng = random.Random(seed)
    for k in range(strands):
        pts, px, py, ph = [], x + k * 6, y, rng.random() * 6
        for i in range(14):
            px += math.sin(i * 0.6 + ph) * (9 + i * 1.4)
            py -= rise / 14
            pts.append((px, py))
        m = mask_of(lambda d: [d.line(pts, fill=255, width=int(7 + 16 * 1)) ], 14)
        paint(img, m, color, alpha * (1 - k * 0.25))


def streak_bg(img, p, kind, t=0.0, seed=1):
    """Background per character: green = forest glow + steam + fireflies, yellow = cold rain, red = fire + veins,
    mika = lake fog + moon, connor = candle room + sigil."""
    rng = random.Random(seed)
    grad(img, Image.new("L", (S, S), 255), p["bg_top"], p["bg_bot"], 0, S)
    d = ImageDraw.Draw(img)
    if kind == "green":
        for i in range(14):                                       # tree trunks in the dark
            x = rng.randint(0, S)
            m = mask_of(lambda dd: dd.rectangle((x, 0, x + rng.randint(30, 70), S), fill=255), 10)
            paint(img, m, (4, 18, 12), 0.7)
        glow(img, 130, 250, 340, (200, 130, 40), 0.55)            # the warm kitchen window
        m = mask_of(lambda dd: dd.rectangle((60, 150, 200, 330), fill=255), 2)
        paint(img, m, (255, 214, 130), 0.45)
        for k in (130,):
            d.line((k, 150, k, 330), fill=(60, 30, 10, 255), width=6)
            d.line((60, 240, 200, 240), fill=(60, 30, 10, 255), width=6)
        for i in range(34):
            x, y, r = rng.randint(0, S), rng.randint(60, 820), rng.randint(3, 8)
            glow(img, x, y, r * 5, (190, 255, 120), 0.5)
        smoke(img, 790, 800, 360, (210, 255, 220), seed + 3, 3, 0.25)   # steam from a cup
    elif kind == "yellow":
        for i in range(70):
            x, y, l = rng.randint(-100, S), rng.randint(-100, S), rng.randint(60, 220)
            d.line((x, y, x - l * 0.35, y + l), fill=mix(p["bg_bot"], p["glow"], rng.random() * 0.5) + (255,), width=rng.choice([2, 3, 4]))
        glow(img, 480, 380, 520, (200, 160, 30), 0.35)
        for k in range(5):                                        # a cracked mirror edge: cold sharp lines
            a = rng.random() * 6.28
            d.line((480, 400, 480 + math.cos(a) * 900, 400 + math.sin(a) * 900), fill=(255, 236, 140, 255), width=2)
    elif kind == "red":
        for i in range(9):                                        # flame silhouettes from below
            x = rng.randint(-40, S)
            h = rng.randint(300, 760)
            pts = [(x - 90, S), (x - 50, S - h * 0.55), (x - 10, S - h * 0.7), (x + 10, S - h), (x + 40, S - h * 0.6), (x + 90, S)]
            m = poly_mask(pts, blur=5)
            grad(img, m, (255, 120, 20), (150, 10, 10), S - h, S)
        glow(img, 480, 520, 560, (255, 60, 20), 0.35)
        for i in range(10):                                       # veins creeping in from the corners
            sx, sy = rng.choice([(0, 0), (S, 0), (0, S), (S, S)])
            pts, px, py = [(sx, sy)], sx, sy
            for k in range(14):
                px += (480 - px) * 0.08 + rng.randint(-34, 34)
                py += (440 - py) * 0.08 + rng.randint(-34, 34)
                pts.append((px, py))
            line(d, pts, rng.randint(3, 8), (130, 0, 10, 255), False)
        for i in range(60):
            x, y = rng.randint(0, S), rng.randint(0, S)
            d.ellipse((x, y, x + 5, y + 5), fill=(255, rng.randint(120, 220), 60, 255))
    elif kind == "mika":
        glow(img, 700, 170, 300, (160, 200, 230), 0.65)           # moon
        m = mask_of(lambda dd: dd.ellipse((650, 120, 750, 220), fill=255), 2)
        paint(img, m, (236, 244, 250), 0.9)
        d.rectangle((0, 620, S, S), fill=mix(p["bg_top"], p["bg_bot"], 0.6) + (255,))
        for i in range(24):                                       # moon path on the water
            y = 640 + i * 14
            d.line((700 - (30 + i * 3), y, 700 + (30 + i * 3), y), fill=(150, 190, 220, 255), width=3 if i % 2 else 2)
        for i in range(5):
            x0_, x1_ = rng.randint(-200, 400), rng.randint(600, 1200)
            m = mask_of(lambda dd: dd.ellipse((x0_, 520 + i * 70, x1_, 650 + i * 80), fill=255), 40)
            paint(img, m, (190, 210, 224), 0.28)
    else:  # connor
        for cx_, cy_ in ((120, 300), (850, 360), (800, 150)):
            glow(img, cx_, cy_, 220, (255, 160, 60), 0.7)
            d.rectangle((cx_ - 8, cy_, cx_ + 8, cy_ + 100), fill=(236, 220, 190, 255))
            glow(img, cx_, cy_ - 8, 40, (255, 220, 120), 1.2)
        for r in (360, 330):                                      # a faint sigil circle behind him
            d.ellipse((480 - r, 420 - r, 480 + r, 420 + r), outline=(130, 60, 40, 255), width=3)
        for k in range(8):
            a = k * math.pi / 4 + 0.2
            d.line((480 + math.cos(a) * 330, 420 + math.sin(a) * 330, 480 + math.cos(a + 2.4) * 330, 420 + math.sin(a + 2.4) * 330), fill=(110, 50, 36, 255), width=3)


# ------------------------------------------------------------------ the figures
def body_noah(img, p, breath=0, sway=0, kind="green", open_scarf=False):
    """Shoulders, neck (returns nothing). The scarf comes later because it sits on top of the head's chin."""
    by = breath
    sh = [(40, S + 20), (90, 860 + by), (230, 780 + by), (390, 752 + by), (570, 752 + by), (730, 780 + by), (870, 860 + by), (920, S + 20)]
    m = poly_mask(sh)
    grad(img, m, p["shirt"], shade(p["shirt"], 0.45), 760, S)
    rimm = mask_of(lambda d: line(d, sh[1:4], 8, 255, True), 3)
    paint(img, rimm, p["rim"], 0.5, m)
    neck = poly_mask([(430, 590), (428, 700 + by), (480, 770 + by), (532, 700 + by), (530, 590)])
    grad(img, neck, p["skin"], p["skin_sh"], 600, 720)
    return m


def scarf_noah(img, p, breath=0, sway=0, kind="green", tail=True):
    by = breath
    d = ImageDraw.Draw(img)
    band = poly_mask([(352, 700 + by), (410, 724 + by), (480, 734 + by), (550, 724 + by), (608, 700 + by), (650, 748 + by), (620, 812 + by), (480, 840 + by), (340, 812 + by), (310, 748 + by)])
    grad(img, band, p["scarf1"], shade(p["scarf1"], 0.62), 670, 840)
    for k in range(6):                                            # stripes following the wrap
        yy = 700 + k * 24 + by
        m = mask_of(lambda dd: line(dd, [(310 + k * 5, yy + 10), (480, yy + 36), (650 - k * 5, yy + 10)], 9, 255), 1)
        paint(img, m, p["scarf2"], 0.9, band)
    sm = mask_of(lambda dd: dd.polygon(spline([(330, 700 + by), (480, 760 + by), (630, 700 + by), (640, 840), (320, 840)]), fill=255), 22)
    paint(img, sm, (0, 0, 0), 0.35, band)
    for fx in (380, 440, 520, 580):                               # folds
        line(d, [(fx, 700 + by), (fx + (fx - 480) * 0.15, 750 + by), (fx + (fx - 480) * 0.2, 820 + by)], 4, shade(p["scarf1"], 0.5) + (180,))
    if tail:                                                      # the long end, swaying
        sx = sway
        pts = [(556, 770 + by), (640 + sx * 0.4, 800 + by), (690 + sx, 900), (700 + sx * 1.3, S), (604 + sx * 1.3, S), (590 + sx, 900), (540 + sx * 0.4, 830 + by)]
        tm = poly_mask(pts)
        grad(img, tm, p["scarf1"], shade(p["scarf1"], 0.55), 780, S)
        for k in range(5):
            yy = 850 + k * 34
            m = mask_of(lambda dd: dd.line([(560 + sx * 0.9, yy), (700 + sx * 1.2, yy + 18)], fill=255, width=14), 0)
            paint(img, m, p["scarf2"], 0.9, tm)
        for k in range(6):                                        # fringe
            xx = 604 + sx * 1.3 + k * 17
            d.line((xx, 940, xx - 2, S), fill=shade(p["scarf1"], 0.7) + (255,), width=4)


def head_noah(p, kind="green", eyes_open=1.0, look=(0, 0), mouth_kind="smile", brow_tilt=0, blush_amt=1.0, blood=False, wild=0.0, seed=2,
              slit=False, tears=False, tilt_brow=0.0):
    """The head on its own layer so it can nod, tilt and shake. Hair back, face, features, hair front."""
    L = new()
    d = ImageDraw.Draw(L)
    rng = random.Random(seed)
    hc, hs, hh = p["hair"], p["hair_sh"], p["hair_hi"]
    back = poly_mask([(300, 400), (296, 300), (330, 210), (420, 158), (540, 158), (632, 210), (668, 300), (664, 400), (660, 500), (610, 540), (350, 540), (300, 500)])
    grad(L, back, hc, hs, 160, 540)
    for i in range(7 + int(wild * 8)):                            # wild back locks stick out
        a = rng.uniform(math.pi * 1.05, math.pi * 1.95) if wild > 0 else rng.uniform(math.pi * 1.1, math.pi * 1.9)
        r = 260 + rng.random() * 70 * (1 + wild * 2)
        lock(L, (480 + math.cos(a) * 160, 400 + math.sin(a) * 180), (480 + math.cos(a) * r, 380 + math.sin(a) * r * 0.95), 54, hc, hh, hs, hl=False)
    fm = face_mask()
    grad(L, fm, p["skin_hi"], p["skin"], 210, 520, None)
    paint(L, mask_of(lambda dd: dd.ellipse((CX - 130, 380, CX + 130, 680), fill=0), 0), p["skin"], 0)   # no-op placeholder keeps order stable
    jaw = poly_mask([(332, 470), (356, 560), (414, 628), (480, 654), (546, 628), (604, 560), (628, 470), (700, 470), (700, 720), (260, 720), (260, 470)], blur=22)
    paint(L, ImageChops.invert(jaw), p["skin_sh"], 0.55, fm)
    side = mask_of(lambda dd: (dd.ellipse((290, 300, 360, 620), fill=255), dd.ellipse((600, 300, 670, 620), fill=255)), 28)
    paint(L, side, p["skin_sh"], 0.45, fm)
    chin = mask_of(lambda dd: dd.ellipse((CX - 70, 590, CX + 70, 670), fill=255), 16)
    paint(L, chin, p["skin_hi"], 0.25, fm)
    glow_m = mask_of(lambda dd: dd.ellipse((CX - 60, 440, CX + 60, 520), fill=255), 24)
    paint(L, glow_m, p["skin_hi"], 0.22, fm)
    blush(L, p, blush_amt, fm)
    for sx in (-1, 1):                                            # ears
        em = poly_mask([(CX + sx * 150, 430), (CX + sx * 186, 410), (CX + sx * 194, 470), (CX + sx * 164, 520), (CX + sx * 150, 500)])
        grad(L, em, p["skin"], p["skin_sh"], 410, 520)
    nose(L, p)
    eye_h = 112
    for sx in (-1, 1):
        eye(L, CX + sx * EYE_DX * 1.0 + sx * 0, EYE_Y, 96, eye_h, p, open_=eyes_open, look=look, slit=slit, flip=sx, ring=p.get("ring"))
        brow(L, CX + sx * EYE_DX, EYE_Y - 74 - (eyes_open < 0.7) * 4, 86, brow_tilt + tilt_brow * sx * 0, 11, shade(hc, 0.85), flip=sx)
    mouth(L, p, mouth_kind)
    if tears:
        for sx in (-1, 1):
            xx = CX + sx * EYE_DX * 1.0
            line(d, [(xx, EYE_Y + 50), (xx + sx * 6, 520), (xx + sx * 2, 600), (xx + sx * 8, 660)], 11, (150, 4, 12, 255))
            line(d, [(xx, EYE_Y + 50), (xx + sx * 6, 520), (xx + sx * 2, 600)], 4, (255, 60, 60, 255))
            d.ellipse((xx + sx * 8 - 9, 650, xx + sx * 8 + 9, 678), fill=(150, 4, 12, 255))
    if blood:
        for sx in (-1, 1):
            xx = CX + sx * EYE_DX
            m = mask_of(lambda dd: dd.ellipse((xx - 44, EYE_Y - 52, xx + 44, EYE_Y + 62), fill=255), 6)
            paint(L, m, (120, 0, 10), 0.28, fm)
    # --- hair front: bangs and side locks
    hairline = poly_mask([(318, 330), (330, 248), (420, 196), (540, 196), (630, 248), (642, 330), (600, 300), (560, 270), (500, 262), (440, 268), (380, 290)])
    paint(L, hairline, hc)
    paint(L, mask_of(lambda dd: dd.rectangle((300, 150, 660, 280), fill=255), 30), hs, 0.0)
    bang_defs = [(330, 250, 344, 520 + wild * 40, 64, -6), (386, 232, 398, 372 + wild * 6, 72, -4), (442, 226, 438, 382 + wild * 8, 64, 2),
                 (486, 224, 482, 446 + wild * 20, 38, 0), (524, 226, 536, 378 + wild * 8, 70, 6), (580, 232, 590, 368 + wild * 8, 70, 8),
                 (622, 250, 616, 520 + wild * 40, 62, 10)]
    for (rx_, ry_, tx_, ty_, w_, b_) in bang_defs:
        lock(L, (rx_, ry_), (tx_, ty_), w_, hc, hh, hs, bend=b_)
    for sx in (-1, 1):                                            # long side locks framing the cheeks
        for k in range(2):
            lock(L, (CX + sx * (150 + k * 12), 300 + k * 30), (CX + sx * (172 + k * 8 + wild * 30), 610 + k * 40 + wild * 50), 64 - k * 10, hc, hh, hs, bend=-sx * 10)
    lock(L, (470, 200), (430 - wild * 30, 112 - wild * 20), 28, hc, hh, hs, bend=-30)             # the ahoge
    lock(L, (500, 202), (560 + wild * 40, 124 - wild * 10), 22, hc, hh, hs, bend=26)
    if wild > 0:
        for i in range(5):
            a = rng.uniform(-0.9, 0.9)
            lock(L, (480 + a * 120, 214), (480 + a * 380, 60 + rng.random() * 40), 38, hc, hh, hs, bend=a * 40)
    sh = mask_of(lambda dd: dd.rectangle((330, 280, 640, 420), fill=255), 26)
    paint(L, sh, (0, 0, 0), 0.0)
    fs = mask_of(lambda dd: dd.polygon(spline([(340, 300), (400, 330), (480, 330), (560, 330), (620, 300), (620, 350), (480, 380), (340, 350)]), fill=255), 16)
    paint(L, fs, (0, 0, 0), 0.38, fm)                              # shadow of the fringe on the forehead
    return L


def hand(img, x, y, sc, ang, p, curl=0.0, col=None):
    """A simple big hand: palm + four fingers + thumb; `curl` 0 open .. 1 fist."""
    layer = new()
    d = ImageDraw.Draw(layer)
    c = col or p["skin"]
    palm = [(-60, -10), (-48, 70), (0, 96), (50, 70), (62, -10), (30, -40), (-30, -40)]
    d.polygon([(x + px * sc, y + py * sc) for px, py in palm], fill=c + (255,))
    for i, fx in enumerate((-48, -16, 16, 46)):
        ln = (96 + (14 if i in (1, 2) else 0)) * (1 - 0.55 * curl)
        pts = [(fx, -24), (fx + (i - 1.5) * 4 * (1 - curl), -24 - ln)]
        d.line([(x + a * sc, y + b * sc) for a, b in pts], fill=c + (255,), width=int(30 * sc))
        r = 15 * sc
        ex, ey = x + pts[1][0] * sc, y + pts[1][1] * sc
        d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=c + (255,))
        d.line([(x + fx * sc, y - 20 * sc), (x + fx * sc, y - 6 * sc)], fill=shade(c, 0.7) + (255,), width=max(2, int(3 * sc)))
    d.line([(x - 52 * sc, y + 20 * sc), (x - 100 * sc, y - 18 * sc * (1 - curl) - 6 * sc)], fill=c + (255,), width=int(30 * sc))
    sh = mask_of(lambda dd: dd.polygon([(x + px * sc, y + py * sc + 30 * sc) for px, py in palm], fill=255), 14)
    layer = layer.rotate(ang, center=(x, y), resample=Image.BICUBIC)
    img.alpha_composite(layer)


def cup(img, x, y, sc, ang, p):
    layer = new()
    d = ImageDraw.Draw(layer)
    d.polygon([(x - 56 * sc, y - 40 * sc), (x + 56 * sc, y - 40 * sc), (x + 40 * sc, y + 40 * sc), (x - 40 * sc, y + 40 * sc)], fill=(240, 232, 214, 255))
    d.ellipse((x - 56 * sc, y - 52 * sc, x + 56 * sc, y - 28 * sc), fill=(150, 90, 40, 255), outline=(250, 244, 230, 255), width=int(5 * sc))
    d.arc((x + 36 * sc, y - 26 * sc, x + 92 * sc, y + 24 * sc), -90, 90, fill=(240, 232, 214, 255), width=int(10 * sc))
    d.line((x - 50 * sc, y - 8 * sc, x + 46 * sc, y - 8 * sc), fill=p["scarf2"] + (255,), width=int(8 * sc))
    layer = layer.rotate(ang, center=(x, y), resample=Image.BICUBIC)
    img.alpha_composite(layer)


# ------------------------------------------------------------------ whole Noah
STATES = {  # per personality: look of the face
    "green": dict(eyes_open=1.0, mouth_kind="smile", brow_tilt=-6, blush_amt=1.0),
    "yellow": dict(eyes_open=0.62, mouth_kind="smirk", brow_tilt=8, blush_amt=0.2),
    "red": dict(eyes_open=1.12, mouth_kind="grit", brow_tilt=22, blush_amt=0.0, wild=1.0, slit=True, tears=True),
}


def noah_image(kind="green", *, bg=True, blink=0.0, breath=0, sway=0, dx=0, dy=0, tilt=0.0, mouth_kind=None, eyes_open=None, look=(0, 0),
               hand_pose=None, fx=None, t=0.0, scar_on=None, dim=1.0, seed=2, shut=False):
    p = PAL[kind]
    img = new((0, 0, 0, 255)) if bg else new()
    if bg:
        streak_bg(img, p, kind, t)
    body_noah(img, p, breath, sway, kind)
    st = dict(STATES[kind])
    if mouth_kind:
        st["mouth_kind"] = mouth_kind
    eo = st.pop("eyes_open") if eyes_open is None else (st.pop("eyes_open") and eyes_open)
    eo = eo * (1 - blink) if not shut else 0.03
    head = head_noah(p, eyes_open=max(0.04, eo), look=look, seed=seed, **st)
    head = rot(head, tilt, (480, 700), dx, dy + breath * 0.5)
    img.alpha_composite(head)
    if scar_on or (scar_on is None and kind == "red"):
        scar(img, 372, 700 + breath, 26, p)
    scarf_noah(img, p, breath, sway, kind)
    if hand_pose:
        hand_pose(img, p)
    if fx:
        fx(img, p)
    if dim < 1:
        img = Image.blend(Image.new("RGBA", (S, S), (0, 0, 0, 255)), img, dim)
    return img


def fusion_image(*, bg=True, breath=0, sway=0, dx=0, dy=0, tilt=0.0, glitch=0.0, seed=5, blink=0.0, shut=False, dim=1.0):
    """Phase 4: the three Noahs in one face - torn into jagged vertical bands, blood from the eyes."""
    rng = random.Random(seed)
    imgs = [noah_image(k, bg=False, breath=breath, sway=sway, dx=dx, dy=dy, tilt=tilt, blink=blink, shut=shut) for k in ("green", "yellow", "red")]
    p = PAL["red"]
    base = new((0, 0, 0, 255))
    if bg:
        streak_bg(base, dict(PAL["red"], bg_top=(6, 0, 8), bg_bot=(40, 6, 30)), "red", seed=9)
        d = ImageDraw.Draw(base)
        for i in range(2):                                        # the wall torn open: a black jagged rift behind him
            x = 150 + i * 650
            pts = [(x, 0)] + [(x + rng.randint(-70, 70), k * 70) for k in range(1, 14)] + [(x, S)]
            m = poly_mask(pts, closed=False)
            paint(base, m, (0, 0, 0), 0.0)
            line(d, pts, 10, (255, 230, 200, 255), False)
            line(d, pts, 4, (255, 40, 40, 255), False)
    cut1 = [(0, 0)] + [(440 + rng.randint(-14, 14), y) for y in range(0, S + 80, 80)] + [(0, S)]
    cut2 = [(S, 0)] + [(528 + rng.randint(-14, 14), y) for y in range(0, S + 80, 80)] + [(S, S)]
    m_green = mask_of(lambda dd: dd.polygon(cut1, fill=255))
    m_red = mask_of(lambda dd: dd.polygon(cut2, fill=255))
    base.alpha_composite(imgs[1])
    base.alpha_composite(Image.composite(imgs[0], new(), m_green))
    base.alpha_composite(Image.composite(imgs[2], new(), m_red))
    d = ImageDraw.Draw(base)
    for xs in (cut1[1:-1], cut2[1:-1]):                           # seams glow
        line(d, xs, 4, (255, 255, 255, 220), False)
    for sx in (-1, 1):                                            # blood from the eyes, stylised
        xx = CX + sx * EYE_DX + dx
        for w_, c in ((13, (120, 0, 8, 255)), (5, (255, 50, 50, 255))):
            line(d, [(xx, EYE_Y + 40 + dy), (xx + sx * 10, 530 + dy), (xx + sx * 2, 610 + dy), (xx + sx * 12, 700 + dy), (xx + sx * 8, 780 + dy)], w_, c)
    if glitch > 0:
        a = np.asarray(base.convert("RGB")).copy()
        for _ in range(int(glitch * 14)):
            y = rng.randint(0, S - 30)
            h_ = rng.randint(8, 50)
            a[y:y + h_] = np.roll(a[y:y + h_], rng.randint(-int(80 * glitch), int(80 * glitch)), axis=1)
        base = Image.fromarray(a, "RGB").convert("RGBA")
    if dim < 1:
        base = Image.blend(Image.new("RGBA", (S, S), (0, 0, 0, 255)), base, dim)
    return base


# ------------------------------------------------------------------ Mika and Connor
def mika_image(*, bg=True):
    p = PAL["mika"]
    img = new((0, 0, 0, 255))
    if bg:
        streak_bg(img, p, "mika")
    d = ImageDraw.Draw(img)
    sh = [(20, S + 20), (60, 880), (200, 800), (380, 764), (580, 764), (760, 800), (900, 880), (940, S + 20)]
    m = poly_mask(sh)
    grad(img, m, p["shirt"], shade(p["shirt"], 0.5), 770, S)
    for k in range(9):                                            # washed-out fabric streaks
        xx = 90 + k * 95
        line(d, [(xx, 800 + (abs(xx - 480) * 0.18)), (xx + 20, 900), (xx - 8, S)], 5, shade(p["shirt"], 0.7 + (k % 3) * 0.1) + (120,))
    hoodie = poly_mask([(260, 720), (330, 690), (480, 770), (630, 690), (700, 720), (730, 810), (620, 860), (480, 880), (340, 860), (230, 810)])
    grad(img, hoodie, shade(p["shirt"], 1.12), shade(p["shirt"], 0.6), 690, 880)
    line(d, [(250, 740), (330, 700), (480, 780), (630, 700), (710, 740)], 10, shade(p["shirt"], 0.5) + (255,))
    neck = poly_mask([(430, 590), (428, 720), (480, 770), (532, 720), (530, 590)])
    grad(img, neck, p["skin"], p["skin_sh"], 600, 740)
    for sx in (-1, 1):                                            # hoodie strings and the little metal tips
        line(d, [(480 + sx * 36, 790), (480 + sx * 44, 860), (480 + sx * 36, 940)], 7, (210, 214, 220, 255))
        d.ellipse((480 + sx * 36 - 8, 936, 480 + sx * 36 + 8, 968), fill=(120, 130, 140, 255))
    head = head_mika(p)
    img.alpha_composite(head)
    # hood pooled around the neck, in front of the chin line
    hood = poly_mask([(290, 680), (380, 720), (480, 740), (580, 720), (670, 680), (700, 760), (600, 800), (480, 810), (360, 800), (260, 760)])
    grad(img, hood, shade(p["shirt"], 1.2), shade(p["shirt"], 0.7), 690, 810)
    for fx_ in (360, 430, 530, 600):
        line(d, [(fx_, 720), (fx_ + (fx_ - 480) * 0.1, 770), (fx_ + (fx_ - 480) * 0.15, 800)], 4, shade(p["shirt"], 0.55) + (170,))
    # the cigarette: held in the right corner of the mouth, red ember, smoke rising across the face
    line(d, [(CX + 50, 590), (CX + 190, 560), (CX + 232, 552)], 15, (236, 232, 222, 255))
    line(d, [(CX + 228, 553), (CX + 246, 550)], 15, (255, 70, 30, 255))
    glow(img, CX + 252, 550, 60, (255, 70, 20), 1.2)
    smoke(img, CX + 258, 540, 380, (210, 226, 240), 3, 3, 0.55)
    return img


def head_mika(p):
    L = new()
    d = ImageDraw.Draw(L)
    rng = random.Random(11)
    hc, hs, hh = p["hair"], p["hair_sh"], p["hair_hi"]
    back = poly_mask([(296, 400), (292, 290), (340, 200), (440, 160), (560, 160), (640, 200), (668, 290), (664, 400), (676, 560), (600, 640), (360, 640), (284, 560)])
    grad(L, back, hc, hs, 160, 640)
    for i in range(10):                                           # messy, uncombed
        a = rng.uniform(math.pi * 1.0, math.pi * 2.0)
        lock(L, (480 + math.cos(a) * 170, 400 + math.sin(a) * 190), (480 + math.cos(a) * (310 + rng.random() * 80), 390 + math.sin(a) * (300 + rng.random() * 60)), 56, hc, hh, hs, hl=False)
    fm = face_mask()
    grad(L, fm, p["skin_hi"], p["skin"], 210, 520)
    jaw = poly_mask([(332, 470), (356, 560), (414, 628), (480, 654), (546, 628), (604, 560), (628, 470), (700, 470), (700, 720), (260, 720), (260, 470)], blur=22)
    paint(L, ImageChops.invert(jaw), p["skin_sh"], 0.55, fm)
    side = mask_of(lambda dd: (dd.ellipse((290, 300, 360, 620), fill=255), dd.ellipse((600, 300, 670, 620), fill=255)), 28)
    paint(L, side, p["skin_sh"], 0.45, fm)
    for sx in (-1, 1):
        em = poly_mask([(CX + sx * 150, 430), (CX + sx * 188, 410), (CX + sx * 196, 472), (CX + sx * 164, 522), (CX + sx * 150, 500)])
        grad(L, em, p["skin"], p["skin_sh"], 410, 520)
        bag = mask_of(lambda dd: dd.ellipse((CX + sx * EYE_DX - 50, EYE_Y + 28, CX + sx * EYE_DX + 50, EYE_Y + 76), fill=255), 10)
        paint(L, bag, (120, 90, 120), 0.35, fm)                   # heavy, sleepy eyes
    nose(L, p)
    for sx in (-1, 1):
        eye(L, CX + sx * EYE_DX, EYE_Y, 96, 112, p, open_=0.5, look=(0.5, 0.2), flip=sx, lash=0.8, ring=(90, 230, 255))
        e = mask_of(lambda dd: dd.rectangle((CX + sx * EYE_DX - 48, EYE_Y - 6, CX + sx * EYE_DX + 48, EYE_Y + 40), fill=255), 12)
        paint(L, e, (210, 40, 50), 0.12, fm)                      # bloodshot
        line(d, [(CX + sx * EYE_DX - 40, EYE_Y - 40), (CX + sx * EYE_DX, EYE_Y - 48), (CX + sx * EYE_DX + 40, EYE_Y - 40)], 10, shade(hc, 1.0) + (255,))
    mouth(L, p, "smirk", y=584, w=46)
    paint(L, poly_mask([(318, 330), (330, 248), (420, 196), (540, 196), (630, 248), (642, 330), (600, 300), (560, 270), (500, 262), (440, 268), (380, 290)]), hc)
    for i, (rx_, ry_, tx_, ty_, w_, b_) in enumerate([(326, 250, 356, 440, 80, -10), (392, 226, 410, 420, 90, -4), (452, 218, 500, 410, 90, 10),
                                                      (520, 220, 580, 430, 94, 12), (590, 236, 640, 470, 84, 14), (350, 230, 316, 330, 60, -26)]):
        lock(L, (rx_, ry_), (tx_, ty_), w_, hc, hh, hs, bend=b_)
    for sx in (-1, 1):
        lock(L, (CX + sx * 150, 300), (CX + sx * 176, 580), 66, hc, hh, hs, bend=-sx * 12)
    lock(L, (470, 200), (420, 110), 30, hc, hh, hs, bend=-30)
    fs = mask_of(lambda dd: dd.polygon(spline([(340, 300), (480, 330), (620, 300), (620, 350), (480, 380), (340, 350)]), fill=255), 16)
    paint(L, fs, (0, 0, 0), 0.35, fm)
    return L


def connor_image(*, bg=True):
    p = PAL["connor"]
    img = new((0, 0, 0, 255))
    if bg:
        streak_bg(img, p, "connor")
    d = ImageDraw.Draw(img)
    sh = [(0, S + 20), (40, 880), (200, 790), (380, 756), (580, 756), (760, 790), (920, 880), (S, S + 20)]
    m = poly_mask(sh)
    grad(img, m, (62, 52, 58), (22, 16, 22), 760, S)                     # the dark cardigan
    for k in range(14):                                           # knit texture
        xx = 40 + k * 66
        line(d, [(xx, 800 + abs(xx - 480) * 0.22), (xx + 10, 960)], 3, (96, 84, 90, 150), False)
    neck = poly_mask([(432, 590), (430, 720), (480, 770), (530, 720), (528, 590)])
    grad(img, neck, p["skin"], p["skin_sh"], 600, 740)
    shirt = poly_mask([(380, 740), (480, 700), (580, 740), (560, 960), (400, 960)])
    grad(img, shirt, (240, 236, 226), (176, 170, 164), 720, 960)
    for sx in (-1, 1):                                            # collar points
        c = poly_mask([(480, 720), (480 + sx * 90, 706), (480 + sx * 118, 790), (480 + sx * 20, 770)], closed=True)
        grad(img, c, (250, 246, 236), (196, 190, 184), 700, 800)
    cardi = [(380, 740), (400, 960), (330, 960), (240, 800)]
    for sx in (-1, 1):
        lap = poly_mask([(480 + sx * 90, 730), (480 + sx * 110, 960), (480 + sx * 230, 960), (480 + sx * 250, 800), (480 + sx * 200, 770)])
        grad(img, lap, (74, 62, 68), (30, 22, 28), 740, 960)
        line(d, [(480 + sx * 92, 730), (480 + sx * 110, 960)], 6, (16, 10, 14, 255), False)
    for k in range(3):
        yy = 790 + k * 72
        d.ellipse((470, yy, 490, yy + 20), fill=(190, 160, 100, 255))
    head = head_connor(p)
    img.alpha_composite(head)
    # iron key on a chain over the chest
    chain = [(380, 720), (410, 800), (450, 860), (480, 880), (510, 860), (550, 800), (580, 720)]
    for i in range(0, len(chain) - 1):
        line(d, [chain[i], chain[i + 1]], 5, (150, 150, 160, 255), False)
    for i, (cx_, cy_) in enumerate(spline(chain, False, 5)[::3]):
        d.ellipse((cx_ - 5, cy_ - 3, cx_ + 5, cy_ + 3), outline=(190, 190, 204, 255), width=2)
    kx, ky = 480, 890
    d.ellipse((kx - 26, ky - 8, kx + 26, ky + 44), outline=(120, 124, 136, 255), width=12)
    d.rectangle((kx - 8, ky + 40, kx + 8, ky + 160), fill=(110, 114, 126, 255))
    for k in range(3):
        d.rectangle((kx + 8, ky + 110 + k * 16, kx + 34, ky + 120 + k * 16), fill=(110, 114, 126, 255))
    d.line((kx - 20, ky - 2, kx + 14, ky - 2), fill=(200, 204, 216, 255), width=3)
    d.line((kx - 3, ky + 46, kx - 3, ky + 150), fill=(190, 194, 206, 255), width=3)
    # hands folded in front, at the bottom edge
    hand_l = poly_mask([(330, 960), (344, 900), (410, 880), (470, 900), (480, 960)])
    hand_r = poly_mask([(630, 960), (616, 900), (550, 880), (490, 900), (480, 960)])
    for hm_ in (hand_l, hand_r):
        grad(img, hm_, p["skin"], p["skin_sh"], 880, 960)
    for k in range(5):
        line(d, [(350 + k * 26, 912 + abs(k - 2) * 4), (362 + k * 24, 950)], 3, shade(p["skin_sh"], 0.8) + (255,), False)
        line(d, [(610 - k * 26, 912 + abs(k - 2) * 4), (598 - k * 24, 950)], 3, shade(p["skin_sh"], 0.8) + (255,), False)
    return img


def head_connor(p):
    L = new()
    hc, hs, hh = p["hair"], p["hair_sh"], p["hair_hi"]
    back = poly_mask([(322, 400), (318, 300), (350, 220), (430, 172), (540, 168), (622, 220), (650, 300), (646, 400), (640, 470), (330, 470)])
    grad(L, back, hc, hs, 160, 470)
    fm = face_mask()
    grad(L, fm, p["skin_hi"], p["skin"], 210, 520)
    jaw = poly_mask([(332, 470), (356, 560), (414, 628), (480, 654), (546, 628), (604, 560), (628, 470), (700, 470), (700, 720), (260, 720), (260, 470)], blur=22)
    paint(L, ImageChops.invert(jaw), p["skin_sh"], 0.55, fm)
    side = mask_of(lambda dd: (dd.ellipse((290, 300, 360, 620), fill=255), dd.ellipse((600, 300, 670, 620), fill=255)), 28)
    paint(L, side, p["skin_sh"], 0.4, fm)
    for sx in (-1, 1):
        em = poly_mask([(CX + sx * 150, 430), (CX + sx * 184, 410), (CX + sx * 190, 470), (CX + sx * 164, 520), (CX + sx * 150, 500)])
        grad(L, em, p["skin"], p["skin_sh"], 410, 520)
    d = ImageDraw.Draw(L)
    for sx in (-1, 1):                                            # soft crow's feet and nasolabial lines: kind, older
        line(d, [(CX + sx * 140, EYE_Y + 10), (CX + sx * 158, EYE_Y + 20)], 3, shade(p["skin_sh"], 0.8) + (200,))
        line(d, [(CX + sx * 60, 520), (CX + sx * 78, 570), (CX + sx * 70, 600)], 3, shade(p["skin_sh"], 0.8) + (130,))
    nose(L, p)
    for sx in (-1, 1):
        eye(L, CX + sx * EYE_DX, EYE_Y, 90, 90, p, open_=0.82, look=(0, 0.1), flip=sx, lash=0.55)
        brow(L, CX + sx * EYE_DX, EYE_Y - 68, 88, -5, 9, shade(hc, 0.75), flip=sx)
    mouth(L, p, "soft", y=580, w=40)
    # neat swept hair: one smooth mass, a parting on the left, long soft highlight swoops
    mass = poly_mask([(322, 440), (318, 330), (340, 250), (410, 196), (500, 178), (590, 200), (640, 260), (650, 340), (640, 440), (628, 360), (590, 310), (520, 290), (440, 300), (380, 340), (350, 400)])
    grad(L, mass, hc, hs, 180, 440)
    dd = ImageDraw.Draw(L)
    for k in range(9):
        y0 = 214 + k * 14
        line(dd, [(396 + k * 4, y0 + 40), (470, y0 - 8 + k), (560, y0 + 4 + k * 3), (630 - k * 3, y0 + 52 + k * 6)], 5, mix(hc, hh, 0.45) + (150,))
    for (rx_, ry_, tx_, ty_, w_, b_) in [(430, 214, 350, 330, 46, -20), (490, 196, 400, 300, 52, -30), (550, 204, 470, 292, 50, -34), (606, 226, 560, 306, 44, -30),
                                         (640, 280, 610, 356, 34, -10), (352, 250, 336, 380, 36, -6)]:
        lock(L, (rx_, ry_), (tx_, ty_), w_, hc, hh, hs, bend=b_)
    line(dd, [(404, 214), (392, 262), (368, 330)], 6, shade(hs, 0.7) + (255,))        # the parting
    line(dd, [(330, 340), (326, 420)], 18, mix(hc, hs, 0.4) + (255,))
    line(dd, [(632, 340), (638, 420)], 18, mix(hc, hs, 0.4) + (255,))
    fs = mask_of(lambda dd: dd.polygon(spline([(340, 290), (480, 310), (620, 290), (620, 340), (480, 360), (340, 340)]), fill=255), 16)
    paint(L, fs, (0, 0, 0), 0.3, fm)
    return L


# ------------------------------------------------------------------ pixel image -> coloured ASCII
RAMP = " .'`,:;-~=+*xo%#&@"
FLAT = 0.17
CROP = (140, 110, 820, 790)
EDGE = "|/-\\"


_GLYPHS = None
GLYPH_SET = " .,'`\"^:;~-_=+*<>/\\|()[]{}!?ilIoxcXO0#%&@$"


def glyph_bitmaps(cw=8, ch=16, size=14):
    """Every printable ASCII glyph as a cw x ch coverage mask (from the real font), so cells can be matched by SHAPE."""
    global _GLYPHS
    if _GLYPHS is None:
        font = ImageFont.truetype(FONT, size)
        arr = []
        for g in GLYPH_SET:
            im = Image.new("L", (cw, ch), 0)
            ImageDraw.Draw(im).text((0, ch - 4), g, fill=255, font=font, anchor="ls")
            arr.append(np.asarray(im, dtype=np.float32).reshape(-1) / 255.0)
        _GLYPHS = np.stack(arr)
    return _GLYPHS


def to_cells(im, cols, rows, lam=0.55, vivid=1.12, mono=False, fg_floor=0.0):
    """Shape matching: for every 8x16-pixel cell pick the ASCII glyph (and its fg/bg colours) that reproduces the pixels best.
    Returns rows of (glyph, fg rgb 0..255, bg rgb 0..255); with mono=True bg is black and only glyph + brightness matter."""
    a = np.asarray(im.convert("RGB").resize((cols * 8, rows * 16), Image.LANCZOS)).astype(np.float32) / 255.0
    C = a.reshape(rows, 16, cols, 8, 3).transpose(0, 2, 1, 3, 4).reshape(rows * cols, 128, 3)
    G = glyph_bitmaps()                                            # (n, 128)
    n_on = G.sum(axis=1)[None, :] + 1e-3                           # (1, n)
    n_off = 128 - n_on + 2e-3
    tot = C.sum(axis=1)                                            # (cells, 3)
    err = np.zeros((rows * cols, len(G)), dtype=np.float32)
    fgs, bgs = [], []
    for ch in range(3):
        on = C[:, :, ch] @ G.T                                     # ink-weighted sum (cells, n)
        fg = on / n_on
        bg = (tot[:, ch][:, None] - on) / n_off
        if mono:
            bg = np.zeros_like(bg)
        err += (C[:, :, ch] ** 2).sum(axis=1)[:, None] - 2 * fg * on - 2 * bg * (tot[:, ch][:, None] - on) + n_on * fg ** 2 + n_off * bg ** 2
        fgs.append(fg)
        bgs.append(bg)
    err += lam * (G.sum(axis=1)[None, :] / 128.0) * 2.0
    best = err.argmin(axis=1)
    out = []
    for r in range(rows):
        row = []
        for q in range(cols):
            k = r * cols + q
            b = best[k]
            f = np.array([fgs[c][k, b] for c in range(3)])
            bgc = np.array([bgs[c][k, b] for c in range(3)])
            m = (f + bgc) / 2
            if not mono:
                f, bgc = np.clip(m + (f - m) * vivid, 0, 1), np.clip(m + (bgc - m) * vivid, 0, 1)
            g = GLYPH_SET[b]
            if g == " ":
                f = bgc
            row.append((g, tuple(int(v * 255) for v in np.clip(f, 0, 1)), tuple(int(v * 255) for v in bgc)))
        out.append(row)
    return out


def to_mono_cells(im, cols, rows, lam=0.07):
    """Tone matching for the animations: white ink on black, the glyph whose coverage best matches the pixels (density = brightness)."""
    a = np.asarray(im.convert("L").resize((cols * 8, rows * 16), Image.LANCZOS)).astype(np.float32) / 255.0
    C = a.reshape(rows, 16, cols, 8).transpose(0, 2, 1, 3).reshape(rows * cols, 128)
    G = glyph_bitmaps()
    err = -2 * C @ G.T + (G ** 2).sum(axis=1)[None, :] + lam * G.sum(axis=1)[None, :]
    best = err.argmin(axis=1)
    peak = C.max(axis=1)
    out = []
    for r in range(rows):
        out.append([(GLYPH_SET[best[r * cols + q]], int(min(255, peak[r * cols + q] * 255)), 0) for q in range(cols)])
    return out


def pack_cells(cells):
    return {"w": len(cells[0]), "h": len(cells), "rows": ["".join(c[0] for c in r) for r in cells],
            "fg": ["".join("%02x%02x%02x" % c[1] for c in r) for r in cells], "bg": ["".join("%02x%02x%02x" % c[2] for c in r) for r in cells]}


def to_mono(im, cols, rows, gain=1.0):
    """Glyph-only frame for animations: brightness picks the glyph; colour comes from the personality when it is drawn."""
    a = np.asarray(im.convert("RGB").resize((cols * 4, rows * 8), Image.LANCZOS)).astype(np.float32) / 255.0
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])
    lum = np.clip(lum * 1.6, 0, 1) ** 0.75 * gain
    L = lum.reshape(rows, 8, cols, 4).mean(axis=(1, 3))
    gy, gx = np.gradient(L)
    mag = np.sqrt(gx ** 2 + gy ** 2)
    thr = np.percentile(mag, 94)
    rows_out = []
    for r in range(rows):
        s = []
        for c in range(cols):
            v = L[r, c]
            ch = RAMP[min(len(RAMP) - 1, int(v * len(RAMP)))] if v > 0.04 else " "
            if mag[r, c] > thr and v > 0.15:
                ang = math.degrees(math.atan2(gy[r, c], gx[r, c])) % 180
                ch = "|" if (ang < 22 or ang > 158) else ("-" if 68 < ang < 112 else ("/" if ang < 68 else "\\"))
            s.append(ch)
        rows_out.append("".join(s))
    return rows_out


def preview(cells, path, cell=(10, 20), size=17):
    font = ImageFont.truetype(FONT, size)
    img = Image.new("RGB", (len(cells[0]) * cell[0], len(cells) * cell[1]))
    d = ImageDraw.Draw(img)
    for y, row in enumerate(cells):
        for x, (g, f, b) in enumerate(row):
            d.rectangle((x * cell[0], y * cell[1], (x + 1) * cell[0], (y + 1) * cell[1]), fill=b)
            if g != " ":
                d.text((x * cell[0], y * cell[1] - 1), g, fill=f, font=font)
    img.save(path)


def preview_mono(frames, path, color, cell=(10, 20), size=17, per_row=6):
    font = ImageFont.truetype(FONT, size)
    h, w = len(frames[0]), len(frames[0][0])
    n = len(frames)
    rows_ = (n + per_row - 1) // per_row
    img = Image.new("RGB", (per_row * (w + 2) * cell[0], rows_ * (h + 1) * cell[1]))
    d = ImageDraw.Draw(img)
    for i, fr in enumerate(frames):
        ox, oy = (i % per_row) * (w + 2) * cell[0], (i // per_row) * (h + 1) * cell[1]
        for y, row in enumerate(fr):
            for x, g in enumerate(row):
                if g != " ":
                    k = RAMP.index(g) / len(RAMP) if g in RAMP else 0.6
                    col = tuple(int(c * (0.45 + 0.55 * min(1, k * 1.6))) for c in color)
                    d.text((ox + x * cell[0], oy + y * cell[1]), g, fill=col, font=font)
    img.save(path)


FIGURES = {"noah_green": lambda **k: noah_image("green", **k), "noah_yellow": lambda **k: noah_image("yellow", **k),
           "noah_red": lambda **k: noah_image("red", **k), "noah_fusion": lambda **k: fusion_image(**k),
           "mika": lambda **k: mika_image(**k), "connor": lambda **k: connor_image(**k)}
SIZES = {"big": (60, 30), "small": (30, 15)}


def finish(im):
    """Bloom + vignette + a touch of grain so the pixel painting survives the trip into glyphs."""
    rgb = im.convert("RGB")
    a = np.asarray(rgb).astype(np.float32)
    bl = np.asarray(rgb.filter(ImageFilter.GaussianBlur(22))).astype(np.float32)
    a = a + np.clip(bl - 90, 0, 255) * 0.35
    yy, xx = np.mgrid[0:S, 0:S]
    d = np.sqrt(((xx - S / 2) / (S / 2)) ** 2 + ((yy - S / 2) / (S / 2)) ** 2)
    a *= (1 - 0.45 * np.clip(d - 0.55, 0, 1) ** 1.3)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def build_portraits(names=None):
    os.makedirs(os.path.join(OUT, "previews"), exist_ok=True)
    data = {}
    for name, fn in FIGURES.items():
        if names and name not in names:
            continue
        im = finish(fn()).crop(CROP)
        im.convert("RGB").save(os.path.join(OUT, "previews", "src_%s.png" % name))
        data[name] = {}
        for key, (cols, rows) in SIZES.items():
            cells = to_cells(im, cols, rows)
            data[name][key] = pack_cells(cells)
            preview(cells, os.path.join(OUT, "previews", "portrait_%s_%s.png" % (name, key)), cell=(10, 20) if key == "big" else (16, 32), size=17 if key == "big" else 28)
        print("portrait", name)
    path = os.path.join(OUT, "portraits.json")
    if names and os.path.exists(path):
        old = json.load(open(path))
        old.update(data)
        data = old
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))


# ------------------------------------------------------------------ Noah's animation frames
ACROP = (90, 70, 870, 850)                                        # animation window: head, scarf, raised hands
ASIZES = {"big": (56, 28), "small": (28, 14)}
STATE_FRAMES = {"idle": 8, "windup": 3, "strike": 3, "hurt": 3, "collapse": 6}
LOOK = {"green": "green", "yellow": "yellow", "red": "red", "fusion": "red"}


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def attack_hand(kind, mode, prog):
    """The hand (and its prop) that winds up or strikes: a thrown teacup, a slamming palm, a clawing hand of fire."""
    def f(img, p):
        if mode == "windup":
            x, y, sc, ang = lerp((800, 800, 0.9, -8), (790, 560, 1.15, -24), prog)
        else:
            x, y, sc, ang = lerp((730, 600, 1.4, -8), (650, 560, 1.9, 0), prog)
        if kind == "green":
            cup(img, x - 10, y - 70 * sc, sc * (0.9 if mode == "windup" else 1.1), -25 + 40 * prog if mode == "strike" else -10, p)
            hand(img, x, y, sc, ang, p, curl=0.7 if mode == "windup" else 0.1)
            if mode == "strike":
                d = ImageDraw.Draw(img)
                rng = random.Random(3)
                for _ in range(26):                                # tea spray
                    px, py, r = x + rng.randint(-340, 100), y - rng.randint(60, 420), rng.randint(5, 14)
                    d.ellipse((px - r, py - r, px + r, py + r), fill=(190, 120, 50, 255))
        elif kind == "yellow":
            hand(img, x, y, sc, ang, p, curl=0.0)
            if mode == "strike":
                d = ImageDraw.Draw(img)
                for r in (140, 220, 300):
                    d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), outline=(255, 240, 160, 255), width=6)
        else:
            glow(img, x, y - 40, 130 * sc, (255, 70, 20), 0.7)
            hand(img, x, y, sc, ang, p, curl=0.45, col=(150, 60, 56) if mode == "strike" else None)
            d = ImageDraw.Draw(img)
            for k in range(3 if mode == "strike" else 1):
                line(d, [(x - 360 + k * 50, y - 280 + k * 40), (x - 80, y + 40 + k * 20), (x + 60, y + 200 + k * 30)], 14 - k * 3, (255, 200, 120, 255))
                line(d, [(x - 360 + k * 50, y - 280 + k * 40), (x - 80, y + 40 + k * 20), (x + 60, y + 200 + k * 30)], 5, (255, 40, 30, 255))
    return f


def speed_lines(kind, prog):
    col = {"green": (255, 220, 150), "yellow": (255, 244, 190), "red": (255, 90, 60), "fusion": (255, 255, 255)}[kind]

    def f(img, p):
        d = ImageDraw.Draw(img)
        rng = random.Random(4)
        for _ in range(30):
            a = rng.random() * 6.283
            r0, r1 = 300 + rng.random() * 120, 560 + rng.random() * 260
            d.line((480 + math.cos(a) * r0, 440 + math.sin(a) * r0 * 0.9, 480 + math.cos(a) * r1, 440 + math.sin(a) * r1 * 0.9), fill=col + (255,), width=rng.choice([3, 5, 8]))
    return f


def noah_frame(kind, state, i, n):
    """One animation frame (PIL image, black background): kind = green | yellow | red | fusion."""
    f = i / max(1, n - 1)
    kw = {}
    if state == "idle":
        a = 2 * math.pi * i / n
        kw = dict(breath=int(7 * math.sin(a)), sway=int(16 * math.sin(a + 1.2)), blink=[0, 0, 0, 0, 0, 0.5, 0.95, 0.4][i % 8], dy=int(2 * math.sin(a)))
    elif state == "windup":
        kw = dict(dy=int(14 * f), tilt=-3.5 * f, breath=int(4 * f), mouth_kind=None)
    elif state == "strike":
        kw = dict(dy=int(-18 + 4 * f), tilt=4 * (1 - f), breath=-4, sway=int(-40 + 30 * f))
    elif state == "hurt":
        kw = dict(dx=[-34, 22, -8][i % 3], tilt=[9, -5, 2][i % 3], dy=[10, 4, 0][i % 3], shut=i < 2, mouth_kind="open")
    elif state == "collapse":
        kw = dict(tilt=30 * f ** 0.8, dy=int(40 + 190 * f), breath=int(30 + 120 * f), sway=int(40 * f), shut=f > 0.3, mouth_kind="flat", dim=max(0.28, 1 - 0.7 * f ** 1.5))
    hf = attack_hand(kind if kind != "fusion" else "red", state, f) if state in ("windup", "strike") else None
    fxf = speed_lines(kind, f) if state == "strike" and i > 0 else None
    if kind == "fusion":
        k2 = {k: v for k, v in kw.items() if k in ("breath", "sway", "dx", "dy", "tilt", "blink", "shut", "dim")}
        im = fusion_image(bg=False, glitch=0.35 if state in ("strike", "hurt") else 0.08, seed=5 + i, **k2)
        if hf:
            hf(im, PAL["red"])
        if fxf:
            fxf(im, PAL["red"])
        return im
    return noah_image(kind, bg=False, hand_pose=hf, fx=fxf, **kw)


def morph_frame(a, b, i, n, seed=0):
    """Personality change: the next one tears through the old one in glitchy bands, then settles."""
    rng = random.Random(seed * 100 + i)
    ia, ib = noah_frame(a, "idle", 0, 8), noah_frame(b, "idle", 0, 8)
    f = (i + 1) / n
    out = np.asarray(ia.convert("RGB")).copy()
    nb = np.asarray(ib.convert("RGB"))
    band = 28
    for y in range(0, S, band):
        if rng.random() < f ** 1.2 * 1.1:
            sh = int(rng.randint(-120, 120) * (1 - f)) if f < 0.97 else 0
            out[y:y + band] = np.roll(nb[y:y + band], sh, axis=1)
        elif rng.random() < 0.3:
            out[y:y + band] = np.roll(out[y:y + band], rng.randint(-90, 90), axis=1)
    return Image.fromarray(out)


GAIN = {"green": 1.0, "yellow": 0.95, "red": 1.7, "fusion": 1.25}
TONES = (0.0, 0.14, 0.28, 0.48, 0.74, 1.0)


def tone(rgb):
    l = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0
    return sum(l > t for t in (0.05, 0.14, 0.27, 0.45, 0.68))


def anim_cells(im, size, kind="green"):
    """Colour shape matching like the portraits, then both colours of every cell become one of 6 tones of the personality colour
    (glyph + foreground tone + background tone): recognisable, and cheap to show with a handful of curses colour pairs."""
    cols, rows = ASIZES[size]
    a = np.asarray(im.convert("RGB").crop(ACROP)).astype(np.float32) / 255.0
    a = np.clip(a * GAIN[kind], 0, 1) ** 1.1
    cells = to_cells(Image.fromarray((a * 255).astype(np.uint8)), cols, rows, lam=0.5, vivid=1.3)
    return {"rows": ["".join(c[0] for c in r) for r in cells], "fg": ["".join(str(tone(c[1])) for c in r) for r in cells],
            "bg": ["".join(str(tone(c[2])) for c in r) for r in cells]}


def ImageOps_gray(im, gain=1.0):
    a = np.asarray(im).astype(np.float32) / 255.0 * gain
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    lum = np.clip((lum ** 1.15) * 0.9, 0, 0.8)
    g = Image.fromarray((np.stack([lum] * 3, axis=2) * 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(radius=9, percent=320, threshold=2))
    return g


def build_anim():
    data = {"big": {}, "small": {}, "morph": {"big": {}, "small": {}}}
    sheet = {}
    for kind in ("green", "yellow", "red", "fusion"):
        for size in data:
            if size != "morph":
                data[size][kind] = {}
        for state, n in STATE_FRAMES.items():
            frames = [noah_frame(kind, state, i, n) for i in range(n)]
            for size in ("big", "small"):
                data[size][kind][state] = [anim_cells(im, size, kind) for im in frames]
            sheet[(kind, state)] = [data["big"][kind][state][i]["rows"] for i in range(n)]
            print("anim", kind, state)
    for a, b in (("green", "yellow"), ("yellow", "red"), ("red", "fusion")):
        frames = [morph_frame(a, b, i, 8, seed=len(a)) for i in range(8)]
        for size in ("big", "small"):
            data["morph"][size]["%s-%s" % (a, b)] = [anim_cells(im, size, b) for im in frames]
        sheet[("morph", a + b)] = [data["morph"]["big"]["%s-%s" % (a, b)][i]["rows"] for i in range(8)]
        print("morph", a, b)
    os.makedirs(os.path.join(OUT, "previews"), exist_ok=True)
    with open(os.path.join(OUT, "noah_anim.json"), "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    cols = {"green": (110, 235, 140), "yellow": (240, 220, 80), "red": (255, 70, 60), "fusion": (255, 150, 150)}
    for (kind, state), frames in sheet.items():
        c = cols.get(kind, (240, 240, 240))
        preview_mono(frames, os.path.join(OUT, "previews", "anim_%s_%s.png" % (kind, state)), c, cell=(7, 14), size=12, per_row=4)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("portraits", "all"):
        build_portraits(sys.argv[2:] or None)
    if what in ("anim", "all"):
        build_anim()
    if what == "frame":                                              # quick look: python3 tools/portrait_art.py frame green strike 1
        k, st, i = sys.argv[2], sys.argv[3], int(sys.argv[4])
        im = noah_frame(k, st, i, STATE_FRAMES[st])
        bgim = Image.new("RGB", (S, S)); bgim.paste(im, (0, 0), im)
        bgim.save("/tmp/frame_src.png")
        cells = to_mono_cells(ImageOps_gray(bgim.crop(ACROP), GAIN[k]), 56, 28)
        cells = [[(g, (v, v, v), (0, 0, 0)) for g, v, _ in r] for r in cells]
        preview(cells, "/tmp/frame_ascii.png", cell=(10, 20), size=17)
