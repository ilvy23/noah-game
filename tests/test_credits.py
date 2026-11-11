"""credits.py: bottom-to-top film scroll that ends with the song; seedable random order."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import credits  # noqa: E402

BLOCKS = [{"titel": "A game by", "text": "ME"}, {"titel": "Story", "text": "X\nY"}, {"titel": "Sound", "text": "Z"},
          {"titel": "Thanks", "text": "A"}, {"titel": "In memory of", "text": "Dorothy"}]


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, d):
        self.t += d


def test_the_roll_is_never_slower_than_the_minimum_speed_and_the_end_screen_holds_until_the_song_ends():
    lines, _ = credits.build_lines(BLOCKS, seed=1)
    assert credits.speed_for(len(lines) + 12, 300.0) == credits.MIN_SPEED       # a long song does not slow it down
    assert credits.speed_for(1000, 100.0) == 10.0                               # a short song speeds it up
    c, out = Clock(), io.StringIO()
    credits.roll(BLOCKS, 120.0, out=out, height=12, width=40, seed=1, sleep=c.sleep, now=c.now)
    text = out.getvalue()
    scroll_seconds = (len(lines) + 12) / credits.MIN_SPEED
    assert scroll_seconds < 60                                                  # the whole credits rise within a minute
    assert 119.0 <= c.t <= 121.5                           # then THE END stays until the song is over
    assert text.index("A GAME BY") < text.index("IN MEMORY OF") and "thank you for staying" in text
    assert "\u2588\u2588\u2588\u2588\u2588" in text and "\033[2J" in text                      # banner / end card are drawn big


def test_order_is_random_but_seedable_and_first_last_stay():
    l1, _ = credits.build_lines(BLOCKS, seed=1)
    l2, _ = credits.build_lines(BLOCKS, seed=1)
    l3, _ = credits.build_lines(BLOCKS, seed=2)
    assert l1 == l2
    for ls in (l1, l3):
        txt = "\n".join(ls)
        assert txt.index("A GAME BY") < txt.index("STORY") and txt.index("THANKS") < txt.index("IN MEMORY OF")


def test_music_block_comes_from_sources_file(tmp_path):
    p = tmp_path / "SOURCES.txt"
    p.write_text("Clean names\n")
    (tmp_path / "SONGS.json").write_text('{"mika.flac": "Bob Marley & The Wailers - Jamming", "gone.flac": "Not Here - Missing"}')
    assert credits.music_block(str(p)) is None                       # no song file present: no music block
    (tmp_path / "mika.flac").write_bytes(b"x")
    b = credits.music_block(str(p))
    assert b["titel"] == "Music" and "Music hand picked by ilvy23" in b["text"]
    assert "mika.flac \u2014 Bob Marley & The Wailers - Jamming" in b["text"]            # filename - real name of the song
    assert "gone.flac" not in b["text"]                                                 # only songs that are really there


def _run(width, height, seconds=120.0, seed=1):
    c, out = Clock(), io.StringIO()
    credits.roll(BLOCKS, seconds, out=out, height=height, width=width, seed=seed, sleep=c.sleep, now=c.now)
    return out.getvalue(), c.t


def test_the_credits_are_text_only_and_no_picture_leftovers_remain():
    for gone in ("PICS", "CREDIT", "picture_plan", "_picture", "SLOT"):
        assert not hasattr(credits, gone)
    for w in (40, 80, 120, 245):
        text, _ = _run(w, 44)
        assert "taken by" not in text and "this place is real" not in text and "thank you for staying" in text
        assert "\u2584" not in text and "\u2580" not in text                      # no half-block pixel pictures


def test_composed_frame_keeps_the_text_column_free_of_particles():
    lay = credits.layout(245)
    rng = __import__("random").Random(5)
    parts = credits._particles(rng, 245, 44, lay)
    assert parts and all(p[1] < lay["tx0"] - 3 or p[1] >= lay["tx1"] + 3 for p in parts)       # the margins carry the ash and the fireflies
    rows = [("", "gap")] * 44
    for t in (0.0, 85.0, 100.0, 118.0):
        grid = credits.compose(rows, t, 120.0, 245, 44, lay, parts)
        assert all(cell[0] == " " for row in grid for cell in row[lay["tx0"] - 2:lay["tx1"] + 2])
        assert any(cell[0] != " " for row in grid for cell in row)                       # something drifts in the margins


def test_folk_horror_palette_has_no_neon_codes_or_stars():
    old = {201, 207, 213, 177, 141, 105, 75, 45, 51, 87, 123, 159}
    assert not old & set(credits.PALETTE) and not old & set(credits.BANNER)
    text, _ = _run(245, 44)
    import re
    used = {int(n) for n in re.findall(r"38;5;(\d+)", text)}
    assert not old & used


def test_fake_clock_run_is_deterministic_and_ends_on_time():
    a, ta = _run(245, 44, seed=7)
    b, tb = _run(245, 44, seed=7)
    assert a == b and ta == tb and 119.0 <= ta <= 121.5


def test_the_credits_write_only_what_changed_so_terminals_do_not_lag():
    import io as _io
    class Clk:
        t = 0.0
        def now(self): return self.t
        def sleep(self, d): self.t += d
    c, out = Clk(), _io.StringIO()
    frames = credits.roll(BLOCKS, 120.0, out=out, height=44, width=245, seed=1, sleep=c.sleep, now=c.now)
    assert len(out.getvalue()) / frames < 60_000                                # it was ~840 KB per frame before: 12 MB/s


def test_a_frame_is_cheap_in_bytes_and_in_time_on_a_wide_window():
    import time
    c, writes = Clock(), []

    class Out(io.StringIO):
        def write(self, x):
            writes.append(len(x))
            return super().write(x)
    t0 = time.time()
    credits.roll(BLOCKS, 60.0, out=Out(), height=44, width=245, seed=1, sleep=c.sleep, now=c.now)
    frames = [w for w in writes[2:-2]]
    assert sorted(frames)[len(frames) // 2] < 20000 and max(frames[1:]) < 60000      # only changed cells are written
    assert time.time() - t0 < 30                                                       # ~14 fps needs < 70 ms per frame
