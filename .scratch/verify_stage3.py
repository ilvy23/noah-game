"""Stage 3 verification: achievement notification + 'achievements' command in main.py.

Checks (static, no game run needed):
1. main.py prints a line matching 'Achievement unlocked: <name>' when check_all
   returns a newly-unlocked achievement.
2. main.py has an 'achievements' command that calls achievements.list_all (or
   equivalent listing unlocked + locked).
3. The notification logic does not depend on input (no ask() before the print),
   so EOF/'quit' cannot break it.
"""
import re
import sys

src = open('main.py', encoding='utf-8').read()

problems = []

# 1. Notification string present.
if 'Achievement unlocked' not in src:
    problems.append("main.py does not contain 'Achievement unlocked'")

# 2. check_all is called somewhere in main.py.
if 'check_all' not in src:
    problems.append("main.py never calls achievements.check_all")

# 3. An 'achievements' command exists and lists unlocked+locked.
has_cmd = re.search(r"['\"]achievements['\"]", src)
if not has_cmd:
    problems.append("main.py has no 'achievements' command")
if 'list_all' not in src and 'Achievement unlocked' in src:
    # list_all may be called via the module alias; check for a listing call
    if not re.search(r"achievements\.list_all|list_all\(", src):
        problems.append("no call to achievements.list_all found")

# 4. The unlock print happens before any ask()/pause() in the same block:
#    crude check - find the block that prints the unlock and ensure 'ask(' does
#    not appear between the check_all call and that print.
m_check = src.find('check_all')
m_print = src.find('Achievement unlocked')
if m_check != -1 and m_print != -1:
    between = src[m_check:m_print]
    if 'ask(' in between or 'input(' in between:
        problems.append("an input prompt occurs between check_all and the unlock print")

if problems:
    print('FAIL')
    for p in problems:
        print(' -', p)
    sys.exit(1)

print('OK: notification string present, check_all called, achievements command present, no prompt before the unlock print')
