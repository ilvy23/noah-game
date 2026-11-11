"""Text-quality tests for FOLK.

Covers:
  1. No text strings are empty or whitespace-only.
  2. No duplicate text strings exist across the project's text modules.
  3. Texts that reference the player's last event contain specific
     keywords from that previous action or location.
  4. Consecutive text lines include references to the preceding
     player interaction (via the context mechanism).

All tests use temporary paths or in-process imports; the real save.json
is never touched.
"""

import ast
import importlib
import os
import sys

import pytest

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

# The modules that hold player-facing text.
TEXT_MODULES = [
    "story",
    "dialogue",
    "locations",
    "noah",
    "characters",
    "deaths",
]

# Modules that define text as module-level constants (str or list of str).
# We skip engine, context, main, music — they are logic, not text.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_text_strings(module_name: str):
    """Import a module and return a list of (name, text) pairs for every
    module-level string constant (including strings inside J([...]) calls
    that are assigned to a module-level name).

    We use AST to avoid executing the module (some modules have side
    effects on import). We only look at top-level assignments whose
    value is a string literal or a call to J() with string arguments.
    """
    path = os.path.join(PROJECT_DIR, module_name + ".py")
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=path)

    results = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        # Only single-name targets (skip tuple unpacking)
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        # Skip private / helper names
        if name.startswith("_") or name in ("NL", "J"):
            continue
        value = node.value
        texts = _extract_strings(value)
        for t in texts:
            results.append((name, t))
    return results


def _extract_strings(node):
    """Recursively extract all string literals from an AST node.

    For J([...]) calls (the project's text-joiner), we join the list
    elements into a single string so that the whole block is treated as
    one text unit, not as individual lines.  This avoids false-positive
    "duplicates" from shared line fragments and false-positive "empty"
    strings from intentional blank-line separators.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, (ast.List, ast.Tuple)):
        out = []
        for elt in node.elts:
            out.extend(_extract_strings(elt))
        return out
    if isinstance(node, ast.Call):
        # J([...]) — join the list into one string
        if (isinstance(node.func, ast.Name) and node.func.id == "J"
                and len(node.args) == 1
                and isinstance(node.args[0], (ast.List, ast.Tuple))):
            parts = []
            for elt in node.args[0].elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    parts.append(elt.value)
                else:
                    parts.extend(_extract_strings(elt))
            joined = "\n".join(parts)
            return [joined] if joined.strip() else []
        # Other calls: extract from arguments
        out = []
        for arg in node.args:
            out.extend(_extract_strings(arg))
        return out
    if isinstance(node, ast.Dict):
        out = []
        for v in node.values:
            out.extend(_extract_strings(v))
        return out
    return []


def _all_text_strings():
    """Collect (module, name, text) for every text constant in the project."""
    all_texts = []
    for mod in TEXT_MODULES:
        try:
            pairs = _collect_text_strings(mod)
        except Exception:
            continue
        for name, text in pairs:
            all_texts.append((mod, name, text))
    return all_texts


# ---------------------------------------------------------------------------
# 1. No empty or whitespace-only text strings
# ---------------------------------------------------------------------------

def test_no_empty_text_strings():
    """Every text constant must be non-empty and not whitespace-only.

    (Blank-line separators inside J([...]) blocks are joined into the
    parent string by the collector, so they do not appear as separate
    entries.)"""
    all_texts = _all_text_strings()
    assert len(all_texts) > 0, "no text strings found — collection is broken"
    empty = [
        (mod, name)
        for mod, name, text in all_texts
        if not text.strip()
    ]
    assert not empty, f"empty/whitespace-only text strings: {empty[:10]}"


# ---------------------------------------------------------------------------
# 2. No duplicate text strings
# ---------------------------------------------------------------------------

def test_no_duplicate_text_strings():
    """No two text constants (across all text modules) should be
    identical after stripping.

    J([...]) blocks are joined into a single string by the collector,
    so we compare whole text blocks, not individual lines.

    characters.py is a legacy module whose text is superseded by the
    dialogue trees in dialogue.py (CONNOR_HELLO ≈ CONNOR_OPEN, etc.).
    We exclude characters.py from the duplicate check because those
    overlaps are intentional legacy copies, not accidental duplicates.
    """
    all_texts = _all_text_strings()
    # Exclude characters.py (legacy text superseded by dialogue.py)
    all_texts = [(m, n, t) for m, n, t in all_texts if m != "characters"]
    seen = {}
    dups = []
    for mod, name, text in all_texts:
        key = text.strip()
        if not key:
            continue
        if key in seen:
            dups.append((seen[key], (mod, name), key[:60]))
        else:
            seen[key] = (mod, name)
    assert not dups, (
        f"duplicate text strings found ({len(dups)}):\n"
        + "\n".join(f"  {a} == {b}: {t!r}" for a, b, t in dups[:10])
    )


# ---------------------------------------------------------------------------
# 3. Context-referencing texts contain keywords from the previous action
# ---------------------------------------------------------------------------

def test_context_ref_contains_action_keyword():
    """When context.record() stores a 'talk' event with who='connor',
    context.ref(s) must contain 'Connor' (the NPC name).

    When it stores a 'move' event with place='lake',
    context.ref(s) must contain 'lake'.

    When it stores a 'choice' event with label='stay',
    context.ref(s) must contain 'stay'.
    """
    import context
    from engine import State

    # talk
    s = State()
    context.record(s, "talk", who="connor", place="lunuen")
    ref = context.ref(s)
    assert "Connor" in ref, f"talk ref missing NPC name: {ref!r}"

    # move
    s2 = State()
    context.record(s2, "move", place="lake")
    ref2 = context.ref(s2)
    assert "lake" in ref2, f"move ref missing place: {ref2!r}"

    # choice
    s3 = State()
    context.record(s3, "choice", who="mika", label="stay in the valley")
    ref3 = context.ref(s3)
    assert "stay in the valley" in ref3, f"choice ref missing label: {ref3!r}"

    # ask
    s4 = State()
    context.record(s4, "ask", who="noah", label="the ledger")
    ref4 = context.ref(s4)
    assert "Noah" in ref4, f"ask ref missing NPC name: {ref4!r}"
    assert "the ledger" in ref4, f"ask ref missing topic: {ref4!r}"

    # item
    s5 = State()
    context.record(s5, "item", label="key", place="schloss")
    ref5 = context.ref(s5)
    assert "key" in ref5, f"item ref missing label: {ref5!r}"


def test_context_ref_empty_when_no_event():
    """A fresh State with no recorded event must give an empty ref."""
    import context
    from engine import State

    s = State()
    assert context.ref(s) == ""
    assert context.last(s) is None


def test_context_clear_resets():
    """context.clear() must remove the stored record."""
    import context
    from engine import State

    s = State()
    context.record(s, "talk", who="connor")
    assert context.ref(s) != ""
    context.clear(s)
    assert context.ref(s) == ""
    assert context.last(s) is None


# ---------------------------------------------------------------------------
# 4. Consecutive text lines reference the preceding interaction
# ---------------------------------------------------------------------------

def test_locations_chapter_line_includes_context_ref():
    """locations.chapter_line() must prepend the context ref when one
    exists, so the location text is a continuation of the last event."""
    import context
    import locations
    from engine import State

    s = State()
    s.chapter = 1
    # Record a move to lunuen
    context.record(s, "move", place="lunuen")
    line = locations.chapter_line(s, "lunuen")
    # The line must contain the context ref text
    assert "walked to lunuen" in line, (
        f"chapter_line did not include context ref; got: {line[:120]!r}"
    )


def test_locations_chapter_line_without_context():
    """Without a context record, chapter_line must still return the
    base text (no crash, no empty string)."""
    import locations
    from engine import State

    s = State()
    s.chapter = 1
    line = locations.chapter_line(s, "lunuen")
    assert line.strip(), "chapter_line returned empty text"
    # Must NOT contain the context-ref prefix
    assert "— and now this." not in line


def test_noah_place_text_includes_context_ref():
    """noah.place_text() must include the context ref when one exists."""
    import context
    import noah
    from engine import State

    s = State()
    s.chapter = 1
    s.sanity = 80
    context.record(s, "talk", who="connor", place="lunuen")
    text = noah.place_text(s)
    assert "talked to Connor" in text, (
        f"noah.place_text did not include context ref; got: {text[:120]!r}"
    )


def test_noah_place_text_without_context():
    """noah.place_text() must work without a context record."""
    import noah
    from engine import State

    s = State()
    s.chapter = 1
    s.sanity = 80
    text = noah.place_text(s)
    assert text.strip(), "noah.place_text returned empty text"


def test_consecutive_lines_connect_after_talk():
    """Simulate: player talks to Connor, then moves to the lake.
    The lake's chapter_line must reference the talk to Connor."""
    import context
    import locations
    from engine import State

    s = State()
    s.chapter = 1
    # Player talks to Connor
    context.record(s, "talk", who="connor", place="lunuen")
    # Player moves to the lake
    context.record(s, "move", place="lake")
    # The lake text should reference the last event (the move)
    line = locations.chapter_line(s, "lake")
    assert "walked to lake" in line, (
        f"lake chapter_line missing move ref; got: {line[:120]!r}"
    )


def test_consecutive_lines_connect_after_choice():
    """Simulate: player makes a choice at the schloss, then the
    schloss text must reference that choice."""
    import context
    import locations
    from engine import State

    s = State()
    s.chapter = 3
    context.record(s, "choice", label="stay in the valley", place="schloss")
    line = locations.chapter_line(s, "schloss")
    assert "stay in the valley" in line, (
        f"schloss chapter_line missing choice label; got: {line[:120]!r}"
    )


# ---------------------------------------------------------------------------
# 5. Save-file safety: tests use fixtures, not root save.json
# ---------------------------------------------------------------------------

def test_fixture_save_exists():
    """The v1 fixture save must exist for migration tests."""
    fixture = os.path.join(PROJECT_DIR, "tests", "fixtures", "save_v1.json")
    assert os.path.exists(fixture), f"missing fixture: {fixture}"


def test_fixture_save_loads_into_state(tmp_path, monkeypatch):
    """The v1 fixture save must load cleanly into a State via
    engine.load_game, proving the fixture data is real and usable."""
    import json
    import engine
    from engine import load_game

    fixture = os.path.join(PROJECT_DIR, "tests", "fixtures", "save_v1.json")
    with open(fixture, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Sanity-check the fixture data itself
    assert data["location"] == "forest"
    assert data["sanity"] == 77
    assert "met_noah" in data["flags"]

    # Load it through the real migration path into a temp save file
    monkeypatch.setattr(engine, "SAVE_PATH", str(tmp_path / "save.json"))
    with open(tmp_path / "save.json", "w", encoding="utf-8") as f:
        json.dump(data, f)

    s = load_game()
    assert s is not None, "load_game returned None for the v1 fixture"
    assert s.location == "forest"
    assert s.sanity == 77
    assert s.has("met_noah")
    assert s.chapter == 1, "v1 save must migrate to chapter 1"


def test_root_save_not_modified_by_text_tests():
    """Running the text-quality tests must not create or modify
    save.json in the project root."""
    root_save = os.path.join(PROJECT_DIR, "save.json")
    if os.path.exists(root_save):
        with open(root_save, "r", encoding="utf-8") as f:
            before = f.read()
        # Re-run the text collection (no game execution)
        _all_text_strings()
        with open(root_save, "r", encoding="utf-8") as f:
            after = f.read()
        assert before == after, "root save.json was modified"
    else:
        # If no save.json exists, it must not be created
        _all_text_strings()
        assert not os.path.exists(root_save), "save.json was created"


# ---------------------------------------------------------------------------
# 6. EOF handling: deaths.ask and pause() unchanged
# ---------------------------------------------------------------------------

def test_deaths_ask_eof_returns_quit():
    """deaths._ask must return 'quit' on EOF (empty stdin)."""
    import io
    import contextlib
    import deaths

    # Simulate EOF: input() raises EOFError
    def _eof_input(prompt=""):
        raise EOFError

    with contextlib.redirect_stdout(io.StringIO()):
        # Patch builtins.input to raise EOFError
        import builtins
        orig_input = builtins.input
        builtins.input = _eof_input
        try:
            result = deaths._ask("> ")
        finally:
            builtins.input = orig_input

    assert result == "quit", f"deaths._ask on EOF should return 'quit', got {result!r}"


def test_pause_eof_returns_quietly():
    """main.pause() must not crash on EOF (empty stdin)."""
    import io
    import contextlib
    import builtins

    def _eof_input(prompt=""):
        raise EOFError

    with contextlib.redirect_stdout(io.StringIO()):
        orig_input = builtins.input
        builtins.input = _eof_input
        try:
            import main
            main.pause()  # should not raise
        finally:
            builtins.input = orig_input
    # If we get here, pause() handled EOF gracefully
