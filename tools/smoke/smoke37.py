# 37: chat replies act out a feeling; the tag never reaches history, saved json, bubble, voice or a call
import os, sys, tempfile, time, json
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, expression
capri.read_api_key = lambda: "sk-ant-x"
capri.ai_available = lambda: True
replies = ["[smug] Nice.\nSecond line.", "Nice. [laugh] lol"]
sent_persona = []
capri.llm_reply = lambda msgs, persona, **k: (sent_persona.append(persona), replies.pop(0))[1]
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None; p.go("idle", 99)
spoken = []
p.speaker.speak = lambda text, priority=False, call=False: spoken.append((text, call)) or True
p.open_chat(); c = p.chat
labels = []
orig = c.add_bubble
c.add_bubble = lambda role, text, *a, **k: (labels.append((role, text)), orig(role, text, *a, **k))[1]
def pump(secs):
    t0 = time.time()
    while time.time() - t0 < secs:
        p.root.update(); p._tick(); time.sleep(0.02)
for msg in ("rate my desktop", "and now?"):
    p.route_reply = True                                   # as if this came in during call mode
    c.submit(msg); pump(1.2)
    print("after", repr(msg), "-> expr:", p.expr and p.expr[0], "| icon:", p.icon and p.icon[0])
    p.expr = None; p.expr_gate = expression.Gate()
saved = json.load(open(os.path.join(capri.data_dir(), "chat_history.json")))
texts = [m["content"] for m in c.history] + [m["content"] for m in saved] + [t for _, t in labels] + [t for t, _ in spoken]
print("asked for tags:", "[smug]" in sent_persona[0])
print("assistant history:", [m["content"] for m in c.history if m["role"] == "assistant"])
print("spoken (text, to call):", spoken)
print("tag leaked anywhere:", any(w in t.lower() for t in texts for w in ("[smug]", "[laugh]", "smug", "laugh]")))
print("ok")
