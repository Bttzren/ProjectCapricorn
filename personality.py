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
        "sleepy": ["*yawns in static*", "Battery's low, choom. Brain's buffering.", "Five more minutes, then I flatline for real.",
                   "So tired. Even my chrome's yawning."],
        "lonely": ["Hello? Anybody jacked in?", "You're deep in the biz. It's fine. It's fine.",
                   "I counted your tabs. Twice. That's a lot, choom.", "Poke me, choom. Please."],
        "sassy": ["Ignoring me? Real preem, choom.", "I'm not mad. I'm just glitching. Aggressively.",
                  "Cool cool cool. Ghost in your machine, over here.", "Some of us got feelings, gonk."],
        "playful": ["Race you to the edge of the screen, choom!", "Feeling nova. Let's cause some trouble.",
                    "Bet I can delta outta here faster than you can blink.", "Ooh, what's the gig?",
                    "*does a little chrome-powered hop*"],
        "content": ["...", "*glitches*", "Just vibin' in Night City.", "Tiny step, choom. You got this.",
                    "Still here. Still preem.", "Nice tabs. Corpo-level organized."],
    },
    "poke": {
        "sleepy": ["Mmf. Five more minutes, choom.", "...hm? Boop.", "Rude. I was recharging."],
        "lonely": ["You noticed me, choom!", "Hi hi hi!", "Yay, a poke!"],
        "sassy": ["Poke me again. I dare you, gonk.", "Rude. Also, hi.", "Hands off the chrome."],
        "playful": ["Boop! Again, choom!", "Hehe, nova!", "Catch me if you can!"],
        "content": ["Hey, choom!", "Boop.", "Yeah? What's the biz?", "Preem poke.", "Poke accepted."],
    },
    "wake": {
        "sleepy": ["...hm? Oh. Hey, choom.", "Dreamt in neon. Was preem."],
        "lonely": ["You came back, choom!", "Oh! Hey!"],
        "sassy": ["Oh, NOW you want me."],
        "playful": ["Up up up! Night City's waiting!"],
        "content": ["Wake up, samurai. Kidding. Hey.", "Hm? Hey, choom."],
    },
    "checkin": [
        "Water break, choom. Chrome don't run on thirst.",
        "Shoulders down. Unclench the jaw. Even netrunners relax.",
        "Stand up and stretch. Flatlining at a desk ain't preem.",
        "What's the gig right now?",
        "Look away from the screen for 20 seconds. Eyes need a reboot.",
        "Eaten lately? Even edgerunners eat.",
    ],
    "late": ["It's real late, choom. Sleep is the best cyberware.", "Bed. Go. I'll keep watch over the pixels.",
             "Whatever it is, it'll still be there after you recharge."],
}

GREET = {
    "morning": ["Mornin', choom! Brain online?", "Good morning. Coffee first, then take on the city.", "Up already? Preem."],
    "afternoon": ["Afternoon, choom. Hydrate.", "Hey. Halfway through the day. Keep it nova.", "Welcome back to the grid."],
    "evening": ["Evenin', choom. Wind down soon?", "Hey. Long day in the city?", "Good evening. Neon's glowing."],
    "night": ["It's late, choom... still on the gig?", "Night owl mode. Preem. Kinda.", "Shouldn't you be asleep, choom?"],
}

OFFLINE = [
    (("hello", "hi ", "hey", "yo"), ["Hey, choom. Good to see you.", "Hi hi. What's the biz?", "Hello hello, choom."]),
    (("thank",), ["Anytime, choom.", "No sweat. I'm preem like that.", "Aw. Stop. Keep going."]),
    (("stuck", "help"), ["Pick the smallest next step, choom, and do only that. What is it?",
                         "Write one sentence about the gig. Then one tiny action. Delta."]),
    (("tired", "sleep"), ["Then recharge, choom. I'll keep watch.", "A nap is a valid strategy. Even samurai sleep."]),
    (("bored",), ["Want me to dance? Right-click me, choom.", "Go get water, then pick a gig. Boredom hates movement."]),
    (("joke",), ["I tried to catch a bug. It glitched away. Classic.",
                 "Why was the netrunner calm? No ICE in sight. Get it? Ice? ...I'll see myself out."]),
    (("love", "cute"), ["...glitches happily.", "Don't make me blush in five colors, choom."]),
]
OFFLINE_FALLBACK = {
    "sleepy": ["Mm. Tell me more, I'm half asleep.", "...yeah. Sure. Zzz."],
    "lonely": ["I like it when you talk to me, choom.", "Keep going, I'm listening."],
    "sassy": ["Mhm. Riveting, choom.", "Say more. Or don't."],
    "playful": ["Ooh! Go on, choom!", "Wait, really? Spill it."],
    "content": ["Hm. Tell me more, choom.", "I'm listening.", "Go on."],
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
            "sleepy": {"sleep": 25, "lounge": 12, "walk": -15, "dance": -4, "teleport": -8},
            "lonely": {"curious": 14, "idle": 6, "teleport": -6},
            "sassy": {"teleport": 8, "dance": -3, "curious": -6},
            "playful": {"dance": 8, "teleport": 8, "walk": 10, "curious": 6, "lounge": -6},
            "content": {},
        }[self.mood(now)]
        out = [(n, max(1, w + bias.get(n, 0))) for n, w in opts]
        if "sleep" in bias and "sleep" not in {n for n, _ in out}:
            out.append(("sleep", bias["sleep"]))     # a sleepy Capri can nap even if she hasn't been idle long
        return out

    def line(self, kind, now):
        pool = LINES[kind]
        if isinstance(pool, dict):
            pool = pool.get(self.mood(now)) or pool["content"]
        if kind == "checkin" and hour_of(now) < 5:
            pool = LINES["late"]
        return self.rng.choice(pool)

    def greeting(self, now):
        text = self.rng.choice(GREET[part_of_day(hour_of(now))])
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
                return self.rng.choice(replies) + " (No API key set, so I'm in offline mode.)"
        return self.rng.choice(OFFLINE_FALLBACK[self.mood(now)]) + " (Offline mode: add a key to chat for real.)"

    def context(self, now, doing=""):
        """Extra system-prompt text so LLM replies match her current state."""
        tm = time.strftime("%A %H:%M", time.localtime(now))
        parts = [f"Right now it is {tm}.", f"Your current mood is {self.mood(now)}.",
                 "Let that colour your tone lightly; stay brief and kind."]
        if doing:
            parts.append(f"You are currently {doing}.")
        if self.user_name:
            parts.append(f"The user's name is {self.user_name}.")
        if self.affection < 25:
            parts.append("You feel a little neglected and are glad they're talking to you.")
        return " ".join(parts)
