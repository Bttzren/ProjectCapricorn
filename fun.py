"""Small in-character toys: dice, coin, 8-ball, and a to-do list (pure logic, no Tk)."""
import re

EIGHT_BALL = ["Preem. Do it.", "Nova yes.", "Signs point to yes, choom.", "Ask me after caffeine.",
              "Flatline chances: high. Nope.", "My chrome says no.", "Probably. Don't quote me.",
              "Reply hazy. Reboot and try again.", "Absolutely. Go get it.", "Nah, choom. Pick another gig."]


def roll(spec, rng):
    """'d20', '2d6', '20' -> a one-line result. Safe against silly sizes."""
    spec = (spec or "d20").strip().lower()
    m = re.fullmatch(r"(\d{1,2})?d(\d{1,4})|(\d{1,4})", spec)
    if not m:
        return "Try /roll d20, /roll 2d6 or /roll 100."
    if m.group(3):
        n, sides = 1, int(m.group(3))
    else:
        n, sides = int(m.group(1) or 1), int(m.group(2))
    if n < 1 or sides < 2:
        return "Dice need at least 2 sides and at least 1 die."
    dice = [rng.randint(1, sides) for _ in range(n)]
    total = sum(dice)
    shown = " + ".join(map(str, dice)) + (f" = {total}" if n > 1 else "")
    tail = ""
    if n == 1 and sides == 20:
        tail = {20: " Critical! Nova!", 1: " Flatlined. Ouch."}.get(total, "")
    return f"Rolled {n if n > 1 else ''}d{sides}: {shown}.{tail}"


def coin(rng):
    return rng.choice(["Heads.", "Tails.", "Heads. (Preem.)", "Tails. (Gonk luck.)"])


def eight_ball(question, rng):
    if not (question or "").strip():
        return "Ask a question first, choom."
    return rng.choice(EIGHT_BALL)


class Todos:
    """To-do list kept in the dict you pass in (settings.json): [{"t": text, "done": bool}, ...]."""

    def __init__(self, items):
        self.items = items

    def add(self, text):
        text = " ".join((text or "").split())[:80]
        if not text:
            return None
        if len(self.items) >= 30:
            self.items[:] = [i for i in self.items if not i["done"]]
            if len(self.items) >= 30:
                return None
        self.items.append({"t": text, "done": False})
        return text

    def finish(self, number):
        """number is 1-based as shown. Returns the text, or None if invalid / already done."""
        if not (1 <= number <= len(self.items)) or self.items[number - 1]["done"]:
            return None
        self.items[number - 1]["done"] = True
        return self.items[number - 1]["t"]

    def clear_done(self):
        n = len(self.items)
        self.items[:] = [i for i in self.items if not i["done"]]
        return n - len(self.items)

    def open_items(self):
        return [i for i in self.items if not i["done"]]

    def lines(self):
        if not self.items:
            return ["Nothing on the list. Add one: /todo add <thing>"]
        return [f"{n}. [{'x' if i['done'] else ' '}] {i['t']}" for n, i in enumerate(self.items, 1)]

    def nag(self):
        o = self.open_items()
        if not o:
            return ""
        return f"Still on the list, choom: {o[0]['t']}" + (f" (+{len(o) - 1} more)" if len(o) > 1 else "")
