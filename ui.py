"""ui.py - terminal presentation: text reveal with a voice, colours, arrow-key choices.

- reveal(): types text out letter by letter (Enter or Space skips to the end) while a voice loops.
- choose(): up/down + Enter, or press the number; falls back to typing the number when there is no tty.
- Everything takes injectable I/O so it can be tested without a terminal.
"""
import os
import re
import select
import sys
import time

try:
    import termios
    import tty
except ImportError:      # not on this platform
    termios = tty = None

RESET = "\033[0m"
COLORS = {  # Noah's three personalities have fixed colours: normal green, second yellow, third red
    "noah": "\033[32m", "noah2": "\033[33m", "noah3": "\033[1;31m",
    "mika": "\033[36m", "connor": "\033[37m", "narrator": "", "system": "\033[90m",
    "title": "\033[1;35m", "dim": "\033[2m",
}
PUNCT_PAUSE = {".": 0.28, "!": 0.28, "?": 0.28, ",": 0.12, ";": 0.15, ":": 0.15, "—": 0.2, "...": 0.35}
_ANSI = re.compile(r"\033\[[0-9;]*m")


def color_ok(out=None):
    out = out or sys.stdout
    return not os.environ.get("NO_COLOR") and getattr(out, "isatty", lambda: False)()


def paint(text, who, out=None):
    c = COLORS.get(who, "")
    return "%s%s%s" % (c, text, RESET) if c and color_ok(out) else text


def visible_len(s):
    return len(_ANSI.sub("", s))


class Keys:
    """Raw single-key reader. read() -> 'up' 'down' 'left' 'right' 'enter' 'esc' or a character; None if none."""

    def __init__(self, stream=None):
        self.stream = stream or sys.stdin
        self.fd = None
        self.old = None

    def __enter__(self):
        if termios and self.stream.isatty():
            self.fd = self.stream.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *a):
        if self.fd is not None and self.old is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    @property
    def raw(self):
        return self.fd is not None

    def ready(self, timeout=0.0):
        return self.raw and bool(select.select([self.stream], [], [], timeout)[0])

    def read(self, timeout=None):
        if not self.raw:
            return None
        if timeout is not None and not self.ready(timeout):
            return None
        ch = os.read(self.fd, 1).decode(errors="ignore")
        if ch == "\x1b":
            # an arrow key is ESC [ A (or ESC O A); the bytes can arrive one by one, so read until the final letter
            seq = ""
            deadline = time.monotonic() + 0.08
            while time.monotonic() < deadline:
                if self.ready(0.01):
                    c = os.read(self.fd, 1).decode(errors="ignore")
                    seq += c
                    if len(seq) >= 2 and (c.isalpha() or c == "~"):
                        break
            names = {"[A": "up", "[B": "down", "[C": "right", "[D": "left",
                     "OA": "up", "OB": "down", "OC": "right", "OD": "left"}
            if not seq:
                return "esc"
            return names.get(seq[:2])           # other keys (Home, PgUp, ...) are ignored, never turned into 'esc'
        if ch in ("\r", "\n"):
            return "enter"
        return ch


_TOKEN = re.compile(r"\033\[[0-9;]*m|.", re.S)


def reveal(text, who="narrator", speed=0.032, out=None, sleep=time.sleep, keys=None, mixer=None, instant=False, end="\n"):
    """Type `text` out letter by letter with a voice. Enter/Space skips the rest. Returns True if skipped.
    Without a terminal (and no injected sleep) the text appears at once, so tests and pipes stay fast."""
    out = out or sys.stdout
    if sleep is time.sleep and not getattr(out, "isatty", lambda: False)():
        instant = True
    c = COLORS.get(who, "") if color_ok(out) else ""
    if mixer is not None and not instant:
        import audio
        audio.voice_on(mixer, who)
    skipped = False
    try:
        if c:
            out.write(c)
        tokens = _TOKEN.findall(text)
        for i, tok in enumerate(tokens):
            if instant or skipped:
                out.write("".join(tokens[i:]))
                break
            out.write(tok)
            out.flush()
            if tok.startswith("\033"):
                continue
            delay = speed
            nxt = tokens[i + 1] if i + 1 < len(tokens) else " "
            if tok in PUNCT_PAUSE and nxt in (" ", "\n"):
                delay = PUNCT_PAUSE[tok]
            elif tok == "\n":
                delay = 0.1
            if tok != " ":
                if keys is not None and getattr(keys, "raw", False):
                    k = keys.read(timeout=delay)
                    if k in ("enter", " "):
                        skipped = True
                elif keys is not None:
                    k = keys.read(timeout=delay)
                    if k in ("enter", " "):
                        skipped = True
                else:
                    sleep(delay)
        out.write((RESET if c else "") + end)
        out.flush()
    finally:
        if mixer is not None:
            import audio
            audio.voice_off(mixer)
    return skipped


def reveal_broken(first, second, who_first="noah", who_second="noah3", cut=0.55, speed=0.03, fast=0.006, out=None,
                  sleep=time.sleep, mixer=None):
    """The boss moment: `first` is typed until `cut` of its length, stops mid-word, then `second` is typed very fast
    on a new line in another personality's colour."""
    out = out or sys.stdout
    n = max(1, int(len(first) * cut))
    reveal(first[:n], who_first, speed=speed, out=out, sleep=sleep, mixer=mixer, end="")
    sleep(0.35)
    out.write("\n")
    reveal(second, who_second, speed=fast, out=out, sleep=sleep, mixer=mixer)


def choose(prompt, options, out=None, inp=None, keys=None, aliases=None):
    """Pick one of `options` with up/down + Enter, or by pressing its number. Returns the index.
    Without a terminal: prints the numbered list and reads a number from `inp` (default input())."""
    out = out or sys.stdout
    inp = inp or input
    own = keys is None
    keys = keys or Keys()
    if own:
        keys.__enter__()
    try:
        if not keys.raw:
            if prompt:
                out.write(prompt + "\n")
            for i, o in enumerate(options, 1):
                out.write("  %d) %s\n" % (i, o))
            while True:
                a = inp("> ").strip()
                if a.isdigit() and 1 <= int(a) <= len(options):
                    return int(a) - 1
                if aliases and a.lower() in aliases:
                    return aliases[a.lower()]
                if aliases is not None:
                    out.write("\n  (the valley does not understand that.)\n\n")
        pos = 0
        if prompt:
            out.write(prompt + "\n")
        import shutil
        cols = max(20, shutil.get_terminal_size((80, 24)).columns - 8)
        shown = [o if len(o) <= cols else o[: cols - 1] + "\u2026" for o in options]
        total = len(options)

        def draw(first):
            if not first:
                out.write("\033[%dA" % total)
            out.write("".join("\r\033[K %s %d) %s\n" % ("\033[7m>\033[0m" if i == pos else " ", i + 1, o)
                              for i, o in enumerate(shown)))
            out.flush()
        def collapse():
            """Replace the whole menu by one line with the chosen answer, so old menus never pile up."""
            out.write("\033[%dA\r\033[J" % total)
            out.write(" \033[7m>\033[0m %s\n" % shown[pos])
            out.flush()
        draw(True)
        while True:
            k = keys.read()
            if k in ("up", "k"):
                pos = (pos - 1) % total
            elif k in ("down", "j"):
                pos = (pos + 1) % total
            elif k == "enter":
                collapse()
                return pos
            elif k and k.isdigit() and 1 <= int(k) <= total:
                pos = int(k) - 1
                collapse()
                return pos
            draw(False)
    finally:
        if own:
            keys.__exit__()


BOX_WIDTH = 66
_SFX = re.compile(r"\{\{(.+?)\}\}")


def _wrap(text, width):
    import textwrap
    out = []
    for para in text.replace("\r\n", "\n").split("\n"):
        if not para.strip():
            out.append("")
        else:
            out += textwrap.wrap(para, width, replace_whitespace=False, drop_whitespace=True) or [""]
    while out and out[-1] == "":
        out.pop()
    return out


def boxed(text, who="narrator", label="", width=None, speed=0.032, out=None, sleep=time.sleep, keys=None, mixer=None,
          instant=False):
    """Type `text` in an invisible fixed-width block: a ═══ line with the speaker's name on top, a ─── line below, no
    side borders. Enter/Space skips. Returns True if skipped."""
    out = out or sys.stdout
    if width is None:
        import shutil
        width = max(30, min(BOX_WIDTH, shutil.get_terminal_size((80, 24)).columns - 6))
    if sleep is time.sleep and not getattr(out, "isatty", lambda: False)():
        instant = True
    c = COLORS.get(who, "") if color_ok(out) else ""
    r = RESET if c else ""
    title = (" %s " % label) if label else ""
    out.write("%s\u2550\u2550%s%s%s\n" % (c, title, "\u2550" * (width + 2 - len(title)), r))
    if mixer is not None and not instant:
        import audio
        audio.voice_on(mixer, who)
    skipped = False
    try:
        # {{KRACK!}}: a sound effect gets its own centred, bold line with air around it, never inside the running text
        lines = []
        for part in _SFX.split(text):
            if len(lines) and False:
                pass
            lines.append(part)
        flow = []
        for i, part in enumerate(_SFX.split(text)):
            if i % 2:
                flow.append(("sfx", part.strip()))
            elif part.strip():
                flow += [("text", l) for l in (_wrap(part.strip(), width) or [""])]
        for kind, line in (flow or [("text", "")]):
            if kind == "sfx":
                out.write("\n" + "\033[1;31m" * (1 if c or color_ok(out) else 0) + ("   %s" % line).center(width + 4) + (RESET if color_ok(out) else "") + "\n\n")
                out.flush()
                if not instant:
                    sleep(0.35)
                continue
            out.write("%s  %s" % (c, r))
            for i, ch in enumerate(line):
                if instant or skipped:
                    out.write(line[i:])
                    break
                out.write(ch)
                out.flush()
                delay = speed
                nxt = line[i + 1] if i + 1 < len(line) else " "
                if ch in PUNCT_PAUSE and nxt == " ":
                    delay = PUNCT_PAUSE[ch]
                if ch != " ":
                    if keys is not None:
                        if keys.read(timeout=delay) in ("enter", " "):
                            skipped = True
                    else:
                        sleep(delay)
            out.write("\n")
            out.flush()
        out.write("%s%s%s\n" % (c, "\u2500" * (width + 4), r))
        out.flush()
    finally:
        if mixer is not None:
            import audio
            audio.voice_off(mixer)
    return skipped
