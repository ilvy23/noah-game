# engine.py — FOLK: the state, sanity, save/load, and text rendering.
"""Core engine for the terminal folk-horror game FOLK.

No external dependencies. Stdlib only.
"""

import json
import os
import re
import sys
import time

import music  # noqa: F401  — background music; engine owns the save path, music never touches it

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


def render(text: str, pace: float = 0.004, pause_after: float = 0.0) -> None:
    """Print text in short blocks (line by line) with a faint pace.

    Keeps full lines intact so colors are not split. A single Ctrl-C exits
    cleanly; a double Ctrl-C hard-stops.
    """
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n")]
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
        self.sanity: int = 80                  # 0–100
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
        self._noah_rest_day: int = 0           # last day Noah restored sanity

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

    # -- sanity -------------------------------------------------------------
    def sanity_change(self, delta: int, reason: str = "") -> None:
        before = self.sanity
        self.sanity = max(0, min(100, self.sanity + delta))
        after = self.sanity
        if after < before:
            render_quiet(f"\n{C_DIM}(something inside you settles a little further down. "
                         f"sanity {before} → {after}){C_RESET}")
        elif after > before:
            render_quiet(f"\n{C_DIM}(the air tastes a little less like water. "
                         f"sanity {before} → {after}){C_RESET}")
        if before > 40 >= after:
            render(f"\n{C_DIM}— the second person in your head starts calling itself “we.” —{C_RESET}")
        if before > 20 >= after:
            render(f"\n{C_RED}— you are no longer sure which direction is out. —{C_RESET}")

    @property
    def sanity_tier(self) -> str:
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
            "version": 3,
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
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
    return SAVE_PATH


def load_game() -> State:
    with open(SAVE_PATH, "r", encoding="utf-8") as f:
        return State.from_dict(json.load(f))


def save_exists() -> bool:
    return os.path.exists(SAVE_PATH)
