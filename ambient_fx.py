"""ambient_fx.py - small animated scenes for the story's plain-text scenes, drawn with the cine_fx engine (half-block pictures, glow, particles) and the text on
top as speech bubbles / a caption strip (speech.py, via ctx.dialog).

    run_text(ctx, kind, text)        kind: "stairs" | "cellar" ; quoted 'speech' becomes a bubble of Noah, everything else narration on the caption strip
    SCENE_KIND                       story scene id -> kind (the ones that are covered)
Covered: k7.anreise (the stairs down), k7.warn10, k7.warn20 (the cellar, Noah on his knees). Everything else in story.json is still shown by the normal text UI.
"""
import math
import re

import noah_gore_fx as G
import photo_fx
from noah_gore_fx import Canvas, Particles, add, glow, mix, mul, smooth, _hash

SCENE_KIND = {"k7.anreise": "stairs", "k7.warn10": "cellar", "k7.warn20": "cellar"}


class Stairs:
    """The spiral stairs going down: stone steps in rings that turn and sink away into the dark, a torch light that flickers, the cold blue of the cube in the coat
    at the bottom edge, and Noah's small figure behind you that hurries, falls back, stops a moment too far back."""

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.parts = Particles(rng, 200)

    def draw(self, cv, t, dt):
        w, h = self.w, self.h
        cx, cy = w // 2, int(h * 0.42)
        cv.clear((4, 4, 8))
        flick = 0.85 + 0.15 * math.sin(t * 13) * math.sin(t * 7.3)
        for y in range(2 * h):
            for x in range(0, w, 2):                                                       # computed at half width (two columns share a value): keeps the frame under 40 ms
                dx, dy = (x + 0.5 - cx) / 2.2, (y / 2.0 - cy) * 1.0
                r = math.hypot(dx, dy) + 0.01
                a = math.atan2(dy, dx) + t * 0.35 + r * 0.06                           # the stairs turn as they go down
                step = 0.5 + 0.5 * math.sin(a * 7.0)
                ring = 0.5 + 0.5 * math.sin(r * 0.9 - t * 1.4)                         # and sink: rings move towards the middle
                depth = max(0.0, 1.0 - 1.0 / (0.04 * r + 0.8))
                lum = (0.25 + 0.55 * step * ring) * (0.12 + 0.88 * depth) * flick
                n = _hash(x, y, 3)
                c = mul((150, 140, 132), lum * (0.9 + 0.2 * n))
                if step > 0.93:
                    c = add(c, (255, 170, 80), 0.25 * flick * depth)                  # the lit edge of a step
                photo_fx.put_pixel(cv, x, y, c)
                photo_fx.put_pixel(cv, x + 1, y, c)
        glow(cv, cx, cy + 2, 18, 7, (255, 150, 60), 0.35 * flick)                       # your torch light, from above and to the side
        gx = int(w * 0.5 + w * 0.26 * math.sin(t * 0.5))                                # Noah behind you: closes up, stops too far back
        lag = 0.5 + 0.5 * math.sin(t * 1.1)
        gy = int(h * (0.74 + 0.04 * lag))
        for yy in range(-9, 0):                                                          # a small, slight silhouette, one hand trailing on the wall
            half = 2 if yy < -6 else 3
            for dx in range(-half, half + 1):
                photo_fx.put_pixel(cv, gx + dx, 2 * gy + yy, mix((20, 18, 26), (110, 76, 56), 0.35 if dx > 1 else 0.0))
        for dy in range(-3, 2):
            for dx in range(-2, 3):
                if dx * dx + dy * dy < 6:
                    photo_fx.put_pixel(cv, gx + dx, 2 * gy - 12 + dy, (150, 108, 88) if dx > 0 else (60, 44, 42))
        cube = 0.5 + 0.5 * math.sin(t * 2.1)
        glow(cv, int(w * 0.9), h - 2, 20, 7, (110, 170, 255), 0.22 + 0.1 * cube)         # the cube in your coat, so cold it hurts
        if _hash(int(t * 6), 1, 2) > 0.55:
            self.parts.add(cx + self.rng.uniform(-30, 30), h * 0.1, 0, self.rng.uniform(1, 3), 3.0, "dust", 0.3)
        self.parts.step(dt)
        self.parts.draw(cv, 0.2)
        photo_fx.finish(cv, t, 0.05, 0.4)
        return 0, 0


class Cellar:
    """The cellar: wet stone, three candles, Noah on his knees in the middle with his head up, not blinking; later the thin smile. Nothing else moves but the flames."""

    def __init__(self, w, h, rng):
        self.w, self.h, self.rng = w, h, rng
        self.fire = G.Fire(0, w, h, rng, decay=0.1)
        self.parts = Particles(rng, 200)
        self.body = G.Body(max(9, int(h * 0.42)), rng)

    def draw(self, cv, t, dt):
        w, h = self.w, self.h
        self.fire.step()
        cv.clear((6, 5, 6))
        for y in range(h):                                                                # a brick wall in the dark, the floor below
            for x in range(w):
                brick = ((x // 9) + (y // 2) * 4 + (4 if (y // 2) % 2 else 0)) % 9
                c = mix((18, 14, 14), (40, 32, 30), _hash(x // 9, y // 2, brick) * 0.9)
                if y > h * 0.72:
                    c = mix((14, 12, 12), (30, 26, 24), _hash(x // 6, y, 5))
                if x % 9 == 0 or (y % 2 == 0 and y < h * 0.72):
                    c = mul(c, 0.6)
                cv.ch[y * w + x], cv.fg[y * w + x], cv.bg[y * w + x] = " ", c, c
        cx = w // 2
        for ox in (-int(w * 0.28), int(w * 0.22), int(w * 0.08)):                          # candles
            x = cx + ox
            for yy in range(int(h * 0.72) - 4, int(h * 0.72)):
                cv.put(x, yy, "|", (226, 214, 190), (150, 130, 110))
            self.fire.inject(x, int(h * 0.72) - 5, 0.7 + 0.2 * math.sin(t * 9 + ox))
            glow(cv, x, int(h * 0.72) - 6, 22, 9, (255, 150, 60), 0.14 * (0.8 + 0.2 * math.sin(t * 11 + ox)))
        grid = self.body.render(0.0)
        blit = G.blit_grid
        top = int(h * 0.72) - len(grid) // 2 - 1
        blit(cv, grid, cx - len(grid[0]) // 2, max(1, top), 1.0, 0.7)                      # Noah on his knees: the standing boy squashed (knees tucked), head up
        if t > 2.0:                                                                       # the thin smile
            sm = smooth((t - 2.0) / 3.0)
            for dx in range(-3, 4):
                cv.put(cx + dx, max(1, top) + 4 + (1 if abs(dx) < 2 else 0) - int(sm * (abs(dx) // 3)), "_" if abs(dx) < 2 else "-", mul((200, 120, 110), 0.5 + 0.5 * sm))
        self.fire.draw(cv, 0.14, solid=0.5)
        self.parts.step(dt)
        self.parts.draw(cv, 0.2)
        photo_fx.finish(cv, t, 0.05, 0.45)
        return 0, 0


KINDS = {"stairs": Stairs, "cellar": Cellar}


def boxes_for(text):
    """Quoted 'speech' (single quotes at a word edge) -> Noah's bubbles; the rest -> narration."""
    out, pos = [], 0
    for m in re.finditer(r"(?:(?<=\s)|^)'(.{3,}?)'(?=[\s.,!?;:)]|$)", text):
        if text[pos:m.start()].strip():
            out.append(("narrator", text[pos:m.start()].strip(), None))
        out.append(("noah", m.group(1).strip(), (0.5, 0.6)))
        pos = m.end()
    if text[pos:].strip():
        out.append(("narrator", text[pos:].strip(), None))
    return out or [("narrator", text, None)]


def run_text(ctx, kind, text, seed=1):
    """Play the text scene `kind` with `text` drawn on it as bubbles and captions. ctx = mika_ending.Ctx (or anything with dialog())."""
    ctx.dialog(KINDS[kind], boxes_for(text), 0.0, 6.0, seed=seed)
