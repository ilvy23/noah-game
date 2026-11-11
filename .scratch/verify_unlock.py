# Verify that achievements.check_all prints 'Achievement unlocked: <name>' exactly once per unlock
import io, sys, os, contextlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import achievements
from engine import State

s = State()
# Simulate: visit 3 places
s.visited = ["village", "forest", "lake"]
# Simulate: met noah
s.flag("met_noah")
# Simulate: found an item
s.inventory.append("letter")

# Capture stdout
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    newly = achievements.check_all(s)

out = buf.getvalue()
print("newly unlocked:", newly)
print("output:")
print(out)

# Verify each unlock printed exactly once
for a in achievements.ACHIEVEMENTS:
    if a["id"] in newly:
        line = f"Achievement unlocked: {a['name']}"
        count = out.count(line)
        assert count == 1, f"{line} printed {count} times, expected 1"
        print(f"OK: {line} printed exactly once")

# Verify no duplicate unlocks on second call
buf2 = io.StringIO()
with contextlib.redirect_stdout(buf2):
    newly2 = achievements.check_all(s)
assert newly2 == [], f"second call should unlock nothing, got {newly2}"
assert buf2.getvalue() == "", f"second call should print nothing, got {buf2.getvalue()!r}"
print("OK: second call unlocks nothing, prints nothing")
print("ALL CHECKS PASSED")
