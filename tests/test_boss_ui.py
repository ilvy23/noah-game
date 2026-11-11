"""Intro timing (fake clock) and the fight controller (fake screen)."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boss  # noqa: E402
import boss_ui  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def t(self):
        return self.now

    def sleep(self, d):
        self.now += d

    def wait_until(self, t):
        if t > self.now:
            self.now = t


class Mix:
    def __init__(self):
        self.calls = []

    def boss_intro(self):
        self.calls.append("intro")

    def dip(self, s):
        self.calls.append("dip")

    def impact(self):
        self.calls.append("impact")

    def boss_phase_two(self):
        self.calls.append("phase_two")


def test_intro_cuts_at_forty_seconds_then_types_fast_and_ends_at_fifty_two():
    clock, out, mix = FakeClock(), io.StringIO(), Mix()
    marks = {}
    orig = out.write

    def spy(s):
        r = orig(s)
        if "cut" not in marks and "fucking noise!?" in out.getvalue():
            marks["cut"] = clock.now
        return r
    out.write = spy
    boss_ui.run_intro(out=out, clock=clock, mixer=mix)
    text = out.getvalue()
    assert mix.calls == ["intro", "dip", "impact"]                              # music dips, then the boom lands
    assert "I'll make you tea ev\n" in text.replace("\r", "")                    # the line stops mid-word
    assert text.index("tea ev") < text.index("what is this fucking noise!?") and "\033[?5h" in text   # flash at the impact
    assert 45.3 <= marks["cut"] <= 46.2                                          # the line stops at 44 s, the boom comes after a held breath
    assert 51.9 <= clock.now <= 52.6                                             # fight starts at ~52 s


class FakeScreen:
    def __init__(self, menu_choices, bar=1.0, keys=()):
        self.choices = list(menu_choices)
        self.bar = bar
        self.keys = list(keys)
        self.frames = 0
        self.said = []

    def key(self, timeout):
        return self.keys.pop(0) if self.keys else None

    def frame(self, b, message, who, **kw):
        self.frames += 1

    def say(self, text, who):
        self.said.append((text, who))

    def blackout(self, ms=0):
        self.blackouts = getattr(self, "blackouts", 0) + 1

    def menu(self, b, opts, message=""):
        return self.choices.pop(0) if self.choices else 0

    def timing_bar(self, b):
        return self.bar


def test_fight_runs_to_victory_and_calls_the_phase_hook_for_the_fusion():
    b = boss.Boss(seed=1)
    seen = []
    scr = FakeScreen([0] * 60, keys=[])
    f = boss_ui.Fight(b, scr, clock=FakeClock(), on_phase=seen.append)
    b.hp = 10 ** 6                                     # cannot lose in this test
    b._hurt = lambda *a: False                        # an idle heart no longer survives the harder phases
    assert f.run() == "won"
    assert seen == [2, 3, 4]


def test_losing_restarts_the_phase_and_noah_says_a_line(tmp_path):
    b = boss.Boss(seed=1, lines={1: ["Please stand still.", "Again?"]})
    scr = FakeScreen([0] * 80)
    f = boss_ui.Fight(b, scr, clock=FakeClock(), retries=1)
    b.hp = 1
    b.invuln = 0
    orig = b.update

    def kill(dt, dx=0, dy=0):
        b.bullets.append(boss.Bullet(b.hx, b.hy, 0, 0, "x", dmg=9))
        return orig(dt, dx, dy)
    b.update = kill
    assert f.run() == "lost"                              # retries=1 is used up by the second loss
    assert b.retries == 1 and scr.blackouts >= 1
    assert any(w == "noah" for _t, w in scr.said)          # Noah says a line after the restart


def test_act_item_and_mercy_menus_work_and_mercy_ends_the_fight():
    b = boss.Boss(seed=1, has_tesseract=True)
    # ACT -> Say his name, then the rest: ITEM -> Tesseract, then FIGHT until mercy
    scr = FakeScreen([1, 1] + [2, 1] + [0] * 80)
    f = boss_ui.Fight(b, scr, clock=FakeClock())
    b.hp = 10 ** 6
    b._hurt = lambda *a: False                        # an idle heart no longer survives the harder phases
    assert f.run() == "won"
    assert b.tesseract_used and any(t == "[TEXT: boss.act.name]" for t, _w in scr.said)


def test_placeholders_are_replaced_by_supplied_texts():
    b = boss.Boss(seed=1, has_tesseract=True)
    scr = FakeScreen([1, 1] + [0] * 80)
    f = boss_ui.Fight(b, scr, clock=FakeClock(), texts={"boss.act.name": "You say his name."})
    b.hp = 10 ** 6
    b._hurt = lambda *a: False                        # an idle heart no longer survives the harder phases
    f.run()
    assert ("You say his name.", "noah") in scr.said


def test_every_arrow_event_in_the_dodge_phase_is_one_step():
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    x = int(b.hx)
    scr = FakeScreen([], keys=["left"])
    f = boss_ui.Fight(b, scr, clock=FakeClock())
    b.state = "enemy"
    b.t = 0
    b.cfg["turn"]
    orig = b.update
    seen = []

    def stop(dt, dx=0, dy=0):
        seen.append(int(b.hx))
        b.state = "player"
        return []
    b.update = stop
    f.enemy_turn()
    assert seen == [x - 1]


def test_after_the_intro_the_fight_starts_with_an_attack_not_with_the_menu():
    b = boss.Boss(seed=1)
    scr = FakeScreen([])
    seen = []
    f = boss_ui.Fight(b, scr, clock=FakeClock(), retries=0)
    orig = scr.menu
    scr.menu = lambda *a, **k: (seen.append(b.state), orig(*a, **k))[1]
    b.update = lambda dt, dx=0, dy=0: (setattr(b, "state", "won"), [])[1]        # one frame is enough here
    f.run()
    assert b.state == "won" and seen == []                                        # no menu was shown before the attack
