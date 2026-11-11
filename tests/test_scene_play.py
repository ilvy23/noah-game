"""scene_play / scene_lib: the text parser, the verb table, the puppets, the backdrops, handcrafted scenes headless at three sizes, the game hooks."""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio  # noqa: E402,F401
import cine_fx  # noqa: E402
import decision_fx  # noqa: E402
import mika_ending  # noqa: E402
import noah_gore_fx as G  # noqa: E402
import scene_play  # noqa: E402
import story_game as sg  # noqa: E402
from scene_lib import actions, backdrops, figures, overrides, parser, verbs  # noqa: E402

STORY = json.load(open(sg.STORY, encoding="utf-8"))
SIZES = [(80, 24), (120, 40), (245, 45)]


class IO:
    def show(self, *a):
        pass


def make_ctx(w, h, fps=2):
    out = io.StringIO()
    ctx = mika_ending.Ctx(IO(), None, texts={}, sleep=lambda s: None, size=lambda: (w, h), out=out, fps=fps)
    ctx.keys, ctx.cps, ctx.hold_scale, ctx.choices = False, 4000, 0.05, []
    return ctx, out


def inside(out, w, h):
    """Every cursor move of the output lies inside the w x h screen (the last line is never touched)."""
    for r, c in re.findall(r"\x1b\[(\d+);(\d+)H", out):
        assert 1 <= int(r) <= h - 1 and 1 <= int(c) <= w


# ---------------------------------------------------------------- parser
def test_prose_speech_becomes_bubbles_and_the_tag_is_dropped():
    beats, cast = parser.parse("A man sits on the bench. 'Evening,' he says. 'Welcome gift, man.'", main=["mika"])
    assert [(b.kind, b.who) for b in beats] == [("narr", None), ("say", "mika"), ("say", "mika")]
    assert beats[1].text == "Evening," and "mika" in cast and "you" not in cast


def test_the_speaker_is_found_from_a_name_a_pronoun_or_you():
    beats, _ = parser.parse("'Hi,' says Connor. 'Hello,' you say. 'Quiet,' Noah whispers.", main=["noah"])
    assert [b.who for b in beats if b.kind == "say"] == ["connor", "you", "noah"]
    beats, _ = parser.parse("Mika sits. 'Hey.' He nods. 'Sit.'", main=[])
    assert [b.who for b in beats if b.kind == "say"] == ["mika", "mika"]


def test_actions_come_from_the_verb_table_and_go_to_the_named_figure():
    beats, cast = parser.parse("Noah stands up and nods. You sit down. Mika holds out a cigarette.", main=["noah"])
    acts = [(a[0], a[1]) for b in beats for a in b.acts]
    assert ("noah", "stand") in acts and ("noah", "nod") in acts and ("you", "sit") in acts
    assert ("mika", "hold_out") in acts and ("you", "take") in acts and "mika" in cast


def test_unknown_narration_gets_a_subtle_fallback_never_bare_text():
    beats, _ = parser.parse("The fog is thick and the lake is flat.", main=["mika"])
    assert beats[0].kind == "narr" and beats[0].push                                   # scenery: the camera moves in slowly
    beats, _ = parser.parse("Mika's eyes are red and tired.", main=["mika"])
    assert beats[0].push and beats[0].acts and beats[0].acts[0][0] == "mika" and beats[0].acts[0][1] in actions.ACTIONS
    beats, _ = parser.parse("Behind you something knocks, twice, and the candles flicker.", main=[])
    assert ("world", "thud") in [(a[0], a[1]) for a in beats[0].acts] and ("world", "flicker") in [(a[0], a[1]) for a in beats[0].acts]


def test_time_jump_cards_and_screenplay_form():
    beats, cast = parser.parse("— Later —\nNOAH: I made tea.\n(Noah pours the tea)\nMIKA: Cheers.", main=[])
    assert [b.kind for b in beats] == ["card", "say", "narr", "say"]
    assert beats[0].text == "Later" and beats[1].who == "noah" and beats[3].who == "mika"
    assert ("noah", "pour") in [(a[0], a[1]) for a in beats[2].acts]


def test_no_story_text_is_lost_except_pure_attributions():
    for sid, sc in STORY.items():
        nodes = [n["text"] for n in sc["baum"]["knoten"].values()] if sc.get("baum") else [sc.get("text", "")]
        for text in nodes[:6]:
            beats, _ = parser.parse(text, main=list(sc.get("figuren") or []))
            shown = re.sub(r"\W+", "", " ".join(b.text for b in beats)).lower()
            for word in re.findall(r"[A-Za-z]{6,}", text)[:12]:
                assert word.lower() in shown or re.search(r"(says?|asks?|said|whispers?|adds?)", text), (sid, word)


def test_long_speech_is_split_into_bubble_sized_pieces():
    text = "'" + " ".join("This is sentence number %d of a very long speech." % i for i in range(12)) + "'"
    beats, _ = parser.parse(text, main=["connor"])
    assert len(beats) >= 3 and all(len(b.text) <= parser.LIMIT * 1.5 and b.who == "connor" for b in beats)


# ---------------------------------------------------------------- verbs and actions
def test_every_verb_points_at_an_existing_action_and_every_action_is_reachable():
    assert set(verbs.ACTION_NAMES) <= set(actions.ACTIONS)
    internal = {"rest", "straighten", "turn_back", "look_back", "neutral", "unhug", "walk_to", "walk_in", "walk_out", "gesture2", "step_forward", "lean_back"}
    missing = set(actions.ACTIONS) - set(verbs.ACTION_NAMES) - internal - {"stand", "fall_forward"}
    assert not missing, missing
    for name in ("stand", "sit", "kneel", "nod", "shake_head", "raise_hand", "lower_hand", "hold_out", "hug", "fall_forward", "take_knife", "pour", "light_cig", "smile",
                 "flinch", "look_away", "point", "open_door", "walk_out", "walk_in"):
        assert name in verbs.ACTION_NAMES, name


@pytest.mark.parametrize("w,h", SIZES)
def test_every_action_plays_for_every_character_inside_the_canvas(w, h):
    for style in figures.STYLES:
        for name in list(actions.ACTIONS) + ["walk_in", "walk_out", "walk_to"]:
            p = figures.Puppet(style, x=0.5, seat=True)
            cv = G.Canvas(w, h - 1)
            p.act(name, 0.0)
            for i in range(0, 40):
                t = i * 0.15
                p.update(t)
                p.draw(cv, int(cv.h * 2 * 0.78), t=t)
            assert p.history and len(cv.ch) == cv.w * cv.h


def test_actions_change_the_state_in_the_right_direction():
    p = figures.Puppet("noah")
    p.act("sit", 0.0)
    for i in range(30):
        p.update(i * 0.1)
    assert p.state["tA"] > 60 and p.history == ["sit"]
    p.act("stand", 3.1)
    for i in range(31, 60):
        p.update(i * 0.1)
    assert p.state["tA"] < 5
    q = figures.Puppet("mika", x=0.7)
    q.act("walk_out", 0.0)
    for i in range(60):
        q.update(i * 0.1)
    assert q.x > 1.0


def test_light_cig_gives_a_cigarette_and_the_puff_event():
    p = figures.Puppet("mika")
    p.act("light_cig", 0.0)
    ev = []
    for i in range(40):
        ev += p.update(i * 0.1)
    assert p.props["prop_a"] == "cig" and "puff" in ev and "flame" in ev


# ---------------------------------------------------------------- backdrops
@pytest.mark.parametrize("w,h", SIZES)
def test_every_backdrop_draws_deterministically(w, h):
    for kind in backdrops.KINDS:
        outs = []
        for _ in range(2):
            b = backdrops.make(kind, w, h - 1, 3, seed=2)
            cv = G.Canvas(w, h - 1)
            for i in range(3):
                b.draw(cv, i * 0.4, 0.4)
            outs.append((cv.ch[:], cv.fg[:], cv.bg[:]))
        assert outs[0] == outs[1], kind


def test_the_automatic_mapping_never_gives_an_unknown_picture():
    for sid, sc in STORY.items():
        if sc["art"] in ("boss", "items", "credits"):
            continue
        pl = overrides.plan(sid, sc, sc.get("ort"), sc.get("kapitel") or 1, sc.get("text", ""))
        assert pl["kind"] in backdrops.KINDS or pl["kind"].startswith("ambient:"), sid
        for f in pl["figs"]:
            assert f in figures.STYLES


# ---------------------------------------------------------------- scenes headless
def run_scene(sid, w, h):
    ctx, out = make_ctx(w, h)
    sc = STORY[sid]
    visited = scene_play.play(sc, ctx, sid=sid, place=sc.get("ort"))
    return visited, out.getvalue(), ctx


@pytest.mark.parametrize("w,h", SIZES)
def test_handcrafted_scenes_run_to_the_end_inside_the_screen(w, h):
    for sid in ("prolog", "k1.nook_noah", "k1.see_mika", "k2.connor_1", "k4.anwerbung", "k6.traum", "k7.noah_vor"):
        visited, out, ctx = run_scene(sid, w, h)
        assert visited or sid == "prolog"
        assert out.endswith("\x1b[?25h") or "\x1b[?25h" in out
        inside(out, w, h)
        shown = [e for e in ctx.log if e[0] in ("say", "narr", "card")]
        assert shown, sid


def test_a_scene_plays_the_same_every_time():
    a = run_scene("k1.see_mika", 120, 40)[1]
    b = run_scene("k1.see_mika", 120, 40)[1]
    assert a == b and len(a) > 5000


def test_choices_are_an_overlay_and_the_scripted_answer_is_followed():
    ctx, out = make_ctx(120, 40)
    ctx.choices = [1, 0, 0, 0]
    v = scene_play.play(STORY["k1.see_mika"], ctx, sid="k1.see_mika")
    assert v[0] == "n1" and v[1] == "n2"                                           # option 2 of n1 leads to n2
    assert "Take the cigarette" in out.getvalue() and "choose" in out.getvalue()


def test_timed_choice_times_out_with_none_and_ticks_each_second():
    ctx, out = make_ctx(120, 40, fps=4)
    s = scene_play.Session(ctx, {"sid": "k7.entscheidung", "scene": STORY["k7.entscheidung"], "chapter": 7})
    s.open()
    ticks = []
    r = s.timed(["a", "b"], 3, ticks.append)
    s.close()
    assert r is None and ticks == [1, 2]


def test_the_time_jump_card_fades_the_picture_and_writes_the_title():
    ctx, out = make_ctx(120, 40)
    s = scene_play.Session(ctx, {"sid": "x", "scene": {"figuren": ["noah"]}, "place": "nook", "chapter": 1})
    s.open()
    s.show("— Later —\nNoah nods.", "noah")
    s.close()
    assert ("card", "Later") in [(e[0], e[2]) for e in ctx.log] and "Later" in out.getvalue()


def test_small_terminals_fall_back_in_the_game_hook(monkeypatch, capsys):
    io_ = sg.RealIO()
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sg.shutil, "get_terminal_size", lambda d=None: os.terminal_size((100, 30)))
    sg.RealIO._hinted = False
    assert io_.scene_begin({"sid": "prolog", "scene": {}, "chapter": 1}) is False and io_.sp is None
    assert "120x40" in capsys.readouterr().out
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False, raising=False)
    assert io_.scene_begin({"sid": "prolog", "scene": {}, "chapter": 1}) is False


def test_the_hook_opens_the_animated_view_on_a_big_tty(monkeypatch):
    opened = []

    class FakeSession:
        def __init__(self, ctx, info):
            self.info = info

        def open(self):
            opened.append(self.info["sid"])

        def close(self):
            opened.append("closed")

        def show(self, text, who):
            opened.append(("show", who))

        def set_node(self, n):
            pass
    monkeypatch.setattr(scene_play, "Session", FakeSession)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sg.shutil, "get_terminal_size", lambda d=None: os.terminal_size((200, 50)))
    monkeypatch.delenv("FOLK_PLAIN", raising=False)
    io_ = sg.RealIO()
    assert io_.scene_begin({"sid": "k1.see_mika", "scene": {}, "chapter": 1}) is True
    io_.show("hello", "mika")
    io_.scene_end()
    assert opened == ["k1.see_mika", ("show", "mika"), "closed"] and io_.sp is None


class ScriptIO:
    def __init__(self):
        self.shown, self.timed = [], []

    mixer = None

    def show(self, text, who="narrator"):
        self.shown.append((who, text))

    def pause(self):
        pass

    def timed_pick(self, options, seconds, on_tick=None):
        self.timed.append(options)
        return 0

    def pick(self, options, aliases=None):
        return 0


def game(tmp_path):
    return sg.Game(io=ScriptIO(), story=STORY, save_path=str(tmp_path / "s.json"), boss_runner=lambda l, p: "won", credits_runner=lambda b, s: None)


def test_show_ending_prints_no_text_when_the_animation_played_it_on_a_tty(tmp_path, monkeypatch):
    monkeypatch.setattr(cine_fx, "run_named", lambda ctx, name, seed=1: None)
    g = game(tmp_path)
    g.cinematics = True
    g.show_ending("slaughter-it")
    assert not any("ending" in w or len(t) > 300 for w, t in g.io.shown)               # the animation said the whole text
    g = game(tmp_path)
    g.cinematics = False
    g.show_ending("slaughter-it")
    assert any(t == STORY["k7.ending_slaughter"]["text"] for _w, t in g.io.shown)       # headless: the old text path


def test_show_ending_keeps_the_text_when_the_animation_breaks(tmp_path, monkeypatch):
    def boom(ctx, name, seed=1):
        raise RuntimeError("x")
    monkeypatch.setattr(cine_fx, "run_named", boom)
    g = game(tmp_path)
    g.cinematics = True
    g.show_ending("ending-3")
    assert any(t == STORY["k7.ending_3"]["text"] for _w, t in g.io.shown)


def test_decision_uses_the_animated_choice_on_a_real_tty_and_the_old_menu_otherwise(tmp_path, monkeypatch):
    calls = []

    def fake(ctx, text, options, seconds=30, warns=None, who="noah", seed=3):
        calls.append((text, options, seconds, warns))
        return None
    monkeypatch.setattr(cine_fx, "run_named", lambda ctx, name, seed=1: None)
    monkeypatch.setattr(decision_fx, "timed_pick_scene", fake)
    monkeypatch.setattr(decision_fx, "available", lambda ctx: True)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    g = game(tmp_path)
    g.cinematics = True
    assert g.decision() == "ending-3"                                                   # no answer in 30 s = ending 3, as before
    assert calls and calls[0][2] == 30 and set(calls[0][3]) == {10, 20} and g.io.timed == []
    calls.clear()
    g = game(tmp_path)
    g.cinematics = False
    assert g.decision() == "let-it-live" and not calls and g.io.timed


# ---------------------------------------------------------------- cinema gallery
def test_the_cinema_lists_every_scene_and_the_flag_starts_it(monkeypatch):
    import scene_cinema
    ids = [e[0] for e in scene_cinema.entries(STORY)]
    assert "k1.see_mika" in ids and "prolog" in ids and "ort.haus.k1" in ids and "ending-let" in ids and "bench" in ids and len(ids) == len(set(ids))
    assert not any(STORY[i]["art"] in scene_cinema.SKIP_ART for i in ids if i in STORY)
    got = []
    monkeypatch.setattr(scene_cinema, "run", lambda start=None, mixer=None: got.append(start))
    monkeypatch.setattr(sg.audio, "get", lambda: type("M", (), {"stop": lambda self: None})())
    sg.main(["--cinema", "--scene", "k4.anwerbung"])
    assert got == ["k4.anwerbung"]


def test_the_cinema_plays_story_cine_and_mika_entries(monkeypatch):
    import scene_cinema
    calls = []
    monkeypatch.setattr(scene_play, "play", lambda sc, ctx, sid=None, place=None, **k: calls.append(("story", sid, place)))
    monkeypatch.setattr(cine_fx, "run_named", lambda ctx, name, seed=1: calls.append(("cine", name)))
    ctx = scene_cinema.make_ctx()
    items = {e[0]: e for e in scene_cinema.entries(STORY)}
    scene_cinema.play_entry(items["ort.see.k2"], ctx, STORY)
    scene_cinema.play_entry(items["decision"], ctx, STORY)
    assert calls == [("story", "ort.see.k2", "see"), ("cine", "decision")]
