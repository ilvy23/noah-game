import re
with open("tests/test_scripted_playthroughs.py") as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if "def test_talk_noah_all_tiers" in line or "def test_talk_noah_restores_sanity_once_per_day" in line:
        # print 5 lines before and 50 lines after
        start = max(0, i - 3)
        end = min(len(lines), i + 50)
        print(f"--- line {i} ---")
        for j in range(start, end):
            print(f"{j+1}: {lines[j].rstrip()}")
        print()
