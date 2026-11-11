"""story_extra.py - hooks for scenes added outside story_game.py (menu entries, pools, prerequisites).

ENTRY: sid -> (place, menu label)       POOL: chapter -> [sid, ...]       NEEDS: sid -> sid that must be done first
Every sid here must exist in story/story.json (export it with the Schreiber's export_story.py).
"""
ENTRY = {
    "k1.noah_tasse": ("nook", "Sit with Noah by the stove"),
    "k1.noah_fuechse": ("nook", "Follow the voice behind the Nook"),
    "k2.noah_liste": ("nook", "Fetch the kettle at the Nook"),
    "k3.noah_geburtstag": ("lunuen", "Talk to the baker once more"),
    "k3.noah_zeichnung": ("nook", "Look at the drawing book"),
    "k2.noah_see": ("see", "Walk out onto the jetty"),
    "k4.noah_geschenk": ("nook", "Close your eyes for Noah"),
    "k4.noah_platte": ("nook", "Listen to the old record"),
    "k5.noah_plan": ("nook", "Read the new sheet under the sugar tin"),
    "k6.noah_abschied": ("nook", "Sit down at the scrubbed table"),
}
POOL = {
    1: ["k1.noah_tasse", "k1.noah_fuechse"],
    2: ["k2.noah_liste", "k2.noah_see"],
    3: ["k3.noah_zeichnung", "k3.noah_geburtstag"],
    4: ["k4.noah_geschenk", "k4.noah_platte"],
    5: ["k5.noah_plan"],
    6: ["k6.noah_abschied"],
}
NEEDS = {
    "k4.noah_geschenk": "k3.noah_zeichnung",
    "k5.noah_plan": "k4.noah_geschenk",
    "k6.noah_abschied": "k5.noah_plan",
}

# reaching (scene, node) sets the flag
FLAG_AT = {
    ("k1.noah_fuechse", "n1"): "rehearsed",
    ("k1.noah_fuechse", "n4"): "kind_fox",
    ("k1.noah_tasse", "n4"): "kind_mug",
    ("k1.noah_tasse", "n5"): "kind_mug",
    ("k2.noah_liste", "n6"): "promise",
    ("k3.noah_geburtstag", "n6"): "paid_cost",
    ("k4.noah_geschenk", "n4"): "gift",
    ("k4.noah_geschenk", "n6"): "gift",
    ("k4.noah_geschenk", "n7"): "gift",
    ("k4.noah_platte", "n2"): "kind_record",
    ("k4.noah_platte", "n4"): "kind_record",
    ("k5.noah_plan", "n9"): "promise",
    ("k6.noah_abschied", "n6"): "promise",
}

# shown right before the final choice if the flag is set; order matters
ENDING_QUOTES = [
    ("promise", "You said you'd tell me. I wrote it on the last line of my list, so I wouldn't have to remember it."),
    ("gift", "The cup with your name on it. I sanded the rim until it couldn't hurt your mouth. It was the only thing I had to send anywhere."),
    ("paid_cost", "You paid for the rye with everything you had in your pocket. I ate it in four days, one slice at a time, so it would last. Nobody told me it was allowed to be gone."),
    ("rehearsed", "I practised thank you on a fox for a week, and it always sounded like lying. It doesn't now, does it? ...Thank you."),
    ("kind_mug", "You drank from the guest cup. First one ever. I washed it after, and turned the handle to the door like always, but it was different. It had been used."),
    ("kind_fox", "Marta took the bread out of your hand. She never did that for me. I'm glad it was you. I mean it, I'm... I'm glad."),
    ("kind_record", "You stayed for the whole record. Nobody has ever stayed for the whole record. I counted the minutes you didn't look at the door."),
]
