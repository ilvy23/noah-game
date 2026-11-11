"""speech.py - speech bubbles drawn ON a running animation (the Mika ending never drops to a bare terminal).

    run_dialog(ctx, scene_factory, boxes, t0=0.0, span=2.0, seed=1)
        boxes = [(who, text, anchor)]; anchor = (fx, fy) fractions of the screen where the speaker is (the bubble sits above it with a pointer),
        or None for a bar at the bottom (narration). Each box is a rounded bordered box in the speaker's colour, typed with the speaker's voice blips;
        Enter finishes the typing, the next Enter goes on. The scene keeps animating behind it: its time t0 .. t0 + span runs back and forth.
        Without a keyboard (tests, pipes) every box stays for a short, text-length dependent time and moves on by itself.
Layout: terminals >= 160 columns get a column at the RIGHT edge (dim backing, bordered bubbles, name tag, a pointer line toward the speaker's side, older
bubbles above the newest, fading); narrower ones a strip at the bottom. The middle of the picture is never covered.
Pure drawing on a noah_gore_fx.Canvas; nothing is printed outside the frame loop; the cursor is hidden while it runs.
"""
import chain
import textwrap
import time

import noah_gore_fx as G

COLORS = {"mika": (90, 235, 200), "noah": (255, 125, 105), "noah2": (255, 125, 105), "noah3": (255, 70, 60), "connor": (240, 200, 120),
          "narrator": (214, 218, 224), "system": (90, 235, 255), "tesseract": (120, 200, 255)}
NAMES = {"mika": "MIKA", "noah": "NOAH", "noah2": "NOAH", "noah3": "NOAH", "connor": "CONNOR", "system": "", "narrator": "", "tesseract": "THE CUBE"}
CPS = 32.0                                         # typed characters per second
BG = (8, 10, 16)


def pingpong(x, span):
    """x runs up for ever; the result runs 0..span..0..span ..."""
    if span <= 0:
        return 0.0
    m = x % (2 * span)
    return m if m <= span else 2 * span - m


PANEL_MIN_COLS = 160                               # from this width the speech lives in a column at the RIGHT edge; narrower terminals get a bottom strip
HISTORY = 3                                        # older bubbles stay above the current one, fading


def panel_width(w):
    return max(44, min(50, w // 5))


def layout(w, h, who, text, anchor):
    """(x, y, box_w, lines, pointer_tip_x or None). Wide terminal: a panel at the right edge, the newest bubble at its bottom, the pointer line leaving
    its left side toward the speaker. Narrow terminal: a strip at the bottom. Nothing here ever covers the middle of the frame."""
    if w >= PANEL_MIN_COLS:
        bw = panel_width(w)
        lines = textwrap.wrap(text, bw - 4) or [""]
        bh = len(lines) + 2
        x = w - bw - 1
        return x, max(1, h - bh - 2), bw, lines, (x - 4 if anchor else None)
    bw = max(24, min(w - 6, 100))
    lines = textwrap.wrap(text, bw - 4) or [""]
    bh = len(lines) + 2
    return max(1, (w - bw) // 2), max(1, h - bh - 1), bw, lines, None


def _back(cv, x, y, bw, bh, a=0.8):
    """A semi-transparent dark backing: what is behind shines through a little."""
    for yy in range(y, y + bh):
        for xx in range(x, x + bw):
            if 0 <= xx < cv.w and 0 <= yy < cv.h:
                i = yy * cv.w + xx
                cv.bg[i] = G.mix(cv.bg[i], BG, a)
                cv.ch[i] = " "


def _one(cv, who, lines, shown, x, y, bw, col, text_col, tag=True):
    bh = len(lines) + 2
    _back(cv, x, y, bw, bh)
    name = NAMES.get(who, "") if tag else ""
    top = "╭" + (("─ %s " % name) if name else "─").ljust(bw - 2, "─") + "╮"
    cv.text(x, y, top, col)
    cv.text(x, y + bh - 1, "╰" + "─" * (bw - 2) + "╯", col)
    for r in range(1, bh - 1):
        cv.put(x, y + r, "│", col)
        cv.put(x + bw - 1, y + r, "│", col)
    left = shown
    for r, l in enumerate(lines):
        cv.text(x + 2, y + 1 + r, l[:max(0, left)], text_col)
        left -= len(l) + 1
    return bh


def draw_bubble(cv, who, text, shown, anchor, t, history=()):
    col = COLORS.get(who, COLORS["narrator"])
    x, y, bw, lines, px = layout(cv.w, cv.h, who, text, anchor)
    wide = cv.w >= PANEL_MIN_COLS
    if wide:                                                       # the panel: a dim column behind everything, older bubbles above the newest
        for yy in range(1, cv.h - 1):
            for xx in range(x - 1, cv.w):
                i = yy * cv.w + xx
                cv.bg[i] = G.mul(cv.bg[i], 0.55)
                cv.fg[i] = G.mul(cv.fg[i], 0.55)
        top = y
        for k, (hw, ht) in enumerate(reversed(list(history)[-HISTORY:])):
            hl = textwrap.wrap(ht, bw - 4) or [""]
            hy = top - len(hl) - 3
            if hy < 1:
                break
            f = (0.62, 0.42, 0.28)[k]
            _one(cv, hw, hl, 10 ** 6, x, hy, bw, G.mul(COLORS.get(hw, COLORS["narrator"]), f), G.mul((240, 240, 245), f))
            top = hy
    bh = _one(cv, who, lines, shown, x, y, bw, col, (240, 240, 245) if who != "noah3" else (255, 130, 120))
    if px is not None:                                             # the pointer line leaves the panel toward the speaker's side
        yy = y + bh // 2
        cv.put(px, yy, "◀", col)
        for xx in range(px + 1, x):
            cv.put(xx, yy, "─", col)
    if shown >= len(text) and int(t * 2) % 2 == 0:
        cv.put(x + bw - 2, y + bh - 1, "▾", col)


def hold_time(text):
    return 1.2 + len(text) / 38.0


def run_dialog(ctx, factory, boxes, t0=0.0, span=2.0, seed=1, cues=()):
    """Run `boxes` over the animation made by factory(w, h, rng) -> scene with draw(cv, t, dt). Returns the number of boxes shown."""
    boxes = [(b[0], b[1], b[2] if len(b) > 2 else None) for b in boxes if b[1]]
    for who, text, _ in boxes:
        ctx.log.append(("say", who, text))
    if not boxes:
        return 0
    cols, rows = ctx.size()
    w, h = cols, rows - 1
    if w < 40 or h < 14:                                            # too small for a picture: timed cards
        for who, text, _ in boxes:
            ctx.card(text, min(4.0, hold_time(text)))
        return len(boxes)
    import random
    import ui
    scene = factory(w, h, random.Random(seed))
    cv, prev, fps = G.Canvas(w, h), None, getattr(ctx, "fps", G.FPS)
    keys = ui.Keys() if getattr(ctx, "keys", True) and ctx.out is __import__("sys").stdout else None
    try:
        truecolor = __import__("ascii_art").has_truecolor()
    except Exception:
        truecolor = True
    ctx.out.write("\033[?25l\033[0m")
    mixer, voiced = ctx.mixer, None
    try:
        with (keys if keys is not None else _NoKeys()) as k:
            raw = bool(getattr(k, "raw", False))
            i, clock, born, done_at = 0, 0.0, 0.0, None
            hist = []
            while i < len(boxes):
                who, text, anchor = boxes[i]
                started = time.monotonic()
                n = int((clock - born) * CPS)
                if mixer is not None and n < len(text) and voiced != i:
                    import audio
                    audio.voice_on(mixer, who)
                    voiced = i
                if n >= len(text) and mixer is not None and voiced == i:
                    import audio
                    audio.voice_off(mixer)
                    voiced = -1
                dx, dy = scene.draw(cv, t0 + pingpong(clock, span), 1.0 / fps) or (0, 0)
                draw_bubble(cv, who, text, min(n, len(text)), anchor, clock, hist)
                s, prev = cv.shifted(int(dx), int(dy)).diff(prev, truecolor)
                ctx.out.write(s)
                ctx.out.flush()
                key = k.read(timeout=max(0.0, 1.0 / fps - (time.monotonic() - started))) if raw else None
                if not raw:
                    ctx.sleep(max(0.0, 1.0 / fps - (time.monotonic() - started)))
                clock += 1.0 / fps
                if n >= len(text) and done_at is None:
                    done_at = clock
                if key in ("enter", " "):
                    if n < len(text):
                        born = clock - len(text) / CPS - 0.01          # finish the typing at once
                    else:
                        hist.append((who, text))
                        i, born, done_at = i + 1, clock, None
                elif not raw and done_at is not None and clock - done_at >= hold_time(text) * 0.6:
                    hist.append((who, text))
                    i, born, done_at = i + 1, clock, None
    finally:
        if mixer is not None:
            import audio
            audio.voice_off(mixer)
        chain.leave(ctx.out)                                               # like gore.play: clean screen, cursor back (black inside a chain)
        ctx.out.flush()
    return len(boxes)


class _NoKeys:
    raw = False

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, timeout=None):
        return None
