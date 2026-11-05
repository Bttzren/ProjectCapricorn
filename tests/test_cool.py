import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

import brief  # noqa: E402
import neon  # noqa: E402


def blob():
    img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    for y in range(12, 28):
        for x in range(12, 28):
            img.putpixel((x, y), (200, 30, 30, 255))
    img.putpixel((10, 10), (200, 30, 30, 120))                       # a soft pixel must not survive
    return img


class NeonTests(unittest.TestCase):
    def test_outline_is_solid_and_outside(self):
        out = neon.outline(blob(), neon.COLORS["cyan"], 2)
        self.assertEqual(out.getpixel((20, 20)), (200, 30, 30, 255))              # the sprite itself is untouched
        self.assertEqual(out.getpixel((10, 20)), neon.COLORS["cyan"] + (255,))    # rim just outside the left edge
        self.assertEqual(out.getpixel((2, 2))[3], 0)                              # far away stays clear
        self.assertTrue(all(a in (0, 255) for _r, _g, _b, a in out.getdata()))     # no soft edges anywhere

    def test_ghost_is_sparse_tinted_and_hard(self):
        g1, g2 = neon.ghost(blob(), neon.COLORS["magenta"], 1), neon.ghost(blob(), neon.COLORS["magenta"], 2)
        n = lambda im: sum(1 for p in im.getdata() if p[3])    # noqa: E731
        self.assertGreater(n(g1), n(g2))
        self.assertGreater(n(g2), 0)
        self.assertTrue(all(p[:3] == neon.COLORS["magenta"] for p in g1.getdata() if p[3]))
        self.assertTrue(all(p[3] in (0, 255) for p in g1.getdata()))

    def test_hex(self):
        self.assertEqual(neon.hex_of((0, 240, 255)), "#00f0ff")


class BriefTests(unittest.TestCase):
    def test_full_briefing(self):
        lines, facts = brief.build(["a", "b", "c", "d"], ["water", "gym"], [(1000 + 600, "call mom"), (500, "old")],
                                   1000, ("focus", 900))
        self.assertTrue(lines[0].startswith("To-dos (4): a, b, c (+1 more)"))
        self.assertIn("Habits left today: water, gym", lines)
        self.assertIn("Next reminder in 10 min: call mom", lines)
        self.assertTrue(any("Focus timer: 15 min" in x for x in lines))
        self.assertIn("4 open to-dos", facts)
        self.assertNotIn("old", " ".join(lines))                    # past reminders are not upcoming

    def test_empty(self):
        lines, facts = brief.build([], [], [], 0)
        self.assertEqual(lines, ["Nothing on your plate. Nova."])
        self.assertIn("nothing is pending", facts)
        self.assertEqual(brief.fallback(lines), lines[0])


if __name__ == "__main__":
    unittest.main()


class IntentTests(unittest.TestCase):
    def test_controls_launch_and_more(self):
        import listen
        i = listen.intent
        for text, action in (("pause the music", "playpause"), ("Hey Capri, next song", "next"), ("skip", "next"),
                             ("previous track", "prev"), ("volume up", "volup"), ("turn it down", "voldown"),
                             ("mute", "mute"), ("take a screenshot", "screenshot"), ("lock my screen", "lock"),
                             ("show desktop", "desktop"), ("play some music", "playpause")):
            self.assertEqual(i(text), ("control", action), text)
        self.assertEqual(i("open discord"), ("launch", "open discord"))
        self.assertEqual(i("search for best crosshair")[0], "launch")
        self.assertEqual(i("go to youtube")[0], "launch")
        self.assertEqual(i("what's on my plate")[0], "brief")
        self.assertEqual(i("start a focus session")[0], "focus")
        self.assertEqual(i("tell my friends I'm late")[0], "task")             # still goes to the agent
        self.assertEqual(i("play the new valorant trailer")[0], "task")
        self.assertEqual(i("how loud is a jet")[0], "chat")
        self.assertEqual(i("stop"), ("stop", ""))
        self.assertEqual(i("set a timer for 5 minutes")[0], "remind")
