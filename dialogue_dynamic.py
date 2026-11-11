"""Dynamic dialogue selection for the story game.

This module adds a small, self-contained layer on top of the existing
dialogue engine.  It lets dialogue authors attach *variants* to any line
and have the engine pick the right one based on:

* the player's current inventory items,
* stat thresholds (trust, fear, level, ...),
* the player's decision history.

Nothing here modifies existing state; it only *reads* it.  All helpers
degrade gracefully: if the state has no inventory, no stats, or no
decision history, the fallback line is returned unchanged.

Usage
-----
    from dialogue_dynamic import pick

    line = pick(s, {
        "default": "You look tired.",
        "has:flashlight": "The flashlight in your hand makes you feel safer.",
        "trust>=3": "You trust me, don't you?",
        "decided:helped_mika": "You still think about that night with Mika.",
    })

Each key is a *condition*.  The first condition that matches wins;
``default`` always matches and is checked last.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Condition parsing
# ---------------------------------------------------------------------------

# A condition is one of:
#   default                          -> always matches
#   has:<item_id>                    -> item in inventory
#   has_any:<id1>,<id2>              -> at least one of the listed items
#   trust>=N / trust<=N / trust==N   -> stat comparison (trust, fear, level)
#   decided:<decision_id>            -> decision recorded in history
#   not_decided:<decision_id>        -> decision NOT recorded
#   familiarity>=N                   -> familiarity with a character (via
#                                       characters.get_relationship)
_COND_RE = re.compile(
    r"^(?P<kind>has_any|has|trust|fear|level|familiarity|decided|not_decided)"
    r"(?P<op>>=|<=|==|!=|>|<)?"
    r"(?P<value>.*)$"
)


def _get_inventory(s) -> List[str]:
    """Return the player's inventory as a list of item ids (never raises)."""
    inv = getattr(s, "inventory", None)
    if inv is None:
        return []
    if isinstance(inv, dict):
        return [k for k, v in inv.items() if v]
    if isinstance(inv, (list, tuple, set)):
        return list(inv)
    return []


def _get_stat(s, name: str) -> Optional[int]:
    """Return a numeric stat from the state, or None if absent."""
    val = getattr(s, name, None)
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    return None


def _get_familiarity(s, who: str) -> Optional[int]:
    """Return familiarity with a character via characters.get_relationship."""
    try:
        from characters import get_relationship
    except Exception:
        return None
    try:
        rel = get_relationship(s, who)
    except Exception:
        return None
    if rel is None:
        return None
    fam = rel.get("familiarity") if isinstance(rel, dict) else getattr(rel, "familiarity", None)
    if isinstance(fam, (int, float)) and not isinstance(fam, bool):
        return int(fam)
    return None


def _has_decision(s, decision_id: str) -> bool:
    """Check whether a decision id is present in the player's history.

    Looks through every character relationship for the decision id, then
    falls back to a flat ``s.decisions`` list/set/dict if present.
    """
    # Try the characters module: search all known relationships.
    try:
        from characters import get_relationship
        from context import last as _ctx_last
        # Determine who from context if possible
        who = ""
        try:
            rec = _ctx_last(s)
            if rec and isinstance(rec, dict):
                who = rec.get("who", "")
        except Exception:
            pass
        if who:
            rel = get_relationship(s, who)
            if rel and decision_id in rel.get("decisions", []):
                return True
    except Exception:
        pass
    # Fallback: look at s.decisions (list or set of ids).
    dec = getattr(s, "decisions", None)
    if dec is None:
        return False
    if isinstance(dec, (list, tuple, set)):
        return decision_id in dec
    if isinstance(dec, dict):
        return decision_id in dec
    return False


def _compare(op: str, actual: Optional[int], target: int) -> bool:
    """Apply a comparison operator; returns False if actual is None."""
    if actual is None:
        return False
    if op == ">=":
        return actual >= target
    if op == "<=":
        return actual <= target
    if op == "==":
        return actual == target
    if op == "!=":
        return actual != target
    if op == ">":
        return actual > target
    if op == "<":
        return actual < target
    return False


def condition_matches(s, condition: str) -> bool:
    """Evaluate a single condition string against the player state.

    Returns True if the condition is met, False otherwise.
    Unknown or malformed conditions return False (never raise).
    """
    if not condition or not isinstance(condition, str):
        return False
    condition = condition.strip()
    if condition == "default":
        return True

    m = _COND_RE.match(condition)
    if not m:
        return False

    kind = m.group("kind")
    op = m.group("op") or ""
    value = m.group("value").strip()

    # --- inventory conditions ---
    if kind == "has":
        return value in _get_inventory(s)

    if kind == "has_any":
        items = [x.strip() for x in value.split(",") if x.strip()]
        inv = _get_inventory(s)
        return any(item in inv for item in items)

    # --- stat conditions ---
    if kind in ("trust", "fear", "level"):
        if not op:
            return False
        try:
            target = int(value)
        except (ValueError, TypeError):
            return False
        actual = _get_stat(s, kind)
        return _compare(op, actual, target)

    # --- familiarity conditions ---
    if kind == "familiarity":
        # Format: familiarity:<who> or familiarity>=N (uses last-interaction who)
        if not op:
            return False
        try:
            target = int(value)
        except (ValueError, TypeError):
            return False
        # Try to get the "who" from context.last(s)
        who = ""
        try:
            from context import last as _ctx_last
            rec = _ctx_last(s)
            if rec and isinstance(rec, dict):
                who = rec.get("who", "")
        except Exception:
            pass
        if not who:
            return False
        actual = _get_familiarity(s, who)
        return _compare(op, actual, target)

    # --- decision conditions ---
    if kind == "decided":
        return _has_decision(s, value)

    if kind == "not_decided":
        return not _has_decision(s, value)

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pick(s, variants: Dict[str, str], fallback: str = "") -> str:
    """Select a dialogue line from a dict of condition -> line variants.

    Parameters
    ----------
    s : State
        The player state object (any object with the expected attributes).
    variants : dict
        Mapping of condition strings to dialogue lines.  Keys are evaluated
        in insertion order; the first match wins.  A key of ``"default"``
        (or the ``fallback`` argument) is used when nothing else matches.
    fallback : str, optional
        Line to return if no condition matches and no ``default`` key exists.

    Returns
    -------
    str
        The selected dialogue line.  Never raises; returns ``fallback``
        (or ``""``) if the state is missing or no variant matches.
    """
    if not variants or not isinstance(variants, dict):
        return fallback

    for condition, line in variants.items():
        try:
            if condition_matches(s, condition):
                return line if isinstance(line, str) else str(line)
        except Exception:
            # A broken condition should never crash the game.
            continue

    # No condition matched; try an explicit default key.
    if "default" in variants:
        line = variants["default"]
        return line if isinstance(line, str) else str(line)

    return fallback


def pick_first(s, conditions: List[str], lines: List[str], fallback: str = "") -> str:
    """Pick the first line whose corresponding condition matches.

    ``conditions`` and ``lines`` must be the same length.  This is a
    convenience wrapper around :func:`pick` for callers that prefer
    parallel lists over a dict.
    """
    if not conditions or not lines:
        return fallback
    n = min(len(conditions), len(lines))
    variants = {conditions[i]: lines[i] for i in range(n)}
    return pick(s, variants, fallback)


def has_item(s, item_id: str) -> bool:
    """True if the player currently carries ``item_id``."""
    return item_id in _get_inventory(s)


def stat_at_least(s, name: str, threshold: int) -> bool:
    """True if the named stat is >= threshold (False if stat is missing)."""
    actual = _get_stat(s, name)
    return actual is not None and actual >= threshold


def decided(s, decision_id: str) -> bool:
    """True if the player has recorded the given decision."""
    return _has_decision(s, decision_id)
