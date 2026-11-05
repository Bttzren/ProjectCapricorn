"""Open apps and websites by name ("open Discord", "go to YouTube", "search for ...") without any AI.

She indexes the Start Menu shortcuts (Windows), /Applications (Mac) or .desktop files (Linux), matches what you
said against those names and opens the shortcut. Websites come from a small fixed list; searches go to Google
with your words URL-encoded. She only ever opens things from the index, the fixed list, or a search URL she
built herself, never a command line or path that came from speech.
"""
import difflib
import os
import re
import subprocess
import sys
import urllib.parse
import webbrowser

SITES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com", "gmail": "https://mail.google.com",
    "github": "https://github.com", "reddit": "https://www.reddit.com", "twitch": "https://www.twitch.tv",
    "twitter": "https://x.com", "x": "https://x.com", "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com", "discord": "https://discord.com/app", "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com", "chatgpt": "https://chatgpt.com", "claude": "https://claude.ai",
    "wikipedia": "https://www.wikipedia.org", "amazon": "https://www.amazon.com", "tiktok": "https://www.tiktok.com",
    "instagram": "https://www.instagram.com", "drive": "https://drive.google.com",
    "google drive": "https://drive.google.com", "google docs": "https://docs.google.com",
    "calendar": "https://calendar.google.com", "google calendar": "https://calendar.google.com",
    "steam": "https://store.steampowered.com", "crunchyroll": "https://www.crunchyroll.com",
    "disney plus": "https://www.disneyplus.com", "prime video": "https://www.primevideo.com",
}
SEARCH = {"google": "https://www.google.com/search?q=", "youtube": "https://www.youtube.com/results?search_query=",
          "wikipedia": "https://en.wikipedia.org/w/index.php?search=", "maps": "https://www.google.com/maps/search/",
          "github": "https://github.com/search?q=", "reddit": "https://www.reddit.com/search/?q="}
# built-in Windows tools (opened by their fixed names)
WINDOWS_SYSTEM = {"notepad": "notepad.exe", "calculator": "calc.exe", "calc": "calc.exe", "paint": "mspaint.exe",
                  "settings": "ms-settings:", "file explorer": "explorer.exe", "explorer": "explorer.exe",
                  "files": "explorer.exe"}
SKIP = re.compile(r"uninstall|readme|read me|help|documentation|release notes|license|website|manual|\bsetup\b", re.I)
FILLER = re.compile(r"\b(the|my|app|application|program|please|for me|up|on my computer|on my pc)\b", re.I)


def clean_name(text):
    t = FILLER.sub(" ", (text or "").lower())
    return " ".join(re.sub(r"[^a-z0-9+ ]", " ", t).split())


# ------------------------------------------------------------------ what is installed
def start_menu_roots(env=os.environ):
    roots = []
    for var in ("ProgramData", "APPDATA"):
        base = env.get(var)
        if base:
            roots.append(os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs"))
    return roots


def index_apps(platform=None, roots=None, listdir=os.walk):
    """{lowercase name: path or id} of things she may open on this computer."""
    platform = platform or sys.platform
    out = {}
    if platform.startswith("win"):
        for root in roots if roots is not None else start_menu_roots():
            for folder, _dirs, files in listdir(root):
                for f in files:
                    stem, ext = os.path.splitext(f)
                    if ext.lower() in (".lnk", ".url") and not SKIP.search(stem):
                        out.setdefault(clean_name(stem), os.path.join(folder, f))
        for name, cmd in WINDOWS_SYSTEM.items():
            out.setdefault(name, cmd)
    elif platform == "darwin":
        for root in roots if roots is not None else ("/Applications", os.path.expanduser("~/Applications"),
                                                      "/System/Applications"):
            try:
                for f in os.listdir(root):
                    if f.endswith(".app"):
                        out.setdefault(clean_name(f[:-4]), f[:-4])
            except OSError:
                continue
    else:
        for root in roots if roots is not None else ("/usr/share/applications",
                                                      os.path.expanduser("~/.local/share/applications")):
            try:
                for f in os.listdir(root):
                    if f.endswith(".desktop"):
                        out.setdefault(clean_name(f[:-8].split(".")[-1]), f)
            except OSError:
                continue
    out.pop("", None)
    return out


# ------------------------------------------------------------------ understanding the request
def parse_open(text):
    """('open', name) | ('search', query, engine) | None from what the user said or typed."""
    t = " ".join((text or "").split()).strip(" .!?")
    low = t.lower()
    m = re.match(r"(?:search|look up|google)\s+(youtube|google|wikipedia|maps|github|reddit)\s+for\s+(.+)", low)
    if m:
        return ("search", t[len(low) - len(m.group(2)):], m.group(1))
    m = re.match(r"(?:search|look up|google|find)\s+(?:for\s+|up\s+)?(.+?)\s+on\s+(youtube|google|wikipedia|maps|github|reddit)$", low)
    if m:
        return ("search", t[low.index(m.group(1)):low.index(m.group(1)) + len(m.group(1))], m.group(2))
    m = re.match(r"(?:search|look up|google)\s+(?:for\s+|up\s+)?(.+)", low)
    if m:
        return ("search", t[len(low) - len(m.group(1)):], "google")
    m = re.match(r"(?:open|launch|start|run|go to|goto|pull up|bring up)\s+(.+)", low)
    if m:
        name = clean_name(m.group(1))
        return ("open", name) if name and len(name.split()) <= 4 else None
    return None


def match(name, apps, sites=SITES, cutoff=0.78):
    """('app', name, target) | ('site', name, url) | None. Installed apps beat websites."""
    q = clean_name(name)
    if not q:
        return None
    if q in apps:
        return ("app", q, apps[q])
    if q in sites:
        return ("site", q, sites[q])
    starts = [k for k in apps if k.startswith(q + " ") or k.startswith(q)]
    if starts and len(q) >= 3:
        k = min(starts, key=len)
        return ("app", k, apps[k])
    words = set(q.split())
    inside = [k for k in apps if words <= set(k.split())]            # "chrome" -> "google chrome"
    if inside and len(q) >= 3:
        k = min(inside, key=len)
        return ("app", k, apps[k])
    close = difflib.get_close_matches(q, list(apps), n=1, cutoff=cutoff)
    if close:
        return ("app", close[0], apps[close[0]])
    close = difflib.get_close_matches(q, list(sites), n=1, cutoff=cutoff)
    if close:
        return ("site", close[0], sites[close[0]])
    return None


def search_url(query, engine="google"):
    base = SEARCH.get(engine, SEARCH["google"])
    return base + urllib.parse.quote_plus(" ".join((query or "").split())[:200])


# ------------------------------------------------------------------ doing it
def opener(kind, target, platform=None, startfile=None, popen=subprocess.Popen, webopen=webbrowser.open):
    """A zero-argument function that opens `target`. kind is 'app' or 'site'. Raises ValueError for a bad URL."""
    platform = platform or sys.platform
    if kind == "site":
        if not target.startswith(("https://", "http://")):
            raise ValueError("not a web address")
        return lambda: webopen(target)
    if platform.startswith("win"):
        sf = startfile or getattr(os, "startfile", None)
        if sf is None:
            raise ValueError("can't open apps here")
        return lambda: sf(target)
    if platform == "darwin":
        return lambda: popen(["open", "-a", target])
    return lambda: popen(["gtk-launch", target.replace(".desktop", "")])
