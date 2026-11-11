"""gallery.py - `python3 play.py --gallery`: every portrait, Noah animation and both ULTRA TESSERACT cinematics; any key = next, q = quit."""
import os
import shutil
import sys
import time

import portraits
import ui
import ultra_fx


def _tc():
    return os.environ.get("COLORTERM", "") in ("truecolor", "24bit")


def pages():
    """[(title, kind, payload)] in showing order."""
    out = []
    for n in portraits.PORTRAITS:
        for size in ("big", "small"):
            out.append(("portrait %s (%s)" % (n, size), "portrait", (n, size)))
    for k in portraits.KINDS:
        for st in portraits.STATES:
            out.append(("Noah %s: %s" % (k, st), "anim", (k, st)))
    for a, b in zip(portraits.KINDS, portraits.KINDS[1:]):
        out.append(("morph %s -> %s" % (a, b), "morph", (a, b)))
    out.append(("ULTRA TESSERACT: unfolding", "ultra", ("unlock", ultra_fx.UNLOCK_SECONDS)))
    out.append(("ULTRA TESSERACT: used", "ultra", ("use", ultra_fx.USE_SECONDS)))
    return out


def _wait(keys, seconds=None):
    """True = go on, False = quit. With seconds: returns early on a key, else loops by returning None at the timeout."""
    k = keys.read(timeout=seconds) if keys.raw else ("enter" if seconds is None else None)
    if k in ("q", "Q", "esc"):
        return False
    return True if k else None


def show_page(page, keys, out, cols, lines):
    title, kind, data = page
    tc = _tc()
    out.write("\033[2J\033[H" + title + "   (any key: next, q: quit)\n")
    if kind == "portrait":
        for l in portraits.portrait(data[0], data[1], tc) or ["(no art file)"]:
            out.write(l + "\n")
        out.flush()
        return _wait(keys) is not False
    if kind in ("anim", "morph"):
        size = "big" if cols >= 60 and lines >= 32 else "small"
        t0 = time.monotonic()
        while True:
            t = time.monotonic() - t0
            if kind == "anim":
                st = data[1]
                n = portraits.frame_count(data[0], st)
                fr = portraits.anim_frame(data[0], st, int(t * (7 if st == "idle" else 5)) % max(n, 1), size)
                col = data[0]
            else:
                fr = portraits.morph_frame(data[0], data[1], int(t * 6) % 12, size)
                col = data[1] if int(t * 6) % 12 >= 4 else data[0]
            out.write("\033[2;1H" + "\n".join(portraits.anim_ansi(fr, col, tc)) + "\033[0m\n")
            out.flush()
            r = _wait(keys, 0.06)
            if r is not None or not keys.raw:
                return r is not False
            if False:
                return r
    w, h = max(20, cols - 1), max(10, lines - 2)
    fn = ultra_fx.unlock_frame if data[0] == "unlock" else ultra_fx.use_frame
    while True:
        t0 = time.monotonic()
        while time.monotonic() - t0 < data[1] + 1.0:
            t = min(time.monotonic() - t0, data[1] - 0.01)
            out.write("\033[2;1H" + ultra_fx.render_ansi(fn(t, w, h), w, h, tc) + "\n")
            out.flush()
            r = _wait(keys, 0.04)
            if r is not None or not keys.raw:
                return r is not False


def run(out=None):
    out = out or sys.stdout
    size = shutil.get_terminal_size((100, 40))
    with ui.Keys() as keys:
        out.write("\033[?25l")
        try:
            for page in pages():
                if not show_page(page, keys, out, size.columns, size.lines):
                    break
        except KeyboardInterrupt:
            pass
        finally:
            out.write("\033[0m\033[?25h\033[2J\033[H")
            out.flush()
