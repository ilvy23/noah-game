"""story_game.py - plays the story in story/story.json (prologue, 7 chapters, boss, three endings, credits).

All text comes from story/story.json (exported from the Drehbuch). This module only does the flow:
places, scenes, decision trees, flags, chapter progress, variants, audio cues, the timed ending and the credits.
All input/output goes through an IO object so the whole game can be played by a test.
"""
import chain
import json
import os
import shutil
import sys
import time

import ambient_fx
import ascii_art
import audio
import boss_ui
import credits
import decision_fx
import menu_art
import cine_fx
import mika_ending
import portraits
import scene_play
import ui

HERE = os.path.dirname(os.path.abspath(__file__))
STORY = os.path.join(HERE, "story", "story.json")
SAVE = os.path.join(HERE, "save_story.json")

PLACE_NAMES = {"lunuen": "Lünen (town)", "nook": "the Nook", "haus": "your house", "gymnasium": "the Gymnasium",
               "wald": "the forest", "see": "the lake", "schloss": "the castle"}
SCENE_PLACE = {
    "k6.noah_clair": "nook",
    "k1.nook_noah": "nook", "k1.see_mika": "see", "k2.connor_1": "lunuen", "k2.noah_nook": "nook",
    "k2.gymnasium_connor": "gymnasium", "k3.noah_verfolgt": "wald", "k3.connor_2": "lunuen", "k3.mika": "see",
    "k4.anwerbung": "see", "k4.mika_reaktion": "see", "k4.noah_angst": "nook", "k6.mika_froh": "see",
}
CHAPTER_SCENES = {1: ["k1.nook_noah", "k1.see_mika"], 2: ["k2.connor_1", "k2.noah_nook", "k2.gymnasium_connor"],
                  3: ["k3.noah_verfolgt", "k3.connor_2", "k3.mika"], 4: ["k4.anwerbung", "k4.mika_reaktion", "k4.noah_angst"],
                  5: [], 6: ["k6.mika_froh"], 7: []}
# Chapter progress: the MUST scenes plus any NEED scenes of the POOL (so there are many ways forward, not one path)
MUST = {1: {"k1.nook_noah"}, 4: {"k4.anwerbung"}, 5: {"k5.tesserakt"}, 6: {"k6.traum"}}
POOL = {1: ["k1.nook_noah", "k1.see_mika", "k1.haus_nacht", "k1.kirche_fenster"],
        2: ["k2.connor_1", "k2.noah_nook", "k2.gymnasium_connor", "k2.baeckerei", "k2.schulhof", "k2.dachboden"],
        3: ["k3.noah_verfolgt", "k3.mika", "k3.connor_2", "k3.lichtung", "k3.nook_leer", "k3.haus_wand"],
        4: ["k4.anwerbung", "k4.mika_reaktion", "k4.noah_angst", "k4.berg", "k4.ritualzimmer"],
        5: ["k5.tesserakt"], 6: ["k6.traum", "k6.mika_froh", "k6.noah_clair"]}
NEED = {1: 2, 2: 3, 3: 3, 4: 2, 5: 1, 6: 2}
# scenes the player starts from a menu entry: sid -> (place, label)
ENTRY = {
    "k1.haus_nacht": ("haus", "Listen to the house in the dark"), "k1.kirche_fenster": ("lunuen", "Walk up to the church window"),
    "k2.baeckerei": ("lunuen", "Step into the bakery"), "k2.schulhof": ("gymnasium", "Watch the schoolyard"),
    "k2.dachboden": ("haus", "Climb up to the attic"),
    "k3.lichtung": ("wald", "Follow the path to the clearing"), "k3.nook_leer": ("nook", "Search the empty Nook"),
    "k3.haus_wand": ("haus", "Press your ear against the humming wall"),
    "k4.berg": ("wald", "Climb up the burnt hill"), "k4.ritualzimmer": ("haus", "Step into the ritual room"),
    "k5.tesserakt": ("schloss", "Search the east wing"), "k6.traum": ("haus", "Go to bed with the cube in your pocket"),
    "k6.noah_clair": ("nook", "Visit the Nook after dark"),          # the scene had no way in at all
}
NEEDS = {"k2.gymnasium_connor": "k2.connor_1",         # the scene starts "as calm as he was in the church"
         "k3.connor_2": "k2.connor_1", "k4.mika_reaktion": "k4.anwerbung", "k6.mika_froh": "k6.traum", "k6.noah_clair": "k6.traum"}
AUDIO_SCENE = {"k5.tesserakt": "keller", "k6.traum": "traum", "k6.noah_clair": "clair"}   # scenes with a song of their own
# reaching a node sets a flag / raises Mika's hint level / makes Mika's smoke sequence play
FLAG_AT = {("k4.anwerbung", "n2"): "joined", ("k4.anwerbung", "n5"): "joined", ("k4.anwerbung", "n6"): "joined",
           ("k5.tuer", "n2"): "door_open", ("k5.tesserakt", "n2"): "tesseract",
           ("k6.traum", "n12"): "note", ("k6.traum", "n13"): "note", ("k6.noah_clair", "n7"): "bond", ("k6.noah_clair", "n8"): "bond", ("k2.connor_1", "n5"): "invited"}
HINT_AT = {("k1.see_mika", "n6"): 1, ("k1.see_mika", "n7"): 1, ("k1.see_mika", "n8"): 1, ("k3.mika", "n2"): 1, ("k3.mika", "n3"): 2,
           ("k3.mika", "n5"): 2, ("k3.mika", "n6"): 2, ("k4.mika_reaktion", "n5"): 2, ("k4.mika_reaktion", "n6"): 3,
           ("k6.mika_froh", "n1"): 3}
# place options that only lead to a scene which starts by itself on arrival: never offered as a menu entry
HIDDEN_OPTIONS = {("ort.see.k1", "Walk towards the red dot")}
SMOKE_AT = set()                     # the smoke sound is part of Mika's song now, it starts with his scene
# choices / place options that only make sense once the player has been there: (scene, node, label) or (place text, option) -> requirement
# requirement: "done:<sid>" scene played, "flag:<f>" flag set, "noflag:<f>" flag not set (see Game.req_ok)
CHOICE_REQ = {("k2.connor_1", "n1", "Ask about the man on the lake bench"): "done:k1.see_mika",     # he must have met Mika
              ("k2.connor_1", "n2", "Ask about Dorothy"): "flag:dorothy",                           # he must have heard the name from the baker
              ("k2.baeckerei", "n1", "Take the bread and ask about the man on the lake bench"): "done:k1.see_mika",
              ("k4.mika_reaktion", "n1", "Tell him you joined"): "flag:joined",
              ("k4.mika_reaktion", "n1", "Tell him you refused"): "noflag:joined",
              ("k4.noah_angst", "n1", "Tell him you saw Connor at the lake"): "done:k4.anwerbung",
              ("k6.mika_froh", "n1", "Show him the note"): "flag:note",
              ("k7.noah_vor", "n1", "Put the cube down on the stone"): "flag:tesseract",
              ("k7.noah_vor", "n6", "Hold on to the cube"): "flag:tesseract"}
OPTION_REQ = {("ort.lunuen.k2", "Ask the baker about the man on the lake bench"): "done:k1.see_mika",
              ("ort.haus.k6", "Go to bed with the cube in your pocket"): "noflag:dream_done"}        # the dream is dreamt once
OPTION_FLAG = {("ort.lunuen.k2", "Ask the baker what she knew about Lizzy"): "dorothy"}           # she says the name Dorothy
# ch. 1 only: the places the player has not come across yet are not offered under "Go somewhere else"
UNNAMED = {"k1.kirche_fenster"}        # the man at the window is Connor, but his name is only given in chapter 2: no name label before that
FIRST_PLACES = ("haus", "lunuen")
OPTION_TRIGGER = {("ort.schloss.k5", "Search the east wing"): "k5.tuer",
                  ("ort.haus.k6", "Go to bed with the cube in your pocket"): "k6.traum"}
try:                                                    # scenes added through story_extra.py
    import story_extra as _x
    ENTRY.update(_x.ENTRY)
    for _ch, _l in _x.POOL.items():
        POOL[_ch] = POOL.get(_ch, []) + [i for i in _l if i not in POOL.get(_ch, [])]
    NEEDS.update(_x.NEEDS)
    FLAG_AT.update(getattr(_x, "FLAG_AT", {}))
    ENDING_QUOTES = list(getattr(_x, "ENDING_QUOTES", []))
except ImportError:
    ENDING_QUOTES = []
WHO = {"noah": "noah", "mika": "mika", "connor": "connor"}
VARIANT_ORDER = ["tesserakt", "traum", "beitritt", "mika_hint", "begegnung", "wiederbesuch", "bond"]


class RealIO:
    sp = None                                       # the running animated scene (scene_play.Session), None = the old text view
    _hinted = False

    def __init__(self, mixer=None):
        self.mixer = mixer

    # ---- animated scenes (scene_play): picture + figures + bubbles; only on a real terminal of at least 120x40, else the old text view
    def scene_begin(self, info):
        if self.sp is not None:
            return True
        if not sys.stdout.isatty() or os.environ.get("FOLK_PLAIN"):
            return False
        cols, rows = shutil.get_terminal_size((100, 40))
        if cols < scene_play.MIN_COLS or rows < scene_play.MIN_ROWS:
            if not RealIO._hinted:
                RealIO._hinted = True
                print("  (enlarge the window to at least %dx%d to see the scenes animated)" % (scene_play.MIN_COLS, scene_play.MIN_ROWS))
            return False
        self.sp = scene_play.Session(mika_ending.Ctx(self, self.mixer), info)
        self.sp.open()
        return True

    def scene_node(self, nid):
        if self.sp is not None:
            self.sp.set_node(nid)

    def scene_end(self):
        sp, self.sp = self.sp, None
        if sp is not None:
            sp.close()

    NAMES = {"noah": "Noah", "mika": "Mika", "connor": "Connor", "noah2": "Noah", "noah3": "Noah", "system": ""}

    def show(self, text, who="narrator"):
        if self.sp is not None:
            self.sp.show(text, who)
            return
        with ui.Keys() as keys:
            ui.boxed(text, who, label=self.NAMES.get(who, ""), keys=keys, mixer=self.mixer)

    def pick(self, options, aliases=None):
        if self.sp is not None:
            return self.sp.pick(options)
        return ui.choose("", options, aliases=aliases)

    def timed_pick(self, options, seconds, on_tick=None):
        """Arrow keys + Enter within `seconds`; None on timeout. on_tick(elapsed) is called about once a second."""
        if self.sp is not None:
            return self.sp.timed(options, seconds, on_tick)
        with ui.Keys() as keys:
            if not keys.raw:
                return ui.choose("", options)
            pos, t0, last = 0, time.monotonic(), 0
            for i, o in enumerate(options):
                print("  %s %d) %s" % (">" if i == pos else " ", i + 1, o))
            while True:
                el = time.monotonic() - t0
                if el >= seconds:
                    return None
                if on_tick and int(el) > last:
                    last = int(el)
                    on_tick(last)
                k = keys.read(timeout=0.1)
                if k in ("up", "down"):
                    pos = (pos + (1 if k == "down" else -1)) % len(options)
                    print("\033[%dA" % len(options), end="")
                    for i, o in enumerate(options):
                        print("\r\033[K  %s %d) %s" % (">" if i == pos else " ", i + 1, o))
                elif k == "enter":
                    return pos
                elif k and k.isdigit() and 1 <= int(k) <= len(options):
                    return int(k) - 1

    def art(self, place, chapter):
        if self.sp is not None:
            return
        name = ascii_art.PLACE_ART.get(place)
        if name and ascii_art.pick_size() and sys.stdout.isatty():
            sys.stdout.write("\033[2J\033[H")                  # every place is a fresh screen: picture on top, text below
            ascii_art.show(name, chapter)

    PORTRAIT = {"noah": "noah_green", "mika": "mika", "connor": "connor"}

    def portrait(self, who):
        """The bust of the speaking character above the text, once per scene, only when the window is big enough."""
        name = self.PORTRAIT.get(who)
        if not name or not sys.stdout.isatty() or self.sp is not None:
            return
        size = portraits.pick_size(*shutil.get_terminal_size((100, 40)))
        lines = portraits.portrait(name, size, ascii_art.has_truecolor()) if size else []
        if lines:
            pad = " " * max(0, (shutil.get_terminal_size((100, 40)).columns - portraits.BIG[0] // (1 if size == "big" else 2)) // 2)
            sys.stdout.write("\033[2J\033[H" + "\n".join(pad + l for l in lines) + "\n")
            sys.stdout.flush()

    def pause(self):
        with ui.Keys() as keys:
            if keys.raw:
                while keys.read(timeout=None) not in ("enter", " "):
                    pass
            else:
                try:
                    input("")
                except EOFError:
                    pass


def flush_stdin():
    """Throw away keys typed so far (a real terminal only)."""
    try:
        import termios
        if sys.stdin.isatty():
            termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass


class Game:
    def __init__(self, io=None, story=None, mixer=None, boss_runner=None, credits_runner=None, save_path=None, seed=None):
        self.io = io or RealIO(mixer)
        self.story = story if story is not None else json.load(open(STORY, encoding="utf-8"))
        self.mixer = mixer
        self.boss_runner = boss_runner or self._default_boss
        self.credits_runner = credits_runner or self._default_credits
        self.sleep = time.sleep                     # tests replace it so the timed cinematics run instantly
        self.cinematics = sys.stdout.isatty()       # the full-screen ASCII scenes (cine_fx) only run on a real terminal
        self.ultra_unused = False                   # set after the fight: ULTRA TESSERACT unlocked and never used (Mika's ending)
        self.save_path = save_path or SAVE          # looked up now, so a changed SAVE (tests) is honoured
        self.seed = seed
        self.st = {"chapter": 1, "place": "haus", "flags": [], "done": [], "visited": [], "noah": 0, "hint": 0, "prologue": False}

    # ---------------------------------------------------------------- helpers
    def flag(self, f):
        if f not in self.st["flags"]:
            self.st["flags"].append(f)

    def has(self, f):
        return f in self.st["flags"]

    def audio(self, fn, *a):
        if self.mixer is not None:
            getattr(self.mixer, fn)(*a)

    def save(self):
        with open(self.save_path, "w", encoding="utf-8") as fh:
            json.dump(self.st, fh)

    def load(self):
        try:
            with open(self.save_path, encoding="utf-8") as fh:
                self.st.update(json.load(fh))
            if "known" not in self.st:
                self.st["known"] = list(PLACE_NAMES)        # a save from before places were discovered: nothing is hidden
            return True
        except (OSError, ValueError):
            return False

    def scene(self, sid):
        return self.story.get(sid) or {}

    def who_of(self, sid):
        figs = self.scene(sid).get("figuren") or []
        return WHO.get(figs[0], "narrator") if figs else "narrator"

    def variant(self, sid):                           # "beitritt" = joined, or invited AND past the supper (chapter 3)
        """The variant text for the first matching condition, or None."""
        vs = self.scene(sid).get("varianten") or {}
        ok = {"tesserakt": self.has("tesseract"), "traum": self.has("dream_done"),
              "beitritt": self.has("joined") or (self.has("invited") and self.st["chapter"] >= 3),
              "mika_hint": self.st["hint"] >= 2,
              "begegnung": self.st["noah"] >= 2, "wiederbesuch": self.st["place"] in self.st["visited"], "bond": self.has("bond")}
        for name in VARIANT_ORDER:
            if name in vs and ok.get(name):
                return vs[name]
        return None

    def available(self, sid):
        if sid not in self.story or sid in self.st["done"]:
            return False
        if sid in NEEDS and NEEDS[sid] not in self.st["done"]:
            return False
        return not (sid == "k6.mika_froh" and not self.has("dream_done"))

    def req_ok(self, req):
        kind, _, arg = req.partition(":")
        return {"done": lambda: arg in self.st["done"], "flag": lambda: self.has(arg), "noflag": lambda: not self.has(arg)}[kind]()

    def know(self, place):
        k = self.st.setdefault("known", list(FIRST_PLACES))
        if place not in k:
            k.append(place)

    def destinations(self, place):
        """Where "Go somewhere else" leads: in chapter 1 only what the player has come across (the town first, the Nook on the road home,
        the lake from the bedroom window or after Noah), later every place of the chapter."""
        out = [p for p in self.places() if p != place]
        if self.st["chapter"] == 1:
            out = [p for p in out if p in self.st.get("known", FIRST_PLACES)]
        return out

    def where(self, sid):
        return (ENTRY.get(sid) or (SCENE_PLACE.get(sid), None))[0]

    def next_goal(self):
        """The scene that moves the story forward next (a must scene first, then the nearest pool scene)."""
        ch, done = self.st["chapter"], set(self.st["done"])
        must = [s for s in sorted(MUST.get(ch, ())) if s not in done]
        if must:
            return must[0]
        pool = [s for s in POOL.get(ch, []) if self.available(s)]
        return pool[0] if pool else None

    def hint_text(self):
        sid = self.next_goal()
        if not sid:
            return "Nothing more to find here. The valley is waiting for you to move on."
        place, label = ENTRY.get(sid, (SCENE_PLACE.get(sid), None))
        if place:
            self.know(place)                           # the hint names it, so it must be reachable
        where = PLACE_NAMES.get(place, "somewhere")
        return "Something is waiting for you at %s%s." % (where, ": %s" % label.lower() if label else "")

    def side_entries(self, place):
        ch = self.st["chapter"]
        return [(ENTRY[s][1], s) for s in POOL.get(ch, []) if s in ENTRY and ENTRY[s][0] == place and self.available(s)
                and s not in ("k5.tesserakt", "k6.traum")]

    def places(self):
        ch = self.st["chapter"]
        out = []
        for sid, s in self.story.items():
            if sid.startswith("ort.") and sid.endswith(".k%d" % ch) and not s.get("entfaellt"):
                out.append(s["ort"])
        return out

    # ---------------------------------------------------------------- scenes
    def scene_info(self, sid, place=None):
        """What scene_play needs to pick a picture and the figures for a scene (or a place text: sid ort.<place>.k<n>)."""
        return {"sid": sid, "scene": self.scene(sid), "place": place or self.where(sid), "chapter": self.st["chapter"]}

    def animated(self, info):
        """Open the animated scene view when the IO has one (a real terminal of 120x40+); the caller must call scene_end() when it is True."""
        return bool(getattr(self.io, "scene_begin", lambda i: False)(info))

    def play_tree(self, sid):
        if not self.scene(sid).get("baum"):
            return
        begun = self.animated(self.scene_info(sid))
        try:
            self._play_tree(sid, begun)
        finally:
            if begun:
                self.io.scene_end()

    def _play_tree(self, sid, begun):
        sc = self.scene(sid)
        tree = sc.get("baum")
        who = self.who_of(sid)
        if not begun:
            getattr(self.io, "portrait", lambda w: None)(who)
        if sid in AUDIO_SCENE:
            self.audio("scene_start", AUDIO_SCENE[sid])
        elif who == "noah":
            self.st["noah"] += 1
            self.audio("scene_start", "noah", "alt" if self.st["noah"] in (2, 3) else "main")
        elif who == "connor":
            self.audio("scene_start", "connor")
        elif who == "mika":
            self.audio("scene_start", "mika")                 # Mika's own song from the very first moment
        nid = tree["start"]
        var = self.variant(sid)
        first = True
        while nid:
            node = tree["knoten"][nid]
            text = var if (first and var) else node["text"]
            first = False
            getattr(self.io, "scene_node", lambda n: None)(nid)
            self.io.show(text, "narrator" if sid in UNNAMED and "k2.connor_1" not in self.st["done"] else who)
            for f in [FLAG_AT.get((sid, nid))]:
                if f:
                    self.flag(f)
            lvl = HINT_AT.get((sid, nid))
            if lvl:
                self.st["hint"] = max(self.st["hint"], lvl)
            if (sid, nid) in SMOKE_AT:
                self.audio("mika_smoke")
            wahl = [c for c in node.get("wahl") or [] if (sid, nid, c["label"]) not in CHOICE_REQ or self.req_ok(CHOICE_REQ[(sid, nid, c["label"])])]
            if not wahl:
                break
            i = self.io.pick([c["label"] for c in wahl])
            nid = wahl[i]["ziel"]
        if who in ("noah", "connor", "mika") or sid in AUDIO_SCENE:
            self.audio("scene_end")
        self.st["done"].append(sid)
        self.save()

    def play_text(self, sid):
        text, kind = self.scene(sid).get("text", ""), ambient_fx.SCENE_KIND.get(sid)
        if kind and text.strip():                      # the stairs and the cellar are animated scenes with bubbles, not plain text
            ambient_fx.run_text(mika_ending.Ctx(self.io, self.mixer, sleep=self.sleep, fps=None if self.sleep is time.sleep else 2), kind, text)
        else:
            begun = self.animated(self.scene_info(sid))
            try:
                if not begun:
                    getattr(self.io, "portrait", lambda w: None)(self.who_of(sid))
                self.io.show(text, self.who_of(sid))
            finally:
                if begun:
                    self.io.scene_end()
        self.st["done"].append(sid)

    def enter_place(self, place, announce=True):
        self.st["place"] = place
        self.know(place)
        if place == "lunuen":
            self.know("nook")                          # the hut is on the road home from the town
        elif place == "nook":
            self.know("see")                           # Noah's way to the lake
        self.audio("enter_place", place)
        self.arrive()

    def arrive(self):
        """Show the place text once per chapter and place, then play the scenes that start by themselves."""
        ch, place = self.st["chapter"], self.st["place"]
        key = "%d:%s" % (ch, place)
        if key not in self.st.setdefault("shown", []):
            sid = "ort.%s.k%d" % (place, ch)
            sc = self.scene(sid)
            begun = self.animated(self.scene_info(sid, place))
            try:
                getattr(self.io, "art", lambda p, c: None)(place, ch)
                if sc and not sc.get("entfaellt"):
                    self.io.show(self.variant(sid) or sc.get("text", ""))
            finally:
                if begun:
                    self.io.scene_end()
            self.st["shown"].append(key)
        if place not in self.st["visited"]:
            self.st["visited"].append(place)
        self.auto_scenes()

    def auto_scenes(self):
        while True:
            ch, place = self.st["chapter"], self.st["place"]
            nxt = None
            for s in CHAPTER_SCENES.get(ch, []):
                if SCENE_PLACE.get(s) == place and s not in self.st["done"] and \
                        (s not in NEEDS or NEEDS[s] in self.st["done"]) and not (s == "k6.mika_froh" and not self.has("dream_done")):
                    nxt = s
                    break
            if nxt is None:
                return
            self.play_tree(nxt) if self.scene(nxt).get("baum") else self.play_text(nxt)
            self.check_chapter()
            if self.st["chapter"] != ch:
                self.arrive_new_chapter()
                return

    def arrive_new_chapter(self):
        self.audio("enter_place", self.st["place"])
        self.arrive()

    def after_scene(self, sid):
        if sid == "k3.noah_verfolgt":
            pass
        self.check_chapter()

    def run_option(self, place, opt):
        ch = self.st["chapter"]
        sid = "ort.%s.k%d" % (place, ch)
        begun = self.animated(self.scene_info(sid, place))
        try:
            self.io.show(opt["text"])
        finally:
            if begun:
                self.io.scene_end()
        if (sid, opt["name"]) in OPTION_FLAG:
            self.flag(OPTION_FLAG[(sid, opt["name"])])
        if (sid, opt["name"]) == ("ort.haus.k1", "Go upstairs to the bedroom"):
            self.know("see")                           # the window looks out over the lake
        trig = OPTION_TRIGGER.get((sid, opt["name"]))
        if trig == "k5.tuer":
            self.play_tree("k5.tuer")
            if self.has("door_open"):
                self.play_tree("k5.tesserakt")
                self.flag("tesseract")                     # the cube is always taken (there is no "leave it" any more)
                self.play_text("k5.draussen")
                self.check_chapter()
        elif trig == "k6.traum" and self.has("tesseract") and not self.has("dream_done"):
            self.play_tree("k6.traum")
            self.flag("dream_done")
            if self.has("note"):
                self.play_text("k6.zettel")
            self.check_chapter()

    def check_chapter(self):
        ch = self.st["chapter"]
        done = set(self.st["done"])
        if ch in (6,) and self.has("tesseract") and not self.has("dream_done"):
            return
        if ch < 7 and MUST.get(ch, set()) <= done and len(done & set(POOL.get(ch, []))) >= NEED.get(ch, 1) \
                and (ch != 6 or self.has("tesseract")):
            nxt = ch + 1
            if nxt == 6 and not self.has("tesseract"):
                nxt = 7
            self.st["chapter"] = nxt
            self.st["visited"] = []
            self.st["shown"] = []
            self.io.show("\n— chapter %d —" % nxt, "system")
            if nxt == 7:
                self.st["place"] = "haus"
            self.save()

    def jump(self, sid):
        """Start at a scene (for testing/writing): sets chapter, place and the flags the story would have by then."""
        sc = self.scene(sid)
        ch = sc.get("kapitel") or 1
        place = (ENTRY.get(sid) or (None,))[0] or SCENE_PLACE.get(sid) or sc.get("ort") or ("schloss" if ch >= 5 else "haus")
        self.finale_from = None
        if sid.startswith("k7") or sid in ("credits",):
            ch, place = 7, "schloss"
            self.finale_from = {"k7.anreise": "anreise", "k7.noah_vor": "noah_vor", "k7.entscheidung": "decision",
                                "k7.ending_let": "ending:let-it-live", "k7.ending_slaughter": "ending:slaughter-it",
                                "k7.ending_3": "ending:ending-3", "credits": "ending:let-it-live"}.get(sid, "boss" if "boss" in sid else "ort")
        self.st.update(chapter=ch, place=place, prologue=True, visited=[], shown=[], known=list(PLACE_NAMES))
        for c in range(1, ch):
            for r in list(MUST.get(c, ())) + [x for x in POOL.get(c, []) if x not in MUST.get(c, ())][:NEED.get(c, 1)]:
                if r not in self.st["done"]:
                    self.st["done"].append(r)
        if ch >= 4:
            self.flag("invited")
        if ch >= 5:
            self.flag("door_open")
        if ch >= 6:
            self.flag("tesseract")
        if ch >= 7:
            self.flag("dream_done")
            self.flag("note")
        self.pending = None if self.finale_from else (sid if sc.get("baum") or sc.get("text") else None)
        return sid

    # ---------------------------------------------------------------- main loop
    def run(self):
        if not self.st["prologue"]:
            self.audio("enter_place", "haus")
            begun = self.animated(self.scene_info("prolog", "haus"))
            try:
                self.io.show(self.scene("prolog").get("text", ""))
            finally:
                if begun:
                    self.io.scene_end()
            self.st["prologue"] = True
            self.io.pause()
        if getattr(self, "finale_from", None):
            step, self.finale_from = self.finale_from, None
            return self.finale(step)
        pending = getattr(self, "pending", None)
        self.audio("enter_place", self.st["place"])
        if pending:
            self.pending = None
            self.st.setdefault("shown", []).append("%d:%s" % (self.st["chapter"], self.st["place"]))
            getattr(self.io, "art", lambda p, c: None)(self.st["place"], self.st["chapter"])
            if pending in self.st["done"]:
                self.st["done"].remove(pending)
            self.play_tree(pending) if self.scene(pending).get("baum") else self.play_text(pending)
            self.check_chapter()
        else:
            self.enter_place(self.st["place"])
        while True:
            self.arrive()
            ch = self.st["chapter"]
            if ch == 7 and self.st["place"] == "schloss":
                return self.finale()
            place = self.st["place"]
            sc = self.scene("ort.%s.k%d" % (place, ch))
            sid_ort = "ort.%s.k%d" % (place, ch)
            opts = [(o["name"], ("opt", o)) for o in (sc.get("optionen") or [])
                    if (sid_ort, o["name"]) not in HIDDEN_OPTIONS and ((sid_ort, o["name"]) not in OPTION_REQ or self.req_ok(OPTION_REQ[(sid_ort, o["name"])]))]
            if ch == 6 and place == "haus" and self.has("tesseract") and not self.has("dream_done") and \
                    not any(o["name"].startswith("Go to bed") for o in (sc.get("optionen") or [])):
                pass
            for label, sid in self.side_entries(place):
                opts.append((label, ("scene", sid)))
            opts.append(("What should I do now?", ("hint", None)))
            opts.append(("Go somewhere else", ("go", None)))
            opts.append(("Save and quit", ("quit", None)))
            i = self.io.pick([o[0] for o in opts])
            kind, val = opts[i][1]
            if kind == "opt":
                self.run_option(place, val)
            elif kind == "scene":
                self.play_tree(val) if self.scene(val).get("baum") else self.play_text(val)
                self.check_chapter()
            elif kind == "hint":
                self.io.show(self.hint_text(), "system")
            elif kind == "go":
                dests = self.destinations(place)
                j = self.io.pick([PLACE_NAMES[p] for p in dests] + ["stay here"])
                if j < len(dests):
                    self.enter_place(dests[j])
            else:
                self.save()
                return "quit"

    # ---------------------------------------------------------------- finale
    intro = True
    ultra = False                                  # --fight --ultra: the ULTRA TESSERACT is unlocked from the start
    start_phase = 1                                # --fight --phase 3: begin in that phase (for trying a phase quickly)

    def boss_song_gone(self):
        """The fight is over: whatever fade the fight screen started finishes, anything still playing is faded out, and only then does the
        game go on (so two songs are never audible together)."""
        self.audio("wait_silent")
        self.audio("fade_out")
        self.audio("wait_silent")

    def cine(self, name):
        """One of the full-screen ASCII scenes of cine_fx (defeat, decision, ending-let ...). Skipped headless; a broken scene must never stop the game."""
        if not self.cinematics:
            return False
        try:
            cine_fx.run_named(mika_ending.Ctx(self.io, self.mixer, sleep=self.sleep), name)
            return True
        except KeyboardInterrupt:
            raise
        except Exception:
            return False

    def fight_only(self):
        """Straight into the boss fight (for testing), then the decision, ending and credits."""
        self.flag("tesseract")
        self.flag("dream_done")
        self.flag("note")
        self.st.update(chapter=7, place="schloss", prologue=True)
        self.audio("enter_place", "schloss")
        while self.boss_runner(self.boss_lines(), 1.0) != "won":
            self.io.show("[TEXT: boss.defeat]", "system")
        self.boss_song_gone()                          # the boss song is silent BEFORE the defeat scene, the decision or any ending song
        self.cine("defeat")                            # Noah comes apart (scene) in the quiet
        end = self.decision()
        self.show_ending(end)
        return end

    def _default_boss(self, lines, power):
        try:
            texts = json.load(open(os.path.join(HERE, "story", "boss_texts.json"), encoding="utf-8"))
        except (OSError, ValueError):
            texts = {}
        res = boss_ui.play(lines=lines, power=power, mixer=self.mixer, has_tesseract=self.has("tesseract"), texts=texts,
                           intro=self.intro, ultra=self.ultra, phase=self.start_phase, has=self.has)
        self.ultra_unused = boss_ui.play.last.ultra_unused()
        return res

    def _default_credits(self, blocks, seconds):
        credits.roll(blocks, seconds)

    def boss_lines(self):
        out = {}
        for i in range(1, 5):
            z = self.scene("k7.boss_p%d" % i).get("zeilen") or []
            out[i] = [l.replace("||", " ").replace("  ", " ") for l in z]
        return out

    def finale(self, start="ort"):
        """The last chapter in order: place, descent, Noah, the fight, the decision, the ending. `start` skips ahead."""
        order = ["ort", "anreise", "noah_vor", "boss", "decision"]
        self.audio("enter_place", "schloss")
        if start.startswith("ending:"):
            if start == "ending:mika-ultra":              # the jump carries the spared-Noah text the decision would have shown (drawn as bubbles later)
                self.spared_text = self.scene("k7.entscheidung")["baum"]["knoten"]["n2"]["text"]
            self.show_ending(start.split(":", 1)[1])
            return start.split(":", 1)[1]
        i = order.index(start) if start in order else 0
        if i <= 0:
            begun = self.animated(self.scene_info("ort.schloss.k7", "schloss"))
            try:
                self.io.show(self.scene("ort.schloss.k7").get("text", ""))
            finally:
                if begun:
                    self.io.scene_end()
        if i <= 1:
            self.play_text("k7.anreise")
        if i <= 2:
            self.play_tree("k7.noah_vor")
        if i <= 3:
            power = 1.0 if self.has("tesseract") else 0.3
            while self.boss_runner(self.boss_lines(), power) != "won":
                self.io.show("[TEXT: boss.defeat]", "system")
            self.boss_song_gone()                      # the boss song is silent BEFORE the defeat scene, the decision or any ending song
            self.cine("defeat")                        # Noah comes apart (scene) in the quiet
        end = self.decision()
        self.show_ending(end)
        return end

    def decision(self):
        self.cine("decision")                                  # the quiet before the choice (the 30 s timer below is untouched)
        tree = self.scene("k7.entscheidung")["baum"]["knoten"]
        n1 = tree["n1"]
        quotes = [t for flag, t in ENDING_QUOTES if self.has(flag)]
        if quotes:                                             # the best moments come right before the choice (peak-end)
            begun = self.animated(self.scene_info("k7.entscheidung"))      # the candle cellar behind the quotes
            try:
                self.io.show("\n\n".join(quotes), "noah")
            finally:
                if begun:
                    self.io.scene_end()
        text1 = self.variant("k7.entscheidung") or n1["text"]
        warns = {10: "k7.warn10", 20: "k7.warn20"}
        opts = [c["label"] for c in n1["wahl"] if c["ziel"]]
        ctx = mika_ending.Ctx(self.io, self.mixer, sleep=self.sleep)
        if self.cinematics and sys.stdin.isatty() and decision_fx.available(ctx):
            # real terminal: the 30 s choice is an overlay on the animated cellar (decision_fx); the same timer, keys and ending-3 rule
            i = decision_fx.timed_pick_scene(ctx, text1, opts, 30, {s: self.scene(w).get("text", "") for s, w in warns.items() if self.scene(w).get("text", "").strip()})
        else:
            self.io.show(text1, "noah")

            def tick(sec):
                if sec in warns:
                    t = self.scene(warns[sec]).get("text", "")
                    if t.strip():
                        self.io.show(t, "noah3")
            i = self.io.timed_pick(opts, 30, tick)
        if i is None:
            return "ending-3"
        text = tree[n1["wahl"][i]["ziel"]]["text"]
        end = ["let-it-live", "slaughter-it"][i]
        if end == "let-it-live" and self.ultra_unused:
            self.spared_text = text                                # the hidden ending draws it as speech bubbles on its first scene, never on a bare terminal
            return "mika-ultra"
        self.io.show(text, "noah")
        return end

    def show_ending(self, name):
        if name == "mika-ultra":
            return self.show_mika_ending()
        sid = {"let-it-live": "k7.ending_let", "slaughter-it": "k7.ending_slaughter", "ending-3": "k7.ending_3"}[name]
        self.audio("fade_out")                         # the fight music goes; the ending text is read in silence
        played = self.cine({"let-it-live": "ending-let", "slaughter-it": "ending-slaughter", "ending-3": "ending-3"}[name])
        if not played:                                 # the animation plays the whole ending text as bubbles itself; the plain text only when it did not run (tests, pipes)
            self.io.show(self.scene(sid).get("text", ""), "noah3" if name != "let-it-live" else "noah")
        self.io.pause()
        blocks = list(self.scene("credits").get("blocks") or [])
        music = credits.music_block(os.path.join(HERE, "soundtracks", "SOURCES.txt"))
        if music:
            blocks.append(music)
        self.audio("ending", name)                     # the song starts exactly when the credits start to rise
        self.credits_runner(blocks, self.ending_seconds(name))
        self.audio("stop")
        try:
            os.remove(self.save_path)
        except OSError:
            pass

    def show_mika_ending(self):
        """The hidden ending: six scenes (mika_ending.py), the song runs from the bench scene on, then the credits."""
        self.audio("fade_out")
        mika_ending.run(mika_ending.Ctx(self.io, self.mixer, sleep=self.sleep, fps=None if self.sleep is time.sleep else 2,
                                        spared=getattr(self, "spared_text", None)))
        flush_stdin()                                  # the credits start by themselves: no key is needed and none typed earlier is consumed
        blocks = list(self.scene("credits").get("blocks") or [])
        music = credits.music_block(os.path.join(HERE, "soundtracks", "SOURCES.txt"))
        if music:
            blocks.append(music)
        self.audio("ending", "mika-ultra")             # the special ending song (soundtracks/ending-special.*, else Mika's song) starts WITH the credits
        try:
            self.credits_runner(blocks, self.ending_seconds("mika-ultra"))
        finally:
            chain.end(sys.stdout)
        self.audio("stop")
        try:
            os.remove(self.save_path)
        except OSError:
            pass

    def ending_seconds(self, name):
        track = audio.ending_track(name)
        d = audio.duration(audio.find_file(track)) if track else None
        return d or 200.0


SHORTCUTS = {"--mika": "k1.see_mika", "--mika2": "k3.mika", "--noah": "k1.nook_noah", "--connor": "k2.connor_1",
             "--anwerbung": "k4.anwerbung", "--castle": "k5.tuer", "--dream": "k6.traum", "--boss": "k7.noah_vor",
             "--ending": "k7.entscheidung"}      # also: --fight (straight into the boss fight, --nointro skips the 52 s intro, --phase 1-4 starts in that phase)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--artdemo" in argv:                     # what does MY terminal do with the pictures? (send a screenshot of this)
        import shutil as _sh
        sz = _sh.get_terminal_size()
        print("window %dx%d | picture size: %s | truecolor: %s | TERM=%s COLORTERM=%s" % (
            sz.columns, sz.lines, ascii_art.pick_size(), ascii_art.has_truecolor(), os.environ.get("TERM"), os.environ.get("COLORTERM")))
        print("colour ramp:   " + "".join("\033[48;2;%d;%d;%dm \033[0m" % (i * 255 // 59, 40, 255 - i * 255 // 59) for i in range(60)))
        for nm in ("schloss", "see", "wald"):
            print("\n== %s ==" % nm)
            ascii_art.show(nm, 1, animate=False)
        return
    if "--list" in argv:
        print("jump: python3 play.py --scene <id>   or one of: " + " ".join(SHORTCUTS))
        for sid, s in json.load(open(STORY, encoding="utf-8")).items():
            print("  %-22s %s" % (sid, s.get("art", "")))
        return
    start = None
    if "--cinema" in argv:                      # every scene of the game, played one after the other with next / previous keys
        import scene_cinema
        first = argv[argv.index("--scene") + 1] if "--scene" in argv and argv.index("--scene") + 1 < len(argv) else None
        mixer = audio.get()
        try:
            scene_cinema.run(first, mixer)
        finally:
            mixer.stop()
        return
    if "--gallery" in argv:
        import gallery
        gallery.run()
        return
    fight = "--fight" in argv
    for i, a in enumerate(argv):
        if a == "--scene" and i + 1 < len(argv):
            start = argv[i + 1]
        elif a in SHORTCUTS:
            start = SHORTCUTS[a]
    mixer = audio.get()
    if ascii_art.pick_size() and sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
    a = menu_art.pick()
    print("\n" + ("%s    %s    %s    %s" % (a["noah"], a["mika"], a["connor"], a["face"])).center(60) + "\n" + a["line"].center(60) + "\n")
    game = Game(mixer=mixer)
    game.intro = "--nointro" not in argv
    game.ultra = "--ultra" in argv
    if "--phase" in argv and argv.index("--phase") + 1 < len(argv) and argv[argv.index("--phase") + 1] in "1234":
        game.start_phase = int(argv[argv.index("--phase") + 1])
    if "--mika-ending" in argv or "--only" in argv:      # straight into the hidden Mika ending (spared-Noah text, six scenes, credits)
        game.jump("k7.ending_let")
        game.finale_from = "ending:mika-ultra"
        if "--only" in argv and argv.index("--only") + 1 < len(argv):      # --only burn|slash|awake|fourth|valley|bench: just that scene, then stop
            name = argv[argv.index("--only") + 1]
            if name not in mika_ending.ONLY:
                print("--only %s: one of %s" % (name, " ".join(mika_ending.ONLY)))
                return
            try:
                mika_ending.run(mika_ending.Ctx(game.io, mixer, sleep=game.sleep), only=name)
            except KeyboardInterrupt:
                print("\n\n  (you close your eyes for a moment.)")
            finally:
                mixer.stop()
            return
        try:
            game.run()
        except KeyboardInterrupt:
            print("\n\n  (you close your eyes for a moment.)")
        finally:
            mixer.stop()
        return
    if fight:
        try:
            game.fight_only()
        except KeyboardInterrupt:
            print("\n\n  (you close your eyes for a moment.)")
        finally:
            mixer.stop()
        return
    if start:
        if start not in game.story:
            print("unknown scene %r (python3 play.py --list)" % start)
            return
        game.jump(start)
    else:
        has_save = os.path.exists(game.save_path)                  # "continue" is only offered when there is something to continue
        options = ["new game"] + (["continue"] if has_save else []) + ["quit"]
        aliases = {"new": 0, "n": 0, "quit": len(options) - 1, "q": len(options) - 1}
        if has_save:
            aliases.update({"continue": 1, "c": 1})
        i = ui.choose("", options, aliases=aliases)
        if options[i] == "quit":
            return
        if options[i] == "continue" and not game.load():
            print("  (the save could not be read. starting fresh.)")
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n\n  (you close your eyes for a moment.)")
        if game.st.get("chapter", 1) < 7:
            game.save()
    finally:
        mixer.stop()


if __name__ == "__main__":
    main()
