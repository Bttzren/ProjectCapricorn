import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

import agent  # noqa: E402
import hands as H  # noqa: E402


class Backend:
    def __init__(self):
        self.calls = []

    def move(self, x, y):
        self.calls.append(("move", x, y))

    def click(self, button="left", double=False):
        self.calls.append(("click", button, double))

    def type_text(self, text):
        self.calls.append(("type", text))

    def press(self, combo):
        self.calls.append(("press", tuple(combo)))

    def scroll(self, n):
        self.calls.append(("scroll", n))


def J(**kw):
    return json.dumps(kw)


def make(replies, **kw):
    be = Backend()
    hands = H.Hands(level="full", backend=be, threaded=False, per_min=100)
    it = iter(replies)
    asked = []

    def ask(mt, b64, system, prompt):
        asked.append(prompt)
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    kw.setdefault("sleep", lambda s: None)
    a = agent.Agent(lambda: Image.new("RGB", (2560, 1440), "black"), ask, hands, **kw)
    return a, be, asked


class ParseTests(unittest.TestCase):
    S = (1280, 720)

    def test_click_valid_and_bounds(self):
        a = agent.parse_action('```json\n{"action":"click","x":10.4,"y":700,"why":"x"}\n```', self.S)
        self.assertEqual((a["x"], a["y"]), (10, 700))
        self.assertIsNone(agent.parse_action(J(action="click", x=1280, y=5), self.S))
        self.assertIsNone(agent.parse_action(J(action="click", x=-1, y=5), self.S))
        self.assertIsNone(agent.parse_action(J(action="click", y=5), self.S))

    def test_other_actions(self):
        self.assertEqual(agent.parse_action(J(action="type", text="hi\nthere"), self.S)["text"], "hi there")
        self.assertIsNone(agent.parse_action(J(action="type", text="  "), self.S))
        self.assertEqual(agent.parse_action(J(action="scroll", amount=99), self.S)["amount"], 10)
        self.assertIsNone(agent.parse_action(J(action="scroll", amount=0), self.S))
        self.assertEqual(agent.parse_action(J(action="wait", seconds=99), self.S)["seconds"], 5.0)
        self.assertIsNone(agent.parse_action(J(action="format_disk"), self.S))
        self.assertIsNone(agent.parse_action("just do it", self.S))

    def test_encode_exact_width(self):
        mt, b64, size = agent.encode(Image.new("RGB", (2560, 1440), "red"), 1280)
        self.assertEqual(size, (1280, 720))
        self.assertEqual(mt, "image/jpeg")


class RunTests(unittest.TestCase):
    def test_discord_style_task_with_scaling(self):
        a, be, asked = make([
            J(action="key", keys="win"),
            J(action="type", text="discord"),
            J(action="key", keys="enter"),
            J(action="click", x=640, y=360),
            J(action="type", text="He'll be in 15 minutes"),
            J(action="key", keys="enter"),
            J(action="done", summary="Told them."),
        ])
        notes = []
        a.note_fn = notes.append
        status, summary = a.run("tell my friends I'll be in in 15")
        self.assertEqual((status, summary), ("done", "Told them."))
        self.assertIn(("move", 1280, 720), be.calls)            # 640x360 in the 1280 image = 1280x720 on a 2560 screen
        self.assertIn(("type", "He'll be in 15 minutes"), be.calls)
        self.assertEqual(len(notes), 6)
        self.assertIn("press win", asked[1])                     # history reaches the next prompt

    def test_type_needs_approval(self):
        seen = []
        a, be, _ = make([J(action="type", text="hello"), J(action="done")],
                        approve=lambda k, d: (seen.append((k, d)), False)[1])
        status, _ = a.run("x")
        self.assertEqual(status, "denied")
        self.assertEqual(seen, [("type", "hello")])
        self.assertFalse([c for c in be.calls if c[0] == "type"])

    def test_blocked_keys_stay_blocked(self):
        a, be, asked = make([J(action="key", keys="alt+f4"), J(action="done")])
        a.run("x")
        self.assertEqual(be.calls, [])
        self.assertIn("FAILED", asked[1])
        self.assertIn("blocked", asked[1])

    def test_private_window_stops_before_looking(self):
        a, be, asked = make([J(action="done")], title=lambda: "Chase Online Banking - Chrome")
        status, _ = a.run("x")
        self.assertEqual(status, "private")
        self.assertEqual(asked, [])

    def test_user_moving_mouse_takes_over(self):
        pos = [(0, 0)]
        a, be, _ = make([J(action="click", x=100, y=100), J(action="click", x=300, y=300), J(action="done")],
                        pointer=lambda: pos[0])
        orig = a.hands.do

        def do(action, arg=None):
            r = orig(action, arg)
            pos[0] = (900, 900)                                 # the user grabs the mouse
            return r
        a.hands.do = do
        status, _ = a.run("x")
        self.assertEqual(status, "taken")
        self.assertEqual(len([c for c in be.calls if c[0] == "click"]), 1)

    def test_stop_and_step_cap_and_budget(self):
        a, be, _ = make([J(action="scroll", amount=-1 - i) for i in range(30)], max_steps=4)
        self.assertEqual(a.run("x")[0], "failed")
        self.assertEqual(len(be.calls), 4)

        a, be, _ = make([J(action="scroll", amount=-1 - i) for i in range(10)])
        a.note_fn = lambda t: a.stop()                          # the user hits stop during step 1
        self.assertEqual(a.run("x")[0], "stopped")
        self.assertEqual(len(be.calls), 1)

        class Cap:
            def allow(self):
                return False
        a, _, asked = make([J(action="done")], budget=Cap())
        self.assertEqual(a.run("x")[0], "capped")
        self.assertEqual(asked, [])

    def test_stuck_loop_detected(self):
        a, _, _ = make([J(action="click", x=5, y=5)] * 6)
        self.assertEqual(a.run("x")[0], "failed")

    def test_bad_replies_and_ai_errors(self):
        a, _, asked = make(["nope", J(action="done", summary="ok")])
        self.assertEqual(a.run("x"), ("done", "ok"))
        self.assertIn("valid JSON", asked[1])
        a, _, _ = make(["a", "b", "c"])
        self.assertEqual(a.run("x")[0], "error")
        a, _, _ = make([RuntimeError("401: bad key")])
        self.assertEqual(a.run("x")[0], "error")

    def test_click_on_capri_herself_is_refused(self):
        a, be, asked = make([J(action="click", x=10, y=10), J(action="done")], blocked=lambda x, y: True)
        a.run("x")
        self.assertEqual(be.calls, [])
        self.assertIn("covered by me", asked[1])

    def test_agent_needs_full_control(self):
        be = Backend()
        hands = H.Hands(level="media", backend=be, threaded=False)
        a = agent.Agent(lambda: Image.new("RGB", (100, 100)), lambda *x: J(action="click", x=5, y=5), hands,
                        sleep=lambda s: None, max_steps=2)
        a.run("x")
        self.assertEqual(be.calls, [])


class HandsExtraTests(unittest.TestCase):
    def test_lone_win_key_allowed_but_not_win_combos_with_nothing(self):
        self.assertEqual(H.normalize_combo("win"), ["win"])
        with self.assertRaises(ValueError):
            H.normalize_combo("ctrl")
        with self.assertRaises(ValueError):
            H.normalize_combo("win+r")

    def test_click_at_scroll_validation(self):
        be = Backend()
        h = H.Hands(level="full", backend=be, threaded=False)
        self.assertTrue(h.do("click_at", (5, 6, "double"))[0])
        self.assertFalse(h.do("click_at", (-5, 6))[0])
        self.assertFalse(h.do("click_at", ("a", 6))[0])
        self.assertFalse(h.do("click_at", (5, 6, "middle"))[0])
        self.assertTrue(h.do("scroll", -3)[0])
        self.assertFalse(h.do("scroll", "x")[0])
        h.set_level("media")
        self.assertFalse(h.do("click_at", (5, 6))[0])


if __name__ == "__main__":
    unittest.main()
