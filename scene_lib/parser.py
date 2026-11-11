"""scene_lib/parser.py - story text -> beats of an animated scene.

The story texts are prose with 'quoted speech'; the design notes also allow screenplay form. parse(text, main=[...]) understands both:
    'speech' (single or double quotes)      -> a speech beat of the speaker found next to it (name / he / she / you), else the last speaker, else the scene's main figure
    NAME: speech                            -> a speech beat of NAME
    (action in brackets, own line)          -> an action beat
    - Later -                               -> a time-jump card (fade, title)
    every other sentence                    -> narration: a caption strip; its verbs (verbs.VERBS) become ACTIONS of the figure named before the verb
A pure attribution ("he says.") is dropped because the bubble's name tag says it. Nothing else is ever dropped or reworded.
Unknown narration gets the subtle fallback: a small gesture of the last actor and a camera push-in (Beat.push), never just bare text.
"""
import re

from .verbs import VERBS, WORLD

KNOWN = {"noah": "noah", "mika": "mika", "connor": "connor"}
ALIAS = [(r"\b(?:the )?(?:boy|kid|kid with the scarf)\b", "noah"), (r"\b(?:the )?(?:priest|pastor|old man|teacher)\b", "connor")]
NAME_RE = re.compile(r"\b(Mika|Noah|Connor)\b")
PRON_RE = re.compile(r"\b(you|your|yours|yourself|he|him|his|she|her)\b", re.I)
QUOTE_RE = re.compile(r"(?:(?<=\s)|^|(?<=[(\[—-]))(?:'(.{2,}?)'|\"(.{2,}?)\")(?=[\s.,!?;:)\]—-]|$)", re.S)
CARD_RE = re.compile(r"^\s*[—–-]{1,3}\s*(.+?)\s*[—–-]{1,3}\s*$")
SCRIPT_RE = re.compile(r"^([A-Za-z]{2,12}):\s+(.+)$")
PAREN_RE = re.compile(r"^\(([^)]+)\)\s*$")
TAG_RE = re.compile(r"^[,.;:\s]*(?:(?:he|she|they|you|[A-Z][a-z]+)\s+)?(?:says?|said|asks?|asked|whispers?|adds?|replies|murmurs?|answers?|continues?|mutters?|calls?|laughs?)"
                    r"(?:\s+(?:he|she|[A-Z][a-z]+))?(?:\s+(?:softly|quietly|lightly|calmly|kindly|gently|slowly|flatly|simply|easily|warmly|finally|again|then))?[.,:;!?\s]*$")
SAYS = re.compile(r"\b(?:says?|said|asks?|asked|whispers?|adds?|replies|murmurs?|answers?|continues?|mutters?|calls?|laughs?)\b")
SHOCK_RE = re.compile(r"\b[A-Z]{4,}\b|!{2,}|\b[A-Z]{3,}!")
EXTRA = [(r"\bwoman\b", "woman"), (r"\bman with the dog\b|\bman\b", "stranger"), (r"\bgirl\b|\bchild\b|\bkid\b", "child")]
LIMIT = 170


class Beat:
    def __init__(self, kind, text, who=None, acts=None, push=False, shock=False):
        self.kind, self.text, self.who = kind, text, who
        self.acts = acts or []                 # (actor, action, delay seconds)
        self.push, self.shock = push, shock

    def __repr__(self):
        return "Beat(%s, %r, %r, %r)" % (self.kind, self.who, self.text[:40], self.acts)


def sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+(?=[A-Z'\"(—])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def shock(text):
    return bool(SHOCK_RE.search(text))


def chunk(text, limit=LIMIT):
    """Whole sentences up to `limit` characters per piece (a longer single sentence is cut at a comma or a space)."""
    out, cur = [], ""
    for s in sentences(text) or [text]:
        while len(s) > limit * 1.4:
            cut = max(s.rfind(", ", 0, limit), s.rfind(" ", 0, limit)) or limit
            out.append((cur + " " + s[:cut + 1]).strip() if cur else s[:cut + 1].strip())
            cur, s = "", s[cut + 1:].strip()
        if cur and len(cur) + len(s) + 1 > limit:
            out.append(cur)
            cur = ""
        cur = (cur + " " + s).strip()
    return out + ([cur] if cur else [])


class Parser:
    def __init__(self, main=(), you=True):
        self.main = list(main)
        self.cast = list(self.main)
        self.last = self.main[0] if self.main else None        # the last actor named / speaking (what "he" means)
        self.speaker = None
        self.you = you
        self.n = 0

    # ---------------------------------------------------------------- actors
    def add(self, who):
        if who and who not in self.cast:
            self.cast.append(who)

    def mentions(self, s):
        """[(position, actor)] in a sentence: names, aliases, you, he/she (= the last actor)."""
        out = [(m.start(), KNOWN[m.group(1).lower()]) for m in NAME_RE.finditer(s)]
        for rx, who in ALIAS:
            out += [(m.start(), who) for m in re.finditer(rx, s, re.I)]
        for m in PRON_RE.finditer(s):
            w = m.group(1).lower()
            out.append((m.start(), "you" if w in ("you", "your", "yours", "yourself") else "?"))
        out.sort()
        res, last = [], self.last
        for pos, who in out:
            if who == "?":
                who = last
            else:
                last = who if who != "you" else last
            if who:
                res.append((pos, who))
        return res

    def acts_of(self, s):
        """Actions in a narration sentence: [(actor, action, delay)] and whether the fallback was needed."""
        low = s.lower()
        ms = self.mentions(s)
        acts, delay = [], 0.0
        for row in VERBS:
            rx, act = row[0], row[1]
            m = re.search(rx, low)
            if not m:
                continue
            before = [w for p, w in ms if p < m.start()]
            after = [w for p, w in ms if p >= m.start()]
            who = before[-1] if before else (after[0] if after and act in ("walk_in",) else (self.last or (self.main[0] if self.main else "you")))
            if who == "you" and act in ("gesture",):
                continue
            if act == "gesture" and acts:
                continue
            self.add(who)
            acts.append((who, act, delay, m.start()))
            if len(row) > 2:
                partner = next((w for w in after if w != who), "you" if who != "you" else None)
                if partner:
                    self.add(partner)
                    acts.append((partner, row[2], delay + 1.1, m.start() + 1))
            delay += 0.7
        for rx, effect in WORLD:
            if re.search(rx, low):
                acts.append(("world", effect, delay, 0))
                delay += 0.3
        acts.sort(key=lambda a: a[3])
        out = []
        for i, (who, act, d, _) in enumerate(acts[:3]):
            out.append((who, act, 0.15 + 0.8 * i))
        if ms:
            self.last = next((w for p, w in ms if w != "you"), self.last)
        return out

    def speaker_of(self, before, after):
        """Who says the quote: a name or pronoun right after it, else right before it, else the last speaker, else the scene's first figure."""
        for side, rx_pos in ((after[:70], 0), (before[-70:], 1)):
            if not side.strip():
                continue
            ms = self.mentions(side)
            if re.search(r"\byou (?:say|ask|mumble|whisper|reply|answer|stammer|manage|tell)", side, re.I):
                return "you"
            if SAYS.search(side) or rx_pos == 1:
                named = [w for p, w in ms if w != "you"]
                if named:
                    return named[0] if rx_pos == 0 else named[-1]
            for rx, who in EXTRA:
                if re.search(rx, side, re.I) and not self.main:
                    return who
        return self.speaker or self.last or (self.main[0] if self.main else "stranger")

    # ---------------------------------------------------------------- text
    def para(self, p):
        beats = []
        m = CARD_RE.match(p)
        if m and not QUOTE_RE.search(p) and len(p) < 70:
            return [Beat("card", m.group(1))]
        m = PAREN_RE.match(p)
        if m:
            return [self.narr(m.group(1).strip())]
        m = SCRIPT_RE.match(p)
        if m and m.group(1).lower() in KNOWN | {"you": "you", "narrator": None}:
            who = KNOWN.get(m.group(1).lower(), m.group(1).lower())
            if who != "narrator":
                return self.say(who, m.group(2).strip().strip("'\""), [])
        pos = 0
        quotes = list(QUOTE_RE.finditer(p))
        for q in quotes:
            before, after = p[pos:q.start()], p[q.end():]
            nxt = QUOTE_RE.search(after)
            after = after[:nxt.start()] if nxt else after
            if before.strip():
                beats += self.narr_many(before)
            who = self.speaker_of(p[:q.start()], after)
            beats += self.say(who, (q.group(1) or q.group(2)).strip(), [])
            self.speaker = who if who != "you" else self.speaker
            pos = q.end()
            tail_end = nxt.start() + q.end() if nxt else len(p)
            tail = p[q.end():tail_end]
            if tail.strip() and TAG_RE.match(tail):                     # "he says." : the bubble's name tag already says it
                pos = tail_end
                if who != "you":
                    self.last = who
        rest = p[pos:]
        if rest.strip():
            beats += self.narr_many(rest)
        return beats

    def say(self, who, text, acts):
        self.add(who)
        self.last = who if who != "you" else self.last
        out = []
        for i, c in enumerate(chunk(text)):
            out.append(Beat("say", c, who, [] if i else acts, shock=shock(c)))
        return out

    def narr_many(self, text):
        text = re.sub(r"^[,;:\s]+", "", text).strip()
        if not text:
            return []
        if TAG_RE.match(text):
            return []
        text = text[0].upper() + text[1:]
        return [self.narr(c) for c in chunk(text)]

    def narr(self, text):
        self.n += 1
        acts = []
        for s in sentences(text):
            for a in self.acts_of(s):
                if a[:2] not in [x[:2] for x in acts]:
                    acts.append((a[0], a[1], a[2] + 0.5 * len(acts)))
        push = False
        if not [a for a in acts if a[0] != "world"]:                    # the subtle fallback: a small gesture of the figure the sentence is about (scenery: only the camera moves)
            ms = [w for _, w in self.mentions(text)]
            who = ms[0] if ms else None
            if who:
                self.add(who)
                acts = [(who, ("gesture", "look_down", "gesture2", "look_up")[self.n % 4], 0.4)] + acts
            push = True
        return Beat("narr", text, None, acts[:6], push, shock(text))


def parse(text, main=(), you=True):
    """-> (beats, cast): the beats in order and the list of figure ids that appear ("you" included when the text speaks to / about the player)."""
    p = Parser(main, you)
    beats = []
    for para in [x for x in re.split(r"\n+", text.replace("\r", "")) if x.strip()]:
        beats += p.para(para.strip())
    cast = [c for c in p.cast if c]
    if you and ("you" in [a[0] for b in beats for a in b.acts] or re.search(r"\byou(r)?\b", text, re.I)) and "you" not in cast:
        cast.append("you")
    return beats, cast
