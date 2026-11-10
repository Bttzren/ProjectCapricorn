# 49: awareness by program name — a fake Windows layer feeds (title, program); she must get the activity right
# and only start game mode for a game that is really being played
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda *a, **k: ""
p = capri.Capri(); p.boot = None; p.cancel_intro()
front = {"title": "", "app": ""}
w = p.win32
w.ok = True
w.foreground_title = lambda: front["title"]
w.foreground_app = lambda: capri.awareness.app_key(front["app"])
w.idle_seconds = lambda: 1.0
w.foreground = lambda: None
w.work_area = lambda: None
p.aware = True; p.settings["aware_notice"] = True
import meeting
meeting.read_mic_entries = lambda: []
said = []
orig_say = p.say
def say(text, *a, **k):
    said.append(text); return orig_say(text, *a, **k)
p.say = say
def show(title, app, secs=1.2):
    front.update(title=title, app=app); p.next_watch = 0; t = time.time()
    while time.time() - t < secs:
        p.next_watch = 0; p._tick(); p.root.update(); time.sleep(0.02)
    return p.ctx, (p.game.key if p.game else None)
ok = True
cases = [
    ("#valorant | The Boys - Discord", r"C:\Users\x\AppData\Local\Discord\app-1.0\Discord.exe", "chat", None),
    ("Steam", r"C:\Program Files (x86)\Steam\steamwebhelper.exe", None, None),
    ("VALORANT clips - Twitch - Google Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe", "video", None),
    ("valorant", r"C:\Windows\explorer.exe", None, None),
    ("Daft Punk - One More Time", r"C:\Users\x\AppData\Roaming\Spotify\Spotify.exe", "music", None),
    ("Palworld", r"D:\SteamLibrary\Palworld\Pal\Binaries\Win64\Palworld-Win64-Shipping.exe", "game", None),
    ("", r"C:\Riot Games\VALORANT\live\ShooterGame\Binaries\Win64\VALORANT-Win64-Shipping.exe", "game", "valorant"),
]
tiny_log = []
for title, app, want_ctx, want_game in cases:
    ctx, game = show(title, app)
    tiny_log.append(p.tiny_on())
    good = ctx == want_ctx and game == want_game
    ok = ok and good
    print(("ok   " if good else "FAIL ") + f"{title[:34]!r:38} {capri.awareness.app_key(app):28} -> {ctx}, game mode: {game}")
# tiny mode "auto": off for chat/store/video/music, on for ANY game (Palworld has no game mode), and it stays on
# for a moment when you alt-tab away
print("tiny per case:", tiny_log)
ok = ok and tiny_log == [False, False, False, False, False, True, True]
p.end_game(quiet=True); show("general - Discord", "Discord.exe", 0.6); print("alt-tab to Discord, still tiny:", p.tiny_on())
ok = ok and p.tiny_on()
p.played_at -= 100; print("two minutes later:", p.tiny_on()); ok = ok and not p.tiny_on()
print("she said:", [s[:50] for s in said][-3:])
for attr in ("ctx", "seen"):
    v = getattr(p, attr)
    assert "discord" not in str(v).lower() and "palworld" not in str(v).lower(), "title/program kept in " + attr
import json
saved = json.dumps(p.settings).lower() + open(os.path.join(home, ".capri", "capri.log")).read().lower()
leak = [w_ for w_ in ("the boys", "daft punk", "palworld", "steamwebhelper", "spotify.exe") if w_ in saved]
print("titles/programs in settings or log:", leak or "none")
sys.exit(0 if ok and not leak else 1)
