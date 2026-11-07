# 35: mini face — chat avatar (talking / thinking / mad) and tiny mode on the desktop (auto during focus)
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab, Image
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None
p.fx, p.fy = 400.0, float(p.ground()); p.go("idle", 99)
def pump(secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        p._tick(); p.root.update(); time.sleep(0.02)
t0 = time.time(); ok = capri.MINI_FACES.load(); print("mini faces:", ok, "load s:", round(time.time() - t0, 2), sorted(capri.MINI_FACES.src))
p.open_chat(); c = p.chat; c.win.geometry("420x200+10+700"); pump(0.4)
p.talk_until = time.time() + 3; pump(0.5)
x, y = c.portrait.winfo_rootx(), c.portrait.winfo_rooty()
ImageGrab.grab(bbox=(x - 4, y - 4, x + c.portrait.winfo_width() + 4, y + c.portrait.winfo_height() + 4)).save("/tmp/mini_chat.png")
print("chat avatar size:", c.portrait.winfo_width(), c.portrait.winfo_height())
c.win.withdraw()
print("tiny before focus:", p.tiny_on()); p.start_focus(25); print("tiny during focus (auto):", p.tiny_on())
p.say("Focus. I'll be small.", 5, speak=None); pump(0.6)
wx, wy = p.root.winfo_rootx(), p.root.winfo_rooty()
ImageGrab.grab(bbox=(wx, wy, wx + p.Wd, wy + p.Hd)).save("/tmp/tiny.png")
img = p.pil_cache.get(p._last_ck); print("tiny frame:", img.size if img else None, "alpha:", sorted(set(img.getchannel("A").getdata())) if img else None)
p.express("laugh", forced=True); pump(0.3); print("tiny + laugh -> cut-in:", p.cutin is not None)
p.set_tiny("off"); print("tiny off during focus:", p.tiny_on())
print("ok")
