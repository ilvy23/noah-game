"""portraits.py - the character busts (art/portraits.json) and Noah's fight animation frames (art/noah_anim.json).

Both files are made by tools/portrait_art.py (pixel art drawn by code, converted to coloured ASCII by glyph shape matching).
    portrait(name, size)     - ANSI lines of a bust: name in PORTRAITS, size 'big' (60x30) or 'small' (30x15)
    pick_size(cols, lines)   - 'big' / 'small' / None for a window, leaving `reserve` lines for text under the picture
    anim_frame(kind, state, i, size) - one animation frame {'rows': [...], 'fg': [...], 'bg': [...]} (glyphs + foreground/background tones 0..5)
    fight_layout(w, h)       - where Noah's animation goes next to the 43-wide arena (never overlapping it), or None
"""
import json
import os

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art")
PORTRAITS = ("noah_green", "noah_yellow", "noah_red", "noah_fusion", "mika", "connor")
KINDS = ("green", "yellow", "red", "fusion")                       # Noah's personalities in order = fight phases 1..4
STATES = ("idle", "windup", "strike", "hurt", "collapse")
BIG, SMALL = (60, 30), (30, 15)
ANIM = {"big": (56, 28), "small": (28, 14)}
BASE = {"green": (90, 235, 120), "yellow": (245, 215, 70), "red": (255, 60, 60), "fusion": (255, 130, 130)}
ARENA_W = 41 + 2
GAP = 5                                                            # empty columns between the animation and the arena (the screen shakes by 3)
_cache = {}


def _load(name):
    if name not in _cache:
        try:
            with open(os.path.join(ART, name + ".json"), encoding="utf-8") as fh:
                _cache[name] = json.load(fh)
        except (OSError, ValueError):
            _cache[name] = {}
    return _cache[name]


def pick_size(cols, lines, reserve=10):
    """Portrait size for a window: big needs 60 columns and 30 + reserve lines, small 30 columns and 15 + reserve lines."""
    if cols >= BIG[0] + 4 and lines >= BIG[1] + reserve:
        return "big"
    if cols >= SMALL[0] + 4 and lines >= SMALL[1] + reserve:
        return "small"
    return None


def _256(r, g, b):
    return 16 + 36 * (r * 5 // 255) + 6 * (g * 5 // 255) + (b * 5 // 255)


def _sgr(fg, bg, truecolor):
    if truecolor:
        return "\033[38;2;%d;%d;%d;48;2;%d;%d;%dm" % (fg + bg)
    return "\033[38;5;%d;48;5;%dm" % (_256(*fg), _256(*bg))


def portrait(name, size="big", truecolor=True):
    """The bust as a list of ANSI strings (foreground + background colour per cell); [] when the art file is missing."""
    p = (_load("portraits").get(name) or {}).get(size)
    if not p:
        return []
    out = []
    for y, row in enumerate(p["rows"]):
        fg, bg = p["fg"][y], p["bg"][y]
        parts, last = [], None
        for x, ch in enumerate(row):
            f = (int(fg[6 * x:6 * x + 2], 16), int(fg[6 * x + 2:6 * x + 4], 16), int(fg[6 * x + 4:6 * x + 6], 16))
            b = (int(bg[6 * x:6 * x + 2], 16), int(bg[6 * x + 2:6 * x + 4], 16), int(bg[6 * x + 4:6 * x + 6], 16))
            if ch == " ":
                f = b
            if (f, b) != last:
                parts.append(_sgr(f, b, truecolor))
                last = (f, b)
            parts.append(ch)
        out.append("".join(parts) + "\033[0m")
    return out


def has_art():
    return bool(_load("portraits")) and bool(_load("noah_anim"))


def frame_count(kind, state):
    return len(_load("noah_anim").get("big", {}).get(kind, {}).get(state, ())) or 1


def anim_frame(kind, state, i, size="big"):
    """Frame i (wraps around) of a state; None when the animation file is missing."""
    fr = _load("noah_anim").get(size, {}).get(kind, {}).get(state)
    return fr[i % len(fr)] if fr else None


def morph_frame(old, new, i, size="big"):
    """Personality change frames (old -> new, i 0..7)."""
    fr = _load("noah_anim").get("morph", {}).get(size, {}).get("%s-%s" % (old, new))
    return fr[min(i, len(fr) - 1)] if fr else None


TONES = (0.0, 0.14, 0.28, 0.48, 0.74, 1.0)


def band(kind, x, w):
    """Colour of a column: the personality, or for the fusion three bands (green | yellow | red)."""
    return ("green" if x < w * 0.4 else "yellow" if x < w * 0.6 else "red") if kind == "fusion" else kind


def tone_rgb(kind, t):
    return tuple(int(v * TONES[t]) for v in BASE[kind])


def anim_ansi(frame, kind, truecolor=True):
    """A frame as ANSI lines: glyph + foreground tone on a background tone of the personality colour (every cell opaque)."""
    out = []
    for rows, fg, bg in zip(frame["rows"], frame["fg"], frame["bg"]):
        parts, last, w = [], None, len(rows)
        for x, ch in enumerate(rows):
            k = band(kind, x, w)
            f, b = tone_rgb(k, int(fg[x])), tone_rgb(k, int(bg[x]))
            if (f, b) != last:
                parts.append(_sgr(f, b, truecolor))
                last = (f, b)
            parts.append(ch)
        out.append("".join(parts) + "\033[0m")
    return out


def fight_layout(w, h, art_h_needed=None):
    """Where Noah's animation goes in the fight screen: dict(size, x, y, w, h) left of the arena, or None when there is no room.
    The arena column sits at ox = (w - 43) // 2; the art ends GAP columns before it and never overlaps rows or columns of the arena."""
    ox = max(0, (w - ARENA_W) // 2)
    for size in ("big", "small"):
        aw, ah = ANIM[size]
        if ox - GAP - aw >= 1 and h >= ah + 3:
            return dict(size=size, x=ox - GAP - aw, y=1, w=aw, h=ah)
    return None
