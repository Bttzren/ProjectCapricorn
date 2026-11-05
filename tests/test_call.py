import array
import math
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import call as C  # noqa: E402


class NameTests(unittest.TestCase):
    def test_name_anywhere_and_misheard(self):
        for t in ("hey Capri what do you think", "yo kapri come here", "what about you capree", "Capri?"):
            self.assertTrue(C.mentions_name(t), t)
        for t in ("that's a carry", "we should play cherry", "choom, check this out", "copy that", ""):
            self.assertFalse(C.mentions_name(t), t)


class ConversationTests(unittest.TestCase):
    def conv(self, **kw):
        self.t = [1000.0]
        return C.Conversation(clock=lambda: self.t[0], **kw)

    def test_only_answers_when_addressed(self):
        c = self.conv()
        self.assertFalse(c.hear("Friend", "lol that clutch was insane"))
        self.assertFalse(c.hear("Friend", "I'm going to queue another game"))
        self.assertTrue(c.hear("Friend", "capri what's the best agent"))

    def test_cooldown_and_rate_limit(self):
        c = self.conv()
        self.assertTrue(c.hear("Friend", "Capri say hi"))
        c.said("Hi everyone.")
        self.t[0] += 2
        self.assertFalse(c.hear("Friend", "Capri say it again"))            # inside the cooldown
        for _ in range(8):
            self.t[0] += 6
            if c.hear("Friend", "Capri again"):
                c.said("ok")
        self.t[0] += 6
        self.assertFalse(c.hear("Friend", "Capri one more"))               # 8 a minute is the cap

    def test_follow_up_window(self):
        c = self.conv()
        self.assertTrue(c.hear("Friend", "capri tell a joke"))
        c.said("Why did the gamer cross the road?")
        self.t[0] += 8
        self.assertTrue(c.hear("Friend", "wait what do you mean by that?"))
        c.said("Respawn point.")
        self.t[0] += 30                                                    # window over
        self.assertFalse(c.hear("Friend", "what do you mean by that?"))
        self.t[0] += 1
        self.assertFalse(c.hear("Friend", "ok"))                           # too short to be a follow-up

    def test_messages_and_system_prompt(self):
        c = self.conv()
        c.hear("Friend", "capri roast Mike")
        c.said("Mike plays like his monitor is off.")
        m = c.messages()
        self.assertEqual(len(m), 1)
        self.assertIn("Friend: capri roast Mike", m[0]["content"])
        self.assertIn("Capri: Mike plays", m[0]["content"])
        self.assertIn("SKIP", C.Conversation.system("You are Capri.", "", "mild", ""))

    def test_clean_reply(self):
        f = C.Conversation.clean_reply
        self.assertEqual(f("SKIP"), "")
        self.assertEqual(f("*Sure* thing, choom!\nsecond line"), "Sure thing, choom!")
        self.assertEqual(f("I'm sorry, I can't"), "")
        self.assertLessEqual(len(f("word " * 100).split()), 25)


def tone(level, n=1600):
    return array.array("h", [int(level * math.sin(i / 3.0)) for i in range(n)]).tobytes()


class FakeWhisper:
    def __init__(self, texts):
        self.texts = list(texts)

    def transcribe(self, pcm):
        return self.texts.pop(0) if self.texts else ""


class LoopTests(unittest.TestCase):
    def run_loop(self, texts, answer):
        events, spoken = [], []
        t = [1000.0]
        conv = C.Conversation(clock=lambda: t[0])
        loop = C.CallLoop(FakeWhisper(texts), conv, answer, lambda k, x: events.append((k, x)), spoken.append)
        stream = ([tone(0)] * 10 + [tone(4000)] * 8 + [tone(0)] * 12) * len(texts)
        for c in stream:
            t[0] += 0.1
            loop.feed(c)
            while not loop.jobs.empty():
                loop.process(loop.jobs.get())
        return events, spoken

    def test_answers_when_addressed_and_speaks(self):
        events, spoken = self.run_loop(["we're about to start", "capri what's up"], lambda conv: "Not much, choom.")
        self.assertEqual([k for k, _ in events], ["heard", "heard", "reply"])
        self.assertEqual(spoken, ["Not much, choom."])

    def test_skip_means_silence(self):
        events, spoken = self.run_loop(["capri anyone here"], lambda conv: "SKIP")
        self.assertEqual(spoken, [])
        self.assertNotIn("reply", [k for k, _ in events])

    def test_ai_failure_is_reported_not_raised(self):
        def boom(conv):
            raise RuntimeError("no key")
        events, spoken = self.run_loop(["capri hello"], boom)
        self.assertIn(("error", "no key"), events)
        self.assertEqual(spoken, [])

    def test_thread_lifecycle(self):
        events = []
        loop = C.CallLoop(FakeWhisper(["capri hi"]), C.Conversation(), lambda c: "Hi!", lambda k, x: events.append(k),
                          lambda s: None)
        loop.start()
        loop.jobs.put(tone(4000, 8000))
        t0 = time.time()
        while "reply" not in events and time.time() - t0 < 5:
            time.sleep(0.02)
        loop.stop()
        self.assertIn("reply", events)


if __name__ == "__main__":
    unittest.main()
