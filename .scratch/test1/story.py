# story.py — FOLK: prologue, act flavor, the ritual night, and the four endings.
from typing import Dict

import context

NL = "\n"
J = NL.join

# ---------------------------------------------------------------------------
# PROLOGUE — plays once, at the very start
# ---------------------------------------------------------------------------
PROLOGUE = J([
    "You pull into a street that is not on any map you have ever used.",
    "",
    "The house is brick, like everything else, but older. The bricks are laid",
    "in a pattern you cannot name — not herringbone, not bond, something",
    "between. The front door is dark wood, waxed by someone who is still",
    "waxing it.",
    "",
    "You inherited this. That is what the paper says. You cannot remember the",
    "name on the paper. You cannot remember the drive. You remember the keys",
    "in your hand, the smell of the forest at the edge of town, and a voice",
    "in the back of your head saying *correct, correct, correct*.",
    "",
    "The valley is behind the house. You can see it from the kitchen window:",
    "a long, low fold of land that the town does not talk about. The lake is in",
    "it. The forest is in it. The old castle is in it. The valley does not",
    "sleep. The valley waits. You know this the way you know your own name.",
    "",
    "On the hallway table, in a seal of wax the color of a bruise that healed",
    "wrong, is a letter. It is addressed to whoever comes next.",
    "",
    "It is addressed to you.",
    "",
    "> look, to begin.",
])

# ---------------------------------------------------------------------------
# CHAPTERS — the five acts of the week, and the objective for each.
# A chapter is unlocked when its `done` flag is set. The objective is
# shown by `journal` and `status`.
# ---------------------------------------------------------------------------

CHAPTERS: Dict[str, dict] = {
    "1": {
        "title": "the letter",
        "objective": "read the letter in the house, then find out who lives in the valley",
        "done_flag": "ch1_done",
    },
    "2": {
        "title": "the count",
        "objective": "talk to Connor in the forest and ask him about the count",
        "done_flag": "ch2_done",
    },
    "3": {
        "title": "the face",
        "objective": "talk to Mika at the lake and ask him about the face in the painting",
        "done_flag": "ch3_done",
    },
    "4": {
        "title": "the cost",
        "objective": "ask the archivist about the cost, then read the ledger in the schloss",
        "done_flag": "ch4_done",
    },
    "5": {
        "title": "the keeping",
        "objective": "go to the schloss with the key, the ritual text, and the ledger read",
        "done_flag": "ch5_done",
    },
}


def current_chapter(s) -> int:
    """Return the first chapter whose done_flag is not set (1..5)."""
    for i in range(1, 6):
        if not s.has(CHAPTERS[str(i)]["done_flag"]):
            return i
    return 5


def chapter_objective(s) -> str:
    """The objective text for the current chapter."""
    ch = current_chapter(s)
    return CHAPTERS[str(ch)]["objective"]


def chapter_title(s) -> str:
    """The title of the current chapter."""
    ch = current_chapter(s)
    return CHAPTERS[str(ch)]["title"]


def chapter_done(s, ch: int) -> bool:
    """True if the given chapter is complete."""
    return s.has(CHAPTERS[str(ch)]["done_flag"])


def chapter_condition_met(s, ch: int) -> bool:
    """True if the current chapter's objective is satisfied.

    The conditions use flags that already exist in the game:
      ch1: read the letter (examine letter) + met someone (connor/mika/archivist)
      ch2: talked to Connor (connor_told or connor_notebook_read)
      ch3: talked to Mika (asked_mika_painting or mika_why)
      ch4: asked the archivist about the cost + read the ledger
      ch5: has key + ritual text + ledger read (ritual_unlocked)
    """
    if ch == 1:
        return (s.has("read_letter")
                and (s.has("met_connor") or s.has("met_mika")
                     or s.has("met_archivist")))
    if ch == 2:
        return (s.has("connor_told") or s.has("connor_notebook_read")
                or s.has("connor_dates_asked"))
    if ch == 3:
        return (s.has("asked_mika_painting") or s.has("mika_why")
                or s.has("asked_mika_valley"))
    if ch == 4:
        return (s.has("asked_archivist_cost") and s.has("read_ledger"))
    if ch == 5:
        return ritual_unlocked(s)
    return False


def advance_chapter(s) -> str:
    """Check if the current chapter's condition is met. If so, set the
    done_flag, advance s.chapter, and return a short in-world message.
    Returns "" if no chapter advanced."""
    ch = current_chapter(s)
    if ch >= 5:
        return ""
    if not chapter_condition_met(s, ch):
        return ""
    s.flag(CHAPTERS[str(ch)]["done_flag"])
    s.chapter = ch + 1
    next_ch = CHAPTERS[str(ch + 1)]
    # Pick up what the player just did, so the chapter turn is not a
    # standalone line but a consequence of the last interaction.
    prev = context.ref(s)
    if prev:
        return (f"\n— the week turns. —\n"
                f"  {prev}. the valley notes it.\n"
                f"  chapter {ch + 1}: {next_ch['title']}\n"
                f"  objective: {next_ch['objective']}")
    return (f"\n— the week turns. —\n"
            f"  chapter {ch + 1}: {next_ch['title']}\n"
            f"  objective: {next_ch['objective']}")


# ---------------------------------------------------------------------------
# ACT FLAVOR — a short line shown when the day advances
# ---------------------------------------------------------------------------
ACT_FLAVOR = {
    1: "Day one. The town is the right shape, in the wrong order.",
    2: "Day two. The shopkeeper says good morning with the exact right amount of voice.",
    3: "Day three. The lake is breathing. You have started to believe it.",
    4: "Day four. Connor says the ledger has your name. Mika says the face is yours.",
    5: "Day five. The gate on the hill was polished today. The valley is close.",
    6: "Day six. The town does not speak. The town does not need to. The town is the payment.",
    7: "Day seven. The night is here. It has always been here.",
}

# ---------------------------------------------------------------------------
# ENDINGS
# ---------------------------------------------------------------------------
ENDINGS = {
    "quiet": J([
        "ENDING — THE QUIET END",
        "",
        "You drive out of the valley before you can explain why you are driving.",
        "The road unwinds. The houses fall behind. The forest falls behind.",
        "You do not look in the rear-view mirror. This is the correct thing to do.",
        "You have learned that there are places where 'correct' is the only word that still means something.",
        "",
        "You get a new job. A new street. A new name on the paper, and this time",
        "you remember it.",
        "",
        "But some nights, when the streetlights come on too early, you look out the window and the valley is there. It is always there. It is in the back of the light. It is in the order of the houses. It is in the exact right amount of voice in every stranger's good morning.",
        "",
        "The valley doesn't sleep. It waits. And it is not angry that you left.",
        "It is patient. It has been patient for longer than your name has been",
        "a name.",
        "",
        "— you left. you did not stay. the valley is still there. —",
    ]),
    "folk": J([
        "ENDING — THE FOLK END",
        "",
        "You stay. Not because you want to. Because *staying* is the shape you",
        "have been, for a while, in a way you cannot point to.",
        "",
        "The valley does not take you. That would be a mistake, and the valley does not make mistakes. The valley *receives* you. The lake holds your hand the way it held the last hand. The forest counts you into the circle, 118, 119, 120. The schloss is under the hill, and the hill is under the schloss, and you are the middle word in a sentence that was written before you had a mouth.",
        "",
        "The ledger is updated before dawn. The ink is never the same color",
        "twice. This year, it is the color of a bruise that healed wrong.",
        "",
        "The town continues. The shopkeeper says good morning. The lake is flat.",
        "The gate is locked. The gate is not locked. It is *answered*.",
        "",
        "Somewhere, a letter is being sealed in wax the color of a bruise that",
        "healed wrong. It is addressed to whoever comes next.",
        "",
        "— the valley is full. the valley is patient. the valley is you. —",
    ]),
    "broken": J([
        "ENDING — THE BROKEN CYCLE",
        "",
        "You hold the ledger up to the fire you did not know you were allowed to light. The pages are thick, cream, and smell of the forest after rain. One name per year. Hundreds of them. All of them local. All of them people who lived in Lünen.",
        "",
        "The last entry is your name. You read it once. You do not read it twice.",
        "",
        "You do not need to. You have the ritual text. You have the key. You have",
        "what the town does not have: the willingness to be *incorrect*.",
        "",
"The fire takes the names. It does not take the valley. That is the part you expected to be harder. The valley does not burn. The valley is not in the paper. The valley is in the *keeping* — in the watching, in the payment, in the correct amount of voice. And the keeping is what the ledger was for. And the keeping is what the fire took.",
        "",
"For the first time in centuries, the valley is *empty*. Not gone. Empty. The lake is still flat. The forest still grows in circles. The schloss is still under the hill. But there is no one to be fed. There is no one to wait for. The valley waits, and there is no one left to wait for, and the waiting is all that is left, and the waiting is not the valley.",
        "",
        "The town does not know what to do with a valley that no one is feeding.",
        "The shopkeeper's good morning is a half second longer than it used to be.",
        "The lake is flat. The lake is still flat. The lake is just water.",
        "",
        "— the cycle is broken. the valley is empty. the valley is patient. the",
        "  valley is waiting for someone who is not you. —",
    ]),
    "second": J([
        "ENDING — THE SECOND NAME",
        "",
        "You reach for the name in the ledger. Not your name. The one that is",
        "blank. The one that is *waiting*.",
        "",
        "You have read Connor's notebook. You have read Mika's journal. You know",
        "what the valley wants. You know what the valley is. You know that the",
        "valley does not want a sacrifice. It wants a *witness*. And you have",
        "been the witness long enough that your name is on the page, and your",
        "name is also *off* the page, in a space that is the shape of a name",
        "that has not been written yet.",
        "",
        "You put your hand in the water. The water holds it. The water has held",
        "hands before. The water is holding two hands now.",
        "",
        "The ledger is updated before dawn. The ink is never the same color twice.",
        "This year, there are two entries. One is your name. The other is blank.",
        "The blank one is in a different hand. It is not a redaction. It is a",
        "name, crossed out so many times the page is worn through.",
        "",
        "You do not know whose name it is. You will know. The blank space is",
        "waiting. The blank space is patient. The blank space is you, and the",
        "blank space is not you, and the difference is not one you can live with,",
        "in either direction.",
        "",
        "The town continues. The lake is flat. The gate is locked. The gate is",
        "answered. And somewhere, in a journal you have read and a notebook you",
        "have read and a letter you have read, a name is being written for the",
        "first time, in a hand that is not yours and a hand that is.",
        "",
        "— the ledger has two names. one is yours. the other is waiting. —",
    ]),
}

# ---------------------------------------------------------------------------
# THE RITUAL — what unlocks the cellar under the schloss, and the climax
# ---------------------------------------------------------------------------

# You need three things before the hill will let you down:
#   the key          (from the Schloss)
#   the ritual text  (from Mika, at the Gymnasium)
#   the ledger read  (the ledger in the Schloss, opened)
def ritual_unlocked(s) -> bool:
    """The cellar under the schloss opens when the player has the key, the
    ritual text, and has read the ledger. Noah's help (noah_ally) also
    unlocks it: he knows the way down, and the gate answers him.
    """
    base = (s.has_item("key")
            and s.has_item("ritual_text")
            and s.has("read_ledger"))
    if base:
        return True
    # Noah's path: he knows the way down even without the full ritual.
    return s.has("noah_ally") and s.has("read_ledger")


def available_choices(s):
    """Which of the four final choices are actually on the table.

    The valley is patient, but it is not generous: some doors only open
    if you have earned them.

      quiet   — always. leaving is the one thing the valley cannot stop.
      folk    — always. staying is the one thing the valley cannot refuse.
      broken  — you must have *seen* the cost. the archivist told you,
                or you asked him, or you paid. otherwise the fire is
                not yours to light.
      second  — you must have *met* the other name. conor told you the
                ledger is not ink, or mika told you the valley wants a
                witness, or you asked mika about the valley. otherwise
                the blank space is just a blank space.
    """
    out = []
    for key, desc, ending in CHOICES:
        if ending == "quiet" or ending == "folk":
            out.append((key, desc, ending))
        elif ending == "broken":
            if (s.has("archivist_paid") or s.has("archivist_cost_asked")
                    or s.has("asked_archivist_cost")):
                out.append((key, desc, ending))
        elif ending == "second":
            if (s.has("connor_told") or s.has("asked_mika_valley")
                    or s.has("mika_why")):
                out.append((key, desc, ending))
    return out


def check_ending(s):
    """Return an ending id if the run has to end now, else None.

    The one forced ending: if your head goes completely empty, the valley
    does not let you keep going. You simply *become* the next line.

    A second one: if you have paid the cost to the archivist and then
    walked away from the schloss, the valley does not let you keep the
    name. it takes it back. this is the only ending that can happen
    *outside* the cellar.
    """
    if s.sanity <= 0:
        return "folk"
    if s.has("archivist_paid") and s.location != "schloss" and not s.has("made_choice"):
        return "paid"
    return None


FINAL = J([
    "The door at the bottom of the stairs is not wood. It is the same",
    "pattern as the bricks on the house — the thing between herringbone and",
    "bond, the pattern you could not name. It is warm. It is warm the way a",
    "door should not be warm, and it is warm in a hand's shape.",
    "",
    "You open it with the key. The key does not turn. The key *settles*.",
    "",
    "Below: a round room. Not carved, not built — grown, the way the forest",
    "grows in circles. The walls are lined with the things the town has",
    "offered over the years, and the offerings are not food, and they are not",
    "gold. They are *attention*. A chair set with a place no one sat in. A",
    "window that looks out on the valley from underneath the hill, so the",
    "lake is a ceiling and the forest is a floor and everything you have ever",
    "seen in Lünen is arranged here like a sentence.",
    "",
    "In the middle of the room, on a plinth of that unnamed brick, is a",
    "writing. It is the ledger. It is the ritual text. They are the same",
    "page, and they have always been the same page.",
    "",
    "One side holds the names that were fed. The other side holds the",
    "instruction for feeding them. The valley has kept both, and the valley",
    "is this room. This room is the keeping. It is the only thing in Lünen",
    "that is not an accident.",
    "",
    "The last name on the page is yours. It is finished. It is not a draft.",
    "",
    "There is a blank space under it. It is the right size for a second name.",
    "",
    "The valley does not ask. It is patient. You have spent a week wrong —",
    "in the exact right amount of voice — and now you can be right.",
])

CHOICES = [
    ("1", "step back out of the room, up the hill, and drive out of the valley before you can explain it",
     "quiet"),
    ("2", "take your place in the circle. become the name the ledger needs. let the lake hold your hand",
     "folk"),
    ("3", "turn the page to the instruction side and refuse to keep it. break the keeping",
     "broken"),
    ("4", "write into the blank space — not your name, the other one, the one that is waiting",
     "second"),
]


# The line shown under each ending, before the game exits.
AFTER_LINE = {
    "quiet": "FOLK — the valley remembers. thank you for not staying.",
    "folk": "FOLK — the ledger has your name. thank you for staying.",
    "broken": "FOLK — the cycle is broken. thank you for being incorrect.",
    "paid": "FOLK — the name is the cost. the cost is the name. thank you for paying.",
    "second": "FOLK — the ledger has two names. thank you for the second one.",
}
