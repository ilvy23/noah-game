import re
with open("main.py") as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if "def talk_npc" in line:
        for j in range(i-1, min(i+50, len(lines))):
            print(f"{j+1}: {lines[j].rstrip()}")
        break
