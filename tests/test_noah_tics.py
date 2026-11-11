# tests/test_noah_tics.py — Noah's tsundere tics must stay rare.
#
# Requirement: "hmph"/"tch"-style tsundere tics may appear in at most
# ~20% of Noah's lines (roughly one line in five), never as a tic in
# every line.

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import noah  # noqa: E402


def _all_lines(obj):
    """Collect every non-empty line of text from Noah's text data."""
    lines = []
    if isinstance(obj, str):
        for ln in obj.split("\n"):
            ln = ln.strip()
            if ln:
                lines.append(ln)
    elif isinstance(obj, dict):
        for v in obj.values():
            lines.extend(_all_lines(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            lines.extend(_all_lines(v))
    return lines


# The tsundere tic words. "I mean" is Noah's classic tsundere
# self-correction; it counts as a tic when it starts a sentence.
TIC_RE = re.compile(
    r"\b(hmph|hmpf|tsk|pfft|tch)\b"
    r"|\bi mean,",
    re.IGNORECASE,
)


def _noah_lines():
    return (
        _all_lines(noah.NOAH_OPEN)
        + _all_lines(noah.NOAH_TREE)
        + _all_lines(noah.NOAH_TOPICS)
        + _all_lines(noah.NOAH_CHAPTER)
    )


def test_tic_words_at_most_twentieth_of_lines():
    lines = _noah_lines()
    assert lines, "Noah's text data must not be empty"
    tic_lines = [ln for ln in lines if TIC_RE.search(ln)]
    assert len(tic_lines) <= len(lines) / 5, (
        f"{len(tic_lines)} of {len(lines)} lines carry a tsundere tic "
        f"(> 20%); allowed lines: {tic_lines}"
    )


def test_no_tic_in_every_line():
    # The tic must never be a tic in every line: no two consecutive
    # spoken lines may both carry one.
    lines = _noah_lines()
    for a, b in zip(lines, lines[1:]):
        assert not (TIC_RE.search(a) and TIC_RE.search(b)), (
            f"consecutive tic lines: {a!r} then {b!r}"
        )
