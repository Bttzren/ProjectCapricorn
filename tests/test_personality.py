import calendar
import os
import re
import random
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import personality as P  # noqa: E402


def at(hour, day=3):
    """Epoch for a local time on 2026-11-<day> at the given hour."""
    return time.mktime((2026, 11, day, hour, 0, 0, 0, 0, -1))


class MindTests(unittest.TestCase):
    def mind(self, store=None, now=None, **kw):
        return P.Mind({} if store is None else store, now=now or at(14), rng=random.Random(1), **kw)

    def test_mood_follows_time_and_affection(self):
        m = self.mind(now=at(3))
        m.last_interaction = at(3) - 10000
        self.assertEqual(m.mood(at(3)), "sleepy")
        m = self.mind({"affection": 10}, now=at(14))
        m.last_interaction = at(14) - 10000
        self.assertEqual(m.mood(at(14)), "lonely")
        m = self.mind({"affection": 90}, now=at(14))
        self.assertEqual(m.mood(at(14)), "playful")
        m = self.mind({"affection": 50}, now=at(14))
        self.assertEqual(m.mood(at(14)), "content")

    def test_spam_makes_her_sassy_then_recovers(self):
        m = self.mind({"affection": 90}, now=at(14))
        m.annoyed(at(14), 300)
        self.assertEqual(m.mood(at(14) + 10), "sassy")
        self.assertNotEqual(m.mood(at(14) + 400), "sassy")

    def test_affection_grows_with_attention_and_is_clamped(self):
        m = self.mind({"affection": 99}, now=at(14))
        for _ in range(10):
            m.poke(at(14))
            m.chatted(at(14))
        self.assertEqual(m.affection, 100.0)

    def test_affection_fades_when_ignored(self):
        m = self.mind({"affection": 60}, now=at(14))
        t = at(14)
        for _ in range(8):
            t += 3600
            m.tick(t)
        self.assertLess(m.affection, 60)

    def test_absence_reduces_affection_and_is_greeted(self):
        store = {"affection": 80, "last_seen": at(9) - 5 * 3600}
        m = P.Mind(store, now=at(9), rng=random.Random(2))
        self.assertLess(m.affection, 80)
        self.assertIn("hours", m.greeting(at(9)))

    def test_greeting_uses_name_and_part_of_day(self):
        m = self.mind(now=at(8))
        m.user_name = "Sam"
        self.assertIn("Sam", m.greeting(at(8)))
        self.assertEqual(P.part_of_day(8), "morning")
        self.assertEqual(P.part_of_day(14), "afternoon")
        self.assertEqual(P.part_of_day(19), "evening")
        self.assertEqual(P.part_of_day(2), "night")

    def test_state_persists_in_store(self):
        store = {}
        m = P.Mind(store, now=at(14))
        m.poke(at(14))
        m.user_name = "  Ada  "
        m.sync(at(14))
        self.assertEqual(store["user_name"], "Ada")
        self.assertIn("affection", store)
        self.assertEqual(store["last_seen"], at(14))

    def test_lines_exist_for_every_mood_and_kind(self):
        m = self.mind()
        for mood in P.MOODS:
            for kind in ("idle", "poke", "wake"):
                self.assertTrue(P.LINES[kind].get(mood), (kind, mood))
        self.assertTrue(m.line("checkin", at(14)))
        self.assertIn(m.line("checkin", at(3)), P.LINES["late"])

    def test_sleepy_weights_prefer_sleep_and_never_go_below_one(self):
        m = self.mind(now=at(3))
        m.last_interaction = at(3) - 10000
        opts = [("walk", 30), ("lounge", 12), ("teleport", 14), ("dance", 4), ("idle", 14)]
        adj = dict(m.adjust_weights(opts, at(3)))
        self.assertIn("sleep", adj)
        self.assertLess(adj["walk"], 30)
        self.assertTrue(all(w >= 1 for w in adj.values()))

    def test_offline_replies_never_empty_and_flag_offline_mode(self):
        m = self.mind()
        for text in ("hello there", "thanks!", "i'm stuck", "tell me a joke", "random words", ""):
            r = m.offline_reply(text, at(14))
            self.assertTrue(r)
            self.assertIn("ffline", r)

    def test_llm_context_mentions_mood_name_and_activity(self):
        m = self.mind({"affection": 5}, now=at(14))
        m.last_interaction = at(14) - 10000
        m.user_name = "Sam"
        ctx = m.context(at(14), "napping")
        for needle in ("lonely", "Sam", "napping", "neglected"):
            self.assertIn(needle, ctx)

    def test_night_city_slang_and_pg_and_short(self):
        pools = []
        for kind in ("idle", "poke", "wake"):
            for lines in P.LINES[kind].values():
                pools += lines
        pools += P.LINES["checkin"] + P.LINES["late"]
        for greets in P.GREET.values():
            pools += greets
        for _keys, replies in P.OFFLINE:
            pools += replies
        for lines in P.OFFLINE_FALLBACK.values():
            pools += lines
        joined = " ".join(pools).lower()
        for word in ("choom", "preem", "nova", "gonk", "chrome", "netrunner", "gig"):
            self.assertIn(word, joined)
        self.assertGreater(sum(any(w in l.lower() for w in P.SLANG) for l in pools), len(pools) // 2)
        for line in pools:
            self.assertLessEqual(len(line), 120, line)
        bad = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|damn\w*|hell|ass|asshole|crap)\b")
        self.assertEqual([l for l in pools if bad.search(l.lower())], [])

    def test_default_persona_asks_for_slang_but_stays_pg(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        src = open(os.path.join(os.path.dirname(__file__), "..", "capri.py"), encoding="utf-8").read()
        persona = src[src.index("DEFAULT_PERSONA = ("):src.index(")\n", src.index("DEFAULT_PERSONA = ("))]
        for word in ("choom", "preem", "nova", "gonk", "eddies", "PG"):
            self.assertIn(word, persona)


if __name__ == "__main__":
    unittest.main()
