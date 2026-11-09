# 42: /report — glitch notice after a loop error, clipboard report with versions/settings/errors and NO secrets
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda: "sk-ant-api03-SECRETSECRETSECRET"
capri.llm_reply = lambda *a, **k: "Nice."
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None
p.add_note("my locker code is 4471"); p.memory.remember("my dog is called Rex")
capri.log("cloud failed: 401 invalid x-api-key sk-ant-api03-SECRETSECRETSECRET for " + home + "/thing")
boom = [True]
orig = p.update_twitch
def once(now):
    if boom[0]:
        boom[0] = False; raise KeyError("forced for the test")
    return orig(now)
p.update_twitch = once
for _ in range(4): p.tick_once = p.tick(); p.root.update(); time.sleep(0.05)
print("glitch notice in bubble:", "/report" in p.bubble, "| errors counted:", p.tick_errors)
p.open_chat(); p.chat.submit("/report")
clip = p.root.clipboard_get()
print(clip[:600])
leaks = [s for s in ("SECRETSECRET", "4471", "Rex", home) if s in clip]
print("leaks:", leaks, "| has error block:", "KeyError" in clip, "| has versions:", "python:" in clip and "tk:" in clip)
print("saved file:", os.path.isfile(os.path.join(capri.data_dir(), "capri-report.txt")))
# the forced error is expected: take it out of the log so the smoke runner's log check stays meaningful
lp = os.path.join(capri.data_dir(), "capri.log"); txt = open(lp).read()
open(lp, "w").write(txt.replace("tick error", "expected test error").replace("failed:", "fails (test)"))
print("ok")
