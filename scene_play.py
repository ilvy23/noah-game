"""scene_play.py - every story scene as an animation: a backdrop, figures that ACT the text, speech bubbles and captions on top, choices as an overlay.

    play(scene, ctx, sid=None, ...)   plays a whole story scene (all nodes of its tree, asks the choices) and returns the node ids it visited
    Session(ctx, info)                the same, driven from outside (story_game.RealIO): show(text, who) / pick(labels) / timed(labels, seconds, on_tick) / close()
Pieces: scene_lib.parser (text -> beats: speech, actions, narration, time-jump cards), scene_lib.verbs (verb -> action), scene_lib.actions + figures (the puppets),
scene_lib.backdrops (photo and procedural pictures), scene_lib.overrides (per-scene backdrop/cast table), speech.py (bubbles, typing, voice blips).
Everything is frame-based and deterministic (time = frame number); nothing is printed outside the frame loop. ctx = mika_ending.Ctx-like (out, size(), sleep, fps, sfx, mixer, log).
"""
import math
import random
import sys
import time

import noah_gore_fx as G
import speech
from scene_lib import backdrops, figures, overrides, parser

speech.COLORS.setdefault("you", (170, 205, 255))
speech.NAMES.setdefault("you", "YOU")
for _n, _c in (("stranger", (200, 190, 175)), ("woman", (225, 170, 175)), ("child", (230, 200, 150))):
    speech.COLORS.setdefault(_n, _c)
    speech.NAMES.setdefault(_n, {"stranger": "", "woman": "WOMAN", "child": "KID"}[_n])
MIN_COLS, MIN_ROWS = 120, 40
VOICE = {"you": "narrator", "stranger": "narrator", "woman": "narrator", "child": "narrator"}


class World:
    """The backdrop, the puppets, the smoke and tears, the camera."""

    def __init__(self, w, h, plan, chapter, seed=1, sfx=None):
        self.w, self.h, self.plan, self.sfx = w, h, plan, sfx or (lambda n: None)
        self.rng = random.Random(seed)
        kind = plan["kind"]
        self.ambient = None
        if kind.startswith("ambient:"):
            import ambient_fx
            self.ambient = ambient_fx.KINDS[kind.split(":", 1)[1]](w, h, random.Random(seed))
            self.bd = backdrops.make("black", w, h, chapter, seed)
            self.bd.marks.update(left=0.28, mid=0.5, right=0.72)
        else:
            self.bd = backdrops.make(kind, w, h, chapter, seed)
        self.chapter, self.seed = chapter, seed
        self.stage = (1.0 - (speech.panel_width(w) + 3) / float(w)) if w >= getattr(speech, "PANEL_MIN_COLS", 10 ** 6) else 1.0      # wide terminals keep the right column for the speech
        self.bd.marks = {k: v * self.stage + (1 - self.stage) * 0.02 for k, v in self.bd.marks.items()}
        self.figs = {}
        self.parts = G.Particles(self.rng, 300)
        self.zoom, self.zt, self.zf = 1.0, 1.0, (0.5, 0.5)
        self.jolt = 0.0
        self.clock = 0.0
        self.flashes = []                                   # (until, rgb, strength)
        self.log = []                                       # events fired (tests)

    # ---------------------------------------------------------------- cast
    def ensure(self, ids):
        for fid in ids:
            if self.ambient is not None or fid in self.figs:
                continue
            slot, facing = self.plan["figs"].get(fid) or overrides.SLOTS.get(fid, ("mid", -1))
            used = {p.slot for p in self.figs.values()}
            if slot in used:
                slot = next((s for s in ("right", "mid", "far", "left") if s not in used), "far")
            if fid != "you" and "you" not in ids and "you" not in self.figs and slot == "right" and not self.figs:
                slot, facing = "mid", 1
            p = figures.Puppet(fid, x=self.bd.marks[slot], facing=facing, size=1.1 if fid == "you" else 1.0, mood=self.plan.get("mood"), seed=len(self.figs) + 1,
                               seat=self.bd.seat)
            p.slot = slot
            self.figs[fid] = p
            for i, name in enumerate(self.plan.get("preset", {}).get(fid, [])):         # already sitting, cigarette in hand: played before the scene starts
                p.act(name, -60.0 + 5 * i)
                for k in range(26):
                    p.update(-60.0 + 5 * i + k * 0.25)
            if p.history == [] and "you" in self.figs and fid != "you":
                p.facing = -1 if p.x > self.figs["you"].x else 1

    def use(self, kind):
        """Move the scene to another picture (a dream node jumps to another room); the figures stay where they are."""
        self.bd = backdrops.make(kind, self.w, self.h, self.chapter, self.seed)
        self.bd.marks = {k: v * self.stage + (1 - self.stage) * 0.02 for k, v in self.bd.marks.items()}
        self.ambient = None
        self.plan = dict(self.plan, kind=kind)
        for p in self.figs.values():
            p.seat = self.bd.seat

    def effect(self, name, t):
        """The world answers the text: the lights flicker, a cold flash, a thud (jolt), a glow, thicker fog."""
        self.log.append(("world", name))
        if name == "flicker":
            self.flashes += [(t + 0.35, (0, 0, 0), 0.7), (t + 0.9, (0, 0, 0), 0.5)]
        elif name == "cold":
            self.flashes.append((t + 0.5, (120, 170, 255), 0.16))
        elif name == "thud":
            self.jolt = 1.8
        elif name == "glow":
            self.flashes.append((t + 0.8, (255, 210, 140), 0.18))
        elif name == "fog":
            self.bd.fogs = [(a, b, min(0.55, d + 0.15), c, sp) for a, b, d, c, sp in self.bd.fogs]

    def act(self, who, action, t, delay=0.0):
        if who == "world":
            return self.effect(action, t + delay)
        p = self.figs.get(who)
        if p is None:
            return
        if action == "walk_in" and not p.busy() and p.x == self.bd.marks.get(p.slot) and not p.history:
            p.visible = False
        if action in ("walk_out", "approach", "step_back") and p.slot == "left" and False:
            return
        to = None
        if action == "approach":
            others = [q for q in self.figs.values() if q is not p and q.visible]
            if others:
                o = min(others, key=lambda q: abs(q.x - p.x))
                p.act("walk_to", t, delay, to=p.x + (0.12 if o.x > p.x else -0.12))
                return
        p.act(action, t, delay, to=to)

    def focus(self, who, z):
        p = self.figs.get(who)
        if p and p.last:
            hx, hy = p.last["body"]
            self.zf = (max(0.2, min(0.8, hx / self.w)), max(0.3, min(0.7, hy / (2.0 * self.h))))
        self.zt = z

    def anchor(self, who):
        if self.ambient is not None:
            return (0.5, 0.55) if who in ("noah", "noah2", "noah3") else None
        p = self.figs.get(who)
        if not p or not p.last or not p.visible:
            return None
        hx, hy = p.last["head"]
        return (max(0.05, min(0.95, hx / self.w)), max(0.12, hy / 2.0 / self.h))

    # ---------------------------------------------------------------- frame
    def draw(self, cv, t, dt):
        self.clock = t
        if self.ambient is not None:
            self.ambient.draw(cv, t, dt)
        else:
            self.bd.draw(cv, t, dt)
        order = sorted(self.figs.values(), key=lambda p: (p.slot != "far", p.slot == "left"))
        for p in order:
            for ev in p.update(t):
                self.event(p, ev, t)
        tint, lights = self.bd.tint, [(lx, ly, r, c) for lx, ly, r, c in self.bd.lights]
        for p in order:
            if not p.visible:
                continue
            ground = self.bd.ground + (3 if p.name == "you" else -2 if p.slot == "far" else 0)
            p.draw(cv, ground, tint, lights, t)
            if p.props.get("prop_a") == "cig" and p.last and self.rng.random() < 0.5 * dt * 8:        # a thin line of smoke rises from the cigarette
                hx, hy = p.last["ha"]
                self.parts.add(hx + p.facing * 0.06 * p.last["H"], hy / 2.0, self.rng.uniform(-0.6, 0.6), -2.2, 2.4, "smoke", 0.0, 0.2)
            if p.props.get("prop_a") == "cube" and p.last:
                hx, hy = p.last["ha"]
                G.glow(cv, int(hx), int(hy / 2), 9, 4, (110, 190, 255), 0.5 + 0.2 * math.sin(t * 3))
            if p.props.get("prop_b") == "lighter" and p.last:
                hx, hy = p.last["hb"]
                G.glow(cv, int(hx), int(hy / 2) - 1, 6, 3, (255, 170, 60), 0.5)
        self.parts.step(dt)
        self.parts.draw(cv, 0.0)
        for until, rgb, a in list(self.flashes):
            if t >= until:
                self.flashes.remove((until, rgb, a))
            else:
                G.flash(cv, rgb, a * min(1.0, (until - t) / 0.4))
        k = min(1.0, dt * 2.5)
        self.zoom += (self.zt - self.zoom) * k
        if self.zoom > 1.01:
            G.push_in(cv, self.zoom, *self.zf)
        j, self.jolt = self.jolt, max(0.0, self.jolt - dt * 6)
        return (int(self.rng.uniform(-j, j) * 2), int(self.rng.uniform(-j, j))) if j > 0.3 else (0, 0)

    def event(self, p, ev, t):
        self.log.append((p.name, ev))
        last = p.last or {}
        if ev in ("puff", "inhale") and last:
            mx, my = last["mouth"]
            for _ in range(5 if ev == "puff" else 1):
                self.parts.add(mx, my / 2.0, p.facing * self.rng.uniform(0.5, 2.5), self.rng.uniform(-2.0, -0.6), 3.2, "smoke", 0.0, 0.3)
        elif ev == "tears" and last:
            mx, my = last["mouth"]
            for _ in range(3):
                self.parts.add(mx + p.facing * 0.5, my / 2.0 - 1, self.rng.uniform(-0.4, 0.4), 4.0, 1.4, "spray", 6.0)
        elif ev == "jolt":
            self.jolt = 2.2
        elif ev == "ash" and last:
            hx, hy = last["ha"]
            for _ in range(3):
                self.parts.add(hx, hy / 2.0, 0, 1.0, 1.4, "ash", 5.0)
        elif ev == "door":
            self.flashes.append((t + 0.4, (255, 200, 130), 0.25))
        elif ev == "flame" and last:
            hx, hy = last["hb"]
            self.parts.add(hx, hy / 2.0 - 2, 0, -0.5, 0.7, "ember", 0.0)
        elif ev == "pour":
            self.sfx("lake-whispers")
        elif ev.startswith("sfx:"):
            self.sfx(ev[4:])
        elif ev == "cold":
            self.flashes.append((t + 0.3, (120, 160, 255), 0.12))


def hold_scale(ctx):
    return getattr(ctx, "hold_scale", 0.6)


class Session:
    """One animated story scene on the terminal. open() -> show()/pick()/timed() any number of times -> close()."""

    def __init__(self, ctx, info, plan=None, seed=1):
        self.ctx, self.info, self.seed = ctx, info, seed
        self.chapter = info.get("chapter", 1)
        scene = info.get("scene") or {}
        self.plan = plan or overrides.plan(info.get("sid"), scene, info.get("place"), self.chapter, info.get("text", ""))
        self.world = None
        self.cv = self.prev = None
        self.clock = 0.0
        self.node = None
        self.keys = None
        self.opened = False
        self.truecolor = True
        self.fade = 1.0                         # 1 = black, fades to 0 on open
        self.beats_played = []                  # (kind, who, text) for tests
        self.hist = []                          # the bubbles shown so far (the wide layout of speech.py keeps the last three above the newest)
        self.alt = False

    # ---------------------------------------------------------------- terminal
    def open(self):
        ctx = self.ctx
        cols, rows = ctx.size()
        self.w, self.h = cols, rows - 1
        self.fps = getattr(ctx, "fps", None) or 12
        try:
            import ascii_art
            self.truecolor = ascii_art.has_truecolor()
        except Exception:
            pass
        import ui
        want_keys = getattr(ctx, "keys", True) and ctx.out is sys.stdout
        self.keys = ui.Keys() if want_keys else None
        if self.keys is not None:
            self.keys.__enter__()
        self.raw = bool(self.keys and self.keys.raw)
        self.alt = ctx.out is sys.stdout and sys.stdout.isatty()
        ctx.out.write(("\033[?1049h" if self.alt else "") + "\033[?25l\033[0m\033[2J")
        self.cv = G.Canvas(self.w, self.h)
        self.opened = True

    def close(self):
        if not self.opened:
            return
        self.opened = False
        mixer = self.ctx.mixer
        if mixer is not None:
            import audio
            audio.voice_off(mixer)
        if self.keys is not None:
            self.keys.__exit__(None, None, None)
        self.ctx.out.write("\033[0m\033[2J\033[H\033[?25h" + ("\033[?1049l" if self.alt else ""))
        self.ctx.out.flush()

    def _world(self, cast):
        if self.world is None:
            figs = dict(self.plan.get("figs") or {})
            self.world = World(self.w, self.h, self.plan, self.chapter, self.seed, sfx=self.ctx.sfx)
            self.world.ensure([f for f in figs if f in cast or f in figs])
        self.world.ensure(cast)

    def set_node(self, nid):
        self.node = nid
        kind = self.plan.get("nodes", {}).get(nid)
        if kind and self.world is not None and self.world.plan["kind"] != kind:
            self.world.use(kind)
            self.world.flashes.append((self.clock + 0.5, (0, 0, 0), 0.9))                  # the jump cut of a dream

    # ---------------------------------------------------------------- one frame
    def frame(self, overlay=None, wait=True):
        """Draw the world (+ overlay(cv, clock)) and return the key pressed during the frame, if any."""
        started = time.monotonic()
        cv, ctx = self.cv, self.ctx
        dx, dy = self.world.draw(cv, self.clock, 1.0 / self.fps) if self.world else (0, 0)
        if overlay:
            overlay(cv, self.clock)
        if self.fade > 0.01:
            G.darken(cv, 1.0 - self.fade)
            self.fade = max(0.0, self.fade - 1.0 / (self.fps * 0.6))
        s, self.prev = cv.shifted(int(dx), int(dy)).diff(self.prev, self.truecolor)
        ctx.out.write(s)
        ctx.out.flush()
        key = None
        left = max(0.0, 1.0 / self.fps - (time.monotonic() - started))
        if self.raw:
            key = self.keys.read(timeout=left)
        elif wait:
            ctx.sleep(left)
        self.clock += 1.0 / self.fps
        return key

    # ---------------------------------------------------------------- beats
    def show(self, text, who="narrator"):
        """Play the text of a node: its beats in order. `who` is the figure the game says speaks the node (narrator = nobody in particular)."""
        if not text.strip():
            return 0
        main = [who] if who in parser.KNOWN.values() else [f for f in self.plan.get("figs", {}) if f != "you"]
        if who in ("system",):
            beats, cast = [parser.Beat("narr", text.strip())], list(self.plan.get("figs", {}))
        else:
            beats, cast = parser.parse(text, main=main)
        for nid, sub, fig, act in self.plan.get("acts", []):
            for b in beats:
                if (nid in ("*", self.node)) and sub in b.text:
                    b.acts.append((fig, act, 0.2))
                    if fig not in cast:
                        cast.append(fig)
        cast = [c for c in cast if c in figures.STYLES]
        self._world(cast or ["you"])
        for b in beats:
            self.beat(b)
        return len(beats)

    def beat(self, b):
        ctx, w = self.ctx, self.world
        ctx.log.append(("say" if b.kind == "say" else "card" if b.kind == "card" else "narr", b.who, b.text))
        self.beats_played.append((b.kind, b.who, b.text, list(b.acts)))
        if b.kind == "card":
            return self.card(b.text)
        t0 = self.clock
        if b.who:
            w.ensure([b.who] if b.who in figures.STYLES else [])
        for actor, action, delay in b.acts:
            w.ensure([actor] if actor in figures.STYLES else [])
            w.act(actor, action, t0, delay)
        p = w.figs.get(b.who)
        if b.kind == "say" and p:
            p.talking = 1.0
            if not b.acts and len(b.text) > 28 and (len(b.text) + int(t0)) % 3:
                p.act(("gesture", "gesture2", "nod")[len(b.text) % 3], t0, 0.2)
        if b.shock:
            w.jolt = 2.5
            who = p or w.figs.get("noah")
            if who is not None and who.name == "noah":
                who.flash = 1.0
            w.focus(b.who or ("noah" if "noah" in w.figs else next(iter(w.figs), None)), 1.2)
            w.flashes.append((t0 + 0.4, (255, 60, 50), 0.18))
        elif b.push:
            w.focus(next((a for a, _, _ in b.acts), b.who), 1.1)
        else:
            w.zt = 1.0
        cps = getattr(ctx, "cps", speech.CPS)
        who_voice = b.who if b.kind == "say" else "narrator"
        voiced, born, done_at = False, self.clock, None
        text = b.text
        mixer = ctx.mixer
        while True:
            n = int((self.clock - born) * cps)
            if mixer is not None:
                import audio
                if n < len(text) and not voiced:
                    audio.voice_on(mixer, VOICE.get(who_voice, who_voice))
                    voiced = True
                elif n >= len(text) and voiced:
                    audio.voice_off(mixer)
                    voiced = False
            anchor = w.anchor(b.who) if b.kind == "say" else None
            bw = b.who if b.kind == "say" else "narrator"
            key = self.frame(lambda cv, t: speech.draw_bubble(cv, bw, text, min(n, len(text)), anchor or ((0.5, 0.5) if b.kind == "say" else None), t, tuple(self.hist[-3:])))
            if n >= len(text) and done_at is None:
                done_at = self.clock
                if p:
                    p.talking = 0.0
            if key in ("enter", " "):
                if n < len(text):
                    born = self.clock - len(text) / cps - 0.01
                else:
                    break
            elif not self.raw and done_at is not None and self.clock - done_at >= speech.hold_time(text) * hold_scale(ctx):
                break
        self.hist.append((bw, text))
        if p:
            p.talking = 0.0
        if mixer is not None and voiced:
            import audio
            audio.voice_off(mixer)

    def card(self, text, seconds=2.4):
        """A time-jump card: the picture fades to black, the title appears and goes, the picture comes back."""
        t0 = self.clock

        def over(cv, t):
            a = min(1.0, (t - t0) / 0.7, (t0 + seconds - t) / 0.7)
            G.darken(cv, 1.0 - 0.92 * max(0.0, min(1.0, a)))
            col = tuple(int(c * max(0.0, min(1.0, a))) for c in (226, 226, 232))
            cv.text(max(0, (cv.w - len(text)) // 2), cv.h // 2, text, col)
        while self.clock - t0 < seconds:
            key = self.frame(over)
            if key in ("enter", " ") and self.clock - t0 > 0.5:
                break

    # ---------------------------------------------------------------- choices
    def _options_overlay(self, labels, sel, header="", bar=None):
        def over(cv, t):
            width = max(24, min(cv.w - 8, 100))
            lines = []
            for i, lab in enumerate(labels):
                import textwrap
                wrapped = textwrap.wrap(lab, width - 8) or [""]
                lines.append((i, wrapped))
            rows = sum(len(x[1]) for x in lines)
            bh = rows + 2
            x0, y0 = (cv.w - width) // 2, max(1, cv.h - bh - 1)
            for yy in range(y0, y0 + bh):
                for xx in range(x0, x0 + width):
                    cv.put(xx, yy, " ", (230, 230, 236), (8, 10, 16))
            cv.text(x0, y0, "╭" + ("─ %s " % header if header else "─").ljust(width - 2, "─") + "╮", (200, 205, 220), (8, 10, 16))
            cv.text(x0, y0 + bh - 1, "╰" + "─" * (width - 2) + "╯", (200, 205, 220), (8, 10, 16))
            for r in range(1, bh - 1):
                cv.put(x0, y0 + r, "│", (200, 205, 220), (8, 10, 16))
                cv.put(x0 + width - 1, y0 + r, "│", (200, 205, 220), (8, 10, 16))
            r = 1
            for i, wrapped in lines:
                on = i == sel
                col = (255, 232, 150) if on else (180, 184, 196)
                for j, ln in enumerate(wrapped):
                    cv.text(x0 + 2, y0 + r, ("▶ " if on and j == 0 else "  ") + ("%d) " % (i + 1) if j == 0 else "   ") + ln, col, (8, 10, 16))
                    r += 1
            if bar is not None:
                n = int((width - 4) * max(0.0, min(1.0, bar())))
                cv.text(x0 + 2, y0 + bh - 1, "━" * n, (255, 120, 100) if n < (width - 4) * 0.3 else (230, 230, 236), (8, 10, 16))
        return over

    def pick(self, labels):
        """The choice as an overlay on the running animation; returns the index of the label."""
        return self.timed(labels, None, None)

    def timed(self, labels, seconds, on_tick=None):
        """Arrow keys / digits + Enter within `seconds` (None = no limit); returns the index or None on timeout; on_tick(sec) about once a second."""
        if self.world is None:
            self._world(list(self.plan.get("figs", {})) or ["you"])
        self.world.zt = 1.0
        sel, start, last = 0, self.clock, 0
        script = getattr(self.ctx, "choices", None)
        over = self._options_overlay(labels, 0, "choose", (lambda: 1.0 - (self.clock - start) / seconds) if seconds else None)
        while True:
            el = self.clock - start
            if seconds and el >= seconds:
                return None
            if on_tick and int(el) > last:
                last = int(el)
                on_tick(last)
            over = self._options_overlay(labels, sel, "choose" if not seconds else "choose  %ds" % max(0, int(seconds - el)),
                                         (lambda: 1.0 - (self.clock - start) / seconds) if seconds else None)
            key = self.frame(over)
            if key in ("up", "k"):
                sel = (sel - 1) % len(labels)
            elif key in ("down", "j"):
                sel = (sel + 1) % len(labels)
            elif key == "enter":
                return sel
            elif key and key.isdigit() and 1 <= int(key) <= len(labels):
                return int(key) - 1
            elif not self.raw and el > 0.8:                           # no keyboard (tests, pipes): the scripted answer, else the first
                if seconds and not script:
                    continue
                if script:
                    return script.pop(0) % len(labels) if script[0] is not None else None
                return 0


def play(scene, ctx, sid=None, place=None, chapter=None, choose=None, session=None):
    """Play a whole story scene (a dict of story.json) on ctx: every node text as an animated beat sequence, choices as an overlay.
    choose(node_id, labels) -> index (default: the ctx.choices script, or asks on the overlay). Returns the list of node ids visited."""
    chapter = chapter or scene.get("kapitel") or 1
    tree = scene.get("baum")
    if tree:
        text0 = " ".join(n["text"] for n in tree["knoten"].values())
    else:
        text0 = scene.get("text", "")
    info = {"sid": sid, "scene": scene, "place": place or scene.get("ort"), "chapter": chapter, "text": text0}
    s = session or Session(ctx, info)
    s.open()
    visited = []
    try:
        who = (scene.get("figuren") or ["narrator"])[0]
        who = who if who in parser.KNOWN.values() else "narrator"
        if not tree:
            s.show(scene.get("text", ""), who)
            return visited
        nid = tree["start"]
        while nid and len(visited) < 60:                                   # a tree can loop back; 60 nodes is more than any scene has
            node = tree["knoten"][nid]
            visited.append(nid)
            s.set_node(nid)
            s.show(node["text"], who)
            wahl = node.get("wahl") or []
            if not wahl:
                break
            labels = [c["label"] for c in wahl]
            i = choose(nid, labels) if choose else s.pick(labels)
            nid = wahl[i]["ziel"]
        return visited
    finally:
        s.close()
