import json, os, shutil, subprocess, sys, tempfile

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_FILES = ["engine.py","context.py","locations.py","characters.py","story.py","dialogue.py","deaths.py","achievements.py","main.py","noah.py","music.py"]

with tempfile.TemporaryDirectory() as tmp:
    for name in GAME_FILES:
        shutil.copy2(os.path.join(PROJECT_DIR, name), os.path.join(tmp, name))
    save = {
        "version": 2, "location": "nook", "sanity": 80,
        "trust": 0, "fear": 0, "flags": {}, "inventory": [],
        "visited": ["lunuen"], "seen": ["lunuen", "nook"],
        "journal": [], "deaths": 0, "day": 1, "night": False,
        "connor_line": 0, "mika_line": 0,
    }
    with open(os.path.join(tmp, "save.json"), "w") as f:
        json.dump(save, f)
    patch_dir = os.path.join(tmp, "_patch")
    os.makedirs(patch_dir, exist_ok=True)
    with open(os.path.join(patch_dir, "sitecustomize.py"), "w") as f:
        f.write("import time\ntime.sleep = lambda *a, **kw: None\n")
    env = dict(os.environ)
    env["PYTHONPATH"] = patch_dir
    # Run main.py directly with --continue, feeding stdin
    result = subprocess.run(
        [sys.executable, "main.py", "--continue"],
        cwd=tmp, input="\ntalk noah\n0\nq\n",
        capture_output=True, text=True, timeout=120, env=env,
    )
    print("RC:", result.returncode)
    print("STDOUT (last 3000 chars):")
    print(result.stdout[-3000:])
    print("STDERR (last 2000 chars):")
    print(result.stderr[-2000:])
