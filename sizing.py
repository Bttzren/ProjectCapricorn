"""How big she is (pure logic, no Tk): the size you pick plus the small changes she makes by herself."""
import re

STEPS = (0.5, 0.65, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5)
MIN, MAX = 0.4, 2.5
NAMES = {"tiny": 0.5, "small": 0.8, "normal": 1.0, "medium": 1.0, "large": 1.5, "big": 1.5, "huge": 2.0,
         "giant": 2.5, "regular": 1.0}


def clamp(x):
    return max(MIN, min(MAX, float(x)))


def parse(text):
    """'small' | '1.3' | '130%' -> scale, or None."""
    t = (text or "").strip().lower()
    if t in NAMES:
        return NAMES[t]
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(%?)", t)
    if not m:
        return None
    v = float(m.group(1))
    v = v / 100.0 if (m.group(2) or v > 5) else v
    return clamp(v) if v > 0 else None


def step(current, direction):
    """The next preset size up (+1) or down (-1) from `current`."""
    if direction > 0:
        for s in STEPS:
            if s > current + 0.01:
                return s
        return STEPS[-1]
    for s in reversed(STEPS):
        if s < current - 0.01:
            return s
    return STEPS[0]


def cap_for_screen(scale, screen_h, sprite_h=170):
    """Never let her be taller than about 45% of the screen."""
    return max(MIN, min(scale, 0.45 * screen_h / float(sprite_h)))


def auto_factor(gaming=False, focusing=False, sleeping=False, excited=False):
    """How much she changes her own size relative to the size you chose. Smaller when you're busy."""
    if excited:
        return 1.35
    if gaming:
        return 0.65
    if focusing:
        return 0.8
    if sleeping:
        return 0.85
    return 1.0


def quantize(scale):
    """Round to 0.05 so only a handful of sizes ever need loading."""
    return round(round(clamp(scale) / 0.05) * 0.05, 2)


def spoken_size(text):
    """('abs', scale) | ('step', +1/-1) | None for things like 'get bigger', 'make yourself tiny'."""
    t = (text or "").lower()
    if not re.search(r"\b(bigger|larger|grow|enlarge|smaller|shrink|tiny|huge|giant|normal size|regular size|size)\b", t):
        return None
    for word, val in NAMES.items():
        if re.search(rf"\b{word}\b", t) and word not in ("big", "medium", "large", "small"):
            return ("abs", val)
    if re.search(r"\b(bigger|larger|grow|enlarge)\b", t):
        return ("step", 1)
    if re.search(r"\b(smaller|shrink)\b", t):
        return ("step", -1)
    if re.search(r"\b(big|large)\b", t):
        return ("abs", NAMES["large"])
    if re.search(r"\b(small)\b", t):
        return ("abs", NAMES["small"])
    return None
