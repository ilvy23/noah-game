"""scene_lib/overrides.py - which backdrop and which figures a story scene gets.

plan(sid, scene, place, chapter, text) -> dict(kind, figs, mood, preset, hand) :
    kind    a backdrops.KINDS name, or "ambient:stairs" / "ambient:cellar" (ambient_fx scenes used as the picture)
    figs    {figure id: (slot, facing)}  slot = left | mid | right | far; ids noah mika connor you stranger woman child
    preset  {figure id: [actions played instantly before the scene starts]} (Mika already sits with his cigarette)
    mood    Noah's colour: green | yellow | red
    nodes   {node id: kind}  a node that moves to another place
    acts    [(node id or "*", substring of the text, figure, action)]  extra actions fired when a beat contains the substring
Automatic mapping first (place -> kind, then key words of the text, then the figure), HANDCRAFTED holds the scenes that need it: those are listed in HANDCRAFTED.
"""
from . import backdrops

KEYWORDS = [("kirche", ("church", "pew", "altar", "chairs, slowly")), ("ritual", ("ritual room", "circle", "sigil", "painted over")), ("berg", ("hill", "stakes", "pyre", "burnt")),
            ("dachboden", ("attic", "roof beams", "hat boxes")), ("baeckerei", ("bakery", "baker", "yeast")), ("keller", ("cellar", "wrong angles", "candle")),
            ("schule", ("schoolyard", "classroom", "gymnasium", "school")), ("nook", ("nook", "stove", "crate by", "tea")), ("see", ("bench", "lake", "shore", "swing")),
            ("wald", ("forest", "clearing", "trees", "path forks", "woods")), ("schloss", ("castle", "east wing", "library", "shelf")),
            ("haus", ("hallway", "kitchen", "bedroom", "upstairs", "stairs", "wall behind", "floorboards", "door at the end")), ("street", ("street", "bus stop", "town", "fog sits"))]
FIG_KIND = {"noah": "nook", "mika": "see", "connor": "street"}
SLOTS = {"you": ("left", 1), "mika": ("right", -1), "noah": ("right", -1), "connor": ("right", -1), "stranger": ("far", -1), "woman": ("far", -1), "child": ("mid", -1)}

# scene id -> overrides (anything not given is automatic)
HANDCRAFTED = {
    "prolog": dict(kind="haus_aussen", figs={"you": ("mid", 1)}),
    "k1.nook_noah": dict(kind="nook", figs={"you": ("left", 1), "noah": ("right", -1)}, preset={}),
    "k1.noah_tasse": dict(kind="nook", figs={"you": ("left", 1), "noah": ("right", -1)}, preset={"you": ["sit"], "noah": ["sit"]}),
    "k1.see_mika": dict(kind="see", figs={"you": ("left", 1), "mika": ("right", -1)}, preset={"mika": ["sit", "hold_cig"]}, acts=[("*", "swing stops", "you", "look_up")]),
    "k2.connor_1": dict(kind="street", figs={"you": ("left", 1), "connor": ("right", -1)}, preset={"connor": ["hands_behind"]}),
    "k2.gymnasium_connor": dict(kind="schule", figs={"you": ("left", 1), "connor": ("right", -1)}),
    "k3.mika": dict(kind="see", figs={"you": ("left", 1), "mika": ("right", -1)}, preset={"mika": ["sit", "hold_cig"]}),
    "k3.connor_2": dict(kind="street", figs={"you": ("left", 1), "connor": ("right", -1)}),
    "k4.anwerbung": dict(kind="see", figs={"you": ("left", 1), "connor": ("right", -1)}, preset={"connor": ["hands_behind"]}),
    "k4.mika_reaktion": dict(kind="see", figs={"you": ("left", 1), "mika": ("right", -1)}, preset={"mika": ["sit", "hold_cig"]}),
    "k5.tuer": dict(kind="schloss", figs={"you": ("left", 1)}),
    "k5.tesserakt": dict(kind="keller", figs={"you": ("mid", 1)}, acts=[("*", "cube", "you", "tesseract_glow")]),
    "k6.traum": dict(kind="haus", figs={"you": ("left", 1)}, mood="green",
                     nodes={"n2": "wohnzimmer", "n3": "wohnzimmer", "n5": "wohnzimmer", "n6": "wohnzimmer", "n4": "ritual", "n7": "ritual", "n8": "ritual", "n10": "ritual",
                            "n11": "ritual", "n12": "ritual", "n13": "ritual", "n9": "haus", "n14": "haus"}),
    "k6.mika_froh": dict(kind="see", figs={"you": ("left", 1), "mika": ("right", -1)}, preset={"mika": ["sit", "hold_cig"]}),
    "k7.noah_vor": dict(kind="keller", figs={"you": ("left", 1), "noah": ("right", -1)}, mood="red"),
    "k7.entscheidung": dict(kind="ambient:cellar", figs={}),
    "k7.warn10": dict(kind="ambient:cellar", figs={}),
    "k7.warn20": dict(kind="ambient:cellar", figs={}),
    "k1.haus_nacht": dict(kind="haus", figs={"you": ("left", 1)}),
    "k1.kirche_fenster": dict(kind="street", figs={"you": ("left", 1), "connor": ("far", -1)}, preset={"connor": ["hands_behind"]}),
    "k2.baeckerei": dict(kind="baeckerei", figs={"you": ("left", 1), "woman": ("mid", -1)}),
    "k2.schulhof": dict(kind="schule", figs={"you": ("left", 1)}),
    "k2.dachboden": dict(kind="dachboden", figs={"you": ("left", 1)}),
    "k3.lichtung": dict(kind="wald", figs={"you": ("left", 1)}),
    "k3.nook_leer": dict(kind="nook", figs={"you": ("left", 1)}),
    "k3.haus_wand": dict(kind="haus", figs={"you": ("mid", 1)}, acts=[("*", "ear", "you", "touch_wall"), ("*", "palm", "you", "touch_wall")]),
    "k4.berg": dict(kind="berg", figs={"you": ("left", 1)}),
    "k4.ritualzimmer": dict(kind="ritual", figs={"you": ("mid", 1)}),
    "k7.anreise": dict(kind="ambient:stairs", figs={}),
}


def keyword_kind(text):
    low = text.lower()
    best = None
    for kind, words in KEYWORDS:
        hits = sum(low.count(w) for w in words)
        if hits and (best is None or hits > best[0]):
            best = (hits, kind)
    return best[1] if best else None


def plan(sid, scene, place=None, chapter=1, text=""):
    h = HANDCRAFTED.get(sid)
    figs_in = [f for f in (scene.get("figuren") or []) if f in SLOTS]
    if h:
        out = dict(h)
        out.setdefault("figs", {})
        out["handcrafted"] = True
    else:
        kind = backdrops.PLACE_KIND.get(place or "")
        if not kind and sid and sid.startswith("ort."):
            kind = backdrops.PLACE_KIND.get(sid.split(".")[1])
        kind = kind or keyword_kind(text) or (FIG_KIND.get(figs_in[0]) if figs_in else None) or ("schloss" if chapter >= 5 else "street")
        figs = {f: SLOTS[f] for f in figs_in}
        out = dict(kind=kind, figs=figs, handcrafted=False)
    out.setdefault("mood", "green")
    out.setdefault("preset", {})
    out.setdefault("acts", [])
    out.setdefault("nodes", {})
    if out["kind"] not in backdrops.KINDS and not out["kind"].startswith("ambient:"):
        out["kind"] = "street"
    return out
