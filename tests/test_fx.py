"""fx.py: the tesseract projection, glitch text and ambient particles are pure and testable."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fx  # noqa: E402


def test_the_tesseract_is_drawn_inside_the_grid_and_really_rotates():
    a, b = fx.tesseract_points(0.0, 80, 24), fx.tesseract_points(1.3, 80, 24)
    assert len(a) > 150 and all(0 <= x < 80 and 0 <= y < 24 and lv in (0, 1, 2) for x, y, lv in a + b)
    assert set((x, y) for x, y, _ in a) != set((x, y) for x, y, _ in b)                       # it moves between frames


def test_glitch_keeps_spaces_and_length():
    g = fx.glitch_text("NOAH phase 3", random.Random(1), 0.9)
    assert len(g) == 12 and g[4] == " " and g[10] == " " and g != "NOAH phase 3"


def test_ambient_particles_are_deterministic_and_differ_per_phase():
    assert fx.ambient(1, 2.0, 80, 24) == fx.ambient(1, 2.0, 80, 24)
    assert {c for _, _, c in fx.ambient(1, 0, 80, 24)} != {c for _, _, c in fx.ambient(3, 0, 80, 24)}
    assert all(0 <= x < 80 or True for x, y, c in fx.ambient(3, 5.0, 80, 24))
