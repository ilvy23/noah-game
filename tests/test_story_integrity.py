"""story.json vs the tables in story_game.py / story_extra.py: every id exists, every menu entry is reachable."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import story_extra as x  # noqa: E402
import story_game as sg  # noqa: E402

S = json.load(open(sg.STORY, encoding="utf-8"))


def test_all_table_ids_exist_in_story():
    ids = set(sg.ENTRY) | set(sg.NEEDS) | set(sg.NEEDS.values()) | set(sg.SCENE_PLACE) | set(sg.AUDIO_SCENE) | set(x.ENTRY)
    for t in (sg.POOL, sg.MUST, sg.CHAPTER_SCENES, x.POOL):
        for lst in t.values():
            ids |= set(lst)
    ids |= {k[0] for k in sg.FLAG_AT} | {k[0] for k in sg.HINT_AT}
    assert [i for i in sorted(ids) if i not in S] == []
    for sid, nid in list(sg.FLAG_AT) + list(sg.HINT_AT):
        assert nid in S[sid]["baum"]["knoten"], (sid, nid)


def test_every_menu_entry_is_offered_in_a_place_that_is_open_in_its_chapter():
    for ch, pool in sg.POOL.items():
        open_places = {s["ort"] for sid, s in S.items() if sid.startswith("ort.") and sid.endswith(".k%d" % ch) and not s.get("entfaellt")}
        for sid in pool:
            place = sg.ENTRY[sid][0] if sid in sg.ENTRY else sg.SCENE_PLACE.get(sid)
            assert place in open_places or sid in ("k5.tesserakt", "k6.traum"), (ch, sid, place)


def test_trigger_options_exist_and_trees_are_closed():
    for (sid, name) in sg.OPTION_TRIGGER:
        assert name in [o["name"] for o in S[sid]["optionen"]]
    for sid, s in S.items():
        t = s.get("baum")
        if not t:
            continue
        k = t["knoten"]
        assert t["start"] in k and all(c["ziel"] in k for n in k.values() for c in n.get("wahl") or [] if c["ziel"]), sid
        assert all(n["text"].strip() for n in k.values()), sid


def test_game_default_save_path_follows_the_module_constant(monkeypatch, tmp_path):
    monkeypatch.setattr(sg, "SAVE", str(tmp_path / "x.json"))
    assert sg.Game(io=object(), story={}).save_path == str(tmp_path / "x.json")


def test_mika_does_not_talk_like_connor():
    for sid, s in S.items():
        if (s.get("figuren") or [""])[0] == "mika":
            for n, k in (s.get("baum") or {}).get("knoten", {}).items():
                assert "my friend" not in k["text"], (sid, n)
