# 48: /update — against a real git "origin" on disk (no network): check, update with a what's-new list, already
# newest, files changed on this PC are never overwritten, a folder that isn't a git copy
import os, sys, tempfile, time, shutil, subprocess
home = tempfile.mkdtemp(); os.environ["HOME"] = home; os.environ["APPDATA"] = home
sys.path.insert(0, "/home/user/ProjectCapricorn")
import capri, updater
capri.read_api_key = lambda *a, **k: ""
tmp = tempfile.mkdtemp(); origin = os.path.join(tmp, "origin"); copy = os.path.join(tmp, "copy"); os.mkdir(origin)
ENV = updater.git_env(os.environ)
ENV.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull})
def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, env=ENV, capture_output=True, text=True)
def commit(repo, name, text, msg):
    open(os.path.join(repo, name), "w").write(text); git(repo, "add", "-A"); git(repo, "commit", "-q", "-m", msg)
git(origin, "init", "-q", "-b", "main"); commit(origin, "capri.py", "v1", "First"); git(tmp, "clone", "-q", origin, "copy")
capri.app_dir = lambda: copy
p = capri.Capri(); p.boot = None; p.cancel_intro()
p.open_chat(); chat = p.chat
lines = []
orig = chat.system_line
def rec(text, err=False):
    lines.append(("ERR " if err else "") + text); return orig(text, err=err)
chat.system_line = rec
def run(cmd, secs=8):
    del lines[:]; chat.submit(cmd); t = time.time()
    while time.time() - t < secs:
        p._tick(); p.root.update(); time.sleep(0.02)
        if not p.updating and len(lines) >= 2: break
    return [part for ln in lines for part in ln.split("\n")]
ok = True
def check(name, cond, got):
    global ok
    ok = ok and bool(cond); print(("ok   " if cond else "FAIL ") + name + ": " + " | ".join(got)[:230])
got = run("/update check"); check("check, nothing new", any("newest" in g for g in got), got)
commit(origin, "capri.py", "v2", "Fix: she fell off the window"); commit(origin, "x.py", "x", "Sitting: she rides a moving window")
got = run("/update check"); check("check, 2 waiting", any("2 updates waiting" in g for g in got), got)
print("   file still old after a check:", open(os.path.join(copy, "capri.py")).read() == "v1")
got = run("/update"); check("update + what's new", any("Updated!" in g for g in got) and any("rides a moving window" in g for g in got)
                            and open(os.path.join(copy, "capri.py")).read() == "v2", got)
got = run("/update"); check("already newest", any("newest" in g for g in got), got)
commit(origin, "capri.py", "v3", "Newer"); open(os.path.join(copy, "capri.py"), "w").write("my own edit")
got = run("/update"); check("my edits are kept", any(g.startswith("ERR") and "didn't overwrite" in g for g in got)
                            and open(os.path.join(copy, "capri.py")).read() == "my own edit", got)
p.updating = True; got = run("/update", 1); check("one at a time", any("Already checking" in g for g in got), got); p.updating = False
capri.app_dir = lambda: tmp
got = run("/update", 2); check("not a git copy", any("wasn't made with git" in g for g in got), got)
capri.app_dir = lambda: copy; shutil.rmtree(origin)
got = run("/update"); check("download site gone", any(g.startswith("ERR") for g in got), got)
print("still ticking:", p.state, "| busy flag cleared:", not p.updating)
sys.exit(0 if ok and not p.updating else 1)
