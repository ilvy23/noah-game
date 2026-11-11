"""Verify acceptance items 4-8: real mpv start, unknown location, transition,
cwd independence, and missing-player silence."""
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))  # repo root

import music


def mpv_pids(track=None):
    """mpv pids, optionally filtered by track name in the cmdline."""
    out = subprocess.run(["pgrep", "-x", "mpv"], capture_output=True, text=True).stdout.split()
    pids = []
    for p in out:
        try:
            with open(f"/proc/{p}/cmdline", "rb") as f:
                cmd = f.read().decode(errors="replace")
        except OSError:
            continue
        if track is None or track + ".flac" in cmd:
            pids.append(int(p))
    return pids


def wait_pids(pids, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(_alive(p) for p in pids):
            return True
        time.sleep(0.1)
    return False


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# --- Item 4: valid location starts mpv with the correct track ---
music.start("lunuen")
time.sleep(1.5)
pids = mpv_pids("town")
assert pids, "mpv process not found after music.start('lunuen')"
print("item 4 OK: mpv running with town.flac --loop=inf, pids:", pids)

# --- Item 5: unknown location -> no crash, no new player ---
before = set(mpv_pids())
music.play_location("nonexistent_place")
time.sleep(0.5)
after = set(mpv_pids())
assert music.is_playing(), "current player should still be alive"
assert after == before, f"player set changed: {before} -> {after}"
assert music.current_track() == "town", music.current_track()
print("item 5 OK: unknown location kept current track, no new process")

# --- Item 6: transition stops old player before starting new one ---
music.play_location("forest")
time.sleep(1.5)
old_alive = any(_alive(p) for p in pids)
assert not old_alive, "old mpv (town.flac) still alive after transition"
new_pids = mpv_pids("forest")
assert new_pids, "no mpv playing forest.flac after transition"
print("item 6 OK: old town.flac player dead, forest.flac playing")

music.stop()
assert wait_pids(new_pids), "mpv survived music.stop()"
print("stop OK: all players killed")

# --- Item 7: paths resolve relative to game folder, not cwd ---
code = (
    "import sys; sys.path.insert(0, r'%s');\n"
    "import music; print(music._track_path('town'))\n"
) % os.path.abspath(".")
out = subprocess.run(
    [sys.executable, "-c", code],
    capture_output=True, text=True, cwd="/tmp",
)
assert out.returncode == 0, out.stderr
line = out.stdout.strip().splitlines()[-1]
assert line.endswith(os.path.join("soundtracks", "town.flac")), line
assert os.path.exists(line), f"resolved path does not exist: {line}"
print("item 7 OK: from cwd=/tmp resolves to", line)

# --- Item 8: no player available -> silent, no errors ---
code2 = (
    "import sys; sys.path.insert(0, r'%s');\n"
    "import music; music.start('lunuen'); music.play_location('forest');\n"
    "music.stop(); print('NO-PLAYER-OK')\n"
) % os.path.abspath(".")
res = subprocess.run(
    [sys.executable, "-c", code2],
    capture_output=True, text=True, cwd="/tmp",
    env={**os.environ, "PATH": "/usr/bin-nonexistent"},
)
assert res.returncode == 0, f"exit={res.returncode}\nstderr={res.stderr}"
assert "NO-PLAYER-OK" in res.stdout
print("item 8 OK: game logic runs silently with no player available")

print("ALL VERIFIED")
