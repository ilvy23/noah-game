"""A cheap 'is there always a way out?' pilot for the fight patterns (used by tests/test_escape_routes.py and for tuning).

Every DECIDE seconds it builds a danger map of every cell any hazard will make harmful in the next WINDOW seconds (plus the reaction time),
then walks the heart (one cell every 2 frames, like a held key) along the shortest path to the nearest cell that stays safe. It sees the
world REACT seconds late. A pattern that cannot be escaped shows up as hits however well the pilot plays."""
import copy
import math
import os
import random
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import boss  # noqa: E402
import patterns  # noqa: E402

DT, DECIDE, WINDOW = 1 / 30, 0.1, 0.8


def danger(b, ahead):
    """Cells that are harmful at some moment within `ahead` seconds from now (hazards only)."""
    bad = set()
    for h in b.hazards:
        probe = copy.copy(h)
        probe.d = h.d
        for k in range(int(ahead / 0.1) + 1):
            probe.age = h.age + 0.1 * k
            if h.kind == "orb":
                if h.harmful:                                  # an orb: where it will be if it keeps its heading (it turns slowly)
                    d = h.d
                    for j in range(0, 6):
                        x, y = d["px"] + math.cos(d["a"]) * d["sp"] * 2 * 0.1 * k * (1 + j * 0.0), d["py"] + math.sin(d["a"]) * d["sp"] * 0.1 * k
                        bad.update((int(round(x)) + i, int(round(y)) + dy) for i in (-2, -1, 0, 1, 2) for dy in (-1, 0, 1))
                continue
            bad.update((c[0], c[1]) for c in probe.cells())
    return bad


def path_step(start, bad):
    """First step (dx, dy) of the shortest path from start to the nearest cell not in `bad`; (0, 0) when already safe or hopeless."""
    if start not in bad:
        return (0, 0)
    seen, q = {start: None}, deque([start])
    while q:
        c = q.popleft()
        if c not in bad:
            while seen[c] != start and seen[c] is not None:
                c = seen[c]
            return (c[0] - start[0], c[1] - start[1])
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            n = (c[0] + dx, c[1] + dy)
            if 0 <= n[0] < boss.W and 0 <= n[1] < boss.H and n not in seen:
                seen[n] = c
                q.append(n)
    return (0, 0)


def run(name, seed, hx, hy, phase=3, react=0.18, script=None):
    """Hits taken by the pilot during one pattern (or a script [(time, name)]) with no word bullets. Also returns the number of ticks with
    no safe cell at all on the whole map (a pattern that fills the arena)."""
    b = boss.Boss(seed=seed, phase=phase)
    b.hp = 10 ** 6
    b.begin_enemy_turn()
    b.script = list(script or [(0.0, name)])
    b.wall_t, b._spawn, b.hazards = 99, (lambda: None), []
    b.hx, b.hy = float(hx), float(hy)
    t, hits, nosafe, target, last_dec, frame, taps = 0.0, 0, 0, (0, 0), -9.0, 0, 0
    end = max(patterns.duration(n) + tt for tt, n in b.script) + 0.5
    lag = []
    while t < end and b.state == "enemy":
        if t - last_dec >= DECIDE:
            last_dec = t
            bad = danger(b, WINDOW + react)
            if len(bad) >= boss.W * boss.H:
                nosafe += 1
            lag.append((t + react, path_step((int(round(b.hx)), int(round(b.hy))), bad)))
        while lag and lag[0][0] <= t:
            target = lag.pop(0)[1]
            taps = 1 if target != (0, 0) else 0                 # one decision = one key tap (the game then glides a little further, as it does for a real key)
        if taps and frame % 2 == 0:
            b.step(*target)
            taps -= 1
        hp0 = b.hp
        b.update(DT)
        if b.hp < hp0:
            hits += 1
        t += DT
        frame += 1
    return hits, nosafe
