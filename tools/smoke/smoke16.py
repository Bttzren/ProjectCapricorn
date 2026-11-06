import array, math, os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn"); sys.path.insert(0, "/home/user/ProjectCapricorn/tests")
import capri, listen, localai
from test_localai import FAKE_SERVER
script = os.path.join(home, "fake_server.py"); open(script, "w").write(FAKE_SERVER)
d = os.path.join(home, "la"); os.makedirs(d + "/bin"); os.makedirs(d + "/models")
open(d + "/bin/llama-server", "w").write("x"); open(d + "/models/" + localai.MODELS["small"][1], "w").write("m")
capri.LOCAL_AI = localai.LocalAI(localai.Install(d), env_url="",
    argv_builder=lambda b, m, port, t=None: [sys.executable, script, "--port", str(port)], start_timeout=20)
capri.read_api_key = lambda: ""
def tone(level, n=1600): return array.array("h", [int(level*math.sin(i/3.0)) for i in range(n)]).tobytes()
said_text = ["Hey Capri, how was your day"]
def fake_chunks(stop=lambda: False, **k):
    for c in [tone(0)]*4 + [tone(4000)]*10 + [tone(0)]*15 + [tone(0)]*50: yield c
listen.mic_chunks = fake_chunks
listen.installed = lambda: True
class Seg: pass
class Model:
    def transcribe(self, audio, **kw):
        s = Seg(); s.text = said_text[0]; return [s], None
listen.Whisper._load = lambda self: Model()
p = capri.Capri()
p.open_chat()
lines = []
orig_sys = p.chat.system_line
p.chat.system_line = lambda t, err=False: (lines.append(t), orig_sys(t, err))[0]
print("ai_available:", capri.ai_available(), "| /brain:")
p.chat.submit("/brain")
spoken = []
p.speaker.speak = lambda text, priority=False: spoken.append(text) or True
def pump(cond, secs=30):
    t0 = time.time()
    while time.time() - t0 < secs and not cond():
        p.root.update(); time.sleep(0.05)
# 1) voice chat through the local AI
p.start_listening()
pump(lambda: any(m["role"] == "assistant" for m in p.chat.history))
print("history:", [(m["role"], m["content"]) for m in p.chat.history])
print("spoken:", spoken[-1:])
# 2) task phrase: agent not enabled -> reason
said_text[0] = "open discord and tell them I'll be late"
n = len(lines); p.start_listening()
pump(lambda: not p.listening and p.heard_events.empty(), 10)
for _ in range(20): p.root.update(); time.sleep(0.05)
print("after task phrase, listening:", p.listening, "agent:", p.agent)
# 3) offline fallback in auto mode with a key
capri.read_api_key = lambda: "sk-ant-x"
def boom(*a, **k): raise RuntimeError("Can't reach the server (down). Check your internet.")
capri.cloud_reply = boom
print("offline fallback:", capri.llm_reply([{"role": "user", "content": "yo"}], "p"))
capri.BRAIN["mode"] = "cloud"
try: capri.llm_reply([{"role": "user", "content": "yo"}], "p")
except RuntimeError as e: print("cloud-only error kept:", str(e)[:30])
capri.LOCAL_AI.stop()
print("ok")
