#!/usr/bin/env python3
"""play_all.py — drive every death and every ending to its text, headless.

Imports engine/story/deaths directly (no piping through main.py).
For each scenario: sets up a State, triggers the check, and prints
  id, first line of its text.
Finally reports which of the 6 deaths and 4 endings are reachable.
"""
import os
import sys

# Make sure we can import the game modules from the project root.
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

import engine
from engine import State
import story
import deaths


def first_line(text: str) -> str:
    """Return the first non-empty line of a multi-line string."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return "(empty)"


def check_death_scenario(death_id: str) -> dict:
    """Build a State that triggers the given death, run check_death,
    and return {id, first_line, reachable}."""
    s = State()
    # Default: sanity high enough to avoid collapse
    s.sanity = 80

    if death_id == "collapse":
        s.sanity = 0
    elif death_id == "ledger":
        s.flag("read_ledger_twice")
    elif death_id == "counting":
        s.flag("mika_cant")
    elif death_id == "paid":
        s.flag("archivist_paid")
        s.location = "lunuen"  # not schloss, no made_choice
    elif death_id == "forest":
        s.location = "forest"
        s.sanity = 20  # < 25
    elif death_id == "lake":
        s.location = "lake"
        s.sanity = 20  # < 25

    result = deaths.check_death(s)
    reachable = (result == death_id)
    text = deaths.DEATHS[death_id]["text"]
    return {
        "id": death_id,
        "first_line": first_line(text),
        "reachable": reachable,
        "triggered": result,
    }


def check_ending_scenario(ending_id: str) -> dict:
    """Build a State that triggers the given ending, run check_ending,
    and return {id, first_line, reachable}."""
    s = State()
    s.sanity = 80

    if ending_id == "quiet":
        # quiet is a choice-based ending (choice 1 in offer_final).
        # It is always available. check_ending does not force it.
        # Reachable via the final choice menu.
        pass
    elif ending_id == "folk":
        # folk is a choice-based ending (choice 2) AND forced when sanity <= 0.
        s.sanity = 0
    elif ending_id == "broken":
        # broken is a choice-based ending (choice 3).
        # Requires archivist_cost_asked / archivist_paid / asked_archivist_cost.
        s.flag("asked_archivist_cost")
    elif ending_id == "second":
        # second is a choice-based ending (choice 4).
        # Requires connor_told / mika_why / asked_mika_valley.
        s.flag("connor_told")

    # For choice-based endings, check_ending won't trigger them directly.
    # Instead, verify they are in available_choices.
    if ending_id in ("quiet", "broken", "second"):
        # These are reachable via the final choice menu if the ritual is unlocked
        # and the gating flags are set.
        s.flag("read_ledger")
        s.take("key")
        s.take("ritual_text")
        s.location = "schloss"
        choices = story.available_choices(s)
        reachable = any(c[2] == ending_id for c in choices)
    else:
        # folk: check_ending forces it when sanity <= 0
        result = story.check_ending(s)
        reachable = (result == ending_id)

    text = story.ENDINGS[ending_id]
    return {
        "id": ending_id,
        "first_line": first_line(text),
        "reachable": reachable,
    }


def main():
    print("=" * 60)
    print("DEATHS (6)")
    print("=" * 60)
    death_ids = sorted(deaths.DEATHS.keys())
    death_results = []
    for did in death_ids:
        r = check_death_scenario(did)
        death_results.append(r)
        status = "REACHABLE" if r["reachable"] else "NOT REACHABLE"
        print(f"  {r['id']:<12} [{status}]  first line: {r['first_line'][:70]}")

    print()
    print("=" * 60)
    print("ENDINGS (4)")
    print("=" * 60)
    ending_ids = sorted(story.ENDINGS.keys())
    ending_results = []
    for eid in ending_ids:
        r = check_ending_scenario(eid)
        ending_results.append(r)
        status = "REACHABLE" if r["reachable"] else "NOT REACHABLE"
        print(f"  {r['id']:<12} [{status}]  first line: {r['first_line'][:70]}")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    reachable_deaths = [r["id"] for r in death_results if r["reachable"]]
    unreachable_deaths = [r["id"] for r in death_results if not r["reachable"]]
    reachable_endings = [r["id"] for r in ending_results if r["reachable"]]
    unreachable_endings = [r["id"] for r in ending_results if not r["reachable"]]

    print(f"  Deaths reachable:    {len(reachable_deaths)}/6  {reachable_deaths}")
    if unreachable_deaths:
        print(f"  Deaths NOT reachable: {unreachable_deaths}")
    print(f"  Endings reachable:   {len(reachable_endings)}/4  {reachable_endings}")
    if unreachable_endings:
        print(f"  Endings NOT reachable: {unreachable_endings}")

    # Check for empty or repeated text
    print()
    print("TEXT INTEGRITY CHECK")
    all_texts = {}
    for r in death_results:
        all_texts[("death", r["id"])] = deaths.DEATHS[r["id"]]["text"]
    for r in ending_results:
        all_texts[("ending", r["id"])] = story.ENDINGS[r["id"]]

    empty = [k for k, v in all_texts.items() if not v.strip()]
    if empty:
        print(f"  EMPTY TEXT: {empty}")
    else:
        print("  No empty texts.")

    seen_texts = {}
    repeated = []
    for k, v in all_texts.items():
        if v in seen_texts:
            repeated.append((k, seen_texts[v]))
        else:
            seen_texts[v] = k
    if repeated:
        print(f"  REPEATED TEXT: {repeated}")
    else:
        print("  No repeated texts.")


if __name__ == "__main__":
    main()
