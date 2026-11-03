"""Procedural puppet animation for Capri (PIL only, no Tk).

Capri ships as one tiny standing pose.  This module turns that single image into
animation frames by warping its pixel rows: each output row reads a (shifted)
source row, so bodies bob, lean, stretch and talk without gaps or blurring.

    puppet = Puppet(idle_image)
    key, image = puppet.frame("walk", t_seconds, direction)
"""
import math

from PIL import Image

BLACK = (12, 10, 22, 255)
GREEN = (5, 245, 111, 255)
BLUE = (25, 105, 235)

PAD_X = 8     # transparent margin so sway/shear never clips
PAD_TOP = 10  # transparent headroom for stretch / bob


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _near(p, ref, tol):
    return abs(p[0] - ref[0]) + abs(p[1] - ref[1]) + abs(p[2] - ref[2]) <= tol


def find_eyes(img):
    """Bounding boxes (x0, y0, x1, y1) of the left and right eye, found via blue pixels.

    Returns [] when no eyes are found (the rig then falls back to ratios).
    """
    w, h = img.size
    px = img.load()
    pts = [(x, y) for y in range(int(h * 0.3)) for x in range(w)
           if px[x, y][3] > 127 and _near(px[x, y], BLUE, 70)]
    if len(pts) < 4:
        return []
    mid = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2.0
    boxes = []
    for side in (lambda x: x < mid, lambda x: x >= mid):
        grp = [p for p in pts if side(p[0])]
        if grp:
            boxes.append((min(p[0] for p in grp), min(p[1] for p in grp),
                          max(p[0] for p in grp), max(p[1] for p in grp)))
    return boxes


def find_mouth(img, eye_bottom):
    """(y0, y1) rows of the mouth: the first run of white pixels below the eyes."""
    w, h = img.size
    px = img.load()
    cap = max(4, int(h * 0.07))
    y0 = None
    for y in range(eye_bottom + 2, int(h * 0.7)):
        white = sum(1 for x in range(w) if px[x, y][3] > 127 and min(px[x, y][:3]) > 225)
        if white >= 3:
            if y0 is None:
                y0 = y
            if y - y0 >= cap:
                return y0, y
        elif y0 is not None:
            return y0, y
    return (y0, y0 + cap) if y0 is not None else None


def close_eyes(img, boxes):
    """Return a copy of img with the eyes painted shut (face-green lid + dark lash line)."""
    out = img.copy()
    px = out.load()
    w, h = out.size
    for x0, y0, x1, y1 in boxes:
        for y in range(max(0, y0 - 3), min(h, y1 + 4)):
            for x in range(max(0, x0 - 3), min(w, x1 + 4)):
                if px[x, y][3] > 127:
                    px[x, y] = GREEN
        ly = (y0 + y1) // 2 + 1
        for x in range(max(0, x0 - 3), min(w, x1 + 4)):
            if 0 <= ly < h:
                px[x, ly] = BLACK
    return out


class Puppet:
    def __init__(self, idle):
        self.src_open = idle.convert("RGBA")
        self.w, self.h = self.src_open.size
        eyes = find_eyes(self.src_open)
        if eyes:
            eye_bottom = max(b[3] for b in eyes)
            self.src_closed = close_eyes(self.src_open, eyes)
        else:
            eye_bottom = int(self.h * 0.2)
            self.src_closed = self.src_open
        self.eyes = eyes
        m = find_mouth(self.src_open, eye_bottom)
        if m is None:
            m = (int(self.h * 0.255), int(self.h * 0.31))
        self.mouth = m
        self.legs_y = int(self.h * 0.62)
        self.cache = {}

    # -- frame building -------------------------------------------------------
    def build(self, bob=0, sway=0, lean=0, legs=0, jaw=0, sy=1.0, closed=False):
        h, w = self.h, self.w
        src = self.src_closed if closed else self.src_open
        my0, my1 = self.mouth
        ly = self.legs_y
        out = Image.new("RGBA", (w + 2 * PAD_X, h + PAD_TOP), (0, 0, 0, 0))
        for u in range(-PAD_TOP, h):
            lift = bob * _clamp((ly - u) / float(ly), 0.0, 1.0)
            jshift = 0.0
            if u > my0:
                ramp = _clamp((u - my0) / float(max(1, my1 - my0)), 0.0, 1.0)
                tail = _clamp(1.0 - (u - my1) / float(max(1, ly - my1)), 0.0, 1.0) if u > my1 else 1.0
                jshift = jaw * ramp * tail
            s = u + lift - jshift
            if sy != 1.0:
                s = h - (h - s) / sy
            si = int(round(_clamp(s, 0, h - 1)))
            if s < -0.5:          # headroom above the sprite stays empty
                continue
            dx = sway * _clamp(1.0 - u / float(ly), 0.0, 1.0)
            dx += lean * _clamp(1.0 - u / float(h), 0.0, 1.0)
            dx += legs * _clamp((u - ly) / float(max(1, h - ly)), 0.0, 1.0)
            out.paste(src.crop((0, si, w, si + 1)), (PAD_X + int(round(dx)), u + PAD_TOP))
        return out

    # -- animation table --------------------------------------------------------
    @staticmethod
    def _blink(t, period=3.9, length=0.14):
        return (t % period) < length

    def params(self, anim, t, d=1):
        s = math.sin
        blink = self._blink(t)
        if anim == "walk":
            ph = t * 10
            return dict(bob=round(2 * abs(s(ph))), legs=round(3 * s(ph)), lean=2, sway=round(s(ph / 2)),
                        closed=blink)
        if anim == "dance":
            ph = t * 8
            return dict(bob=round(3 * abs(s(ph))), sway=round(3 * s(ph)), legs=round(3 * s(ph / 2)),
                        lean=round(2 * s(ph)), closed=False)
        if anim == "wave":
            return dict(bob=round(2 * abs(s(t * 6.5))), sway=round(2 * s(t * 13)), closed=False)
        if anim == "jump":
            return dict(bob=2, sy=1.08, closed=False)
        if anim == "startle":
            return dict(bob=3, sy=1.1, sway=round(s(t * 40)), closed=False)
        if anim in ("wait", "think"):
            return dict(bob=round(1 + s(t * 2)), sway=round(2 * s(t * 1.5)), lean=round(s(t * 1.5)), closed=blink)
        if anim == "fail":
            return dict(bob=-2, sway=round(1.5 * s(t * 30)), closed=False)
        if anim == "talk":
            return dict(bob=round(abs(s(t * 7))), jaw=round(2.5 * abs(s(t * 14))), sway=round(s(t * 3)),
                        closed=blink)
        if anim == "sleep":
            return dict(bob=round(0.5 + 0.5 * s(t * 1.4)), closed=True)
        if anim == "lounge":
            return dict(bob=round(0.5 + 0.5 * s(t * 1.6)), sway=round(s(t * 0.8)), closed=(t % 7) < 1.2)
        # idle (and anything unknown): breathe, drift, blink
        return dict(bob=round(1.5 * (0.5 + 0.5 * s(t * 2.2))), sway=round(s(t * 1.1)), closed=blink)

    def frame(self, anim, t, d=1):
        p = self.params(anim, t, d)
        key = (anim,) + tuple(sorted(p.items()))
        img = self.cache.get(key)
        if img is None:
            if len(self.cache) > 400:
                self.cache.clear()
            img = self.build(**p)
            self.cache[key] = img
        return key, img
