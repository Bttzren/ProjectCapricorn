# 39: Settings / chat scrolling, including the Windows case where the wheel goes to the FOCUSED window (the pet)
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda: ""
print("wheel_steps:", [capri.wheel_steps(d) for d in (120, -120, 240, -360, 15, -7, 0)])
p = capri.Capri(); p.boot = None; p.cancel_intro()
def pump(n=8):
    for _ in range(n): p.root.update(); time.sleep(0.02)
p.open_settings(); s = p.settings_win; pump()
cx, cy = s.canvas.winfo_rootx() + 100, s.canvas.winfo_rooty() + 100
def wheel_from(widget, delta):
    b = s.canvas.yview()[0]
    widget.event_generate("<MouseWheel>", delta=delta, rootx=cx, rooty=cy, x=1, y=1)
    pump(4); return round(b, 3), round(s.canvas.yview()[0], 3)
print("wheel delivered to the PET window, pointer over settings:", wheel_from(p.canvas, -120))
print("wheel on a deep settings label:", wheel_from(s.win.winfo_children()[-1], -120))
print("wheel up:", wheel_from(p.canvas, 120))
b = s.canvas.yview()[0]; s.win.event_generate("<Next>"); pump(4); print("PageDown:", round(b, 3), "->", round(s.canvas.yview()[0], 3))
s.win.event_generate("<End>"); pump(4); print("End -> bottom:", round(s.canvas.yview()[1], 3))
s.win.event_generate("<Home>"); pump(4); print("Home -> top:", round(s.canvas.yview()[0], 3))
# pointer over the pet itself: nothing scrolls
px, py = p.canvas.winfo_rootx() + 5, p.canvas.winfo_rooty() + 5
b = s.canvas.yview()[0]; p.canvas.event_generate("<MouseWheel>", delta=-120, rootx=px, rooty=py); pump(4)
print("pointer over the pet -> settings unchanged:", s.canvas.yview()[0] == b)
# chat still scrolls
p.open_chat(); c = p.chat; c.win.geometry("400x300+600+20")
for i in range(30): c.system_line(f"line {i}")
pump(10); c.canvas.yview_moveto(1.0); pump()
qx, qy = c.canvas.winfo_rootx() + 50, c.canvas.winfo_rooty() + 50
b = c.canvas.yview()[0]; p.canvas.event_generate("<MouseWheel>", delta=120, rootx=qx, rooty=qy); pump(4)
print("chat wheel up:", round(b, 3), "->", round(c.canvas.yview()[0], 3))
print("ok")
