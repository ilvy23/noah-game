"""scene_lib/actions.py - the action animations a figure can play, as keyframe tracks over the rig of figures.py.

An Act has a duration, numeric tracks {param: [(fraction, value), ...]} (everything else keeps its value), an end ('return' = back to the pose it
started from, 'hold' = stay in the last key: sitting, kneeling, a raised hand), optional walking (dx = screen widths, gait = legs swing), props that
appear in a hand at a fraction (and optionally vanish later) and events that fire once (smoke puff, sound, tears, jolt).
ACTIONS is the table every verb of verbs.py points at. Pure data plus the sampler pose_at().
"""

REST = dict(lean=0.0, head=0.0, aU=6.0, aL=10.0, bU=-4.0, bL=8.0, tA=0.0, sA=0.0, tB=0.0, sB=0.0, rot=0.0, eyes=1.0, mouth=0.0, smile=0.0, look=0.0,
            lift=0.0)
PROPS = ("cig", "cup", "knife", "key", "cube", "note", "lighter", "candle", "flashlight", "teapot", "photo", "hand")
SIT = {"tA": [(1, 88)], "sA": [(1, -88)], "tB": [(1, 84)], "sB": [(1, -80)], "lean": [(0.5, -3), (1, -2)], "aU": [(1, 28)], "aL": [(1, 52)], "bU": [(1, 20)],
       "bL": [(1, 70)]}


class Act:
    def __init__(self, dur, tracks=None, end="return", dx=0.0, gait=False, props=None, events=(), fall=False):
        self.dur, self.tracks, self.end, self.dx, self.gait = dur, tracks or {}, end, dx, gait
        self.props, self.events, self.fall = props or {}, list(events), fall


def A(dur, tracks=None, **kw):
    return Act(dur, tracks, **kw)


def _ease(f):
    return f * f * (3.0 - 2.0 * f)


def sample(track, start, f):
    """Value of a track [(fraction, value)...] that begins at `start` (fraction 0) at fraction f."""
    pts = [(0.0, start)] + [(a, b) for a, b in track]
    for i in range(1, len(pts)):
        if f <= pts[i][0]:
            a, b = pts[i - 1], pts[i]
            span = max(1e-6, b[0] - a[0])
            return a[1] + (b[1] - a[1]) * _ease((f - a[0]) / span)
    return pts[-1][1]


def pose_at(act, state, f):
    """The pose dict of `state` while `act` is at fraction f (0..1)."""
    pose = dict(state)
    for k, track in act.tracks.items():
        tr = list(track)
        if act.end == "return" and tr[-1][0] < 1.0:
            tr.append((1.0, state.get(k, REST.get(k, 0.0))))
        pose[k] = sample(tr, state.get(k, REST.get(k, 0.0)), f)
    return pose


def end_state(act, state):
    return pose_at(act, state, 1.0 if act.end == "hold" else 0.0)


def nod(n=2, amt=24):
    ks = []
    for i in range(n):
        ks += [((i * 2 + 1) / (2.0 * n + 1), amt), ((i * 2 + 2) / (2.0 * n + 1), -2)]
    return ks


def reach(hand="a", up=70, low=20, f=0.4):
    u, l = ("aU", "aL") if hand == "a" else ("bU", "bL")
    return {u: [(f, up)], l: [(f, low)]}


ACTIONS = {
    # posture
    "stand": A(1.4, {"tA": [(0.5, 40), (1, 0)], "sA": [(0.5, -10), (1, 0)], "tB": [(0.5, 50), (1, 0)], "sB": [(0.5, -20), (1, 0)], "lean": [(0.35, 18), (0.7, 8), (1, 0)],
                     "aU": [(0.5, 20), (1, 6)], "aL": [(1, 10)], "bU": [(1, -4)], "bL": [(1, 8)]}, end="hold"),
    "sit": A(1.4, dict(SIT, lean=[(0.4, 14), (1, -2)]), end="hold"),
    "kneel": A(1.6, {"tA": [(0.5, 20), (1, 6)], "sA": [(0.5, -50), (1, -90)], "tB": [(0.5, 10), (1, 8)], "sB": [(0.5, -40), (1, -86)], "lean": [(0.5, 6), (1, 0)],
                     "head": [(1, 8)], "aU": [(1, 14)], "aL": [(1, 30)], "bU": [(1, 8)], "bL": [(1, 30)]}, end="hold"),
    "fall_forward": A(1.3, {"rot": [(0.45, 28), (0.8, 78), (1, 86)], "lean": [(1, 10)], "aU": [(0.5, 120), (1, 170)], "aL": [(1, -10)], "bU": [(0.5, 100), (1, 160)], "bL": [(1, 0)],
                            "head": [(1, -30)], "eyes": [(0.3, 1.4), (1, 0)], "tA": [(1, -10)], "tB": [(1, 6)]}, end="hold", events=[(0.8, "sfx:flesh-fall"), (0.85, "jolt")]),
    "lean_back": A(1.6, {"lean": [(0.4, -14), (0.8, -12)], "head": [(0.5, -8)], "bU": [(0.6, 18)], "aU": [(0.6, 12)]}, end="hold"),
    "lean_forward": A(1.4, {"lean": [(0.5, 14), (0.8, 12)], "head": [(0.5, 8)]}, end="hold"),
    "straighten": A(1.0, {"lean": [(1, 0)], "head": [(1, 0)], "rot": [(1, 0)]}, end="hold"),
    "turn": A(0.9, {"look": [(0.5, 1), (1, 1)], "head": [(0.5, 6)]}, end="hold"),
    "turn_back": A(0.9, {"look": [(0.5, 0), (1, 0)]}, end="hold"),
    # movement
    "walk_in": A(2.6, {}, dx=0.3, gait=True, end="hold"),         # placeholders: Puppet.act builds the real walk from where the figure is and where it goes
    "walk_out": A(2.8, {}, dx=0.7, gait=True, end="hold"),
    "walk_to": A(2.0, {}, dx=0.2, gait=True, end="hold"),
    "step_forward": A(1.0, {}, dx=0.06, gait=True, end="hold"),
    "step_back": A(0.9, {"lean": [(0.4, -8)], "aU": [(0.5, 20)]}, dx=-0.05, gait=True, end="hold"),
    "approach": A(1.8, {}, dx=0.14, gait=True, end="hold"),
    # head and face
    "nod": A(1.0, {"head": nod(2, 22)}),
    "shake_head": A(1.1, {"look": [(0.15, 0.7), (0.35, -0.4), (0.55, 0.7), (0.75, -0.4), (0.9, 0)], "head": [(0.5, 4)]}),
    "look_away": A(1.2, {"look": [(0.5, -1), (1, -1)], "head": [(0.5, 8)]}, end="hold"),
    "look_back": A(0.9, {"look": [(1, 0)], "head": [(1, 0)]}, end="hold"),
    "look_up": A(1.2, {"head": [(0.5, -22)]}, end="return"),
    "look_down": A(1.4, {"head": [(0.5, 26)]}, end="return"),
    "smile": A(1.8, {"smile": [(0.4, 1)], "mouth": [(0.4, 0.0)]}, end="hold"),
    "grin": A(1.8, {"smile": [(0.3, 1.4)], "mouth": [(0.4, 0.3)], "head": [(0.5, -4)]}, end="hold"),
    "frown": A(1.5, {"smile": [(0.4, -1)], "head": [(0.5, 6)]}, end="hold"),
    "neutral": A(0.8, {"smile": [(1, 0)], "eyes": [(1, 1)]}, end="hold"),
    "close_eyes": A(2.0, {"eyes": [(0.15, 0), (0.85, 0), (1, 1)], "head": [(0.4, 8)]}),
    "wide_eyes": A(1.6, {"eyes": [(0.2, 1.5)], "smile": [(0.2, -0.3)]}, end="hold"),
    "laugh": A(1.8, {"mouth": [(0.1, 0.9), (0.2, 0.2), (0.3, 0.9), (0.4, 0.2), (0.5, 0.9), (0.6, 0.2), (0.7, 0.8), (0.9, 0.0)], "head": [(0.1, -8), (0.5, -10), (0.9, 0)],
                       "lean": [(0.1, -4), (0.3, 0), (0.5, -4), (0.7, 0), (0.9, -2)], "smile": [(0.2, 1.4), (1, 1)]}, end="return"),
    "cry": A(2.8, {"head": [(0.3, 22), (0.9, 24)], "eyes": [(0.3, 0.2), (0.9, 0.2)], "smile": [(0.3, -1.4), (0.9, -1.4)], "aU": [(0.4, 130)], "aL": [(0.4, 120)]},
             end="return", events=[(0.3, "tears"), (0.5, "tears"), (0.7, "tears"), (0.9, "tears")]),
    "shiver": A(1.8, {"lean": [(0.1, 2), (0.2, -2), (0.3, 2), (0.4, -2), (0.5, 2), (0.6, -2), (0.7, 2), (0.8, -1), (0.9, 0)], "aU": [(0.3, 20)], "bU": [(0.3, 24)], "aL": [(0.3, 70)], "bL": [(0.3, 70)]},
                      events=[(0.0, "cold")]),
    "flinch": A(1.0, {"lean": [(0.15, -14), (0.7, -8)], "aU": [(0.15, 110)], "aL": [(0.15, 110)], "bU": [(0.15, 100)], "bL": [(0.15, 100)], "eyes": [(0.1, 1.5)], "tA": [(0.15, -10)],
                      "head": [(0.15, -6)]}, events=[(0.05, "jolt")]),
    "tremble": A(2.0, {"aU": [(0.2, 16)], "bU": [(0.2, 14)], "lean": [(0.1, 2), (0.2, -2), (0.3, 2), (0.4, -2), (0.5, 1), (0.6, -1), (0.8, 0)], "eyes": [(0.2, 1.4)]}),
    "cover_face": A(2.0, {"aU": [(0.3, 140)], "aL": [(0.3, 140)], "bU": [(0.3, 130)], "bL": [(0.3, 135)], "head": [(0.3, 18)]}, end="hold"),
    "lower_hands": A(0.9, {"aU": [(1, 6)], "aL": [(1, 10)], "bU": [(1, -4)], "bL": [(1, 8)]}, end="hold"),
    # arms
    "raise_hand": A(1.0, reach("a", 150, 12, 0.5), end="hold"),
    "lower_hand": A(1.0, {"aU": [(1, 6)], "aL": [(1, 10)], "bU": [(1, -4)], "bL": [(1, 8)]}, end="hold"),
    "wave": A(1.8, {"aU": [(0.2, 150), (0.9, 150)], "aL": [(0.2, 10), (0.35, 40), (0.5, -10), (0.65, 40), (0.8, -10)]}),
    "point": A(1.6, {"aU": [(0.3, 88), (0.85, 88)], "aL": [(0.3, 2), (0.85, 2)], "head": [(0.3, 4)]}),
    "shrug": A(1.4, {"aU": [(0.3, 20), (0.7, 20)], "bU": [(0.3, 20), (0.7, 20)], "aL": [(0.3, 70), (0.7, 70)], "bL": [(0.3, 70), (0.7, 70)], "head": [(0.3, 6)], "lean": [(0.3, 2)]}),
    "gesture": A(1.2, {"aU": [(0.3, 54), (0.6, 40)], "aL": [(0.3, 56), (0.6, 40)], "head": [(0.3, 3)]}),
    "gesture2": A(1.3, {"bU": [(0.3, 46), (0.6, 62)], "bL": [(0.3, 60), (0.6, 30)], "aU": [(0.3, 26)], "aL": [(0.3, 60)], "head": [(0.4, -3)]}),
    "fold_arms": A(1.2, {"aU": [(0.4, 28)], "aL": [(0.4, 118)], "bU": [(0.4, 26)], "bL": [(0.4, 120)]}, end="hold"),
    "hands_behind": A(1.0, {"aU": [(0.4, -22)], "aL": [(0.4, 6)], "bU": [(0.4, -26)], "bL": [(0.4, 6)]}, end="hold"),
    "clench": A(1.2, {"aU": [(0.3, 18)], "aL": [(0.3, 60)], "bU": [(0.3, 16)], "bL": [(0.3, 60)], "head": [(0.3, 10)], "smile": [(0.3, -1)]}),
    "knock": A(1.8, {"aU": [(0.2, 84), (0.35, 76), (0.5, 86), (0.65, 76), (0.8, 86)], "aL": [(0.2, 10), (0.35, 36), (0.5, 10), (0.65, 36), (0.8, 10)]}, events=[(0.35, "sfx:iron-bar-hit")]),
    "touch_wall": A(2.2, {"aU": [(0.3, 86), (0.85, 86)], "aL": [(0.3, 4), (0.85, 4)], "head": [(0.3, 4)], "lean": [(0.3, 5), (0.85, 5)]}),
    "open_door": A(2.0, {"aU": [(0.3, 80), (0.6, 70)], "aL": [(0.3, 8)], "lean": [(0.4, 8), (0.8, 4)]}, dx=0.04, events=[(0.5, "door")]),
    "pat": A(1.3, {"aU": [(0.3, 70), (0.45, 60), (0.6, 70), (0.75, 60)], "aL": [(0.3, 20)]}),
    "hand_head": A(1.6, {"aU": [(0.35, 150), (0.8, 150)], "aL": [(0.35, 120), (0.8, 120)], "head": [(0.35, -4)]}),
    "hold_out": A(1.4, {"aU": [(0.4, 82), (1, 82)], "aL": [(0.4, 6), (1, 6)]}, end="hold", props={}),
    "take": A(1.5, {"aU": [(0.35, 80), (0.6, 70), (1, 30)], "aL": [(0.35, 8), (0.6, 40), (1, 90)]}, end="hold"),
    "hand_over": A(1.6, {"aU": [(0.35, 84), (0.9, 84)], "aL": [(0.35, 6), (0.9, 6)], "lean": [(0.35, 6)]}, end="return"),
    "hug": A(2.6, {"aU": [(0.3, 70), (0.5, 40)], "aL": [(0.3, 20), (0.5, 90)], "bU": [(0.3, 60), (0.5, 36)], "bL": [(0.3, 24), (0.5, 90)], "lean": [(0.4, 10)], "head": [(0.5, 12)],
                    "eyes": [(0.5, 0)]}, dx=0.06, gait=True, end="hold"),
    "unhug": A(1.4, {"aU": [(1, 6)], "aL": [(1, 10)], "bU": [(1, -4)], "bL": [(1, 8)], "lean": [(1, 0)], "eyes": [(0.5, 1)]}, dx=-0.05, end="hold"),
    # things in the hands
    "take_knife": A(1.4, {"aU": [(0.4, 30), (0.8, 40)], "aL": [(0.4, 70), (0.8, 80)], "head": [(0.4, 4)]}, end="hold", props={"prop_a": ("knife", 0.4, None)}, events=[(0.4, "sfx:knife-draw")]),
    "raise_knife": A(1.2, {"aU": [(0.4, 150)], "aL": [(0.4, 20)], "lean": [(0.4, -4)]}, end="hold", props={"prop_a": ("knife", 0.0, None)}),
    "take_cube": A(1.4, {"aU": [(0.4, 50), (0.8, 52)], "aL": [(0.4, 80), (0.8, 84)], "head": [(0.4, 14)]}, end="hold", props={"prop_a": ("cube", 0.4, None)}),
    "take_key": A(1.4, {"aU": [(0.4, 70), (0.8, 68)], "aL": [(0.4, 20)], "head": [(0.4, 10)]}, end="hold", props={"prop_a": ("key", 0.4, None)}),
    "take_note": A(1.4, {"aU": [(0.4, 40), (0.8, 44)], "aL": [(0.4, 90), (0.8, 92)], "head": [(0.4, 18)]}, end="hold", props={"prop_a": ("note", 0.4, None)}),
    "take_cup": A(1.6, {"aU": [(0.4, 50), (0.8, 46)], "aL": [(0.4, 70), (0.8, 78)]}, end="hold", props={"prop_a": ("cup", 0.4, None)}),
    "drink": A(2.0, {"aU": [(0.3, 120), (0.55, 120)], "aL": [(0.3, 90), (0.55, 100)], "head": [(0.3, -10), (0.55, -10)]}, end="return"),
    "pour": A(2.6, {"aU": [(0.3, 76), (0.7, 76)], "aL": [(0.3, 14), (0.5, 40), (0.7, 40)], "bU": [(0.3, 56), (0.7, 56)], "bL": [(0.3, 50), (0.7, 50)], "head": [(0.3, 16)]},
                 props={"prop_a": ("teapot", 0.0, 1.0), "prop_b": ("cup", 0.0, 1.0)}, events=[(0.45, "pour")]),
    "light_cig": A(2.6, {"aU": [(0.25, 118), (0.8, 118)], "aL": [(0.25, 100), (0.8, 100)], "bU": [(0.25, 112), (0.8, 112)], "bL": [(0.25, 100), (0.8, 100)], "head": [(0.25, 14), (0.8, 8)]},
                   end="return", props={"prop_a": ("cig", 0.2, None), "prop_b": ("lighter", 0.2, 0.85)}, events=[(0.4, "flame"), (0.7, "puff")]),
    "smoke": A(3.2, {"aU": [(0.2, 122), (0.35, 122), (0.7, 20), (0.9, 12)], "aL": [(0.2, 104), (0.35, 104), (0.7, 70), (0.9, 40)], "head": [(0.3, -4), (0.6, -8), (0.9, -2)],
                     "lean": [(0.5, -3)]}, end="return", events=[(0.3, "inhale"), (0.62, "puff"), (0.7, "puff")]),
    "hold_cig": A(1.0, {"aU": [(0.4, 36), (1, 34)], "aL": [(0.4, 92), (1, 90)]}, end="hold", props={"prop_a": ("cig", 0.2, None)}),
    "tap_ash": A(1.4, {"aU": [(0.3, 56), (0.6, 50)], "aL": [(0.3, 70), (0.5, 40), (0.6, 70)]}, events=[(0.5, "ash")]),
    "put_out": A(1.4, {"aU": [(0.4, 54)], "aL": [(0.4, 50)]}, props={"prop_a": ("cig", 0.0, 0.7)}),
    "tuck_ear": A(1.4, {"aU": [(0.4, 150), (0.8, 140)], "aL": [(0.4, 90), (0.8, 90)]}, props={"prop_a": ("cig", 0.0, 0.8)}),
    "salute2": A(1.2, {"aU": [(0.3, 130), (0.7, 130)], "aL": [(0.3, 70), (0.7, 70)], "head": [(0.3, -4)], "smile": [(0.3, 1)]}),
    "write": A(2.4, {"aU": [(0.3, 56), (0.8, 52)], "aL": [(0.3, 60), (0.8, 70)], "head": [(0.3, 22), (0.8, 22)], "lean": [(0.3, 10)]}),
    "read_note": A(2.4, {"aU": [(0.3, 44), (0.9, 44)], "aL": [(0.3, 88), (0.9, 88)], "bU": [(0.3, 40), (0.9, 40)], "bL": [(0.3, 88), (0.9, 88)], "head": [(0.3, 22), (0.9, 22)]},
                   props={"prop_a": ("note", 0.0, None)}),
    "light_candle": A(2.0, {"aU": [(0.3, 70), (0.8, 70)], "aL": [(0.3, 40), (0.8, 40)], "head": [(0.3, 14)]}, props={"prop_a": ("candle", 0.2, None)}),
    "tesseract_glow": A(2.4, {"aU": [(0.3, 54), (0.9, 54)], "aL": [(0.3, 82), (0.9, 86)], "head": [(0.3, 18)], "eyes": [(0.3, 1.4)]}, end="hold", props={"prop_a": ("cube", 0.2, None)},
                        events=[(0.3, "glow")]),
    "drop_item": A(1.2, {"aU": [(0.3, 26)], "aL": [(0.3, 20)], "head": [(0.3, 14)]}, props={"prop_a": ("cup", 0.0, 0.3)}, events=[(0.3, "sfx:glass-crack")]),
    "stab": A(1.4, {"aU": [(0.3, 150), (0.5, 40)], "aL": [(0.3, 10), (0.5, 4)], "lean": [(0.3, -6), (0.5, 22)], "head": [(0.5, 10)]}, props={"prop_a": ("knife", 0.0, None)},
              events=[(0.5, "sfx:stab-flesh"), (0.5, "jolt")]),
    "throw_up_hands": A(1.4, {"aU": [(0.3, 150), (0.8, 150)], "bU": [(0.3, 146), (0.8, 146)], "aL": [(0.3, 10)], "bL": [(0.3, 10)], "head": [(0.3, -8)]}),
    "stare": A(1.8, {"head": [(0.3, -3), (0.8, -3)], "eyes": [(0.2, 1.25), (0.8, 1.25)], "lean": [(0.4, 3)]}),
    "busy": A(2.4, {"aU": [(0.2, 52), (0.4, 40), (0.6, 56), (0.8, 42)], "aL": [(0.2, 50), (0.4, 70), (0.6, 46), (0.8, 66)], "bU": [(0.2, 38), (0.5, 48), (0.8, 38)], "bL": [(0.2, 60), (0.5, 50), (0.8, 60)],
                      "head": [(0.3, 20), (0.8, 20)], "lean": [(0.3, 6)]}),
    "bow_head": A(1.8, {"head": [(0.4, 26), (0.85, 26)], "lean": [(0.4, 6)], "eyes": [(0.4, 0.3), (0.85, 0.3)]}),
    "rest": A(0.2, {}, end="return"),
}

IDLE_ACTS = {"mika": [(7.0, "smoke"), (11.0, "tap_ash")], "noah": [(9.0, "look_down"), (13.0, "shiver")], "connor": [(10.0, "nod"), (17.0, "look_down")],
             "you": [(8.0, "look_down"), (13.0, "look_up")], "stranger": [(9.0, "nod")], "woman": [(9.0, "look_down")]}
