import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import voice  # noqa: E402


class FakeProc:
    def __init__(self, done=False):
        self.done, self.written, self.terminated = done, b"", False
        outer = self

        class Stdin:
            def write(self, b):
                outer.written += b

            def close(self):
                pass
        self.stdin = Stdin()

    def poll(self):
        return 0 if self.done else None

    def terminate(self):
        self.terminated, self.done = True, True


class Rig:
    def __init__(self):
        self.procs, self.t = [], 1000.0

    def popen(self, argv, **kw):
        p = FakeProc()
        p.argv, p.kw = argv, kw
        self.procs.append(p)
        return p

    def clock(self):
        return self.t


def speaker(r, platform="linux", have=("espeak-ng",), **kw):
    return voice.Speaker(platform=platform, which=lambda n: "/bin/" + n if n in have else None,
                         popen=r.popen, clock=r.clock, **kw)


class CleanTests(unittest.TestCase):
    def test_strips_stage_directions_notes_and_symbols(self):
        self.assertEqual(voice.clean("*glitches* Hello there! \U0001F600"), "Hello there!")
        self.assertEqual(voice.clean("Hey. Good to see you. (No API key set, so I'm in offline mode.)"),
                         "Hey. Good to see you")
        self.assertEqual(voice.clean("see https://example.com/x now"), "see link now")

    def test_quiet_for_noise_and_snores(self):
        for t in ("", "...", "!", "zzz...", "*glitches*", "Z z Z"):
            self.assertEqual(voice.clean(t), "", t)

    def test_ellipsis_becomes_a_pause_and_long_text_is_capped(self):
        self.assertEqual(voice.clean("...hm? Oh. Hi."), "hm? Oh. Hi")
        self.assertLessEqual(len(voice.clean("word " * 200)), 280)


class CommandTests(unittest.TestCase):
    def test_each_platform(self):
        w = voice.build_command("win32", which=lambda n: "C:/ps.exe" if n == "powershell" else None)
        self.assertEqual(w[0], "C:/ps.exe")
        self.assertIn("System.Speech", w[-1])
        self.assertIn("Zira", w[-1])
        m = voice.build_command("darwin", which=lambda n: "/usr/bin/say")
        self.assertTrue(m[0].endswith("say"))
        self.assertEqual(m[-2:], ["-f", "-"])
        l = voice.build_command("linux", which=lambda n: "/x/" + n if n == "espeak" else None)
        self.assertTrue(l[0].endswith("espeak"))
        self.assertIn("--stdin", l)

    def test_unavailable_when_no_engine(self):
        self.assertIsNone(voice.build_command("linux", which=lambda n: None))
        self.assertIsNone(voice.build_command("win32", which=lambda n: None))

    def test_voice_name_is_quoted_safely_on_windows(self):
        w = voice.build_command("win32", which=lambda n: "ps", voice="Bob's Voice")
        self.assertIn("Bob''s Voice", w[-1])


class SpeakerTests(unittest.TestCase):
    def test_text_goes_on_stdin_not_argv(self):
        r = Rig()
        s = speaker(r)
        self.assertTrue(s.speak("Hello; whoami `id` now"))
        p = r.procs[0]
        self.assertNotIn("whoami", " ".join(p.argv))
        self.assertIn(b"whoami", p.written)
        self.assertNotIn("id", p.argv[1:])

    def test_ambient_dropped_while_busy_and_rate_limited_priority_interrupts(self):
        r = Rig()
        s = speaker(r)
        self.assertTrue(s.speak("first line"))
        self.assertFalse(s.speak("second line"))            # busy
        self.assertTrue(s.speak("alert!", priority=True))   # interrupts
        self.assertTrue(r.procs[0].terminated)
        r.procs[1].done = True
        r.t += 1
        self.assertFalse(s.speak("too soon"))               # within min_gap
        r.t += 5
        self.assertTrue(s.speak("fine now"))

    def test_nothing_spoken_when_unavailable_or_empty(self):
        r = Rig()
        self.assertFalse(speaker(r, have=()).speak("hi there"))
        self.assertFalse(speaker(r).speak("..."))
        self.assertEqual(r.procs, [])

    def test_failure_disables_voice_instead_of_crashing(self):
        def boom(*a, **k):
            raise OSError("no such file")
        s = voice.Speaker(platform="linux", which=lambda n: "/x/" + n, popen=boom)
        self.assertFalse(s.speak("hello there"))
        self.assertFalse(s.available)

    @unittest.skipIf(sys.platform.startswith("win"), "uses a POSIX shell script as a fake engine")
    def test_real_subprocess_path_with_fake_engine(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "heard.txt")
            exe = os.path.join(d, "espeak-ng")
            with open(exe, "w") as f:
                f.write(f"#!/bin/sh\ncat > '{out}'\n")
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
            s = voice.Speaker(platform="linux", which=lambda n: exe if n == "espeak-ng" else None)
            self.assertTrue(s.speak("Hi, it is me! \U0001F600"))
            for _ in range(50):
                if not s.speaking:
                    break
                time.sleep(0.05)
            self.assertEqual(open(out, encoding="utf-8").read(), "Hi, it is me!")


if __name__ == "__main__":
    unittest.main()
