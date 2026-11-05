import json
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


def wav_bytes(seconds=0.5, rate=8000):
    import io
    import wave
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(rate * seconds))
    return buf.getvalue()


class FakeResp:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeFishServer:
    def __init__(self, data=None, errors=()):
        self.data, self.errors, self.requests = data if data is not None else wav_bytes(), list(errors), []

    def __call__(self, req, timeout=None):
        import urllib.error
        self.requests.append(req)
        if self.errors:
            code = self.errors.pop(0)
            raise urllib.error.HTTPError(req.full_url, code, "err", {}, None)
        return FakeResp(self.data)


class FishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def fish(self, server, **kw):
        return voice.FishVoice("sekrit-key", cache_dir=self.tmp.name, opener=server, **kw)

    def test_request_shape_uses_capris_voice_id_and_bearer_key(self):
        srv = FakeFishServer()
        path = self.fish(srv).fetch("Hey, choom!")
        req = srv.requests[0]
        self.assertEqual(req.full_url, "https://api.fish.audio/v1/tts")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer sekrit-key")
        body = json.loads(req.data)
        self.assertEqual(body["text"], "Hey, choom!")
        self.assertEqual(body["reference_id"], "ef387f44931d4ab6a3f959a083c9fbb1")
        self.assertEqual(body["format"], "wav")
        self.assertTrue(os.path.isfile(path))

    def test_audio_is_cached_so_repeat_lines_cost_nothing(self):
        srv = FakeFishServer()
        f = self.fish(srv)
        a = f.fetch("Boop.")
        b = f.fetch("Boop.")
        self.assertEqual(a, b)
        self.assertEqual(len(srv.requests), 1)
        f.fetch("Different line.")
        self.assertEqual(len(srv.requests), 2)

    def test_model_header_rejected_retries_without_it(self):
        srv = FakeFishServer(errors=[400])
        self.fish(srv).fetch("hello there")
        self.assertEqual(len(srv.requests), 2)
        self.assertIsNotNone(srv.requests[0].get_header("Model"))
        self.assertIsNone(srv.requests[1].get_header("Model"))

    def test_helpful_errors(self):
        for code, word in ((401, "bad Fish Audio key"), (402, "credits"), (404, "voice model not found")):
            with self.assertRaises(RuntimeError) as cm:
                self.fish(FakeFishServer(errors=[code])).fetch("x" + str(code) + " line")
            self.assertIn(word, str(cm.exception))

    def test_non_wav_response_rejected_and_not_cached(self):
        f = self.fish(FakeFishServer(data=b"<html>nope</html>"))
        with self.assertRaises(RuntimeError):
            f.fetch("some line")
        self.assertEqual([n for n in os.listdir(self.tmp.name) if n.endswith(".wav")], [])

    def test_cache_is_pruned(self):
        f = self.fish(FakeFishServer(), max_cache=3)
        for i in range(6):
            f.fetch(f"line number {i}")
        self.assertLessEqual(len([n for n in os.listdir(self.tmp.name) if n.endswith(".wav")]), 3)

    def test_wav_seconds(self):
        p = os.path.join(self.tmp.name, "t.wav")
        open(p, "wb").write(wav_bytes(0.5, 8000))
        self.assertAlmostEqual(voice.wav_seconds(p), 0.5, places=2)
        self.assertEqual(voice.wav_seconds(os.path.join(self.tmp.name, "missing.wav")), 0.0)

    def speaker(self, srv, r, played, have=("espeak-ng",), **kw):
        def player(path):
            played.append(path)
            return None, 0.5
        return voice.Speaker(platform="linux", which=lambda n: "/bin/" + n if n in have else None,
                             popen=r.popen, clock=r.clock, fish=self.fish(srv), player=player, threaded=False, **kw)

    def test_speaker_uses_fish_and_reports_speaking_while_audio_plays(self):
        r, played = Rig(), []
        s = self.speaker(FakeFishServer(), r, played)
        self.assertEqual(s.engine, "fish")
        self.assertTrue(s.speak("Hey, choom!"))
        self.assertEqual(len(played), 1)
        self.assertEqual(r.procs, [])                 # system voice untouched
        self.assertTrue(s.speaking)
        r.t += 1
        self.assertFalse(s.speaking)                  # clip finished (0.5s)

    def test_fish_failure_falls_back_to_system_voice_and_records_why(self):
        r, played = Rig(), []
        s = self.speaker(FakeFishServer(errors=[402]), r, played)
        self.assertTrue(s.speak("Water break, choom"))
        self.assertEqual(played, [])
        self.assertEqual(len(r.procs), 1)
        self.assertIn(b"Water break", r.procs[0].written)
        self.assertIn("credits", s.last_error)

    def test_no_player_falls_back_to_system_voice(self):
        r = Rig()
        s = voice.Speaker(platform="linux", which=lambda n: "/bin/" + n if n == "espeak-ng" else None,
                          popen=r.popen, clock=r.clock, fish=self.fish(FakeFishServer()),
                          player=lambda p: None, threaded=False)
        self.assertTrue(s.speak("hello there"))
        self.assertEqual(len(r.procs), 1)
        self.assertIn("audio player", s.last_error)

    def test_fish_only_still_counts_as_available(self):
        r = Rig()
        s = voice.Speaker(platform="linux", which=lambda n: None, popen=r.popen, clock=r.clock,
                          fish=self.fish(FakeFishServer()), player=lambda p: (None, 0.1), threaded=False)
        self.assertTrue(s.available)
        self.assertTrue(s.speak("hello there"))

    def test_stopping_during_download_cancels_playback(self):
        r, played = Rig(), []
        s = self.speaker(FakeFishServer(), r, played)
        orig = s.fish.fetch

        def slow_fetch(text):
            path = orig(text)
            s.stop()                                   # user/priority line arrives mid-download
            return path
        s.fish.fetch = slow_fetch
        s.speak("long line here")
        self.assertEqual(played, [])

    def test_play_file_picks_a_linux_player_and_survives_none(self):
        launched = []
        res = voice.play_file("/x/a.wav", "linux", which=lambda n: "/bin/" + n if n == "aplay" else None,
                              popen=lambda argv, **k: launched.append(argv) or FakeProc())
        self.assertEqual(launched[0][0], "/bin/aplay")
        self.assertIsNotNone(res)
        self.assertIsNone(voice.play_file("/x/a.wav", "linux", which=lambda n: None))
        mac = voice.play_file("/x/a.wav", "darwin", which=lambda n: "/usr/bin/" + n,
                              popen=lambda argv, **k: launched.append(argv) or FakeProc())
        self.assertEqual(launched[-1], ["/usr/bin/afplay", "/x/a.wav"])

    def test_windows_playback_uses_winsound_async_from_a_file(self):
        calls = []

        class WS:
            SND_FILENAME, SND_ASYNC, SND_PURGE = 1, 2, 4

            @staticmethod
            def PlaySound(a, b):
                calls.append((a, b))
        p = os.path.join(self.tmp.name, "w.wav")
        open(p, "wb").write(wav_bytes(0.25, 8000))
        proc, secs = voice.play_file(p, "win32", winsound_mod=WS)
        self.assertIsNone(proc)
        self.assertAlmostEqual(secs, 0.25, places=2)
        self.assertEqual(calls[0], (p, 3))
        voice.stop_playback("win32", winsound_mod=WS)
        self.assertEqual(calls[1], (None, 4))


if __name__ == "__main__":
    unittest.main()


class EdgeVoiceTests(unittest.TestCase):
    def test_edge_fetch_caches_and_cleans_up(self):
        import tempfile
        d = tempfile.mkdtemp()
        calls = []

        def synth(text, v, path):
            calls.append(text)
            with open(path, "wb") as f:
                f.write(b"x" * 500)
        e = voice.EdgeVoice("en-US-AriaNeural", d, synth=synth)
        p1 = e.fetch("hello choom")
        self.assertTrue(p1.endswith(".mp3") and os.path.getsize(p1) == 500)
        self.assertEqual(e.fetch("hello choom"), p1)
        self.assertEqual(len(calls), 1)
        self.assertFalse([f for f in os.listdir(d) if f.endswith(".part")])

    def test_edge_failure_raises_and_leaves_no_file(self):
        import tempfile
        d = tempfile.mkdtemp()

        def synth(text, v, path):
            open(path, "wb").write(b"")
        with self.assertRaises(RuntimeError):
            voice.EdgeVoice("v", d, synth=synth).fetch("hi")
        self.assertEqual(os.listdir(d), [])

    def test_speaker_prefers_fish_then_edge_then_system(self):
        class Bad:
            def fetch(self, t):
                raise RuntimeError("no credits")

        class Good:
            def fetch(self, t):
                return "/tmp/x.mp3"
        played, sys_said = [], []
        sp = voice.Speaker(platform="linux", which=lambda n: None, fish=Bad(), edge=Good(), threaded=False,
                           player=lambda p: (played.append(p), (None, 1.0))[1])
        self.assertEqual(sp.engine, "fish")
        sp.speak("hi there", priority=True)
        self.assertEqual(played, ["/tmp/x.mp3"])
        sp2 = voice.Speaker(platform="linux", which=lambda n: None, edge=Good(), threaded=False,
                            player=lambda p: (played.append(p), (None, 1.0))[1])
        self.assertEqual(sp2.engine, "edge")
        self.assertTrue(sp2.available)

    def test_mp3_windows_path_goes_on_stdin(self):
        import io
        seen = {}

        class P:
            def __init__(self, argv, **kw):
                seen["argv"] = argv
                self.stdin = io.BytesIO()
                self.stdin.close = lambda: seen.setdefault("data", self.stdin.getvalue())
        res = voice.play_mp3("C:\\Users\\O'Brien\\a.mp3", "win32", which=lambda n: "powershell.exe", popen=P)
        self.assertIsNotNone(res)
        self.assertNotIn("O'Brien", " ".join(seen["argv"]))
        self.assertIn(b"O'Brien", seen["data"])

    def test_play_file_routes_mp3(self):
        got = []
        voice.play_file("/tmp/a.mp3", "linux", which=lambda n: "/usr/bin/" + n if n == "mpg123" else None,
                        popen=lambda argv, **kw: got.append(argv))
        self.assertEqual(got[0][0], "/usr/bin/mpg123")


class CallRoutingTests(unittest.TestCase):
    class Good:
        def fetch(self, t):
            return "/tmp/x.mp3"

    def test_call_speech_goes_to_the_call_player_and_needs_neural_voice(self):
        local, call = [], []
        sp = voice.Speaker(platform="linux", which=lambda n: None, edge=self.Good(), threaded=False,
                           player=lambda p: (local.append(p), (None, 1.0))[1])
        self.assertFalse(sp.speak("hello friends", priority=True, call=True))       # no call player yet
        self.assertIn("virtual cable", sp.last_error)
        sp.call_player = lambda p: (call.append(p), (None, 2.0))[1]
        self.assertTrue(sp.speak("hello friends", priority=True, call=True))
        self.assertEqual((call, local), (["/tmp/x.mp3"], []))
        sp.stop()
        sp.speak("just for me", priority=True)
        self.assertEqual(local, ["/tmp/x.mp3"])                                      # ordinary speech stays local

    def test_system_voice_cannot_speak_into_a_call(self):
        sp = voice.Speaker(platform="linux", which=lambda n: "/usr/bin/espeak", threaded=False)
        sp.call_player = lambda p: (None, 1.0)
        self.assertFalse(sp.speak("hi", priority=True, call=True))

    def test_failed_call_voice_does_not_leak_to_the_system_voice(self):
        class Bad:
            def fetch(self, t):
                raise RuntimeError("offline")
        said = []
        sp = voice.Speaker(platform="linux", which=lambda n: "/usr/bin/espeak", edge=Bad(), threaded=False)
        sp.call_player = lambda p: (None, 1.0)
        sp._speak_system = lambda line: said.append(line) or True
        sp.speak("secret call line", priority=True, call=True)
        self.assertEqual(said, [])
