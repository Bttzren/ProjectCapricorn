import array, math, os, sys, tempfile, time, threading
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn"); sys.path.insert(0, "/home/user/ProjectCapricorn/tests")
import capri, listen, localai
from tkinter import messagebox
from test_localai import FAKE_SERVER
script = os.path.join(home, "fake_server.py"); open(script, "w").write(FAKE_SERVER)
d = os.path.join(home, "la"); os.makedirs(d + "/bin"); os.makedirs(d + "/models")
open(d + "/bin/llama-server", "w").write("x"); open(d + "/models/" + localai.MODELS["small"][1], "w").write("m")
capri.LOCAL_AI = localai.LocalAI(localai.Install(d), env_url="",
    argv_builder=lambda b, m, port, t=None: [sys.executable, script, "--port", str(port)], start_timeout=20)
capri.read_api_key = lambda: ""
messagebox.askyesno = lambda *a, **k: True
def tone(l, n=1600): return array.array("h", [int(l*math.sin(i/3.0)) for i in range(n)]).tobytes()
S = tone(0); T = tone(4000)
script_audio = [S]*10 + [T]*8 + [S]*12 + [S]*30 + [T]*8 + [S]*12 + [S]*30 + [T]*8 + [S]*12
texts = iter(["we should grab food later", "Hey Capri, how was your day", "never mind"])
stop_ev = threading.Event()
def chunks(stop=lambda: False, **k):
    for c in script_audio:
        if stop(): return
        time.sleep(0.004); yield c
    while not stop(): time.sleep(0.02); yield S
listen.mic_chunks = chunks
listen.installed = lambda: True
class Seg: pass
class Model:
    def transcribe(self, audio, **kw):
        s = Seg(); s.text = next(texts); return [s], None
listen.Whisper._load = lambda self: Model()
p = capri.Capri(); p.cancel_intro()
spoken = []
p.speaker.speak = lambda text, priority=False: spoken.append(text) or True
p.chat = None
p.enable_wake()
def pump(cond, secs=20):
    t0 = time.time()
    while time.time() - t0 < secs and not cond():
        p.root.update(); time.sleep(0.03)
pump(lambda: p.chat is not None and any(m["role"] == "assistant" for m in p.chat.history))
print("history:", [(m["role"], m["content"]) for m in p.chat.history])
print("chat window state:", p.chat.win.state())
print("spoken:", spoken)
print("wake running:", p.wake.running)
p.disable_wake(); print("after off:", p.wake)
