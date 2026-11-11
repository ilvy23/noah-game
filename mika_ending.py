"""mika_ending.py - the hidden "Mika's Ultra-Tesseract" ending. Condition (story_game.decision): the tesseract unfolded into the
ULTRA TESSERACT, was NEVER used in the fight, and the player lets Noah live.

run(ctx) calls the six scenes in order. noah_slashes, mika_awakens and noah_burns are full-screen animations (noah_gore_fx.py), fourth_wall too (fourth_wall_fx.py); valley_burns (valley_fx.py) and
bench_scene (mika_fx.py) too. Keep the names and the signature:
    noah_slashes, mika_awakens, noah_burns, fourth_wall, valley_burns, bench_scene
Commands:  python3 play.py --mika-ending                  the whole ending (~3 min) and the credits
           python3 play.py --mika-ending --only burn      just one scene: slash | awake | burn | fourth | valley | bench
                                                           | mika | abyss | intro | phase2 | phase3 | phase4 | defeat | decision
                                                           | ending-let | ending-slaughter | ending-3
Cosmetic only: nothing here executes anything, writes files or changes settings. Texts are drafts in story/boss_texts.json (mika.*).
"""
import chain
import json
import os
import re
import shutil
import sys
import time

import audio
import abyss_fx
import cine_fx
import fourth_wall_fx
import mika_fx
import noah_gore_fx as gore
import lyrics_fx
import speech
import valley_fx

HERE = os.path.dirname(os.path.abspath(__file__))
FINAL_LINE = "at last you made the right choice, cheers mate!"


def load_texts():
    try:
        with open(os.path.join(HERE, "story", "boss_texts.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


class Ctx:
    """What a scene gets. io.show(text, who) = a text box (waits for a key); card()/wait() are timed and never block on input;
    sfx(name) is silent for a missing file; song(key) starts a mika_ending song from tracks.json or silently nothing."""

    def __init__(self, io, mixer=None, texts=None, sfx=None, sleep=time.sleep, size=None, out=None, fps=None, spared=None):
        self.io, self.mixer = io, mixer
        self.spared = spared                                                         # the text of the "let him live" choice, shown as bubbles on the first scene
        self.fps = fps or gore.FPS                                                   # frames per second of the full-screen scenes (tests use few)
        self.texts = load_texts() if texts is None else texts
        self.sfx = sfx or audio.sfx
        self.sleep = sleep
        self.size = size or (lambda: tuple(shutil.get_terminal_size((100, 40))))     # (columns, rows)
        self.out = out or sys.stdout
        self.log = []                                                                # ("card"|"say"|"wait", ...) for tests

    def lines(self, key):
        v = self.texts.get(key, "")
        return list(v) if isinstance(v, list) else [v]

    def say(self, key, who="narrator"):
        for t in self.lines(key):
            self.log.append(("say", who, t))
            self.io.show(t, who)

    def card(self, text, seconds=2.0):
        """One centred line on screen for `seconds` (placeholder for the real animation frames)."""
        self.log.append(("card", text))
        w = self.size()[0]
        self.out.write("\n" + text.center(w) + "\n")
        self.out.flush()
        self.sleep(seconds)

    def wait(self, seconds):
        self.log.append(("wait", seconds))
        self.sleep(seconds)

    def audio(self, fn, *a):
        if self.mixer is not None and hasattr(self.mixer, fn):
            getattr(self.mixer, fn)(*a)

    def song(self, key):
        self.audio("mika_ending_song", key)

    def dialog(self, factory, boxes, t0=0.0, span=2.0, seed=1):
        """Speech bubbles on a running animation (speech.py); nothing is ever printed on a bare terminal."""
        return speech.run_dialog(self, factory, boxes, t0, span, seed)

    def song_section(self, name, start, end, fade_in=9.0, fade_out=3.0):
        """Play part of a song file (start/end in seconds of the file) with a slow fade-in and a fade-out; silent without a mixer or without the file."""
        self.audio("play_section", name, start, end, fade_in, fade_out)


def _cards(ctx, key, seconds, sfx=(), step=1):
    """Show every line of `key` as a card; the sounds in `sfx` are cycled, one per `step` lines."""
    for i, t in enumerate(ctx.lines(key)):
        if sfx and i % step == 0:
            ctx.sfx(sfx[(i // step) % len(sfx)])
        ctx.card(t, seconds)


def chunks(text, limit=150):
    """A long text as bubble-sized pieces (whole sentences where possible)."""
    out, cur = [], ""
    for part in [x for x in re.split(r"(?<=[.!?])\s+|\n+", text or "") if x.strip()]:
        if cur and len(cur) + len(part) + 1 > limit:
            out.append(cur)
            cur = ""
        cur = (cur + " " + part).strip()
    return out + ([cur] if cur else [])


def boxes(who, lines, anchor=None):
    return [(who, c, anchor) for t in lines for c in chunks(t)]


NOAH_AT, MIKA_AT = (0.5, 0.5), (0.5, 0.42)                    # where the speakers stand on their scenes (bubble pointers)


def noah_slashes(ctx):
    """Noah cuts at the player and nothing cuts. ~25 s of full-screen animation (noah_gore_fx.SlashScene): diagonal and horizontal cuts, a stab,
    a flurry, the last huge strike that bounces off a faint glow; every cut seals again; Noah goes from fury to disbelief to fear.
    His words are speech bubbles on the scene (the spared-Noah text of the decision first)."""
    ctx.dialog(gore.SlashScene, boxes("noah", (ctx.lines("mika.slash.intro") if not ctx.spared else [ctx.spared] + ctx.lines("mika.slash.intro")), NOAH_AT), 0.0, 1.5, seed=1)
    gore.play(ctx, gore.SlashScene, gore.SlashScene.CUT_END, gore.slash_captions(ctx.lines("mika.slash.lines")), gore.SLASH_CUES, seed=1)
    ctx.dialog(gore.SlashScene, boxes("noah3", ctx.lines("mika.slash.noah"), NOAH_AT), gore.SlashScene.CUT_END - 3.0, 2.0, seed=1)


def mika_awakens(ctx):
    """A hum that grows until it is Mika (noah_gore_fx.AwakenScene, ~32 s): one faint dot, the whole screen slowly lit teal/white/green, a rising
    pulse, motes from the edges, tiny text, and at the end the floor starts to crack (glow-hum-rising under all of it). The last words are bubbles."""
    ctx.song("awakens")
    gore.play(ctx, gore.AwakenScene, 32.0, gore.spread(ctx.lines("mika.awake.lines"), 1.2, 30.4), gore.AWAKEN_CUES, seed=2)
    ctx.dialog(gore.AwakenScene, boxes("noah3", ctx.lines("mika.awake.noah"), NOAH_AT) + boxes("mika", ctx.lines("mika.awake.mika"), MIKA_AT), 29.0, 2.5, seed=2)


NOAH_BURNS_SONG = {"file": "noah-burns-song", "start": 135.0, "end": 210.0, "fade_in": 8.0, "fade_out": 3.0, "lyrics": "noah-burns-song"}      # tracks.json "noah_burns_song" overrides it


def noah_burns_song():
    """{file, start, end, lyrics}: the part of the song under noah_burns (seconds in the file). The scene is stretched to end - start."""
    cfg = dict(NOAH_BURNS_SONG)
    try:
        cfg.update(audio.load_table().get("noah_burns_song") or {})
    except Exception:
        pass
    return cfg


def noah_burns(ctx):
    """The floor opens, Noah burns, an angel comes down out of the sky, his eyes, the hand from the abyss takes him (noah_gore_fx.BurnScene, 53 s of
    beats stretched over the song part end - start = ~75 s: word rain, abyss_fx, angel_fx). The song part plays with fades and its lyrics (a user-supplied
    .lrc, soundtracks/lyrics) stand on the right. Explicit gore, stylised; the caption lines are mika.burn.lines."""
    cfg = noah_burns_song()
    length = max(20.0, float(cfg["end"]) - float(cfg["start"]))
    k = length / gore.BurnScene.END
    ctx.song_section(cfg["file"], float(cfg["start"]), float(cfg["end"]), float(cfg.get("fade_in", 9.0)), float(cfg.get("fade_out", 3.0)))
    lpath = lyrics_fx.default_path(cfg.get("lyrics") or cfg["file"])
    lines, exact = lyrics_fx.load_json(lpath.replace(".lrc", ".words.json"))              # the user's word-timed json first ...
    if lines:
        layer = lyrics_fx.BigLayer(lines, float(cfg["start"]), exact=exact)
    else:                                                                               # ... else the .lrc (+ optional words.txt)
        layer = lyrics_fx.BigLayer(lyrics_fx.load(lpath), float(cfg["start"]), words=lyrics_fx.load_words(lpath.replace(".lrc", ".words.txt")))
    caps = gore.scale_captions(gore.burn_captions(ctx.lines("mika.burn.lines")), k)
    cues = gore.scale_cues(gore.BURN_CUES, k)
    def factory(w, h, r):
        bs = gore.BurnScene(w, h, r)
        return gore.Scaled(bs, k, lambda cv, t: layer.draw(cv, t, bs.lyric_zones(t / k)))
    gore.play(ctx, factory, length, caps, cues, seed=3)
    ctx.wait(0.8)


def fourth_wall(ctx):
    """The tesseract Mika just let go spins up faster and faster, bleeds white, cracks the screen like glass, talks to the player with what it can read
    in-process (user, host, time, size, folder, uptime, load), prints fake system messages, then a long static/error screen, the CRT switch-off and black
    (fourth_wall_fx.py, ~75 s). Mika's song is cut off hard at the start. Harmless: only escape sequences and printed text."""
    ctx.audio("stop")                                 # Jamming is cut off hard (it only fades IN, at the bench start)
    fourth_wall_fx.run(ctx)
    ctx.audio("stop")                                 # the TV is off: abrupt silence; the credits (with the special song) start next


def valley_burns(ctx):
    """The valley of Luenen at night (valley_fx.py, ~40 s): the procession, close on four hooded faces, everything ignites in a wave from the shore, the
    figures burn, run and are dragged over the ground into the lake, a whirlpool takes them (water simulation), steam, the settled lake, Mika at the shore."""
    ctx.song("valley-burns")
    gore.play(ctx, valley_fx.ValleyScene, valley_fx.END, valley_fx.valley_captions(ctx.lines("mika.valley.lines")), valley_fx.VALLEY_CUES, seed=4)
    ctx.wait(0.2)


BENCH_AT = (0.56, 0.58)


def bench_end_captions(lines):
    """Lined up with BenchScene.pose(end): toast 0.4-4.0 s, inhale ~4.6-7.4, exhale 7-8.6, the hand opens 12-13.2 (the goodbye bubbles hold that window)."""
    times = [(0.5, 7.6), (8.4, 11.6)]
    return [(a, b, t) for (a, b), t in zip(times, lines)] + [(11.7 + 0.2 * k, 11.8 + 0.2 * k, t) for k, t in enumerate(lines[2:])]


def bench_scene(ctx):
    """The bench (mika_fx.BenchScene): the smoke sound plays out and Jamming comes in at half of it (Mixer.bench_song); dusk at the lake, the time-jump card
    as an overlay, the lighter, narration and Mika's lines as bubbles, the inhale and the smoke ribbon, the camera pulling out until only a glowing cube
    hangs over the water; Mika says goodbye (the last line is FINAL_LINE), lets the cube go - the tesseract scene (fourth_wall) takes over. No bare text."""
    intro = lambda w, h, r: mika_fx.BenchScene(w, h, r, "intro")
    end = lambda w, h, r: mika_fx.BenchScene(w, h, r, "end")
    ctx.audio("bench_song")
    lines = ctx.lines("mika.bench.lines")
    gore.play(ctx, intro, 9.0, [(0.6, 4.4, lines[0])] if lines else [], mika_fx.BENCH_CUES["intro"], seed=5)
    ctx.dialog(intro, boxes("narrator", lines[1:]) + boxes("mika", ctx.lines("mika.bench.mika"), BENCH_AT), 5.5, 3.0, seed=5)
    gore.play(ctx, end, 16.0, bench_end_captions(ctx.lines("mika.bench.end")), mika_fx.BENCH_CUES["end"], seed=6)
    ctx.dialog(end, boxes("mika", ctx.lines("mika.bench.goodbye"), BENCH_AT) + boxes("mika", ctx.lines("mika.bench.final"), BENCH_AT)
               + boxes("narrator", ctx.lines("mika.bench.flick")), 12.0, 3.0, seed=6)       # Mika's LAST line is FINAL_LINE; then the cube is let go


def mika_showcase(ctx):
    """Mika on his own: forms in teal light, opens his glowing eyes, then the bench with the joint (mika_fx.MikaDemo, 14 s). Only for --only mika."""
    gore.play(ctx, mika_fx.MikaDemo, mika_fx.MikaDemo.END, [], mika_fx.MIKA_CUES, seed=7)


def angel_scene(ctx):
    """The mourning angel coming down out of the torn sky, then the extreme close-up of Noah's eyes (noah_gore_fx.AngelDemo, 9.5 s). In the ending it is part of noah_burns."""
    gore.play(ctx, gore.AngelDemo, gore.AngelDemo.END, [], gore.ANGEL_CUES, seed=9)


def abyss_scene(ctx):
    """The Schlund on its own (abyss_fx.AbyssDemo, 11.5 s): a burnt Noah falls through the maw and lands in the hell. In the ending it is part of noah_burns."""
    gore.play(ctx, abyss_fx.AbyssDemo, abyss_fx.AbyssDemo.END, [], abyss_fx.ABYSS_CUES, seed=8)


def _cine(name):
    return lambda ctx: cine_fx.run_named(ctx, name)


ONLY = {"slash": noah_slashes, "awake": mika_awakens, "burn": noah_burns, "fourth": fourth_wall, "valley": valley_burns, "bench": bench_scene,
        "mika": mika_showcase, "abyss": abyss_scene, "angel": angel_scene}
ONLY.update({name: _cine(name) for name in cine_fx.NAMED})              # intro, phase2-4, defeat, decision, ending-let, ending-slaughter, ending-3
SCENES = (noah_slashes, mika_awakens, noah_burns, valley_burns, bench_scene, fourth_wall)      # the 4th wall is the END; the credits follow


def run(ctx, only=None):
    """All six scenes, or just one: only = a name from ONLY ("slash", "awake", "burn", ...) for quick judging (python3 play.py --mika-ending --only burn)."""
    chain.begin(ctx.out)
    try:
        for scene in ([ONLY[only]] if only else SCENES):
            scene(ctx)
    finally:
        if only:
            chain.end(ctx.out)               # the whole ending keeps the alternate screen open for the credits (story_game ends it)
