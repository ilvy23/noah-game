"""Every pattern and every choreographed turn must leave a way out: an oracle pilot (tests/escape_oracle.py: sees the danger a short time ahead,
walks to the nearest cell that stays safe, reacts 180 ms or 260 ms late) must take only a hit or two, and there must always be a safe cell."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boss  # noqa: E402
import escape_oracle as oracle  # noqa: E402
import patterns  # noqa: E402

SEEDS = 5


def start(seed):
    r = random.Random(seed)
    return r.choice([4, 12, 20, 28, 37]), r.choice([1, 5, 9])


def test_every_pattern_has_a_way_out_at_both_reaction_times():
    for react, worst in ((0.18, 2), (0.26, 3)):
        for ph, names in patterns.BY_PHASE.items():
            for name in names:
                hits = []
                for seed in range(SEEDS):
                    hx, hy = start(seed)
                    h, nosafe = oracle.run(name, seed, hx, hy, phase=ph, react=react)
                    assert nosafe == 0, (name, ph, "no safe cell on the whole map")
                    hits.append(h)
                assert max(hits) <= worst and sum(hits) / SEEDS <= 1.0, (name, ph, react, hits)


def test_every_choreographed_turn_has_a_way_out():
    for react in (0.18, 0.26):
        for ph in (1, 2, 3, 4):
            seqs = patterns.SIGNATURES[ph] + ([patterns.RAGE[ph]] if ph in patterns.RAGE else []) + ([patterns.TRINITY] if ph == 4 else [])
            for seq in seqs:
                hits = []
                for seed in range(SEEDS):
                    hx, hy = start(seed)
                    h, nosafe = oracle.run(None, seed, hx, hy, phase=ph, react=react, script=seq)
                    assert nosafe == 0
                    hits.append(h)
                assert max(hits) <= 4 and sum(hits) / SEEDS <= 1.8, (ph, [n for _, n in seq], react, hits)


def test_the_escape_oracle_notices_when_there_is_no_way_out():
    class Wall(patterns.Hazard):
        pass
    b = boss.Boss(seed=1, phase=3)
    full = patterns.Hazard("rect", 0.0, 3.0, dmg=3, x=0, y=0, w=boss.W, h=boss.H, ch="#", tele="!")
    full.age = 0.1
    b.hazards = [full]
    assert len(oracle.danger(b, 0.5)) == boss.W * boss.H
