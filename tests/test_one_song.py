"""After the fusion is beaten only ONE song is audible at any moment: the boss song is silent before the defeat scene, the decision and every ending
(a model mixer: the fight screen starts a fade that keeps the boss song audible until wait_silent)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cine_fx  # noqa: E402
import mika_ending  # noqa: E402
from test_mika_ending import make  # noqa: E402


class ModelMixer:
    enabled = True

    def __init__(self):
        self.audible, self.fading, self.max, self.log = set(), set(), 0, []

    def _start(self, name):
        self.audible.add(name)
        self.max = max(self.max, len(self.audible))
        self.log.append(("start", name, sorted(self.audible)))

    def enter_place(self, place):
        self.audible.clear()
        self._start("place-" + place)

    def boss_song(self):
        self.audible.clear()
        self._start("boss")

    def fight_over(self):                       # what boss_ui's on_end does: a fade thread, the song stays audible until it has finished
        self.fading = {"boss"}

    def wait_silent(self, timeout=10.0):
        self.audible -= self.fading
        self.fading = set()

    def fade_out(self, fade=None):
        self.audible.clear()
        self.fading = set()

    def ending(self, name):
        self.fade_out()
        self._start("ending-" + name)

    def bench_song(self):
        self._start("mika")

    def mika_ending_song(self, key):             # a crossfade between two Mika-ending songs: the new one replaces the old
        self.audible.discard("mika")
        self._start("mika-" + key)

    def stop(self):
        self.audible.clear()

    def __getattr__(self, name):                # every other mixer call (scene_start, impact ...) is irrelevant here
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None


def run_to_end(tmp_path, monkeypatch, ending, unused=False):
    m = ModelMixer()
    seen = []
    monkeypatch.setattr(cine_fx, "run_named", lambda ctx, name, seed=1: seen.append((name, sorted(m.audible))))
    monkeypatch.setattr(mika_ending, "run", lambda ctx: (m.bench_song(), m.mika_ending_song("x")))
    g, io_, calls = make(tmp_path, unused, choice=0 if ending != "slaughter-it" else 1, timeout=ending == "ending-3")
    g.mixer = m
    g.cinematics = True

    def boss(lines, power):
        m.boss_song()
        m.fight_over()
        m.max = 0                                # from here on: how many songs are audible together?
        return "won"
    g.boss_runner = boss
    g.ultra_unused = unused
    got = g.finale("boss")
    return m, seen, got


def test_only_one_song_is_audible_from_the_end_of_the_fight_through_every_ending(tmp_path, monkeypatch):
    for ending, unused in (("let-it-live", False), ("slaughter-it", False), ("ending-3", False), ("mika-ultra", True)):
        m, seen, got = run_to_end(tmp_path, monkeypatch, ending, unused)
        assert got == ending, (ending, got)
        assert m.max <= 1, (ending, m.log)
        assert seen and all("boss" not in audible for _n, audible in seen), (ending, seen)       # silent for the defeat scene and the decision
        assert not [e for e in m.log if e[0] == "start" and "boss" in e[2] and e[1] != "boss"], (ending, m.log)
