# tests/test_music.py — music module: mapping, restart rules, process-group kill.
# These tests never play real audio (a fake player command is injected) and
# never touch save.json.
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import music
import locations


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_ORIG_RESOLVE = music._resolve_player
_ORIG_TRACK_PATH = music._track_path


def _reset():
    """Reset module state between tests (including patched module functions)."""
    music.stop()
    music._enabled = True
    music._player_cmd = None
    music._player_failed = False
    music._music_env_disabled = False
    music._resolve_player = _ORIG_RESOLVE
    music._track_path = _ORIG_TRACK_PATH
    os.environ.pop("MUSIC", None)

def _fake_player(tmp_path):
    """Create a fake player script that just sleeps (no audio)."""
    fake = tmp_path / "fakeplayer"
    fake.write_text("#!/bin/sh\nexec sleep 60\n")
    fake.chmod(0o755)
    return str(fake)


def _inject_fake_player(tmp_path):
    """Point the music module at the fake player."""
    fake = _fake_player(tmp_path)
    music._player_cmd = [fake, "--loop=inf", "{file}"]


# ---------------------------------------------------------------------------
# mapping
# ---------------------------------------------------------------------------

def test_mapping_town():
    _reset()
    assert music.LOCATION_TRACKS["lunuen"] == "town"
    assert music.LOCATION_TRACKS["house"] == "town"
    assert music.LOCATION_TRACKS["gymnasium"] == "town"


def test_mapping_forest():
    _reset()
    assert music.LOCATION_TRACKS["forest"] == "forest"
    assert music.LOCATION_TRACKS["lake"] == "forest"
    assert music.LOCATION_TRACKS["schloss"] == "forest"


def test_mapping_nook():
    _reset()
    assert music.LOCATION_TRACKS["nook"] == "nook"


def test_mapping_covers_all_locations():
    """Every location in locations.LOCATIONS must have a track mapping."""
    _reset()
    for loc_id in locations.LOCATIONS:
        assert loc_id in music.LOCATION_TRACKS, f"{loc_id} has no track mapping"


# ---------------------------------------------------------------------------
# same-track no-restart
# ---------------------------------------------------------------------------

def test_same_track_no_restart(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)
    # create a fake track file so _start_player doesn't bail on missing file
    track_file = music.SOUNDTRACK_DIR + "/town.flac"
    assert os.path.isfile(track_file), "town.flac must exist in soundtracks/"

    ok1 = music.play_location("lunuen")
    assert ok1, "first play should start the player"
    proc1 = music._current_proc

    ok2 = music.play_location("house")  # same track (town)
    assert ok2
    assert music._current_proc is proc1, "same track must NOT restart the player"

    music.stop()


# ---------------------------------------------------------------------------
# change-track restarts
# ---------------------------------------------------------------------------

def test_change_track_restarts(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)

    ok1 = music.play_location("lunuen")  # town
    assert ok1
    proc1 = music._current_proc

    ok2 = music.play_location("forest")  # forest
    assert ok2
    proc2 = music._current_proc
    assert proc2 is not proc1, "different track must start a new player"
    assert proc1.poll() is not None, "old player must be stopped"

    music.stop()


# ---------------------------------------------------------------------------
# unknown location keeps current track
# ---------------------------------------------------------------------------

def test_unknown_location_keeps_current(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)

    ok1 = music.play_location("lunuen")
    assert ok1
    proc1 = music._current_proc

    # "unknown_place" is not in LOCATION_TRACKS
    ok2 = music.play_location("unknown_place")
    assert ok2, "unknown location should keep the current track playing"
    assert music._current_proc is proc1, "unknown location must NOT restart"

    music.stop()


# ---------------------------------------------------------------------------
# stop kills the process group
# ---------------------------------------------------------------------------

def test_stop_kills_process_group(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)

    ok = music.play_location("lunuen")
    assert ok
    proc = music._current_proc
    assert proc is not None
    assert proc.poll() is None, "player should be running before stop"

    music.stop()

    # give it a moment to die
    time.sleep(0.2)
    assert proc.poll() is not None, "player must be dead after stop()"


def test_stop_kills_group_not_just_child(tmp_path):
    """The player runs in its own process group; stop() kills the whole group."""
    _reset()
    _inject_fake_player(tmp_path)

    ok = music.play_location("lunuen")
    assert ok
    proc = music._current_proc
    pgid = os.getpgid(proc.pid)
    assert pgid != os.getpid(), "player must be in its own process group"

    music.stop()
    time.sleep(0.2)
    assert proc.poll() is not None


# ---------------------------------------------------------------------------
# missing file / missing player is silent
# ---------------------------------------------------------------------------

def test_missing_file_silent(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)
    # point at a track that doesn't exist
    music._track_path = lambda track: str(tmp_path / "nonexistent.flac")
    ok = music.play_location("lunuen")
    assert not ok, "missing file must not start a player"
    assert music._current_proc is None


def test_missing_player_silent(tmp_path):
    _reset()
    # no player at all
    music._player_cmd = None
    music._resolve_player = lambda: None
    ok = music.play_location("lunuen")
    assert not ok, "missing player must not start anything"
    assert music._current_proc is None


# ---------------------------------------------------------------------------
# disable / MUSIC=0
# ---------------------------------------------------------------------------

def test_disable_stops(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)
    ok = music.play_location("lunuen")
    assert ok, "play_location should start the player before disable()"
    music.disable()
    assert music._current_proc is None, "disable() must stop the player"


def test_music_env_zero(tmp_path):
    _reset()
    _inject_fake_player(tmp_path)
    # simulate the MUSIC=0 environment switch (read at import time)
    music._music_env_disabled = True
    try:
        ok = music.play_location("lunuen")
        assert not ok, "MUSIC=0 must prevent the player from starting"
    finally:
        music._music_env_disabled = False
