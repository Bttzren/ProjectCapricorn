# 38: falling/hopping uses the dangle pose on the new skin; landing returns to idle cleanly
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
capri.read_api_key = lambda: ""
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None
p.fx, p.fy = 400.0, float(p.ground()); p.go("idle", 99); time.sleep(1.0)
p.hop(12); seen = []
for _ in range(80):
    p._tick(); p.root.update(); time.sleep(0.02)
    k = p._last_ck[0][0] if p._last_ck else None
    if not seen or seen[-1] != (p.state, k): seen.append((p.state, k))
    if p.state != "air" and len(seen) > 1: break
for _ in range(5): p._tick(); p.root.update(); time.sleep(0.02)
print("states/poses:", seen[:4], "-> now:", p.state, p._last_ck[0][0])
p.fy = float(p.ground()) - 300; p.go("air")
for _ in range(3): p._tick(); p.root.update(); time.sleep(0.02)
print("dropped from 300px -> pose:", p._last_ck[0][0])
p.set_skin("classic", announce=False); p.go("air")
for _ in range(3): p._tick(); p.root.update(); time.sleep(0.02)
print("classic skin falling -> pose:", p._last_ck[0][0])
print("ok")
