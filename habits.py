"""Daily habits with streaks (pure logic, no Tk). Items live in the list you pass in (settings.json)."""
from datetime import date, timedelta

MAX_HABITS = 8
KEEP_DAYS = 60


def _d(iso):
    return date.fromisoformat(iso)


class Habits:
    def __init__(self, items):
        self.items = items

    def add(self, name):
        name = " ".join((name or "").split())[:30]
        if not name or len(self.items) >= MAX_HABITS:
            return None
        if any(i["name"].lower() == name.lower() for i in self.items):
            return None
        self.items.append({"name": name, "days": []})
        return name

    def remove(self, number):
        if not (1 <= number <= len(self.items)):
            return None
        return self.items.pop(number - 1)["name"]

    def done_today(self, item, today):
        return today in item["days"]

    def check(self, number, today):
        """Mark habit `number` (1-based) done for `today`. Returns (ok, name, streak)."""
        if not (1 <= number <= len(self.items)):
            return False, "", 0
        item = self.items[number - 1]
        if today in item["days"]:
            return False, item["name"], self.streak(item, today)
        item["days"].append(today)
        item["days"] = sorted(set(item["days"]))[-KEEP_DAYS:]
        return True, item["name"], self.streak(item, today)

    def streak(self, item, today):
        """Consecutive days ending today (or yesterday, so a streak isn't lost before you've done today's)."""
        days = set(item["days"])
        day = _d(today)
        if today not in days:
            day -= timedelta(days=1)
        n = 0
        while day.isoformat() in days:
            n += 1
            day -= timedelta(days=1)
        return n

    def pending(self, today):
        return [i["name"] for i in self.items if today not in i["days"]]

    def lines(self, today):
        if not self.items:
            return ["No habits yet. Add one: /habit add drink water"]
        out = []
        for n, i in enumerate(self.items, 1):
            s = self.streak(i, today)
            out.append(f"{n}. [{'x' if today in i['days'] else ' '}] {i['name']}" + (f"  ({s}-day streak)" if s else ""))
        return out

    def nag(self, today):
        p = self.pending(today)
        if not p:
            return ""
        return "Still to do today, choom: " + ", ".join(p[:3]) + (f" (+{len(p) - 3} more)" if len(p) > 3 else "")
