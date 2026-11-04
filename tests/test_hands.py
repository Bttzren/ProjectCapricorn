import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import hands as H  # noqa: E402


class FakeUser32:
    def __init__(self):
        self.events, self.mouse, self.locked = [], [], False

    def keybd_event(self, vk, scan, flags, extra):
        self.events.append((vk, flags))

    def mouse_event(self, flags, dx, dy, data, extra):
        self.mouse.append(flags)

    def VkKeyScanW(self, code):
        ch = chr(code)
        if ch.isupper():
            return 0x100 | ord(ch)
        if ch.isalnum():
            return ord(ch.upper())
        if ch == " ":
            return 0x20
        return -1 if ch == "☃" else 0xBE                  # '.' etc.

    def LockWorkStation(self):
        self.locked = True


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append(argv)


def hands(level, **kw):
    u = FakeUser32()
    t = [1000.0]
    h = H.Hands(level=level, backend=H.WinBackend(u, sleep=lambda s: None), clock=lambda: t[0], threaded=False, **kw)
    h.u, h.t = u, t
    return h


class ComboTests(unittest.TestCase):
    def test_normalizes_and_orders(self):
        self.assertEqual(H.normalize_combo("Ctrl+Shift+T"), ["ctrl", "shift", "t"])
        self.assertEqual(H.normalize_combo("shift+control+a"), ["ctrl", "shift", "a"])
        self.assertEqual(H.normalize_combo("F5"), ["f5"])
        self.assertEqual(H.normalize_combo("cmd+Return"), ["win", "enter"])

    def test_rejects_garbage_and_blocked_shortcuts(self):
        for bad in ("", "+", "ctrl+", "ctrl+ctrl+a", "banana+a", "ctrl+nonsense", "alt+f4", "ctrl+alt+del",
                    "Control+Alt+Delete", "win+r", "ctrl+shift+esc"):
            with self.assertRaises(ValueError, msg=bad):
                H.normalize_combo(bad)

    def test_clean_text_removes_enter_tab_controls_and_caps_length(self):
        self.assertEqual(H.clean_text("hi\nthere\tfriend\x00"), "hi there friend")
        self.assertEqual(len(H.clean_text("a" * 1000)), H.MAX_TYPE)
        self.assertEqual(H.clean_text("\n\n"), "")


class LevelTests(unittest.TestCase):
    def test_visual_level_sends_nothing_ever(self):
        h = hands("visual")
        for action, arg in (("playpause", None), ("mute", None), ("lock", None), ("press", "ctrl+s"),
                            ("type", "hello"), ("click", None), ("screenshot", None)):
            ok, msg = h.do(action, arg)
            self.assertFalse(ok, action)
            self.assertIn("Settings", msg)
        self.assertEqual((h.u.events, h.u.mouse, h.u.locked), ([], [], False))

    def test_media_level_allows_media_but_not_keys_text_or_clicks(self):
        h = hands("media")
        self.assertTrue(h.do("playpause")[0])
        self.assertTrue(h.do("mute")[0])
        self.assertTrue(h.do("volup")[0])
        self.assertTrue(h.do("lock")[0])
        self.assertTrue(h.u.locked)
        before = len(h.u.events)
        for action, arg in (("press", "ctrl+s"), ("type", "hello"), ("click", None)):
            self.assertFalse(h.do(action, arg)[0], action)
        self.assertEqual(len(h.u.events), before)

    def test_full_level_allows_everything(self):
        h = hands("full")
        self.assertTrue(h.do("press", "ctrl+s")[0])
        self.assertTrue(h.do("type", "Hi.")[0])
        self.assertTrue(h.do("click", "double")[0])

    def test_unknown_level_falls_back_to_visual_and_unknown_action_is_refused(self):
        h = hands("god-mode")
        self.assertEqual(h.level, "visual")
        self.assertFalse(hands("full").do("format_c")[0])

    def test_level_can_be_lowered_instantly(self):
        h = hands("full")
        self.assertTrue(h.do("press", "f5")[0])
        h.set_level("visual")
        self.assertFalse(h.do("press", "f5")[0])


class CheckTests(unittest.TestCase):
    def test_check_validates_without_pressing_anything(self):
        h = hands("full")
        self.assertEqual(h.check("press", "ctrl+s"), (True, ""))
        self.assertFalse(h.check("press", "alt+f4")[0])
        self.assertFalse(h.check("type", " ")[0])
        self.assertFalse(hands("media").check("type", "hi")[0])
        self.assertEqual(h.u.events, [])


class WindowsBackendTests(unittest.TestCase):
    def test_media_key_codes(self):
        h = hands("media")
        h.do("playpause")
        self.assertEqual(h.u.events, [(0xB3, 0), (0xB3, 2)])

    def test_combo_presses_modifiers_around_the_key_and_releases_in_reverse(self):
        h = hands("full")
        h.do("press", "ctrl+shift+t")
        vk = lambda ch: ord(ch.upper())
        self.assertEqual(h.u.events, [(0x11, 0), (0x10, 0), (vk("t"), 0), (vk("t"), 2), (0x10, 2), (0x11, 2)])

    def test_extended_keys_get_the_extended_flag(self):
        h = hands("full")
        h.do("press", "delete")
        self.assertEqual(h.u.events, [(0x2E, 1), (0x2E, 3)])

    def test_typing_uses_shift_for_capitals_and_skips_unknown_characters(self):
        h = hands("full")
        h.do("type", "Hi☃")
        vks = [e for e in h.u.events if e[1] == 0]
        self.assertEqual(vks[0], (0x10, 0))                      # shift down for 'H'
        self.assertIn((ord("H"), 0), h.u.events)
        self.assertIn((ord("I"), 0), h.u.events)                 # lowercase i -> VK 'I'
        self.assertEqual(len([e for e in h.u.events if e[0] not in (0x10,) and e[1] == 0]), 2)   # snowman skipped

    def test_clicks_do_not_move_the_mouse(self):
        h = hands("full")
        h.do("click")
        h.do("click", "right")
        h.do("click", "double")
        self.assertEqual(h.u.mouse, [2, 4, 8, 16, 2, 4, 2, 4])

    def test_text_never_includes_enter(self):
        h = hands("full")
        h.do("type", "line one\nline two")
        self.assertNotIn((0x0D, 0), h.u.events)


class SafetyTests(unittest.TestCase):
    def test_rate_limit(self):
        h = hands("media")
        results = [h.do("volup")[0] for _ in range(H.MAX_PER_MIN + 3)]
        self.assertEqual(results.count(True), H.MAX_PER_MIN)
        h.t[0] += 61
        self.assertTrue(h.do("volup")[0])

    def test_bad_input_is_a_friendly_refusal_not_a_crash(self):
        h = hands("full")
        ok, msg = h.do("press", "alt+f4")
        self.assertFalse(ok)
        self.assertIn("blocked", msg)
        self.assertFalse(h.do("press", "")[0])
        self.assertFalse(h.do("type", "   ")[0])
        self.assertFalse(h.do("click", "triple")[0])
        self.assertEqual(h.u.events, [])

    def test_backend_exception_is_contained(self):
        class Boom(FakeUser32):
            def keybd_event(self, *a):
                raise OSError("denied")
        h = H.Hands(level="media", backend=H.WinBackend(Boom(), sleep=lambda s: None), threaded=False)
        ok, msg = h.do("mute")
        self.assertFalse(ok)
        self.assertIn("slipped", msg)

    def test_log_has_action_names_only_never_typed_text(self):
        logs = []
        h = hands("full", log=logs.append)
        h.do("type", "my secret password")
        h.do("press", "ctrl+s")
        self.assertEqual(logs, ["hands: type", "hands: press"])
        self.assertFalse(any("secret" in l for l in logs))


class CmdBackendTests(unittest.TestCase):
    def cmd(self, platform, have):
        run = FakeRun()
        b = H.CmdBackend(platform, which=lambda n: "/bin/" + n if n in have else None, run=run)
        return H.Hands(level="full", backend=b, threaded=False), run

    def test_linux_media_and_keys(self):
        h, run = self.cmd("linux", ("playerctl", "pactl", "xdotool", "loginctl"))
        h.do("playpause")
        h.do("volup")
        h.do("press", "ctrl+shift+t")
        h.do("type", "hello")
        h.do("click", "right")
        h.do("lock")
        self.assertEqual(run.calls, [["/bin/playerctl", "play-pause"],
                                     ["/bin/pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
                                     ["/bin/xdotool", "key", "--", "ctrl+shift+t"],
                                     ["/bin/xdotool", "type", "--delay", "40", "--", "hello"],
                                     ["/bin/xdotool", "click", "3"],
                                     ["/bin/loginctl", "lock-session"]])

    def test_missing_tool_is_a_friendly_message(self):
        h, run = self.cmd("linux", ())
        ok, msg = h.do("playpause")
        self.assertFalse(ok)
        self.assertIn("playerctl", msg)

    def test_text_is_passed_as_an_argument_never_through_a_shell(self):
        h, run = self.cmd("linux", ("xdotool",))
        h.do("type", "$(rm -rf ~) ; `id`")
        argv = run.calls[0]
        self.assertEqual(argv[-1], "$(rm -rf ~) ; `id`")
        self.assertIsInstance(argv, list)

    def test_mac_text_goes_in_argv_not_in_the_script(self):
        h, run = self.cmd("darwin", ("osascript",))
        h.do("type", 'he said "hi" \\ done')
        argv = run.calls[0]
        self.assertNotIn("he said", " ".join(argv[:-1]))
        self.assertEqual(argv[-1], 'he said "hi" \\ done')

    def test_mac_play_pause_not_supported_yet(self):
        h, _ = self.cmd("darwin", ("osascript",))
        ok, msg = h.do("playpause")
        self.assertFalse(ok)
        self.assertIn("Mac", msg)


if __name__ == "__main__":
    unittest.main()
