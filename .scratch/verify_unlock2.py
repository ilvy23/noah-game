"""Verify that 'Achievement unlocked:' is printed at the right moments in main.py."""
import io, sys, contextlib, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import engine
import main
import achievements

def fresh_state():
    s = engine.State()
    return s

def capture(fn, *args, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kw)
    return buf.getvalue()

# --- 1. Visiting a new location triggers unlock ---
s = fresh_state()
s.visited = []
s.visited.append("nook")
# Simulate arriving at a new location: the game_loop adds to visited then calls check_all
# We test the check_all call directly:
out = capture(achievements.check_all, s)
assert "Achievement unlocked:" not in out, f"should not unlock yet: {out}"
s.visited.append("village")
s.visited.append("forest")
out = capture(achievements.check_all, s)
assert "Achievement unlocked: First Steps" in out, f"expected First Steps unlock, got: {out}"
print("PASS: visiting 3 locations triggers 'Achievement unlocked: First Steps'")

# --- 2. Talking to Noah triggers unlock ---
s2 = fresh_state()
s2.flag("met_noah")
out = capture(achievements.check_all, s2)
assert "Achievement unlocked: A Friend in the Nook" in out, f"got: {out}"
print("PASS: talking to Noah triggers 'Achievement unlocked: A Friend in the Nook'")

# --- 3. Talking to Connor triggers unlock ---
s3 = fresh_state()
s3.flag("met_connor")
out = capture(achievements.check_all, s3)
assert "Achievement unlocked: The Keeper's Trust" in out, f"got: {out}"
print("PASS: talking to Connor triggers 'Achievement unlocked: The Keeper's Trust'")

# --- 4. Talking to Mika triggers unlock ---
s4 = fresh_state()
s4.flag("met_mika")
out = capture(achievements.check_all, s4)
assert "Achievement unlocked: The Quiet One" in out, f"got: {out}"
print("PASS: talking to Mika triggers 'Achievement unlocked: The Quiet One'")

# --- 5. Finding an item triggers unlock ---
s5 = fresh_state()
s5.inventory.append("letter")
out = capture(achievements.check_all, s5)
assert "Achievement unlocked: Something in Hand" in out, f"got: {out}"
print("PASS: finding an item triggers 'Achievement unlocked: Something in Hand'")

# --- 6. Surviving to day 3 triggers unlock ---
s6 = fresh_state()
s6.day = 3
out = capture(achievements.check_all, s6)
assert "Achievement unlocked: Three Days" in out, f"got: {out}"
print("PASS: surviving to day 3 triggers 'Achievement unlocked: Three Days'")

# --- 7. Reaching an ending triggers unlock ---
s7 = fresh_state()
s7.flags["ending"] = "quiet"
out = capture(achievements.check_all, s7)
assert "Achievement unlocked: The Quiet Ending" in out, f"got: {out}"
print("PASS: reaching quiet ending triggers 'Achievement unlocked: The Quiet Ending'")

# --- 8. Triggering a death triggers unlock ---
s8 = fresh_state()
s8.flags["death_collapse"] = True
out = capture(achievements.check_all, s8)
assert "Achievement unlocked: Collapse" in out, f"got: {out}"
print("PASS: death by collapse triggers 'Achievement unlocked: Collapse'")

# --- 9. No duplicate unlocks ---
s9 = fresh_state()
s9.flag("met_noah")
out1 = capture(achievements.check_all, s9)
out2 = capture(achievements.check_all, s9)
assert "Achievement unlocked:" in out1
assert "Achievement unlocked:" not in out2, f"second call should not re-unlock: {out2}"
print("PASS: no duplicate unlock on second check_all call")

print("\nAll 9 checks passed.")
