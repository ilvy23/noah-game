import sys, os, io, contextlib
sys.path.insert(0, "..")

import engine
from engine import State
import achievements

# Test 1: check_all with a state that has no achievements key at all
s = State()
s.visited.append("house")
s.visited.append("nook")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    newly = achievements.check_all(s)
print("Test 1 (fresh state, 3 visited):")
print("  newly:", newly)
print("  output:", repr(buf.getvalue().strip()))
assert "Achievement unlocked: First Steps" in buf.getvalue()
print("  PASS")

# Test 2: check_all again — should not re-unlock
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    newly2 = achievements.check_all(s)
print("\nTest 2 (second call, already unlocked):")
print("  newly:", newly2)
print("  output:", repr(buf2.getvalue().strip()))
assert newly2 == []
print("  PASS")

# Test 3: check_all with a state that has an exception in a check
s3 = State()
s3.flags["achievements"] = []
# Force an exception in one check by making s.visited a non-list
class BadVisited:
    def __len__(self):
        raise ValueError("boom")
s3.visited = BadVisited()
buf3 = io.StringIO()
with contextlib.redirect_stdout(buf3):
    newly3 = achievements.check_all(s3)
print("\nTest 3 (exception in check):")
print("  newly:", newly3)
print("  output:", repr(buf3.getvalue().strip()))
assert newly3 == []
print("  PASS")

# Test 4: list_all with no achievements unlocked
s4 = State()
buf4 = io.StringIO()
with contextlib.redirect_stdout(buf4):
    achievements.list_all(s4)
out4 = buf4.getvalue()
print("\nTest 4 (list_all, no unlocks):")
print("  Level line:", [l for l in out4.splitlines() if "Level" in l])
print("  ✓ found:", "✓" in out4)
print("  · found:", "·" in out4)
assert "·" in out4
assert "✓" not in out4
print("  PASS")

# Test 5: list_all with some unlocks
s5 = State()
s5.flags["achievements"] = ["first_steps", "met_noah"]
buf5 = io.StringIO()
with contextlib.redirect_stdout(buf5):
    achievements.list_all(s5)
out5 = buf5.getvalue()
print("\nTest 5 (list_all, 2 unlocks):")
print("  ✓ found:", "✓" in out5)
print("  · found:", "·" in out5)
assert "✓" in out5
assert "·" in out5
print("  PASS")

# Test 6: level formula
s6 = State()
s6.flags["achievements"] = []
assert achievements.level(s6) == 1
s6.flags["achievements"] = ["a"]
assert achievements.level(s6) == 1
s6.flags["achievements"] = ["a", "b"]
assert achievements.level(s6) == 2
s6.flags["achievements"] = ["a", "b", "c"]
assert achievements.level(s6) == 2
s6.flags["achievements"] = ["a", "b", "c", "d"]
assert achievements.level(s6) == 3
print("\nTest 6 (level formula): PASS")

print("\nAll tests passed.")
