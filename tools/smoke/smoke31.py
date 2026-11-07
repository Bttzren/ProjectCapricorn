# 31: no "are you sure?" popups — tasks/typing never ask; mic/screen features explain once, ever
import os, sys, tempfile, json
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
from tkinter import messagebox
dialogs = []
messagebox.askyesno = lambda title, msg, **k: (dialogs.append(title), True)[1]
import capri, agent
capri.read_api_key = lambda: "sk-ant-x"
p = capri.Capri(); p.boot = None; p.root.update()
p.hands.level = "full"; p.settings["hands"] = "full"
print("enable tasks 1st:", p.enable_agent(), dialogs[-1:]); n = len(dialogs)
p.settings["agent"] = False; print("enable tasks 2nd:", p.enable_agent(), "| new dialogs:", dialogs[n:])
agent.Agent.run = lambda self, task: ("done", "ok")
n = len(dialogs); ok, why = p.start_agent("open notepad and type hello")
print("start task:", ok, "| dialogs:", dialogs[n:], "| bubble:", p.bubble[:60])
print("typing approved without popup:", p._agent_typing("type", "hello"), "| dialogs:", dialogs[n:])
n = len(dialogs)
for key in ("ledges", "vision", "hear"):
    getattr(p, "enable_" + key)()
    p.settings[{"vision": "ai_vision"}.get(key, key)] = False
    getattr(p, "enable_" + key)()
print("ledges/vision/hear on twice each -> dialogs:", dialogs[n:])
n = len(dialogs); p.apply_preset("full"); p.apply_preset("none", ask=True); p.apply_preset("full")
print("preset full twice -> dialogs:", dialogs[n:])
# a user who already had things on before this update: no dialog at all
home2 = tempfile.mkdtemp(); os.environ["HOME"] = home2; os.environ["APPDATA"] = home2
os.makedirs(capri.data_dir(), exist_ok=True)
json.dump({"agent": True, "hands": "full", "ledges": True, "hear": True}, open(os.path.join(capri.data_dir(), "settings.json"), "w"))
q = capri.Capri(); q.boot = None
n = len(dialogs); q.settings["agent"] = False; q.enable_agent(); q.enable_ledges()
print("existing user re-enabling -> dialogs:", dialogs[n:], "| consented:", sorted(q.settings["consented"]))
print("ok")
