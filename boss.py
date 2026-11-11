"""boss.py - the fight against Noah, Undertale-like: you choose an action, then you dodge.

Pure game logic (no curses, no sleeping, no I/O) so it can be tested with fixed seeds:
    b = Boss(seed=1, power=0.5); b.begin_enemy_turn(); b.update(dt, dx, dy) ...
Four phases = Noah's personalities (green: reluctant, yellow: wants to, red: definitely, fusion: all three).
Attacks are written words that fall or fly, and in the last two phases shadow hands that chase the heart. On top of that
every personality has its own themed, telegraphed patterns (patterns.py).

Pacing: every enemy turn has an ARC (patterns.arc_for): calm -> build -> climax (the fusion: calm, trinity, build, climax), each ending with
a breather. Noah's life crossing 50% / 20% (THRESHOLDS) emits ("threshold", phase, pct) and makes the next turn a "rage" turn in which the
arena changes (box, cage). Events for the UI/sound: ("sfx", name) from hazards, ("boss_hit", dmg), ("turn", arc), ("threshold", ...).
Hazards can act on the fight through patterns.STEP: gravity (heart is pulled), dark (only a circle round the heart is drawn), orbs (homing).

ULTRA TESSERACT (named constants below): if the player carries the tesseract and the FIRST hit that lands on Noah deals
ULTRA_UNLOCK_DMG (15) or more damage, the item unfolds into the ULTRA TESSERACT and replaces the normal one in the ITEM menu.
Once per fight it: wipes every attack, stops time for ULTRA_FREEZE (5 s), heals ULTRA_HEAL (12) HP, grants ULTRA_INVULN (3 s,
counted after time resumes), gives a shield that absorbs the next ULTRA_SHIELD (2) hits and deals ULTRA_SHARE (50%) of the
current phase's HP to Noah (he is never killed by it).
"""
import math
import random

import patterns

W, H = 41, 11                     # arena cells
# ================================================================ DIFFICULTY KNOBS (patterns.py has TEMPO / OVERLAP / ARC_PLAN / SIGNATURES / RAGE)
# Meant to climb: green is gentle, yellow is felt, red is hard, the fusion is the hardest.
#   words_rate   word bullets: seconds between spawns is PHASES[p]["rate"] * words_rate  (bigger = fewer words)
#   words_speed  word bullets fly this much faster
#   pace         warnings last this much of their written time (never below MIN_WARN): smaller = less time to read a pattern
#   tight        gaps, safe lanes and the lit circle shrink (< 1) or grow (> 1), see patterns.tight
#   cross        chance that a word also comes from the other direction (phase 2: falling words, phase 4: words from the sides)
#   wall         (seconds between sweeping rows, half-width of their gap) or None; GAP 3 means a 7-cell gap
#   hands        chance multiplier for the homing shadow hands (phases 3 and 4)
#   breather     seconds at the end of an enemy turn in which only few words fall
DIFFICULTY = {
    1: dict(words_rate=2.30, words_speed=0.90, pace=1.10, tight=1.15, wall=None, hands=0.0, cross=0.0, breather=2.2),
    2: dict(words_rate=1.15, words_speed=1.05, pace=1.00, tight=1.00, wall=(6.5, 3), hands=0.0, cross=0.10, breather=1.6),
    3: dict(words_rate=0.95, words_speed=1.15, pace=0.85, tight=0.88, wall=(3.0, 3), hands=1.0, cross=0.0, breather=1.1),
    4: dict(words_rate=0.75, words_speed=1.25, pace=0.85, tight=0.85, wall=(2.6, 2), hands=1.3, cross=0.8, breather=0.7),
}
MIN_WARN = 0.7                    # no pattern is ever announced for less than this
PHASES = {
    # green: the sweet, scared Noah (tea, honey, the guest cup, the fox, Clair de Lune, "thank you")
    1: dict(who="noah", hp=22, turn=8.0, rate=0.82, speed=1.1,
            words=["sorry", "please", "stay", "tea?", "honey", "cookies", "guest cup", "friend", "don't go", "thank you", "the fox",
                   "Clair de Lune", "I made too much", "idiot", "not like I care", "warm", "you came back"]),
    # yellow: the second voice, harsher
    2: dict(who="noah2", hp=30, turn=9.0, rate=0.62, speed=1.12,
            words=["mine", "listen", "stand still", "weak", "pathetic", "smile", "kneel", "quiet", "obey", "little bird",
                   "who would miss you", "good boy", "stop crying", "say thank you", "you came to ME"]),
    # red: what was pushed down - the abuse, the anger, the rotten thing, hell formulas
    3: dict(who="noah3", hp=34, turn=9.0, rate=1.7, speed=1.0,
            words=["MAMA", "WHY", "BURN", "HOLD HIM DOWN", "NEVER ENOUGH", "ASH", "SCREAM", "ignis et cinis", "sanguis", "mors vincit",
                   "CORPUS PUTRE", "in nomine nihili", "ave putrescens", "feed the dark", "I WAS SIX", "it hurts it hurts"]),
    4: dict(who="noah3", hp=40, turn=10.0, rate=2.3, speed=1.0,
            words=["sorry", "mine", "BURN", "mama", "ALL OF US", "tea?", "kneel", "ignis et cinis", "ave putrescens", "HOLD HIM DOWN",
                   "thank you", "CORPUS PUTRE", "stay", "NEVER ENOUGH", "Clair de Lune", "ASH"]),
}
ULTRA_UNLOCK_DMG, ULTRA_HEAL, ULTRA_FREEZE, ULTRA_INVULN, ULTRA_SHIELD, ULTRA_SHARE = 15, 12, 5.0, 3.0, 2, 0.5
ULTRA_FREEZE_INVULN_HOLD = ULTRA_FREEZE + ULTRA_INVULN   # invulnerability ticks only while time runs: 3 s after the 5 s stop
PLAYER_HP = 35                     # one pool for all four phases (heals 8, tesseract 8, ultra 12 still work)
HEAL_AMOUNT = 8
INVULN = 0.8
HARD = 1.0                        # demanding: bullets are a bit faster, spawns a bit denser
GRAVITY = 4.0                     # rows per second the "weight" pattern pulls the heart
# (phase, fraction of Noah's life): crossing it plays a set-piece (boss_ui) and makes the next turn a climax in which the arena changes
THRESHOLDS = ((2, 0.5), (3, 0.5), (4, 0.5), (3, 0.2), (4, 0.2))
BIG_HIT = 10                      # a hit of this size cracks Noah's picture
ARC_RATE = {"calm": 1.3}          # calm turns spawn fewer words; the last 1.8 s of every turn are a breather too


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "text", "dmg", "home", "age")

    def __init__(self, x, y, vx, vy, text, dmg=3, home=False):
        self.x, self.y, self.vx, self.vy, self.text, self.dmg, self.home, self.age = x, y, vx, vy, text, dmg, home, 0.0

    def hits(self, hx, hy):
        return int(round(self.y)) == int(round(hy)) and self.x - 0.5 <= hx <= self.x + len(self.text) - 0.5


class Boss:
    def __init__(self, seed=0, power=0.0, lines=None, has_tesseract=False, ultra=False, phase=1):
        self.rng = random.Random(seed)
        self.power = max(0.0, min(1.0, power))          # 0..1: Noah's third personality is stronger near the tesseract
        self.phase = phase if phase in PHASES else 1
        self.shown = self.phase                      # the phase the SCREEN shows: it stays on the beaten one until the transition has played
        self.cracks = 0                              # big hits on this Noah: his picture cracks more with each (reset per phase)
        self.enemy_hp = PHASES[self.phase]["hp"]
        self.hp = PLAYER_HP
        self.hx, self.hy = W / 2.0, H - 2.0
        self.bullets = []
        self.state = "player"                           # player | enemy | won | lost
        self.t = 0.0
        self.spawn_t = 0.0
        self.invuln = 0.0
        self.defending = False
        self.heals = 3
        self.lines = lines or {}
        self.line_i = {1: 0, 2: 0, 3: 0, 4: 0}
        self.events = []                                # ("phase", 2) ("hit", dmg) ("won",) ... for UI and audio
        self.shake = False
        self.has_tesseract = has_tesseract or ultra
        self.tesseract_used = False
        self.first_hit_done = False                     # the first hit that lands decides whether the tesseract unfolds
        self.ultra_unlocked = bool(ultra)               # --ultra starts with it unlocked
        self.ultra_used = False
        self.ultra_announce = False                     # set when it unfolds; the screen plays the cinematic and clears it
        self.shield = 0                                 # hits the ultra shield still absorbs
        self.slow = 0.0                                 # honey: the heart wades through it
        self._last_step = -9.0
        self.hazards = []                               # themed patterns (patterns.py)
        self.script = []                                # [(time, pattern)] still to start in this enemy turn
        self.turns = {1: 0, 2: 0, 3: 0, 4: 0}
        self.freeze = 0.0                               # seconds during which words hang in the air
        self.retries = 0
        self.time = 0.0
        self.fx = {"shake": 0.0, "flash": 0.0}   # timers read by the screen: whole-screen shake and flash
        self.walls = []                              # sweeping rows of words with one gap (phase 3 and 4)
        self.dir = (0, 0)
        self.dir_t = -9.0
        self.streak = 0
        self.gravity = 0                             # -1 up, 0 none, 1 down: set every frame by a gravity hazard
        self.dark = 0.0                              # radius (rows) of the lit circle while the lights are out, else 0
        self.arc = "calm"                            # the shape of the current enemy turn: calm | build | climax | trinity | rage
        self.crossed = set()                         # HP thresholds already played
        self.rage = False                            # the next enemy turn is the one after a big hit
        self.wiped = []
        self.rage_turn = False                       # this enemy turn is that one (the arena is drawn differently)

    # --- phase data
    @property
    def cfg(self):
        return PHASES[self.phase]

    @property
    def who(self):
        """Whose colours and face the screen uses: the phase that is SHOWN (see `shown`)."""
        return PHASES[self.shown]["who"]

    @property
    def hp_shown(self):
        """Noah's life as the screen draws it: empty while the beaten phase is still on screen."""
        return self.enemy_hp if self.shown == self.phase else 0

    @property
    def hp_ratio(self):
        return max(0.0, min(1.0, self.hp_shown / float(PHASES[self.shown]["hp"])))

    # --- player turn
    def attack(self, accuracy):
        """accuracy 0..1 from the timing bar. Returns the damage dealt."""
        if self.state != "player":
            return 0
        dmg = damage_for(accuracy)
        if dmg > 0 and not self.first_hit_done:
            self.first_hit_done = True
            if dmg >= ULTRA_UNLOCK_DMG and self.has_tesseract and not self.tesseract_used and not self.ultra_unlocked:
                self.ultra_unlocked = self.ultra_announce = True
                self.events.append(("ultra_unlock",))
        self.enemy_hp -= dmg
        if dmg > 0:
            self.events.append(("boss_hit", dmg))
        if dmg >= BIG_HIT and self.enemy_hp > 0:
            self.cracks += 1
            self.events.append(("crack", self.cracks))
        if self.enemy_hp <= 0:
            self._next_phase()
        else:
            self._thresholds()
            self.begin_enemy_turn()
        return dmg

    def _thresholds(self):
        """Noah's life crossing 50% / 20%: one ("threshold", phase, percent) event for the deepest line crossed, and the next turn is a rage turn."""
        frac = self.enemy_hp / float(PHASES[self.phase]["hp"])
        hit = [pct for ph, pct in THRESHOLDS if ph == self.phase and frac <= pct and (ph, pct) not in self.crossed]
        for pct in hit:
            self.crossed.add((self.phase, pct))
        if hit:
            self.rage = True
            self.events.append(("threshold", self.phase, int(min(hit) * 100)))
            self.fx["shake"], self.fx["flash"] = 1.0, 0.2

    def defend(self):
        if self.state == "player":
            self.defending = True
            self.begin_enemy_turn()

    def heal(self):
        if self.state != "player" or self.heals <= 0:
            return False
        self.heals -= 1
        self.hp = min(PLAYER_HP, self.hp + HEAL_AMOUNT)
        self.begin_enemy_turn()
        return True

    def mercy(self):
        if self.state == "mercy":
            self.state = "won"
            self.events.append(("won",))
            return True
        return False

    def retry_phase(self):
        """After a defeat: the same phase again, full HP, Noah's HP for this phase restored."""
        self.hp = PLAYER_HP
        self.enemy_hp = PHASES[self.phase]["hp"]
        self.heals = max(self.heals, 2)
        self.turns[self.phase] = 0                  # a new try starts calm again
        self.cracks = 0
        self.rage = False
        self.bullets = []
        self.invuln = 0.0
        self.retries += 1
        self.events.append(("retry", self.phase))
        self.fx["shake"], self.fx["flash"] = 0.8, 0.2
        self.begin_enemy_turn()                    # no menu: the next attack starts at once

    def act(self, what):
        """ACT: 'check' or 'name'. Returns the text id/placeholder to show. Costs the turn."""
        if self.state != "player":
            return ""
        if what == "name":
            if self.phase == 1:
                self.enemy_hp = min(self.enemy_hp, 6)   # saying his name reaches the cute one: the phase nearly ends
                line = "[TEXT: boss.act.name]"
            else:
                line = "[TEXT: boss.act.noeffect]"
        else:
            line = "[TEXT: boss.act.check.%d]" % self.phase
        self.begin_enemy_turn()
        return line

    def ultra_unused(self):
        """True when the tesseract unfolded into the ULTRA TESSERACT and neither it nor the normal one was ever used (Mika's ending)."""
        return self.ultra_unlocked and not (self.tesseract_used or self.ultra_used)

    TESSERACT_HEAL, TESSERACT_FREEZE, TESSERACT_SHARE = 8, 3.0, 0.35

    def use_tesseract(self):
        """Once per fight: every attack on screen is erased, time stops for 3 s, you heal 8 HP, and the cube hits Noah for a
        third of this phase's life. (The screen plays a full ASCII animation first.)"""
        if self.state != "player" or not self.has_tesseract or self.tesseract_used:
            return False
        self.tesseract_used = True
        self.freeze = self.TESSERACT_FREEZE
        self.hp = min(PLAYER_HP, self.hp + self.TESSERACT_HEAL)
        dmg = int(round(PHASES[self.phase]["hp"] * self.TESSERACT_SHARE))
        self.enemy_hp = max(1, self.enemy_hp - dmg)
        self.events.append(("tesseract", dmg))
        self.fx["shake"], self.fx["flash"] = 1.5, 0.4
        self.begin_enemy_turn()
        self.freeze = self.TESSERACT_FREEZE
        return True

    def snapshot(self):
        """What the attacks look like right now as [(x, y, char)] arena cells (for the afterimages and for Mika's smoke to clear)."""
        out = []
        for bl in self.bullets:
            x, y = int(round(bl.x)), int(round(bl.y))
            out += [(x + i, y, ch) for i, ch in enumerate(bl.text) if 0 <= x + i < W and 0 <= y < H]
        for h in self.hazards:
            out += h.cells()[:160]
        return out

    def use_ultra(self):
        """The ULTRA TESSERACT, once per fight (see the module docstring for the numbers). Returns the damage dealt to Noah or 0."""
        if self.state != "player" or not self.ultra_unlocked or self.ultra_used:
            return 0
        self.wiped = self.snapshot()                       # what Mika's smoke clears (the screen animates it)
        self.ultra_used = self.tesseract_used = True
        self.hp = min(PLAYER_HP, self.hp + ULTRA_HEAL)
        dmg = int(round(PHASES[self.phase]["hp"] * ULTRA_SHARE))
        self.enemy_hp = max(1, self.enemy_hp - dmg)
        self.shield = ULTRA_SHIELD
        self.cracks += 3
        self.events.append(("ultra", dmg))
        self.begin_enemy_turn()
        self.freeze = ULTRA_FREEZE
        self.invuln = ULTRA_FREEZE_INVULN_HOLD            # ticks down only once time runs again
        self.fx["shake"], self.fx["flash"] = 2.0, 0.5
        return dmg

    def talk(self):
        """The line Noah says now (text id [TEXT: boss.<phase>.<n>] when the owner has not supplied one)."""
        ls = self.lines.get(self.phase) or []
        i = self.line_i[self.phase]
        self.line_i[self.phase] += 1
        return ls[i % len(ls)] if ls else "[TEXT: boss.p%d.%d]" % (self.phase, i)

    def _next_phase(self):
        if self.phase == 4:
            self.state = "mercy"                        # the fight is over: only MERCY (the final decision) is left
            self.bullets = []
            self.events.append(("mercy",))
            return
        self.phase += 1
        self.cracks = 0
        self.enemy_hp = PHASES[self.phase]["hp"]
        self.rage = False
        self.events.append(("phase", self.phase))
        self.fx["shake"], self.fx["flash"] = 1.2, 0.25
        self.begin_enemy_turn()

    # --- enemy turn
    def begin_enemy_turn(self):
        self.state = "enemy"
        self.t = 0.0
        self.spawn_t = 0.0
        self.bullets = []
        self.walls = []
        self.hazards = []
        self.slow = 0.0
        self.arc = "rage" if self.rage and self.phase in patterns.RAGE else patterns.arc_for(self.phase, self.turns[self.phase])
        self.script = patterns.schedule(self.phase, self.turns[self.phase], self.cfg["turn"], self.rng, self.arc)
        self.turns[self.phase] += 1
        self.gravity, self.dark = 0, 0.0
        self.events.append(("turn", self.arc))
        wall = DIFFICULTY[self.phase]["wall"]
        self.GAP = wall[1] if wall else self.GAP_DEFAULT                  # instance value: the screen reads b.GAP to draw the gap
        self.wall_t = (3.5 if self.arc == "calm" else 1.5) if wall else 99.0
        self.hx, self.hy = W / 2.0, H - 2.0
        self.shake = self.phase == 4
        self.rage_turn = self.arc == "rage"
        self.rage = False
        if self.arc in ("climax", "rage"):
            self.fx["shake"], self.fx["flash"] = max(self.fx["shake"], 0.45), max(self.fx["flash"], 0.1)

    def _spawn(self):
        c = self.cfg
        words = c["words"]
        p = self.phase
        d = DIFFICULTY[p]
        sp = c.get("speed", 1.0) * d["words_speed"]
        if p in (1, 4) or (p == 2 and self.rng.random() < d["cross"]):
            w = self.rng.choice(words)
            self.bullets.append(Bullet(self.rng.uniform(1, W - len(w) - 1), 0, 0, 3.5 * HARD * sp, w, dmg=4))
        if p == 2 or (p == 4 and self.rng.random() < d["cross"]):
            w = self.rng.choice(words)
            left = self.rng.random() < 0.5
            self.bullets.append(Bullet(-len(w) if left else W, self.rng.randint(1, H - 2),
                                       (7 if left else -7) * HARD * sp * (1 + 0.15 * self.power), 0, w, dmg=4))
        if p in (3, 4) and sum(1 for x in self.bullets if x.home) < 2 and self.rng.random() < d["hands"] * ((0.22 + 0.08 * self.power) if p == 3 else (0.25 + 0.1 * self.power)):
            self.bullets.append(Bullet(self.rng.choice([1, W - 3]), 0, 0, 0, "✠", dmg=5, home=True))   # shadow hand
        if p == 3:
            w = self.rng.choice(words)
            self.bullets.append(Bullet(self.rng.uniform(1, W - len(w) - 1), 0, 0, 3.6 * HARD * sp, w, dmg=3))

    WALL_WARN, WALL_LIVE, GAP, GAP_DEFAULT = 0.9, 0.45, 3, 3

    def _walls(self, dt, ev):
        """A row of words sweeps the arena with one gap: telegraphed for 0.9 s, then it hits for 0.45 s."""
        wall = DIFFICULTY[self.phase]["wall"]
        if wall:
            self.wall_t -= dt
            if self.wall_t <= 0 and len(self.walls) < 2:
                self.wall_t = wall[0]
                y = max(1, min(H - 2, int(round(self.hy)) + self.rng.randint(-3, 3)))
                gaps = [g for g in range(4, W - 4) if abs(g - self.hx) >= 4 + self.GAP] or [self.rng.randint(4, W - 5)]
                self.walls.append({"y": y, "gap": self.rng.choice(gaps), "age": 0.0, "hit": False})
        for w in self.walls:
            w["age"] += dt
            live = self.WALL_WARN <= w["age"] <= self.WALL_WARN + self.WALL_LIVE
            if live and not w["hit"] and self.invuln <= 0 and int(round(self.hy)) == w["y"] and abs(self.hx - w["gap"]) > self.GAP:
                w["hit"] = True
                if self._hurt(4, ev, 0.4):
                    return
        self.walls = [w for w in self.walls if w["age"] < self.WALL_WARN + self.WALL_LIVE + 0.1]

    def _hurt(self, dmg, ev, shake):
        """The heart takes a hit (the ultra shield eats it first). True when this was the lethal one."""
        self.invuln = INVULN
        if self.shield > 0:
            self.shield -= 1
            ev.append(("shield", self.shield))
            self.fx["shake"], self.fx["flash"] = 0.2, 0.06
            return False
        self.hp -= dmg
        self.fx["shake"], self.fx["flash"] = shake, 0.12
        ev.append(("hit", dmg))
        if self.hp <= 0:
            self.hp = 0
            self.state = "lost"
            self.bullets, self.walls, self.hazards = [], [], []
            ev.append(("lost",))
            return True
        return False

    def _patterns(self, dt, ev):
        """Start the scheduled patterns, age the hazards and let live ones hurt the heart (once each). True if the heart died."""
        while self.script and self.script[0][0] <= self.t:
            d = DIFFICULTY[self.phase]
            patterns.tight = d["tight"]
            new = patterns.PATTERNS[self.script.pop(0)[1]](self.rng, self.hx, self.hy, self.power)
            patterns.tight = 1.0
            for h in new:
                h.warn = max(MIN_WARN, h.warn * d["pace"]) if h.warn > MIN_WARN else h.warn
            self.hazards += new
            for s in dict.fromkeys(h.d.get("snd0", "warning") for h in new):          # a sound for each kind of warning
                ev.append(("sfx", s))
        rx, ry = int(round(self.hx)), int(round(self.hy))
        for h in self.hazards:
            h.age += dt
            if h.harmful and not h.d.get("on"):
                h.d["on"] = True
                if h.d.get("snd1"):
                    ev.append(("sfx", h.d["snd1"]))
                if h.d.get("pulse"):
                    self.fx["shake"] = max(self.fx["shake"], 0.2)
            step = patterns.STEP.get(h.kind)
            if step and h.harmful:
                step(h, dt, self)
            if h.harmful and (not h.hit or h.d.get("repeat")) and self.invuln <= 0 and any(c[0] == rx and c[1] == ry for c in h.cells()):
                h.hit = True
                if h.d.get("slow"):
                    self.slow = 2.0
                if self._hurt(max(1, h.dmg // 2) if self.defending else h.dmg, ev, 0.3):
                    return True
        self.hazards = [h for h in self.hazards if not h.done]
        if self.gravity:                                 # "weight": the heart is pulled, the player has to move against it
            self.hy = max(0.0, min(H - 1.0, self.hy + self.gravity * GRAVITY * dt))
        return False

    def step(self, dx, dy):
        """One key press moves the heart exactly one cell (a held key repeats), so a single press is always visible."""
        if self.state != "enemy":
            return
        if self.slow > 0 and self.time - self._last_step < 0.2:      # honey: steps come slowly
            return
        self._last_step = self.time
        self.hx = max(0.0, min(W - 1.0, round(self.hx) + dx))
        self.hy = max(0.0, min(H - 1.0, round(self.hy) + dy))
        # a second press in the same direction soon after the first means the key is held: glide smoothly
        same = (dx, dy) == self.dir and self.time - self.dir_t < 0.6
        self.streak = self.streak + 1 if same else 0
        self.dir, self.dir_t = (dx, dy), self.time

    def update(self, dt, dx=0, dy=0):
        """Advance the dodge phase by dt seconds; dx, dy in {-1,0,1}. Returns events produced."""
        ev = []
        if self.state != "enemy":
            return ev
        self.time += dt
        for k in self.fx:
            self.fx[k] = max(0.0, self.fx[k] - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.slow = max(0.0, self.slow - dt)
        self.gravity, self.dark = 0, 0.0                 # hazards set them again this frame
        if self.streak >= 1 and self.time - self.dir_t <= 0.15 and self.dir != (0, 0):
            self.hx = max(0.0, min(W - 1.0, self.hx + self.dir[0] * 16.0 * dt))
            self.hy = max(0.0, min(H - 1.0, self.hy + self.dir[1] * 9.0 * dt))
        self.invuln = max(0.0, self.invuln)
        k = 0.4 if self.slow > 0 else 1.0
        self.hx = max(0.0, min(W - 1.0, self.hx + dx * 14.0 * dt * k))
        self.hy = max(0.0, min(H - 1.0, self.hy + dy * 9.0 * dt * k))
        if self.freeze > 0:                              # time is stopped: the heart can move, nothing else does
            used = min(self.freeze, dt)
            self.freeze -= used
            dt -= used
            if dt <= 1e-9:
                self.events += ev
                return ev
        self.t += dt                                     # the turn timer stops with time
        self.spawn_t += dt
        rate = self.cfg["rate"] / (1 + 0.08 * self.power) / HARD * ARC_RATE.get(self.arc, 1.0)
        rate *= DIFFICULTY[self.phase]["words_rate"]
        if self.t > self.cfg["turn"] - DIFFICULTY[self.phase]["breather"]:
            rate *= 1.8                                  # the breather at the end of every turn
        while self.spawn_t >= rate:
            self.spawn_t -= rate
            self._spawn()
        for b in self.bullets:
            b.age += dt
            if b.home:
                ang = math.atan2(self.hy - b.y, self.hx - b.x)
                sp = 2.0 + 0.5 * self.power
                b.vx, b.vy = math.cos(ang) * sp, math.sin(ang) * sp
                if b.age > 3.5:
                    b.vy = -4
            b.x += b.vx * dt
            b.y += b.vy * dt
            if self.invuln <= 0 and b.hits(self.hx, self.hy) if not b.home else \
                    (self.invuln <= 0 and abs(b.x - self.hx) < 1.0 and abs(b.y - self.hy) < 0.8):
                if self._hurt(max(1, b.dmg // 2) if self.defending else b.dmg, ev, 0.35):
                    self.events += ev
                    return ev
        self.bullets = [b for b in self.bullets if -12 < b.x < W + 12 and -3 < b.y < H + 3]
        self._walls(dt, ev)
        if self.state != "lost" and self._patterns(dt, ev):
            self.events += ev
            return ev
        if self.state == "lost":                         # a wall killed the heart: the turn must not end as "your turn"
            self.events += ev
            return ev
        if self.t >= self.cfg["turn"]:
            self.state = "player"
            self.defending = False
            self.bullets, self.hazards = [], []
            self.shake = False
            self.gravity, self.dark = 0, 0.0
            ev.append(("your_turn",))
        self.events += ev
        return ev


MAX_HIT = 18


def damage_for(accuracy):
    """0 = far from the middle (a miss), 1 = dead centre (MAX_HIT). Grows steeply towards the centre."""
    a = max(0.0, min(1.0, accuracy))
    return 0 if a < 0.08 else max(1, int(round(MAX_HIT * a ** 1.6)))


def offset(position):
    """Distance from the middle of the bar as a number from -15 to 15 (0 = perfect)."""
    return int(round((position - 0.5) * 30))


def timing_accuracy(position):
    """Position of the sliding cursor 0..1 across the bar; 1.0 = dead centre."""
    return max(0.0, 1.0 - abs(position - 0.5) * 2.0)
