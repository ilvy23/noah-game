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
    # Run with a simple debug script that imports main and patches ask
    debug_script = os.path.join(tmp, "debug.py")
    with open(debug_script, "w") as f:
        f.write('''
import sys
import main

orig_ask = main.ask
def debug_ask(prompt_text="> "):
    result = orig_ask(prompt_text)
    sys.stderr.write(f"[DEBUG] ask returned: {repr(result)}\\n")
    return result
main.ask = debug_ask

main.main()
''')
    result = subprocess.run(
        [sys.executable, "debug.py", "--continue"],
        cwd=tmp, input="\ntalk noah\n0\nq\n",
        capture_output=True, text=True, timeout=120, env=env,
    )
    print("RC:", result.returncode)
    print("STDOUT:")
    print(result.stdout[:4000])
    print("STDERR:")
    print(result.stderr[:3000])
