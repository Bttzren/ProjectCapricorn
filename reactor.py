"""Optional automatic game events from small screen regions (PIL only, no Tk).

Many games draw a recognisable thing in a FIXED place when something happens (a death banner, a kill
marker, a VICTORY screen). A detector watches one small rectangle (given as fractions of the screen)
and fires when it looks like a reference image. Only those few small patches are captured, only while
that game is in front, never saved or sent. No game memory, files or processes are touched.

Config file (game_events.json next to capri.py or in ~/.capri):
  {"valorant": {"detectors": [
      {"event": "death", "region": [0.40, 0.80, 0.20, 0.10],
       "templates": ["templates/valorant_death.png"], "threshold": 0.10, "cooldown": 6}]}}
"""
import json
import os
import queue
import threading
import time

from PIL import Image, ImageChops, ImageStat

import gamemode

SIG = 24


def signature(img):
    return img.convert("RGB").resize((SIG, SIG), Image.BOX)


def distance(a, b):
    """0.0 = identical ... 1.0 = opposite. Mean absolute colour difference of two small signatures."""
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / (3 * 255.0)


class RegionDetector:
    def __init__(self, event, region, templates, threshold=0.10, cooldown=4.0, n=1):
        self.event, self.region, self.threshold, self.cooldown, self.n = event, tuple(region), threshold, cooldown, n
        self.sigs = [signature(t) for t in templates]
        self._on, self._last = False, -1e9

    def score(self, crop):
        sig = signature(crop)
        return min(distance(sig, s) for s in self.sigs)

    def check(self, crop, now):
        """True once when the region starts to match (not again until it stops matching and the cooldown passes)."""
        match = self.score(crop) <= self.threshold
        fire = match and not self._on and now - self._last >= self.cooldown
        self._on = match
        if fire:
            self._last = now
        return fire


def bbox(region, screen):
    W, H = screen
    x, y, w, h = region
    x0, y0 = max(0, int(x * W)), max(0, int(y * H))
    return (x0, y0, min(W, max(x0 + 1, int((x + w) * W))), min(H, max(y0 + 1, int((y + h) * H))))


def grab_region(box):
    try:
        from PIL import ImageGrab
        return ImageGrab.grab(bbox=box)
    except Exception:
        return None


class Reactor:
    """Polls the detectors on a background thread; events are collected with take()."""

    def __init__(self, detectors, screen, grab=grab_region, hz=2.5, clock=time.time):
        self.detectors, self.screen, self.grab, self.hz, self.clock = detectors, screen, grab, hz, clock
        self.events = queue.Queue()
        self.error = ""
        self._stop = threading.Event()
        self._thread = None

    def poll(self):
        fired = []
        for d in self.detectors:
            crop = self.grab(bbox(d.region, self.screen))
            if crop is None:
                self.error = "can't capture the screen here"
                return fired
            if d.check(crop, self.clock()):
                fired.append((d.event, d.n))
            del crop                                         # the patch is gone as soon as it's compared
        return fired

    def _run(self):
        while not self._stop.wait(1.0 / self.hz):
            try:
                for ev in self.poll():
                    self.events.put(ev)
            except Exception as exc:
                self.error = type(exc).__name__
                return

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def take(self):
        out = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                return out


def load_config(path):
    """({game_key: [RegionDetector]}, [warnings]). A missing file is fine; bad entries are skipped."""
    if not os.path.isfile(path):
        return {}, []
    base = os.path.dirname(os.path.abspath(path))
    warns, out = [], {}
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict)
    except (OSError, ValueError, AssertionError):
        return {}, [f"{os.path.basename(path)} isn't valid JSON"]
    for game, body in cfg.items():
        if game not in gamemode.GAMES or not isinstance(body, dict):
            warns.append(f"unknown game '{game}'")
            continue
        for i, d in enumerate(body.get("detectors", [])):
            tag = f"{game}[{i}]"
            try:
                event = d["event"]
                if event not in gamemode.EVENT_KINDS:
                    raise ValueError(f"unknown event '{event}'")
                x, y, w, h = [float(v) for v in d["region"]]
                if not (0 <= x < 1 and 0 <= y < 1 and 0 < w <= 1 and 0 < h <= 1 and x + w <= 1.0001 and y + h <= 1.0001):
                    raise ValueError("region must be fractions of the screen")
                temps = []
                for rel in d["templates"]:
                    p = os.path.normpath(os.path.join(base, rel))
                    if not p.startswith(base):
                        raise ValueError("templates must be inside the config folder")
                    temps.append(Image.open(p).convert("RGB"))
                if not temps:
                    raise ValueError("needs at least one template")
                thr = min(0.5, max(0.01, float(d.get("threshold", 0.10))))
                out.setdefault(game, []).append(RegionDetector(
                    event, (x, y, w, h), temps, thr, max(1.0, float(d.get("cooldown", 4.0))), int(d.get("n", 1))))
            except (KeyError, TypeError, ValueError, OSError) as exc:
                warns.append(f"{tag}: {exc}")
    return out, warns
