"""Things Capri remembers about you (pure logic, no Tk). Stored locally in the list you pass in."""

MAX_FACTS = 20
MAX_LEN = 120


class Memory:
    def __init__(self, items):
        self.items = items

    def remember(self, text):
        text = " ".join((text or "").split())[:MAX_LEN]
        if not text or text.lower() in (i.lower() for i in self.items):
            return None
        if len(self.items) >= MAX_FACTS:
            self.items.pop(0)                         # forget the oldest
        self.items.append(text)
        return text

    def forget(self, number):
        if not (1 <= number <= len(self.items)):
            return None
        return self.items.pop(number - 1)

    def lines(self):
        if not self.items:
            return ["I don't know anything about you yet. Tell me: /remember my favorite game is Minecraft"]
        return [f"{n}. {t}" for n, t in enumerate(self.items, 1)]

    def context(self):
        """Extra AI instructions listing what she knows (empty when she knows nothing)."""
        if not self.items:
            return ""
        return "Things the user told you to remember about them: " + "; ".join(self.items) + "."

    def callback(self, rng):
        """A line that brings one fact back up, or '' if there are none."""
        if not self.items:
            return ""
        fact = rng.choice(self.items)
        return rng.choice([f"Hey, I remember: {fact}. Still true, choom?",
                           f"Random thought: {fact}. I think about that.",
                           f"You told me: {fact}. Just checking in."])
