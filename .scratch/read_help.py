with open('main.py') as f:
    lines = f.readlines()
for i in range(660, 700):
    print(f"{i+1}: {lines[i].rstrip()}")
