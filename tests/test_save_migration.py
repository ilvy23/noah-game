"""Save migration tests: v1 -> v2, v2 round-trip, and edge cases.

The real save.json in the repo is a v1 save (no `version` key). These
tests copy it into a temporary directory and verify that `State.from_dict`
migrates it cleanly, that v2 saves round-trip, and that no data is lost.
"""

import json
import os
import sys

import pytest

# make the project importable when pytest runs from the tests/ directory
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import engine  # noqa: E402
from engine import State  # noqa: E402


REAL_SAVE = os.path.join(PROJECT_DIR, "tests", "fixtures", "save_v1.json")   # a frozen v1 save; the player's own save.json is never a test input


def _load_real_save():
    with open(REAL_SAVE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# v1 migration (the real save.json in the repo is a v1 save)
# ---------------------------------------------------------------------------

def test_real_save_is_v1():
    """The repo's save.json has no `version` key, so it is a v1 save."""
    d = _load_real_save()
    assert "version" not in d, "expected the repo save to be v1 (no version key)"


def test_v1_save_migrates():
    """A v1 save must load into a State with all v2 fields present."""
    d = _load_real_save()
    s = State.from_dict(d)
    # v1 fields preserved
    assert s.location == d["location"]
    assert s.sanity == d["sanity"]
    assert s.flags == d["flags"]
    assert s.inventory == d["inventory"]
    assert s.day == d["day"]
    assert s.night == d["night"]
    # v2 fields get defaults
    assert s.trust == 0
    assert s.fear == 0
    assert s.journal == []
    assert s.deaths == 0
    assert isinstance(s.seen, list)
    # v1 migration: every visited location is treated as already-seen
    for loc in d["visited"]:
        assert loc in s.seen


def test_v1_save_roundtrips_as_v2(tmp_path, monkeypatch):
    """A v1 save loaded and re-saved must be a v2 save (has `version`)."""
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    d = _load_real_save()
    s = State.from_dict(d)
    engine.save_game(s)

    with open(save_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["version"] == 4
    assert saved["location"] == d["location"]
    assert saved["sanity"] == d["sanity"]
    assert saved["trust"] == 0
    assert saved["fear"] == 0
    assert saved["deaths"] == 0
    assert saved["achievements"] == []


def test_v1_save_loads_via_load_game(tmp_path, monkeypatch):
    """load_game() must accept a v1 save file and return a State."""
    save_path = tmp_path / "save.json"
    with open(REAL_SAVE, "r", encoding="utf-8") as f:
        original = f.read()
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(original)
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    assert engine.save_exists()
    s = engine.load_game()
    assert isinstance(s, State)
    assert s.location == "forest"
    assert s.sanity == 77


def test_v1_missing_fields_get_defaults():
    """A v1 save missing optional fields must not crash."""
    d = {"location": "lunuen", "sanity": 50}
    s = State.from_dict(d)
    assert s.location == "lunuen"
    assert s.sanity == 50
    assert s.trust == 0
    assert s.fear == 0
    assert s.flags == {}
    assert s.inventory == []
    assert s.visited == ["lunuen"]
    assert s.journal == []
    assert s.deaths == 0
    assert s.day == 1
    assert s.night is False


def test_v2_save_keeps_seen():
    """A v2 save with an explicit `seen` list must keep it (not be overwritten)."""
    d = {
        "version": 2,
        "location": "lake",
        "sanity": 42,
        "trust": 5,
        "fear": 3,
        "flags": {"test_flag": True},
        "inventory": ["key"],
        "visited": ["lunuen", "lake"],
        "seen": ["lunuen"],
        "journal": [{"kind": "learned", "text": "something"}],
        "deaths": 1,
        "day": 3,
        "night": False,
    }
    s = State.from_dict(d)
    assert s.seen == ["lunuen"]
    assert s.location == "lake"
    assert s.sanity == 42
    assert s.trust == 5
    assert s.fear == 3
    assert s.has("test_flag")
    assert s.has_item("key")
    assert s.journal == [{"kind": "learned", "text": "something"}]
    assert s.deaths == 1
    assert s.day == 3


def test_v2_roundtrip_preserves_everything(tmp_path, monkeypatch):
    """A v2 save must survive save -> load with every field intact."""
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    s = State()
    s.location = "gymnasium"
    s.sanity = 33
    s.trust = 12
    s.fear = -7
    s.flag("made_choice", True)
    s.take("ritual_text")
    s.take("key")
    s.visited.append("gymnasium")
    s.seen.append("lunuen")
    s.journal_add("learned", "the valley is patient")
    s.deaths = 2
    s.day = 6
    s.night = True

    engine.save_game(s)
    s2 = engine.load_game()

    assert s2.location == "gymnasium"
    assert s2.sanity == 33
    assert s2.trust == 12
    assert s2.fear == -7
    assert s2.has("made_choice")
    assert s2.has_item("ritual_text")
    assert s2.has_item("key")
    assert s2.visited == ["lunuen", "gymnasium"]
    assert s2.seen == ["lunuen"]
    assert s2.journal == [{"kind": "learned", "text": "the valley is patient"}]
    assert s2.deaths == 2
    assert s2.day == 6
    assert s2.night is True


def test_v4_save_has_achievements_field(tmp_path, monkeypatch):
    """A v4 save must include the `achievements` field."""
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    s = State()
    s.achievements = ["first_talk", "found_item"]
    engine.save_game(s)

    with open(save_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["version"] == 4
    assert saved["achievements"] == ["first_talk", "found_item"]


def test_v4_roundtrip_preserves_achievements(tmp_path, monkeypatch):
    """A v4 save with achievements must survive save -> load."""
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    s = State()
    s.achievements = ["first_talk", "found_item", "survived_day3"]
    engine.save_game(s)
    s2 = engine.load_game()

    assert s2.achievements == ["first_talk", "found_item", "survived_day3"]


def test_v1_fixture_loads_with_empty_achievements():
    """The v1 fixture must load with an empty achievements list."""
    d = _load_real_save()
    s = State.from_dict(d)
    assert s.achievements == []


def test_v1_fixture_preserves_all_fields():
    """The v1 fixture must preserve every pre-existing field after migration."""
    d = _load_real_save()
    s = State.from_dict(d)
    assert s.location == d["location"]
    assert s.sanity == d["sanity"]
    assert s.flags == d["flags"]
    assert s.inventory == d["inventory"]
    assert s.visited == d["visited"]
    assert s.day == d["day"]
    assert s.night == d["night"]
    # v2+ fields get defaults
    assert s.trust == 0
    assert s.fear == 0
    assert s.journal == []
    assert s.deaths == 0
    assert s.chapter == 1
    assert s.achievements == []


def test_v2_save_migrates_to_v4(tmp_path, monkeypatch):
    """A v2 save must load and re-save as v4 with achievements field."""
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    d = {
        "version": 2,
        "location": "lake",
        "sanity": 42,
        "trust": 5,
        "fear": 3,
        "flags": {"test_flag": True},
        "inventory": ["key"],
        "visited": ["lunuen", "lake"],
        "seen": ["lunuen"],
        "journal": [{"kind": "learned", "text": "something"}],
        "deaths": 1,
        "day": 3,
        "night": False,
    }
    s = State.from_dict(d)
    engine.save_game(s)

    with open(save_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["version"] == 4
    assert saved["achievements"] == []
    assert saved["location"] == "lake"
    assert saved["sanity"] == 42
    assert saved["trust"] == 5
    assert saved["fear"] == 3
    assert saved["deaths"] == 1
    assert saved["day"] == 3


def test_v3_save_migrates_to_v4(tmp_path, monkeypatch):
    """A v3 save must load and re-save as v4 with achievements field."""
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(engine, "SAVE_PATH", str(save_path))

    d = {
        "version": 3,
        "location": "forest",
        "sanity": 60,
        "trust": 10,
        "fear": -5,
        "flags": {"met_noah": True},
        "inventory": ["notebook"],
        "visited": ["lunuen", "forest"],
        "seen": ["lunuen"],
        "journal": [],
        "deaths": 0,
        "day": 2,
        "night": False,
        "chapter": 2,
        "connor_line": 3,
        "mika_line": 1,
        "noah_rest_day": 1,
        "context": None,
    }
    s = State.from_dict(d)
    engine.save_game(s)

    with open(save_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["version"] == 4
    assert saved["achievements"] == []
    assert saved["location"] == "forest"
    assert saved["sanity"] == 60
    assert saved["trust"] == 10
    assert saved["fear"] == -5
    assert saved["chapter"] == 2
    assert saved["deaths"] == 0
    assert saved["day"] == 2
