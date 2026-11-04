import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

import skins  # noqa: E402

SHEET = os.path.join(os.path.dirname(__file__), "..", "pet", "spritesheet.webp")


class SkinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheet = Image.open(SHEET).convert("RGBA")

    def test_alpha_is_never_changed(self):
        base = self.sheet.getchannel("A").tobytes()
        for s in skins.IDS:
            self.assertEqual(skins.apply(self.sheet, s).getchannel("A").tobytes(), base, s)

    def test_neon_and_unknown_are_unchanged(self):
        self.assertEqual(skins.apply(self.sheet, "neon").tobytes(), self.sheet.tobytes())
        self.assertEqual(skins.apply(self.sheet, "???").tobytes(), self.sheet.tobytes())

    def test_other_skins_actually_differ_from_each_other(self):
        outs = {s: skins.apply(self.sheet, s).tobytes() for s in skins.IDS}
        self.assertEqual(len(set(outs.values())), len(skins.IDS))

    def test_ocean_swaps_red_and_blue_and_acid_swaps_red_and_green(self):
        px = Image.new("RGBA", (1, 1), (200, 50, 10, 255))
        self.assertEqual(skins.apply(px, "ocean").getpixel((0, 0)), (10, 50, 200, 255))
        self.assertEqual(skins.apply(px, "acid").getpixel((0, 0)), (50, 200, 10, 255))

    def test_chrome_and_gold_are_tinted_grayscale_ramps(self):
        px = Image.new("RGBA", (1, 1), (255, 255, 255, 255))
        for s in ("chrome", "gold"):
            r, g, b, a = skins.apply(px, s).getpixel((0, 0))
            self.assertEqual(a, 255)
            self.assertGreater(max(r, g, b), 200)
        dark = Image.new("RGBA", (1, 1), (0, 0, 0, 255))
        self.assertLess(sum(skins.apply(dark, "gold").getpixel((0, 0))[:3]), 60)


if __name__ == "__main__":
    unittest.main()
