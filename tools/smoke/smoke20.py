import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, hands, launcher
from PIL import ImageGrab
calls = []
class BE:
    def __getattr__(self, n): return lambda *a, **k: calls.append((n,) + a)
hands.make_backend = lambda *a, **k: BE()
capri.read_api_key = lambda: ""
launcher.index_apps = lambda *a, **k: {"discord": "Discord.lnk", "spotify": "Spotify.lnk"}
opened = []
launcher.opener = lambda kind, target, *a, **k: (lambda: opened.append((kind, target)))
said = []
capri.Capri.say_moment = lambda self, sit, fb, *a, **k: said.append((sit, fb))
p = capri.Capri(); p.cancel_intro(); p.root.update()
p.open_chat(); lines = []
p.chat.system_line = lambda t, err=False: lines.append(t)
p.hands.set_level("media")
for c in ["/open discord", "/open youtube", "/search best valorant crosshair", "/open flurbnorp", "/desktop"]:
    p.chat.submit(c)
for _ in range(10): p.root.update()
print("opened:", opened)
print("media-level desktop (needs full):", [l for l in lines if "Full" in l or "full" in l][-1:])
# voice path
p.heard_events.put(("heard", "Hey Capri next song", "wake")); p.heard_events.put(("heard", "open spotify", "wake"))
p.heard_events.put(("heard", "volume up", "wake"))
for _ in range(10): p.root.update(); time.sleep(0.02)
print("backend calls:", [c for c in calls if c[0] in ("media",)], "| opened:", opened[-1])
# brief
p.todos.add("finish homework"); p.habits.add("drink water"); p.add_reminder(25, "call mom")
p.chat.submit("/brief")
print("brief lines:", [l for l in lines if l.startswith(("To-dos", "Habits", "Next"))]); print("brief moment:", said[-1][0][:140])
# neon render
p.hands.set_level("full"); p.set_neon("cyan")
for _ in range(10): p.root.update(); time.sleep(0.03)
x, y = p.root.winfo_rootx(), p.root.winfo_rooty()
ImageGrab.grab(bbox=(x, y, x + p.Wd, y + p.Hd)).save("/tmp/neon_idle.png")
p.state = "fly"; p.fvx, p.fvy = 900.0, 0.0
import math
for i in range(30):
    p.fx += 14; p.root.update(); p.draw(time.time()); time.sleep(0.02)
x, y = p.root.winfo_rootx(), p.root.winfo_rooty()
ImageGrab.grab(bbox=(x, y, x + p.Wd, y + p.Hd)).save("/tmp/neon_fly.png")
print("ghosts cached:", len(p.ghost_cache))
