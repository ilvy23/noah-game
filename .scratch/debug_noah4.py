import sys, os, json, tempfile, shutil, subprocess

tmp = tempfile.mkdtemp(dir=".scratch")
GAME_FILES = ["engine.py", "context.py", "locations.py", "characters.py", "story.py", "dialogue.py", "deaths.py", "main.py", "noah.py", "music.py"]
for f in GAME_FILES:
    shutil.copy2(f, tmp)

patch_dir = os.path.join(tmp, "_patch")
os.makedirs(patch_dir, exist_ok=True)
with open(os.path.join(patch_dir, "sitecustomize.py"), "w") as f:
    f.write("import time\ntime.sleep = lambda *a, **kw: None\n")

save = {
    "version": 2, "location": "nook", "sanity": 80, "trust": 0, "fear": 0,
    "flags": {}, "inventory": [], "visited": ["lunuen", "nook"],
    "seen": ["lunuen", "nook"], "journal": [], "deaths": 0,
    "day": 1, "night": False, "connor_line": 0, "mika_line": 0,
}
with open(os.path.join(tmp, "save.json"), "w") as f:
    json.dump(save, f, indent=2)

env = dict(os.environ)
env["PYTHONPATH"] = patch_dir

proc = subprocess.run(
    [sys.executable, "main.py", "--continue"],
    input="\nlook\ntalk noah\nleave\nq\n",
    capture_output=True, text=True, timeout=30, cwd=tmp, env=env,
)
print("RC:", proc.returncode)
print("STDOUT:")
print(proc.stdout[:6000])
print("STDERR:")
print(proc.stderr[:1000])
