# tests/test_summary.py — end-of-run summary screen

import io
import sys
from contextlib import redirect_stdout

import pytest

import engine
from engine import State
import achievements
import main
import deaths


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _capture(fn, *args, **kwargs):
    """Run fn and return everything it printed."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*args, **kwargs)
    return buf.getvalue()


def _make_state(day=3, visited=("lunuen", "nook", "forest"), ach=("first_talk", "found_item")):
    s = State()
    s.day = day
    s.visited = list(visited)
    s.achievements = list(ach)
    return s


# ---------------------------------------------------------------------------
# show_summary exists and displays the four required fields
# ---------------------------------------------------------------------------

def test_show_summary_function_exists():
    assert hasattr(main, "show_summary")
    assert callable(main.show_summary)


def test_summary_displays_days_survived():
    s = _make_state(day=5)
    out = _capture(main.show_summary, s)
    assert "days survived" in out.lower()
    assert "5" in out


def test_summary_displays_places_visited():
    s = _make_state(visited=("lunuen", "nook", "forest"))
    out = _capture(main.show_summary, s)
    assert "places visited" in out.lower()
    assert "3" in out
    assert "lunuen" in out
    assert "nook" in out
    assert "forest" in out


def test_summary_displays_achievements_unlocked():
    s = _make_state(ach=("first_talk", "found_item"))
    out = _capture(main.show_summary, s)
    assert "achievements unlocked" in out.lower()
    # should show the count
    assert "2" in out


def test_summary_displays_current_level():
    s = _make_state(ach=("first_talk", "found_item"))
    out = _capture(main.show_summary, s)
    assert "level" in out.lower()
    # level = 1 + unlocked // 2 = 1 + 1 = 2
    assert "2" in out


def test_summary_shows_correct_level_formula():
    # 4 achievements -> level = 1 + 4//2 = 3
    s = _make_state(ach=("a", "b", "c", "d"))
    out = _capture(main.show_summary, s)
    assert "3" in out


def test_summary_fresh_state():
    s = State()
    out = _capture(main.show_summary, s)
    assert "days survived" in out.lower()
    assert "places visited" in out.lower()
    assert "achievements unlocked" in out.lower()
    assert "level" in out.lower()


# ---------------------------------------------------------------------------
# summary is triggered on death
# ---------------------------------------------------------------------------

def test_death_screen_calls_show_summary():
    """death_screen should call main.show_summary before the choice loop."""
    s = State()
    s.sanity = 0  # triggers "collapse" death
    s.day = 4
    s.visited = ["lunuen", "nook"]
    s.achievements = ["first_talk"]

    # death_screen enters a while-True loop; feed it "quit" via stdin
    import builtins
    orig_input = builtins.input
    builtins.input = lambda prompt="": ("quit" if prompt else "")
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = deaths.death_screen(s, "collapse")
        out = buf.getvalue()
    finally:
        builtins.input = orig_input

    assert result is None  # quit returns None
    assert "days survived" in out.lower()
    assert "places visited" in out.lower()
    assert "achievements unlocked" in out.lower()
    assert "level" in out.lower()


# ---------------------------------------------------------------------------
# summary is triggered on ending
# ---------------------------------------------------------------------------

def test_ending_path_calls_show_summary():
    """The ending branch in game_loop calls show_summary before break."""
    # We verify by checking that show_summary is called in the code path.
    # Simulate: set up state with an ending flag and verify the function exists
    # and is wired in (we can't easily run the full game_loop, so we check
    # the source contains the call).
    import inspect
    src = inspect.getsource(main.game_loop)
    assert "show_summary" in src


# ---------------------------------------------------------------------------
# EOF behavior is preserved
# ---------------------------------------------------------------------------

def test_deaths_ask_returns_quit_on_eof():
    """deaths._ask must return 'quit' on EOFError."""
    import builtins
    orig_input = builtins.input

    def _eof_input(prompt=""):
        raise EOFError

    builtins.input = _eof_input
    try:
        result = deaths._ask("> ")
    finally:
        builtins.input = orig_input

    assert result == "quit"


def test_pause_returns_nothing_on_eof():
    """main.pause must not raise and must return None on EOFError."""
    import builtins
    orig_input = builtins.input

    def _eof_input(prompt=""):
        raise EOFError

    builtins.input = _eof_input
    try:
        result = main.pause()
    finally:
        builtins.input = orig_input

    assert result is None


def test_ask_returns_quit_on_eof():
    """main.ask must return 'quit' on EOFError."""
    import builtins
    orig_input = builtins.input

    def _eof_input(prompt=""):
        raise EOFError

    builtins.input = _eof_input
    try:
        result = main.ask("> ")
    finally:
        builtins.input = orig_input

    assert result == "quit"


# ---------------------------------------------------------------------------
# summary does not interfere with death_screen's return value
# ---------------------------------------------------------------------------

def test_death_screen_load_choice_still_works():
    """After summary, the load/new/quit choices still work."""
    import builtins
    orig_input = builtins.input

    # Feed: "quit" to exit
    builtins.input = lambda prompt="": "quit"
    s = State()
    s.sanity = 0
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = deaths.death_screen(s, "collapse")
    finally:
        builtins.input = orig_input

    assert result is None


def test_death_screen_new_choice_still_works():
    """Choosing 'new' after the summary returns a fresh State."""
    import builtins
    orig_input = builtins.input

    builtins.input = lambda prompt="": "new"
    s = State()
    s.sanity = 0
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = deaths.death_screen(s, "collapse")
    finally:
        builtins.input = orig_input

    assert result is not None
    assert isinstance(result, State)
    assert result.sanity == 80  # fresh state
