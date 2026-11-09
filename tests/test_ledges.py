import os
import random
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw  # noqa: E402

import ledges as L  # noqa: E402

SCREEN = (1280, 720)


def page(boxes=(), size=SCREEN, bg=255, lines=()):
    im = Image.new("RGB", size, (bg, bg, bg))
    d = ImageDraw.Draw(im)
    for (x0, y0, x1, y1) in boxes:
        d.rectangle((x0, y0, x1, y1), fill=(238, 238, 238), outline=(140, 140, 140), width=2)
    for (x0, y, x1) in lines:
        d.line((x0, y, x1, y), fill=(120, 120, 120), width=2)
    return im


def near(a, b, tol=10):
    return abs(a - b) <= tol


class DetectTests(unittest.TestCase):
    def test_finds_a_box_and_its_top_edge(self):
        found = L.detect(page(boxes=[(200, 300, 700, 520)]), screen=SCREEN)
        boxes = [f for f in found if f["kind"] == "box"]
        self.assertEqual(len(boxes), 1)
        b = boxes[0]
        self.assertTrue(near(b["l"], 200), b)
        self.assertTrue(near(b["r"], 700), b)
        self.assertTrue(near(b["t"], 300, 8), b)

    def test_finds_several_boxes_and_orders_boxes_widest_first(self):
        found = L.detect(page(boxes=[(100, 100, 300, 250), (400, 200, 1000, 400), (150, 500, 450, 650)]),
                         screen=SCREEN)
        widths = [f["r"] - f["l"] for f in found if f["kind"] == "box"]
        self.assertEqual(len(widths), 3)
        self.assertEqual(widths, sorted(widths, reverse=True))

    def test_blank_page_and_smooth_gradients_have_no_ledges(self):
        self.assertEqual(L.detect(page(), screen=SCREEN), [])
        grad = Image.new("RGB", SCREEN)
        px = grad.load()
        for y in range(SCREEN[1]):
            for x in range(SCREEN[0]):
                px[x, y] = (x * 255 // SCREEN[0],) * 3
        self.assertEqual(L.detect(grad, screen=SCREEN), [])

    def test_a_lone_short_line_is_not_a_ledge_but_a_long_one_is(self):
        self.assertEqual(L.detect(page(lines=[(100, 300, 220)]), screen=SCREEN), [])        # too short
        found = L.detect(page(lines=[(100, 300, 900)]), screen=SCREEN)
        self.assertEqual([f["kind"] for f in found], ["edge"])

    def test_boxes_narrower_than_the_minimum_are_ignored(self):
        self.assertEqual(L.detect(page(boxes=[(300, 300, 400, 400)]), screen=SCREEN), [])

    def test_a_photo_is_one_box_and_its_noisy_inside_adds_no_false_ledges(self):
        rnd = random.Random(1)
        im = Image.new("RGB", SCREEN, (255, 255, 255))
        noise = Image.frombytes("RGB", (600, 300), bytes(rnd.randrange(256) for _ in range(600 * 300 * 3)))
        im.paste(noise, (300, 200))
        found = L.detect(im, screen=SCREEN)
        self.assertLessEqual(len(found), 2)                          # the photo's border, nothing inside it
        boxes = [f for f in found if f["kind"] == "box"]
        self.assertEqual(len(boxes), 1)
        self.assertTrue(near(boxes[0]["l"], 300, 12) and near(boxes[0]["r"], 900, 12) and near(boxes[0]["t"], 200, 12))
        inside = [f for f in found if 215 < f["t"] < 490 and f["l"] > 310]
        self.assertEqual(inside, [])

    def test_her_own_windows_are_masked_out(self):
        im = page(boxes=[(200, 300, 700, 520), (800, 300, 1200, 600)])
        masked = L.detect(im, masks=[(780, 280, 440, 340)], screen=SCREEN)           # covers the second box
        lefts = [round(f["l"]) for f in masked if f["kind"] == "box"]
        self.assertEqual(len(lefts), 1)
        self.assertTrue(near(lefts[0], 200))

    def test_screen_scaling_is_applied(self):
        big = page(boxes=[(400, 600, 1400, 1000)], size=(2560, 1440))                     # a 2x screenshot
        found = L.detect(big, screen=(1280, 720))
        b = [f for f in found if f["kind"] == "box"][0]
        self.assertTrue(near(b["l"], 200, 12) and near(b["r"], 700, 12) and near(b["t"], 300, 12), b)

    def test_runs_fast_enough_for_a_full_hd_screen(self):
        im = page(boxes=[(200, 300, 900, 700), (1000, 100, 1800, 500)], size=(1920, 1080))
        t = time.time()
        L.detect(im, screen=(1920, 1080))
        self.assertLess(time.time() - t, 2.0)

    def test_darker_theme_boxes_are_found_too(self):
        im = Image.new("RGB", SCREEN, (24, 24, 30))
        ImageDraw.Draw(im).rectangle((300, 200, 800, 450), fill=(48, 48, 58), outline=(90, 90, 100), width=2)
        self.assertEqual(len([f for f in L.detect(im, screen=SCREEN) if f["kind"] == "box"]), 1)


class TrackTests(unittest.TestCase):
    def test_ids_are_stable_while_a_box_scrolls_and_new_boxes_get_new_ids(self):
        a = {"l": 200, "t": 300, "r": 700, "kind": "box"}
        first, n = L.track([], [a], 0)
        self.assertEqual(first[0]["id"], "L1")
        scrolled = dict(a, t=340)
        second, n = L.track(first, [scrolled], n)
        self.assertEqual(second[0]["id"], "L1")
        third, n = L.track(second, [scrolled, {"l": 800, "t": 340, "r": 1200, "kind": "box"}], n)
        self.assertEqual({x["id"] for x in third}, {"L1", "L2"})

    def test_a_box_that_jumped_far_is_a_new_ledge(self):
        first, n = L.track([], [{"l": 200, "t": 100, "r": 700, "kind": "box"}], 0)
        second, n = L.track(first, [{"l": 200, "t": 600, "r": 700, "kind": "box"}], n)
        self.assertNotEqual(second[0]["id"], first[0]["id"])


class SafetyTests(unittest.TestCase):
    def test_private_looking_pages_are_never_scanned(self):
        for t in ("Chase Online Banking - Chrome", "Sign in to your account", "Bitwarden", "New Incognito Tab",
                  "InPrivate - Microsoft Edge", "My Password Manager", "PayPal Checkout"):
            self.assertFalse(L.should_scan(t), t)
        for t in ("YouTube - Chrome", "main.py - Visual Studio Code", "", None):
            self.assertTrue(L.should_scan(t), t)


class ScannerTests(unittest.TestCase):
    def test_scan_returns_detections_and_forgets_the_screenshot(self):
        img = page(boxes=[(200, 300, 700, 520)])
        seen = []
        s = L.Scanner(capture=lambda: img, detect=lambda i, m, sc: seen.append((i, m, sc)) or [{"l": 1}], threaded=False)
        self.assertTrue(s.start([(0, 0, 10, 10)], SCREEN))
        self.assertEqual(seen[0][1:], ([(0, 0, 10, 10)], SCREEN))
        self.assertEqual(s.take(), [{"l": 1}])
        self.assertIsNone(s.take())                                 # taken once
        self.assertFalse(hasattr(s, "image"))                       # nothing keeps the screenshot

    def test_capture_failure_is_reported_not_raised(self):
        s = L.Scanner(capture=lambda: None, threaded=False)
        s.start([], SCREEN)
        self.assertIn("capture", s.error)
        self.assertIsNone(s.take())

    def test_detector_errors_are_contained(self):
        s = L.Scanner(capture=lambda: page(), detect=lambda *a: 1 / 0, threaded=False)
        s.start([], SCREEN)
        self.assertEqual(s.error, "ZeroDivisionError")

    def test_threaded_scan_completes_and_is_not_restarted_while_busy(self):
        img = page(boxes=[(200, 300, 700, 520)])
        s = L.Scanner(capture=lambda: img)
        s.start([], SCREEN)
        for _ in range(100):
            if not s.busy:
                break
            time.sleep(0.05)
        self.assertEqual(len(s.take()), 1)


class TrackMoveTests(unittest.TestCase):
    def test_a_moved_window_keeps_its_ids_box_to_box(self):
        prev = [{"id": "L1", "l": 318, "t": 698, "r": 962, "kind": "box"},
                {"id": "L2", "l": 318, "t": 726, "r": 962, "kind": "edge"}]
        new = [{"l": 318, "t": 626, "r": 980, "kind": "edge"},          # title bar's lower line, now 72 px away
               {"l": 318, "t": 598, "r": 962, "kind": "box"}]           # the real new top, 100 px away
        out, _ = L.track(prev, new, 2)
        ids = {d["t"]: d["id"] for d in out}
        self.assertEqual(ids[598], "L1")
        self.assertEqual(ids[626], "L2")


class HoldTests(unittest.TestCase):
    PREV = [{"id": "L1", "l": 318, "t": 698, "r": 962, "kind": "box"}]

    def test_keeps_the_seat_while_part_of_its_edge_is_visible(self):
        runs = [{"l": 561, "t": 699, "r": 962, "kind": "edge"}]           # her body hides the left part
        self.assertEqual([d["id"] for d in L.hold(self.PREV, [], runs, "L1")], ["L1"])

    def test_drops_it_when_the_window_is_gone_or_moved(self):
        self.assertEqual(L.hold(self.PREV, [], [], "L1"), [])                               # closed
        self.assertEqual(L.hold(self.PREV, [], [{"l": 318, "t": 400, "r": 962}], "L1"), [])  # moved up a lot
        self.assertEqual(L.hold(self.PREV, [], [{"l": 900, "t": 698, "r": 940}], "L1"), [])  # only a sliver

    def test_no_change_when_still_found_or_not_sitting(self):
        new = [{"id": "L1", "l": 318, "t": 699, "r": 962}]
        self.assertIs(L.hold(self.PREV, new, [], "L1"), new)
        self.assertEqual(L.hold(self.PREV, [], [{"l": 318, "t": 698, "r": 962}], None), [])

    def test_a_box_partly_behind_her_still_counts(self):
        img = Image.new("RGB", (1280, 800), (30, 30, 40))
        ImageDraw.Draw(img).rectangle((300, 300, 900, 600), fill=(200, 200, 210))
        mask = [(250, 150, 280, 330)]                     # her window covers the box's top-left corner
        found = L.detect(img, mask, self_mask=mask[0])
        tops = [f for f in found if abs(f["t"] - 300) <= 6]
        self.assertTrue(tops, found)
        self.assertEqual(tops[0]["kind"], "box")
        self.assertLess(tops[0]["l"], 300)                # it continues behind her window, under her feet
        self.assertGreater(tops[0]["r"], 880)
        # a plain short line that ends at her window, with no side anywhere, is still not a box
        img2 = Image.new("RGB", (1280, 800), (30, 30, 40))
        ImageDraw.Draw(img2).line((300, 300, 700, 300), fill=(220, 220, 220), width=2)
        self.assertFalse([f for f in L.detect(img2, mask, self_mask=mask[0]) if f["kind"] == "box"])

    def test_behind_her_chat_window_is_unknown_not_a_continuation(self):
        img = Image.new("RGB", (1280, 800), (30, 30, 40))
        ImageDraw.Draw(img).rectangle((300, 300, 900, 600), fill=(200, 200, 210))
        chat = (250, 150, 280, 330)                      # the CHAT window covers the corner, not her
        tops = [f for f in L.detect(img, [chat], self_mask=(1000, 0, 200, 200)) if abs(f["t"] - 300) <= 6]
        self.assertFalse([f for f in tops if f["l"] < 500])     # never extended behind the chat window
        self.assertFalse([f for f in tops if f["kind"] == "box"])

    def test_detect_raw_returns_every_run(self):
        img = Image.new("RGB", (1280, 800), (30, 30, 40))
        d = ImageDraw.Draw(img)
        d.rectangle((300, 300, 900, 600), fill=(200, 200, 210))
        found, runs = L.detect(img, raw=True)
        self.assertTrue(found)
        self.assertGreaterEqual(len(runs), len(found))
        self.assertEqual(L.detect(img), found)


if __name__ == "__main__":
    unittest.main()
