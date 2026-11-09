# 45: soak test — normal life for a while with a real window on screen and ledges on; invariants every frame
import os, sys, tempfile, time, subprocess, random
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
import capri
capri.read_api_key = lambda: ""
capri.llm_reply = lambda *a, **k: "[happy] Nice."
other = subprocess.Popen([sys.executable, "-c", """
import sys, tkinter as tk
r = tk.Tk(); r.overrideredirect(True); r.geometry("640x320+320+700"); r.configure(bg="#2b2f3a")
tk.Frame(r, bg="#d0d4e0", height=28).pack(fill="x"); tk.Label(r, text="Some app", bg="#2b2f3a", fg="white").pack()
r.after(200000, r.destroy); r.mainloop()
"""])
time.sleep(1.5)
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.rng.seed(int(os.environ.get("SOAK_SEED", "7"))); random.seed(int(os.environ.get("SOAK_SEED", "7")))
p.enable_ledges()
SECS = float(os.environ.get("SOAK_SECS", "40"))   # SOAK_SECS=300 for a long run
wa = p.work_area(); states = {}; problems = []; floating_since = None; last_state = None; transitions = 0
t0 = time.time()
while time.time() - t0 < SECS:
    p.root.update(); p.tick_errors_before = getattr(p, "tick_errors", 0)
    try:
        p._tick()
    except Exception as exc:
        problems.append(f"tick raised {type(exc).__name__}: {exc}")
    now = time.time()
    # speed up her life: shorten whatever she's doing so many behaviours happen in the soak window
    if p.state in ("idle", "perch", "lounge", "sleep", "curious") and p.state_dur and now - p.state_t0 > 3:
        p.state_dur = min(p.state_dur, now - p.state_t0)
    if random.random() < 0.004: p.react("happy")
    if random.random() < 0.003: p.express(random.choice(list(capri.expression.EMOTIONS)), forced=True)
    if random.random() < 0.002: p.sit_somewhere(quiet=True)
    s = p.state; states[s] = states.get(s, 0) + 1
    if s != last_state: transitions += 1; last_state = s
    if not (wa[0] - 200 <= p.fx <= wa[2] + 200 and wa[1] - 50 <= p.fy <= wa[3] + 5):
        problems.append(f"off-screen at {round(p.fx)},{round(p.fy)} in {s}")
    if s == "perch" and not p.surf:
        problems.append("perched on nothing")
    standing = s in ("idle", "walk", "lounge", "sleep", "curious", "dance") and not p.surf
    if standing and p.fy < p.ground() - 6:
        floating_since = floating_since or now
        if now - floating_since > 1.0:
            problems.append(f"floating in {s} at y={round(p.fy)} (ground {p.ground()})"); floating_since = now
    else:
        floating_since = None
    time.sleep(0.02)
other.kill()
print("states seen:", sorted(states, key=lambda k: -states[k]))
print("state changes:", transitions, "| tick errors:", getattr(p, "tick_errors", 0))
uniq = sorted(set(problems))
print("problems:", len(problems), uniq[:8])
print("ok")
