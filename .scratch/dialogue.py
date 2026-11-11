# dialogue.py — FOLK v2: choice-based dialogue trees for Connor, Mika, and
# the Archivist (new NPC). Each tree is at least 3 nodes deep with at least
# 3 choices per node on the main branch. Every meaningful choice sets a
# story flag and/or shifts trust / fear / sanity, and the NPC's opening
# line depends on the current sanity tier.
#
# Node format:
#   {"id": str, "text": str, "choices": [(label, next_id_or_None, effects), ...]}
#   effects = {"flag": str, "trust": int, "fear": int, "sanity": int,
#              "learned": str, "decided": str}
#   next_id None = end of conversation (back to the prompt).
#
# Style: same join pattern as characters.py. No raw double-quotes inside
# any string literal (use \u201c / \u201d for speech, \u2014 for em dash).

from typing import Dict, List, Optional

from engine import render

NL = "\n"


def J(lines):
    return NL.join(lines)


# ===========================================================================
# CONNOR — the neighbour. Counts things. Is never wrong, which is the problem.
# ===========================================================================

CONNOR_OPEN = {
    "steady": J([
        "Connor is on the step. He was not there a moment ago. He is not",
        "surprised to see you. That is the worst part.",
        "",
        "  \u201cOh. Hey. You're the one, right?\u201d",
        "",
        "He says it like a question he has already answered.",
    ]),
    "thin": J([
        "Connor is on the step. Again. He was not there a moment ago. He",
        "was not there an hour ago. He is not sure he was there a day ago.",
        "",
        "  \u201cHey. Right. You.\u201d",
        "",
        "He is counting something. His lips are moving. He stops when he",
        "sees you counting his lips.",
        "",
        "  \u201cTwelve. There are always twelve. Don't ask.\u201d",
    ]),
    "low": J([
        "Connor is on the step. He is sitting now. He was not sitting a",
        "moment ago. He is holding a notebook. He closes it when he sees",
        "you. Opens it again. Closes it again.",
        "",
        "  \u201cYou came. Good. The dates say you'd come. The dates are\u201d",
        "  \u201calways right. I'm never right.\u201d",
    ]),
    "critical": J([
        "Connor is on the step. He is not Connor. He is the valley wearing",
        "Connor. He knows your name. He has always known your name. He is",
        "not surprised.",
        "",
        "  \u201cYou. Right. You. I've been waiting for you. I've always been",
        "  \u201cwaiting for you. The dates are always right. I'm never right.\u201d",
    ]),
}

CONNOR_TREE: Dict[str, dict] = {
    "n1": {
        "text": J([
            "  \u201cYou're the one, right?\u201d",
            "",
            "He asks if you've seen the lake. Not the water. The lake. The",
            "whole thing. The flat thing. The thing that is not quiet.",
        ]),
        "choices": [
            ("yes, I've seen it",
             "n2",
             {"flag": "connor_lake_yes", "trust": 5, "fear": 3,
              "learned": "told Connor I have seen the lake",
              "decided": "connor: yes, I've seen it"}),
            ("no, I haven't",
             "n2",
             {"flag": "connor_lake_no", "trust": -5, "fear": 8,
              "learned": "told Connor I have not seen the lake",
              "decided": "connor: no, I haven't"}),
            ("I don't remember",
             "n2",
             {"flag": "connor_lake_forgot", "trust": -3, "fear": 10, "sanity": -5,
              "learned": "told Connor I don't remember the lake",
              "decided": "connor: I don't remember"}),
        ],
    },
    "n2": {
        "text": J([
            "He shows you the notebook. The pages are dates, in a hand that",
            "keeps trying to be tidy and keeps failing.",
            "",
            "  \u201cThe dates say you'd come.\u201d",
        ]),
        "choices": [
            ("read it",
             "n3",
             {"flag": "connor_notebook_read", "sanity": -8, "fear": 10,
              "learned": "read Connor's notebook: my name, three weeks from now",
              "decided": "connor: read the notebook"}),
            ("put it down",
             "n3",
             {"flag": "connor_notebook_refused", "trust": 8, "fear": -3,
              "learned": "put Connor's notebook down",
              "decided": "connor: put the notebook down"}),
            ("what are the dates?",
             "n3",
             {"flag": "connor_dates_asked", "trust": 3, "fear": 5,
              "learned": "the dates are arrangements, not dates",
              "decided": "connor: asked what the dates are"}),
        ],
    },
    "n3": {
        "text": J([
            "  \u201cI need you to understand something.\u201d",
            "",
            "He is not asking for help. He is *telling* you.",
        ]),
        "choices": [
            ("tell me",
             None,
             {"flag": "connor_told", "sanity": -12, "fear": 12, "trust": 5,
              "learned": "Connor told me about the ledger. The ink is not ink.",
              "decided": "connor: told me"}),
            ("I'm leaving",
             None,
             {"flag": "connor_leaving", "trust": 10, "fear": -5,
              "learned": "told Connor I'm leaving",
              "decided": "connor: I'm leaving"}),
            ("I'm not leaving",
             None,
             {"flag": "connor_staying", "trust": -8, "fear": 8,
              "learned": "told Connor I'm not leaving",
              "decided": "connor: I'm not leaving"}),
        ],
    },
}


# ===========================================================================
# MIKA — the painter. His uncle is the archivist. He is not calm; he is
# correct, which is worse.
# ===========================================================================

MIKA_OPEN = {
    "steady": J([
        "Mika is at the edge of the lake. He is not painting. He is",
        "watching the water. His canvas is on the ground, face down.",
        "He has been here a while. His boots are wet.",
        "",
        "  \u201cOh. You.\u201d",
        "",
        "He says it like he has been expecting you for a specific",
        "amount of time and you have arrived at exactly the right moment.",
    ]),
    "thin": J([
        "Mika is at the edge of the lake. He is painting. The canvas is",
        "the lake. The lake is the canvas. He has been painting for a",
        "while. The painting is finished. The painting is not finished.",
        "",
        "  \u201cYou're early. The dates say you'd come on Friday. It's\u201d",
        "  \u201cTuesday. That's fine. The dates are a suggestion. I'm not\u201d",
        "  \u201ca fan of suggestions.\u201d",
    ]),
    "low": J([
        "Mika is in the water. The water is in you. You are in the",
        "water. The water is in the lake. The lake is in the valley.",
        "The valley is in the house. The house is in you. You are in",
        "the house. The house is in the valley. The valley is in you.",
        "",
        "  \u201cYou and me. We're the same thing. We've always been the\u201d",
        "  \u201csame thing. I just knew it first. I just knew it first.\u201d",
    ]),
    "critical": J([
        "Mika is not Mika. He is the lake. He is not surprised to see",
        "you. He has been seeing you. He has been seeing you since",
        "before you had a face.",
        "",
        "  \u201cYou. Right. You. I've been seeing you. I've always been",
        "  \u201cseeing you. The face is yours. It has always been yours.\u201d",
    ]),
}

MIKA_TREE: Dict[str, dict] = {
    "n1": {
        "text": J([
            "  \u201cCan you count with me?\u201d",
            "",
            "He starts counting. One. Two. Three. He stops at eleven.",
            "He looks at you.",
        ]),
        "choices": [
            ("twelve",
             "n2",
             {"flag": "mika_counted_twelve", "sanity": -5, "trust": 8,
              "learned": "counted twelve with Mika",
              "decided": "mika: twelve"}),
            ("what's twelve?",
             "n2",
             {"flag": "mika_asked_twelve", "sanity": -10, "fear": 12,
              "learned": "Mika said twelve is me",
              "decided": "mika: what's twelve?"}),
            ("stay silent",
             "n2",
             {"flag": "mika_counted_silence", "trust": 3, "fear": 5,
              "learned": "stayed silent while Mika counted twelve",
              "decided": "mika: stayed silent"}),
        ],
    },
    "n2": {
        "text": J([
            "  \u201cThe water is not water.\u201d",
            "",
            "He says this like a fact. Like a weather report.",
        ]),
        "choices": [
            ("what is it?",
             "n3",
             {"flag": "mika_what", "sanity": -12, "fear": 15,
              "learned": "the water is a mouth. the town is the tongue. the forest is the teeth.",
              "decided": "mika: what is it?"}),
            ("I don't believe you",
             "n3",
             {"flag": "mika_disbelieved", "trust": -8, "fear": 8,
              "learned": "told Mika I don't believe him",
              "decided": "mika: I don't believe you"}),
            ("why tell me?",
             "n3",
             {"flag": "mika_why", "trust": 5, "fear": 5,
              "learned": "Mika said he can't take it back",
              "decided": "mika: why tell me?"}),
        ],
    },
    "n3": {
        "text": J([
            "  \u201cStop counting.\u201d",
            "",
            "He says this quietly. He means it. He is not asking. He is",
            "*requesting*.",
        ]),
        "choices": [
            ("okay",
             None,
             {"flag": "mika_stopped", "trust": 10, "fear": -3,
              "learned": "told Mika to stop counting, he stopped",
              "decided": "mika: okay"}),
            ("I can't",
             None,
             {"flag": "mika_cant", "sanity": -15, "fear": 15, "trust": -5,
              "learned": "told Mika I can't stop counting",
              "decided": "mika: I can't"}),
            ("why?",
             None,
             {"flag": "mika_why_stopped", "sanity": -15, "fear": 18, "trust": 3,
              "learned": "Mika said the water is counting too, and it's almost at me",
              "decided": "mika: why?"}),
        ],
    },
}


# ===========================================================================
# THE ARCHIVIST — Mika's uncle. New NPC. The calmest person in L\u00fcnen.
# He is not calm because he is not afraid. He is calm because he has
# already decided what he is going to do, and he has already done it.
# ===========================================================================

ARCHIVIST_OPEN = {
    "steady": J([
        "The archivist is in the basement. He is very calm. He is the",
        "calmest person in L\u00fcnen. He is not calm because he is not",
        "afraid. He is calm because he has already decided what he is",
        "going to do, and he has already done it, and he is just waiting",
        "for the rest of the town to catch up.",
        "",
        "  \u201cAh. The name in the ledger. I've been expecting you. I've",
        "  \u201cbeen expecting you for thirty years. I'm the archivist. I",
        "  \u201ckeep the records. The records are the valley. The valley",
        "  \u201cis the records.\u201d",
    ]),
    "thin": J([
        "The archivist is in the basement. He is very calm. He is the",
        "calmest person in L\u00fcnen. He is not calm because he is not",
        "afraid. He is calm because he has already decided what he is",
        "going to do, and he has already done it, and he is just waiting",
        "for the rest of the town to catch up.",
        "",
        "  \u201cYou. Right. You. I've been expecting you. I've always been",
        "  \u201cexpecting you. The records are the valley. The valley is",
        "  \u201cthe records. You are the record. You have always been the",
        "  \u201crecord.\u201d",
    ]),
    "low": J([
        "The archivist is in the basement. He is very calm. He is the",
        "calmest person in L\u00fcnen. He is not calm because he is not",
        "afraid. He is calm because he has already decided what he is",
        "going to do, and he has already done it, and he is just waiting",
        "for the rest of the town to catch up.",
        "",
        "  \u201cYou and me. We're the same thing. We've always been the",
        "  \u201csame thing. I just knew it first. I just knew it first.\u201d",
        "  \u201cI just knew it first.\u201d",
    ]),
    "critical": J([
        "The archivist is in the basement. He is not the archivist. He is",
        "the valley. He is not surprised to see you. He has been seeing",
        "you. He has been seeing you since before you had a face.",
        "",
        "  \u201cYou. Right. You. I've been seeing you. I've always been",
        "  \u201cseeing you. The records are you. The records have always",
        "  \u201cbeen you.\u201d",
    ]),
}

ARCHIVIST_TREE: Dict[str, dict] = {
    "n1": {
        "text": J([
            "  \u201cThe records are the valley. The valley is the records.\u201d",
            "",
            "He says this like a fact. Like a weather report. Like a man",
            "who has said it a thousand times and is not tired of it.",
        ]),
        "choices": [
            ("what do the records say about me?",
             "n2",
             {"flag": "archivist_records_asked", "trust": 5, "fear": 8,
              "learned": "the records say I am the next name",
              "decided": "archivist: what do the records say about me?"}),
            ("I don't want to know",
             "n2",
             {"flag": "archivist_refused", "trust": -5, "fear": 5,
              "learned": "told the archivist I don't want to know",
              "decided": "archivist: I don't want to know"}),
            ("who else is in the records?",
             "n2",
             {"flag": "archivist_others_asked", "trust": 3, "fear": 10,
              "learned": "the records have hundreds of names, all local",
              "decided": "archivist: who else is in the records?"}),
        ],
    },
    "n2": {
        "text": J([
            "  \u201cThe records say you are the next name. The records have",
            "  \u201csaid this for thirty years. The records are not wrong.\u201d",
            "  \u201cThe records are never wrong. That's the thing with them.\u201d",
        ]),
        "choices": [
            ("can I change it?",
             "n3",
             {"flag": "archivist_change_asked", "trust": 8, "fear": 5,
              "learned": "the archivist said the records can be changed, but it costs",
              "decided": "archivist: can I change it?"}),
            ("I don't believe you",
             "n3",
             {"flag": "archivist_disbelieved", "trust": -10, "fear": 8,
              "learned": "told the archivist I don't believe him",
              "decided": "archivist: I don't believe you"}),
            ("why tell me?",
             "n3",
             {"flag": "archivist_why", "trust": 5, "fear": 5,
              "learned": "the archivist said he's been saying it to the records for thirty years",
              "decided": "archivist: why tell me?"}),
        ],
    },
    "n3": {
        "text": J([
            "  \u201cThe records can be changed. But it costs. The cost is",
            "  \u201cnot money. The cost is not time. The cost is *you*. The cost",
            "  \u201cis the name. The name is the cost. The cost is the name.\u201d",
        ]),
        "choices": [
            ("I'll pay",
             None,
             {"flag": "archivist_paid", "trust": 15, "fear": 10, "sanity": -10,
              "learned": "told the archivist I'll pay the cost",
              "decided": "archivist: I'll pay"}),
            ("I won't pay",
             None,
             {"flag": "archivist_refused_pay", "trust": -12, "fear": 8,
              "learned": "told the archivist I won't pay",
              "decided": "archivist: I won't pay"}),
            ("what is the cost?",
             None,
             {"flag": "archivist_cost_asked", "trust": 5, "fear": 12, "sanity": -8,
              "learned": "the cost is the name. the name is the cost.",
              "decided": "archivist: what is the cost?"}),
        ],
    },
}


# ===========================================================================
# ASK <topic> — a small keyword system. The player can ask an NPC about
# specific topics. Each topic returns a short line and may set a flag.
# ===========================================================================

ASK_TOPICS: Dict[str, Dict[str, dict]] = {
    "connor": {
        "lake": {
            "text": J([
                "  \u201cThe lake is breathing. Not the water moving. The whole",
                "  \u201clake. In. Out. In. Out. It's been doing it all week. I",
                "  \u201ccounted. I counted wrong. It's been doing it longer.\u201d",
            ]),
            "flag": "asked_connor_lake",
            "learned": "Connor: the lake is breathing, not the water moving",
        },
        "notebook": {
            "text": J([
                "  \u201cThere's a notebook in the forest. Hollow tree, third",
                "  \u201ccircle from the road. It's mine. I lost it. Or I left it.",
                "  \u201cOr I'm still writing it and this copy is the one I",
                "  \u201cfinished. If you read it, read it fast. Slow is how it",
                "  \u201creads you back.\u201d",
            ]),
            "flag": "asked_connor_notebook",
            "learned": "Connor: the notebook is in the hollow tree, third circle",
        },
        "ledger": {
            "text": J([
                "  \u201cThe ledger has your name. I've seen it. I've seen it",
                "  \u201cin the water. The water is the ledger. The lake is the",
                "  \u201cledger. You just have to be in it long enough.\u201d",
            ]),
            "flag": "asked_connor_ledger",
            "learned": "Connor: the ledger has my name, the water is the ledger",
        },
    },
    "mika": {
        "painting": {
            "text": J([
                "  \u201cThe painting is the lake. The figure is in the lake.",
                "  \u201cThe face is not painted. It has not been painted in",
                "  \u201cthree years. I left the face out on purpose. I knew it",
                "  \u201cwould be yours. I just didn't know what yours looked",
                "  \u201clike yet.\u201d",
            ]),
            "flag": "asked_mika_painting",
            "learned": "Mika: the painting's face is mine, left out on purpose",
        },
        "uncle": {
            "text": J([
                "  \u201cMy uncle is the archivist. He's very calm. He's been",
                "  \u201cvery calm for thirty years. I think that's the problem.",
                "  \u201cHe's not calm because he's not afraid. He's calm because",
                "  \u201che's already decided what he's going to do, and he's",
                "  \u201calready done it.\u201d",
            ]),
            "flag": "asked_mika_uncle",
            "learned": "Mika: his uncle is the archivist, calm for thirty years",
        },
        "valley": {
            "text": J([
                "  \u201cThe valley doesn't want a sacrifice. It wants a",
                "  \u201cwitness. That's what my uncle says. My uncle is the",
                "  \u201carchivist. My uncle is very calm. My uncle has been",
                "  \u201cvery calm for thirty years. I think that's the",
                "  \u201cproblem.\u201d",
            ]),
            "flag": "asked_mika_valley",
            "learned": "Mika: the valley wants a witness, not a sacrifice",
        },
    },
    "noah": {
        "counting": {
            "text": J([
                "  \u201cI don't know what I'm counting. I know I'm",
                "  \u201ccounting. I know the numbers are real. I know the",
                "  \u201cnumbers are not mine. They're the valley's. I'm just",
                "  \u201cthe mouth it uses. Connor is the mouth it uses",
                "  \u201ctoo. We're both mouths. The valley has a lot of",
                "  \u201cpractice.”",
            ]),
            "flag": "asked_noah_counting",
            "learned": "Noah: the counting is the valley's, he is just the mouth",
        },
        "help": {
            "text": J([
                "  \u201cYou want me to help you? I can. I can stop",
                "  \u201ccounting. But if I stop, the valley stops too. And",
                "  \u201cif the valley stops, the lake stops, and the lake",
                "  \u201cis the only thing keeping the water in the",
                "  \u201cground. Do you want the water to come up? I don't. I",
                "  \u201cwant to keep counting. I want to keep being the mouth.",
                "  \u201cIt's the only thing I'm good at.”",
            ]),
            "flag": "asked_noah_help",
            "learned": "Noah: he can stop counting but the valley would stop too",
        },
        "hurt": {
            "text": J([
                "  \u201cYou want to hurt me? I can do that. I can make",
                "  \u201cthe counting louder. I can make it so loud that",
                "  \u201cthe lake cracks. I can make it so loud that the",
                "  \u201cvalley forgets its own name. But I won't. I won't",
                "  \u201cdo it. I'm the mouth, not the hand. The hand is the",
                "  \u201carchivist. The hand is always the archivist.”",
            ]),
            "flag": "asked_noah_hurt",
            "learned": "Noah: he can make the counting louder but won't",
        },
    },
    "archivist": {
        "records": {
            "text": J([
                "  \u201cThe records are the valley. The valley is the",
                "  \u201crecords. One name per year. Hundreds of them. All of",
                "  \u201cthem local. All of them people who lived in L\u00fcnen.",
                "  \u201cThe last entry is your name. The date is this week.",
                "  \u201cThe ink is still wet.\u201d",
            ]),
            "flag": "asked_archivist_records",
            "learned": "archivist: the records have my name, the ink is still wet",
        },
        "cost": {
            "text": J([
                "  \u201cThe records can be changed. But it costs. The cost is",
                "  \u201cnot money. The cost is not time. The cost is *you*. The",
                "  \u201ccost is the name. The name is the cost. The cost is",
                "  \u201cthe name.\u201d",
            ]),
            "flag": "asked_archivist_cost",
            "learned": "archivist: the cost is the name, the name is the cost",
        },
        "ritual": {
            "text": J([
                "  \u201cThe ritual is in two days. Maybe one day. Time is a",
                "  \u201csuggestion. The gate opens by the hand it chooses. I",
                "  \u201cthink the hand is yours. I think the hand has always",
                "  \u201cbeen yours. I think the hand is a suggestion the",
                "  \u201cvalley makes to itself.\u201d",
            ]),
            "flag": "asked_archivist_ritual",
            "learned": "archivist: the ritual is in two days, the hand is mine",
        },
    },
}


# ===========================================================================
# NOAH — the boy in the forest. He is counting with you, and he knows it.
# Opening line depends on the sanity tier; the tree has one specific
# help/hurt moment that changes the state of the week.
# ===========================================================================

NOAH_OPEN: Dict[str, str] = {
    "steady": J([
        "A boy is sitting in the hollow tree, legs swinging, and he is",
        "counting under his breath. Not counting to ten. Counting *out*",
        "of the air. He sees you and does not stop counting.",
        "\u201cYou're early,\u201d he says. \u201cOr late. I can't tell which is",
        "which anymore. I'm Noah.\u201d",
    ]),
    "thin": J([
        "A boy is sitting in the hollow tree and he is counting under",
        "his breath, and the counting is in your head too, and you",
        "don't remember when it started. He sees you and does not",
        "stop counting.",
        "\u201cYou're early,\u201d he says. \u201cOr late. I can't tell which is",
        "which anymore. I'm Noah.\u201d",
    ]),
    "low": J([
        "The hollow tree is breathing. The boy in it is counting. You",
        "are counting. You cannot tell where the counting belongs.",
        "He sees you and his mouth is moving, and the words are yours.",
        "\u201cYou're early,\u201d he says. \u201cOr late. I can't tell which is",
        "which anymore. I'm Noah.\u201d",
    ]),
    "critical": J([
        "There is a boy in the hollow tree, or the hollow tree is a",
        "boy, or the hollow tree is you, and the counting is the",
        "only thing that is still in order. He sees you and does",
        "not stop.",
        "\u201cYou're early,\u201d he says. \u201cOr late. I can't tell which is",
        "which anymore. I'm Noah.\u201d",
    ]),
}

NOAH_TREE: Dict[str, dict] = {
    "n1": {
        "id": "n1",
        "text": J([
            "\u201cThe valley is breathing again,\u201d Noah says. \u201cIt started",
            "last week. Maybe the week before. I've been counting the",
            "breaths. I've lost count. I can't stop counting. Do you",
            "want to help me count, or do you want to stop me?\u201d",
        ]),
        "choices": [
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
            ("tell him to stop", "n_hurt",
             {"fear": 1, "sanity": -3,
              "decided": "told Noah to stop counting"}),
            ("ask what the valley is breathing for", "n_why",
             {"sanity": -1,
              "learned": "Noah: the valley breathes to keep the count going"}),
        ],
    },
    "n_help": {
        "id": "n_help",
        "text": J([
            "You sit down. You count. The numbers are not numbers, not",
            "at first, but they become numbers, and the counting becomes",
            "a small, warm, living thing between the two of you. Noah",
            "looks at you and his face does something you will not be",
            "able to describe to anyone.",
            "\u201cYou're the first person who's helped me count in a",
            "while,\u201d he says. \u201cThe others just stop me. Stopping is",
            "worse. Stopping is how it gets into your head.\u201d",
        ]),
        "choices": [
            ("ask him what the count is for", "n_purpose",
             {"trust": 1,
              "learned": "Noah: the count is the valley's memory of the names"}),
            ("ask him if he is afraid", "n_afraid",
             {"sanity": -1,
              "learned": "Noah: he is not afraid, he is already inside it"}),
            ("thank him and leave", None,
             {"flag": "noah_ally", "trust": 1,
              "decided": "helped Noah count; he is on your side now"}),
        ],
    },
    "n_hurt": {
        "id": "n_hurt",
        "text": J([
            "You tell him to stop. He stops. The silence that follows is",
            "the worst thing you have heard all week. It is not",
            "quiet. It is *full*. It is the sound of a count that has",
            "been stopped but not finished, and it is in your chest now,",
            "and it is not going to leave.",
            "\u201cYou see,\u201d Noah says, very quietly. \u201cThat's how it gets",
            "in. You stop it, and it stays. The valley doesn't forget",
            "a count. It keeps it. It keeps all of them.\u201d",
        ]),
        "choices": [
            ("apologise", "n_apologise",
             {"trust": -1, "sanity": -2,
              "decided": "apologised to Noah for stopping the count"}),
            ("ask what happens to the stopped counts", "n_stopped",
             {"fear": 1,
              "learned": "Noah: the stopped counts are in the lake, still running"}),
            ("leave without another word", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_why": {
        "id": "n_why",
        "text": J([
            "\u201cIt breathes so it doesn't forget,\u201d Noah says. \u201cEvery",
            "breath is a name. Every name is a person who lived in",
            "L\u00fcnen and is still in L\u00fcnen. The valley remembers them",
            "by breathing them. If it stopped breathing, they'd stop",
            "being. I don't think that's a metaphor. I think it's a",
            "mechanism.\u201d",
        ]),
        "choices": [
            ("ask if your name is in the count", "n_name",
             {"fear": 1, "sanity": -2,
              "learned": "Noah: your name is in the count, and it is still wet"}),
            ("ask how he knows all this", "n_knows",
             {"trust": 1,
              "learned": "Noah: he has been counting since he was six"}),
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
        ],
    },
    "n_purpose": {
        "id": "n_purpose",
        "text": J([
            "\u201cThe count is the memory,\u201d Noah says. \u201cThe valley can't",
            "write. It can't speak. It can only count. Every count is",
            "a name. Every name is a person. If the count stops, the",
            "name stops. If the name stops, the person stops. I don't",
            "think that's a metaphor. I think it's a mechanism.\u201d",
        ]),
        "choices": [
            ("ask if your name is in the count", "n_name",
             {"fear": 1, "sanity": -2,
              "learned": "Noah: your name is in the count, and it is still wet"}),
            ("thank him and leave", None,
             {"flag": "noah_ally", "trust": 1,
              "decided": "helped Noah count; he is on your side now"}),
        ],
    },
    "n_afraid": {
        "id": "n_afraid",
        "text": J([
            "Noah thinks about this for a long time. The tree creaks.",
            "A bird lands on a branch and does not sing.",
            "\u201cI'm not afraid,\u201d he says. \u201cI'm already inside it. There's",
            "a difference. Afraid means you're on the outside looking",
            "in. I'm on the inside looking out. The inside is quieter",
            "than I expected. The outside is louder.\u201d",
        ]),
        "choices": [
            ("ask him what the inside looks like", "n_inside",
             {"sanity": -2,
              "learned": "Noah: the inside is a room with no walls and a very old chair"}),
            ("thank him and leave", None,
             {"flag": "noah_ally", "trust": 1,
              "decided": "helped Noah count; he is on your side now"}),
        ],
    },
    "n_apologise": {
        "id": "n_apologise",
        "text": J([
            "You say sorry. Noah looks at you for a long time. The",
            "counting has not started again. The silence is still in",
            "your chest. It is slightly smaller than it was.",
            "\u201cOkay,\u201d he says. \u201cI'll let you count with me. But the",
            "count that you stopped is still in the lake. It's still",
            "running. It's running your number. I don't know what that",
            "means. I don't think it's good.\u201d",
        ]),
        "choices": [
            ("ask what the stopped count means", "n_stopped",
             {"fear": 1,
              "learned": "Noah: the stopped counts are in the lake, still running"}),
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_stopped": {
        "id": "n_stopped",
        "text": J([
            "\u201cThey're in the lake,\u201d Noah says. \u201cEvery count that's been",
            "stopped is in the lake. They're still running. They're",
            "running the numbers of the people who stopped them. I've",
            "seen them in the water. They look like handwriting. They",
            "look like your handwriting.\u201d",
        ]),
        "choices": [
            ("ask if you can stop the stopped count", "n_stop_it",
             {"fear": 1, "sanity": -2,
              "learned": "Noah: you can't stop the stopped count, you can only join it"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_name": {
        "id": "n_name",
        "text": J([
            "Noah is quiet for a long time. The counting has stopped.",
            "You are counting. You don't know when you started.",
            "\u201cYour name is in the count,\u201d he says. \u201cIt's the last",
            "one. It's still wet. I don't know what that means. I",
            "don't think it's good. I think it means the valley is",
            "still deciding what to do with you.\u201d",
        ]),
        "choices": [
            ("ask what the valley will do with you", "n_decide",
             {"fear": 1, "sanity": -2,
              "learned": "Noah: the valley will keep you, or it will let you go, and it hasn't decided yet"}),
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_knows": {
        "id": "n_knows",
        "text": J([
            "\u201cI've been counting since I was six,\u201d Noah says. \u201cMy",
            "mother started me. She said the valley was counting and",
            "I should keep up. I've kept up. I'm the only one who's",
            "kept up. The others stop. The valley keeps them. I don't",
            "think that's a metaphor. I think it's a mechanism.\u201d",
        ]),
        "choices": [
            ("ask if his mother is still counting", "n_mother",
             {"fear": 1, "sanity": -2,
              "learned": "Noah: his mother is in the lake, still counting, still running"}),
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
        ],
    },
    "n_inside": {
        "id": "n_inside",
        "text": J([
            "\u201cIt's a room,\u201d Noah says. \u201cNo walls. A very old chair. The",
            "chair is for the person who is being counted. The room",
            "is for the count. The count is for the valley. The valley",
            "is for the names. The names are for the people. The people",
            "are for you.\u201d",
        ]),
        "choices": [
            ("ask if you are in the room", "n_room",
             {"fear": 1, "sanity": -3,
              "learned": "Noah: you are in the room, you have been for a while, you just didn't know"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_stop_it": {
        "id": "n_stop_it",
        "text": J([
            "\u201cYou can't stop it,\u201d Noah says. \u201cYou can only join it. The",
            "stopped count is running your number. If you join it, the",
            "number stops running. If you don't join it, the number",
            "keeps running. I don't know which is worse. I think they",
            "are the same thing.\u201d",
        ]),
        "choices": [
            ("join the count", None,
             {"flag": "noah_ally", "trust": 1, "sanity": -3,
              "decided": "joined Noah's count; the stopped number has stopped running"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_decide": {
        "id": "n_decide",
        "text": J([
            "\u201cIt will keep you, or it will let you go,\u201d Noah says. \u201cI",
            "don't know which. I don't think it knows either. I think",
            "it's still deciding. I think the deciding is the point. I",
            "think the valley is a machine that makes decisions, and",
            "you are the decision it is making.\u201d",
        ]),
        "choices": [
            ("ask how to influence the decision", "n_influence",
             {"trust": 1,
              "learned": "Noah: you can't influence the decision, you can only be in it or out of it"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_mother": {
        "id": "n_mother",
        "text": J([
            "Noah is quiet. The tree creaks. The counting has stopped.",
            "\u201cShe's in the lake,\u201d he says. \u201cShe's still counting. She's",
            "still running. I can see her in the water. She looks like",
            "handwriting. She looks like my handwriting. I don't think",
            "that's a metaphor. I think it's a mechanism.\u201d",
        ]),
        "choices": [
            ("ask if you can see her too", "n_see_her",
             {"fear": 1, "sanity": -3,
              "learned": "Noah: you can see her if you look at the lake at the right time"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_room": {
        "id": "n_room",
        "text": J([
            "\u201cYou're in the room,\u201d Noah says. \u201cYou've been in the room",
            "for a while. You just didn't know. The chair is for you.",
            "The count is for you. The valley is for you. The names are",
            "for you. You are the decision the valley is making.\u201d",
        ]),
        "choices": [
            ("ask how to leave the room", "n_leave_room",
             {"fear": 1, "sanity": -3,
              "learned": "Noah: you can't leave the room, you can only be counted or stop counting"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_influence": {
        "id": "n_influence",
        "text": J([
            "\u201cYou can't influence it,\u201d Noah says. \u201cYou can only be in it",
            "or out of it. In is the count. Out is the lake. I don't",
            "know which is better. I think they are the same thing. I",
            "think the valley doesn't know either. I think the deciding",
            "is the point.\u201d",
        ]),
        "choices": [
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_see_her": {
        "id": "n_see_her",
        "text": J([
            "\u201cYou can see her if you look at the lake at the right time,\u201d",
            "Noah says. \u201cThe right time is when the count is at its",
            "highest. The highest is when you've been counting the",
            "longest. I don't know what that means. I don't think it's",
            "good. I think it means you're already in it.\u201d",
        ]),
        "choices": [
            ("ask what happens if you see her", "n_see_consequence",
             {"fear": 1, "sanity": -3,
              "learned": "Noah: if you see her, she sees you, and the count changes"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_leave_room": {
        "id": "n_leave_room",
        "text": J([
            "\u201cYou can't leave the room,\u201d Noah says. \u201cYou can only be",
            "counted or stop counting. If you stop counting, the count",
            "stops. If the count stops, the name stops. If the name",
            "stops, the person stops. I don't think that's a metaphor.",
            "I think it's a mechanism.\u201d",
        ]),
        "choices": [
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
    "n_see_consequence": {
        "id": "n_see_consequence",
        "text": J([
            "\u201cIf you see her, she sees you,\u201d Noah says. \u201cAnd the count",
            "changes. The count changes to your number. Your number",
            "starts running. I don't know what that means. I don't think",
            "it's good. I think it means the valley has decided. I",
            "think it means you're in the room now. I think you've been",
            "in the room the whole time.\u201d",
        ]),
        "choices": [
            ("sit down and count with him", "n_help",
             {"trust": 1, "sanity": -2,
              "learned": "Noah: the valley is breathing, he has lost count"}),
            ("leave", None,
             {"flag": "noah_hurt", "fear": 1,
              "decided": "hurt Noah by stopping the count; he will remember it"}),
        ],
    },
}


# ===========================================================================
# RUNNER — the function that drives a conversation tree.
# ===========================================================================

def run_tree(s, who: str, tree: Dict[str, dict], open_text: str) -> None:
    """Drive a choice-based dialogue tree. `who` is the NPC id (connor, mika,
    archivist). `tree` is the node dict. `open_text` is the tier-appropriate
    opening line. Returns when the player reaches a terminal node (next_id
    is None) or types 'leave'."""
    render(open_text)
    render("")

    node_id = "n1"
    while node_id is not None:
        node = tree[node_id]
        render(node["text"])
        render("")
        for i, (label, next_id, effects) in enumerate(node["choices"], 1):
            render(f"  {i}. {label}")
        render("  0. leave")
        render("")
        choice = input("> ").strip().lower()
        if choice in ("", "0", "leave", "quit", "q"):
            # player leaves the conversation early
            s.journal_add("decided", f"left {who} mid-conversation")
            return
        try:
            n = int(choice)
        except ValueError:
            render("")
            render("  (you do not know what to do with that. the valley does.)")
            continue
        if not (1 <= n <= len(node["choices"])):
            render("")
            render("  (you do not know what to do with that. the valley does.)")
            continue
        label, next_id, effects = node["choices"][n - 1]
        # apply effects
        if effects.get("flag"):
            s.flag(effects["flag"])
        if effects.get("trust"):
            s.trust_change(effects["trust"])
        if effects.get("fear"):
            s.fear_change(effects["fear"])
        if effects.get("sanity"):
            s.sanity_change(effects["sanity"])
        if effects.get("learned"):
            s.journal_add("learned", effects["learned"])
        if effects.get("decided"):
            s.journal_add("decided", effects["decided"])
        node_id = next_id


def ask_topic(s, who: str, topic: str) -> bool:
    """Handle `ask <topic>`. Returns True if the topic was recognized."""

    topics = ASK_TOPICS.get(who, {})
    t = topics.get(topic)
    if t is None:
        return False
    render(t["text"])
    if t.get("flag"):
        s.flag(t["flag"])
    if t.get("learned"):
        s.journal_add("learned", t["learned"])
    if t.get("trust"):
        s.trust_change(t["trust"])
    if t.get("fear"):
        s.fear_change(t["fear"])
    if t.get("sanity"):
        s.sanity_change(t["sanity"])
    return True
