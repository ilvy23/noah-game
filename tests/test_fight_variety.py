"""The v2 fight: new patterns, arcs (calm -> build -> climax), HP thresholds, set-pieces, sfx hooks, a fuzzed whole fight."""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio  # noqa: E402
import boss  # noqa: E402
import boss_ui  # noqa: E402
import patterns  # noqa: E402
import setpieces  # noqa: E402

NEW = ["petal_rain", "fireflies", "cookie", "musicbox", "mirror", "stare", "squeeze", "weight", "heartbeat", "cage", "blackout", "pillars", "sigil"]
TURN = {p: boss.PHASES[p]["turn"] for p in (1, 2, 3, 4)}


def started(name, phase=3, seed=1, hx=20.0, hy=9.0):
    b = boss.Boss(seed=seed)
    b.phase = phase
    b.begin_enemy_turn()
    b.script, b.hp, b.hx, b.hy = [(0.0, name)], 10 ** 6, hx, hy
    b.spawn_t, b.wall_t, b.bullets = -99, 99, []
    return b


def test_at_least_twelve_new_patterns_spread_over_all_phases():
    assert len(NEW) >= 12 and all(n in patterns.PATTERNS for n in NEW)
    for ph, k in ((1, 4), (2, 4), (3, 5)):
        assert sum(1 for n in NEW if n in patterns.BY_PHASE[ph]) >= k
    assert sum(1 for n in NEW if n in patterns.BY_PHASE[4]) >= 4         # the fusion uses new ones too


def test_every_pattern_stays_in_bounds_ends_and_the_new_ones_really_hurt_an_idle_heart():
    for name in patterns.PATTERNS:
        hurt = 0
        for seed, (hx, hy) in enumerate([(4, 2), (20.5, 9), (37, 9), (12, 5), (28, 3), (8, 9), (33, 6), (20, 1)]):
            b = started(name, seed=seed, hx=hx, hy=hy)
            for _ in range(int((patterns.duration(name) + 0.6) * 30)):
                b.update(1 / 30)
                assert 0 <= b.hx <= boss.W - 1 and 0 <= b.hy <= boss.H - 1
                for h in b.hazards:
                    for x, y, ch in h.cells() + h.ghost():
                        assert 0 <= x < boss.W and 0 <= y < boss.H and isinstance(ch, str)
            assert not b.hazards and not b.script                         # the whole thing finished
            hurt += 10 ** 6 - b.hp
        if name in NEW and name not in ("fireflies", "blackout"):
            assert hurt > 0, name


def test_signatures_rage_and_calm_turns_fit_inside_their_turn():
    for ph in (1, 2, 3, 4):
        for seq in patterns.SIGNATURES[ph] + ([patterns.RAGE[ph]] if ph in patterns.RAGE else []):
            assert [t for t, _ in seq] == sorted(t for t, _ in seq) and seq[0][0] >= 1.2          # a silent beat first
            for t, n in seq:
                assert t + patterns.duration(n) <= TURN[ph] + 0.3, (ph, seq)
        for s in range(30):
            for arc in ("calm", "build"):
                for t, n in patterns.schedule(ph, 0, TURN[ph], random.Random(s), arc):
                    assert t + patterns.duration(n) <= TURN[ph] - patterns.END_MARGIN[ph] + 1e-6        # the breather at the end of the turn
                    assert arc != "calm" or n in patterns.CALM[ph]


def test_arcs_go_calm_build_climax_and_the_fusion_keeps_its_trinity():
    assert [patterns.arc_for(1, i) for i in range(5)] == ["calm", "build", "climax", "build", "climax"]
    assert [patterns.arc_for(4, i) for i in range(5)] == ["build", "trinity", "climax", "build", "climax"]       # no calm turn in the fusion
    assert [patterns.arc_for(3, i) for i in range(3)] == ["build", "build", "climax"]
    assert patterns.schedule(4, 1, 9.0, random.Random(1)) == patterns.TRINITY
    assert patterns.schedule(2, 2, 9.0, random.Random(3)) in patterns.SIGNATURES[2]
    assert patterns.schedule(3, 0, 8.0, random.Random(1), "rage") == patterns.RAGE[3]


def test_climax_turns_are_choreographed_and_use_new_patterns():
    for ph in (1, 2, 3, 4):
        assert any(n in NEW for seq in patterns.SIGNATURES[ph] for _, n in seq)
        assert len({tuple(s) for s in patterns.SIGNATURES[ph]}) >= 3


def test_orbs_turn_slowly_so_a_change_of_direction_shakes_them_off():
    b = started("fireflies", phase=1, hx=20.0, hy=5.0)
    b.update(1.05)
    orbs = [h for h in b.hazards if h.kind == "orb"]
    assert orbs
    h = orbs[0]
    a0, last = h.d["a"], h.d["a"]
    b.hx, b.hy = 38.0, 1.0                              # the heart suddenly sits somewhere else
    for _ in range(30):
        b.update(1 / 30)
        turned = abs((h.d["a"] - last + math.pi) % (2 * math.pi) - math.pi)
        assert turned <= math.radians(h.d["turn"]) / 30 + 1e-6
        last = h.d["a"]


def test_gravity_pulls_the_heart_the_box_has_a_safe_inside_and_the_dark_has_a_lit_circle():
    b = started("weight", phase=2)
    b.hy = 3.0
    ys = []
    for _ in range(90):
        b.update(1 / 30)
        ys.append(b.hy)
    assert max(ys) > 3.0 and b.hy >= 3.0                 # pulled down while "dir" is down
    # the box: a heart in the middle of it is never hurt
    b = started("squeeze", phase=2, hx=20.0, hy=5.0)
    for _ in range(int(6.0 * 30)):
        b.update(1 / 30)
        rect = [h for h in b.hazards if h.kind == "box"]
        if rect and rect[0].harmful:
            x0, x1, y0, y1 = patterns._box_rect(rect[0])
            b.hx = min(max(b.hx, x0 + 1), x1 - 1)
            b.hy = min(max(b.hy, y0 + 1), y1 - 1)
    assert b.hp == 10 ** 6
    # the dark
    b = started("blackout", phase=3)
    b.update(1.0)
    assert b.dark > 0 and boss_ui.lit(b, b.hx, b.hy) and not boss_ui.lit(b, b.hx + 15, b.hy)
    b.update(7.0)
    assert b.dark == 0 and boss_ui.lit(b, 0, 0)


def test_hp_thresholds_play_once_and_the_next_turn_is_a_rage_turn():
    b = boss.Boss(seed=1, phase=2)
    b.state = "player"
    b.enemy_hp = 17
    b.attack(0.45)                                       # a small hit that crosses 50% of 30
    assert [e for e in b.events if e[0] == "threshold"] == [("threshold", 2, 50)]
    assert b.arc == "rage" and b.rage_turn
    b.state = "player"
    b.attack(0.45)
    assert len([e for e in b.events if e[0] == "threshold"]) == 1       # not again
    assert b.arc != "rage"
    c = boss.Boss(seed=1, phase=3)
    c.state, c.enemy_hp = "player", 6
    c.attack(0.45)
    assert [e[2] for e in c.events if e[0] == "threshold"] == [20]       # the deepest line crossed
    d = boss.Boss(seed=1, phase=1)
    d.state, d.enemy_hp = "player", 14
    d.attack(0.45)
    assert not [e for e in d.events if e[0] == "threshold"]              # the sweet one has none


def test_retry_starts_the_phase_calm_again():
    b = boss.Boss(seed=1, phase=3)
    b.begin_enemy_turn()
    b.begin_enemy_turn()
    b.begin_enemy_turn()
    assert b.arc == "climax"
    b.retry_phase()
    assert b.arc == patterns.arc_for(3, 0)             # the plan starts over (green and yellow: calm)


def test_sfx_plays_only_an_existing_file_and_never_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "_sfx_last", {})
    played = []
    monkeypatch.setattr(audio, "default_backend", lambda path, loop, vol: played.append((path, loop)) or None)
    monkeypatch.setattr(audio.shutil, "which", lambda name: None)                       # (no mpv: the plain backend path)
    assert audio.sfx("slam", directory=str(tmp_path)) is None and played == []         # nothing there: silence
    (tmp_path / "sfx").mkdir()
    (tmp_path / "sfx" / "slam.wav").write_bytes(b"x")
    audio.sfx("slam", directory=str(tmp_path))
    assert played == [(str(tmp_path / "sfx" / "slam.wav"), False)]
    audio.sfx("slam", directory=str(tmp_path))                                          # within 80 ms: not restarted
    assert len(played) == 1
    monkeypatch.setenv("MUSIC", "0")
    audio._sfx_last.clear()
    audio.sfx("slam", directory=str(tmp_path))
    assert len(played) == 1
    monkeypatch.setattr(audio, "find_file", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    assert audio.sfx("slam") is None


def test_setpieces_stay_on_screen_at_any_size_and_have_text_keys():
    for name, p in setpieces.PIECES.items():
        assert p["seconds"] >= 2.0 and all(0 <= t <= p["seconds"] for t, _ in p["sfx"])
        shown = 0
        for w, h in ((245, 45), (100, 30), (40, 14), (12, 6)):
            for k in range(int(p["seconds"] * 15) + 1):
                t = k / 15
                cells = p["frame"](t, w, h, "a line of text that is long " * 3) if name.startswith("begin") else p["frame"](t, w, h, "x" * 30, 3)
                shown += len(cells)
                assert all(0 <= x < w and 0 <= y < h and 0 <= c < 10 for x, y, _ch, c in cells), (name, t)
        assert shown > 0
    assert setpieces.text_key("begin2") == "boss.beat.begin2" and setpieces.text_key("thr50", 3) == "boss.beat.thr50.3"
    assert setpieces.default_text("thr20", 4) and setpieces.amp("begin4", 3.1) > 0.5


class FuzzScreen:
    """A fake screen that presses random keys and records every set-piece and sound."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.pieces, self.said, self.frames = [], [], 0

    def key(self, timeout):
        return self.rng.choice([None, None, "left", "right", "up", "down", "a", "d", "w", "s"])

    def frame(self, b, message, who, **kw):
        self.frames += 1

    def say(self, text, who):
        self.said.append(text)

    def blackout(self, ms=0):
        pass

    def menu(self, b, opts, message=""):
        return 0 if opts[0] != "MERCY" else 0

    def timing_bar(self, b):
        return self.rng.choice([0.3, 0.7, 1.0])

    def setpiece(self, b, name, text=""):
        self.pieces.append((name, b.phase, text))


class Clock:
    def t(self):
        return 0.0


def test_a_fuzzed_whole_fight_never_crashes_plays_every_set_piece_and_finishes():
    for seed in range(4):
        b = boss.Boss(seed=seed, power=0.5, has_tesseract=bool(seed % 2))
        scr, sounds = FuzzScreen(seed), []
        f = boss_ui.Fight(b, scr, clock=Clock(), sfx=sounds.append, texts={"boss.beat.begin2": "mine now"})
        orig = b.update
        n = [0]

        def update(dt, dx=0, dy=0, orig=orig, n=n):
            n[0] += 1
            r = orig(dt, dx, dy)
            b.hp = max(b.hp, 5)                          # cannot lose here: the point is to get through every phase
            assert 0 <= b.hx <= boss.W - 1 and 0 <= b.hy <= boss.H - 1
            return r
        b.update = update
        assert f.run() == "won"
        names = [p[0] for p in scr.pieces]
        assert "begin1" not in names and {"begin2", "begin3", "begin4"} <= set(names)       # no heading at the very start
        assert ("begin2", 2, "mine now") in scr.pieces                        # the owner's text wins over the draft
        assert {"boss-hit", "phase-shift", "warning"} <= set(sounds)
        assert "noah-roar" in sounds                                          # every climax turn roars


def test_start_phase_option_starts_in_that_phase_with_its_opening_piece():
    b = boss.Boss(seed=1, phase=3)
    assert b.phase == 3 and b.enemy_hp == boss.PHASES[3]["hp"]
    scr = FuzzScreen(1)
    f = boss_ui.Fight(b, scr, clock=Clock(), sfx=lambda n: None)
    b.hp = 10 ** 6
    b._hurt = lambda *a: False
    f.run()
    assert scr.pieces[0] == ("begin3", 3, setpieces.DEFAULT_TEXT["begin3"])
