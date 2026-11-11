"""fourth_wall_fx.py: the 4th-wall cinematic runs headless on a fake screen to the end, is deterministic, stays inside the screen, restores the
title, fires its sounds in time and is strictly cosmetic (no subprocess, no writes, no network, only /proc/uptime and /proc/loadavg are read)."""
import builtins
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fourth_wall_fx as F  # noqa: E402
import mika_ending as me  # noqa: E402
import noah_gore_fx as G  # noqa: E402

SIZES = [(80, 24), (120, 40), (245, 45)]
INFO = {"user": "ilvy", "host": "nixos", "time": "03:33:03", "cols": 80, "rows": 24, "cwd": "claude-game", "uptime": "2h 05m", "load": "0.42 0.38 0.30",
        "up_s": 7500.0, "mon": "Nov 08", "greeting": "good evening", "session": "12m 03s"}
TOKEN = re.compile(r"(\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x07)")


class DummyIO:
    def show(self, text, who="narrator"):
        pass


class Screen:
    """A tiny terminal: tracks the cursor, refuses glyphs outside cols x (rows - 1), newlines (scrolling) and records titles, bells and sync frames."""

    def __init__(self, cols, rows):
        self.cols, self.rows, self.x, self.y = cols, rows, 1, 1
        self.titles, self.bells, self.frames, self.ended_clean = [], 0, 0, False

    def feed(self, text):
        for tok in TOKEN.split(text):
            m = re.fullmatch(r"\x1b\[(\d+);(\d+)H", tok)
            if m:
                self.y, self.x = int(m.group(1)), int(m.group(2))
                assert 1 <= self.y <= self.rows - 1 and 1 <= self.x <= self.cols, (self.y, self.x)
            elif tok == "\x07":
                self.bells += 1
            elif tok.startswith("\x1b]"):
                self.titles.append(tok[4:-1])
            elif tok.startswith("\x1b["):
                self.frames += tok == "\x1b[?2026h"
            else:
                assert "\n" not in tok and "\r" not in tok
                for _ in tok:
                    assert self.x <= self.cols and self.y <= self.rows - 1, (self.y, self.x)
                    self.x += 1
        self.ended_clean = text.endswith("\x1b[0m\x1b[2J\x1b[H\x1b[?25h\x1b]2;FOLK\x07\x1b[?1049l\x1b[?25h")


def run(size, fps=3, info=INFO, guard=True, wind=None):
    out, sfx, clock = io.StringIO(), [], [0.0]

    def sleep(d):
        clock[0] += d
    ctx = me.Ctx(DummyIO(), sfx=sfx.append, sleep=sleep, size=lambda: size, out=out, fps=fps)
    ctx.info = info
    if wind is not None:
        ctx.winshake = wind
    me.fourth_wall(ctx)
    return ctx, out.getvalue(), sfx, clock[0]


def test_runs_to_the_end_inside_the_screen_on_every_size():
    for size in SIZES:
        ctx, text, sfx, spent = run(size)
        scr = Screen(*size)
        scr.feed(text)
        assert scr.frames == int(F.SECONDS * 3), size                          # one synchronized frame per tick
        assert 0 < spent <= F.SECONDS + 1.0
        assert text.endswith("\x1b[0m\x1b[2J\x1b[H\x1b[?25h\x1b]2;FOLK\x07\x1b[?1049l\x1b[?25h")     # black screen, cursor back, title back
        assert scr.titles[-1] == "FOLK" and len(scr.titles) >= 7 and scr.bells == 3
        assert f"{INFO['user']}@{INFO['host']}" in " ".join(scr.titles) and "i can see you, ilvy" in scr.titles
        assert scr.frames and F.BLACK_T < F.SECONDS


def test_deterministic_and_fps_independent_ending():
    a = run((120, 40))[1]
    assert a == run((120, 40))[1]
    assert run((245, 45), fps=2)[1].count("\x1b[?2026h") == int(F.SECONDS * 2)       # the real game runs at 2 fps in tests of other modules


def test_the_player_is_addressed_with_real_data():
    text = run((120, 40), fps=15)[1]
    for word in ("good evening, ilvy", "12m 03s", "i am a door", "on nixos", "03:33:03", "80 wide and 24 tall", "claude-game", "2h 05m", "0.42 0.38 0.30", "rm -rf /home/ilvy/*", "SIGNAL LOST"):
        assert word in re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text), word
    assert "just kidding" in re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)


def test_sounds_in_time_and_present():
    ctx, text, sfx, _ = run((80, 24))
    need = {"tesseract-spin-up", "electric-surge", "glitch-burst", "static-burst", "glass-crack", "system-error-beep", "typing-fast", "impact-boom-huge",
            "riser-reverse", "sub-drop"}
    assert need <= set(sfx), need - set(sfx)
    assert sfx[0] == "tesseract-spin-up" and sfx[-1] == "glitch-burst" and sfx.index("impact-boom-huge") < sfx.index("glass-crack", sfx.index("impact-boom-huge") + 1)
    assert [t for t, _ in F.CUES] == sorted(t for t, _ in F.CUES) and F.CUES[-1][0] < F.OFF_T            # the switch-off is silent
    import audio
    for name in need:
        assert os.path.exists(os.path.join(os.path.dirname(audio.__file__), "soundtracks", "sfx", name + ".mp3")), name


def test_strictly_cosmetic_only_proc_files_are_read(monkeypatch):
    seen = []
    real_open = builtins.open

    def guarded_open(file, mode="r", *a, **k):
        assert not any(c in str(mode) for c in "wax+"), (file, mode)
        seen.append(str(file))
        assert str(file) in ("/proc/uptime", "/proc/loadavg"), file
        return real_open(file, mode, *a, **k)

    def boom(*a, **k):
        raise AssertionError("forbidden call")
    ctx_texts = me.load_texts()
    for name in ("Popen", "run", "call", "check_call", "check_output"):
        monkeypatch.setattr(subprocess, name, boom)
    for name in ("system", "popen", "remove", "unlink", "rename", "mkdir", "rmdir", "fork", "execv", "execvp", "kill", "write"):
        monkeypatch.setattr(os, name, boom)
    import socket
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(builtins, "open", guarded_open)
    out, sfx = io.StringIO(), []
    ctx = me.Ctx(DummyIO(), sfx=sfx.append, sleep=lambda s: None, size=lambda: (120, 40), out=out, fps=2, texts=ctx_texts)
    me.fourth_wall(ctx)                                                       # the real sysinfo(): user, host, clock, size, cwd, /proc reads
    assert set(seen) <= {"/proc/uptime", "/proc/loadavg"} and seen
    assert out.getvalue().count("\x1b[?2026h") == int(F.SECONDS * 2)


def test_window_shake_only_through_the_existing_best_effort_class_and_restored():
    import ultra_fx
    writes = []
    ws = ultra_fx.WindowShake(env={"TERM": "xterm-256color"}, write=writes.append, read_reply=lambda: "\x1b[3;100;80t")
    ctx, text, sfx, _ = run((120, 40), wind=ws)
    assert writes[0] == "\033[13t" and len(writes) > 3
    assert all(re.fullmatch(r"\x1b\[13t|\x1b\[3;\d+;\d+t", w) for w in writes)
    assert writes[-1] == "\033[3;100;80t"                                     # the window is back where it was
    none = ultra_fx.WindowShake(env={"TERM": "xterm", "FOLK_WINSHAKE": "0"}, write=writes.append)
    w0 = len(writes)
    run((120, 40), wind=none)
    assert len(writes) == w0                                                  # opted out: nothing is sent


def test_cube_gets_brighter_and_faster_and_the_glass_breaks():
    b = [F.kf(F.CUBE, t)[3] for t in (0, 4, 8, 10.8, 11.0)]
    assert b == sorted(b) and b[-1] == 1.0
    r = [F.kf(F.SPIN, t) for t in (0, 4, 8, 10.8)]
    assert r == sorted(r)
    sc = F.FourthScene(120, 39, G.random.Random(4), INFO, me.load_texts())
    assert len(set(sc.shard)) > 14 and sc.borders and len(sc.start) == len(sc.members)
    cv = G.Canvas(120, 39)
    sc.draw(cv, 0.0, 1 / 15.0)
    first = sc.phase
    for k in range(1, 30):
        sc.draw(cv, k / 15.0, 1 / 15.0)
    mid = sc.phase
    assert mid > first > 0
    for t in (0.2, 11.5, 12.5, 15.0, 20.0, 30.0, 34.0, 38.0, 40.0, 42.0, F.OFF_T + 0.2, F.BLACK_T + 0.1):
        dx, dy = sc.draw(cv, t, 1 / 15.0)
        assert len(cv.ch) == 120 * 39 == len(cv.fg) == len(cv.bg)
    assert all(c == " " for c in cv.ch) and all(c == (0, 0, 0) for c in cv.bg)       # after BLACK_T: a hard cut to black


def test_texts_are_there_and_sanitised():
    t = me.load_texts()
    assert 12 <= len(t["mika.fourth.talk"]) <= 18
    for k in ("lines", "spill", "talk", "kernel", "procs", "files", "rm", "joke", "lost"):
        assert t["mika.fourth." + k], k
    assert len(t["mika.fourth.lines"]) == len(F.CAPTION_TIMES)
    assert F._clean("evil\x1b]0;x\x07name") == "evil0xname" and F._clean("\x1b") == "you"
    info = F.sysinfo((80, 24))
    assert all("\x1b" not in str(v) for v in info.values()) and info["cols"] == 80
    assert F.fill("hi {user} {nope}", {"user": "x"}) == "hi x {nope}"


def test_tiny_terminal_falls_back_to_cards():
    ctx, text, sfx, spent = run((30, 10))
    assert "\x1b[?2026h" not in text and sfx and any(e[0] == "card" for e in ctx.log)


def test_first_frame_is_the_cube_over_black_and_the_window_comes_up_around_it():
    sc = F.FourthScene(120, 39, G.random.Random(4), INFO, me.load_texts())
    cv = G.Canvas(120, 39)
    sc.draw(cv, 0.0, 1 / 15.0)
    assert max(max(c) for c in cv.fg) > 60 and max(max(c) for c in cv.bg) <= 3       # the glowing cube, nothing else (the bench ends like that)
    assert max(max(c) for c in cv.bg[:120] + cv.fg[:120]) <= 3                      # the FOLK title bar is still black
    sc.draw(cv, F.FADE_IN + 0.5, 1 / 15.0)
    assert max(max(c) for c in cv.fg + cv.bg) > 40


class FakeFS:
    def __init__(self):
        self.calls = []

    def start(self, sleep, size):
        self.calls.append("start")
        return True

    def stop(self):
        self.calls.append("stop")


def test_fullscreen_wraps_the_scene_and_is_restored_on_ctrl_c():
    fs = FakeFS()
    sizes = iter([(120, 40), (245, 45)] + [(245, 45)] * 99)
    out, sfx = io.StringIO(), []
    ctx = me.Ctx(DummyIO(), sfx=sfx.append, sleep=lambda s: None, size=lambda: next(sizes), out=out, fps=2)
    ctx.fullscreen, ctx.info = fs, INFO
    me.fourth_wall(ctx)
    assert fs.calls == ["start", "stop"] and out.getvalue().endswith("\x1b]2;FOLK\x07\x1b[?1049l\x1b[?25h")

    def interrupted(d):
        raise KeyboardInterrupt
    fs2, out2 = FakeFS(), io.StringIO()
    ctx2 = me.Ctx(DummyIO(), sfx=lambda n: None, sleep=interrupted, size=lambda: (120, 40), out=out2, fps=2)
    ctx2.fullscreen, ctx2.info = fs2, INFO
    try:
        me.fourth_wall(ctx2)
        assert False
    except KeyboardInterrupt:
        pass
    assert fs2.calls == ["start", "stop"] and out2.getvalue().endswith("\x1b]2;FOLK\x07\x1b[?1049l\x1b[?25h")      # fullscreen, cursor and title back


def test_fullscreen_orders_and_only_the_allowed_commands():
    log, written = [], []
    size = [(120, 40)]

    def run_hypr(argv):
        log.append(list(argv))
        if argv[:2] == ["hyprctl", "activewindow"]:
            return '{"fullscreen": 0}'
        size[0] = (245, 45)
        return ""
    fs = F.Fullscreen(env={"TERM": "xterm-kitty", "HYPRLAND_INSTANCE_SIGNATURE": "x"}, write=written.append, run=run_hypr)
    assert fs.start(lambda d: None, lambda: size[0]) and fs.did == "hypr"
    assert written == ["\033[10;1t", "\033[9;1t"]                                   # xterm ops first: kitty ignores them (size unchanged)
    fs.stop()
    assert log == [["hyprctl", "activewindow", "-j"], ["hyprctl", "dispatch", "fullscreen", "0"], ["hyprctl", "dispatch", "fullscreen", "0"]]
    # already fullscreen: untouched, nothing to undo
    log.clear()
    fs = F.Fullscreen(env={"HYPRLAND_INSTANCE_SIGNATURE": "x"}, run=lambda a: (log.append(list(a)), '{"fullscreen": 2}')[1])
    assert not fs.start(lambda d: None, lambda: (1, 1)) and (fs.stop() or log == [["hyprctl", "activewindow", "-j"]])
    # sway
    log.clear()
    fs = F.Fullscreen(env={"SWAYSOCK": "/x"}, run=lambda a: (log.append(list(a)), '{"focused": true, "fullscreen_mode": 0}')[1])
    assert fs.start(lambda d: None, lambda: (1, 1)) and fs.did == "sway"
    fs.stop()
    assert log[-2:] == [["swaymsg", "fullscreen", "enable"], ["swaymsg", "fullscreen", "disable"]]
    # xterm that really resizes: only window ops, no command at all
    log.clear(), written.clear()
    sz = [(80, 24)]
    fs = F.Fullscreen(env={"TERM": "xterm"}, write=lambda x: (written.append(x), sz.__setitem__(0, (200, 60))), run=lambda a: log.append(a))
    assert fs.start(lambda d: None, lambda: sz[0]) and fs.did == "xterm10"
    fs.stop()
    assert written == ["\033[10;1t", "\033[10;0t"] and not log
    # opt-out and nothing else
    assert not F.Fullscreen(env={"TERM": "xterm", "FOLK_FULLSCREEN": "0", "SWAYSOCK": "/x"}, run=boom_run).start(lambda d: None, lambda: (1, 1))
    assert not F.Fullscreen(env={}, run=boom_run).start(lambda d: None, lambda: (1, 1))


def boom_run(argv):
    raise AssertionError(argv)


def test_run_helper_refuses_everything_but_the_four_commands(monkeypatch):
    seen = []
    monkeypatch.setattr(F.subprocess, "run", lambda argv, **k: seen.append((list(argv), k)) or type("R", (), {"stdout": ""})())
    for argv in (["rm", "-rf", "/"], ["sh", "-c", "id"], ["hyprctl", "dispatch", "exec", "x"], ["notify-send", "x"]):
        assert F._run(argv) == ""
    assert not seen
    F._run(["swaymsg", "fullscreen", "enable"])
    assert seen[0][0] == ["swaymsg", "fullscreen", "enable"] and seen[0][1]["timeout"] == 2 and "shell" not in seen[0][1]


def test_input_lock_flushes_keys_before_and_after_and_echo_is_off():
    import pty
    import select
    import termios
    master, slave = pty.openpty()
    fake = os.fdopen(slave, "r", closefd=False)
    real_stdin = sys.stdin
    sys.stdin = fake
    try:
        os.write(master, b"abc")                                              # typed before the scene: must not leak in
        with F._QuietTty(True):
            assert not termios.tcgetattr(slave)[3] & termios.ECHO and not termios.tcgetattr(slave)[3] & termios.ICANON
            assert not select.select([slave], [], [], 0.1)[0]                 # flushed on entry
            os.write(master, b"xyz")                                          # typed during the scene: dropped
        assert termios.tcgetattr(slave)[3] & termios.ECHO                     # echo restored
        assert not select.select([slave], [], [], 0.1)[0]                     # and nothing left for the next scene
    finally:
        sys.stdin = real_stdin
        os.close(master)
        os.close(slave)
