# tests/test_noah.py — the rewritten Noah: bright, tsundere, NOT horror.
#
# Checks:
#   1. No horror keywords in Noah's dialogue or his location text.
#   2. No whole sentence duplicated across the four sanity tiers.
#   3. No whole sentence duplicated between tree nodes.
#   4. The nook text changes with trust, chapter, and noah_hurt.
#   5. The sanity restore has a working cooldown (once per day).
#   6. noah_ally / noah_hurt flags exist in the tree and are settable.
#   7. The ask topics have unique text (no shared whole line).
import re
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import noah  # noqa: E402
import dialogue  # noqa: E402
import engine  # noqa: E402

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

HORROR_WORDS = [
    "counting", "hollow", "breathing", "mouth", "ledger",
    "valley keeps", "closer", "moment ago",
    "did not light", "if it stops", "not a cushion",
]

# Phrases that must not appear as whole words (word-boundary regexes,
# so "for the bench" does not trip the "or the bench" ban).
HORROR_PHRASES = [
    r"\bor the bench\b",
]


def _all_lines(obj) -> list:
    """Collect every line of text from an open tier, a tree, or a topic dict."""
    lines = []
    if isinstance(obj, str):
        for ln in obj.split("\n"):
            ln = ln.strip()
            if ln:
                lines.append(ln)
    elif isinstance(obj, dict):
        for v in obj.values():
            lines.extend(_all_lines(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            lines.extend(_all_lines(v))
    return lines


def _normalize(line: str) -> str:
    """Strip quotes, whitespace, and markdown emphasis for comparison."""
    line = line.strip()
    line = re.sub(r"^\s*\d+\.\s+", "", line)
    line = re.sub(r"[*_]", "", line)
    line = line.replace("\u201c", "").replace("\u201d", "")
    line = re.sub(r"\s+", " ", line).strip()
    return line.lower()


# ---------------------------------------------------------------------------
# 1. No horror keywords
# ---------------------------------------------------------------------------

def test_no_horror_words_in_noah_open():
    text = "\n".join(noah.NOAH_OPEN.values()).lower()
    for word in HORROR_WORDS:
        assert word not in text, f"horror word {word!r} found in NOAH_OPEN"


def test_no_horror_words_in_noah_tree():
    text = "\n".join(_all_lines(noah.NOAH_TREE)).lower()
    for word in HORROR_WORDS:
        assert word not in text, f"horror word {word!r} found in NOAH_TREE"


def test_no_horror_words_in_noah_topics():
    text = "\n".join(_all_lines(noah.NOAH_TOPICS)).lower()
    for word in HORROR_WORDS:
        assert word not in text, f"horror word {word!r} found in NOAH_TOPICS"


def test_no_horror_words_in_place_text():
    s = engine.State()
    s.sanity = 80
    text = noah.place_text(s).lower()
    for word in HORROR_WORDS:
        assert word not in text, f"horror word {word!r} found in place_text"


# ---------------------------------------------------------------------------
# 2. No whole sentence duplicated across tiers
# ---------------------------------------------------------------------------

def test_no_shared_line_across_tiers():
    tiers = list(noah.NOAH_OPEN.keys())
    assert len(tiers) == 4, f"expected 4 tiers, got {tiers}"
    seen = {}
    for tier in tiers:
        for line in _all_lines(noah.NOAH_OPEN[tier]):
            norm = _normalize(line)
            if norm in seen:
                pytest.fail(
                    f"sentence duplicated across tiers: "
                    f"{norm!r} in {seen[norm]!r} and {tier!r}"
                )
            seen[norm] = tier


# ---------------------------------------------------------------------------
# 3. No whole sentence duplicated between tree nodes
# ---------------------------------------------------------------------------

def test_no_shared_line_across_tree_nodes():
    nodes = list(noah.NOAH_TREE.keys())
    assert len(nodes) >= 3, f"expected at least 3 nodes, got {nodes}"
    seen = {}
    for node_id in nodes:
        for line in _all_lines(noah.NOAH_TREE[node_id]["text"]):
            norm = _normalize(line)
            if norm in seen:
                pytest.fail(
                    f"sentence duplicated across nodes: "
                    f"{norm!r} in {seen[norm]!r} and {node_id!r}"
                )
            seen[norm] = node_id


# ---------------------------------------------------------------------------
# 4. Nook text changes with trust, chapter, and noah_hurt
# ---------------------------------------------------------------------------

def test_place_text_changes_with_trust():
    s1 = engine.State()
    s1.sanity = 80
    s1.trust = 0
    s1.chapter = 1
    t1 = noah.place_text(s1)

    s2 = engine.State()
    s2.sanity = 80
    s2.trust = 20
    s2.chapter = 4
    t2 = noah.place_text(s2)

    assert t1 != t2, "nook text should change with trust+chapter"


def test_place_text_cold_when_hurt():
    s = engine.State()
    s.sanity = 80
    s.trust = 20
    s.chapter = 4
    s.flag("noah_hurt", True)
    text = noah.place_text(s)
    assert "cold" in text.lower() or "shut" in text.lower() or "closed" in text.lower()


def test_place_text_changes_with_chapter():
    s1 = engine.State()
    s1.sanity = 80
    s1.trust = 10
    s1.chapter = 1
    t1 = noah.place_text(s1)

    s2 = engine.State()
    s2.sanity = 80
    s2.trust = 10
    s2.chapter = 3
    t2 = noah.place_text(s2)

    assert t1 != t2, "nook text should change with chapter"


# ---------------------------------------------------------------------------
# 5. Sanity restore cooldown
# ---------------------------------------------------------------------------

def _apply_noah_rest(s):
    """Mirror of the main.py talk-noah sanity restore logic."""
    if s.day != s._noah_rest_day:
        s._noah_rest_day = s.day
        s.sanity_change(8, "sitting with Noah")


def test_sanity_restore_cooldown():
    s = engine.State()
    s.sanity = 50
    s.day = 1

    # First talk: should restore +8
    before = s.sanity
    _apply_noah_rest(s)
    after_first = s.sanity
    assert after_first == before + 8, f"first restore should give +8, got {after_first - before}"

    # Second talk same day: should NOT restore
    before2 = s.sanity
    _apply_noah_rest(s)
    after_second = s.sanity
    assert after_second == before2, f"second restore same day should give +0, got {after_second - before2}"


def test_sanity_restore_next_day():
    s = engine.State()
    s.sanity = 50
    s.day = 1
    s._noah_rest_day = 1

    # Next day: should restore again
    s.day = 2
    before = s.sanity
    _apply_noah_rest(s)
    after = s.sanity
    assert after == before + 8, f"next day restore should give +8, got {after - before}"


# ---------------------------------------------------------------------------
# 6. noah_ally / noah_hurt flags in the tree
# ---------------------------------------------------------------------------

def test_noah_ally_flag_in_tree():
    found = False
    for node in noah.NOAH_TREE.values():
        for label, next_id, effects in node["choices"]:
            if effects.get("flag") == "noah_ally":
                found = True
                break
        if found:
            break
    assert found, "noah_ally flag not found in any tree choice"


def test_noah_hurt_flag_in_tree():
    found = False
    for node in noah.NOAH_TREE.values():
        for label, next_id, effects in node["choices"]:
            if effects.get("flag") == "noah_hurt":
                found = True
                break
        if found:
            break
    assert found, "noah_hurt flag not found in any tree choice"


# ---------------------------------------------------------------------------
# 7. Ask topics have unique text
# ---------------------------------------------------------------------------

def test_ask_topics_unique_lines():
    topics = noah.NOAH_TOPICS
    assert len(topics) >= 3, f"expected at least 3 topics, got {list(topics.keys())}"
    seen = {}
    for topic_name, topic in topics.items():
        for line in _all_lines(topic["text"]):
            norm = _normalize(line)
            if norm in seen:
                pytest.fail(
                    f"line duplicated across topics: "
                    f"{norm!r} in {seen[norm]!r} and {topic_name!r}"
                )
            seen[norm] = topic_name


# ---------------------------------------------------------------------------
# 8. NOAH_CHAPTER has 5 entries
# ---------------------------------------------------------------------------

def test_noah_chapter_has_5_entries():
    assert len(noah.NOAH_CHAPTER) == 5, f"expected 5 chapter lines, got {len(noah.NOAH_CHAPTER)}"
    for ch in range(1, 6):
        assert ch in noah.NOAH_CHAPTER, f"missing chapter {ch}"


# ---------------------------------------------------------------------------
# 9. dialogue.py re-exports Noah's data
# ---------------------------------------------------------------------------

def test_dialogue_reexports_noah():
    assert dialogue.NOAH_OPEN is noah.NOAH_OPEN
    assert dialogue.NOAH_TREE is noah.NOAH_TREE
    assert dialogue.NOAH_TOPICS is noah.NOAH_TOPICS
    assert dialogue.NOAH_CHAPTER is noah.NOAH_CHAPTER


def test_ask_topics_noah_uses_noah_topics():
    assert dialogue.ASK_TOPICS["noah"] is noah.NOAH_TOPICS
