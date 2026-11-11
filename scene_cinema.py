"""scene_cinema.py - the cinema gallery:  python3 play.py --cinema   (python3 play.py --cinema --scene k1.see_mika  starts at that scene)

Lists every scene of the game (the story scenes of story/story.json and the full-screen cine scenes: fight intro, phases, defeat, decision, endings, Mika ending parts),
plays the chosen one, and afterwards offers  Enter / Right = next,  Left = previous,  r = replay,  q = back to the list.  Choices inside a story scene are asked on the animation.
"""
import json
import os
import shutil
import sys

import cine_fx
import mika_ending
import scene_play
import ui

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_ART = ("boss", "items", "credits")


def entries(story=None):
    """[(id, label, kind)] kind = story | cine | mika; story scenes first in game order, then the cinematic ones."""
    story = story if story is not None else json.load(open(os.path.join(HERE, "story", "story.json"), encoding="utf-8"))
    out = []
    for sid, sc in story.items():
        if sc.get("art") in SKIP_ART or sc.get("entfaellt"):
            continue
        kind = "place" if sid.startswith("ort.") else "tree" if sc.get("baum") else "text"
        out.append((sid, "ch%s  %-6s %s" % (sc.get("kapitel", "-"), kind, ", ".join(sc.get("figuren") or []) or "-"), "story"))
    out += [(n, "cine   full-screen scene", "cine") for n in cine_fx.NAMED]
    out += [(n, "ending part (Mika)", "mika") for n in mika_ending.ONLY if n not in cine_fx.NAMED]
    return out


class Plain:
    mixer = None

    def show(self, text, who="narrator"):
        print(text)


def make_ctx(mixer=None):
    return mika_ending.Ctx(Plain(), mixer)


def play_entry(entry, ctx, story):
    sid, _, kind = entry
    if kind == "story":
        sc = story[sid]
        place = sc.get("ort") or (sid.split(".")[1] if sid.startswith("ort.") else None)
        scene_play.play(sc, ctx, sid=sid, place=place)
    elif kind == "cine":
        cine_fx.run_named(ctx, sid)
    else:
        mika_ending.ONLY[sid](ctx)


def list_screen(items, pos, keys):
    """Arrow keys / PgUp-like j,k, Enter to play, q to leave. Returns the index or None."""
    rows = max(8, shutil.get_terminal_size((100, 40)).lines - 5)
    while True:
        top = max(0, min(pos - rows // 2, len(items) - rows))
        sys.stdout.write("\033[2J\033[H  FOLK cinema - up/down choose, Enter play, q quit\n\n")
        for i in range(top, min(len(items), top + rows)):
            sid, label, kind = items[i]
            sys.stdout.write("  %s %-24s %s\n" % ("\033[1;33m>\033[0m" if i == pos else " ", sid, label))
        sys.stdout.flush()
        k = keys.read(timeout=None)
        if k in ("up", "k"):
            pos = (pos - 1) % len(items)
        elif k in ("down", "j"):
            pos = (pos + 1) % len(items)
        elif k == "left":
            pos = max(0, pos - rows)
        elif k == "right":
            pos = min(len(items) - 1, pos + rows)
        elif k == "enter":
            return pos
        elif k in ("q", "esc"):
            return None


def after(keys, name, i, n):
    w, h = shutil.get_terminal_size((100, 40))
    sys.stdout.write("\033[%d;1H\033[2K\033[7m  %s (%d/%d)   Enter/Right = next   Left = previous   r = replay   q = list  \033[0m" % (h, name, i + 1, n))
    sys.stdout.flush()
    while True:
        k = keys.read(timeout=None)
        if k in ("enter", "right", "n"):
            return 1
        if k in ("left", "p"):
            return -1
        if k == "r":
            return 0
        if k in ("q", "esc"):
            return None


def run(start=None, mixer=None):
    story = json.load(open(os.path.join(HERE, "story", "story.json"), encoding="utf-8"))
    items = entries(story)
    pos = next((i for i, e in enumerate(items) if e[0] == start), 0)
    ctx = make_ctx(mixer)
    try:
        while True:
            if start is None:
                with ui.Keys() as keys:
                    pos = list_screen(items, pos, keys)
                if pos is None:
                    return
            start = None
            while True:
                play_entry(items[pos], ctx, story)
                with ui.Keys() as keys:
                    step = after(keys, items[pos][0], pos, len(items))
                sys.stdout.write("\033[0m\033[2J\033[H")
                if step is None:
                    break
                pos = (pos + step) % len(items)
    except KeyboardInterrupt:
        sys.stdout.write("\033[0m\033[?25h\n")
