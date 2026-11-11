"""Character personality, relationship, and motivation system.

This module defines the core data structures that drive dynamic dialogue:

- PERSONALITIES: each NPC's speaking style, core motivation, and emotional
  baseline. Used by the dialogue engine to select lines and reactions.
- RELATIONSHIPS: per-NPC relationship state (trust, familiarity, key
  decisions) that persists across saves and influences future dialogue.
- MOTIVATIONS: what each NPC wants, and how the player's inventory, stats,
  and decision history change what they say and do.

The dialogue engine (dialogue.py) calls into this module to:
  1. Pick the right personality variant for the current relationship state.
  2. Check whether the player's inventory or stats trigger a special line.
  3. Log the player's decision so future conversations react to it.
"""

from typing import Dict, List, Optional, Tuple


# ===========================================================================
# PERSONALITY PROFILES
# ===========================================================================
# Each NPC has a base personality that shapes their speaking style and
# emotional reactions. The `tiers` dict maps sanity tiers to short
# personality descriptors the dialogue engine can use to pick lines.

PERSONALITIES: Dict[str, dict] = {
    "connor": {
        "name": "Connor",
        "role": "the keeper of the notebook",
        "style": "fragmented, urgent, self-contradicting",
        "motivation": "to be believed before the lake finishes counting",
        "fear": "being dismissed as a madman",
        "tiers": {
            "steady": "wary but coherent; speaks in short, factual bursts",
            "thin": "anxious; repeats himself; watches the water more than you",
            "low": "barely holding together; sentences trail off",
            "critical": "no longer fully present; speaks in the lake's voice",
        },
        "inventory_reactions": {
            # item_id -> extra line Connor says when the player has this item
            "notebook": "You have it. You actually have it. I thought I'd lost it. I thought I'd lost it and then I thought I'd never find it and then I thought it was never mine to begin with. But you have it. That's... that's a start.",
            "ledger": "You've seen the ledger. I can tell. You have that look. The look that means you've read your own name and you're trying to decide whether to believe it.",
        },
        "stat_reactions": {
            # (stat_name, threshold, direction) -> extra line
            ("trust", 20, ">="): "You're not trying to convince me. I can tell. Most people try. You just... stand there. That's rarer than it should be.",
            ("fear", 40, ">="): "You're scared. I can see it. Good. The ones who aren't scared are the ones the lake takes first. The scared ones last longer. That's not a comfort. It's a fact.",
        },
    },
    "mika": {
        "name": "Mika",
        "role": "the painter at the lake",
        "style": "circular, recursive, counting",
        "motivation": "to finish the painting before the face is painted for him",
        "fear": "being the face in the painting",
        "tiers": {
            "steady": "calm but watchful; speaks in complete, deliberate sentences",
            "thin": "distracted; counts under his breath; the painting is more real than he is",
            "low": "dissolving; the boundary between him and the lake is thinning",
            "critical": "no longer distinguishable from the lake; speaks in plural",
        },
        "inventory_reactions": {
            "painting": "You have the painting. You've been holding it. I can see the weight of it in your hands. The face is still blank. It's still blank. That's the important part. That's the part I need you to understand.",
            "notebook": "You read it. You read my uncle's notebook. You read it and you didn't tell me. That's... that's a kind of kindness I didn't know you had.",
        },
        "stat_reactions": {
            ("trust", 30, ">="): "You trust me. Or you trust the version of me that's still here. I don't know which. It's hard to tell the difference from the inside.",
            ("sanity", 30, "<="): "You're not well. I can see it. The valley does that. It takes a little of you each day and you don't notice until you look in the water and the face looking back is a little less yours.",
        },
    },
    "archivist": {
        "name": "The Archivist",
        "role": "Mika's uncle; keeper of the records",
        "style": "formal, repetitive, absolute",
        "motivation": "to keep the records accurate, even if accuracy means your name is in them",
        "fear": "the records being wrong",
        "tiers": {
            "steady": "composed; speaks in complete, declarative sentences",
            "thin": "slightly less composed; the repetition is a little faster",
            "low": "the calm is a performance; you can see the effort it takes",
            "critical": "the calm is the thing; he is the records now",
        },
        "inventory_reactions": {
            "ledger": "You have the ledger. I see it. The records said you would have it. The records are always right. I'm never right. But you have it, and that is a fact the records did not predict. That is... unusual.",
            "key": "You have the key. The records said you would have the key. The records are always right. I'm never right. The key is the cost. The cost is the key. The key is the name. The name is the key.",
        },
        "stat_reactions": {
            ("trust", 40, ">="): "You trust me. The records noted that. The records noted it before you did. The records are always right. I'm never right. But you trust me, and that is a fact I did not predict. That is... unusual.",
            ("fear", 50, ">="): "You are afraid. The records noted that. The records noted it before you were afraid. The records are always right. I'm never right. But you are afraid, and that is a fact I did not predict. That is... unusual.",
        },
    },
    "noah": {
        "name": "Noah",
        "role": "the one who stays",
        "style": "gentle, patient, quietly devastating",
        "motivation": "to keep you alive long enough to understand what's happening",
        "fear": "losing you to the valley",
        "tiers": {
            "steady": "warm; speaks in short, kind sentences; offers tea",
            "thin": "still warm; the kindness is a little more deliberate",
            "low": "the warmth is a shield; you can see what's behind it",
            "critical": "the warmth is the thing; he is the valley's patience",
        },
        "inventory_reactions": {
            "tea": "You brought tea. You actually brought tea. I... I didn't know you could do that. I didn't know you could bring me something. That's... that's a kind of trust I didn't know you had.",
            "notebook": "You have the notebook. You've been carrying it. I can see the weight of it. That's a lot of weight for one person to carry. You don't have to carry it alone. You don't have to carry it at all. But you are. And that's... that's a kind of courage I didn't know you had.",
        },
        "stat_reactions": {
            ("sanity", 60, ">="): "You're holding together. I can see it. That's more than most people manage. That's more than I managed. That's... that's a kind of strength I didn't know you had.",
            ("trust", 25, ">="): "You trust me. I can see it. That's... that's a kind of trust I didn't know you had. I didn't know you could trust anyone. I didn't know you could trust me. But you do. And that's... that's a kind of grace I didn't know you had.",
        },
    },
}


# ===========================================================================
# RELATIONSHIP STATE
# ===========================================================================
# Per-NPC relationship data that persists across saves.
# Each entry tracks:
#   trust:        int  -100..100  (how much the NPC trusts the player)
#   familiarity:  int  0..100     (how well the player knows the NPC)
#   decisions:    list of str     (key decisions the player made with this NPC)
#   last_tier:    str            (last sanity tier the NPC was at)

def default_relationship(who: str) -> dict:
    """Return a fresh relationship dict for an NPC."""
    return {
        "trust": 0,
        "familiarity": 0,
        "decisions": [],
        "last_tier": "steady",
        "state": "neutral",   # derived label, kept in sync by update_relationship
    }


# ---------------------------------------------------------------------------
# RELATIONSHIP STATE LABELS
# ---------------------------------------------------------------------------
# The raw trust value (-100..100) is the source of truth; these labels are
# what the dialogue engine and motivation profiles branch on.

STATE_THRESHOLDS: List[Tuple[str, int]] = [
    ("friendly", 20),    # trust >= 20
    ("hostile", -20),    # trust <= -20
]


def relationship_state(trust: int) -> str:
    """Map a raw trust value to a relationship state label.

    'friendly' when trust >= 20, 'hostile' when trust <= -20,
    'neutral' in between. Pure function so it can be tested directly.
    """
    if trust >= 20:
        return "friendly"
    if trust <= -20:
        return "hostile"
    return "neutral"


def rel_state(s, who: str) -> str:
    """Return the current relationship state label for an NPC.

    Recomputes from the live trust value (the stored `state` field is
    only a cached copy used by older saves and serialisation).
    """
    return relationship_state(get_relationship(s, who)["trust"])


def update_relationship(s, who: str, trust_delta: int = 0,
                        familiarity_delta: int = 0) -> str:
    """Apply an interaction's effect to the NPC's relationship and return
    the resulting state label.

    This is the single entry point the dialogue engine should call after
    a meaningful exchange: it adjusts trust (clamped to -100..100) and
    familiarity (clamped to 0..100), refreshes the cached `state` label,
    and keeps everything consistent for save/load.
    """
    rel = get_relationship(s, who)
    rel["trust"] = max(-100, min(100, rel["trust"] + trust_delta))
    rel["familiarity"] = max(0, min(100, rel["familiarity"] + familiarity_delta))
    rel["state"] = relationship_state(rel["trust"])
    return rel["state"]


# ===========================================================================
# MOTIVATION PROFILES
# ===========================================================================
# What each NPC is actually driving at, and how that drive shows up in
# speech depending on the relationship state. `drive` is the underlying
# want; `states` maps a relationship label to the line the NPC uses to
# surface that want. The dialogue engine picks the line for the current
# state; motivation_line() makes sure a state's line is only voiced once
# per run (the voiced set persists in the save).

MOTIVATIONS: Dict[str, dict] = {
    "connor": {
        "drive": "to be believed before the lake finishes counting",
        "states": {
            "friendly": "You're still here. You're still listening. I don't know what to do with that, but I'm going to keep talking, because you're the only one left who might carry it out of the valley."
                      ,
            "neutral": "I'm telling you this because I don't know who else to tell. Believe me or don't. But write it down. The lake doesn't like things written down."
                      ,
            "hostile": "You don't believe me. I can see it in your hands, the way you hold the paper. Fine. I'll keep talking anyway. Someone has to say it out loud, even if it's to no one."
                      ,
        },
    },
    "mika": {
        "drive": "to finish the painting before the face is painted for him",
        "states": {
            "friendly": "You've seen the painting. You've held it. So you know what I'm trying to do, and you haven't laughed. That's more than the lake has ever given me. I'm going to finish it. I have to finish it."
                      ,
            "neutral": "I'm painting. That's all I do now. The face is still blank, and every day it's a little less blank. You can help, or you can stand there, or you can go. I'd rather you stay."
                      ,
            "hostile": "You're looking at me like I'm already in the painting. I can tell. You're wrong, but you're looking at me like it. That's not going to help either of us."
                      ,
        },
    },
    "archivist": {
        "drive": "to keep the records accurate, even if accuracy means your name is in them",
        "states": {
            "friendly": "You are in the records. I want you to understand that this is not a threat. It is the highest honour the records extend. The records do not extend it often."
                      ,
            "neutral": "The records are complete, and they are accurate, and they include you. I am not the one who wrote your name. I am only the one who keeps it."
                      ,
            "hostile": "You are not in the records yet. That is a temporary state. The records are always right. I am never right. But the records will be right about you, and they will be right soon."
                      ,
        },
    },
    "noah": {
        "drive": "to keep you alive long enough to understand what's happening",
        "states": {
            "friendly": "You're staying. I'm glad. I'm glad because it means I can keep doing this, and I don't know what I'd do if there was no one left to do it for. Sit. I'll put the kettle on."
                      ,
            "neutral": "You look tired. I can tell. Everyone looks tired after a while. That's the valley. You don't have to talk about it. You just have to keep going, a little longer than you think you can."
                      ,
            "hostile": "You don't trust me. I understand. I'd be careful too, in your place. But I'm still going to make you tea, because the valley is patient and I'm not, and you need one of us to be."
                      ,
        },
    },
}


def motivation_line(s, who: str) -> Optional[str]:
    """Return the NPC's motivation line for the current relationship state,
    or None if that line has already been voiced this run.

    The voiced set is stored on `s.motivations` (a dict of NPC id -> list
    of voiced state labels) so it persists across saves and the same line
    is never repeated.
    """
    profile = MOTIVATIONS.get(who)
    if not profile:
        return None
    state = rel_state(s, who)
    line = profile.get("states", {}).get(state)
    if not line:
        return None
    if not hasattr(s, "motivations") or s.motivations is None:
        s.motivations = {}
    voiced = s.motivations.setdefault(who, [])
    if state in voiced:
        return None
    voiced.append(state)
    return line


def get_relationship(s, who: str) -> dict:
    """Get or create the relationship state for an NPC on the State object.

    The relationship data is stored in `s.relationships` (a dict keyed by
    NPC id). If the key is missing (old save), a default is created.
    """
    if not hasattr(s, "relationships") or s.relationships is None:
        s.relationships = {}
    if who not in s.relationships:
        s.relationships[who] = default_relationship(who)
    return s.relationships[who]


def record_decision(s, who: str, decision: str) -> None:
    """Log a player decision in the NPC's relationship record.

    The decision is stored as a short string (e.g. 'mika: twelve').
    Future conversations can check this list to react to past choices.
    """
    rel = get_relationship(s, who)
    if decision not in rel["decisions"]:
        rel["decisions"].append(decision)


def has_decision(s, who: str, decision: str) -> bool:
    """Check whether the player made a specific decision with this NPC."""
    rel = get_relationship(s, who)
    return decision in rel["decisions"]


def bump_familiarity(s, who: str, amount: int = 1) -> None:
    """Increase the player's familiarity with an NPC (0..100)."""
    rel = get_relationship(s, who)
    rel["familiarity"] = min(100, rel["familiarity"] + amount)


# ===========================================================================
# DYNAMIC LINE SELECTION
# ===========================================================================

def select_line(s, who: str, base_text: str) -> str:
    """Select the final line to show for an NPC, given the current state.

    This is the core of the dynamic dialogue system. It checks:
    1. Inventory reactions: does the player have an item the NPC reacts to?
    2. Stat reactions: do the player's stats cross a threshold?
    3. Decision history: has the player made a decision this NPC remembers?

    The base_text is the tier-appropriate line from dialogue.py. The
    returned text is base_text plus any dynamic additions.
    """
    lines = [base_text]
    personality = PERSONALITIES.get(who)
    if not personality:
        return base_text

    # 1. Inventory reactions
    for item_id, reaction in personality.get("inventory_reactions", {}).items():
        if s.has_item(item_id):
            lines.append(reaction)

    # 2. Stat reactions
    for (stat_name, threshold, direction), reaction in personality.get("stat_reactions", {}).items():
        value = getattr(s, stat_name, 0)
        if direction == ">=" and value >= threshold:
            lines.append(reaction)
        elif direction == "<=" and value <= threshold:
            lines.append(reaction)

    # 3. Decision history: if the player made a key decision, the NPC
    #    references it in a short follow-up line.
    rel = get_relationship(s, who)
    if rel["decisions"]:
        last_decision = rel["decisions"][-1]
        lines.append(_decision_reaction(who, last_decision))

    return "\n".join(lines)


def _decision_reaction(who: str, decision: str) -> str:
    """Return a short line where the NPC references the player's last decision."""
    # Map of (who, decision) -> reaction line.
    # Only a subset of decisions have explicit reactions; the rest get
    # a generic acknowledgment.
    reactions = {
        ("mika", "mika: twelve"): "You said twelve. I remember. I remember everything. The lake remembers too. That's the problem. The lake remembers everything.",
        ("mika", "mika: what's twelve?"): "You asked what twelve is. I told you. I told you and you didn't believe me. That's... that's a kind of honesty I didn't know you had.",
        ("connor", "connor: I believe you"): "You believe me. I can see it. That's... that's a kind of trust I didn't know you had. I didn't know you could believe anyone. I didn't know you could believe me. But you do.",
        ("archivist", "archivist: I'll pay"): "You said you'd pay. The records noted that. The records noted it before you said it. The records are always right. I'm never right. But you said it, and that is a fact I did not predict.",
        ("noah", "noah: I'm staying"): "You said you're staying. I can see it. That's... that's a kind of courage I didn't know you had. I didn't know you could stay. I didn't know you could stay with me. But you do.",
    }
    key = (who, decision)
    if key in reactions:
        return reactions[key]
    # Generic acknowledgment for decisions without a specific reaction.
    return f"You said {decision.split(':', 1)[-1].strip()}. I remember. I remember everything. That's the thing about me. I remember everything."


# ===========================================================================
# MOTIVATION CHECKS
# ===========================================================================

def motivation_shift(s, who: str) -> Optional[str]:
    """Check whether the NPC's motivation has shifted based on the player's
    current state. Returns a short line if the motivation has changed,
    or None if it hasn't.

    This is called by the dialogue engine before showing the opening line.
    If the player's inventory or stats have changed since the last
    conversation, the NPC's motivation may have shifted, and they say so.
    """
    personality = PERSONALITIES.get(who)
    if not personality:
        return None

    rel = get_relationship(s, who)
    last_tier = rel.get("last_tier", "steady")
    current_tier = s.sanity_tier

    # If the tier changed, the NPC's emotional state has shifted.
    if last_tier != current_tier:
        rel["last_tier"] = current_tier
        tier_shift_lines = {
            ("connor", "steady", "thin"): "I'm not as steady as I was. I can feel it. The lake is closer. I can hear it. I can hear it breathing.",
            ("connor", "thin", "low"): "I'm not holding together. I can feel it. The lake is in me. I can feel it. I can feel it breathing.",
            ("mika", "steady", "thin"): "I'm not as calm as I was. I can feel it. The painting is closer. I can see it. I can see the face.",
            ("mika", "thin", "low"): "I'm not holding together. I can feel it. The lake is in me. I can feel it. I can feel it counting.",
            ("archivist", "steady", "thin"): "I'm not as composed as I was. I can feel it. The records are closer. I can see them. I can see your name.",
            ("archivist", "thin", "low"): "I'm not holding together. I can feel it. The records are in me. I can feel them. I can feel them writing.",
            ("noah", "steady", "thin"): "I'm not as warm as I was. I can feel it. The valley is closer. I can hear it. I can hear it breathing.",
            ("noah", "thin", "low"): "I'm not holding together. I can feel it. The valley is in me. I can feel it. I can feel it counting.",
        }
        key = (who, last_tier, current_tier)
        if key in tier_shift_lines:
            return tier_shift_lines[key]

    return None


# ===========================================================================
# SAVE/LOAD INTEGRATION
# ===========================================================================

def serialize_relationships(s) -> dict:
    """Return the relationships dict in a form suitable for JSON saving."""
    if not hasattr(s, "relationships") or s.relationships is None:
        return {}
    return s.relationships


def serialize_motivations(s) -> dict:
    """Return the voiced-motivation tracking dict for JSON saving."""
    if not hasattr(s, "motivations") or s.motivations is None:
        return {}
    return s.motivations


def deserialize_relationships(s, data: dict) -> None:
    """Load relationships from a save dict. Missing keys get defaults."""
    if not hasattr(s, "relationships") or s.relationships is None:
        s.relationships = {}
    for who, rel_data in data.items():
        default = default_relationship(who)
        default.update(rel_data)
        # keep the cached state label in sync with the loaded trust value
        default["state"] = relationship_state(default["trust"])
        s.relationships[who] = default


def deserialize_motivations(s, data: dict) -> None:
    """Load voiced-motivation tracking from a save dict (missing = empty)."""
    if not hasattr(s, "motivations") or s.motivations is None:
        s.motivations = {}
    for who, voiced in (data or {}).items():
        s.motivations[who] = list(voiced)


import texts as _texts  # noqa: E402  (text/*.md overrides the defaults above)
_texts.apply(__name__)
