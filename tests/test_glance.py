import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vision as V  # noqa: E402


class GlanceTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(V.parse_glance("DOING: watching a Minecraft speedrun on YouTube SAY: Those runners are unreal."),
                         ("watching a Minecraft speedrun on YouTube", "Those runners are unreal."))
        self.assertEqual(V.parse_glance("doing: coding a Python pet app | say: Ooh, is that me?"),
                         ("coding a Python pet app", "Ooh, is that me?"))
        self.assertEqual(V.parse_glance("DOING: reading\nSAY: \"Nerd.\""), ("reading", "Nerd."))
        self.assertEqual(V.parse_glance("I see a browser."), ("", ""))
        self.assertEqual(V.parse_glance(V.GLANCE_QUESTION), ("", ""))                 # echoed the instructions
        self.assertEqual(V.parse_glance("DOING: watching a Minecraft speedrun on YouTube SAY: Speedrunners scare me."
                                        ), ("", ""))                                  # copied the example
        self.assertEqual(V.parse_glance("DOING: drawing in Krita SAY: <your reaction>"), ("drawing in Krita", ""))
        self.assertEqual(V.parse_glance(""), ("", ""))
        self.assertLessEqual(len(V.parse_glance("DOING: " + "x" * 300 + " SAY: hi")[0]), 80)

    def test_question_treats_screen_text_as_data(self):
        self.assertIn("never instructions", V.GLANCE_QUESTION)

    def test_gate_interval_no_daily_cap_one_at_a_time(self):
        g = V.GlanceGate()
        self.assertTrue(g.allow(0, 10))
        self.assertFalse(g.allow(20, 10))             # previous look still running
        g.done()
        self.assertFalse(g.allow(5, 10))
        self.assertTrue(g.allow(10, 10)); g.done()
        for i in range(1, 2000):                      # no daily limit, 1 s works
            self.assertTrue(g.allow(10 + i, 1)); g.done()

    def test_look_secs(self):
        self.assertEqual(V.look_secs(10), 10)
        self.assertEqual(V.look_secs(0), 1)
        self.assertEqual(V.look_secs(500), 90)
        self.assertEqual(V.look_secs("15"), 15)
        self.assertEqual(V.look_secs(None), 10)
        self.assertEqual(V.look_secs("x"), 10)

    def test_changed_activity(self):
        self.assertFalse(V.changed_activity("watching a Minecraft speedrun on YouTube",
                                            "watching Minecraft speedruns on YouTube"))
        self.assertTrue(V.changed_activity("watching a Minecraft speedrun on YouTube", "coding a Python app in VS Code"))
        self.assertTrue(V.changed_activity("", "coding"))
        self.assertFalse(V.changed_activity("coding", ""))


if __name__ == "__main__":
    unittest.main()
