"""noah_gore_fx.py: the three full-screen scenes of the Mika ending (slashes, awakening, Noah burns) run headless with a fake sleep:
they end, stay on screen, are deterministic, fire their sounds and draw nothing outside the terminal."""
import io
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mika_ending as me  # noqa: E402
import noah_gore_fx as G  # noqa: E402

SIZES = [(80, 24), (120, 40), (245, 45)]
SCENES = {"slash": me.noah_slashes, "awake": me.mika_awakens, "burn": me.noah_burns}
SECONDS = {"slash": 25.0, "awake": 32.0, "burn": 75.0}
CSI = re.compile(r"(\x1b\[[0-9;?]*[A-Za-z])")


class DummyIO:
    def __init__(self):
        self.shown = []

    def show(self, text, who="narrator"):
        self.shown.append((who, text))


def run_scene(name, size, fps=3, seed=None):
    out, sfx, clock = io.StringIO(), [], [0.0]

    def sleep(d):
        clock[0] += d
    ctx = me.Ctx(DummyIO(), sfx=sfx.append, sleep=sleep, size=lambda: size, out=out, fps=fps)
    ctx.dialog = lambda *a, **k: 0                                      # these tests measure the animation frames only (bubbles: tests/test_ending_flow.py)
    SCENES[name](ctx)
    return ctx, out.getvalue(), sfx, clock[0]


def assert_inside(text, cols, rows):
    """A tiny terminal: every cursor jump and every printed glyph must land inside cols x (rows - 1); no newlines (no scrolling)."""
    x = y = 1
    for tok in CSI.split(text):
        m = re.fullmatch(r"\x1b\[(\d+);(\d+)H", tok)
        if m:
            y, x = int(m.group(1)), int(m.group(2))
            assert 1 <= y <= rows - 1 and 1 <= x <= cols, (y, x)
        elif tok.startswith("\x1b"):
            continue
        else:
            assert "\n" not in tok and "\r" not in tok
            for _ in tok:
                assert x <= cols and y <= rows - 1, (y, x)
                x += 1


def test_every_scene_runs_to_the_end_on_every_size_inside_the_screen():
    for name in SCENES:
        for size in SIZES:
            ctx, text, sfx, spent = run_scene(name, size)
            assert_inside(text, *size)
            assert text.count("\x1b[?2026h") == int(SECONDS[name] * 3), (name, size)          # one synchronized frame per tick
            assert text.endswith("\x1b[0m\x1b[2J\x1b[H\x1b[?25h")                              # the terminal is left clean, cursor back
            assert 0 < spent <= SECONDS[name] + 1.0, (name, spent)                          # paced by sleep, never longer than it claims
            assert sfx, name


def test_deterministic_and_diffed():
    a = run_scene("burn", (80, 24))[1]
    b = run_scene("burn", (80, 24))[1]
    assert a == b
    cv = G.Canvas(20, 5)
    cv.put(3, 2, "x", (255, 0, 0), (0, 0, 0))
    first, cells = cv.diff(None)
    again, _ = cv.diff(cells)
    assert "\x1b[3;1H" in first and "H" not in again                  # an unchanged frame writes no cursor jumps
    cv.put(10, 4, "y", (0, 255, 0))
    assert cv.diff(cells)[0].count("H") == 1                                                # one changed cell, one jump


def test_full_frame_rate_gives_the_real_frame_counts():
    for name in SCENES:
        ctx, text, sfx, spent = run_scene(name, (80, 24), fps=G.FPS)
        assert text.count("\x1b[?2026h") == int(SECONDS[name] * G.FPS)


def test_the_sounds_of_each_scene():
    need = {"slash": {"knife-draw", "blade-block", "stab-flesh", "bone-crack-1", "bone-crack-2", "blade-shatter"},
            "awake": {"glow-hum-rising", "lake-whispers", "stone-split"},
            "burn": {"ground-rumble", "stone-split", "hell-roar", "growl-demon", "fire-ignite", "fire-roar", "flesh-burn", "blood-boil",
                     "scream-distorted-1", "scream-distorted-2", "scream-fire", "scream-falling-1", "fall-wind", "sub-drop"}}
    for name, sounds in need.items():
        sfx = run_scene(name, (80, 24))[2]
        assert sounds <= set(sfx), (name, sounds - set(sfx))
    import audio
    for name in need["burn"] | need["slash"] | need["awake"]:
        assert os.path.exists(os.path.join(os.path.dirname(audio.__file__), "soundtracks", "sfx", name + ".mp3")), name


def test_captions_are_the_text_lines_in_order():
    ctx, text, sfx, _ = run_scene("burn", (120, 40))
    cards = [t for k, t in [e for e in ctx.log if e[0] == "card"]]
    assert cards == ctx.lines("mika.burn.lines")
    cap = G.burn_captions(ctx.lines("mika.burn.lines"))
    assert [a for a, b, _ in cap] == sorted(a for a, b, _ in cap) and all(b > a for a, b, _ in cap) and cap[-1][1] <= 53.0
    assert len(G.burn_captions(["one", "two", "three"])) == 3                               # a rewritten text with another line count still works
    assert len(G.slash_captions(["a"] * 5)) == 5 and G.slash_captions([]) == []


def test_terminal_too_small_falls_back_to_cards():
    ctx, text, sfx, spent = run_scene("burn", (30, 10))
    assert "\x1b[?2026h" not in text and sfx and any(e[0] == "card" for e in ctx.log)


def test_body_face_and_pieces_do_not_crash_at_any_size():
    for hf in (8, 13, 20, 30, 40):
        b = G.Body(hf, random.Random(1))
        assert b.cells and b.mask
        for t in (0, 5, 9, 15, 25, 31):
            g = b.render(t)
            assert len(g) == hf and all(len(r) == b.wf for r in g)
    for size in SIZES:
        sc = G.BurnScene(size[0], size[1] - 1, random.Random(1))
        assert sc.face.P is not None
    assert G.Face(30, 10, random.Random(1)).P is None                                       # no room for a portrait: the scene draws fire instead


def test_only_runs_exactly_one_scene():
    ctx = me.Ctx(DummyIO(), sfx=lambda n: None, sleep=lambda s: None, size=lambda: (30, 10), out=io.StringIO(), fps=2)
    me.run(ctx, only="burn")
    assert ("card", ctx.lines("mika.burn.lines")[0]) in ctx.log and not any("slash" in str(e) for e in ctx.log)
    assert {"slash", "awake", "burn", "fourth", "valley", "bench"} <= set(me.ONLY)
