"""Precise check for Stage 2 (engine.py part): no user-facing sanity messages,
mechanics + save logic intact."""
import ast, sys

src = open('engine.py').read()
tree = ast.parse(src)
errors = []

# 1. No sanity status/message/comment functions (sanity_status_line etc.)
func_names = [n.name for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
bad_funcs = [f for f in func_names
             if 'sanity' in f.lower() and any(k in f.lower()
             for k in ('status', 'message', 'warn', 'flavour', 'flavor', 'comment'))]
if bad_funcs:
    errors.append(f"sanity message functions still exist: {bad_funcs}")

# 2. No render/render_quiet/print call whose arguments mention sanity
for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        fn = node.func
        name = getattr(fn, 'id', '') or getattr(fn, 'attr', '')
        if name in ('render', 'render_quiet', 'print'):
            for arg in ast.walk(node):
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and 'sanity' in arg.value.lower():
                    errors.append(f"line {node.lineno}: user-facing call {name}() mentions sanity: {arg.value!r}")

# 3. Mechanics intact: sanity_change, sanity_tier, State.sanity
if 'sanity_change' not in func_names:
    errors.append("State.sanity_change missing (mechanics broken)")
if 'sanity_tier' not in func_names:
    errors.append("State.sanity_tier missing (mechanics broken)")
state_has_sanity = False
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef) and node.name == 'State':
        for sub in ast.walk(node):
            if isinstance(sub, ast.Attribute) and sub.attr == 'sanity':
                state_has_sanity = True
if not state_has_sanity:
    errors.append("State.sanity attribute missing (mechanics broken)")

# 4. Save/load still carries the sanity key
if '"sanity"' not in src and "'sanity'" not in src:
    errors.append("save dict no longer carries the 'sanity' key")

# 5. Behavioural: load a v1-style save with sanity, and one without
import importlib.util, tempfile, os, sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location('engine', 'engine.py')
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)

s = eng.State.from_dict({"location": "lunuen", "sanity": 77, "trust": 3})
assert s.sanity == 77 and s.trust == 3, "v1 save with sanity did not load"

s2 = eng.State.from_dict({"location": "lunuen"})
assert s2.sanity == 80, "save without sanity key did not default"

d = eng.State().to_dict()
assert d["sanity"] == 80, "to_dict lost sanity"

if errors:
    print("FAIL:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("PASS: no user-facing sanity messages; mechanics + save logic intact")
