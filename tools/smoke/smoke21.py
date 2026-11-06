import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab, Image
greets = []
capri.Capri.greet = lambda self: greets.append(time.time())
capri.read_api_key = lambda: ""
p = capri.Capri()
print("boot started:", bool(p.boot), "first:", p.boot["first"], "dur:", p.boot["dur"], "booted flag before:", p.settings.get("booted"))
p.root.update()
frames = []
D = p.boot["dur"]
for f in (0.10, 0.22, 0.40, 0.52, 0.66, 0.80, 0.90):
    p.boot["t0"] = time.time() - f * D
    p.update_boot(time.time()) if False else None
    p.draw(time.time()); p.root.update()
    x, y = p.root.winfo_rootx(), p.root.winfo_rooty()
    frames.append(ImageGrab.grab(bbox=(x, y, x + p.Wd, y + p.Hd)))
W, H = frames[0].size
sheet = Image.new("RGB", (W * 4 + 30, H * 2 + 10), (40, 40, 60))
for i, fr in enumerate(frames): sheet.paste(fr, ((i % 4) * (W + 10), (i // 4) * (H + 10)))
sheet.save("/tmp/boot_sheet.png"); print("sheet", sheet.size)
# let it run to completion in real time
p.boot["t0"] = time.time() - D + 0.5
t0 = time.time()
while p.boot and time.time() - t0 < 5: p.root.update(); time.sleep(0.03)
print("finished:", p.boot is None, "booted flag:", p.settings.get("booted"), "greeted:", len(greets))
# second launch style: replay via command, skip by poking
p.start_boot(first=False, greet=False); print("replay running:", bool(p.boot), "dur", p.boot["dur"])
p.finish_boot(skipped=True); print("skipped ok:", p.boot is None, "greets still", len(greets))
# setting off -> no boot
p.settings["boot_anim"] = False
