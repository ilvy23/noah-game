"""At most ONE song is audible at any moment through the whole Mika ending, the other endings and the defeat / decision flow (crossfades and fade-outs excepted)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio  # noqa: E402
import mika_ending as me  # noqa: E402
import noah_gore_fx as G  # noqa: E402
from music_harness import Rec, SCALE, make_mixer, overlaps  # noqa: E402
from test_mika_ending import make  # noqa: E402

LIMIT = 7.0          # virtual seconds: the longest intended crossfade is 3.5 s; a real overlap lasts for a whole scene


def run_flow(tmp_path, monkeypatch, unused, choice, timeout=False, jump="k7.noah_vor"):
    monkeypatch.setenv("MUSIC", "1")
    monkeypatch.setattr(G, "FPS", 2)
    mixer = make_mixer(tmp_path, audio)
    g, io, calls = make(tmp_path, unused, timeout=timeout, choice=choice)
    g.mixer = mixer
    g.sleep = lambda s: time.sleep(min(s, 0.002))
    g.cinematics = True
    g.credits_runner = lambda b, s: mixer.wait()
    g.jump(jump)
    g.run()
    mixer.wait()
    mixer.stop()
    return overlaps(Rec.events, LIMIT * 0)


def test_the_whole_mika_ending_never_plays_two_songs_on_top_of_each_other(tmp_path, monkeypatch):
    bad = [o for o in run_flow(tmp_path, monkeypatch, True, 0) if o[1] > LIMIT]
    assert not bad, bad


def test_the_other_endings_and_the_defeat_decision_flow(tmp_path, monkeypatch):
    for unused, choice, timeout in ((False, 0, False), (False, 1, False), (False, 0, True)):
        d = tmp_path / ("e%d%d%d" % (unused, choice, timeout))
        d.mkdir()
        bad = [o for o in run_flow(d, monkeypatch, unused, choice, timeout) if o[1] > LIMIT]
        assert not bad, (unused, choice, timeout, bad)


def test_a_song_section_takes_over_whatever_is_still_playing(tmp_path):
    mixer = make_mixer(tmp_path, audio)
    mixer.enter_place("schloss")
    mixer.wait()
    mixer.crossfade("boss-noa", loop=True, fade=0.5)
    mixer.wait()
    mixer.play_section("noah-burns-song", 135.0, 160.0, 4.0, 2.0)
    mixer.wait()
    mixer.sleep(0)
    alive = [e for e in Rec.events if e[3] == "start"]
    assert [o for o in overlaps(Rec.events) if o[1] > LIMIT] == []
    assert alive[-1][2] == "noah-burns-song"
