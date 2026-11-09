# 44: sit on stuff — a real window on the (virtual) screen, she finds its top edge, flies over, perches; where is she?
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
import capri, tkinter as tk
from PIL import ImageGrab, Image
capri.read_api_key = lambda: ""
capri.llm_reply = lambda *a, **k: "Nice."
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None
# a window-like box from ANOTHER program (her own windows are ignored on purpose): top edge at y=700
import subprocess
other = subprocess.Popen([sys.executable, "-c", """
import sys, tkinter as tk
r = tk.Tk(); r.overrideredirect(True); r.geometry("640x320+320+700"); r.configure(bg="#2b2f3a")
tk.Frame(r, bg="#d0d4e0", height=28).pack(fill="x"); tk.Label(r, text="Some app", bg="#2b2f3a", fg="white").pack()
r.after(int(sys.argv[1]) * 1000, lambda: r.geometry("640x320+320+600"))   # the window moves up 100 px
r.after(int(sys.argv[2]) * 1000, r.destroy); r.mainloop()
""", "22", "34"])
time.sleep(1.5)
def pump(s):
    t0 = time.time()
    while time.time() - t0 < s:
        p.root.update(); p._tick(); time.sleep(0.03)
pump(0.5)
p.enable_ledges(); pump(6)
print("ledges found:", [(int(d["l"]), int(d["t"]), int(d["r"]), d["kind"]) for d in p.ledges][:4])
p.sit_somewhere(quiet=True)
seated, t0 = 0.0, time.time()
while time.time() - t0 < 12:                     # several ledge scans happen while she sits
    p.root.update(); p._tick(); time.sleep(0.03)
    if p.state == "perch" and p.surf: seated += 0.03
print("seated for about", round(seated, 1), "s of 12 (scans every ~2.5 s)")
x, y = p.root.winfo_rootx(), p.root.winfo_rooty()
ImageGrab.grab(bbox=(x, y, x + p.Wd, y + p.Hd + 40)).save("/tmp/perch.png")
t0 = time.time()                                   # the window moves up at ~22 s after it opened
while time.time() - t0 < 12:
    p.root.update(); p._tick(); time.sleep(0.03)
print("after the window moved up to y=600 -> state:", p.state, "| feet y:", round(p.fy), "| surf:", p.surf)
t0 = time.time()                                   # ...and closes at ~34 s
while time.time() - t0 < 10:
    p.root.update(); p._tick(); time.sleep(0.03)
print("after the window closed -> state:", p.state, "| feet y:", round(p.fy), "(ground is", p.ground(), ")")
print("state:", p.state, "| surf:", p.surf, "| feet y:", round(p.fy), "| drawn pose:", p._last_ck and p._last_ck[0][0])
shot = Image.open("/tmp/perch.png"); x, y = 0, 0
# lowest pixel of her body (her colours are saturated pink/green) relative to the box's top edge
px = shot.load(); low = None
for yy in range(shot.height - 1, -1, -1):
    if any((lambda c: (c[0] > 180 and c[1] < 90) or (c[1] > 180 and c[0] < 90))(px[xx, yy]) for xx in range(0, shot.width, 2)):
        low = y + yy; break
print("lowest coloured pixel in the seated shot (window-relative):", low)
other.kill()
print("ok")
