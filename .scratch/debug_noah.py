import sys, os, json, tempfile, shutil, subprocess
sys.path.insert(0, ".")

tmp = tempfile.mkdtemp(dir=".scratch")
for f in os.listdir("."):
    if f.endswith(".py") or f == "save.json":
        shutil.copy2(f, tmp)

save = {
    "location": "nook", "sanity": 80, "trust": 0, "fear": 0,
    "flags": {}, "inventory": [], "visited": ["lunuen", "nook"],
    "seen": ["lunuen", "nook"], "journal": [], "deaths": 0,
    "day": 1, "night": False, "chapter": 1,
    "connor_line": 0, "mika_line": 0, "noah_rest_day": 0,
}
with open(os.path.join(tmp, "save.json"), "w") as f:
    json.dump(save, f)

proc = subprocess.run(
    ["python3", "main.py"],
    input="\ntalk noah\nleave\nq\n",
    capture_output=True, text=True, timeout=30, cwd=tmp,
)
print("RC:", proc.returncode)
print("STDOUT:")
print(proc.stdout[:3000])
print("STDERR:")
print(proc.stderr[:1000])
