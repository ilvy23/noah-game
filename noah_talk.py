"""noah_talk.py - Noah's short lines during the fight (pure logic: no curses, no I/O, deterministic with a seeded rng).

Lines live in story/boss_texts.json:
    boss.talk.<kind>              lines for any phase            boss.talk.<phase>.<kind>   lines of one personality (1 green .. 4 fusion)
    boss.talk.flag.<flag>         only after a story decision (the story flag is set)
kinds: idle (every few seconds), hit (the player hit him), big (a big hit), hurt (the player got hurt), low (the player is nearly dead),
       heal, weak (he is nearly dead), miss, death (the player died), user (key moments only: the player's name, {user})
A line is never repeated before every other line of its list was used. `{user}` is the system user name and appears only in the "user" kind.
"""
import random

IDLE_EVERY = (3.5, 6.0)            # seconds between two idle lines in the dodge phase (random in this range)
FLAG_CHANCE = 0.22                 # chance that an idle line is one that belongs to a story decision the player made
FLAGS = ("promise", "gift", "paid_cost", "rehearsed", "kind_mug", "kind_fox", "kind_record", "bond", "joined", "invited", "note", "tesseract", "dream_done")
COOLDOWN = 2.2                     # minimum seconds between two event lines (hit / hurt / low ...)


class Talker:
    def __init__(self, texts=None, has=None, rng=None, user="friend"):
        self.texts, self.has, self.user = texts or {}, has or (lambda f: False), user
        self.rng = rng or random.Random()
        self.used = {}                      # list key -> indexes already said
        self.last = ""
        self.next_idle = self.rng.uniform(*IDLE_EVERY)
        self.quiet = 0.0                    # cooldown left for event lines

    def _lines(self, key):
        v = self.texts.get(key)
        return v if isinstance(v, list) else ([v] if isinstance(v, str) and v else [])

    def _take(self, key):
        """A line of one list that was not used before the list ran out (and never the same one twice in a row)."""
        ls = self._lines(key)
        if not ls:
            return ""
        used = self.used.setdefault(key, set())
        fresh = [i for i in range(len(ls)) if i not in used and ls[i] != self.last]
        if not fresh:
            used.clear()
            fresh = [i for i in range(len(ls)) if ls[i] != self.last] or list(range(len(ls)))
        i = self.rng.choice(fresh)
        used.add(i)
        return ls[i]

    def pick(self, phase, kind):
        """One line for this kind, preferring the personality's own list, or "" when there is none."""
        pool = [k for k in ("boss.talk.%d.%s" % (phase, kind), "boss.talk.%s" % kind) if self._lines(k)]
        if not pool:
            return ""
        key = pool[0] if len(pool) == 1 or self.rng.random() < 0.7 else pool[1]
        line = self._take(key).replace("{user}", self.user)
        self.last = line
        return line

    def flag_line(self):
        """A line about something the player did earlier in the story, or "" when no decision has a line yet."""
        got = [f for f in FLAGS if self.has(f) and self._lines("boss.talk.flag." + f)]
        if not got:
            return ""
        line = self._take("boss.talk.flag." + self.rng.choice(got))
        self.last = line
        return line

    def event(self, phase, kind):
        """A line for something that just happened; "" while the last one is still fresh (so lines never pile up)."""
        if self.quiet > 0:
            return ""
        line = self.pick(phase, kind)
        if line:
            self.quiet = COOLDOWN
        return line

    def tick(self, dt, phase):
        """Called every frame of the dodge phase: returns an idle line when it is time (about every 3.5-6 s), else ""."""
        self.quiet = max(0.0, self.quiet - dt)
        self.next_idle -= dt
        if self.next_idle > 0:
            return ""
        self.next_idle = self.rng.uniform(*IDLE_EVERY)
        if self.rng.random() < FLAG_CHANCE:
            line = self.flag_line()
            if line:
                return line
        return self.pick(phase, "idle")

    def key_moment(self, phase):
        """The player's name, once, at a moment that matters (the start of the fusion, a very low Noah, the fifth death...)."""
        return self.pick(phase, "user")
