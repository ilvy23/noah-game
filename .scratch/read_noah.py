import re
with open("noah.py") as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if "NOAH_OPEN" in line and ("steady" in line or "thin" in line or "low" in line or "critical" in line):
        print(f"{i}: {line.rstrip()}")
