"""ui.py: reveal animation + voice, colours, broken line, arrow-key choices."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio  # noqa: E402
import ui  # noqa: E402


class TTY(io.StringIO):
    def isatty(self):
        return True


class FakeKeys:
    raw = True

    def __init__(self, seq):
        self.seq = list(seq)

    def read(self, timeout=None):
        return self.seq.pop(0) if self.seq else "enter"


def test_reveal_types_every_character_with_pauses_and_no_color_off_tty():
    out, waits = io.StringIO(), []
    ui.reveal("Hi, you. Ok?", out=out, sleep=waits.append)
    assert out.getvalue() == "Hi, you. Ok?\n"
    assert len(waits) == len("Hi,you.Ok?")           # one wait per non-space char
    assert max(waits) >= 0.28                        # sentence end pauses longer


def test_personality_colours_noah_green_yellow_red(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    for who, code in (("noah", "\033[32m"), ("noah2", "\033[33m"), ("noah3", "\033[1;31m")):
        out = TTY()
        ui.reveal("x", who, out=out, sleep=lambda s: None)
        assert out.getvalue().startswith(code) and ui.RESET in out.getvalue()
    monkeypatch.setenv("NO_COLOR", "1")
    out = TTY()
    ui.reveal("x", "noah3", out=out, sleep=lambda s: None)
    assert "\033" not in out.getvalue()


def test_enter_skips_the_rest_of_the_text():
    out = io.StringIO()
    skipped = ui.reveal("abcdef", out=out, keys=FakeKeys(["x", "enter"]), sleep=lambda s: None)
    assert skipped and out.getvalue() == "abcdef\n"


def test_voice_loops_during_the_reveal_and_stops_after(tmp_path):
    (tmp_path / "voices").mkdir()
    (tmp_path / "voices" / "noah.wav").write_bytes(b"x")

    class P(audio.Player):
        live = []

        def __init__(self, path, loop, volume):
            super().__init__(path, loop, volume)
            self.up = True
            P.live.append(self)

        def alive(self):
            return self.up

        def stop(self):
            self.up = False
    m = audio.Mixer(backend=P, sleep=lambda s: None, table={}, directory=str(tmp_path))
    seen = []
    ui.reveal("hello", "noah", out=io.StringIO(), sleep=lambda s: seen.append([p.up for p in P.live]), mixer=m)
    assert seen and all(any(x) for x in seen)       # a voice player was alive while typing
    assert not any(p.up for p in P.live) and ("voice", "noah") in m.log


def test_broken_line_cuts_mid_word_then_types_fast_in_the_third_voice():
    out, waits = io.StringIO(), []
    ui.reveal_broken("It's not like I want to do this at all", "what is this fucking noise!?",
                     cut=0.5, out=out, sleep=waits.append)
    first, second = out.getvalue().split("\n")[:2]
    assert first == "It's not like I want"[:len(first)] and len(first) < len("It's not like I want to do this at all")
    assert second == "what is this fucking noise!?"
    assert min(waits) <= 0.006                        # the second line is typed very fast


def test_choose_with_arrow_keys_and_number_and_fallback():
    out = io.StringIO()
    assert ui.choose("pick", ["a", "b", "c"], out=out, keys=FakeKeys(["down", "down", "enter"])) == 2
    assert ui.choose("pick", ["a", "b", "c"], out=io.StringIO(), keys=FakeKeys(["up", "enter"])) == 2   # wraps
    assert ui.choose("pick", ["a", "b", "c"], out=io.StringIO(), keys=FakeKeys(["2"])) == 1
    class NoTTY:
        raw = False
    answers = iter(["x", "9", "2"])
    assert ui.choose("pick", ["a", "b"], out=io.StringIO(), inp=lambda p: next(answers), keys=NoTTY()) == 1


def test_boxed_text_is_an_invisible_block_with_lines_on_top_and_bottom():
    out = io.StringIO()
    ui.boxed("word " * 60, "mika", label="Mika", width=40, out=out, sleep=lambda s: None)
    lines = out.getvalue().rstrip("\n").split("\n")
    assert lines[0].startswith("\u2550\u2550") and "Mika" in lines[0] and lines[-1] == "\u2500" * 44
    assert len(lines[0]) == 44 == len(lines[-1])                                 # same width as the bottom line
    body = lines[1:-1]
    assert body and all(len(l) <= 42 and l.startswith("  ") for l in body)       # wrapped, indented, no side borders
    assert not any(ch in out.getvalue() for ch in "\u2502\u256d\u256e\u2570\u256f")


def test_boxed_skip_and_non_tty_instant():
    out = io.StringIO()
    assert ui.boxed("abcdef ghij", width=30, out=out, keys=FakeKeys(["x", "enter"]), sleep=lambda s: None)
    assert "abcdef ghij" in out.getvalue()
    out2 = io.StringIO()
    ui.boxed("hello", width=30, out=out2)                                        # no tty, default sleep: instant
    assert "hello" in out2.getvalue()


def test_choose_collapses_the_menu_into_the_chosen_line():
    out = io.StringIO()
    assert ui.choose("", ["a", "b", "c"], out=out, keys=FakeKeys(["down", "enter"])) == 1
    text = out.getvalue()
    assert "\033[3A" in text and text.rstrip().endswith("b")          # cursor up over the menu, then only the answer


def test_arrow_keys_work_with_one_press_even_when_the_bytes_arrive_one_by_one():
    import threading
    import time
    r, w = os.pipe()
    keys = ui.Keys(stream=os.fdopen(r, "rb", buffering=0, closefd=False))
    keys.fd = r
    keys.old = None

    def feed(parts):
        for p in parts:
            os.write(w, p)
            time.sleep(0.02)
    for parts, want in (([b"\x1b", b"[", b"B"], "down"), ([b"\x1b[A"], "up"), ([b"\x1bO", b"C"], "right"), ([b"\x1b[5~"], None)):
        t = threading.Thread(target=feed, args=(parts,))
        t.start()
        assert keys.read(timeout=1.0) == want                     # one press, one key, nothing left over
        t.join()
        assert not keys.ready(0.05)
    os.write(w, b"\r")
    assert keys.read(timeout=1.0) == "enter"
    os.close(w)


def test_sound_effects_get_their_own_centred_bold_line_outside_the_running_text():
    out = io.StringIO()
    ui.boxed("The plaster comes away. {{KRACK!}} Something inside moves.", width=40, out=out, sleep=lambda s: None)
    lines = out.getvalue().split("\n")
    sfx = [l for l in lines if "KRACK!" in l]
    assert len(sfx) == 1 and sfx[0].strip() == "KRACK!" and "KRACK!" not in "".join(l for l in lines if l is not sfx[0])
    i = lines.index(sfx[0])
    assert lines[i - 1] == "" and lines[i + 1] == ""                         # air above and below
    assert any("The plaster comes away." in l for l in lines[:i]) and any("Something inside moves." in l for l in lines[i:])
