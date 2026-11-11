"""Tests for the journal command (main.show_journal).

Verifies that:
  · the journal command exists and is callable
  · output contains all four expected categories (people, places, items, facts)
  · meeting a new person updates the people list
  · visiting a new place updates the places list
  · finding an item updates the items list
  · learning a fact updates the facts list
  · a fresh state shows empty-category placeholders
"""
import io
import contextlib

import pytest

import engine
import main


def _capture_journal(s):
    """Run show_journal(s) and return the captured stdout as a string."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main.show_journal(s)
    return buf.getvalue()


def test_journal_command_exists():
    """main.show_journal is a callable function."""
    assert callable(main.show_journal)


def test_journal_output_has_all_four_categories():
    """A state with data in every category shows all four section headers."""
    s = engine.State()
    s.journal_add("met", "Connor")
    s.journal_add("learned", "The valley counts.")
    s.take("bread")
    s.visited.append("schloss")
    out = _capture_journal(s)
    assert "PEOPLE MET" in out
    assert "PLACES VISITED" in out
    assert "ITEMS FOUND" in out
    assert "FACTS LEARNED" in out


def test_journal_people_met_shows_name():
    """Meeting a person adds their name to the people section."""
    s = engine.State()
    s.journal_add("met", "Mika")
    out = _capture_journal(s)
    assert "Mika" in out


def test_journal_meeting_new_person_updates_list():
    """A second person appears in the list after being met."""
    s = engine.State()
    s.journal_add("met", "Connor")
    out_before = _capture_journal(s)
    assert "Connor" in out_before
    assert "Mika" not in out_before

    s.journal_add("met", "Mika")
    out_after = _capture_journal(s)
    assert "Connor" in out_after
    assert "Mika" in out_after


def test_journal_places_visited_shows_location():
    """Visiting a new place adds it to the places section."""
    s = engine.State()
    s.visited.append("lake")
    out = _capture_journal(s)
    # The location name (not just the id) should appear
    import locations
    lake_name = locations.LOCATIONS["lake"].get("name", "lake")
    assert lake_name in out or "lake" in out.lower()


def test_journal_visiting_new_place_updates_list():
    """A second place appears after being visited."""
    s = engine.State()
    s.visited.append("schloss")
    out_before = _capture_journal(s)

    s.visited.append("lake")
    out_after = _capture_journal(s)
    import locations
    lake_name = locations.LOCATIONS["lake"].get("name", "lake")
    assert lake_name in out_after or "lake" in out_after.lower()
    # schloss should still be there
    schloss_name = locations.LOCATIONS["schloss"].get("name", "schloss")
    assert schloss_name in out_after or "schloss" in out_after.lower()


def test_journal_items_found_shows_item():
    """Taking an item adds it to the items section."""
    s = engine.State()
    s.take("notebook")
    out = _capture_journal(s)
    assert "notebook" in out.lower()


def test_journal_finding_new_item_updates_list():
    """A second item appears after being taken."""
    s = engine.State()
    s.take("bread")
    out_before = _capture_journal(s)
    assert "bread" in out_before.lower()

    s.take("notebook")
    out_after = _capture_journal(s)
    assert "bread" in out_after.lower()
    assert "notebook" in out_after.lower()


def test_journal_facts_learned_shows_fact():
    """A learned fact appears in the facts section."""
    s = engine.State()
    s.journal_add("learned", "The archivist keeps the key.")
    out = _capture_journal(s)
    assert "The archivist keeps the key." in out


def test_journal_learning_new_fact_updates_list():
    """A second fact appears after being learned."""
    s = engine.State()
    s.journal_add("learned", "The valley counts.")
    out_before = _capture_journal(s)
    assert "The valley counts." in out_before

    s.journal_add("learned", "The gate is shaped like a hand.")
    out_after = _capture_journal(s)
    assert "The valley counts." in out_after
    assert "The gate is shaped like a hand." in out_after


def test_journal_fresh_state_shows_placeholders():
    """A fresh state with no data shows placeholder text for each category."""
    s = engine.State()
    # Remove the default 'lunuen' from visited to test the empty case
    s.visited = []
    out = _capture_journal(s)
    assert "(no one yet)" in out
    # places and items sections should also show their placeholders
    places_section = out.split("PLACES VISITED")[1].split("ITEMS FOUND")[0]
    assert "(nowhere yet)" in places_section
    items_section = out.split("ITEMS FOUND")[1].split("FACTS LEARNED")[0]
    assert "(nothing yet)" in items_section
    facts_section = out.split("FACTS LEARNED")[1].split("chapter")[0]
    assert "(nothing yet)" in facts_section


def test_journal_output_is_built_from_state():
    """The journal output changes when the state changes.

    This confirms the output is dynamically built from the state object,
    not a static string.
    """
    s = engine.State()
    out_empty = _capture_journal(s)

    s.journal_add("met", "Connor")
    s.journal_add("learned", "Something new.")
    s.take("bread")
    out_filled = _capture_journal(s)

    assert out_empty != out_filled
    assert "Connor" in out_filled
    assert "Something new." in out_filled
    assert "bread" in out_filled.lower()


def test_journal_deduplication():
    """Adding the same person twice does not create a duplicate entry."""
    s = engine.State()
    s.journal_add("met", "Connor")
    s.journal_add("met", "Connor")  # duplicate
    out = _capture_journal(s)
    # Connor should appear exactly once in the people section
    people_section = out.split("PEOPLE MET")[1].split("PLACES VISITED")[0]
    assert people_section.count("Connor") == 1
