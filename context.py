# context.py — FOLK: a small shared memory of the player's last interaction.
"""Track the player's most recent event, choice, or location so that the
texts in story.py, dialogue.py, locations.py, and noah.py can pick up
what the player just did instead of standing alone.

The memory lives on the State object (``s.context``) so it survives
save/load and is visible to every module. It stores:

  * ``kind``   — what happened: 'talk', 'choice', 'move', 'ask', 'item'
  * ``who``    — the NPC involved (for talk/ask), or ''
  * ``label``  — the exact choice label or topic the player picked
  * ``place``  — the location id the player is now in (or came from)
  * ``text``   — a short human-readable summary, e.g. "told Connor yes"

Texts can call ``context.ref(s)`` to get a one-line reference to the
preceding interaction, or ``context.last(s)`` for the full record.
"""

from typing import Optional


def record(s, kind: str, who: str = "", label: str = "",
           place: str = "", text: str = "") -> None:
    """Store the player's last interaction on the state.

    ``kind`` is one of: 'talk', 'choice', 'move', 'ask', 'item'.
    ``who`` is the NPC id (connor, mika, archivist, noah) or ''.
    ``label`` is the choice label or topic the player picked.
    ``place`` is the location id involved.
    ``text`` is a short summary; if empty it is derived from the rest.
    """
    if not text:
        text = _derive(kind, who, label, place)
    s.context = {
        "kind": kind,
        "who": who,
        "label": label,
        "place": place,
        "text": text,
    }


def last(s) -> Optional[dict]:
    """Return the stored last-interaction record, or None if there is none."""
    return getattr(s, "context", None)


def ref(s) -> str:
    """A short, in-world reference to the preceding interaction.

    Returns '' when there is nothing to refer to (fresh game, first
    action) so callers can simply skip the line.
    """
    rec = last(s)
    if not rec:
        return ""
    return rec.get("text", "")


def who_name(who: str) -> str:
    """Display name for an NPC id ('' stays '')."""
    return {
        "connor": "Connor",
        "mika": "Mika",
        "archivist": "the archivist",
        "noah": "Noah",
    }.get(who, who)


def _derive(kind: str, who: str, label: str, place: str) -> str:
    """Build the summary line when the caller did not provide one."""
    name = who_name(who)
    if kind == "talk":
        return f"talked to {name}" if name else "talked to someone"
    if kind == "choice":
        base = f"told {name}" if name else "told someone"
        return f"{base}: {label}" if label else base
    if kind == "ask":
        base = f"asked {name}" if name else "asked someone"
        return f"{base} about {label}" if label else base
    if kind == "move":
        return f"walked to {place}" if place else "moved"
    if kind == "item":
        return f"picked up {label}" if label else "picked something up"
    return label or kind


def clear(s) -> None:
    """Forget the last interaction (used when a run restarts)."""
    s.context = None


def attach(s) -> None:
    """Make sure the state has a context slot (idempotent).

    Called from State.__init__ and State.from_dict so old saves that
    predate this field still get a working slot.
    """
    if not hasattr(s, "context"):
        s.context = None
