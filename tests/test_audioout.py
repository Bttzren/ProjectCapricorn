import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import audioout as A  # noqa: E402


DEVICES = [
    {"name": "Microphone (Realtek Audio)", "max_output_channels": 0},
    {"name": "Speakers (Realtek Audio)", "max_output_channels": 2},
    {"name": "CABLE Output (VB-Audio Virtual Cable)", "max_output_channels": 0, "max_input_channels": 2},
    {"name": "CABLE Input (VB-Audio Virtual Cable)", "max_output_channels": 2},
    {"name": "Headphones (USB)", "max_output_channels": 2},
]


class FindCableTests(unittest.TestCase):
    def test_finds_the_cable_input_not_output(self):
        self.assertEqual(A.find_cable(DEVICES), 3)

    def test_none_when_absent(self):
        self.assertIsNone(A.find_cable(DEVICES[:2] + DEVICES[4:]))
        self.assertIsNone(A.find_cable([]))

    def test_other_virtual_devices(self):
        self.assertEqual(A.find_cable([{"name": "BlackHole 2ch", "max_output_channels": 2}]), 0)
        self.assertEqual(A.find_cable([{"name": "VoiceMeeter Input (VB-Audio VoiceMeeter VAIO)",
                                        "max_output_channels": 2}]), 0)
        # a microphone-side virtual device must not be chosen
        self.assertIsNone(A.find_cable([{"name": "CABLE Output (VB-Audio Virtual Cable)", "max_output_channels": 0}]))


def make_mp3(seconds=1.0):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                    "-ac", "1", "-ar", "24000", p], check=True)
    return p


class DecodeTests(unittest.TestCase):
    def test_real_mp3_decodes_to_requested_rate_and_channels(self):
        try:
            import av  # noqa: F401
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest("av/numpy not installed")
        p = make_mp3(1.0)
        data = A.decode(p, 48000, 2)
        self.assertEqual(data.shape[1], 2)
        self.assertAlmostEqual(len(data) / 48000.0, 1.0, delta=0.15)
        self.assertLessEqual(abs(data).max(), 0.95)
        mono = A.decode(p, 16000, 1)
        self.assertEqual(mono.shape[1], 1)
        self.assertGreater(abs(mono).max(), 0.1)                     # it's a real tone, not silence


class FakeSD:
    def __init__(self):
        self.streams, self.default = [], type("D", (), {"device": (0, 1)})()

    def query_devices(self, i=None):
        if i is None:
            return DEVICES
        return {"default_samplerate": 48000, "max_output_channels": DEVICES[i]["max_output_channels"] or 2}

    def OutputStream(self, device, samplerate, channels, dtype):
        s = FakeStream(device, samplerate, channels)
        self.streams.append(s)
        return s


class FakeStream:
    def __init__(self, device, rate, ch):
        self.device, self.rate, self.ch, self.written = device, rate, ch, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    slow = False

    def write(self, data):
        if FakeStream.slow:
            import time
            time.sleep(0.002)
        self.written += len(data)


class PlayerTests(unittest.TestCase):
    def test_plays_on_cable_and_speakers_and_reports_length(self):
        import time
        sd = FakeSD()
        decoded = []

        def dec(path, rate, ch):
            decoded.append((rate, ch))
            import numpy as np
            return np.zeros((rate * 2, ch), dtype="float32")
        pl = A.Player(sd, decoder=dec, chunk=4800)
        secs = A.call_player(pl, 3)("x.mp3")
        self.assertEqual(secs[0], None)
        self.assertAlmostEqual(secs[1], 2.0, places=2)
        t0 = time.time()
        while pl.busy and time.time() - t0 < 5:
            time.sleep(0.01)
        self.assertEqual(sorted(s.device for s in sd.streams), [1, 3])
        self.assertTrue(all(s.written == 96000 for s in sd.streams))

    def test_stop_interrupts(self):
        import time
        sd = FakeSD()
        FakeStream.slow = True
        self.addCleanup(setattr, FakeStream, "slow", False)

        def dec(path, rate, ch):
            import numpy as np
            return np.zeros((rate * 600, ch), dtype="float32")
        pl = A.Player(sd, decoder=dec, chunk=4800)
        pl.play("x", [3])
        time.sleep(0.05)
        pl.stop()
        t0 = time.time()
        while pl.busy and time.time() - t0 < 5:
            time.sleep(0.01)
        self.assertFalse(pl.busy)
        self.assertLess(sd.streams[0].written, 48000 * 600)

    def test_no_devices_is_an_error_and_duplicates_collapse(self):
        pl = A.Player(FakeSD(), decoder=lambda *a: None)
        with self.assertRaises(RuntimeError):
            pl.play("x", [None])
        sd = FakeSD()

        def dec(path, rate, ch):
            import numpy as np
            return np.zeros((100, ch), dtype="float32")
        pl = A.Player(sd, decoder=dec)
        pl.play("x", [3, 3])
        import time
        time.sleep(0.2)
        self.assertEqual(len(sd.streams), 1)


if __name__ == "__main__":
    unittest.main()
