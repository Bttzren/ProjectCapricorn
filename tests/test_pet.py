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

    def test_no_soft_or_purple_edges_that_would_halo_against_the_color_key(self):
        """Windows blends soft edges with the magenta key: every pixel must be solid or clear."""
        import colorsys
        edge = purple = 0
        for row in self.art.rows:
            for f in row:
                a = f.getchannel("A")
                self.assertEqual(set(a.getdata()) - {0, 255}, set())
                px = f.load()
                w, h = f.size
                for y in range(h):
                    for x in range(w):
                        r, g, b, al = px[x, y]
                        if al == 0:
                            continue
                        self.assertNotEqual((r, g, b), (255, 0, 255))
                        if any(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] == 0
                               for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                            edge += 1
                            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                            purple += 1 if (0.68 <= hh <= 0.88 and ss > 0.25 and vv > 0.25) else 0
        self.assertLess(purple / float(edge), 0.03, "purple rim is back on her outline")

    def test_crisp_handles_key_colour_and_soft_pixels(self):
        from PIL import Image
        im = Image.new("RGBA", (6, 6), (0, 0, 0, 0))
        for x in range(1, 5):
            for y in range(1, 5):
                im.putpixel((x, y), (255, 0, 255, 255) if (x, y) == (2, 2) else (200, 10, 60, 255))
        im.putpixel((0, 3), (130, 60, 230, 200))      # purple soft edge pixel
        im.putpixel((5, 3), (130, 60, 230, 60))       # too faint: dropped
        out = capri.crisp(im)
        self.assertEqual(out.getpixel((5, 3))[3], 0)
        self.assertEqual(out.getpixel((0, 3)), (200, 10, 60, 255))   # recoloured from the solid body
        self.assertNotEqual(out.getpixel((2, 2))[:3], (255, 0, 255))

    def test_chat_portraits_exist(self):
        for k in ("idle", "talk", "angry"):
            self.assertIn(k, self.art.portraits)

    def test_missing_sheet_falls_back_to_placeholder(self):
        ph = capri.PlaceholderSprites(170)
        self.assertEqual(ph.frame("walk", 0, 1)[1].size, ph.idle.size)


if __name__ == "__main__":
    unittest.main()
