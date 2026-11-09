import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report as R  # noqa: E402


class ReportTests(unittest.TestCase):
    def test_scrubs_keys_paths_and_emails(self):
        text = ("key sk-ant-api03-abcdefgh_ijkl-1234 and AIzaSyA1234567890abcdefghijklmnop and "
                "fish 0123456789abcdef0123456789abcdef x-api-key: hunter2 me@school.ca C:\\Users\\sam\\.capri\\capri.log")
        out = R.scrub(text, home="C:\\Users\\sam")
        for secret in ("sk-ant-api03", "AIzaSy", "0123456789abcdef0123", "hunter2", "me@school.ca", "sam"):
            self.assertNotIn(secret, out)
        self.assertIn("~\\.capri\\capri.log", out)

    def test_only_safe_settings(self):
        s = {"skin": "capri", "ai_vision": True, "vision_interval": 10, "notes": [{"text": "wifi pass"}],
             "memory": ["my dog"], "user_name": "Sam", "consented": {"agent": True}, "brain": "x" * 100}
        out = R.safe_settings(s)
        self.assertEqual(out, {"skin": "capri", "ai_vision": True, "vision_interval": 10})

    def test_recent_log_keeps_errors_with_traceback_and_the_tail(self):
        log = ["ok line %d" % i for i in range(300)]
        log[50] = "2026 tick error: Traceback (most recent call last):"
        log[51:55] = ["  File x", "  line", "KeyError: 'y'", "after"]
        picked = R.recent_log("\n".join(log))
        self.assertIn("2026 tick error: Traceback (most recent call last):", picked)
        self.assertIn("KeyError: 'y'", picked)
        self.assertIn("ok line 299", picked)
        self.assertNotIn("ok line 10", picked)
        self.assertLessEqual(len(picked), R.MAX_LOG_LINES + 1)

    def test_build(self):
        rep = R.build({"python": "3.13.1", "skin": "capri"}, {"skin": "capri", "notes": ["secret note"]},
                      "x failed: sk-ant-abcdefghijk123", home="/home/sam")
        self.assertTrue(rep.startswith("=== CAPRI BUG REPORT ==="))
        self.assertIn("python: 3.13.1", rep)
        self.assertNotIn("secret note", rep)
        self.assertNotIn("sk-ant-abcdefghijk123", rep)
        self.assertIn("x failed: [removed]", rep)

    def test_rotate(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "capri.log")
        with open(p, "w") as f:
            f.write("x" * 2000)
        self.assertFalse(R.rotate(p, max_bytes=5000))
        self.assertTrue(R.rotate(p, max_bytes=1000))
        self.assertFalse(os.path.exists(p))
        self.assertTrue(os.path.exists(p + ".1"))
        self.assertFalse(R.rotate(os.path.join(d, "missing.log")))


if __name__ == "__main__":
    unittest.main()
