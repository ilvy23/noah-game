# tests/test_dialogue_flag_logic.py — the dialogue trees and ask-topics set the
# right flags and shift the right values, and the death check reacts to them.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine
from engine import State
import dialogue
import deaths


class FakeStdout:
    """Capture render() output without printing it."""
    def __init__(self):
        self.lines = []
    def write(self, s):
        self.lines.append(s)
    def flush(self):
        pass


def _quiet_state(sanity=80):
    s = State()
    s.sanity = sanity
    return s


def _run_tree(s, who, tree, open_text, choices):
    """Drive run_tree with scripted choices (list of ints, one per node)."""
    import builtins
    inputs = iter([str(c) for c in choices])
    real_input = builtins.input
    builtins.input = lambda prompt="": next(inputs)
    try:
        dialogue.run_tree(s, who, tree, open_text)
    finally:
        builtins.input = real_input


# ---------------------------------------------------------------------------
# Connor tree
# ---------------------------------------------------------------------------

def test_connor_tree_sets_flags():
    s = _quiet_state()
    # n1: choice 1 (yes, I've seen it) -> n2
    # n2: choice 1 (read it) -> n3
    # n3: choice 1 (tell me) -> None
    _run_tree(s, "connor", dialogue.CONNOR_TREE, "open", [1, 1, 1])
    assert s.has("connor_lake_yes")
    assert s.has("connor_notebook_read")
    assert s.has("connor_told")
    assert s.trust > 0  # trust went up
    assert s.sanity < 80  # sanity went down


def test_connor_tree_leaves_early():
    s = _quiet_state()
    # n1: choice 0 (leave) -> end
    _run_tree(s, "connor", dialogue.CONNOR_TREE, "open", [0])
    assert not s.has("connor_lake_yes")
    assert not s.has("connor_notebook_read")
    assert not s.has("connor_told")


def test_connor_tree_invalid_choice_stays():
    s = _quiet_state()
    # n1: choice 99 (invalid) -> stays at n1
    # n1: choice 1 (yes) -> n2
    # n2: choice 0 (leave) -> end
    _run_tree(s, "connor", dialogue.CONNOR_TREE, "open", [99, 1, 0])
    assert s.has("connor_lake_yes")
    assert not s.has("connor_notebook_read")


# ---------------------------------------------------------------------------
# Mika tree
# ---------------------------------------------------------------------------

def test_mika_tree_sets_flags():
    s = _quiet_state()
    # n1: choice 1 (twelve) -> n2
    # n2: choice 1 (what is it?) -> n3
    # n3: choice 2 (I can't) -> None
    _run_tree(s, "mika", dialogue.MIKA_TREE, "open", [1, 1, 2])
    assert s.has("mika_counted_twelve")
    assert s.has("mika_what")
    assert s.has("mika_cant")
    assert s.sanity < 80  # sanity went down


def test_mika_tree_cant_triggers_death():
    s = _quiet_state()
    # n1: choice 1 (twelve) -> n2
    # n2: choice 1 (what is it?) -> n3
    # n3: choice 2 (I can't) -> None
    _run_tree(s, "mika", dialogue.MIKA_TREE, "open", [1, 1, 2])
    assert s.has("mika_cant")
    death_id = deaths.check_death(s)
    assert death_id == "counting"


# ---------------------------------------------------------------------------
# Archivist tree
# ---------------------------------------------------------------------------

def test_archivist_tree_sets_flags():
    s = _quiet_state()
    # n1: choice 1 (what do the records say about me?) -> n2
    # n2: choice 1 (can I change it?) -> n3
    # n3: choice 3 (what is the cost?) -> None
    _run_tree(s, "archivist", dialogue.ARCHIVIST_TREE, "open", [1, 1, 3])
    assert s.has("archivist_records_asked")
    assert s.has("archivist_change_asked")
    assert s.has("archivist_cost_asked")


def test_archivist_tree_paid_triggers_death_outside_schloss():
    s = _quiet_state()
    s.location = "lunuen"  # not schloss
    # n1: choice 1 -> n2
    # n2: choice 1 -> n3
    # n3: choice 1 (I'll pay) -> None
    _run_tree(s, "archivist", dialogue.ARCHIVIST_TREE, "open", [1, 1, 1])
    assert s.has("archivist_paid")
    death_id = deaths.check_death(s)
    assert death_id == "paid"


# ---------------------------------------------------------------------------
# Ask topics
# ---------------------------------------------------------------------------

def test_ask_topic_sets_flag():
    s = _quiet_state()
    ok = dialogue.ask_topic(s, "mika", "valley")
    assert ok is True
    assert s.has("asked_mika_valley")


def test_ask_topic_unknown_returns_false():
    s = _quiet_state()
    ok = dialogue.ask_topic(s, "mika", "nonexistent_topic")
    assert ok is False


def test_ask_topic_archivist_cost():
    s = _quiet_state()
    ok = dialogue.ask_topic(s, "archivist", "cost")
    assert ok is True
    assert s.has("asked_archivist_cost")


# ---------------------------------------------------------------------------
# Death check order
# ---------------------------------------------------------------------------

def test_death_check_sanity_collapse_first():
    s = _quiet_state(sanity=0)
    s.flag("mika_cant")
    death_id = deaths.check_death(s)
    assert death_id == "collapse"  # sanity 0 wins over mika_cant


def test_death_check_ledger_before_counting():
    s = _quiet_state()
    s.flag("read_ledger_twice")
    s.flag("mika_cant")
    death_id = deaths.check_death(s)
    assert death_id == "ledger"  # ledger wins over counting


def test_death_check_forest_requires_low_sanity():
    s = _quiet_state(sanity=80)
    s.location = "forest"
    death_id = deaths.check_death(s)
    assert death_id is None  # sanity too high

    s.sanity = 20
    death_id = deaths.check_death(s)
    assert death_id == "forest"


def test_death_check_lake_requires_low_sanity():
    s = _quiet_state(sanity=80)
    s.location = "lake"
    death_id = deaths.check_death(s)
    assert death_id is None  # sanity too high

    s.sanity = 20
    death_id = deaths.check_death(s)
    assert death_id == "lake"


def test_death_check_paid_only_outside_schloss():
    s = _quiet_state()
    s.flag("archivist_paid")
    s.location = "schloss"
    death_id = deaths.check_death(s)
    assert death_id is None  # in schloss, no death

    s.location = "lunuen"
    death_id = deaths.check_death(s)
    assert death_id == "paid"


def test_death_check_no_death_when_healthy():
    s = _quiet_state()
    s.location = "lunuen"
    death_id = deaths.check_death(s)
    assert death_id is None


# ---------------------------------------------------------------------------
# Dynamic dialogue selection: inventory
# ---------------------------------------------------------------------------

def test_condition_matches_has_item():
    s = _quiet_state()
    s.inventory = ["flashlight", "notebook"]
    assert dialogue.condition_matches(s, "has:flashlight") is True
    assert dialogue.condition_matches(s, "has:notebook") is True
    assert dialogue.condition_matches(s, "has:missing_item") is False


def test_condition_matches_has_any():
    s = _quiet_state()
    s.inventory = ["flashlight"]
    assert dialogue.condition_matches(s, "has_any:flashlight,notebook") is True
    assert dialogue.condition_matches(s, "has_any:notebook,ledger") is False


def test_condition_matches_has_empty_inventory():
    s = _quiet_state()
    s.inventory = []
    assert dialogue.condition_matches(s, "has:flashlight") is False


def test_pick_dynamic_inventory_variant():
    s = _quiet_state()
    s.inventory = ["flashlight"]
    variants = {
        "has:flashlight": "You have the flashlight.",
        "default": "You have nothing.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You have the flashlight."


def test_pick_dynamic_inventory_fallback():
    s = _quiet_state()
    s.inventory = []
    variants = {
        "has:flashlight": "You have the flashlight.",
        "default": "You have nothing.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You have nothing."


# ---------------------------------------------------------------------------
# Dynamic dialogue selection: stats (trust / fear)
# ---------------------------------------------------------------------------

def test_condition_matches_trust_gte():
    s = _quiet_state()
    s.trust = 25
    assert dialogue.condition_matches(s, "trust>=20") is True
    assert dialogue.condition_matches(s, "trust>=30") is False


def test_condition_matches_trust_eq():
    s = _quiet_state()
    s.trust = 15
    assert dialogue.condition_matches(s, "trust==15") is True
    assert dialogue.condition_matches(s, "trust==20") is False


def test_condition_matches_fear_lte():
    s = _quiet_state()
    s.fear = 10
    assert dialogue.condition_matches(s, "fear<=15") is True
    assert dialogue.condition_matches(s, "fear<=5") is False


def test_condition_matches_fear_gt():
    s = _quiet_state()
    s.fear = 40
    assert dialogue.condition_matches(s, "fear>30") is True
    assert dialogue.condition_matches(s, "fear>50") is False


def test_pick_dynamic_trust_variant():
    s = _quiet_state()
    s.trust = 30
    variants = {
        "trust>=20": "You seem to trust me.",
        "default": "You are wary of me.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You seem to trust me."


def test_pick_dynamic_fear_variant():
    s = _quiet_state()
    s.fear = 50
    variants = {
        "fear>=40": "You look frightened.",
        "default": "You look calm.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You look frightened."


# ---------------------------------------------------------------------------
# Dynamic dialogue selection: decision history
# ---------------------------------------------------------------------------

def test_condition_matches_decided():
    s = _quiet_state()
    s.decisions = ["helped_mika", "refused_connor"]
    assert dialogue.condition_matches(s, "decided:helped_mika") is True
    assert dialogue.condition_matches(s, "decided:refused_connor") is True
    assert dialogue.condition_matches(s, "decided:unknown_decision") is False


def test_condition_matches_not_decided():
    s = _quiet_state()
    s.decisions = ["helped_mika"]
    assert dialogue.condition_matches(s, "not_decided:refused_connor") is True
    assert dialogue.condition_matches(s, "not_decided:helped_mika") is False


def test_pick_dynamic_decision_variant():
    s = _quiet_state()
    s.decisions = ["helped_mika"]
    variants = {
        "decided:helped_mika": "You helped Mika before.",
        "default": "You haven't helped anyone yet.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You helped Mika before."


def test_pick_dynamic_not_decided_variant():
    s = _quiet_state()
    s.decisions = []
    variants = {
        "not_decided:helped_mika": "You haven't helped anyone yet.",
        "default": "You have helped someone.",
    }
    assert dialogue.pick_dynamic(s, variants) == "You haven't helped anyone yet."


# ---------------------------------------------------------------------------
# Relationship state updates
# ---------------------------------------------------------------------------

def test_relationship_state_friendly():
    from characters import relationship_state
    assert relationship_state(20) == "friendly"
    assert relationship_state(50) == "friendly"
    assert relationship_state(100) == "friendly"


def test_relationship_state_hostile():
    from characters import relationship_state
    assert relationship_state(-20) == "hostile"
    assert relationship_state(-50) == "hostile"
    assert relationship_state(-100) == "hostile"


def test_relationship_state_neutral():
    from characters import relationship_state
    assert relationship_state(0) == "neutral"
    assert relationship_state(19) == "neutral"
    assert relationship_state(-19) == "neutral"


def test_update_relationship_increases_trust():
    from characters import update_relationship, get_relationship
    s = _quiet_state()
    state = update_relationship(s, "connor", trust_delta=25)
    assert state == "friendly"
    rel = get_relationship(s, "connor")
    assert rel["trust"] == 25
    assert rel["state"] == "friendly"


def test_update_relationship_decreases_trust():
    from characters import update_relationship, get_relationship
    s = _quiet_state()
    state = update_relationship(s, "connor", trust_delta=-30)
    assert state == "hostile"
    rel = get_relationship(s, "connor")
    assert rel["trust"] == -30
    assert rel["state"] == "hostile"


def test_update_relationship_clamps_trust():
    from characters import update_relationship, get_relationship
    s = _quiet_state()
    update_relationship(s, "connor", trust_delta=150)
    rel = get_relationship(s, "connor")
    assert rel["trust"] == 100  # clamped to max

    s2 = _quiet_state()
    update_relationship(s2, "connor", trust_delta=-150)
    rel2 = get_relationship(s2, "connor")
    assert rel2["trust"] == -100  # clamped to min


def test_update_relationship_familiarity():
    from characters import update_relationship, get_relationship
    s = _quiet_state()
    update_relationship(s, "mika", trust_delta=5, familiarity_delta=10)
    rel = get_relationship(s, "mika")
    assert rel["familiarity"] == 10


def test_record_decision_stores_decision():
    from characters import record_decision, get_relationship
    s = _quiet_state()
    record_decision(s, "mika", "helped_mika")
    rel = get_relationship(s, "mika")
    assert "helped_mika" in rel["decisions"]


def test_record_decision_no_duplicates():
    from characters import record_decision, get_relationship
    s = _quiet_state()
    record_decision(s, "mika", "helped_mika")
    record_decision(s, "mika", "helped_mika")
    rel = get_relationship(s, "mika")
    assert rel["decisions"].count("helped_mika") == 1


# ---------------------------------------------------------------------------
# Dialogue lines change when player conditions are met
# ---------------------------------------------------------------------------

def test_dialogue_line_changes_with_inventory():
    s1 = _quiet_state()
    s1.inventory = ["flashlight"]
    s2 = _quiet_state()
    s2.inventory = []

    variants = {
        "has:flashlight": "You carry the flashlight.",
        "default": "Your hands are empty.",
    }
    line1 = dialogue.pick_dynamic(s1, variants)
    line2 = dialogue.pick_dynamic(s2, variants)
    assert line1 != line2
    assert "flashlight" in line1
    assert "empty" in line2


def test_dialogue_line_changes_with_trust():
    s1 = _quiet_state()
    s1.trust = 30
    s2 = _quiet_state()
    s2.trust = 0

    variants = {
        "trust>=20": "You trust me now.",
        "default": "You are still cautious.",
    }
    line1 = dialogue.pick_dynamic(s1, variants)
    line2 = dialogue.pick_dynamic(s2, variants)
    assert line1 != line2
    assert "trust" in line1
    assert "cautious" in line2


def test_dialogue_line_changes_with_fear():
    s1 = _quiet_state()
    s1.fear = 60
    s2 = _quiet_state()
    s2.fear = 5

    variants = {
        "fear>=40": "Fear is eating you.",
        "default": "You feel steady.",
    }
    line1 = dialogue.pick_dynamic(s1, variants)
    line2 = dialogue.pick_dynamic(s2, variants)
    assert line1 != line2
    assert "fear" in line1.lower()
    assert "steady" in line2


def test_dialogue_line_changes_with_decision():
    s1 = _quiet_state()
    s1.decisions = ["helped_mika"]
    s2 = _quiet_state()
    s2.decisions = []

    variants = {
        "decided:helped_mika": "Mika remembers what you did.",
        "default": "Mika doesn't know you well.",
    }
    line1 = dialogue.pick_dynamic(s1, variants)
    line2 = dialogue.pick_dynamic(s2, variants)
    assert line1 != line2
    assert "remembers" in line1
    assert "doesn't know" in line2


def test_pick_dynamic_first_match_wins():
    s = _quiet_state()
    s.inventory = ["flashlight", "notebook"]
    s.trust = 30
    variants = {
        "has:flashlight": "First match.",
        "trust>=20": "Second match.",
        "default": "Fallback.",
    }
    assert dialogue.pick_dynamic(s, variants) == "First match."


def test_pick_dynamic_no_match_returns_fallback():
    s = _quiet_state()
    s.inventory = []
    s.trust = 0
    variants = {
        "has:flashlight": "Has flashlight.",
        "trust>=20": "High trust.",
    }
    assert dialogue.pick_dynamic(s, variants, "Fallback line.") == "Fallback line."


def test_pick_dynamic_empty_variants():
    s = _quiet_state()
    assert dialogue.pick_dynamic(s, {}, "Fallback.") == "Fallback."
    assert dialogue.pick_dynamic(s, None, "Fallback.") == "Fallback."
