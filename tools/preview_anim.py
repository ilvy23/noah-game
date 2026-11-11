"""tools/preview_anim.py - tinted contact sheets of Noah's animation frames and the ultra cinematics into art/previews/ (reads art/*.json)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import portraits as P
import ultra_fx as U
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "art", "previews")
FONT = "/nix/store/0ll7yhrqgbkmb05wwya0vgjd7y4v2hq5-nerd-fonts-jetbrains-mono-3.4.0+2.304/share/fonts/truetype/NerdFonts/JetBrainsMono/JetBrainsMonoNerdFontMono-Bold.ttf"
F = ImageFont.truetype(FONT, 17)
CASES = (("idle", 0), ("windup", 2), ("strike", 1), ("hurt", 0), ("collapse", 5))
for kind in P.KINDS:
    im = Image.new("RGB", (len(CASES) * 570, 560)); d = ImageDraw.Draw(im)
    for n, (st, i) in enumerate(CASES):
        fr = P.anim_frame(kind, st, i, "big")
        for y, (row, fg, bg) in enumerate(zip(fr["rows"], fr["fg"], fr["bg"])):
            for x, ch in enumerate(row):
                k = P.band(kind, x, len(row)); X = n * 570 + x * 10
                d.rectangle((X, y * 20, X + 10, y * 20 + 20), fill=P.tone_rgb(k, int(bg[x])))
                if ch != " ":
                    d.text((X, y * 20 - 1), ch, fill=P.tone_rgb(k, int(fg[x])), font=F)
    im.save(os.path.join(OUT, "anim_sheet_%s.png" % kind))
G = ImageFont.truetype(FONT, 11)
for which, fn, secs in (("unlock", U.unlock_frame, U.UNLOCK_SECONDS), ("use", lambda t, w, h: U.use_frame(t, w, h, None, (50, 20)), U.USE_SECONDS)):
    w, h, ts = 100, 34, 6
    im = Image.new("RGB", (3 * w * 7, 2 * h * 13)); d = ImageDraw.Draw(im)
    for n in range(6):
        t = secs * (n + 0.5) / 6.0 if n < 5 else secs - 0.05
        ox, oy = (n % 3) * w * 7, (n // 3) * h * 13
        for x, y, ch, c in fn(t, w, h):
            d.text((ox + x * 7, oy + y * 13), ch, fill=U.PALETTE[c][1], font=G)
    im.save(os.path.join(OUT, "ultra_%s.png" % which))
