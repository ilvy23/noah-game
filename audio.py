"""audio.py - the game's soundtrack manager (extends music.py's rules, does not replace it).

- All tracks live in soundtracks/ and are named in soundtracks/tracks.json (add tracks there).
- At most ONE music player runs, except during a crossfade of at most `fade` seconds.
- Volume changes go over mpv's IPC socket; with ffplay only (no IPC) a fade degrades to a hard cut.
- Everything that takes time (fades, sequences) runs in a daemon thread, so input never blocks.
  A newer request cancels an older sequence (generation counter).
- A missing file, a missing player or a dead player is ignored silently.
- Fully testable: pass a `backend` (player factory) and a `sleep` function.
"""
import atexit
import json
import math
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDTRACK_DIR = os.path.join(PROJECT_DIR, "soundtracks")
EXTS = (".flac", ".mp3", ".ogg", ".wav")

# --- music levels (tunable). mpv's volume property is CUBIC: 50 % is -18 dB, 32 % is -30 dB. Everything below is in true dB and converted once.
MUSIC_MASTER_DB = 3.0                          # all music, relative to the file at the percent the code asks for
MUSIC_TRIM_DB = {"noah-burns-song": -3.0, "strange": -2.0, "ending-special": -3.0}       # per song (these are mastered hotter: -8 / -16 / -13 LUFS against about -18)
RAMP_MIN_STEPS = 30
RAMP_STEPS_PER_SECOND = 30                      # every volume change is many small IPC steps on an ease curve, never one jump


def ramp_curve(n):
    """n points 1/n .. 1 of a smoothstep ease: monotonic, small steps, no jump at either end."""
    return [(lambda f: f * f * (3 - 2 * f))(i / float(n)) for i in range(1, n + 1)]


def db_to_pct(db):
    """mpv volume percent that gives `db` of real gain (cubic law)."""
    return 100.0 * 10 ** (db / 60.0)


def load_table(path=None):
    path = path or os.path.join(SOUNDTRACK_DIR, "tracks.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"default": ["town"], "fade": 0}


def find_file(name, directory=None):
    d = directory or SOUNDTRACK_DIR
    for ext in EXTS:
        p = os.path.join(d, name + ext)
        if os.path.isfile(p):
            return p
    return None


def duration(path):
    """Length in seconds via ffprobe, or None."""
    exe = shutil.which("ffprobe")
    if not exe or not path:
        return None
    try:
        out = subprocess.check_output([exe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                      stderr=subprocess.DEVNULL, timeout=5)
        return float(out.decode().strip())
    except Exception:
        return None


# ------------------------------------------------------------------ players
class Player:
    """One running audio file. Subclasses must be able to start, set volume and stop."""
    can_fade = False

    def __init__(self, path, loop, volume):
        self.path, self.loop, self.volume = path, loop, volume

    def alive(self):
        return False

    def set_volume(self, v):
        self.volume = v

    def stop(self):
        pass


class MpvPlayer(Player):
    can_fade = True

    def __init__(self, path, loop, volume, start=0.0, af=None):
        super().__init__(path, loop, volume)
        self.sock = os.path.join(tempfile.gettempdir(), "folk-mpv-%d-%d.sock" % (os.getpid(), id(self)))
        cmd = ["mpv", "--no-video", "--really-quiet", "--volume=%d" % volume] + (["--af=" + af] if af else []) + [
               "--input-ipc-server=" + self.sock, "--loop-file=inf" if loop else "--loop-file=no"] + (["--start=%.2f" % start] if start else []) + [path]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)

    def alive(self):
        return self.proc.poll() is None

    def set_volume(self, v):
        self.volume = v
        for _ in range(20):
            if os.path.exists(self.sock):
                break
            time.sleep(0.05)
        try:
            with socket.socket(socket.AF_UNIX) as s:
                s.settimeout(0.5)
                s.connect(self.sock)
                s.sendall((json.dumps({"command": ["set_property", "volume", max(0, min(130, v))]}) + "\n").encode())
        except OSError:
            pass

    def stop(self):
        try:
            if self.proc.poll() is None:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            self.proc.wait(timeout=2)
        except Exception:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            except Exception:
                pass
        try:
            os.unlink(self.sock)
        except OSError:
            pass


class FfplayPlayer(Player):
    def __init__(self, path, loop, volume, start=0.0):
        super().__init__(path, loop, volume)
        cmd = ["ffplay", "-nodisp", "-loglevel", "quiet", "-volume", str(volume)] + (["-ss", "%.2f" % start] if start else []) + \
              (["-loop", "0"] if loop else ["-autoexit"]) + [path]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)

    def alive(self):
        return self.proc.poll() is None

    def stop(self):
        try:
            if self.proc.poll() is None:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            self.proc.wait(timeout=2)
        except Exception:
            pass


def default_backend(path, loop, volume, start=0.0):
    if shutil.which("mpv"):
        return MpvPlayer(path, loop, volume, start)
    if shutil.which("ffplay"):
        return FfplayPlayer(path, loop, volume, start)
    return None


# ------------------------------------------------------------------ mixer
class Mixer:
    def __init__(self, backend=default_backend, sleep=time.sleep, table=None, directory=None, enabled=True):
        self.backend, self.sleep = backend, sleep
        self.t = table or load_table()
        self.dir = directory or SOUNDTRACK_DIR
        self.enabled = enabled and os.environ.get("MUSIC", "1") != "0"
        self.lock = threading.RLock()
        self.gen = 0
        self.music = None        # (name, player)
        self.sfx_players = []
        self.place = None
        self.scene_tag = None
        self.log = []            # for tests: ("start", name) / ("stop", name) / ("vol", name, v)
        self.default_i = 0
        self.threads = []
        self.fading = 0          # fade_outs in progress (any thread)
        self.duck_f, self.last_vol = 1.0, 100

    # -- basics
    def _start(self, name, loop, volume=100):
        if not self.enabled:
            return None
        path = find_file(name, self.dir)
        if not path:
            return None
        try:
            p = self.backend(path, loop, self._pct(name, volume, duck=False))
        except (OSError, ValueError):
            return None
        if p is not None:
            p._lvl = volume
            self.log.append(("start", name, volume))
        return p

    def _stop_player(self, name, p):
        if p is not None:
            self.log.append(("stop", name))
            p.stop()

    def _pct(self, name, v, duck=True):
        """The player's real mpv percent for the logical level v (0..100): master + per-song trim + the current duck (all in dB, cubic law)."""
        db = MUSIC_MASTER_DB + MUSIC_TRIM_DB.get(name, 0.0)
        if duck and self.duck_f < 1.0:
            db += 20.0 * math.log10(max(self.duck_f, 1e-4))
        return round(v * 10 ** (db / 60.0), 2)

    def _vol(self, name, p, v):
        self.log.append(("vol", name, v))
        self.last_vol = v
        p._lvl = v                                   # the logical level the player is at now (fades start from here, never from a jump)
        p.set_volume(self._pct(name, v))

    def duck(self, db=None, seconds=1.0):
        """Pull the running music down by `db` (default DUCK_DB) while a big effect plays, then bring it back on an ease curve (a thread; never blocks).
        Attack DUCK_ATTACK s, release DUCK_RELEASE s, both in many small steps."""
        db = DUCK_DB if db is None else db
        if not self.enabled or not self.music:
            return

        def run():
            low = 10 ** (db / 20.0)
            self._duck_ramp(1.0, low, DUCK_ATTACK)
            self.sleep(max(0.0, seconds))
            self._duck_ramp(low, 1.0, DUCK_RELEASE)
            self._set_duck(1.0)
        t = threading.Thread(target=run, daemon=True)
        self.threads.append(t)
        t.start()

    def _duck_ramp(self, a, b, seconds):
        for f in ramp_curve(max(RAMP_MIN_STEPS, int(seconds * RAMP_STEPS_PER_SECOND))):
            self._set_duck(a + (b - a) * f)
            self.sleep(seconds / max(RAMP_MIN_STEPS, int(seconds * RAMP_STEPS_PER_SECOND)))

    def _set_duck(self, f):
        with self.lock:
            self.duck_f = f
            cur = self.music
        if cur and cur[1].alive():
            try:
                cur[1].set_volume(self._pct(cur[0], self.last_vol))
            except Exception:
                pass

    def current(self):
        with self.lock:
            return self.music[0] if self.music and self.music[1].alive() else None

    def _run(self, fn, *a):
        self.gen += 1
        gen = self.gen
        t = threading.Thread(target=fn, args=(gen,) + a, daemon=True)
        self.threads.append(t)
        t.start()
        return t

    def wait(self):
        """Tests: wait for all sequence threads."""
        for t in list(self.threads):
            t.join(timeout=10)

    def _cancelled(self, gen):
        return gen is not None and gen != self.gen

    # -- fading
    def _ramp(self, name, p, a, b, seconds, gen, steps=20):
        """Fade the logical level a -> b (percent) over `seconds`: equal steps in AMPLITUDE (cubic law) on an ease curve, at least RAMP_MIN_STEPS steps."""
        if not getattr(p, "can_fade", False) or seconds <= 0:
            self._vol(name, p, b)
            return
        n = max(steps if steps and steps > 30 else 0, RAMP_MIN_STEPS, int(seconds * RAMP_STEPS_PER_SECOND))
        a3, b3 = (max(a, 0) / 100.0) ** 3, (max(b, 0) / 100.0) ** 3
        for f in ramp_curve(n):
            if self._cancelled(gen):
                return
            v = 100.0 * (a3 + (b3 - a3) * f) ** (1.0 / 3.0)
            if time.monotonic() < getattr(self, "dip_until", 0.0):
                v = v * 0.2
            self._vol(name, p, v)
            self.sleep(seconds / n)

    def crossfade(self, name, loop=True, fade=None, gen=None):
        """Fade the current track out while `name` fades in. Returns True if `name` is now playing."""
        fade = self.t.get("fade", 2.0) if fade is None else fade
        gen = self.gen if gen is None else gen
        with self.lock:
            old = self.music
            if old and old[0] == name and old[1].alive():
                return True
            can = bool(old) and getattr(old[1], "can_fade", False) and fade > 0
            new = self._start(name, loop, 0 if can else 100)
            if new is None:
                return False
            self.music = (name, new)
        if can and getattr(new, "can_fade", False):
            outs = threading.Thread(target=self._fade_pair, args=(old, name, new, fade, gen), daemon=True)
            outs.start()
            self.threads.append(outs)
        else:
            if old:
                self._stop_player(*old)
        return True

    def _fade_pair(self, old, name, new, fade, gen):
        """Equal-power crossfade (cos / sin on the amplitude), many small steps."""
        steps = max(RAMP_MIN_STEPS, int(fade * RAMP_STEPS_PER_SECOND))
        lo = getattr(old[1], "_lvl", 100)
        for i in range(1, steps + 1):
            if self._cancelled(gen):
                break
            f = i / float(steps)
            self._vol(old[0], old[1], lo * math.cos(f * math.pi / 2) ** (1.0 / 3.0))
            self._vol(name, new, 100.0 * math.sin(f * math.pi / 2) ** (1.0 / 3.0))
            self.sleep(fade / steps)
        self._stop_player(*old)
        # a cancelled fade must not push the incoming track to full volume while a newer request fades it
        # (two songs on top of each other); but if nobody took it over it must not stay stuck half quiet
        if self._cancelled(gen):
            with self.lock:
                if self.music and self.music[1] is new:
                    self._vol(name, new, 100)

    def fade_out(self, fade=None, gen=None):
        fade = self.t.get("fade", 2.0) if fade is None else fade
        if gen is None:                            # asked from outside: cancel every sequence that is still waiting to start a song
            self.gen += 1
            gen = self.gen
        with self.lock:
            old, self.music = self.music, None
            if old:
                self.fading += 1
        if old:
            try:
                self._ramp(old[0], old[1], getattr(old[1], "_lvl", 100), 0, fade, gen)
                self._stop_player(*old)
            finally:
                with self.lock:
                    self.fading -= 1

    def wait_silent(self, timeout=10.0):
        """Block until a running fade_out (maybe in another thread) has stopped its song."""
        end = time.monotonic() + timeout
        while self.fading > 0 and time.monotonic() < end:
            time.sleep(0.05)

    def stop(self):
        self.gen += 1
        with self.lock:
            old, self.music = self.music, None
            sfx, self.sfx_players = self.sfx_players, []
        for p in sfx:
            p.stop()
        if old:
            self._stop_player(*old)

    def sfx(self, name):
        """One-shot sound effect; may overlap music but not other music."""
        p = self._start(name, False)
        if p is not None:
            self.sfx_players = [x for x in self.sfx_players if x.alive()] + [p]
        return p

    # -- default music: game-1, game-2 alternate after each track
    def _default_name(self):
        lst = self.t.get("default") or ["town"]
        name = lst[self.default_i % len(lst)]
        if not find_file(name, self.dir):
            for fb in self.t.get("fallback", []):
                if find_file(fb, self.dir):
                    return fb
        return name

    def play_default(self, gen=None):
        gen = self.gen if gen is None else gen
        name = self._default_name()
        ok = self.crossfade(name, loop=False, gen=gen)
        if ok:
            threading.Thread(target=self._advance_default, args=(self.gen, name), daemon=True).start()
        return ok

    def tick(self):
        """If the default track ended, start the next one. Returns True if it advanced."""
        with self.lock:
            cur = self.music
        defaults = self.t.get("default") or []
        if cur and cur[0] in defaults and not cur[1].alive() and self.scene_tag is None:
            self.default_i += 1
            self.play_default()
            return True
        return False

    def _advance_default(self, gen, name):
        # poll in the background; real time on purpose (the injected sleep is only for fades)
        while not self._cancelled(gen):
            with self.lock:
                cur = self.music
            if not cur or cur[0] != name:
                return
            if not cur[1].alive():
                self.default_i += 1
                self.play_default(gen)
                return
            time.sleep(0.2)

    # -- public API used by the game
    def enter_place(self, place):
        with self.lock:
            self.place = place
            if self.scene_tag:       # a character scene owns the music until it ends
                return
        self._apply_place()

    def _apply_place(self):
        place = self.place
        if place in self.t.get("strange_places", []):
            self._run(self._strange_sequence)
        elif place in self.t.get("places", {}):
            self.gen += 1
            self.crossfade(self.t["places"][place], loop=True)       # a place with a song of its own
        else:
            cur = self.current()
            if cur in (self.t.get("default") or []) or cur is None or cur == self.t.get("strange", {}).get("track") \
                    or cur in self.t.get("fallback", []):
                if cur is None or cur == self.t.get("strange", {}).get("track"):
                    self.gen += 1
                    self.play_default()
            else:
                self.gen += 1
                self.play_default()

    def _strange_sequence(self, gen):
        s = self.t.get("strange", {})
        if self.current() == s.get("track"):
            return
        self.fade_out(gen=gen)
        if self._cancelled(gen):
            return
        tape = self.sfx(s.get("tape", ""))
        if tape is not None:
            d = duration(find_file(s["tape"], self.dir)) or 7.0
            self.sleep(d)
        if self._cancelled(gen):
            return
        self.crossfade(s.get("track", ""), loop=True, gen=gen)

    def scene_start(self, who, variant=None):
        """Character scene: noah (variant main|alt), connor, mika."""
        with self.lock:
            self.scene_tag = who
        if who == "noah":
            name = self.t["noah"].get("alt" if variant == "alt" else "main")
        elif who == "connor":
            name = self.t["connor"]["track"]
        elif who in self.t.get("scenes", {}):
            name = self.t["scenes"][who]
        elif who == "mika":
            self.gen += 1
            self._run(self._mika_sequence)          # his song and the smoke sound belong together: both from the first moment
            return
        else:
            return
        self.gen += 1
        self.crossfade(name, loop=True)

    def scene_end(self):
        with self.lock:
            self.scene_tag = None
        self._apply_place()

    def mika_smoke(self):
        """The smoke sound plays on top of Mika's song (which already runs); the song ducks while it plays."""
        self.scene_tag = "mika"
        self._run(self._mika_sequence)

    def _mika_sequence(self, gen):
        m = self.t["mika"]
        if self.current() != m["track"]:
            self.crossfade(m["track"], loop=True, gen=gen)
        self.sfx(m["smoke"])
        d = duration(find_file(m["smoke"], self.dir)) or 14.0
        with self.lock:
            cur = self.music
        if cur and cur[0] == m["track"]:
            self._ramp(cur[0], cur[1], 100, 55, 1.0, gen, steps=5)
            self.sleep(max(0.0, d - 3.0))
            if not self._cancelled(gen):
                self._ramp(cur[0], cur[1], 55, 100, 2.0, gen, steps=5)

    def boss_intro(self):
        """Rip sound, then the mood song starts almost silent and reaches full volume after boss_intro_seconds."""
        n = self.t["noah"]
        self.scene_tag = "boss"
        self._run(self._boss_intro_sequence)

    def _boss_intro_sequence(self, gen):
        n = self.t["noah"]
        total = float(self.t.get("boss_intro_seconds", 52))
        self.fade_out(fade=0.5, gen=gen)
        self.sfx(n["rip"])
        self.sleep(0.9)
        with self.lock:
            p = self._start(n["mood"], False, 3)
            if p is None:
                return
            self.music = (n["mood"], p)
        self._ramp(n["mood"], p, 3, 100, total, gen, steps=52)

    def dip(self, seconds):
        """Pull the running music down to a fifth for a moment (the held breath before the impact)."""
        self.dip_until = time.monotonic() + seconds

    def impact(self):
        """A low boom; the music is back at full level the moment it hits."""
        self.dip_until = 0.0
        self.sfx("impact")
        cur = self.music
        if cur and getattr(cur[1], "can_fade", False):
            self._vol(cur[0], cur[1], 100)

    def boss_phase_two(self):
        self.gen += 1
        self.crossfade(self.t["noah"]["boss"], loop=True, fade=3.0)

    def ending(self, name):
        self.scene_tag = "ending"
        self.gen += 1
        track = ending_track(name, self.t, self.dir)
        if track:
            self.fade_out(fade=1.5)
            self._start_and_hold(track)

    def fade_out_async(self, seconds):
        """Fade the running music out over `seconds` in a thread (the caller goes on at once)."""
        self._run(lambda gen: self.fade_out(fade=seconds, gen=gen))

    def bench_song(self):
        """The bench scene's music: the smoke sound (mika-smoke) plays out first and Mika's song comes in at half of it."""
        self.scene_tag = "mika"
        self._run(self._bench_sequence)

    def _bench_sequence(self, gen):
        m = self.t["mika"]
        self.fade_out(fade=1.0, gen=gen)
        self.sfx(m["smoke"])                                   # the lighter/smoke sound and Mika's song start TOGETHER, the song fades in
        if not self._cancelled(gen):
            self.crossfade(m["track"], loop=True, fade=3.0, gen=gen)

    def mika_ending_song(self, key):
        """A song of the hidden Mika ending (tracks.json "mika_ending"); silently nothing while the file does not exist yet."""
        name = (self.t.get("mika_ending") or {}).get(key)
        if name and find_file(name, self.dir):
            self.gen += 1
            self.crossfade(name, loop=True, fade=1.0)

    def play_section(self, name, start=0.0, end=None, fade_in=1.5, fade_out=3.0, volume=100):
        """Play a part of a song: from `start` seconds into the file (mpv --start / ffplay -ss) with a fade-in; with `end` (seconds in the file) it fades out
        over the last `fade_out` seconds and stops. Silently nothing when the file is missing. Returns the player or None."""
        if not self.enabled:
            return None
        path = find_file(name, self.dir)
        if not path:
            return None
        try:
            try:
                p = self.backend(path, False, 0, start)
            except TypeError:                                    # a backend without the start parameter (tests)
                p = self.backend(path, False, 0)
        except (OSError, ValueError):
            return None
        if p is None:
            return None
        self.log.append(("start", name, 0, start))
        p._lvl = 0
        with self.lock:
            self.gen += 1
            gen = self.gen
            old, self.music = self.music, (name, p)
        if old:                                      # a song section never plays on top of what is still running: that fades out under it (1.2 s)
            def take_over():
                self._ramp(old[0], old[1], getattr(old[1], "_lvl", 100), 0, 1.2, None)
                self._stop_player(*old)
            t0 = threading.Thread(target=take_over, daemon=True)
            self.threads.append(t0)
            t0.start()

        def ramp():
            self._ramp(name, p, 0, volume, fade_in, gen)
            if self._cancelled(gen):
                return
            if end is not None:
                self.sleep(max(0.0, (end - start) - fade_in - fade_out))
                self._ramp(name, p, volume, 0, fade_out, gen)
                if not self._cancelled(gen):
                    self._stop_player(name, p)
        t = threading.Thread(target=ramp, daemon=True)
        self.threads.append(t)
        t.start()
        return p

    def _start_and_hold(self, track):
        p = self._start(track, False)
        if p is not None:
            with self.lock:
                self.music = (track, p)

    def shutdown(self):
        self.stop()


def ending_track(name, table=None, directory=None):
    """The song of an ending: tracks.json "endings_special"[name] (the user's own song, soundtracks/ending-special.*) if that file exists, else "endings"[name]."""
    t = table or load_table()
    sp = (t.get("endings_special") or {}).get(name)
    if sp and find_file(sp, directory):
        return sp
    return (t.get("endings") or {}).get(name)


_mixer = None


def get():
    global _mixer
    if _mixer is None:
        _mixer = Mixer()
        atexit.register(_mixer.shutdown)
    return _mixer


# ------------------------------------------------------------------ one-shot sound effects (hooks: files are added later)
SFX_NAMES = ("boss-hit", "slam", "warning", "laser-charge", "laser-fire", "phase-shift", "heart-hurt", "noah-roar", "heartbeat")
_sfx_live, _sfx_last = [], {}
SFX_MAX_DEFAULT = 12.0                          # seconds a one-shot may play at most
SFX_MAX = {"crowd-scream-distant": 8.0, "scream-choir": 8.0, "fire-roar": 20.0, "glow-hum-rising": 32.0}


# --- how loud the one-shot effects are (all of it tunable here; TRUE dB: the gain is applied inside the mpv filter chain, not through the cubic volume).
# Level of a sound = SFX_GAIN_DB + SFX_TRIM_DB[name]. The trims bring every file to its class: big impacts about -18 LUFS, ordinary effects -22, Noah's burning
# and the tesseract scene's hum -25, ambience loops -29, screams and crowds -31 (and muffled: distant). Music beds sit around -26 LUFS and duck by DUCK_DB.
SFX_GAIN_DB = -8.0                              # the global knob: raise it to bring ALL effects forward, lower it to push them back
SFX_TRIM_DB = {
    # big impacts: in front
    "impact-boom-huge": -3, "sub-drop": -4, "hell-roar": 1, "glass-crack": 1, "blade-shatter": 5, "stone-split": 6, "bone-crack-1": 5, "bone-crack-2": 2,
    "iron-bar-hit": 2, "shield-hit": 6, "church-bell-toll": 6,
    # screams: a distant weeping
    "scream-distorted-1": -10, "scream-distorted-2": -10, "scream-fire": -13, "scream-falling-1": -8, "scream-falling-2": -14, "scream-reverse": -9,
    "scream-choir": -10, "crowd-scream-distant": -10,
    # ambience / loops: quiet
    "glow-hum-rising": -8, "lake-whispers": -7, "bubbles-gurgle": 6, "fall-wind": -7, "ground-rumble": -7, "gurgle-breath": -1,
    # Noah burning, flesh
    "fire-ignite": 0, "fire-roar": -7, "flesh-burn": 6, "blood-boil": 6, "growl-demon": -1, "stab-flesh": 2, "blood-spurt": 2, "sob-small": 2,
    # the tesseract scene and small ones
    "tesseract-spin-up": -8, "electric-surge": -7, "glitch-burst": -6, "static-burst": 6, "system-error-beep": -1, "typing-fast": 6, "riser-reverse": -3,
    "knife-draw": 2, "blade-block": -3}
SFX_FILTER = {n: "lowpass=f=2400" for n in ("scream-distorted-1", "scream-distorted-2", "scream-fire", "scream-falling-1", "scream-falling-2",
                                           "scream-reverse", "scream-choir", "crowd-scream-distant")}     # muffled, as if far away
SFX_FADE_IN, SFX_FADE_OUT = 0.025, 0.05        # seconds inside every effect: no click at the start or the end
DUCK_DB, DUCK_ATTACK, DUCK_RELEASE, DUCK_MIN_SECONDS = -6.0, 0.18, 1.0, 0.8   # the music ducks this much while an effect of at least that length plays
_dur_cache = {}


def sfx_level_db(name):
    return SFX_GAIN_DB + SFX_TRIM_DB.get(name, 0.0)


def sfx_filter(name, dur=None, cap=None):
    """The mpv --af chain of a one-shot: true-dB gain, optional lowpass, a short fade-in and a fade-out at the end (or at the cap)."""
    parts = ["volume=%.1fdB" % sfx_level_db(name)]
    if name in SFX_FILTER:
        parts.append(SFX_FILTER[name])
    parts.append("afade=t=in:st=0:d=%.3f" % SFX_FADE_IN)
    end = min(dur, cap) if dur and cap else (dur or cap)
    if end and end > SFX_FADE_OUT * 2:
        parts.append("afade=t=out:st=%.3f:d=%.3f" % (end - SFX_FADE_OUT, SFX_FADE_OUT))
    return ",".join(parts)


class PooledPlayer(Player):
    """One effect playing in the pool; alive() until its (estimated) end."""
    can_fade = False

    def __init__(self, pool, slot, until):
        super().__init__("", False, 100)
        self.pool, self.slot, self.until = pool, slot, until

    def alive(self):
        return time.monotonic() < self.until and self.pool.slots[self.slot].get("player") is self

    def stop(self):
        if self.pool.slots[self.slot].get("player") is self:
            self.pool.command(self.slot, ["stop"])
            self.until = 0.0


class SfxPool:
    """A few LONG-LIVED idle mpv processes for the one-shots: no process start and no audio-device open per effect (that was the crackle). Each effect is sent
    over the IPC socket as set_property af (gain + fades) and loadfile. Falls back to nothing (the caller then starts a single mpv)."""
    SIZE = 6

    def __init__(self, size=None, spawn=None, send=None):
        self.slots = [{} for _ in range(size or self.SIZE)]
        self._spawn_fn, self._send_fn = spawn or self._spawn, send or self._send
        self.lock = threading.Lock()

    @staticmethod
    def _spawn(sock):
        return subprocess.Popen(["mpv", "--idle=yes", "--no-video", "--really-quiet", "--force-window=no", "--audio-channels=stereo", "--audio-samplerate=48000",
                                 "--audio-stream-silence=yes", "--volume=100", "--input-ipc-server=" + sock], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    @staticmethod
    def _send(sock, commands):
        for _ in range(40):
            if os.path.exists(sock):
                break
            time.sleep(0.05)
        with socket.socket(socket.AF_UNIX) as c:
            c.settimeout(0.5)
            c.connect(sock)
            c.sendall(b"".join((json.dumps({"command": cmd}) + "\n").encode() for cmd in commands))

    def _slot(self, i):
        sl = self.slots[i]
        if not sl.get("proc") or sl["proc"].poll() is not None:
            sl["sock"] = os.path.join(tempfile.gettempdir(), "folk-sfx-%d-%d.sock" % (os.getpid(), i))
            sl["proc"] = self._spawn_fn(sl["sock"])
        return sl

    def command(self, i, cmd):
        try:
            self._send_fn(self.slots[i]["sock"], [cmd])
        except OSError:
            pass

    def play(self, path, af, seconds):
        """Start `path` with the filter chain `af` on an idle member (the one that finishes first when all are busy). Returns a PooledPlayer or None."""
        with self.lock:
            now = time.monotonic()
            i = min(range(len(self.slots)), key=lambda k: self.slots[k].get("until", 0.0))
            sl = self._slot(i)
            try:
                self._send_fn(sl["sock"], [["set_property", "af", "lavfi=[%s]" % af], ["loadfile", path, "replace"]])
            except OSError:
                return None
            sl["until"] = now + seconds
            p = PooledPlayer(self, i, sl["until"])
            sl["player"] = p
            return p

    def shutdown(self):
        for sl in self.slots:
            pr = sl.get("proc")
            if pr is not None and pr.poll() is None:
                try:
                    os.killpg(os.getpgid(pr.pid), signal.SIGTERM)
                except Exception:
                    pass
            try:
                os.unlink(sl.get("sock", ""))
            except OSError:
                pass


_pool = None


def _get_pool():
    global _pool
    if _pool is None and shutil.which("mpv"):
        _pool = SfxPool()
        atexit.register(_pool.shutdown)
    return _pool


def stop_sfx():
    for p in _sfx_live:
        try:
            p.stop()
        except Exception:
            pass
    _sfx_live.clear()


atexit.register(stop_sfx)


SFX_VOLUME = 85                                  # mpv percent (mpv's scale is cubic: 100 = file level, 85 = about -4 dB). The old behaviour, a little quieter.


def sfx(name, directory=None):
    """Play soundtracks/sfx/<name>.* once if such a file exists; silently do nothing otherwise (no file, no player, MUSIC=0).
    The same sound is not restarted within 80 ms. A plain one-shot next to the music: no ducking, capped in length (SFX_MAX)."""
    try:
        if os.environ.get("MUSIC", "1") == "0":
            return None
        path = find_file(name, os.path.join(directory or SOUNDTRACK_DIR, "sfx"))
        now = time.monotonic()
        if not path or now - _sfx_last.get(name, -9.0) < 0.08:
            return None
        _sfx_last[name] = now
        p = default_backend(path, False, SFX_VOLUME)
        if p:
            t = threading.Timer(SFX_MAX.get(name, SFX_MAX_DEFAULT), p.stop)
            t.daemon = True
            t.start()
        _sfx_live[:] = [x for x in _sfx_live if x.alive()] + ([p] if p else [])
        return p
    except Exception:
        return None


# ------------------------------------------------------------------ text voices (Undertale-style blips)
def voice_on(mixer, name):
    """Loop a short blip pattern while text is being revealed. Not music: may run next to it."""
    voice_off(mixer)
    d = getattr(mixer, "dir", None)
    if d is None or not getattr(mixer, "enabled", False):
        return None
    path = find_file(name, os.path.join(d, "voices"))
    if not path:
        return None
    try:
        p = mixer.backend(path, True, 55)
    except (OSError, ValueError):
        p = None
    mixer.voice = p
    if p is not None:
        mixer.log.append(("voice", name))
    return p


def voice_off(mixer):
    p = getattr(mixer, "voice", None)
    mixer.voice = None
    if p is not None:
        p.stop()
