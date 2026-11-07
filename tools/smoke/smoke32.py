# 32: skins — every pose of the new skin through the real draw path (hard alpha, no key colour), skin switching
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri
from PIL import Image, ImageDraw
capri.read_api_key = lambda: ""
t0 = time.time(); p = capri.Capri(); print("startup s:", round(time.time() - t0, 2), "kind:", p.art.kind, "w,h:", p.art.w, p.art.h)
p.boot = None; p.choose_next = lambda: None
shots = []
def grab(label, setup):
    setup(); p.clear_sprite_caches()
    ph, ax, ay, w, h = p.sprite_image(time.time())
    img = p.pil_cache.get(p._last_ck) if p._last_ck else None
    shots.append((label, img))
def st(state, **kw):
    def f():
        p.go(state, 99); p.talk_until = kw.get("talk", 0); p.glitch = kw.get("glitch", 0.0); p.angle = p.angle_t
        p.anim = kw.get("anim", p.anim)
    return f
grab("idle", st("idle"))
grab("talk", st("idle", talk=time.time() + 5))
grab("wave/grin", st("idle", anim="wave"))
grab("perch", st("perch"))
grab("drag", st("drag"))
grab("sleep", st("sleep"))
grab("lounge", st("lounge"))
grab("lounge talk", st("lounge", talk=time.time() + 5))
grab("glitch", st("idle", glitch=0.45))
grab("fail", st("idle", anim="fail"))
W = sum((i.width if i else 50) + 14 for _, i in shots) + 10; H = max((i.height if i else 50) for _, i in shots) + 30
out = Image.new("RGB", (W, H), (12, 10, 22)); d = ImageDraw.Draw(out); x = 8
alphas = set()
for n, i in shots:
    d.text((x, 4), n, fill=(255, 255, 255))
    if i:
        out.paste(i, (x, H - i.height - 4), i); alphas |= set(i.getchannel("A").getdata()); x += i.width + 14
        if any(px[:3] == (255, 0, 255) and px[3] == 255 for px in i.getdata()): print("KEY COLOR in", n)
    else:
        d.text((x, 30), "NONE", fill=(255, 80, 80)); x += 64
out.save("/tmp/skin_states.png"); print("alpha values:", sorted(alphas))
for n in ("watcher", "classic"):
    t0 = time.time(); ok = p.set_skin(n, announce=False); print(n, ok, p.art.kind, round(time.time() - t0, 2), "s")
