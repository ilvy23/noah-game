"""photo_fx / BigLayer / angel photo: baked pictures load, big lyric lines appear and fade one after the other, the angel draws inside the canvas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import angel_fx  # noqa: E402
import lyrics_fx  # noqa: E402
import noah_gore_fx as G  # noqa: E402
import photo_fx  # noqa: E402


def test_pictures_baked_or_drawn_in_code_and_no_third_party_photo_is_baked():
    import json
    for n in ("angel", "aerial", "lake", "font", "font2"):
        assert photo_fx.has(n)
    baked = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "art", "photos.json")))
    assert set(baked) == {"lake", "font", "font2"}                                   # the owner's own lake photos and the fonts only
    w, h, ch, raw = photo_fx.image("angel")
    assert ch == 4 and len(raw) == w * h * 4 and any(raw[3::4]) and not all(raw[3::4])           # a statue shape with transparent surroundings
    w, h, ch, raw = photo_fx.image("aerial")
    assert ch == 3 and len(raw) == w * h * 3


def test_big_layer_words_land_on_their_times_and_burn_later():
    lay = lyrics_fx.BigLayer([(1.0, "one two"), (5.0, "three four")], 0.0, hold=6.0)
    plan = lay.plan(120, 40, [(2, 1, 58, 34), (62, 1, 118, 34)])
    assert [it["word"]["text"] for it in plan] == ["one", "two", "three", "four"]
    assert all(it["burn"] - it["land"] >= lay.LAND_VISIBLE for it in plan)
    assert plan[0]["land"] < plan[2]["land"]


def test_big_layer_draws_red_and_stays_inside():
    cv = G.Canvas(120, 40)
    lay = lyrics_fx.BigLayer([(0.0, "nonsense words here")], 0.0)
    lay.draw(cv, 1.0, [(2, 2, 60, 20), (60, 20, 118, 38)])
    reds = [c for c in cv.fg + cv.bg if c[0] > 80 and c[1] < 110 and c[2] < 60]
    assert reds
    lay.draw(cv, 1.0, [])                                                                  # no zones: nothing, no crash


def test_angel_photo_draws_and_clips():
    cv = G.Canvas(80, 30)
    w, h = angel_fx.draw_angel_statue(cv, 70, -5, 40, 1.0, 0.3)
    assert w == 40 and h > 10 and "▀" in cv.ch


def test_valley_uses_the_real_lake_and_bench_draws():
    import random
    import mika_fx
    import valley_fx
    for size in ((245, 44), (120, 40)):
        v = valley_fx.ValleyScene(size[0], size[1] - 1, random.Random(1))
        assert len(v.mask) > 300 and v.in_lake(*v.lake[:2]) and v.houses and v.cult
        cv = G.Canvas(size[0], size[1] - 1)
        for t in (0.5, 13.0, 22.0, 35.0):
            v.draw(cv, t, 1 / 12.0)
        b = mika_fx.BenchScene(size[0], size[1] - 1, random.Random(2), "end")
        for t in (0.5, 7.0, 13.5):
            b.draw(cv, t, 1 / 12.0)


def test_bench_arm_follows_the_story_and_ambient_scenes_run():
    import random
    import ambient_fx
    import mika_fx
    b = mika_fx.BenchScene(120, 39, random.Random(3), "end")
    mouth, toast, opened = b.pose(0.0, True), b.pose(3.0, True), b.pose(13.5, True)
    assert toast[3] < mouth[3] - 8 and opened[2] > mouth[2] + 10                       # the joint goes up to the sunset, later the hand opens
    intro = mika_fx.BenchScene(120, 39, random.Random(3), "intro")
    assert intro.pose(0.5, False)[3] > intro.pose(4.6, False)[3] + 10                  # from the lap to the mouth after the pocket
    for kind, cls in ambient_fx.KINDS.items():
        s = cls(120, 39, random.Random(1))
        cv = G.Canvas(120, 39)
        for i in range(12):
            s.draw(cv, i / 12.0, 1 / 12.0)
    boxes = ambient_fx.boxes_for("He waits. 'It's okay,' he whispers. 'Take your time.'")
    assert [b_[0] for b_ in boxes] == ["narrator", "noah", "narrator", "noah"]


def test_ending_text_is_bubbles_in_order_and_decision_overlay_draws():
    import json
    import cine_fx
    import decision_fx
    t = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "story", "story.json")))
    for name, sid in cine_fx.ENDING_SID.items():
        boxes = cine_fx.ending_boxes(name, t[sid]["text"])
        assert len(boxes) == len(cine_fx.ENDING_ANCHORS[name]) and all(b[1] for b in boxes)
        assert list(cine_fx.ENDING_ANCHORS[name]) == sorted(cine_fx.ENDING_ANCHORS[name])
    assert [b[0] for b in cine_fx.ending_boxes("ending-3", t["k7.ending_3"]["text"]) if b[0] != "narrator"][:3] == ["noah", "noah2", "noah3"]
    cv = G.Canvas(120, 39)
    decision_fx.draw_overlay(cv, ["Let him live", "Kill him"], 1, 12.0, 30.0)
    assert any("Kill him" in "".join(cv.ch[y * 120:(y + 1) * 120]) for y in range(39))


def test_hand_made_word_times_override_the_automatic_timing(tmp_path):
    f = tmp_path / "w.txt"
    f.write_text("# c\n[00:01.00] one\n00:02.5 two\n[00:07.0] three\n")
    words = lyrics_fx.load_words(str(f))
    assert words == [(1.0, "one"), (2.5, "two"), (7.0, "three")] and lyrics_fx.load_words(str(tmp_path / "none")) == []
    lay = lyrics_fx.BigLayer([(1.0, "one two"), (6.0, "three")], 0.0, words=words)
    assert [round(w["s"] - 1.0, 2) for w in lay.words if w["line"] == 0] == [0.0, 1.5] and [round(w["s"] - 6.0, 2) for w in lay.words if w["line"] == 1] == [1.0]


def test_word_timed_json_gives_lines_and_exact_word_times(tmp_path):
    import json
    f = tmp_path / "w.json"
    f.write_text(json.dumps({"lines": [{"words": [{"t": "zzz ", "s": 100000}]}, {"words": [{"t": "aaa ", "s": 150000}, {"t": "bbb ", "s": 151500}]}]}))
    lines, exact = lyrics_fx.load_json(str(f))
    assert lines == [(150.0, "aaa bbb")] and exact == [[0.0, 1.5]] and lyrics_fx.load_json(str(tmp_path / "no")) == ([], [])
    lay = lyrics_fx.BigLayer(lines, 135.0, exact=exact)
    assert [round(w["s"] - 150.0, 2) for w in lay.words] == [0.0, 1.5]


def test_climax_line_is_flagged_and_draw_returns_a_jolt():
    cv = G.Canvas(245, 44)
    lay = lyrics_fx.BigLayer([(0.0, "Father into your hands I commend my spirit")], 0.0, exact=[[0.0, 0.6, 0.9, 1.2, 2.0, 2.3, 2.8, 3.0]])
    for i in range(0, 60):
        jolt = lay.draw(cv, i / 12.0, [(2, 1, 100, 38), (143, 1, 192, 38)])
    assert lay.is_climax(0) and isinstance(jolt, tuple)


def test_every_lyric_word_is_shown_inside_the_screen_and_readable():
    import lettering
    import random
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lines, exact = lyrics_fx.load_json(os.path.join(root, "soundtracks", "lyrics", "noah-burns-song.words.json"))
    if not lines:
        return                                                                          # the user's json is not in the repo everywhere
    texts = [t.split() for _, t in lines]
    assert texts[0] == ["Father", "father", "Father", "father", "Father", "father", "Father"]      # four main shouts, three quiet echoes
    for w, h in ((245, 44), (120, 40)):
        lay = lyrics_fx.BigLayer(lines, 135.0, exact=exact)
        bs = G.BurnScene(w, h - 1, random.Random(3))
        zones = bs.lyric_zones(13.5)
        plan = lay.plan(w, h - 1, zones)
        assert [it["word"]["text"] for it in plan] == [x for t in texts for x in t]
        right = zones[-1][2] if w >= 160 else w - 2
        for it in plan:
            wd = lettering.get(it["word"]["text"], it["scale"])
            assert it["x"] >= 1 and it["x"] + wd.w <= right + 2, (w, it["word"]["text"], it["x"], wd.w)
            assert it["y"] >= 1 and it["y"] + wd.h // 2 <= h - 1 - 5, (w, it["word"]["text"], it["y"])
            assert it["burn"] - it["land"] >= 0.6, (w, it["word"]["text"])
            assert it["scale"] >= (0.3 if it["word"]["kind"] == "main" else 0.2)
        cv = G.Canvas(w, h - 1)
        for i in range(0, 70 * 12):                                                     # the whole song part renders without error
            lay.draw(cv, i / 12.0, zones)
