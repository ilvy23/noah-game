"""Patterns, ultra tesseract rules, portraits/animation data, layout without overlap, cinematics, gallery pages."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boss  # noqa: E402
import boss_ui  # noqa: E402
import gallery  # noqa: E402
import patterns  # noqa: E402
import portraits  # noqa: E402
import ultra_fx  # noqa: E402


def test_every_pattern_is_telegraphed_fair_and_deterministic():
    for name, fn in patterns.PATTERNS.items():
        a = fn(random.Random(4), 20, 9, 0.5)
        b = fn(random.Random(4), 20, 9, 0.5)
        assert a and [(h.kind, h.warn, h.d.get("x")) for h in a] == [(h.kind, h.warn, h.d.get("x")) for h in b], name
        for h in a:
            assert h.warn >= 0.6 and h.ghost(), name                      # always a visible warning first
            assert h.cells() == []                                        # harmless while only the ghost shows
            for k in range(1, 20):
                h.age = h.warn + h.live * k / 20
                assert len({(x, y) for x, y, _ in h.cells()}) < 0.55 * patterns.W * patterns.H, name   # never fills the arena


def test_each_personality_has_at_least_three_patterns_and_the_schedule_is_seeded():
    for ph in (1, 2, 3):
        assert len(patterns.BY_PHASE[ph]) >= 3
    assert patterns.schedule(2, 0, 9.0, random.Random(1)) == patterns.schedule(2, 0, 9.0, random.Random(1))
    assert patterns.schedule(4, 1, 9.0, random.Random(1)) == patterns.TRINITY
    assert [n for _, n in patterns.schedule(4, 1, 9.0, random.Random(1))] == [n for _, n in patterns.TRINITY]


def test_phase_pressure_rises_green_to_fusion():
    def n(ph):
        # patterns per second in a build turn, averaged over seeds
        return sum(len(patterns.schedule(ph, 0, boss.PHASES[ph]["turn"], random.Random(s), "build")) for s in range(100)) / 100 / boss.PHASES[ph]["turn"]
    assert n(1) < n(2) < n(3) < n(4)
    assert boss.PHASES[4]["rate"] >= boss.PHASES[3]["rate"]                    # (the fusion's words are rarer, its patterns are denser)


def test_patterns_hurt_once_and_a_whole_fight_stays_deterministic():
    def run(seed):
        b = boss.Boss(seed=seed)
        out = []
        for ph in (1, 2, 3, 4):
            b.phase = ph
            b.begin_enemy_turn()
            b.hp = 10 ** 6
            for _ in range(int(b.cfg["turn"] / 0.05)):
                b.update(0.05)
            out.append((len(b.events), b.hp))
        return out
    assert run(3) == run(3)
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    b.hazards = [patterns.Hazard("rect", 0.1, 5.0, dmg=3, x=0, y=0, w=41, h=11, ch="#", tele="!")]
    b.script = []
    b.update(0.2)
    assert b.hp == boss.PLAYER_HP - 3
    b.update(1.0)
    assert b.hp == boss.PLAYER_HP - 3                                       # one hit per hazard


def test_honey_slows_the_heart():
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    b.hazards = [patterns.Hazard("drip", 0.0, 3.0, dmg=2, x=int(b.hx), speed=0.1, slow=True)]
    b.hy = 0.0
    b.script = []
    b.update(0.05)
    assert b.slow > 0
    x = b.hx
    b.step(1, 0)
    b.step(1, 0)                                                             # the second one comes too soon
    assert b.hx == round(x) + 1


def test_ultra_unlocks_only_for_a_first_hit_of_15_with_the_tesseract():
    b = boss.Boss(seed=1, has_tesseract=True)
    assert b.attack(1.0) >= boss.ULTRA_UNLOCK_DMG and b.ultra_unlocked and b.ultra_announce and ("ultra_unlock",) in b.events
    c = boss.Boss(seed=1, has_tesseract=True)
    c.attack(0.55)                                                          # a weak first hit ...
    c.state = "player"
    c.attack(1.0)                                                           # ... and a perfect second one: too late
    assert not c.ultra_unlocked
    d = boss.Boss(seed=1)
    d.attack(1.0)
    assert not d.ultra_unlocked and not d.use_ultra()                       # nothing carried, nothing unfolds
    e = boss.Boss(seed=1, has_tesseract=True)
    e.tesseract_used = True
    e.attack(1.0)
    assert not e.ultra_unlocked


def test_ultra_numbers_effects_and_once_per_fight():
    assert (boss.ULTRA_UNLOCK_DMG, boss.ULTRA_HEAL, boss.ULTRA_FREEZE, boss.ULTRA_INVULN, boss.ULTRA_SHIELD, boss.ULTRA_SHARE) == (15, 12, 5.0, 3.0, 2, 0.5)
    b = boss.Boss(seed=1, ultra=True)
    b.hp, hp0 = 4, b.enemy_hp
    b.bullets.append(boss.Bullet(5, 0, 0, 4.0, "word"))
    b.state = "player"
    dmg = b.use_ultra()
    assert dmg == round(boss.PHASES[1]["hp"] * 0.5) and b.enemy_hp == hp0 - dmg
    assert b.hp == 16 and b.shield == 2 and b.freeze == 5.0 and b.bullets == [] and b.ultra_used and b.state == "enemy"
    b.update(4.9)
    assert b.freeze > 0 and b.t == 0.0 and b.invuln > boss.ULTRA_INVULN                 # time really stopped
    b.update(0.3)
    assert b.freeze == 0 and 2.5 < b.invuln <= boss.ULTRA_INVULN + 0.01                  # 3 s of invulnerability start now
    b.state = "player"
    assert not b.use_ultra()


def test_shield_absorbs_two_hits():
    b = boss.Boss(seed=1, ultra=True)
    b.begin_enemy_turn()
    b.shield = 2
    ev = []
    for _ in range(3):
        b.invuln = 0
        b._hurt(4, ev, 0.3)
    assert b.hp == boss.PLAYER_HP - 4 and [e for e in ev if e[0] == "shield"] == [("shield", 1), ("shield", 0)]


class Screen:
    def __init__(self, choices):
        self.choices, self.log, self.said = list(choices), [], []

    def key(self, t):
        return None

    def frame(self, *a, **k):
        pass

    def say(self, t, w):
        self.said.append(t)

    def blackout(self, ms=0):
        pass

    def menu(self, b, opts, message=""):
        self.log.append(list(opts))
        return self.choices.pop(0) if self.choices else 0

    def timing_bar(self, b):
        return 1.0

    def ultra_unlock_animation(self, b):
        self.log.append("unlock")

    def ultra_animation(self, b):
        self.log.append("use")


def test_item_menu_shows_ultra_instead_of_the_tesseract_after_a_perfect_first_hit():
    b = boss.Boss(seed=1, has_tesseract=True)
    s = Screen([0, 2, 1])                       # FIGHT (perfect) ... later: ITEM -> the ultra entry
    f = boss_ui.Fight(b, s)
    f.player_turn()
    assert "unlock" in s.log and b.ultra_unlocked
    b.state = "player"
    f.player_turn()
    items = [m for m in s.log if isinstance(m, list) and m[0].startswith("Heal")][-1]
    assert "ULTRA TESSERACT: stop time" in items and "Tesseract: stop time" not in items
    assert "use" in s.log and b.ultra_used


def test_portrait_and_animation_data_shapes():
    assert portraits.has_art()
    for n in portraits.PORTRAITS:
        for size, (w, h) in (("big", portraits.BIG), ("small", portraits.SMALL)):
            lines = portraits.portrait(n, size)
            assert len(lines) == h and "48;2;" in lines[0]               # truecolor with a background behind every glyph
    for k in portraits.KINDS:
        for st in portraits.STATES:
            for size, (w, h) in portraits.ANIM.items():
                fr = portraits.anim_frame(k, st, 0, size)
                assert len(fr["rows"]) == h and all(len(r) == w for r in fr["rows"]) and all(len(r) == w for r in fr["fg"]) and all(len(r) == w for r in fr["bg"])
            assert portraits.frame_count(k, st) >= 3
        assert portraits.frame_count(k, "idle") >= 6
    assert portraits.morph_frame("green", "yellow", 3)["rows"]
    assert portraits.portrait("noah_green", "big", truecolor=False)[0].count("48;5;") > 5


def test_size_selection_and_no_overlap_with_the_arena():
    assert portraits.pick_size(245, 45) == "big"
    assert portraits.pick_size(80, 24) is None
    sizes = [(245, 45), (200, 40), (160, 36), (120, 30), (110, 24), (100, 30), (80, 24), (60, 20)]
    seen = set()
    for w, h in sizes:
        lay = portraits.fight_layout(w, h)
        if lay is None:
            continue
        seen.add(lay["size"])
        ox = (w - portraits.ARENA_W) // 2
        assert lay["x"] >= 1 and lay["x"] + lay["w"] + 3 < ox                    # a clear gap even while the screen shakes
        assert lay["y"] + lay["h"] < h
    assert portraits.fight_layout(80, 24) is None and portraits.fight_layout(245, 45)["size"] == "big" and "small" in seen


def test_cinematics_are_long_enough_and_stay_on_screen():
    assert 6 <= ultra_fx.UNLOCK_SECONDS <= 9 and 9 <= ultra_fx.USE_SECONDS <= 11
    for w, h in ((244, 44), (79, 23)):
        for fn, secs in ((ultra_fx.unlock_frame, ultra_fx.UNLOCK_SECONDS), (lambda t, w, h: ultra_fx.use_frame(t, w, h, (3, 2, ["ab  c"]), (10, 5), ["BURN"]), ultra_fx.USE_SECONDS)):
            counts = []
            for i in range(0, 40):
                cells = fn(secs * i / 40, w, h)
                assert all(0 <= x < w and 0 <= y < h and x + len(ch) <= w and 0 <= c < len(ultra_fx.PALETTE) for x, y, ch, c in cells)
                counts.append(len(cells))
            assert min(counts) > 0 and max(counts) > 300
    assert len(ultra_fx.title_rows()) == 5
    assert "ULTRA".count("U") == 1 and ultra_fx.render_ansi(ultra_fx.unlock_frame(8.3, 100, 30), 100, 30).count("\n") == 30


def test_gallery_lists_everything():
    kinds = [p[1] for p in gallery.pages()]
    assert kinds.count("portrait") == 12 and kinds.count("anim") == 20 and kinds.count("morph") == 3 and kinds.count("ultra") == 2


# ---------------------------------------------------------------- the shake
def test_shake_amplitude_rises_then_decays_with_separate_aftershocks():
    q, tr = ultra_fx.USE_QUAKES, ultra_fx.USE_TREMOR
    amps = [ultra_fx.shake_amp(t / 20.0, q, tr) for t in range(0, 208)]
    assert max(amps) == 1.0 and all(0.0 <= a <= 1.0 for a in amps)
    assert ultra_fx.shake_amp(2.0, q, tr) == 0 and ultra_fx.shake_amp(5.0, q, tr) > ultra_fx.shake_amp(3.5, q, tr) > 0          # tremor rises
    assert ultra_fx.shake_amp(6.7, q, tr) > ultra_fx.shake_amp(7.1, q, tr) > 0.1                                                  # exponential decay
    bumps = [t for t in (7.35, 8.3, 9.1) if ultra_fx.shake_amp(t + 0.02, q, tr) > ultra_fx.shake_amp(t - 0.02, q, tr)]
    assert bumps == [7.35, 8.3, 9.1]                                                                                             # three aftershocks
    assert ultra_fx.shake_amp(10.3, q, tr) < 0.05


def test_every_cell_is_shaken_within_bounds_and_stays_on_screen():
    w, h = 120, 40
    cells = [(x, y, "x", 0) for x in range(0, w, 3) for y in range(h)]
    seen = set()
    for i in range(60):
        t = 6.6 + i / 30.0
        dx, dy = ultra_fx.shake_offset(t, 1.0)
        assert abs(dx) <= ultra_fx.SHAKE_X and abs(dy) <= ultra_fx.SHAKE_Y
        seen.add((dx, dy))
        out = ultra_fx.shaken(cells, t, w, h, 1.0)
        assert out and all(0 <= x < w and 0 <= y < h for x, y, _, _ in out)
    assert len(seen) > 20 and ultra_fx.shake_offset(1.0, 0.0) == (0, 0)                  # it really jumps; no amplitude, no shake
    assert max(abs(ultra_fx.shake_offset(i / 30.0, 1.0)[0]) for i in range(300)) >= 6     # and gets close to the full +-8 columns


def test_use_and_unlock_frames_really_shake_and_end_quiet():
    a = ultra_fx.use_frame(6.9, 100, 30, scene=[(10, 10, "arena", 5)])
    assert ultra_fx.use_amp(6.9) > 0.3 and a
    assert ultra_fx.use_amp(6.6) == 1.0 and ultra_fx.use_amp(10.3) < 0.05 and ultra_fx.unlock_amp(6.6) >= 0.7
    assert 9 <= ultra_fx.USE_SECONDS <= 11 and 6 <= ultra_fx.UNLOCK_SECONDS <= 9


def test_window_shake_opt_out_terminals_and_restore():
    log = []
    ok = ultra_fx.WindowShake(env={"TERM": "xterm-256color"}, write=log.append, read_reply=lambda: "\033[3;100;50t")
    assert ok.enabled() and ok.start() and ok.pos == (100, 50)
    ok.move(10, -20)
    ok.move(-5, 5)
    ok.stop()
    assert log[0] == "\033[13t" and log[1] == "\033[3;110;30t" and log[-1] == "\033[3;100;50t"                 # restored to the original place
    for env in ({"TERM": "xterm", "FOLK_WINSHAKE": "0"}, {"TERM": "linux"}, {"TERM": "xterm", "TMUX": "/tmp/x"}, {"TERM": "dumb"}):
        quiet = []
        w = ultra_fx.WindowShake(env=env, write=quiet.append, read_reply=lambda: "\033[3;1;1t")
        assert not w.enabled() and not w.start()
        w.move(5, 5)
        w.stop()
        assert quiet == []                                                                                   # opt-out: nothing is even asked
    silent = []
    w = ultra_fx.WindowShake(env={"TERM": "xterm"}, write=silent.append, read_reply=lambda: "")
    assert not w.start()
    w.move(9, 9)
    w.stop()
    assert silent == ["\033[13t"]                                                                            # no reply: never moved, nothing to restore
    moved = ultra_fx.WindowShake(env={"TERM": "xterm"}, write=silent.append, read_reply=lambda: "\033[3;0;0t")
    moved.start()
    moved.move(-50, -50)
    assert silent[-1] == "\033[3;0;0t"                                                                       # never negative


def test_the_speech_has_three_slow_beats_and_the_blast_tears_the_screen():
    assert [typed for typed in (ultra_fx.typed(ultra_fx.SPEECH, t) for t in (0.4, 1.5, 3.2, 4.5))] == ["", "I...", "I... am...", "I... am... every side at once."]
    scene = [(x, 5, "abc", 1) for x in range(0, 90, 4)]
    near, far = ultra_fx.scene_blown(scene, 0.05, 100, 30), ultra_fx.scene_blown(scene, 1.0, 100, 30)
    assert near and far and near != far and ultra_fx.scene_blown(scene, 2.0, 100, 30) == []
