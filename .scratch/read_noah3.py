import re
with open("noah.py") as f:
    lines = f.readlines()
for i in range(28, 100):
    print(f"{i+1}: {lines[i].rstrip()}")
