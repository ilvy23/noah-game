"""Tests for the `hint` command (noah.hint + main.show_hint).

Covers:
  * the command exists and is dispatchable via main.py
  * hint() returns a non-empty string for valid game states
  * hint logic is deterministic (same state → same hint)
  * tone: every hint carries at least one tsundere/warm keyword
  * spoiler safety: no ending names or plot-twist phrases in any state
"""
import pytest

from engine import State
import noah
import main
import story


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _state(**kw) -> State:
    """Build a State with the given overrides."""
    s = State()
    for k, v in kw.items():
        setattr(s, k, v)
    return s


# ---------------------------------------------------------------------------
# command existence
# ---------------------------------------------------------------------------

def test_hint_function_exists():
    assert hasattr(noah, "hint")
    assert callable(noah.hint)


def test_show_hint_function_exists():
    assert hasattr(main, "show_hint")
    assert callable(main.show_hint)


def test_hint_is_dispatched_in_game_loop():
    """The game_loop source must contain a branch for 'hint'."""
    import inspect
    src = inspect.getsource(main.game_loop)
    assert '"hint"' in src or "'hint'" in src


def test_hint_in_help_text():
    """The how-to-play screen must mention the hint command."""
    import inspect
    src = inspect.getsource(main._how_to_play)
    assert "hint" in src


# ---------------------------------------------------------------------------
# return type and non-emptiness
# ---------------------------------------------------------------------------

def test_hint_returns_string():
    s = _state()
    result = noah.hint(s)
    assert isinstance(result, str)


def test_hint_is_non_empty():
    s = _state()
    result = noah.hint(s)
    assert len(result.strip()) > 0


def test_hint_non_empty_low_sanity():
    s = _state(sanity=10)
    result = noah.hint(s)
    assert len(result.strip()) > 0


def test_hint_non_empty_ritual_ready():
    s = _state()
    s.inventory.append("key")
    s.inventory.append("ritual_text")
    s.flags["read_ledger"] = True
    result = noah.hint(s)
    assert len(result.strip()) > 0


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------

def test_hint_deterministic_fresh_state():
    s1 = _state()
    s2 = _state()
    assert noah.hint(s1) == noah.hint(s2)


def test_hint_deterministic_low_sanity():
    s1 = _state(sanity=10)
    s2 = _state(sanity=10)
    assert noah.hint(s1) == noah.hint(s2)


def test_hint_deterministic_ritual_ready():
    s1 = _state()
    s1.inventory.append("key")
    s1.inventory.append("ritual_text")
    s1.flags["read_ledger"] = True

    s2 = _state()
    s2.inventory.append("key")
    s2.inventory.append("ritual_text")
    s2.flags["read_ledger"] = True

    assert noah.hint(s1) == noah.hint(s2)


def test_hint_deterministic_chapter2():
    s1 = _state()
    s1.flags["ch1_done"] = True
    s2 = _state()
    s2.flags["ch1_done"] = True
    assert noah.hint(s1) == noah.hint(s2)


# ---------------------------------------------------------------------------
# tone: tsundere / warm keywords
# ---------------------------------------------------------------------------

# Every hint must contain at least one of these markers.
_TONE_MARKERS = ("tch", "listen", "idiot", "fine", "not like", "i was not", "that's not")


def _has_tone(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _TONE_MARKERS)


def test_tone_fresh_state():
    assert _has_tone(noah.hint(_state()))


def test_tone_low_sanity():
    assert _has_tone(noah.hint(_state(sanity=10)))


def test_tone_thin_sanity():
    assert _has_tone(noah.hint(_state(sanity=30)))


def test_tone_ritual_ready():
    s = _state()
    s.inventory.append("key")
    s.inventory.append("ritual_text")
    s.flags["read_ledger"] = True
    assert _has_tone(noah.hint(s))


def test_tone_chapter1_no_letter():
    s = _state()
    assert _has_tone(noah.hint(s))


def test_tone_chapter2():
    s = _state()
    s.flags["ch1_done"] = True
    assert _has_tone(noah.hint(s))


def test_tone_chapter3():
    s = _state()
    s.flags["ch1_done"] = True
    s.flags["ch2_done"] = True
    assert _has_tone(noah.hint(s))


def test_tone_chapter4():
    s = _state()
    s.flags["ch1_done"] = True
    s.flags["ch2_done"] = True
    s.flags["ch3_done"] = True
    assert _has_tone(noah.hint(s))


def test_tone_day6():
    s = _state(day=6)
    assert _has_tone(noah.hint(s))


# ---------------------------------------------------------------------------
# spoiler safety: no ending names or plot-twist phrases
# ---------------------------------------------------------------------------

# Phrases that would spoil an ending or a major plot twist.
_SPOILER_PHRASES = (
    "quiet ending",
    "broken ending",
    "second ending",
    "paid ending",
    "the ending is",
    "the last name",
    "the blank space",
    "the ledger has your name",
    "you will die",
    "you will be taken",
    "the valley will take you",
    "the fire is yours to light",
    "the blank space is not a blank space",
)


def _no_spoilers(text: str) -> bool:
    low = text.lower()
    return not any(p in low for p in _SPOILER_PHRASES)


def test_no_spoilers_fresh_state():
    assert _no_spoilers(noah.hint(_state()))


def test_no_spoilers_low_sanity():
    assert _no_spoilers(noah.hint(_state(sanity=10)))


def test_no_spoilers_thin_sanity():
    assert _no_spoilers(noah.hint(_state(sanity=30)))


def test_no_spoilers_ritual_ready():
    s = _state()
    s.inventory.append("key")
    s.inventory.append("ritual_text")
    s.flags["read_ledger"] = True
    assert _no_spoilers(noah.hint(s))


def test_no_spoilers_chapter1():
    assert _no_spoilers(noah.hint(_state()))


def test_no_spoilers_chapter2():
    s = _state()
    s.flags["ch1_done"] = True
    assert _no_spoilers(noah.hint(s))


def test_no_spoilers_chapter3():
    s = _state()
    s.flags["ch1_done"] = True
    s.flags["ch2_done"] = True
    assert _no_spoilers(noah.hint(s))


def test_no_spoilers_chapter4():
    s = _state()
    s.flags["ch1_done"] = True
    s.flags["ch2_done"] = True
    s.flags["ch3_done"] = True
    assert _no_spoilers(noah.hint(s))


def test_no_spoilers_chapter4_cost_asked():
    s = _state()
    s.flags["ch1_done"] = True
    s.flags["ch2_done"] = True
    s.flags["ch3_done"] = True
    s.flags["asked_archivist_cost"] = True
    assert _no_spoilers(noah.hint(s))


def test_no_spoilers_day6():
    assert _no_spoilers(noah.hint(_state(day=6)))


def test_no_spoilers_noah_ally_path():
    """Even with noah_ally set, the hint must not name an ending."""
    s = _state()
    s.flags["noah_ally"] = True
    s.flags["read_ledger"] = True
    assert _no_spoilers(noah.hint(s))


# ---------------------------------------------------------------------------
# state-dependent branching (sanity check that different states give
# different hints where expected)
# ---------------------------------------------------------------------------

def test_low_sanity_hint_mentions_clearing():
    """When sanity is critical, Noah should point at the clearing."""
    text = noah.hint(_state(sanity=10)).lower()
    assert "clearing" in text


def test_ritual_ready_hint_mentions_hill():
    """When the ritual is ready, Noah should point at the hill."""
    s = _state()
    s.inventory.append("key")
    s.inventory.append("ritual_text")
    s.flags["read_ledger"] = True
    text = noah.hint(s).lower()
    assert "hill" in text


def test_chapter1_hint_mentions_letter_or_talk():
    """Chapter 1 hint should mention the letter or talking to someone."""
    text = noah.hint(_state()).lower()
    assert "letter" in text or "talk" in text
