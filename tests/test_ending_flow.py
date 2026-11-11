"""The ending's flow, audio levels and bubbles: no bare text, music/smoke order, special song hook, KDE fullscreen, quiet effects."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio  # noqa: E402
import fourth_wall_fx as F  # noqa: E402
import mika_ending as me  # noqa: E402
import noah_gore_fx as G  # noqa: E402
import speech  # noqa: E402
from test_audio import Fake, TABLE, make  # noqa: E402
from music_harness import make_mixer  # noqa: E402


class DummyIO:
    def __init__(self):
        self.shown = []

    def show(self, text, who="narrator"):
        self.shown.append((who, text))


def test_volume_constants_effects_in_front_music_lower_screams_distant():
    assert audio.MUSIC_MASTER_DB <= 6 and 60 <= audio.SFX_VOLUME <= 100          # effects: plain one-shots a little under the file level, no ducking
    big, normal, ambient, scream = (audio.sfx_level_db(n) for n in ("impact-boom-huge", "boss-hit", "glow-hum-rising", "scream-fire"))
    assert big > ambient + 4 and big > scream + 8 and normal > scream                                # big impacts in front, ambience quiet, screams distant
    assert abs(audio.db_to_pct(-18.0) - 50.0) < 0.5 and abs(audio.db_to_pct(-60.0) - 10.0) < 0.1      # mpv's volume is CUBIC: 50 % is -18 dB
    f = audio.sfx_filter("scream-fire", 5.0, 12.0)
    assert f.startswith("volume=") and "lowpass" in f and "afade=t=in:st=0:d=0.025" in f and "afade=t=out:st=4.950:d=0.050" in f
    assert audio.SFX_FADE_IN <= 0.03 and 0.03 <= audio.SFX_FADE_OUT <= 0.06 and audio.DUCK_ATTACK >= 0.12 and 0.7 <= audio.DUCK_RELEASE <= 1.2
    assert audio.load_table()["noah_burns_song"]["fade_in"] >= 10 and audio.load_table()["noah_burns_song"]["fade_out"] >= 5


def test_ramps_are_smooth_many_small_monotonic_steps():
    c = audio.ramp_curve(30)
    assert len(c) == 30 and c == sorted(c) and c[-1] == 1.0 and max(b - a for a, b in zip([0.0] + c, c)) < 0.08     # no step above 8 % of the range
    from music_harness import Rec
    p = Rec("/x/a.flac", False, 0)
    mx = audio.Mixer(backend=Rec, sleep=lambda s: None, table=TABLE)
    Rec.events = []
    mx._ramp("a", p, 0, 100, 3.0, mx.gen)
    vols = [e[4] for e in Rec.events if e[3] == "vol"]
    assert len(vols) >= 90 and vols == sorted(vols) and max(b - a for a, b in zip(vols, vols[1:])) < 5.0        # >= 30 steps per second, tiny steps
    Rec.events = []
    mx._ramp("a", p, 100, 0, 1.0, mx.gen)
    v = [e[4] for e in Rec.events if e[3] == "vol"]
    assert len(v) >= 30 and v == sorted(v, reverse=True) and v[-1] < 1.0


def test_effect_edges_are_faded_no_click_first_and_last_samples_near_zero():
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        return
    d = os.path.join(audio.SOUNDTRACK_DIR, "sfx")
    for name in ("impact-boom-huge", "glass-crack", "static-burst", "typing-fast", "scream-fire", "sob-small", "system-error-beep"):
        path = audio.find_file(name, d)
        dur, cap = audio.duration(path), audio.SFX_MAX.get(name, audio.SFX_MAX_DEFAULT)
        chain = audio.sfx_filter(name, dur, cap)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-t", "%.3f" % min(dur, cap), "-af", chain, "-ac", "1", "-ar", "48000", "-f", "s16le", "-"],
                             capture_output=True, timeout=60).stdout
        import struct
        n = len(raw) // 2
        smp = struct.unpack("<%dh" % n, raw[:n * 2])
        assert n > 2000 and max(abs(x) for x in smp[:4]) < 60 and max(abs(x) for x in smp[-4:]) < 60, (name, smp[:4], smp[-4:])      # starts and ends at ~0


def test_sfx_pool_sends_gain_and_fades_to_a_long_lived_player_instead_of_spawning_one_per_effect():
    sent, spawned = [], []

    class Proc:
        def poll(self):
            return None
    pool = audio.SfxPool(size=3, spawn=lambda sock: spawned.append(sock) or Proc(), send=lambda sock, cmds: sent.append((sock, cmds)))
    a = pool.play("/x/a.mp3", "volume=-8.0dB,afade=t=in:st=0:d=0.025", 2.0)
    b = pool.play("/x/b.mp3", "volume=-9.0dB", 2.0)
    c = pool.play("/x/c.mp3", "volume=-9.0dB", 2.0)
    d = pool.play("/x/d.mp3", "volume=-9.0dB", 2.0)
    assert len(spawned) == 3 and len({x[0] for x in sent[:3]}) == 3                      # three long-lived players, reused for the fourth effect
    assert sent[0][1] == [["set_property", "af", "lavfi=[volume=-8.0dB,afade=t=in:st=0:d=0.025]"], ["loadfile", "/x/a.mp3", "replace"]]
    assert sent[3][0] == sent[0][0] and a.alive() is False and d.alive()               # the oldest one was taken over


def test_music_ducks_while_an_effect_plays_and_comes_back(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    p = m.music[1]
    m.duck(-6.0, 0.0)
    for t in list(m.threads):
        t.join(timeout=5)
    ducked = [e[2] for e in m.log if e[0] == "vol"]
    assert m.duck_f == 1.0 and abs(p.volume - audio.db_to_pct(audio.MUSIC_MASTER_DB)) < 0.1                                                   # back to full, smoothly


def test_bench_song_starts_with_the_smoke_sound_at_once(tmp_path):
    m = make(tmp_path)
    slept = []
    m.sleep = slept.append
    m.bench_song()
    m.wait()
    starts = [e[1] for e in m.log if e[0] == "start"]
    assert starts[:2] == ["mika-smoke", "mika"] and m.current() == "mika"
    assert 7.0 not in slept                                           # no waiting for half of the smoke sound: the song starts together with it


def test_fade_out_async_does_not_block(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    m.sleep = lambda s: None
    m.fade_out_async(3.5)
    m.wait()
    assert m.current() is None


def test_special_ending_song_is_used_when_present_else_mika(tmp_path):
    table = dict(TABLE, endings={"mika-ultra": "mika"}, endings_special={"mika-ultra": "ending-special"})
    (tmp_path / "mika.flac").write_bytes(b"x")
    assert audio.ending_track("mika-ultra", table, str(tmp_path)) == "mika"                   # missing: fall back to Mika's song
    (tmp_path / "ending-special.mp3").write_bytes(b"x")
    assert audio.ending_track("mika-ultra", table, str(tmp_path)) == "ending-special"
    real = audio.load_table()
    assert real["endings_special"]["mika-ultra"] == "ending-special"
    assert real["noah_burns_song"]["fade_in"] >= 10 and real["noah_burns_song"]["fade_out"] >= 5     # song fades


def test_speech_bubbles_are_drawn_on_the_animation_without_printing_bare_text():
    class Scene:
        def __init__(self, w, h, rng):
            pass

        def draw(self, cv, t, dt):
            cv.put(3, 3, "#", (200, 50, 50), (10, 0, 0))
            return 0, 0
    for width, panel in ((100, False), (245, True)):
        out, io_ = io.StringIO(), DummyIO()
        ctx = me.Ctx(io_, sleep=lambda s: None, size=lambda: (width, 40), out=out, fps=4)
        n = ctx.dialog(Scene, [("mika", "Man... that was a lot of floor.", (0.5, 0.5)), ("narrator", "The water stays flat.", None),
                               ("mika", "Chilling now, man.", (0.5, 0.5))], 0.0, 2.0)
        text = out.getvalue()
        assert n == 3 and io_.shown == []
        assert "╭" in text and "╯" in text and "MIKA" in text and text.count("\x1b[?2026h") >= 6 and "\n" not in text
        assert ("◀" in text) == panel                                                       # the pointer line leaves the right panel; the strip has none
        assert [e[1:] for e in ctx.log if e[0] == "say"][0] == ("mika", "Man... that was a lot of floor.")


def test_bubbles_never_cover_the_middle_of_the_frame():
    for w, h in ((245, 44), (120, 39), (100, 39)):
        for anchor in ((0.5, 0.5), None, (0.1, 0.9)):
            x, y, bw, lines, px = speech.layout(w, h, "mika", "x " * 150, anchor)
            assert y + len(lines) + 2 <= h - 1 and x >= 1 and x + bw <= w
            if w >= speech.PANEL_MIN_COLS:
                assert x >= w - 52 and bw <= 50                                              # a column at the right edge: the centre stays free
            else:
                assert y > h // 2 - 2 or len(lines) < 6                                      # a strip at the bottom
    cv = G.Canvas(245, 44)
    cv.fg = [(200, 200, 200)] * (245 * 44)
    speech.draw_bubble(cv, "noah", "Hello there.", 99, (0.5, 0.5), 0.0, [("mika", "one"), ("noah", "two"), ("mika", "three")])
    mid = [cv.ch[y * 245 + x] for y in range(5, 40) for x in range(60, 150)]
    assert set(mid) <= {" "}                                                                  # nothing drawn in the middle
    assert cv.fg[10 * 245 + 220] != (200, 200, 200) or cv.bg[10 * 245 + 220] != (0, 0, 0)    # the panel is dimmed backing


def test_credits_start_by_themselves_after_the_ending_and_stdin_is_flushed(tmp_path, monkeypatch):
    import story_game as sg
    from test_mika_ending import make as make_game
    monkeypatch.setenv("MUSIC", "0")
    flushed, order = [], []
    monkeypatch.setattr(sg, "flush_stdin", lambda: flushed.append(1))
    monkeypatch.setattr(me, "run", lambda ctx, only=None: order.append("ending"))
    g, io_, calls = make_game(tmp_path, True)
    io_.pause = lambda: order.append("PAUSE")
    g.credits_runner = lambda b, s: order.append("credits")
    g.show_mika_ending()
    assert order == ["ending", "credits"] and flushed == [1]                                      # no Enter press in between


def test_kde_fullscreen_toggles_once_verifies_by_size_and_restores():
    log, size = [], [(120, 40)]

    def run(argv):
        log.append(list(argv))
        if argv == F.KDE_ARGV:
            size[0] = (245, 45) if len(log) == 1 else (120, 40)
        return ""
    env = {"XDG_CURRENT_DESKTOP": "KDE", "WAYLAND_DISPLAY": "wayland-0", "TERM": "foot"}
    fs = F.Fullscreen(env=env, run=run)
    assert fs.start(lambda d: None, lambda: size[0]) and fs.did == "kde" and log == [F.KDE_ARGV]
    fs.stop()
    assert log == [F.KDE_ARGV, F.KDE_ARGV] and size[0] == (120, 40)
    fs.stop()
    assert len(log) == 2                                                                         # stop is idempotent: restored once
    # size never changes: assume it did not work (or was already fullscreen) and do NOT toggle back
    log.clear()
    fs = F.Fullscreen(env=env, run=lambda a: log.append(list(a)) or "")
    assert not fs.start(lambda d: None, lambda: (120, 40)) and fs.did is None
    fs.stop()
    assert log == [F.KDE_ARGV]
    log.clear()
    assert not F.Fullscreen(env=dict(env, FOLK_FULLSCREEN="0"), run=lambda a: log.append(a)).start(lambda d: None, lambda: (1, 1)) and not log


def test_busctl_is_exactly_one_allowed_command(monkeypatch):
    assert F.KDE_ARGV in F.ALLOWED_ARGV and F.KDE_ARGV[0] == "busctl" and "Window Fullscreen" in F.KDE_ARGV
    seen = []
    monkeypatch.setattr(F.subprocess, "run", lambda argv, **k: seen.append((list(argv), k)) or type("R", (), {"stdout": ""})())
    F._run(["busctl", "--user", "call", "org.kde.kglobalaccel", "/component/kwin", "org.freedesktop.DBus.Peer", "Ping"])
    F._run(["busctl", "--user", "introspect", "x"])
    assert not seen
    F._run(F.KDE_ARGV)
    assert seen and seen[0][1]["timeout"] == 2 and "shell" not in seen[0][1]


def test_static_phase_is_long_music_free_and_the_switch_off_is_silent():
    assert F.STATIC_LEN >= 20 and F.OFF_T - F.STATIC_T == F.STATIC_LEN
    assert all(t < F.OFF_T for t, _ in F.CUES) and F.SECONDS - F.BLACK_T <= 0.5                   # black, then the credits at once
    ctx = me.Ctx(DummyIO(), sfx=lambda n: None, sleep=lambda s: None, size=lambda: (80, 24), out=io.StringIO(), fps=2)
    ctx.info = {"user": "u", "host": "h", "time": "1", "cols": 80, "rows": 24, "cwd": "c", "uptime": "1h", "load": "0", "up_s": 1.0, "mon": "Nov 08",
                "greeting": "hi", "session": "1s"}
    calls = []

    class Mx:
        def __getattr__(self, n):
            if n in ("voice", "dir", "enabled", "backend", "log"):
                raise AttributeError(n)
            return lambda *a: calls.append((n,) + a)
    ctx.mixer = Mx()
    me.fourth_wall(ctx)
    assert calls[0] == ("stop",) and calls[-1] == ("stop",) and ("mika_ending_song", "fourth-wall") not in calls
