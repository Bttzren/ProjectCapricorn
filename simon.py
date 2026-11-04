"""Simon: repeat the growing colour sequence (pure logic, no Tk)."""
import random

COLORS = ("green", "red", "blue", "yellow")


class Simon:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.seq, self.pos, self.completed, self.over = [], 0, 0, False

    def next_round(self):
        """Add one colour; returns the full sequence to show."""
        self.seq.append(self.rng.choice(COLORS))
        self.pos = 0
        return list(self.seq)

    def press(self, color):
        """'ok' (keep going), 'round_done', 'wrong' (game over) or 'ignored'."""
        if self.over or not self.seq or color not in COLORS:
            return "ignored"
        if color != self.seq[self.pos]:
            self.over = True
            return "wrong"
        self.pos += 1
        if self.pos == len(self.seq):
            self.completed += 1
            return "round_done"
        return "ok"
