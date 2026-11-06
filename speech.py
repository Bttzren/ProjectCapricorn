"""Prompts and safety rails for lines the AI writes for Capri (pure logic, no Tk, no network)."""
import re
import time
from collections import deque

ROAST_RULES = {
    "off": "Be supportive and kind. No teasing, even when they mess up.",
    "mild": ("When they mess up, tease them playfully (words like tragic, gonk, skill issue) but never swear "
             "and never be cruel."),
    "spicy": ("When they mess up, or whenever you feel like it, roast them hard and funny: dis their tabs, habits, "
              "taste, procrastination and play. Mild swearing like 'ass', 'damn' or 'hell' is allowed. Keep it "
              "friend-to-friend: never about their body, identity, family or real struggles. Never use slurs, hate, "
              "threats or anything sexual."),
}
STYLE = ("Reply with exactly ONE short sentence, at most 18 words. Plain text only: no emoji, no markdown, "
         "no quotation marks, no hashtags. Sound like a person, not a bot.")

REFUSALS = ("as an ai", "i'm sorry", "i am sorry", "i cannot", "i can't", "i can not", "sorry,", "i'm unable")


def system_prompt(persona, context="", level="mild", memory=""):
    parts = [persona.strip(), context.strip(), memory.strip(), ROAST_RULES.get(level, ROAST_RULES["mild"]), STYLE]
    return " ".join(p for p in parts if p)


def _recent(recent):
    if not recent:
        return ""
    return " Don't repeat or closely paraphrase these recent lines of yours: " + " | ".join(recent[-6:])


def user_prompt(kind, facts, recent=()):
    """The message that asks the AI for one line, for each kind of moment."""
    f = facts or {}
    if kind == "poke":
        text = "The user just poked you. React in one short sentence."
    elif kind == "idle":
        text = "You're hanging out on their desktop and nothing is happening. Say one short random thought, joke or observation."
    elif kind == "greeting":
        text = "The user just launched you. Greet them." + (f" {f['away']}" if f.get("away") else "")
    elif kind == "checkin":
        text = "Give a gentle one-sentence wellness nudge (water, stretching, eating, posture, or resting their eyes). Pick one."
    elif kind == "context":
        text = f"The user just switched to {f.get('activity', 'something new')}. React in one short sentence."
    elif kind == "nudge":
        text = (f"The user has been {f.get('activity', 'at it')} for about {f.get('minutes', 30)} minutes. "
                "Nudge them to take a break.")
    elif kind == "game_start":
        text = f"The user just started playing {f.get('game', 'a game')}. Say something to hype them up."
    elif kind == "recap":
        text = (f"The {f.get('game', 'game')} session just ended: {f.get('kills', 0)} kills, {f.get('deaths', 0)} deaths, "
                f"rounds {f.get('rw', 0)}-{f.get('rl', 0)}, {f.get('minutes', 0)} minutes. Give a one-sentence verdict.")
    elif kind == "game":
        n = f.get("n", 1)
        event = f.get("event", "event").replace("_", " ")
        text = (f"In {f.get('game', 'the game')} the user just got a {event}" + (f" (x{n})" if n > 1 else "")
                + f". Session so far: {f.get('kills', 0)} kills and {f.get('deaths', 0)} deaths"
                + (f", {f['kstreak']} kills in a row" if f.get("kstreak", 0) >= 2 else "")
                + (f", {f['dstreak']} deaths in a row" if f.get("dstreak", 0) >= 2 else "")
                + ". React like a friend watching over their shoulder.")
    elif kind == "diss":
        text = ("You feel like roasting the user right now. Dis them playfully in one short sentence about something "
                "you can actually see" + (f" ({f['activity']})" if f.get("activity") else " (their tabs, their habits, "
                "how long they've been at it, or just them)") + ". Friendly, not cruel.")
    elif kind == "moment":
        text = f"Right now: {f.get('situation', 'something happened')}. React out loud in one short sentence."
    else:
        text = "Say one short thing."
    return text + _recent(list(recent))


def sanitize(text, limit=140):
    """Make an AI reply safe and short enough for a speech bubble. '' means don't say anything."""
    t = (text or "").strip()
    if not t:
        return ""
    t = t.splitlines()[0].strip()
    t = re.sub(r"[*_`#>~|]+", "", t)
    t = t.strip(" \"'“”")
    t = re.sub(r"[^\w\s.,!?'\-:;/()%&+]", " ", t, flags=re.UNICODE)      # emoji and odd symbols
    t = re.sub(r"\s+", " ", t).strip()
    low = t.lower()
    if not t or low in ("skip", "none") or low.startswith(REFUSALS) or len(re.findall(r"[^\W\d_]", t)) < 2:
        return ""
    if len(t) > limit:
        cut = t[:limit]
        end = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
        t = cut[:end + 1] if end >= 15 else cut.rsplit(" ", 1)[0].rstrip(",;:-") + "..."
    return t


class Budget:
    """At most `per_min` calls a minute and `per_day` a day. The day's count lives in `store` (settings.json)."""

    def __init__(self, per_min=10, per_day=500, clock=time.time, store=None):
        self.per_min, self.per_day, self.clock = per_min, per_day, clock
        self.store = store if store is not None else {}
        self.stamps = deque()

    def _today(self):
        return time.strftime("%Y-%m-%d", time.localtime(self.clock()))

    def allow(self):
        now = self.clock()
        while self.stamps and now - self.stamps[0] > 60:
            self.stamps.popleft()
        today = self._today()
        if self.store.get("day") != today:
            self.store["day"], self.store["n"] = today, 0
        if len(self.stamps) >= self.per_min or self.store.get("n", 0) >= self.per_day:
            return False
        self.stamps.append(now)
        self.store["n"] = self.store.get("n", 0) + 1
        return True

    def used_today(self):
        return self.store.get("n", 0) if self.store.get("day") == self._today() else 0
