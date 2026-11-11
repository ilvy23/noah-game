"""menu_art.py - random faces and little pictures for the title menu."""
import random

FACES = [
    "(=^.^=)", "(o_o)", "(._.)", "(^_^)", "(-_-)", "(>_<)", "(O_O)", "(x_x)", "(;_;)", "(^o^)", "(>:D)", "(\u2022_\u2022)",
"(\u2299_\u2299)", "(\u00b4;\u03c9;`)", "(\u30fb\u00d7\u30fb)", "(\u0ca0_\u0ca0)",
]
NOAH = ["(^_^)", "(>.<)", "(\u2022///\u2022)", "(;_;)", "(\u00ac_\u00ac)", "(^_^)\u2665"]
MIKA = ["(-_-) ~", "(\u2022\u203f\u2022) ~", "(-.-)zZ", "(o_O) ~"]
CONNOR = ["(\u00b4\u2022\u03c9\u2022`)", "( \u02d8\u03c9\u02d8 )", "(\u2022\u203f\u2022)", "(-\u203f-)"]
THINGS = [
    ["   ,--.   ", "  ( oo )  ", "   )__(   ", "  /|  |\\  "],
    ["  _/\\_    ", " (    )   ", "  \\__/    ", "   ||     "],
    ["  .--.    ", " |o_o |   ", " |:_/ |   ", "//   \\ \\  "],
    ["   /\\     ", "  /  \\    ", " / || \\   ", "/__||__\\  "],
    ["  ~~~~~   ", " ~ ~~~ ~  ", "  ~~~~~   ", "   ~~~    "],
]
LINES = [
    "the valley does not sleep. it waits.",
    "keep the lights on. all of them.",
    "left or right around the lake?",
    "it's not like i was waiting for you.",
    "friend, the door is always open.",
    "tea is ready. nobody has used the second cup.",
]


def pick(rng=None):
    """-> dict(face, noah, mika, connor, thing (4 lines), line)"""
    rng = rng or random.Random()
    return {"face": rng.choice(FACES), "noah": rng.choice(NOAH), "mika": rng.choice(MIKA),
            "connor": rng.choice(CONNOR), "thing": rng.choice(THINGS), "line": rng.choice(LINES)}


def title_box(width=50, rng=None):
    """The title box with random decoration; every row has the same width."""
    a = pick(rng)

    def row(txt=""):
        return "  \u2502" + txt[:width].ljust(width) + "\u2502"
    rows = ["  \u250c" + "\u2500" * width + "\u2510", row(),
            row("            F O L K          " + a["face"]), row(),
            row("      a folk-horror story in the valley"),
            row(), row("      " + a["line"]), row()]
    for t in a["thing"][:2]:
        rows.append(row("      " + t))
    rows += [row("      " + a["noah"] + "   " + a["mika"] + "   " + a["connor"]), row(),
             "  \u2514" + "\u2500" * width + "\u2518"]
    return rows
