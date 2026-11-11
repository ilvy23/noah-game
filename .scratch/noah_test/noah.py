# noah.py — FOLK: Noah, the balm. He is NOT horror.
# He is a cute tsundere boy who has turned a little clearing into a
# cosy nook. Every line is unique. The narration is warm and funny,
# the way a cosy anime scene is narrated.
#
# Node format (same as dialogue.py):
#   {"id": str, "text": str, "choices": [(label, next_id_or_None, effects), ...]}
#   effects = {"flag": str, "trust": int, "fear": int, "sanity": int,
#              "learned": str, "decided": str}

from typing import Dict

NL = "\n"


def J(lines):
    return NL.join(lines)


# ===========================================================================
# NOAH_OPEN — four sanity tiers, each completely different in what happens.
#   steady:   bright and bossy, he hosts you proudly, flusters when praised
#   thin:     notices you look tired, fusses while pretending not to
#   low:      gentler, wraps a blanket around you, drops half the act
#   critical: ONE short honest warm sentence, then an immediate cover-up
# ===========================================================================

NOAH_OPEN: Dict[str, str] = {
    "steady": J([
        "The clearing smells like chamomile and warm wood. The shed door",
        "is propped open with a flat stone, and the light inside is the",
        "soft yellow of a kitchen at four in the afternoon. A kettle",
        "sits on a little stove, and the steam from it curls up and",
        "disappears into the paper stars strung across the branches.",
        "The stars are not lit. They are waiting. The bench is the right",
        "size for two people, and there is a chipped mug with a cat on",
        "it sitting on the bench, and the cat is facing you, and the",
        "cat is the best kind of welcome.",
        "",
        "Noah is on the bench. He is holding a biscuit. He is not",
        "eating the biscuit. He is holding it the way you hold a",
        "spare umbrella, like a small piece of insurance against the",
        "rest of the world.",
        "",
        "  \u201cOh. Hey. You're the one, right?\u201d",
        "",
        "He says it like a question he has already answered, and then he",
        "looks at the biscuit, and his ears are a little red, and he",
        "says, very quietly, without the performance: \u201cI-it's not like",
        "I was waiting for you or anything. I was just... making tea.",
        "The kettle was already on. I was going to drink it. You can",
        "have a sip. T-Tch. Don't get the wrong idea.\u201d",
    ]),
    "thin": J([
        "The clearing is quiet in the way a library is quiet, not the",
        "way a forest is quiet. The shed door is open. Inside, the",
        "kettle is on, and the steam is doing that slow curling thing",
        "again, and the two mugs are out on the shelf, and the second",
        "mug is the one with the cat on it, and the cat is facing the",
        "door, and the cat has been facing the door for a while.",
        "",
        "Noah is inside the shed. He is making tea. He has been making",
        "tea for a while. The kettle is warm. The mugs are out. There",
        "are two mugs out. One is for Noah. The other is for you. You",
        "did not bring a mug. Noah did not bring a mug. The mugs are",
        "there anyway.",
        "",
        "He sees you and his face does something you will not be able",
        "to describe to an archivist. He looks at your face. He looks",
        "at your shoulders. He looks at the way you are standing, like",
        "you are trying very hard to be a person who is not tired.",
        "",
        "  \u201cYou're early. I-it's not like I was expecting you or",
        "  \u201canything! I was just... making tea. The kettle was already on.",
        "  \u201cI was going to drink it. You can have a sip. T-Tch. Don't",
        "  \u201cget the wrong idea. I-it's not like I'm proud of it or",
        "  \u201cany of that!\u201d",
    ]),
    "low": J([
        "The paper stars are lit now. They are not bright. They are the",
        "soft gold of a street lamp seen through a window, and they",
        "make the clearing look like the inside of a dream you would",
        "want to stay in. The shed door is open. The kettle is on. The",
        "two mugs are out. The second mug is the one with the cat on",
        "it, and the cat is facing the bench, and the bench is warm,",
        "and the bench has been warm for a while, and someone was",
        "sitting here, and someone is still sitting here.",
        "",
        "Noah is on the bench. He is holding a blanket. The blanket is",
        "patched in three places, and the patches are in different",
        "colours, and the colours are the right colours, and the",
        "blanket is the kind of blanket that is not a blanket but a",
        "small weather system you can wrap yourself in. He sees you",
        "and his face does something you will not be able to describe",
        "to an archivist. He does not say anything. He just holds the",
        "blanket out, and the blanket is warm, and the blanket is the",
        "right size for you, and the blanket is not a blanket but a",
        "small weather system you can wrap yourself in.",
        "",
        "  \u201cYou're the new one! I-it's not like I was waiting for you",
        "  \u201cor anything! I was just... sitting. The bench was already",
        "  \u201chere. I was going to sit. You can sit too. T-Tch! Don't",
        "  \u201cget the wrong idea! I-it's not like I'm happy about it or",
        "  \u201canything!\u201d",
    ]),
    "critical": J([
        "The clearing is small. The shed is small. The bench is the",
        "right size for two people and the wrong size for one. The",
        "kettle is on. The steam is doing the slow curling thing. The",
        "mug with the cat on it is on the bench, and the cat is facing",
        "you, and the cat has been facing you for a while, and the cat",
        "is not going to stop facing you, and the cat is the only thing",
        "in the clearing that is not a question.",
        "",
        "Noah is on the bench. He is holding the mug. The mug is warm.",
        "He is not holding it like a weapon. He is holding it like a",
        "shield. He sees you and his face does something you will not",
        "be able to describe to an archivist. For one moment, the",
        "brightness goes out of his eyes, and he is just a boy, and he",
        "is very tired, and he says, very quietly, without the",
        "performance: \u201cI'm scared. I don't know what the valley is. I",
        "don't know what the tea is. I just know that if I stop, the",
        "tea stops, and if the tea stops, I stop.\u201d",
        "",
        "Then the brightness comes back, and he is bright again, and he",
        "says: \u201cEhh? What? I-it's not like I was waiting for you or",
        "anything! I'm Noah! And you are going to be my best friend!",
        "T-Tch! Don't get the wrong idea!\u201d And the kettle is warm, and",
        "the kettle is warm, and that is the whole of it.",
    ]),
}


# ===========================================================================
# NOAH_TREE — the conversation tree. Root id "n1". Flags noah_ally /
# noah_hurt.
# ===========================================================================

NOAH_TREE: Dict[str, dict] = {
    "n1": {
        "id": "n1",
        "text": J([
            "  \u201cEhh? You want to talk? I-it's not like I was waiting for",
            "you or anything! I was just... making tea. The kettle was",
            "already on. I was going to drink it. You can have a sip.",
            "T-Tch. Don't get the wrong idea. So. What do you want to",
            "know? I-it's not like I'm going to tell you everything!",
            "I'm not a *library*!\u201d",
        ]),
        "choices": [
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
            ("ask what he is worried about", "n_worry",
             {"trust": 2, "sanity": 3,
              "learned": "Noah: he is worried about the valley, but he won't say how",
              "decided": "asked Noah what he is worried about"}),
            ("ask about the shed", "n_shed",
             {"trust": 1, "sanity": 2,
              "learned": "Noah: the shed is not a clubhouse, it is a nook",
              "decided": "asked Noah about the shed"}),
        ],
    },
    "n_tea": {
        "id": "n_tea",
        "text": J([
            "You sit down. The bench is the right size for two people and",
            "the wrong size for one. Noah pours the tea. The tea is",
            "warm. The tea is not warm. The tea is *there*. The tea is",
            "the only thing in the clearing that is not a question.",
            "",
            "Noah looks at you and his face does something you will not be",
            "able to describe to an archivist. His ears are red. His",
            "mug is warm. The mug is not warm. The mug is *there*.",
            "",
            "  \u201cT-Tch. Don't get the wrong idea. I-it's not like I'm",
            "  \u201cproud of it or anything! I was just... making tea. The",
            "  \u201ckettle was already on. I was going to drink it. You can",
            "  \u201chave a sip. I-it's not like I'm happy about it or",
            "  \u201canything!\u201d",
        ]),
        "choices": [
            ("thank him and leave", None,
             {"flag": "noah_ally", "trust": 5, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "thanked Noah and left; he is on your side now"}),
            ("ask if he is scared", "n_scared",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: he is scared, but he won't say how",
              "decided": "asked Noah if he is scared"}),
            ("ask what happens if the tea runs out", "n_tea_out",
             {"trust": 2, "sanity": 2,
              "learned": "Noah: the tea doesn't run out, the kettle is always on",
              "decided": "asked Noah what happens if the tea runs out"}),
        ],
    },
    "n_worry": {
        "id": "n_worry",
        "text": J([
            "Noah thinks about this for a long time. The kettle is warm.",
            "The mugs are out. The stars are not lit. The stars are",
            "*ready* to be lit.",
            "",
            "  \u201cI'm not worried,\u201d he says, and his ears are red, and the",
            "kettle is warm, and the mugs are out, and the stars are not",
            "lit, and the stars are *ready* to be lit. \u201cI'm already",
            "inside it. There's a difference. Worried means you're on the",
            "outside looking in. I'm on the inside looking out. The",
            "inside is quieter than I expected. The outside is louder.\u201d",
        ]),
        "choices": [
            ("ask what the inside is like", "n_inside",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: the inside is quieter than he expected",
              "decided": "asked Noah what the inside is like"}),
            ("ask if he is scared", "n_scared",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: he is scared, but he won't say how",
              "decided": "asked Noah if he is scared"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
        ],
    },
    "n_shed": {
        "id": "n_shed",
        "text": J([
            "  \u201cThe shed is not a shed,\u201d Noah says, and he says it the",
            "way you say a cat is not a dog, with the full seriousness",
            "of a person who has been asked this before and is not",
            "enjoying the repeat.",
            "\u201cThe shed is a nook. A nook is not a shed. A nook is a",
            "place where the tea is warm and the bench is the right size",
            "for two people and the wrong size for one. The shed is for",
            "the tea. The tea is for the bench. The bench is for the",
            "nook. The nook is for the valley. The valley is for the",
            "names. The names are for the tea. The tea is for you.\u201d",
        ]),
        "choices": [
            ("ask if the valley is in the tea", "n_valley_tea",
             {"trust": 2, "sanity": 2,
              "learned": "Noah: the valley is in the tea, and the tea is in the valley",
              "decided": "asked Noah if the valley is in the tea"}),
            ("ask if he is scared", "n_scared",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: he is scared, but he won't say how",
              "decided": "asked Noah if he is scared"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
        ],
    },
    "n_scared": {
        "id": "n_scared",
        "text": J([
            "Noah is quiet for a long time. The kettle is warm. The mugs",
            "are out. The stars are not lit. The stars are *ready* to be",
            "lit. He is looking at the bench. The bench is the right size",
            "for two people and the wrong size for one. He is looking at",
            "the empty space where the second person would sit. He is",
            "looking at the space where the second person would sit, and",
            "the space is not empty, and the space is not full, and the",
            "space is *there*.",
            "",
            "  \u201cI'm scared,\u201d he says, and he says it the way he says",
            "everything, like it is a small weather report about a small",
            "storm that is not happening. \u201cI don't know what the valley",
            "is. I don't know what the tea is. I just know that if I",
            "stop, the tea stops, and if the tea stops, I stop.\u201d",
            "He says it like a fact. Like a weather report. Like the",
            "kettle is going to boil over if he doesn't say it out loud.",
            "",
            "Then the brightness comes back, and he is bright again, and",
            "he says: \u201cEhh? What? I-it's not like I was waiting for you or",
            "anything! I'm Noah! And you are going to be my best friend!",
            "T-Tch! Don't get the wrong idea!\u201d And the kettle is warm, and",
            "the kettle is warm, and that is the whole of it.",
        ]),
        "choices": [
            ("ask what happens if he stops", "n_stop",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: if he stops, the tea stops, and if the tea stops, the valley stops",
              "decided": "asked Noah what happens if he stops"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
            ("leave without another word", None,
             {"flag": "noah_hurt", "trust": -3,
              "decided": "left Noah without another word; he will remember it"}),
        ],
    },
    "n_tea_out": {
        "id": "n_tea_out",
        "text": J([
            "  \u201cThe tea doesn't run out,\u201d Noah says, and he says it the",
            "way you say the sun will come up, without checking the",
            "sky, because checking is what other people do.",
            "\u201cThe kettle is always on. The kettle is not a kettle. The",
            "kettle is a *nook*. The nook is for the tea. The tea is for",
            "the bench. The bench is for the nook. The nook is for the",
            "valley. The valley is for the names. The names are for the",
            "tea. The tea is for you.\u201d",
        ]),
        "choices": [
            ("ask if the valley is in the tea", "n_valley_tea",
             {"trust": 2, "sanity": 2,
              "learned": "Noah: the valley is in the tea, and the tea is in the valley",
              "decided": "asked Noah if the valley is in the tea"}),
            ("ask if he is scared", "n_scared",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: he is scared, but he won't say how",
              "decided": "asked Noah if he is scared"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
        ],
    },
    "n_inside": {
        "id": "n_inside",
        "text": J([
            "  \u201cIt's a room,\u201d Noah says, and his voice is very small, and",
            "the kettle is warm, and the mugs are out, and the stars are",
            "not lit, and the stars are *ready* to be lit. \u201cNo walls. A",
            "very old chair. The chair is for the person who is having",
            "tea. The room is for the tea. The tea is for the bench. The",
            "bench is for the nook. The nook is for the valley. The",
            "valley is for the names. The names are for the tea. The tea",
            "is for you.\u201d",
        ]),
        "choices": [
            ("ask if the valley is in the tea", "n_valley_tea",
             {"trust": 2, "sanity": 2,
              "learned": "Noah: the valley is in the tea, and the tea is in the valley",
              "decided": "asked Noah if the valley is in the tea"}),
            ("ask if he is scared", "n_scared",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: he is scared, but he won't say how",
              "decided": "asked Noah if he is scared"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
        ],
    },
    "n_valley_tea": {
        "id": "n_valley_tea",
        "text": J([
            "  \u201cThe valley is in the tea,\u201d Noah says, and he says it the",
            "way you say the kettle is on, which is a fact, not a",
            "feeling, and he is very proud of the difference.",
            "\u201cThe tea is in the valley. The valley is in the names. The",
            "names are in the tea. The tea is in the bench. The bench is",
            "in the nook. The nook is in the shed. The shed is in the",
            "clearing. The clearing is in the forest. The forest is in",
            "the valley. The valley is in the tea. The tea is for you.\u201d",
        ]),
        "choices": [
            ("ask if he is scared", "n_scared",
             {"trust": 3, "sanity": 3,
              "learned": "Noah: he is scared, but he won't say how",
              "decided": "asked Noah if he is scared"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
            ("leave without another word", None,
             {"flag": "noah_hurt", "trust": -3,
              "decided": "left Noah without another word; he will remember it"}),
        ],
    },
    "n_stop": {
        "id": "n_stop",
        "text": J([
            "Noah is quiet for a long time. He is looking at the biscuit",
            "shelf. One, two, three, four. He is not looking at the biscuits.",
            "He is looking at the *shelf*. The shelf is the right size for",
            "four biscuits and the wrong size for five.",
            "",
            "  \u201cIf I stop, the tea stops,\u201d he says, and he says it the way",
            "you say a door is closed, without looking at the door.",
            "\u201cIf the tea stops, the valley stops. If the valley stops, the",
            "names stop. If the names stop, the tea stops. I don't think",
            "that's a metaphor. I think it's a mechanism.\u201d",
        ]),
        "choices": [
            ("ask what happens to the stopped tea", "n_stopped",
             {"trust": 2, "sanity": 2,
              "learned": "Noah: the stopped tea is in the kettle, still warm",
              "decided": "asked Noah what happens to the stopped tea"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
            ("leave without another word", None,
             {"flag": "noah_hurt", "trust": -3,
              "decided": "left Noah without another word; he will remember it"}),
        ],
    },
    "n_stopped": {
        "id": "n_stopped",
        "text": J([
            "  \u201cThe stopped tea is in the kettle,\u201d Noah says, and his voice",
            "is very small, and the kettle is warm, and the mugs are out,",
            "and the stars are not lit, and the stars are *ready* to be",
            "lit. \u201cIt's still warm. It's still running. It's running the",
            "numbers of the people who stopped it. I've seen it in the",
            "water. It looks like handwriting. It looks like your",
            "handwriting.\u201d",
        ]),
        "choices": [
            ("ask if you can stop the stopped tea", "n_stop_it",
             {"trust": 2, "sanity": 2,
              "learned": "Noah: you can't stop the stopped tea, you can only join it",
              "decided": "asked Noah if you can stop the stopped tea"}),
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
            ("leave without another word", None,
             {"flag": "noah_hurt", "trust": -3,
              "decided": "left Noah without another word; he will remember it"}),
        ],
    },
    "n_stop_it": {
        "id": "n_stop_it",
        "text": J([
            "  \u201cYou can't stop it,\u201d Noah says, and his voice is very small,",
            "and the kettle is warm, and the mugs are out, and the stars",
            "are not lit, and the stars are *ready* to be lit. \u201cYou can",
            "only join it. Join is the tea. Out is the kettle. I don't",
            "know which is better. I think they are the same thing. I",
            "think the valley doesn't know either. I think the deciding",
            "is the point.\u201d",
        ]),
        "choices": [
            ("sit down and have tea with him", "n_tea",
             {"trust": 3, "sanity": 5,
              "learned": "Noah: the tea is warm, the bench is the right size for two",
              "decided": "sat down and had tea with Noah"}),
            ("leave without another word", None,
             {"flag": "noah_hurt", "trust": -3,
              "decided": "left Noah without another word; he will remember it"}),
        ],
    },
}


# ===========================================================================
# NOAH_CHAPTER — one line per chapter (1-5), shown after the tier opening.
# ===========================================================================

NOAH_CHAPTER: Dict[int, str] = {
    1: J([
        "  (Noah is still a little wary of you. He has made room for a",
        "  second mug, though. The second mug is the best kind of evidence.)",
    ]),
    2: J([
        "  (The shed has a door now. He built it last week. He says it was",
        "  always there. He is not looking at you when he says it.)",
    ]),
    3: J([
        "  (There are more fairy lights. There is a small shelf of books he",
        "  has clearly read twice. He pretends they are decoration.)",
    ]),
    4: J([
        "  (He has started leaving the kettle on for you. Not *for* you.",
        "  It just *happens* to be on. The mugs are both warm. Both.)",
    ]),
    5: J([
        "  (The sign on the shed has changed. It now says: NOT a",
        "  clubhouse!! (but yours is fine). He will not explain it. He",
        "  will not meet your eyes. The tea is already poured.)",
    ]),
}

# ===========================================================================
# NOAH_TOPICS — the ask topics. Same format as ASK_TOPICS["noah"].
# ===========================================================================

NOAH_TOPICS: Dict[str, dict] = {
    "tea": {
        "text": J([
            "  \u201cThe tea is warm. The tea is not warm. The tea is *there*.",
            "  \u201cThe kettle is always on. The kettle is not a kettle. The",
            "  \u201ckettle is a *nook*. The nook is for the tea. The tea is",
            "  \u201cfor the bench. The bench is for the nook. The nook is",
            "  \u201cfor the valley. The valley is for the names. The names",
            "  \u201care for the tea. The tea is for you.\u201d",
        ]),
        "flag": "asked_noah_tea",
        "learned": "Noah: the tea is warm, the kettle is always on, the nook is for the tea",
    },
    "worry": {
        "text": J([
            "  \u201cI'm not worried. I'm already inside it. There's a",
            "  \u201cdifference. Worried means you're on the outside looking",
            "  \u201cin. I'm on the inside looking out. The inside is",
            "  \u201cquieter than I expected. The outside is louder.\u201d",
        ]),
        "flag": "asked_noah_worry",
        "learned": "Noah: he is not worried, he is already inside it",
    },
    "shed": {
        "text": J([
            "  \u201cThe shed is not a shed. The shed is a nook. A nook is",
            "  \u201cnot a shed. A nook is a place where the tea is warm and",
            "  \u201cthe bench is the right size for two people and the wrong",
            "  \u201csize for one. The shed is for the tea. The tea is for",
            "  \u201cthe bench. The bench is for the nook. The nook is for",
            "  \u201cthe valley. The valley is for the names. The names are",
            "  \u201cfor the tea. The tea is for you.\u201d",
        ]),
        "flag": "asked_noah_shed",
        "learned": "Noah: the shed is a nook, the nook is for the tea",
    },
}


# ===========================================================================
# NOAH_PLACE — the cosy nook description, growing with trust and chapter,
# cold if noah_hurt is set.
# ===========================================================================

def place_text(s) -> str:
    """Return the nook description. Grows with trust and chapter.
    Cold if noah_hurt is set."""
    trust = s.trust
    ch = s.chapter if hasattr(s, "chapter") else 1
    hurt = s.has("noah_hurt") if hasattr(s, "has") else False

    if hurt:
        return J([
            "The clearing is quiet in a way that is not peaceful. The",
            "shed door is shut. The stars are dark. The kettle is",
            "cold. The two mugs are back on the shelf, and the cat",
            "mug is facing the wall, and the cat is not facing you,",
            "and the cat has not been facing you for a while, and the",
            "cat is not going to face you again. The bench is empty.",
            "The bench is the right size for two people and the wrong",
            "size for one. The tea is not poured. The tea is not",
            "warm. The tea is *there*, but it is not for you.",
        ])

    if trust >= 20 and ch >= 4:
        return J([
            "The clearing is warm in the way a kitchen is warm in",
            "November. The shed door is open. The stars are lit, and",
            "they are the soft gold of a street lamp seen through a",
            "window, and they make the clearing look like the inside",
            "of a dream you would want to stay in. The kettle is on.",
            "The two mugs are out on the bench, and the cat mug is",
            "facing you, and the cat has been facing you for a while,",
            "and the cat is not going to stop facing you, and the cat",
            "is the best kind of welcome. The bench is warm. The bench",
            "has been warm for a while. Someone was sitting here. The",
            "tea is poured. The tea is warm. The tea is the only",
            "thing in the clearing that is not a question.",
        ])

    if trust >= 10 and ch >= 2:
        return J([
            "The clearing is small and warm. A shed sits under a",
            "canopy of paper stars on string, and the stars are not",
            "lit yet, but they are waiting, and the waiting is the",
            "best kind of evidence. The shed door is open. Inside: a",
            "kettle, a shelf of mismatched mugs, a blanket folded to",
            "look like a cushion, and a hand-drawn sign on the wall",
            "that says \u201cNOT a clubhouse!!\u201d in very serious letters.",
            "The bench is the right size for two people and the wrong",
            "size for one. The snack shelf has biscuits. The biscuits",
            "are not for you. The biscuits are *for* you. This is not",
            "a contradiction. This is Noah.",
        ])

    return J([
        "Past the last row of trees, the forest opens into a small",
        "clearing that someone has clearly been working on. A shed,",
        "no bigger than a garden hut, sits under a canopy of paper",
        "stars on string. The stars are not lit. They are waiting.",
        "The shed door is open. Inside: a kettle, a shelf of",
        "mismatched mugs, a blanket folded to look like a cushion,",
        "and a hand-drawn sign on the wall that says \u201cNOT a",
        "clubhouse!!\u201d in very serious letters.",
    ])
