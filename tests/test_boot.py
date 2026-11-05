import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boot  # noqa: E402


class BootTests(unittest.TestCase):
    def test_timeline_order(self):
        D = boot.duration(False)
        p0, p1, p2, p3 = (boot.progress(D * f, D) for f in (0.0, 0.2, 0.5, 0.82))
        self.assertEqual(p0["reveal"], 0.0)
        self.assertGreater(p1["beam"], 0.5)
        self.assertEqual(p1["reveal"], 0.0)                         # still powering on
        self.assertTrue(0.0 < p2["reveal"] < 1.0)
        self.assertGreater(p3["flash"], 0.5)
        self.assertEqual(p3["reveal"], 1.0)
        self.assertTrue(boot.progress(D, D)["done"])
        self.assertFalse(boot.progress(D * 0.99, D)["done"])

    def test_values_stay_in_range(self):
        D = 3.4
        for i in range(-5, 160):
            p = boot.progress(i * D / 100, D)
            for k in ("beam", "ring", "reveal", "flash"):
                self.assertTrue(0.0 <= p[k] <= 1.0, (i, k, p[k]))

    def test_reveal_never_goes_backwards(self):
        D = 3.4
        vals = [boot.progress(i * D / 200, D)["reveal"] for i in range(201)]
        self.assertEqual(vals, sorted(vals))

    def test_terminal_types_then_finishes(self):
        D = 3.4
        L = boot.lines(False)
        self.assertEqual(boot.typed(L, 0.0, D), [])
        mid = boot.typed(L, D * 0.4, D)
        self.assertTrue(1 <= len(mid) < len(L) or mid[-1].endswith("_"))
        self.assertTrue(mid[-1].endswith("_"))
        end = boot.typed(L, D * 0.8, D)
        self.assertEqual(end, L)                                    # fully typed, no cursor left
        self.assertEqual(len(boot.typed(L, D * 0.8, D)), len(L))

    def test_first_run_is_longer_and_different(self):
        self.assertGreater(boot.duration(True), boot.duration(False))
        self.assertNotEqual(boot.lines(True), boot.lines(False))
        self.assertIn("ONLINE", boot.lines(False)[-1])


if __name__ == "__main__":
    unittest.main()
