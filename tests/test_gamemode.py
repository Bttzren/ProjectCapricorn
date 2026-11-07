import json
import os
import random
import re
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw  # noqa: E402

import gamemode as G  # noqa: E402
import reactor as R  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def session(level="mild", seed=1, key="valorant"):
    c = Clock()
    s = G.Session(key, random.Random(seed), level, clock=c)
    s.c = c
    return s


def step(s, kind, n=1):
    s.c.t += 10                       # well past the talking cooldown
    return s.event(kind, n)


STRONG = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt|nigg\w*|fag\w*|retard\w*|dick\w*|piss\w*)\b")


class GameDetectTests(unittest.TestCase):
    def test_detect_game(self):
        self.assertEqual(G.detect_game("VALORANT"), "valorant")
        self.assertEqual(G.detect_game("Counter-Strike 2"), "cs2")
        self.assertEqual(G.detect_game("League of Legends (TM) Client"), "league")
        self.assertIsNone(G.detect_game("YouTube - Chrome"))
        for watching in ("Valorant clips - Twitch - Microsoft Edge", "Fortnite montage - YouTube - Google Chrome",
                         "Overwatch 2 patch notes - Google Chrome", "League of Legends wiki - Fandom"):
            self.assertIsNone(G.detect_game(watching), watching)             # watching/reading, not playing
        self.assertIsNone(G.detect_game(""))
        self.assertIsNone(G.detect_game(None))

    def test_parse_match(self):
        self.assertEqual(G.parse_match("13-7 15/12"), {"rounds": (13, 7), "kd": (15, 12)})
        self.assertEqual(G.parse_match("13:11"), {"rounds": (13, 11)})
        self.assertEqual(G.parse_match("20/5"), {"kd": (20, 5)})
        for bad in ("", "banana", "a-b", "5000-1", "-", None):
            self.assertIsNone(G.parse_match(bad), bad)


class SessionTests(unittest.TestCase):
    def test_counts_kills_deaths_and_kd(self):
        s = session()
        for _ in range(3):
            step(s, "kill")
        step(s, "death")
        self.assertEqual((s.kills, s.deaths), (3, 1))
        self.assertAlmostEqual(s.kd, 3.0)
        self.assertIn("3/1", s.status())
        one = session()
        step(one, "death")
        self.assertIn("1 death", one.status())
        self.assertNotIn("1 deaths", one.status())
        step(one, "death")
        self.assertIn("2 deaths", one.status())

    def test_multikills_are_counted_and_have_their_own_lines(self):
        s = session()
        self.assertEqual(step(s, "kill", 2), G.MULTI[2])
        self.assertEqual(s.kills, 2)
        self.assertEqual(step(s, "kill", 3), G.MULTI[3])
        self.assertEqual(step(s, "kill", 4), G.MULTI[4])
        s2 = session()
        self.assertIn(step(s2, "ace"), G.ACE)
        self.assertEqual(s2.kills, 5)
        self.assertIn(step(session(), "kill", 99), G.ACE)            # absurd numbers are capped

    def test_streaks(self):
        s = session()
        step(s, "kill")
        step(s, "kill")
        line = step(s, "kill")
        self.assertIn("3", line)
        d = session("spicy")
        step(d, "death")
        step(d, "death")
        line = step(d, "death")
        self.assertIn("3 deaths in a row", line)
        self.assertEqual(d.dstreak, 3)
        step(d, "kill")
        self.assertEqual(d.dstreak, 0)

    def test_roast_levels(self):
        for level in G.LEVELS:
            s = session(level)
            lines = {step(s, "death") for _ in range(1)}
            for l in lines:
                self.assertTrue(l)
        off = session("off")
        for _ in range(30):
            line = step(off, "death")
            self.assertFalse(re.search(r"\bass\b|tragic|gonk|embarrass|coward", line, re.I), line)
        spicy = {session("spicy", seed=i).event("death") for i in range(40)}
        self.assertTrue(any(re.search(r"\bass\b", l) for l in spicy))
        mild = {session("mild", seed=i).event("death") for i in range(40)}
        self.assertFalse(any(re.search(r"\bass\b", l) for l in mild))

    def test_all_text_is_short_and_nothing_stronger_than_ass(self):
        pools = [G.KILL, G.KILL_STREAK, G.GOOD_KD, G.ACE, G.CLUTCH, G.ROUND_WIN, G.MATCH_WIN, G.START,
                 list(G.MULTI.values())]
        for table in (G.DEATH, G.DEATH_STREAK, G.BAD_KD, G.ROUND_LOSS, G.MATCH_LOSS):
            for level, pool in table.items():
                pools.append(pool)
        pools += list(G.VERDICT["great"]), list(G.VERDICT["good"]), list(G.VERDICT["mid"])
        pools += [pool for pool in G.VERDICT["bad"].values()]
        for pool in pools:
            for line in pool:
                self.assertLessEqual(len(line), 100, line)
                self.assertIsNone(STRONG.search(line.lower()), line)
        for level in ("off", "mild"):                                  # the one mild swear is spicy-only
            for table in (G.DEATH, G.DEATH_STREAK, G.BAD_KD, G.ROUND_LOSS, G.MATCH_LOSS):
                for line in table[level]:
                    self.assertFalse(re.search(r"\bass\b", line.lower()), line)
            for line in G.VERDICT["bad"][level]:
                self.assertFalse(re.search(r"\bass\b", line.lower()), line)

    def test_bad_and_good_kd_comments_after_enough_events(self):
        s = session("mild")
        for _ in range(2):
            step(s, "kill")
        for _ in range(2):
            step(s, "death")
        for _ in range(2):
            step(s, "round_loss")
        s.kills, s.deaths = 1, 8
        s.dstreak = 0
        self.assertIn("1/9", step(s, "death"))          # the death is counted first
        g = session()
        for _ in range(6):
            step(g, "kill")
        g.kills, g.deaths, g.kstreak = 11, 2, 0
        self.assertRegex(step(g, "kill"), r"12\D+2")      # 11 + this kill, either wording

    def test_cooldown_keeps_ordinary_lines_from_spamming_but_big_events_always_talk(self):
        s = session()
        s.c.t = 1000
        self.assertTrue(s.event("kill"))
        s.c.t += 1
        self.assertEqual(s.event("kill"), "")                          # too soon, still counted
        self.assertEqual(s.kills, 2)
        s.c.t += 0.5
        self.assertTrue(s.event("clutch"))
        self.assertTrue(s.event("match_win"))
        s.c.t += 4
        self.assertTrue(s.event("death"))

    def test_unknown_events_are_ignored(self):
        s = session()
        self.assertEqual(s.event("pizza"), "")
        self.assertEqual(s.events, 0)

    def test_rounds_and_apply_result(self):
        s = session()
        step(s, "round_win")
        step(s, "round_win")
        step(s, "round_loss")
        self.assertEqual((s.rounds_w, s.rounds_l), (2, 1))
        s.apply_result(rounds=(13, 7), kd=(15, 12))
        self.assertEqual((s.rounds_w, s.rounds_l, s.kills, s.deaths), (13, 7, 15, 12))
        self.assertIn("15 kills, 12 deaths (K/D 1.25), rounds 13-7", s.recap())

    def test_verdicts_follow_kd(self):
        s = session("spicy")
        s.kills, s.deaths = 20, 5
        self.assertIn(s.verdict(), G.VERDICT["great"])
        s.kills, s.deaths = 5, 20
        self.assertIn(s.verdict(), G.VERDICT["bad"]["spicy"])
        s.kills, s.deaths = 12, 12
        self.assertIn(s.verdict(), G.VERDICT["good"])

    def test_summary_has_numbers_only(self):
        s = session()
        step(s, "kill")
        d = s.summary()
        self.assertEqual(set(d), {"game", "k", "d", "rw", "rl", "min", "day"})
        self.assertTrue(all(isinstance(v, (int, str)) for v in d.values()))

    def test_unknown_game_key_and_level_fall_back(self):
        s = G.Session("minesweeper", level="brutal")
        self.assertEqual((s.key, s.level), ("other", "mild"))
        self.assertEqual(s.name, "your game")
        self.assertTrue(s.start_line())


def banner(color=(200, 30, 30), size=(300, 80)):
    im = Image.new("RGB", size, (20, 20, 25))
    d = ImageDraw.Draw(im)
    d.rectangle((20, 15, size[0] - 20, size[1] - 15), fill=color)
    d.text((40, 30), "YOU DIED", fill=(255, 255, 255))
    return im


class ReactorTests(unittest.TestCase):
    def test_distance_and_detector_matching(self):
        det = R.RegionDetector("death", (0.4, 0.8, 0.2, 0.1), [banner()])
        self.assertLess(det.score(banner()), 0.01)
        self.assertGreater(det.score(Image.new("RGB", (300, 80), (20, 20, 25))), 0.1)
        self.assertGreater(det.score(banner(color=(30, 200, 30))), 0.1)         # wrong colour is not a match

    def test_fires_once_per_appearance_with_cooldown_and_rearms(self):
        det = R.RegionDetector("death", (0.4, 0.8, 0.2, 0.1), [banner()], cooldown=5)
        blank = Image.new("RGB", (300, 80), (20, 20, 25))
        t = 100.0
        self.assertTrue(det.check(banner(), t))
        self.assertFalse(det.check(banner(), t + 0.4))                          # still on screen: no repeat
        self.assertFalse(det.check(blank, t + 0.8))
        self.assertFalse(det.check(banner(), t + 1.0))                          # back too soon (cooldown)
        det.check(blank, t + 5.5)
        self.assertTrue(det.check(banner(), t + 6.0))

    def test_small_noise_still_matches(self):
        det = R.RegionDetector("death", (0, 0, 1, 1), [banner()], threshold=0.1)
        noisy = banner().point(lambda v: min(255, v + 6))
        self.assertTrue(det.check(noisy, 1.0))

    def test_bbox_clamps_to_the_screen(self):
        self.assertEqual(R.bbox((0.5, 0.5, 0.25, 0.25), (1000, 800)), (500, 400, 750, 600))
        x0, y0, x1, y1 = R.bbox((0.9, 0.9, 0.5, 0.5), (1000, 800))
        self.assertTrue(x1 <= 1000 and y1 <= 800 and x1 > x0 and y1 > y0)

    def test_reactor_polls_the_regions_and_reports_events(self):
        det = R.RegionDetector("kill", (0.1, 0.1, 0.2, 0.1), [banner()], cooldown=1)
        seen_boxes, frames = [], [Image.new("RGB", (300, 80), (20, 20, 25)), banner(), banner()]
        t = [10.0]

        def grab(box):
            seen_boxes.append(box)
            return frames.pop(0)
        r = R.Reactor([det], (1000, 800), grab=grab, clock=lambda: t[0])
        self.assertEqual(r.poll(), [])
        t[0] += 1
        self.assertEqual(r.poll(), [("kill", 1)])
        t[0] += 1
        self.assertEqual(r.poll(), [])
        self.assertEqual(seen_boxes[0], (100, 80, 300, 160))                    # only a SMALL patch is captured

    def test_reactor_reports_when_it_cannot_capture(self):
        r = R.Reactor([R.RegionDetector("kill", (0, 0, 0.5, 0.5), [banner()])], (100, 100), grab=lambda b: None)
        self.assertEqual(r.poll(), [])
        self.assertIn("capture", r.error)

    def test_background_thread_delivers_events_and_stops(self):
        det = R.RegionDetector("death", (0, 0, 1, 1), [banner()])
        r = R.Reactor([det], (100, 100), grab=lambda b: banner(), hz=50)
        r.start()
        got = []
        for _ in range(100):
            got = r.take()
            if got:
                break
            time.sleep(0.02)
        r.stop()
        self.assertEqual(got, [("death", 1)])


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        os.makedirs(os.path.join(self.dir, "templates"))
        banner().save(os.path.join(self.dir, "templates", "death.png"))
        self.path = os.path.join(self.dir, "game_events.json")

    def write(self, obj):
        with open(self.path, "w") as f:
            json.dump(obj, f)

    def good(self, **over):
        d = {"event": "death", "region": [0.4, 0.8, 0.2, 0.1], "templates": ["templates/death.png"]}
        d.update(over)
        return d

    def test_missing_file_is_fine(self):
        self.assertEqual(R.load_config(os.path.join(self.dir, "nope.json")), ({}, []))

    def test_loads_a_valid_config(self):
        self.write({"valorant": {"detectors": [self.good(threshold=0.2, cooldown=6)]}})
        cfg, warns = R.load_config(self.path)
        self.assertEqual(warns, [])
        d = cfg["valorant"][0]
        self.assertEqual((d.event, d.threshold, d.cooldown), ("death", 0.2, 6.0))

    def test_bad_entries_are_skipped_with_a_warning_not_a_crash(self):
        self.write({"valorant": {"detectors": [
            self.good(event="pizza"), self.good(region=[2, 0, 1, 1]), self.good(templates=[]),
            self.good(templates=["templates/missing.png"]), {"event": "death"}, self.good()]},
            "notagame": {}, "cs2": 5})
        cfg, warns = R.load_config(self.path)
        self.assertEqual(len(cfg["valorant"]), 1)
        self.assertGreaterEqual(len(warns), 6)

    def test_templates_cannot_escape_the_config_folder(self):
        outside = os.path.join(os.path.dirname(self.dir), "secret.png")
        banner().save(outside)
        self.addCleanup(lambda: os.path.exists(outside) and os.remove(outside))
        self.write({"valorant": {"detectors": [self.good(templates=["../secret.png"])]}})
        cfg, warns = R.load_config(self.path)
        self.assertEqual(cfg, {})
        self.assertTrue(any("inside" in w for w in warns))

    def test_threshold_is_clamped_and_bad_json_is_reported(self):
        self.write({"valorant": {"detectors": [self.good(threshold=9, cooldown=0)]}})
        d = R.load_config(self.path)[0]["valorant"][0]
        self.assertEqual((d.threshold, d.cooldown), (0.5, 1.0))
        with open(self.path, "w") as f:
            f.write("{not json")
        cfg, warns = R.load_config(self.path)
        self.assertEqual(cfg, {})
        self.assertTrue(warns)


if __name__ == "__main__":
    unittest.main()
