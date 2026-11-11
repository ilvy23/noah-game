import sys, os, io, contextlib
sys.path.insert(0, "..")

# Import the game modules directly (no subprocess, no save.json)
import engine
from engine import State, render_quiet
import achievements

# Build a fresh state
s = State()

# Simulate visiting 3 places (lunuen is already visited)
s.visited.append("house")
s.visited.append("nook")

# Call check_all and capture what it prints
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    newly = achievements.check_all(s)

out = buf.getvalue()
print("=== Newly unlocked:", newly)
print("=== Output:")
print(out)
print("=== 'Achievement unlocked:' in output:", "Achievement unlocked:" in out)

# Now test list_all
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    achievements.list_all(s)
out2 = buf2.getvalue()
print("\n=== list_all output (first 20 lines):")
for ln in out2.splitlines()[:20]:
    print(ln)
print("=== ✓ found:", "✓" in out2)
print("=== · found:", "·" in out2)
