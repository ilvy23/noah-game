import re

src = open('noah.py').read()
lines = src.splitlines()
for i, line in enumerate(lines, 1):
    if re.search(r'sanity|mind|head|clear|fog|blur|shak|waver|steady|calm|panic|fear', line, re.I):
        print(f'{i:4d}: {line}')
