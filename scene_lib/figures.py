"""scene_lib/figures.py - the puppet: a small jointed figure drawn as half-block pixels, played with the actions of actions.py.

Puppet(name) has a rig (lean, head, two arms with elbow, two legs with knee, whole-body rotation), a resting pose that persists between actions, a
breathing / blinking idle layer, a talking mouth, props in the hands (cigarette, knife, cube ...) and a body that is always locked to the ground,
so sitting, kneeling and falling need no extra bookkeeping. Characters differ only by STYLES (colours, coat, hood, scarf, height).
draw() paints into a noah_gore_fx.Canvas with photo_fx.put_pixel; everything is clipped, nothing is printed. Deterministic: only t decides.
"""
import math

import photo_fx
from noah_gore_fx import add, mix, mul

from .actions import ACTIONS, Act, IDLE_ACTS, REST, end_state, pose_at

MOODS = {"green": (96, 205, 118), "yellow": (236, 206, 72), "red": (222, 58, 54)}
STYLES = {
    "noah": dict(skin=(232, 190, 168), hair=(38, 30, 46), top=MOODS["green"], legs=(52, 56, 84), shoes=(30, 26, 34), scarf=(190, 72, 72), h=0.92, tw=0.058),
    "mika": dict(skin=(214, 176, 150), hair=(60, 50, 44), top=(146, 150, 152), coat=(58, 68, 62), hood=(152, 154, 152), legs=(48, 48, 62), shoes=(34, 30, 30), h=1.0, tw=0.06),
    "connor": dict(skin=(220, 190, 168), hair=(158, 156, 158), top=(40, 40, 48), coat=(34, 34, 44), legs=(32, 32, 40), shoes=(22, 20, 24), collar=(230, 230, 236), h=1.08, tw=0.058),
    "you": dict(skin=(214, 176, 150), hair=(72, 54, 42), top=(58, 70, 104), legs=(42, 44, 58), shoes=(30, 28, 30), back=True, h=1.0, tw=0.062),
    "stranger": dict(skin=(200, 170, 150), hair=(40, 40, 44), top=(70, 64, 60), coat=(54, 50, 50), legs=(40, 38, 40), shoes=(24, 22, 22), h=1.0, tw=0.06),
    "woman": dict(skin=(214, 182, 160), hair=(90, 84, 90), top=(104, 70, 74), coat=(80, 58, 62), hood=(116, 96, 100), legs=(50, 44, 48), shoes=(28, 26, 26), h=0.95, tw=0.058),
    "child": dict(skin=(226, 190, 168), hair=(120, 90, 60), top=(170, 120, 70), legs=(60, 60, 80), shoes=(30, 26, 30), h=0.7, tw=0.05),
}
LEN = dict(torso=0.30, neck=0.09, upper=0.15, fore=0.14, thigh=0.25, shin=0.25, head_r=0.072)


def _lerp(a, b, k):
    return a + (b - a) * k


class Buf:
    """Pixels of one figure: {(x, ypx): colour}, painted in the order they were set."""

    def __init__(self):
        self.p = {}

    def disc(self, cx, cy, r, col, shade=0.0):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for x in range(int(cx - r - 1), int(cx + r + 2)):
                if (x - cx) ** 2 + ((y - cy) * 1.0) ** 2 <= r * r:
                    self.p[(x, y)] = col if not shade else mul(col, 1.0 - shade * ((y - cy + r) / (2 * r + 1e-6)))

    def capsule(self, a, b, r, col, shade=0.18):
        (x0, y0), (x1, y1) = a, b
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy or 1e-6
        for y in range(int(min(y0, y1) - r - 1), int(max(y0, y1) + r + 2)):
            for x in range(int(min(x0, x1) - r - 1), int(max(x0, x1) + r + 2)):
                u = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / ll))
                d = math.hypot(x - (x0 + u * dx), y - (y0 + u * dy))
                if d <= r:
                    self.p[(x, y)] = mul(col, 1.0 - shade * (d / (r + 1e-6)) * (1 if x >= x0 + u * dx else 0.4))

    def px(self, x, y, col):
        self.p[(int(x), int(y))] = col

    def paint(self, cv, tint, lights, outline=(10, 10, 14)):
        occ = self.p
        rim = {(x + dx, y + dy) for (x, y) in occ for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))} - set(occ)
        for x, y in rim:
            photo_fx.put_pixel(cv, x, y, outline)
        for (x, y), c in occ.items():
            c = (c[0] * tint[0], c[1] * tint[1], c[2] * tint[2])
            for lx, ly, rad, rgb in lights:
                d = math.hypot(x - lx, y - ly)
                if d < rad:
                    k = (1 - d / rad) ** 2
                    c = (c[0] + rgb[0] * k * 0.5, c[1] + rgb[1] * k * 0.5, c[2] + rgb[2] * k * 0.5)
            photo_fx.put_pixel(cv, x, y, (min(255, int(c[0])), min(255, int(c[1])), min(255, int(c[2]))))


class Puppet:
    def __init__(self, name, style=None, x=0.5, facing=1, size=1.0, mood=None, seed=0, seat=False):
        self.name = name
        self.style = dict(STYLES.get(style or name, STYLES["stranger"]))
        if mood and name == "noah":
            self.style["top"] = MOODS.get(mood, MOODS["green"])
        self.x, self.facing, self.size, self.seed, self.seat = x, facing, size, seed, seat
        self.state = dict(REST)
        self.props = {"prop_a": None, "prop_b": None}
        self.pose = dict(REST)
        self.blend_from, self.blend_t0 = dict(REST), -9.0
        self.run = None                     # (act, name, t0, state0, x0, fired, flipped_from)
        self.queue = []                     # [(t_start, name)]
        self.talking = 0.0
        self.flash = 0.0                    # red flash of Noah's shirt on a shock line
        self.last = {}                      # where the head, mouth and hands were drawn last frame (for bubbles, smoke, tears)
        self.idle_next = {}
        self.history = []                   # names of the actions played (tests)
        self.visible = True

    # ---------------------------------------------------------------- acting
    def act(self, name, t, delay=0.0, to=None):
        """Queue an action. walk_in / walk_out / walk_to are built here (they need to know where the figure is and where it goes)."""
        built = None
        if name in ("walk_in", "walk_out", "walk_to"):
            built = Act(2.0, {}, end="hold", gait=True)
            built.to, built.kind = to, name
            self.queue.append((t + delay, name, built, None))
        else:
            if name not in ACTIONS:
                name = "gesture"
            self.queue.append((t + delay, name, None, None))
        self.queue.sort(key=lambda q: q[0])

    def _finish(self, t):
        """The running action ends now: its end pose, props and position become the resting ones."""
        if not self.run:
            return
        act, name, t0, s0, x0, fired, flip = self.run
        self.state = end_state(act, s0)
        for pn, (prop, on, off) in act.props.items():
            self.props[pn] = None if off is not None else prop
        if act.dx and name.startswith("walk"):
            self.x = x0 + act.dx
        elif act.dx:
            self.x = x0 + act.dx * self.facing
        self.run = None
        self.blend_from, self.blend_t0 = dict(self.pose), t

    def update(self, t):
        """Advance to scene time t; returns the events (names) fired since the last call."""
        events = []
        while self.queue and self.queue[0][0] <= t:
            ts, name, built, xs = self.queue.pop(0)
            self._finish(ts)
            act = built or ACTIONS[name]
            self.history.append(name)
            if built:
                if built.kind == "walk_in":
                    tgt = built.to if built.to is not None else self.x
                    self.x = -0.12 if tgt < 0.5 else 1.12
                else:
                    tgt = built.to if built.to is not None else (-0.15 if self.x < 0.5 else 1.15)
                built.dx, built.dur, self.visible, name = tgt - self.x, max(1.2, abs(tgt - self.x) * 9.0), True, "walk"
            if name.startswith("walk") and act.dx:
                self.facing = 1 if act.dx > 0 else -1
            self.run = (act, name, ts, dict(self.state), self.x, set(), self.facing)
            self.blend_from, self.blend_t0 = dict(self.pose), ts
        pose = dict(self.state)
        if self.run:
            act, name, t0, s0, x0, fired, flip = self.run
            f = max(0.0, min(1.0, (t - t0) / act.dur))
            pose = pose_at(act, s0, f)
            for pn, (prop, on, off) in act.props.items():
                if f >= on and ("on", pn) not in fired:
                    fired.add(("on", pn))
                    self.props[pn] = prop
                if off is not None and f >= off and ("off", pn) not in fired:
                    fired.add(("off", pn))
                    self.props[pn] = None
            for i, (ef, en) in enumerate(act.events):
                if f >= ef and i not in fired:
                    fired.add(i)
                    events.append(en)
            if act.dx:
                e = f * f * (3 - 2 * f)
                self.x = x0 + act.dx * e * (1 if name.startswith("walk") else self.facing)
            if act.gait:
                env = min(1.0, f * 6, (1 - f) * 6) if name.startswith("walk") else min(1.0, f * 6, (1 - f) * 6) * 0.6
                ph = (t - t0) * 7.0
                pose["tA"], pose["tB"] = pose["tA"] + 26 * env * math.sin(ph), pose["tB"] - 26 * env * math.sin(ph)
                pose["sA"] = pose["sA"] - 22 * env * max(0.0, math.sin(ph + 1.2))
                pose["sB"] = pose["sB"] - 22 * env * max(0.0, -math.sin(ph + 1.2))
                pose["aU"] = pose["aU"] - 12 * env * math.sin(ph) if "aU" not in act.tracks else pose["aU"]
                pose["bU"] = pose["bU"] + 12 * env * math.sin(ph) if "bU" not in act.tracks else pose["bU"]
            if f >= 1.0:
                self._finish(t)
        elif not self.queue:                                      # nothing to do: the figure lives on its own
            for per, name in IDLE_ACTS.get(self.name, ()):
                key = (per, name)
                due = self.idle_next.setdefault(key, per * (0.5 + 0.13 * (self.seed % 5)))
                if t >= due and not (name == "smoke" and self.props.get("prop_a") != "cig") and self.talking < 0.5:
                    self.idle_next[key] = t + per
                    self.act(name, t)
                    break
        # blend from the pose before the last switch (no pops), then the idle layer
        k = max(0.0, min(1.0, (t - self.blend_t0) / 0.22))
        k = k * k * (3 - 2 * k)
        out = {}
        for p, v in pose.items():
            out[p] = _lerp(self.blend_from.get(p, v), v, k) if isinstance(v, (int, float)) else v
        ph = self.seed * 1.7
        out["lean"] += 0.9 * math.sin(1.6 * t + ph)
        out["aU"] += 1.4 * math.sin(1.6 * t + 1 + ph)
        out["bU"] += 1.2 * math.sin(1.6 * t + 2 + ph)
        out["head"] += 1.6 * math.sin(0.8 * t + ph)
        if (t + self.seed * 0.7) % 3.7 < 0.13:
            out["eyes"] = 0.0
        if self.talking > 0.5:
            out["mouth"] = max(out["mouth"], 0.35 + 0.6 * abs(math.sin(t * 11)))
            out["head"] += 3 * math.sin(t * 4.1)
        self.pose = out
        self.flash = max(0.0, self.flash - 0.04)
        return events

    def busy(self):
        return bool(self.run or self.queue)

    # ---------------------------------------------------------------- drawing
    def points(self, p, H, ground):
        """Joint positions (pixel coordinates) of pose p for a figure H pixels high standing at x (cells) on `ground` (pixel row)."""
        la = math.radians(p["lean"])
        neck = (math.sin(la) * LEN["torso"], math.cos(la) * LEN["torso"])
        ha = la + math.radians(p["head"])
        head = (neck[0] + math.sin(ha) * LEN["neck"], neck[1] + math.cos(ha) * LEN["neck"])
        sh = (neck[0] - math.sin(la) * 0.035, neck[1] - math.cos(la) * 0.035)

        def arm(u, l):
            ru, rl = math.radians(u), math.radians(u + l)
            e = (sh[0] + math.sin(ru) * LEN["upper"], sh[1] - math.cos(ru) * LEN["upper"])
            return e, (e[0] + math.sin(rl) * LEN["fore"], e[1] - math.cos(rl) * LEN["fore"])

        def leg(t, s):
            rt, rs = math.radians(t), math.radians(t + s)
            k = (math.sin(rt) * LEN["thigh"], -math.cos(rt) * LEN["thigh"])
            return k, (k[0] + math.sin(rs) * LEN["shin"], k[1] - math.cos(rs) * LEN["shin"])
        pts = {"hip": (0.0, 0.0), "neck": neck, "head": head, "sh": sh}
        pts["ea"], pts["ha"] = arm(p["aU"], p["aL"])
        pts["eb"], pts["hb"] = arm(p["bU"], p["bL"])
        pts["ka"], pts["fa"] = leg(p["tA"], p["sA"])
        pts["kb"], pts["fb"] = leg(p["tB"], p["sB"])
        r = math.radians(p["rot"])
        c, s = math.cos(r), math.sin(r)
        pts = {k: (x * c + y * s, -x * s + y * c) for k, (x, y) in pts.items()}
        low = min(pts[k][1] for k in ("hip", "ka", "fa", "kb", "fb", "neck", "head")) - (LEN["head_r"] if p["rot"] > 40 else 0.0)
        out = {}
        for k, (x, y) in pts.items():
            out[k] = (x * self.facing * H, ground - (y - low + p.get("lift", 0.0)) * H)
        return out

    def draw(self, cv, ground, tint=(1, 1, 1), lights=(), t=0.0):
        """Paint the figure; ground = pixel row (two per cell row) of its feet. Returns the buffer's bounding head position in cells."""
        if not self.visible:
            return
        st, p = self.style, self.pose
        H = st["h"] * cv.h * 2 * 0.58 * self.size
        x0 = self.x * cv.w
        pts = {k: (x0 + x, y) for k, (x, y) in self.points(p, H, ground).items()}
        b, f = Buf(), self.facing
        top = st["top"]
        if self.name == "noah" and self.flash > 0:
            top = mix(top, MOODS["red"], min(1.0, self.flash))
        coat = st.get("coat")
        sleeve = coat or top
        tw = max(1.1, st["tw"] * H)
        lr = max(1.0, 0.04 * H)

        def arm(e, h, w, col):
            k = 1.35 if (coat and w == "near") else 0.8 if w == "far" else 1.0
            b.capsule(pts["sh"], pts[e], max(0.9, 0.032 * H), mul(col, k))
            b.capsule(pts[e], pts[h], max(0.8, 0.028 * H), mul(col, k * 1.05))
            b.disc(pts[h][0], pts[h][1], max(0.8, 0.026 * H), st["skin"])
        arm("eb", "hb", "far", sleeve)
        b.capsule(pts["hip"], pts["kb"], lr, mul(st["legs"], 0.8))
        b.capsule(pts["kb"], pts["fb"], lr * 0.9, mul(st["legs"], 0.8))
        b.capsule((pts["fb"][0], pts["fb"][1]), (pts["fb"][0] + f * 0.04 * H, pts["fb"][1]), max(0.8, lr * 0.7), mul(st["shoes"], 0.9))
        b.capsule(pts["hip"], pts["neck"], tw, mul(top, 0.95), 0.25)
        b.capsule(((pts["hip"][0] + pts["neck"][0]) / 2, (pts["hip"][1] + pts["neck"][1]) / 2), pts["neck"], tw * 1.08, top, 0.2)
        b.capsule(pts["hip"], pts["ka"], lr, st["legs"])
        b.capsule(pts["ka"], pts["fa"], lr * 0.9, st["legs"])
        b.capsule(pts["fa"], (pts["fa"][0] + f * 0.045 * H, pts["fa"][1]), max(0.8, lr * 0.7), st["shoes"])
        if coat:                                                                    # long coat: a skirt from the waist down to the knee, swaying a little
            hx, hy = pts["hip"]
            nx, ny = pts["neck"]
            hem_y = max(pts["ka"][1], pts["kb"][1]) + 0.03 * H if p["tA"] < 50 else hy + 0.12 * H
            sway = math.sin(t * 1.3 + self.seed) * 0.01 * H
            for yy in range(int(min(hy, ny) + (hy - ny) * 0.2 if hy > ny else hy), int(hem_y) + 1):
                u = (yy - (ny + (hy - ny) * 0.3)) / max(1.0, hem_y - (ny + (hy - ny) * 0.3))
                u = max(0.0, min(1.0, u))
                cx = _lerp(nx * 0.5 + hx * 0.5, hx, 0.5) + sway * u
                half = tw * (1.0 + 0.55 * u)
                for xx in range(int(cx - half), int(cx + half) + 1):
                    shade = 0.82 + 0.18 * ((xx - cx + half) / (2 * half + 1e-6))
                    if yy >= (hy if hy > ny else ny) - 1 or abs(xx - cx) <= half:
                        b.px(xx, yy, mul(coat, shade))
        # head
        hx, hy = pts["head"]
        r = max(2.2, LEN["head_r"] * H)
        look = p["look"]
        s = f * 0.5 * (1 - max(look, 0.0)) * (1.0 if look > -0.3 else -1.0)
        if st.get("back") and look > -0.3:
            s = f * 0.2
        sg = 1 if s >= 0 else -1
        if st.get("hood"):
            b.disc(hx - f * 0.15 * r, hy - 0.1 * r, r * 1.3, mul(st["hood"], 0.85), 0.25)
            b.disc(hx + s * r * 0.9, hy + 0.12 * r, r * 0.88, mul(st["skin"], 0.55))
            b.disc(hx + s * r * 0.9, hy + 0.12 * r, r * 0.78, st["skin"])
        else:
            back = st.get("back") and abs(look) < 0.3
            for y in range(int(hy - r - 1), int(hy + r + 2)):
                for x in range(int(hx - r - 1), int(hx + r + 2)):
                    dxn, dyn = (x - hx) / r, (y - hy) / r
                    if dxn * dxn + dyn * dyn > 1.0:
                        continue
                    hair = dyn < (0.55 if back else -0.25) or dxn * sg < -0.4 or (self.name == "noah" and dyn < 0.0 and dxn * sg > 0.1)
                    b.px(x, y, st["hair"] if hair else mul(st["skin"], 1.0 - 0.1 * (dyn + 1) / 2))
        if not st.get("back") or look < -0.3 or look > 0.3:
            fx = hx + s * r * (1.0 if st.get("hood") else 1.05)
            eye_y = hy - (0.0 if st.get("hood") else 0.05) * r
            eyes = p["eyes"]
            eye_c = (22, 18, 26) if eyes > 0.3 else mul(st["skin"], 0.6)
            for ex in ((fx,) if abs(s) > 0.2 else (fx - 0.45 * r, fx + 0.45 * r)):
                b.px(ex, eye_y, eye_c)
                if eyes > 1.2:
                    b.px(ex, eye_y - 1, (235, 235, 240))
            my = hy + 0.55 * r
            mc = (110, 40, 46)
            mw = 1 if abs(s) > 0.2 else 2
            b.px(fx, my, mc)
            if mw == 2:
                b.px(fx - 1, my, mc)
                b.px(fx + 1 - 0, my, mc)
            if p["smile"] > 0.4:
                b.px(fx - 1 - (mw - 1), my - 1, mc)
                b.px(fx + 1 + (mw - 1) * 0, my - 1, mc)
            elif p["smile"] < -0.4:
                b.px(fx - 1, my + 1, mc)
            if p["mouth"] > 0.3:
                b.px(fx, my + 1, mc)
        if self.name == "noah":                                                      # the scarf and its tail
            b.capsule((pts["neck"][0] - f * 1, pts["neck"][1] + 1), (pts["neck"][0] + f * 1, pts["neck"][1] + 1), max(1.0, 0.03 * H), st["scarf"])
            for k in range(1, 6):
                b.px(pts["neck"][0] - f * (1 + k * 0.9), pts["neck"][1] + 2 + k * 0.9 + math.sin(t * 3 + k) * 0.6, mul(st["scarf"], 0.9))
        if st.get("collar"):
            b.px(pts["neck"][0] + f, pts["neck"][1] + 1, st["collar"])
            b.px(pts["neck"][0], pts["neck"][1] + 1, st["collar"])
        if self.seat and p["tA"] > 60 and p["sA"] < -40:                             # a stool under a sitting figure
            sx, sy = pts["hip"]
            for xx in range(int(sx - 0.12 * H), int(sx + 0.16 * H)):
                b.px(xx, sy + 2, (88, 64, 46))
                b.px(xx, sy + 3, (58, 42, 32))
            for xx in (int(sx - 0.1 * H), int(sx + 0.14 * H)):
                for yy in range(int(sy + 4), int(ground) + 1):
                    b.px(xx, yy, (58, 42, 32))
        arm("ea", "ha", "near", sleeve)
        for pn, hand in (("prop_b", "hb"), ("prop_a", "ha")):
            if self.props.get(pn):
                self._prop(b, self.props[pn], pts[hand], H, t)
        b.paint(cv, tint, lights)
        self.last = {"head": (hx, hy - r), "mouth": (hx + s * r, hy + 0.55 * r), "ha": pts["ha"], "hb": pts["hb"], "body": ((hx + pts["hip"][0]) / 2, (hy + pts["hip"][1]) / 2),
                     "feet": (x0, ground), "H": H, "r": r}

    def _prop(self, b, name, hand, H, t):
        x, y = hand
        f = self.facing
        if name == "cig":
            b.capsule((x, y), (x + f * 0.06 * H, y - 0.01 * H), 0.5, (236, 232, 222), 0.0)
            b.px(x + f * 0.07 * H, y - 0.01 * H, (255, 150 + int(70 * (0.5 + 0.5 * math.sin(t * 6))), 60))
        elif name == "lighter":
            b.px(x, y, (190, 190, 200))
            b.px(x + f, y - 1, (255, 210, 90))
            b.px(x + f, y - 2, (255, 150, 40))
        elif name == "cup":
            for dx in range(-1, 2):
                for dy in range(0, 3):
                    b.px(x + dx, y - dy, (226, 220, 206))
            b.px(x + 2 * f, y - 1, (226, 220, 206))
        elif name == "teapot":
            for dx in range(-2, 3):
                for dy in range(0, 3):
                    b.px(x + dx, y - dy, (150, 110, 80))
            b.px(x + 3 * f, y - 2, (150, 110, 80))
            b.px(x - 3 * f, y - 1, (120, 90, 70))
        elif name == "knife":
            b.capsule((x, y), (x + f * 0.1 * H, y - 0.05 * H), 0.6, (224, 230, 240), 0.0)
            b.px(x, y, (60, 40, 30))
        elif name == "key":
            b.capsule((x, y), (x + f * 0.05 * H, y - 0.02 * H), 0.5, (176, 150, 90), 0.0)
            b.px(x + f * 0.05 * H, y - 0.02 * H + 1, (176, 150, 90))
        elif name == "note":
            for dx in range(0, 5):
                for dy in range(0, 4):
                    b.px(x + f * dx, y - dy, (232, 226, 206) if (dx + dy) % 3 else (200, 194, 176))
        elif name == "photo":
            for dx in range(0, 4):
                for dy in range(0, 3):
                    b.px(x + f * dx, y - dy, (190, 180, 160))
        elif name == "cube":
            k = 0.5 + 0.5 * math.sin(t * 2.6)
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    b.px(x + dx, y + dy - 2, (int(100 + 50 * k), int(190 + 40 * k), 255))
            b.px(x - 1, y - 3, (230, 250, 255))
        elif name == "candle":
            for dy in range(0, 4):
                b.px(x, y - dy, (232, 220, 190))
            b.px(x, y - 4, (255, 210 + int(30 * math.sin(t * 13)), 90))
            b.px(x, y - 5, (255, 150, 50))
        elif name == "flashlight":
            b.capsule((x, y), (x + f * 0.08 * H, y), 1.0, (90, 90, 100), 0.0)
        # "hand": nothing extra
