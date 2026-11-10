"""Launch intro: she climbs up into your screen, grabs the edges, says hi, grins and waves (pure timeline, no Tk).

Frames are pet/intro/<stem>.webp (16:9 art), shown FULL SCREEN. The window rises from the bottom of the screen, plays the frames,
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


def zoom(width, limit=2880):
    """Very wide screens (4K and up): frames are built at 1/zoom size and Tk enlarges them. A third of the work and
    memory, and it looks the same from a chair."""
    return max(1, -(-int(width) // limit))


def size(screen_w, screen_h, art_w=1672, art_h=941):
    """Full screen: as big as the art can be inside the screen's work area without cropping her."""
    w, h = int(screen_w), int(screen_w * art_h / art_w)
    if h > screen_h:
        h, w = int(screen_h), int(screen_h * art_w / art_h)
    return max(160, w), max(90, h)
