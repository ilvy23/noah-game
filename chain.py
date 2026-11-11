"""chain.py - one alternate screen for a chain of full-screen scenes: between two scenes only black shows, never the terminal (no empty prompt, no cursor)."""
active = False
BLACK = "\033[0m\033[48;2;0;0;0m\033[2J\033[H\033[?25l"


def begin(out):
    global active
    if not active:
        out.write("\033[?1049h" + BLACK)
        out.flush()
        active = True


def end(out):
    global active
    if active:
        active = False
        out.write("\033[0m\033[?25h\033[?1049l")
        out.flush()


def leave(out):
    """What a scene writes when it ends: black inside a chain, a clean terminal with the cursor back otherwise."""
    out.write(BLACK if active else "\033[0m\033[2J\033[H\033[?25h")
