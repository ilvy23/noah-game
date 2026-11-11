import sys, os, subprocess, json, shutil, tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_FILES = ["main.py", "engine.py", "achievements.py", "context.py", "dialogue.py",
              "locations.py", "noah.py", "story.py", "deaths.py", "characters.py",
              "music.py", "save.json"]

tmp = tempfile.mkdtemp()
for f in GAME_FILES:
    src = os.path.join(PROJECT, f)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(tmp, f))

# patch time.sleep
patch_dir = os.path.join(tmp, "_patch")
os.makedirs(patch_dir, exist_ok=True)
with open(os.path.join(patch_dir, "sitecustomize.py"), "w") as fh:
    fh.write("import time\ntime.sleep = lambda *a, **kw: None\n")

# write a save with sanity=80, location=nook
save = {
    "version": 2, "location": "nook", "sanity": 80,
    "trust": 0, "fear": 0, "flags": {}, "inventory": [],
    "visited": ["lunuen", "nook"], "seen": ["lunuen", "nook"],
    "journal": [], "deaths": 0, "day": 1, "night": False,
    "connor_line": 0, "mika_line": 0,
}
with open(os.path.join(tmp, "save.json"), "w") as fh:
    json.dump(save, fh, indent=2)

env = dict(os.environ)
env["PYTHONPATH"] = patch_dir

result = subprocess.run(
    [sys.executable, "main.py", "--continue"],
    cwd=tmp, input="\ntalk noah\nleave\nq\n", capture_output=True, text=True, timeout=60, env=env,
)
print("RC:", result.returncode)
print("STDOUT:")
print(result.stdout[:3000])
print("STDERR:")
print(result.stderr[:2000])
