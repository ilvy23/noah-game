"""credits.py - film credits: the text rises from the bottom of the screen to the top while the ending song plays.

Folk-horror palette (bone, moss, rust, ember, dusty gold, fog); ash, embers and fireflies drift in the margins while the
text column stays in the middle. No pictures: only the text, the song and the particles. The speed is never below MIN_SPEED lines per second; THE END stays until the song is over. Block order is random but
seedable; Enter only skips the held end card.
"""
import json
import math
import textwrap
import os
import random
import re
import shutil
import sys
import time


MIN_SPEED = 2.2          # lines per second: never slower than this, however long the song is
FONT = {"F": ["#####", "#    ", "#### ", "#    ", "#    "], "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
        "L": ["#    ", "#    ", "#    ", "#    ", "#####"], "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
        "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "], "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
        "E": ["#####", "#    ", "#### ", "#    ", "#####"], "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
        "D": ["#### ", "#   #", "#   #", "#   #", "#### "], " ": ["  ", "  ", "  ", "  ", "  "]}
PALETTE = (107, 179, 166, 109)        # moss, dusty gold, rust, fog grey-blue: titles cycle through these
BONE, PARCH, EMBER, FOG, MOSS = 230, 187, 208, 109, 107
BANNER = (166, 202, 208, 180, 230)    # rust -> ember -> dusty gold -> bone, one colour per banner row
TEXT_W = 50                           # the text column; the particles only drift in the margins left and right of it
def big(word):
    return ["  ".join(FONT[c][i] for c in word) for i in range(5)]


def music_block(sources_path):
    """'Music' block: 'filename - real name of the song' per track (soundtracks/SONGS.json, built from the files' tags)."""
    songs = {}
    try:
        with open(os.path.join(os.path.dirname(sources_path), "SONGS.json"), encoding="utf-8") as fh:
            songs = json.load(fh)
    except (OSError, ValueError):
        pass
    here = os.path.dirname(sources_path)
    songs = {k: v for k, v in songs.items() if os.path.isfile(os.path.join(here, k))}      # only the songs the player has put in
    if not songs:
        return None
    lines = ["Music hand picked by ilvy23", ""]
    lines += ["%s — %s" % (k, v) for k, v in sorted(songs.items())]
    return {"titel": "Music", "text": "\n".join(lines)}


def build_styled(blocks, seed=None):
    """-> ([(text, style)], rng). Styles: banner, title, name, body, dim, gap. First and last block keep their place."""
    rng = random.Random(seed)
    blocks = list(blocks)
    if len(blocks) > 3:
        mid = blocks[1:-1]
        rng.shuffle(mid)
        blocks = [blocks[0]] + mid + [blocks[-1]]
    out = [(l, "banner%d" % i) for i, l in enumerate(big("FOLK"))] + [("", "gap"), ("a folk-horror story in the valley", "dim"), ("", "gap"), ("", "gap"), ("", "gap")]
    for b in blocks:
        out += [("══  %s  ══" % b["titel"].upper(), "title"), ("", "gap")]
        for l in b["text"].split("\n"):
            dim = bool(re.search(r"\.(flac|mp3|wav)\s—", l))
            out.append((l, "dim" if dim else ("name" if len(b["text"].split("\n")) <= 3 else "body")))
        out += [("", "gap"), ("", "gap"), ("", "gap")]
    return out, rng


def build_lines(blocks, width=60, seed=None):
    styled, rng = build_styled(blocks, seed)
    return [t for t, _s in styled], rng


def speed_for(total_lines, seconds):
    return max(MIN_SPEED, total_lines / max(1.0, seconds))


def _color(style, progress, truecolor_ok=True):
    if style.startswith("sgr:"):
        return style[4:]
    pal = PALETTE[int(progress * len(PALETTE) * 2) % len(PALETTE)]
    if style.startswith("banner"):
        return "1;38;5;%d" % BANNER[int(style[6:])]
    return {"title": "1;38;5;%d" % pal, "name": "1;38;5;%d" % BONE, "body": "38;5;%d" % PARCH, "dim": "2;38;5;%d" % FOG,
            "gap": "0"}.get(style, "0")


def layout(width):
    """-> dict: tx0/tx1, the text column (the particles stay out of it)."""
    tx0 = max(0, (width - TEXT_W) // 2)
    return {"tx0": tx0, "tx1": min(width, tx0 + TEXT_W)}


def _particles(rng, width, height, lay):
    zones = [(0, lay["tx0"] - 3), (lay["tx1"] + 3, width)]
    zones = [z for z in zones if z[1] - z[0] > 1]
    out = []
    for _ in range(max(0, width * height // 300) if zones else 0):
        a, b = rng.choice(zones)
        out.append((rng.choice(("ash", "ash", "ember", "firefly")), rng.uniform(a, b - 1), rng.uniform(0, height),
                    rng.uniform(0.3, 1.0), rng.random() * 6.28))
    return out


def compose(rows, t, seconds, width, height, lay, parts):
    """rows: [(text, style)] per screen row -> grid of [char, sgr] cells. Order: particles, then text."""
    grid = [[[" ", None] for _ in range(width)] for _ in range(height)]
    tx0, tx1 = lay["tx0"], lay["tx1"]
    def masked(x, y):
        return tx0 - 2 <= x < tx1 + 2
    for kind, x0, y0, sp, ph in parts:
        if kind == "ash":
            x, y, ch, sg = x0 + 2 * math.sin(t * 0.4 + ph), (y0 + sp * t * 0.9) % height, ".,'"[int(ph * 10) % 3], "2;38;5;%d" % (241 if ph > 3 else 245)
        elif kind == "ember":
            x, y, ch = x0 + 1.5 * math.sin(t * 0.7 + ph), (y0 - sp * t * 0.7) % height, "'" if sp > 0.6 else "."
            sg = "38;5;%d" % (208 if math.sin(t * 3 + ph) > 0 else 166)
        else:
            x, y, ch = x0 + 4 * math.sin(t * 0.25 + ph), y0 + 2 * math.cos(t * 0.31 + ph * 2), "\u00b7"
            b = math.sin(t * 1.3 + ph)
            if b < -0.4:
                continue
            sg = "1;38;5;%d" % (179 if b > 0.4 else 107)
        x, y = int(x), int(y)
        if 0 <= x < width and 0 <= y < height and not masked(x, y):
            grid[y][x] = [ch, sg]
    for y, (text, style) in enumerate(rows):
        text = text.strip("\n")
        if style.startswith(("banner", "sgr:")):
            text = text.replace("#", "\u2588")                      # banner letters are drawn as solid blocks
        x0 = max(0, (width - len(text)) // 2)
        for i, ch in enumerate(text):
            if x0 + i < width:
                grid[y][x0 + i] = [ch, _color(style, t / max(1.0, seconds))]
    return grid


def _render(grid, prev=None):
    """Frame -> terminal bytes. The first frame (prev=None) is drawn whole; every later frame writes only the cells that
    changed since the previous one, so a 245x44 screen costs a few KB per frame instead of ~800 KB (which made terminals lag
    and tear)."""
    if prev is None or len(prev) != len(grid):
        lines = []
        for row in grid:
            parts, cur = [], None
            for ch, st in row:
                if st != cur:
                    parts.append("\033[0m" + ("\033[%sm" % st if st else ""))
                    cur = st
                parts.append(ch)
            lines.append("".join(parts) + "\033[0m")
        return "\033[H" + "\n".join(l + "\033[K" for l in lines)
    out = []
    for y, (row, old) in enumerate(zip(grid, prev)):
        n, x = len(row), 0
        while x < n:
            if row[x] == old[x]:
                x += 1
                continue
            seg, cur = ["\033[%d;%dH" % (y + 1, x + 1)], None
            while x < n and (row[x] != old[x] or (x + 1 < n and row[x + 1] != old[x + 1])):     # bridge one-cell gaps
                ch, st = row[x]
                if st != cur:
                    seg.append("\033[0m" + ("\033[%sm" % st if st else ""))
                    cur = st
                seg.append(ch)
                x += 1
            seg.append("\033[0m")
            out.append("".join(seg))
    return "".join(out)


def roll(blocks, seconds, out=None, height=None, width=None, seed=None, sleep=time.sleep, now=time.monotonic, fps=14, keys=None):
    """Scroll the credits for `seconds`. Returns the number of frames drawn."""
    out = out or sys.stdout
    size = shutil.get_terminal_size((80, 24))
    height = height or size.lines - 1
    width = width or size.columns
    styled, rng = build_styled(blocks, seed)
    lay = layout(width)
    wrap = min(TEXT_W, width)                               # a narrow text column keeps the particles in the margins: wrap the long lines
    styled = [(w, s) for t, s in styled for w in (textwrap.wrap(t, wrap) or [""] if s in ("title", "name", "body", "dim") and len(t) > wrap else [t])]
    total = len(styled) + height
    speed = speed_for(total, seconds)                       # lines per second
    pace = 1.0 + rng.uniform(-0.04, 0.04)                   # slight random pace
    parts = _particles(rng, width, height, lay)
    out.write("\033[?25l\033[2J")
    t0 = now()
    frames = 0

    last_grid = [None]

    def draw(rows, t):
        grid = compose(rows, t, seconds, width, height, lay, parts)
        grid = [[tuple(c) for c in r] for r in grid]
        out.write(_render(grid, last_grid[0]))
        last_grid[0] = grid
        out.flush()

    try:
        while True:
            el = now() - t0
            top = int(el * pace * speed)
            if top >= total:
                break
            rows = []
            for row in range(height):
                idx = row + top - height
                rows.append(styled[idx] if 0 <= idx < len(styled) else ("", "gap"))
            draw(rows, el)
            frames += 1
            sleep(1.0 / fps)
        # the roll is over: the end card fades in and stays until the song is over (Enter ends it earlier)
        card = big("THE END")
        mid = max(0, height // 2 - 4)
        fade = [236, 240, 244, 247, 250]
        k = 0
        while now() - t0 < seconds:
            if keys is not None and keys.read(timeout=1.0 / fps) in ("enter", " "):
                break
            if keys is None:
                sleep(1.0 / fps)
            f = k // 8                                      # fade level: grey ramp, then the ember-to-bone gradient
            rows = [("", "gap")] * mid + [(l, "sgr:1;38;5;%d" % (BANNER[i] if f >= 5 else fade[f])) for i, l in enumerate(card)]
            rows += [("", "gap"), ("thank you for staying.", "dim"), ("", "gap"), ("(=^.^=)", "sgr:38;5;%d" % MOSS)]
            draw(rows[:height], now() - t0)
            k += 1
    finally:
        out.write("\033[?25h\033[2J\033[H")
        out.flush()
    return frames
