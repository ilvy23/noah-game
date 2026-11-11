# tests/test_dialogue_dynamic.py — unit tests for the dynamic dialogue
# selection layer added to dialogue.py (pick_dynamic, condition_matches,
# has_item, stat_at_least, decided, pick_first).

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import State
import dialogue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state(inventory=None, trust=0, fear=0, decisions=None):
    """Build a State with the given attributes."""
    s = State()
    if inventory is not None:
        s.inventory = list(inventory)
    s.trust = trust
    s.fear = fear
    if decisions is not None:
        s.decisions = list(decisions)
    return s


# ---------------------------------------------------------------------------
# condition_matches — inventory
# ---------------------------------------------------------------------------

def test_has_item_matches():
    s = _state(inventory=["flashlight", "note"])
    assert dialogue.condition_matches(s, "has:flashlight") is True


def test_has_item_no_match():
    s = _state(inventory=["flashlight"])
    assert dialogue.condition_matches(s, "has:nonexistent") is False


def test_has_any_one_match():
    s = _state(inventory=["flashlight"])
    assert dialogue.condition_matches(s, "has_any:flashlight,other") is True


def test_has_any_no_match():
    s = _state(inventory=["flashlight"])
    assert dialogue.condition_matches(s, "has_any:other,another") is False


def test_has_empty_inventory():
    s = _state(inventory=[])
    assert dialogue.condition_matches(s, "has:flashlight") is False


# ---------------------------------------------------------------------------
# condition_matches — stats
# ---------------------------------------------------------------------------

def test_trust_gte_match():
    s = _state(trust=5)
    assert dialogue.condition_matches(s, "trust>=3") is True


def test_trust_gte_no_match():
    s = _state(trust=2)
    assert dialogue.condition_matches(s, "trust>=3") is False


def test_trust_eq_match():
    s = _state(trust=5)
    assert dialogue.condition_matches(s, "trust==5") is True


def test_trust_eq_no_match():
    s = _state(trust=5)
    assert dialogue.condition_matches(s, "trust==6") is False


def test_fear_lte_match():
    s = _state(fear=2)
    assert dialogue.condition_matches(s, "fear<=2") is True


def test_fear_gt_no_match():
    s = _state(fear=2)
    assert dialogue.condition_matches(s, "fear>2") is False


def test_stat_missing_returns_false():
    s = State()  # trust defaults to 0
    assert dialogue.condition_matches(s, "trust>=100") is False


# ---------------------------------------------------------------------------
# condition_matches — decisions
# ---------------------------------------------------------------------------

def test_decided_match():
    s = _state(decisions=["helped_mika"])
    assert dialogue.condition_matches(s, "decided:helped_mika") is True


def test_decided_no_match():
    s = _state(decisions=["helped_mika"])
    assert dialogue.condition_matches(s, "decided:abandoned_mika") is False


def test_not_decided_match():
    s = _state(decisions=["helped_mika"])
    assert dialogue.condition_matches(s, "not_decided:abandoned_mika") is True


def test_not_decided_no_match():
    s = _state(decisions=["helped_mika"])
    assert dialogue.condition_matches(s, "not_decided:helped_mika") is False


def test_decided_empty_history():
    s = _state(decisions=[])
    assert dialogue.condition_matches(s, "decided:helped_mika") is False
    assert dialogue.condition_matches(s, "not_decided:helped_mika") is True


# ---------------------------------------------------------------------------
# condition_matches — default and malformed
# ---------------------------------------------------------------------------

def test_default_always_matches():
    s = State()
    assert dialogue.condition_matches(s, "default") is True


def test_malformed_condition_returns_false():
    s = State()
    assert dialogue.condition_matches(s, "garbage") is False
    assert dialogue.condition_matches(s, "") is False
    assert dialogue.condition_matches(s, None) is False


# ---------------------------------------------------------------------------
# pick_dynamic
# ---------------------------------------------------------------------------

def test_pick_dynamic_selects_matching_variant():
    s = _state(inventory=["flashlight"], trust=5)
    variants = {
        "has:flashlight": "You feel safe with the flashlight.",
        "trust>=3": "You trust me, don't you?",
        "default": "You look tired.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You feel safe with the flashlight."


def test_pick_dynamic_first_match_wins():
    s = _state(inventory=["flashlight"], trust=5)
    variants = {
        "trust>=3": "Trust line.",
        "has:flashlight": "Flashlight line.",
        "default": "Default.",
    }
    # trust>=3 is listed first and matches, so it wins
    assert dialogue.pick_dynamic(s, variants) == "Trust line."


def test_pick_dynamic_falls_back_to_default():
    s = _state(inventory=[], trust=0)
    variants = {
        "has:flashlight": "Should not appear",
        "trust>=99": "Should not appear",
        "default": "Default line",
    }
    assert dialogue.pick_dynamic(s, variants) == "Default line"


def test_pick_dynamic_fallback_arg():
    s = _state(inventory=[], trust=0)
    variants = {
        "has:flashlight": "Should not appear",
    }
    assert dialogue.pick_dynamic(s, variants, fallback="Fallback") == "Fallback"


def test_pick_dynamic_empty_variants():
    s = State()
    assert dialogue.pick_dynamic(s, {}, fallback="Empty") == "Empty"


def test_pick_dynamic_none_variants():
    s = State()
    assert dialogue.pick_dynamic(s, None, fallback="None") == "None"


def test_pick_dynamic_none_state():
    assert dialogue.pick_dynamic(None, {"has:x": "x", "default": "fb"}) == "fb"


# ---------------------------------------------------------------------------
# pick_first
# ---------------------------------------------------------------------------

def test_pick_first_selects_matching_line():
    s = _state(inventory=["flashlight"], trust=5)
    conditions = ["has:flashlight", "trust>=3", "default"]
    lines = ["Flashlight", "Trust", "Default"]
    assert dialogue.pick_first(s, conditions, lines) == "Flashlight"


def test_pick_first_fallback():
    s = _state(inventory=[], trust=0)
    conditions = ["has:flashlight", "trust>=99"]
    lines = ["Flashlight", "Trust"]
    assert dialogue.pick_first(s, conditions, lines, fallback="FB") == "FB"


# ---------------------------------------------------------------------------
# has_item / stat_at_least / decided helpers
# ---------------------------------------------------------------------------

def test_has_item_true():
    s = _state(inventory=["flashlight"])
    assert dialogue.has_item(s, "flashlight") is True


def test_has_item_false():
    s = _state(inventory=["flashlight"])
    assert dialogue.has_item(s, "nonexistent") is False


def test_stat_at_least_true():
    s = _state(trust=5)
    assert dialogue.stat_at_least(s, "trust", 3) is True


def test_stat_at_least_false():
    s = _state(trust=2)
    assert dialogue.stat_at_least(s, "trust", 3) is False


def test_decided_true():
    s = _state(decisions=["helped_mika"])
    assert dialogue.decided(s, "helped_mika") is True


def test_decided_false():
    s = _state(decisions=["helped_mika"])
    assert dialogue.decided(s, "abandoned_mika") is False


# ---------------------------------------------------------------------------
# Graceful degradation — missing attributes
# ---------------------------------------------------------------------------

def test_missing_inventory_graceful():
    s = State()
    s.inventory = None  # simulate missing inventory
    assert dialogue.has_item(s, "flashlight") is False
    assert dialogue.condition_matches(s, "has:flashlight") is False


def test_missing_decisions_graceful():
    s = State()
    # State has no .decisions attribute by default
    assert not hasattr(s, "decisions")
    assert dialogue.decided(s, "helped_mika") is False
    assert dialogue.condition_matches(s, "decided:helped_mika") is False


def test_pick_dynamic_missing_attrs_graceful():
    s = State()
    s.inventory = None
    variants = {
        "has:flashlight": "x",
        "trust>=99": "y",
        "decided:z": "w",
        "default": "safe",
    }
    assert dialogue.pick_dynamic(s, variants) == "safe"
