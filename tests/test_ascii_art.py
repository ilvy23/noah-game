"""ascii_art.py: pictures exist for the mapped places, are graded per chapter and picked by window size."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ascii_art as A  # noqa: E402


def test_every_mapped_place_has_a_wide_and_a_small_picture():
    for place, name in A.PLACE_ART.items():
        d = A.load(name)
        assert d, place
        for key, (w, h) in (("ultra", (200, 30)), ("wide", (140, 35)), ("small", (90, 23)), ("tiny", (60, 15)), ("mini", (50, 12))):
            assert (d[key]["w"], d[key]["h"]) == (w, h) and len(d[key]["rows"]) == h and len(d[key]["rgb"][0]) == 3 * w


def test_lines_are_coloured_graded_by_chapter_and_fall_back_to_256_colours():
    night = A.lines("wald", 1, "small", truecolor=True)
    sun = A.lines("wald", 6, "small", truecolor=True)
    assert len(night) == 23 and "\033[38;2;" in "".join(night) and night != sun
    assert "\033[38;5;" in "".join(A.lines("wald", 1, "small", truecolor=False))
    assert A.lines("gibtesnicht", 1, "small") == []


def test_size_follows_the_window_and_tiny_windows_get_no_picture():
    assert A.pick_size(245, 45) == "ultra" and A.pick_size(160, 60) == "wide" and A.pick_size(100, 40) == "small" and A.pick_size(80, 32) == "tiny"
    assert A.pick_size(80, 24) == "mini" and A.pick_size(50, 20) is None


def test_show_prints_every_row_and_banner_spells_folk():
    out = io.StringIO()
    n = A.show("see", 3, out=out, animate=False, size="small", truecolor=True)
    assert n == 23 and out.getvalue().count("\n") == 23
    assert len(A.banner()) == 5


def test_the_banner_sweep_redraws_the_five_rows_with_moving_colours():
    out = io.StringIO()
    A.banner_sweep(out, sleep=lambda s: None, frames=4)
    text = out.getvalue()
    assert text.count("\033[5A") == 4 and text.count("\n") == 5 * 5          # first draw + four redraws
    assert len(set(__import__("re").findall(r"38;5;(\d+)m", text))) > 4        # the colours really move


def test_truecolor_is_assumed_unless_the_terminal_clearly_cannot(monkeypatch):
    for k in ("FOLK_COLORS", "COLORTERM"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    assert A.has_truecolor()
    monkeypatch.setenv("TERM", "linux")
    assert not A.has_truecolor()
    monkeypatch.setenv("FOLK_COLORS", "256")
    monkeypatch.setenv("COLORTERM", "truecolor")
    assert not A.has_truecolor()
