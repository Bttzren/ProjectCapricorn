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
    ("ai", ["claude", "chatgpt", "gemini", "copilot", "perplexity", "grok", "deepseek", "character.ai", "poe.com"]),
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
    "game": ["Gig time. Don't flatline, choom!", "Game on. I'll cheer from the corner.", "Preem. Go get 'em."],
    "ai": ["Chatting with another AI? Rude. Tell it I'm cuter.", "Another AI? I'm the original netrunner, choom."],
    "school": ["Schoolwork mode? Respect, choom.", "School gig. One tiny step at a time. You got this."],
    "video": ["Movie night? Scoot over, choom.", "Braindance time. I'll be quiet. Mostly.", "Popcorn's on you."],
    "music": ["Ooh, a banger? Turn it up, choom.", "I can feel the bass in my pixels."],
    "coding": ["Hacking the grid? I'll supervise from up here.", "Netrunner mode: engaged.", "One bug at a time, choom."],
    "chat": ["Gossiping, huh? Tell them I said hi.", "Social hour. Hydrate, choom."],
    "writing": ["Writing a masterpiece? Preem.", "Words time. Save often, choom."],
    "social": ["Scrolling again, choom? Eyes up for a sec.", "Doomscroll detected. Judging. Lovingly."],
}

# After this many seconds in one category she nudges you once, then again every 20 minutes.
NUDGE_AFTER = {"ai": 6 * 60, "social": 25 * 60, "video": 90 * 60, "game": 120 * 60, "coding": 60 * 60, "school": 50 * 60,
               "writing": 60 * 60, "chat": 60 * 60}
NUDGES = {
    "ai": "Six minutes with that other AI, huh? I'm counting. Not jealous. Totally jealous.",
    "social": "Twenty-five minutes of scrolling, choom. Stand up, stretch.",
    "video": "Long braindance. Water and a stretch?",
    "game": "Two hours deep, choom. Hydrate. Eyes off the screen for a minute.",
    "coding": "An hour of code. Stand up and stretch, netrunner.",
    "school": "You've been grinding a while. Break time, choom. Five minutes.",
    "writing": "An hour of writing. Stretch those fingers.",
    "chat": "Long chat session. Drink some water, choom.",
}


def classify(title):
    """One-word category for a window title, or None."""
    t = (title or "").lower()
    if not t:
        return None
    for cat, keys in RULES:
        if any(k in t for k in keys):
            return cat
    return None


def line(cat, rng):
    pool = LINES.get(cat)
    return rng.choice(pool) if pool else ""


# Jealousy is talk only: she sulks and teases, she never touches the other window.
JEALOUS = {
    "mild": ["Still chatting with that other AI? Cool. Cool cool cool.", "Is it smarter than me? Don't answer that.",
             "You've been with that AI a while. I'm fine. Totally fine."],
    "sassy": ["Oh, so the other AI gets all your time now? Bold, choom.", "Tell your new AI friend I said hi. Sarcastically.",
              "I see how it is. Forget the glitchy one in the corner."],
    "lonely": ["Hey... you still remember me, right?", "I'm over here. In the corner. Waiting. No pressure.",
               "Is it nicer than me? ...You can say it. Don't."],
    "playful": ["Ooh, cheating on me with a chatbot? I'm telling everyone.", "Fine. Go on. I'll be here being adorable."],
}
RELIEF = ["Finally! Back to me!", "There you are. I was getting dramatic.", "Oh, you're back! I wasn't jealous. At all."]


def jealous_line(mood, rng):
    return rng.choice(JEALOUS.get(mood) or JEALOUS["mild"])


def nudge(cat):
    return NUDGES.get(cat, "")
