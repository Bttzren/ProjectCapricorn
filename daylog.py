"""How long you spent in each kind of app today (pure logic, no Tk).

Only category totals are kept (e.g. coding: 130 minutes), never window titles. Kept 14 days, on this computer.
"""

NAMES = {"coding": "coding", "video": "videos", "music": "music", "school": "schoolwork", "chat": "chatting",
         "writing": "writing", "game": "gaming", "cyberpunk": "Cyberpunk", "social": "social media",
         "ai": "AI chats", "other": "other apps"}
KEEP_DAYS = 14


def fmt(minutes):
    m = int(round(minutes))
    return f"{m // 60}h{m % 60:02d}" if m >= 60 else f"{m}m"


class DayLog:
    def __init__(self, store):
        self.s = store.setdefault("days", {})

    def add(self, day, cat, secs):
        if secs <= 0:
            return
        d = self.s.setdefault(day, {})
        d[cat or "other"] = d.get(cat or "other", 0.0) + float(secs)
        if len(self.s) > KEEP_DAYS:
            for old in sorted(self.s)[:len(self.s) - KEEP_DAYS]:
                del self.s[old]

    def minutes(self, day):
        return {k: v / 60.0 for k, v in self.s.get(day, {}).items()}

    def total(self, day):
        return sum(self.minutes(day).values())

    def summary(self, day, top=5):
        mins = {k: v for k, v in self.minutes(day).items() if v >= 1}
        if not mins:
            return "Nothing tracked yet today."
        parts = [f"{NAMES.get(k, k)} {fmt(v)}" for k, v in sorted(mins.items(), key=lambda kv: -kv[1])[:top]]
        return f"Today: {', '.join(parts)}  (total {fmt(sum(mins.values()))})"
