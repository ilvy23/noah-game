"""Stage 2 (part 6/6) verification:
1. Old save (tests/fixtures/save_v1.json, has a sanity value) loads without error.
2. deaths.py / characters.py contain no on-screen sanity messages.
3. No test asserts the presence of a sanity display string.
"""
import json
import re
import sys

sys.path.insert(0, ".")
import engine  # noqa: E402

# --- 1. old save loads -------------------------------------------------------
with open("tests/fixtures/save_v1.json", encoding="utf-8") as f:
    raw = json.load(f)
s = engine.State.from_dict(raw)
print("save_v1.json loaded OK; sanity value in save:", raw.get("sanity"))
print("  State.sanity ==", s.sanity)

# --- 2. sanity mentions in deaths.py / characters.py -------------------------
pat = re.compile(r"sanity", re.IGNORECASE)
problems = []
for fname in ("deaths.py", "characters.py"):
    for i, line in enumerate(open(fname, encoding="utf-8"), 1):
        if pat.search(line):
            problems.append((fname, i, line.rstrip()))
if problems:
    print("\nSANITY MENTIONS FOUND:")
    for fname, i, line in problems:
        print(f"  {fname}:{i}: {line}")
else:
    print("\nno 'sanity' mentions in deaths.py / characters.py")

# --- 3. tests asserting sanity display strings -------------------------------
print("\nTEST MENTIONS OF 'sanity':")
import glob
for fname in sorted(glob.glob("tests/*.py")):
    for i, line in enumerate(open(fname, encoding="utf-8"), 1):
        if pat.search(line):
            print(f"  {fname}:{i}: {line.rstrip()}")

print("\nDONE")
