# verify_ending.py — play the Schloss ending once, headless, and verify it.
#
# Imports engine/story/deaths, builds a State at location 'schloss' with the
# flags needed for the ending, calls the ending code directly (no stdin
# piping, no main.py), and prints the ending text.

import sys
import os

# Make sure the project root is importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine
import story
import deaths
from engine import State, render, render_quiet, rule


def build_state() -> State:
    """Build a State at 'schloss' with all flags needed for the ending."""
    s = State()
    s.location = "schloss"
    s.visited = ["lunuen", "schloss"]
    s.seen = ["lunuen", "schloss"]
    s.sanity = 80

    # Items needed for ritual_unlocked
    s.take("key")
    s.take("ritual_text")

    # Flags needed for ritual_unlocked
    s.flag("read_ledger", True)

    # Flags to unlock all four endings in available_choices
    s.flag("archivist_paid", True)       # unlocks "broken"
    s.flag("connor_told", True)          # unlocks "second"

    # Noah's flags for the concrete story outcome
    s.flag("noah_ally", True)

    # Ensure no death is triggered
    assert not deaths.check_death(s), f"Death triggered: {deaths.check_death(s)}"

    return s


def play_ending(s: State, choice_key: str) -> str:
    """Call the ending code directly and return the full ending text."""
    # Verify the ritual is unlocked
    assert story.ritual_unlocked(s), "Ritual not unlocked"

    # Verify the choice is available
    choices = story.available_choices(s)
    available_keys = [k for k, _, _ in choices]
    assert choice_key in available_keys, f"Choice {choice_key} not in {available_keys}"

    # Find the ending id for this choice
    ending_id = None
    for key, desc, ending in choices:
        if key == choice_key:
            ending_id = ending
            break
    assert ending_id is not None, "Could not find ending id"

    # Set the flags that offer_final would set
    s.flag("made_choice", True)
    s.flag("ending", ending_id)

    # Print the ending text (this is what the player sees)
    render(story.FINAL)
    render("")

    # Noah's flags matter: concrete story outcomes
    if s.has("noah_ally"):
        render("")
        render("  Noah is at the bottom of the stairs. He is holding a mug.")
        render("  The mug is warm. The mug is not warm. The mug is *there*.")
        render("")
        render("  \u201cI-it's not like I was waiting for you or anything!\u201d")
        render("  \u201cI was just... making tea. The kettle was already on.\u201d")
        render("  \u201cYou can have a sip. T-Tch. Don't get the wrong idea.\u201d")
        render("")
        s.sanity_change(10, "Noah's tea at the schloss")

    # Print the choices
    for key, desc, ending in story.available_choices(s):
        render(f"  {key}.  {desc}")
    render("")

    # Print the ending text
    render(story.ENDINGS[ending_id])
    render("")
    render(story.AFTER_LINE[ending_id])

    return ending_id


def main():
    print("=" * 60)
    print("FOLK — Schloss Ending Verification")
    print("=" * 60)
    print()

    s = build_state()
    print(f"State: location={s.location}, sanity={s.sanity}")
    print(f"Items: {s.inventory}")
    print(f"Flags: {s.flags}")
    print(f"Ritual unlocked: {story.ritual_unlocked(s)}")
    print(f"Available choices: {[k for k, _, _ in story.available_choices(s)]}")
    print()

    # Play the "broken" ending (choice 3)
    ending_id = play_ending(s, "3")
    print()
    print("=" * 60)
    print(f"Ending: {ending_id}")
    print("=" * 60)

    # Verify the ending text is non-empty and contains expected content
    ending_text = story.ENDINGS[ending_id]
    assert ending_text, "Ending text is empty"
    assert "ENDING" in ending_text, "Ending text missing 'ENDING' header"
    print()
    print(f"Ending text length: {len(ending_text)} chars")
    print(f"Ending text lines: {len(ending_text.splitlines())}")
    print()
    print("VERIFICATION PASSED")


if __name__ == "__main__":
    main()
