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
        self.assertEqual(i("hey capri open spotify"), ("launch", "open spotify"))
        self.assertEqual(i("can you please play some music")[0], "control")
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
        self.assertEqual(L.intent("go to youtube")[0], "launch")
        self.assertEqual(L.intent("can you please play some music")[0], "control")


class WakeWordTests(unittest.TestCase):
    def test_strip_wake(self):
        s = L.strip_wake
        self.assertEqual(s("Hey Capri, open Discord"), (True, "open Discord"))
        self.assertEqual(s("hey capri"), (True, ""))
        self.assertEqual(s("Choom. what's the weather like"), (True, "what's the weather like"))
        self.assertEqual(s("Yo choom, play some music"), (True, "play some music"))
        self.assertEqual(s("Hey, Kapri! open spotify"), (True, "open spotify"))
        self.assertEqual(s("hey chum open youtube"), (True, "open youtube"))

    def test_not_woken_by_other_speech(self):
        s = L.strip_wake
        for t in ("I was telling capri about it", "what time is it", "hey Chris open the door", "the copy is ready",
                  "hey cherry open it", "carry the box", "", "hey", "zoom call at three"):
            self.assertFalse(s(t)[0], t)

    def test_segmenter_cuts_phrases(self):
        sg = L.Segmenter()
        out = []
        stream = [silence()] * 10 + [tone(4000)] * 8 + [silence()] * 12 + [silence()] * 5 + [tone(4000)] * 6 + [silence()] * 12
        for c in stream:
            u = sg.feed(c)
            if u:
                out.append(u)
        self.assertEqual(len(out), 2)
        self.assertGreater(len(out[0]), len(tone(4000)) * 8)       # includes the pre-roll and the whole phrase

    def test_blip_is_not_a_phrase_and_hum_is_learned(self):
        sg = L.Segmenter()
        self.assertEqual([sg.feed(c) for c in [silence()] * 5 + [tone(4000)] + [silence()] * 20], [None] * 26)
        sg = L.Segmenter()
        hum = [tone(900)] * 60                                     # steady background noise
        self.assertEqual([x for x in (sg.feed(c) for c in hum) if x], [])


class FakeWhisper2:
    def __init__(self, texts):
        self.texts = list(texts)
        self.calls = 0

    def transcribe(self, pcm):
        self.calls += 1
        return L.clean_transcript(self.texts.pop(0))


def phrase(n=8):
    return [tone(4000)] * n + [silence()] * 12


def run_loop(texts, stream, **kw):
    events = []
    t = [0.0]
    w = FakeWhisper2(texts)
    loop = L.WakeLoop(w, lambda k, x: events.append((k, x)), clock=lambda: t[0], **kw)
    for c in stream:
        t[0] += 0.1
        loop.read(iter([c]))
        while not loop.jobs.empty():
            loop.process(loop.jobs.get())
    return events, w, loop


class WakeLoopTests(unittest.TestCase):
    QUIET = [silence()] * 10

    def test_command_in_one_phrase_and_other_talk_dropped(self):
        ev, w, _ = run_loop(["just chatting with friends", "Hey Capri, open discord"],
                            self.QUIET + phrase() + phrase())
        self.assertEqual(ev, [("command", "open discord")])
        self.assertEqual(w.calls, 2)

    def test_wake_then_follow_up_command(self):
        ev, _, _ = run_loop(["hey capri", "tell my friends I'm late"], self.QUIET + phrase() + phrase())
        self.assertEqual(ev, [("wake", ""), ("command", "tell my friends I'm late")])

    def test_follow_up_expires(self):
        ev, _, _ = run_loop(["choom", "random chatter"], self.QUIET + phrase() + [silence()] * 120 + phrase(),
                            follow_s=3.0)
        self.assertEqual(ev, [("wake", "")])

    def test_ignored_while_paused_and_just_after(self):
        state = {"p": True}
        events = []
        t = [0.0]
        w = FakeWhisper2(["hey capri open discord"] * 3)
        loop = L.WakeLoop(w, lambda k, x: events.append((k, x)), paused=lambda: state["p"], clock=lambda: t[0])
        for c in self.QUIET + phrase():
            t[0] += 0.1
            loop.read(iter([c]))
        self.assertTrue(loop.jobs.empty())
        self.assertEqual(w.calls, 0)

    def test_long_phrases_and_rate_limit(self):
        long_phrase = [tone(4000)] * 150 + [silence()] * 12
        ev, w, _ = run_loop(["hey capri open x"], self.QUIET + long_phrase, max_phrase_s=5.0, segmenter=L.Segmenter(max_s=30))
        self.assertEqual((ev, w.calls), ([], 0))
        stream = self.QUIET + phrase() * 5
        ev, w, _ = run_loop(["choom hi"] * 5, stream, per_min=2)
        self.assertEqual(w.calls, 2)

    def test_whisper_errors_are_reported_not_raised(self):
        class Bad:
            def transcribe(self, pcm):
                raise RuntimeError("no model")
        events = []
        loop = L.WakeLoop(Bad(), lambda k, x: events.append((k, x)))
        loop.process(tone(4000, 8000))
        self.assertEqual(events, [("error", "no model")])

    def test_threads_start_and_stop(self):
        events = []
        stream = self.QUIET + phrase()

        def source():
            for c in stream:
                time.sleep(0.002)
                yield c
            while not loop._stop.is_set():
                time.sleep(0.01)
                yield silence()
        import time
        loop = L.WakeLoop(FakeWhisper2(["hey capri open spotify"]), lambda k, x: events.append((k, x)))
        loop.start(source)
        t0 = time.time()
        while not events and time.time() - t0 < 5:
            time.sleep(0.02)
        loop.stop()
        self.assertEqual(events, [("command", "open spotify")])
