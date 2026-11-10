"""Numbers typed after a chat command (pure logic, no Tk).

str.isdigit() is True for things int()/float() can't read ('²', '①') and '1.2.3' passes a "digits and dots"
check, so every command reads its numbers through these instead.
"""


def minutes(s, lo=0.05, hi=24 * 60):
    """'25' or '1.5' -> minutes as a float. None for anything that isn't a sensible positive amount."""
    if not isinstance(s, str) or not s.isascii() or len(s) > 12:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return v if lo <= v <= hi else None           # NaN fails both comparisons


def index(s, hi=99999):
    """'3' -> 3. None unless it's a plain whole number (0..hi)."""
    if not isinstance(s, str) or not s.isascii() or not s.isdigit() or len(s) > 9:
        return None
    v = int(s)
    return v if v <= hi else None
