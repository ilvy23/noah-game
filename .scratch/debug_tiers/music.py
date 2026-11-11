# music.py — FOLK: looping background music.
"""Background music for FOLK.

Design rules (see the brief):
- Tracks live in ./soundtracks/ (resolved relative to the game folder, not the cwd).
- Mapping by location id: lunuen/house/gymnasium -> town, forest/lake/schloss -> forest,
  nook -> nook. Unknown location -> keep the current track (no restart).
- The player is launched in its own process group (start_new_session=True) and every
  stop path kills the whole group, so no orphan player process can ever survive.
- Cleanup is layered: atexit (normal exit) + try/finally in main (exceptions, Ctrl-C).
- Music is optional: missing files or a missing player are ignored silently.
- The player's stdout/stderr/stdin go to DEVNULL so the game's text output and
  input are never disturbed.
- This module never touches save.json.
"""

import atexit
import os
import shutil
import signal
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDTRACK_DIR = os.path.join(PROJECT_DIR, "soundtracks")

# location id -> track name (without extension)
LOCATION_TRACKS = {
    "lunuen": "town",
    "house": "town",
    "gymnasium": "town",
    "forest": "forest",
    "lake": "forest",
    "schloss": "forest",
    "nook": "nook",
}

# Candidate players, in priority order. Each entry is a list of argument
# templates; "{file}" is replaced with the track path.
_PLAYER_COMMANDS = [
    ["mpv", "--no-video", "--really-quiet", "--loop=inf", "{file}"],
    ["ffplay", "-nodisp", "-autoexit", "-loop", "0", "{file}"],
    ["pw-play", "{file}"],
]

# ---------------------------------------------------------------------------
# module state
# ---------------------------------------------------------------------------

_current_track = None          # track name (e.g. "town") of the running player
_current_proc = None           # the running player Popen
_enabled = True                # flipped by disable() / MUSIC=0 / --no-music
_player_cmd = None             # resolved player command (without the file), or None
_player_failed = False         # set once the resolved player dies immediately


# Read once at import time; tests can flip _enabled directly.
_music_env_disabled = os.environ.get("MUSIC", "1") == "0"


def _music_disabled() -> bool:
    """True if music is disabled via the MUSIC=0 environment switch."""
    return _music_env_disabled


def disable() -> None:
    """Turn music off for this run (used by the --no-music flag)."""
    global _enabled
    _enabled = False
    stop()


def _resolve_player() -> list:
    """Find the first usable player command. Cached after the first call.

    Returns the command list with the file argument removed (the file is
    appended at launch time), or None if no player exists.
    """
    global _player_cmd
    if _player_cmd is not None:
        return _player_cmd
    for template in _PLAYER_COMMANDS:
        exe = template[0]
        if shutil.which(exe) is not None:
            _player_cmd = template
            return _player_cmd
    return None


def _track_path(track: str) -> str:
    return os.path.join(SOUNDTRACK_DIR, track + ".flac")


def _kill_group(proc) -> None:
    """Kill the player's whole process group; never raises."""
    if proc is None:
        return
    try:
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
    except Exception:
        pass
    try:
        proc.wait(timeout=2)
    except Exception:
        pass


def stop() -> None:
    """Stop the current player (kill its process group). Idempotent, silent."""
    global _current_track, _current_proc
    _kill_group(_current_proc)
    _current_proc = None
    _current_track = None


def _start_player(track: str) -> bool:
    """Launch the player for `track`. Returns True if it is running.

    Silent on every failure mode: no player, missing file, immediate crash.
    """
    global _current_track, _current_proc, _player_failed
    if not _enabled:
        return False
    if _music_env_disabled:
        return False
    cmd_template = _resolve_player()
    if cmd_template is None:
        return False
    path = _track_path(track)
    if not os.path.isfile(path):
        return False

    cmd = [arg.replace("{file}", path) if "{file}" in arg else arg
           for arg in cmd_template]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,   # own process group -> killable as a group
        )
    except (OSError, ValueError):
        return False

    # give it a moment to die on its own (bad file, missing codec, ...)
    try:
        proc.wait(timeout=0.3)
    except subprocess.TimeoutExpired:
        pass
    if proc.poll() is not None:
        # the player died immediately: treat it as a failed player
        _player_failed = True
        return False

    _current_proc = proc
    _current_track = track
    return True


def play_location(loc_id: str) -> bool:
    """Start music for a location id.

    - Unknown location id: keep the current track (no new player started).
    - Same track already playing: do NOT restart it.
    - Different track: stop the old player first, then start the new one.
    Returns True if a player is running for this location afterwards.
    """
    track = LOCATION_TRACKS.get(loc_id)
    if track is None:
        return _current_proc is not None and _current_proc.poll() is None
    if track == _current_track and _current_proc is not None \
            and _current_proc.poll() is None:
        return True
    stop()
    return _start_player(track)


def start(loc_id: str) -> bool:
    """Start music for the opening location (used at game start)."""
    return play_location(loc_id)


def is_playing() -> bool:
    return _current_proc is not None and _current_proc.poll() is None


def current_track() -> str:
    return _current_track


# ---------------------------------------------------------------------------
# atexit: normal exit (quit, death, ending, menu quit) always stops the player
# ---------------------------------------------------------------------------

def _atexit_stop() -> None:
    stop()


atexit.register(_atexit_stop)
