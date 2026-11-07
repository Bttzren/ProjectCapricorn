"""Small movement helpers so Capri moves like she has weight (pure math, no Tk).

- Walks speed up and slow down instead of starting/stopping at full speed.
- At the edge of the screen (or a window) she slows, turns, and walks back instead of bouncing instantly.
- Her steps (bob + run frames) follow the distance she covers, so her feet don't skate.
- Landings squash more after a long fall than after a small hop.
"""
import math

RAMP = 0.35          # seconds to reach full walking speed / to stop
TURN_PAUSE = 0.25    # seconds standing still when turning around at an edge
STRIDE = 26.0        # px (at 100% size) per step cycle of the run animation


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def walk_factor(age, dur, ramp=RAMP):
    """0..1 speed multiplier for a walk that started `age` seconds ago and lasts `dur` seconds."""
    if dur is None or dur <= 0:
        return smoothstep(age / ramp) if ramp > 0 else 1.0
    ramp = min(ramp, dur / 2)
    if ramp <= 0:
        return 1.0
    return min(smoothstep(age / ramp), smoothstep((dur - age) / ramp))


def edge_slow(x, lo, hi, direction, zone):
    """0.25..1 multiplier: slow down when walking toward an edge closer than `zone` px."""
    if zone <= 0:
        return 1.0
    gap = (hi - x) if direction > 0 else (x - lo)
    return 0.25 + 0.75 * smoothstep(gap / zone)


def step_phase(phase, distance, stride):
    """Advance the step clock by the distance walked (in strides). One unit = one full step cycle."""
    return phase + abs(distance) / max(1e-6, stride)


def bob(phase, height):
    """Vertical bob (negative = up) for the step clock: one bounce per step."""
    return -abs(math.sin(phase * math.pi)) * height


def landing_squash(vy, scale=1.0):
    """How hard a landing looks (0.35..1.0) from the downward speed at impact (px per 1/25 s at 100% size)."""
    v = max(0.0, vy / max(1e-6, scale))
    return 0.35 + 0.65 * smoothstep(v / 30.0)
