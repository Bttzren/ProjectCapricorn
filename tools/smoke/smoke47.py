# 47: command fuzz — every slash command with missing / weird / huge arguments. Nothing may raise, and the pet must
# keep ticking afterwards. Real-world side effects (keys, mouse, downloads, mic, launching apps) are stubbed.
import os, re, sys, tempfile, time, random
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
messagebox.showinfo = messagebox.showwarning = messagebox.showerror = lambda *a, **k: None
import capri
capri.read_api_key = lambda *a, **k: ""
capri.llm_reply = lambda *a, **k: "[happy] Nice."
capri.vision_ask = lambda *a, **k: "DOING: testing things SAY: Okay."
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.rng.seed(3); random.seed(3)

did = []
def stub(name, ret=None):
    setattr(p, name, lambda *a, **k: (did.append(name), ret)[1])
for name, ret in (("open_thing", None), ("do_control", None), ("start_agent", (False, "stubbed")),
                  ("start_listening", None), ("enable_call", False), ("enable_hear", False), ("hear_now", None),
                  ("install_hear", None), ("install_ears", None), ("install_brain", None), ("remove_brain", None),
                  ("install_voice", None), ("enable_wake", False), ("run_brief", None), ("run_clip", None),
                  ("start_spotter", False), ("look", None), ("enable_agent", False), ("enable_vision", False),
                  ("enable_ledges", False)):
    stub(name, ret)
p.hands.do = lambda action, arg=None: (did.append("hands.do"), (True, "ok (fuzz)"))[1]
p.speak = lambda *a, **k: None                       # no TTS threads

chat = p.open_chat() or p.chat
src = open(capri.__file__, encoding="utf-8").read()
a = src.index("    def command(self, text):"); body = src[a:src.index("\n    def ", a + 10)]
cmds = sorted(set(re.findall(r'"(/[a-z0-9]+)"', body)) | set(capri.GAME_COMMANDS) | set(getattr(capri, "HAND_COMMANDS", {})))
ARGS = ["", "on", "off", "0", "1", "-1", "5", "3.5", "1.2.3", "999999999999999999999", "abc", "ON", "  ", "every",
        "every 5", "every 0", "every 9999", "every x", "once", "list", "add", "add x", "remove", "remove 99", "del 1",
        "1 hello there", "0 x", "-5 x", "1e9 x", "nan x", "inf", "red", "#ff00ff", "#zzz", "outline", "outline on",
        "capri", "watcher", "classic", "nope", "smug", "win", "loss", "valorant", "small", "big", "see", "full", "none",
        "some", "auto", "local", "cloud", "summarize", "last", "first", "50", "200", "5000", "tiny", "huge",
        "ctrl+c", "alt+f4", "win+r", "a" * 3000, "\U0001f600 é中", "'; drop", "%s %d {0} {x}", "\\n\\t", "\"", "/", "//",
        "1 " + "z" * 2000, "translate french", "fix", "x y z w v", "25 05", "13/40", "2020-02-30", "jan 5", "today", "\u00b2", "\u00b2 x", "\u2460", "1.2.3 x", "5 x", "0.01 x",
        "999999999999999999999 x", "\u00b2-1", "13-7 15/12", "999999999-1", "rm \u00b2", "remove 1", "del 0", "rm 999999999999",
        "add " + "q" * 500, "13-\u00b2", "\u0663", "1\x00 2", "\t", "on on on", "off extra", "#12345", "#1234567", "rgb(1,2,3)"]
fails = []
orig_report = p.root.report_callback_exception
def on_cb_error(exc, val, tb):
    fails.append(f"callback raised {exc.__name__}: {val}")
p.root.report_callback_exception = on_cb_error

n = 0
for c in cmds:
    for arg in ARGS:
        text = (c + " " + arg).rstrip() if arg.strip() else c + arg
        n += 1
        try:
            chat.submit(text)
        except Exception as exc:
            import traceback
            where = traceback.extract_tb(exc.__traceback__)[-1]
            fails.append(f"{text[:60]!r} raised {type(exc).__name__}: {str(exc)[:80]} (line {where.lineno})")
        if n % 40 == 0:
            p.root.update()
            try:
                p._tick()
            except Exception as exc:
                fails.append(f"tick after {text[:40]!r} raised {type(exc).__name__}: {exc}")
        if chat is None or not chat.alive():
            chat = p.open_chat() or p.chat           # /settings etc. may have changed windows; chat must reopen
# she must still be alive and well after all that
t0 = time.time()
while time.time() - t0 < 4:
    p.root.update()
    try:
        p._tick()
    except Exception as exc:
        fails.append(f"tick at the end raised {type(exc).__name__}: {exc}"); break
p.save_settings()
try:
    p.quit()
except Exception as exc:
    fails.append(f"quit raised {type(exc).__name__}: {exc}")
try:                                                   # whatever the commands saved must still start a fresh pet
    p2 = capri.Capri(); p2.boot = None; p2.cancel_intro()
    t0 = time.time()
    while time.time() - t0 < 2:
        p2.root.update(); p2._tick()
    p2.open_settings(); p2.root.update()
    p2.quit()
except Exception as exc:
    import traceback
    fails.append(f"restart on the fuzzed settings raised {type(exc).__name__}: {exc} "
                 f"(line {traceback.extract_tb(exc.__traceback__)[-1].lineno})")
uniq = sorted(set(fails))
print(f"commands: {len(cmds)}  inputs tried: {n}  stubbed side effects called: {len(did)}  problems: {len(uniq)}")
for f in uniq[:60]:
    print("  " + f)
sys.exit(1 if uniq else 0)
