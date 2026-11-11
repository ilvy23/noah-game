with open('noah.py') as f:
    lines = f.readlines()
for i in range(103, 130):
    print(f"{i+1}: {lines[i].rstrip()}")
