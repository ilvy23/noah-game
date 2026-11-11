"""Engine tests: State, sanity, journal, save/load, migration."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine
from engine import State, save_game, load_game, save_exists


# ---------------------------------------------------------------------------
# State basics
# ---------------------------------------------------------------------------

def test_fresh_state_defaults():
    s = State()
    assert s.location == "lunuen"
    assert s.sanity == 80
    assert s.trust == 0
    assert s.fear == 0
    assert s.flags == {}
    assert s.inventory == []
    assert s.visited == ["lunuen"]
    assert s.seen == []
    assert s.journal == []
    assert s.deaths == 0
    assert s.day == 1
    assert s.night is False


def test_sanity_clamped():
    s = State()
    s.sanity_change(-200)
    assert s.sanity == 0
    s.sanity_change(200)
    assert s.sanity == 100


def test_trust_clamped():
    s = State()
    s.trust_change(200)
    assert s.trust == 100
    s.trust_change(-300)
    assert s.trust == -100


def test_fear_clamped():
    s = State()
    s.fear_change(-200)
    assert s.fear == -100
    s.fear_change(300)
    assert s.fear == 100


def test_sanity_tier_boundaries():
    s = State()
    s.sanity = 100
    assert s.sanity_tier == "steady"
    s.sanity = 60
    assert s.sanity_tier == "steady"
    s.sanity = 59
    assert s.sanity_tier == "thin"
    s.sanity = 40
    assert s.sanity_tier == "thin"
    s.sanity = 39
    assert s.sanity_tier == "low"
    s.sanity = 20
    assert s.sanity_tier == "low"
    s.sanity = 19
    assert s.sanity_tier == "critical"
    s.sanity = 0
    assert s.sanity_tier == "critical"


def test_flag_set_and_has():
    s = State()
    assert not s.has("test_flag")
    s.flag("test_flag")
    assert s.has("test_flag")
    s.flag("test_flag", False)
    assert not s.has("test_flag")


def test_inventory_take_and_has():
    s = State()
    assert not s.has_item("key")
    assert s.take("key") is True
    assert s.has_item("key")
    assert s.take("key") is False  # already have it
    assert s.inventory == ["key"]


def test_journal_add_dedupes():
    s = State()
    s.journal_add("learned", "the lake is breathing")
    s.journal_add("learned", "the lake is breathing")  # duplicate
    s.journal_add("learned", "the forest is counting")
    assert len(s.journal) == 2
    assert s.journal[0]["kind"] == "learned"
    assert s.journal[0]["text"] == "the lake is breathing"


def test_journal_has():
    s = State()
    s.journal_add("decided", "told Connor I'm leaving")
    assert s.journal_has("decided", "told Connor I'm leaving")
    assert not s.journal_has("decided", "told Mika I'm leaving")


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    s.location = "lake"
    s.sanity = 42
    s.trust = 17
    s.fear = -3
    s.flag("mika_why")
    s.take("key")
    s.journal_add("learned", "the valley wants a witness")
    s.deaths = 1
    s.day = 5
    s.night = True
    save_game(s)
    assert save_exists()
    loaded = load_game()
    assert loaded.location == "lake"
    assert loaded.sanity == 42
    assert loaded.trust == 17
    assert loaded.fear == -3
    assert loaded.has("mika_why")
    assert loaded.has_item("key")
    assert loaded.journal_has("learned", "the valley wants a witness")
    assert loaded.deaths == 1
    assert loaded.day == 5
    assert loaded.night is True


def test_save_file_is_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    s.flag("test")
    save_game(s)
    with open(tmp_path / "save.json") as f:
        data = json.load(f)
    assert data["version"] == 4


# ---------------------------------------------------------------------------
# v1 → v2 migration
# ---------------------------------------------------------------------------

def test_v1_save_migration(tmp_path, monkeypatch):
    """A v1 save (no `version` key, no `seen` list) must load cleanly."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v1 = {
        "location": "forest",
        "sanity": 77,
        "flags": {},
        "inventory": [],
        "visited": ["lunuen", "forest"],
        "day": 2,
        "night": False,
        "connor_line": 0,
        "mika_line": 0,
    }
    with open(tmp_path / "save.json", "w") as f:
        json.dump(v1, f)
    s = load_game()
    assert s.location == "forest"
    assert s.sanity == 77
    assert s.day == 2
    # v2 fields get defaults
    assert s.trust == 0
    assert s.fear == 0
    assert s.journal == []
    assert s.deaths == 0
    # migration: visited locations are treated as already-seen
    assert "lunuen" in s.seen
    assert "forest" in s.seen


def test_v2_save_not_migrated(tmp_path, monkeypatch):
    """A v2 save with an explicit `seen` list must keep it."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v2 = {
        "version": 2,
        "location": "lake",
        "sanity": 50,
        "trust": 5,
        "fear": -2,
        "flags": {"mika_why": True},
        "inventory": ["key"],
        "visited": ["lunuen", "lake"],
        "seen": ["lunuen"],  # only lunuen seen, lake not yet
        "journal": [],
        "deaths": 0,
        "day": 3,
        "night": False,
    }
    with open(tmp_path / "save.json", "w") as f:
        json.dump(v2, f)
    s = load_game()
    assert s.seen == ["lunuen"]  # not overwritten by visited
    assert s.has("mika_why")
    assert s.has_item("key")


# ---------------------------------------------------------------------------
# v3 migration: chapter field
# ---------------------------------------------------------------------------

def test_v3_save_has_chapter(tmp_path, monkeypatch):
    """A fresh save must have version 3 and chapter 1."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    save_game(s)
    with open(tmp_path / "save.json") as f:
        data = json.load(f)
    assert data["version"] == 4


def test_v1_save_migrates_to_chapter_1(tmp_path, monkeypatch):
    """A v1 save (no version, no chapter) must load with chapter=1."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v1 = {
        "location": "forest",
        "sanity": 77,
        "flags": {},
        "inventory": [],
        "visited": ["lunuen", "forest"],
        "day": 2,
        "night": False,
    }
    with open(tmp_path / "save.json", "w") as f:
        json.dump(v1, f)
    s = load_game()
    assert s.chapter == 1
    assert s.location == "forest"
    assert s.sanity == 77


def test_v2_save_migrates_to_chapter_1(tmp_path, monkeypatch):
    """A v2 save (version: 2, no chapter) must load with chapter=1."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v2 = {
        "version": 2,
        "location": "lake",
        "sanity": 50,
        "trust": 5,
        "fear": -2,
        "flags": {"mika_why": True},
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
    assert s.chapter == 1
    assert s.has("mika_why")
    assert s.has_item("key")


def test_v3_save_preserves_chapter(tmp_path, monkeypatch):
    """A v3 save with chapter=3 must load with chapter=3."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v3 = {
        "version": 3,
        "location": "schloss",
        "sanity": 40,
        "trust": 10,
        "fear": 5,
        "flags": {"ch1_done": True, "ch2_done": True, "ch3_done": True},
        "inventory": ["key", "ritual_text"],
        "visited": ["lunuen", "forest", "lake", "schloss"],
        "seen": ["lunuen", "forest", "lake"],
        "journal": [],
        "deaths": 0,
        "day": 5,
        "night": True,
        "chapter": 4,
    }
    with open(tmp_path / "save.json", "w") as f:
        json.dump(v3, f)
    s = load_game()
    assert s.chapter == 4
    assert s.has("ch1_done")
    assert s.has("ch2_done")
    assert s.has("ch3_done")


# ---------------------------------------------------------------------------
# save failure (PermissionError / OSError)
# ---------------------------------------------------------------------------

def test_save_failure_prints_friendly_message(tmp_path, monkeypatch, capsys):
    """When save.json cannot be written, the game must print a short
    friendly message in the game's voice and keep running (no traceback)."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    s.flag("test")

    # Simulate a PermissionError on open()
    import builtins
    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if "save.json" in str(path):
            raise PermissionError("[Errno 13] Permission denied: save.json")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    result = save_game(s)
    captured = capsys.readouterr()
    # save_game returns "" on failure
    assert result == ""
    # the friendly message is printed
    assert "could not write" in captured.out
    # the game state is intact (game keeps running)
    assert s.has("test")


def test_save_failure_oserror(tmp_path, monkeypatch, capsys):
    """An OSError (not just PermissionError) must also be handled gracefully."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()

    import builtins
    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if "save.json" in str(path):
            raise OSError("[Errno 5] Input/output error: save.json")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    result = save_game(s)
    captured = capsys.readouterr()
    assert result == ""
    assert "could not write" in captured.out


# ---------------------------------------------------------------------------
# Context tracking mechanism
# ---------------------------------------------------------------------------

import context


def test_context_fresh_state_has_no_record():
    """A fresh State must have context=None and ref() must return ''."""
    s = State()
    assert s.context is None
    assert context.last(s) is None
    assert context.ref(s) == ""


def test_context_record_talk():
    """record() with kind='talk' must store a retrievable record."""
    s = State()
    context.record(s, "talk", who="connor", place="forest")
    rec = context.last(s)
    assert rec is not None
    assert rec["kind"] == "talk"
    assert rec["who"] == "connor"
    assert rec["place"] == "forest"
    assert "Connor" in rec["text"]
    assert context.ref(s) == rec["text"]


def test_context_record_choice():
    """record() with kind='choice' must include the label in the text."""
    s = State()
    context.record(s, "choice", who="mika", label="tell me about the face")
    rec = context.last(s)
    assert rec["kind"] == "choice"
    assert rec["who"] == "mika"
    assert rec["label"] == "tell me about the face"
    assert "Mika" in rec["text"]
    assert "tell me about the face" in rec["text"]


def test_context_record_move():
    """record() with kind='move' must include the destination."""
    s = State()
    context.record(s, "move", place="lake")
    rec = context.last(s)
    assert rec["kind"] == "move"
    assert rec["place"] == "lake"
    assert "lake" in rec["text"]


def test_context_record_item():
    """record() with kind='item' must include the item label."""
    s = State()
    context.record(s, "item", label="key")
    rec = context.last(s)
    assert rec["kind"] == "item"
    assert rec["label"] == "key"
    assert "key" in rec["text"]


def test_context_record_ask():
    """record() with kind='ask' must include the topic."""
    s = State()
    context.record(s, "ask", who="archivist", label="the cost")
    rec = context.last(s)
    assert rec["kind"] == "ask"
    assert rec["who"] == "archivist"
    assert rec["label"] == "the cost"
    assert "the cost" in rec["text"]


def test_context_overwrite():
    """A second record() call must replace the first."""
    s = State()
    context.record(s, "talk", who="connor")
    context.record(s, "move", place="lake")
    rec = context.last(s)
    assert rec["kind"] == "move"
    assert rec["place"] == "lake"
    assert "connor" not in rec["who"]


def test_context_clear():
    """clear() must reset context to None."""
    s = State()
    context.record(s, "talk", who="mika")
    context.clear(s)
    assert s.context is None
    assert context.last(s) is None
    assert context.ref(s) == ""


def test_context_attach_idempotent():
    """attach() must set context=None if missing, and not overwrite if present."""
    s = State()
    # Fresh state already has context=None from __init__
    context.attach(s)
    assert s.context is None
    # After a record, attach must not wipe it
    context.record(s, "talk", who="noah")
    context.attach(s)
    assert context.last(s) is not None
    assert context.last(s)["who"] == "noah"


def test_context_survives_save_load(tmp_path, monkeypatch):
    """A context record must survive a save/load round-trip."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    s = State()
    context.record(s, "talk", who="connor", place="forest")
    save_game(s)
    loaded = load_game()
    rec = context.last(loaded)
    assert rec is not None
    assert rec["kind"] == "talk"
    assert rec["who"] == "connor"
    assert rec["place"] == "forest"


def test_context_old_save_without_context(tmp_path, monkeypatch):
    """A v1 save (no context key) must load with context=None."""
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    v1 = {
        "location": "forest",
        "sanity": 77,
        "flags": {},
        "inventory": [],
        "visited": ["lunuen", "forest"],
        "day": 2,
        "night": False,
    }
    with open(tmp_path / "save.json", "w") as f:
        json.dump(v1, f)
    s = load_game()
    assert s.context is None
    assert context.last(s) is None
    assert context.ref(s) == ""


def test_context_ref_in_story_advance():
    """story.advance_chapter must reference the last interaction when present."""
    import story
    s = State()
    # Set up: chapter 1 condition met
    s.flag("read_letter")
    s.flag("met_connor")
    context.record(s, "talk", who="connor", place="forest")
    msg = story.advance_chapter(s)
    assert "the week turns" in msg
    assert "talked to Connor" in msg


def test_context_ref_in_story_advance_no_context():
    """story.advance_chapter must still work when there is no context."""
    import story
    s = State()
    s.flag("read_letter")
    s.flag("met_connor")
    # No context.record call
    msg = story.advance_chapter(s)
    assert "the week turns" in msg
    assert "talked to" not in msg


def test_context_ref_in_locations_chapter_line():
    """locations.chapter_line must reference the last interaction when present."""
    import locations
    s = State()
    context.record(s, "talk", who="connor", place="forest")
    line = locations.chapter_line(s, "lunuen")
    assert "talked to Connor" in line


def test_context_ref_in_locations_chapter_line_no_context():
    """locations.chapter_line must still return the base line without context."""
    import locations
    s = State()
    line = locations.chapter_line(s, "lunuen")
    assert line != ""
    assert "talked to" not in line


def test_context_ref_in_noah_place_text():
    """noah.place_text must reference the last interaction when present."""
    import noah
    s = State()
    context.record(s, "talk", who="mika", place="lake")
    text = noah.place_text(s)
    assert "talked to Mika" in text


def test_context_ref_in_noah_place_text_no_context():
    """noah.place_text must still work without context."""
    import noah
    s = State()
    text = noah.place_text(s)
    assert "talked to" not in text
    assert "clearing" in text


def test_context_who_name():
    """who_name must map NPC ids to display names."""
    assert context.who_name("connor") == "Connor"
    assert context.who_name("mika") == "Mika"
    assert context.who_name("archivist") == "the archivist"
    assert context.who_name("noah") == "Noah"
    assert context.who_name("") == ""
    assert context.who_name("unknown") == "unknown"


def test_context_ref_never_empty_after_record():
    """Every recorded event kind must produce a non-empty ref string."""
    import context
    for kind, kwargs in [
        ("talk", {"who": "connor"}),
        ("move", {"place": "lake"}),
        ("choice", {"label": "stay"}),
        ("ask", {"who": "noah", "label": "the ledger"}),
        ("item", {"label": "key"}),
    ]:
        s = State()
        context.record(s, kind, **kwargs)
        ref = context.ref(s)
        assert ref.strip(), f"{kind}: ref is empty or whitespace-only: {ref!r}"


def test_context_record_replaces_previous_event():
    """A second record must replace the first (consecutive interactions),
    and the ref must not mix both events together."""
    import context
    s = State()
    context.record(s, "talk", who="connor", place="lunuen")
    context.record(s, "move", place="lake")
    ref = context.ref(s)
    assert "lake" in ref
    assert "Connor" not in ref, f"old event leaked into new ref: {ref!r}"
