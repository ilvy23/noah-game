# -*- coding: utf-8 -*-
"""Achievement system tests.

Covers:
  - at least 12 achievements, each with a name and a one-line condition
  - level formula: level = 1 + unlocked // 2
  - the `achievements` command lists both unlocked and locked achievements
  - the unlock line appears exactly once per achievement (idempotency)
  - save round-trip preserves the achievements list
  - migration from a v1 save (no `achievements` key) loads cleanly
"""

import io
import json
import os
import sys
from contextlib import redirect_stdout

import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import achievements  # noqa: E402
import engine         # noqa: E402
from engine import State, save_game, load_game  # noqa: E402

REAL_SAVE = os.path.join(PROJECT_DIR, "tests", "fixtures", "save_v1.json")


# ---------------------------------------------------------------------------
# Achievement definitions
# ---------------------------------------------------------------------------

def test_at_least_12_achievements():
    assert len(achievements.ACHIEVEMENTS) >= 12, (
        f"expected at least 12 achievements, got {len(achievements.ACHIEVEMENTS)}"
    )


def test_every_achievement_has_name_and_condition():
    for a in achievements.ACHIEVEMENTS:
        assert "name" in a and a["name"], f"achievement {a.get('id')!r} missing name"
        assert "condition" in a and a["condition"], (
            f"achievement {a.get('id')!r} missing condition"
        )
        # condition must be a single line (no embedded newlines)
        assert "\n" not in a["condition"], (
            f"achievement {a['id']!r} condition spans multiple lines"
        )


def test_achievement_ids_are_unique():
    ids = [a["id"] for a in achievements.ACHIEVEMENTS]
    assert len(ids) == len(set(ids)), "duplicate achievement ids found"


def test_achievement_ids_helper():
    expected = [a["id"] for a in achievements.ACHIEVEMENTS]
    assert achievements.achievement_ids() == expected


def test_get_achievement_returns_dict():
    first = achievements.ACHIEVEMENTS[0]
    got = achievements.get_achievement(first["id"])
    assert got is not None
    assert got["id"] == first["id"]
    assert got["name"] == first["name"]


def test_get_achievement_unknown_returns_none():
    assert achievements.get_achievement("nonexistent_id") is None


# ---------------------------------------------------------------------------
# Level formula
# ---------------------------------------------------------------------------

def test_level_with_zero_unlocked():
    s = State()
    s.flags["achievements"] = []
    assert achievements.level(s) == 1


def test_level_with_one_unlocked():
    s = State()
    s.flags["achievements"] = ["first_steps"]
    assert achievements.level(s) == 1  # 1 + 1//2 = 1


def test_level_with_two_unlocked():
    s = State()
    s.flags["achievements"] = ["first_steps", "met_noah"]
    assert achievements.level(s) == 2  # 1 + 2//2 = 2


def test_level_with_three_unlocked():
    s = State()
    s.flags["achievements"] = ["first_steps", "met_noah", "met_connor"]
    assert achievements.level(s) == 2  # 1 + 3//2 = 2


def test_level_with_four_unlocked():
    s = State()
    s.flags["achievements"] = ["first_steps", "met_noah", "met_connor", "met_mika"]
    assert achievements.level(s) == 3  # 1 + 4//2 = 3


def test_level_with_all_unlocked():
    s = State()
    s.flags["achievements"] = [a["id"] for a in achievements.ACHIEVEMENTS]
    n = len(achievements.ACHIEVEMENTS)
    assert achievements.level(s) == 1 + n // 2


def test_unlocked_count():
    s = State()
    s.flags["achievements"] = ["first_steps", "met_noah"]
    assert achievements.unlocked_count(s) == 2


# ---------------------------------------------------------------------------
# check_all: unlock line appears exactly once per achievement
# ---------------------------------------------------------------------------

def _make_state_with_achievements(ids):
    s = State()
    s.flags["achievements"] = list(ids)
    return s


def test_check_all_unlocks_new_achievements():
    s = State()
    s.visited = ["lunuen", "nook", "forest"]  # earns first_steps
    buf = io.StringIO()
    with redirect_stdout(buf):
        newly = achievements.check_all(s)
    assert "first_steps" in newly
    assert "first_steps" in s.flags["achievements"]


def test_check_all_idempotent_no_duplicate_unlocks():
    """Calling check_all twice must not unlock the same achievement twice."""
    s = State()
    s.visited = ["lunuen", "nook", "forest"]
    buf1 = io.StringIO()
    with redirect_stdout(buf1):
        newly1 = achievements.check_all(s)
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        newly2 = achievements.check_all(s)
    # second call unlocks nothing new
    assert newly2 == []
    # no duplicate ids in the unlocked list
    ids = s.flags["achievements"]
    assert len(ids) == len(set(ids)), f"duplicate ids in {ids}"


def test_check_all_prints_unlock_line_exactly_once():
    """The 'Achievement unlocked' line must appear exactly once per new achievement."""
    s = State()
    s.visited = ["lunuen", "nook", "forest"]  # earns first_steps
    buf = io.StringIO()
    with redirect_stdout(buf):
        achievements.check_all(s)
    output = buf.getvalue()
    count = output.count("Achievement unlocked:")
    assert count == 1, f"expected exactly 1 unlock line, got {count}"
    assert "First Steps" in output


def test_check_all_multiple_unlocks_each_printed_once():
    """When several achievements are earned at once, each prints exactly once."""
    s = State()
    s.visited = ["lunuen", "nook", "forest", "lake", "gymnasium", "hill"]  # first_steps + explorer
    s.flag("met_noah")  # met_noah
    buf = io.StringIO()
    with redirect_stdout(buf):
        newly = achievements.check_all(s)
    output = buf.getvalue()
    for ach_id in newly:
        ach = achievements.get_achievement(ach_id)
        line = f"Achievement unlocked: {ach['name']}"
        assert output.count(line) == 1, (
            f"expected exactly 1 line for {ach['name']!r}, got {output.count(line)}"
        )


def test_check_all_does_not_reprint_already_unlocked():
    """An achievement already in the list must not print a second unlock line."""
    s = State()
    s.flag("met_noah")
    s.flags["achievements"] = ["met_noah"]  # already unlocked
    buf = io.StringIO()
    with redirect_stdout(buf):
        newly = achievements.check_all(s)
    assert newly == []
    assert "Achievement unlocked:" not in buf.getvalue()


# ---------------------------------------------------------------------------
# list_all: shows both unlocked and locked achievements
# ---------------------------------------------------------------------------

def test_list_all_shows_unlocked_and_locked():
    s = State()
    s.flag("met_noah")
    s.flags["achievements"] = ["met_noah"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        achievements.list_all(s)
    output = buf.getvalue()
    # unlocked achievement is listed
    assert "A Friend in the Nook" in output
    # a locked achievement is also listed
    assert "Explorer" in output
    # level line is present
    assert "Level" in output


def test_list_all_shows_all_achievements():
    s = State()
    buf = io.StringIO()
    with redirect_stdout(buf):
        achievements.list_all(s)
    output = buf.getvalue()
    for a in achievements.ACHIEVEMENTS:
        assert a["name"] in output, f"achievement {a['name']!r} not in list output"


def test_list_all_shows_count():
    s = State()
    s.flag("met_noah")
    s.flags["achievements"] = ["met_noah"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        achievements.list_all(s)
    output = buf.getvalue()
    total = len(achievements.ACHIEVEMENTS)
    assert f"1/{total}" in output


# ---------------------------------------------------------------------------
# Save round-trip
# ---------------------------------------------------------------------------

def test_save_roundtrip_preserves_achievements(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    s.flag("met_noah")
    s.flag("met_connor")
    s.flags["achievements"] = ["met_noah", "met_connor", "first_steps"]
    save_game(s)
    loaded = load_game()
    assert loaded.flags["achievements"] == ["met_noah", "met_connor", "first_steps"]


def test_save_roundtrip_preserves_state_achievements_field(tmp_path, monkeypatch):
    """The State.achievements field (v4) must survive save -> load."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    s.achievements = ["first_steps", "met_noah"]
    save_game(s)
    loaded = load_game()
    assert loaded.achievements == ["first_steps", "met_noah"]


def test_save_file_contains_achievements_key(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    s.flags["achievements"] = ["first_steps"]
    save_game(s)
    with open(tmp_path / "save.json") as f:
        data = json.load(f)
    assert "achievements" in data
    assert data["version"] == 4


# ---------------------------------------------------------------------------
# Migration from old save (v1: no `achievements` key)
# ---------------------------------------------------------------------------

def test_v1_save_migrates_with_empty_achievements():
    with open(REAL_SAVE) as f:
        d = json.load(f)
    s = State.from_dict(d)
    assert s.achievements == []
    # flags.achievements may or may not be present in the fixture
    assert s.flags.get("achievements", []) == []


def test_v1_save_loads_without_error(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    with open(REAL_SAVE) as f:
        original = f.read()
    with open(tmp_path / "save.json", "w") as f:
        f.write(original)
    s = load_game()
    assert isinstance(s, State)
    assert s.achievements == []


def test_v1_save_roundtrips_as_v4(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    with open(REAL_SAVE) as f:
        d = json.load(f)
    s = State.from_dict(d)
    save_game(s)
    with open(tmp_path / "save.json") as f:
        saved = json.load(f)
    assert saved["version"] == 4
    assert saved["achievements"] == []
    # old fields preserved
    assert saved["location"] == d["location"]
    assert saved["sanity"] == d["sanity"]
    assert saved["day"] == d["day"]


def test_v2_save_migrates_to_v4_with_achievements(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v2 = {
        "version": 2,
        "location": "lake",
        "sanity": 50,
        "trust": 5,
        "fear": -2,
        "flags": {"met_noah": True},
        "inventory": ["key"],
        "visited": ["lunuen", "lake"],
        "seen": ["lunuen"],
        "journal": [],
        "deaths": 0,
        "day": 3,
        "night": False,
    }
    with open(tmp_path / "save.json", "w") as f:
        json.dump(v2, f)
    s = load_game()
    assert s.achievements == []
    save_game(s)
    with open(tmp_path / "save.json") as f:
        saved = json.load(f)
    assert saved["version"] == 4
    assert saved["achievements"] == []
    assert saved["location"] == "lake"
    assert saved["sanity"] == 50
