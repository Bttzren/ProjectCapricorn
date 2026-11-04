import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import arcade  # noqa: E402
import badges  # noqa: E402


class ArcadeTests(unittest.TestCase):
    def test_rps_pick(self):
        self.assertEqual(arcade.rps_pick("R"), "rock")
        self.assertEqual(arcade.rps_pick("scissor"), "scissors")
        self.assertIsNone(arcade.rps_pick("lizard"))

    def test_rps_outcomes_consistent(self):
        rng = random.Random(1)
        seen = set()
        for _ in range(200):
            mine, res = arcade.rps_play("rock", rng)
            seen.add(res)
            if res == "win":
                self.assertEqual(mine, "scissors")
            elif res == "loss":
                self.assertEqual(mine, "paper")
            else:
                self.assertEqual(mine, "rock")
        self.assertEqual(seen, {"win", "loss", "tie"})

    def test_trivia_cycle_no_repeat_and_scoring(self):
        t = arcade.Trivia(random.Random(3))
        self.assertEqual(t.answer("x"), (None, ""))
        seen = set()
        for _ in range(len(arcade.TRIVIA)):
            seen.add(t.ask())
        self.assertEqual(len(seen), len(arcade.TRIVIA))
        t2 = arcade.Trivia(random.Random(0))
        q = t2.ask()
        ok = dict(arcade.TRIVIA)[q][0]
        good, right = t2.answer("  " + ok.upper() + "! ")
        self.assertTrue(good)
        self.assertEqual(t2.score, 1)
        t2.ask()
        good, _ = t2.answer("definitely wrong")
        self.assertFalse(good)
        self.assertEqual(t2.score, 1)

    def test_guess_game(self):
        g = arcade.Guess(random.Random(5), hi=10, tries=3)
        self.assertEqual(g.guess(g.target), "win")
        g = arcade.Guess(random.Random(5), hi=10, tries=2)
        wrong = 1 if g.target != 1 else 2
        self.assertIn(g.guess(wrong), ("low", "high"))
        self.assertEqual(g.guess(wrong), "lose")


class BadgeTests(unittest.TestCase):
    def test_badge_unlocks_once(self):
        b = badges.Badges({})
        got = []
        for _ in range(50):
            got += b.bump("pokes")
        self.assertEqual([k for k, _ in got], ["poker"])
        self.assertEqual(b.bump("pokes"), [])

    def test_streak(self):
        b = badges.Badges({})
        self.assertEqual(b.visit("2026-01-01")[0], 1)
        self.assertEqual(b.visit("2026-01-01")[0], 1)
        self.assertEqual(b.visit("2026-01-02")[0], 2)
        self.assertEqual(b.visit("2026-01-04")[0], 1)
        self.assertEqual(b.store["streak"]["best"], 2)

    def test_streak_badge(self):
        b = badges.Badges({})
        new = []
        for d in range(1, 8):
            new += b.visit(f"2026-02-0{d}")[1]
        self.assertEqual([k for k, _ in new], ["regular"])

    def test_lines_show_progress(self):
        b = badges.Badges({})
        b.bump("flights", 3)
        text = "\n".join(b.lines())
        self.assertIn("(3/10)", text)
        self.assertIn("Daily streak", text)

    def test_gigs_stable_per_day_and_finish(self):
        store = {}
        rng = random.Random(2)
        a = [i["text"] for i in badges.todays_gigs(store, "2026-03-01", rng)]
        self.assertEqual(len(a), badges.GIGS_PER_DAY)
        self.assertEqual(a, [i["text"] for i in badges.todays_gigs(store, "2026-03-01", rng)])
        for n in (1, 2):
            r = badges.finish_gig(store, "2026-03-01", rng, n)
            self.assertEqual((r[0], r[2]), (True, False))
        self.assertFalse(badges.finish_gig(store, "2026-03-01", rng, 1)[0])
        self.assertFalse(badges.finish_gig(store, "2026-03-01", rng, 9)[0])
        r = badges.finish_gig(store, "2026-03-01", rng, 3)
        self.assertEqual((r[0], r[2]), (True, True))
        b = [i["text"] for i in badges.todays_gigs(store, "2026-03-02", rng)]
        self.assertEqual(len(b), badges.GIGS_PER_DAY)
        self.assertFalse(any(i["done"] for i in store["items"]))


if __name__ == "__main__":
    unittest.main()
