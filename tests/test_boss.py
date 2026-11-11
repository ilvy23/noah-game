"""boss.py: movement, collision, damage, phases, victory, defeat, fixed seeds."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boss  # noqa: E402


def run(b, seconds, dx=0, dy=0, step=0.05):
    ev = []
    for _ in range(int(seconds / step)):
        ev += b.update(step, dx, dy)
        if b.state != "enemy":
            break
    return ev


def test_heart_moves_and_is_clamped_to_the_arena():
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    x0 = b.hx
    b.update(0.1, 1, 0)
    assert b.hx > x0
    for _ in range(100):
        b.update(0.1, -1, -1)
        if b.state != "enemy":
            break
    assert b.hx >= 0 and b.hy >= 0


def test_a_word_that_reaches_the_heart_does_damage_then_invulnerability():
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    b.bullets.append(boss.Bullet(b.hx - 1, b.hy, 0, 0, "sorry", dmg=3))
    ev = b.update(0.01)
    assert ("hit", 3) in ev and b.hp == boss.PLAYER_HP - 3 and b.invuln > 0
    ev = b.update(0.01)
    assert ("hit", 3) not in ev                      # still invulnerable


def test_defending_halves_the_damage():
    b = boss.Boss(seed=1)
    b.defend()
    b.bullets.append(boss.Bullet(b.hx, b.hy, 0, 0, "x", dmg=5))
    b.update(0.01)
    assert b.hp == boss.PLAYER_HP - 2


def test_same_seed_same_fight_and_turn_ends_after_its_duration():
    a, c = boss.Boss(seed=7), boss.Boss(seed=7)
    for x in (a, c):
        x.begin_enemy_turn()
        run(x, 2.0)
    assert [(b.x, b.y, b.text) for b in a.bullets] == [(b.x, b.y, b.text) for b in c.bullets]
    ev = run(boss.Boss(seed=3), 0)       # nothing
    b = boss.Boss(seed=3)
    b.begin_enemy_turn()
    b.hp = 10 ** 6
    run(b, 20)
    assert b.state == "player"


def test_phases_advance_through_all_four_personalities_to_victory():
    b = boss.Boss(seed=2)
    seen = [b.who]
    for _ in range(40):
        if b.state in ("won", "mercy"):
            break
        if b.state == "enemy":
            b.hp = 99
            run(b, 30)
        else:
            b.attack(1.0)
            seen.append(b.cfg["who"])
    assert b.state == "mercy" and b.phase == 4            # the fight is over, MERCY is left
    assert b.mercy() and b.state == "won"
    assert ("phase", 2) in b.events and ("phase", 3) in b.events and ("phase", 4) in b.events and ("won",) in b.events
    assert seen[0] == "noah" and "noah2" in seen and seen[-1] == "noah3"


def test_defeat_when_hp_runs_out():
    b = boss.Boss(seed=2)
    b.begin_enemy_turn()
    for _ in range(10):
        b.invuln = 0
        b.bullets.append(boss.Bullet(b.hx, b.hy, 0, 0, "x", dmg=8))
        b.update(0.01)
        if b.state == "lost":
            break
    assert b.state == "lost" and b.hp == 0 and ("lost",) in b.events


def test_shadow_hands_chase_the_heart_in_phase_three():
    b = boss.Boss(seed=5, power=1.0)
    b.phase = 3
    b.begin_enemy_turn()
    b.hp = 10 ** 6
    b.bullets.append(boss.Bullet(1, 0, 0, 0, "✠", dmg=5, home=True))
    d0 = abs(b.bullets[0].x - b.hx) + abs(b.bullets[0].y - b.hy)
    run(b, 0.5)
    hand = [x for x in b.bullets if x.home][0]
    assert abs(hand.x - b.hx) + abs(hand.y - b.hy) < d0


def test_heal_limited_and_talk_uses_supplied_lines_or_placeholder():
    b = boss.Boss(seed=1, lines={1: ["I don't want to hit you!"]})
    b.hp = 5
    assert b.heal() and b.hp == 13 and b.state == "enemy"
    b.state = "player"
    assert b.talk() == "I don't want to hit you!"
    b.phase = 2
    assert b.talk().startswith("[TEXT: boss.p2.")
    for _ in range(3):
        b.state = "player"
        b.heal()
    b.state = "player"
    assert not b.heal()


def test_timing_bar_centre_is_best():
    assert boss.timing_accuracy(0.5) == 1.0 and boss.timing_accuracy(0.0) == 0.0 and boss.timing_accuracy(0.25) == 0.5


def test_retry_restarts_the_same_phase_with_full_hp():
    b = boss.Boss(seed=1)
    b.phase, b.enemy_hp, b.hp, b.state = 3, 5, 0, "lost"
    b.retry_phase()
    assert b.phase == 3 and b.hp == boss.PLAYER_HP and b.enemy_hp == boss.PHASES[3]["hp"] and b.state == "enemy"      # the attack starts at once, no menu
    assert ("retry", 3) in b.events and b.retries == 1


def test_saying_his_name_only_works_in_phase_one():
    b = boss.Boss(seed=1)
    assert b.act("name") == "[TEXT: boss.act.name]" and b.enemy_hp <= 6 and b.state == "enemy"
    b = boss.Boss(seed=1)
    b.phase, b.enemy_hp = 2, boss.PHASES[2]["hp"]
    assert b.act("name") == "[TEXT: boss.act.noeffect]" and b.enemy_hp == boss.PHASES[2]["hp"]
    b = boss.Boss(seed=1)
    assert b.act("check").startswith("[TEXT: boss.act.check.1")


def test_the_tesseract_wipes_the_screen_stops_time_heals_and_hurts_noah_once_and_only_if_carried():
    assert not boss.Boss(seed=1).use_tesseract()
    b = boss.Boss(seed=1, has_tesseract=True)
    b.hp, hp0 = 5, b.enemy_hp
    b.bullets.append(boss.Bullet(5, 0, 0, 4.0, "word"))
    assert b.use_tesseract() and b.tesseract_used and b.state == "enemy"
    assert b.hp == 5 + boss.Boss.TESSERACT_HEAL and b.enemy_hp < hp0 and b.enemy_hp >= 1       # healed, Noah hurt, not killed
    assert b.bullets == [] and b.freeze == boss.Boss.TESSERACT_FREEZE                          # every attack erased, time stopped
    b.bullets.append(boss.Bullet(5, 0, 0, 4.0, "word"))
    y0 = b.bullets[0].y
    b.update(2.0)
    assert b.bullets[0].y == y0                                                                # frozen for 3 s
    b.update(2.0)
    assert b.bullets[0].y > y0
    b.state = "player"
    assert not b.use_tesseract()                                                               # only once


def test_mercy_is_only_possible_after_the_last_phase():
    b = boss.Boss(seed=1)
    assert not b.mercy()
    b.phase, b.enemy_hp = 4, 1
    b.attack(1.0)
    assert b.state == "mercy" and b.mercy() and b.state == "won"


def test_damage_grows_steeply_the_closer_the_bar_is_stopped_to_zero():
    d = [boss.damage_for(a / 10) for a in range(11)]
    assert d[0] == 0 and d[1] == 0 or d[1] <= 1                  # far away: nothing or a scratch
    assert d == sorted(d) and d[-1] == boss.MAX_HIT and d[10] > 2 * d[6]
    assert boss.offset(0.5) == 0 and boss.offset(0.0) == -15 and boss.offset(1.0) == 15
    b = boss.Boss(seed=1)
    hp = b.enemy_hp
    assert b.attack(1.0) == boss.MAX_HIT and b.enemy_hp == hp - boss.MAX_HIT


def test_a_single_key_press_moves_the_heart_exactly_one_cell():
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    x, y = int(b.hx), int(b.hy)
    b.step(-1, 0)
    assert int(b.hx) == x - 1                                     # visible at once, no second press needed
    b.step(0, -1)
    assert int(b.hy) == y - 1
    for _ in range(100):
        b.step(1, 1)
    assert b.hx == boss.W - 1 and b.hy == boss.H - 1              # clamped to the arena


def test_difficulty_escalates_green_to_fusion_and_the_knobs_exist():
    p, d = boss.PHASES, boss.DIFFICULTY
    assert p[1]["hp"] <= p[2]["hp"] <= p[3]["hp"] <= p[4]["hp"] and p[4]["turn"] >= p[1]["turn"]
    for key in ("words_rate", "words_speed", "pace", "tight", "wall", "hands", "cross", "breather"):
        assert all(key in d[ph] for ph in (1, 2, 3, 4)), key
    assert d[1]["pace"] > d[2]["pace"] >= d[3]["pace"] >= d[4]["pace"]            # less and less time to read a pattern
    assert d[1]["tight"] > d[2]["tight"] >= d[3]["tight"] >= d[4]["tight"]        # narrower and narrower gaps
    assert d[1]["breather"] > d[4]["breather"] and d[1]["wall"] is None and d[4]["wall"][0] < d[3]["wall"][0] < d[2]["wall"][0]
    assert d[1]["words_rate"] > d[2]["words_rate"] > d[3]["words_rate"] > d[4]["words_rate"]
    b = boss.Boss(seed=3, power=1.0)
    b.phase = 3
    b.begin_enemy_turn()
    b.hp = 10 ** 6
    hands = 0
    for _ in range(int(8.0 / 0.05)):
        b.update(0.05)
        hands = max(hands, len([x for x in b.bullets if x.home]))
        if b.state != "enemy":
            break
    assert hands <= 2 + 1                                          # a few chasing hands at most


def test_tap_moves_one_cell_and_a_held_key_glides_smoothly():
    b = boss.Boss(seed=1)
    b.begin_enemy_turn()
    b.hx = 20.0
    x0 = b.hx
    b.step(-1, 0)                                                 # tap: exactly one cell
    assert round(x0 - b.hx) == 1
    b.update(0.1)
    assert round(x0 - b.hx) == 1                                  # no glide after a single tap
    b.step(-1, 0)                                                 # second press soon after: the key is held
    x1 = b.hx
    b.update(0.1)
    assert x1 - b.hx > 1.0                                        # now it glides between key repeats
    x2 = b.hx
    b.update(0.3)
    b.update(0.1)
    assert abs(b.hx - x2) < 2.5                                   # and stops shortly after the last key event
    b.step(1, 0)                                                  # direction change: a plain tap again
    assert b.streak == 0


def test_sweeping_wall_is_telegraphed_then_hurts_everywhere_but_the_gap():
    b = boss.Boss(seed=1)
    b.phase = 3
    b.begin_enemy_turn()
    b.hp = 10
    b.walls = [{"y": 5, "gap": 10, "age": 0.0, "hit": False}]
    b.hy, b.hx = 5.0, 30.0
    b.update(0.3)
    assert b.hp == 10                                              # still only a warning
    b.update(0.7)                                                  # now it is live (age 1.0)
    assert b.hp == 6 and b.fx["shake"] > 0                         # outside the gap: hit, the screen shakes
    c = boss.Boss(seed=1)
    c.phase = 3
    c.begin_enemy_turn()
    c.hp = 10
    c.walls = [{"y": 5, "gap": 10, "age": 0.0, "hit": False}]
    c.hy, c.hx = 5.0, 11.0
    c.update(1.0)
    assert c.hp == 10                                              # standing in the gap is safe


def test_yellow_red_and_fusion_spawn_walls_but_green_does_not():
    for ph, expect in ((1, False), (2, True), (3, True), (4, True)):
        b = boss.Boss(seed=2)
        b.phase = ph
        b.begin_enemy_turn()
        b.hp = 10 ** 6
        seen = False
        for _ in range(int(boss.PHASES[ph]["turn"] / 0.05)):
            b.update(0.05)
            seen = seen or bool(b.walls)
            if b.state != "enemy":
                break
        assert seen == expect


def test_phase_changes_and_hits_make_the_screen_shake():
    b = boss.Boss(seed=1)
    b.enemy_hp = 1
    b.attack(1.0)
    assert b.phase == 2 and b.fx["shake"] > 1.0 and b.state == "enemy"


def test_wall_hit_on_the_last_tick_of_a_turn_still_loses():
    from boss import Boss
    b = Boss()
    b.phase, b.enemy_hp = 3, 25
    b.begin_enemy_turn()
    b.hp, b.t, b.wall_t = 3, b.cfg["turn"] - 0.01, 99
    b.walls = [{"y": int(round(b.hy)), "gap": b.hx + 10, "age": 0.9, "hit": False}]
    ev = b.update(0.02)
    assert b.state == "lost" and b.hp == 0 and ("your_turn",) not in ev


def test_the_wall_comes_for_the_player_within_three_rows_and_leaves_the_gap_away_from_him():
    for seed in range(40):
        b = boss.Boss(seed=seed)
        b.phase = 3
        b.begin_enemy_turn()
        b.hy, b.hx = 6.0, 20.0
        b.wall_t = 0.0
        b.hp = 10 ** 6
        b.update(0.01)
        w = b.walls[0]
        assert abs(w["y"] - 6) <= 3 and abs(w["gap"] - 20) >= 7, (seed, w)


def test_every_phase_has_its_own_lore_words():
    p = boss.PHASES
    assert {"tea?", "honey", "guest cup", "friend"} <= set(p[1]["words"])                      # green: sweet, friendship
    assert {"mine", "kneel", "obey"} <= set(p[2]["words"])                                      # yellow: harsher
    assert {"MAMA", "ignis et cinis", "CORPUS PUTRE"} <= set(p[3]["words"])                     # red: suppressed pain, hell formulas
    assert len(p[4]["words"]) >= 12 and p[1]["rate"] < 0.95 and p[2]["rate"] < 0.70            # phases 1 and 2 are a touch harder
