"""Launch intro: she climbs up into your screen, grabs the edges, says hi, grins and waves (pure timeline, no Tk).

Frames are pet/intro/<stem>.webp (16:9 art). The window rises from the bottom of the screen, plays the frames,
then drops away and the normal pet appears. Click to skip. /intro off brings back the old beam animation.
"""
FRAMES = [("intro-grab", 0.45),
          ("intro-mouth1", 0.11), ("intro-mouth2", 0.11), ("intro-mouth3", 0.11), ("intro-mouth2", 0.11),
          ("intro-mouth1", 0.11), ("intro-mouth3", 0.11),
          ("intro-happy", 0.55), ("intro-smear", 0.10),
          ("intro-wave1", 0.14), ("intro-wave2", 0.14), ("intro-wave3", 0.14), ("intro-wave2", 0.14),
          ("intro-wave1", 0.14), ("intro-wave2", 0.14), ("intro-wave3", 0.14),
          ("intro-happy", 0.40)]
ENTER, EXIT = 0.28, 0.30
DURATION = ENTER + sum(d for _, d in FRAMES) + EXIT
STEMS = sorted({s for s, _ in FRAMES})


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def at(t):
    """(frame stem, drop) at time t, or None when it's over. drop: 0 = fully up, 1 = hidden below the screen."""
    if t < 0 or t >= DURATION:
        return None
    if t < ENTER:
        return FRAMES[0][0], 1.0 - _ease(t / ENTER)
    u = t - ENTER
    for stem, d in FRAMES:
        if u < d:
            return stem, 0.0
        u -= d
    return FRAMES[-1][0], _ease(u / EXIT)


def size(screen_w, screen_h, art_w=1672, art_h=941):
    """Window size: about half the screen width, never taller than 45% of it."""
    w = int(min(screen_w * 0.5, 900))
    h = int(w * art_h / art_w)
    if h > screen_h * 0.45:
        h = int(screen_h * 0.45)
        w = int(h * art_w / art_h)
    return max(160, w), max(90, h)
