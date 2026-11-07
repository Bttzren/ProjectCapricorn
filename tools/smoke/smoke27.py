# 27: notes — typed /note and /notes, spoken "note that ..." and "what did I note about ..."
import os, sys, tempfile, time, json
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, listen
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None
p.open_chat()
lines = []
orig = p.chat.system_line
p.chat.system_line = lambda t, err=False: (lines.append(("ERR " if err else "") + t), orig(t, err))[0]
spoken = []
p.speaker.speak = lambda text, priority=False: spoken.append(text) or True
def pump(secs=1.5):
    t0 = time.time()
    while time.time() - t0 < secs:
        p.root.update(); time.sleep(0.03)
p.chat.submit("/note locker code is 4471"); pump(0.3)
p.chat.submit("/note"); pump(0.3)
for phrase in ["Hey Capri, note that the wifi password is on the router",
               "Hey Capri, what did I note about the wifi?", "read my notes", "take a note"]:
    p.heard_events.put(("heard", phrase)); pump(0.8)
    print("bubble:", p.bubble)
p.chat.submit("/notes locker"); pump(0.3)
p.chat.submit("/notes rm 1"); pump(0.3)
print("lines:", lines)
print("spoken:", spoken)
print("saved:", json.load(open(os.path.join(capri.data_dir(), "settings.json"))).get("notes"))
print("ok")
