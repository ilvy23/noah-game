"""Title screen tests: the start menu works with stdin, and --continue
still loads a save directly without the menu."""

import json
import os
import shutil
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    "main.py",
    "noah.py",
    "music.py",
    "achievements.py",
]


def _copy_game(tmp_path):
    for name in GAME_FILES:
        shutil.copy2(os.path.join(PROJECT_DIR, name), tmp_path / name)
    return tmp_path


def _make_sleep_noop(tmp_path):
    patch_dir = tmp_path / "_patch"
    patch_dir.mkdir(exist_ok=True)
    (patch_dir / "sitecustomize.py").write_text(
        "import time\ntime.sleep = lambda *a, **kw: None\n"
    )
    return str(patch_dir)


def _run_game(tmp_path, stdin_lines, extra_args=None):
    patch_dir = _make_sleep_noop(tmp_path)
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = patch_dir + (":" + existing if existing else "")

    stdin_text = "\n".join(stdin_lines) + "\n"
    cmd = [sys.executable, "main.py"] + (extra_args or [])
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


def _save_with(**kwargs):
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


def test_title_screen_shows_menu(tmp_path):
    """The title screen shows the ASCII box and the four menu options."""
    _copy_game(tmp_path)
    out, err, rc = _run_game(tmp_path, ["4"])
    assert rc == 0, f"game crashed: {err}"
    assert "F O L K" in out
    assert "new game" in out
    assert "continue" in out
    assert "how to play" in out
    assert "quit" in out
    assert "the valley is patient. thank you for playing." in out


def test_title_screen_new_game(tmp_path):
    """Choosing '1' (new game) starts a fresh game."""
    _copy_game(tmp_path)
    out, err, rc = _run_game(tmp_path, ["1", "", "", "quit"])
    assert rc == 0, f"game crashed: {err}"
    assert "You pull into a street" in out
    assert "how to play" in out
    assert "saved. the valley is patient." in out


def test_title_screen_continue_no_save(tmp_path):
    """Choosing '2' (continue) with no save shows a message and stays in menu."""
    _copy_game(tmp_path)
    out, err, rc = _run_game(tmp_path, ["2", "1", "", "", "quit"])
    assert rc == 0, f"game crashed: {err}"
    assert "no save to continue" in out
    assert "You pull into a street" in out


def test_title_screen_continue_with_save(tmp_path):
    """Choosing '2' (continue) with a save loads it."""
    _copy_game(tmp_path)
    save = _save_with(location="forest", sanity=77)
    with open(tmp_path / "save.json", "w", encoding="utf-8") as f:
        json.dump(save, f)
    out, err, rc = _run_game(tmp_path, ["2", "", "", "quit"])
    assert rc == 0, f"game crashed: {err}"
    assert "loaded a save. the valley remembers you." in out
    assert "You pull into a street" in out


def test_title_screen_how_to_play(tmp_path):
    """Choosing '3' (how to play) shows the help text, then returns to menu."""
    _copy_game(tmp_path)
    out, err, rc = _run_game(tmp_path, ["3", "", "1", "", "", "quit"])
    assert rc == 0, f"game crashed: {err}"
    assert "how to play" in out
    assert "travel" in out
    assert "talk" in out
    assert "ask" in out
    assert "journal" in out
    assert "examine" in out
    assert "status" in out
    assert "quit" in out
    # After how-to-play, the menu should still be available
    assert "new game" in out


def test_continue_flag_skips_menu(tmp_path):
    """--continue loads the save directly without showing the menu."""
    _copy_game(tmp_path)
    save = _save_with(location="lake", sanity=50)
    with open(tmp_path / "save.json", "w", encoding="utf-8") as f:
        json.dump(save, f)
    out, err, rc = _run_game(tmp_path, ["", "", "quit"], extra_args=["--continue"])
    assert rc == 0, f"game crashed: {err}"
    assert "loaded a save. the valley remembers you." in out
    assert "You pull into a street" in out
    # The menu should NOT be shown (the title box is shown but no menu options)
    assert "1.  new game" not in out
    assert "2.  continue" not in out
    assert "3.  how to play" not in out
    assert "4.  quit" not in out


def test_continue_flag_no_save(tmp_path):
    """--continue with no save starts fresh without the menu."""
    _copy_game(tmp_path)
    out, err, rc = _run_game(tmp_path, ["", "", "quit"], extra_args=["--continue"])
    assert rc == 0, f"game crashed: {err}"
    assert "no save. starting fresh." in out
    assert "You pull into a street" in out
    assert "1.  new game" not in out
    assert "2.  continue" not in out


def test_title_box_sides_equal_length(tmp_path):
    """Every line of the title box must have the same visible length,
    so the left and right borders line up."""
    _copy_game(tmp_path)
    out, err, rc = _run_game(tmp_path, ["4"])
    assert rc == 0, f"game crashed: {err}"
    lines = out.split("\n")
    box_lines = [ln for ln in lines if "┌" in ln or "│" in ln or "└" in ln]
    assert len(box_lines) >= 3, f"expected at least 3 box lines, got {len(box_lines)}"
    lengths = set(len(ln) for ln in box_lines)
    assert len(lengths) == 1, (
        f"title box lines have different lengths: {sorted(lengths)}\n"
        + "\n".join(f"  {len(ln):3d}  {ln!r}" for ln in box_lines)
    )
