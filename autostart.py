"""Start Capri when you log in to Windows (pure logic + file writes, no Tk).

Writes a tiny Capri.vbs into your Startup folder that launches her with no console window. Remove it
(or untick the setting) to stop. Nothing else on your system is touched.
"""
import os
import sys

NAME = "Capri.vbs"


def startup_dir(env=None):
    env = os.environ if env is None else env
    appdata = env.get("APPDATA")
    if not appdata:
        return None
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def launch_command(frozen=None, executable=None, script=None):
    """The command that starts her: the .exe if built, else pythonw (no console) + capri.py."""
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = executable or sys.executable
    if frozen:
        return [executable], os.path.dirname(executable)
    pyw = os.path.join(os.path.dirname(executable), "pythonw.exe")
    exe = pyw if os.path.isfile(pyw) else executable
    script = script or os.path.abspath(sys.argv[0])
    return [exe, script], os.path.dirname(script)


def _q(s):
    return '""' + s.replace('"', '""') + '""'          # a quoted argument inside a VBScript string


def build_vbs(parts, workdir):
    cmd = " ".join(_q(p) for p in parts)
    wd = workdir.replace('"', '""')
    return ('Set sh = CreateObject("WScript.Shell")\r\n'
            f'sh.CurrentDirectory = "{wd}"\r\n'
            f'sh.Run "{cmd}", 0, False\r\n')


def is_enabled(env=None):
    d = startup_dir(env)
    return bool(d) and os.path.isfile(os.path.join(d, NAME))


def enable(env=None, **kw):
    d = startup_dir(env)
    if not d:
        return False, "Start-with-Windows only works on Windows."
    parts, wd = launch_command(**kw)
    try:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, NAME), "w", encoding="utf-8", newline="") as f:
            f.write(build_vbs(parts, wd))
    except OSError as exc:
        return False, f"Couldn't set that up: {exc}"
    return True, "I'll start when you log in."


def disable(env=None):
    d = startup_dir(env)
    if not d:
        return False, "Start-with-Windows only works on Windows."
    try:
        os.remove(os.path.join(d, NAME))
    except FileNotFoundError:
        pass
    except OSError as exc:
        return False, f"Couldn't remove it: {exc}"
    return True, "Okay, I won't start by myself."
