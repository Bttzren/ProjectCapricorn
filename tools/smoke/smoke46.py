# 46: /see every 1 with a SLOW vision AI (3 s per look): one look at a time, no thread pile-up, chat still works
import os, sys, tempfile, time, threading
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
import capri, ledges
from PIL import Image
capri.read_api_key = lambda: "sk-ant-x"
capri.ai_available = lambda: True
inflight, max_inflight, looks = [0], [0], [0]
lock = threading.Lock()
def slow_look(system, mt, b64, q, n=120, model=None, room=1, **k):
    with lock:
        inflight[0] += 1; max_inflight[0] = max(max_inflight[0], inflight[0]); looks[0] += 1
    time.sleep(3.0)
    with lock:
        inflight[0] -= 1
    return "DOING: reading a long article SAY: That's a lot of words."
capri.vision_ask = slow_look
capri.llm_reply = lambda msgs, persona, **k: "Sure thing."
frame = [0]
def changing_screen():                 # the screen changes every look, so every look is sent
    frame[0] += 1
    return Image.new("RGB", (800, 450), ((frame[0] * 40) % 255, 30, 60))
ledges.capture = changing_screen
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None; p.go("idle", 999)
p.open_chat(); p.chat.submit("/see on"); p.chat.submit("/see every 1")
print("look every:", p.look_every())
threads0 = threading.active_count(); peak = threads0
t0 = time.time(); sent_chat = False
while time.time() - t0 < 30:
    p.root.update(); p._tick(); time.sleep(0.03)
    peak = max(peak, threading.active_count())
    if not sent_chat and time.time() - t0 > 10:
        p.chat.submit("hey are you still there?"); sent_chat = True
replies = [m["content"] for m in p.chat.history if m["role"] == "assistant"]
print("looks in 30 s:", looks[0], "| most at once:", max_inflight[0], "| threads at start/peak:", threads0, peak)
print("chat reply arrived:", replies[-1:] , "| results queue empty:", p.glance_results.empty(), "| gate busy now:", p.glance_gate.busy)
print("ok")
