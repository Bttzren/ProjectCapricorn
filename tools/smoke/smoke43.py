# 43: Settings jump bar — one click scrolls to each section
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.cancel_intro()
p.open_settings(); s = p.settings_win; w = s.win; w.geometry("470x600+10+10")
for _ in range(10): p.root.update(); time.sleep(0.03)
names = [n for n, _ in s.sections]; print("jump bar:", names)
labels = s.jumpbar.winfo_children()
for lbl in labels:
    lbl.event_generate("<Button-1>"); p.root.update(); time.sleep(0.03)
    # the section's title should now be near the top of the visible area
    frame = dict(s.sections)[lbl.cget("text")]
    top = frame.winfo_rooty() - s.canvas.winfo_rooty()
    print(f"{lbl.cget('text'):10s} -> view {s.canvas.yview()[0]:.3f}, section top at {top:4d}px", "OK" if -10 <= top <= 120 or s.canvas.yview()[1] >= 0.999 else "OFF")
labels[1].event_generate("<Button-1>"); p.root.update(); time.sleep(0.2); p.root.update()
ImageGrab.grab(bbox=(10, 10, 480, 610)).save("/tmp/settings_jump.png")
print("ok")
