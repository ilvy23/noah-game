"""Direct test: feed scripted inputs and watch what each prompt reads."""
import sys, json, builtins

# Build the save state
sys.path.insert(0, ".")
import engine, story, deaths

s = engine.State()
s.location = "schloss"
s.sanity = 80
s.flags["read_ledger"] = True
s.inventory = ["key", "ritual_text"]
s.seen = ["lunuen", "schloss"]

print("=== setup ===")
print("ritual_unlocked:", story.ritual_unlocked(s))
print("choices:", [(k, e) for k, d, e in story.available_choices(s)])
print("death:", deaths.check_death(s))

# Now simulate the input stream the game would see
# The test sends: "", "", "1"
# pause() #1 reads "", pause() #2 reads "", ask(">") should read "1"
# But what if pause() reads more than one line?

# Let's trace: mock input to log every call
inputs = iter(["", "", "1"])
calls = []

def fake_input(prompt=""):
    val = next(inputs, None)
    calls.append(val)
    if val is None:
        raise EOFError
    return val

builtins.input = fake_input

import main

# Trace pause
orig_pause = main.pause
def traced_pause():
    r = orig_pause()
    print(f"  pause() -> {r!r}")
    return r
main.pause = traced_pause

# Trace ask
orig_ask = main.ask
def traced_ask(p="> "):
    r = orig_ask(p)
    print(f"  ask({p!r}) -> {r!r}")
    return r
main.ask = traced_ask

orig_ask2 = main._ask
def traced_ask2(p="> "):
    r = orig_ask2(p)
    print(f"  _ask({p!r}) -> {r!r}")
    return r
main._ask = traced_ask2

print("\n=== simulating: pause #1 (after prologue) ===")
r1 = main.pause()
print(f"pause #1 returned: {r1!r}")
print(f"quit check: {r1 in ('q','quit','exit','save','leaving')}")

print("\n=== simulating: pause #2 (after how_to_play) ===")
r2 = main.pause()
print(f"pause #2 returned: {r2!r}")
print(f"quit check: {r2 in ('q','quit','exit','save','leaving')}")

print("\n=== simulating: offer_final choice ===")
# Suppress render noise
main.render = lambda *a, **kw: None
result = main.offer_final(s)
print(f"offer_final returned: {result}")
print(f"made_choice: {s.has('made_choice')}")
print(f"ending: {s.flags.get('ending')}")
print(f"\ninput calls: {calls}")
