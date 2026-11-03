import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

import rig  # noqa: E402

SPRITE = os.path.join(os.path.dirname(__file__), "..", "sprites", "idle.png")


def opaque(img):
    return img.getchannel("A").point(lambda v: 255 if v > 127 else 0).getbbox()


class RigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idle = Image.open(SPRITE).convert("RGBA")
        cls.p = rig.Puppet(cls.idle)

    def test_finds_both_eyes_in_the_face(self):
        self.assertEqual(len(self.p.eyes), 2)
        left, right = self.p.eyes
        self.assertLess(left[2], right[0])
        for box in self.p.eyes:
            self.assertLess(box[3], self.idle.height * 0.3)

    def test_mouth_is_below_eyes_and_above_legs(self):
        y0, y1 = self.p.mouth
        self.assertGreater(y0, max(b[3] for b in self.p.eyes))
        self.assertLess(y1, self.p.legs_y)

    def test_every_animation_returns_padded_frame_with_feet_on_the_bottom_edge(self):
        w, h = self.idle.size
        for anim in ("idle", "walk", "dance", "wave", "jump", "startle", "wait", "think", "fail", "talk",
                     "sleep", "lounge", "nonsense"):
            for t in (0.0, 0.37, 1.9, 4.1):
                key, img = self.p.frame(anim, t, 1)
                self.assertEqual(img.size, (w + 2 * rig.PAD_X, h + rig.PAD_TOP), anim)
                self.assertIsNotNone(opaque(img), anim)
                self.assertEqual(opaque(img)[3], h + rig.PAD_TOP, f"{anim} feet moved")

    def test_no_semitransparent_pixels(self):
        _, img = self.p.frame("walk", 0.2, 1)
        self.assertTrue(all(a in (0, 255) for a in img.getchannel("A").getdata()))

    def test_frames_are_cached_and_reused(self):
        k1, i1 = self.p.frame("idle", 0.0)
        k2, i2 = self.p.frame("idle", 0.0)
        self.assertEqual(k1, k2)
        self.assertIs(i1, i2)

    def test_walk_actually_moves(self):
        frames = {self.p.frame("walk", t / 20.0)[0] for t in range(20)}
        self.assertGreater(len(frames), 3)

    def test_blink_closes_the_eyes(self):
        open_img = self.p.build(closed=False)
        shut_img = self.p.build(closed=True)
        self.assertNotEqual(open_img.tobytes(), shut_img.tobytes())
        x0, y0, x1, y1 = self.p.eyes[0]
        blue = [p for p in shut_img.crop((rig.PAD_X + x0, rig.PAD_TOP + y0, rig.PAD_X + x1 + 1, rig.PAD_TOP + y1 + 1)).getdata()
                if rig._near(p, rig.BLUE, 70) and p[3] > 127]
        self.assertEqual(blue, [])

    def test_talk_jaw_changes_mouth_area(self):
        shut = self.p.build(jaw=0)
        wide = self.p.build(jaw=3)
        self.assertNotEqual(shut.tobytes(), wide.tobytes())

    def test_falls_back_when_no_eyes(self):
        blank = Image.new("RGBA", (40, 80), (200, 10, 10, 255))
        p = rig.Puppet(blank)
        self.assertEqual(p.eyes, [])
        _, img = p.frame("talk", 0.1)
        self.assertEqual(img.size, (40 + 2 * rig.PAD_X, 80 + rig.PAD_TOP))


if __name__ == "__main__":
    unittest.main()
