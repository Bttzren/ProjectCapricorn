# 34: face close-up by the bubble and a cut-in, screenshotted from the real window; gating of cut-ins
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, expression
from PIL import ImageGrab, Image
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.choose_next = lambda: None
p.fx, p.fy = 400.0, float(p.ground()); p.go("idle", 99)
def pump(secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        p._tick(); p.root.update(); time.sleep(0.02)
def shot(path):
    x, y = p.root.winfo_rootx(), p.root.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + p.Wd, y + p.Hd)).save(path)
pump(0.3)
p.say("Nice tabs. Very organized. Kind of.", 6, speak=None); p.express("smug", forced=True); pump(1.0); shot("/tmp/face_smug.png")
p.expr = None; pump(0.1)
p.say("lol that's tragic", 6, speak=None); p.express("laugh", forced=True); pump(0.45); shot("/tmp/cutin_laugh.png")
print("cut-in on screen:", p.cutin is not None)
pump(1.0); print("cut-in gone after ~1.1 s:", p.cutin is None)
p.expr = None; p.expr_gate = expression.Gate(); p.express("laugh"); print("second laugh within 5 min -> cut-in:", p.cutin is not None)
p.expr = None; p.settings["cutins"] = False; p.express("surprised", forced=True); print("cut-ins off -> cut-in:", p.cutin is not None)
a = Image.open("/tmp/face_smug.png"); print("shots:", a.size)
print("ok")
