# 33: expressions — AI tag drives a pose and never reaches the bubble/voice/recent lines; gating; every emotion
import os, sys, tempfile, time
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, expression
from PIL import Image, ImageDraw
capri.read_api_key = lambda: "sk-ant-x"
prompts = []
capri.llm_reply = lambda msgs, system, **k: (prompts.append(msgs[-1]["content"]), "[laugh] lol that's tragic")[1]
p = capri.Capri(); p.boot = None; p.cancel_intro(); p.choose_next = lambda: None; p.go("idle", 99)
spoken = []
p.speaker.speak = lambda text, priority=False: spoken.append(text) or True
p.ai_enabled = lambda: True
p.say_ai("idle", {}, "fallback line", 5, speak="priority")
t0 = time.time()
while time.time() - t0 < 3 and not p.recent_lines:
    p.drain_ai(time.time()); time.sleep(0.02)
print("asked for a tag:", "[smug]" in prompts[-1])
print("bubble:", repr(p.bubble), "| spoken:", spoken, "| recent:", list(p.recent_lines))
print("tag leaked:", any("laugh" in x.lower() for x in [p.bubble] + spoken + list(p.recent_lines)))
print("expression:", p.expr and p.expr[0])
p._tick(); print("anim drawn while laughing:", p.art.pick(p.expr[0]) if p.expr else None, "| hop_y:", round(p.hop_y, 1))
p.expr = None; p.expr_gate = expression.Gate()
p.calm = True; print("calm blocks:", not p.express("surprised")); p.calm = False
p.agent = object(); print("task blocks:", not p.express("surprised")); p.agent = None
p.settings["expressive"] = False; print("setting off blocks:", not p.express("surprised"))
print("but /express preview works:", p.express("smug", forced=True)); p.settings["expressive"] = True
# contact sheet: every emotion on both the new skin and the classic sheet
rows = []
for skin in ("capri", "classic"):
    p.set_skin(skin, announce=False); row = []
    for name in expression.EMOTIONS:
        p.expr = None; p.go("idle", 99); p.express(name, forced=True)
        t = time.time()
        for _ in range(6):
            p._tick(); time.sleep(0.03)
        p.clear_sprite_caches(); p.sprite_image(time.time())
        row.append((name, p.pil_cache.get(p._last_ck)))
    rows.append(row)
cw = max(i.width for r in rows for _, i in r if i) + 8; ch = max(i.height for r in rows for _, i in r if i) + 22
out = Image.new("RGB", (cw * len(expression.EMOTIONS) + 10, ch * 2 + 10), (12, 10, 22)); d = ImageDraw.Draw(out)
alphas = set()
for y, r in enumerate(rows):
    for x, (n, i) in enumerate(r):
        d.text((5 + x * cw, 5 + y * ch), n, fill=(255, 255, 255))
        if i: out.paste(i, (5 + x * cw, 5 + y * ch + ch - i.height - 4), i); alphas |= set(i.getchannel("A").getdata())
out.save("/tmp/emotions.png"); print("alpha:", sorted(alphas)); print("ok")
