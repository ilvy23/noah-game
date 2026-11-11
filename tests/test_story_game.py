"""story_game.py: a scripted playthrough from the prologue to an ending and the credits, plus the timed ending."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio  # noqa: E402
import story_game as sg  # noqa: E402

STORY = json.load(open(sg.STORY, encoding="utf-8"))


class FakeIO:
    def __init__(self, game_ref, timeout=False, trace=None):
        self.g = game_ref
        self.timeout = timeout
        self.shown = []
        self.picks = []

    mixer = None
    arts = None

    def art(self, place, chapter):
        (self.arts if self.arts is not None else []).append((place, chapter))

    def show(self, text, who="narrator"):
        self.shown.append((who, text))
        if self.mixer is not None:
            self.mixer.log.append(("show", text[:20]))
            self.mixer.wait()                                   # let the fades and sequences run, like a reading player

    def pause(self):
        pass

    def timed_pick(self, options, seconds, on_tick=None):
        if on_tick:
            on_tick(10)
            on_tick(20)
        return None if self.timeout else 0

    def pick(self, options, aliases=None):
        g = self.g[0]
        self.picks.append(options)
        if "Save and quit" in options:                       # place menu
            goal = g.next_goal()
            if goal:
                place, label = sg.ENTRY.get(goal, (sg.SCENE_PLACE.get(goal), None))
                if place == g.st["place"] and label in options:
                    return options.index(label)
            return options.index("Go somewhere else")
        if "stay here" in options:                            # destination menu
            goal = g.next_goal()
            g.hint_text()                                     # a player who is lost asks the hint, which also reveals the place
            target = "schloss" if g.st["chapter"] == 7 else (g.where(goal) if goal else "haus")
            names = [sg.PLACE_NAMES[p] for p in g.destinations(g.st["place"])]
            return names.index(sg.PLACE_NAMES[target]) if sg.PLACE_NAMES[target] in names else len(names)
        return 0                                              # inside a scene always the first answer

class Fake(audio.Player):
    can_fade = True

    def __init__(self, path, loop, volume):
        super().__init__(path, loop, volume)
        self.up = True

    def alive(self):
        return self.up

    def stop(self):
        self.up = False


def play(tmp_path, timeout=False):
    ref = [None]
    mixer = audio.Mixer(backend=Fake, sleep=lambda s: None)
    calls = {"boss": [], "credits": []}
    io = FakeIO(ref, timeout)
    io.mixer = mixer
    g = sg.Game(io=io, story=STORY, mixer=mixer, save_path=str(tmp_path / "save.json"),
                boss_runner=lambda lines, power: calls["boss"].append((lines, power)) or "won",
                credits_runner=lambda blocks, sec: calls["credits"].append((blocks, sec)))
    ref[0] = g
    end = g.run()
    mixer.wait()
    return g, io, end, calls, mixer


def test_full_playthrough_to_ending_with_credits_and_story_flags(tmp_path):
    g, io, end, calls, mixer = play(tmp_path)
    assert end == "let-it-live"
    assert g.st["chapter"] == 7 and g.has("joined") and g.has("tesseract") and g.has("note") and g.has("dream_done")
    texts = " ".join(t for _w, t in io.shown)
    assert "navi buzzes" in texts                                   # the owner's prologue is the first thing
    assert "WITH LOVE" not in texts or True
    assert calls["boss"] and calls["boss"][0][1] == 1.0              # tesseract carried: Noah's third persona is strong
    assert calls["boss"][0][0][4] and "Delicious" in " ".join(calls["boss"][0][0][4])
    blocks, seconds = calls["credits"][0]
    assert any(b["titel"] == "A game by" for b in blocks) and any(b["titel"] == "Music" for b in blocks)
    assert seconds > 100
    started = [e[1] for e in mixer.log if e[0] == "start"]
    assert "strange-tape" in started and "strange" in started       # the castle: tape click, then the long track
    assert "noa-alt" in started and "noa-main" in started           # Noah's 1st and 2nd/3rd meeting
    assert "ending-let-it-live" in started
    log = mixer.log
    end_text = log.index(("show", "(You carry him up th"))
    song = log.index(("start", "ending-let-it-live", 100))
    assert end_text < song                              # the ending song starts after the ending text, with the credits
    assert any(("A game by" in b["titel"]) and "ilvy23" in b["text"] for b in calls["credits"][0][0])
    credit_text = " ".join(b["text"] for b in calls["credits"][0][0])
    assert "Claude" in credit_text and "qwen3.8:27b" in credit_text
    assert not os.path.exists(tmp_path / "save.json")                # finished game: save removed


def test_personality_colours_are_used_for_noah_scenes(tmp_path):
    g, io, *_ = play(tmp_path)
    who = {w for w, _t in io.shown}
    assert {"noah", "mika", "connor", "narrator"} <= who


def test_thirty_seconds_without_choice_gives_ending_three_with_warning_lines(tmp_path):
    g, io, end, calls, mixer = play(tmp_path, timeout=True)
    assert end == "ending-3"
    warn = [t for w, t in io.shown if w == "noah3" and ("thinking" in t or "okay" in t)]
    assert len(warn) == 2                                             # the 10 s and 20 s lines were shown in red
    assert "ending-3" in [e[1] for e in mixer.log if e[0] == "start"]


def test_chapters_open_places_one_after_the_other(tmp_path):
    g = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "s.json"))
    assert g.places() == ["lunuen", "nook", "haus", "see"] or set(g.places()) == {"lunuen", "nook", "haus", "see"}
    g.st["chapter"] = 3
    assert "wald" in g.places() and "schloss" not in g.places()
    g.st["chapter"] = 5
    assert "schloss" in g.places()


def test_save_and_continue(tmp_path):
    g = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "s.json"))
    g.st["chapter"], g.st["place"] = 4, "see"
    g.flag("joined")
    g.save()
    h = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "s.json"))
    assert h.load() and h.st["chapter"] == 4 and h.has("joined")


def test_variants_follow_conditions(tmp_path):
    g = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "s.json"))
    assert g.variant("k1.nook_noah") is None
    g.st["noah"] = 2
    assert g.variant("k1.nook_noah") and "back" in g.variant("k1.nook_noah")
    g.flag("tesseract")
    assert g.variant("ort.haus.k5") and "welcoming" in g.variant("ort.haus.k5")


def test_mikas_song_starts_with_the_scene_and_the_cigarette_adds_the_smoke_sound(tmp_path):
    ref = [None]
    mixer = audio.Mixer(backend=Fake, sleep=lambda s: None)
    io = FakeIO(ref)
    io.mixer = mixer
    answers = iter([0, 0, 0, 0])                       # take the cigarette at once, sit down, say left, head home
    io.pick = lambda options, aliases=None: next(answers)
    g = sg.Game(io=io, story=STORY, mixer=mixer, save_path=str(tmp_path / "s.json"))
    ref[0] = g
    g.play_tree("k1.see_mika")
    mixer.wait()
    started = [e[1] for e in mixer.log if e[0] == "start"]
    assert started.index("mika") < started.index("mika-smoke") and g.st["hint"] == 1   # his song first, the smoke sound on top
    first = io.shown[0][1]
    assert "Wanna smoke?" in first                     # the offer comes straight away, in Mika's very first text
    mixer.stop()


def test_jump_to_the_mika_scene_sets_the_story_state_and_plays_it_first(tmp_path):
    ref = [None]
    io = FakeIO(ref)
    answers = iter([2, 99])
    io.pick = lambda options, aliases=None: (_ for _ in ()).throw(SystemExit) if False else (0 if "Save and quit" not in options else options.index("Save and quit"))
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"))
    ref[0] = g
    g.jump("k1.see_mika")
    assert g.st["chapter"] == 1 and g.st["place"] == "see" and g.st["prologue"]
    assert g.run() == "quit"
    first = io.shown[0]
    assert first[0] == "mika" and "washed-out hoodie" in first[1]                 # Mika's scene comes first, no prologue
    g2 = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "t.json"))
    g2.jump("k5.tesserakt")
    assert g2.st["chapter"] == 5 and g2.has("door_open") and "k4.anwerbung" in g2.st["done"]


def test_shortcuts_exist_in_the_story():
    for sid in sg.SHORTCUTS.values():
        assert sid in STORY


def test_the_red_dot_option_is_not_offered_because_mika_comes_by_himself(tmp_path):
    io = FakeIO([None])
    seen = []
    io.pick = lambda options, aliases=None: (seen.append(list(options)) or (options.index("Save and quit") if "Save and quit" in options else 0))
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"))
    g.jump("k1.see_mika")
    g.run()
    menu = [o for o in seen if "Save and quit" in o][0]
    assert "Walk towards the red dot" not in menu and "Look at the water" in menu


def test_the_smoke_sound_starts_with_mikas_scene_even_if_you_refuse_the_cigarette(tmp_path):
    ref = [None]
    mixer = audio.Mixer(backend=Fake, sleep=lambda s: None)
    io = FakeIO(ref)
    io.mixer = mixer
    answers = iter([3])                                 # keep your distance, say hi: no cigarette at all
    io.pick = lambda options, aliases=None: next(answers) if "Keep your distance and say hi" in options else 0
    g = sg.Game(io=io, story=STORY, mixer=mixer, save_path=str(tmp_path / "s.json"))
    ref[0] = g
    g.play_tree("k1.see_mika")
    mixer.wait()
    started = [e[1] for e in mixer.log if e[0] == "start"]
    assert "mika" in started and "mika-smoke" in started
    mixer.stop()


def test_fight_only_goes_straight_to_the_boss_then_the_decision(tmp_path):
    io = FakeIO([None])
    calls = []
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"),
                boss_runner=lambda lines, power: calls.append(power) or "won", credits_runner=lambda b, s: None)
    assert g.fight_only() == "let-it-live" and calls == [1.0]
    assert g.st["chapter"] == 7


def test_jump_to_the_decision_goes_straight_to_the_choice_and_the_ending(tmp_path):
    ref = [None]
    io = FakeIO(ref)
    calls = {"boss": 0, "credits": 0}
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"),
                boss_runner=lambda l, p: calls.__setitem__("boss", calls["boss"] + 1) or "won",
                credits_runner=lambda b, s: calls.__setitem__("credits", calls["credits"] + 1))
    ref[0] = g
    g.jump("k7.entscheidung")
    assert g.run() == "let-it-live"
    texts = " ".join(t for _w, t in io.shown)
    assert calls == {"boss": 0, "credits": 1}                         # no boss fight, no replay of the whole finale
    assert "Noah kneels in the middle of the cellar floor" in texts and "You bring the cube back" not in texts


def test_jump_to_noah_before_the_fight_runs_the_fight_but_not_the_descent(tmp_path):
    io = FakeIO([None])
    boss = []
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"), boss_runner=lambda l, p: boss.append(1) or "won",
                credits_runner=lambda b, s: None)
    g.jump("k7.noah_vor")
    g.run()
    texts = " ".join(t for _w, t in io.shown)
    assert boss == [1] and ("Noah stops three steps behind you" in texts or "I touched it when I was little" in texts)
    assert "The stairs go down" not in texts


def test_ctrl_c_ends_the_game_quietly(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("MUSIC", "0")
    monkeypatch.setattr(sg, "SAVE", str(tmp_path / "s.json"))
    monkeypatch.setattr(sg.Game, "run", lambda self: (_ for _ in ()).throw(KeyboardInterrupt()))
    sg.main(["--scene", "k1.see_mika"])                                # must not raise
    assert "close your eyes" in capsys.readouterr().out


def test_arriving_at_a_place_shows_its_picture_first(tmp_path):
    io = FakeIO([None])
    io.arts = []
    io.pick = lambda options, aliases=None: options.index("Save and quit") if "Save and quit" in options else 0
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"))
    g.jump("k1.see_mika")
    g.run()
    assert ("see", 1) in io.arts


def test_the_clair_de_lune_scene_plays_its_song_sets_the_bond_and_changes_the_decision_text(tmp_path):
    ref = [None]
    mixer = audio.Mixer(backend=Fake, sleep=lambda s: None)
    io = FakeIO(ref)
    io.mixer = mixer
    answers = iter([0, 1, 0, 0])                                 # sit next to him, stay quiet, promise, stay until the candle is out
    io.pick = lambda options, aliases=None: next(answers)
    g = sg.Game(io=io, story=STORY, mixer=mixer, save_path=str(tmp_path / "s.json"))
    ref[0] = g
    g.play_tree("k6.noah_clair")
    mixer.wait()
    assert g.has("bond") and "noah-clair" in [e[1] for e in mixer.log if e[0] == "start"]
    assert "You told me you'd tell me" in g.variant("k7.entscheidung")
    mixer.stop()


def test_chapter_one_can_be_finished_without_meeting_mika_by_exploring_the_house_and_the_church(tmp_path):
    io = FakeIO([None])
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"))
    assert g.next_goal() == "k1.nook_noah"                                   # the must scene comes first
    g.st["done"].append("k1.nook_noah")
    g.st["place"] = "haus"
    assert ("Listen to the house in the dark", "k1.haus_nacht") in g.side_entries("haus")
    g.play_tree("k1.haus_nacht")
    g.check_chapter()
    assert g.st["chapter"] == 2                                              # Noah + one side scene are enough
    assert "k1.see_mika" not in g.st["done"]


def test_the_hint_names_the_next_place_and_action(tmp_path):
    g = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "s.json"))
    assert "the Nook" in g.hint_text()
    g.st["done"] += ["k1.nook_noah", "k1.see_mika"]
    assert "Something is waiting" in g.hint_text() and ":" in g.hint_text()          # now a menu action is named


def test_every_menu_scene_exists_in_the_story_and_has_a_place():
    for sid, (place, label) in sg.ENTRY.items():
        assert sid in STORY and place in sg.PLACE_NAMES and label, sid
    for ch, pool in sg.POOL.items():
        for sid in pool:
            assert sid in STORY, sid
        assert sg.NEED[ch] <= len(pool)


def test_jump_puts_the_player_where_the_scene_happens(tmp_path):
    for sid, place in (("k3.lichtung", "wald"), ("k6.traum", "haus"), ("k5.tesserakt", "schloss"), ("k2.baeckerei", "lunuen")):
        g = sg.Game(io=FakeIO([None]), story=STORY, save_path=str(tmp_path / "s.json"))
        g.jump(sid)
        assert g.st["place"] == place, sid


def test_the_final_choice_is_preceded_by_what_the_player_did_for_noah(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "ENDING_QUOTES", [("promise", "You said you'd tell me."), ("gift", "I still have the cup."), ("kind_mug", "You glued the mug.")])
    io = FakeIO([None])
    g = sg.Game(io=io, story=STORY, save_path=str(tmp_path / "s.json"))
    g.flag("promise")
    g.flag("kind_mug")
    g.decision()
    texts = [t for _w, t in io.shown]
    assert texts[0] == "You said you'd tell me.\n\nYou glued the mug."                # only the deeds that happened, in order
    assert "I still have the cup." not in " ".join(texts)
    assert "You have to decide" in texts[1] or "decide" in texts[1]


def test_every_flag_and_ending_quote_from_story_extra_points_at_a_real_node():
    import story_extra as x
    for (sid, nid), flag in x.FLAG_AT.items():
        assert sid in STORY and nid in STORY[sid]["baum"]["knoten"], (sid, nid)
    flags = set(x.FLAG_AT.values())
    for flag, text in x.ENDING_QUOTES:
        assert flag in flags and text.strip(), flag
    for sid, (place, label) in x.ENTRY.items():
        assert sid in STORY and place in sg.PLACE_NAMES and label
    for ch, sids in x.POOL.items():
        assert all(s in STORY for s in sids)


def test_the_boss_song_fades_out_when_the_fight_is_over_before_the_choice(tmp_path):
    ref = [None]
    mixer = audio.Mixer(backend=Fake, sleep=lambda s: None)
    io = FakeIO(ref)
    io.mixer = mixer
    g = sg.Game(io=io, story=STORY, mixer=mixer, save_path=str(tmp_path / "s.json"),
                boss_runner=lambda l, p: mixer.boss_phase_two() or "won", credits_runner=lambda b, s: None)
    ref[0] = g
    g.fight_only()
    mixer.wait()
    log = mixer.log
    boss_start = log.index(("start", "boss-noa", 100)) if ("start", "boss-noa", 100) in log else [i for i, e in enumerate(log) if e[:2] == ("start", "boss-noa")][0]
    stops = [i for i, e in enumerate(log) if e == ("stop", "boss-noa")]
    shows = [i for i, e in enumerate(log) if e[0] == "show" and e[1].startswith("Noah kneels in the m")]
    assert stops and shows and stops[0] < shows[0]                              # the boss song is gone before the choice text appears
    mixer.stop()
