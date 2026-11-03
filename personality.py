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
        "sleepy": ["*yawns in glitch*", "Eyes... buffering.", "Five more minutes.", "So. Tired. Pixels."],
        "lonely": ["Hello? Anyone?", "You're busy. It's fine. It's fine.", "I counted your tabs. Twice.",
                   "Poke me. Please."],
        "sassy": ["Wow. Ignoring me. Bold.", "I'm not mad. I'm just glitching.", "Cool cool cool.",
                  "Some of us have feelings."],
        "playful": ["Race you to the corner!", "I feel like dancing.", "Bet I can teleport faster than you can blink.",
                    "Ooh, what are we doing?", "*does a little hop*"],
        "content": ["...", "*glitches*", "Just vibing.", "Tiny step. You got this.", "Still here.", "Nice tabs. So many."],
    },
    "poke": {
        "sleepy": ["Mmf. Five more minutes.", "...hm? Boop.", "Rude. I was resting."],
        "lonely": ["You noticed me!", "Hi hi hi!", "Yay, a poke!"],
        "sassy": ["Poke me again. I dare you.", "Rude. Also, hi.", "Finger. Away."],
        "playful": ["Boop! Again!", "Hehe!", "Catch me!"],
        "content": ["Hi!", "Boop.", "Yes?", "Hello hello.", "Poke accepted."],
    },
    "wake": {
        "sleepy": ["...hm? Oh. Hi.", "I was dreaming in 8 colours."],
        "lonely": ["You came back!", "Oh! Hi!"],
        "sassy": ["Oh, NOW you want me."],
        "playful": ["Up up up!"],
        "content": ["Morning. Or whatever it is.", "Hm? Hi."],
    },
    "checkin": [
        "Water break? Go on.", "Shoulders down. Unclench your jaw.", "Stand up and stretch for a sec.",
        "What are you working on right now?", "Look away from the screen for 20 seconds.",
        "Have you eaten recently?",
    ],
    "late": ["It's really late. Sleep is a feature, you know.", "Bed? Bed. I'll watch the pixels.",
             "Whatever it is, it'll still be there tomorrow."],
}

GREET = {
    "morning": ["Morning! Brain online?", "Good morning. Coffee first, then world.", "Up already? Respect."],
    "afternoon": ["Afternoon. Hydrate.", "Hey. Halfway through the day.", "Welcome back."],
    "evening": ["Evening. Wind down soon?", "Hey. Long day?", "Good evening. Pixels are glowing."],
    "night": ["It's late... still working?", "Night owl mode. I approve. Mostly.", "Shouldn't you be asleep?"],
}

OFFLINE = [
    (("hello", "hi ", "hey", "yo"), ["Hey. Good to see you.", "Hi hi.", "Hello hello."]),
    (("thank",), ["Anytime.", "You're welcome. I'm very helpful. For a sprite.", "Aw. Stop. Keep going."]),
    (("stuck", "help"), ["Pick the smallest next step and do only that. What is it?",
                         "Write one sentence about what you're trying to do. Then one tiny action."]),
    (("tired", "sleep"), ["Then rest. Seriously. I'll keep watch.", "A nap is a valid strategy."]),
    (("bored",), ["Want me to dance? Right-click me.", "Go get water, then decide. Boredom likes movement."]),
    (("joke",), ["I tried to catch a bug. It glitched away.", "Why was the pixel calm? No edge cases. Edge. Get it?"]),
    (("love", "cute"), ["...glitches happily.", "Don't make me blush in 5 colours."]),
]
OFFLINE_FALLBACK = {
    "sleepy": ["Mm. Tell me more, I'm half asleep.", "...yeah. Sure. Zzz."],
    "lonely": ["I like it when you talk to me.", "Keep going, I'm listening."],
    "sassy": ["Mhm. Riveting.", "Say more. Or don't."],
    "playful": ["Ooh! Go on!", "Wait, really? Tell me everything."],
    "content": ["Hm. Tell me more.", "I'm listening.", "Go on."],
}


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
