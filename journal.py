"""A tiny mood journal (pure logic, no Tk). Entries live in the list you pass in."""
from datetime import date, timedelta

MAX_ENTRIES = 120

REPLIES = {
    1: ["That sounds rough, choom. I'm here. If it's heavy, talk to someone you trust too.",
        "Ugh. Tomorrow's a fresh run. Rest up."],
    2: ["Meh days happen. Be gentle with yourself.", "Not great, huh? Small win tomorrow. One tiny step."],
    3: ["Solid middle-of-the-road. Respect.", "Okay day. Okay is fine, choom."],
    4: ["Nice! Good day. Keep that energy.", "Preem. I'll take a good day."],
    5: ["NOVA! Best day! Tell me everything!", "Five out of five?! Legendary, choom."],
}


class Journal:
    def __init__(self, items):
        self.items = items

    def add(self, day, score, note=""):
        """Record how today went (1-5). Replaces today's entry. Returns True if it was the first for `day`."""
        if not (1 <= int(score) <= 5):
            raise ValueError("score must be 1-5")
        note = " ".join((note or "").split())[:100]
        first = not any(e["d"] == day for e in self.items)
        self.items[:] = [e for e in self.items if e["d"] != day] + [{"d": day, "s": int(score), "n": note}]
        self.items[:] = sorted(self.items, key=lambda e: e["d"])[-MAX_ENTRIES:]
        return first

    def has(self, day):
        return any(e["d"] == day for e in self.items)

    def reply(self, score, rng):
        return rng.choice(REPLIES[int(score)])

    def last(self, n=7):
        return self.items[-n:]

    def average(self, n=7):
        recent = self.last(n)
        return sum(e["s"] for e in recent) / len(recent) if recent else None

    def lines(self, n=7):
        if not self.items:
            return ["No entries yet. Try /feel 4 pretty good day"]
        out = [f"{date.fromisoformat(e['d']).strftime('%a %b %d')}: {e['s']}/5 {'*' * e['s']}" + (f"  {e['n']}" if e["n"] else "")
               for e in self.last(n)]
        avg = self.average(n)
        return out + [f"Average of the last {len(self.last(n))}: {avg:.1f}/5"]
