"""The scenes added on top of the three Noah scenes: valley, Mika (bench, showcase), abyss, the boss intro noise, the phase merges, defeat, decision and the
three other endings. Headless with a fake sleep: they end, stay inside the terminal, are deterministic and fire sounds; the hooks in the game call them."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boss_ui  # noqa: E402
import cine_fx  # noqa: E402
import mika_ending as me  # noqa: E402
import mika_fx  # noqa: E402
import noah_gore_fx as G  # noqa: E402
import valley_fx  # noqa: E402
from test_mika_ending import make  # noqa: E402
from test_noah_gore_fx import DummyIO, assert_inside  # noqa: E402

NEW = ["valley", "mika", "abyss", "angel", "bench", "intro", "phase2", "phase3", "phase4", "beat50", "beat20", "defeat", "decision", "ending-let", "ending-slaughter", "ending-3"]
SIZES = [(80, 24), (120, 40), (245, 45)]


def run(name, size, fps=2):
    out, sfx = io.StringIO(), []
    ctx = me.Ctx(DummyIO(), sfx=sfx.append, sleep=lambda s: None, size=lambda: size, out=out, fps=fps)
    if name not in cine_fx.ENDING_SID:                                  # the endings play their whole text as bubbles on the picture: not stubbed
        ctx.dialog = lambda *a, **k: 0                                      # these tests measure the animation frames only (bubbles: tests/test_ending_flow.py)
    me.run(ctx, only=name)
    return ctx, out.getvalue(), sfx


def test_every_new_scene_runs_on_every_size_inside_the_screen():
    for name in NEW:
        for size in SIZES:
            ctx, text, sfx = run(name, size)
            assert_inside(text, *size)
            assert text.count("\x1b[?2026h") >= 4 and text.endswith(("\x1b[?25h", "\x1b[?1049l")), (name, size)
            assert sfx or name in ("intro", "bench"), name                              # bench is silent on purpose (only the song)


def test_new_scenes_are_deterministic_and_have_a_commented_cue_table():
    for name in ("valley", "abyss", "ending-slaughter", "phase4"):
        assert run(name, (80, 24))[1] == run(name, (80, 24))[1], name
    for table in (valley_fx.VALLEY_CUES, cine_fx.PHASE_CUES, cine_fx.DEFEAT_CUES, cine_fx.LET_CUES, cine_fx.THREE_CUES, mika_fx.MIKA_CUES):
        assert table


def test_all_sound_names_exist_or_are_known_missing():
    import audio
    names = set()
    import abyss_fx
    for table in (valley_fx.VALLEY_CUES, cine_fx.INTRO_CUES, cine_fx.PHASE_CUES, cine_fx.DEFEAT_CUES, cine_fx.DECISION_CUES, cine_fx.LET_CUES,
                  cine_fx.SLAUGHTER_CUES, cine_fx.THREE_CUES, abyss_fx.ABYSS_CUES, G.BURN_CUES):
        names |= {n for _, n in table}
    have = {f[:-4] for f in os.listdir(os.path.join(os.path.dirname(audio.__file__), "soundtracks", "sfx")) if f.endswith(".mp3")}
    assert len(names & have) >= len(names) * 0.6                                          # the rest are hooks for sounds the audio agent still adds (silent until then)


def test_burn_has_the_word_rain_and_the_abyss():
    import random
    sc = G.BurnScene(120, 39, random.Random(1))
    cv = G.Canvas(120, 39)
    for i in range(int(20.0 * 15)):
        sc.draw(cv, i / 15.0, 1 / 15.0)
    assert len(sc.rain.words) > 20 and {w["k"] for w in sc.rain.words} == {"h", "f"}      # hate and forgiveness at once
    assert any(w["text"] in G.HATE for w in sc.rain.words) and any(w["text"] in G.FORGIVE for w in sc.rain.words)
    assert sc.rain.level(2.0) == 0 and sc.rain.level(20.0) > 0.5 and sc.rain.level(35.0) == 0


def test_water_simulation_stays_bounded_and_settles():
    wt = valley_fx.Water(60, 12)
    wt.poke(30, 6, 1.5)
    for _ in range(80):
        wt.step()
    assert max(abs(v) for r in wt.a for v in r) <= 2.0
    for _ in range(1500):
        wt.step()
    assert max(abs(v) for r in wt.a for v in r) < 0.05


def test_mika_is_drawn_standing_and_sitting():
    for sit in (False, True):
        f = mika_fx.MikaFigure(30, sit)
        g, joint = f.cells(1.0, eyes=1.0, inhale=0.5)
        assert sum(1 for r in g for c in r if c) > 100 and (joint is not None) == sit
        assert sum(1 for r in f.cells(1.0, reveal=0.3)[0] for c in r if c) < sum(1 for r in g for c in r if c)      # dissolve in


def test_the_old_boss_intro_is_back_no_full_screen_noise_scene():
    assert not hasattr(boss_ui, "intro_scene")


def test_game_hooks_call_the_scenes_in_order(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cine_fx, "run_named", lambda ctx, name, seed=1: calls.append(name))
    g, io_, _ = make(tmp_path, False)
    g.cinematics = True
    g.fight_only()
    assert calls == ["defeat", "decision", "ending-let"]
    calls.clear()
    g.cinematics = False
    g.show_ending("slaughter-it")
    assert calls == []                                                                    # headless runs and tests never play scenes
    g.cinematics = True
    for name, scene in (("slaughter-it", "ending-slaughter"), ("ending-3", "ending-3")):
        calls.clear()
        g.show_ending(name)
        assert calls == [scene]


def test_lrc_parser_and_the_lyrics_layer_with_a_nonsense_file(tmp_path):
    import lyrics_fx
    f = tmp_path / "x.lrc"
    f.write_text("[ar:nobody]\n[00:01.00]blorp zim\n[00:02.50]quux\n[00:05.00]frib frab\nnot a line\n[01:00.5]late\n", encoding="utf-8")
    lines = lyrics_fx.load(str(f))
    assert lines == [(1.0, "blorp zim"), (2.5, "quux"), (5.0, "frib frab"), (60.5, "late")]
    assert lyrics_fx.load(str(tmp_path / "missing.lrc")) == []                                     # no file: nothing, no crash
    layer = lyrics_fx.Layer(lines, start=10.0)                                                       # song position = 10 s + scene time
    assert [t for _, t in layer.visible(0.0)] == ["blorp zim", "quux", "frib frab"]                   # lines up to 9 s old are still standing
    assert lyrics_fx.Layer(lines, 0.0).visible(0.5) == [] and [t for _, t in lyrics_fx.Layer(lines, 0.0).visible(3.0)] == ["blorp zim", "quux"]
    layer = lyrics_fx.Layer(lines, start=0.0)
    cv = G.Canvas(60, 20)
    layer.draw(cv, 3.0)
    rows = ["".join(cv.ch[y * 60:(y + 1) * 60]).rstrip() for y in range(20)]
    shown = [(y, r) for y, r in enumerate(rows) if r.strip()]
    assert [r.strip() for _, r in shown] == ["blorp zim", "quux"] and shown[0][0] < shown[1][0]       # newest at the bottom, standing on top of each other
    assert all(r.endswith(("zim", "quux")) and len(r) == 60 - 3 for _, r in shown)                    # right-aligned
    lyrics_fx.Layer([], 0).draw(cv, 3.0)
    assert lyrics_fx.Layer(lines, 0).visible(100.0) == []                                            # old lines are gone after `life`


def test_the_real_lrc_if_present_parses_without_crashing():
    import lyrics_fx
    lines = lyrics_fx.load(lyrics_fx.default_path())
    assert lines == sorted(lines, key=lambda x: x[0])


def test_play_section_starts_at_the_offset_and_fades(tmp_path):
    import audio
    (tmp_path / "song.flac").write_bytes(b"x")
    seen = []

    class P:
        def __init__(self, path, loop, volume, start=0.0):
            seen.append(("start", os.path.basename(path), volume, start))
            self.volume = volume

        def set_volume(self, v):
            seen.append(("vol", round(v)))

        def stop(self):
            seen.append(("stop",))

        def alive(self):
            return True
    m = audio.Mixer(backend=P, sleep=lambda s: None, table={"default": ["x"], "fallback": []}, directory=str(tmp_path))
    m.play_section("song", 135.0, 140.0, fade_in=1.0, fade_out=1.0, volume=80)
    for th in m.threads:
        th.join(2)
    assert seen[0] == ("start", "song.flac", 0, 135.0) and ("vol", round(80 * 10 ** (audio.MUSIC_MASTER_DB / 60.0))) in seen and seen[-1] == ("stop",)
    assert m.play_section("nothere", 0, None) is None


def test_burn_song_setting_and_scaling():
    cfg = me.noah_burns_song()
    assert cfg["file"] == "noah-burns-song" and cfg["start"] == 135.0 and cfg["end"] == 210.0
    caps = G.scale_captions([(1.0, 2.0, "a")], 2.0)
    assert caps == [(2.0, 4.0, "a")] and G.scale_cues([(1.0, "x")], 3.0) == [(3.0, "x")]
    cv = G.Canvas(20, 10)
    cv.put(2, 2, "x", (255, 0, 0), None)
    G.push_in(cv, 2.0, 0.0, 0.0)
    assert cv.ch[4 * 20 + 4] == "x"                                                                  # a push-in on the top left corner doubles the picture


def test_connor_leads_and_the_bench_has_no_joint_sounds():
    import random
    sc = valley_fx.ValleyScene(120, 39, random.Random(1))
    assert sc.cult[0].get("connor") and sc.first is not None
    assert mika_fx.BENCH_CUES == {"intro": [], "end": []}
    names = {n for _, n in mika_fx.MIKA_CUES}
    assert not any("joint" in n or "lighter" in n for n in names)
