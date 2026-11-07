"""Game mode: Capri hypes your kills and roasts your deaths (pure logic, no Tk).

She never reads a game's memory or files. Events come from YOU (/kill, /death, ...) or from the
optional screen-region detectors in reactor.py. This module only turns events into commentary and
keeps the session's K/D.
"""
import random
import time

# key -> (display name, window-title keywords)
GAMES = {
    "valorant": ("Valorant", ("valorant",)),
    "cs2": ("Counter-Strike 2", ("counter-strike",)),
    "apex": ("Apex Legends", ("apex legends",)),
    "overwatch": ("Overwatch", ("overwatch",)),
    "fortnite": ("Fortnite", ("fortnite",)),
    "league": ("League of Legends", ("league of legends",)),
    "rocket": ("Rocket League", ("rocket league",)),
    "cyberpunk": ("Cyberpunk 2077", ("cyberpunk 2077",)),
    "other": ("your game", ()),
}
EVENT_KINDS = ("kill", "death", "ace", "clutch", "round_win", "round_loss", "match_win", "match_loss")
LEVELS = ("off", "mild", "spicy")          # how hard she roasts you: off = only supportive

BIG = ("ace", "clutch", "match_win", "match_loss")       # always get a line, even during the cooldown
MIN_GAP = 3.0                                             # seconds between ordinary kill/death lines

KILL = ["Clean! Nova.", "Preem shot, choom!", "Delete him.", "Easy money.", "One down.",
        "Crisp. Do it again.", "That's the aim I like to see."]
MULTI = {2: "Double kill! Keep going!", 3: "TRIPLE! Choom is cooking!", 4: "QUAD! Don't choke now!"}
KILL_STREAK = ["{n} kills in a row. You're on fire.", "Streak of {n}. Don't get cocky.",
               "{n} straight. Somebody stop this person."]
GOOD_KD = ["{k}/{d}. Carrying the whole lobby.", "{k} and {d}. Menace behavior, choom."]
ACE = ["ACE!! Absolute legend. Screenshot that.", "FIVE! Is this even fair?!"]
CLUTCH = ["CLUTCH! Ice in your veins, choom!", "That clutch was preem. I screamed. Silently."]
ROUND_WIN = ["Round! Keep it rolling.", "W. Next one.", "Nova round."]
MATCH_WIN = ["GG! Victory! Preem work.", "WIN! Go touch grass. Briefly. Then queue again."]

DEATH = {
    "off": ["Shake it off. Next round.", "Happens to everyone. Reset.", "They got lucky. Go again."],
    "mild": ["Ouch. That was tragic.", "You got flatlined. Rest in pixels.",
             "Bro walked straight into that, gonk.", "Peek smarter, not harder.", "Skill issue? ...Kidding. Mostly."],
    "spicy": ["Bro, that was ass.", "You died to THAT? Embarrassing.", "Absolute ass round. Wow.",
              "Did you even have your monitor on?", "My guy, that aim was ass."],
}
DEATH_STREAK = {
    "off": ["{n} deaths in a row. Breathe. Reset.", "Rough patch. You'll bounce back."],
    "mild": ["{n} deaths in a row. Maybe switch spots, gonk.", "{n} straight deaths. Tragic."],
    "spicy": ["{n} deaths in a row. You're ass today, choom.", "{n} in a row. Uninstall? ...Kidding. Maybe."],
}
BAD_KD = {
    "off": ["{k}/{d}, but you're still trying. Respect."],
    "mild": ["{k}/{d}... the team is carrying you."],
    "spicy": ["{k}/{d}. A bot lobby would be too hard for you."],
}
ROUND_LOSS = {
    "off": ["Shake it off. Next round."],
    "mild": ["Lost it. Tighten up.", "Round gone. Focus."],
    "spicy": ["Embarrassing round. Do better.", "That round was ass."],
}
MATCH_LOSS = {
    "off": ["GG. We learn and go again."],
    "mild": ["That one hurt. Queue again?", "Loss. It happens. Hydrate."],
    "spicy": ["Wow. That loss was ass. Queue again, coward.", "Brutal. Blame the team. And yourself."],
}
START = ["{game}? Don't int, choom.", "{game} time. I'll stay small and quiet. And judge.",
         "Locked in. Go get 'em."]
VERDICT = {
    "great": ["Absolute menace.", "Carried. Legendary."],
    "good": ["Solid. Respect.", "Preem session."],
    "mid": ["Mid. It happens.", "Not bad, not great."],
    "bad": {"off": ["Tough one. Shake it off."], "mild": ["Rough one."],
            "spicy": ["That was ass. Queue again?"]},
}


def detect_game(title):
    """Which supported game is this window title? None if none (also for browser tabs and video/social sites:
    'Valorant clips - Twitch' is watching, not playing)."""
    import awareness
    if awareness.is_web(title):
        return None
    t = (title or "").lower()
    for key, (_name, words) in GAMES.items():
        if any(w in t for w in words):
            return key
    return None


def parse_match(text):
    """'13-7 15/12' -> {'rounds': (13, 7), 'kd': (15, 12)}; either part may be missing. None if unreadable."""
    out = {}
    for tok in (text or "").replace(",", " ").split():
        for sep, name in (("-", "rounds"), ("/", "kd"), (":", "rounds")):
            if sep in tok:
                a, _, b = tok.partition(sep)
                if a.isdigit() and b.isdigit() and int(a) < 1000 and int(b) < 1000:
                    out[name] = (int(a), int(b))
                break
    return out or None


class Session:
    def __init__(self, key="other", rng=None, level="mild", clock=time.time):
        self.key = key if key in GAMES else "other"
        self.rng, self.clock = rng or random.Random(), clock
        self.level = level if level in LEVELS else "mild"
        self.kills = self.deaths = self.rounds_w = self.rounds_l = 0
        self.kstreak = self.dstreak = self.events = 0
        self.started = clock()
        self._last = -1e9

    @property
    def name(self):
        return GAMES[self.key][0]

    @property
    def kd(self):
        return self.kills / float(max(1, self.deaths))

    def minutes(self):
        return (self.clock() - self.started) / 60.0

    def start_line(self):
        return self.rng.choice(START).format(game=self.name)

    def _pick(self, pool, **kw):
        return self.rng.choice(pool).format(k=self.kills, d=self.deaths, **kw)

    def event(self, kind, n=1):
        """Count an event and return a line to say ('' if she should stay quiet this time)."""
        if kind not in EVENT_KINDS:
            return ""
        now = self.clock()
        n = max(1, min(int(n), 5))
        self.events += 1
        line = ""
        if kind in ("kill", "ace"):
            n = 5 if kind == "ace" else n
            self.kills += n
            self.kstreak += n
            self.dstreak = 0
            if kind == "ace" or n >= 5:
                line = self._pick(ACE)
            elif n >= 2:
                line = MULTI[n]
            elif self.kstreak >= 3:
                line = self._pick(KILL_STREAK, n=self.kstreak)
            elif self.events >= 6 and self.kd >= 2:
                line = self._pick(GOOD_KD)
            else:
                line = self._pick(KILL)
        elif kind == "death":
            self.deaths += 1
            self.dstreak += 1
            self.kstreak = 0
            if self.dstreak >= 3:
                line = self._pick(DEATH_STREAK[self.level], n=self.dstreak)
            elif self.events >= 6 and self.kd < 0.5:
                line = self._pick(BAD_KD[self.level])
            else:
                line = self._pick(DEATH[self.level])
        elif kind == "clutch":
            line = self._pick(CLUTCH)
        elif kind == "round_win":
            self.rounds_w += 1
            line = self._pick(ROUND_WIN)
        elif kind == "round_loss":
            self.rounds_l += 1
            line = self._pick(ROUND_LOSS[self.level])
        elif kind == "match_win":
            line = self._pick(MATCH_WIN)
        elif kind == "match_loss":
            line = self._pick(MATCH_LOSS[self.level])
        if kind not in BIG and now - self._last < MIN_GAP:
            return ""                                    # counted, but don't talk over yourself
        self._last = now
        return line

    def apply_result(self, rounds=None, kd=None):
        """Fix up the totals from a post-match report (/match 13-7 15/12)."""
        if rounds:
            self.rounds_w, self.rounds_l = rounds
        if kd:
            self.kills, self.deaths = kd

    def verdict(self):
        kd = self.kd
        if kd >= 1.5:
            return self.rng.choice(VERDICT["great"])
        if kd >= 1.0:
            return self.rng.choice(VERDICT["good"])
        if kd >= 0.7:
            return self.rng.choice(VERDICT["mid"])
        return self.rng.choice(VERDICT["bad"][self.level])

    def recap(self):
        rounds = f", rounds {self.rounds_w}-{self.rounds_l}" if (self.rounds_w or self.rounds_l) else ""
        return (f"{self.name}: {self.kills} kills, {self.deaths} deaths (K/D {self.kd:.2f}){rounds}. "
                + self.verdict())

    def status(self):
        rounds = f"  rounds {self.rounds_w}-{self.rounds_l}" if (self.rounds_w or self.rounds_l) else ""
        return f"{self.name}: {self.kills}/{self.deaths} (K/D {self.kd:.2f}){rounds}  streak: " \
               + (f"{self.kstreak} kill{'s' if self.kstreak != 1 else ''}" if self.kstreak
                  else f"{self.dstreak} death{'s' if self.dstreak != 1 else ''}" if self.dstreak else "none")

    def summary(self):
        """Small dict for the history list (numbers only)."""
        return {"game": self.key, "k": self.kills, "d": self.deaths, "rw": self.rounds_w, "rl": self.rounds_l,
                "min": int(self.minutes()), "day": time.strftime("%Y-%m-%d")}
