# 50: Settings > AI look-interval slider (NeonSlider): click / drag / arrow keys set 1-90 s and save it; the
# buttons for the local AI that can see exist
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda *a, **k: ""
p = capri.Capri(); p.boot = None; p.cancel_intro()
installs = []
p.install_brain = lambda which="small": installs.append(which)
def run(secs):
    t = time.time()
    while time.time() - t < secs:
        p._tick(); p.root.update(); time.sleep(0.02)
p.open_settings(); run(0.8)
sw = p.settings_window if getattr(p, "settings_window", None) else None
if sw is None:
    sw = next(v for v in vars(p).values() if isinstance(v, capri.SettingsWindow))
sl = sw.interval_slider
ok = True
def check(name, cond, extra=""):
    global ok
    ok = ok and bool(cond); print(("ok   " if cond else "FAIL ") + name + (" " + str(extra) if extra != "" else ""))
check("starts at the default", sl.value() == 10 and "every 10 seconds" in sw.interval_lbl.cget("text"), sw.interval_lbl.cget("text"))
capri.WHEEL_TARGETS[str(sw.win)].yview_moveto(0.45); run(0.3)
sl.event_generate("<Button-1>", x=int(sl.x_of(45)), y=12); run(0.1)
check("click sets it", p.settings.get("vision_interval") == 45, p.settings.get("vision_interval"))
sl.event_generate("<B1-Motion>", x=5000, y=12); run(0.1)
check("drag far right stops at 90", p.settings.get("vision_interval") == 90 and p.look_every() == 90)
sl.event_generate("<B1-Motion>", x=-500, y=12); run(0.1)
check("drag far left stops at 1", p.settings.get("vision_interval") == 1 and "every 1 second" in sw.interval_lbl.cget("text")
      and "seconds" not in sw.interval_lbl.cget("text"), sw.interval_lbl.cget("text"))
sl.set(sl.value() + 1); sl.set(sl.value() + 1); sl.set(sl.value() - 1)
check("nudges", p.settings.get("vision_interval") == 2)
sl.set(500); check("set() clamps", sl.value() == 90)
import json
saved = json.load(open(os.path.join(home, ".capri", "settings.json"))) if os.path.exists(os.path.join(home, ".capri", "settings.json")) else p.settings
check("saved to disk", saved.get("vision_interval") == 90, saved.get("vision_interval"))
xs = [sl.x_of(v) for v in (1, 10, 45, 90)]
check("round trip", [sl.value_at(x) for x in xs] == [1, 10, 45, 90])
def buttons(w):
    out = []
    for ch in w.winfo_children():
        try:
            t = ch.cget("text")
        except Exception:
            t = ""
        if t: out.append((t, ch))
        out += buttons(ch)
    return out
labels = [t for t, _ in buttons(sw.win)]
check("button: a local AI that sees", any("ONE THAT SEES" in t for t in labels) and any(t.startswith("FASTER") for t in labels))
for t, wdg in buttons(sw.win):
    if "ONE THAT SEES" in t or t.startswith("FASTER"):
        wdg.event_generate("<Button-1>", x=3, y=3); wdg.event_generate("<ButtonRelease-1>", x=3, y=3)
run(0.2)
check("the buttons install the vision models", installs == ["see", "see-fast"], installs)
sys.exit(0 if ok else 1)
