import io, sys, os, json, shutil, subprocess, tempfile

tmp = tempfile.mkdtemp(dir=os.path.abspath("."))
game = os.path.join(tmp, "game")
shutil.copytree("..", game, ignore=shutil.ignore_patterns(".scratch", "__pycache__", "save.json"))

# Scripted input: start new game, visit 3 places, then check achievements
stdin_lines = [
    "1",          # new game
    "",           # pause after prologue
    "",           # pause after how-to-play
    "house",      # travel to house (visited: lunuen, house)
    "forest",     # travel to forest (visited: lunuen, house, forest)
    "achievements",
    "quit",
]

result = subprocess.run(
    ["python3", "main.py", "--no-music"],
    input="\n".join(stdin_lines) + "\n",
    capture_output=True, text=True, timeout=30,
    cwd=game,
)

out = result.stdout
print("=== STDOUT (last 80 lines) ===")
for ln in out.splitlines()[-80:]:
    print(ln)
print("=== STDERR ===")
print(result.stderr[-2000:] if result.stderr else "(empty)")
print("=== RC:", result.returncode)

has_unlock = "Achievement unlocked:" in out
print("\n=== 'Achievement unlocked:' found:", has_unlock)
has_check = "✓" in out
has_dot = "·" in out
print("=== ✓ (unlocked marker) found:", has_check)
print("=== · (locked marker) found:", has_dot)
