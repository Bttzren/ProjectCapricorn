"""Breach Protocol: a hacking puzzle (pure logic, no Tk).

Pick code cells from a grid to fill a buffer so that it contains the daemon sequences (in a row).
Rules (like the Cyberpunk 2077 mini-game): the first pick is in the TOP row; after that picks
alternate between the same COLUMN and the same ROW as the previous pick; a cell can't be reused.
Every puzzle is generated from a real legal path, so completing ALL daemons is always possible.
"""
import random

CODES = ("1C", "55", "BD", "E9", "7A")
DAEMON_NAMES = ("DATAMINE", "ICEPICK", "CAMERA.OFF", "MASS.VULN", "GHOST.EXE", "BLACKWALL", "OVERCLOCK", "REBOOT")


class Daemon:
    def __init__(self, name, seq):
        self.name, self.seq = name, tuple(seq)

    def __repr__(self):
        return f"Daemon({self.name}, {' '.join(self.seq)})"


def _contains(codes, seq):
    n = len(seq)
    return any(tuple(codes[i:i + n]) == seq for i in range(len(codes) - n + 1))


class Breach:
    def __init__(self, size=5, buffer=7, daemons=3, rng=None):
        self.size, self.buffer = size, buffer
        self.rng = rng or random.Random()
        self.picks = []                       # [(row, col)]
        for _ in range(200):
            if self._generate(daemons):
                break
        else:
            raise RuntimeError("couldn't generate a breach puzzle")

    # -- generation ---------------------------------------------------------
    def _generate(self, n_daemons):
        r, size = self.rng, self.size
        self.grid = [[r.choice(CODES) for _ in range(size)] for _ in range(size)]
        path, used = [(0, r.randrange(size))], {(0, 0)}
        used = {path[0]}
        axis = "col"                           # the next pick moves along the column
        while len(path) < self.buffer:
            pr, pc = path[-1]
            cands = [(rr, pc) for rr in range(size) if (rr, pc) not in used] if axis == "col" \
                else [(pr, cc) for cc in range(size) if (pr, cc) not in used]
            if not cands:
                return False
            nxt = r.choice(cands)
            path.append(nxt)
            used.add(nxt)
            axis = "row" if axis == "col" else "col"
        codes = [self.grid[a][b] for a, b in path]
        lengths = sorted(r.sample([2, 2, 3, 3, 4], n_daemons))
        seqs = []
        for ln in lengths:
            start = r.randrange(0, self.buffer - ln + 1)
            seq = tuple(codes[start:start + ln])
            if seq not in seqs:
                seqs.append(seq)
        if len(seqs) < n_daemons:
            return False
        names = r.sample(DAEMON_NAMES, len(seqs))
        self.daemons = [Daemon(nm, sq) for nm, sq in zip(names, seqs)]
        self.solution = path
        return True

    # -- play ---------------------------------------------------------------
    @property
    def codes(self):
        return [self.grid[a][b] for a, b in self.picks]

    def legal(self):
        """Cells that may be picked right now."""
        if len(self.picks) >= self.buffer:
            return set()
        if not self.picks:
            return {(0, c) for c in range(self.size)}
        pr, pc = self.picks[-1]
        used = set(self.picks)
        if len(self.picks) % 2 == 1:           # 1st, 3rd, ... pick was made; move along the column
            return {(rr, pc) for rr in range(self.size) if (rr, pc) not in used}
        return {(pr, cc) for cc in range(self.size) if (pr, cc) not in used}

    def pick(self, row, col):
        if (row, col) not in self.legal():
            return False
        self.picks.append((row, col))
        return True

    def completed(self):
        codes = self.codes
        return [d for d in self.daemons if _contains(codes, d.seq)]

    def progress(self, daemon):
        """How many codes of the daemon are matched at the end of the buffer (full length if completed)."""
        codes = self.codes
        if _contains(codes, daemon.seq):
            return len(daemon.seq)
        for k in range(min(len(codes), len(daemon.seq) - 1), 0, -1):
            if tuple(codes[-k:]) == daemon.seq[:k]:
                return k
        return 0

    def done(self):
        return (len(self.picks) >= self.buffer or len(self.completed()) == len(self.daemons)
                or not self.legal())

    def score(self):
        return len(self.completed())

    def best_possible(self):
        """Most daemons any legal sequence of picks could complete (brute force; used by tests/hints)."""
        best = 0

        def go(picks):
            nonlocal best
            codes = [self.grid[a][b] for a, b in picks]
            got = sum(1 for d in self.daemons if _contains(codes, d.seq))
            best = max(best, got)
            if got == len(self.daemons) or len(picks) >= self.buffer:
                return
            if not picks:
                nxt = [(0, c) for c in range(self.size)]
            else:
                pr, pc = picks[-1]
                used = set(picks)
                nxt = ([(rr, pc) for rr in range(self.size)] if len(picks) % 2 == 1
                       else [(pr, cc) for cc in range(self.size)])
                nxt = [p for p in nxt if p not in used]
            for p in nxt:
                go(picks + [p])
                if best == len(self.daemons):
                    return
        go([])
        return best
