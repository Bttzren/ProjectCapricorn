import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw  # noqa: E402

import gfx  # noqa: E402


def sprite():
    im = Image.new("RGBA", (40, 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 6, 31, 54), fill=(251, 9, 72, 255))
    d.rectangle((14, 14, 25, 24), fill=(5, 245, 111, 255))
    d.ellipse((17, 17, 22, 22), fill=(20, 20, 60, 255))
    return im


class GfxTests(unittest.TestCase):
    def test_enlarging_is_crisper_than_plain_lanczos(self):
        im = sprite()
        plain = im.resize((60, 90), Image.LANCZOS)
        sharp = gfx.resize_sharp(im, (60, 90))
        self.assertEqual(sharp.size, (60, 90))
        self.assertGreater(gfx.sharpness(sharp), gfx.sharpness(plain))

    def test_alpha_is_not_touched_by_sharpening(self):
        im = sprite().resize((60, 90), Image.LANCZOS)
        self.assertEqual(list(gfx.sharpen_rgb(im, 150).getchannel("A").getdata()), list(im.getchannel("A").getdata()))

    def test_strength_grows_with_enlargement_and_is_bounded(self):
        self.assertLess(gfx.strength(0.8), gfx.strength(1.0))
        self.assertLess(gfx.strength(1.0), gfx.strength(1.5))
        self.assertLessEqual(gfx.strength(9.0), 220)

    def test_shrinking_and_same_size_work(self):
        im = sprite()
        self.assertEqual(gfx.resize_sharp(im, (20, 30)).size, (20, 30))
        self.assertEqual(gfx.resize_sharp(im, (40, 60)).size, (40, 60))


if __name__ == "__main__":
    unittest.main()
