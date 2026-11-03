import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import capri
except Exception:  # no Tk / Pillow-Tk on this machine
    capri = None

PET = os.path.join(os.path.dirname(__file__), "..", "pet")


@unittest.skipIf(capri is None, "needs tkinter and Pillow ImageTk")
class PetSheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.art = capri.SheetSprites(PET, 170)

    def test_bundled_sheet_is_found_first(self):
        self.assertEqual(os.path.abspath(capri.find_pet_dir()), os.path.abspath(PET))

    def test_all_rows_and_frame_counts(self):
        self.assertEqual([len(r) for r in self.art.rows], [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8])

    def test_every_action_resolves_to_a_frame(self):
        for anim in ("idle", "walk", "wave", "dance", "talk", "sleep", "lounge", "startle", "jump", "fail",
                     "wait", "think"):
            for d in (1, -1):
                key, img = self.art.frame(anim, 0.4, d)
                self.assertGreater(img.width, 10, anim)

    def test_walking_left_and_right_use_different_rows(self):
        self.assertNotEqual(self.art.frame("walk", 0.0, 1)[0][0], self.art.frame("walk", 0.0, -1)[0][0])

    def test_slicing_never_cuts_through_her(self):
        """Every cell's outer 1px border must be empty: nothing is clipped by the grid."""
        from PIL import Image
        sheet = Image.open(os.path.join(PET, "spritesheet.webp")).convert("RGBA")
        W, H = sheet.size
        cwf, chf = W / 8.0, H / 11.0
        cw, ch = int(round(cwf)), int(round(chf))
        for r in range(11):
            for c in range(8):
                x0, y0 = int(round(c * cwf)), int(round(r * chf))
                a = sheet.crop((x0, y0, x0 + cw, y0 + ch)).getchannel("A")
                bb = a.getbbox()
                if bb is None:
                    continue
                self.assertGreater(bb[0], 0, (r, c))
                self.assertGreater(bb[1], 0, (r, c))
                self.assertLess(bb[2], cw, (r, c))
                self.assertLess(bb[3], ch, (r, c))

    def test_chat_portraits_exist(self):
        for k in ("idle", "talk", "angry"):
            self.assertIn(k, self.art.portraits)

    def test_missing_sheet_falls_back_to_placeholder(self):
        ph = capri.PlaceholderSprites(170)
        self.assertEqual(ph.frame("walk", 0, 1)[1].size, ph.idle.size)


if __name__ == "__main__":
    unittest.main()
