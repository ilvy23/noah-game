"""lyrics_fx.py - synced lyrics from a user-supplied standard .lrc file ([mm:ss.xx] text per line, times relative to the song FILE).

    parse_lrc(text)            -> sorted [(seconds, line)]   (tags like [ar:...] and unparsable lines are ignored)
    load(path)                 -> the same from a file; [] when the file is missing or unreadable (never raises)
    Layer(lines, start, ...)   .draw(cv, t): t = seconds since the scene started; the song position is start + t. Lines stack STANDING on the right
                               (right-aligned column, newest at the bottom, older ones dim and fade out). Pale colour, nothing when there is no file.
The game never contains lyrics: the file is supplied by the user (soundtracks/lyrics/noah-burns-song.lrc).
"""
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc(text):
    out = []
    for raw in text.splitlines():
        stamps = TAG.findall(raw)
        if not stamps:
            continue
        line = TAG.sub("", raw).strip()
        for m, s in stamps:
            out.append((int(m) * 60 + float(s), line))
    return sorted(out, key=lambda x: x[0])


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return parse_lrc(fh.read())
    except (OSError, ValueError):
        return []


class Offsets(list):
    """Per-word seconds after the line start; .ends = the seconds at which each word stops being sung, .kinds = 'main' or 'echo' for each word."""
    ends = None
    kinds = None


FATHER_PERIOD = 1.86                                  # the user's lrc: the four main 'Father' shouts are 1.86 s apart (140.93, 142.76, 144.63, 146.52 against the json's +0.27)
ECHO_AFTER = 1.0                                      # a quiet 'father' answers its main shout about 1 s later (audio: 142.2, 144.1, 145.9) and stops when the next main arrives


def load_json(path, from_s=140.0):
    """Word-timed lyrics from the user's own json (lines[{start_ms, words[{t, s, e}]}], start/end of every word in ms), CORRECTED where it disagrees with the user's other
    sources and the audio: (1) the opening has FOUR main 'Father' shouts, each of the first three followed by a quiet echo 'father'; the json had the echo of the second as a
    main third word, no echoes of the first and third and no fourth main; (2) the long 'In' of the second long line starts at ~187.7 s (user lrc 187.45 + the
    json's offset), not at 189.47 where the json has a 0.09 s 'In'.
    Returns (lines, exact): lines = [(seconds, text)] from `from_s` on, exact = [Offsets]; ([], []) when the file is missing."""
    import json
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return [], []
    raw = []
    for ln in data.get("lines", []):
        ws = [(w["s"] / 1000.0, (w.get("e", w["s"]) / 1000.0), w["t"].strip(), "main") for w in ln.get("words", []) if w.get("t", "").strip()]
        if ws:
            raw.append(ws)
    for i, ws in enumerate(raw):
        if len(ws) == 4 and all(w[2].lower() == "father" for w in ws) and ws[0][0] >= from_s:             # (1) the four mains and their three echoes
            m1, m2, e2, m3 = ws[0][0], ws[1][0], ws[2][0], ws[3][0]
            m4 = m3 + FATHER_PERIOD
            ev = [(m1, "main"), (m1 + ECHO_AFTER, "echo"), (m2, "main"), (e2, "echo"), (m3, "main"), (m3 + ECHO_AFTER, "echo"), (m4, "main")]
            nxt = raw[i + 1][0][0] if i + 1 < len(raw) else m4 + 2.0
            out = []
            for k, (t0, kind) in enumerate(ev):
                t1 = ev[k + 1][0] if k + 1 < len(ev) else nxt - 0.3
                out.append((t0, min(t1, t0 + 0.9) if kind == "main" and k + 1 < len(ev) else t1, "Father" if kind == "main" else "father", kind))
            raw[i] = out
        if ws[0][2] == "In" and len(ws) > 3 and ws[0][1] - ws[0][0] < 0.3 and i > 0:                          # (2) the long 'In' before 'my self righteous suicide'
            start = raw[i - 1][-1][1] + 0.14
            raw[i] = [(start, ws[0][1], "In", "main")] + ws[1:]
    lines, exact = [], []
    for ws in raw:
        if ws[0][0] >= from_s:
            t0 = ws[0][0]
            off = Offsets(t - t0 for t, _, _, _ in ws)
            off.ends = [e - t0 for _, e, _, _ in ws]
            off.kinds = [k for _, _, _, k in ws]
            lines.append((t0, " ".join(w for _, _, w, _ in ws)))
            exact.append(off)
    return lines, exact


def load_words(path):
    """Optional hand-made word times: one word per line, `[mm:ss.xx] word` or `ss.xx word` (seconds in the song file), in the order of the lyrics.
    Returns [(seconds, word)] or [] when the file is missing. # starts a comment."""
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.split("#", 1)[0].strip()
                m = re.match(r"\[?(?:(\d+):)?(\d+(?:\.\d+)?)\]?\s+(\S.*)$", raw)
                if m:
                    out.append((int(m.group(1) or 0) * 60 + float(m.group(2)), m.group(3).strip()))
    except OSError:
        return []
    return out


def default_path(name="noah-burns-song"):
    return os.path.join(HERE, "soundtracks", "lyrics", name + ".lrc")


class Layer:
    """Draws the lines whose time has come. keep = how many stay on screen, life = seconds until a line has faded out."""

    def __init__(self, lines, start=0.0, keep=9, life=11.0, bottom=6):
        self.lines, self.start, self.keep, self.life, self.bottom = lines or [], start, keep, life, bottom

    def visible(self, t):
        """[(age_seconds, text)] oldest first, for the scene time t."""
        pos = self.start + t
        shown = [(pos - ts, text) for ts, text in self.lines if 0 <= pos - ts < self.life and text]
        return shown[-self.keep:]

    def draw(self, cv, t):
        vis = self.visible(t)
        y = cv.h - 1 - self.bottom
        for age, text in reversed(vis):                                  # newest at the bottom, older ones stand above it
            k = 1.0 if age < 3.0 else max(0.0, 1.0 - (age - 3.0) / (self.life - 3.0))
            fade_in = min(1.0, age / 0.4)
            c = (int(205 * k * fade_in + 18), int(222 * k * fade_in + 18), int(255 * k * fade_in + 24))
            x = cv.w - 3 - len(text)
            if y < 0:
                break
            for i, ch in enumerate(text):
                if ch != " " and 0 <= x + i < cv.w:
                    cv.put(x + i, y, ch, c)
            y -= 1


class BigLayer:
    """The lyrics from the first 'Father' on, EVERY word, as big blood-red lettering (lettering.py) that reads at a glance.
    Words come on pages (the free area left and right of Noah; on a narrow terminal two full-width bands): a phrase is kept together, a page that is full flips to the other
    one (the old words there burn away, but never before they have been fully visible for 0.7 s). Every word lands on its own beat. In the opening the four MAIN 'Father' shouts
    are big, each of the first three is followed by a small ghosted echo that burns away when the next main hits. Held or screamed words (sung longer than 0.7 s) stretch while
    they are sung, tremble harder and glow, a long 'I' also grows tall, and a shock ring leaves them when the note ends. draw() returns the jolt (dx, dy) of the hits."""
    FROM = "father"
    LAND_VISIBLE = 0.7                  # seconds a word stays fully readable after it lands, whatever happens to its page
    LINGER = 3.4                        # seconds after the last word of a line lands that the line burns away by itself
    BURN = 0.9
    HOLD_MIN = 0.7                      # a word sung longer than this counts as held

    def __init__(self, lines, start=0.0, hold=6.5, colour=(176, 8, 12), words=None, exact=None):
        lines = [(ts, tx) for ts, tx in (lines or []) if tx]
        for i, (_, tx) in enumerate(lines):
            if tx.lower().startswith(self.FROM):
                lines = lines[i:]
                break
        self.exact = {}                                  # line index -> seconds after the line start of each word
        if words:
            pos = 0
            for i, (ts, tx) in enumerate(lines):
                n = len(tx.split())
                if pos + n > len(words):
                    break
                got = [w[0] for w in words[pos:pos + n]]
                pos += n
                lines[i] = (min(ts, got[0]), tx)
                self.exact[i] = [max(0.0, g - lines[i][0]) for g in got]
        if exact:
            self.exact = {i: e for i, e in enumerate(exact[:len(lines)])}
        self.lines = lines
        self.start, self.hold, self.colour = start, hold, colour
        self._rng = __import__("random").Random(11)
        self._plans, self._sparks, self._done, self._t = {}, [], set(), None
        self.words = self._flatten()

    # -- the words of all lines in song time
    def _flatten(self):
        out = []
        for i, (ts, tx) in enumerate(self.lines):
            toks = tx.split()
            offs = self.exact.get(i)
            if offs is None:
                nxt = self.lines[i + 1][0] if i + 1 < len(self.lines) else ts + 4.0
                span = max(0.5, min(nxt - ts, self.hold) * 0.72)
                wts = [len(w) + 2 for w in toks]
                tot, acc, offs = float(sum(wts)), 0.0, []
                for w in wts:
                    offs.append(span * acc / tot)
                    acc += w
            ends = getattr(offs, "ends", None)
            kinds = getattr(offs, "kinds", None)
            for k, w in enumerate(toks):
                s_ = ts + offs[k]
                e_ = ts + (ends[k] if ends else (offs[k + 1] if k + 1 < len(offs) else offs[k] + 0.6))
                out.append(dict(line=i, k=k, text=w, s=s_, e=max(e_, s_ + 0.1), kind=(kinds[k] if kinds else "main"), n=len(toks)))
        return out

    def is_climax(self, i):
        return self.lines[i][1].lower().startswith("father into your hands i commend")

    # -- the plan: where every word stands on which page, when it lands and when it burns
    def plan(self, w, h, zones):
        import lettering
        key = (w, h, tuple(tuple(z) for z in zones))
        if key in self._plans:
            return self._plans[key]
        top, bottom = 1, h - 6                                                             # the bottom rows belong to the captions
        wide = w >= 160 and len(zones) >= 2
        if wide:
            pages = [dict(x0=max(1, z[0]), x1=min(w - 1, z[2]), y0=top, y1=bottom) for z in zones[:2]]
        else:
            mid = (top + 3 + bottom) // 2
            pages = [dict(x0=2, x1=w - 2, y0=top + 3, y1=mid - 1), dict(x0=2, x1=w - 2, y0=mid, y1=bottom)]
        toks = [x["text"] for x in self.words]
        widest = max(lettering.measure(t, 1.0) for t in toks) if toks else 100
        pw = pages[0]["x1"] - pages[0]["x0"]
        smax = 0.66 if wide else 0.5
        s = max(0.34, min(smax, 0.97 * pw / float(widest)))
        row_h = int(round((lettering.BOT - lettering.TOP) * s / 2.0)) + 2
        for p in pages:
            p["rows"] = max(1, (p["y1"] - p["y0"] + 1) // row_h)
            p["row_h"] = row_h
        placed, cur = [], 0
        state = [dict(row=-1, x=None, items=[], scale=s) for _ in pages]
        def wmeasure(wd, sc):
            base = lettering.measure(wd["text"], sc)
            held = wd["e"] - wd["s"] > self.HOLD_MIN and wd["kind"] == "main"
            return base, held
        def clear(pi, when):
            for it in state[pi]["items"]:
                it["burn"] = min(it["burn"], max(when, it["land"] + self.LAND_VISIBLE))
            state[pi].update(row=-1, x=None, items=[])
        def new_row(pi, when=0.0):
            st = state[pi]
            if wide and st["row"] + 1 >= pages[pi]["rows"] and st["items"]:             # the page is full: it scrolls up one row, the top row burns away
                keep = []
                for it_ in st["items"]:
                    if it_["row"] == 0:
                        it_["burn"] = min(it_["burn"], max(when, it_["land"] + self.LAND_VISIBLE))
                    else:
                        it_["row"] -= 1
                        it_["moves"].append((when, pages[pi]["row_h"]))
                        keep.append(it_)
                st["items"] = keep
                st["x"] = pages[pi]["x0"]
                return True
            st["row"] += 1
            st["x"] = pages[pi]["x0"]
            return st["row"] < pages[pi]["rows"]
        def choose_page(line_words, when, prefer):
            """The page for a line: the other one if it can show the line's widest word at >= 0.45 (shrunk to fit if need be), else this one again."""
            wmax = max(lettering.measure(lw["text"], 1.0) for lw in line_words if lw["kind"] == "main")
            best = prefer
            for cand in ((prefer + 1) % len(pages), prefer):
                pw_ = pages[cand]["x1"] - pages[cand]["x0"]
                fit = min(s, 0.97 * pw_ / float(wmax))
                if fit >= (0.58 if wide else 0.3) or cand == prefer:
                    best = cand
                    state[cand]["scale"] = max(fit, 0.34) if fit < s else s
                    break
            clear(best, when)
            return best
        gap = max(5, int(round(18 * s)))
        li_prev = -1
        for wd in self.words:
            scale = state[cur]["scale"] * (0.5 if wd["kind"] == "echo" else 1.0)
            wm, held = wmeasure(wd, scale)
            new_line = wd["line"] != li_prev
            if new_line:
                li_prev = wd["line"]
                # the phrase should fit on the page it starts on: estimate its rows from here
                line_words = [x for x in self.words if x["line"] == wd["line"]]
                need, xx = 1, 0
                width = pages[cur]["x1"] - pages[cur]["x0"]
                for lw in line_words:
                    m_, _ = wmeasure(lw, s * (0.5 if lw["kind"] == "echo" else 1.0))
                    if lw["kind"] == "main" and lw["k"] > 0 and wd["line"] == 0:
                        need, xx = need + 1, 0
                    if xx and xx + gap + m_ > width:
                        need, xx = need + 1, 0
                    xx += (gap if xx else 0) + m_
                left = pages[cur]["rows"] - (state[cur]["row"] + 1)
                if state[cur]["row"] >= 0 and left < min(need, pages[cur]["rows"]):
                    other_ok = (not wide) or min(s, 0.97 * (pages[(cur + 1) % len(pages)]["x1"] - pages[(cur + 1) % len(pages)]["x0"]) / float(max(lettering.measure(lw["text"], 1.0) for lw in line_words if lw["kind"] == "main"))) >= 0.58
                    if other_ok:
                        cur = choose_page(line_words, wd["s"], cur)
                state[cur]["x"] = None                                                   # a new line starts a new row
            pi = cur
            st, pg = state[pi], pages[pi]
            if st["row"] < 0:
                new_row(pi, wd["s"])
            width_ok = lambda x_: x_ + wm <= pg["x1"] + 1
            force = wd["kind"] == "main" and wd["line"] == 0 and wd["k"] > 0
            if st["x"] is None or force or not width_ok(st["x"]):
                if st["x"] is not None or force:
                    pass
                if not new_row(pi, wd["s"]):
                    cur = pi = choose_page([x for x in self.words if x["line"] == wd["line"]], wd["s"], pi)
                    st, pg = state[pi], pages[pi]
                    new_row(pi, wd["s"])
            if wd["kind"] == "echo" and st["x"] is not None and st["x"] + wm > pg["x1"] + 1:
                if not new_row(pi, wd["s"]):
                    clear(pi, wd["s"])
                    new_row(pi, wd["s"])
            x_slot = st["x"]
            y = pg["y0"] + st["row"] * pg["row_h"]
            it = dict(word=wd, page=pi, x=x_slot, slot=wm, y=y, scale=scale, land=wd["s"], held=held, burn=1e9, ghost=0.55 if wd["kind"] == "echo" else 1.0, row=st["row"], moves=[])
            placed.append(it)
            st["items"].append(it)
            st["x"] = x_slot + wm + gap
        # lines burn away by themselves some seconds after their last word; echoes when the next main shout hits
        by_line = {}
        for it in placed:
            by_line.setdefault(it["word"]["line"], []).append(it)
        for li, its in by_line.items():
            last = max(max(i["land"] for i in its), max(i["word"]["e"] for i in its) - 1.0)
            for i in its:
                i["burn"] = min(i["burn"], max(last + self.LINGER, i["land"] + self.LAND_VISIBLE))
        for k, it in enumerate(placed):
            if it["word"]["kind"] == "echo":
                nxt = next((o for o in placed[k + 1:] if o["word"]["kind"] == "main"), None)
                if nxt is not None:
                    it["burn"] = min(it["burn"], max(nxt["land"], it["land"] + self.LAND_VISIBLE))
        self._plans[key] = placed
        return placed

    def draw(self, cv, t, zones):
        import lettering
        import noah_gore_fx as G
        if not zones or not lettering.has():
            return (0, 0)
        dt = max(0.0, min(0.2, t - self._t)) if self._t is not None else 0.0
        self._t = t
        pos = self.start + t
        jolt, flash_k = 0.0, 0.0
        sparks = self._sparks
        for it in self.plan(cv.w, cv.h, zones):
            wd = it["word"]
            wa = pos - it["land"]
            if wa < 0:
                continue
            burn = (pos - it["burn"]) / self.BURN
            if burn >= 1.0:
                continue
            main = wd["kind"] == "main"
            climax = self.is_climax(wd["line"])
            last = climax and wd["k"] == wd["n"] - 1
            power = (1.0 + (0.9 if climax else 0.0) + (0.6 if last else 0.0)) if main else 0.4
            if main and wa < 0.14 * power:
                jolt = max(jolt, (1.0 - wa / (0.14 * power)) * (1.0 + (1.2 if climax else 0.0) + (1.0 if last else 0.0)))
                flash_k = max(flash_k, 0.16 * (1.0 - wa / (0.14 * power)))
            if last and wa < 0.25:
                G.flash(cv, (255, 244, 230), 0.55 * (1.0 - wa / 0.25))                       # 'spirit': the short white flash
            hold = 0.0                                                                       # no stretching: held words keep their shape (owner's call)
            wobj = lettering.get(wd["text"], it["scale"])
            xd = it["x"] + (it["slot"] - wobj.w) // 2
            if wa < 0.5 and main:
                G.glow(cv, xd + wobj.w // 2, it["y"] + wobj.h // 4, max(6, wobj.w // 2), max(3, wobj.h // 4), (230, 20, 12), 0.35 * (1.0 - wa / 0.5) * power)
            ydraw = it["y"] - sum(dy * min(1.0, max(0.0, (pos - tm) / 0.3)) for tm, dy in it["moves"])
            lettering.draw(cv, wobj, xd, int(round(ydraw)), wa, t, max(0.0, burn), 1.0 if wa > 0.12 else wa / 0.12, power, sparks, hold, it["ghost"])
            if burn < 0.0 and wa > 1.0 and main and self._rng.random() < 0.03:             # embers rise off the lettering now and then
                sparks.append([xd + self._rng.randrange(max(1, wobj.w)), 2 * it["y"] + 6, self._rng.uniform(-2, 2), -self._rng.uniform(4, 9), 0.0, self._rng.uniform(0.6, 1.3)])
        lettering.step_sparks(cv, sparks, dt)
        if flash_k > 0.01:
            G.flash(cv, (255, 40, 30), flash_k)
        a = 2.4 * jolt
        return (int(round(self._rng.uniform(-a, a) * 2.0)), int(round(self._rng.uniform(-a, a) * 0.6))) if a > 0.3 else (0, 0)


def _h(a, b, c):
    return ((a * 73856093) ^ (b * 19349663) ^ (c * 83492791)) & 0xFFFF
