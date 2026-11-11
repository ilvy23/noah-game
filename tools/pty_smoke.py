"""tools/pty_smoke.py - runs the game in a real pty and reads the screen with pyte.
uv run --no-project --with pyte python3 tools/pty_smoke.py COLSxROWS "args" seconds "keys"   (keys: e=Enter, n=next key, l/r/u/d arrows)"""
import fcntl, os, pty, select, struct, subprocess, sys, termios, time
import pyte

cols, rows = map(int, sys.argv[1].split("x"))
args, secs, keys = sys.argv[2].split(), float(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else ""
m, s = pty.openpty()
fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
env = dict(os.environ, MUSIC="0", TERM="xterm-256color", COLORTERM="truecolor", PYTHONUNBUFFERED="1")
cmd = [sys.executable, "-c", open(args[1]).read()] if args[0] == "-c" else [sys.executable, "play.py"] + args
p = subprocess.Popen(cmd, stdin=s, stdout=s, stderr=s, env=env, close_fds=True)
os.close(s)
scr = pyte.Screen(cols, rows); st = pyte.ByteStream(scr)
raw = b""
t0, ki = time.time(), 0
last = t0 + 0.5
seq = {"e": b"\r", "n": b" ", "l": b"\x1b[D", "r": b"\x1b[C", "u": b"\x1b[A", "d": b"\x1b[B", "q": b"q"}
while time.time() - t0 < secs and p.poll() is None:
    if select.select([m], [], [], 0.1)[0]:
        try:
            d = os.read(m, 65536)
        except OSError:
            break
        raw += d; st.feed(d)
    if ki < len(keys) and keys[ki] == "m":                      # m = wait until the fight menu is on screen
        if "FIGHT" in "\n".join(scr.display) and time.time() - last > 1.0:
            ki += 1; last = time.time()
    elif ki < len(keys) and time.time() - last > 0.5:
        if keys[ki] != "w":
            os.write(m, seq[keys[ki]])
        ki += 1; last = time.time()
alive = p.poll() is None
if alive:
    p.kill()
text = "\n".join(scr.display)
print("\n".join(l.rstrip() for l in scr.display))
print("---- winops: query", raw.count(b"\x1b[13t"), "moves", raw.count(b"\x1b[3;1"), "speech", raw.count(b"every side at once"), "alive at end:", alive, "exit:", p.poll(), "bytes:", len(raw), "traceback:", b"Traceback" in raw, "nonblank rows:", sum(1 for l in scr.display if l.strip()))
