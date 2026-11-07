"""Capri's mind: mood, memory and things to say (pure logic, no Tk).

`Mind` keeps its long-term state inside the settings dict you give it (the app saves that
dict to ~/.capri/settings.json), so affection, the user's name and the last-seen time
survive restarts.
"""
import random
import time

MOODS = ("sleepy", "lonely", "sassy", "playful", "content")

LINES = {
    "idle": {
        "sleepy": ["*yawns in static*", "Running on fumes over here.", "If I blink too long, assume I'm defragging.",
                   "Low power mode. Talk slow.", "Everything's fine. I'm just horizontal on the inside."],
        "lonely": ["Hello? Anybody jacked in?", "I counted your tabs. Twice. It didn't help.",
                   "You're busy. I get it. I'm also busy. Sitting.", "Poke me if you need anything. Or nothing.",
                   "Quiet in here. Suspiciously quiet."],
        "sassy": ["Ignoring me? Bold strategy.", "I'm not mad. I'm just glitching. Aggressively.",
                  "Cool. Love being wallpaper. Very corpo of you.", "Some of us have feelings, gonk.", "Noted. Filed under 'rude'."],
        "playful": ["Race you to the edge of the screen.", "I could reorganize your desktop. I won't. Probably.",
                    "Bet I can delta out of here before you blink.", "Feeling nova. What are we breaking today?",
                    "*does a little hop*", "Got a gig for me? Small one's fine."],
        "content": ["...", "*glitches*", "Just vibing in Night City.", "Still here. Still preem.",
                    "Nice tabs. Very organized. Kind of.", "One thing at a time. You've got this.",
                    "This is a good spot. I'm keeping it."],
    },
    "poke": {
        "sleepy": ["Mmf. Five more minutes.", "...hm? Boop.", "Rude. I was recharging."],
        "lonely": ["Oh! Hi.", "Finally, some attention.", "Hi hi hi."],
        "sassy": ["Poke me again. I dare you.", "Rude. Also, hi.", "Hands off the chrome."],
        "playful": ["Boop. Again.", "Hehe. Missed me.", "Catch me if you can."],
        "content": ["Hey.", "Boop.", "Yeah? What's up?", "Poke accepted.", "Present."],
    },
    "wake": {
        "sleepy": ["...hm? Oh. Hey.", "Dreamt in neon. Was nice."],
        "lonely": ["You came back.", "Oh! Hey!"],
        "sassy": ["Oh, NOW you want me."],
        "playful": ["Up up up. The city's waiting."],
        "content": ["Wake up, samurai. Kidding. Hey.", "Hm? Hey, choom."],
    },
    "checkin": [
        "Water break. Chrome doesn't run on thirst.",
        "Shoulders down. Unclench the jaw.",
        "Stand up and stretch. Flatlining at a desk isn't preem.",
        "What's the gig right now? Say it in one line.",
        "Look away from the screen for 20 seconds. Eyes need a reboot.",
        "Eaten lately? Even edgerunners eat.",
    ],
    "late": ["It's really late. Sleep is the best cyberware.", "Bed. Go. I'll keep watch over the pixels.",
             "Whatever it is, it'll still be there after you sleep."],
}

GREET = {
    "morning": ["Morning. Brain online yet?", "Good morning. Coffee first, then the city.", "Up already? Respect."],
    "afternoon": ["Afternoon. Drink some water.", "Halfway through the day. Keep going.", "Welcome back to the grid."],
    "evening": ["Evening. Winding down soon?", "Hey. Long day?", "Good evening. Neon's on."],
    "night": ["It's late... still at it?", "Night owl mode. Bold.", "Shouldn't you be asleep, choom?"],
}

OFFLINE = [
    (("hello", "hi ", "hey", "yo"), ["Hey. Good to see you.", "Hi. What's up?", "Hello hello."]),
    (("thank",), ["Anytime.", "No sweat, choom.", "Aw. Stop. Keep going."]),
    (("stuck", "help"), ["Pick the smallest next step and do only that. What is it?",
                         "Write one sentence about the problem. Then one tiny action."]),
    (("tired", "sleep"), ["Then recharge. I'll keep watch.", "A nap is a valid strategy. Even samurai sleep."]),
    (("bored",), ["Want me to dance? Right-click me.", "Get water, then pick one thing. Boredom hates movement."]),
    (("joke",), ["I tried to catch a bug. It glitched away. Classic.",
                 "Why was the netrunner calm? No ICE in sight. ...I'll see myself out."]),
    (("love", "cute"), ["...glitches happily.", "Don't make me blush in five colors."]),
]
OFFLINE_FALLBACK = {
    "sleepy": ["Mm. Tell me more, I'm half asleep.", "...yeah. Sure. Zzz."],
    "lonely": ["I like it when you talk to me.", "Keep going, I'm listening."],
    "sassy": ["Mhm. Riveting.", "Say more. Or don't."],
    "playful": ["Ooh. Go on.", "Wait, really? Spill it."],
    "content": ["Hm. Tell me more.", "I'm listening.", "Go on."],
}

SLANG = ("choom", "preem", "nova", "gonk", "eddies", "chrome", "delta", "flatline", "gig", "biz", "corpo", "netrunner")


def hour_of(now):
    return time.localtime(now).tm_hour


def part_of_day(hour):
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


class Mind:
    def __init__(self, store, now=None, rng=None):
        self.s = store
        self.rng = rng or random.Random()
        now = time.time() if now is None else now
        self.affection = float(self.s.get("affection", 50.0))
        self.last_seen = float(self.s.get("last_seen", now))
        away_h = max(0.0, (now - self.last_seen) / 3600.0)
        self.away_hours = away_h
        self.affection = max(0.0, min(100.0, self.affection - min(40.0, away_h * 0.8)))
        self.last_interaction = now
        self.annoyed_until = 0.0
        self.last_tick = now
        self.sync(now)

    # -- persistence ------------------------------------------------------------
    @property
    def user_name(self):
        return self.s.get("user_name", "")

    @user_name.setter
    def user_name(self, v):
        self.s["user_name"] = v.strip()[:40]

    def sync(self, now):
        self.s["affection"] = round(self.affection, 1)
        self.s["last_seen"] = now

    # -- events -----------------------------------------------------------------
    def tick(self, now):
        """Call every so often: affection slowly fades while you ignore her."""
        dt = max(0.0, now - self.last_tick)
        self.last_tick = now
        if now - self.last_interaction > 20 * 60:
            self.affection = max(0.0, self.affection - dt / 3600.0 * 6.0)
        self.sync(now)

    def poke(self, now):
        self.affection = min(100.0, self.affection + 1.5)
        self.last_interaction = now

    def chatted(self, now):
        self.affection = min(100.0, self.affection + 3.0)
        self.last_interaction = now

    def fed(self, now):
        self.affection = min(100.0, self.affection + 8.0)
        self.last_interaction = now

    def annoyed(self, now, secs=300):
        self.annoyed_until = now + secs
        self.last_interaction = now

    # -- state ------------------------------------------------------------------
    def energy(self, now):
        h = hour_of(now)
        base = 0.15 if h < 6 else 0.6 if h < 9 else 0.85 if h < 18 else 0.6 if h < 22 else 0.3
        if now - self.last_interaction < 300:
            base += 0.15
        return max(0.0, min(1.0, base))

    def mood(self, now):
        if now < self.annoyed_until:
            return "sassy"
        if self.energy(now) < 0.25:
            return "sleepy"
        if self.affection < 25:
            return "lonely"
        if self.affection > 65 and self.energy(now) > 0.5:
            return "playful"
        return "content"

    # -- behaviour --------------------------------------------------------------
    def adjust_weights(self, opts, now):
        """opts: list of (name, weight). Returns a new list biased by mood."""
        bias = {
            "sleepy": {"sleep": 25, "lounge": 12, "walk": -15, "dance": -4, "teleport": -8, "fly": -6, "zoom": -3},
            "lonely": {"curious": 14, "idle": 6, "teleport": -6, "orbit": 10},
            "sassy": {"teleport": 8, "dance": -3, "curious": -6, "zoom": 4},
            "playful": {"dance": 8, "teleport": 8, "walk": 10, "curious": 6, "lounge": -6, "fly": 8, "zoom": 5,
                        "orbit": 4},
            "content": {},
        }[self.mood(now)]
        out = [(n, max(1, w + bias.get(n, 0))) for n, w in opts]
        if "sleep" in bias and "sleep" not in {n for n, _ in out}:
            out.append(("sleep", bias["sleep"]))     # a sleepy Capri can nap even if she hasn't been idle long
        return out

    def pick(self, key, pool):
        """Random line from `pool` without repeats: every line is used once before any comes back, and the
        last one isn't the first of the next round."""
        bags = self.__dict__.setdefault("_bags", {})
        bag = bags.get(key)
        if not bag or not set(bag) <= set(pool):
            last = self.__dict__.setdefault("_last", {}).get(key)
            bag = list(pool)
            self.rng.shuffle(bag)
            if len(bag) > 1 and bag[-1] == last:
                bag[0], bag[-1] = bag[-1], bag[0]
            bags[key] = bag
        choice = bag.pop()
        self.__dict__.setdefault("_last", {})[key] = choice
        return choice

    def line(self, kind, now):
        pool, key = LINES[kind], kind
        if isinstance(pool, dict):
            key = f"{kind}:{self.mood(now)}"
            pool = pool.get(self.mood(now)) or pool["content"]
        if kind == "checkin" and hour_of(now) < 5:
            pool, key = LINES["late"], "late"
        return self.pick(key, pool)

    def greeting(self, now):
        part = part_of_day(hour_of(now))
        text = self.pick("greet:" + part, GREET[part])
        name = self.user_name
        if name:
            text = text.rstrip(".!?") + f", {name}."
        if self.away_hours >= 3:
            text = f"{self.away_hours:.0f} hours. I counted. " + text
        return text

    def offline_reply(self, text, now):
        low = " " + text.lower() + " "
        for keys, replies in OFFLINE:
            if any(k in low for k in keys):
                return self.pick("offline:" + keys[0], replies) + " (No API key set, so I'm in offline mode.)"
        mood = self.mood(now)
        return self.pick("fallback:" + mood, OFFLINE_FALLBACK[mood]) + " (Offline mode: add a key to chat for real.)"

    def context(self, now, doing="", activity=""):
        """Extra system-prompt text so LLM replies match her current state."""
        tm = time.strftime("%A %H:%M", time.localtime(now))
        parts = [f"Right now it is {tm}.", f"Your current mood is {self.mood(now)}.",
                 "Let that colour your tone lightly; stay brief and kind."]
        if doing:
            parts.append(f"You are currently {doing}.")
        if activity:
            parts.append(f"The user seems to be {activity} right now.")
        if self.user_name:
            parts.append(f"The user's name is {self.user_name}.")
        if self.affection < 25:
            parts.append("You feel a little neglected and are glad they're talking to you.")
        return " ".join(parts)
