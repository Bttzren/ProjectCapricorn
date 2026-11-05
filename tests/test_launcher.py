import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import launcher as L  # noqa: E402


def make_start_menu():
    d = tempfile.mkdtemp()
    for rel in ("Discord Inc/Discord.lnk", "Spotify.lnk", "Steam/Steam.lnk", "Steam/Uninstall Steam.lnk",
                "Google Chrome.lnk", "Valorant.lnk", "Visual Studio Code/Visual Studio Code.lnk", "Readme.lnk",
                "Epic Games Launcher.lnk"):
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").close()
    return d


class IndexTests(unittest.TestCase):
    def test_windows_index_skips_junk_and_adds_system_apps(self):
        apps = L.index_apps("win32", [make_start_menu()])
        self.assertIn("discord", apps)
        self.assertIn("visual studio code", apps)
        self.assertNotIn("uninstall steam", apps)
        self.assertNotIn("readme", apps)
        self.assertEqual(apps["notepad"], "notepad.exe")

    def test_mac_and_linux(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "Safari.app"))
        self.assertEqual(L.index_apps("darwin", [d]), {"safari": "Safari"})
        d2 = tempfile.mkdtemp()
        open(os.path.join(d2, "org.mozilla.firefox.desktop"), "w").close()
        self.assertEqual(L.index_apps("linux", [d2]), {"firefox": "org.mozilla.firefox.desktop"})


class ParseTests(unittest.TestCase):
    def test_open_phrases(self):
        self.assertEqual(L.parse_open("Open Discord"), ("open", "discord"))
        self.assertEqual(L.parse_open("launch the Spotify app please"), ("open", "spotify"))
        self.assertEqual(L.parse_open("go to youtube"), ("open", "youtube"))
        self.assertIsNone(L.parse_open("open the door and tell my friends I'm late now ok"))
        self.assertIsNone(L.parse_open("how are you"))

    def test_search_phrases(self):
        self.assertEqual(L.parse_open("search for best valorant crosshair"), ("search", "best valorant crosshair", "google"))
        self.assertEqual(L.parse_open("search youtube for lofi beats"), ("search", "lofi beats", "youtube"))
        self.assertEqual(L.parse_open("look up cats on youtube"), ("search", "cats", "youtube"))

    def test_search_url_is_encoded(self):
        u = L.search_url("a&b=c d/../x", "youtube")
        self.assertTrue(u.startswith("https://www.youtube.com/results?search_query="))
        self.assertNotIn(" ", u)
        self.assertNotIn("&b=", u)


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.apps = L.index_apps("win32", [make_start_menu()])

    def test_exact_prefix_fuzzy(self):
        self.assertEqual(L.match("discord", self.apps)[0:2], ("app", "discord"))
        self.assertEqual(L.match("chrome", self.apps)[1], "google chrome")
        self.assertEqual(L.match("Visual Studio", self.apps)[1], "visual studio code")
        self.assertEqual(L.match("spotfy", self.apps)[1], "spotify")          # misheard

    def test_apps_beat_sites_and_sites_work_without_apps(self):
        self.assertEqual(L.match("spotify", self.apps)[0], "app")
        self.assertEqual(L.match("youtube", self.apps)[0], "site")
        self.assertEqual(L.match("reddit", {})[0], "site")

    def test_no_match(self):
        self.assertIsNone(L.match("flurbnorp", self.apps))
        self.assertIsNone(L.match("", self.apps))


class OpenerTests(unittest.TestCase):
    def test_windows_app_and_site(self):
        got = []
        L.opener("app", "C:/x/Discord.lnk", "win32", startfile=got.append)()
        L.opener("site", "https://x.com", "win32", webopen=got.append)()
        self.assertEqual(got, ["C:/x/Discord.lnk", "https://x.com"])

    def test_refuses_non_web_urls(self):
        for bad in ("file:///etc/passwd", "javascript:alert(1)", "calc.exe"):
            with self.assertRaises(ValueError):
                L.opener("site", bad, "win32")

    def test_mac_and_linux_use_argument_lists(self):
        got = []
        L.opener("app", "Safari", "darwin", popen=got.append)()
        L.opener("app", "org.mozilla.firefox.desktop", "linux", popen=got.append)()
        self.assertEqual(got, [["open", "-a", "Safari"], ["gtk-launch", "org.mozilla.firefox"]])


if __name__ == "__main__":
    unittest.main()
