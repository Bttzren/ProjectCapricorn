import os
import re
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import awareness as A  # noqa: E402


class AwarenessTests(unittest.TestCase):
    def test_classifies_common_windows(self):
        cases = {
            "Lo-fi beats - YouTube - Google Chrome": "video",
            "main.py - capri - Visual Studio Code": "coding",
            "Windows PowerShell": "coding",
            "Spotify Premium": "music",
            "Discord | #general": "chat",
            "Homework - Google Classroom": "school",
            "Cyberpunk 2077": "cyberpunk",
            "Steam": "game",
            "(3) TikTok - Microsoft Edge": "social",
            "Essay.docx - Word": "writing",
            "Claude - Google Chrome": "ai",
        }
        for title, cat in cases.items():
            self.assertEqual(A.classify(title), cat, title)

    def test_watching_or_reading_about_a_game_is_not_gaming(self):
        cases = {
            "Minecraft speedrun WORLD RECORD - YouTube - Google Chrome": "video",
            "Valorant clips - Twitch - Microsoft Edge": "video",
            "r/Minecraft - Reddit - Google Chrome": "social",
            "steam deck review - YouTube": "video",
            "Cyberpunk: Edgerunners | Netflix": "video",
            "Among Us but - YouTube": "video",
            "Minecraft Wiki - Google Chrome": None,
            "Minecraft 1.21": "game",
            "Cyberpunk 2077": "cyberpunk",
            "Steam": "game",
        }
        for title, cat in cases.items():
            self.assertEqual(A.classify(title), cat, title)
        self.assertTrue(A.is_web("Anything - Mozilla Firefox"))
        self.assertTrue(A.is_web("Fortnite montage \u2014 YouTube"))
        self.assertFalse(A.is_web("VALORANT"))
        self.assertFalse(A.is_web(""))

    def test_unknown_and_empty_are_none(self):
        for t in ("", None, "Untitled - Notepad", "Calculator", "New Tab - Google Chrome"):
            self.assertIsNone(A.classify(t), t)

    def test_youtube_music_is_not_confused_with_video_only_when_listed_first(self):
        # 'video' is checked before 'music', so a plain YouTube tab is video
        self.assertEqual(A.classify("Some video - YouTube"), "video")
        self.assertEqual(A.classify("Spotify"), "music")

    def test_every_category_has_a_phrase_and_lines(self):
        for cat, _ in A.RULES:
            self.assertIn(cat, A.PHRASE, cat)
            self.assertTrue(A.line(cat, random.Random(1)), cat)

    def test_lines_are_short_and_pg(self):
        bad = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|damn\w*|hell|ass|asshole|crap)\b")
        texts = [l for ls in A.LINES.values() for l in ls] + list(A.NUDGES.values())
        for t in texts:
            self.assertLessEqual(len(t), 100, t)
            self.assertIsNone(bad.search(t.lower()), t)

    def test_nudges_exist_for_every_timed_category(self):
        for cat in A.NUDGE_AFTER:
            self.assertTrue(A.nudge(cat), cat)


if __name__ == "__main__":
    unittest.main()
