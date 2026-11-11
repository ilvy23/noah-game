# noah.py — FOLK: Noah, the balm. He is NOT horror.
# A super-cute tsundere anime boy who turned a bleak clearing into a
# cosy nook. Bossy, flustered, denies caring while caring a lot.
#
# Node format (same as dialogue.py):
#   {"id": str, "text": str, "choices": [(label, next_id_or_None, effects), ...]}
#   effects = {"flag": str, "trust": int, "fear": int, "sanity": int,
#              "learned": str, "decided": str}

from typing import Dict

import context

NL = "\n"


def J(lines):
    return NL.join(lines)


# ===========================================================================
# NOAH_OPEN — four sanity tiers, four completely different little scenes.
#   steady:   proudly setting out tea, bossy
#   thin:     sees you are tired, fusses while claiming he does not care
#   low:      wraps a patched blanket round you, drops half the act
#   critical: one short honest warm sentence, then an immediate cover-up
# ===========================================================================

NOAH_OPEN: Dict[str, str] = {
    "steady": J([
        "He is already standing by the little stove, sleeves rolled up,",
        "holding the kettle like a trophy. The steam curls past his",
        "face and he does not even blink at it.",
        "",
        "  \u201cYou're actually here. Good. I was just about to make",
        "tea and I hate making it alone. Sit down, the bench is",
        "right there. I saved you a spot.\u201d",
        "",
        "He pours two mugs anyway. One of them has a cat on it, and",
        "the cat is looking at you with total confidence.",
        "",
        "  \u201cHere. The cat one is the good one. I mean, it's the",
        "only one with a cat on it. That's not a compliment, it's",
        "just a fact.\u201d",
    ]),
    "thin": J([
        "He is sitting on the bench with his knees up, pretending to",
        "polish a spoon. He has been polishing the same spoon for a",
        "long time. His eyes flick to yours the moment you step in.",
        "",
        "  \u201cYou look tired. Sit down, the tea is already made.",
        "I was going to drink it, but you can have some. You look",
        "like you need it more than I do.\u201d",
        "",
        "He slides the cat mug across the bench without looking at",
        "you. His ears are red. The spoon is still being polished.",
    ]),
    "low": J([
        "He is crouched by the stove, and the moment you appear he",
        "stands up with a blanket in his hands. It is patched in",
        "three places. He wraps it around your shoulders before you",
        "can say a word.",
        "",
        "  \u201cYou're shivering. Here, take this. It's warm and",
        "you need it. Sit down, I'll make you some tea. You look",
        "like you've been out in the rain.\u201d",
        "",
        "He does not look at you while he says it. He is looking at",
        "the kettle. The kettle is doing nothing. His ears are very",
        "red, and the blanket is very warm, and he does not take it",
        "off you.",
    ]),
    "critical": J([
        "He is sitting very still on the bench. He looks up at you",
        "and for one second his face is completely soft, and he",
        "says, very quietly, without any performance at all:",
        "",
        "  \u201cI'm glad you came. I was getting scared you wouldn't.\u201d",
        "",
        "Then his face crumples into a full-blown scowl and he turns",
        "his head away so hard his hair swings.",
        "",
        "  \u201cI mean, it's not like I was waiting for you or",
        "anything. The kettle was just on. That's all. That's the",
        "whole thing.\u201d",
    ]),
}


# ===========================================================================
# NOAH_TREE — 10 nodes. Root is n1.
#   n1  root: what is he doing (tea / why the nook / who is he)
#   n2  tea ritual
#   n3  why he built the nook
#   n4  his backstory, told sideways
#   n5  what he thinks of the valley people
#   n6  comic quarrel
#   n7  the kind path (sets noah_ally)
#   n8  the rude path (sets noah_hurt)
#   n9  leaving (kind)
#   n10 leaving (rude)
# ===========================================================================

NOAH_TREE: Dict[str, dict] = {
    "n1": {
        "id": "n1",
        "text": J([
            "He is standing in the middle of the clearing with his",
            "arms crossed, looking at you the way a cat looks at a",
            "newly delivered box. Suspicious. Interested. Refusing",
            "to admit either.",
            "",
            "  \u201cYou want to talk? Sure. I was just about to",
            "start my afternoon, but go ahead. Ask me something.",
            "I'm not busy. I'm just pretending to be busy.\u201d",
        ]),
        "choices": [
            ("ask about the tea", "n2", {}),
            ("ask why he built the nook", "n3", {}),
            ("ask who he is", "n4", {}),
            ("ask what he thinks of the valley people", "n5", {}),
            ("tease him about the cat mug", "n6", {}),
            ("tell him you're glad he's here", "n7", {}),
            ("mock him for living in a shed", "n8", {}),
        ],
    },
    "n2": {
        "id": "n2",
        "text": J([
            "His face lights up for exactly one second before he",
            "catches himself and crosses his arms.",
            "",
            "  \u201cThe tea. Sure. It's not a big deal. I just",
            "boil the water, pour it, wait. That's it. That's the",
            "whole ritual. You're asking too many questions, you",
            "know that?\u201d",
            "",
            "He is already reaching for the kettle.",
        ]),
        "choices": [
            ("ask why the nook", "n3", {}),
            ("ask who he is", "n4", {}),
            ("tease him about the cat mug", "n6", {}),
            ("tell him you're glad he's here", "n7", {}),
            ("mock him for living in a shed", "n8", {}),
        ],
    },
    "n3": {
        "id": "n3",
        "text": J([
            "He looks at the shed. He looks at the bench. He looks at",
            "the string of paper stars. His jaw tightens.",
            "",
            "  \u201cWhy did I build it? I mean, it's not like I had",
            "a grand plan. The clearing was empty and I wanted it",
            "to not be. So I put a kettle here, then a bench, then",
            "the stars. One thing after the other. That's the whole",
            "story. Yeah, the bench is for sitting. I know what",
            "a bench is for. Stop looking at me like that.\u201d",
            "",
            "He is checking the string of stars with one careful",
            "finger, making sure they are all still hanging.",
        ]),
        "choices": [
            ("ask about the tea", "n2", {}),
            ("ask who he is", "n4", {}),
            ("ask what he thinks of the valley people", "n5", {}),
            ("tease him about the cat mug", "n6", {}),
            ("tell him you're glad he's here", "n7", {}),
            ("mock him for living in a shed", "n8", {}),
        ],
    },
    "n4": {
        "id": "n4",
        "text": J([
            "He stops. He looks at you. He looks at the kettle.",
            "He looks at you again, and his face does something",
            "complicated.",
            "",
            "  \u201cWho am I? You want a name? I'm the guy who",
            "lives in the shed. That's the whole job description.",
            "I mean, I don't have a backstory or anything. I was",
            "here, then I wasn't, then I was again. You're asking",
            "too many questions, you know that?\u201d",
            "",
            "He turns to the stove and stirs the tea with a spoon he",
            "doesn't need to stir with.",
        ]),
        "choices": [
            ("ask about the tea", "n2", {}),
            ("ask why he built the nook", "n3", {}),
            ("ask what he thinks of the valley people", "n5", {}),
            ("tease him about the cat mug", "n6", {}),
            ("tell him you're glad he's here", "n7", {}),
            ("mock him for living in a shed", "n8", {}),
        ],
    },
    "n5": {
        "id": "n5",
        "text": J([
            "He snorts. Then he snorts again, harder, and he has to",
            "turn away because he's laughing.",
            "",
            "  \u201cThe valley people? Connor is a walking cloud.",
            "Mika is arty, like, aggressively arty. And the other",
            "one is so polite it's scary. I'm not being mean about",
            "it. I'm just observing. You wouldn't understand.",
            "",
            "He is grinning. He is trying very hard not to grin.",
            "He is failing.",
        ]),
        "choices": [
            ("ask about the tea", "n2", {}),
            ("ask why he built the nook", "n3", {}),
            ("ask who he is", "n4", {}),
            ("tease him about the cat mug", "n6", {}),
            ("tell him you're glad he's here", "n7", {}),
            ("mock him for living in a shed", "n8", {}),
        ],
    },
    "n6": {
        "id": "n6",
        "text": J([
            "His face goes completely red. He points at you. He",
            "points at the mug. He points at you again.",
            "",
            "  \u201cYou're making fun of the cat? It's not a cat,",
            "it's a design. A very serious design. I didn't choose",
            "it because I like cats, it was on sale. You're the",
            "worst. I'm taking the mug. I'm taking the whole",
            "shelf.\u201d",
            "",
            "He is not taking the shelf. He is holding the mug with",
            "both hands and looking at you with wide, offended eyes.",
        ]),
        "choices": [
            ("apologize and tell him you're glad he's here", "n7", {}),
            ("double down and mock the shed", "n8", {}),
            ("ask about the tea", "n2", {}),
            ("ask who he is", "n4", {}),
        ],
    },
    "n7": {
        "id": "n7",
        "text": J([
            "He goes very quiet. His ears go red. His nose goes red.",
            "His whole face goes red, like a traffic light that has",
            "broken and is stuck on the last colour.",
            "",
            "  \u201cYou're not bad. That's the highest I go.",
            "Sit down, I'll make you another cup. Don't get the",
            "wrong idea, the kettle was already on. I mean, it's",
            "not like I care that you said that. I was going to",
            "say it anyway.\u201d",
            "",
            "He is already pouring. He is pouring too much. The tea",
            "is spilling over the rim and he is not stopping.",
        ]),
        "choices": [
            ("stay a while and drink the tea", None,
             {"flag": "noah_ally", "trust": 10, "sanity": 5,
              "learned": "Noah is a friend. He made the nook because he wanted to.",
              "decided": "told Noah he's glad he's here"}),
            ("say you'll come back tomorrow", "n9",
             {"flag": "noah_ally", "trust": 8, "sanity": 3,
              "learned": "Noah is a friend. He made the nook because he wanted to.",
              "decided": "promised Noah you'll come back"}),
        ],
    },
    "n8": {
        "id": "n8",
        "text": J([
            "He goes very still. His face goes pale. Then it goes",
            "red, but a different red, the kind that means anger",
            "instead of embarrassment.",
            "",
            "  \u201cYou think this is a joke? I didn't build this",
            "for fun. I built it because it was empty and I wanted",
            "it to not be. And you're standing there making fun of",
            "it. You're the worst. I'm not angry, I'm just done.",
            "Go away.\u201d",
            "",
            "He turns his back to you. He is not crying. He is",
            "definitely not crying. His shoulders are shaking a little.",
        ]),
        "choices": [
            ("apologize and tell him you're glad he's here", "n7",
             {"trust": 5, "sanity": 2,
              "decided": "apologized to Noah after mocking him"}),
            ("leave without apologizing", "n10",
             {"flag": "noah_hurt", "trust": -10,
              "decided": "mocked Noah and left without apologizing"}),
        ],
    },
    "n9": {
        "id": "n9",
        "text": J([
            "He is watching you pack up. He is pretending not to",
            "watch you pack up. He is failing at pretending.",
            "",
            "  \u201cYou're leaving already? The tea is still warm.",
            "You can have the rest. Come back when you want. I'll",
            "be here. I'm always here. I mean, the kettle is always",
            "on. That's all.\u201d",
            "",
            "He is holding the cat mug. He is not drinking from it.",
            "He is looking at the door.",
        ]),
        "choices": [
            ("leave", None,
             {"trust": 3, "sanity": 2,
              "decided": "left Noah's nook on good terms"}),
        ],
    },
    "n10": {
        "id": "n10",
        "text": J([
            "He stands at the far end of the bench, arms folded,",
            "and his whole body goes rigid, like a door that has",
            "just been shut.",
            "",
            "  \u201cGo. The door is that way. I'm not mad at",
            "you. I'm just done.\u201d",
            "",
            "He puts the cat mug back on the shelf, one careful",
            "step at a time, and his eyes shine a little as he",
            "does it.",
        ]),
        "choices": [
            ("leave", None,
             {"flag": "noah_hurt", "trust": -5,
              "decided": "left Noah's nook after hurting him"}),
        ],
    },
}


# ===========================================================================
# NOAH_TOPICS — ask topics: tea, worry, shed
# ===========================================================================

NOAH_TOPICS: Dict[str, dict] = {
    "tea": {
        "text": J([
            "He slams the kettle down like it owes him money.",
            "",
            "  \u201cThe tea. Sure. I boil the water until it goes",
            "crazy, then I tip it into the mug. That's the whole",
            "recipe. The cat mug is mine. The other one is also",
            "mine. But you can use it. It's just sitting there.",
            "Don't make it weird.\u201d",
            "",
            "He pours. He pours too much. The tea goes over the rim",
            "and he keeps pouring. His ears are the color of the",
            "biscuits.",
        ]),
        "flag": "asked_noah_tea",
        "learned": "Noah's tea: boil the water, pour it into the mug. The cat mug is his, the other one is his too, but you can use it.",
    },
    "worry": {
        "text": J([
            "He sets the spoon down. He picks it up again. He sets it",
            "down a second time, and this time he leaves it there.",
            "",
            "  \u201cWorry? I don't keep a list or anything. I just",
            "notice. You skip breakfast. You stand in the rain",
            "without a coat. It's not my business. I just see it.",
            "Sit down. The kettle is on. I was making a pot for",
            "myself. There is extra. There is always extra. I mean,",
            "don't make it a thing.\u201d",
            "",
            "He pushes the second mug toward you with one finger.",
            "He does not look up. His ears are the color of the",
            "biscuits on the shelf.",
        ]),
        "flag": "asked_noah_worry",
        "learned": "Noah worries about you. He just won't say it directly.",
    },
    "shed": {
        "text": J([
            "He puts his hands in his pockets. He pulls them out.",
            "He puts them in again. He is thinking very hard.",
            "",
            "  \u201cThe shed? I didn't plan it. I just needed",
            "somewhere to put the kettle. The bench came later.",
            "The stars came even later. The sign came last, and it's",
            "not a statement, it's a warning. The walls have my tea",
            "stains on them. Every one of them is from a different",
            "day.\u201d",
            "",
            "He taps the wall once, gently, like he is checking",
            "that it is still there. It is still there.",
        ]),
        "flag": "asked_noah_shed",
        "learned": "Noah built the nook because the clearing was empty and he wanted it to not be.",
    },
}
# ===========================================================================

NOAH_CHAPTER: Dict[int, str] = {
    1: J([
        "  \u201cYou're new here, right? I'm not surprised. Everyone",
        "looks the same when they first arrive. Sit down. The tea",
        "is already made.\u201d",
    ]),
    2: J([
        "  \u201cYou look tired. I'm not saying this because I care.",
        "I just hate seeing someone waste a perfectly good face.",
        "Sit. The tea is warm.\u201d",
    ]),
    3: J([
        "  \u201cYou've been here a while now. I'm not saying this",
        "because I've been watching the door or anything. The",
        "kettle was just on. That's all. Sit down.\u201d",
    ]),
    4: J([
        "  \u201cYou're still here? I'm not saying this because I was",
        "hoping you'd come back. I was just making tea. The kettle",
        "was already on. Sit. The bench is right there.\u201d",
    ]),
    5: J([
        "  \u201cThis is the last one, right? I'm not saying this",
        "because I'm sad or anything. I was just going to say it",
        "anyway. You're not bad. Sit down. I'll make you",
        "another cup.\u201d",
    ]),
}


# ===========================================================================
# place_text — the ONLY text that describes the nook.
# Grows with trust and chapter. Cold and dull if noah_hurt.
# ===========================================================================

def place_text(s) -> str:
    """Noah's clearing, described from the player's current state.

    The description picks up the player's last interaction (via
    context.ref) so the text is a continuation of what just
    happened, not a standalone line.
    """
    if s.has("noah_hurt"):
        return J([
            "The clearing is empty. The shed door is closed. The",
            "bench is there. The kettle is cold. The stars are",
            "unlit. The mugs are on the shelf. The cat mug is on",
            "the shelf. The blanket is folded. The clearing is",
            "small. The clearing is quiet. The clearing is cold.",
            "The clearing is not waiting for anyone. The clearing",
            "is just a clearing. The shed is just a shed. The",
            "bench is just a bench. The kettle is just a kettle.",
            "The stars are just stars. The mugs are just mugs.",
            "The blanket is just a blanket. The clearing is not",
            "here. The clearing is just there.",
        ])

    parts = []

    # base: always present
    parts.append(J([
        "Past the last row of trees, the forest opens into a small",
        "clearing that someone has clearly been working on. A",
        "shed, no bigger than a garden hut, sits under a canopy of",
        "paper stars on string. The stars are not lit. They are",
        "*ready* to be lit. The shed door is open. Inside: a",
        "kettle, a shelf of mismatched mugs, a cushion that is",
        "a blanket folded into a cushion shape, and",
        "a hand-drawn sign on the wall that says \u201cNOT a",
        "clubhouse!!\u201d in very serious letters.",
    ]))

    parts.append(J([
        "There is a bench outside. The bench is the right size for",
        "two people and the wrong size for one. There is a",
        "snack shelf on the shed wall. The snack shelf has",
        "biscuits. The biscuits are not for you. The biscuits",
        "are *for* you. That is the whole point of the shelf.",
    ]))

    # trust >= 5: the kettle is warm
    if s.trust >= 5:
        parts.append(J([
            "The kettle is warm. It has been warm since you arrived.",
            "The mugs are out. There are two mugs out. One is for",
            "Noah. The other is for you. They were already out.",
        ]))

    # trust >= 15: the stars are lit
    if s.trust >= 15:
        parts.append(J([
            "The paper stars are lit now. They are glowing softly.",
            "The clearing feels smaller. The shed is nearer. The",
            "bench is nearer. The biscuits are nearer. You are",
            "not sure which of those is the comforting one.",
        ]))

    # trust >= 30: the cat mug is on the bench
    if s.trust >= 30:
        parts.append(J([
            "The cat mug is on the bench. The cat is the best",
            "kind of welcome. The blanket is unrolled. The",
            "blanket is warm. The blanket is a hug. The blanket",
            "is Noah. The blanket is the best kind of hug.",
        ]))

    # chapter 2: the snack shelf has more
    if s.chapter >= 2:
        parts.append(J([
            "The snack shelf has more biscuits now. There are",
            "cookies. There are crackers. There is a jar of",
            "jam. The jam is for you. The jam was always for you.",
            "This is the jam's whole purpose.",
        ]))

    # chapter 3: the bench has a cushion
    if s.chapter >= 3:
        parts.append(J([
            "The bench has a cushion now. The cushion is a blanket",
            "folded to look like a cushion. The cushion is warm.",
            "The cushion is soft. The cushion is the best kind of",
            "cushion.",
        ]))

    # chapter 4: the stars are more
    if s.chapter >= 4:
        parts.append(J([
            "There are more stars now. The string is longer. The",
            "stars are brighter. The stars are *ready* to be lit.",
            "The stars are waiting. The stars are Noah. The stars",
            "are the best kind of stars.",
        ]))

    # chapter 5: the shed has a window
    if s.chapter >= 5:
        parts.append(J([
            "The shed has a window now. The window is small. The",
            "window is bright. The window is a door. The window",
            "is Noah. The window is the best kind of window. The",
            "window is open. The window is warm. The window is",
            "the best kind of warm.",
        ]))

    # Pick up the player's last interaction, so the description is a
    # continuation of what just happened instead of a standalone line.
    prev = context.ref(s)
    if prev:
        parts.insert(0, f"  (you {prev}; the clearing is still here.)")
    return NL.join(parts)


# ===========================================================================
# HINTS — the `hint` command. Noah gives one short, in-character nudge
# about what to do next, based on the current state.
#
# Rules:
#   * deterministic: same state → same hint (no randomness)
#   * tsundere/warm: every hint carries at least one of the voice markers
#     ("tch", "listen", "idiot", "fine", "not like")
#   * never spoils: no ending names ("quiet", "broken", "second", "paid"),
#     no "the ending", no "the last name", no "the blank space", no
#     "the ledger has your name" — even in critical states
# ===========================================================================

def hint(s) -> str:
    """Return one short hint from Noah for the player's current situation.

    The hint is chosen by a fixed priority list over the state, so it is
    fully deterministic. It never names an ending or reveals what the
    final choice is — it only points at the next concrete step.
    """
    # 1. danger: sanity is low — go to Noah, the one safe place
    if s.sanity < 25:
        return ("tch. you look like you're about to fall over. "
                "listen — come to the clearing. the tea is already made. "
                "i was not waiting for you. the kettle was just on.")

    # 2. danger: sanity is thin — same advice, softer
    if s.sanity < 40:
        return ("fine, you can keep going out there. but listen — "
                "the clearing is close, and the bench is the right size "
                "for two. that's not an invitation. it's a fact.")

    # 3. the ritual is ready — point at the hill without naming what waits
    if story_ritual_ready(s):
        return ("tch. you have everything you need now. "
                "the hill is the next step — i'm not saying it's the last. "
                "i'm saying it's next. go. and don't look back at me like "
                "that. i'm not coming. ...unless you ask.")

    # 4. chapter 1: read the letter and talk to someone
    if story_chapter(s) == 1:
        if not s.has("read_letter"):
            return ("listen. there is a letter in the house. read it first. "
                    "i'm not telling you because it matters — i'm telling you "
                    "because you will ask me later and i will be busy.")
        return ("tch. you read the letter. good. now talk to someone — "
                "connor, mika, whoever is standing there. "
                "the valley does not explain itself to people who do not ask.")

    # 5. chapter 2: Connor's story
    if story_chapter(s) == 2:
        return ("fine. connor has something to tell you. "
                "ask him about the dates. i'm not saying it's important. "
                "i'm saying he will stop pretending if you ask twice.")

    # 6. chapter 3: Mika's painting
    if story_chapter(s) == 3:
        return ("tch. mika is at the gymnasium. "
                "ask her about the painting. she will not say it first — "
                "she never does. that's not a hint, that's just how she is.")

    # 7. chapter 4: the archivist and the cost
    if story_chapter(s) == 4:
        if not s.has("asked_archivist_cost"):
            return ("listen. the archivist keeps the key, and the key keeps "
                    "the cost. ask him about the cost before you go anywhere "
                    "else. i'm not worried. i'm just stating the sequence.")
        return ("tch. you asked about the cost. good. "
                "now read the ledger in the schloss. "
                "i'm not saying it will change your mind. "
                "i'm saying it will change what you know.")

    # 8. chapter 5 / fallback: the hill is ready or the week is almost over
    if s.day >= 6:
        return ("fine. the week is almost over and you are still here. "
                "listen — the hill is the next step. "
                "i'm not saying it's the last one. i'm saying it's next. "
                "go. and the tea is still warm if you come back.")
    return ("tch. you're standing there. "
            "listen — the clearing is close, and the bench is the right "
            "size for two. that's not an invitation. it's a fact. "
            "and the tea is already made. i was not waiting for you.")


def story_chapter(s) -> int:
    """Current chapter number (1..5), read from the story module."""
    import story
    return story.current_chapter(s)


def story_ritual_ready(s) -> bool:
    """Whether the final step is unlocked, read from the story module."""
    import story
    return story.ritual_unlocked(s)


import texts as _texts  # noqa: E402  (text/*.md overrides the defaults above)
_texts.apply(__name__)
