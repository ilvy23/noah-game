"""ascii_art.py - shows the coloured ASCII pictures from art/<name>.json (made by tools/art.py).

The picture is picked by terminal size (wide 140x35, small 90x23, none if the window is too small) and graded by
chapter (night, grey day, dusk, cold, storm, false sun, dead). Truecolor is used when the terminal can do it.
"""
import json
import os
import shutil
import sys
import time

ART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art")
PLACE_ART = {"wald": "wald", "schloss": "schloss", "see": "see"}
# per chapter: (r, g, b multipliers, saturation, brightness)
GRADE = {1: ((0.72, 0.8, 1.0), 0.9, 0.85), 2: ((0.95, 1.0, 1.05), 0.45, 1.25), 3: ((1.15, 0.85, 1.15), 1.0, 0.95),
         4: ((0.85, 1.0, 1.25), 0.9, 1.2), 5: ((0.8, 1.05, 0.9), 0.8, 0.9), 6: ((1.4, 1.15, 0.7), 1.2, 1.3),
         7: ((1.15, 0.55, 0.55), 0.9, 0.8),
         8: ((1.1, 1.0, 0.85), 0.9, 1.05)}                 # 8 = credits: faded, bone-and-moss, folk-horror valley


def load(name):
    try:
        with open(os.path.join(ART_DIR, name + ".json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def pick_size(cols=None, lines=None):
    size = shutil.get_terminal_size((100, 40))
    cols, lines = cols or size.columns, lines or size.lines
    if cols >= 204 and lines >= 43:
        return "ultra"                                  # very wide windows get a long, panoramic picture
    if cols >= 142 and lines >= 51:
        return "wide"                                   # picture + a text block must fit on the screen together
    if cols >= 92 and lines >= 39:
        return "small"
    if cols >= 62 and lines >= 31:
        return "tiny"
    if cols >= 52 and lines >= 24:
        return "mini"
    return None


def grade(rgb, chapter):
    mul, sat, bright = GRADE.get(chapter, GRADE[1])
    r, g, b = rgb
    m = (r + g + b) / 3.0
    r, g, b = [m + (v - m) * sat for v in (r, g, b)]
    return tuple(int(max(0, min(255, v * k * bright))) for v, k in zip((r, g, b), mul))


def _256(r, g, b):
    return 16 + 36 * (r * 5 // 255) + 6 * (g * 5 // 255) + (b * 5 // 255)


def has_truecolor():
    """24-bit colour is assumed unless the terminal clearly cannot do it (FOLK_COLORS=256 forces the 256-colour fallback)."""
    forced = os.environ.get("FOLK_COLORS", "").lower()
    if forced in ("256", "8"):
        return False
    if forced in ("true", "truecolor", "24bit") or os.environ.get("COLORTERM", "") in ("truecolor", "24bit"):
        return True
    return os.environ.get("TERM", "") not in ("linux", "vt100", "vt220", "dumb", "screen", "")


def lines(name, chapter=1, size=None, truecolor=None, bg=0.40):
    """The picture as a list of ANSI strings, or [] when there is none / the window is too small."""
    data = load(name)
    size = size or pick_size()
    if not data or size not in data:
        return []
    truecolor = has_truecolor() if truecolor is None else truecolor
    g = data[size]
    out = []
    for y, row in enumerate(g["rows"]):
        px = g["rgb"][y]
        parts, last = [], None
        for x, ch in enumerate(row):
            if ch == " " and not bg:
                parts.append(" ")
                continue
            c = grade((px[3 * x], px[3 * x + 1], px[3 * x + 2]), chapter)
            if c != last:
                if truecolor:
                    parts.append("\033[38;2;%d;%d;%d;48;2;%d;%d;%dm" % (c + tuple(int(v * bg) for v in c)) if bg else "\033[38;2;%d;%d;%dm" % c)
                else:
                    parts.append("\033[38;5;%d;48;5;%dm" % (_256(*c), _256(*[int(v * bg) for v in c])) if bg else "\033[38;5;%dm" % _256(*c))
                last = c
            parts.append(ch)
        out.append("".join(parts) + "\033[0m")
    return out


def show(name, chapter=1, out=None, animate=True, size=None, truecolor=None, sleep=time.sleep):
    out = out or sys.stdout
    ls = lines(name, chapter, size, truecolor)
    for l in ls:
        out.write(l + "\n")
        if animate and ls:
            sleep(0.012)
    out.flush()
    return len(ls)


LETTERS = {"F": ["#####", "#    ", "#### ", "#    ", "#    "], "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
           "L": ["#    ", "#    ", "#    ", "#    ", "#####"], "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"]}


def banner(word="FOLK"):
    rows = ["  ".join(LETTERS[c][i] for c in word) for i in range(5)]
    return ["\033[1;35m%s\033[0m" % r.center(60) for r in rows]


def banner_sweep(out=None, sleep=time.sleep, frames=18):
    """The FOLK banner: a wave of colour runs over the letters once (only on a real terminal)."""
    out = out or sys.stdout
    pal = (53, 89, 125, 161, 197, 203, 209, 215, 221, 227, 193, 159, 123, 87, 51, 45, 39, 33)
    rows = ["  ".join(LETTERS[c][i] for c in "FOLK") for i in range(5)]
    for f in range(frames + 1):
        if f:
            out.write("\033[5A")
        for r in rows:
            cells = []
            for x, ch in enumerate(r.center(60)):
                col = pal[(x // 3 + f) % len(pal)] if ch != " " else 0
                cells.append("\033[1;38;5;%dm%s" % (col, ch) if ch != " " else " ")
            out.write("".join(cells) + "\033[0m\n")
        out.flush()
        sleep(0.05)
