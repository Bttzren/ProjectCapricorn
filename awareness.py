"""What is the user doing? (pure logic, no Tk)

Capri only ever sees the *title of the front window* (e.g. "YouTube - Google Chrome") and the *name of the
program it belongs to* (e.g. "discord"), and turns them into a one-word category. Neither is stored, logged or
sent anywhere. She never sees keystrokes or screen contents. Only a short hint like "coding" can reach the AI
in chat, and only while awareness is on.
"""
import re

# Keywords looked for in the title. Order matters: the first category with a match wins.
RULES = [
    ("cyberpunk", ["cyberpunk 2077", "cyberpunk2077", "edgerunners"]),
    ("game", ["minecraft", "roblox", "fortnite", "valorant", "league of legends", "genshin impact", "overwatch",
              "apex legends", "counter-strike", "rocket league", "among us", "marvel rivals", "rainbow six",
              "grand theft auto", "elden ring", "terraria", "stardew valley", "osu!", "lethal company", "helldivers",
              "call of duty", "warzone", "ea sports fc", "nba 2k", "dead by daylight", "the finals", "deadlock",
              "hollow knight", "celeste", "baldur's gate", "palworld", "phasmophobia", "destiny 2", "war thunder",
              "dota 2", "pubg", "sea of thieves", "the sims", "geometry dash", "brawlhalla", "fall guys", "hades",
              "risk of rain", "satisfactory", "factorio", "team fortress", "left 4 dead", "garry's mod", "portal 2",
              "half-life", "the witcher", "red dead redemption", "skyrim", "fallout", "starfield",
              "zenless zone zero", "honkai", "wuthering waves", "path of exile", "diablo", "world of warcraft",
              "final fantasy", "monster hunter", "dark souls", "sekiro", "resident evil", "forza horizon",
              "euro truck simulator", "cities: skylines", "age of empires", "rimworld", "subnautica",
              "no man's sky", "escape from tarkov", "balatro", "slay the spire", "vampire survivors", "undertale",
              "deltarune", "five nights at freddy's", "r.e.p.o", "content warning", "it takes two", "split fiction"]),
    ("ai", ["claude", "chatgpt", "gemini", "copilot", "perplexity"]),
    ("school", ["google classroom", "classroom", "brightspace", "d2l", "khan academy", "quizlet", "desmos",
                "kahoot", "schoology", "turnitin", "edpuzzle"]),
    ("music", ["spotify", "soundcloud", "apple music", "youtube music", "tidal"]),
    ("video", ["youtube", "netflix", "twitch", "prime video", "disney+", "crunchyroll", "hulu", "vlc media"]),
    ("coding", ["visual studio code", "visual studio", "pycharm", "intellij", "sublime text", "notepad++",
                "powershell", "command prompt", "windows terminal", "git bash", "github", "stack overflow", "replit",
                "codespaces", "jupyter", "vim", "cmd.exe"]),
    ("chat", ["discord", "whatsapp", "telegram", "messenger", "signal", "slack", "microsoft teams"]),
    ("writing", ["google docs", "microsoft word", "notion", "obsidian", "onenote", "libreoffice writer"]),
    ("social", ["tiktok", "twitter", "reddit", "instagram", "facebook", "snapchat", "pinterest", "tumblr"]),
]


def _word(key):
    """A keyword as a whole word: 'vim' is not in 'Vimeo', 'signal' is not in 'signals'."""
    return re.compile(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])")


_RULES = [(cat, [_word(k) for k in keys]) for cat, keys in RULES]

# The app's own name at the END of a title ("essay.docx - Word") says more than any word before it.
# "" = a launcher or a system window: not an activity, she says nothing.
TAILS = {"word": "writing", "steam": "", "epic games launcher": "",
         "riot client": "", "battle.net": "", "ea": "", "xbox": "", "file explorer": "", "task manager": "",
         "settings": "", "friends list": "", "program manager": ""}

# The program's file name without ".exe" -> category ("" = not an activity). This beats the title.
APPS = {"discord": "chat", "discordcanary": "chat", "discordptb": "chat", "slack": "chat", "telegram": "chat",
        "whatsapp": "chat", "signal": "chat", "ms-teams": "chat", "teams": "chat", "messenger": "chat",
        "code": "coding", "code - insiders": "coding", "cursor": "coding", "pycharm64": "coding", "idea64": "coding",
        "sublime_text": "coding", "notepad++": "coding", "devenv": "coding", "windowsterminal": "coding",
        "powershell": "coding", "pwsh": "coding", "cmd": "coding",
        "winword": "writing", "onenote": "writing", "obsidian": "writing", "notion": "writing",
        "spotify": "music", "applemusic": "music", "itunes": "music", "tidal": "music",
        "vlc": "video", "mpv": "video", "mpc-hc64": "video", "mpc-be64": "video", "potplayermini64": "video",
        "steam": "", "steamwebhelper": "", "epicgameslauncher": "", "riotclientux": "", "riotclientservices": "",
        "battle.net": "", "eadesktop": "", "galaxyclient": "", "explorer": "", "taskmgr": "", "systemsettings": "",
        "searchhost": "", "shellexperiencehost": "", "startmenuexperiencehost": "", "lockapp": ""}
BROWSER_APPS = ("chrome", "msedge", "firefox", "brave", "opera", "opera_gx", "vivaldi", "arc", "chromium", "zen",
                "librewolf", "waterfox", "safari")
GAME_APPS = ("valorant", "cs2", "r5apex", "r5apex_dx12", "overwatch", "league of legends", "rocketleague",
             "robloxplayerbeta", "minecraft.windows", "gta5", "gta5_enhanced", "eldenring", "terraria",
             "stardew valley", "osu!", "helldivers2", "cod", "destiny2", "dota2", "tslgame", "rainbowsix",
             "genshinimpact", "starrail", "zenlesszonezero", "geometrydash", "rustclient", "phasmophobia",
             "lethal company", "among us", "hollow knight", "celeste", "bg3", "bg3_dx11", "deadlock", "rdr2",
             "witcher3", "skyrimse", "fallout4", "starfield", "pathofexile", "wow", "ffxiv_dx11", "sekiro",
             "darksoulsiii", "forzahorizon5", "eurotrucks2", "factorio", "rimworldwin64", "subnautica", "nms",
             "escapefromtarkov", "balatro", "slaythespire", "vampiresurvivors", "undertale", "deltarune", "hades",
             "hades2", "peak", "repo", "content warning", "brawlhalla", "fallguys_client_game", "tf_win64", "hl2",
             "left4dead2", "portal2", "gmod", "aces", "dayz_x64", "ts4_x64", "ittakestwo", "cyberpunk2077")
GAME_APP_ENDINGS = ("-win64-shipping", "-wingdk-shipping", "-win64-shipping-eac")     # Unreal Engine games


def app_key(path):
    """'C:\\Games\\VALORANT-Win64-Shipping.exe' -> 'valorant-win64-shipping'. Only the file name is used."""
    name = (path or "").replace("\\", "/").rsplit("/", 1)[-1].strip().lower()
    return name[:-4] if name.endswith(".exe") else name


def is_game_app(app):
    a = app_key(app)
    return bool(a) and (a in GAME_APPS or a.endswith(GAME_APP_ENDINGS))


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


BROWSERS = ("google chrome", "microsoft edge", "mozilla firefox", "firefox", "brave", "opera", "opera gx", "vivaldi",
            "arc", "chromium", "safari", "zen browser", "librewolf")
SITES = ("youtube", "twitch", "reddit", "netflix", "tiktok", "twitter", "instagram", "facebook", "kick.com",
         "prime video", "crunchyroll", "fandom", "wiki")


def _segments(title):
    t = (title or "").lower().replace("\u2014", "-").replace("\u2013", "-")
    return [p.strip() for p in t.split(" - ") if p.strip()]


def is_web(title, app=""):
    """A browser tab or a video/social site? Then a game name in the title means you're WATCHING or READING
    about it ("Valorant clips - Twitch"), not playing."""
    if app_key(app) in BROWSER_APPS:
        return True
    t = (title or "").lower().strip()
    if not t:
        return False
    segs = _segments(t)
    return bool(segs and segs[-1] in BROWSERS) or any(s in t for s in SITES)


def _match(text, web):
    for cat, pats in _RULES:
        if web and cat in ("game", "cyberpunk"):
            continue
        if any(p.search(text) for p in pats):
            return cat
    return None


def classify(title, app=""):
    """One-word category for the front window, or None. `app` is the program's name when it's known.
    The program wins over the title, the app or site named at the end of the title wins over words before it,
    and in a browser / on a site, game names never count as playing."""
    t = (title or "").lower()
    a = app_key(app)
    if not t and not a:
        return None
    web = is_web(t, a)
    if a and not web:
        if is_game_app(a):
            return "cyberpunk" if a.startswith("cyberpunk") else "game"
        if a in APPS:
            return APPS[a] or None
    segs = [s for s in _segments(t) if s not in BROWSERS]
    if segs:
        last = segs[-1]                                   # the app ("... - Word") or the site ("... - YouTube")
        if not web:
            for name, cat in TAILS.items():
                if last == name or last.startswith(name + " "):
                    return cat or None
        hit = _match(last, web)
        if hit:
            return hit
    return _match(t, web)


def line(cat, rng):
    pool = LINES.get(cat)
    return rng.choice(pool) if pool else ""


def nudge(cat):
    return NUDGES.get(cat, "")
