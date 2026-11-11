# main.py — FOLK. The player loop. Run it with:
#   python3 main.py            (fresh start)
#   python3 main.py --continue (load a save if one exists)

import sys

import context
import engine
from engine import State, render, render_quiet, rule, prompt, save_game, load_game, save_exists
import locations
import characters
import story
import dialogue
import deaths
import music
import achievements

# sanity tiers the NPC dialogue actually covers
_TALK_TIERS = ("steady", "thin", "low")


def talk_tier(s):
    t = s.sanity_tier
    return t if t in _TALK_TIERS else "low"


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------

def ask(prompt_text="> "):
    try:
        return input(prompt_text).strip().lower()
    except EOFError:
        return "quit"


def pause():
    """Wait for the player to continue (Enter)."""
    try:
        input("")
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# talking to Connor / Mika
# ---------------------------------------------------------------------------

def _pick(lines, seed):
    if not lines:
        return ""
    return lines[seed % len(lines)]


def talk_npc(s, who):
    context.record(s, "talk", who=who, place=s.location)
    tier = talk_tier(s)
    # --- new dialogue trees (dialogue.py) take priority when available ---
    if who == "connor":
        open_text = dialogue.CONNOR_OPEN.get(tier, dialogue.CONNOR_OPEN["low"])
        dialogue.run_tree(s, "connor", dialogue.CONNOR_TREE, open_text)
        s.flag("met_connor")
    elif who == "mika":
        open_text = dialogue.MIKA_OPEN.get(tier, dialogue.MIKA_OPEN["low"])
        dialogue.run_tree(s, "mika", dialogue.MIKA_TREE, open_text)
        s.flag("met_mika")
    elif who == "archivist":
        open_text = dialogue.ARCHIVIST_OPEN.get(tier, dialogue.ARCHIVIST_OPEN["low"])
        dialogue.run_tree(s, "archivist", dialogue.ARCHIVIST_TREE, open_text)
        s.flag("met_archivist")
    elif who == "noah":
        # Noah uses the raw sanity tier (all 4 tiers are reachable)
        raw_tier = s.sanity_tier
        open_text = dialogue.NOAH_OPEN.get(raw_tier, dialogue.NOAH_OPEN["low"])
        dialogue.run_tree(s, "noah", dialogue.NOAH_TREE, open_text)
        s.flag("met_noah")
        # Sanity restore with cooldown: +8 sanity once per day
        if s.day != s._noah_rest_day:
            s._noah_rest_day = s.day
            s.sanity_change(8, "sitting with Noah")
            render("")
            render("  the tea is warm. the bench is the right size for two.")
            render("  you sit. the valley is patient. you are not.")
    else:
        # fallback to the old flat lines (only reachable for unknown NPC ids)
        render("")
        render("  no one is here. the light is, though.")

    # chapter progression after any conversation
    msg = story.advance_chapter(s)
    if msg:
        render("")
        render(msg)

    achievements.check_all(s)


# ---------------------------------------------------------------------------
# examining things
# ---------------------------------------------------------------------------

def parse_who(cmd, loc):
    """Resolve who to talk to from a `talk` / `talk <name>` command."""
    words = cmd.split()
    if len(words) >= 2:
        name = words[1]
        if name in ("connor", "mika", "archivist", "noah"):
            return name
        if name in (loc.get("npc"), loc.get("npc2")):
            return name
        return None
    return loc.get("npc")


def show_hint(s):
    """The hint command: Noah gives one short, in-character nudge."""
    import noah
    render("")
    render(noah.hint(s))
    render("")


def show_summary(s):
    """End-of-run summary screen.

    Shows: days survived, places visited, achievements unlocked this run,
    and current level. Called after a death or an ending.
    """
    render("")
    rule(60)
    render("  END OF RUN — the valley keeps the count")
    rule(60)
    render("")
    render(f"  days survived          {s.day}")
    render(f"  places visited         {len(s.visited)}  ({', '.join(s.visited) if s.visited else 'none'})")
    render(f"  achievements unlocked  {achievements.unlocked_count(s)}/{len(achievements.ACHIEVEMENTS)}")
    render(f"  level                  {achievements.level(s)}")
    render("")
    rule(60)
    render("")


def show_journal(s):
    """The journal command: everything you have learned and decided.

    Displays four categories built from the current game state:
      · people met   — from s.journal entries with kind='met'
      · places visited — from s.visited
      · items found    — from s.inventory
      · facts learned  — from s.journal entries with kind='learned'
    """
    render("")
    rule(60)
    render("  JOURNAL — what you have learned and decided")
    rule(60)
    render("")

    # --- People met ---
    render("  PEOPLE MET")
    met = [e["text"] for e in s.journal if e.get("kind") == "met"]
    if met:
        for name in met:
            render("    · " + name)
    else:
        render("    (no one yet)")
    render("")

    # --- Places visited ---
    render("  PLACES VISITED")
    if s.visited:
        for loc_id in s.visited:
            loc = locations.LOCATIONS.get(loc_id, {})
            name = loc.get("name", loc_id)
            render("    · " + name)
    else:
        render("    (nowhere yet)")
    render("")

    # --- Items found ---
    render("  ITEMS FOUND")
    if s.inventory:
        for iid in s.inventory:
            item = locations.ITEMS.get(iid, {})
            name = item.get("name", iid)
            render("    · " + name)
    else:
        render("    (nothing yet)")
    render("")

    # --- Facts learned ---
    render("  FACTS LEARNED")
    learned = [e["text"] for e in s.journal if e.get("kind") == "learned"]
    if learned:
        for fact in learned:
            render("    · " + fact)
    else:
        render("    (nothing yet)")
    render("")

    # --- Other journal entries (decided, death) ---
    other = [e for e in s.journal if e.get("kind") in ("decided", "death")]
    if other:
        render("  OTHER")
        for e in other:
            kind = e.get("kind", "")
            text = e.get("text", "")
            if kind == "decided":
                render("    · decided   " + text)
            elif kind == "death":
                render("    · died      " + text)
            else:
                render("    · " + text)
        render("")

    render("  chapter  " + str(story.current_chapter(s)) + " — " + story.chapter_title(s))
    render("  objective  " + story.chapter_objective(s))
    render("")
    render("  flags set: " + (", ".join(sorted(s.flags)) if s.flags else "(none)"))
    render("  trust " + str(s.trust) + "   fear " + str(s.fear))
    render("")
    # topics you can still ask about, per NPC
    for who in ("connor", "mika", "archivist"):
        topics = sorted(dialogue.ASK_TOPICS.get(who, {}).keys())
        if topics:
            render("  ask " + who + ": " + ", ".join(topics))
    render("")


def examine_item(s, iid):
    item = locations.ITEMS[iid]
    render(item["name"])
    rule()
    render(item["text"])
    s.take(iid)
    s.sanity_change(-2, "examined " + item["name"])

    # special beats
    if iid == "letter":
        s.flag("read_letter")
    if iid == "ledger":
        if not s.has("read_ledger"):
            s.flag("read_ledger")
            s.sanity_change(-10, "read the ledger")
        else:
            render("")
            render("The last line is different. It is your name, but written")
            render("*from the other side of the page*.")
            s.flag("read_ledger_twice")
            s.sanity_change(-12, "read the ledger again")
    elif iid == "notebook":
        s.flag("met_connor")
    elif iid == "ritual_text":
        s.flag("has_instruction")
    elif iid == "key":
        s.flag("has_key")

    # chapter progression: check if the current chapter's objective is met
    msg = story.advance_chapter(s)
    if msg:
        render("")
        render(msg)

    achievements.check_all(s)
    pause()


# ---------------------------------------------------------------------------
# the schloss cellar / the final choice
# ---------------------------------------------------------------------------

def offer_final(s):
    """Shown when you go back to the schloss with everything in place."""
    if not story.ritual_unlocked(s):
        return False
    if s.has("made_choice"):
        return False
    render(story.FINAL)
    render("")
    # Noah's flags matter: concrete story outcomes
    if s.has("noah_ally"):
        render("")
        render("  Noah is at the bottom of the stairs. He is holding a mug.")
        render("  The mug is warm. The mug is not warm. The mug is *there*.")
        render("")
        render("  \u201cI-it's not like I was waiting for you or anything!\u201d")
        render("  \u201cI was just... making tea. The kettle was already on.\u201d")
        render("  \u201cYou can have a sip. T-Tch. Don't get the wrong idea.\u201d")
        render("")
        s.sanity_change(10, "Noah's tea at the schloss")
    if s.has("noah_hurt"):
        render("")
        render("  Noah is at the bottom of the stairs. He is not holding a mug.")
        render("  The mug is in. The mug is not in. The mug is *there*.")
        render("")
        render("  \u201cI-it's not like I'm angry or anything!\u201d")
        render("  \u201cI was just... sitting. The bench was already here.\u201d")
        render("  \u201cYou can sit too. T-Tch. Don't get the wrong idea.\u201d")
        render("")
    for key, desc, ending in story.available_choices(s):
        render(f"  {key}.  {desc}")
    render("")
    choice = ask(">")
    for key, desc, ending in story.available_choices(s):
        if choice.startswith(key):
            context.record(s, "choice", label=desc, place="schloss")
            s.flag("made_choice", True)
            s.flag("ending", ending)
            achievements.check_all(s)
            return True
    render("")
    render("  the valley does not repeat the question. you may try again.")
    return False


# ---------------------------------------------------------------------------
# core loop
# ---------------------------------------------------------------------------

def status(s):
    render("")
    tier_name = s.sanity_tier
    fill = int(40 * s.sanity / 100)
    bar = "[" + "*" * fill + " " * (40 - fill) + "]"
    render(f"  sanity   {s.sanity:3d}/100   {tier_name}")
    render("")
    render("  chapter  " + str(story.current_chapter(s)) + " — " + story.chapter_title(s))
    render("  objective  " + story.chapter_objective(s))
    render("")
    render("  in hand  " + ", ".join(s.inventory) if s.inventory else "  in hand  (nothing)")
    render("  place    " + s.location)
    render("  day      " + str(s.day) + (" — night" if s.night else ""))
    render("  trust    " + str(s.trust) + "   fear " + str(s.fear))
    render("")
    render(f"  level    {achievements.level(s)}   achievements {achievements.unlocked_count(s)}/{len(achievements.ACHIEVEMENTS)}")
    if s.journal:
        render("")
        render("  in your head (latest):")
        for e in s.journal[-5:]:
            render("    · " + e.get("text", ""))
    if story.ritual_unlocked(s):
        render("")
        render("  the hill is ready. the hill will let you down if you go to it.")


def show_location(s):
    loc = locations.LOCATIONS[s.location]
    render("")
    rule(60)
    render(loc["name"].upper())
    rule(60)
    render("")
    if s.location == "nook":
        import noah
        render(noah.place_text(s))
        render("")
    else:
        for para in loc["base"]:
            render(para)
            render("")
    tier = s.sanity_tier
    if tier in ("thin", "low", "critical"):
        for para in loc.get("thin", []):
            render(para)
            render("")
    if tier in ("low", "critical"):
        for para in loc.get("low", []):
            render(para)
            render("")

    # chapter-specific line
    ch_line = locations.chapter_line(s, s.location)
    if ch_line:
        render(ch_line)
        render("")

    # status strip
    fill = int(40 * s.sanity / 100)
    bar = "[" + "*" * fill + " " * (40 - fill) + "]"
    render(f"  {bar}  {s.sanity}/100  ({s.sanity_tier})")


def show_reminder(s):
    """One short line for a place you have already seen, plus the exits."""
    loc = locations.LOCATIONS[s.location]
    render("")
    render(f"  {loc['name']} — {loc.get('tag', '')}")
    render("")
    # status strip
    fill = int(40 * s.sanity / 100)
    bar = "[" + "*" * fill + " " * (40 - fill) + "]"
    render(f"  {bar}  {s.sanity}/100  ({s.sanity_tier})")


def list_options(s, loc):
    render("")
    render("  you can:")
    for verb, target, hint in loc["exits"]:
        if target == "schloss" and not s.has("asked_archivist_cost"):
            render(f"    {verb:>10s}   {hint}  (the gate is locked; the archivist keeps the key)")
            continue
        render(f"    {verb:>10s}   {hint}")
    if loc.get("npc"):
        name = {"connor": "Connor", "mika": "Mika", "archivist": "the archivist", "noah": "Noah"}.get(loc["npc"], loc["npc"].title())
        render(f"    {'talk':>10s}   {name} is here")
    if loc.get("npc2"):
        name = {"archivist": "the archivist", "noah": "Noah"}.get(loc["npc2"], loc["npc2"].title())
        render(f"    {'talk {name}':>10s}   {name} is here (talk <name>)")
    if loc.get("npc") or loc.get("npc2"):
        render(f"    {'ask <who> <topic>':>10s}   ask someone something specific")
    for iid in loc.get("items", []):
        state = "(read)" if s.has_item(iid) else ""
        render(f"    {'examine':>10s}   {locations.ITEMS[iid]['name']}  {state}")
    render(f"    {'journal':>10s}   what you have learned and decided")
    render(f"    {'status':>10s}   where your head is at")
    render(f"    {'quit':>10s}     save and leave for now")
    render("")


def game_loop(s):
    # redraw=True means "print the full location description this round."
    # It is set to True when you arrive somewhere (travel) or when your
    # sanity tier shifts (the world gets thicker/thinner). Status, talk and
    # examine keep it False so you get a quick result and the prompt back
    # without the whole scene being reprinted.
    redraw = True
    while True:
        loc = locations.LOCATIONS[s.location]
        if s.location not in s.visited:
            s.visited.append(s.location)
            achievements.check_all(s)

        # schloss special: if the ritual is unblocked and not yet chosen
        if s.location == "schloss" and offer_final(s):
            ending = s.flags.get("ending")
            achievements.check_all(s)
            render(story.ENDINGS[ending])
            render("")
            render(story.AFTER_LINE[ending])
            if not save_game(s):
                render("")
                render("  (the valley could not write your name down this time. it will keep it in its own way.)")
            break

        # death check: sanity collapse, the forest, the lake, a wrong
        # answer, the week running out, or the archivist's price
        death_id = deaths.check_death(s)
        if death_id:
            new_s = deaths.death_screen(s, death_id)
            if new_s is None:
                break
            s = new_s
            achievements.check_all(s)
            redraw = True
            continue

        if redraw:
            if s.location in s.seen:
                show_reminder(s)
            else:
                show_location(s)
                s.seen.append(s.location)
            redraw = False

        list_options(s, loc)
        prompt()
        cmd = ask("")
        if not cmd:
            continue

        if cmd in ("q", "quit", "exit", "save", "leaving"):
            if save_game(s):
                render("")
                render("  saved. the valley is patient. come back when you are ready.")
            else:
                render("")
                render("  (the valley could not write your name down this time. it will keep it in its own way.)")
            break

        # remember the tier so we can tell if the world just shifted
        tier_before = s.sanity_tier

        if cmd in ("status", "s"):
            status(s)
            save_game(s)
            continue

        if cmd in ("journal", "j", "notes"):
            show_journal(s)
            save_game(s)
            continue

        if cmd in ("hint", "h"):
            show_hint(s)
            save_game(s)
            continue

        if cmd in ("achievements", "a", "achievements list"):
            achievements.check_all(s)
            achievements.list_all(s)
            save_game(s)
            continue

        if cmd in ("talk", "t") or cmd.startswith("talk "):
            who = parse_who(cmd, loc)
            if who:
                talk_npc(s, who)
            else:
                render("")
                render("  no one is here. the light is, though.")
            save_game(s)
            redraw = (s.sanity_tier != tier_before)
            continue

        if cmd.startswith("ask "):
            parts = cmd.split()
            # ask <who> <topic>  or  ask <topic> (uses the main npc)
            who = None
            topic = None
            if len(parts) >= 3:
                who = parts[1]
                topic = " ".join(parts[2:])
            elif len(parts) == 2:
                topic = parts[1]
                who = loc.get("npc")
            if who is None:
                render("")
                render("  no one to ask. the light is, though.")
            else:
                if who not in ("connor", "mika", "archivist", "noah"):
                    # allow "ask mika uncle" style and bare topic lists
                    if who in (loc.get("npc"), loc.get("npc2")):
                        pass
                    else:
                        render("")
                        render(f"  {who} is not here to answer.")
                        who = None
                if who:
                    context.record(s, "ask", who=who, label=topic or "", place=s.location)
                    if not dialogue.ask_topic(s, who, topic):
                        render("")
                        render(f"  {who} looks at you, but that is not a question the valley has an answer for.")
                        s.sanity_change(-1, "a question with no answer")
            save_game(s)
            redraw = (s.sanity_tier != tier_before)
            continue

        if cmd in ("look", "l"):
            show_location(s)
            if s.location not in s.seen:
                s.seen.append(s.location)
            save_game(s)
            continue

        if cmd in ("examine", "e", "read"):
            items_here = loc.get("items", [])
            if not items_here:
                render("")
                render("  nothing here to hold.")
            elif len(items_here) == 1:
                context.record(s, "item", label=items_here[0], place=s.location)
                examine_item(s, items_here[0])
            else:
                render("")
                render("  you can touch:")
                for i, iid in enumerate(items_here, 1):
                    render(f"    {i}. {locations.ITEMS[iid]['name']}")
                choice = ask(">")
                try:
                    n = int(choice)
                    if 1 <= n <= len(items_here):
                        context.record(s, "item", label=items_here[n - 1], place=s.location)
                        examine_item(s, items_here[n - 1])
                except ValueError:
                    pass
            save_game(s)
            redraw = (s.sanity_tier != tier_before)
            continue

        # travel: match by target id or verb
        moved = False
        for verb, target, hint in loc["exits"]:
            if cmd == target or cmd == verb or target in cmd:
                # chapter locks: the schloss is only reachable from chapter 4,
                # the lake from chapter 3
                if target == "schloss" and story.current_chapter(s) < 4:
                    render("")
                    render("  the hill is there. The gate is there. But the hill")
                    render("  is not *for you yet*. It is not a lock. It is a")
                    render("  *sequence*. You have not earned the sequence.")
                    render("  The archivist keeps the key, and the key keeps")
                    render("  the cost, and the cost keeps the name.")
                    s.sanity_change(-2, "the hill is not for you yet")
                    save_game(s)
                    redraw = (s.sanity_tier != tier_before)
                    break
                if target == "lake" and story.current_chapter(s) < 3:
                    render("")
                    render("  The road to the lake is there. The lake is there.")
                    render("  But the lake is not *for you yet*. It is not a")
                    render("  lock. It is a *sequence*. You have not earned")
                    render("  the sequence. The water is flat and patient")
                    render("  and it does not care that you are early.")
                    s.sanity_change(-2, "the lake is not for you yet")
                    save_game(s)
                    redraw = (s.sanity_tier != tier_before)
                    break
                # the schloss gate is locked until the archivist has told
                # you about the cost (ask him, or talk to him and ask)
                if target == "schloss" and not s.has("asked_archivist_cost"):
                    render("")
                    render("  the gate is locked. the keyhole is shaped like a hand")
                    render("  with all five fingers spread. it does not want to be")
                    render("  locked. it wants to be *answered*. you have not been")
                    render("  answered yet. the archivist keeps the key.")
                    s.sanity_change(-2, "the gate will not open")
                    save_game(s)
                    redraw = (s.sanity_tier != tier_before)
                    break
                context.record(s, "move", place=target)
                s.location = target
                moved = True
                break
        if moved:
            s.day = min(7, s.day + 1) if s.day < 7 else 7
            # night falls in the middle of the week
            s.night = s.day >= 4
            # the track follows the place (same track: no restart; unknown: keep)
            music.play_location(s.location)
            redraw = True
            achievements.check_all(s)
        else:
            render("")
            render("  (you do not know what to do with that. the valley does.)")
            s.sanity_change(-1, "lost for a moment")
            redraw = (s.sanity_tier != tier_before)

        achievements.check_all(s)
        save_game(s)

        ending = story.check_ending(s)
        if ending:
            achievements.check_all(s)
            render("")
            render(story.ENDINGS[ending])
            render("")
            render(story.AFTER_LINE[ending])
            show_summary(s)
            if not save_game(s):
                render("")
                render("  (the valley could not write your name down this time. it will keep it in its own way.)")
            break

        death_id = deaths.check_death(s)
        if death_id:
            new_s = deaths.death_screen(s, death_id)
            if new_s is None:
                break
            s = new_s
            achievements.check_all(s)
            redraw = True
            continue


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _how_to_play():
    render("")
    render("  how to play")
    rule()
    render("    travel    type a place: house · forest · lake · schloss · gymnasium · lunuen")
    render("    talk      talk to whoever is standing there (talk <name> for the other one)")
    render("    ask       ask <who> <topic> — ask someone something specific")
    render("    journal   what you have learned and decided")
    render("    hint      noah will tell you what to do next (he will not be nice about it)")
    render("    examine   touch / read what is here")
    render("    status    where your head is at")
    render("    quit      save and leave for now")
    render("    summary   shown automatically when a run ends (death or ending)")
    render("")
    pause()


def _title_screen():
    """ASCII title screen with New Game / Continue / How to Play / Quit."""
    render("")
    render("  ┌──────────────────────────────────────────────────┐")
    render("  │                                                  │")
    render("  │            F O L K                               │")
    render("  │                                                  │")
    render("  │      a folk-horror story in the valley           │")
    render("  │                                                  │")
    render("  │      Das Tal schläft nicht. Es wartet.           │")
    render("  │                                                  │")
    render("  └──────────────────────────────────────────────────┘")
    render("")


def _menu():
    """Show the four menu options and read a choice."""
    render("    1.  new game")
    render("    2.  continue")
    render("    3.  how to play")
    render("    4.  quit")
    render("")


def main():
    if "--no-music" in sys.argv:
        music.disable()
    _title_screen()

    if "--continue" in sys.argv:
        # --continue skips the menu and loads directly
        if save_exists():
            s = load_game()
            render("")
            render("  (loaded a save. the valley remembers you.)")
            render("")
        else:
            s = State()
            render("")
            render("  (no save. starting fresh.)")
            render("")
    else:
        # interactive menu
        while True:
            _menu()
            choice = ask("> ")
            if choice in ("1", "new", "n"):
                s = State()
                break
            elif choice in ("2", "continue", "c"):
                if save_exists():
                    s = load_game()
                    render("")
                    render("  (loaded a save. the valley remembers you.)")
                    render("")
                    break
                else:
                    render("")
                    render("  (no save to continue. the valley has forgotten you.)")
                    render("")
            elif choice in ("3", "how", "h", "help"):
                _how_to_play()
            elif choice in ("4", "quit", "q", "exit"):
                render("")
                render("  the valley is patient. thank you for playing.")
                render("")
                return
            else:
                render("")
                render("  (the valley does not understand that.)")
                render("")

    # start the music immediately once the player has chosen new game / continue
    music.start(s.location)

    render(story.PROLOGUE)
    pause()
    _how_to_play()
    try:
        game_loop(s)
    finally:
        # exceptions and Ctrl-C must never leave an orphan player behind
        music.stop()

    render("")
    render("  the valley is patient. thank you for playing.")
    render("")


if __name__ == "__main__":
    main()
