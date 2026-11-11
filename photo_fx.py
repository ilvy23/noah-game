"""photo_fx.py - the baked reference photos (art/photos.json, made by tools/photo_cells.py) as half-block pixel pictures, and the big pixel font.

    image(name)                      -> (w, h, channels, bytes) at the stored resolution; "angel" and "aerial" are drawn by proc_art.py instead of read
    fit(name, w_px, h_px, crop=None) -> rows of (r, g, b[, a]) resampled (nearest/box) to w_px x h_px, optionally from a crop (x0, y0, x1, y1) in stored pixels
    paint(cv, px, x0, y0, grade=None)  one cell = two pixels (upper half-block): px is rows of (r, g, b[, a]); pixels with a < 0.5 leave the cell alone, soft alpha blends
    big_text(cv, text, x, y, colour, ...)  text in 14 px high (7 rows) pixel letters, deep red with a soft glow, optional per-letter jitter
Pure data and drawing; no input; everything clipped by Canvas.
"""
import base64
import json
import os
import zlib

import proc_art

HERE = os.path.dirname(os.path.abspath(__file__))
PROCEDURAL = ("angel", "aerial")                                   # proc_art.py draws these (they used to be third-party photos)
_data = {}
_px = {}


def _load():
    if not _data:
        try:
            with open(os.path.join(HERE, "art", "photos.json"), encoding="utf-8") as fh:
                _data.update(json.load(fh))
        except (OSError, ValueError):
            _data["_missing"] = True
    return _data


def has(name):
    return name in _load() or name in PROCEDURAL


def image(name):
    """(w, h, channels, bytes) of a stored picture, or None."""
    if name in _px:
        return _px[name]
    if name in PROCEDURAL and name not in _load():                             # drawn in code, not baked
        _px[name] = getattr(proc_art, name)()
        return _px[name]
    d = _load().get(name)
    if not d or "w" not in d:
        _px[name] = None
        return None
    key = "rgba" if "rgba" in d else "rgb"
    raw = zlib.decompress(base64.b64decode(d[key]))
    _px[name] = (d["w"], d["h"], 4 if key == "rgba" else 3, raw)
    return _px[name]


def _refl(v, n):
    v %= 2 * n
    return v if v < n else 2 * n - 1 - v


def fit(name, w_px, h_px, crop=None, reflect=False):
    """The picture resampled to w_px x h_px (nearest, from `crop` = (x0, y0, x1, y1) in stored pixels). Rows of tuples; alpha 0..1 as 4th value when stored."""
    im = image(name)
    if im is None:
        return [[(0, 0, 0)] * w_px for _ in range(h_px)]
    W, H, ch, raw = im
    x0, y0, x1, y1 = crop or (0, 0, W, H)
    kx, ky = max(1, min(3, int((x1 - x0) / float(w_px) + 0.5))), max(1, min(3, int((y1 - y0) / float(h_px) + 0.5)))      # shrinking: average a few samples (no aliasing)
    out = []
    for j in range(h_px):
        row = []
        for i in range(w_px):
            acc, n = [0, 0, 0, 0], 0
            for b in range(ky):
                sy = _refl(int(y0 + (j + (b + 0.5) / ky) * (y1 - y0) / float(h_px)), H) if reflect else min(H - 1, max(0, int(y0 + (j + (b + 0.5) / ky) * (y1 - y0) / float(h_px))))
                for a in range(kx):
                    sx = _refl(int(x0 + (i + (a + 0.5) / kx) * (x1 - x0) / float(w_px)), W) if reflect else min(W - 1, max(0, int(x0 + (i + (a + 0.5) / kx) * (x1 - x0) / float(w_px))))
                    k = (sy * W + sx) * ch
                    acc[0] += raw[k]; acc[1] += raw[k + 1]; acc[2] += raw[k + 2]
                    if ch == 4:
                        acc[3] += raw[k + 3]
                    n += 1
            row.append((acc[0] // n, acc[1] // n, acc[2] // n) if ch == 3 else (acc[0] // n, acc[1] // n, acc[2] // n, acc[3] / (255.0 * n)))
        out.append(row)
    return out


def paint(cv, px, x0, y0, grade=None):
    """Draw pixel rows as half-blocks at cell (x0, y0). grade(r, g, b, x, y) -> (r, g, b) lets a scene colour the photo (night, dusk, gold)."""
    for r in range(len(px) // 2):
        y = y0 + r
        if not 0 <= y < cv.h:
            continue
        top_row, bot_row = px[2 * r], px[2 * r + 1]
        for c in range(len(top_row)):
            x = x0 + c
            if not 0 <= x < cv.w:
                continue
            t, b = top_row[c], bot_row[c]
            ta = t[3] if len(t) > 3 else 1.0
            ba = b[3] if len(b) > 3 else 1.0
            if ta < 0.04 and ba < 0.04:
                continue
            tc = grade(t[0], t[1], t[2], x, 2 * r) if grade else t[:3]
            bc = grade(b[0], b[1], b[2], x, 2 * r + 1) if grade else b[:3]
            i = y * cv.w + x
            if ta < 0.98 or ba < 0.98:                                                 # a soft edge: blend with what is under it
                if cv.ch[i] == "▀":
                    ot, ob = cv.fg[i], cv.bg[i]
                else:
                    ot = ob = cv.bg[i]
                tc = tuple(ot[k] + (tc[k] - ot[k]) * ta for k in range(3))
                bc = tuple(ob[k] + (bc[k] - ob[k]) * ba for k in range(3))
            cv.ch[i], cv.fg[i], cv.bg[i] = "▀", tc, bc


def put_pixel(cv, x, ypx, colour):
    """One half-block pixel at cell column x, pixel row ypx (two per cell row); the other half of the cell keeps what it had."""
    x, ypx = int(x), int(ypx)
    y = ypx // 2
    if not (0 <= x < cv.w and 0 <= y < cv.h):
        return
    i = y * cv.w + x
    top, bot = (cv.fg[i], cv.bg[i]) if cv.ch[i] == "\u2580" else (cv.bg[i], cv.bg[i])
    if ypx % 2 == 0:
        top = colour
    else:
        bot = colour
    cv.ch[i], cv.fg[i], cv.bg[i] = "\u2580", top, bot


DROP = ("..#..", ".###.", "#####", "#####", ".###.", "..#..")


def teardrop(cv, x, ypx, light=1.0, scale=1):
    """A rounded tear (5 x 6 pixels, a glint at the upper left; scale 2 = a fat drop of 10 x 12) centred on cell column x, top pixel row ypx."""
    for r, row in enumerate(DROP):
        for c, v in enumerate(row):
            if v == "#":
                glint = (r == 2 and c == 1) or (r == 1 and c == 1)
                col = (255, 255, 255) if glint else ((170, 205, 235) if r < 4 else (110, 150, 200))
                col = tuple(int(v * light) for v in col)
                for dy in range(scale):
                    for dx in range(scale):
                        put_pixel(cv, x - 2 * scale + c * scale + dx, ypx + r * scale + dy, col)


def font_h():
    return (_load().get("font") or {}).get("h", 14)


def text_width(text):
    g = (_load().get("font") or {}).get("glyphs") or {}
    return sum(len((g.get(c) or g.get(" ") or ["..."])[0]) - 1 for c in text)


def wrap(text, width_cols):
    """Break a line into lines that fit width_cols big letters."""
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cur and text_width(trial) > width_cols:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [text]


def big_text(cv, text, x, y, colour=(200, 12, 16), alpha=1.0, glow=0.35, jitter=None, scale=1.0, hot=0.0):
    """Draw `text` in big pixel letters, cell (x, y) = top-left. Letters are 14 px = 7 rows high at scale 1 (smaller scales sample the font down); hot 0..1
    turns the letters white-hot. jitter(i) -> (dx, dy) in cells per letter. Returns (width, height) in cells."""
    g = (_load().get("font") or {}).get("glyphs") or {}
    if not g:
        return 0, 0
    s = max(0.2, min(1.0, scale))
    cx = 0
    hot_c = (255, 235, 210)
    for i, ch in enumerate(text):
        rows = g.get(ch) or g.get(" ")
        if rows is None:
            continue
        dx, dy = jitter(i) if jitter else (0, 0)
        w = len(rows[0])
        ow, oh = max(1, int(round(w * s))), max(2, int(round(len(rows) * s)))
        for r in range(0, oh, 2):
            for c in range(ow):
                sc = min(w - 1, int(c / s))
                top = rows[min(len(rows) - 1, int(r / s))][sc] == "#"
                bot = r + 1 < oh and rows[min(len(rows) - 1, int((r + 1) / s))][sc] == "#"
                if not (top or bot):
                    continue
                xx, yy = x + cx + c + dx, y + r // 2 + dy
                if not (0 <= xx < cv.w and 0 <= yy < cv.h):
                    continue
                k = yy * cv.w + xx
                base = tuple(int(v + (h_ - v) * hot) for v, h_ in zip(colour, hot_c))
                hi = tuple(int(v * alpha) for v in (min(255, base[0] + 40), base[1] + 6, base[2] + 6))
                lo = tuple(int(v * alpha) for v in base)
                under_t, under_b = (cv.fg[k], cv.bg[k]) if cv.ch[k] == "\u2580" else (cv.bg[k], cv.bg[k])
                cv.ch[k], cv.fg[k], cv.bg[k] = "\u2580", hi if top else under_t, lo if bot else under_b
                if glow:
                    for ddx, ddy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        cv.light(xx + ddx, yy + ddy, (colour[0], 0, 0), glow * 0.12 * alpha, 0.0)
        cx += max(1, int(round((w - 1) * s)))
    return cx, int(round(font_h() * s)) // 2


_fin = {}


def finish(cv, t, grain=0.04, vignette=0.45):
    """The last pass of a picture: a gentle vignette and a living film grain. The factors are tabulated once per size (6 noise patterns that cycle), which keeps this around 10 ms at 245x44."""
    w, h = cv.w, cv.h
    key = (w, h, grain, vignette)
    tabs = _fin.get(key)
    if tabs is None:
        tabs = []
        for p_ in range(6):
            tab = []
            for y in range(h):
                dy = (y + 0.5) / h - 0.5
                for x in range(w):
                    dx = (x + 0.5) / w - 0.5
                    v = 1.0 - vignette * min(1.0, (dx * dx * 2.2 + dy * dy * 3.0)) * 1.6
                    n = (((x * 73856093) ^ (y * 19349663) ^ (p_ * 83492791)) & 0xFF) / 255.0 - 0.5
                    tab.append(v * (1.0 + grain * 2.0 * n))
            tabs.append(tab)
        _fin[key] = tabs
    tab = tabs[int(t * 12) % 6]
    fg, bg = cv.fg, cv.bg
    for i in range(w * h):
        k = tab[i]
        f, b = fg[i], bg[i]
        fg[i] = (min(255, int(f[0] * k)), min(255, int(f[1] * k)), min(255, int(f[2] * k)))
        bg[i] = (min(255, int(b[0] * k)), min(255, int(b[1] * k)), min(255, int(b[2] * k)))
