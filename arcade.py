"""Little games to play with Capri in the chat: rock-paper-scissors, trivia, number guess (pure logic, no Tk)."""
import random
import re

# ---------------------------------------------------------------- rock paper scissors
RPS = ("rock", "paper", "scissors")
BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
ALIASES = {"r": "rock", "p": "paper", "s": "scissors", "scissor": "scissors"}


def rps_pick(text):
    t = (text or "").strip().lower()
    t = ALIASES.get(t, t)
    return t if t in RPS else None


def rps_play(choice, rng=None):
    """(her_pick, 'win' | 'loss' | 'tie') from the USER's point of view."""
    rng = rng or random.Random()
    mine = rng.choice(RPS)
    if mine == choice:
        return mine, "tie"
    return mine, ("win" if BEATS[choice] == mine else "loss")


# ---------------------------------------------------------------- trivia
# (question, [accepted answers...])  answers are compared in lowercase without punctuation
TRIVIA = [
    ("What year is Cyberpunk 2077 set in? (the game's title)", ["2077"]),
    ("What is the capital of Canada?", ["ottawa"]),
    ("How many sides does a hexagon have?", ["6", "six"]),
    ("What planet is known as the Red Planet?", ["mars"]),
    ("What gas do plants absorb from the air?", ["carbon dioxide", "co2"]),
    ("What is the largest planet in our solar system?", ["jupiter"]),
    ("In binary, what is 101 in decimal?", ["5", "five"]),
    ("What does CPU stand for? (first word only)", ["central"]),
    ("Which element has the symbol Au?", ["gold"]),
    ("How many players are on a standard soccer team on the field?", ["11", "eleven"]),
    ("What is 12 times 12?", ["144"]),
    ("Which ocean is the largest?", ["pacific"]),
    ("What is the fastest land animal?", ["cheetah"]),
    ("What language is this app written in?", ["python"]),
    ("How many minutes are in a day?", ["1440"]),
    ("What is the chemical symbol for water?", ["h2o"]),
    ("Who painted the Mona Lisa? (last name)", ["vinci", "da vinci", "leonardo"]),
    ("How many continents are there?", ["7", "seven"]),
    ("What is the square root of 81?", ["9", "nine"]),
    ("What is the hardest natural substance?", ["diamond"]),
    ("In Valorant, how many players are on a team?", ["5", "five"]),
    ("What colour do you get mixing blue and yellow?", ["green"]),
    ("What is the smallest prime number?", ["2", "two"]),
    ("Which country has the maple leaf on its flag?", ["canada"]),
    ("How many bits are in a byte?", ["8", "eight"]),
]


def norm(text):
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").lower()).strip()


class Trivia:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.current = None
        self.score = self.asked = 0
        self._bag = []

    def ask(self):
        if not self._bag:
            self._bag = list(range(len(TRIVIA)))
            self.rng.shuffle(self._bag)
        self.current = TRIVIA[self._bag.pop()]
        self.asked += 1
        return self.current[0]

    def answer(self, text):
        """(correct, right_answer). (None, '') when no question is open."""
        if not self.current:
            return None, ""
        q, ok = self.current
        self.current = None
        good = norm(text) in ok
        if good:
            self.score += 1
        return good, ok[0]


# ---------------------------------------------------------------- number guess
class Guess:
    def __init__(self, rng=None, hi=100, tries=7):
        self.rng = rng or random.Random()
        self.hi, self.max_tries = hi, tries
        self.target = self.rng.randint(1, hi)
        self.tries = 0
        self.over = False

    def guess(self, n):
        """'low' | 'high' | 'win' | 'lose'."""
        self.tries += 1
        if n == self.target:
            self.over = True
            return "win"
        if self.tries >= self.max_tries:
            self.over = True
            return "lose"
        return "low" if n < self.target else "high"
