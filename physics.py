"""Throwing and falling (pure logic, no Tk).

Units match the app's air loop: positions in pixels, velocities in pixels per 25 fps frame, y grows downward.
"""

FRAME = 25.0                  # the app's reference frame rate
GRAVITY = 1.1                 # per frame, times dpi
TERMINAL = 38.0               # max fall speed, times dpi
WALL_BOUNCE = 0.6
CEILING_BOUNCE = 0.5
FLOOR_BOUNCE = 0.5            # how much speed she keeps when she hits the ground hard
BOUNCE_MIN = 9.0              # below this impact speed (times dpi) she just lands
AIR_DRAG = 0.992              # per frame
THROW_MAX = 42.0              # max launch speed per frame, times dpi
SAMPLE_WINDOW = 0.12          # seconds of mouse history that make up the throw
STALE = 0.15                  # a throw only counts if the mouse was still moving this recently


class Tracker:
    """Remembers the last few mouse samples while she's being dragged."""

    def __init__(self):
        self.samples = []

    def add(self, t, x, y):
        self.samples = [s for s in self.samples if t - s[0] <= 0.4] + [(t, x, y)]

    def velocity(self, now):
        """(vx, vy) in pixels per second over the last SAMPLE_WINDOW, or (0, 0) if she was held still."""
        if len(self.samples) < 2 or now - self.samples[-1][0] > STALE:
            return 0.0, 0.0
        last = self.samples[-1]
        recent = [s for s in self.samples if last[0] - s[0] <= SAMPLE_WINDOW]
        first = recent[0] if len(recent) >= 2 else self.samples[-2]
        dt = max(0.001, last[0] - first[0])
        return (last[1] - first[1]) / dt, (last[2] - first[2]) / dt


def launch(vx_s, vy_s, dpi=1.0):
    """Mouse speed in px/second -> per-frame launch velocity, clamped. Returns (vx, vy, speed_fraction 0..1)."""
    k = 0.85 / FRAME
    lim = THROW_MAX * max(1.0, dpi)
    vx = max(-lim, min(lim, vx_s * k))
    vy = max(-lim, min(lim, vy_s * k))
    return vx, vy, min(1.0, (vx * vx + vy * vy) ** 0.5 / lim)


def step_air(x, y, vx, vy, dt, box, half_w, height, dpi=1.0):
    """Advance one air step. box = (left, top, right, bottom) she may be in; (x, y) is her feet point,
    half_w her half width, height her height. Returns (x, y, vx, vy, events) where events is a set of
    'wall', 'ceiling', 'bounce' (hit the floor hard and rebounds) and 'floor' (hit the floor and stays)."""
    dpi = max(1.0, dpi)
    ev = set()
    f = dt * FRAME
    vy = min(vy + GRAVITY * dpi * f, TERMINAL * dpi)
    vx *= AIR_DRAG ** f
    x += vx * f
    y += vy * f
    l, t, r, b = box
    if x < l + half_w or x > r - half_w:
        x = min(max(x, l + half_w), r - half_w)
        if abs(vx) > 1.5 * dpi:
            ev.add("wall")
        vx *= -WALL_BOUNCE
    if y - height < t:
        y = t + height
        if vy < 0:
            vy = -vy * CEILING_BOUNCE
            ev.add("ceiling")
    if y >= b and vy > 0:
        y = b
        if vy > BOUNCE_MIN * dpi:
            vy = -vy * FLOOR_BOUNCE
            vx *= 0.85
            ev.add("bounce")
        else:
            ev.add("floor")
    return x, y, vx, vy, ev
