"""Daily habit checklist (pure logic, no Tk). No streaks. Items live in the list you pass in (settings.json)."""
MAX_HABITS = 8
KEEP_DAYS = 60


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
        """Mark habit `number` (1-based) done for `today`. Returns (ok, name)."""
        if not (1 <= number <= len(self.items)):
            return False, ""
        item = self.items[number - 1]
        if today in item["days"]:
            return False, item["name"]
        item["days"].append(today)
        item["days"] = sorted(set(item["days"]))[-KEEP_DAYS:]
        return True, item["name"]

    def pending(self, today):
        return [i["name"] for i in self.items if today not in i["days"]]

    def lines(self, today):
        if not self.items:
            return ["No habits yet. Add one: /habit add drink water"]
        out = []
        for n, i in enumerate(self.items, 1):
            out.append(f"{n}. [{'x' if today in i['days'] else ' '}] {i['name']}")
        return out

    def nag(self, today):
        p = self.pending(today)
        if not p:
            return ""
        return "Still to do today, choom: " + ", ".join(p[:3]) + (f" (+{len(p) - 3} more)" if len(p) > 3 else "")
