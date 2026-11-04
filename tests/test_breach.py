import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import breach as B  # noqa: E402


def make(seed=1, **kw):
    return B.Breach(rng=random.Random(seed), **kw)


class BreachTests(unittest.TestCase):
    def test_every_generated_puzzle_is_fully_solvable(self):
        for seed in range(150):
            g = make(seed)
            self.assertEqual(g.best_possible(), len(g.daemons), seed)

    def test_the_stored_solution_follows_the_rules_and_completes_everything(self):
        for seed in range(40):
            g = make(seed)
            for r, c in g.solution:
                self.assertIn((r, c), g.legal(), seed)
                self.assertTrue(g.pick(r, c))
            self.assertEqual(g.score(), len(g.daemons), seed)

    def test_first_pick_must_be_in_the_top_row(self):
        g = make(3)
        self.assertEqual(g.legal(), {(0, c) for c in range(5)})
        self.assertFalse(g.pick(1, 1))
        self.assertTrue(g.pick(0, 2))

    def test_picks_alternate_column_then_row_and_cells_are_never_reused(self):
        g = make(4)
        g.pick(0, 2)
        self.assertTrue(all(c == 2 for _, c in g.legal()))        # same column
        self.assertNotIn((0, 2), g.legal())
        g.pick(3, 2)
        self.assertTrue(all(r == 3 for r, _ in g.legal()))        # same row
        self.assertNotIn((3, 2), g.legal())
        self.assertFalse(g.pick(0, 0))                            # illegal pick is refused and ignored
        self.assertEqual(len(g.picks), 2)

    def test_buffer_limit_and_done(self):
        g = make(5, buffer=5)
        for r, c in g.solution:
            g.pick(r, c)
        self.assertTrue(g.done())
        self.assertEqual(g.legal(), set())
        self.assertFalse(g.pick(0, 0))

    def test_done_when_all_daemons_complete_even_with_buffer_left(self):
        g = make(6, buffer=9)
        for r, c in g.solution:
            g.pick(r, c)
            if g.score() == len(g.daemons):
                break
        self.assertTrue(g.done())

    def test_progress_tracks_partial_matches_at_the_end_of_the_buffer(self):
        g = make(7)
        d = B.Daemon("T", ("AA", "BB", "CC"))
        g.daemons = [d]
        g.grid = [["AA"] * 5, ["BB"] * 5, ["CC"] * 5, ["1C"] * 5, ["55"] * 5]
        g.picks = [(0, 0)]
        self.assertEqual(g.progress(d), 1)
        g.picks = [(0, 0), (1, 0)]
        self.assertEqual(g.progress(d), 2)
        g.picks = [(0, 0), (1, 0), (3, 0)]
        self.assertEqual(g.progress(d), 0)
        g.picks = [(0, 0), (1, 0), (2, 0)]
        self.assertEqual(g.progress(d), 3)
        self.assertEqual(g.score(), 1)

    def test_daemons_are_distinct_and_at_least_two_long(self):
        for seed in range(60):
            g = make(seed)
            seqs = [d.seq for d in g.daemons]
            self.assertEqual(len(set(seqs)), len(seqs))
            self.assertTrue(all(len(s) >= 2 for s in seqs))
            self.assertEqual(len({d.name for d in g.daemons}), len(g.daemons))

    def test_done_when_no_legal_moves_remain(self):
        g = make(8)
        g.pick(0, 0)
        g.legal = lambda: set()                                  # a dead end before the buffer is full
        self.assertTrue(g.done())

    def test_impossible_sizes_are_refused_not_looped_forever(self):
        with self.assertRaises(RuntimeError):
            make(9, size=2, buffer=7)


if __name__ == "__main__":
    unittest.main()
