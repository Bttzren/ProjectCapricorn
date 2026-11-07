import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import meeting as M  # noqa: E402


class TitleTests(unittest.TestCase):
    def test_meeting_titles(self):
        for t in ("Zoom Meeting", "Zoom", "Meet - abc-defg-hij - Google Chrome", "Google Meet - Microsoft Edge",
                  "Meeting with Sam | Microsoft Teams", "Call with Ana | Microsoft Teams", "Cisco Webex Meetings",
                  "meet.google.com/abc-defg-hij"):
            self.assertTrue(M.title_is_meeting(t), t)

    def test_not_meetings(self):
        for t in ("", None, "Chat | Microsoft Teams", "YouTube - Google Chrome", "meeting notes.docx - Word",
                  "#general | Discord", "Zoom out - Paint", "Meet the parents (2000) - Netflix"):
            self.assertFalse(M.title_is_meeting(t), t)


class MicTests(unittest.TestCase):
    def test_app_names(self):
        self.assertEqual(M.app_name(r"C:#Users#me#AppData#Local#Discord#app-1.0.9#Discord.exe"), "discord")
        self.assertEqual(M.app_name("MSTeams_8wekyb3d8bbwe"), "msteams")
        self.assertEqual(M.app_name("Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe"), "windowssoundrecorder")

    def test_in_use_means_stop_is_zero_and_capri_is_ignored(self):
        entries = [(r"C:#Discord#Discord.exe", 133000, 0),                    # in a voice call now
                   (r"C:#Zoom#bin#Zoom.exe", 132000, 132500),                 # used earlier, closed
                   (r"C:#Python312#python.exe", 133100, 0),                   # Capri's own push-to-talk
                   (r"C:#dist#Capri.exe", 133100, 0),
                   (r"C:#Discord#Discord.exe", 133001, 0),                    # duplicate
                   (r"C:#Never#used.exe", 0, 0)]
        self.assertEqual(M.mic_users(entries), ["discord"])

    def test_registry_reader_is_safe_off_windows(self):
        self.assertIsInstance(M.read_mic_entries(), list)


class DetectorTests(unittest.TestCase):
    def test_start_grace_and_end(self):
        d = M.Detector(grace=45)
        self.assertIsNone(d.update(0, "YouTube"))
        self.assertEqual(d.update(1, "Zoom Meeting"), "start")
        self.assertIsNone(d.update(3, "Zoom Meeting"))
        self.assertIsNone(d.update(10, "Notes - Word"))           # alt-tabbed out: still quiet
        self.assertIsNone(d.update(40, "Notes - Word"))
        self.assertEqual(d.update(48, "Notes - Word"), "end")
        self.assertFalse(d.active)

    def test_mic_keeps_it_going_with_any_window_in_front(self):
        d = M.Detector(grace=45)
        self.assertEqual(d.update(0, "Valorant", ["discord"]), "start")
        self.assertIn("discord", d.why)
        self.assertIsNone(d.update(100, "Valorant", ["discord"]))
        self.assertIsNone(d.update(120, "Valorant", []))
        self.assertEqual(d.update(170, "Valorant", []), "end")


if __name__ == "__main__":
    unittest.main()
