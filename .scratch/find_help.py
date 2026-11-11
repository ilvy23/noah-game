import re
with open("main.py") as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if "_how_to_play" in line or "_title_screen" in line or "_menu" in line:
        print(f"{i}: {line.rstrip()}")
