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
            "Steam": None,                      # the store / library is not playing
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
            "Steam": None,                      # the store / library is not playing
        }
        for title, cat in cases.items():
            self.assertEqual(A.classify(title), cat, title)
        self.assertTrue(A.is_web("Anything - Mozilla Firefox"))
        self.assertTrue(A.is_web("Fortnite montage \u2014 YouTube"))
        self.assertFalse(A.is_web("VALORANT"))
        self.assertFalse(A.is_web(""))

    def test_the_app_named_at_the_end_of_the_title_wins(self):
        cases = {
            "#valorant | My Server - Discord": "chat",          # a channel named after a game is still chatting
            "valorant notes.docx - Word": "writing",
            "fortnite.py - stuff - Visual Studio Code": "coding",
            "lofi beats - YouTube Music - Google Chrome": "music",
            "Apple Music review - YouTube - Brave": "video",
            "Vimeo - staff picks - Mozilla Firefox": None,      # 'vim' is a whole word only
            "Signals and Systems.pdf": None,
            "Signal": "chat",
            "Epic Games Launcher": None,
            "Friends List": None,
            "File Explorer": None,
            "Minecraft* 1.21.4 - Singleplayer": "game",
            "Marvel Rivals  ": "game",
        }
        for title, cat in cases.items():
            self.assertEqual(A.classify(title), cat, title)

    def test_program_name_beats_the_title(self):
        self.assertEqual(A.app_key("C:\\Riot Games\\VALORANT\\live\\VALORANT-Win64-Shipping.exe"), "valorant-win64-shipping")
        self.assertEqual(A.app_key("/usr/bin/discord"), "discord")
        self.assertEqual(A.app_key(""), "")
        self.assertEqual(A.app_key(None), "")
        cases = [
            ("Daft Punk - One More Time", "C:\\Users\\x\\AppData\\Roaming\\Spotify\\Spotify.exe", "music"),
            ("anything at all", "D:\\Games\\Palworld-Win64-Shipping.exe", "game"),     # any Unreal Engine game
            ("Roblox", "RobloxPlayerBeta.exe", "game"),
            ("Fortnite", "explorer.exe", None),                                   # a folder named Fortnite
            ("Valorant", "steamwebhelper.exe", None),                             # its store page
            ("Minecraft speedrun - YouTube", "chrome.exe", "video"),
            ("Valorant", "msedge.exe", None),                                     # a browser tab is never playing
            ("Cyberpunk 2077 (C) 2020 by CD Projekt RED", "Cyberpunk2077.exe", "cyberpunk"),
            ("general - Discord", "Discord.exe", "chat"),
            ("Minecraft 1.21", "javaw.exe", "game"),                              # unknown program: the title decides
            ("", "cs2.exe", "game"),
            ("", "", None),
        ]
        for title, app, cat in cases:
            self.assertEqual(A.classify(title, app), cat, (title, app))
        self.assertTrue(A.is_game_app("X-Win64-Shipping.exe"))
        self.assertFalse(A.is_game_app("chrome.exe"))
        self.assertFalse(A.is_game_app(""))
        self.assertTrue(A.is_web("New Tab", "firefox.exe"))

    def test_app_tables_use_known_categories(self):
        cats = {c for c, _ in A.RULES} | {""}
        for table in (A.APPS, A.TAILS):
            for name, cat in table.items():
                self.assertIn(cat, cats, name)
                self.assertEqual(name, name.lower())
        self.assertFalse(set(A.BROWSER_APPS) & set(A.APPS))
        self.assertFalse(set(A.GAME_APPS) & set(A.APPS))

    def test_unknown_and_empty_are_none(self):
        for t in ("", None, "Untitled - Notepad", "Calculator", "New Tab - Google Chrome"):
            self.assertIsNone(A.classify(t), t)

    def test_youtube_music_is_not_confused_with_video_only_when_listed_first(self):
        # a plain YouTube tab is video; YouTube Music is music
        self.assertEqual(A.classify("Song - YouTube Music"), "music")
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
