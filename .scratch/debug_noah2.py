import json, os, shutil, subprocess, sys, tempfile

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GAME_FILES = ["engine.py","context.py","locations.py","characters.py","story.py","dialogue.py","deaths.py","achievements.py","main.py","noah.py","music.py"]

def run(sanity):
    tmp = tempfile.mkdtemp()
    for name in GAME_FILES:
        shutil.copy2(os.path.join(PROJECT_DIR, name), os.path.join(tmp, name))
    patch_dir = os.path.join(tmp, "_patch")
    os.makedirs(patch_dir, exist_ok=True)
    with open(os.path.join(patch_dir, "sitecustomize.py"), "w") as f:
        f.write("import time\ntime.sleep = lambda *a, **kw: None\n")
    save = {
        "version": 2, "location": "nook", "sanity": sanity,
        "trust": 0, "fear": 0, "flags": {}, "inventory": [],
        "visited": ["lunuen"], "seen": ["lunuen", "nook"],
        "journal": [], "deaths": 0, "day": 1, "night": False,
        "connor_line": 0, "mika_line": 0,
    }
    with open(os.path.join(tmp, "save.json"), "w") as f:
        json.dump(save, f)
    env = dict(os.environ)
    env["PYTHONPATH"] = patch_dir
    result = subprocess.run(
        [sys.executable, "main.py", "--continue"],
        cwd=tmp, input="\n\ntalk noah\nleave\nq\n",
        capture_output=True, text=True, timeout=120, env=env,
    )
    # Find the nook header and print the next 10 lines
    lines = result.stdout.split("\n")
    for i, line in enumerate(lines):
        if "Noah's nook" in line or "the nook" in line:
            print(f"sanity={sanity}: found nook header at line {i}")
            for j in range(i, min(i+15, len(lines))):
                print(f"  {j}: {lines[j]}")
            break
    else:
        print(f"sanity={sanity}: NOOK HEADER NOT FOUND")
        print("  last 20 lines:")
        for line in lines[-20:]:
            print(f"  {line}")

for s in [80, 50, 30, 10]:
    run(s)
