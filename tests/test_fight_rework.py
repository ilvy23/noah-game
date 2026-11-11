"""Fight rework: the beaten phase stays on screen until the transition has played, no MERCY button after the fusion, death animation and
unlimited retries, Ctrl+C asks, Noah's dynamic lines, cracks and faces, the ULTRA bonus animations (pure parts)."""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boss  # noqa: E402
import boss_ui  # noqa: E402
import noah_talk  # noqa: E402
import ultra_bonus  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS = json.load(open(os.path.join(HERE, "story", "boss_texts.json"), encoding="utf-8"))


class Clock:
    def t(self):
        return 0.0


class Screen:
    def __init__(self, choices=(), leave=None):
        self.choices, self.log, self.menus, self.said = list(choices), [], [], []
        self.leave = leave

    def key(self, timeout):
        return None

    def frame(self, b, message, who, **kw):
        self.log.append(("frame", b.shown, b.who, b.hp_shown, b.phase))

    def say(self, text, who):
        self.said.append((text, who))

    def blackout(self, ms=0):
        self.log.append(("blackout", 0, 0, 0, 0))

    def menu(self, b, opts, message=""):
        self.menus.append(list(opts))
        return self.choices.pop(0) if self.choices else 0

    def timing_bar(self, b):
        return 1.0

    def transition(self, b):
        self.log.append(("transition", b.shown, b.who, b.hp_shown, b.phase))

    def death(self, b):
        self.log.append(("death", b.shown, 0, 0, b.phase))


def fight(b, scr, **kw):
    return boss_ui.Fight(b, scr, clock=Clock(), sfx=lambda n: None, talker=noah_talk.Talker({}), **kw)


def test_the_beaten_phase_stays_on_screen_until_the_transition_then_the_next_appears():
    for start in (1, 2, 3):
        b = boss.Boss(seed=1, phase=start)
        b.state, b.enemy_hp = "player", 1
        scr = Screen()
        f = fight(b, scr)
        old_who = boss.PHASES[start]["who"]
        f.player_turn()                                              # the killing blow, the "-18", the transition, the next phase
        assert b.phase == start + 1 and b.shown == b.phase
        t = [i for i, e in enumerate(scr.log) if e[0] == "transition"][0]
        before = [e for e in scr.log[:t] if e[0] == "frame" and e[4] == start + 1]       # frames after the killing blow
        assert before and all(e[1] == start and e[2] == old_who and e[3] == 0 for e in before)       # old look, empty life bar
        assert scr.log[t][1] == start and scr.log[t][2] == old_who                                   # still the old one when it starts
        after = [e for e in scr.log[t + 1:] if e[0] == "frame"]
        assert after and all(e[1] == start + 1 for e in after)


def test_boss_keeps_the_old_look_in_who_and_hp_shown_until_told():
    b = boss.Boss(seed=1)
    b.state, b.enemy_hp = "player", 1
    b.attack(1.0)
    assert b.phase == 2 and b.shown == 1 and b.who == "noah" and b.hp_shown == 0
    b.shown = b.phase
    assert b.who == "noah2" and b.hp_shown == boss.PHASES[2]["hp"] and b.hp_ratio == 1.0


def test_after_the_fusion_there_is_no_mercy_button_the_game_goes_straight_on():
    b = boss.Boss(seed=1, phase=4)
    b.state, b.enemy_hp = "player", 1
    scr, ended = Screen(), []
    f = fight(b, scr, on_end=lambda: ended.append(1))
    assert f.run() == "won" and ended == [1] and b.state == "won"
    assert ["MERCY"] not in scr.menus                                 # nothing to press
    assert any("quiet" in t for t, _w in scr.said)


def test_death_plays_the_animation_and_retries_are_unlimited():
    b = boss.Boss(seed=1)
    b.state = "player"
    scr = Screen()
    f = fight(b, scr)
    deaths = []
    orig = b.update

    def update(dt, dx=0, dy=0):
        if len(deaths) < 3 and b.state == "enemy":
            deaths.append(1)
            b.hp = 0
            b.state = "lost"
            return []
        return orig(dt, dx, dy)
    b.update = update
    b._hurt = lambda *a: False
    assert f.run() == "won"
    assert [e[0] for e in scr.log].count("death") == 3 and b.retries == 3 and b.phase == 4


def test_ctrl_c_asks_and_the_fight_goes_on_when_you_stay_or_leaves_when_you_say_yes():
    for answer in (False, True):
        b = boss.Boss(seed=1, phase=4)
        b.state, b.enemy_hp = "player", 1
        scr = Screen()
        asked = []
        scr.confirm_leave = lambda: asked.append(1) or answer
        f = fight(b, scr)
        orig, boom = scr.frame, [True]

        def frame(bb, m, w, **kw):
            if boom[0]:
                boom[0] = False
                raise KeyboardInterrupt
            return orig(bb, m, w, **kw)
        scr.frame = frame
        if answer:
            try:
                f.run()
                assert False, "should have left"
            except KeyboardInterrupt:
                pass
        else:
            assert f.run() == "won"
        assert asked == [1]


def test_noah_never_repeats_a_line_before_the_list_is_used_up_and_the_name_is_rare():
    t = noah_talk.Talker(TEXTS, rng=random.Random(3), user="Ilvy")
    for ph in (1, 2, 3, 4):
        for kind in ("idle", "hit", "hurt", "death"):
            n = len(TEXTS["boss.talk.%d.%s" % (ph, kind)])
            got = [t._take("boss.talk.%d.%s" % (ph, kind)) for _ in range(n)]
            assert len(set(got)) == n, (ph, kind)
        assert len(TEXTS["boss.talk.%d.idle" % ph]) >= 10                     # many lines
    lines = []
    for _ in range(4000):                                                     # 2 min of fight at 30 fps: idle lines only
        lines.append(t.tick(1 / 30, 3))
    said = [x for x in lines if x]
    assert 20 <= len(said) <= 40 and all(len(x) <= 70 for x in said)         # every 3.5 - 6 s, short
    assert not any("Ilvy" in x for x in said)                                 # the name is only for key moments
    assert "Ilvy" in noah_talk.Talker(TEXTS, rng=random.Random(1), user="Ilvy").key_moment(2)
    assert all(not any(c in x for x in said for c in "{}") for c in "{}")


def test_story_decisions_change_what_noah_says_and_event_lines_have_a_cooldown():
    none = noah_talk.Talker(TEXTS, has=lambda f: False, rng=random.Random(2))
    assert none.flag_line() == ""
    kind = noah_talk.Talker(TEXTS, has=lambda f: f == "kind_mug", rng=random.Random(2))
    assert kind.flag_line() in TEXTS["boss.talk.flag.kind_mug"]
    seen = {noah_talk.Talker(TEXTS, has=lambda f: f == "bond", rng=random.Random(s)).flag_line() for s in range(8)}
    assert seen <= set(TEXTS["boss.talk.flag.bond"])
    t = noah_talk.Talker(TEXTS, rng=random.Random(5))
    assert t.event(1, "hurt") and t.event(1, "hurt") == ""                    # not twice in a row
    t.tick(2.5, 1)
    assert t.event(1, "hurt")
    for key in ("boss.talk.miss", "boss.talk.heal", "boss.beaten") + tuple("boss.talk.flag.%s" % f for f in noah_talk.FLAGS):
        assert TEXTS[key]


def test_big_hits_crack_him_and_his_face_gives_way():
    b = boss.Boss(seed=1)
    b.state = "player"
    b.attack(1.0)                                                             # 18 damage
    assert b.cracks == 1 and ("crack", 1) in b.events
    b.state = "player"
    b.enemy_hp = 3
    b.attack(0.3)
    b.state = "player"
    assert b.hp_ratio < 0.3
    assert boss_ui.face_for("noah", 1.0) != boss_ui.face_for("noah", 0.5) != boss_ui.face_for("noah", 0.1)
    c = boss.Boss(seed=1)
    c.state, c.enemy_hp, c.cracks = "player", 1, 3
    c.attack(1.0)
    assert c.cracks == 0 and c.phase == 2                                     # a new Noah starts unbroken


def test_ultra_remembers_what_it_wiped_and_the_bonus_animations_stay_on_screen():
    b = boss.Boss(seed=2, ultra=True)
    b.phase = 3
    b.begin_enemy_turn()
    b.hp = 10 ** 6
    for _ in range(90):
        b.update(1 / 30)
    b.state = "player"
    cracks = b.cracks
    b.use_ultra()
    assert b.wiped and not b.bullets and b.cracks == cracks + 3
    for t in [i / 15 for i in range(int(ultra_bonus.BEAM_SECONDS * 15))]:
        assert ultra_bonus.beam(t, (60, 0), (10, 14))
    wiped = [(40 + i, 5, "x") for i in range(10)] + [(30, 8, "y")]
    front = lambda t: ultra_bonus.front(66, t)               # noqa: E731
    first = ultra_bonus.mika(1.0, (60, 3), wiped, front)
    last = ultra_bonus.mika(3.3, (60, 3), wiped, front)
    assert sum(1 for c in first if c[2] in ("x", "y")) == 11
    assert not [c for c in last if c[2] in ("x", "y")]                       # the smoke has cleared them all
    hist = [[(1, 1, "a")], [(1, 2, "a")], [(1, 3, "a")]]
    ghosts = ultra_bonus.ghost_layers(hist)
    assert len(ghosts) == 2 and ghosts[0][2] != ghosts[1][2]                 # older = plainer
