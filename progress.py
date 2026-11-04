"""Eddies, streaks, achievements and skins (pure logic, no Tk).

State lives in the dict you pass in (the app keeps it inside settings.json), so it survives restarts.
"""
from datetime import date, timedelta

# id -> (display name, price in eddies)
SKINS = {"neon": ("Neon", 0), "ocean": ("Ocean", 30), "acid": ("Acid", 30), "chrome": ("Chrome", 60),
         "gold": ("Gold", 100)}

EARN = {"focus": 10, "todo": 5, "tag_win": 5}
CHAT_DAY_BONUS = 2

# id, name, description, test(progress) -> bool, reward
ACHIEVEMENTS = [
    ("first_focus", "First Gig", "Finish a focus session", lambda p: p.count("focus") >= 1, 10),
    ("focus_5", "Grinder", "Finish 5 focus sessions", lambda p: p.count("focus") >= 5, 25),
    ("night_owl", "Night Owl", "Chat with Capri after midnight", lambda p: p.count("night_chat") >= 1, 5),
    ("streak_3", "Regular", "Visit 3 days in a row", lambda p: p.streak >= 3, 15),
    ("streak_7", "Chrome Veteran", "Visit 7 days in a row", lambda p: p.streak >= 7, 40),
    ("todo_5", "Task Slayer", "Finish 5 to-dos", lambda p: p.count("todo") >= 5, 20),
    ("tag_win", "Quick Hands", "Catch Capri in tag", lambda p: p.count("tag_win") >= 1, 10),
    ("chat_50", "Chatterbox", "Send 50 messages", lambda p: p.count("chat") >= 50, 15),
    ("netrunner", "Netrunner", "Complete every daemon in a breach", lambda p: p.count("breach_perfect") >= 1, 20),
    ("ice_breaker", "Ice Breaker", "Run 5 breaches", lambda p: p.count("breach_run") >= 5, 20),
    ("ramen_5", "Ramen Regular", "Feed Capri ramen 5 times", lambda p: p.count("feed") >= 5, 10),
]


class Progress:
    def __init__(self, store):
        self.s = store
        self.s.setdefault("eddies", 0)
        self.s.setdefault("streak", 0)
        self.s.setdefault("last_day", "")
        self.s.setdefault("counts", {})
        self.s.setdefault("done", [])
        self.s.setdefault("skins", ["neon"])
        if "neon" not in self.s["skins"]:
            self.s["skins"].append("neon")

    # -- read
    @property
    def eddies(self):
        return int(self.s["eddies"])

    @property
    def streak(self):
        return int(self.s["streak"])

    def count(self, kind):
        return int(self.s["counts"].get(kind, 0))

    def owns(self, skin):
        return skin in self.s["skins"]

    def unlocked(self, ach_id):
        return ach_id in self.s["done"]

    # -- change
    def earn(self, n):
        self.s["eddies"] = max(0, self.eddies + int(n))

    def spend(self, n):
        """Pay n eddies if you have them."""
        if self.eddies < n:
            return False
        self.earn(-n)
        return True

    def record_breach(self, done, total):
        """A breach finished with `done` of `total` daemons. Returns messages to show."""
        c = self.s["counts"]
        c["breach_run"] = c.get("breach_run", 0) + 1
        gain = 5 * done + (5 if done == total and total > 0 else 0)
        if done == total and total > 0:
            c["breach_perfect"] = c.get("breach_perfect", 0) + 1
        self.earn(gain)
        return [f"Breach: {done}/{total} daemons, +{gain} eddies."] + self._check()

    def login(self, today=None):
        """Daily streak. Returns messages to show (empty if already counted today)."""
        today = today or date.today().isoformat()
        last = self.s["last_day"]
        if last == today:
            return []
        yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
        self.s["streak"] = self.streak + 1 if last == yesterday else 1
        self.s["last_day"] = today
        self.s["counts"]["chat_today"] = 0
        bonus = 3 * min(self.streak, 5)
        self.earn(bonus)
        msgs = [f"Day {self.streak} streak! +{bonus} eddies."] if self.streak > 1 else [f"Welcome! +{bonus} eddies."]
        return msgs + self._check()

    def record(self, kind, hour=None):
        """Something happened (focus / chat / todo / tag_win). Returns messages to show."""
        c = self.s["counts"]
        c[kind] = c.get(kind, 0) + 1
        msgs = []
        if kind in EARN:
            self.earn(EARN[kind])
            msgs.append(f"+{EARN[kind]} eddies.")
        if kind == "chat":
            c["chat_today"] = c.get("chat_today", 0) + 1
            if c["chat_today"] == 1:
                self.earn(CHAT_DAY_BONUS)
                msgs.append(f"First chat today: +{CHAT_DAY_BONUS} eddies.")
            if hour is not None and hour < 5:
                c["night_chat"] = c.get("night_chat", 0) + 1
        return msgs + self._check()

    def _check(self):
        msgs = []
        for ach_id, name, _desc, test, reward in ACHIEVEMENTS:
            if ach_id not in self.s["done"] and test(self):
                self.s["done"].append(ach_id)
                self.earn(reward)
                msgs.append(f"Achievement: {name}! +{reward} eddies.")
        return msgs

    def buy_skin(self, skin):
        """(ok, message). Owned skins are free to switch to."""
        if skin not in SKINS:
            return False, "No such skin."
        name, cost = SKINS[skin]
        if self.owns(skin):
            return True, f"{name} is already yours."
        if self.eddies < cost:
            return False, f"{name} costs {cost} eddies. You have {self.eddies}."
        self.earn(-cost)
        self.s["skins"].append(skin)
        return True, f"Bought {name} for {cost} eddies."

    def stats_lines(self):
        done = [a[1] for a in ACHIEVEMENTS if a[0] in self.s["done"]]
        return [f"Eddies: {self.eddies}   Streak: {self.streak} day(s)",
                f"Focus sessions: {self.count('focus')}   To-dos done: {self.count('todo')}   Messages: {self.count('chat')}",
                "Achievements (%d/%d): %s" % (len(done), len(ACHIEVEMENTS), ", ".join(done) or "none yet"),
                "Skins owned: " + ", ".join(SKINS[s][0] for s in self.s["skins"] if s in SKINS)]
