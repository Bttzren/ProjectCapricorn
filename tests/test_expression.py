import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import expression as E  # noqa: E402
import speech  # noqa: E402


class TagTests(unittest.TestCase):
    def test_parse_and_strip(self):
        self.assertEqual(E.parse_tag("[smug] Nice tabs."), ("smug", "Nice tabs."))
        self.assertEqual(E.parse_tag("  [Smug]: Nice tabs."), ("smug", "Nice tabs."))
        self.assertEqual(E.parse_tag("(annoyed) Stop clicking."), ("angry", "Stop clicking."))
        self.assertEqual(E.parse_tag("[neutral] Okay."), ("", "Okay."))
        self.assertEqual(E.parse_tag("[smug]\nNice tabs."), ("smug", "Nice tabs."))     # tag on its own line
        self.assertEqual(E.parse_tag("Nice tabs."), (None, "Nice tabs."))              # no tag: no guessing
        self.assertEqual(E.parse_tag("[vibing] Nice."), (None, "Nice."))               # unknown tag dropped
        self.assertEqual(E.parse_tag("[a real long bracket thing] x"), (None, "[a real long bracket thing] x"))
        self.assertEqual(E.parse_tag(""), (None, ""))

    def test_tag_never_reaches_the_bubble(self):
        for raw in ("[smug] Nice tabs.", "[smug]\nNice tabs.", "[SMUG] - Nice tabs."):
            emo, rest = E.parse_tag(raw)
            line = speech.sanitize(rest)
            self.assertEqual(line, "Nice tabs.")
            self.assertNotIn("smug", line.lower())

    def test_every_emotion_is_complete(self):
        icons = {None, "!", "?", "heart", "note", "star", "anger"}
        motions = {"hop", "bounce", "shake", "tremble", "tilt", "droop", "puff", "sway", "none"}
        for name, (chain, mot, icon) in E.EMOTIONS.items():
            self.assertTrue(chain, name)
            self.assertIn(mot, motions, name)
            self.assertIn(icon, icons, name)
            self.assertEqual(E.canonical(name), name)
        for word, target in E.SYNONYMS.items():
            self.assertIn(target, E.EMOTIONS, word)
        for n in E.EMOTIONS:
            self.assertIn(f"[{n}]", E.TAG_INSTRUCTION)

    def test_prompt_asks_for_tag_only_when_asked(self):
        self.assertIn("[smug]", speech.user_prompt("idle", {}, (), tags=True))
        self.assertNotIn("[smug]", speech.user_prompt("idle", {}, ()))

    def test_mood_faces(self):
        self.assertEqual(E.for_mood("sassy"), "smug")
        self.assertIsNone(E.for_mood("content"))
        self.assertIsNone(E.for_mood("whatever"))


class GateAndMotionTests(unittest.TestCase):
    def test_gate_rate_limits_mild_but_not_strong(self):
        g = E.Gate(gap=12)
        self.assertTrue(g.allow(0, "smug"))
        self.assertFalse(g.allow(5, "happy"))
        self.assertTrue(g.allow(6, "surprised"))         # strong moments always show
        self.assertTrue(g.allow(20, "happy"))
        self.assertTrue(g.allow(21, "sad", forced=True))  # /express preview
        self.assertFalse(g.allow(100, ""))
        self.assertFalse(g.allow(100, "nope"))

    def test_motions_stay_in_place_and_settle(self):
        for name, (_c, mot, _i) in E.EMOTIONS.items():
            for t in (0.0, 0.1, 0.4, 1.0, 1.9):
                dy, ang, sx, sy = E.motion(mot, t, 2.0)
                self.assertLessEqual(abs(dy), 10.0, name)
                self.assertLessEqual(abs(ang), 10.0, name)
                self.assertTrue(0.9 <= sx <= 1.1 and 0.9 <= sy <= 1.1, name)
            self.assertEqual(E.motion(mot, 2.0, 2.0), (0.0, 0.0, 1.0, 1.0))
            end = E.motion(mot, 1.99, 2.0)
            self.assertLess(abs(end[1]), 1.0, name)                      # faded out at the end
        self.assertEqual(E.motion("tilt", 1.0, 2.0, direction=-1)[1], -9.0)


class ArtTests(unittest.TestCase):
    ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pet")

    def test_every_emotion_has_a_face_file(self):
        have = {f[:-4] for f in os.listdir(os.path.join(self.ROOT, "faces")) if f.endswith(".png")}
        self.assertIn(E.FACE_DEFAULT, have)
        for name in E.EMOTIONS:
            self.assertIn(E.face_for(name, have), have, name)
        self.assertEqual(E.face_for("smug", {"face-calm"}), "face-calm")       # missing art: calm face
        self.assertIsNone(E.face_for("smug", set()))

    def test_cutins_exist_and_are_only_big_moments(self):
        have = {f[:-4] for f in os.listdir(os.path.join(self.ROOT, "cutins"))}
        for name, stem in E.CUTINS.items():
            self.assertIn(stem, have)
            self.assertIn(name, E.Gate.STRONG)
        self.assertGreaterEqual(E.CUTIN_GAP, 120)

    def test_cutin_slides_in_holds_and_leaves(self):
        self.assertEqual(E.cutin_slide(0), -1.0)
        self.assertEqual(E.cutin_slide(0.5), 0.0)
        self.assertGreater(E.cutin_slide(1.05), 0.0)
        self.assertIsNone(E.cutin_slide(E.CUTIN_SECS))
        self.assertIsNone(E.cutin_slide(-0.1))


if __name__ == "__main__":
    unittest.main()
