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

    def test_body_clock_makes_her_sleepy(self):
        m = self.mind(now=at(3))
        m.last_interaction = at(3) - 10000
        self.assertEqual(m.mood(at(3)), "sleepy")

    def test_she_chooses_her_own_mood_and_holds_it(self):
        m = self.mind(now=at(14))
        first = m.mood(at(14))
        self.assertIn(first, P.MOODS)
        self.assertEqual(m.mood(at(14) + 60), first)           # holds it
        self.assertGreaterEqual(m.cur_until - at(14), P.MOOD_MIN)
        self.assertLessEqual(m.cur_until - at(14), P.MOOD_MAX)

    def test_moods_drift_by_themselves_over_a_day(self):
        m = self.mind({"affection": 50}, now=at(10))
        seen, t = set(), at(10)
        for _ in range(400):
            t += 120
            m.last_interaction = t                              # even while the user chats constantly
            seen.add(m.mood(t))
        self.assertGreaterEqual(len(seen - {"sleepy"}), 4)

    def test_user_attention_nudges_but_never_sets_her_mood(self):
        m = self.mind({"affection": 50}, now=at(14))
        m.set_mood("content", at(14), 900)
        for i in range(30):
            m.poke(at(14) + i)
        self.assertEqual(m.mood(at(14) + 40), "content")      # spamming doesn't flip her
        calm = self.mind({"affection": 50}, now=at(14))
        self.assertGreater(m.weights(at(14) + 40)["hyper"], calm.weights(at(14) + 40)["hyper"])

    def test_her_state_tilts_the_odds(self):
        lonely = self.mind({"affection": 5}, now=at(14))
        lonely.last_interaction = at(14) - 7200
        happy = self.mind({"affection": 95}, now=at(14))
        self.assertGreater(lonely.weights(at(14))["lonely"], happy.weights(at(14))["lonely"])
        self.assertGreater(happy.weights(at(14))["playful"], lonely.weights(at(14))["playful"])
        bored = self.mind({"affection": 50}, now=at(14))
        bored.last_interaction = at(14) - 3600
        self.assertGreater(bored.weights(at(14))["restless"], self.mind(now=at(14)).weights(at(14))["restless"])

    def test_she_can_announce_her_own_mood_change_once(self):
        m = self.mind(now=at(14))
        m.set_mood("content", at(14), 100)
        m.set_mood("hyper", at(14) + 200)
        self.assertEqual(m.take_shift(), ("content", "hyper"))
        self.assertIsNone(m.take_shift())
        for mood in P.MOODS:
            self.assertIn(mood, P.SHIFT_LINES)

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

    def test_sleepy_weights_slow_her_down_and_never_go_below_one(self):
        m = self.mind(now=at(3))
        m.last_interaction = at(3) - 10000
        opts = [("walk", 30), ("lounge", 12), ("teleport", 14), ("dance", 4), ("idle", 14)]
        adj = dict(m.adjust_weights(opts, at(3)))
        self.assertNotIn("sleep", adj)               # she never naps
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
        m.set_mood("lonely", at(14), 900)
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
        self.assertGreater(sum(any(w in l.lower() for w in P.SLANG) for l in pools), len(pools) // 3)
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

    def test_every_mood_has_lines_weights_and_fallbacks(self):
        for mood in P.MOODS:
            m = self.mind({"affection": 50}, now=at(14))
            m.set_mood(mood, at(14), 900)
            for kind in ("idle", "poke", "wake"):
                self.assertIn(mood, P.LINES[kind])
            self.assertIn(mood, P.OFFLINE_FALLBACK)
            self.assertTrue(m.adjust_weights([("walk", 10)], at(14)))
            self.assertTrue(m.line("idle", at(14)))
            self.assertIn(mood, m.context(at(14)))
            self.assertGreater(m.chatter_scale(at(14)), 0)

    def test_hyper_talks_more_and_expresses_with_her_body(self):
        m = self.mind({"affection": 50}, now=at(14))
        m.set_mood("hyper", at(14), 900)
        now = at(14) + 10
        self.assertLess(m.chatter_scale(now), 1.0)
        act, icon = m.expression(now)
        self.assertIn((act, icon), P.EXPRESSIONS["hyper"])

    def test_default_persona_is_the_edgerunners_capri(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "capri.py"), encoding="utf-8").read()
        persona = src[src.index("DEFAULT_PERSONA = ("):src.index(")\n", src.index("DEFAULT_PERSONA = ("))]
        for word in ("Edgerunners", "curious", "chaotic", "thrill", "never encourage real harm"):
            self.assertIn(word, persona)

    def test_her_mood_decides_how_hard_she_roasts_within_the_ceiling(self):
        m = self.mind(now=at(14))
        for mood, want in (("sassy", "spicy"), ("playful", "spicy"), ("content", "mild"), ("lonely", "off")):
            m.set_mood(mood, at(14), 900)
            self.assertEqual(m.roast_level(at(14), "mood"), want, mood)
        m.set_mood("sassy", at(14), 900)
        self.assertEqual(m.roast_level(at(14), "mild"), "mild")       # ceiling caps her
        self.assertEqual(m.roast_level(at(14), "off"), "off")
        self.assertEqual(m.roast_level(at(14), "spicy"), "spicy")

    def test_she_only_dissed_unprompted_when_mood_and_setting_allow(self):
        m = self.mind(now=at(14))
        m.set_mood("lonely", at(14), 900)
        self.assertFalse(any(m.wants_to_diss(at(14), "mood") for _ in range(200)))
        m.set_mood("sassy", at(14), 900)
        self.assertFalse(any(m.wants_to_diss(at(14), "off") for _ in range(200)))
        self.assertTrue(any(m.wants_to_diss(at(14), "mood") for _ in range(200)))

    def test_diss_lines_exist_and_stay_off_the_hard_stuff(self):
        bad = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt|nigg\w*|fag\w*|retard\w*|kill yourself)\b")
        for mood, lines in P.DISS.items():
            self.assertIn(mood, P.MOODS)
            for l in lines:
                self.assertLessEqual(len(l), 120)
                self.assertIsNone(bad.search(l.lower()), l)
        m = self.mind(now=at(14))
        m.set_mood("sassy", at(14), 900)
        self.assertIn(m.line("diss", at(14)), P.DISS["sassy"])


if __name__ == "__main__":
    unittest.main()
