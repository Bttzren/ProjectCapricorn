# 30: movement trace — eased walk, edge turn with a pause, steps follow distance, landing squash by fall height
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.root.update()
p.choose_next = lambda: None
lo, hi = p.bounds()
dt = 0.04
def run_walk(x0, d, dur, secs):
    p.fx, p.fy, p.surf, p.dir = x0, float(p.ground()), None, d
    p.go("walk", dur); p.walk_k = 1.0
    t0 = p.state_t0; out = []
    for i in range(int(secs / dt)):
        now = t0 + i * dt
        prev = p.fx
        p.step_state(now, dt, now - t0)
        out.append((round(now - t0, 2), round(p.fx - prev, 2), p.anim, round(p.step_ph, 2), round(p.hop_y, 2)))
        if p.state != "walk": break
    return out
tr = run_walk((lo + hi) / 2, 1, 3.0, 3.2)
sp = [abs(r[1]) for r in tr]
print("fw:", p.fw, "stride:", round(p.stride(), 1), "bounds:", round(lo), round(hi))
print("speed first 10:", sp[:10])
print("speed mid:", sp[len(sp)//2], "| last 6:", sp[-6:], "| ended in state:", p.state)
print("steps walked:", tr[-1][3], "frames on step clock:", p.art.frame("walk", 0, 1, 0.0)[0], p.art.frame("walk", 0, 1, 0.5)[0], p.art.frame("walk", 0, 1, 1.0)[0])
tr = run_walk(hi - 80, 1, 6.0, 4.0)
turn = [r for r in tr if r[2] == "idle"]
print("edge: min speed before turn:", min(abs(r[1]) for r in tr[:int(len(tr)*0.4)] if r[1] > 0) if tr else None,
      "| paused ticks:", len(turn), "| dir now:", p.dir, "| max x <= hi:", max(r[1] for r in tr) is not None and p.fx <= hi)
for vy in (3, 38):
    p.vy = vy * p.dpi; p.land(); print(f"land after vy={vy}: squash={p.land_squash:.2f}")
print("ok")
