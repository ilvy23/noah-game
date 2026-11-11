"""A harness that plays whole endings through the REAL Mixer with a fake backend and measures how long two songs are audible at the same time.
Time is scaled (SCALE): the mixer's fades sleep 1 % of their length, so a six-minute ending runs in seconds; the overlap is measured in virtual seconds."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCALE = 0.01
AUDIBLE = 8.0                       # mpv percent below which a player counts as silent
SFX_LIKE = {"mika-smoke", "strange-tape", "noa-rip", "impact"}       # one-shots that are meant to play over a song
T0 = time.monotonic()


class Rec:
    """A fake player that logs every start / volume / stop with the (wall) time."""
    can_fade = True
    events = []
    lock = threading.Lock()

    def __init__(self, path, loop, volume, start=0.0):
        self.name = os.path.splitext(os.path.basename(path))[0]
        self.up, self.volume = True, volume
        self.log("start", volume)

    def log(self, what, v=None):
        with Rec.lock:
            Rec.events.append((time.monotonic(), id(self), self.name, what, v))

    def alive(self):
        return self.up

    def set_volume(self, v):
        self.volume = v
        self.log("vol", v)

    def stop(self):
        if self.up:
            self.up = False
            self.log("stop")


def overlaps(events, min_len=0.0):
    """[(start_virtual, length_virtual, [names])] where two or more songs (not one-shots) were audible at once."""
    ev = sorted(events)
    state, out, cur = {}, [], None
    for t, pid, name, what, v in ev:
        if name in SFX_LIKE:
            continue
        if what in ("start", "vol"):
            state[pid] = (name, v)
        elif what == "stop":
            state.pop(pid, None)
        loud = sorted(n for n, vv in state.values() if vv >= AUDIBLE)
        if len(loud) >= 2 and cur is None:
            cur = (t, loud)
        elif len(loud) < 2 and cur is not None:
            out.append(((cur[0] - T0) / SCALE, (t - cur[0]) / SCALE, cur[1]))
            cur = None
    if cur is not None:
        out.append(((cur[0] - T0) / SCALE, (ev[-1][0] - cur[0]) / SCALE, cur[1]))
    return [o for o in out if o[1] > min_len]


def make_mixer(tmp_path, audio):
    table = audio.load_table()
    names = set()

    def walk(v):
        if isinstance(v, str):
            names.add(v)
        elif isinstance(v, list):
            [walk(x) for x in v]
        elif isinstance(v, dict):
            [walk(x) for x in v.values()]
    walk({k: v for k, v in table.items() if k not in ("fade", "boss_intro_seconds", "noah_burns_song")})
    names.add("noah-burns-song")
    for n in names:
        (tmp_path / (n + ".flac")).write_bytes(b"x")
    Rec.events = []
    return audio.Mixer(backend=Rec, sleep=lambda s: time.sleep(s * SCALE), table=table, directory=str(tmp_path))
