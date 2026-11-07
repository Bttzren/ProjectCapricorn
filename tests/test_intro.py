import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import intro as I  # noqa: E402


class IntroTests(unittest.TestCase):
    def test_timeline(self):
        self.assertEqual(I.at(0)[0], "intro-grab")
        self.assertEqual(I.at(0)[1], 1.0)                         # starts hidden below the screen
        self.assertEqual(I.at(I.ENTER)[1], 0.0)
        stems = [I.at(t / 50.0)[0] for t in range(int(I.DURATION * 50))]
        self.assertIn("intro-wave2", stems)
        self.assertLess(stems.index("intro-mouth1"), stems.index("intro-happy"))
        self.assertLess(stems.index("intro-happy"), stems.index("intro-wave1"))
        self.assertGreater(I.at(I.DURATION - 0.01)[1], 0.9)          # dropped away at the end
        self.assertIsNone(I.at(I.DURATION))
        self.assertIsNone(I.at(-1))
        self.assertTrue(3.0 < I.DURATION < 5.0)

    def test_every_frame_file_exists(self):
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pet", "intro")
        for s in I.STEMS:
            self.assertTrue(os.path.isfile(os.path.join(root, s + ".webp")), s)

    def test_size(self):
        self.assertEqual(I.size(1920, 1080), (863, 486))                 # height cap (45%) wins on 1080p
        self.assertEqual(I.size(1920, 1600), (900, 506))
        w, h = I.size(1280, 400)
        self.assertLessEqual(h, 180)
        self.assertAlmostEqual(w / h, 1672 / 941, places=1)
        self.assertGreaterEqual(I.size(100, 100)[0], 160)


if __name__ == "__main__":
    unittest.main()
