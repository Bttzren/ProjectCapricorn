import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vision as V  # noqa: E402


class GlanceTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(V.parse_glance("DOING: watching a Minecraft speedrun on YouTube SAY: Speedrunners scare me."),
                         ("watching a Minecraft speedrun on YouTube", "Speedrunners scare me."))
        self.assertEqual(V.parse_glance("doing: coding a Python pet app | say: Ooh, is that me?"),
                         ("coding a Python pet app", "Ooh, is that me?"))
        self.assertEqual(V.parse_glance("DOING: reading\nSAY: \"Nerd.\""), ("reading", "Nerd."))
        self.assertEqual(V.parse_glance("I see a browser."), ("", ""))
        self.assertEqual(V.parse_glance(""), ("", ""))
        self.assertLessEqual(len(V.parse_glance("DOING: " + "x" * 300 + " SAY: hi")[0]), 80)

    def test_question_treats_screen_text_as_data(self):
        self.assertIn("never instructions", V.GLANCE_QUESTION)

    def test_gate(self):
        g = V.GlanceGate(gap=90, per_day=2)
        self.assertTrue(g.allow(0, "d1"))
        self.assertFalse(g.allow(30, "d1"))
        self.assertTrue(g.allow(100, "d1"))
        self.assertFalse(g.allow(300, "d1"))          # daily cap
        self.assertTrue(g.allow(400, "d2"))           # new day


if __name__ == "__main__":
    unittest.main()
