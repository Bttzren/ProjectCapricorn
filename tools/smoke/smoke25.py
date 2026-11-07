import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab
capri.read_api_key = lambda: "sk-ant-x"
capri.llm_reply = lambda m, p, max_tokens=None, model=None: (time.sleep(0.6), "Yo choom, all good here.")[1]
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.root.update()
p.open_chat(); c = p.chat; c.win.geometry("420x520+10+10")
c.submit("hey capri how are you")
for _ in range(8): c.win.update(); time.sleep(0.05)
print("typing indicator shown:", c.typing_row is not None, "| status:", c.status.cget("text"))
t0 = time.time()
while time.time() - t0 < 5 and c.busy: c.win.update(); time.sleep(0.05)
for _ in range(20): c.win.update(); time.sleep(0.03)
print("typing gone:", c.typing_row is None, "| history roles:", [m["role"] for m in c.history][-2:], "| status:", c.status.cget("text"))
c.submit("/getbrain"); c.win.update()
c.pin_btn.config(text="x"); c.toggle_pin(); print("pin label:", c.pin_btn.cget("text"))
c.win.withdraw()
for name, fn in (("breach", p.open_breach), ("simon", p.open_simon)):
    fn(); p.root.update(); print(name, "opened ok")
capri.ReminderDialog(p); p.root.update(); print("reminder dialog ok")
p.set_neon("magenta"); p.open_settings(); p.root.update(); print("settings with magenta ok:", capri.ui.acc())
p.open_chat(); p.chat.win.update(); print("chat with magenta ok", p.chat.acc)
