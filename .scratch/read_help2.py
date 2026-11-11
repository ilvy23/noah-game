with open('main.py') as f:
    lines = f.readlines()
for i in range(395, 425):
    print(f"{i+1}: {lines[i].rstrip()}")
