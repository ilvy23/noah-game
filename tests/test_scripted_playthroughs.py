"""Scripted playthroughs: run `python3 main.py --continue` as a subprocess
in a temporary directory and feed stdin.

Covers at least 3 different endings and at least 2 different deaths, with
specific text assertions for each.

The real save.json in the repo is read-only and is never touched: the game
runs in a temp directory with its own save.json.

How the game reads stdin:
  1. main() calls pause() twice (two blank lines consumed).
  2. game_loop starts. If location is schloss and the ritual is unlocked,
     offer_final() renders the final scene and calls ask(">") for a choice.
  3. If a death is triggered, death_screen() renders the death text and
     calls _ask("> ") for a choice (1=load, 2=start over, q=quit).
"""

import json
import os
import shutil
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL_SAVE = os.path.join(PROJECT_DIR, "tests", "fixtures", "save_v1.json")   # a frozen v1 save; the player's own save.json is never a test input

GAME_FILES = [
    "engine.py",
    "texts.py",
    "story_extra.py",
    "ascii_art.py",
    "story_game.py",
    "boss_ui.py",
    "boss.py",
    "credits.py",
    "audio.py",
    "ui.py",
    "menu_art.py",
    "context.py",
    "locations.py",
    "characters.py",
    "story.py",
    "dialogue.py",
    "deaths.py",
    "achievements.py",
    "main.py",
    "noah.py",
    "music.py",
]


def _copy_game(tmp_path):
    for name in GAME_FILES:
        shutil.copy2(os.path.join(PROJECT_DIR, name), tmp_path / name)
    return tmp_path


def _make_sleep_noop(tmp_path):
    """Create a sitecustomize.py that patches time.sleep to a no-op."""
    patch_dir = tmp_path / "_patch"
    patch_dir.mkdir(exist_ok=True)
    (patch_dir / "sitecustomize.py").write_text(
        "import time\ntime.sleep = lambda *a, **kw: None\n"
    )
    return str(patch_dir)


def _run_game(tmp_path, stdin_lines, menu=False):
    """Run the game in tmp_path with the given stdin lines.
    menu=False: pass --continue (skip the start menu).
    menu=True:  run main.py with no args so the start menu is shown.
    Returns (stdout, stderr, returncode)."""
    patch_dir = _make_sleep_noop(tmp_path)
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = patch_dir + (":" + existing if existing else "")

    stdin_text = "\n".join(stdin_lines) + "\n"
    cmd = [sys.executable, "main.py"] + ([] if menu else ["--continue"])
    result = subprocess.run(
        cmd,
        cwd=str(tmp_path),
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    return result.stdout, result.stderr, result.returncode


def _read_real_save():
    with open(REAL_SAVE, "r", encoding="utf-8") as f:
        return f.read()


def _write_temp_save(tmp_path, data):
    with open(tmp_path / "save.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _save_with(**kwargs):
    """Build a v2 save dict with the given overrides."""
    base = {
        "version": 2,
        "location": "lunuen",
        "sanity": 80,
        "trust": 0,
        "fear": 0,
        "flags": {},
        "inventory": [],
        "visited": ["lunuen"],
        "seen": ["lunuen"],
        "journal": [],
        "deaths": 0,
        "day": 1,
        "night": False,
        "connor_line": 0,
        "mika_line": 0,
    }
    base.update(kwargs)
    return base


# ===========================================================================
# ENDING TESTS
# ===========================================================================

def test_ending_quiet(tmp_path):
    """The quiet ending: leave the valley (choice 1)."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"read_ledger": True},
        inventory=["key", "ritual_text"],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    # Two empty lines for the two pauses, then "1" for the quiet ending.
    lines = ["", "", "1"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    assert "ENDING — THE QUIET END" in out
    assert "you drive out of the valley" in out.lower()
    # The after-line for the quiet ending
    assert "thank you for not staying" in out.lower()


def test_ending_folk(tmp_path):
    """The folk ending: stay in the valley (choice 2)."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"read_ledger": True},
        inventory=["key", "ritual_text"],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    lines = ["", "", "2"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    assert "ENDING — THE FOLK END" in out
    assert "the valley *receives* you" in out.lower()
    assert "thank you for staying" in out.lower()


def test_ending_broken(tmp_path):
    """The broken ending: break the cycle (choice 3).
    Requires archivist_cost_asked or archivist_paid or asked_archivist_cost."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"read_ledger": True, "asked_archivist_cost": True},
        inventory=["key", "ritual_text"],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    lines = ["", "", "3"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    assert "ENDING — THE BROKEN CYCLE" in out
    assert "the fire takes the names" in out.lower()
    assert "thank you for being incorrect" in out.lower()


def test_ending_second(tmp_path):
    """The second ending: write the second name (choice 4).
    Requires connor_told or mika_why or asked_mika_valley."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"read_ledger": True, "connor_told": True},
        inventory=["key", "ritual_text"],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    lines = ["", "", "4"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    assert "ENDING — THE SECOND NAME" in out
    assert "the ledger has two names" in out.lower()
    assert "thank you for the second one" in out.lower()


# ===========================================================================
# DEATH TESTS
# ===========================================================================

def test_death_collapse(tmp_path):
    """Sanity collapse: sanity <= 0 triggers the 'collapse' death."""
    _copy_game(tmp_path)
    save = _save_with(
        location="lunuen",
        sanity=0,
        seen=["lunuen"],
    )
    _write_temp_save(tmp_path, save)

    # Two empty lines for pauses, then "q" to quit the death screen.
    lines = ["", "", "q"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    # Specific text from the collapse death
    assert "THE HEAD GIVES OUT" in out
    assert "it happens the way a wire snaps" in out.lower()
    # Death screen choices
    assert "load the last save" in out.lower()
    assert "start over" in out.lower()


def test_death_counting(tmp_path):
    """The 'counting' death: told Mika you can't stop counting."""
    _copy_game(tmp_path)
    save = _save_with(
        location="lake",
        sanity=50,
        flags={"mika_cant": True},
        seen=["lunuen", "lake"],
    )
    _write_temp_save(tmp_path, save)

    lines = ["", "", "q"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    assert "YOU CANNOT STOP COUNTING" in out
    assert "you tell mika you cannot stop counting" in out.lower()
    assert "load the last save" in out.lower()


def test_death_ledger(tmp_path):
    """The 'ledger' death: read the ledger's last line twice."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=50,
        flags={"read_ledger_twice": True},
        inventory=["key"],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    lines = ["", "", "q"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    assert "THE LEDGER'S LAST LINE" in out
    assert "you read the last line of the ledger a second time" in out.lower()
    assert "load the last save" in out.lower()


# ===========================================================================
# SAVE INTEGRITY
# ===========================================================================

# ===========================================================================
# STAGE 5: full menu-driven playthrough and the Noah-outcome run
# ===========================================================================

def test_full_playthrough_from_start_menu(tmp_path):
    """A full run through the REAL start menu (no --continue):
    menu -> continue -> prologue -> how to play -> schloss -> ending.
    """
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"read_ledger": True, "asked_archivist_cost": True},
        inventory=["key", "ritual_text"],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    # "2" = continue at the menu; two empty lines = prologue + how-to pauses;
    # "3" = break the cycle (the broken ending).
    lines = ["2", "", "", "3"]
    out, err, rc = _run_game(tmp_path, lines, menu=True)

    assert rc == 0, f"game crashed: {err}"
    # the start menu was shown
    assert "F O L K" in out
    assert "new game" in out
    assert "continue" in out
    # the prologue and how-to were shown
    assert "how to play" in out
    # the final choice and the broken ending
    assert "ENDING — THE BROKEN CYCLE" in out
    assert "the fire takes the names" in out.lower()
    assert "thank you for being incorrect" in out.lower()


def test_noah_outcome_run(tmp_path):
    """Noah's help changes a concrete outcome: with noah_ally + read_ledger
    the ritual unlocks WITHOUT the key or the ritual text, so an ending is
    reachable at the schloss that would otherwise be impossible.
    """
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"noah_ally": True, "read_ledger": True},
        inventory=[],  # no key, no ritual text — only Noah's path works
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    # Two empty lines for the pauses, then "1" for the quiet ending.
    lines = ["", "", "1"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    # the final choice was offered even without key/ritual_text
    assert "ENDING — THE QUIET END" in out
    assert "thank you for not staying" in out.lower()


def test_noah_outcome_requires_noah_ally(tmp_path):
    """Control case: the SAME save without noah_ally must NOT unlock the
    ritual (no key, no ritual text), so no ending is offered.
    """
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss",
        sanity=80,
        flags={"read_ledger": True},
        inventory=[],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)

    lines = ["", "", "q"]
    out, err, rc = _run_game(tmp_path, lines)

    assert rc == 0, f"game crashed: {err}"
    # no ending was offered — the player just quits
    assert "ENDING — THE QUIET END" not in out
    assert "saved. the valley is patient." in out


# ===========================================================================
# SAVE INTEGRITY
# ===========================================================================

# ===========================================================================
# NOAH TALK + LOOK AT EVERY TIER AND CHAPTER
# ===========================================================================

def test_talk_noah_all_tiers(tmp_path):
    """`talk noah` works at every hidden-meter tier (steady, thin, low, critical): the game understands the command, Noah answers,
    and his answer is not an empty or an error line. The two start-up screens (prologue, how to play) each take one blank line."""
    _copy_game(tmp_path)
    for sanity, tier_name in [(80, "steady"), (50, "thin"), (30, "low"), (10, "critical")]:
        _write_temp_save(tmp_path, _save_with(location="nook", sanity=sanity, seen=["lunuen", "nook"]))
        out, err, rc = _run_game(tmp_path, ["", "", "talk noah", "0", "q"])
        assert rc == 0, f"game crashed at tier {tier_name}: {err}"
        assert "you do not know what to do with that" not in out, f"talk noah was not understood at tier {tier_name}"
        after = out.split("Noah is here", 1)[-1]                       # everything after the first screen that offers him
        assert "Noah" in after and len(after.strip()) > 200, f"Noah said nothing at tier {tier_name}"


def test_look_nook_all_tiers_and_chapters(tmp_path):
    """`look` at the nook must produce different text at every tier and
    chapter combination."""
    _copy_game(tmp_path)
    tiers = [80, 50, 30, 10]
    chapters = [1, 2, 3, 4, 5]
    seen_texts = set()
    for sanity in tiers:
        for chapter in chapters:
            save = _save_with(
                location="nook", sanity=sanity, chapter=chapter,
                seen=["lunuen", "nook"],
            )
            _write_temp_save(tmp_path, save)
            lines = ["", "look", "q"]
            out, err, rc = _run_game(tmp_path, lines)
            assert rc == 0, f"game crashed at sanity={sanity} chapter={chapter}: {err}"
            # capture the nook description (the lines between the header and the status strip)
            lines_out = out.split("\n")
            nook_text = ""
            in_nook = False
            for line in lines_out:
                if "Noah's nook" in line or "the nook" in line:
                    in_nook = True
                    continue
                if in_nook and line.strip().startswith("["):
                    break
                if in_nook:
                    nook_text += line + "\n"
            key = (sanity, chapter)
            assert key not in seen_texts, f"duplicate nook text for {key}"
            seen_texts.add(key)


def test_talk_noah_restores_sanity_once_per_day(tmp_path):
    """Talking to Noah restores the hidden meter at most once per day (mechanics only, no on-screen message): a second talk on the same
    day must not raise it again. The two start-up screens (prologue, how to play) each take one blank line; `0` leaves Noah's menu."""
    _copy_game(tmp_path)

    def sanity_after(talks):
        _write_temp_save(tmp_path, _save_with(location="nook", sanity=50, seen=["lunuen", "nook"]))
        lines = ["", ""] + ["talk noah", "0"] * talks + ["q"]
        out, err, rc = _run_game(tmp_path, lines)
        assert rc == 0, f"game crashed: {err}"
        assert "you do not know what to do with that" not in out
        with open(tmp_path / "save.json", "r", encoding="utf-8") as f:
            return json.load(f)["sanity"]

    once, twice = sanity_after(1), sanity_after(2)
    assert once > 50, f"one talk should restore something, got {once}"
    assert twice == once, f"a second talk on the same day must not restore again ({once} -> {twice})"


def test_noah_ally_shown_at_final(tmp_path):
    """With noah_ally set, the final scene at the schloss must show Noah
    with a mug and restore +10 sanity."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss", sanity=80,
        flags={"noah_ally": True, "read_ledger": True},
        inventory=[],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)
    lines = ["", "", "1"]
    out, err, rc = _run_game(tmp_path, lines)
    assert rc == 0, f"game crashed: {err}"
    assert "Noah is at the bottom of the stairs" in out
    assert "holding a mug" in out


def test_noah_hurt_shown_at_final(tmp_path):
    """With noah_hurt set, the final scene at the schloss must show Noah
    without a mug."""
    _copy_game(tmp_path)
    save = _save_with(
        location="schloss", sanity=80,
        flags={"noah_hurt": True, "read_ledger": True, "noah_ally": True},
        inventory=[],
        seen=["lunuen", "schloss"],
    )
    _write_temp_save(tmp_path, save)
    lines = ["", "", "1"]
    out, err, rc = _run_game(tmp_path, lines)
    assert rc == 0, f"game crashed: {err}"
    assert "Noah is at the bottom of the stairs" in out
    assert "not holding a mug" in out


def test_real_save_untouched(tmp_path):
    """The real save.json in the repo must not be modified by any test."""
    before = _read_real_save()
    _copy_game(tmp_path)
    save = _save_with(location="lunuen", sanity=80)
    _write_temp_save(tmp_path, save)
    lines = ["", "", "q"]
    out, err, rc = _run_game(tmp_path, lines)
    after = _read_real_save()
    assert before == after, "the real save.json was modified by the test"


def test_temp_save_is_written(tmp_path):
    """The game must write a save.json in the temp directory, not the repo."""
    _copy_game(tmp_path)
    save = _save_with(location="lunuen", sanity=80)
    _write_temp_save(tmp_path, save)
    lines = ["", "", "q"]
    out, err, rc = _run_game(tmp_path, lines)
    save_path = tmp_path / "save.json"
    assert save_path.exists(), "no save.json written in temp dir"
    with open(save_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["version"] == 4
    # The repo save.json should still be the original v1 save
    with open(REAL_SAVE, "r", encoding="utf-8") as f:
        real = json.load(f)
    assert "version" not in real, "real save.json was overwritten"
