"""tools/photo_cells.py - bakes the owner's own lake photos and the big red lyric fonts into art/photos.json (run once; the game only reads the json).

Run:  uv run --with pillow --with numpy python3 tools/photo_cells.py
    lake    the bench scene's backdrop, composited from docs/ref/lake/ (the owner's photos) and graded to an autumn dusk
    font    DejaVu Sans Condensed Bold, 14 px high bitmaps for the big lyric text
    font2   the heavy display lettering (Noto Serif Display)
The angel and the aerial valley are not baked: proc_art.py draws them in code.
Pixels are stored as zlib+base64 raw RGB(A) rows.
"""
import base64
import glob
import json
import os
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REF = os.path.join(ROOT, "docs", "ref")
OUT = os.path.join(ROOT, "art", "photos.json")


def pack(arr):
    return base64.b64encode(zlib.compress(arr.astype(np.uint8).tobytes(), 9)).decode("ascii")


def smooth(x, a, b):
    t = np.clip((x - a) / float(b - a), 0, 1)
    return t * t * (3 - 2 * t)


def font():
    f = ImageFont.truetype(glob.glob("/nix/store/*dejavu-fonts-2.37/share/fonts/truetype/DejaVuSansCondensed-Bold.ttf")[0], 15)
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,'!?-:;()\" "
    out = {}
    for c in chars:
        adv = int(round(f.getlength(c)))
        img = Image.new("L", (max(adv, 3) + 2, 18), 0)
        ImageDraw.Draw(img).text((1, 14), c, font=f, fill=255, anchor="ls")
        a = np.asarray(img) > 100
        rows = ["".join("#" if v else "." for v in r) for r in a[2:16]]
        out[c] = rows
    return {"h": 14, "glyphs": out}


def font2():
    """The heavy display lettering for the lyrics: Noto Serif Display at weight 900 (sharp wedge serifs), 28 px high bitmaps, strokes thickened by a pixel."""
    path = glob.glob("/nix/store/*noto-fonts-*/share/fonts/noto/NotoSerifDisplay.ttf")[0]
    f = ImageFont.truetype(path, 30)
    try:
        f.set_variation_by_axes([860])
    except Exception:
        pass
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,'!?-:;()\"& "
    out = {}
    for c in chars:
        adv = int(round(f.getlength(c)))
        img = Image.new("L", (max(adv, 4) + 6, 44), 0)
        ImageDraw.Draw(img).text((3, 32), c, font=f, fill=255, anchor="ls")
        img = img.resize((max(4, int(img.size[0] * 0.78)), img.size[1]), Image.LANCZOS)               # condensed: more letters per column
        a = np.asarray(img) > 100
        d = a.copy()
        rows = ["".join("#" if v else "." for v in r) for r in d[4:38]]
        out[c] = rows
    return {"h": 34, "glyphs": out}


def lake():
    """The bench scene's backdrop, composited from the user's real photos of the Cappenberger See (docs/ref/lake/): the wide lake and the autumn forest of lake-06 as the
    view, the golden reeds, the path and the white benches of lake-02 in front of it (reeds by colour, so the lake shows through their gaps), the overhanging branches
    of lake-02 at the left; then graded from a grey day to an autumn dusk (sunset sky from the cloud texture, the mirror water re-lit, warm forest, glowing reeds, cream
    benches). RGBA 704 x 396 (alpha: 255 water, 140 reeds, else 0) plus the bench's bounding box."""
    W, H = 704, 396
    DYA, DYB = 44, 32
    def load(n):
        im = Image.open(os.path.join(REF, "lake", "lake-%02d.jpg" % n)).convert("RGB")
        im.draft("RGB", (1400, 800))
        return np.asarray(im.resize((W, H), Image.LANCZOS), dtype=np.float32)
    def shift(img, dy):
        out = np.empty_like(img)
        if dy >= 0:
            out[dy:] = img[:H - dy]; out[:dy] = img[dy:0:-1] if dy else img[:0]
        else:
            out[:H + dy] = img[-dy:]; out[H + dy:] = img[-1:]
        return out
    A0, B0 = load(6), load(2)
    A, B = shift(A0, -DYA), shift(B0, DYB)
    yy, xx = np.mgrid[0:H, 0:W]
    fy, fx = yy / float(H), xx / float(W)
    def hsv(a):
        mx, mn = a.max(2), a.min(2)
        return mx / 255.0, (mx - mn) / (mx + 1e-3)
    vA, sA = hsv(A); vB, sB = hsv(B)
    r, g, b = B[..., 0], B[..., 1], B[..., 2]
    reed = ((r > g * 0.92) & (g > b * 1.25) & (sB > 0.30) & (vB > 0.35)).astype(np.float32)
    reed = np.asarray(Image.fromarray((reed * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.0)), dtype=np.float32) / 255.0
    reed *= np.clip((fy - 0.52) / 0.07, 0, 1) * (1.0 - 0.55 * smooth(fx, 0.55, 0.92))                     # the right side opens up to the lake
    gstart = 0.60 + DYB / float(H)
    ground = np.clip((fy - gstart) / 0.05, 0, 1)
    branch = ((fx < 0.32) & (fy < 0.52 + DYB / float(H)) & ((sB > 0.18) | (vB < 0.45))).astype(np.float32)
    branch = np.asarray(Image.fromarray((branch * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2)), dtype=np.float32) / 255.0
    keepB = np.maximum(ground, np.maximum(reed, branch * 0.95))
    C = A * (1 - keepB[..., None]) + B * keepB[..., None]
    # ---- classify, then grade
    horizon = int(0.495 * H) - DYA + 20                                                                      # the far shore's waterline in the composite (of lake-06 it is at ~0.5)
    sky_a = (sA < 0.22) & (vA > 0.5) & (yy < horizon + 4) & (keepB < 0.5)
    mirror_a = (sA < 0.20) & (vA > 0.42) & (yy >= horizon + 4) & (keepB < 0.5)
    out = np.zeros_like(C)
    stops = np.array([(0.0, 10, 8, 30), (0.25, 62, 36, 78), (0.5, 150, 70, 88), (0.72, 236, 118, 70), (0.9, 255, 184, 104), (1.0, 255, 238, 180)], dtype=np.float32)
    def ramp(k):
        k = np.clip(k, 0, 1)
        res = np.zeros(k.shape + (3,), dtype=np.float32)
        for i in range(len(stops) - 1):
            m = (k >= stops[i, 0]) & (k <= stops[i + 1, 0])
            t = ((k - stops[i, 0]) / (stops[i + 1, 0] - stops[i, 0]))[..., None]
            res = np.where(m[..., None], stops[i, 1:] * (1 - t) + stops[i + 1, 1:] * t, res)
        return res
    sunx = 0.62 * W
    ksky = np.clip(1.0 - (horizon - yy) / float(max(1, horizon)), 0, 1)
    cloud = np.clip(0.55 + (vA - 0.62) * 2.2, 0.45, 1.25)[..., None]
    skyc = ramp(0.14 + 0.84 * ksky ** 1.4) * cloud
    skyc += np.array([255, 170, 80], dtype=np.float32) * (0.55 * np.exp(-((xx - sunx) / 120.0) ** 2) * ksky ** 3)[..., None]
    kw = np.clip((yy - horizon) / float(H - horizon), 0, 1)
    mirc = ramp(0.14 + 0.82 * (1 - np.clip(kw * 1.4, 0, 1)) ** 1.4) * (0.55 + 0.9 * np.clip(vA - 0.4, 0, 1))[..., None]
    mirc += np.array([255, 176, 90], dtype=np.float32) * (0.8 * np.exp(-((xx - sunx - 30 * kw) / (30 + 80 * kw)) ** 2) * (1 - 0.3 * kw))[..., None]
    # vegetation and everything else: a warm dusk grade (dark, saturated, the sun on the tops)
    lum = (C[..., 0] * 0.3 + C[..., 1] * 0.59 + C[..., 2] * 0.11) / 255.0
    warm = ramp(0.55 + 0.35 * lum)
    veg = C * np.array([0.60, 0.46, 0.36], dtype=np.float32) * 0.9
    veg = veg * 0.62 + warm * (0.30 * (lum[..., None] ** 1.2))
    reedm = (reed > 0.35)[..., None]
    reedc = C * np.array([1.0, 0.78, 0.50], dtype=np.float32) * 0.85 + warm * 0.18
    gm = (ground > 0.5)[..., None]
    benchbox = (yy > 278) & (yy < 304) & (((xx > 150) & (xx < 276)) | ((xx > 336) & (xx < 482)))
    white = ((((vB > 0.80) & (sB < 0.14)) | ((vB > 0.56) & (sB < 0.18) & benchbox)) & (ground > 0.5))[..., None]
    gr = C * np.array([0.50, 0.50, 0.36], dtype=np.float32) * 0.8
    bench = np.array([255, 224, 188], dtype=np.float32) * (0.45 + 0.55 * lum)[..., None] + warm * 0.15
    path = C * np.array([0.84, 0.66, 0.56], dtype=np.float32) * 0.75
    isgray = (sB < 0.12)[..., None]
    out = veg
    out = np.where(reedm, reedc, out)
    out = np.where(gm, np.where(isgray, path, gr), out)
    out = np.where(white, bench, out)
    out = np.where(sky_a[..., None], skyc, out)
    out = np.where(mirror_a[..., None], mirc, out)
    wet = (yy >= horizon + 6) & (keepB < 0.3) & (yy < int(gstart * H) - 6)                                  # all of lake-06's water that the reeds, path and bank do not cover
    refl = C * np.array([0.42, 0.34, 0.34], dtype=np.float32) + warm * 0.10                                   # the forest's mirror image: dark, calm, a little blue-violet
    refl[..., 2] += 14
    wcol = np.where(mirror_a[..., None], mirc, refl)
    wcol = wcol * 0.55 + mirc * 0.55                                                                         # the sunset sky lies over everything on the mirror
    out = np.where(wet[..., None], wcol, out)
    out = np.clip(out, 0, 255)
    alpha = np.where(wet, 255, np.where(reed > 0.35, 140, np.where(sky_a, 60, 0))).astype(np.uint8)
    wb = np.where(white)
    box = [int(np.percentile(wb[1], 3)), int(np.percentile(wb[0], 3)), int(np.percentile(wb[1], 97)), int(np.percentile(wb[0], 97))] if len(wb[0]) else [0, 0, 1, 1]
    arr = np.dstack([out.astype(np.uint8), alpha])
    return {"w": W, "h": H, "rgba": pack(arr), "horizon": horizon, "white": [list(map(int, [np.where(white[..., 0])[1].min(), np.where(white[..., 0])[0].min(), np.where(white[..., 0])[1].max(), np.where(white[..., 0])[0].max()]))]}


def smooth(x, a, b):
    t = np.clip((x - a) / float(b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    data = {"font": font(), "font2": font2(), "lake": lake()}
    with open(OUT, "w") as fh:
        json.dump(data, fh)
    print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
