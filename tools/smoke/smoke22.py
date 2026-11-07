import array, math, os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, hearing, listen
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
def tone(l, n=800): return array.array("h", [int(l*math.sin(i/3.0)) for i in range(n)]).tobytes()
def drums():
    i = 0
    while True:
        i += 1; time.sleep(0.004)
        yield tone(7000 if i % 10 == 0 else 300)
hearing.installed = lambda: True
hearing.loopback_chunks = lambda stop=lambda: False, **k: drums()
listen.installed = lambda: True
class Seg: pass
class Model:
    def transcribe(self, audio, **kw):
        s = Seg(); s.text = "The meeting is moved to Friday at three, bring the report."; return [s], None
listen.Whisper._load = lambda self: Model()
capri.read_api_key = lambda: "sk-ant-x"
capri.llm_reply = lambda msgs, persona, max_tokens=None, model=None: "Meeting moved to Friday 3pm; bring the report."
said, moments = [], []
capri.Capri.say_moment = lambda self, sit, fb, *a, **k: moments.append(sit)
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.root.update()
p.open_chat(); lines = []
p.chat.system_line = lambda t, err=False: lines.append(t)
bubbles = []
p.chat.add_bubble = lambda role, text, animate=False: bubbles.append(text)
p.settings["hear"] = False
p.chat.submit("/hear")
p.chat.submit("/hear on")
hops = []
orig_hop = p.hop; p.hop = lambda power=9.0: (hops.append(power), orig_hop(power))[1]
t0 = time.time()
while time.time() - t0 < 25 and not (hops and moments):
    p.root.update(); time.sleep(0.03)
print("hear running:", p.hear.running, "| music:", p.hear.music, "| hops:", len(hops), "| moment:", moments[:1])
print("state after music start:", p.state)
p.chat.submit("/hear last")
t0 = time.time()
while time.time() - t0 < 5 and not any(l.startswith("They said") for l in lines): p.root.update(); time.sleep(0.03)
print([l for l in lines if l.startswith("They said")])
p.chat.submit("/hear summarize")
t0 = time.time()
while time.time() - t0 < 5 and not bubbles: p.root.update(); time.sleep(0.03)
print("summary bubble:", bubbles)
# muted while she talks
before = p.hear.ring.seconds_held()
p.speaker.speaking
class Sp: speaking = True
p.speaker = Sp()
time.sleep(0.5); mid = p.hear.ring.seconds_held(); time.sleep(0.5); after = p.hear.ring.seconds_held()
print("ring grows while she is silent?", before > 0, "| frozen while she talks:", abs(after - mid) < 0.3)
p.disable_hear(); print("after off:", p.hear, p.settings["hear"])
# preset full starts hearing
import presets
p.speaker = type("S", (), {"speaking": False, "stop": lambda self: None, "available": False, "engine": "none", "last_error": "", "speak": lambda *a, **k: False})()
p.apply_preset("full", ask=False)
for _ in range(10): p.root.update(); time.sleep(0.05)
print("FULL -> hear running:", p.hear is not None and p.hear.running, presets.detect(p.settings))
p.apply_preset("none", ask=False); print("NONE -> hear:", p.hear)
