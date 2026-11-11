"""Prints the loudness of every sound effect before and after audio.py's SFX_GAIN_DB / SFX_TRIM_DB / SFX_FILTER (ffmpeg ebur128: integrated LUFS, peak dBFS).
    python3 tools/sfx_levels.py [name ...]      (read-only: the files are only decoded to null)"""
import math
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audio  # noqa: E402


def measure(path, chain=""):
    af = (chain + "," if chain else "") + "ebur128=peak=true"
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", af, "-f", "null", "-"], capture_output=True, text=True, timeout=60)
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return (float(lufs[-1]) if lufs else None), (float(peak[-1]) if peak else None)


def music_table():
    d = audio.SOUNDTRACK_DIR
    print("\n%-24s %8s | %8s %8s %s" % ("music bed", "LUFS", "at 100%", "at 80%", "(master %+.0f dB, ducked %+.0f dB more under an effect)" % (audio.MUSIC_MASTER_DB, audio.DUCK_DB)))
    for n in ("mika", "noah-burns-song", "strange", "boss-noa", "forest", "town", "connor", "ending-3", "ending-special"):
        p = audio.find_file(n, d)
        if not p:
            continue
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-t", "90", "-i", p, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, timeout=90)
        v = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if v:
            base = float(v[-1]) + audio.MUSIC_MASTER_DB + audio.MUSIC_TRIM_DB.get(n, 0.0)
            print("%-24s %8s | %8.1f %8.1f" % (n, v[-1], base, base + 60 * math.log10(0.8)))


def main(names):
    d = os.path.join(audio.SOUNDTRACK_DIR, "sfx")
    names = names or sorted(os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".mp3"))
    print("%-24s %8s %8s | %8s %8s | %6s" % ("sound", "LUFS", "peak", "LUFS'", "peak'", "dB"))
    for n in names:
        p = audio.find_file(n, d)
        if not p:
            continue
        chain = audio.sfx_filter(n).split(",afade")[0]
        a, b = measure(p), measure(p, chain)
        print("%-24s %8s %8s | %8s %8s | %6.1f" % (n, a[0], a[1], b[0], b[1], audio.sfx_level_db(n)))
    music_table()


if __name__ == "__main__":
    main(sys.argv[1:])
