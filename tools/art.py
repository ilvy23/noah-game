"""tools/art.py - turns photos and painted scenes into dense coloured ASCII (art/<name>.json).

Run:  uv run --with pillow --with pillow-heif --with numpy python3 tools/art.py [name ...]
Each art file holds one grid per size: {"w":..,"h":..,"rows":[chars..],"rgb":[[r,g,b..]..]} for 'wide' and 'small'.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageFont, ImageDraw, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "art")
PHOTOS = os.path.expanduser("~/Pictures/folk-orte")
SIZES = {"ultra": (200, 30), "cred": (94, 34), "wide": (140, 35), "small": (90, 23), "tiny": (60, 15), "mini": (50, 12)}
RAMP = " .'`^,:;-~=+*xoO%#&@"


def load(name):
    im = ImageOps.exif_transpose(Image.open(os.path.join(PHOTOS, name))).convert("RGB")
    im.thumbnail((1800, 1800))
    return im


def crop_to(im, aspect, cx=0.5, cy=0.5):
    """Crop to width/height = aspect, centred at (cx, cy) as fractions."""
    w, h = im.size
    if w / h > aspect:
        nw = int(h * aspect)
        x = int(min(max(cx * w - nw / 2, 0), w - nw))
        return im.crop((x, 0, x + nw, h))
    nh = int(w / aspect)
    y = int(min(max(cy * h - nh / 2, 0), h - nh))
    return im.crop((0, y, w, y + nh))


def grade(im, dark=0.55, tint=(0.80, 0.92, 1.12), sat=0.85, contrast=1.35, vignette=0.55, gamma=1.0):
    a = np.asarray(im).astype(np.float32) / 255.0
    g = a.mean(axis=2, keepdims=True)
    a = g + (a - g) * sat
    a = np.clip((a - 0.5) * contrast + 0.5, 0, 1) ** (1.0 / gamma)
    a = a * dark * np.array(tint, dtype=np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    a = a * (1 - vignette * np.clip(d - 0.35, 0, 1) ** 1.4)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def night_sky(im, seed=3, stars=140, horizon=0.7, clouds=False):
    """Replace a blue daytime sky by a dark night sky with stars; everything else keeps its colours."""
    a = np.asarray(im).astype(np.float32) / 255.0
    h, w = a.shape[:2]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    yy = np.mgrid[0:h, 0:w][0]
    sky = ((b > r + 0.05) & (b > 0.42) & (yy < h * horizon))
    if clouds:                                                  # white clouds count as sky too
        sky = sky | ((lum > 0.5) & (g <= b + 0.08) & (yy < h * horizon))
    sky = sky.astype(np.float32)
    sky = np.asarray(Image.fromarray((sky * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255.0
    t = (np.mgrid[0:h, 0:w][0] / (h * 0.7)).clip(0, 1)[..., None]
    night = (1 - t) * np.array([0.02, 0.03, 0.10]) + t * np.array([0.10, 0.12, 0.28])
    rng = np.random.default_rng(seed)
    for _ in range(stars):
        y, x = int(rng.integers(0, int(h * 0.55))), int(rng.integers(0, w))
        night[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = rng.uniform(0.6, 1.0)
    a = a * (1 - sky[..., None]) + night * sky[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def to_ascii(im, cols, rows, edge_pct=92, gamma=1.45, blank=0.05, dither=0.05):
    """Pixel image -> rows of (char, rgb). Brightness picks the glyph density; only the strongest edges become / \\ | -."""
    im = im.resize((cols * 4, rows * 8), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    gy, gx = np.gradient(lum)

    def cells(x):
        return x.reshape(rows, 8, cols, 4)
    L = cells(lum).mean(axis=(1, 3))
    GX, GY = cells(gx).mean(axis=(1, 3)), cells(gy).mean(axis=(1, 3))
    M = np.sqrt(cells(gx ** 2 + gy ** 2).mean(axis=(1, 3)))
    COL = a.reshape(rows, 8, cols, 4, 3).mean(axis=(1, 3))   # rows, cols, 3
    lo, hi = np.percentile(L, 3), np.percentile(L, 99.5)
    Ln = np.clip((L - lo) / max(hi - lo, 1e-4), 0, 1) ** gamma
    Ln = np.clip(Ln + (np.random.default_rng(5).random(Ln.shape) - 0.5) * dither, 0, 1)      # grain: smooth skies stop looking like stripes
    thr = np.percentile(M, edge_pct)
    out = []
    ramp = " .:-=+*#%@"
    for r in range(rows):
        line = []
        for c in range(cols):
            l = Ln[r, c]
            ch = ramp[min(len(ramp) - 1, int(l * len(ramp)))]
            if M[r, c] > thr and l > 0.12:
                ang = math.degrees(math.atan2(GY[r, c], GX[r, c])) % 180
                ch = "|" if (ang < 22 or ang > 158) else ("-" if 68 < ang < 112 else ("/" if ang < 68 else "\\"))
            if l < blank:
                ch = " "
            col = COL[r, c]
            col = col.mean() + (col - col.mean()) * 1.7        # richer colours than the dark grade
            col = np.clip(col, 0.0, 1.0)
            k = min(3.0, max(1.0, 0.62 / max(float(col.max()), 1e-3)))
            line.append((ch, tuple(int(min(255, float(v) * k * 255)) for v in col)))
        out.append(line)
    return out


def pack(grid):
    return {"w": len(grid[0]), "h": len(grid),
            "rows": ["".join(c for c, _ in row) for row in grid],
            "rgb": [[v for _c, rgb in row for v in rgb] for row in grid]}


def preview(grid, path, cell=(9, 18), size=15):
    fonts = [f for f in (
        "/nix/store/0ll7yhrqgbkmb05wwya0vgjd7y4v2hq5-nerd-fonts-jetbrains-mono-3.4.0+2.304/share/fonts/truetype/NerdFonts/JetBrainsMono/JetBrainsMonoNerdFontMono-Bold.ttf",) if os.path.exists(f)]
    font = ImageFont.truetype(fonts[0], size) if fonts else ImageFont.load_default()
    w, h = len(grid[0]) * cell[0], len(grid) * cell[1]
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for y, row in enumerate(grid):
        for x, (ch, rgb) in enumerate(row):
            if ch != " ":
                d.text((x * cell[0], y * cell[1]), ch, fill=rgb, font=font)
    img.save(path)


def build(name, im, **opt):
    data = {}
    for key, (cols, rows) in SIZES.items():
        g = to_ascii(crop_to(im, cols / (rows * 2.0)), cols, rows, **opt)
        data[key] = pack(g)
        if key == "ultra":
            preview(g, os.path.join(OUT, name + ".png"), cell=(7, 14), size=12)
    with open(os.path.join(OUT, name + ".json"), "w") as fh:
        json.dump(data, fh, separators=(",", ":"))
    print("wrote", name)


W, H = 1120, 560


def _canvas(top, bottom):
    t = np.linspace(0, 1, H)[:, None, None]
    return (np.array(top, dtype=np.float32) * (1 - t) + np.array(bottom, dtype=np.float32) * t) * np.ones((H, W, 3), dtype=np.float32)


def _glow(a, x, y, r, color, k=1.0):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2) / r
    a += (np.exp(-d * d * 2.2) * k)[..., None] * np.array(color, dtype=np.float32)


def _fog(a, y0, y1, strength, seed, color=(0.55, 0.6, 0.7)):
    rng = np.random.default_rng(seed)
    n = Image.fromarray((rng.random((8, 20)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    n = np.asarray(n).astype(np.float32) / 255.0
    yy = np.mgrid[0:H, 0:W][0]
    band = np.clip(1 - np.abs((yy - (y0 + y1) / 2) / ((y1 - y0) / 2)), 0, 1)
    m = (n * band * strength)[..., None]
    a[:] = a * (1 - m) + np.array(color, dtype=np.float32) * m


def _stars(a, n, seed, ymax=0.5):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        y, x = int(rng.integers(0, int(H * ymax))), int(rng.integers(0, W))
        a[y:y + 2, x:x + 2] = rng.uniform(0.5, 1.0)


def _draw(a, fn):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    fn(ImageDraw.Draw(im))
    return np.asarray(im).astype(np.float32) / 255.0


def _tree(d, x, base, h, w, col):
    for i in range(7):
        t = i / 7
        d.polygon([(x - w * (1 - t) / 2, base - h * t), (x + w * (1 - t) / 2, base - h * t), (x, base - h * (t + 0.22))], fill=col)


def painted():
    P = {}
    # --- lake at night: moon, reflection, fog, far shore, bench and swing, a tiny red ember
    a = _canvas((0.01, 0.02, 0.07), (0.07, 0.10, 0.18)); _stars(a, 180, 1)
    _glow(a, 760, 120, 300, (0.35, 0.4, 0.55), 0.9); a[:] = np.clip(a, 0, 1)
    a[330:, :] = _canvas((0.03, 0.05, 0.10), (0.01, 0.02, 0.05))[330:, :]
    _glow(a, 760, 420, 120, (0.30, 0.34, 0.45), 0.5)
    def shore(d):
        d.ellipse((700, 70, 820, 190), fill=(215, 225, 245))
        d.polygon([(0, 332), (140, 300), (300, 318), (480, 296), (700, 322), (900, 300), (1120, 326), (1120, 340), (0, 340)], fill=(4, 8, 14))
        for x in range(0, 1120, 46):
            _tree(d, x + (x * 7) % 23, 330, 40 + (x * 13) % 34, 26, (3, 7, 12))
        d.rectangle((60, 470, 330, 478), fill=(8, 10, 14)); d.rectangle((70, 478, 76, 505), fill=(8, 10, 14)); d.rectangle((314, 478, 320, 505), fill=(8, 10, 14))
        d.rectangle((60, 448, 330, 455), fill=(8, 10, 14))
        d.line((920, 330, 920, 430), fill=(10, 12, 16), width=5); d.line((990, 330, 990, 430), fill=(10, 12, 16), width=5); d.line((912, 330, 998, 330), fill=(10, 12, 16), width=4)
        d.ellipse((294, 440, 302, 448), fill=(255, 60, 30))
    a = _draw(a, shore); _glow(a, 298, 444, 36, (1.0, 0.25, 0.08), 0.8)
    _fog(a, 300, 420, 0.65, 4); _fog(a, 440, 540, 0.45, 5)
    P["see"] = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # --- old house at night
    a = _canvas((0.01, 0.01, 0.05), (0.06, 0.07, 0.12)); _stars(a, 120, 2); _glow(a, 190, 100, 200, (0.3, 0.33, 0.45), 0.7)
    def house(d):
        d.rectangle((0, 470, W, H), fill=(5, 8, 8))
        d.rectangle((340, 250, 800, 480), fill=(16, 12, 12)); d.polygon([(310, 255), (570, 110), (830, 255)], fill=(10, 8, 9))
        d.rectangle((690, 120, 730, 230), fill=(12, 10, 11)); d.rectangle((530, 400, 610, 480), fill=(6, 4, 4))
        for x in (380, 470, 650, 730):
            d.rectangle((x, 290, x + 44, 360), fill=(10, 14, 22)); d.rectangle((x, 390, x + 44, 450), fill=(10, 14, 22))
        d.rectangle((476, 296, 512, 354), fill=(255, 190, 90)); d.line((494, 296, 494, 354), fill=(40, 20, 8), width=3)
        for x in (60, 170, 900, 1010):
            d.line((x, 480, x, 250), fill=(6, 6, 6), width=14)
            for k in range(7): d.line((x, 400 - k * 24, x + (-1) ** k * 70, 340 - k * 34), fill=(6, 6, 6), width=5)
    a = _draw(a, house); _glow(a, 494, 325, 90, (1.0, 0.6, 0.2), 0.9)
    rng = np.random.default_rng(7)
    for _ in range(260):
        x, y = int(rng.integers(0, W)), int(rng.integers(470, H))
        a[y:y + 4, x:x + 5] = [rng.uniform(0.5, 0.8), rng.uniform(0.2, 0.4), 0.05]
    _fog(a, 400, 520, 0.5, 8)
    P["haus"] = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # --- the Nook: a small wooden hut, warm windows, pines
    a = _canvas((0.01, 0.02, 0.05), (0.04, 0.06, 0.10)); _stars(a, 150, 3)
    def hut(d):
        d.rectangle((0, 470, W, H), fill=(5, 9, 7))
        for x in range(-20, W, 60):
            _tree(d, x + (x * 5) % 31, 480, 220 + (x * 11) % 90, 90, (4, 10, 9))
        d.rectangle((400, 330, 720, 480), fill=(34, 20, 12)); d.polygon([(380, 335), (560, 240), (740, 335)], fill=(18, 12, 9))
        d.rectangle((650, 200, 680, 290), fill=(22, 16, 14))
        for y in range(335, 480, 14): d.line((400, y, 720, y), fill=(24, 14, 8), width=2)
        d.rectangle((440, 370, 510, 430), fill=(255, 170, 70)); d.rectangle((610, 370, 680, 430), fill=(255, 150, 60)); d.rectangle((540, 400, 590, 480), fill=(20, 10, 6))
    a = _draw(a, hut); _glow(a, 475, 400, 110, (1.0, 0.55, 0.15), 1.0); _glow(a, 645, 400, 110, (1.0, 0.5, 0.12), 0.9)
    _glow(a, 665, 190, 40, (0.5, 0.5, 0.55), 0.5); _fog(a, 430, 540, 0.45, 9)
    P["nook"] = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # --- cellar: stone vault, steps and the cube
    a = _canvas((0.02, 0.02, 0.03), (0.03, 0.03, 0.04))
    def vault(d):
        for i, c in enumerate(((40, 38, 46), (28, 26, 34), (18, 17, 24), (10, 10, 14))):
            m = i * 90
            d.rectangle((60 + m, 40 + m // 2, 1060 - m, 560), fill=c)
            d.pieslice((60 + m, 40 + m // 2 - 300, 1060 - m, 560 - 300 + m // 2 + 400), 180, 360, fill=None, outline=(70, 68, 82), width=3)
        d.polygon([(0, 560), (200, 430), (920, 430), (1120, 560)], fill=(20, 19, 25))
        for y in range(440, 560, 20): d.line((0 + (y - 440) * 1.6, y, 1120 - (y - 440) * 1.6, y), fill=(32, 30, 38), width=2)
        d.line((560, 100, 560, 240), fill=(70, 60, 50), width=3)
    a = _draw(a, vault)
    for k, (x, y, rr, col) in enumerate(((560, 300, 90, (0.45, 0.10, 0.65)), (560, 300, 55, (0.2, 0.9, 0.95)), (560, 300, 28, (1.0, 1.0, 1.0)))):
        _glow(a, x, y, rr * 2.2, col, 0.9)
    def cube(d):
        for sz, col in ((60, (200, 245, 255)), (42, (120, 70, 190)), (26, (230, 255, 255))):
            d.rectangle((560 - sz, 300 - sz, 560 + sz, 300 + sz), outline=col, width=3)
        d.line((500, 240, 520, 260), fill=(200, 245, 255), width=3); d.line((620, 240, 600, 260), fill=(200, 245, 255), width=3)
        d.line((500, 360, 520, 340), fill=(200, 245, 255), width=3); d.line((620, 360, 600, 340), fill=(200, 245, 255), width=3)
    a = _draw(a, cube); _fog(a, 400, 540, 0.3, 11, (0.35, 0.3, 0.45))
    P["keller"] = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # --- Lünen at night: a street, lamps, lit windows, the church tower
    a = _canvas((0.01, 0.02, 0.06), (0.06, 0.07, 0.12)); _stars(a, 140, 12); _glow(a, 880, 90, 160, (0.3, 0.33, 0.45), 0.6)
    def town(d):
        d.polygon([(480, 300), (640, 300), (1120, 560), (0, 560)], fill=(20, 22, 30))
        for side in (-1, 1):
            for i in range(4):
                x0 = 480 + side * (30 + i * 110) if side < 0 else 640 + 30 + i * 110
                top = 150 + i * 28
                d.rectangle((x0 - 70 if side < 0 else x0, top, x0 if side < 0 else x0 + 70, 330 + i * 24), fill=(24, 20, 24))
        d.polygon([(470, 210), (560, 80), (650, 210)], fill=(22, 20, 28)); d.rectangle((520, 80, 600, 300), fill=(26, 24, 32)); d.polygon([(515, 85), (560, 10), (605, 85)], fill=(20, 18, 26))
        d.rectangle((548, 130, 572, 170), fill=(255, 190, 90))
        for x, y in ((330, 400), (790, 400), (180, 470), (940, 470)):
            d.line((x, y, x, y - 160), fill=(10, 10, 12), width=6)
            d.ellipse((x - 14, y - 178, x + 14, y - 150), fill=(255, 215, 130))
        for x in (90, 250, 380, 700, 840, 1010):
            d.rectangle((x, 250 + (x % 7) * 9, x + 26, 300 + (x % 7) * 9 + (x % 5) * 8), fill=(255, 190, 80))
    a = _draw(a, town)
    for x, y in ((330, 222), (790, 222), (180, 292), (940, 292)):
        _glow(a, x, y, 70, (1.0, 0.75, 0.35), 0.7)
    _fog(a, 380, 520, 0.6, 13); _fog(a, 260, 360, 0.3, 14)
    P["lunuen"] = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    # --- title: a huge moon over a valley of pines, the Nook light far below
    a = _canvas((0.0, 0.01, 0.05), (0.05, 0.07, 0.13)); _stars(a, 260, 15, 0.6); _glow(a, 560, 190, 330, (0.35, 0.4, 0.55), 0.9)
    def valley(d):
        d.ellipse((470, 100, 650, 280), fill=(225, 232, 248))
        d.polygon([(0, 560), (0, 400), (200, 330), (420, 380), (560, 340), (760, 390), (960, 320), (1120, 380), (1120, 560)], fill=(6, 10, 16))
        for x in range(-10, W, 34):
            _tree(d, x, 470 + (x * 7) % 40, 110 + (x * 13) % 80, 56, (3, 6, 10))
        d.rectangle((600, 470, 624, 490), fill=(255, 170, 70))
    a = _draw(a, valley); _glow(a, 612, 480, 60, (1.0, 0.55, 0.15), 0.9); _fog(a, 400, 520, 0.55, 16)
    P["title"] = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return P


def lake_dusk(path, sun_x=0.62):
    """The Cappenberger See (the user's photo lake-06: overcast sky, autumn forest, mirror water) as an autumn dusk, for the glyph pipeline: the grey sky is replaced by an
    indigo-to-rose gradient with a glow at the horizon (only above the tree line, found per column by position AND saturation/luminance), the forest crowns get local
    contrast, warm colour and lifted mid-tones so they stay readable as glyphs, the mirror gets a darker, calmer, violet-tinted copy of that sky under the reflections."""
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    im.thumbnail((1800, 1800))
    a = np.asarray(im).astype(np.float32) / 255.0
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    sat = (a.max(2) - a.min(2)) / (a.max(2) + 1e-3)
    wl = int(0.64 * h)                                                                      # the waterline of the far shore
    tree = (sat > 0.24) | (lum < 0.42)
    tree[wl:] = False
    first = np.where(tree.any(axis=0), tree.argmax(axis=0), wl)                              # per column: the first tree pixel from the top
    first = np.minimum(first, wl)
    kern = np.ones(31) / 31.0                                                                # smooth the edge so single dark pixels do not cut holes
    first = np.convolve(np.pad(first.astype(np.float32), 15, mode="edge"), kern, mode="valid")
    skym = (yy < first[None, :]).astype(np.float32)
    skym = np.asarray(Image.fromarray((skym * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.2)), dtype=np.float32) / 255.0
    # ---- the dusk sky
    ys = np.clip(yy / float(wl), 0, 1)
    top, mid, low = np.array([0.30, 0.22, 0.58]), np.array([0.62, 0.30, 0.52]), np.array([0.86, 0.52, 0.34])
    k = ys ** 1.6
    sky = np.where(k[..., None] < 0.55, top + (mid - top) * (k[..., None] / 0.55), mid + (low - mid) * ((k[..., None] - 0.55) / 0.45))
    cloud = np.clip((lum - lum[: int(0.3 * h)].mean()) * 2.4 + 0.95, 0.7, 1.3)[..., None]   # the overcast texture becomes lit clouds
    sky = sky * cloud * (0.62 + 0.30 * k[..., None])
    glow = np.exp(-((xx - sun_x * w) / (0.30 * w)) ** 2) * np.clip((yy - 0.45 * wl) / (0.55 * wl), 0, 1) ** 2
    sky = sky + glow[..., None] * np.array([0.30, 0.16, 0.05])
    # ---- the forest: local contrast, warm, lifted
    gimg = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    loc = np.asarray(gimg.filter(ImageFilter.UnsharpMask(radius=9, percent=170, threshold=2))).astype(np.float32) / 255.0
    g = loc.mean(axis=2, keepdims=True)
    forest = g + (loc - g) * 1.45
    forest = np.clip((forest - 0.5) * 1.35 + 0.5, 0, 1) ** 0.72
    forest = forest * np.array([1.12, 0.92, 0.74]) * 1.55                                      # darker than the glowing sky: the crowns stand against it as a silhouette with warm texture
    # ---- the mirror: darker, calmer, violet; the sky colour lies on it, the sun path glows
    mir = forest * np.array([0.70, 0.62, 0.86])
    ky = np.clip((yy - wl) / float(h - wl), 0, 1)
    skyref = top + (mid - top) * np.clip(1 - ky * 1.2, 0, 1)[..., None] * 0 + (low * 0.55 + mid * 0.45) * (1 - ky[..., None]) * 0.55 + mid * ky[..., None] * 0.30
    mir = mir * 0.62 + skyref * 0.36
    path = np.exp(-((xx - sun_x * w) / (0.05 * w + 0.22 * w * ky)) ** 2) * (1 - 0.5 * ky) * (yy > wl)
    mir = mir + path[..., None] * np.array([0.60, 0.30, 0.10])
    out = forest
    out = np.where((yy > wl)[..., None], mir, out)
    out = out * (1 - skym[..., None]) + sky * skym[..., None]
    out = np.clip(out, 0, 1)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    out = out * (1 - 0.35 * np.clip(d - 0.55, 0, 1) ** 1.4)[..., None]
    return Image.fromarray((out * 255).astype(np.uint8))


def scenes():
    """name -> pixel image (already graded)."""
    S = {}
    S["wald"] = grade(crop_to(load("IMG_0954.HEIC").filter(ImageFilter.UnsharpMask(radius=3, percent=220, threshold=2)), 2.0, 0.5, 0.45), dark=1.0, tint=(0.95, 1.0, 0.97), sat=1.1, contrast=1.3, vignette=0.35, gamma=1.0)
    S["schloss"] = grade(night_sky(crop_to(load("IMG_8110.HEIC"), 2.0, 0.5, 0.5)), dark=1.0, tint=(0.95, 1.0, 1.08), sat=1.1, contrast=1.3, vignette=0.35)
    S["see"] = lake_dusk(os.path.join(os.path.dirname(HERE), "docs", "ref", "lake", "lake-06.jpg"))      # the user's own photo of the lake, as an autumn dusk
    return S


OPTS = {"wald": dict(edge_pct=94), "see": dict(edge_pct=94), "see": dict(gamma=0.9, blank=0.015, edge_pct=97.5, dither=0.12), "haus": dict(gamma=0.75, blank=0.03, edge_pct=96.5, dither=0.16),
        "nook": dict(gamma=0.75, blank=0.03, edge_pct=96.5, dither=0.16), "keller": dict(gamma=0.8, blank=0.03, edge_pct=95, dither=0.14),
        "lunuen": dict(gamma=0.75, blank=0.03, edge_pct=96.5, dither=0.16), "title": dict(gamma=0.75, blank=0.03, edge_pct=96.5, dither=0.16)}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    S = scenes()
    for name in (sys.argv[1:] or list(S)):
        build(name, S[name], **OPTS.get(name, {}))
