import os, sys, tempfile, json, time
os.environ["HOME"] = tempfile.mkdtemp(); os.environ["APPDATA"] = os.environ["HOME"]
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, hands, agent
from tkinter import messagebox
from PIL import Image
calls, said, asked_dialogs = [], [], []
class BE:
    def __getattr__(self, n):
        return lambda *a, **k: calls.append((n,) + a)
hands.make_backend = lambda *a, **k: BE()
messagebox.askyesno = lambda title, msg, **k: (asked_dialogs.append(title), True)[1]
capri.read_api_key = lambda: "sk-ant-fake"
capri.ledges.capture = lambda: Image.new("RGB", (1920, 1080), "black")
script = iter([json.dumps(d) for d in [
    {"action": "key", "keys": "win"}, {"action": "type", "text": "discord"}, {"action": "key", "keys": "enter"},
    {"action": "click", "x": 640, "y": 360}, {"action": "type", "text": "He will be in 15 minutes"},
    {"action": "done", "summary": "Told your friends."}]])
capri.vision_ask = lambda system, mt, b64, prompt, mx=120, model=None: next(script)
capri.Capri.say_moment = lambda self, sit, fb, *a, **k: said.append((sit, fb))
p = capri.Capri(); p.cancel_intro()
p.open_chat()
lines = []
p.chat.system_line = lambda t, err=False: lines.append(t)
p.chat.submit("/do open discord")          # not ready: needs full + agent
p.hands.set_level("full")
p.chat.submit("/do open discord")
p.settings["agent"] = True
p.chat.submit("/do open discord and tell them I'll be in in 15")
t0 = time.time()
while time.time() - t0 < 30 and not any(l.startswith(("Done", "Stopped")) for l in lines):
    p.root.update(); time.sleep(0.05)
print("\n".join(lines))
print("dialogs:", asked_dialogs)
print("calls:", [c for c in calls if c[0] in ("click","move","type_text","press")])
print("said:", said[-1:])
print("agent cleared:", p.agent is None)
