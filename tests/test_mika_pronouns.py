# tests/test_mika_pronouns.py — regression test: Mika is male.
# Fails if any game file uses she/her/hers/herself/girl/woman/lady in
# a line that also mentions Mika.

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GAME_FILES = [
    "dialogue.py",
    "characters.py",
    "story.py",
    "locations.py",
    "main.py",
    "deaths.py",
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
]

FEMALE_PATTERN = re.compile(
    r"\b(she|her|hers|girl|woman|lady|herself)\b",
    re.IGNORECASE,
)


def test_mika_is_male_in_all_game_files():
    """No game file may use female pronouns in a line that mentions Mika."""
    violations = []
    for fname in GAME_FILES:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                if "Mika" in line and FEMALE_PATTERN.search(line):
                    violations.append(f"{fname}:{lineno}: {line.strip()}")
    assert not violations, "Mika must be male. Female pronouns found:\n" + "\n".join(violations)
