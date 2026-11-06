"""Several screens (pure logic, no Tk): which one is she on, which one are you on, and when to follow."""
from collections import namedtuple

Mon = namedtuple("Mon", "rect work primary")     # rect/work are (left, top, right, bottom)


def contains(rect, x, y):
    return rect[0] <= x < rect[2] and rect[1] <= y < rect[3]


def index_at(mons, x, y):
    """Index of the monitor holding the point; if it's off every screen, the nearest one. None if no monitors."""
    if not mons:
        return None
    for i, m in enumerate(mons):
        if contains(m.rect, x, y):
            return i

    def dist(m):
        dx = max(m.rect[0] - x, 0, x - m.rect[2])
        dy = max(m.rect[1] - y, 0, y - m.rect[3])
        return dx * dx + dy * dy
    return min(range(len(mons)), key=lambda i: dist(mons[i]))


def neighbor(mons, cur, side):
    """The monitor next to `cur` on the 'left' or 'right' (touching, with some vertical overlap), or None."""
    if cur is None or not mons:
        return None
    c = mons[cur].rect
    best, gap = None, 1e9
    for i, m in enumerate(mons):
        if i == cur:
            continue
        r = m.rect
        if min(c[3], r[3]) - max(c[1], r[1]) <= 40:
            continue
        g = (r[0] - c[2]) if side == "right" else (c[0] - r[2])
        if -8 <= g < gap and g < 200:
            best, gap = i, g
    return best


class Follower:
    """Decides when she should hop over to the monitor you've settled on."""

    def __init__(self, dwell=8.0, cooldown=60.0):
        self.dwell, self.cooldown = dwell, cooldown
        self.target, self.since, self.last = None, None, -1e9

    def update(self, now, here, user):
        """here = her monitor, user = your monitor. Returns the monitor to move to, or None."""
        if user is None or here is None or user == here:
            self.target = self.since = None
            return None
        if self.target != user or self.since is None:
            self.target, self.since = user, now
            return None
        if now - self.since >= self.dwell and now - self.last >= self.cooldown:
            self.last, self.target, self.since = now, None, None
            return user
        return None
