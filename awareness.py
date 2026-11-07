"""What is the user doing? (pure logic, no Tk)

Capri only ever sees the *title of the front window* (e.g. "YouTube - Google Chrome") and turns it
into a one-word category. The title itself is never stored, logged or sent anywhere. She never
sees keystrokes or screen contents. Only a short hint like "coding" can reach the AI in chat, and
only while awareness is on.
"""

# Order matters: the first category with a matching keyword wins.
RULES = [
    ("cyberpunk", ["cyberpunk 2077", "cyberpunk2077", "edgerunners"]),
    ("game", ["steam", "minecraft", "roblox", "fortnite", "valorant", "league of legends", "genshin",
              "epic games", "overwatch", "apex legends", "counter-strike", "rocket league", "among us"]),
    ("ai", ["claude", "chatgpt", "gemini", "copilot", "perplexity"]),
    ("school", ["google classroom", "classroom", "brightspace", "d2l", "khan academy", "quizlet", "desmos",
                "kahoot", "schoology", "turnitin", "edpuzzle"]),
    ("video", ["youtube", "netflix", "twitch", "prime video", "disney+", "crunchyroll", "hulu", "vlc media"]),
    ("music", ["spotify", "soundcloud", "apple music", "youtube music", "tidal"]),
    ("coding", ["visual studio code", "pycharm", "intellij", "sublime text", "notepad++", "powershell",
                "command prompt", "windows terminal", "git bash", "github", "stack overflow", "replit",
                "codespaces", "jupyter", "vim", "cmd.exe"]),
    ("chat", ["discord", "whatsapp", "telegram", "messenger", "signal", "slack", "microsoft teams"]),
    ("writing", ["google docs", "microsoft word", "- word", "notion", "obsidian", "onenote", "libreoffice writer"]),
    ("social", ["tiktok", "twitter", "reddit", "instagram", "facebook", "snapchat", "pinterest", "tumblr"]),
]

PHRASE = {
    "cyberpunk": "playing Cyberpunk 2077", "game": "playing a game", "ai": "chatting with another AI",
    "school": "doing schoolwork", "video": "watching a video", "music": "listening to music",
    "coding": "coding", "chat": "chatting with friends", "writing": "writing", "social": "scrolling social media",
}

LINES = {
    "cyberpunk": ["Night City?! That's my home turf, choom!", "Cyberpunk?! Say hi to Night City for me."],
    "game": ["Gig time. Don't flatline!", "Game on. I'll cheer from the corner.", "Preem. Go get 'em."],
    "ai": ["Chatting with another AI? Rude. Tell it I'm cuter.", "Another AI? I'm the original netrunner."],
    "school": ["Schoolwork mode? Respect.", "School gig. One tiny step at a time. You got this."],
    "video": ["Movie night? Scoot over.", "Braindance time. I'll be quiet. Mostly.", "Popcorn's on you."],
    "music": ["Ooh, a banger? Turn it up.", "I can feel the bass in my pixels."],
    "coding": ["Hacking the grid? I'll supervise from up here.", "Netrunner mode: engaged.", "One bug at a time, choom."],
    "chat": ["Gossiping, huh? Tell them I said hi.", "Social hour. Hydrate."],
    "writing": ["Writing a masterpiece? Preem.", "Words time. Save often."],
    "social": ["Scrolling again? Eyes up for a sec.", "Doomscroll detected. Judging. Lovingly."],
}

# After this many seconds in one category she nudges you once, then again every 20 minutes.
NUDGE_AFTER = {"social": 25 * 60, "video": 90 * 60, "game": 120 * 60, "coding": 60 * 60, "school": 50 * 60,
               "writing": 60 * 60, "chat": 60 * 60}
NUDGES = {
    "social": "Twenty-five minutes of scrolling. Stand up, stretch.",
    "video": "Long braindance. Water and a stretch?",
    "game": "Two hours deep. Hydrate. Eyes off the screen for a minute.",
    "coding": "An hour of code. Stand up and stretch, netrunner.",
    "school": "You've been grinding a while. Break time. Five minutes.",
    "writing": "An hour of writing. Stretch those fingers.",
    "chat": "Long chat session. Drink some water.",
}


BROWSERS = ("google chrome", "microsoft edge", "mozilla firefox", "firefox", "brave", "opera", "vivaldi", "arc",
            "chromium", "safari")
SITES = ("youtube", "twitch", "reddit", "netflix", "tiktok", "twitter", "instagram", "facebook", "kick.com",
         "prime video", "crunchyroll", "fandom", "wiki")


def is_web(title):
    """A browser tab or a video/social site? Then a game name in the title means you're WATCHING or READING
    about it ("Valorant clips - Twitch"), not playing."""
    t = (title or "").lower().strip()
    if not t:
        return False
    tail = t.replace("\u2014", "-").replace("\u2013", "-").rsplit(" - ", 1)[-1].strip()
    return tail in BROWSERS or any(s in t for s in SITES)


def classify(title):
    """One-word category for a window title, or None. In a browser / on a site, games don't count."""
    t = (title or "").lower()
    if not t:
        return None
    web = is_web(t)
    for cat, keys in RULES:
        if web and cat in ("game", "cyberpunk"):
            continue
        if any(k in t for k in keys):
            return cat
    return None


def line(cat, rng):
    pool = LINES.get(cat)
    return rng.choice(pool) if pool else ""


def nudge(cat):
    return NUDGES.get(cat, "")
