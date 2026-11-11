"""The hidden Mika / ULTRA TESSERACT ending: condition logic, texts, headless run to the credits."""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boss as boss_mod  # noqa: E402
import mika_ending as me  # noqa: E402
import story_game as sg  # noqa: E402
from test_story_game import FakeIO, STORY  # noqa: E402


def make(tmp_path, unused, timeout=False, choice=0):
    io = FakeIO([None], timeout)
    io.pick_override = None
    calls = {"credits": []}

    def boss_runner(lines, power):
        g.ultra_unused = unused
        return "won"
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"), boss_runner=boss_runner,
                credits_runner=lambda b, s: calls["credits"].append(s))
    io.g[0] = g
    g.sleep = lambda s: None
    io.timed_pick = lambda options, seconds, on_tick=None: None if timeout else choice
    return g, io, calls


def test_condition_all_combinations(tmp_path):
    for unused, choice in itertools.product([True, False], [0, 1]):
        g, io, _ = make(tmp_path, unused, choice=choice)
        g.flag("tesseract")
        g.boss_runner([], 1.0)
        expect = ("mika-ultra" if unused else "let-it-live") if choice == 0 else "slaughter-it"
        assert g.decision() == expect, (unused, choice)
    g, io, _ = make(tmp_path, True, timeout=True)
    g.boss_runner([], 1.0)
    assert g.decision() == "ending-3"


def test_boss_flag_needs_unlock_and_no_use():
    b = boss_mod.Boss(has_tesseract=True)
    assert not b.ultra_unused()                      # never unlocked
    b.ultra_unlocked = True
    assert b.ultra_unused()
    b.tesseract_used = True
    assert not b.ultra_unused()
    b.tesseract_used, b.ultra_used = False, True
    assert not b.ultra_unused()


def test_texts_exist_and_final_line_is_exact():
    t = me.load_texts()
    for k in ("slash.intro", "slash.lines", "slash.noah", "awake.lines", "awake.noah", "awake.mika", "burn.lines", "fourth.lines",
              "valley.lines", "bench.lines", "bench.mika", "bench.final", "bench.end"):
        assert t["mika." + k], k
    assert t["mika.bench.final"] == me.FINAL_LINE == "at last you made the right choice, cheers mate!"


class RecMixer:
    """Records the audio calls the ending makes (and has none of the real methods' effects)."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name in ("voice", "dir", "enabled", "backend", "log"):
            raise AttributeError(name)
        return lambda *a: self.calls.append((name,) + a)


def test_scenes_run_in_order_and_final_line_is_mikas_last(tmp_path):
    io, mx = FakeIO([None]), RecMixer()
    sfx, order = [], []
    ctx = me.Ctx(io, mx, sfx=sfx.append, sleep=lambda s: None, out=open(tmp_path / "o", "w"), fps=2, spared="He lets go of the knife. It rings on the floor.")
    for scene in me.SCENES:
        scene(ctx)
        order.append(len(sfx))
    assert [f.__name__ for f in me.SCENES] == ["noah_slashes", "mika_awakens", "noah_burns", "valley_burns", "bench_scene", "fourth_wall"]
    assert order == sorted(order) and order[0] > 0
    for s in ("glow-hum-rising", "hell-roar", "tesseract-spin-up"):
        assert s in sfx
    assert "lighter-click" not in sfx and "joint-exhale" not in sfx and "joint-inhale" not in sfx      # no joint sounds: only the song
    assert io.shown == []                                                  # NO bare terminal text anywhere in the ending: everything is bubbles/captions
    said = [(who, t) for k, who, t in [e for e in ctx.log if e[0] == "say"]]
    mika = [t for who, t in said if who == "mika"]
    assert mika[-1] == me.FINAL_LINE and any("Chilling now" in m for m in mika)
    assert said[0] == ("noah", "He lets go of the knife. It rings on the floor.")      # the spared-Noah text is the first bubble
    names = [c[0] for c in mx.calls]
    assert "bench_song" in names and "ending" not in names and names.index("bench_song") < names.index("stop")
    assert ("stop",) in mx.calls                             # Mika's song is gone before the tesseract's heavy part


def test_spare_noah_with_unused_ultra_plays_the_mika_ending(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSIC", "0")
    said = []
    monkeypatch.setattr(me.speech, "run_dialog", lambda ctx, f, boxes, *a, **k: said.extend((b[0], b[1]) for b in boxes) or len(boxes))
    g, io, calls = make(tmp_path, True)
    g.jump("k7.noah_vor")
    assert g.run() == "mika-ultra"
    assert me.FINAL_LINE in " ".join(t for _w, t in said) and len(calls["credits"]) == 1
    assert me.FINAL_LINE not in " ".join(t for _w, t in io.shown)         # not on a bare terminal
    g, io, calls = make(tmp_path, False)
    g.jump("k7.noah_vor")
    assert g.run() == "let-it-live"
    assert me.FINAL_LINE not in " ".join(t for _w, t in io.shown)
