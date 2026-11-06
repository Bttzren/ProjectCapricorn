import array, math, os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn"); sys.path.insert(0, "/home/user/ProjectCapricorn/tests")
import capri, hearing, listen, audioout, voice
from tkinter import messagebox
from test_audioout import FakeSD, FakeStream, make_mp3
import numpy as np
messagebox.askyesno = lambda *a, **k: True
def tone(l, n=800): return array.array("h", [int(l*math.sin(i/3.0)) for i in range(n)]).tobytes()
# friends talking through Discord: chatter, then "Capri ..." after a pause
def discord_audio():
    t_end = time.time() + 4.0
    while time.time() < t_end:
        time.sleep(0.02); yield tone(0)
    script = ([tone(0)]*20 + [tone(5000)]*30 + [tone(0)]*30) * 2
    for c in script:
        time.sleep(0.003); yield c
    while True: time.sleep(0.02); yield tone(0)
hearing.installed = lambda: True
hearing.loopback_chunks = lambda stop=lambda: False, **k: discord_audio()
listen.installed = lambda: True
class Seg: pass
texts = iter(["lol did you see that headshot", "hey Capri, who's the best agent in Valorant?"])
class Model:
    def transcribe(self, audio, **kw):
        s = Seg(); s.text = next(texts, ""); return [s], None
listen.Whisper._load = lambda self: Model()
capri.read_api_key = lambda: "sk-ant-x"
asked = []
def fake_llm(msgs, persona, max_tokens=None, model=None):
    asked.append((msgs[0]["content"], persona))
    return "Jett, obviously. Fight me, choom."
capri.llm_reply = fake_llm
mp3 = make_mp3(1.0)
class Edge:
    def fetch(self, t): return mp3
sd = FakeSD(); FakeStream.slow = False
cable_player = audioout.Player(sd, decoder=lambda path, rate, ch: np.zeros((rate // 2, ch), dtype="float32"))
p = capri.Capri(); p.boot = None; p.root.update()
local = []
p.speaker = voice.Speaker(platform="linux", which=lambda n: None, edge=Edge(), threaded=True,
                          player=lambda path: (local.append(path), (None, 0.2))[1])
p.audio_out = cable_player
p.open_chat(); lines = []
p.chat.system_line = lambda t, err=False: lines.append(t)
p.chat.submit("/call")
print("status:", [l for l in lines if "Call mode" in l][-1][:60])
p.chat.submit("/call on")
t0 = time.time()
while time.time() - t0 < 25 and not any(l.startswith("Me:") for l in lines):
    p.root.update(); time.sleep(0.03)
time.sleep(1.0); p.root.update()
print("lines:", [l for l in lines if l.startswith(("Friend", "Me"))])
print("cable devices written:", sorted(set(s.device for s in sd.streams)), "| streams:", len(sd.streams))
print("local-only speaker plays (ambient):", len(local))
call_q = [a for a in asked if "The call so far" in a[0]]
print("AI asked for the call:", len(call_q), "| rules:", bool(call_q) and "SKIP" in call_q[0][1], "| context:", bool(call_q) and "Friend: lol did you see" in call_q[0][0])
p.chat.submit("/call off"); time.sleep(0.5); p.root.update()
print("call active after off:", p.call_active(), "| hear after off (stops in 8s):", p.hear is not None)
import listen as L
for t in ("join discord and talk to my friends", "start call mode", "leave the call", "join the discord and tell them I'll be late",
          "talk to my friends in discord"):
    print(repr(t), "->", L.intent(t))
