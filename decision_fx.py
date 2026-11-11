"""decision_fx.py - the 30 s 'Let him live / Kill him' choice as an overlay on an animated cellar (ambient_fx.Cellar), not on bare text.

    timed_pick_scene(ctx, text, options, seconds=30, warns=None, who="noah") -> index of the chosen option, or None when the time runs out
        text      what Noah says as the choice is put (a bubble over him, typed with his voice blips)
        warns     {elapsed second: text}, e.g. {10: warn10, 20: warn20}: at that second Noah's bubble changes to the text
        options   the labels; Up/Down + Enter or the digits 1..n choose (same keys as RealIO.timed_pick); a countdown bar runs down at the bottom
    available(ctx) -> True on a real terminal that is big enough (else the caller keeps the old text menu).
The timer, the options and the 'no answer = ending-3' rule are the caller's; this only draws and reads keys. Nothing is printed outside the frame loop.
"""
import chain
import random
import sys
import time

import ambient_fx
import noah_gore_fx as G
import speech

CPS = speech.CPS


def available(ctx):
    cols, rows = ctx.size()
    return ctx.out is sys.stdout and sys.stdout.isatty() and cols >= 40 and rows >= 15


def draw_overlay(cv, options, pos, left, total):
    """The option boxes side by side near the bottom and the countdown bar above them (red and trembling when the end is near)."""
    w, h = cv.w, cv.h
    if w >= speech.PANEL_MIN_COLS:                                                      # the speech column owns the right edge: boxes and bar stay left of it
        w = w - speech.panel_width(w) - 3
        y = h - 4
    else:                                                                               # a narrow terminal has the speech strip at the bottom: the options go to the top
        y = 5
    k = max(0.0, left / float(total))
    bar_w = int((w - 12) * k)
    urgent = left < 7.0
    col = (255, 70, 60) if urgent else (210, 214, 220)
    shake = int(left * 9) % 2 if urgent else 0
    for x in range(6, 6 + bar_w):
        cv.put(x + shake, y - 2, "━", col)
    cv.text(w - 12, y - 3 if y > 8 else y + 3, "%2d s" % max(0, int(left + 0.99)), col)
    n = len(options)
    slot = (w - 8) // max(1, n)
    for i, label in enumerate(options):
        txt = " %d) %s " % (i + 1, label)
        x0 = 4 + i * slot + max(0, (slot - len(txt) - 2) // 2)
        sel = i == pos
        fg = (255, 235, 200) if sel else (150, 150, 160)
        bg = (90, 20, 20) if sel else (14, 14, 20)
        for xx in range(x0, x0 + len(txt) + 2):
            cv.put(xx, y, " ", fg, bg)
            cv.put(xx, y - 1, "─" if xx not in (x0, x0 + len(txt) + 1) else "┌" if xx == x0 else "┐", fg, bg)
            cv.put(xx, y + 1, "─" if xx not in (x0, x0 + len(txt) + 1) else "└" if xx == x0 else "┘", fg, bg)
        cv.put(x0, y, "│", fg, bg)
        cv.put(x0 + len(txt) + 1, y, "│", fg, bg)
        cv.text(x0 + 1, y, txt, fg, bg)


def timed_pick_scene(ctx, text, options, seconds=30, warns=None, who="noah", seed=3):
    import ui
    cols, rows = ctx.size()
    w, h = cols, rows - 1
    scene = ambient_fx.Cellar(w, h, random.Random(seed))
    cv, prev, fps = G.Canvas(w, h), None, 12.0
    warns = dict(warns or {})
    try:
        truecolor = __import__("ascii_art").has_truecolor()
    except Exception:
        truecolor = True
    cur, born, clock, pos, voiced, last = text, 0.0, 0.0, 0, False, 0
    mixer = getattr(ctx, "mixer", None)
    ctx.out.write("\033[?25l\033[0m\033[2J")
    try:
        with ui.Keys() as keys:
            while clock < seconds:
                started = time.monotonic()
                el = clock
                if int(el) > last:
                    last = int(el)
                    if last in warns:
                        cur, born, voiced = warns[last], clock, False
                n = int((clock - born) * CPS)
                if mixer is not None and n < len(cur) and not voiced:
                    import audio
                    audio.voice_on(mixer, who)
                    voiced = True
                if mixer is not None and n >= len(cur) and voiced:
                    import audio
                    audio.voice_off(mixer)
                    voiced = False
                scene.draw(cv, 2.0 + clock * 0.5, 1.0 / fps)                          # Noah on his knees; the smile grows as the time runs out
                speech.draw_bubble(cv, "noah3" if clock > 18 else who, cur, min(n, len(cur)), (0.5, 0.52), clock)
                draw_overlay(cv, options, pos, seconds - clock, seconds)
                s, prev = cv.diff(prev, truecolor)
                ctx.out.write(s)
                ctx.out.flush()
                key = keys.read(timeout=max(0.0, 1.0 / fps - (time.monotonic() - started))) if keys.raw else None
                if not keys.raw:
                    time.sleep(max(0.0, 1.0 / fps - (time.monotonic() - started)))
                clock += 1.0 / fps
                if key in ("up", "down"):
                    pos = (pos + (1 if key == "down" else -1)) % len(options)
                elif key in ("left", "right"):
                    pos = (pos + (1 if key == "right" else -1)) % len(options)
                elif key == "enter":
                    return pos
                elif key and key.isdigit() and 1 <= int(key) <= len(options):
                    return int(key) - 1
        return None
    finally:
        if mixer is not None:
            import audio
            audio.voice_off(mixer)
        chain.leave(ctx.out)
        ctx.out.flush()
