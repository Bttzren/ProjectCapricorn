"""Badges, a daily visit streak and daily gigs (pure logic, no Tk). State lives in the dict you pass (settings.json)."""
from datetime import date, timedelta

# key -> (counter, needed, title, how)
BADGES = {
    "poker": ("pokes", 50, "Boop Master", "poke her 50 times"),
    "flyer": ("flights", 10, "Frequent Flyer", "send her flying 10 times"),
    "gamer": ("games", 5, "Arcade Rat", "play 5 mini games"),
    "winner": ("wins", 10, "Winner Winner", "win 10 mini games"),
    "talker": ("chats", 25, "Chatterbox", "use 25 chat commands"),
    "closer": ("done", 10, "Closer", "finish 10 to-dos, habits or gigs"),
    "focus": ("focus", 5, "Deep Diver", "finish 5 focus sessions"),
    "killer": ("kills", 25, "Menace", "log 25 game kills"),
    "tagger": ("tags", 3, "Untaggable", "play tag 3 times"),
    "regular": ("streak_best", 7, "Regular", "open Capri 7 days in a row"),
}

GIGS = [
    "Drink a full glass of water",
    "Stand up and stretch for one minute",
    "Look at something far away for 20 seconds",
    "Tidy one thing on your desk",
    "Text a friend something nice",
    "Take 10 slow breaths",
    "Do 10 pushups or squats",
    "Write down one thing you're grateful for",
    "Close five tabs you don't need",
    "Eat something that isn't a snack",
    "Fix your posture right now",
    "Step outside for a minute",
]
GIGS_PER_DAY = 3


class Badges:
    def __init__(self, store):
        self.store = store
        self.store.setdefault("counts", {})
        self.store.setdefault("earned", [])
        self.store.setdefault("streak", {"last": "", "n": 0, "best": 0})

    def bump(self, counter, n=1):
        """Add to a counter. Returns the list of newly earned (key, title) badges."""
        c = self.store["counts"]
        c[counter] = c.get(counter, 0) + n
        return self.check()

    def check(self):
        new = []
        counts = dict(self.store["counts"])
        counts["streak_best"] = self.store["streak"].get("best", 0)
        for key, (counter, need, title, _how) in BADGES.items():
            if key not in self.store["earned"] and counts.get(counter, 0) >= need:
                self.store["earned"].append(key)
                new.append((key, title))
        return new

    def visit(self, today):
        """Call once per launch. Returns (streak_days, new_badges)."""
        s = self.store["streak"]
        if s["last"] != today:
            try:
                yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
            except ValueError:
                yesterday = ""
            s["n"] = s["n"] + 1 if s["last"] == yesterday else 1
            s["last"] = today
            s["best"] = max(s.get("best", 0), s["n"])
        return s["n"], self.check()

    def lines(self):
        counts = self.store["counts"]
        out = []
        for key, (counter, need, title, how) in BADGES.items():
            have = self.store["streak"].get("best", 0) if counter == "streak_best" else counts.get(counter, 0)
            if key in self.store["earned"]:
                out.append(f"[x] {title}: {how}")
            else:
                out.append(f"[ ] {title}: {how} ({min(have, need)}/{need})")
        s = self.store["streak"]
        out.append(f"Daily streak: {s['n']} (best {s.get('best', 0)})")
        return out


def todays_gigs(store, today, rng):
    """The day's gigs: [{'text', 'done'}]. Picked once per day and kept in `store`."""
    if store.get("day") != today:
        store["day"] = today
        store["items"] = [{"text": t, "done": False} for t in rng.sample(GIGS, GIGS_PER_DAY)]
    return store["items"]


def finish_gig(store, today, rng, number):
    """(ok, text, all_done_now). ok False if the number is wrong or it was already done."""
    items = todays_gigs(store, today, rng)
    if not (1 <= number <= len(items)) or items[number - 1]["done"]:
        return False, "", False
    items[number - 1]["done"] = True
    return True, items[number - 1]["text"], all(i["done"] for i in items)
