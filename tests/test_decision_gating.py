"""Decision audit (docs/DECISION-AUDIT.md): no option is offered before the player can know what it is about."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import story_game as sg  # noqa: E402

STORY = json.load(open(sg.STORY, encoding="utf-8"))


class IO:
    def __init__(self):
        self.menus, self.script = [], []

    def art(self, *a):
        pass

    def show(self, text, who="narrator"):
        pass

    def pause(self):
        pass

    def pick(self, options, aliases=None):
        self.menus.append(list(options))
        return self.script.pop(0) if self.script else 0


def game(tmp_path, chapter=1, place="haus"):
    g = sg.Game(io=IO(), story=STORY, save_path=str(tmp_path / "s.json"))
    g.st.update(chapter=chapter, place=place, prologue=True)
    return g


def offered(g, sid):
    """Every label the tree shows when the first answer is always taken."""
    g.play_tree(sid)
    return [o for m in g.io.menus for o in m]


def test_chapter_one_starts_with_the_town_only_and_discovers_the_rest(tmp_path):
    g = game(tmp_path)
    assert g.destinations("haus") == ["lunuen"]
    g.know("lunuen"); g.enter_place("lunuen")
    assert "nook" in g.destinations("lunuen") and "see" not in g.destinations("lunuen")
    g.enter_place("nook")
    assert "see" in g.destinations("nook")


def test_the_bedroom_window_and_the_hint_show_the_lake(tmp_path):
    g = game(tmp_path)
    opt = next(o for o in STORY["ort.haus.k1"]["optionen"] if o["name"] == "Go upstairs to the bedroom")
    g.run_option("haus", opt)
    assert "see" in g.destinations("haus")
    g2 = game(tmp_path)
    g2.hint_text()
    assert "nook" in g2.destinations("haus")


def test_later_chapters_list_every_place(tmp_path):
    g = game(tmp_path, chapter=2)
    assert set(g.destinations("haus")) == set(g.places()) - {"haus"}


def test_connor_does_not_ask_about_things_the_player_has_not_met(tmp_path):
    g = game(tmp_path, 2, "lunuen")
    offers = offered(g, "k2.connor_1")
    assert "Ask about the man on the lake bench" not in offers and "Ask about Dorothy" not in offers
    g = game(tmp_path, 2, "lunuen")
    g.st["done"].append("k1.see_mika")
    g.flag("dorothy")
    g.io.script = [0]                      # n1 -> n2: the Dorothy question is in the next menu
    offers = offered(g, "k2.connor_1")
    assert "Ask about the man on the lake bench" in offers and "Ask about Dorothy" in offers


def test_the_baker_option_about_the_lake_bench_needs_mika(tmp_path):
    g = game(tmp_path, 2, "lunuen")
    sc = STORY["ort.lunuen.k2"]
    assert sg.OPTION_REQ[("ort.lunuen.k2", "Ask the baker about the man on the lake bench")] == "done:k1.see_mika"
    assert not g.req_ok("done:k1.see_mika")
    assert any(o["name"] == "Ask the baker about the man on the lake bench" for o in sc["optionen"])


def test_mikas_reaction_matches_what_the_player_did_at_the_lake(tmp_path):
    g = game(tmp_path, 4, "see")
    g.flag("joined")
    offers = offered(g, "k4.mika_reaktion")
    assert "Tell him you joined" in offers and "Tell him you refused" not in offers
    g = game(tmp_path, 4, "see")
    offers = offered(g, "k4.mika_reaktion")
    assert "Tell him you refused" in offers and "Tell him you joined" not in offers


def test_noah_does_not_hear_about_the_lake_before_the_recruitment(tmp_path):
    g = game(tmp_path, 4, "nook")
    assert "Tell him you saw Connor at the lake" not in offered(g, "k4.noah_angst")
    g = game(tmp_path, 4, "nook")
    g.st["done"].append("k4.anwerbung")
    assert "Tell him you saw Connor at the lake" in offered(g, "k4.noah_angst")


def test_no_cube_no_cube_choices_in_the_cellar_and_the_note_only_with_the_note(tmp_path):
    g = game(tmp_path, 7, "schloss")
    assert "Put the cube down on the stone" not in offered(g, "k7.noah_vor")
    g = game(tmp_path, 7, "schloss")
    g.flag("tesseract")
    assert "Put the cube down on the stone" in offered(g, "k7.noah_vor")
    g = game(tmp_path, 6, "see")
    assert "Show him the note" not in offered(g, "k6.mika_froh")
    g = game(tmp_path, 6, "see")
    g.flag("note")
    assert "Show him the note" in offered(g, "k6.mika_froh")


def test_the_dream_bed_is_not_offered_again_and_the_clair_scene_has_a_way_in(tmp_path):
    g = game(tmp_path, 6, "haus")
    g.flag("tesseract")
    opts = [o["name"] for o in STORY["ort.haus.k6"]["optionen"] if g.req_ok(sg.OPTION_REQ.get(("ort.haus.k6", o["name"]), "flag:tesseract"))]
    assert "Go to bed with the cube in your pocket" in opts
    g.flag("dream_done")
    assert not g.req_ok(sg.OPTION_REQ[("ort.haus.k6", "Go to bed with the cube in your pocket")])
    g.st["done"].append("k6.traum")
    g.st["place"] = "nook"
    assert ("Visit the Nook after dark", "k6.noah_clair") in g.side_entries("nook")


def test_the_gymnasium_scene_waits_for_the_church_and_the_supper_text_for_chapter_three(tmp_path):
    g = game(tmp_path, 2, "gymnasium")
    assert not g.available("k2.gymnasium_connor")
    g.st["done"].append("k2.connor_1")
    assert g.available("k2.gymnasium_connor")
    g.flag("invited")
    assert g.variant("k2.gymnasium_connor") is None
    g.st["chapter"] = 3
    assert g.variant("k2.gymnasium_connor")


def test_the_church_window_man_has_no_name_label_before_chapter_two(tmp_path):
    g = game(tmp_path, 1, "lunuen")
    shown = []
    g.io.show = lambda text, who="narrator": shown.append(who)
    g.play_tree("k1.kirche_fenster")
    assert set(shown) == {"narrator"}


def test_the_cube_cannot_be_left_in_the_cellar(tmp_path):
    g = game(tmp_path, 5, "schloss")
    offers = offered(g, "k5.tesserakt")
    assert "No, leave it" not in offers and "Leave it" not in offers and "Yes, take it" in offers
    g = game(tmp_path, 5, "schloss")
    opt = {"name": "Search the east wing", "text": "x"}
    g.io.script = [0, 0, 0, 0]                    # pull the book, go down, take the cube
    g.run_option("schloss", opt)
    assert g.has("tesseract") and g.st["chapter"] == 6
