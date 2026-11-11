"""Debug: run the game with 'talk noah' at steady tier and dump the output."""
import json, os, shutil, subprocess, sys, tempfile

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_FILES = ["engine.py","context.py","locations.py","characters.py","story.py",
              "dialogue.py","deaths.py","main.py","noah.py","music.py"]

tmp = tempfile.mkdtemp(dir=".scratch")
for name in GAME_FILES:
    shutil.copy2(os.path.join(PROJECT_DIR, name), os.path.join(tmp, name))

save = {
    "version": 2, "location": "nook", "sanity": 80, "trust": 0, "fear": 0,
    "flags": {}, "inventory": [], "visited": ["lunuen"], "seen": ["lunuen", "nook"],
    "journal": [], "deaths": 0, "day": 1, "night": False,
    "connor_line": 0, "mika_line": 0,
}
with open(os.path.join(tmp, "save.json"), "w") as f:
    json.dump(save, f, indent=2)

patch_dir = os.path.join(tmp, "_patch")
os.makedirs(patch_dir, exist_ok=True)
with open(os.path.join(patch_dir, "sitecustomize.py"), "w") as f:
    f.write("import time\ntime.sleep = lambda *a, **kw: None\n")

env = dict(os.environ)
env["PYTHONPATH"] = patch_dir

stdin_text = "\n\n\ntalk noah\nleave\nq\n"
result = subprocess.run(
    [sys.executable, "main.py", "--continue"],
    cwd=tmp, input=stdin_text, capture_output=True, text=True, timeout=120, env=env,
)
print("=== STDOUT ===")
print(result.stdout)
print("=== STDERR ===")
print(result.stderr)
print("=== RC ===", result.returncode)
