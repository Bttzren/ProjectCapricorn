# 36: launch intro — plays on first launch with the new skin, frames advance, rises/drops, pet hidden, then greets
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, intro
from PIL import ImageGrab
greets = []
capri.Capri.greet = lambda self: greets.append(time.time())
capri.read_api_key = lambda: ""
t0 = time.time(); p = capri.Capri(); print("startup incl. intro load s:", round(time.time() - t0, 2))
print("intro playing:", bool(p.intro), "| beam boot:", bool(p.boot))
it = p.intro; W, H = it["W"], it["H"]; seen = []; shot = False
while p.intro and time.time() - it["t0"] < intro.DURATION + 1:
    p._tick(); p.root.update()
    if it["stem"] and (not seen or seen[-1] != it["stem"]): seen.append(it["stem"])
    if not shot and it["stem"] == "intro-wave2":
        x, y = it["win"].winfo_rootx(), it["win"].winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + W, y + H)).save("/tmp/intro_wave.png"); shot = True
        print("pet canvas items while intro plays:", len(p.canvas.find_all()))
    time.sleep(0.02)
print("frames seen:", seen[:4], "...", seen[-2:], "| count:", len(seen))
print("finished:", p.intro is None, "| greeted:", len(greets), "| booted:", p.settings.get("booted"))
p.settings["skin"] = "classic"; print("classic skin -> intro_ok:", p.intro_ok())
p.settings["skin"] = "capri"; p.settings["intro"] = False; print("intro off -> intro_ok:", p.intro_ok())
print("ok")
