"""boss_ui.py - the boss intro (locked input, timed to the music) and the curses fight screen.

The intro follows the mood song: it reaches full volume at INTRO_END seconds; at CUT seconds Noah's line breaks off
mid-word and another personality types a new line very fast; at INTRO_END the fight starts.
"""
import sys
import time

import math
import random

import boss as boss_mod
import fx
import noah_talk
import portraits
import setpieces
import ui
import ultra_bonus
import ultra_fx


def lit(b, x, y):
    """Is the cell (x, y) of the arena lit? Always, except while the lights are out (a small circle round the heart)."""
    return b.dark <= 0 or ((x - b.hx) / 2.0) ** 2 + (y - b.hy) ** 2 <= b.dark ** 2


def _default_sfx(name):
    import audio
    audio.sfx(name)

INTRO_END = 52.0
CUT = 44.0                        # Noah's line stops mid-word here ...
SILENCE = 1.3                     # ... then everything holds its breath, the music drops ...
BREAK_AT = CUT + SILENCE          # ... and then the boom, the flash and the red line
FACES = {"noah": ("(^_^)", "green"), "noah2": ("(o_o)", "yellow"), "noah3": ("(>:D)", "red")}
TIRED = {"noah": ("(^_^)", "(^_~)", "(;_;)"), "noah2": ("(o_o)", "(o_O)", "(x_x)"), "noah3": ("(>:D)", "(>:()", "(>:O)")}   # fresh, hurt, nearly done


def face_for(who, ratio):
    """Noah's little face in the HUD: it changes as his life runs out."""
    f = TIRED.get(who, TIRED["noah"])
    return f[0] if ratio > 0.6 else (f[1] if ratio > 0.3 else f[2])
SEGMENTS = [   # (start_s, end_s, who, text) - the owner's boss_intro lines replace these through lines=
    (2.0, 11.0, "noah", "It's not like I WANT to do this. So please, just give it back and go home."),
    (13.0, CUT - 0.4, "noah", "And I'll forget this whole thing and, and... I'll make you tea tomorrow, I'll make you tea every day, I'll make you tea ev"),
]
BREAK_LINE = ("noah3", "what is this fucking noise!?")
AFTER = [(47.9, 50.4, "noah2", "Oh... oh no. Not now. I'm still talking, I'm still here, I'm..."),
         (50.7, INTRO_END - 0.3, "noah3", "...it's quiet in here, isn't it.")]


class Clock:
    def __init__(self, now=time.monotonic, sleep=time.sleep):
        self.now, self.sleep = now, sleep
        self.t0 = now()

    def t(self):
        return self.now() - self.t0

    def wait_until(self, t):
        d = t - self.t()
        if d > 0:
            self.sleep(d)


class Tee:
    """Remembers what was printed, so the screen can be redrawn shaking at the moment of the impact."""

    def __init__(self, out):
        self.out, self.buf = out, []

    def write(self, s):
        self.buf.append(s)
        return self.out.write(s)

    def flush(self):
        self.out.flush()

    def isatty(self):
        return getattr(self.out, "isatty", lambda: False)()


def shake_screen(out, text, frames=18, amp=4, sleep=time.sleep, rows=None):
    """Redraw the last screenful at random offsets (the whole terminal content jumps), then settle."""
    import shutil
    rows = rows or shutil.get_terminal_size((100, 30)).lines
    lines = "".join(text).replace("\r", "").split("\n")[-(rows - 3):]
    for f in range(frames):
        k = max(1, amp * (frames - f) // frames)
        dx, dy = random.randint(-k, k), random.randint(-k // 2, k // 2)
        out.write("\033[2J")
        for i, l in enumerate(lines):
            out.write("\033[%d;%dH%s" % (max(1, i + 1 + dy), max(1, 3 + dx), l))
        out.flush()
        sleep(0.035)
    out.write("\033[2J\033[H" + "\n".join(lines) + "\n")
    out.flush()


def flash(out, sleep, times=2):
    """Invert the whole screen for a moment (terminals that cannot do it simply ignore the codes)."""
    for _ in range(times):
        out.write("\033[?5h")
        out.flush()
        sleep(0.07)
        out.write("\033[?5l")
        out.flush()
        sleep(0.07)


def run_intro(out=None, clock=None, mixer=None, keys=None, segments=None, break_line=None, after=None, speed_floor=0.015):
    """Play the locked intro. Input is read and thrown away. Without audio the same schedule runs on the clock."""
    out = out or sys.stdout
    tty = getattr(out, "isatty", lambda: False)()
    if tty:
        out = Tee(out)
    clock = clock or Clock()
    segments = segments or SEGMENTS
    break_line = break_line or BREAK_LINE
    after = after or AFTER
    if mixer is not None:
        mixer.boss_intro()

    def drain():
        if keys is not None and getattr(keys, "raw", False):
            while keys.read(timeout=0) is not None:
                pass

    def timed(start, end, who, text, cut_mid_word=False):
        clock.wait_until(start)
        drain()
        per_char = max(speed_floor, (end - start) / max(1, len(text)))
        ui.reveal(text, who, speed=per_char, out=out, sleep=clock.sleep, mixer=mixer, end="")
        drain()

    for i, (s, e, who, text) in enumerate(segments):
        timed(s, e, who, text)
        out.write("\n")
    clock.wait_until(CUT)
    # the line stops in the middle of a word: the voice dies, the music drops, nothing moves
    if mixer is not None:
        import audio
        audio.voice_off(mixer)
        getattr(mixer, "dip", lambda s: None)(SILENCE)
    clock.wait_until(BREAK_AT)
    # impact: boom, the whole screen flashes, and another personality types fast on a new line, in red
    if mixer is not None:
        getattr(mixer, "impact", lambda: None)()
    flash(out, clock.sleep)
    if tty:
        shake_screen(out.out, out.buf, sleep=clock.sleep)           # the whole screen shakes with the boom
    out.write("\n\n")
    who2, line = break_line
    ui.reveal(line, who2, speed=0.006, out=out, sleep=clock.sleep, mixer=mixer)
    flash(out, clock.sleep, times=1)
    for s, e, who, text in after:
        timed(s, e, who, text)
        out.write("\n")
    clock.wait_until(INTRO_END)
    drain()


class Fight:
    """Controller for the fight: menu, timing bar, dodging. `screen` shows frames and returns keys.
    Losing restarts the same phase (unlimited unless `retries` is given); MERCY at the end is the last action."""

    def __init__(self, b, screen, clock=None, on_phase=None, dt=1 / 30, retries=None, texts=None, on_end=None, sfx=None, has=None, user=None, talker=None):
        self.on_end = on_end or (lambda: None)
        self.sfx = sfx or _default_sfx                   # sfx(name): a one-shot from soundtracks/sfx/ if the file exists (audio.sfx)
        if hasattr(screen, "sfx"):
            screen.sfx = self.sfx
        self._ei = 0
        self.texts = texts or {}
        self.b, self.s = b, screen
        self.clock = clock or Clock()
        self.on_phase = on_phase or (lambda n: None)
        self.dt = dt
        self.max_retries = retries
        self.message = ""
        self.msg_t = 0.0                                 # seconds the line Noah said in the dodge phase stays on screen
        if user is None:
            try:
                import getpass
                user = getpass.getuser()
            except Exception:
                user = "friend"
        self.talk = talker or noah_talk.Talker(self.texts, has, user=user)        # Noah's short lines (noah_talk.py)

    def resolve(self, text):
        """'[TEXT: id]' becomes the owner's/drafted text when we have one."""
        import re
        m = re.match(r"^\[TEXT: ([^\]]+)\]$", text or "")
        return self.texts.get(m.group(1), text) if m else text

    def say(self, text, who=None):
        text = self.resolve(text)
        self.message = text
        self.s.frame(self.b, self.message, who or self.b.who)
        self.s.say(text, who or self.b.who)

    def line(self, phase, i=0):
        ls = self.b.lines.get(phase) or []
        return ls[i % len(ls)] if ls else "[TEXT: boss.p%d.%d]" % (phase, i)

    SFX = {"boss_hit": "boss-hit", "hit": "heart-hurt", "phase": "phase-shift"}

    def pump(self):
        """Look at what the fight logic reported since the last call, play the sounds that go with it, return the new events."""
        new = self.b.events[self._ei:]
        self._ei = len(self.b.events)
        for e in new:
            if e[0] == "sfx":
                self.sfx(e[1])
            elif e[0] in self.SFX:
                self.sfx(self.SFX[e[0]])
            elif e[0] == "turn" and e[1] in ("climax", "rage", "trinity"):
                self.sfx("noah-roar")
        return new

    def piece(self, name, phase=None):
        """A set-piece (setpieces.py) on screens that can play one; the owner's text boss.beat.<name> replaces the draft line."""
        play = getattr(self.s, "setpiece", None)
        if play:
            play(self.b, name, self.texts.get(setpieces.text_key(name, phase)) or setpieces.default_text(name, phase))

    def phase_text(self, phase):
        return self.texts.get("boss.phase.%d" % phase) or self.line(phase, 0)

    def run(self):
        """The whole fight. Ctrl+C asks 'really leave?' (the screen's confirm_leave): no = the fight goes on exactly where it was."""
        while True:
            try:
                return self._run()
            except KeyboardInterrupt:
                ask = getattr(self.s, "confirm_leave", None)
                if ask is None or ask():
                    raise

    def _run(self):
        b = self.b
        if b.state == "player" and b.retries == 0 and not any(b.turns.values()):
            if b.phase > 1:                              # (no heading at the very start: the intro leads straight into the fight)
                self.piece("begin%d" % b.phase)
            b.begin_enemy_turn()                         # after the intro the fight starts at once: no menu first
        while b.state != "won":
            if b.state == "player":
                self.player_turn()
            elif b.state == "mercy":
                self.on_end()                            # the fight itself is over: the boss song fades out now
                self.say(self.texts.get("boss.beaten", "He goes quiet."), "system")     # no button: the game goes straight on
                b.mercy()
            elif b.state == "lost":
                if self.max_retries is not None and b.retries >= self.max_retries:
                    return "lost"
                getattr(self.s, "death", lambda bb: None)(b)                            # the heart breaks (about 2 s)
                self.s.blackout()
                line = ""
                if (b.retries + 1) in (5, 12):                                          # the name: only at a few moments that matter
                    line = self.talk.key_moment(b.phase)
                line = line or self.talk.pick(b.phase, "death")
                b.retry_phase()
                self.s.frame(b, "", b.who)
                self.say(line or self.line(b.phase, b.retries), b.who)
            else:
                self.enemy_turn()
        self.s.frame(b, "", b.who)
        return "won"

    def noah_says(self, line, blocking=False):
        """Noah says something short: on the message line for a few seconds (or, between turns, until it was read)."""
        if not line:
            return
        if blocking:
            self.say(line, self.b.who)
        else:
            self.message, self.msg_t = line, 3.6

    def player_turn(self):
        b = self.b
        opts = ["FIGHT", "ACT", "ITEM", "MERCY"]
        i = self.s.menu(b, opts, self.message)
        before = b.phase
        if i == 0:
            self.s.frame(b, "stop the bar on 0 (Enter): the closer, the harder you hit", b.who)
            dmg = b.attack(self.s.timing_bar(b))
            if dmg:
                getattr(self.s, "react", lambda n: None)("hurt")
            self.say("MISS" if dmg == 0 else "-%d" % dmg, "system")
            for e in self.pump():
                if e[0] == "threshold":                  # 50% / 20%: a slam, a line, Noah's face; the next turn is a rage turn
                    self.piece("thr%d" % e[2], e[1])
            if b.phase == before:                        # (a beaten Noah says nothing more: the transition comes next)
                kind = "miss" if dmg == 0 else ("big" if dmg >= boss_mod.BIG_HIT else "hit")
                if b.hp_ratio < 0.25 and dmg:
                    kind = "weak"
                self.noah_says(self.talk.event(b.phase, kind), blocking=True)
            if b.ultra_announce:                         # a perfect first hit: the carried tesseract unfolds
                b.ultra_announce = False
                getattr(self.s, "ultra_unlock_animation", lambda bb: None)(b)
                self.say(self.texts.get("boss.ultra.unlock", "The tesseract unfolds. ULTRA TESSERACT: once per fight, ITEM."), "system")
        elif i == 1:
            j = self.s.menu(b, ["Check", "Say his name", "back"], "")
            if j in (0, 1):
                self.say(b.act("check" if j == 0 else "name"))
        elif i == 2:
            items = ["Heal (%d)" % b.heals]
            if b.ultra_unlocked and not b.ultra_used:      # replaces the normal tesseract once unlocked
                items.append("ULTRA TESSERACT: stop time")
            elif b.has_tesseract and not b.tesseract_used and not b.ultra_unlocked:
                items.append("Tesseract: stop time")
            items.append("back")
            j = self.s.menu(b, items, "")
            if j == 0:
                if not b.heal():
                    self.say("[TEXT: boss.noheal]", "system")
                else:
                    self.noah_says(self.talk.event(b.phase, "heal"), blocking=True)
            elif j < len(items) - 1:
                if b.ultra_unlocked and not b.ultra_used:
                    if b.use_ultra():
                        getattr(self.s, "ultra_animation", lambda bb: None)(b)
                        getattr(self.s, "ultra_beam", lambda bb: None)(b)             # the cube strikes Noah, his picture cracks
                        getattr(self.s, "ultra_mika", lambda bb: None)(b)             # Mika's silhouette breathes smoke over every attack
                        self.say(self.texts.get("boss.ultra", "ULTRA TESSERACT. Time stops. +12 HP, a shield for two hits, and Noah loses half of this life."), "system")
                elif b.use_tesseract():
                    getattr(self.s, "tesseract_animation", lambda bb: None)(b)
                    self.say("[TEXT: boss.tesseract]", "system")
        else:
            self.say("[TEXT: boss.mercy.locked]", "system")
        if b.phase != before:
            self.on_phase(b.phase)
            getattr(self.s, "transition", lambda bb: None)(b)       # the beaten Noah is still what the screen shows (b.shown) ...
            b.shown = b.phase                                        # ... only now the next one appears
            self.s.blackout()
            self.piece("begin%d" % b.phase)
            if b.phase == 4:                                         # the fusion: the first time his voices use the player's name
                self.noah_says(self.talk.key_moment(4), blocking=True)
            self.say(self.phase_text(b.phase), b.who)
        self.pump()

    def enemy_turn(self):
        b = self.b
        b.shown = b.phase                                # (normally already so; a safety net for other ways into a new phase)
        self.message, self.msg_t = "", 0.0
        while b.state == "enemy":
            k = self.s.key(self.dt)
            moves = 0
            while k is not None and moves < 4:           # every key event is one step, even several per frame
                dx = {"left": -1, "a": -1, "right": 1, "d": 1}.get(k, 0)
                dy = {"up": -1, "w": -1, "down": 1, "s": 1}.get(k, 0)
                if dx or dy:
                    b.step(dx, dy)
                    moves += 1
                k = self.s.key(0)
            b.update(self.dt)
            for e in self.pump():
                if e[0] == "hit":
                    kind = "low" if b.hp <= boss_mod.PLAYER_HP * 0.3 else "hurt"
                    self.noah_says(self.talk.event(b.phase, kind))
            line = self.talk.tick(self.dt, b.phase)
            if line and b.freeze <= 0:
                self.noah_says(line)
            if self.msg_t > 0:
                self.msg_t -= self.dt
                if self.msg_t <= 0:
                    self.message = ""
            self.s.frame(b, self.message, b.who)


class CursesScreen:
    """Real terminal: arena, heart, words, HUD, menu. Needs a tty."""

    def __init__(self, stdscr):
        import curses
        self.c, self.scr = curses, stdscr
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        for n, col in ((1, curses.COLOR_GREEN), (2, curses.COLOR_YELLOW), (3, curses.COLOR_RED), (4, curses.COLOR_WHITE)):
            curses.init_pair(n, col, -1)
        self._flashed = False
        self._trail = []
        self._hist, self._hist_t = [], 0.0
        self.pair = {"noah": 1, "noah2": 2, "noah3": 3, "system": 4}
        self._upairs = {}
        self._apairs = {}
        self._b = None
        self.lay = None
        self._react = None                                        # (state, started) for one-shot Noah animations
        self.sfx = lambda name: None                              # set by Fight
        self.rich = curses.COLORS >= 256 and getattr(curses, "COLOR_PAIRS", 0) > 100

    def _attr(self, who, bold=False):
        return self.c.color_pair(self.pair.get(who, 4)) | (self.c.A_BOLD if bold else 0)

    def _ucolor(self, col):
        """Cinematic palette index -> curses attribute (256 colours when the terminal has them)."""
        a = self._upairs.get(col)
        if a is None:
            n = 20 + col
            name, rgb, c8, c256 = ultra_fx.PALETTE[col]
            self.c.init_pair(n, c256 if self.c.COLORS >= 256 else c8, -1)
            a = self._upairs[col] = self.c.color_pair(n) | self.c.A_BOLD
        return a

    def _aattr(self, kind, fgt, bgt):
        """Attribute for Noah's art: foreground and background are tones (0..5) of the personality colour, so every cell is solid."""
        key = (kind, fgt, bgt)
        a = self._apairs.get(key)
        if a is None:
            if self.rich:
                n = 40 + len(self._apairs)
                self.c.init_pair(n, portraits._256(*portraits.tone_rgb(kind, fgt)), portraits._256(*portraits.tone_rgb(kind, bgt)) if bgt else -1)
                a = self.c.color_pair(n) | (self.c.A_BOLD if fgt >= 5 else 0)
            else:
                a = self._attr({"green": "noah", "yellow": "noah2"}.get(kind, "noah3"), fgt >= 4) | (self.c.A_DIM if fgt <= 1 else 0)
            self._apairs[key] = a
        return a

    def react(self, name):
        self._react = (name, time.monotonic())

    def _noah_state(self, b, now):
        """(state, frame index) for Noah's animation: one-shots first, then what the fight is doing right now."""
        if b.state in ("mercy", "won"):
            return "collapse", portraits.frame_count(portraits.KINDS[b.shown - 1], "collapse") - 1
        if self._react:
            name, t0 = self._react
            i = int((now - t0) * 6)
            if i < 3:
                return name, i
            self._react = None
        if b.state == "enemy":
            live = [h for h in b.hazards if h.harmful and h.age - h.warn < 0.7] or [w for w in b.walls if b.WALL_WARN <= w["age"] < b.WALL_WARN + 0.45]
            if live:
                return "strike", int(now * 8) % 3
            warn = [h.age / max(0.1, h.warn) for h in b.hazards if h.age < h.warn] + [w["age"] / b.WALL_WARN for w in b.walls if w["age"] < b.WALL_WARN]
            if warn:
                return "windup", min(2, int(max(warn) * 3))
        if b.state in ("enemy", "player") and b.hp_ratio < 0.3:      # his expression gives way: now and then he flinches (more when he is nearly done)
            period = now % 3.0
            if period < (1.6 if b.hp_ratio < 0.15 else 0.7):
                return "hurt", int(period * 4) % 3
        return "idle", int(now * 7) % 8

    def _draw_art(self, fr, kind, x0, y0):
        for r, (row, fg, bg) in enumerate(zip(fr["rows"], fr["fg"], fr["bg"])):
            n, x = len(row), 0
            while x < n:
                solid = self.rich and bg[x] != "0"
                if row[x] == " " and not solid:
                    x += 1
                    continue
                k = portraits.band(kind, x, n)
                y = x
                while y < n and fg[y] == fg[x] and bg[y] == bg[x] and portraits.band(kind, y, n) == k and (row[y] != " " or solid):
                    y += 1
                self.put(y0 + r, x0 + x, row[x:y], self._aattr(k, int(fg[x]), int(bg[x])))
                x = y

    def key(self, timeout):
        self.scr.timeout(int(timeout * 1000))
        k = self.scr.getch()
        names = {self.c.KEY_UP: "up", self.c.KEY_DOWN: "down", self.c.KEY_LEFT: "left", self.c.KEY_RIGHT: "right",
                 10: "enter", 13: "enter", 27: "esc"}
        if k == -1:
            return None
        return names.get(k) or (chr(k) if 0 <= k < 256 else None)

    def put(self, y, x, text, attr=0):
        h, w = self.scr.getmaxyx()
        if 0 <= y < h and x < w and text:
            if x < 0:
                text, x = text[-x:], 0
            try:
                self.scr.addnstr(y, x, text, max(0, w - x - 1), attr)
            except self.c.error:
                pass

    def frame(self, b, message, who, menu=None, pos=0, bar=None):
        scr, c = self.scr, self.c
        scr.erase()
        h, w = scr.getmaxyx()
        k = min(1.0, b.fx["shake"] + (0.5 if b.shake else 0.0))
        sx = int(random.uniform(-3, 3) * k)                       # the WHOLE screen jumps, not only the arena
        sy = int(random.uniform(-1.4, 1.4) * k)
        if b.fx["flash"] > 0.08 and not self._flashed:
            self._flashed = True
            c.flash()
        elif b.fx["flash"] <= 0:
            self._flashed = False
        self._b = b
        self.lay = lay = portraits.fight_layout(w, h)
        ox = max(0, (w - (boss_mod.W + 2)) // 2) + sx
        face = face_for(b.who, b.hp_ratio)
        edge = self._attr(b.who, True) | (c.A_REVERSE if b.fx["flash"] > 0.1 else 0)
        now = time.monotonic()
        for ax, ay, ach in fx.ambient(b.shown, now, w, h, rng_seed=b.shown):          # petals / rain / veins around the arena
            in_art = lay and lay["x"] - 1 <= ax <= lay["x"] + lay["w"] and lay["y"] <= ay <= lay["y"] + lay["h"]
            if not in_art and not (ox <= ax <= ox + boss_mod.W + 2 and 1 <= ay <= boss_mod.H + 10):
                self.put(ay, ax, ach, self._attr(b.who))
        if lay:
            kind = portraits.KINDS[b.shown - 1]
            st, i = self._noah_state(b, now)
            fr = portraits.anim_frame(kind, st, i, lay["size"])
            if fr:
                self._draw_art(fr, kind, lay["x"] + sx, lay["y"] + sy)
                cr = b.cracks if b.shown == b.phase else 5                  # big hits crack the picture (a beaten Noah is cracked all over)
                if cr:
                    for k, (cx, cy, cch, _c) in enumerate(setpieces._cracks(lay["w"], lay["h"], min(1.0, 0.22 * cr), seed=b.shown * 7)):
                        gx, gy = lay["x"] + cx + sx, lay["y"] + cy + sy                # pale ice lines with a faint glow: never red
                        self.put(gy, gx + 1, "\u2591", self._ucolor(ultra_fx.BLUE))
                        self.put(gy, gx, cch, self._ucolor(ultra_fx.WHITE if k % 3 else ultra_fx.CYAN))
        head = "NOAH %s   phase %d/4   HP %s" % (face, b.shown, "#" * max(0, b.hp_shown // 2))
        if b.shown >= 3 and random.random() < 0.06:                                  # the HUD forgets itself for a moment
            head = fx.glitch_text(head, random, 0.3)
        self.put(0 + sy, ox, head, self._attr(b.who, True))
        top = 2 + sy
        if b.shown >= 3 and random.random() < 0.04:                                  # the arena flickers its border
            edge = self._attr("noah2", True)
        hbar = "=" if b.arc in ("climax", "rage", "trinity") else "-"       # the border says what kind of turn this is
        if b.rage_turn:
            edge |= c.A_REVERSE
        self.put(top, ox, "+" + hbar * boss_mod.W + "+", edge)
        for y in range(boss_mod.H):
            self.put(top + 1 + y, ox, "|" + " " * boss_mod.W + "|", self._attr(b.who))
        self.put(top + boss_mod.H + 1, ox, "+" + hbar * boss_mod.W + "+", edge)
        if b.gravity and b.state == "enemy":                                  # gravity: arrows along both walls show which way it pulls
            for y in range(boss_mod.H):
                if (y + int(now * 6 * b.gravity)) % 3 == 0:
                    for xx in (ox, ox + boss_mod.W + 1):
                        self.put(top + 1 + y, xx, "v" if b.gravity > 0 else "^", self._attr("noah2", True))
        if b.dark > 0 and b.state == "enemy":                                 # the lights are out: only a small circle round the heart is lit
            for y in range(boss_mod.H):
                run = "".join(" " if lit(b, x, y) else "\u2591" for x in range(boss_mod.W))
                self.put(top + 1 + y, ox + 1, run, self._attr(b.who))
        if b.state in ("enemy", "player"):
            for wl in b.walls:                                    # telegraphed sweeping rows with a gap
                row = top + 1 + wl["y"]
                if wl["age"] < b.WALL_WARN:
                    if int(wl["age"] * 12) % 2:
                        self.put(row, ox + 1, "!" * boss_mod.W, self._attr("noah2", True))
                else:
                    cells = "".join(" " if abs(i - wl["gap"]) <= b.GAP else "\u2593" for i in range(boss_mod.W))
                    self.put(row, ox + 1, cells, self._attr("noah3", True))
            for hz in b.hazards:                                  # themed patterns: blinking ghost first, then the real thing
                if hz.age < hz.warn:
                    if int(hz.age * 10) % 2 or hz.warn - hz.age < 0.25:
                        for x, y, ch in hz.ghost():
                            self.put(top + 1 + y, ox + 1 + x, ch, self._attr("noah2", True))
                else:
                    for x, y, ch in hz.cells():
                        if not lit(b, x, y):
                            continue
                        self.put(top + 1 + y, ox + 1 + x, ch, self._attr("noah3" if b.shown >= 3 else b.who, True) | (c.A_REVERSE if ch in "\u2593\u2720^" else 0))
            for bl in b.bullets:
                x, y = int(round(bl.x)), int(round(bl.y))
                if 0 <= y < boss_mod.H and lit(b, x, y):
                    for i, ch in enumerate(bl.text):
                        if 0 <= x + i < boss_mod.W:
                            self.put(top + 1 + y, ox + 1 + x + i, ch, self._attr("noah3" if bl.home else b.who, True))
            frozen = b.freeze > 0
            if not frozen and now - self._hist_t > 0.09:                           # a short memory of the attacks, for the ghost images
                self._hist_t = now
                self._hist = (self._hist + [b.snapshot()])[-6:]
            if frozen:                                                             # time is stopped: the attacks leave ghost images behind them
                for gx, gy, gch, gcol in ultra_bonus.ghost_layers(self._hist):
                    if 0 <= gx < boss_mod.W and 0 <= gy < boss_mod.H:
                        self.put(top + 1 + gy, ox + 1 + gx, gch, self._ucolor(gcol))
            self._trail = (self._trail + [(b.hx, b.hy)])[-(16 if frozen else 4):]   # while time is stopped the heart draws a long trail
            for i, (tx, ty) in enumerate(self._trail[:-1]):                         # afterimages of the heart
                self.put(top + 1 + int(ty), ox + 1 + int(tx), "\u00b7" if i < len(self._trail) - 3 else "\u2022", self._attr("noah3"))
            blink = b.invuln > 0 and b.freeze <= 0 and int(time.monotonic() * 10) % 2
            if not blink:
                self.put(top + 1 + int(b.hy), ox + 1 + int(b.hx), "\u2665", self._attr("noah3", True) | c.A_REVERSE)
        extra = ("  SHIELD x%d" % b.shield if b.shield else "") + ("  [honey: slow]" if b.slow > 0 else "") + ("  [time stopped %.1f]" % b.freeze if b.freeze > 0 else "")
        self.put(top + boss_mod.H + 3, ox, "YOU  HP %2d/%d  %s%s" % (b.hp, boss_mod.PLAYER_HP, "#" * b.hp, extra), self._attr("system", True))
        if message:
            self.put(top + boss_mod.H + 5, ox, message[: max(0, w - ox - 1)], self._attr(who))
        if bar is not None:
            n = 31
            row = ["-"] * n
            row[n // 2] = "0"
            row[int(bar * (n - 1))] = "O"
            self.put(top + boss_mod.H + 6, ox, "[" + "".join(row) + "]  %+d" % boss_mod.offset(bar), self._attr("system", True))
        if menu:
            for i, o in enumerate(menu):
                self.put(top + boss_mod.H + 7 + i, ox, ("> " if i == pos else "  ") + o, self._attr(b.who, i == pos))
        scr.refresh()

    def tesseract_animation(self, b):
        """The cube: a rotating 4D hypercube grows over the whole screen, rings expand, the screen flashes white and really shakes
        (every cell jumps, and the window too where the terminal allows it)."""
        h, w = self.scr.getmaxyx()
        frames = 46
        quakes, tremor = ((1.0, 0.7, 0.5), (2.0, 0.4, 0.4)), (0.2, 1.0, 0.0, 0.3)
        ws = ultra_fx.WindowShake()
        shaking = ws.start()
        self.c.flash()
        try:
            for f in range(frames):
                self.scr.erase()
                t = f / 14.0
                a = ultra_fx.shake_amp(f * 0.055, quakes, tremor)
                dx, dy = ultra_fx.shake_offset(f * 0.055, a)

                def put(y, x, text, attr=0, dx=dx, dy=dy):
                    self.put(y + dy, x + dx, text, attr)
                grow = min(1.0, f / 14.0) if f < frames - 8 else max(0.0, (frames - f) / 8.0)
                for x, y, lv in fx.tesseract_points(t, w - 2, h - 2, grow=0.2 + 0.8 * grow):
                    col = ("noah2", "system", "noah3")[lv] if f % 6 < 3 else ("system", "noah", "noah2")[lv]
                    put(y, x, "@%#"[lv], self._attr(col, True))
                for r in range(3):                                  # shock rings
                    rad = (f * 2 + r * 9) % 60
                    for k in range(0, 360, 6):
                        px, py = int(w / 2 + math.cos(math.radians(k)) * rad * 2), int(h / 2 + math.sin(math.radians(k)) * rad)
                        put(py, px, "." if r else "o", self._attr("system"))
                if f > frames - 12:
                    for y in range(0, h - 1, 2):
                        put(y, 0, "\u2593" * (w - 1), self._attr("system", True))
                self.scr.refresh()
                if shaking:
                    ws.move(*ultra_fx.window_offset(f * 0.055, a))
                self.c.napms(55)
        finally:
            ws.stop()
        self.c.flash()

    def _capture(self, b):
        """What is on the screen right now as cinematic cells (runs of one colour per row), so the blast can tear the real screen apart."""
        h, w = self.scr.getmaxyx()
        names = {1: ultra_fx.GREEN, 2: ultra_fx.YELLOW, 3: ultra_fx.RED, 4: ultra_fx.WHITE}
        dflt = {1: ultra_fx.GREEN, 2: ultra_fx.YELLOW}.get(b.shown, ultra_fx.RED)
        cells = []
        for y in range(h - 1):
            run, x0, col = "", 0, None
            for x in range(w - 1):
                v = self.scr.inch(y, x)
                ch = v & self.c.A_CHARTEXT
                g = chr(ch) if 32 < ch < 127 else (" " if ch in (0, 32) else "#")
                c = names.get(self.c.pair_number(v & self.c.A_COLOR), dflt)
                if g == " " or c != col:
                    if run:
                        cells.append((x0, y, run, col))
                    run, col = "", c
                if g != " ":
                    if not run:
                        x0 = x
                    run += g
            if run:
                cells.append((x0, y, run, col))
        return cells

    def _play(self, fn, seconds, flash_at=(), amp=None, sfx=(), art=None, kind=None, skip_after=1.2):
        """Run a pure cinematic (ultra_fx): fn(t, w, h) -> cells. Any key after 1.2 s skips it. amp(t) also shakes the real
        terminal window where xterm window ops work (opt out: FOLK_WINSHAKE=0); the window is always put back."""
        h, w = self.scr.getmaxyx()
        ws = ultra_fx.WindowShake()
        shaking = bool(amp) and ws.start()
        t0, flashed, heard = time.monotonic(), set(), set()
        if sfx or art:
            self.c.flushinp()                    # a key still in the buffer must not skip a set-piece
        try:
            while True:
                t = time.monotonic() - t0
                if t >= seconds:
                    break
                for f in flash_at:
                    if t >= f and f not in flashed:
                        flashed.add(f)
                        self.c.flash()
                self.scr.erase()
                for x, y, ch, col in fn(t, w - 1, h - 1):
                    self.put(y, x, ch, self._ucolor(col))
                for ts, name in sfx:
                    if t >= ts and ts not in heard:
                        heard.add(ts)
                        self.sfx(name)
                if art and kind and self.lay:
                    self._piece_art(art(t), kind, w, h, *(ultra_fx.shake_offset(t, amp(t)) if amp else (0, 0)))
                self.scr.refresh()
                if shaking:
                    ws.move(*ultra_fx.window_offset(t, amp(t)))
                k = self.key(0.02)
                if k and t > skip_after:
                    break
        finally:
            ws.stop()
        self.c.flash()

    def _overlay(self, cells, dx=0, dy=0):
        for x, y, ch, col in cells:
            self.put(y + dy, x + dx, ch, self._ucolor(col))

    def death(self, b):
        """The heart breaks (about 2 s): it trembles, splits in two halves that fall away, shards fly, the arena goes dark."""
        h, w = self.scr.getmaxyx()
        ox, top = max(0, (w - (boss_mod.W + 2)) // 2), 2
        hx, hy = ox + 1 + int(b.hx), top + 1 + int(b.hy)
        rng = random.Random(7)
        shards = [(rng.uniform(-16, 16), rng.uniform(-9, -1)) for _ in range(16)]
        self.c.flash()
        t0 = time.monotonic()
        while True:
            t = time.monotonic() - t0
            if t > 2.0:
                break
            self.frame(b, "", b.who)
            cells = []
            if t < 0.55:                                               # a held breath: the heart trembles
                cells.append((hx + (1 if int(t * 30) % 2 else 0), hy, "\u2665", ultra_fx.RED))
            else:
                u = t - 0.55
                cells += [(hx - 1 - int(u * 5), hy + int(14 * u * u), "\u2661", ultra_fx.RED), (hx + 1 + int(u * 5), hy + int(14 * u * u), "\u2661", ultra_fx.RED)]
                for vx, vy in shards:
                    cells.append((int(hx + vx * u * 1.6), int(hy + vy * u + 16 * u * u), ".", ultra_fx.RED if u < 0.9 else ultra_fx.GREY))
                if u > 0.9:                                            # the arena goes out
                    for y in range(boss_mod.H):
                        cells.append((ox + 1, top + 1 + y, "\u2591" * int(boss_mod.W * min(1.0, (u - 0.9) / 0.5)), ultra_fx.GREY))
            self._overlay(cells)
            self.scr.refresh()
            self.c.napms(33)
        self.c.flushinp()

    def confirm_leave(self):
        """Ctrl+C in the fight: really leave? True = leave. The fight is paused while the question is up."""
        h, w = self.scr.getmaxyx()
        msg = "  really leave the fight?   y = leave   n = stay  "
        x0, y0 = max(0, (w - len(msg)) // 2), h // 2
        self.put(y0 - 1, x0, "+" + "-" * len(msg) + "+", self._attr("system", True))
        self.put(y0, x0, "|" + msg + "|", self._attr("system", True) | self.c.A_REVERSE)
        self.put(y0 + 1, x0, "+" + "-" * len(msg) + "+", self._attr("system", True))
        self.scr.refresh()
        self.scr.timeout(-1)
        try:
            while True:
                try:
                    k = self.scr.getch()
                except KeyboardInterrupt:
                    return True                                         # a second Ctrl+C means it
                if k in (ord("y"), ord("Y")):
                    return True
                if k in (ord("n"), ord("N"), 27, 10, 13, ord(" ")):
                    return False
        finally:
            self.scr.timeout(0)
            self.c.flushinp()

    def ultra_beam(self, b):
        """ULTRA bonus: the cube fires a beam onto Noah's picture (ultra_bonus.beam); it flinches, shakes and cracks (b.cracks is already raised)."""
        h, w = self.scr.getmaxyx()
        lay = self.lay
        if not lay:
            return
        src, dst = (w // 2, 0), (lay["x"] + lay["w"] // 2, lay["y"] + lay["h"] // 2)
        t0, hit = time.monotonic(), False
        while True:
            t = time.monotonic() - t0
            if t >= ultra_bonus.BEAM_SECONDS:
                break
            if t >= 0.45 and not hit:
                hit = True
                self.c.flash()
                self.react("hurt")
            b.fx["shake"] = 0.9 if 0.45 <= t < 1.0 else 0.0
            self.frame(b, "", b.who)
            self._overlay(ultra_bonus.beam(t, src, dst))
            self.scr.refresh()
            self.c.napms(33)
        b.fx["shake"] = 0.0

    def ultra_mika(self, b):
        """ULTRA bonus: Mika's silhouette appears next to the arena, breathes out smoke, and the attacks that were on screen are gone where it passes."""
        h, w = self.scr.getmaxyx()
        ox, top = max(0, (w - (boss_mod.W + 2)) // 2), 2
        sil = (min(max(0, w - 14), ox + boss_mod.W + 6), top + 2)
        mouth_x = sil[0] + ultra_bonus.MOUTH[1]
        wiped = [(ox + 1 + x, top + 1 + y, ch) for x, y, ch in getattr(b, "wiped", [])]
        t0 = time.monotonic()
        while True:
            t = time.monotonic() - t0
            if t >= ultra_bonus.MIKA_SECONDS:
                break
            self.frame(b, "", b.who)
            self._overlay(ultra_bonus.mika(t, sil, wiped, lambda tt: ultra_bonus.front(mouth_x, tt)))
            self.scr.refresh()
            self.c.napms(33)

    def _piece_art(self, spec, kind, w, h, dx=0, dy=0):
        """Noah's picture in the middle of a set-piece (the rectangle behind it is cleared first)."""
        fr = portraits.anim_frame(kind, spec[0], spec[1], self.lay["size"])
        if not fr:
            return
        aw, ah = len(fr["rows"][0]), len(fr["rows"])
        x0, y0 = max(0, (w - aw) // 2) + dx, max(0, (h - ah) // 2 - 3) + dy
        for r in range(ah):
            self.put(y0 + r, x0, " " * aw)
        self._draw_art(fr, kind, x0, y0)

    def setpiece(self, b, name, text=""):
        """One of setpieces.PIECES: a silent beat, the hit, a title or a line; Noah's picture in front for the HP ones."""
        p = setpieces.get(name)
        phase = b.phase
        if name in ("thr50", "thr20") and self.scene_beat(name):                  # the 50% / 20% beats as a 3.5 s full-screen scene (cine_fx.Beat)
            return
        frame = (lambda t, w, h: p["frame"](t, w, h, text)) if name.startswith("begin") else (lambda t, w, h: p["frame"](t, w, h, text, phase))
        self._play(frame, p["seconds"], flash_at=p["flash"], amp=lambda t: setpieces.amp(name, t), sfx=p["sfx"], art=p["art"],
                   kind=portraits.KINDS[b.phase - 1], skip_after=2.2)

    def ultra_unlock_animation(self, b):
        self._play(ultra_fx.unlock_frame, ultra_fx.UNLOCK_SECONDS, flash_at=(6.6, 7.5), amp=ultra_fx.unlock_amp)

    def ultra_animation(self, b):
        h, w = self.scr.getmaxyx()
        scene = self._capture(b)
        self._play(lambda t, ww, hh: ultra_fx.use_frame(t, ww, hh, scene=scene, words=[x.text for x in b.bullets][:6] or ["tea?", "BURN", "kneel", "ASH", "mine", "sorry"]),
                   ultra_fx.USE_SECONDS, flash_at=(6.6, 6.8, 7.0, 7.35), amp=ultra_fx.use_amp)

    def scene_beat(self, name):
        """thr50 / thr20 as a scene on the raw terminal (like scene_transition); False = use the old set-piece."""
        if not sys.stdout.isatty():
            return False
        try:
            import curses
            import cine_fx
            import mika_ending
            curses.def_prog_mode()
            curses.endwin()
            try:
                cine_fx.run_named(mika_ending.Ctx(None, None), "beat" + name[3:])
            finally:
                curses.reset_prog_mode()
                self.scr.clear()
                self.scr.refresh()
            return True
        except Exception:
            return False

    def scene_transition(self, b):
        """A personality change as a full-screen ASCII scene (cine_fx.PhaseMerge, 3.8 s): curses is suspended, the scene runs on the raw terminal,
        curses comes back. Only on a real terminal; False = use the old glitch transition."""
        if not sys.stdout.isatty() or not 2 <= b.phase <= 4:
            return False
        try:
            import curses
            import cine_fx
            import mika_ending
            curses.def_prog_mode()
            curses.endwin()
            try:
                cine_fx.run_named(mika_ending.Ctx(None, None), "phase%d" % b.phase)
            finally:
                curses.reset_prog_mode()
                self.scr.clear()
                self.scr.refresh()
            return True
        except Exception:
            return False

    def transition(self, b):
        """A personality changes: the screen fills with glitch in its colour, flashes and shakes, then clears."""
        if self.scene_transition(b):
            return
        h, w = self.scr.getmaxyx()
        glyphs = "#%@&$?!/\\|+=<>"
        self.c.flash()
        for f in range(22):
            self.scr.erase()
            density = 0.05 + 0.5 * math.sin(f / 22 * math.pi)
            for y in range(h - 1):
                line = "".join(random.choice(glyphs) if random.random() < density else " " for _ in range(w - 1))
                self.put(y, 0, line, self._attr(b.who, True))
            if self.lay and b.phase >= 2:
                old, new = portraits.KINDS[b.phase - 2], portraits.KINDS[b.phase - 1]
                fr = portraits.morph_frame(old, new, f * 8 // 22, self.lay["size"])
                if fr:
                    for r in range(self.lay["h"] + 1):
                        self.put(self.lay["y"] + r, self.lay["x"], " " * self.lay["w"])
                    self._draw_art(fr, new if f * 8 // 22 >= 4 else old, self.lay["x"], self.lay["y"])
            self.scr.refresh()
            self.c.napms(40)
        self.c.flash()

    def say(self, text, who):
        """Wait while the message is read; Noah keeps animating (hurt flinch, idle) instead of freezing."""
        end = time.monotonic() + min(2.5, 0.6 + 0.025 * len(text))
        while time.monotonic() < end:
            if self._b is not None:
                self.frame(self._b, text, who)
            self.c.napms(50)

    def blackout(self, ms=600):
        self.scr.erase()
        self.scr.refresh()
        self.c.napms(ms)

    def menu(self, b, opts, message=""):
        pos = 0
        while True:
            self.frame(b, message, b.who, menu=opts, pos=pos)
            k = self.key(0.1)
            if k in ("up", "w"):
                pos = (pos - 1) % len(opts)
            elif k in ("down", "s"):
                pos = (pos + 1) % len(opts)
            elif k == "enter":
                return pos
            elif k and k.isdigit() and 1 <= int(k) <= len(opts):
                return int(k) - 1

    def timing_bar(self, b):
        t0, pos, d = time.monotonic(), 0.0, 1.0
        while True:
            t = (time.monotonic() - t0) * 1.4
            pos = abs((t % 2.0) - 1.0)
            self.frame(b, "", b.who, bar=pos)
            if self.key(0.02) == "enter":
                return boss_mod.timing_accuracy(pos)


def play(lines=None, power=0.0, seed=None, mixer=None, intro=True, out=None, has_tesseract=False, texts=None, ultra=False, phase=1, has=None):
    """Whole encounter in a real terminal. Returns 'won' or 'lost'."""
    import curses
    if intro:
        with ui.Keys() as keys:
            run_intro(out=out, mixer=mixer, keys=keys)
    b = boss_mod.Boss(seed=seed if seed is not None else int(time.time()), power=power, lines=lines, has_tesseract=has_tesseract, ultra=ultra, phase=phase)
    play.last = b                                        # story_game reads b.ultra_unused() after the fight

    def hook(n):
        if mixer is not None and n == 3:
            mixer.boss_phase_two()
    if mixer is not None and not intro:
        mixer.boss_phase_two()

    def go(stdscr):
        def end():
            if mixer is not None:
                import threading
                threading.Thread(target=mixer.fade_out, daemon=True).start()
        return Fight(b, CursesScreen(stdscr), on_phase=hook, texts=texts, on_end=end, has=has).run()
    return curses.wrapper(go)
