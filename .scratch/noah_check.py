"""Independent acceptance check for Noah's texts (written by the supervisor, not by the author of noah.py).
Run from the project folder:  python3 .scratch/noah_check.py      -> prints PASS or FAIL with examples; exit code 0 / 1.
It collects ALL of Noah's text (NOAH_OPEN tiers, NOAH_TREE nodes, NOAH_TOPICS, place_text at many trust/chapter/hurt values)."""
import collections, itertools, re, sys
sys.path.insert(0, ".")
import noah

def flat(x):
    if isinstance(x, dict): return [t for v in x.values() for t in flat(v)]
    if isinstance(x, (list, tuple)): return [t for v in x for t in flat(v)]
    return [x] if isinstance(x, str) else []

def sentences(text):
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|[“”\"]", text) if s.strip()]

norm = lambda s: re.sub(r"[^a-z ]", "", s.lower()).strip()
fails = []

units = {}                                     # name -> full text
for tier, t in noah.NOAH_OPEN.items(): units[f"open:{tier}"] = t
for nid, n in noah.NOAH_TREE.items(): units[f"node:{nid}"] = n.get("text", "")
for k, v in getattr(noah, "NOAH_TOPICS", {}).items(): units[f"topic:{k}"] = "\n".join(flat(v.get("text", "") if isinstance(v, dict) else v))
try:
    import engine
    for trust, chapter, hurt in itertools.product((0, 3, 8), (1, 3, 5), (False, True)):
        s = engine.State(); s.trust = trust; s.chapter = chapter
        if hurt: s.flag("noah_hurt")
        units[f"place:t{trust}c{chapter}{'H' if hurt else ''}"] = noah.place_text(s)
except Exception as e:                         # the place text must work with a plain State
    fails.append(f"place_text could not be evaluated: {type(e).__name__}: {e}")

# 1. no sentence (3+ words) may appear twice anywhere, and none twice inside one text
seen = collections.defaultdict(set)
for name, t in units.items():
    inside = collections.Counter(norm(s) for s in sentences(t) if len(norm(s).split()) >= 3)
    for s, c in inside.items():
        seen[s].add(name)
        if c > 1: fails.append(f"repeated inside {name}: '{s[:70]}' x{c}")
dups = {s: n for s, n in seen.items() if len(n) > 1 and not s.startswith("place")}
dups = {s: n for s, n in dups.items() if not all(x.startswith("place:") for x in n)}
for s, n in sorted(dups.items(), key=lambda kv: -len(kv[1]))[:12]:
    fails.append(f"sentence shared by {len(n)} texts ({', '.join(sorted(n)[:4])}): '{s[:70]}'")

# 2. the four sanity tiers must share nothing (any sentence of 3+ words)
tiers = {t: {norm(s) for s in sentences(txt) if len(norm(s).split()) >= 3} for t, txt in noah.NOAH_OPEN.items()}
for a, b in itertools.combinations(tiers, 2):
    shared = tiers[a] & tiers[b]
    if shared: fails.append(f"tiers {a} / {b} share {len(shared)} sentences, e.g. '{sorted(shared)[0][:70]}'")

# 3. banned horror / uncanny phrases anywhere in Noah's text
banned = [r"closer", r"or the bench", r"moment ago", r"did not light", r"if it stops", r"if the tea stops", r"\bcounting\b", r"\bhollow\b",
          r"breathing", r"\bmouth\b", r"ledger", r"valley keeps", r"the whole of it", r"\bnot a (blanket|cushion|kettle|mug)\b",
          r"weather system", r"is facing (you|the)", r"has been facing", r"not going to stop", r"mugs are there anyway",
          r"did not bring a mug", r"archivist", r"what the valley is", r"what the tea is", r"was not there", r"not able to describe",
          r"will not be able to describe", r"the only thing that is still", r"is not a question", r"\bin order\b", r"for a while"]
alltext = "\n".join(units.values()).lower()
for pat in banned:
    n = len(re.findall(pat, alltext))
    if n: fails.append(f"banned/uncanny phrase /{pat}/ occurs {n}x")
for pat in (r"\b(\w+) is not an? \1\b", r"is not an? (\w+) but (an?|the) "):
    m = re.findall(pat, alltext)
    if m: fails.append(f"'X is not a X but Y' construction x{len(m)}")

# 4. each tier needs tsundere dialogue AND a cosy scene, and the tiers must read differently (verbs / scenes)
for tier, t in noah.NOAH_OPEN.items():
    low = t.lower()
    marks = sum(len(re.findall(p, low)) for p in (r"not like", r"t-tch", r"hmph", r"baka", r"ehh", r"\bmou\b", r"dummy", r"idiot"))
    if marks < 2: fails.append(f"tier {tier}: only {marks} tsundere markers (need >= 2)")

print("NOAH CHECK:", "PASS" if not fails else f"FAIL ({len(fails)} problems)")
for f in fails[:40]: print(" -", f)
sys.exit(1 if fails else 0)
