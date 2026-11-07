# 40: /see on (one switch), glance on app switch with a fake vision AI, privacy/calm gates, Settings button
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
from tkinter import messagebox
dialogs = []
messagebox.askyesno = lambda title, msg, **k: (dialogs.append(title), True)[1]
import capri, ledges
from PIL import Image, ImageGrab
capri.read_api_key = lambda: "sk-ant-x"
asked = []
capri.vision_ask = lambda system, mt, b64, q, n=120, model=None, room=1, **k: (asked.append(q), "DOING: watching a Minecraft speedrun on YouTube SAY: Those runners are unreal.")[1]
capri.llm_reply = lambda *a, **k: "Nice."
ledges.capture = lambda: Image.new("RGB", (800, 450), (20, 20, 30))
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None; p.go("idle", 99)
p.open_chat(); c = p.chat
lines = []
orig = c.system_line
c.system_line = lambda t, err=False: (lines.append(t), orig(t, err))[0]
c.submit("/see on"); print(lines[-1]); print("explainers shown (once each):", dialogs)
print("settings:", {k: p.settings.get(k) for k in ("ledges", "ai_vision", "glance")}, "aware:", p.aware)
def pump(s):
    t0 = time.time()
    while time.time() - t0 < s:
        p.root.update(); p._tick(); time.sleep(0.02)
p.ctx = "video"; p.react_context("video"); pump(0.8)
print("asked the AI:", "DOING:" in asked[-1], "| she said:", repr(p.bubble), "| activity for chat:", repr(p.activity_phrase()))
# periodic looks: every N s (default 10), silent while the activity is the same, speaks when it changes
print("look every (default):", p.look_every())
said = []
orig_say = p.say
p.say = lambda text, *a, **k: (said.append(text), orig_say(text, *a, **k))[1]
ledges.capture = lambda: Image.new("RGB", (800, 450), (120, 40, 90))      # screen changed, same activity
p.glance_gate.last -= 11; p.glance_tick(time.time()); pump(0.6)
print("periodic look, same activity -> spoke:", said, "| looks so far:", len(asked))
p.glance_gate.last -= 11; p.glance_tick(time.time()); pump(0.6)
print("same screen again -> sent to AI:", len(asked), "(2 = unchanged screen skipped)")
capri.vision_ask = lambda system, mt, b64, q, n=120, model=None, room=1, **k: (asked.append(q), "DOING: coding a Python desktop pet in VS Code SAY: Is that me in there?")[1]
ledges.capture = lambda: Image.new("RGB", (800, 450), (200, 200, 230))
p.glance_gate.last -= 11; p.glance_tick(time.time()); pump(0.6)
print("activity changed -> spoke:", said[-1:], "| activity:", p.activity_phrase())
p.open_chat(); p.chat.submit("/see every 1"); p.chat.submit("/see every 500"); print("/see every 500 ->", p.look_every())
p.chat.submit("/see every 10")
p.glance_gate.last = -1e9; p.calm = True; print("calm -> glance:", p.glance("coding")); p.calm = False
p.win32.ok = True; p.win32.foreground_title = lambda: "Online Banking - Google Chrome"; p.win32.idle_seconds = lambda: 1.0
print("banking window -> glance:", p.glance("coding"))
p.win32.foreground_title = lambda: "main.py - VS Code"; p.win32.idle_seconds = lambda: 500.0
print("away from PC -> glance:", p.glance("coding")); p.win32.ok = False
c.submit("/see"); print(lines[-1])
n = len(dialogs); c.submit("/see off"); c.submit("/see on"); print("off then on again -> new explainers:", dialogs[n:])
c.win.withdraw(); p.open_settings(); w = p.settings_win.win; w.geometry("470x420+10+10"); pump(0.5)
ImageGrab.grab(bbox=(10, 10, 480, 430)).save("/tmp/settings_see.png")
print("ok")
