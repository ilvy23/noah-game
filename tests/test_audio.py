"""audio.py with fake players: alternation, crossfade, no overlap outside fades, sequences, cleanup."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio  # noqa: E402

TABLE = {"default": ["game-1", "game-2"], "fallback": ["town"], "strange_places": ["schloss"],
         "strange": {"tape": "strange-tape", "track": "strange"},
         "noah": {"main": "noa-main", "alt": "noa-alt", "mood": "noa-mood", "rip": "noa-rip", "boss": "boss-noa"},
         "mika": {"smoke": "mika-smoke", "track": "mika"}, "connor": {"track": "connor"},
         "endings": {"let-it-live": "ending-let-it-live", "ending-3": "ending-3"}, "fade": 2.0, "boss_intro_seconds": 52}


class Fake(audio.Player):
    can_fade = True
    live = []

    def __init__(self, path, loop, volume):
        super().__init__(path, loop, volume)
        self.up = True
        Fake.live.append(self)

    def alive(self):
        return self.up

    def stop(self):
        self.up = False


def make(tmp_path, names=("game-1", "game-2", "strange", "strange-tape", "noa-main", "noa-alt", "noa-mood", "noa-rip",
                          "boss-noa", "mika", "mika-smoke", "connor", "ending-let-it-live", "ending-3")):
    for n in names:
        (tmp_path / (n + ".flac")).write_bytes(b"x")
    Fake.live = []
    return audio.Mixer(backend=Fake, sleep=lambda s: None, table=TABLE, directory=str(tmp_path))


def names(m):
    return [e for e in m.log if e[0] == "start"]


def test_default_music_starts_and_two_tracks_alternate(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    assert m.current() == "game-1"
    m.gen += 1                     # stop the background poller, drive it by hand
    m.music[1].up = False          # first track ended by itself
    assert m.tick() and m.current() == "game-2"
    m.stop()


def test_crossfade_overlaps_only_during_the_fade_and_old_player_is_stopped(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    m.scene_start("connor")
    m.wait()
    assert m.current() == "connor"
    alive = [p for p in Fake.live if p.alive()]
    assert len(alive) == 1 and alive[0].path.endswith("connor.flac")
    vols = [e for e in m.log if e[0] == "vol"]
    assert vols and any(e[1] == "connor" and e[2] == 100 for e in vols)
    m.stop()
    assert not [p for p in Fake.live if p.alive()]


def test_strange_place_plays_tape_then_loops_strange(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    m.enter_place("schloss")
    m.wait()
    started = [e[1] for e in names(m)]
    assert started.index("strange-tape") < started.index("strange")
    assert m.current() == "strange"
    m.enter_place("lunuen")
    m.wait()
    assert m.current() in ("game-1", "game-2")
    m.stop()


def test_noah_variants_and_scene_end_returns_to_place_music(tmp_path):
    m = make(tmp_path)
    m.enter_place("nook")
    m.wait()
    m.scene_start("noah", "alt")
    assert m.current() == "noa-alt"
    m.scene_end()
    m.wait()
    assert m.current() in ("game-1", "game-2")
    m.scene_start("noah", "main")
    assert m.current() == "noa-main"
    m.stop()


def test_mika_scene_starts_with_his_song_and_the_smoke_plays_on_top_with_ducking(tmp_path):
    m = make(tmp_path)
    m.enter_place("see")
    m.wait()
    m.scene_start("mika")
    m.wait()
    assert m.current() == "mika"                                   # his melody from the first moment, with the smoke sound
    started = [e[1] for e in names(m)]
    assert started.index("mika") < started.index("mika-smoke") and m.current() == "mika"
    vols = [e[2] for e in m.log if e[0] == "vol" and e[1] == "mika"]
    assert min(vols) <= 56 and abs(vols[-1] - 100) < 1e-6                          # ducked while the smoke sound plays, then back
    m.stop()


def test_boss_intro_ramps_to_full_volume_then_phase_two_crossfades(tmp_path):
    m = make(tmp_path)
    m.boss_intro()
    m.wait()
    vols = [e[2] for e in m.log if e[0] == "vol" and e[1] == "noa-mood"]
    assert ("start", "noa-rip", 100) in m.log and ("start", "noa-mood", 3) in m.log
    assert vols[0] < vols[len(vols) // 2] < vols[-1] == 100
    m.boss_phase_two()
    m.wait()
    assert m.current() == "boss-noa"
    m.stop()


def test_ending_track_replaces_everything(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    m.ending("ending-3")
    assert m.current() == "ending-3"
    assert len([p for p in Fake.live if p.alive()]) == 1
    m.stop()


def test_missing_files_and_disabled_player_are_silent(tmp_path):
    m = make(tmp_path, names=())
    m.enter_place("lunuen")
    m.scene_start("noah", "alt")
    m.mika_smoke()
    m.boss_intro()
    m.wait()
    assert m.current() is None
    off = audio.Mixer(backend=Fake, sleep=lambda s: None, table=TABLE, directory=str(tmp_path), enabled=False)
    off.enter_place("lunuen")
    assert off.current() is None


def test_newer_request_cancels_the_old_sequence(tmp_path):
    m = make(tmp_path)
    m.enter_place("schloss")
    m.enter_place("lunuen")      # leaves the strange place at once
    m.wait()
    assert m.current() in ("game-1", "game-2")
    m.stop()


def test_places_and_special_scenes_have_songs_of_their_own(tmp_path):
    table = dict(TABLE, places={"lunuen": "lunuen", "wald": "wald"}, scenes={"keller": "keller", "clair": "noah-clair"})
    for n in ("game-1", "game-2", "lunuen", "wald", "keller", "noah-clair"):
        (tmp_path / (n + ".flac")).write_bytes(b"x")
    Fake.live = []
    m = audio.Mixer(backend=Fake, sleep=lambda s: None, table=table, directory=str(tmp_path))
    m.enter_place("lunuen")
    m.wait()
    assert m.current() == "lunuen"
    m.scene_start("keller")
    m.wait()
    assert m.current() == "keller"
    m.scene_end()
    m.wait()
    assert m.current() == "lunuen"                              # back to the song of the place
    m.enter_place("wald")
    m.wait()
    assert m.current() == "wald"
    m.stop()


def test_a_cancelled_crossfade_never_pushes_the_incoming_song_to_full_volume(tmp_path):
    m = make(tmp_path)
    m.enter_place("lunuen")
    m.wait()
    old = m.music
    new = Fake(str(tmp_path / "connor.flac"), True, 0)
    gen = m.gen
    m.gen += 1                                                   # a newer request arrives: this fade is cancelled
    m._fade_pair(old, "connor", new, 2.0, gen)
    assert not [e for e in m.log if e[0] == "vol" and e[1] == "connor" and e[2] == 100]
    assert not old[1].alive()                                    # the old song is stopped, not left running


def test_mika_scene_on_the_lake_has_only_his_song_not_a_place_song(tmp_path):
    table = dict(TABLE, places={"lunuen": "lunuen"})
    for n in ("game-1", "game-2", "lunuen", "mika", "mika-smoke"):
        (tmp_path / (n + ".flac")).write_bytes(b"x")
    Fake.live = []
    m = audio.Mixer(backend=Fake, sleep=lambda s: None, table=table, directory=str(tmp_path))
    m.enter_place("see")
    m.scene_start("mika")
    m.wait()
    assert m.current() == "mika" and len([p for p in Fake.live if p.alive() and "mika-smoke" not in p.path]) == 1
    m.stop()


def test_cancelled_fade_in_does_not_leave_the_song_half_quiet(tmp_path):
    m = make(tmp_path)
    calls = []

    def sleep(s):
        calls.append(s)
        if len(calls) == 5:
            m.gen += 1                               # a newer request cancels the running crossfade
    m.sleep = sleep
    m.crossfade("game-1", loop=False)
    m.crossfade("game-2", loop=False)
    m.wait()
    vols = [e[2] for e in m.log if e[0] == "vol" and e[1] == "game-2"]
    assert vols[-1] == 100
    assert [p for p in Fake.live if p.up] == [m.music[1]]


def test_wait_silent_blocks_until_a_background_fade_out_has_stopped_the_song(tmp_path):
    import threading
    import time
    m = make(tmp_path)
    m.sleep = lambda s: time.sleep(0.01)
    m.crossfade("game-1", loop=False)
    t = threading.Thread(target=m.fade_out, daemon=True)
    t.start()
    m.wait_silent()
    assert [p for p in Fake.live if p.up] == [] and m.current() is None


def test_boss_song_is_silent_when_the_decision_starts(tmp_path):
    import threading
    import time
    import json
    import story_game as sg
    story = json.load(open(sg.STORY, encoding="utf-8"))
    m = make(tmp_path)
    m.sleep = lambda s: time.sleep(0.01)
    seen = []

    class IO:
        def show(self, text, who="narrator"):
            if "k7.entscheidung" not in seen and who == "noah":
                seen.append(m.current())

        def pick(self, o, aliases=None):
            return 0

        def timed_pick(self, o, s, t=None):
            return 0

        def pause(self):
            pass

    def boss(lines, power):
        m.crossfade("game-1", loop=False)
        threading.Thread(target=m.fade_out, daemon=True).start()          # like boss_ui's end-of-fight fade
        return "won"
    g = sg.Game(io=IO(), story=story, mixer=m, boss_runner=boss, credits_runner=lambda b, s: None, save_path=str(tmp_path / "s.json"))
    g.finale("boss")
    assert seen and seen[0] is None
