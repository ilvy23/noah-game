# locations.py — FOLK: the six connected places, their items, and their exits.
# (join style: each visual line is one list element, joined with a real newline
#  at runtime — this keeps the source clean and avoids fragile \n escaping.)
from typing import Dict, List, Tuple

import story

NL = "\n"

Exit = Tuple[str, str, str]  # verb, target id, hint


def J(lines):
    return NL.join(lines)


CHAPTER_LINES: Dict[str, Dict[int, str]] = {
    "lunuen": {
        1: J([
            "The town is quiet. The streetlights are on. The bakery has",
            "bread. The butcher has bread. The pharmacy has bread. You",
            "are not sure which shop you walked into. You are not sure",
            "you walked into a shop.",
        ]),
        2: J([
            "The town is quiet. The streetlights are on. The bakery has",
            "bread. The butcher has bread. The pharmacy has bread. You",
            "are not sure which shop you walked into. You are not sure",
            "you walked into a shop. The town is counting. You can hear",
            "it in the walls. It is not a sound. It is a *rhythm*.",
        ]),
        3: J([
            "The town is quiet. The streetlights are on. The bakery has",
            "bread. The butcher has bread. The pharmacy has bread. You",
            "are not sure which shop you walked into. You are not sure",
            "you walked into a shop. The town is counting. You can hear",
            "it in the walls. It is not a sound. It is a *rhythm*. The",
            "rhythm is your name.",
        ]),
        4: J([
            "The town is quiet. The streetlights are on. The bakery has",
            "bread. The butcher has bread. The pharmacy has bread. You",
            "are not sure which shop you walked into. You are not sure",
            "you walked into a shop. The town is counting. You can hear",
            "it in the walls. It is not a sound. It is a *rhythm*. The",
            "rhythm is your name. The name is the cost. The cost is the",
            "name.",
        ]),
        5: J([
            "The town is quiet. The streetlights are on. The bakery has",
            "bread. The butcher has bread. The pharmacy has bread. You",
            "are not sure which shop you walked into. You are not sure",
            "you walked into a shop. The town is counting. You can hear",
            "it in the walls. It is not a sound. It is a *rhythm*. The",
            "rhythm is your name. The name is the cost. The cost is the",
            "name. The name is finished. It is not a draft.",
        ]),
    },
    "house": {
        1: J([
            "The house is quiet. The kettle is warm. The chair is facing",
            "the window. The wallpaper shows a street. Not your street.",
            "Not any street. The houses in it are the right shape but the",
            "doors are all closed and the windows are all lit and there",
            "is no one in any of them and the street goes on and on and",
            "on and you cannot find where it ends.",
        ]),
        2: J([
            "The house is quiet. The kettle is warm. The chair is facing",
            "the window. The wallpaper shows a street. Not your street.",
            "Not any street. The houses in it are the right shape but the",
            "doors are all closed and the windows are all lit and there",
            "is no one in any of them and the street goes on and on and",
            "on and you cannot find where it ends. The street is the",
            "valley. The valley is the street. The street is you.",
        ]),
        3: J([
            "The house is quiet. The kettle is warm. The chair is facing",
            "the window. The wallpaper shows a street. Not your street.",
            "Not any street. The houses in it are the right shape but the",
            "doors are all closed and the windows are all lit and there",
            "is no one in any of them and the street goes on and on and",
            "on and you cannot find where it ends. The street is the",
            "valley. The valley is the street. The street is you. You",
            "are the street. The street is the valley.",
        ]),
        4: J([
            "The house is quiet. The kettle is warm. The chair is facing",
            "the window. The wallpaper shows a street. Not your street.",
            "Not any street. The houses in it are the right shape but the",
            "doors are all closed and the windows are all lit and there",
            "is no one in any of them and the street goes on and on and",
            "on and you cannot find where it ends. The street is the",
            "valley. The valley is the street. The street is you. You",
            "are the street. The street is the valley. The valley is",
            "finished. It is not a draft.",
        ]),
        5: J([
            "The house is quiet. The kettle is warm. The chair is facing",
            "the window. The wallpaper shows a street. Not your street.",
            "Not any street. The houses in it are the right shape but the",
            "doors are all closed and the windows are all lit and there",
            "is no one in any of them and the street goes on and on and",
            "on and you cannot find where it ends. The street is the",
            "valley. The valley is the street. The street is you. You",
            "are the street. The street is the valley. The valley is",
            "finished. It is not a draft. The last name on the page is",
            "yours. It is finished. It is not a draft.",
        ]),
    },
    "forest": {
        1: J([
            "The forest is quiet. The trees are old. The paths loop. You",
            "have walked this path before. You will walk it again. The",
            "trees are not hostile. They are *correct* the way the town",
            "is correct. They are where they are supposed to be. You",
            "are not.",
        ]),
        2: J([
            "The forest is quiet. The trees are old. The paths loop. You",
            "have walked this path before. You will walk it again. The",
            "trees are not hostile. They are *correct* the way the town",
            "is correct. They are where they are supposed to be. You",
            "are not. The trees are counting. You can hear it in the",
            "bark. It is not a sound. It is a *rhythm*.",
        ]),
        3: J([
            "The forest is quiet. The trees are old. The paths loop. You",
            "have walked this path before. You will walk it again. The",
            "trees are not hostile. They are *correct* the way the town",
            "is correct. They are where they are supposed to be. You",
            "are not. The trees are counting. You can hear it in the",
            "bark. It is not a sound. It is a *rhythm*. The rhythm is",
            "your name.",
        ]),
        4: J([
            "The forest is quiet. The trees are old. The paths loop. You",
            "have walked this path before. You will walk it again. The",
            "trees are not hostile. They are *correct* the way the town",
            "is correct. They are where they are supposed to be. You",
            "are not. The trees are counting. You can hear it in the",
            "bark. It is not a sound. It is a *rhythm*. The rhythm is",
            "your name. The name is the cost. The cost is the name.",
        ]),
        5: J([
            "The forest is quiet. The trees are old. The paths loop. You",
            "have walked this path before. You will walk it again. The",
            "trees are not hostile. They are *correct* the way the town",
            "is correct. They are where they are supposed to be. You",
            "are not. The trees are counting. You can hear it in the",
            "bark. It is not a sound. It is a *rhythm*. The rhythm is",
            "your name. The name is the cost. The cost is the name. The",
            "name is finished. It is not a draft.",
        ]),
    },
    "lake": {
        1: J([
            "The lake is flat. Not still — *flat*. The water has no",
            "surface in the way you expect a surface to have. It is the",
            "black of a held breath, the black of the back of an",
            "eyelid, the black of the space between two thoughts.",
        ]),
        2: J([
            "The lake is flat. Not still — *flat*. The water has no",
            "surface in the way you expect a surface to have. It is the",
            "black of a held breath, the black of the back of an",
            "eyelid, the black of the space between two thoughts. The",
            "lake is breathing. You can hear it in the water. It is not",
            "a sound. It is a *rhythm*.",
        ]),
        3: J([
            "The lake is flat. Not still — *flat*. The water has no",
            "surface in the way you expect a surface to have. It is the",
            "black of a held breath, the black of the back of an",
            "eyelid, the black of the space between two thoughts. The",
            "lake is breathing. You can hear it in the water. It is not",
            "a sound. It is a *rhythm*. The rhythm is your name.",
        ]),
        4: J([
            "The lake is flat. Not still — *flat*. The water has no",
            "surface in the way you expect a surface to have. It is the",
            "black of a held breath, the black of the back of an",
            "eyelid, the black of the space between two thoughts. The",
            "lake is breathing. You can hear it in the water. It is not",
            "a sound. It is a *rhythm*. The rhythm is your name. The",
            "name is the cost. The cost is the name.",
        ]),
        5: J([
            "The lake is flat. Not still — *flat*. The water has no",
            "surface in the way you expect a surface to have. It is the",
            "black of a held breath, the black of the back of an",
            "eyelid, the black of the space between two thoughts. The",
            "lake is breathing. You can hear it in the water. It is not",
            "a sound. It is a *rhythm*. The rhythm is your name. The",
            "name is the cost. The cost is the name. The name is",
            "finished. It is not a draft.",
        ]),
    },
    "schloss": {
        1: J([
            "The schloss is a ruin. Foundation walls only, stone the",
            "color of the lake at dawn, going down into the hill in a",
            "way that does not match any building you have seen. The",
            "hill is not under the schloss. The schloss is under the",
            "hill. They are the same thing, viewed from two different",
            "sides.",
        ]),
        2: J([
            "The schloss is a ruin. Foundation walls only, stone the",
            "color of the lake at dawn, going down into the hill in a",
            "way that does not match any building you have seen. The",
            "hill is not under the schloss. The schloss is under the",
            "hill. They are the same thing, viewed from two different",
            "sides. The schloss is counting. You can hear it in the",
            "stone. It is not a sound. It is a *rhythm*.",
        ]),
        3: J([
            "The schloss is a ruin. Foundation walls only, stone the",
            "color of the lake at dawn, going down into the hill in a",
            "way that does not match any building you have seen. The",
            "hill is not under the schloss. The schloss is under the",
            "hill. They are the same thing, viewed from two different",
            "sides. The schloss is counting. You can hear it in the",
            "stone. It is not a sound. It is a *rhythm*. The rhythm is",
            "your name.",
        ]),
        4: J([
            "The schloss is a ruin. Foundation walls only, stone the",
            "color of the lake at dawn, going down into the hill in a",
            "way that does not match any building you have seen. The",
            "hill is not under the schloss. The schloss is under the",
            "hill. They are the same thing, viewed from two different",
            "sides. The schloss is counting. You can hear it in the",
            "stone. It is not a sound. It is a *rhythm*. The rhythm is",
            "your name. The name is the cost. The cost is the name.",
        ]),
        5: J([
            "The schloss is a ruin. Foundation walls only, stone the",
            "color of the lake at dawn, going down into the hill in a",
            "way that does not match any building you have seen. The",
            "hill is not under the schloss. The schloss is under the",
            "hill. They are the same thing, viewed from two different",
            "sides. The schloss is counting. You can hear it in the",
            "stone. It is not a sound. It is a *rhythm*. The rhythm is",
            "your name. The name is the cost. The cost is the name. The",
            "name is finished. It is not a draft.",
        ]),
    },
}


def chapter_line(s, loc_id: str) -> str:
    """Return a short chapter-specific line for the given location.
    Returns "" if there is no line for the current chapter."""
    ch = story.current_chapter(s)
    lines = CHAPTER_LINES.get(loc_id, {})
    return lines.get(ch, "")


ITEMS: Dict[str, dict] = {
    "letter": {
        "name": "the letter from the previous owner",
        "text": J([
            "The seal is old wax, the color of a bruise that healed wrong.",
            "The handwriting is yours. Not like yours. Yours from before.",
            "",
            '  "You will arrive on a Tuesday. It will not be a Tuesday you chose.',
            "   I am not warning you. I am the warning, delivered late.",
            "",
            "   They will tell you the valley is a place. It is not.",
            "   It is a debt. The town pays. The house collects.",
            "",
            "   When the ledger is opened, do not read the last line twice.",
            "   The valley reads you back, one line at a time.",
            "",
            '   — the previous owner"',
        ]),
    },
    "notebook": {
        "name": "Connor\u2019s notebook of dates",
        "text": J([
            "A thin black notebook. The pages are dates, in a hand that",
            "keeps trying to be tidy and keeps failing.",
            "",
            "  03.02  — it was quiet. it is always quiet first.",
            "  09.03  — conor counted the trees on the path. 118.",
            "  09.03  — conor counted the trees on the path. 119.",
            "  11.04  — mika said the lake is breathing. i said yes.",
            "  11.04  — mika said the lake is breathing. i said no.",
            "  14.05  — the gate was open at the schloss. no one was there.",
            "  14.05  — the gate was closed at the schloss. i was there.",
            "  21.06  — do not trust the archivist. he is calm.",
            "  28.06  — the ledger has a name on it. it is not yours.",
            "  28.06  — the ledger has a name on it. it is yours.",
            "",
            "The last page is torn out. The tear is clean. Someone",
            "removed a line they could not live with.",
        ]),
    },
    "painting": {
        "name": "Mika\u2019s unfinished painting",
        "text": J([
            "Oil on canvas, the size of a door. The lake, exactly as it is.",
            "The water is the black of a held breath. The trees are right.",
            "",
            "In the center of the water stands a figure. It is not",
            "reflected. It is *there*. It has the shape of a person the way",
            "a shadow has the shape of a person — suggestion, not fact.",
            "",
            "The figure\u2019s face is not painted. The canvas there is bare,",
            "raw, unpainted — as if the painter looked away.",
            "",
            'In the bottom corner, in small letters: "for whoever',
            'comes next. i left the face out on purpose."',
        ]),
    },
    "key": {
        "name": "the key to the schloss gate",
        "text": J([
            "Iron, older than the gate it opens. The bow of the key is",
            "shaped like a hand with all five fingers spread. The teeth",
            "are cut in a pattern that does not repeat.",
            "",
            "It is warm. Not from the pocket. From itself.",
            "",
            "When you hold it, you can almost hear the gate. It does not",
            "want to be locked. It wants to be *answered*.",
        ]),
    },
    "ledger": {
        "name": "the ledger of the Folk",
        "text": J([
            "A book the size of a hymnal, bound in cloth the color of",
            "lake water at 6am. The pages are thick, cream, and smell of",
            "the forest after rain.",
            "",
            "One name per year. Hundreds of them. All of them local.",
            "All of them people who lived in L\u00fcnen.",
            "",
            "Some years have two names. Those years are circled.",
            "",
            "The last entry: your name. The handwriting is not yours.",
            "The date is this week. The ink is still wet.",
            "",
            "You read the last line.",
            "",
            "You read the last line again.",
            "",
            "The line is different. It is your name, but written",
            "*from the other side of the page*, as if someone pressed",
            "a finger through the paper from the valley side and",
            "wrote it up through the ink.",
            "",
            "The letter told you not to read the last line twice.",
            "You read it twice.",
        ]),
    },
    "ritual_text": {
        "name": "the ritual text — TAL / VOLK / JAHRESRITUAL",
        "text": J([
            "A folder, manila, the tabs worn soft. Inside, typed on a",
            "machine that is no longer made:",
            "",
            "  JAHRESRITUAL — VERFAHREN",
            "",
            "  1. On the night the lake goes flat, the gate of the",
            "     Schloss is opened by the hand it chooses.",
            "",
            "  2. The named person walks to the table. Twelve chairs.",
            "     Eleven are for the town. One is for the valley.",
            "",
            "  3. The town does not eat. The town does not drink.",
            "     The town *watches*. Watching is the payment.",
            "",
            "  4. The valley is fed by being seen. What is seen",
            "     does not leave. What leaves does not stay.",
            "",
            "  5. [REDACTED] — the redaction is in a different hand.",
            "     It is not a redaction. It is a name, crossed out",
            "     so many times the page is worn through.",
            "",
            "  6. The ledger is updated before dawn. The ink is",
            "     never the same color twice.",
            "",
            "  7. If the named person refuses, the valley keeps the",
            "     name. A kept name is heavier than a given one.",
            "",
            "The archivist\u2019s notes in the margin, in his calm hand:",
            '"The valley does not want a sacrifice. It wants a',
            'witness. This is the difference, and it is the problem."',
        ]),
    },
}


LOCATIONS: Dict[str, dict] = {
    # 1. L\u00dcNEN — THE DARK TOWN (hub)
    "lunuen": {
        "name": "L\u00fcnen — the dark town",
        "tag": "the town",
        "base": [
            J([
                "The town of L\u00fcnen is a long, low town that sits in the bottom",
                "of a valley it does not mention. The houses are brick, the",
                "streets are narrow, and the streetlights come on at four",
                "o\u2019clock in the afternoon, every day, whether the sun is out or not.",
            ]),
            J([
                "You know the saying before you\u2019ve heard it. It is on the wall",
                "of the bakery, in the window of the pharmacy, painted in white",
                'on the side of the old water tower: "Das Tal schl\u00e4ft nicht.',
                'Es wartet." The valley doesn\u2019t sleep. It waits.',
            ]),
            J([
                "The people here are not unkind. They are *correct*. They say",
                "good morning with the exact right amount of voice. They do not",
                "ask where you are from. They ask when you arrived, and they",
                "seem to already know the answer, and they seem a little",
                "disappointed that it matches.",
            ]),
        ],
        "thin": [
            J([
                "The shop windows are showing the right things, in the wrong",
                "order. The bakery has bread. The butcher has bread. The",
                "pharmacy has bread. You are not sure which shop you walked",
                "into. You are not sure you walked into a shop.",
            ]),
        ],
        "low": [
            J([
                "The street you are standing in is a street you have walked",
                "before. The houses are the same. The windows are the same.",
                "But the order is different. The town has *rearranged itself*",
                "while you were looking at the sky. It does this. You are",
                "beginning to think it does it on purpose.",
            ]),
        ],
        "exits": [
            ("house", "house", "the house at the end of the street (your house)"),
            ("gymnasium", "gymnasium", "Gymnasium Alt-L\u00fcnen, two streets over"),
            ("forest", "forest", "the Cappenberger forest, at the edge of town"),
            ("lake", "lake", "the Cappenberger lake, across the road"),
            ("schloss", "schloss", "the Cappenberger Schloss, up the hill"),
            ("nook", "nook", "the little clearing with the shed, past the bakery"),
        ],
        "items": [],
        "npc": None,
    },

    # 2. THE HOUSE (Alt-L\u00fcnen)
    "house": {
        "name": "The House — Alt-L\u00fcnen",
        "tag": "the house",
        "base": [
            J([
                "The house is brick like the town, but older. The bricks here",
                "are laid in a pattern you can\u2019t quite name — not herringbone,",
                "not bond, something between. The front door is dark wood,",
                "waxed by someone who is still waxing it.",
            ]),
            J([
                "Inside: a hallway with one coat hook, one coat on it, not",
                "yours. A kitchen with a kettle that is warm. A living room",
                "with a chair facing the window, as if someone was sitting",
                "in it and stood up a moment ago and went outside and came",
                "back inside and is now sitting somewhere else.",
            ]),
            J([
                "The wallpaper in the hallway shows a street. Not your street.",
                "Not any street. The houses in it are the right shape but the",
                "doors are all closed and the windows are all lit and there",
                "is no one in any of them and the street goes on and on and",
                "on and you cannot find where it ends.",
            ]),
        ],
        "thin": [
            J([
                "There is a door in the pantry. It was not there this morning.",
                "It is on the inside of the pantry, which is not where a door",
                "goes. It is black. It does not have a handle. It does not",
                "need one. You can hear the other side of it breathing.",
            ]),
        ],
        "low": [
            J([
                "The house is larger than it was. Not larger — *deeper*. The",
                "hallway goes further than the outside wall allows. The",
                "kitchen has a second window that looks out onto the valley",
                "and the valley is looking back and it is not a reflection",
                "because there is nothing in the valley to reflect.",
            ]),
        ],
        "exits": [("town", "lunuen", "back out into L\u00fcnen")],
        "items": ["letter"],
        "npc": None,
    },

    # 3. CAPPENBERGER FOREST
    "forest": {
        "name": "Cappenberger forest — Cappenberger Berge",
        "tag": "the forest",
        "base": [
            J([
                "The Cappenberger forest starts the way a held breath starts:",
                "quietly, and then suddenly, and then you are already in it",
                "and you don\u2019t remember the first three steps.",
            ]),
            J([
                "The trees are old. Not old like \u201cplanted a long time ago.\u201d",
                "Old like *they were here before the idea of a forest was",
                "needed to describe them*. They grow in circles. Not clusters.",
                "Circles. Perfect, slow, patient circles.",
            ]),
            J([
                "The paths loop. You have walked this path before. You will",
                "walk it again. The trees are not hostile. They are *correct*",
                "the way the town is correct. They are where they are supposed",
                "to be. You are not.",
            ]),
            J([
                "There are marks in the bark. Not carvings. *Impressions* —",
                "the shape of a hand, or a face, or something that is neither,",
                "pressed into the wood from the other side. The wood has not",
                "healed around them. It is waiting to.",
            ]),
        ],
        "thin": [
            J([
                "You count the trees on the path. 118. You count them again.",
                "119. You do not count them a third time. The trees are",
                "watching you count. They are not angry. They are *noting it*.",
            ]),
        ],
        "low": [
            J([
                "The forest is not a forest. It is a *mouth*. The trees are",
                "teeth. The paths are the spaces between. You are standing",
                "in the middle of the mouth and the mouth is not closing.",
                "It is *choosing* not to close. It has chosen you, or it has",
                "chosen not to choose you, and the difference is not one",
                "you can live with, in either direction.",
            ]),
        ],
        "exits": [
            ("town", "lunuen", "back to the edge of L\u00fcnen"),
            ("nook", "nook", "the little clearing with the shed, a path off the forest road"),
        ],
        "items": ["notebook"],
        "npc": "connor",
    },

    # 4. CAPPENBERGER LAKE
    "lake": {
        "name": "Cappenberger lake — Cappenberger See",
        "tag": "the lake",
        "base": [
            J([
                "The Cappenberger lake is flat. Not still — *flat*. The water",
                "has no surface in the way you expect a surface to have. It",
                "is the black of a held breath, the black of the back of an",
                "eyelid, the black of the space between two thoughts.",
            ]),
            J([
                "There are no fish. There are no reeds. There are no birds on",
                "the water. There is only the water, and the trees on the far",
                "side, and the sky, and the reflection of the sky, and the",
                "reflection of the trees, and — at 40 and below — the",
                "reflection of something that was there before the sky.",
            ]),
            J([
                "Mika paints here. He has a small canvas, always the same",
                "canvas, and he paints the lake, and the lake is always the",
                "same, and he says \u201cthe valley already happened, we\u2019re just",
                "catching up,\u201d and he says it like it is a comfort, and it",
                "is not, and you can tell he knows it is not, and he says",
                "it again anyway.",
            ]),
        ],
        "thin": [
            J([
                "The water is breathing. Not moving — *breathing*. A slow,",
                "deep, tidal rise and fall that has nothing to do with the",
                "wind. You put your hand in. The water is warm. The water",
                "does not close over your hand. It *holds* it. Gently. Like",
                "a hand holding a hand. Like a hand that has held hands",
                "before.",
            ]),
        ],
        "low": [
            J([
                "You are in the water. You don\u2019t remember getting in. The",
                "water is not wet. It is *present*. It is in the places in",
                "you that water would be in, and it is in the places in you",
                "that water would not be in, and it is not forcing itself.",
                "You are letting it. You have been letting it. You are not",
                "sure which of those two facts is the one that is true.",
            ]),
        ],
        "exits": [("town", "lunuen", "back to L\u00fcnen, across the road")],
        "items": ["painting"],
        "npc": "mika",
    },

    # 5. CAPPENBERGER SCHLOSS
    "schloss": {
        "name": "Cappenberger Schloss — the old castle",
        "tag": "the schloss",
        "base": [
            J([
                "The Cappenberger Schloss is a ruin. Foundation walls only,",
                "stone the color of the lake at dawn, going down into the",
                "hill in a way that does not match any building you have",
                "seen. The hill is not under the schloss. The schloss is",
                "under the hill. They are the same thing, viewed from two",
                "different sides.",
            ]),
            J([
                "The town has kept the gate. The gate is iron, older than the",
                "ruin it stands in front of, and it is locked. The keyhole is",
                "shaped like a hand with all five fingers spread. The gate",
                "does not want to be locked. It wants to be *answered*.",
            ]),
            J([
                "On the night — the ritual night — the gate opens by the hand",
                "it chooses. The town walks up the hill. The town does not",
                "speak. The town does not need to. The town is the payment.",
            ]),
        ],
        "thin": [
            J([
                "The gate is open. It was not open an hour ago. The hinges",
                "are not rusted. They are *polished*. Someone has been",
                "opening and closing this gate, recently, and they are not",
                "the town, because the town does not polish things.",
            ]),
        ],
        "low": [
            J([
                "The schloss is not a ruin. It is a *shell*. The walls are",
                "the outer layer of something that is still in there, still",
                "alive, still *waiting*. The foundations go down further than",
                "the hill is tall. You can hear it down there. It is not",
                "breathing. It is *counting*. It is counting down to a",
                "number that is your name.",
            ]),
        ],
        "exits": [("town", "lunuen", "back down the hill to L\u00fcnen")],
        "items": ["key", "ledger"],
        "npc": None,
    },

    # 6. NOAH'S NOOK — the little clearing with the shed (his place)
    "nook": {
        "name": "Noah's nook — the little clearing",
        "tag": "the nook",
        "base": [
            J([
                "Past the last row of trees, the forest opens into a small",
                "clearing that someone has clearly been working on. A",
                "shed, no bigger than a garden hut, sits under a canopy of",
                "paper stars on string. The stars are not lit. They are",
                "*ready* to be lit. The shed door is open. Inside: a",
                "kettle, a shelf of mismatched mugs, a cushion that is",
                "not a cushion but a blanket folded to look like one, and",
                "a hand-drawn sign on the wall that says \u201cNOT a",
                "clubhouse!!\u201d in very serious letters.",
            ]),
            J([
                "There is a bench outside. The bench is the right size for",
                "two people and the wrong size for one. There is a",
                "snack shelf on the shed wall. The snack shelf has",
                "biscuits. The biscuits are not for you. The biscuits",
                "are *for* you. This is not a contradiction. This is",
                "Noah.",
            ]),
        ],
        "thin": [
            J([
                "The kettle is warm. It has been warm for a while. The",
                "mugs are out. There are two mugs out. One is for",
                "Noah. The other is for you. You did not bring a mug.",
                "Noah did not bring a mug. The mugs are there anyway.",
            ]),
        ],
        "low": [
            J([
                "The paper stars are lit now. You did not light them.",
                "Noah did not light them. They are lit. The clearing is",
                "smaller than it was. Not smaller — *closer*. The shed",
                "is closer. The bench is closer. The biscuits are",
                "closer. You are not sure which of those is the",
                "comforting one.",
            ]),
        ],
        "exits": [
            ("town", "lunuen", "back to L\u00fcnen, past the bakery"),
            ("forest", "forest", "back into the Cappenberger forest"),
        ],
        "items": [],
        "npc": "noah",
    },

    # 7. GYMNASIUM ALT-L\u00dcNEN
    "gymnasium": {
        "name": "Gymnasium Alt-L\u00fcnen",
        "tag": "the school",
        "base": [
            J([
                "The Gymnasium Alt-L\u00fcnen is a long, low building, brick like",
                "the town, with a courtyard that is always exactly the right",
                "size for the number of students in it, which is never the",
                "number you would expect.",
            ]),
            J([
                "The teachers are *aware* in a way they can\u2019t quite express.",
                "They do not say the valley. They say \u201cthe ground.\u201d They say",
                "\u201cthe weather.\u201d They say \u201cthe soil.\u201d They do not say the",
                "valley. They know what the valley is. They are not allowed",
                "to say it. They are not afraid of it. They are *correct*",
                "about it, the way the town is correct about everything.",
            ]),
            J([
                "The art room is where Mika works. The door is unlocked. The",
                "paints are out. The canvas is on the easel. The painting is",
                "the lake. The figure is in the lake. The face is not painted.",
                "It has not been painted in three years. Mika says he is",
                "waiting for the right face. Mika says the right face is",
                "already waiting for him.",
            ]),
            J([
                "The archive is in the basement. The archivist is Mika\u2019s",
                "uncle. He is very calm. He is the calmest person in L\u00fcnen.",
                "He is not calm because he is not afraid. He is calm because",
                "he has already decided what he is going to do, and he has",
                "already done it, and he is just waiting for the rest of the",
                "town to catch up.",
            ]),
        ],
        "thin": [
            J([
                "The corridor is longer than the building. Not longer —",
                "*deeper*. The lockers go on past the outside wall. The",
                "classrooms go on past the outside wall. The school is not",
                "a school. It is a *shell* the way the schloss is a shell.",
                "The students are not students. They are *names* the way the",
                "ledger is names. The school is where the names go to be",
                "read aloud, once a year, in a voice that is not a voice.",
            ]),
        ],
        "low": [
            J([
                "You are in the art room. The door is behind you. The door",
                "is not behind you. The door is *in front of you*, and it has",
                "always been in front of you, and the canvas is not on the",
                "easel, the canvas is on *you*, and the painting is not the",
                "lake, the painting is *you*, and the figure in the lake is",
                "not a figure, the figure is the *shape of you*, and the face",
                "is not unpainted, the face is *your face*, and Mika is",
                "standing behind you, and Mika is not standing behind you,",
                "and Mika is *you*, and the valley is *you*, and the valley",
                "has always been *you*, and the valley is not *you*, and the",
                "valley is *what you will be*, and the valley is *what you",
                "were*, and the valley is *what you are between*.",
            ]),
        ],
        "exits": [("town", "lunuen", "back out into L\u00fcnen")],
        "items": ["ritual_text"],
        "npc": "mika",
        "npc2": "archivist",
    },

}
