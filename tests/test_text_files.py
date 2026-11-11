"""text/*.md must mirror the built-in texts exactly until the owner edits them."""
import json
import os
import re
import subprocess
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import texts  # noqa: E402

DUMP = (
    "import json,sys;sys.path.insert(0,%r);"
    "import story,locations,noah,dialogue,deaths,achievements,characters as c;"
    "mods=[story,locations,noah,dialogue,deaths,achievements,c];"
    "print(json.dumps({m.__name__:{n:repr(getattr(m,n)) for n in dir(m) if n.isupper()} for m in mods},sort_keys=True))"
) % ROOT


def _dump(off):
    env = dict(os.environ)
    if off:
        env["GAME_TEXTS_OFF"] = "1"
    else:
        env.pop("GAME_TEXTS_OFF", None)
    raw = subprocess.check_output([sys.executable, "-c", DUMP], env=env, cwd=ROOT).decode()
    return json.loads(re.sub(r" at 0x[0-9a-f]+", "", raw))


def test_snapshot_rendered_texts_identical_with_and_without_md():
    assert _dump(True) == _dump(False)


def test_every_id_used_by_the_code_exists_and_none_is_unused():
    have = texts.load_all()
    ids = texts.known_ids()
    assert not (ids - set(have)), sorted(ids - set(have))[:5]
    assert not (set(have) - ids), sorted(set(have) - ids)[:5]


def test_edited_text_is_rewrapped_and_unchanged_text_is_kept_byte_for_byte():
    default = "  line one\n  line two"
    assert texts.resolve(default, "line  one line two") == default
    edited = texts.resolve(default, "  " + "word " * 40)
    assert edited != default and all(len(l) <= texts.WRAP for l in edited.split("\n"))
    assert all(l.startswith("  ") for l in edited.split("\n"))


def test_edit_in_md_reaches_the_module(tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("## fake.GREETING.0\nCompletely new words here.\n\n## fake.PLACE\n[TEXT: fake.PLACE]\n")
    monkeypatch.setattr(texts, "TEXT_DIR", str(tmp_path))
    monkeypatch.delenv("GAME_TEXTS_OFF", raising=False)
    mod = types.ModuleType("fake")
    mod.GREETING = ["Old words here today.", ("Tuple label here ok", "next_id")]
    mod.PLACE = "An old place text here."
    sys.modules["fake"] = mod
    try:
        assert texts.apply("fake") == 2
        assert mod.GREETING[0] == "Completely new words here."
        assert mod.GREETING[1] == ("Tuple label here ok", "next_id")
        assert mod.PLACE == "[TEXT: fake.PLACE]"
    finally:
        del sys.modules["fake"]


def test_placeholders_are_listed(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.md").write_text("## x.A\n[TEXT: x.A]\n\n## x.B\nreal text here\n")
    monkeypatch.setattr(texts, "TEXT_DIR", str(tmp_path))
    texts.todo()
    out = capsys.readouterr().out
    assert "x.A" in out and "x.B" not in out and "1 placeholders" in out


def test_malformed_file_reports_file_and_line(tmp_path):
    p = tmp_path / "bad.md"
    p.write_text("## ok.A\ntext\n## bad id with spaces\nmore\n")
    with pytest.raises(ValueError) as e:
        texts.parse(str(p))
    assert "bad.md:3" in str(e.value)
    p.write_text("## dup.A\nx\n## dup.A\ny\n")
    with pytest.raises(ValueError):
        texts.parse(str(p))
