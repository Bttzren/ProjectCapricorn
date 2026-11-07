# 41: local vision — glances go to the LOCAL vision server (image, no cloud call); /brain cloud sends them to the
# key; /do stays cloud-only even with a local vision model; /getbrain see restarts a running text engine
import os, sys, tempfile, time, json
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn"); sys.path.insert(0, "/home/user/ProjectCapricorn/tests")
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
import capri, localai, ledges
from test_localai import FAKE_SERVER
from PIL import Image
# a fake installed vision model + engine
d = os.path.join(home, "la"); script = os.path.join(home, "fake_server.py"); open(script, "w").write(FAKE_SERVER)
os.makedirs(d + "/bin"); open(d + "/bin/llama-server", "w").write("x")
md = os.path.join(d, "models", "see"); os.makedirs(md)
for n in ("m.gguf", "mmproj-m.gguf"): open(os.path.join(md, n), "w").write("x")
json.dump({"model": "m.gguf", "mmproj": "mmproj-m.gguf"}, open(os.path.join(md, "files.json"), "w"))
argvs = []
def argv(b, m, port, threads=None, mmproj=None):
    argvs.append(mmproj); return [sys.executable, script, "--port", str(port)] + (["--mmproj", mmproj] if mmproj else [])
capri.LOCAL_AI = localai.LocalAI(localai.Install(d), which="see", env_url="", argv_builder=argv, start_timeout=20)
cloud = []
capri.http_json = lambda req, timeout=25: (cloud.append(req.full_url), {"content": [{"type": "text", "text": "DOING: cloud look SAY: cloud."}]})[1]
capri.llm_reply = lambda *a, **k: "Nice."
ledges.capture = lambda: Image.new("RGB", (800, 450), (20, 20, 30))
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None; p.go("idle", 99)
p.settings["brain_model"] = "see"; capri.LOCAL_AI.which = "see"; capri.LOCAL_AI.refresh()
def pump(s):
    t0 = time.time()
    while time.time() - t0 < s:
        p.root.update(); p._tick(); time.sleep(0.03)
print("no key, local vision -> can_look:", capri.can_look(), "| local_sees:", capri.local_sees())
p.open_chat(); p.chat.submit("/see on"); print(p.chat.history[-1]["content"] if p.chat.history else "", "|", "see on")
p.ctx = "video"; p.glance_gate.last = -1e9; started = p.glance("video"); pump(4)
print("glance started:", started, "| engine started with --mmproj:", bool(argvs and argvs[-1]), "| cloud calls:", len(cloud))
print("what she knows you're doing:", p.activity_phrase())   # fake server echoes 'IMAGE <question>'
capri.read_api_key = lambda: "sk-ant-x"
print("with a key + local vision -> glance stays local:", capri.local_sees())
p.hands.level = "full"; p.settings["agent"] = True
print("/do with key:", p.agent_ready()[0], "| agent ask goes to cloud:", end=" ")
p._agent_ask("image/jpeg", "QUJD", "sys", "next?"); print(cloud[-1:] != [] and "anthropic" in cloud[-1])
capri.read_api_key = lambda: ""; print("/do with ONLY local vision ->", p.agent_ready())
capri.read_api_key = lambda: "sk-ant-x"; p.set_brain("cloud"); n = len(cloud)
p.glance_gate.last = -1e9; p.glance_gate.busy = False; p.glance("video"); pump(1.5); print("/brain cloud -> glance went to cloud:", len(cloud) > n)
p.set_brain("auto")
# installing 'see' while a text engine runs -> it is stopped so the next start loads the projector
capri.LOCAL_AI.which = "small"; stopped = []
orig_stop = capri.LOCAL_AI.stop; capri.LOCAL_AI.stop = lambda: (stopped.append(1), orig_stop())[1]
p.brain_events.put(("ok", "see")); p.drain_brain(); print("install finished -> running engine stopped:", bool(stopped), "| which:", capri.LOCAL_AI.which)
capri.LOCAL_AI.stop = orig_stop; capri.LOCAL_AI.stop()
print("ok")
