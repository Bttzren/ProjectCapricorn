import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import ImageGrab
capri.read_api_key = lambda: "sk-ant-x"
capri.llm_reply = lambda msgs, persona, max_tokens=None, model=None: "Hello friend, how are you?"
p = capri.Capri(); p.root.update()
p.open_chat(); bubbles = []
p.chat.add_bubble = lambda role, text, animate=False: bubbles.append((role, text))
p.root.clipboard_clear(); p.root.clipboard_append("Hola amigo")
p.chat.submit("/clip translate english")
t0 = time.time()
while time.time() - t0 < 5 and not bubbles: p.root.update(); time.sleep(0.05)
print("clip bubble:", bubbles)
p.chat.win.withdraw()
p.open_settings(); w = p.settings_win.win
w.geometry("460x1100+0+0"); w.update(); time.sleep(0.5); w.update()
ImageGrab.grab(bbox=(0, 0, 470, 1100)).save("/tmp/settings_top.png")
print("saved")
