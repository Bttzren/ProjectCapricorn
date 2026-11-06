import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, listen
from tkinter import messagebox
dialogs = []
messagebox.askyesno = lambda title, msg, **k: (dialogs.append((title, msg)), True)[1]
capri.read_api_key = lambda: ""
listen.installed = lambda: True
installed = []
p = capri.Capri()
p.start_wake = lambda: installed.append("wake") or True
p.root.update()
w0, h0 = p.fw, p.fh
print("base size", w0, h0, "canvas", p.Wd, p.Hd)
p.open_chat(); lines = []
p.chat.system_line = lambda t, err=False: lines.append(t)
p.chat.submit("/size huge"); p.root.update()
print("huge:", p.fw, p.fh, "scale", p.size_now)
p.chat.submit("/size tiny"); p.root.update()
print("tiny:", p.fw, p.fh, p.size_now)
p.chat.submit("/size bigger"); p.root.update(); print("bigger from tiny:", p.size_now)
for _ in range(15): p.root.update(); time.sleep(0.02)   # draw frames at new size
# auto size shrinks while gaming
p.set_size(1.0, announce=False); base = p.size_now
import gamemode; p.game = gamemode.Session("valorant"); p.apply_size(); print("gaming:", base, "->", p.size_now); p.game = None; p.apply_size(); print("after game:", p.size_now)
p.set_auto_size(False); p.game = gamemode.Session("valorant"); p.apply_size(); print("auto off while gaming:", p.size_now); p.game = None
# presets
import presets
print("start:", presets.detect(p.settings))
p.chat.submit("/preset full")
print("dialog title:", dialogs[-1][0]); print("full ->", presets.detect(p.settings), "hands", p.hands.level, "wake started:", installed)
p.chat.submit("/powers")
p.chat.submit("/preset none")
print("none ->", presets.detect(p.settings), "hands", p.hands.level, "dialogs total", len(dialogs))
p.start_listening(); print("push-to-talk blocked msg ok")
p.settings["agent"] = True; print("custom ->", presets.detect(p.settings))
p.chat.submit("/preset some"); print("some ->", presets.detect(p.settings), p.hands.level)
# settings window renders
p.open_settings(); p.root.update(); print("settings opened:", p.settings_win.win.winfo_exists())
p.apply_preset("full", ask=False); 
for _ in range(15): p.root.update(); time.sleep(0.03)
print("reopened after preset:", p.settings_win is not None and p.settings_win.win.winfo_exists())
# clip
p.root.clipboard_clear(); p.root.clipboard_append("Hola amigo, como estas?")
capri.llm_reply = lambda msgs, persona, max_tokens=None, model=None: "Hello friend, how are you?"
capri.read_api_key = lambda: "sk-ant-x"
p.chat.submit("/clip translate english")
t0 = time.time()
while time.time() - t0 < 5 and p.clip_events.empty() and not any("Hello friend" in str(l) for l in lines): p.root.update(); time.sleep(0.05)
for _ in range(10): p.root.update()
print("lines tail:", [l for l in lines if "clipboard" in l.lower() or "Hello" in l][-2:])
print("ok")
