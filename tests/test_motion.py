import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import motion as M  # noqa: E402


class MotionTests(unittest.TestCase):
    def test_walk_ramps_up_and_down(self):
        self.assertEqual(M.walk_factor(0, 4), 0.0)
        self.assertLess(M.walk_factor(0.1, 4), 0.5)
        self.assertEqual(M.walk_factor(2, 4), 1.0)
        self.assertLess(M.walk_factor(3.9, 4), 0.2)
        self.assertEqual(M.walk_factor(4, 4), 0.0)
        speeds = [M.walk_factor(t / 100, 4) for t in range(0, 40)]
        self.assertEqual(speeds, sorted(speeds))                 # smooth start, never jerks backwards
        self.assertGreater(M.walk_factor(0.25, 0.5), 0.9)        # short walk still reaches speed mid-way
        self.assertEqual(M.walk_factor(5, None), 1.0)            # open-ended: ramps up only

    def test_slows_near_the_edge_it_walks_toward(self):
        self.assertEqual(M.edge_slow(500, 0, 1000, 1, 60), 1.0)
        self.assertLess(M.edge_slow(990, 0, 1000, 1, 60), 0.35)
        self.assertEqual(M.edge_slow(990, 0, 1000, -1, 60), 1.0)  # walking away from it: full speed
        self.assertGreaterEqual(M.edge_slow(1000, 0, 1000, 1, 60), 0.25)

    def test_steps_follow_distance_not_time(self):
        p = M.step_phase(0.0, 26.0, 26.0)
        self.assertAlmostEqual(p, 1.0)
        self.assertAlmostEqual(M.step_phase(p, -13.0, 26.0), 1.5)
        self.assertEqual(M.step_phase(3.0, 0.0, 26.0), 3.0)      # standing still: feet stay put
        self.assertAlmostEqual(M.bob(1.0, 3), 0.0, places=6)
        self.assertAlmostEqual(M.bob(0.5, 3), -3.0)

    def test_landing_harder_after_long_fall(self):
        small, big = M.landing_squash(3), M.landing_squash(38)
        self.assertGreaterEqual(small, 0.35)
        self.assertLess(small, 0.5)
        self.assertEqual(big, 1.0)
        self.assertAlmostEqual(M.landing_squash(30, 2.0), M.landing_squash(15))   # scales with size/DPI


if __name__ == "__main__":
    unittest.main()
