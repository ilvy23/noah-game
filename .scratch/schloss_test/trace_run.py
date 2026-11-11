"""Run main.main() in-process with a traced input() to see who reads what."""
import builtins, sys

sys.path.insert(0, ".")
lines = iter(["", "", "1"])
log = []

def traced_input(prompt=""):
    try:
        val = next(lines)
    except StopIteration:
        raise EOFError
    log.append(val)
    import traceback
    # capture the caller
    stack = traceback.extract_stack()
    caller = [f for f in stack if "main.py" in f.filename or "deaths.py" in f.filename][-1]
    sys.stderr.write(f"INPUT {val!r}  <- {caller.name}:{caller.lineno}\n")
    return val

builtins.input = traced_input

import main
try:
    main.main()
except SystemExit as e:
    sys.stderr.write(f"SystemExit: {e}\n")
sys.stderr.write(f"TOTAL INPUTS CONSUMED: {log}\n")
