# deaths.py — FOLK. The six ways the valley takes you.
#
# Each death has its own text, its own short screen, and the same
# two choices afterwards: load the last save, or start over.
#
# The death check runs at the end of every game-loop round, after
# the player's action has been applied. It returns the id of the
# first matching death, or None if you are still alive.

from typing import Dict

import engine
from engine import (
    render, render_quiet, rule, prompt,
    State, save_game, load_game, save_exists,
)

NL = "\n"


def J(lines):
    return NL.join(lines)


# ---------------------------------------------------------------------------
# The six deaths
# ---------------------------------------------------------------------------

DEATHS: Dict[str, dict] = {
    "collapse": {
        "title": "the head gives out",
        "text": J([
            "It happens the way a wire snaps: quietly, and all at once.",
            "",
            "You are standing somewhere. You know that you are standing",
            "somewhere. You do not know where, or why, or what your name",
            "is. The light is very bright and very far away, and the",
            "valley is very close, and it is not angry. It is patient.",
            "",
            "You have been patient too, for a long time.",
            "",
            "The last thing you understand is that you are still",
            "understanding. The last thing you feel is that you are",
            "still feeling. After that, the valley keeps the rest.",
        ]),
    },
    "ledger": {
        "title": "the ledger's last line",
        "text": J([
            "You read the last line of the ledger a second time.",
            "",
            "The first time, it was a name. The second time, it is yours.",
            "",
            "The ink is still wet. It has always been wet. The archivist",
            "has been writing it for a long time, and he is not in a",
            "hurry, and neither are you, because you are not you anymore.",
            "",
            "You close the book. The book closes. The valley keeps the",
            "difference.",
        ]),
    },
    "counting": {
        "title": "you cannot stop counting",
        "text": J([
            "You tell Mika you cannot stop counting.",
            "",
            "He does not look surprised. He has been counting too,",
            "he says, and he has been counting since before you came,",
            "and he will be counting after you go, and the number is",
            "the same either way.",
            "",
            "You try to stop. You cannot. The number keeps going.",
            "It keeps going. It keeps going.",
            "",
            "Mika puts his hand on your shoulder and says: it is all",
            "right. You do not have to stop. You only have to keep",
            "counting. And you do. And you do. And you do.",
        ]),
    },
    "paid": {
        "title": "the archivist's price",
        "text": J([
            "You pay the archivist what he asks.",
            "",
            "He does not take it from your hand. He takes it from",
            "somewhere else. Somewhere you do not have a name for.",
            "He weighs it in the air, and it is exactly right, and he",
            "nods, and the gate behind him opens, and the gate in",
            "front of you closes, and the valley keeps the difference.",
            "",
            "You try to go back. There is no back. There is only the",
            "archivist, and the ledger, and the light, and the long",
            "quiet of a room that has been waiting for you for a",
            "very long time.",
        ]),
    },
    "forest": {
        "title": "lost in the forest",
        "text": J([
            "You walk into the forest and the forest does not let you",
            "out.",
            "",
            "The trees are the same trees. The path is the same path.",
            "But the path does not go where it used to go, and the trees",
            "do not stand where they used to stand, and the light is",
            "the wrong colour, and the air is the wrong weight, and",
            "you are the wrong person.",
            "",
            "You walk for a long time. You walk for a long time. You",
            "walk for a long time. The forest keeps the difference.",
        ]),
    },
    "lake": {
        "title": "taken by the lake",
        "text": J([
            "You go to the lake and the lake does not let you go.",
            "",
            "The water is very still. It is very still because it is",
            "waiting. It has been waiting for a long time, and it is",
            "not in a hurry, and neither are you, because you are not",
            "you anymore.",
            "",
            "You step in. The water takes you. The lake keeps the",
            "difference.",
        ]),
    },
}


# ---------------------------------------------------------------------------
# The death check
# ---------------------------------------------------------------------------

def check_death(s) -> str:
    """Return a death id if the player has just died, else None.

    Order matters: the first match wins.
    1. sanity collapse — anywhere, any time
    2. read the ledger's last line twice
    3. told Mika you can't stop counting
    4. paid the archivist and are not in the schloss completing it
    5. lost in the forest while your head is thin
    6. taken by the lake while your head is thin
    """
    # 1. sanity collapse — anywhere, any time
    if s.sanity <= 0:
        return "collapse"
    # 2. read the ledger's last line twice
    if s.has("read_ledger_twice"):
        return "ledger"
    # 3. told Mika you can't stop counting
    if s.has("mika_cant"):
        return "counting"
    # 4. paid the archivist and are not in the schloss completing it
    if s.has("archivist_paid") and s.location != "schloss" and not s.has("made_choice"):
        return "paid"
    # 5. lost in the forest while your head is thin
    if s.location == "forest" and s.sanity < 25:
        return "forest"
    # 6. taken by the lake while your head is thin
    if s.location == "lake" and s.sanity < 25:
        return "lake"
    return None


def death_ids():
    return sorted(DEATHS.keys())


# ---------------------------------------------------------------------------
# The death screen
# ---------------------------------------------------------------------------

def _ask(prompt_text: str) -> str:
    """Read one line from the player. EOF (scripted runs) returns 'quit'."""
    try:
        return input(prompt_text).strip().lower()
    except EOFError:
        return "quit"


def death_screen(s, death_id: str) -> None:
    """Print the death text and a short screen, then offer the two choices:
    load the last save, or start over. Returns the new State (or None if the
    player quit to the shell)."""
    d = DEATHS[death_id]
    s.deaths += 1
    s.journal_add("death", f"died: {d['title']}")

    render("")
    rule(60)
    render(f"  {d['title'].upper()}")
    rule(60)
    render("")
    render(d["text"])
    render("")
    rule(60)
    render(f"  you have died {s.deaths} time{'s' if s.deaths != 1 else ''}. the valley keeps the difference.")
    rule(60)
    render("")

    while True:
        render("  what now?")
        render("    1. load the last save")
        render("    2. start over")
        choice = _ask("> ")
        if choice in ("1", "load", "l"):
            if save_exists():
                new_s = load_game()
                render("")
                render("  (loaded a save. the valley remembers you.)")
                return new_s
            render("")
            render("  (no save to load. the valley has forgotten you.)")
        elif choice in ("2", "new", "n", "start"):
            new_s = State()
            render("")
            render("  (starting fresh. the valley has forgotten you.)")
            return new_s
        elif choice in ("q", "quit", "exit"):
            render("")
            render("  (the valley lets you go. for now.)")
            return None
        else:
            render("")
            render("  (the valley does not understand that.)")
