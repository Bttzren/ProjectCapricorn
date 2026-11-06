import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import monitors as M  # noqa: E402
import physics as P  # noqa: E402
import sysmon as S  # noqa: E402


class PhysicsTests(unittest.TestCase):
    def test_throw_speed_comes_from_recent_mouse_motion(self):
        t = P.Tracker()
        for i in range(6):
            t.add(1.0 + i * 0.02, 100 + i * 20, 500)            # 1000 px/s to the right
        vx, vy = t.velocity(1.11)
        self.assertAlmostEqual(vx, 1000, delta=60)
        self.assertAlmostEqual(vy, 0, delta=1)

    def test_holding_still_before_release_is_no_throw(self):
        t = P.Tracker()
        t.add(1.0, 0, 0)
        t.add(1.05, 400, 0)
        self.assertEqual(t.velocity(1.5), (0.0, 0.0))            # stale: she was held still afterwards
        self.assertEqual(P.Tracker().velocity(1.0), (0.0, 0.0))

    def test_launch_is_clamped_and_reports_power(self):
        vx, vy, power = P.launch(1e6, -1e6, 1.0)
        self.assertEqual((vx, vy), (P.THROW_MAX, -P.THROW_MAX))
        self.assertEqual(power, 1.0)
        self.assertLess(P.launch(200, 0)[2], 0.2)
        self.assertGreater(P.launch(0, 0, 2.0)[2] + 1, 0)

    def run_fall(self, vx, vy, steps=400):
        x, y, evs = 300.0, 200.0, []
        box = (0, 0, 1000, 800)
        for _ in range(steps):
            x, y, vx, vy, ev = P.step_air(x, y, vx, vy, 0.04, box, 40, 170)
            evs.append(ev)
            if "floor" in ev:
                break
        return x, y, evs

    def test_a_drop_bounces_then_comes_to_rest_on_the_floor(self):
        x, y, evs = self.run_fall(0, 0)
        self.assertEqual(y, 800)
        self.assertTrue(any("bounce" in e for e in evs))
        self.assertIn("floor", evs[-1])

    def test_a_hard_throw_hits_the_wall_and_stays_on_screen(self):
        x, y, evs = self.run_fall(40, -5)
        self.assertTrue(any("wall" in e for e in evs))
        self.assertTrue(40 <= x <= 960)

    def test_throw_up_into_the_ceiling_rebounds(self):
        x, y, vx, vy, ev = P.step_air(500, 175, 0, -30, 0.04, (0, 0, 1000, 800), 40, 170)
        self.assertIn("ceiling", ev)
        self.assertGreater(vy, 0)
        self.assertGreaterEqual(y - 170, 0)


MONS = [M.Mon((0, 0, 1920, 1080), (0, 0, 1920, 1040), True), M.Mon((1920, 0, 3840, 1080), (1920, 0, 3840, 1080), False),
        M.Mon((-1280, 100, 0, 1000), (-1280, 100, 0, 1000), False)]


class MonitorTests(unittest.TestCase):
    def test_which_monitor_holds_a_point(self):
        self.assertEqual(M.index_at(MONS, 500, 500), 0)
        self.assertEqual(M.index_at(MONS, 2500, 500), 1)
        self.assertEqual(M.index_at(MONS, -300, 500), 2)
        self.assertEqual(M.index_at(MONS, 4100, 500), 1)          # off every screen: nearest
        self.assertIsNone(M.index_at([], 1, 1))

    def test_neighbors(self):
        self.assertEqual(M.neighbor(MONS, 0, "right"), 1)
        self.assertEqual(M.neighbor(MONS, 0, "left"), 2)
        self.assertIsNone(M.neighbor(MONS, 1, "right"))
        self.assertIsNone(M.neighbor(MONS, None, "left"))

    def test_she_follows_only_after_you_settle_and_not_too_often(self):
        f = M.Follower(dwell=8, cooldown=60)
        self.assertIsNone(f.update(0, 0, 1))                      # you just crossed over
        self.assertIsNone(f.update(5, 0, 1))
        self.assertIsNone(f.update(6, 0, 0))                      # you went back: reset
        self.assertIsNone(f.update(7, 0, 1))
        self.assertEqual(f.update(16, 0, 1), 1)                   # settled for 9 s
        self.assertIsNone(f.update(20, 0, 1))
        self.assertIsNone(f.update(40, 0, 1))                     # cooldown
        self.assertIsNone(f.update(70, 0, 1))                     # (re-arming after cooldown)
        self.assertEqual(f.update(80, 0, 1), 1)


class SysmonTests(unittest.TestCase):
    def test_cpu_meter_computes_load_between_samples(self):
        seq = iter([(100, 1000), (150, 1100), (150, 1200)])
        m = S.CpuMeter(lambda: next(seq))
        self.assertIsNone(m.sample())
        self.assertEqual(m.sample(), 50.0)
        self.assertEqual(m.sample(), 100.0)
        self.assertIsNone(S.CpuMeter(lambda: None).sample())

    def test_cpu_high_is_announced_once_after_sustained_load_then_calm(self):
        r = S.Reactor()
        evs = []
        for t in range(0, 40, 3):
            evs += r.feed(t, 98.0, {})
        self.assertEqual([e[0] for e in evs], ["cpu_high"])
        evs = []
        for t in range(40, 100, 3):
            evs += r.feed(t, 10.0, {})
        self.assertEqual([e[0] for e in evs], ["cpu_calm"])

    def test_a_short_spike_says_nothing_and_complaints_are_rate_limited(self):
        r = S.Reactor()
        out = []
        for t in range(0, 12, 3):
            out += r.feed(t, 99.0, {})
        out += r.feed(15, 5.0, {})
        self.assertEqual(out, [])
        for t in range(100, 130, 3):
            out += r.feed(t, 99.0, {})
        self.assertEqual([e[0] for e in out], ["cpu_high"])
        for t in range(140, 400, 3):                              # calm, then hot again inside the cooldown
            out += r.feed(t, 5.0 if t < 200 else 99.0, {})
        self.assertEqual([e[0] for e in out].count("cpu_high"), 1)

    def test_usb_baseline_is_silent_then_plug_and_unplug_are_noticed(self):
        r = S.Reactor()
        self.assertEqual(r.feed(0, None, {"a": "Old mouse"}), [])
        self.assertEqual(r.feed(3, None, {"a": "Old mouse", "b": "Thumb drive"}), [("usb_in", "Thumb drive")])
        self.assertEqual(r.feed(10, None, {"a": "Old mouse"}), [("usb_out", "Thumb drive")])
        self.assertEqual(r.feed(20, None, {"a": "Old mouse"}), [])

    def test_watch_collects_events_for_the_app_to_drain(self):
        t = [0.0]
        devs = [{}]
        w = S.Watch(cpu_reader=lambda: None, dev_reader=lambda: devs[0], clock=lambda: t[0])
        w.poll()
        devs[0] = {"x": "Keyboard"}
        t[0] = 5.0
        w.poll()
        self.assertEqual(w.drain(), [("usb_in", "Keyboard")])
        self.assertEqual(w.drain(), [])

    def test_texts_exist_for_every_event_and_dont_leak_labels_to_the_ai(self):
        for kind in ("cpu_high", "cpu_calm", "usb_in", "usb_out"):
            self.assertTrue(S.LINES[kind])
            self.assertIn("the user", S.SITUATION[kind])


import random  # noqa: E402

import awareness as A  # noqa: E402
import speech as SP  # noqa: E402


class JealousyTests(unittest.TestCase):
    def test_other_ai_sites_are_recognised(self):
        for title in ("ChatGPT - Google Chrome", "Grok", "DeepSeek Chat", "Perplexity", "Gemini - Microsoft Edge"):
            self.assertEqual(A.classify(title), "ai", title)

    def test_jealousy_is_words_only_and_mood_flavoured(self):
        rng = random.Random(1)
        for mood in ("mild", "sassy", "lonely", "playful", "content", "hyper"):
            self.assertTrue(A.jealous_line(mood, rng))
        self.assertIn("ai", A.NUDGE_AFTER)
        self.assertIn("never mean", SP.user_prompt("jealous", {"minutes": 7}))
        self.assertIn("7 minutes", SP.user_prompt("jealous", {"minutes": 7}))
        self.assertTrue(A.RELIEF)
        self.assertIn("came back", SP.user_prompt("relief", {}))


if __name__ == "__main__":
    unittest.main()
