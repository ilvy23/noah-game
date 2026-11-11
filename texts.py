"""texts.py - the game's player-facing text lives in text/*.md, not in Python.

Each text is a heading `## <id>` followed by its body. The ids are the path of
the string inside its module (`noah.NOAH_TREE.start.text`) and never change.
Line breaks inside a body do not matter for texts the owner has edited: they
are re-wrapped. A text that is unchanged from the built-in default is used
byte for byte, so the game looks the same until the owner rewrites it.

The Python modules keep their old strings as defaults. Each text module calls
`texts.apply(__name__)` as its last line; that replaces the defaults in place
(dicts and lists) by the text of the md files. A body of `[TEXT: <id>]` is a
placeholder: the game shows it, `python texts.py todo` lists them.

    python texts.py export   write text/*.md from the built-in defaults
    python texts.py check    ids in the files that no module knows / parse errors
    python texts.py todo     list placeholders
"""
import importlib
import os
import re
import sys
import textwrap

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEXT_DIR = os.path.join(PROJECT_DIR, "text")
WRAP = 64
MODULES = ["story", "locations", "noah", "dialogue", "deaths", "achievements", "characters"]

_ID_LIKE = re.compile(r"^[a-z0-9_.:\-/]+$")
_PLACEHOLDER = re.compile(r"^\[TEXT: ([^\]]+)\]$")


def file_for(module: str, name: str) -> str:
    """Which md file a top-level name belongs to."""
    if module == "story":
        return "endings.md" if name in ("ENDINGS", "CHOICES", "AFTER_LINE", "FINAL") else "prolog.md"
    if module == "locations":
        return "gegenstaende.md" if name == "ITEMS" else "orte.md"
    if module == "dialogue":
        for who in ("CONNOR", "MIKA", "ARCHIVIST"):
            if name.startswith(who):
                return who.lower() + ".md"
        return "dialogue.md"
    return {"noah": "noah.md", "deaths": "tode.md", "achievements": "erfolge.md",
            "characters": "figuren.md"}[module]


def is_text(s: str) -> bool:
    s = s.strip()
    return bool(s) and not _ID_LIKE.match(s) and (" " in s or "\n" in s)


def key(k) -> str:
    """A dict key or list index as part of an id (no spaces or odd characters)."""
    return re.sub(r"[^A-Za-z0-9_.\-]+", "_", str(k)).strip("_")


def _norm(s: str) -> str:
    return " ".join(s.split())


def walk(obj, path, out):
    """Collect (path, string) for every text-like string; keys are structure."""
    if isinstance(obj, str):
        if is_text(obj):
            out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, path + [key(k)], out)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            walk(v, path + [str(i)], out)


def _top_names(mod):
    return [n for n, v in vars(mod).items()
            if n.isupper() and not n.startswith("_") and isinstance(v, (dict, list, tuple, str))]


def collect(module_name: str):
    mod = sys.modules.get(module_name) or importlib.import_module(module_name)
    out = []
    for n in _top_names(mod):
        items = []
        walk(getattr(mod, n), [n], items)
        for path, s in items:
            out.append((module_name + "." + ".".join(path), n, s))
    return out


# ---------------------------------------------------------------- md files
def parse(path):
    """-> {id: body}; raises ValueError('file:line: ...') on a broken file."""
    texts, cur, buf = {}, None, []

    def flush():
        if cur is not None:
            body = "\n".join(buf).strip("\n")
            texts[cur] = body
    with open(path, encoding="utf-8") as fh:
        for no, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if line.startswith("## "):
                flush()
                cur, buf = line[3:].strip(), []
                if not cur or " " in cur:
                    raise ValueError("%s:%d: bad id %r" % (path, no, cur))
                if cur in texts:
                    raise ValueError("%s:%d: duplicate id %s" % (path, no, cur))
            elif cur is not None:
                buf.append(line)
    flush()
    return texts


def load_all():
    out = {}
    if not os.path.isdir(TEXT_DIR):
        return out
    for fn in sorted(os.listdir(TEXT_DIR)):
        if fn.endswith(".md") and not fn.startswith("legacy"):
            for k, v in parse(os.path.join(TEXT_DIR, fn)).items():
                out[k] = v
    return out


def _wrap(body: str) -> str:
    """Re-wrap an owner-written body, paragraph by paragraph, keeping the indent."""
    paras = re.split(r"\n\s*\n", body)
    out = []
    for p in paras:
        indent = re.match(r"\s*", p.split("\n")[0]).group(0)
        flat = " ".join(p.split())
        out.append("\n".join(textwrap.wrap(flat, WRAP, initial_indent=indent,
                                           subsequent_indent=indent) or [""]))
    return "\n\n".join(out)


def resolve(default: str, body):
    """The text to use: default if unchanged, re-wrapped body if edited."""
    if body is None or _norm(body) == _norm(default):
        return default
    return _wrap(body)


def apply(module_name: str) -> int:
    """Replace default strings of a module by md text. Returns how many changed."""
    if os.environ.get("GAME_TEXTS_OFF"):
        return 0
    mod = sys.modules[module_name]
    texts = load_all()
    if not texts:
        return 0
    changed = [0]

    def sub(obj, path):
        if isinstance(obj, str):
            tid = module_name + "." + ".".join(path)
            body = texts.get(tid)
            if body is None or not is_text(obj):
                return obj
            new = resolve(obj, body)
            if new != obj:
                changed[0] += 1
            return new
        if isinstance(obj, dict):
            for k in list(obj):
                obj[k] = sub(obj[k], path + [key(k)])
            return obj
        if isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = sub(obj[i], path + [str(i)])
            return obj
        if isinstance(obj, tuple):
            return tuple(sub(v, path + [str(i)]) for i, v in enumerate(obj))
        return obj
    for n in _top_names(mod):
        setattr(mod, n, sub(getattr(mod, n), [n]))
    return changed[0]


# ---------------------------------------------------------------- commands
def export(force=False):
    os.makedirs(TEXT_DIR, exist_ok=True)
    os.environ["GAME_TEXTS_OFF"] = "1"
    files = {}
    for m in MODULES:
        for tid, name, s in collect(m):
            files.setdefault(file_for(m, name), []).append((tid, s))
    for fn, items in files.items():
        path = os.path.join(TEXT_DIR, fn)
        if os.path.exists(path) and not force:
            print("exists, skipped:", fn)
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("<!-- Edit only the text under each ## line. Never change a ## line. -->\n\n")
            for tid, s in items:
                fh.write("## %s\n%s\n\n" % (tid, s))
        print("wrote %s (%d texts)" % (fn, len(items)))


def known_ids():
    os.environ["GAME_TEXTS_OFF"] = "1"
    ids = set()
    for m in MODULES:
        for tid, _n, _s in collect(m):
            ids.add(tid)
    return ids


def check():
    bad = 0
    ids = known_ids()
    try:
        have = load_all()
    except ValueError as e:
        print("ERROR", e)
        return 1
    for tid in sorted(set(have) - ids):
        print("unknown id:", tid)
        bad += 1
    for tid in sorted(ids - set(have)):
        print("missing id (default stays):", tid)
    return 1 if bad else 0


def todo():
    n = 0
    for tid, body in load_all().items():
        if _PLACEHOLDER.match(body.strip()):
            print(tid)
            n += 1
    print("%d placeholders" % n)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "export":
        export(force="--force" in sys.argv)
    elif cmd == "check":
        sys.exit(check())
    elif cmd == "todo":
        sys.exit(todo())
    else:
        print(__doc__)
