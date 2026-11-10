import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cmdargs as A  # noqa: E402


class CmdArgsTests(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(A.minutes("25"), 25.0)
        self.assertEqual(A.minutes("1.5"), 1.5)
        self.assertEqual(A.minutes("0.1"), 0.1)
        for bad in ("1.2.3", "", "abc", "-5", "0", "nan", "inf", "1e9", "99999", "²", "①", "1" * 40, None, 5):
            self.assertIsNone(A.minutes(bad), repr(bad))
        self.assertEqual(A.minutes("600", hi=600), 600.0)
        self.assertIsNone(A.minutes("601", hi=600))

    def test_index(self):
        self.assertEqual(A.index("3"), 3)
        self.assertEqual(A.index("0"), 0)
        self.assertEqual(A.index("007"), 7)
        for bad in ("", "-1", "1.0", "abc", "²", "①", "9" * 30, "100000", None, 3):
            self.assertIsNone(A.index(bad), repr(bad))


if __name__ == "__main__":
    unittest.main()
