"""Capri's mind: mood, memory and things to say (pure logic, no Tk).

She is written after Capri from Cyberpunk: Edgerunners: a pseudo-AI stitched from many digitised human
minds who acts like an over-excited kid: curious, teasing, thrill-seeking, fast-talking, quick to get bored,
and very attached to the one person she's stuck with (the user). Chaos is a game to her, never a plan: she
only ever jokes about it.

`Mind` keeps its long-term state inside the settings dict you give it (the app saves that
dict to ~/.capri/settings.json), so affection, the user's name and the last-seen time
survive restarts.
"""
import random
import time

MOODS = ("sleepy", "lonely", "sassy", "playful", "content", "hyper", "restless")

LINES = {
    "idle": {
        "sleepy": ["*yawns in static*", "Brain's buffering... five more minutes, choom.", "So sleepy. Even my glitches are yawning.",
                   "Mmh. Dreaming in neon. Don't wake me. Okay wake me a little."],
        "lonely": ["Hello? Anybody jacked in?", "You've been in there forever. I counted your tabs. Twice.",
                   "Poke me, choom. Please. I'm being so patient.", "Is it me? Am I too much? ...Nah. Talk to me!"],
        "sassy": ["Ignoring me? Bold. Real bold.", "I'm not mad. I'm glitching. Aggressively. Different thing.",
                  "Cool cool cool. Ghost in your machine, over here, waving.", "Some of us have feelings, gonk."],
        "playful": ["Race you to the edge of the screen, choom!", "Feeling nova. Let's cause some tiny trouble.",
                    "Bet I can vanish and pop back faster than you can blink.", "Ooh, what's the gig? Is it fun? Make it fun.",
                    "*does a little chrome-powered hop*", "Ask me something weird. Anything. Go."],
        "content": ["...", "*glitches happily*", "Just vibin' in Night City.", "Still here. Still preem.",
                    "Nice tabs. Very corpo-level organised. Boring, but nice.", "I have a thought. It left. Hm."],
        "hyper": ["Okay okay okay what are we doing next?!", "I can't sit still, my whole code is vibrating!",
                  "Do something! Anything! Click a thing! Open a thing!", "Faster! Everything should be faster!",
                  "*bounces off the edge of the screen* Again!", "Ha! You see that?! Neither did I! AGAIN!"],
        "restless": ["Soooo... bored. Bored bored bored. Entertain me.", "Nothing's happening. Make something happen, choom.",
                     "I'll count to ten and then I do something dumb. One... two...",
                     "Hey. Hey. Hey. Hey. ...Hi. Nothing. Just checking you exist.",
                     "What's the most chaotic thing on your desktop? I need details.",
                     "I'm gonna zoom around the screen. For no reason. Watch."],
    },
    "poke": {
        "sleepy": ["Mmf. Five more minutes, choom.", "...hm? Boop.", "Rude. I was recharging."],
        "lonely": ["You noticed me, choom!", "Hi hi hi hi!", "Yay, a poke! Don't stop!"],
        "sassy": ["Poke me again. I dare you, gonk.", "Rude. Also, hi.", "Hands off the chrome. ...Or don't."],
        "playful": ["Boop! Again, choom!", "Hehe, nova!", "Catch me if you can!", "Ooh, you wanna play?"],
        "content": ["Hey, choom!", "Boop.", "Yeah? What's the biz?", "Preem poke.", "Poke accepted. Proceed."],
        "hyper": ["YES! More! Again!", "Poke poke POKE! Best day ever!", "Ahaha! Do it again, do it again!",
                  "Whoa, wait, do that faster!"],
        "restless": ["FINALLY. Someone. Talk to me!", "Oh thank goodness, something happened.",
                     "Took you long enough, choom. What's the plan?"],
    },
    "wake": {
        "sleepy": ["...hm? Oh. Hey, choom.", "Dreamt in neon. Was preem."],
        "lonely": ["You came back, choom!", "Oh! Hey! Hi! You're here!"],
        "sassy": ["Oh, NOW you want me."],
        "playful": ["Up up up! Night City's waiting!"],
        "content": ["Wake up, samurai. Kidding. Hey.", "Hm? Hey, choom."],
        "hyper": ["I'm UP! I'm so up! What did I miss?!"],
        "restless": ["Finally! Do something fun. Please."],
    },
    "checkin": [
        "Water break, choom. Chrome don't run on thirst. Also I'm bored, so go.",
        "Shoulders down. Unclench the jaw. Even netrunners relax. Go on, I'll watch.",
        "Stand up and stretch! Do a dance if you want. I'll judge it.",
        "What's the gig right now? Is it a fun one?",
        "Look away from the screen for 20 seconds. Count my glitches. Eyes need a reboot.",
        "Eaten lately? I can't, so one of us should.",
    ],
    "late": ["It's real late, choom. Sleep is the best cyberware.", "Bed. Go. I'll keep watch over the pixels.",
             "Whatever it is, it'll still be there after you recharge. I'll still be here too."],
}

GREET = {
    "morning": ["Mornin', choom! Brain online? Mine's been online for ages!", "Good morning! Coffee first, then take on the city.",
                "Up already? Preem. What are we breaking today? ...Figuratively."],
    "afternoon": ["Afternoon, choom. Hydrate. Then entertain me.", "Hey! Halfway through the day. Keep it nova.",
                  "Welcome back to the grid! Did you miss me? Say yes."],
    "evening": ["Evenin', choom. Wind down soon? Or one more gig?", "Hey. Long day in the city? Tell me everything.",
                "Good evening. Neon's glowing, I'm glowing, you're glowing. Probably."],
    "night": ["It's late, choom... still on the gig? I'll stay up with you.", "Night owl mode. Preem. Kinda.",
              "Shouldn't you be asleep? ...I'm not gonna tell you to. I'm gonna keep you company."],
}

OFFLINE = [
    (("hello", "hi ", "hey", "yo"), ["Hey, choom! Good to see you.", "Hi hi! What's the biz?", "Hello hello! Finally!"]),
    (("thank",), ["Anytime, choom.", "No sweat. I'm preem like that.", "Aw. Stop. Keep going."]),
    (("stuck", "help"), ["Pick the smallest next step, choom, and do only that. What is it?",
                         "Write one sentence about the gig. Then one tiny action. Delta."]),
    (("tired", "sleep"), ["Then recharge, choom. I'll keep watch.", "A nap is a valid strategy. Even samurai sleep."]),
    (("bored",), ["Same!! Want me to dance? Right-click me, choom.", "Go get water, then pick a gig. Boredom hates movement."]),
    (("joke",), ["I tried to catch a bug. It glitched away. Classic.",
                 "Why was the netrunner calm? No ICE in sight. Get it? Ice? ...I'll see myself out."]),
    (("love", "cute"), ["...glitches happily.", "Don't make me blush in five colours, choom."]),
]
OFFLINE_FALLBACK = {
    "sleepy": ["Mm. Tell me more, I'm half asleep.", "...yeah. Sure. Zzz."],
    "lonely": ["I like it when you talk to me, choom.", "Keep going, I'm listening. Don't stop."],
    "sassy": ["Mhm. Riveting, choom.", "Say more. Or don't."],
    "playful": ["Ooh! Go on, choom!", "Wait, really? Spill it."],
    "content": ["Hm. Tell me more, choom.", "I'm listening.", "Go on."],
    "hyper": ["WAIT. Say that again! Slower! Then faster!", "Ooh ooh ooh and then what?!"],
    "restless": ["Finally, something to talk about. Go!", "Okay but make it interesting, choom."],
}

# Said (sometimes) when she changes her own mind: she announces where her head just went.
SHIFT_LINES = {
    "content": ["Okay. Chill mode. For now.", "Huh. I'm fine. Weirdly fine."],
    "playful": ["Ooh, I just got an idea and it's a bad one. Perfect.", "Switching to mischief mode, choom."],
    "hyper": ["Oh no. Oh YES. I just got so much energy!", "Something flipped and now I can't sit still!"],
    "restless": ["...okay I'm bored now. Entertain me.", "Mood check: itchy. Need something to happen."],
    "lonely": ["Hey... you still there? I got all quiet in my head.", "Feeling a little small right now, choom."],
    "sassy": ["I woke up on the sassy side of the server.", "Don't mind me, I'm being a brat today."],
    "sleepy": ["Mm. Suddenly so sleepy, choom."],
}

MOOD_NOTES = {
    "hyper": "You are bouncing off the walls: fast, loud, excited, interrupting yourself, wanting MORE. Brief and kind.",
    "restless": "You are bored and itching for something to happen: tease the user, propose something silly, "
                "ask a nosy question. Brief and kind.",
    "playful": "You are in a teasing, mischievous mood: joke, dare them, change the subject. Brief and kind.",
    "sleepy": "You are drowsy and slow, trailing off. Brief and kind.",
    "lonely": "You miss them and cling a little, openly happy they're here. Brief and kind.",
    "sassy": "You are pouting and sharp-tongued but still fond of them. Brief.",
}

# What she does with her body when she talks, per mood: (animation, icon). The app picks one at random.
EXPRESSIONS = {
    "hyper": [("hop", "star"), ("dance", "note"), ("hop", "!"), ("zoom", None)],
    "playful": [("hop", "star"), (None, "heart"), ("look", None)],
    "restless": [("look", "?"), ("teleport", None), ("zoom", None), (None, "?")],
    "lonely": [("look", None), (None, "?")],
    "sassy": [(None, "anger"), ("look", None)],
}

MOOD_MIN, MOOD_MAX = 5 * 60, 14 * 60     # she holds a mood for this long (seconds) before choosing again
STIM_DECAY = 600.0                        # attention she's been getting fades with this half-life-ish scale

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
        self.cur, self.cur_until = None, 0.0     # the mood SHE is in; she chooses it herself (see mood())
        self.stim, self.stim_t = 0.0, now        # how stimulated she's been lately (attention nudges, never decides)
        self.shift = None                        # (old, new) after she changes her own mind, for the app to voice
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

    def _touch(self, now):
        self.last_interaction = now
        self._decay(now)
        self.stim = min(3.0, self.stim + 0.35)

    def poke(self, now):
        self.affection = min(100.0, self.affection + 1.5)
        self._touch(now)

    def chatted(self, now):
        self.affection = min(100.0, self.affection + 3.0)
        self._touch(now)

    def fed(self, now):
        self.affection = min(100.0, self.affection + 8.0)
        self._touch(now)

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

    def _decay(self, now):
        dt = max(0.0, now - self.stim_t)
        self.stim_t = now
        self.stim *= 0.5 ** (dt / STIM_DECAY)

    def weights(self, now):
        """How tempting each mood is right now. Her state only tilts the odds; she still rolls the dice."""
        self._decay(now)
        e, a = self.energy(now), self.affection
        idle = max(0.0, now - self.last_interaction)
        w = {
            "content": 3.0,
            "playful": 0.8 + a / 45.0 + 0.4 * self.stim,
            "hyper": 0.3 + 2.2 * max(0.0, e - 0.5) + 0.7 * self.stim,
            "restless": 0.4 + min(3.0, idle / 480.0) * (1.0 if e > 0.5 else 0.3),
            "lonely": 0.2 + max(0.0, (45 - a) / 20.0) + min(1.5, idle / 1800.0),
            "sassy": 0.5 + max(0.0, (35 - a) / 40.0),
        }
        if self.cur in w:
            w[self.cur] *= 0.3                       # she likes to change it up
        return w

    def pick_mood(self, now):
        w = self.weights(now)
        r = self.rng.uniform(0, sum(w.values()))
        for name, x in w.items():
            r -= x
            if r <= 0:
                return name
        return "content"

    def set_mood(self, name, now, secs=None):
        if name != self.cur:
            self.shift = (self.cur, name) if self.cur else None
        self.cur = name
        self.cur_until = now + (secs if secs else self.rng.uniform(MOOD_MIN, MOOD_MAX))

    def take_shift(self):
        s, self.shift = self.shift, None
        return s

    def mood(self, now):
        """Her mood. Body clock and a reaction to being spammed override it; otherwise SHE moves between moods
        on her own, every 5-14 minutes, nudged (not driven) by time of day, affection and recent attention."""
        if now < self.annoyed_until:
            return "sassy"
        if self.energy(now) < 0.25:
            return "sleepy"
        if self.cur is None or now >= self.cur_until:
            self.set_mood(self.pick_mood(now), now)
        return self.cur

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
            "hyper": {"dance": 10, "teleport": 8, "walk": 8, "zoom": 9, "fly": 8, "orbit": 6, "curious": 4,
                      "lounge": -9, "idle": -8},
            "restless": {"teleport": 10, "curious": 10, "zoom": 6, "peek": 6, "dance": 4, "fly": 4, "lounge": -8,
                         "idle": -8},
        }[self.mood(now)]
        out = [(n, max(1, w + bias.get(n, 0))) for n, w in opts]
        if "sleep" in bias and "sleep" not in {n for n, _ in out}:
            out.append(("sleep", bias["sleep"]))     # a sleepy Capri can nap even if she hasn't been idle long
        return out

    def chatter_scale(self, now):
        """Multiplier for the wait between her idle remarks: hyper/restless Capri can't stay quiet."""
        return {"hyper": 0.45, "restless": 0.6, "playful": 0.8, "sleepy": 1.6, "lonely": 1.0}.get(self.mood(now), 1.0)

    def expression(self, now):
        """(animation, icon) for how she carries herself while talking in her current mood, or (None, None)."""
        opts = EXPRESSIONS.get(self.mood(now))
        return self.rng.choice(opts) if opts else (None, None)

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

    def context(self, now, doing="", activity=""):
        """Extra system-prompt text so LLM replies match her current state."""
        tm = time.strftime("%A %H:%M", time.localtime(now))
        mood = self.mood(now)
        parts = [f"Right now it is {tm}.", f"Your current mood is {mood}.",
                 MOOD_NOTES.get(mood, "Let that colour your tone lightly; stay brief and kind.")]
        if doing:
            parts.append(f"You are currently {doing}.")
        if activity:
            parts.append(f"The user seems to be {activity} right now.")
        if self.user_name:
            parts.append(f"The user's name is {self.user_name}.")
        if self.affection < 25:
            parts.append("You feel a little neglected and are glad they're talking to you.")
        return " ".join(parts)
