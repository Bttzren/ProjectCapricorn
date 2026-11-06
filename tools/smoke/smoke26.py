import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.root.update()
print("neon:", p.neon_name, "| outline:", p.outline_on(), "| ui accent:", capri.ui.acc())
p.say("Yo choom, no more blue outline. Promise.", 20, speak=None)
for _ in range(25): p.root.update(); time.sleep(0.03)
x, y = p.root.winfo_rootx(), p.root.winfo_rooty()
ImageGrab.grab(bbox=(x, y, x + p.Wd, y + p.Hd)).save("/tmp/pet_clean.png")
p.set_neon("cyan"); p.settings["outline"] = True; p.clear_sprite_caches()
for _ in range(10): p.root.update(); time.sleep(0.03)
print("opt-in outline works:", p.outline_on())
