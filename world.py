"""The world around her: special days, Night City Radio, battery moods (pure logic, no Tk)."""
import calendar
import re

RADIO = [
    "Night City Radio. All the hits, none of the ICE.",
    "This is your DJ in the static. Hydrate, choom.",
    "Next up: forty minutes of pure synth. Nova.",
    "Traffic update: everything's a mess. As usual.",
    "Weather: neon, with a chance of glitch.",
    "Shoutout to every netrunner still awake. You're preem.",
    "Reminder: chrome doesn't fix bad posture.",
    "You're listening to the only station that can't be hacked. Probably.",
    "Dedicated to everyone with 47 tabs open: respect.",
    "That was a banger. Pretend I know the name of the band.",
    "Drop what you're doing. Roll your shoulders. Back to it.",
    "And now, a word from our sponsor: water. Drink some.",
]

# (month, day) -> (key, line)
SPECIAL = {
    (1, 1): ("newyear", "Happy New Year, choom! New year, new gigs."),
    (2, 14): ("valentine", "Happy Valentine's Day! I got you a heart. It's a glitch, but it's sincere."),
    (3, 14): ("pi", "Happy Pi Day! 3.14159... and then I glitch."),
    (10, 31): ("halloween", "Happy Halloween! Boo. I'm a ghost in your machine all year."),
    (12, 10): ("cp77", "Happy Night City Day, choom! The city's birthday."),
    (12, 25): ("xmas", "Merry Christmas, choom! Eddies for everyone. (Not really.)"),
    (12, 31): ("nye", "Last day of the year. Happy New Year's Eve, choom!"),
}


def parse_birthday(text):
    """'MM-DD' (or 'M/D') -> 'MM-DD' if it's a real calendar day, else None. Feb 29 is allowed."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*[-/]\s*(\d{1,2})\s*", text or "")
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12) or not (1 <= day <= calendar.monthrange(2024, month)[1]):
        return None
    return f"{month:02d}-{day:02d}"


def special_day(month, day, birthday="", name=""):
    """(key, line) if today is special, else None. Birthdays win."""
    if birthday and birthday == f"{month:02d}-{day:02d}":
        who = f", {name}" if name else ""
        return "birthday", f"Happy Birthday{who}! Cake for you, glitches for me. Kidding. Mostly."
    return SPECIAL.get((month, day))


def battery_event(state, percent, plugged):
    """Battery moods with hysteresis, so she only speaks when something changes.

    state: dict you keep between calls. percent: 0-100 or None if unknown. Returns a line or None.
    """
    if percent is None or percent > 100:
        return None
    low = state.get("low", False)
    if not plugged and percent <= 20 and not low:
        state["low"] = True
        return f"Battery's at {percent}%. Plug in before we flatline, choom."
    if plugged and low and percent < 95:
        state["low"] = False
        return "Ahh, juice. Thanks, choom."
    if plugged and percent >= 30:
        state["low"] = False
    if not plugged and percent >= 40:
        state["low"] = False
    return None
