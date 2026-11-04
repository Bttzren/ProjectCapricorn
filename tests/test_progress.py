import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import fun  # noqa: E402
import progress as P  # noqa: E402


class ProgressTests(unittest.TestCase):
    def test_streak_grows_resets_and_pays_a_login_bonus(self):
        p = P.Progress({})
        m = p.login("2026-11-01")
        self.assertEqual(p.streak, 1)
        self.assertEqual(p.eddies, 3)
        self.assertTrue(m)
        self.assertEqual(p.login("2026-11-01"), [])                 # same day: nothing
        p.login("2026-11-02")
        p.login("2026-11-03")
        self.assertEqual(p.streak, 3)
        self.assertTrue(p.unlocked("streak_3"))
        p.login("2026-11-10")                                       # missed days
        self.assertEqual(p.streak, 1)

    def test_login_bonus_is_capped(self):
        p = P.Progress({})
        for d in range(1, 12):
            p.login(f"2026-11-{d:02d}")
        before = p.eddies
        p.login("2026-11-12")
        self.assertEqual(p.eddies - before, 15)

    def test_focus_pays_and_unlocks_achievements_once(self):
        p = P.Progress({})
        m = p.record("focus")
        self.assertIn("+10 eddies.", m)
        self.assertTrue(any("First Gig" in x for x in m))
        e = p.eddies
        m2 = p.record("focus")
        self.assertFalse(any("First Gig" in x for x in m2))
        self.assertEqual(p.eddies, e + 10)

    def test_first_chat_of_day_bonus_and_night_owl(self):
        p = P.Progress({})
        p.login("2026-11-01")
        e = p.eddies
        p.record("chat", hour=2)
        self.assertEqual(p.eddies, e + P.CHAT_DAY_BONUS + 5)      # +5 is the Night Owl achievement
        self.assertTrue(p.unlocked("night_owl"))
        e = p.eddies
        p.record("chat", hour=14)
        self.assertEqual(p.eddies, e)                               # only the first chat of the day pays

    def test_chat_50_achievement(self):
        p = P.Progress({})
        for _ in range(50):
            p.record("chat", hour=12)
        self.assertTrue(p.unlocked("chat_50"))

    def test_buying_skins(self):
        p = P.Progress({"eddies": 40})
        self.assertEqual(p.buy_skin("neon"), (True, "Neon is already yours."))
        ok, msg = p.buy_skin("chrome")
        self.assertFalse(ok)
        self.assertIn("60", msg)
        self.assertEqual(p.eddies, 40)
        self.assertTrue(p.buy_skin("ocean")[0])
        self.assertEqual(p.eddies, 10)
        self.assertTrue(p.owns("ocean"))
        self.assertFalse(p.buy_skin("nope")[0])

    def test_state_lives_in_the_store_and_survives_reload(self):
        store = {}
        p = P.Progress(store)
        p.record("focus")
        p.buy_skin("neon")
        again = P.Progress(store)
        self.assertEqual(again.count("focus"), 1)
        self.assertEqual(again.eddies, p.eddies)

    def test_eddies_never_negative_and_stats_render(self):
        p = P.Progress({})
        p.earn(-50)
        self.assertEqual(p.eddies, 0)
        self.assertEqual(len(p.stats_lines()), 4)

    def test_every_skin_has_a_price_and_neon_is_free(self):
        self.assertEqual(P.SKINS["neon"][1], 0)
        import skins
        self.assertEqual(set(P.SKINS), set(skins.IDS))


class FunTests(unittest.TestCase):
    def test_roll(self):
        r = random.Random(1)
        self.assertTrue(fun.roll("", r).startswith("Rolled d20"))
        self.assertIn("=", fun.roll("2d6", r))
        self.assertTrue(fun.roll("100", r).startswith("Rolled d100"))
        for bad in ("banana", "0d6", "d1", "999d6", "2d99999"):
            self.assertTrue(fun.roll(bad, r).startswith(("Try", "Dice")), bad)

    def test_crits(self):
        class R:
            def __init__(self, v): self.v = v
            def randint(self, a, b): return self.v
        self.assertIn("Critical", fun.roll("d20", R(20)))
        self.assertIn("Flatlined", fun.roll("d20", R(1)))

    def test_coin_and_8ball(self):
        r = random.Random(2)
        self.assertIn(fun.coin(r).split(".")[0], ("Heads", "Tails"))
        self.assertIn("question", fun.eight_ball("  ", r))
        self.assertIn(fun.eight_ball("will it work?", r), fun.EIGHT_BALL)

    def test_todos(self):
        items = []
        t = fun.Todos(items)
        self.assertIsNone(t.add("   "))
        self.assertEqual(t.add("  do   homework "), "do homework")
        t.add("walk")
        self.assertEqual(len(t.open_items()), 2)
        self.assertEqual(t.finish(1), "do homework")
        self.assertIsNone(t.finish(1))                               # already done
        self.assertIsNone(t.finish(9))
        self.assertIsNone(t.finish(0))
        self.assertIn("walk", t.nag())
        self.assertEqual(t.clear_done(), 1)
        self.assertEqual(len(items), 1)                              # kept in the shared list
        self.assertTrue(fun.Todos([]).lines()[0].startswith("Nothing"))
        self.assertEqual(fun.Todos([]).nag(), "")

    def test_todo_list_is_capped(self):
        t = fun.Todos([])
        for i in range(40):
            t.add(f"task {i}")
        self.assertLessEqual(len(t.items), 30)


if __name__ == "__main__":
    unittest.main()
