with open('dialogue.py') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'NOAH_OPEN' in line or 'NOAH_TREE' in line:
        print(f"{i}: {line.rstrip()}")
