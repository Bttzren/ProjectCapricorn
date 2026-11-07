"""How Capri shows what she feels (pure logic, no Tk).

The AI starts each line it writes for her with a tag like "[smug]". parse_tag() strips it off (the tag is never
shown or spoken) and Capri plays that emotion: a sprite row, a small in-place motion and maybe an icon.

Custom art: a sheet row or a file named after the emotion (e.g. expressions/smug.png) replaces the built-in
pose automatically; see SPRITE_SPEC. Expressions never move her across the screen: hop/shake/tilt in place only.
"""
import math
import re

# name: (fallback animation chain on the current sheet, motion, icon)
#   motions: hop | bounce | shake | tremble | tilt | droop | puff | sway | none
#   icons: canvas shapes Capri already draws: "!", "?", "heart", "note", "star", "anger" (or None)
EMOTIONS = {
    "happy":       (["waving", "jumping"], "hop", None),
    "laugh":       (["jumping", "waving"], "bounce", None),
    "excited":     (["jumping", "waving"], "bounce", "star"),
    "love":        (["waving"], "sway", "heart"),
    "proud":       (["idle"], "puff", "star"),
    "smug":        (["look-a", "idle"], "tilt", None),
    "sad":         (["failed", "waiting"], "droop", None),
    "angry":       (["failed"], "shake", "anger"),
    "surprised":   (["jumping", "failed"], "hop", "!"),
    "scared":      (["failed", "waiting"], "tremble", "!"),
    "thinking":    (["review", "waiting"], "none", "?"),
    "confused":    (["look-b", "review"], "tilt", "?"),
    "embarrassed": (["look-b", "waiting"], "tremble", None),
    "sleepy":      (["waiting", "idle"], "droop", None),
    "bored":       (["waiting", "idle"], "sway", None),
    "curious":     (["look-a", "review"], "tilt", "?"),
    "singing":     (["waving", "idle"], "sway", "note"),
}
NEUTRAL = ("neutral", "calm", "none", "normal", "chill")

# face close-ups (pet/faces/<stem>.png) shown by her speech bubble; pick by what each picture shows
FACES = {
    "happy": "capri-face", "laugh": "face-laugh", "excited": "face-laugh", "love": "capri-face",
    "proud": "face-smug", "smug": "face-smug", "sad": "face-aside", "angry": "face-many",
    "surprised": "face-wide", "scared": "face-wide", "thinking": "face-calm", "confused": "face-look",
    "embarrassed": "face-aside", "sleepy": "face-calm", "bored": "face-aside", "curious": "face-look",
    "singing": "capri-face",
}
FACE_DEFAULT = "face-calm"
# anime-style cut-in panels (pet/cutins/<stem>.png): only big moments, rarely
CUTINS = {"laugh": "cutin-laugh", "excited": "cutin-grin", "surprised": "cutin-eyes"}
CUTIN_GAP = 300.0           # seconds between cut-ins (unless previewed with /express)
CUTIN_SECS = 1.1

SYNONYMS = {
    "joy": "happy", "glad": "happy", "cheerful": "happy", "pleased": "happy", "content": "happy", "grin": "happy",
    "amused": "laugh", "lol": "laugh", "laughing": "laugh", "giggle": "laugh", "funny": "laugh",
    "hyped": "excited", "hype": "excited", "pumped": "excited", "thrilled": "excited",
    "loving": "love", "affectionate": "love", "adoring": "love", "warm": "love",
    "smirk": "smug", "sassy": "smug", "cocky": "smug", "teasing": "smug", "playful": "smug",
    "upset": "sad", "down": "sad", "lonely": "sad", "disappointed": "sad", "hurt": "sad",
    "mad": "angry", "annoyed": "angry", "grumpy": "angry", "irritated": "angry", "furious": "angry",
    "shocked": "surprised", "wow": "surprised", "startled": "surprised", "amazed": "surprised",
    "nervous": "scared", "worried": "scared", "afraid": "scared", "anxious": "scared",
    "thoughtful": "thinking", "hmm": "thinking", "pondering": "thinking", "focused": "thinking",
    "puzzled": "confused", "unsure": "confused", "lost": "confused",
    "shy": "embarrassed", "flustered": "embarrassed", "awkward": "embarrassed", "blush": "embarrassed",
    "tired": "sleepy", "drowsy": "sleepy", "yawn": "sleepy",
    "meh": "bored", "unimpressed": "bored", "deadpan": "bored", "dry": "bored",
    "interested": "curious", "intrigued": "curious", "sing": "singing", "humming": "singing",
    "proudly": "proud", "smug-proud": "proud", "confident": "proud",
}

# her current mood -> the expression a preset (non-AI) line gets
MOOD_FACE = {"sassy": "smug", "playful": "happy", "sleepy": "sleepy", "lonely": "bored", "content": None}

TAG = re.compile(r"^\s*[\[(<{]\s*([A-Za-z][A-Za-z \-]{0,18})\s*[\])>}]\s*[:\-–—]?\s*")

TAG_INSTRUCTION = (" Start your reply with ONE tag in square brackets for how you feel saying it, from: "
                   + " ".join(f"[{n}]" for n in list(EMOTIONS) + ["neutral"])
                   + ". Example: [smug] Nice tabs. The tag is never shown or spoken.")

SPRITE_SPEC = ("Expression sprites: one file per emotion in the pet folder's 'expressions' subfolder, named after the "
               "emotion (" + ", ".join(EMOTIONS) + ").png / .webp / .gif. A horizontal strip of 1-8 frames with the "
               "same frame proportions as the main sheet, or an animated GIF/WebP. Transparent background, fully "
               "opaque art (pixels under ~67% opacity are cut), character in the same spot and scale as the sheet.")


def canonical(word):
    """'Smug' -> 'smug', 'annoyed' -> 'angry', 'neutral' -> '', anything unknown -> None."""
    w = re.sub(r"[^a-z\-]", "", (word or "").lower().strip())
    if w in NEUTRAL:
        return ""
    if w in EMOTIONS:
        return w
    return SYNONYMS.get(w)


def parse_tag(raw):
    """(emotion or '' or None, text without the tag). A tag alone on the first line is fine too.
    None = no usable tag (unknown word or none at all): show no expression, don't guess."""
    t = (raw or "").strip()
    m = TAG.match(t)
    if not m:
        return None, t
    emo = canonical(m.group(1))
    rest = t[m.end():].strip()
    if emo is None:
        # an unknown bracketed word: drop it if it looks like a tag (one or two words), keep the text
        return None, rest if len(m.group(1).split()) <= 2 else t
    return emo, rest


def for_mood(mood):
    return MOOD_FACE.get(mood)


class Gate:
    """Not every line gets acted out (the user hates corny): at most one expression per `gap` seconds,
    except strong ones the moment calls for."""
    STRONG = ("surprised", "scared", "angry", "laugh", "excited", "love")

    def __init__(self, gap=12.0):
        self.gap, self.last = gap, -1e9

    def allow(self, now, emotion, forced=False):
        if not emotion or emotion not in EMOTIONS:
            return False
        if forced or emotion in self.STRONG or now - self.last >= self.gap:
            self.last = now
            return True
        return False


def motion(kind, age, dur, dpi=1.0, direction=1):
    """(dy_px, angle_deg, sx, sy) for an in-place motion `age` seconds into an expression lasting `dur`.
    Fades out over the last 0.3 s so she settles back smoothly."""
    if age < 0 or age >= dur:
        return 0.0, 0.0, 1.0, 1.0
    fade = min(1.0, (dur - age) / 0.3, age / 0.08 if age < 0.08 else 1.0)
    dy = ang = 0.0
    sx = sy = 1.0
    if kind == "hop":
        dy = -abs(math.sin(min(age, 0.5) * math.pi / 0.5)) * 10 * dpi if age < 0.5 else 0.0
    elif kind == "bounce":
        dy = -abs(math.sin(age * 12)) * 6 * dpi
    elif kind == "shake":
        ang = math.sin(age * 40) * 6
    elif kind == "tremble":
        ang = math.sin(age * 55) * 2.5
    elif kind == "tilt":
        ang = 9.0 * direction
    elif kind == "droop":
        ang, sy, sx = -5.0 * direction, 0.95, 1.03
    elif kind == "puff":
        sy, sx = 1.05, 0.98
    elif kind == "sway":
        ang = math.sin(age * 4) * 7
    return dy * fade, ang * fade, 1.0 + (sx - 1.0) * fade, 1.0 + (sy - 1.0) * fade


def face_for(emotion, have=None):
    """Face file stem for an emotion, falling back to the calm face (or None if the set has neither)."""
    stem = FACES.get(emotion, FACE_DEFAULT)
    if have is None or stem in have:
        return stem
    return FACE_DEFAULT if FACE_DEFAULT in have else None


def cutin_slide(age, dur=CUTIN_SECS, edge=0.15):
    """0..1 horizontal offset fraction for a cut-in: slides in from the left, holds, slides out to the right.
    Returns -1..0 while entering, 0 while holding, 0..1 while leaving, None when it's over."""
    if age < 0 or age >= dur:
        return None
    if age < edge:
        x = age / edge
        return -(1 - x * x * (3 - 2 * x))
    if age > dur - edge:
        x = (age - (dur - edge)) / edge
        return x * x * (3 - 2 * x)
    return 0.0


# ------------------------------------------------------------------ mini face (her visor: chat avatar, tiny mode)
MINI = ("idle", "blink", "talk", "talk2", "look_left", "look_right", "annoyed", "annoyed_talk", "glitch", "watcher")
MINI_FOR = {"angry": "annoyed", "scared": "glitch", "sleepy": "blink", "confused": "look_left",
            "curious": "look_right", "embarrassed": "look_left", "thinking": "look_right"}


def mini_pick(t, talking=False, thinking=False, angry=False, watcher=False, emotion=None):
    """Which mini face to show at time t (seconds). Deterministic in t so it's testable:
    talking -> mouth shapes, thinking -> glances side to side, angry -> annoyed, otherwise idle with a blink
    every ~4.3 s, an occasional sideways look and a rare glitch. The Watcher has one face (+ blink)."""
    cyc, ph = int(t // 4.3), t % 4.3
    if watcher:
        return "blink" if ph < 0.15 else "watcher"
    if angry or emotion == "angry":
        return "annoyed_talk" if talking and int(t * 6) % 2 else "annoyed"
    if talking:
        return ("talk", "talk2", "talk", "idle")[int(t * 7) % 4]
    if emotion in MINI_FOR:
        return MINI_FOR[emotion]
    if thinking:
        return "look_left" if int(t / 0.9) % 2 else "look_right"
    if ph < 0.15:
        return "blink"
    if cyc % 9 == 4 and 2.0 <= ph < 2.25:
        return "glitch"
    if cyc % 5 == 2 and 1.0 <= ph < 2.0:
        return "look_left" if cyc % 2 else "look_right"
    return "idle"


_ANY_TAG = re.compile(r"\s*[\[(<{]\s*([A-Za-z][A-Za-z \-]{0,18})\s*[\])>}]\s*")


def strip_tags(text):
    """Remove every bracketed emotion word ([smug], (laugh), [neutral]...) anywhere in a reply. Other brackets
    stay. Used on chat replies, which aren't run through speech.sanitize, so no tag reaches the bubble, the
    voice, the saved history or a call."""
    def drop(m):
        return " " if canonical(m.group(1)) is not None else m.group(0)
    out = _ANY_TAG.sub(drop, text or "")
    return re.sub(r"[ \t]{2,}", " ", out).replace(" \n", "\n").strip()


def split_reply(raw):
    """(emotion or None, clean text) for a multi-line chat reply."""
    emo, rest = parse_tag(raw)
    return emo, strip_tags(rest)
