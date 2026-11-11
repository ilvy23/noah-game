"""fx.py - pure helpers for the screen effects of the fight (so they can be tested without a terminal)."""
import math
import random


def tesseract_points(t, w, h, grow=1.0):
    """A rotating tesseract (4D hypercube) projected to a w x h character cell grid at time t (seconds).
    Returns a list of (x, y, level) with level 0..2 (dim, mid, bright). Edges join corners that differ in one coordinate."""
    verts = [[(i >> k & 1) * 2 - 1 for k in range(4)] for i in range(16)]
    a, b, c = t * 0.9, t * 0.63, t * 0.41
    proj = []
    for x, y, z, u in verts:
        x, u = x * math.cos(a) - u * math.sin(a), x * math.sin(a) + u * math.cos(a)        # rotate in the x-w plane
        z, u = z * math.cos(b) - u * math.sin(b), z * math.sin(b) + u * math.cos(b)        # ... and the z-w plane
        y, z = y * math.cos(c) - z * math.sin(c), y * math.sin(c) + z * math.cos(c)        # ... and the y-z plane
        k = 1.0 / (2.6 - u * 0.55)                                                         # 4D -> 3D perspective
        x, y, z = x * k, y * k, z * k
        k2 = 1.0 / (3.2 - z * 0.6)                                                         # 3D -> 2D perspective
        proj.append((x * k2, y * k2, z))
    ext_x = max(abs(p[0]) for p in proj) or 1.0                  # fit the cube to the window, then let it grow in
    ext_y = max(abs(p[1]) for p in proj) or 1.0
    sx, sy = w * 0.44 * grow / ext_x, h * 0.44 * grow / ext_y
    proj = [(w / 2.0 + px * sx, h / 2.0 + py * sy, pz) for px, py, pz in proj]
    pts = []
    for i in range(16):
        for j in range(i + 1, 16):
            if bin(i ^ j).count("1") == 1:
                (x1, y1, z1), (x2, y2, z2) = proj[i], proj[j]
                n = int(max(abs(x2 - x1) / 2.0, abs(y2 - y1))) + 1
                for s in range(n + 1):
                    f = s / n
                    px, py = x1 + (x2 - x1) * f, y1 + (y2 - y1) * f
                    if 0 <= px < w and 0 <= py < h:
                        z = z1 + (z2 - z1) * f
                        pts.append((int(px), int(py), 2 if z > 0.35 else (1 if z > -0.3 else 0)))
    return pts


def glitch_text(text, rng, strength=0.25):
    """Corrupt some letters of `text` for a moment (the HUD 'forgets' itself)."""
    junk = "#%@&$?!/\\|<>~^"
    return "".join(rng.choice(junk) if (ch != " " and rng.random() < strength) else ch for ch in text)


AMBIENT = {  # what drifts around the arena per personality: sweet petals, cold rain, red veins, everything
    1: ("·", "•", "*", "."), 2: ("|", "'", ":", "/"), 3: ("~", "†", "¤", ";"), 4: ("~", "†", "*", "|", "."),
}


def ambient(phase, t, w, h, rng_seed=0, n=40):
    """Particles around the screen for the phase: list of (x, y, char). Positions depend on time, deterministic."""
    rng = random.Random(rng_seed)
    chars = AMBIENT.get(phase, AMBIENT[1])
    out = []
    for i in range(n):
        x0, y0, sp = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.4, 2.2)
        if phase == 1:                                     # petals: slow drift down and sideways
            x, y = (x0 + math.sin(t * 0.7 + i) * 3) % w, (y0 + t * sp) % h
        elif phase == 2:                                   # cold rain: fast diagonal
            x, y = (x0 - t * sp * 2.0) % w, (y0 + t * sp * 5.0) % h
        elif phase == 3:                                   # red veins creep in from the corners and pulse
            ang = i * 2.399
            r = (t * sp * 2.0 + i) % (min(w, h * 2) / 2)
            x, y = w / 2 + math.cos(ang) * (min(w, h * 2) / 2 - r) * 1.6, h / 2 + math.sin(ang) * (min(w, h * 2) / 2 - r) * 0.8
        else:
            x, y = (x0 + math.sin(t + i) * 5) % w, (y0 - t * sp * 2.0) % h
        out.append((int(x), int(y), chars[i % len(chars)]))
    return out
