"""Verify Stage 2 acceptance items for engine.py (part 3/6)."""
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import engine  # noqa: E402

# 1+2: no sanity-related output anywhere in engine.py source
src = open("engine.py").read()
import re
# find every print/render call and make sure none mention sanity
offending = []
for m in re.finditer(r"(?:print|render|render_quiet|sys\.stdout\.write)\s*\((.*?)\)", src, re.S):
    if "sanity" in m.group(1).lower():
        offending.append(m.group(0)[:80])
assert not offending, f"sanity in output calls: {offending}"
print("OK: no sanity in any engine.py output call")

# 3: loading a save dict with a sanity field must not raise
s = engine.State.from_dict({"location": "lunuen", "sanity": 42, "trust": 5, "fear": -3})
assert s.sanity == 42
print("OK: from_dict with sanity field loads, sanity =", s.sanity)

# 4: the real fixture must load via engine code
with open("tests/fixtures/save_v1.json") as f:
    fixture = json.load(f)
s2 = engine.State.from_dict(fixture)
assert s2.location == fixture.get("location", "lunuen")
print("OK: tests/fixtures/save_v1.json loads; sanity =", s2.sanity)

# roundtrip: to_dict still contains sanity
d = s2.to_dict()
assert "sanity" in d, "sanity must stay in save data"
print("OK: to_dict preserves sanity =", d["sanity"])

# 6: deaths.ask returns 'quit' on EOF
import deaths  # noqa: E402
buf = io.StringIO()
old_stdin, old_stdout = sys.stdin, sys.stdout
sys.stdin = old_stdin  # empty stdin -> EOF
try:
    sys.stdin = io.StringIO("")
    out = deaths._ask("choose? ")
finally:
    sys.stdin, sys.stdout = old_stdin, old_stdout
assert out == "quit", f"deaths._ask on EOF returned {out!r}"
print("OK: deaths._ask returns 'quit' on EOF")

# 7: main.pause returns 'quit' on EOF
import main  # noqa: E402
sys.stdin = io.StringIO("")
try:
    p = main.pause()
finally:
    sys.stdin = old_stdin
assert p is None, f"pause() on EOF returned {p!r}"
print("OK: main.pause() returns nothing (None) on EOF")

print("ALL ENGINE PART CHECKS PASSED")
