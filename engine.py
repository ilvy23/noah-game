# -*- coding: utf-8 -*-
# sanity field is preserved in save data but not displayed or processed by the engine
"""Core engine for the terminal folk-horror game FOLK.

No external dependencies. Stdlib only.
"""

import json
import os
import re
import sys
import time

import context
import music  # noqa: F401  — background music; engine owns the save path, music never touches it

# achievements is imported lazily inside save_game to avoid a circular import
# (achievements.py imports from engine.py at module level).


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(PROJECT_DIR, "save.json")

# ---------------------------------------------------------------------------
# ANSI colors (auto-detected; fall back to plain text)
# ---------------------------------------------------------------------------

_COLOR_OK = sys.stdout.isatty() and os.environ.get("TERM") not in (None, "dumb")

if _COLOR_OK:
    C_DIM = "\x1b[2m"
    C_FOG = "\x1b[38;5;242m"
    C_RED = "\x1b[38;5;167m"
    C_GHOST = "\x1b[38;5;110m"
    C_TOWN = "\x1b[38;5;222m"
    C_RESET = "\x1b[0m"
else:
    C_DIM = C_FOG = C_RED = C_GHOST = C_TOWN = C_RESET = ""


def _bell() -> None:
    if _COLOR_OK:
        sys.stdout.write("\a")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

def _strip_ansi(s: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


def _visible_len(s: str) -> int:
    return len(_strip_ansi(s))


VOICE = "narrator"          # who is speaking right now (dialogue code sets it): noah, mika, connor, narrator


def set_voice(name: str) -> None:
    global VOICE
    VOICE = name or "narrator"


def _typewriter_ok() -> bool:
    return sys.stdout.isatty() and not os.environ.get("FOLK_PLAIN")


def render(text: str, pace: float = 0.004, pause_after: float = 0.0) -> None:
    """Print text in short blocks (line by line) with a faint pace.

    Keeps full lines intact so colors are not split. A single Ctrl-C exits
    cleanly; a double Ctrl-C hard-stops.
    """
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
    if _typewriter_ok() and text.strip():
        try:
            import audio
            import ui
            with ui.Keys() as keys:
                ui.reveal(text.replace("\r\n", "\n"), VOICE, speed=0.009, keys=keys, mixer=audio.get())
            if pause_after:
                time.sleep(pause_after)
            return
        except (KeyboardInterrupt, EOFError):
            print(f"\n{C_DIM}(you close your eyes for a moment…){C_RESET}")
            raise SystemExit("\n\nFOLK will remember where you were. Type: save\n") from None
    try:
        for i, ln in enumerate(lines):
            print(ln)
            sys.stdout.flush()
            if i < len(lines) - 1:
                time.sleep(pace * max(1, _visible_len(ln)) + 0.001)
        if pause_after:
            time.sleep(pause_after)
    except (KeyboardInterrupt, EOFError):
        print(f"\n{C_DIM}(you close your eyes for a moment…){C_RESET}")
        raise SystemExit("\n\nFOLK will remember where you were. Type: save\n") from None


def render_quiet(text: str) -> None:
    print(text)
    sys.stdout.flush()


def rule(width: int = 46) -> None:
    print(f"{C_DIM}{'~' * width}{C_RESET}")


def prompt() -> None:
    print(f"\n{C_DIM}> {C_RESET}", end="")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class State:
    """Everything the game remembers about the player's week.

    v2 adds: trust / fear (relationship values), a journal of what you
    learned and decided, a death counter, and a `seen` set that tracks
    which locations have already had their full description printed
    (so revisits get a one-liner instead of the whole scene).
    """

    def __init__(self) -> None:
        self.location: str = "lunuen"          # location id
        self.sanity: int = 80  # 0–100 (hidden internal meter, not displayed)
        self.trust: int = 0                    # -100..100  (NPCs' trust in you)
        self.fear: int = 0                     # -100..100  (your fear of the valley)
        self.flags: dict = {}                  # story flags
        self.inventory: list = []              # item ids
        self.visited: list = ["lunuen"]        # location ids seen
        self.seen: list = []                   # location ids whose full text was printed
        self.journal: list = []                # list of {"kind":..., "text":...}
        self.deaths: int = 0                   # how many times you have died
        self.day: int = 1                      # 1..7
        self.night: bool = False               # time of day in town
        self.chapter: int = 1                  # story chapter (1..5)
        self._connor_line: int = 0             # dialogue index (kept for old saves)
        self._mika_line: int = 0
        self._noah_rest_day: int = 0           # last day Noah's rest was applied
        self.context = None                    # last interaction (see context.py)
        self.achievements: list = []           # unlocked achievement ids (v4)
        self.relationships: dict = {}          # per-NPC relationship state (characters.py)
        self.motivations: dict = {}            # voiced motivation lines (characters.py)

    # -- relationships ------------------------------------------------------
    def trust_change(self, delta: int, reason: str = "") -> None:
        before = self.trust
        self.trust = max(-100, min(100, self.trust + delta))
        if self.trust != before:
            render_quiet(f"\n{C_DIM}(the valley's trust in you shifts a little. "
                         f"trust {before} → {self.trust}){C_RESET}")

    def fear_change(self, delta: int, reason: str = "") -> None:
        before = self.fear
        self.fear = max(-100, min(100, self.fear + delta))
        if self.fear != before:
            render_quiet(f"\n{C_DIM}(the fear in you settles a little further. "
                         f"fear {before} → {self.fear}){C_RESET}")

    # -- journal ------------------------------------------------------------
    def journal_add(self, kind: str, text: str) -> None:
        """kind is one of: 'learned', 'decided', 'met', 'item', 'death'."""
        entry = {"kind": kind, "text": text}
        # avoid exact duplicates
        for e in self.journal:
            if e.get("kind") == kind and e.get("text") == text:
                return
        self.journal.append(entry)

    def journal_has(self, kind: str, text: str) -> bool:
        return any(e.get("kind") == kind and e.get("text") == text for e in self.journal)

    # -- hidden internal meter (no on-screen messages) ---------------------
    def sanity_change(self, delta: int, reason: str = "") -> None:
        """Adjust the hidden internal meter silently (no on-screen message)."""
        self.sanity = max(0, min(100, self.sanity + delta))

    @property
    def sanity_tier(self) -> str:
        """Return a tier name for the current hidden meter value (mechanics only)."""
        if self.sanity >= 60:
            return "steady"
        if self.sanity >= 40:
            return "thin"
        if self.sanity >= 20:
            return "low"
        return "critical"

    def flag(self, name: str, value: bool = True) -> None:
        self.flags[name] = value

    def has(self, name: str) -> bool:
        return bool(self.flags.get(name))

    # -- inventory ----------------------------------------------------------
    def take(self, item_id: str) -> bool:
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            return True
        return False

    def has_item(self, item_id: str) -> bool:
        return item_id in self.inventory

    # -- persistence --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": 4,
            "location": self.location,
            "sanity": self.sanity,
            "trust": self.trust,
            "fear": self.fear,
            "flags": self.flags,
            "inventory": self.inventory,
            "visited": self.visited,
            "seen": self.seen,
            "journal": self.journal,
            "deaths": self.deaths,
            "day": self.day,
            "night": self.night,
            "chapter": self.chapter,
            "connor_line": self._connor_line,
            "mika_line": self._mika_line,
            "noah_rest_day": self._noah_rest_day,
            "context": self.context,
            "achievements": self.achievements,
            "relationships": self.relationships,
            "motivations": self.motivations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "State":
        """Load a save. v1 saves (no `version` key) are migrated in place:
        missing fields get their defaults, old fields are preserved."""
        s = cls()
        s.location = d.get("location", "lunuen")
        s.sanity = d.get("sanity", 80)
        s.trust = d.get("trust", 0)
        s.fear = d.get("fear", 0)
        s.flags = d.get("flags", {})
        s.inventory = d.get("inventory", [])
        s.visited = d.get("visited", ["lunuen"])
        s.seen = d.get("seen", [])
        s.journal = d.get("journal", [])
        s.deaths = d.get("deaths", 0)
        s.day = d.get("day", 1)
        s.night = d.get("night", False)
        s.chapter = d.get("chapter", 1)
        s._connor_line = d.get("connor_line", 0)
        s._mika_line = d.get("mika_line", 0)
        s._noah_rest_day = d.get("noah_rest_day", 0)
        s.context = d.get("context")           # last interaction (v3 saves)
        s.achievements = d.get("achievements", [])  # v4: unlocked achievement ids
        s.relationships = d.get("relationships", {})  # v5: per-NPC relationship state
        s.motivations = d.get("motivations", {})      # v5: voiced motivation lines
        # v1 -> v2 migration: if the save has no `seen` list, treat every
        # visited location as already-seen so the player does not get a
        # surprise full-text dump on their first revisit.
        if "seen" not in d and "visited" in d:
            s.seen = list(d["visited"])
        # v2 -> v3 migration: chapter field (defaults to 1 if absent).
        # v1 saves (no `version` key) and v2 saves (version: 2) both get
        # chapter=1 and their existing data preserved.
        if "chapter" not in d:
            s.chapter = 1
        return s


def save_game(state: State) -> str:
    """Save the game state and check for newly-earned achievements.

    `achievements.check_all(s)` is called here so that every save point
    (after talking, moving, finding items, surviving a day, reaching an
    ending or a death) triggers the 'Achievement unlocked: <name>' line
    exactly once per achievement.
    """
    import achievements  # deferred: avoids circular import at module load
    try:
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
    except (PermissionError, OSError) as exc:
        render_quiet(f"\n{C_DIM}(the valley could not write your name down this time. "
                     f"the week will keep it in its own way.){C_RESET}")
        return ""
    achievements.check_all(state)
    return SAVE_PATH


def load_game() -> State:
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        return State.from_dict(json.load(f))


def save_exists() -> bool:
    return os.path.exists(SAVE_PATH)


# ===========================================================================
# INTEGRATION LAYER — dialogue & character systems
# ===========================================================================
# These helpers are the single place where the engine talks to the new
# dialogue.py and characters.py systems.  They are pure readers/writers of
# State; they never mutate anything except the State object passed in.

import dialogue as _dialogue
import characters as _characters


def player_inventory(s) -> list:
    """Return the player's inventory as a list of item ids (never raises)."""
    inv = getattr(s, "inventory", None)
    if inv is None:
        return []
    if isinstance(inv, dict):
        return [k for k, v in inv.items() if v]
    if isinstance(inv, (list, tuple, set)):
        return list(inv)
    return []


def player_stats(s) -> dict:
    """Return a dict of the player's numeric stats (trust, fear, level, sanity)."""
    stats = {}
    for name in ("trust", "fear", "level", "sanity"):
        val = getattr(s, name, None)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            stats[name] = int(val)
    return stats


def decision_history(s) -> list:
    """Return a flat list of all decision ids recorded across all NPCs."""
    out = []
    # Per-NPC decisions stored by characters.py
    rels = getattr(s, "relationships", None)
    if isinstance(rels, dict):
        for who, rel in rels.items():
            if isinstance(rel, dict):
                for d in rel.get("decisions", []):
                    if d not in out:
                        out.append(d)
    # Global decisions list (if present)
    dec = getattr(s, "decisions", None)
    if isinstance(dec, (list, tuple, set)):
        for d in dec:
            if d not in out:
                out.append(d)
    elif isinstance(dec, dict):
        for d in dec:
            if d not in out:
                out.append(d)
    return out


def update_relationship(s, who: str, trust_delta: int = 0,
                        familiarity_delta: int = 0) -> str:
    """Apply an interaction's effect to an NPC's relationship.

    Delegates to characters.update_relationship and returns the new
    relationship state label (e.g. 'friendly', 'hostile', 'neutral').
    Also syncs the global s.trust so dialogue.py's stat checks work.
    """
    state = _characters.update_relationship(s, who, trust_delta, familiarity_delta)
    # Sync global trust so dialogue.py's _dyn_get_stat(s, 'trust') sees it
    rel = getattr(s, "relationships", {}).get(who, {})
    if isinstance(rel, dict) and "trust" in rel:
        s.trust = rel["trust"]
    return state


def record_player_decision(s, who: str, decision: str) -> None:
    """Record a player decision in the NPC's relationship record."""
    _characters.record_decision(s, who, decision)


def has_player_decision(s, who: str, decision: str) -> bool:
    """Check whether the player made a specific decision with this NPC."""
    return _characters.has_decision(s, who, decision)


def pick_dialogue_line(s, variants: dict, fallback: str = "") -> str:
    """Select a dialogue line using dialogue.py's dynamic selection.

    `variants` is a dict of condition -> line.  The first matching
    condition wins; 'default' is checked last.
    """
    return _dialogue.pick_dynamic(s, variants, fallback)


def npc_reaction(s, who: str, base_text: str) -> str:
    """Get the NPC's reaction line for the current relationship state.

    Delegates to characters.select_line, which checks the NPC's
    relationship state, decision history, and motivation to pick the
    most appropriate line.
    """
    return _characters.select_line(s, who, base_text)


def motivation_line(s, who: str):
    """Return the NPC's motivation line for the current state, or None."""
    return _characters.motivation_line(s, who)


def motivation_shift(s, who: str):
    """Check whether the NPC's motivation has shifted; return the line or None."""
    return _characters.motivation_shift(s, who)


def relationship_state(s, who: str) -> str:
    """Return the current relationship state label for an NPC."""
    return _characters.rel_state(s, who)


def bump_familiarity(s, who: str, amount: int = 1) -> None:
    """Increase the player's familiarity with an NPC."""
    _characters.bump_familiarity(s, who, amount)
