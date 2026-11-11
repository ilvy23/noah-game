# -*- coding: utf-8 -*-
"""Achievement and level system for FOLK.

Achievements are defined as a list of dicts:
    {"id": str, "name": str, "condition": str, "check": callable}

`check(s)` returns True when the achievement is earned.
`level(s)` returns 1 + (unlocked // 2).
`check_all(s)` unlocks any newly-earned achievements and prints a line for each.
"""

from engine import render_quiet, C_DIM, C_RESET


# ---------------------------------------------------------------------------
# Achievement definitions
# ---------------------------------------------------------------------------

ACHIEVEMENTS = [
    {
        "id": "first_steps",
        "name": "First Steps",
        "condition": "Visit at least 3 different places",
        "check": lambda s: len(s.visited) >= 3,
    },
    {
        "id": "explorer",
        "name": "Explorer",
        "condition": "Visit every place in the valley",
        "check": lambda s: len(s.visited) >= 6,
    },
    {
        "id": "met_noah",
        "name": "A Friend in the Nook",
        "condition": "Talk to Noah",
        "check": lambda s: s.has("met_noah"),
    },
    {
        "id": "met_connor",
        "name": "The Keeper's Trust",
        "condition": "Talk to Connor",
        "check": lambda s: s.has("met_connor"),
    },
    {
        "id": "met_mika",
        "name": "The Quiet One",
        "condition": "Talk to Mika",
        "check": lambda s: s.has("met_mika"),
    },
    {
        "id": "found_item",
        "name": "Something in Hand",
        "condition": "Find at least one item",
        "check": lambda s: len(s.inventory) >= 1,
    },
    {
        "id": "collector",
        "name": "Collector",
        "condition": "Find at least 3 items",
        "check": lambda s: len(s.inventory) >= 3,
    },
    {
        "id": "survivor_3",
        "name": "Three Days",
        "condition": "Survive to day 3",
        "check": lambda s: s.day >= 3,
    },
    {
        "id": "survivor_5",
        "name": "Five Days",
        "condition": "Survive to day 5",
        "check": lambda s: s.day >= 5,
    },
    {
        "id": "survivor_7",
        "name": "The Full Week",
        "condition": "Reach day 7",
        "check": lambda s: s.day >= 7,
    },
    {
        "id": "ending_quiet",
        "name": "The Quiet Ending",
        "condition": "Reach the quiet ending",
        "check": lambda s: s.flags.get("ending") == "quiet",
    },
    {
        "id": "ending_folk",
        "name": "The Folk Ending",
        "condition": "Reach the folk ending",
        "check": lambda s: s.flags.get("ending") == "folk",
    },
    {
        "id": "ending_broken",
        "name": "The Broken Ending",
        "condition": "Reach the broken ending",
        "check": lambda s: s.flags.get("ending") == "broken",
    },
    {
        "id": "ending_second",
        "name": "The Second Ending",
        "condition": "Reach the second ending",
        "check": lambda s: s.flags.get("ending") == "second",
    },
    {
        "id": "ending_paid",
        "name": "The Paid Ending",
        "condition": "Reach the paid ending",
        "check": lambda s: s.flags.get("ending") == "paid",
    },
    {
        "id": "death_collapse",
        "name": "Collapse",
        "condition": "Die by sanity collapse",
        "check": lambda s: s.flags.get("death_collapse"),
    },
    {
        "id": "death_counting",
        "name": "The Counting",
        "condition": "Die by the counting",
        "check": lambda s: s.flags.get("death_counting"),
    },
    {
        "id": "death_ledger",
        "name": "The Ledger",
        "condition": "Die by the ledger",
        "check": lambda s: s.flags.get("death_ledger"),
    },
    {
        "id": "death_forest",
        "name": "Lost in the Forest",
        "condition": "Die in the forest",
        "check": lambda s: s.flags.get("death_forest"),
    },
    {
        "id": "death_lake",
        "name": "Taken by the Lake",
        "condition": "Die at the lake",
        "check": lambda s: s.flags.get("death_lake"),
    },
    {
        "id": "death_paid",
        "name": "The Archivist's Price",
        "condition": "Pay the archivist and die",
        "check": lambda s: s.flags.get("death_paid"),
    },
    {
        "id": "chapter_3",
        "name": "Into the Deep",
        "condition": "Reach chapter 3",
        "check": lambda s: s.chapter >= 3,
    },
    {
        "id": "chapter_5",
        "name": "The Hill",
        "condition": "Reach chapter 5",
        "check": lambda s: s.chapter >= 5,
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def achievement_ids() -> list:
    """Return all achievement ids in definition order."""
    return [a["id"] for a in ACHIEVEMENTS]


def get_achievement(ach_id: str) -> dict:
    """Return the achievement dict for `ach_id`, or None."""
    for a in ACHIEVEMENTS:
        if a["id"] == ach_id:
            return a
    return None


def unlocked_count(s) -> int:
    """How many achievements are currently unlocked."""
    unlocked = s.flags.get("achievements", [])
    return len(unlocked)


def level(s) -> int:
    """Level = 1 + (unlocked // 2)."""
    return 1 + unlocked_count(s) // 2


def check_all(s) -> list:
    """Check every achievement; unlock any newly-earned ones.

    Prints 'Achievement unlocked: <name>' for each new unlock.
    Returns the list of newly-unlocked achievement ids.
    """
    unlocked = s.flags.setdefault("achievements", [])
    newly = []
    for a in ACHIEVEMENTS:
        if a["id"] in unlocked:
            continue
        try:
            earned = a["check"](s)
        except Exception:
            earned = False
        if earned:
            unlocked.append(a["id"])
            newly.append(a["id"])
            render_quiet(f"\n{C_DIM}Achievement unlocked: {a['name']}{C_RESET}")
    return newly


def list_all(s) -> None:
    """Print all achievements with their unlock status."""
    unlocked = set(s.flags.get("achievements", []))
    render_quiet("")
    render_quiet(f"  Level {level(s)}  —  {len(unlocked)}/{len(ACHIEVEMENTS)} achievements")
    render_quiet("")
    for a in ACHIEVEMENTS:
        mark = "✓" if a["id"] in unlocked else "·"
        render_quiet(f"    {mark}  {a['name']:<28s}  {a['condition']}")
    render_quiet("")


import texts as _texts  # noqa: E402  (text/*.md overrides the defaults above)
_texts.apply(__name__)
