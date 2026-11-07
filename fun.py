"""Small in-character toys: dice, coin, 8-ball, and a to-do list (pure logic, no Tk)."""
import re

EIGHT_BALL = ["Preem. Do it.", "Nova yes.", "Signs point to yes.", "Ask me after caffeine.",
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
        return "Ask a question first."
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


LORE = [
    "In Night City, chrome is a fashion choice and a personality.",
    "Fun fact: every netrunner's worst enemy is a 30-second loading bar.",
    "The best gigs start with a plan and end with a different plan.",
    "Rumor has it the neon never turns off. It just gets tired and glows dimmer.",
    "Street wisdom: never trust a vending machine that says 'free'.",
    "Ripperdocs say: the best upgrade is a good night's sleep.",
    "A true choom never leaves you on read.",
    "Old netrunner proverb: back up your files. Then back up your backup.",
    "In the city, everybody's got a side hustle and a ramen stash.",
    "They say there's a ghost in every machine. Mine's just very cute.",
    "Preem advice: drink water before the heist, not during.",
    "Night City tip: the loudest ad is usually the least useful.",
]

HOROSCOPE = [
    "Neon aligns in your favor. Start the thing you've been putting off.",
    "A small glitch will become a funny story. Don't sweat it.",
    "Someone will need your help today. Be the choom they hoped for.",
    "Beware of unnecessary tabs. Close five. Feel lighter.",
    "A tiny step now beats a perfect plan later. Move.",
    "Your luck is chrome-plated today. Take the shot.",
    "Rest is a power-up. Schedule some.",
    "An old idea comes back sharper. Write it down.",
    "Expect a plot twist before lunch. Roll with it.",
    "Today's lucky number is whatever you're procrastinating on. Do that one.",
]

SIGNS = [(1, 20, "Capricorn"), (2, 19, "Aquarius"), (3, 20, "Pisces"), (4, 20, "Aries"), (5, 21, "Taurus"),
         (6, 21, "Gemini"), (7, 22, "Cancer"), (8, 23, "Leo"), (9, 23, "Virgo"), (10, 23, "Libra"),
         (11, 22, "Scorpio"), (12, 22, "Sagittarius"), (12, 31, "Capricorn")]


def sign_for(month, day):
    for m, d, name in SIGNS:
        if (month, day) <= (m, d):
            return name
    return "Capricorn"


def horoscope(today_iso, birthday=""):
    """Same forecast all day for the same person (seeded by the date and sign). Just for fun."""
    sign = "Wildcard"
    if birthday and re.fullmatch(r"\d\d-\d\d", birthday):
        sign = sign_for(int(birthday[:2]), int(birthday[3:]))
    seed = sum(ord(c) * (i + 3) for i, c in enumerate(today_iso + sign))
    return f"{sign} forecast: {HOROSCOPE[seed % len(HOROSCOPE)]}"
