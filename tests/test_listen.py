import array
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import listen as L  # noqa: E402


def tone(level, n=L.CHUNK):
    a = array.array("h", [int(level * math.sin(i / 3.0)) for i in range(n)])
    return a.tobytes()


def silence():
    return tone(0)


class EndpointTests(unittest.TestCase):
    def run_ep(self, levels, **kw):
        ep = L.Endpointer(**kw)
        for lv in levels:
            st = ep.feed(lv)
            if st in ("done", "timeout", "max"):
                return st, ep
        return ep.state, ep

    def test_speech_then_silence_ends(self):
        levels = [50] * 4 + [3000] * 10 + [60] * 15
        self.assertEqual(self.run_ep(levels)[0], "done")

    def test_never_talks_times_out(self):
        self.assertEqual(self.run_ep([50] * 100)[0], "timeout")

    def test_short_blip_is_not_speech(self):
        st, ep = self.run_ep([50] * 4 + [3000] + [50] * 100)
        self.assertEqual(st, "timeout")

    def test_noisy_room_raises_threshold(self):
        st, ep = self.run_ep([1000] * 4 + [1200] * 80)         # steady hum, nobody talking
        self.assertGreater(ep.threshold, 1200)
        self.assertEqual(st, "timeout")

    def test_long_talking_is_cut(self):
        st, _ = self.run_ep([50] * 4 + [4000] * 400, max_s=5)
        self.assertEqual(st, "max")

    def test_rms(self):
        self.assertEqual(L.rms(b""), 0.0)
        self.assertGreater(L.rms(tone(5000)), 3000)
        self.assertLess(L.rms(silence()), 1)


class FakeWhisper:
    def __init__(self, text):
        self.text, self.got = text, None

    def transcribe(self, pcm):
        self.got = len(pcm)
        return L.clean_transcript(self.text)


class ListenTests(unittest.TestCase):
    def test_record_and_transcribe(self):
        chunks = [silence()] * 4 + [tone(4000)] * 10 + [silence()] * 15 + [tone(4000)] * 50
        w = FakeWhisper("open discord")
        text, state = L.listen_once(iter(chunks), w)
        self.assertEqual((text, state), ("open discord", "done"))
        self.assertLess(w.got, len(b"".join(chunks)))           # stopped listening before the stream ended

    def test_nobody_talks_skips_transcription(self):
        w = FakeWhisper("hello")
        self.assertEqual(L.listen_once(iter([silence()] * 100), w), ("", "timeout"))
        self.assertIsNone(w.got)

    def test_real_whisper_wrapper_with_fake_model(self):
        import numpy  # noqa: F401
        calls = []

        class Seg:
            text = " Hey Capri, open Discord. "

        class Model:
            def transcribe(self, audio, **kw):
                calls.append((audio.dtype.name, audio.shape[0], kw["language"]))
                return [Seg()], None
        w = L.Whisper(loader=lambda name: Model())
        self.assertEqual(w.transcribe(tone(2000, 3200)), "Hey Capri, open Discord.")
        self.assertEqual(calls[0], ("float32", 3200, "en"))
        w.transcribe(tone(2000, 3200))
        self.assertEqual(len(calls), 2)


class TextTests(unittest.TestCase):
    def test_junk_dropped(self):
        for junk in ("", "Thank you.", "you", "[BLANK_AUDIO]", " . ", "(music)", "Thanks for watching!"):
            self.assertEqual(L.clean_transcript(junk), "", junk)
        self.assertEqual(L.clean_transcript("  what's   the plan [noise] "), "what's the plan")

    def test_intents(self):
        i = L.intent
        self.assertEqual(i("Hey Capri, stop."), ("stop", ""))
        self.assertEqual(i("never mind"), ("stop", ""))
        self.assertEqual(i("Hey Capri, join the discord and tell them I'll be in in 15")[0], "task")
        self.assertEqual(i("hey capri open spotify"), ("task", "Open spotify"))
        self.assertEqual(i("can you please play some music")[0], "task")
        self.assertEqual(i("how was your day")[0], "chat")
        self.assertEqual(i("Thank you.")[0], "none")
        self.assertEqual(i("Hey Capri")[0], "none")
        self.assertEqual(i("starting to feel tired")[0], "chat")     # 'starting' is not the word 'start'

    def test_installed_is_boolean(self):
        self.assertIsInstance(L.installed(), bool)


if __name__ == "__main__":
    unittest.main()


class CloseTests(unittest.TestCase):
    def test_microphone_generator_is_closed(self):
        closed = []

        def gen():
            try:
                while True:
                    yield tone(4000)
            finally:
                closed.append(1)
        L.record(gen(), L.Endpointer(max_s=1.0))
        self.assertEqual(closed, [1])

    def test_more_intents(self):
        self.assertEqual(L.intent("tell me a joke")[0], "chat")
        self.assertEqual(L.intent("go away")[0], "chat")
        self.assertEqual(L.intent("go to youtube")[0], "task")
        self.assertEqual(L.intent("can you please play some music")[0], "task")
