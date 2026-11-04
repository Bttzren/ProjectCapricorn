import os
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import progress  # noqa: E402
import sfx  # noqa: E402
import world  # noqa: E402


class SfxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.played = []

    def make(self, **kw):
        return sfx.Sfx(self.tmp.name, lambda p: self.played.append(p) or (None, 0.1), **kw)

    def test_every_pattern_renders_a_valid_wav_of_the_right_length(self):
        s = self.make()
        for name, notes in sfx.PATTERNS.items():
            p = s.path(name)
            with wave.open(p, "rb") as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, sfx.RATE))
                want = sum(int(sfx.RATE * ms / 1000.0) for _, ms in notes)
                self.assertEqual(w.getnframes(), want, name)

    def test_sounds_are_not_all_silence_but_never_clip(self):
        pcm = sfx.synth([(880, 100)])
        samples = [int.from_bytes(pcm[i:i + 2], "little", signed=True) for i in range(0, len(pcm), 2)]
        self.assertGreater(max(map(abs, samples)), 1000)
        self.assertLess(max(map(abs, samples)), 32767)
        self.assertEqual(set(sfx.synth([(0, 50)])), {0})

    def test_play_respects_enabled_busy_and_unknown(self):
        s = self.make()
        self.assertTrue(s.play("blip"))
        self.assertEqual(len(self.played), 1)
        s.enabled = False
        self.assertFalse(s.play("blip"))
        s.enabled = True
        self.assertFalse(s.play("nonsense"))
        busy = self.make(busy=lambda: True)
        self.assertFalse(busy.play("blip"))
        self.assertEqual(len(self.played), 1)

    def test_files_are_cached_and_player_errors_are_contained(self):
        s = self.make()
        a = s.path("click")
        m = os.path.getmtime(a)
        self.assertEqual(s.path("click"), a)
        self.assertEqual(os.path.getmtime(a), m)
        boom = sfx.Sfx(self.tmp.name, lambda p: 1 / 0)
        self.assertFalse(boom.play("blip"))


class WorldTests(unittest.TestCase):
    def test_birthday_parsing(self):
        self.assertEqual(world.parse_birthday("3-7"), "03-07")
        self.assertEqual(world.parse_birthday(" 12/25 "), "12-25")
        self.assertEqual(world.parse_birthday("02-29"), "02-29")
        for bad in ("", "13-01", "02-30", "banana", "1-32", "0-5"):
            self.assertIsNone(world.parse_birthday(bad), bad)

    def test_special_days_and_birthday_wins(self):
        self.assertEqual(world.special_day(12, 25)[0], "xmas")
        self.assertEqual(world.special_day(10, 31)[0], "halloween")
        self.assertIsNone(world.special_day(6, 6))
        key, line = world.special_day(12, 25, birthday="12-25", name="Sam")
        self.assertEqual(key, "birthday")
        self.assertIn("Sam", line)

    def test_battery_warns_once_then_celebrates_charging(self):
        st = {}
        self.assertIsNone(world.battery_event(st, 80, False))
        self.assertIn("19%", world.battery_event(st, 19, False))
        self.assertIsNone(world.battery_event(st, 18, False))         # no repeat
        self.assertIsNone(world.battery_event(st, 15, False))
        self.assertIn("juice", world.battery_event(st, 22, True))
        self.assertIsNone(world.battery_event(st, 40, True))
        self.assertIn("20%", world.battery_event(st, 20, False))      # warns again later

    def test_battery_unknown_values_are_ignored(self):
        self.assertIsNone(world.battery_event({}, None, False))
        self.assertIsNone(world.battery_event({}, 255, False))

    def test_radio_lines_are_short(self):
        for l in world.RADIO:
            self.assertLessEqual(len(l), 100, l)


class ProgressExtrasTests(unittest.TestCase):
    def test_breach_payouts_and_achievements(self):
        p = progress.Progress({})
        m = p.record_breach(2, 3)
        self.assertEqual(p.eddies, 10)
        self.assertIn("2/3", m[0])
        m = p.record_breach(3, 3)
        self.assertEqual(p.eddies, 10 + 20 + 20)                      # 5x3 + 5 perfect bonus, then Netrunner (+20)
        self.assertTrue(p.unlocked("netrunner"))
        self.assertEqual(p.record_breach(0, 3)[0].split(",")[1].strip(), "+0 eddies.")

    def test_ice_breaker_after_five_runs(self):
        p = progress.Progress({})
        for _ in range(5):
            p.record_breach(1, 3)
        self.assertTrue(p.unlocked("ice_breaker"))

    def test_spend(self):
        p = progress.Progress({"eddies": 5})
        self.assertTrue(p.spend(3))
        self.assertEqual(p.eddies, 2)
        self.assertFalse(p.spend(3))
        self.assertEqual(p.eddies, 2)


if __name__ == "__main__":
    unittest.main()
