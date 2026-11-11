import sys, os, io, contextlib
sys.path.insert(0, ".")

# Test 1: check_all prints 'Achievement unlocked: <name>'
from engine import State
import achievements

s = State()
s.visited = ["lunuen", "house", "forest"]  # 3 places -> first_steps
s.flags["met_noah"] = True  # met_noah

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    newly = achievements.check_all(s)

out = buf.getvalue()
print("=== check_all output ===")
print(repr(out))
print("newly:", newly)
assert "Achievement unlocked: First Steps" in out, "First Steps not printed"
assert "Achievement unlocked: A Friend in the Nook" in out, "met_noah not printed"
print("PASS: check_all prints notifications")

# Test 2: list_all shows both unlocked and locked
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    achievements.list_all(s)
out2 = buf2.getvalue()
print("=== list_all output ===")
print(out2)
assert "First Steps" in out2
assert "Explorer" in out2  # locked
assert "✓" in out2  # unlocked marker
assert "·" in out2  # locked marker
print("PASS: list_all shows unlocked and locked")

# Test 3: level formula
assert achievements.level(s) == 1 + 2 // 2 == 2, f"level={achievements.level(s)}"
print("PASS: level formula")

# Test 4: no double-print on second call
buf3 = io.StringIO()
with contextlib.redirect_stdout(buf3):
    newly2 = achievements.check_all(s)
assert newly2 == [], f"expected no new unlocks, got {newly2}"
assert "Achievement unlocked" not in buf3.getvalue()
print("PASS: no double-print")
