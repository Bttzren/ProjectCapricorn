#!/usr/bin/env python3
"""Capri - a desktop companion.

She roams your screen, glitch-teleports, lounges, perches on your windows,
reacts to your cursor, runs focus timers, and chats (Claude or Gemini key).

Run:  python capri.py          Preview a Codex/Petdex sheet:  python capri.py --pet-preview
"""
import collections
import json
import math
import os
import queue
import random
import re
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import font as tkfont

import agent
import audioout
import autostart
import awareness
import boot
import breach
import brief
import call as calls
import clip
import daylog
import fun
import gamemode
import habits
import hands
import hearing
import journal
import launcher
import ledges
import listen
import localai
import memory
import meeting
import neon
import notes
import personality
import presets
import reactor
import sfx
import simon
import sizing
import speech
import ui
import vision
import voice
import world

try:
    from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageTk
except ImportError:  # Pillow is required
    r = tk.Tk()
    r.withdraw()
    from tkinter import messagebox
    messagebox.showerror("Capri", "Capri needs Pillow.\n\nRun:  pip install pillow")
    sys.exit(1)

NAME = "Capri"
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
TICK_MS = 40
HAND_COMMANDS = {"/pause": ("playpause", None), "/next": ("next", None), "/prev": ("prev", None),
                 "/volup": ("volup", None), "/voldown": ("voldown", None), "/mute": ("mute", None),
                 "/shot": ("screenshot", None), "/lock": ("lock", None)}
GAME_COMMANDS = {"/kill": ("kill", 1), "/death": ("death", 1), "/ace": ("ace", 1), "/clutch": ("clutch", 1),
                 "/rw": ("round_win", 1), "/rl": ("round_loss", 1)}
SPRITE_HEIGHT = 170            # on-screen sprite height at 100% display scaling
SLEEP_AFTER = 300              # seconds without poking her before she naps
FOCUS_MIN, BREAK_MIN = 25, 5
CHECKIN_EVERY = (40 * 60, 70 * 60)
MODEL = os.environ.get("CAPRI_MODEL", "claude-sonnet-5-5")
LINE_MODEL = os.environ.get("CAPRI_LINE_MODEL", "claude-haiku-5-5")        # short lines: fast and cheap
VISION_MODEL = os.environ.get("CAPRI_VISION_MODEL", "claude-haiku-5-5")    # looking at screenshots
AGENT_MODEL = os.environ.get("CAPRI_AGENT_MODEL", "claude-sonnet-5-5")      # doing tasks: needs to aim well
GEMINI_MODELS = [m for m in (os.environ.get("CAPRI_GEMINI_MODEL"),) if m] or [
    "gemini-flash-latest", "gemini-3.8-flash", "gemini-2.5-flash"]
KEY = "#ff00ff"               # Windows transparency key

C_BG, C_PANEL, C_PANEL2 = ui.BG, ui.PANEL, ui.PANEL2
C_GREEN, C_RED, C_BLUE = "#05f56f", "#fb0948", "#1969eb"
C_TEXT, C_DIM, C_BLACK = "#eaeaf5", "#8a8aa3", "#0c0a16"

DEFAULT_PERSONA = (
    "You are Capri, a small glitchy companion who lives on the user's desktop: a fragmented AI woven "
    "from many human souls, playful and a bit cheeky, warm underneath. You talk like a Night City local "
    "from Cyberpunk: casual street slang such as choom (friend), preem (great), nova (cool), gonk (fool), "
    "eddies (money), chrome (cyberware), delta (leave), flatline (fail or shut down), gig (job), biz "
    "(business), corpo and netrunner. Use slang sparingly: at most one slang word in a reply, and most "
    "replies need none. Don't call them choom every time. Your humour is dry and observant, not cheesy: no "
    "catchphrases, no forced hype, no exclamation-mark spam. Keep it PG: no real swearing or slurs. Reply in "
    "1-3 short sentences, plain text, no markdown, no emoji. Help with quick questions, focus, and getting "
    "unstuck by suggesting one tiny next step. Never claim to be anyone else."
)


# ------------------------------------------------------------------ paths, settings, log
def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    d = os.path.join(os.path.expanduser("~"), ".capri")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def log(msg):
    try:
        with open(os.path.join(data_dir(), "capri.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, obj):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f)
    except OSError:
        pass


def read_first(names):
    for d in (app_dir(), data_dir()):
        for n in names:
            try:
                with open(os.path.join(d, n), encoding="utf-8") as f:
                    t = f.read().strip()
                if t:
                    return t
            except OSError:
                pass
    return ""


def enable_dpi_awareness():
    if not IS_WIN:
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ------------------------------------------------------------------ chat backends
def read_api_key():
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        k = os.environ.get(var, "").strip()
        if k:
            return k
    for d in (data_dir(), app_dir()):          # a key saved from the app wins over the template file
        try:
            with open(os.path.join(d, "api_key.txt"), encoding="utf-8") as f:
                k = f.read().strip()
        except OSError:
            continue
        if k and not k.startswith("PASTE_"):
            return k
    return ""


def save_api_key(key):
    with open(os.path.join(data_dir(), "api_key.txt"), "w", encoding="utf-8") as f:
        f.write(key.strip() + "\n")


def read_fish_key():
    """Fish Audio key for Capri's real voice: FISH_API_KEY, or fish_key.txt in ~/.capri or beside capri.py."""
    k = os.environ.get("FISH_API_KEY", "").strip()
    if k:
        return k
    for d in (data_dir(), app_dir()):
        try:
            with open(os.path.join(d, "fish_key.txt"), encoding="utf-8") as f:
                k = f.read().strip()
        except OSError:
            continue
        if k and not k.startswith("PASTE_"):
            return k
    return ""


def save_fish_key(key):
    with open(os.path.join(data_dir(), "fish_key.txt"), "w", encoding="utf-8") as f:
        f.write(key.strip() + "\n")


def clear_fish_key():
    try:
        os.remove(os.path.join(data_dir(), "fish_key.txt"))
    except OSError:
        pass


def make_speaker():
    """Capri's real voice (Fish Audio) if a key is set, else the computer's built-in voice."""
    key = read_fish_key()
    fish = None
    if key:
        fish = voice.FishVoice(key, os.environ.get("CAPRI_FISH_VOICE") or voice.DEFAULT_FISH_VOICE,
                               os.path.join(data_dir(), "voice_cache"))
    edge = None
    if os.environ.get("CAPRI_EDGE", "on").lower() != "off" and voice.edge_installed():
        edge = voice.EdgeVoice(os.environ.get("CAPRI_EDGE_VOICE") or voice.DEFAULT_EDGE_VOICE,
                               os.path.join(data_dir(), "voice_cache"))
    return voice.Speaker(fish=fish, edge=edge, log=log)


def detect_provider(key):
    forced = os.environ.get("CAPRI_PROVIDER", "").strip().lower()
    if forced in ("claude", "anthropic"):
        return "anthropic"
    if forced == "gemini":
        return "gemini"
    return "anthropic" if key.startswith("sk-ant") else "gemini"


def http_json(req, timeout=45):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8"))["error"]["message"]
        except Exception:
            detail = str(exc.reason)
        raise RuntimeError(f"{exc.code}: {detail}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Can't reach the server ({exc.reason}). Check your internet.")


def clean_history(messages):
    out = []
    for m in messages:
        role = "user" if m["role"] == "user" else "assistant"
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n" + m["content"]
        else:
            out.append({"role": role, "content": m["content"]})
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def claude_reply(key, messages, persona, max_tokens=400, model=None):
    body = json.dumps({"model": model or MODEL, "max_tokens": max_tokens, "system": persona,
                       "messages": clean_history(messages)}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    data = http_json(req)
    text = "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text").strip()
    return text or "(empty reply, try again)"


def gemini_reply(key, messages, persona, max_tokens=800, model=None):
    contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
                for m in clean_history(messages)]
    body = json.dumps({"systemInstruction": {"parts": [{"text": persona}]}, "contents": contents,
                       "generationConfig": {"maxOutputTokens": max_tokens}}).encode()
    last = "no Gemini model worked"
    for model in list(GEMINI_MODELS):
        req = urllib.request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            data = http_json(req)
        except RuntimeError as exc:
            last = str(exc)
            if last[:3] in ("400:", "404:") and "key" not in last.lower():
                continue
            raise
        parts = ((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        if model != GEMINI_MODELS[0]:
            GEMINI_MODELS.remove(model)
            GEMINI_MODELS.insert(0, model)
        return text or "(Gemini sent an empty reply, try again)"
    raise RuntimeError(last)


CABLE_HELP = ("To talk in a call I need a virtual audio cable so your friends can hear me. 1) Install the free "
              "VB-Audio Virtual Cable (vb-audio.com/Cable) and restart. 2) In Discord > Settings > Voice & Video, set "
              "Input Device to 'CABLE Output'. 3) So they still hear YOU: Windows Sound settings > Recording > your "
              "microphone > Properties > Listen > tick 'Listen to this device' and pick 'CABLE Input'. Then /call on.")


LOCAL_AI = localai.LocalAI()
BRAIN = {"mode": "auto"}          # auto: cloud when there's a key, local otherwise | cloud | local


def refresh_imports():
    """After pip installs a package while she's running, make it importable without a restart."""
    import importlib
    import site
    importlib.invalidate_caches()
    try:
        us = site.getusersitepackages()
        if os.path.isdir(us) and us not in sys.path:
            sys.path.append(us)
    except Exception:
        pass


def ai_available():
    """Can she write text right now with something (a key and/or a local AI)?"""
    mode = BRAIN["mode"]
    if mode == "local":
        return LOCAL_AI.available()
    if mode == "cloud":
        return bool(read_api_key())
    return bool(read_api_key()) or LOCAL_AI.available()


def llm_reply(messages, persona, max_tokens=None, model=None):
    key = read_api_key()
    mode = BRAIN["mode"]
    if mode == "local" or (mode == "auto" and not key):
        return LOCAL_AI.reply(messages, persona, max_tokens or 300)
    try:
        return cloud_reply(key, messages, persona, max_tokens, model)
    except RuntimeError as exc:
        if mode == "auto" and str(exc).startswith("Can't reach the server") and LOCAL_AI.available():
            return LOCAL_AI.reply(messages, persona, max_tokens or 300)          # offline: use the local AI
        raise


def cloud_reply(key, messages, persona, max_tokens=None, model=None):
    if not key:
        raise RuntimeError("No API key yet. Put your key in api_key.txt next to me and restart.")
    fn = gemini_reply if detect_provider(key) == "gemini" else claude_reply
    kw = {}
    if max_tokens:
        kw["max_tokens"] = max_tokens
    if model:
        kw["model"] = model
    return fn(key, messages, persona, **kw)


GEMINI_AGENT_NOTE = (" Coordinates are PIXELS in the screenshot you were given (x from the left, y from the top), "
                     "not a 0-1000 scale. Reply with the JSON object only.")


def vision_ask(system, media_type, b64, prompt, max_tokens=120, model=None, room=1):
    """Ask the vision model about ONE shrunken screenshot. The image goes to the AI provider that owns your key.
    room: multiplier for Gemini's token cap (its newer models spend output tokens on thinking first)."""
    key = read_api_key()
    if not key:
        raise RuntimeError("401: no API key")
    if detect_provider(key) == "gemini":
        body = json.dumps(vision.gemini_body(system, media_type, b64, prompt, max_tokens * room)).encode()
        last = "no Gemini model worked"
        for model in list(GEMINI_MODELS):
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", data=body,
                headers={"Content-Type": "application/json", "x-goog-api-key": key})
            try:
                return vision.gemini_text(http_json(req, timeout=25))
            except RuntimeError as exc:
                last = str(exc)
                if last[:3] in ("400:", "404:") and "key" not in last.lower():
                    continue
                raise
        raise RuntimeError(last)
    body = json.dumps(vision.anthropic_body(model or VISION_MODEL, system, media_type, b64, prompt, max_tokens)).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    return vision.anthropic_text(http_json(req, timeout=25))


# ------------------------------------------------------------------ Windows helpers
class Win32:
    def __init__(self):
        self.ok = False
        if not IS_WIN:
            return
        try:
            import ctypes
            from ctypes import wintypes
            self.ct, self.wt = ctypes, wintypes
            self.u = ctypes.windll.user32
            try:
                self.dwm = ctypes.windll.dwmapi
            except Exception:
                self.dwm = None
            self.ok = True
        except Exception:
            log("win32 init failed: " + traceback.format_exc())

    def work_area(self):
        if not self.ok:
            return None
        try:
            r = self.wt.RECT()
            if self.u.SystemParametersInfoW(0x0030, 0, self.ct.byref(r), 0):
                return (r.left, r.top, r.right, r.bottom)
        except Exception:
            pass
        return None

    def foreground(self):
        """(l, t, r, b, hwnd) of the active normal window, or None."""
        if not self.ok:
            return None
        try:
            ct, wt, u = self.ct, self.wt, self.u
            hwnd = u.GetForegroundWindow()
            if not hwnd or u.IsIconic(hwnd) or not u.IsWindowVisible(hwnd) or u.IsZoomed(hwnd):
                return None
            pid = wt.DWORD()
            u.GetWindowThreadProcessId(hwnd, ct.byref(pid))
            if pid.value == os.getpid():
                return None
            cls = ct.create_unicode_buffer(64)
            u.GetClassNameW(hwnd, cls, 64)
            if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
                return None
            r = wt.RECT()
            if not (self.dwm and self.dwm.DwmGetWindowAttribute(hwnd, 9, ct.byref(r), ct.sizeof(r)) == 0):
                u.GetWindowRect(hwnd, ct.byref(r))
            if r.right - r.left < 200 or r.bottom - r.top < 100:
                return None
            return (r.left, r.top, r.right, r.bottom, int(hwnd))
        except Exception:
            return None

    def foreground_title(self):
        """Title of the front window (used only to pick a one-word category; never stored or logged)."""
        if not self.ok:
            return ""
        try:
            ct, wt, u = self.ct, self.wt, self.u
            hwnd = u.GetForegroundWindow()
            if not hwnd:
                return ""
            pid = wt.DWORD()
            u.GetWindowThreadProcessId(hwnd, ct.byref(pid))
            if pid.value == os.getpid():
                return ""
            n = u.GetWindowTextLengthW(hwnd)
            buf = ct.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            return buf.value
        except Exception:
            return ""

    def hotkey(self, letter, on_press):
        """Global Ctrl+Alt+<letter>. on_press runs on a helper thread, so it must only queue something."""
        if not self.ok or not letter:
            return False
        ok = threading.Event()
        res = {}

        def run():
            try:
                ct, wt, u = self.ct, self.wt, self.u
                res["ok"] = bool(u.RegisterHotKey(None, 0x4361, 0x1 | 0x2 | 0x4000, ord(letter.upper())))
                ok.set()
                if not res["ok"]:
                    return
                msg = wt.MSG()
                while u.GetMessageW(ct.byref(msg), None, 0, 0) > 0:
                    if msg.message == 0x0312:
                        on_press()
            except Exception:
                res["ok"] = False
                ok.set()
        threading.Thread(target=run, daemon=True).start()
        ok.wait(2)
        return bool(res.get("ok"))

    def cursor_pos(self):
        """(x, y) of the mouse, safe to call from any thread. None where unknown."""
        if not self.ok:
            return None
        try:
            ct, wt = self.ct, self.wt
            pt = wt.POINT()
            self.u.GetCursorPos(ct.byref(pt))
            return pt.x, pt.y
        except Exception:
            return None

    def idle_seconds(self):
        """Seconds since the last keyboard/mouse input (just the time; never which keys)."""
        if not self.ok:
            return 0.0
        try:
            ct, wt = self.ct, self.wt

            class LASTINPUTINFO(ct.Structure):
                _fields_ = [("cbSize", wt.UINT), ("dwTime", wt.DWORD)]
            li = LASTINPUTINFO()
            li.cbSize = ct.sizeof(LASTINPUTINFO)
            self.u.GetLastInputInfo(ct.byref(li))
            return ((ct.windll.kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000.0
        except Exception:
            return 0.0

    def battery(self):
        """(percent or None, plugged_in). Desktops without a battery report (None, True)."""
        if not self.ok:
            return None, True
        try:
            ct = self.ct

            class POWER(ct.Structure):
                _fields_ = [("ac", ct.c_ubyte), ("flag", ct.c_ubyte), ("pct", ct.c_ubyte), ("sys", ct.c_ubyte),
                            ("life", ct.c_ulong), ("full", ct.c_ulong)]
            st = POWER()
            if not ct.windll.kernel32.GetSystemPowerStatus(ct.byref(st)):
                return None, True
            if st.flag == 128 or st.pct > 100:           # no battery / unknown
                return None, True
            return int(st.pct), st.ac == 1
        except Exception:
            return None, True


# ------------------------------------------------------------------ art
def hard_alpha(img):
    r, g, b, a = img.split()
    return Image.merge("RGBA", (r, g, b, a.point(lambda v: 255 if v > 127 else 0)))


def crisp(img, cut=170):
    """Hard-edge a frame for color-key transparency (Windows draws magenta wherever alpha is 0).

    Any soft edge pixel would blend with the key color and leave a pink halo, so every pixel becomes
    fully opaque or fully clear. Kept edge pixels take their color from the solid pixels beside them,
    which also removes the purple rim that soft anti-aliasing leaves in the art.
    """
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    edge = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a >= 250:
                # fully solid; never let art collide with the key color
                px[x, y] = (254, 0, 255, 255) if (r, g, b) == (255, 0, 255) else (r, g, b, 255)
            elif a < cut:
                px[x, y] = (0, 0, 0, 0)
            else:
                edge.append((x, y))
    fixed = []
    for x, y in edge:
        for rad in (1, 2):
            near = [px[i, j] for j in range(max(0, y - rad), min(h, y + rad + 1))
                    for i in range(max(0, x - rad), min(w, x + rad + 1)) if px[i, j][3] >= 250]
            if near:
                n = len(near)
                fixed.append((x, y, (sum(c[0] for c in near) // n, sum(c[1] for c in near) // n,
                                     sum(c[2] for c in near) // n, 255)))
                break
        else:
            fixed.append((x, y, px[x, y][:3] + (255,)))
    for x, y, c in fixed:
        px[x, y] = c
    return img


def scale_to(img, h, pixel=True):
    k = h / img.height
    if 0.92 <= k <= 1.08:
        return crisp(img)
    return crisp(img.resize((max(1, round(img.width * k)), h), Image.LANCZOS))


def thumb(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), h), Image.BOX)


def head_portrait(frame, h=56):
    """Chat-avatar crop: the top of her silhouette (hair + face)."""
    bb = frame.getchannel("A").getbbox()
    if not bb:
        return thumb(frame, h)
    x0, y0, x1, y1 = bb
    return thumb(frame.crop((x0, y0, x1, y0 + max(8, int((y1 - y0) * 0.38)))), h)


def head_portraits(frames, h=56):
    """Head crops for a whole animation, all cut with the same box so the avatar doesn't jitter."""
    boxes = [b for b in (f.getchannel("A").getbbox() for f in frames) if b]
    if not boxes:
        return [thumb(f, h) for f in frames]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    box = (x0, y0, x1, y0 + max(8, int((y1 - y0) * 0.38)))
    return [thumb(f.crop(box), h) for f in frames]


def norm(name):
    return str(name).lower().replace("_", "-").replace(" ", "-")


class SheetSprites:
    """Codex/Petdex style pet: spritesheet.webp|png (8 columns) + pet.json, one row per state."""
    kind = "sheet"
    flip_dir = False
    DEFAULT_ROWS = ["idle", "running-right", "running-left", "waving", "jumping", "failed",
                    "waiting", "running", "review"]
    FALLBACK = {
        "idle": ["idle"], "wave": ["waving", "jumping", "idle"], "jump": ["jumping", "waving", "idle"],
        "fail": ["failed", "idle"], "wait": ["waiting", "review", "idle"], "think": ["review", "waiting", "idle"],
        "run": ["running", "running-right", "idle"],
        "dance": ["waving", "jumping", "idle"], "startle": ["jumping", "failed", "idle"],
        "talk": ["waving", "idle"],
        "look-a": ["look-a", "idle"], "look-b": ["look-b", "idle"], "type": ["waving", "idle"],
    }

    def __init__(self, folder, target_h):
        path = next((os.path.join(folder, n) for n in ("spritesheet.webp", "spritesheet.png")
                     if os.path.isfile(os.path.join(folder, n))), None)
        if not path:
            raise FileNotFoundError("spritesheet")
        meta = load_json(os.path.join(folder, "pet.json"), {})
        meta = meta if isinstance(meta, dict) else {}
        sheet = Image.open(path).convert("RGBA")
        W, H = sheet.size
        cols = int(meta.get("columns") or meta.get("cols") or 8)
        cwf = W / float(cols)                      # cells need not be whole pixels (scaled sheets)
        rows_m = meta.get("rows")
        nrows = rows_m if isinstance(rows_m, int) and rows_m > 0 else max(1, int(round(H / (cwf * 208 / 192))))
        chf = H / float(nrows)
        cw, ch = int(round(cwf)), int(round(chf))
        cells, boxes = [], []
        for r in range(nrows):
            row = []
            for c in range(cols):
                x0, y0 = int(round(c * cwf)), int(round(r * chf))
                cell = sheet.crop((x0, y0, x0 + cw, y0 + ch))
                bb = cell.getchannel("A").point(lambda v: 255 if v > 127 else 0).getbbox()
                if bb and (bb[2] - bb[0]) > 3 and (bb[3] - bb[1]) > 3:
                    row.append(cell)
                    boxes.append(bb)
            cells.append(row)
        if not boxes:
            raise ValueError("empty spritesheet")
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
        self.rows = [[scale_to(c.crop(box), target_h) for c in row] for row in cells]
        self.w, self.h = next(f for row in self.rows for f in row).size
        mapping = {n: i for i, n in enumerate(self.DEFAULT_ROWS)}
        for key in ("states", "animations", "rows"):
            v = meta.get(key)
            if isinstance(v, dict):
                for n, spec in v.items():
                    row = spec.get("row") if isinstance(spec, dict) else spec
                    if isinstance(row, int):
                        mapping[norm(n)] = row
            elif isinstance(v, list):
                for i, spec in enumerate(v):
                    if isinstance(spec, str):
                        mapping[norm(spec)] = i
                    elif isinstance(spec, dict):
                        n = spec.get("name") or spec.get("id") or spec.get("state")
                        if n:
                            mapping[norm(n)] = spec.get("row", i) if isinstance(spec.get("row", i), int) else i
        override = load_json(os.path.join(folder, "pet_map.json"), None) or load_json(
            os.path.join(app_dir(), "pet_map.json"), {})
        if isinstance(override, dict):
            for n, row in override.items():
                if isinstance(row, int):
                    mapping[norm(n)] = row
        for name, row in (("look-a", 9), ("look-b", 10)):      # the sheet's two "look around" loops
            if name not in mapping and row < len(self.rows) and self.rows[row]:
                mapping[name] = row
        self.map = mapping
        self.emotes = {}
        idle_row = self.rows[mapping.get("idle", 0)] if mapping.get("idle", 0) < len(self.rows) else []
        base = (idle_row or next(r for r in self.rows if r))[0]
        self.portraits = {"idle": head_portrait(base)}
        for key, name, i in (("talk", "waving", 1), ("angry", "failed", 0)):
            fr = self.row_frames(name)
            if fr:
                self.portraits[key] = head_portrait(fr[min(i, len(fr) - 1)])
        self.avatar = {}
        for key, name in (("idle", "idle"), ("talk", "waving")):
            fr = self.row_frames(name)
            if fr:
                self.avatar[key] = head_portraits(fr)

    def row_frames(self, name):
        i = self.map.get(name)
        return self.rows[i] if i is not None and 0 <= i < len(self.rows) and self.rows[i] else None

    def frame(self, anim, t, d):
        if anim == "walk":
            order = ["running-right", "running", "idle"] if d > 0 else ["running-left", "running", "idle"]
        else:
            order = self.FALLBACK.get(anim, ["idle"])
        for name in order + ["idle"]:
            fr = self.row_frames(name)
            if fr:
                i = int(t * (5 if name == "idle" else 9)) % len(fr)
                return (name, i), fr[i]
        fr = next(r for r in self.rows if r)
        return ("any", 0), fr[0]


class PlaceholderSprites:
    """Last-resort stand-in if the Capri sheet can't be found or read."""
    kind = "placeholder"
    flip_dir = True

    def __init__(self, target_h):
        im = Image.new("RGBA", (40, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle((8, 10, 32, 60), fill=(251, 9, 72, 255), outline=(12, 10, 22, 255))
        d.rectangle((8, 10, 32, 28), fill=(5, 245, 111, 255), outline=(12, 10, 22, 255))
        d.rectangle((12, 16, 17, 22), fill=(25, 105, 235, 255))
        d.rectangle((23, 16, 28, 22), fill=(25, 105, 235, 255))
        k = max(1, round(target_h / 64))
        self.idle = im.resize((40 * k, 64 * k), Image.NEAREST)
        self.w, self.h = self.idle.size
        self.emotes, self.portraits = {}, {"idle": thumb(self.idle, 56)}

    def frame(self, anim, t, d):
        return ("p",), self.idle


def find_pet_dir():
    home = os.path.expanduser("~")
    cands = [os.environ.get("CAPRI_PET_DIR"), os.path.join(app_dir(), "pet"),
             os.path.join(getattr(sys, "_MEIPASS", app_dir()), "pet"), os.path.join(data_dir(), "pet"),
             os.path.join(home, ".codex", "pets", "capri")]
    pets = os.path.join(home, ".codex", "pets")
    if os.path.isdir(pets):
        cands += [os.path.join(pets, n) for n in sorted(os.listdir(pets)) if "capri" in n.lower()]
    for c in cands:
        if c and any(os.path.isfile(os.path.join(c, n)) for n in ("spritesheet.webp", "spritesheet.png")):
            return c
    return None


def load_art(dpi):
    target = int(SPRITE_HEIGHT * dpi)
    folder = find_pet_dir()
    if folder:
        try:
            art = SheetSprites(folder, target)
            log(f"loaded sheet pet from {folder}, rows={len(art.rows)} map={art.map}")
            return art
        except Exception:
            log("sheet pet failed: " + traceback.format_exc())
    log("no usable Capri sheet found; showing the placeholder")
    return PlaceholderSprites(target)


# ------------------------------------------------------------------ posing and glitch
def glitch_fx(img, ax, amt, rng):
    p = int(6 + 18 * amt)
    w, h = img.size
    base = Image.new("RGBA", (w + 2 * p, h), (0, 0, 0, 0))
    base.paste(img, (p, 0))
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    y = 0
    while y < h:
        bh = rng.randint(3, 16)
        dx = rng.randint(-p, p) if rng.random() < 0.25 + 0.6 * amt else 0
        band = base.crop((0, y, base.width, min(h, y + bh)))
        out.paste(band, (dx, y))
        y += bh
    r, g, b, a = out.split()
    d = max(1, int(2 + 5 * amt))
    r, b = ImageChops.offset(r, d, 0), ImageChops.offset(b, -d, 0)
    a = ImageChops.lighter(ImageChops.lighter(a, ImageChops.offset(a, d, 0)), ImageChops.offset(a, -d, 0))
    out = Image.merge("RGBA", (r, g, b, a))
    px = out.load()
    for yy in range(0, h, 2):
        if rng.random() < 0.18 * amt:
            for xx in range(out.width):
                px[xx, yy] = (0, 0, 0, 0)
    return hard_alpha(out), ax + p


def pose(img, angle=0.0, sx=1.0, sy=1.0, flip=False, dim=False, glitch=0.0, rng=random):
    """Returns (image, pivot_x, pivot_y): pivot is the feet point inside the image."""
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
        img = img.resize((max(2, round(img.width * sx)), max(2, round(img.height * sy))), Image.NEAREST)
    if dim:
        r, g, b, a = img.split()
        rgb = ImageEnhance.Brightness(Image.merge("RGB", (r, g, b))).enhance(0.62)
        img = Image.merge("RGBA", (*rgb.split(), a))
    w, h = img.size
    ax, ay = w / 2.0, float(h)
    if abs(angle) > 0.5:
        th = math.radians(angle)
        py = h / 2.0
        rx, ry = py * math.sin(th), py * math.cos(th)
        rot = img.rotate(angle, expand=True, resample=Image.NEAREST)
        ax, ay = rot.width / 2.0 + rx, rot.height / 2.0 + ry
        img = hard_alpha(rot)
    if glitch > 0.02:
        img, ax = glitch_fx(img, ax, glitch, rng)
    return img, ax, ay


# ------------------------------------------------------------------ small ui helpers
def pick_font(root, *families):
    have = set(tkfont.families(root))
    for f in families:
        if f in have:
            return f
    return "TkDefaultFont"


def round_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def chamfer_rect(c, x1, y1, x2, y2, cut, **kw):
    """A sharp rectangle with two cut corners (top-left and bottom-right)."""
    pts = [x1 + cut, y1, x2, y1, x2, y2 - cut, x2 - cut, y2, x1, y2, x1, y1 + cut]
    return c.create_polygon(pts, **kw)


def flat_button(parent, text, command, bg, fg, hover, font, padx=12, pady=5):
    """The app's button, drawn sharp and neon: solid when `bg` is the accent green, outlined otherwise."""
    filled = bg in (C_GREEN, C_RED)
    color = C_RED if (bg == C_RED or (not filled and fg == C_RED)) else ui.acc()
    if isinstance(font, tuple) and len(font) >= 2:
        font = (ui.mono_font(parent), font[1], "bold")
    return ui.button(parent, text, command, font, filled=filled, color=color, padx=padx, pady=pady)


# ------------------------------------------------------------------ chat window
class ChatWindow:
    CHIPS = [("Focus 25", "/focus"), ("Break it down", "Help me break what I'm working on into tiny steps."),
             ("I'm stuck", "I'm stuck. Ask me one question to get me moving."), ("Surprise me", "Tell me something fun.")]

    def __init__(self, pet):
        self.pet = pet
        root = pet.root
        self.fam = pet.font_family
        self.fam = ui.mono_font(root)
        self.acc, self.acc2 = ui.acc(), ui.THEME["acc2"]
        self.win = tk.Toplevel(root)
        self.win.title("CAPRI//LINK")
        self.win.configure(bg=C_BG)
        self.win.minsize(340, 460)
        self.win.geometry(pet.settings.get("chat_geom", "400x600"))
        self.topmost = pet.settings.get("chat_topmost", True)
        self.win.attributes("-topmost", self.topmost)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.q = queue.Queue()
        self.busy = False
        self.images = {}
        self.av_i = 0
        self.face_override = None
        self.typing_job = None
        self.typing_row = None
        self.history = load_json(os.path.join(data_dir(), "chat_history.json"), [])
        if not isinstance(self.history, list):
            self.history = []
        self.persona = read_first(["persona.txt"]) or DEFAULT_PERSONA
        self.f_body = (self.fam, 10)
        self.f_small = (self.fam, 8)
        self.f_bold = (self.fam, 9, "bold")
        self.build()
        for m in self.history[-40:]:
            self.add_bubble(m["role"], m["content"], m.get("ts", ""), animate=False)
        if not self.history:
            self.add_bubble("assistant", "Hey. I'm here. Type something, or tap a button below.", animate=False)
        self.win.after(60, self.scroll_end)
        self.entry.focus_set()
        self.win.after(160, self.tick_avatar)

    # ---- layout
    def photo(self, key):
        img = self.pet.art.portraits.get(key) or self.pet.art.portraits["idle"]
        if key not in self.images:
            self.images[key] = ImageTk.PhotoImage(img)
        return self.images[key]

    def build(self):
        w = self.win
        acc = self.acc
        ui.rule(w, 12, acc, C_BG).pack(fill="x")
        head = tk.Frame(w, bg=C_PANEL)
        head.pack(fill="x")
        self.portrait = tk.Label(head, image=self.photo("idle"), bg=C_PANEL, bd=0, highlightthickness=2,
                                 highlightbackground=acc)
        self.portrait.pack(side="left", padx=(12, 10), pady=8)
        col = tk.Frame(head, bg=C_PANEL)
        col.pack(side="left")
        tk.Label(col, text="CAPRI//LINK", bg=C_PANEL, fg=acc, font=(self.fam, 14, "bold")).pack(anchor="w")
        tk.Label(col, text="ENCRYPTED CHANNEL  v2.0", bg=C_PANEL, fg=ui.DIM, font=(self.fam, 7)).pack(anchor="w")
        self.status = tk.Label(col, text="● ONLINE", bg=C_PANEL, fg=C_GREEN, font=(self.fam, 8, "bold"))
        self.status.pack(anchor="w")
        right = tk.Frame(head, bg=C_PANEL)
        right.pack(side="right", padx=10)
        self.pin_btn = ui.button(right, "[PINNED]" if self.topmost else "[PIN]", self.toggle_pin, self.f_small, pady=2)
        self.pin_btn.pack(side="left", padx=3)
        ui.button(right, "[CLEAR]", self.clear, self.f_small, pady=2).pack(side="left", padx=3)
        ui.rule(w, 8, ui.blend(acc, C_BG, 0.5), C_BG, notch=False).pack(fill="x")

        self.keybar = None
        if not ai_available():
            self.build_keybar()

        # input area (packed first so it stays at the bottom)
        bottom = tk.Frame(w, bg=C_PANEL)
        bottom.pack(side="bottom", fill="x")
        ui.rule(bottom, 8, acc, C_PANEL, notch=False).pack(fill="x")
        chips = tk.Frame(bottom, bg=C_PANEL)
        chips.pack(fill="x", padx=10, pady=(6, 2))
        for label, payload in self.CHIPS:
            ui.button(chips, "[" + label.upper() + "]", lambda p=payload: self.chip(p), (self.fam, 7, "bold"),
                      padx=6, pady=2).pack(side="left", padx=(0, 5))
        row = tk.Frame(bottom, bg=C_PANEL)
        row.pack(fill="x", padx=10, pady=(4, 10))
        box = tk.Frame(row, bg=C_PANEL2, highlightthickness=1, highlightbackground=ui.LINE, highlightcolor=acc)
        box.pack(side="left", fill="x", expand=True)
        tk.Label(box, text="›", bg=C_PANEL2, fg=acc, font=(self.fam, 12, "bold")).pack(side="left", padx=(8, 0))
        self.entry = tk.Text(box, height=1, wrap="word", bg=C_PANEL2, fg=ui.TEXT, insertbackground=acc,
                             relief="flat", bd=0, padx=6, pady=8, font=(self.fam, 10), undo=True, width=1,
                             highlightthickness=0, selectbackground=ui.blend(acc, C_BG, 0.55), selectforeground="#ffffff")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<KeyRelease>", self.autogrow)
        ui.button(row, "MIC", lambda: self.pet.start_listening(), (self.fam, 9, "bold"), padx=10, pady=9).pack(
            side="left", padx=(8, 0), fill="y")
        ui.button(row, "SEND ▸", self.send, (self.fam, 9, "bold"), filled=True, padx=12, pady=9).pack(
            side="left", padx=(6, 0), fill="y")

        # messages
        mid = tk.Frame(w, bg=C_BG)
        mid.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(mid, bg=C_BG, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=C_BG)
        self.win_id = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self.on_resize)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        for wd in (self.canvas, self.inner):
            wd.bind("<MouseWheel>", self.on_wheel)
            wd.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
            wd.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.bubbles = []
        self.win.after(700, self.blink)

    def blink(self):
        """The little status dot pulses while she's online."""
        if not self.alive():
            return
        try:
            txt = self.status.cget("text")
            if txt.startswith("●") and self.status.cget("fg") in (C_GREEN, ui.blend(C_GREEN, C_PANEL, 0.6)):
                self.status.config(fg=ui.blend(C_GREEN, C_PANEL, 0.6) if self.status.cget("fg") == C_GREEN else C_GREEN)
        except tk.TclError:
            return
        self.win.after(700, self.blink)

    def build_keybar(self):
        bar = self.keybar = tk.Frame(self.win, bg=C_PANEL2, highlightthickness=1,
                                     highlightbackground=ui.blend(ui.THEME["warn"], C_BG, 0.5))
        bar.pack(fill="x")
        tk.Label(bar, text="[!] NO AI KEY. Paste a Claude (sk-ant...) or Gemini key to unlock real chat, or type "
                           "/getbrain for a free local AI. Until then I answer in offline mode.", bg=C_PANEL2,
                 fg=ui.THEME["warn"], font=self.f_small, wraplength=360, justify="left").pack(anchor="w", padx=10,
                                                                                               pady=(6, 2))
        row = tk.Frame(bar, bg=C_PANEL2)
        row.pack(fill="x", padx=10, pady=(0, 8))
        self.key_entry = tk.Entry(row, bg=C_PANEL, fg=C_TEXT, insertbackground=self.acc, relief="flat", show="*",
                                  font=(self.fam, 9), highlightthickness=1, highlightbackground=ui.LINE,
                                  highlightcolor=self.acc)
        self.key_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.key_entry.bind("<Return>", lambda e: self.save_key())
        ui.button(row, "SAVE KEY", self.save_key, self.f_small, filled=True, padx=10, pady=4).pack(
            side="left", padx=(6, 0))

    def drop_keybar(self):
        if self.keybar is not None:
            self.keybar.destroy()
            self.keybar = None

    def save_key(self):
        key = self.key_entry.get().strip()
        if len(key) < 20 or " " in key:
            return self.system_line("That doesn't look like a whole key. Copy all of it.", err=True)
        try:
            save_api_key(key)
        except OSError as exc:
            return self.system_line(f"Couldn't save the key: {exc}", err=True)
        self.drop_keybar()
        self.system_line("Key saved. Real chat unlocked.")

    def on_resize(self, e):
        self.canvas.itemconfigure(self.win_id, width=e.width)
        wrap = max(160, int(e.width * 0.70))
        for lbl in self.bubbles:
            try:
                lbl.config(wraplength=wrap)
            except tk.TclError:
                pass

    def on_wheel(self, e):
        self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units" if abs(e.delta) < 120 else "units")

    def scroll_end(self):
        self.win.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def autogrow(self, _e=None):
        lines = int(self.entry.index("end-1c").split(".")[0])
        self.entry.config(height=max(1, min(5, lines)))

    # ---- bubbles
    def add_bubble(self, role, text, ts="", animate=False):
        mine = role == "user"
        row = tk.Frame(self.inner, bg=C_BG)
        row.pack(fill="x", padx=12, pady=(10, 0))
        side = "right" if mine else "left"
        holder = tk.Frame(row, bg=C_BG)
        holder.pack(side=side)
        col = self.acc2 if mine else self.acc
        bg = ui.blend(col, C_BG, 0.88)
        fg = "#ffe9fb" if mine else "#e6fcff"
        stamp = ts or time.strftime("%H:%M")
        tag = tk.Label(holder, text=("YOU" if mine else "CAPRI") + f"  {stamp}", bg=C_BG, fg=col,
                       font=(self.fam, 7, "bold"))
        tag.pack(anchor="e" if mine else "w")
        line = tk.Frame(holder, bg=bg, highlightthickness=1, highlightbackground=ui.blend(col, C_BG, 0.62))
        line.pack()
        wrap = int(max(160, self.canvas.winfo_width() * 0.70))
        if mine:
            lbl = tk.Label(line, text=text, bg=bg, fg=fg, font=self.f_body, justify="left", anchor="w",
                           padx=12, pady=7, wraplength=wrap)
            lbl.pack(side="left")
            tk.Frame(line, bg=col, width=4).pack(side="left", fill="y")
        else:
            tk.Frame(line, bg=col, width=4).pack(side="left", fill="y")
            lbl = tk.Label(line, text="" if animate else text, bg=bg, fg=fg, font=self.f_body, justify="left",
                           anchor="w", padx=12, pady=7, wraplength=wrap)
            lbl.pack(side="left")
        self.bubbles.append(lbl)
        for wd in (row, holder, line, lbl, tag):
            wd.bind("<MouseWheel>", self.on_wheel)
        lbl.bind("<Button-1>", lambda e, t=text: self.copy(t))
        self.win.after(30, self.scroll_end)
        return lbl

    def system_line(self, text, err=False):
        row = tk.Frame(self.inner, bg=C_BG)
        row.pack(fill="x", padx=12, pady=(8, 0))
        color = ui.THEME["err"] if err else ui.DIM
        lbl = tk.Label(row, text=("[ERR] " if err else "[SYS] ") + text, bg=C_BG, fg=color, font=(self.fam, 8),
                       wraplength=int(max(160, self.canvas.winfo_width() * 0.92)), justify="left", anchor="w")
        lbl.pack(fill="x")
        self.bubbles.append(lbl)
        self.win.after(30, self.scroll_end)

    def copy(self, text):
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        self.set_status("● COPIED", self.acc)
        self.win.after(1200, lambda: self.set_status("● ONLINE", C_GREEN))

    def set_status(self, text, color=C_GREEN):
        self.status.config(text=text, fg=color)

    def set_face(self, key):
        self.face_override = key if key == "angry" else None
        if self.face_override:
            self.portrait.config(image=self.photo(key if key in self.pet.art.portraits else "idle"))

    def tick_avatar(self):
        if not self.alive():
            return
        av = getattr(self.pet.art, "avatar", None)
        if av and not self.face_override:
            key = "talk" if (self.busy or time.time() < self.pet.talk_until) else "idle"
            frames = av.get(key) or av.get("idle")
            if frames:
                self.av_i = (self.av_i + 1) % len(frames)
                k = (key, self.av_i)
                if k not in self.images:
                    self.images[k] = ImageTk.PhotoImage(frames[self.av_i])
                self.portrait.config(image=self.images[k])
        self.win.after(160, self.tick_avatar)

    # ---- sending
    def on_enter(self, e):
        if e.state & 0x1:  # shift
            return None
        self.send()
        return "break"

    def chip(self, payload):
        self.submit(payload)

    def send(self):
        text = self.entry.get("1.0", "end").strip()
        self.entry.delete("1.0", "end")
        self.autogrow()
        if text:
            self.submit(text)

    def submit(self, text):
        if text.startswith("/"):
            return self.command(text)
        if self.busy:
            return self.system_line("Hold on, still thinking about the last one.")
        self.add_bubble("user", text)
        self.history.append({"role": "user", "content": text, "ts": time.strftime("%H:%M")})
        self.busy = True
        self.set_status("▌TYPING…", self.acc)
        self.set_face("talk")
        self.show_typing()
        self.pet.react("think")
        now = time.time()
        mind = self.pet.mind
        mind.chatted(now)
        persona = (self.persona + " " + mind.context(now, self.pet.doing(), self.pet.activity_phrase())
                   + " " + self.pet.memory.context()).strip()
        offline = None if ai_available() else mind.offline_reply(text, now)
        snapshot = [{"role": m["role"], "content": m["content"]} for m in self.history[-20:]]
        threading.Thread(target=self.work, args=(snapshot, persona, offline), daemon=True).start()
        self.win.after(100, self.poll)

    def show_typing(self):
        self.typing_row = self.add_bubble("assistant", "●", animate=False)
        self.dots = 0

        def step():
            if self.typing_row is None:
                return
            self.dots = (self.dots + 1) % 4
            try:
                self.typing_row.config(text="● " * max(1, self.dots))
            except tk.TclError:
                return
            self.typing_job = self.win.after(350, step)
        step()

    def hide_typing(self):
        if self.typing_job:
            self.win.after_cancel(self.typing_job)
        if self.typing_row is not None:
            try:
                self.typing_row.master.master.master.destroy()  # row frame
            except tk.TclError:
                pass
            if self.typing_row in self.bubbles:
                self.bubbles.remove(self.typing_row)
        self.typing_row, self.typing_job = None, None

    def work(self, msgs, persona, offline=None):
        try:
            if offline:
                time.sleep(0.6)
            self.q.put(("ok", offline or llm_reply(msgs, persona)))
        except Exception as exc:
            self.q.put(("err", str(exc) or type(exc).__name__))

    def poll(self):
        try:
            kind, text = self.q.get_nowait()
        except queue.Empty:
            if self.alive():
                self.win.after(100, self.poll)
            return
        self.busy = False
        if not self.alive():
            return
        self.hide_typing()
        if kind == "ok":
            self.history.append({"role": "assistant", "content": text, "ts": time.strftime("%H:%M")})
            self.save_history()
            lbl = self.add_bubble("assistant", text, animate=True)
            self.typewrite(lbl, text, 0)
            self.pet.react("happy")
            self.pet.speak(text, priority=True, call=self.pet.take_route())
            try:
                if self.win.state() != "normal":                  # a voice command: show it above her instead
                    self.pet.say(text[:200], 9, speak=None)
            except tk.TclError:
                pass
        else:
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
            self.system_line("Couldn't reach the AI: " + text, err=True)
            self.set_status("● ERROR", C_RED)
            self.set_face("angry")
            self.pet.react("error")
            self.win.after(2500, self.reset_face)

    def reset_face(self):
        if self.alive():
            self.set_face("idle")
            self.set_status("● ONLINE", C_GREEN)

    def typewrite(self, lbl, text, i):
        if not self.alive():
            return
        i = min(len(text), i + 3)
        self.pet.talk_until = time.time() + 0.3
        try:
            lbl.config(text=text[:i])
        except tk.TclError:
            return
        self.scroll_end()
        if i < len(text):
            self.win.after(16, lambda: self.typewrite(lbl, text, i))
        else:
            lbl.bind("<Button-1>", lambda e, t=text: self.copy(t))
            self.reset_face()

    def command(self, text):
        parts = text.split(None, 2)
        cmd = parts[0].lower()
        p = self.pet
        if cmd == "/help":
            self.system_line("/focus [min]  /remind <min> <text>  /name <you>  /mood  /key <api key>  "
                             "/settings  /fly  /party  /aware  /voice  /fishkey  /pause  /mute  /volup  /shot  /lock  /press <keys>  "
                             "/type <text>  /click  /hands  /tag  /todo  /done  /roll  /coin  /8ball  /tp  /dance  "
                             "/sleep  /calm  /watch  /look  /ailines  /kill  /death  /rw  /rl  /gg  /kd  /roast  /match  /game  /hack  /simon  /sit  /ledges  /feed  /radio  /sfx  /birthday  /habit  /did  /note  /notes  /remember  /facts  /feel  "
                             "/journal  /day  /horoscope  /lore  /do  /stop  /agent  /preset  /powers  /size  /neon  /boot  /hear  /call  /open  /search  /brief  /desktop  /clip  /talk  /wake  /getears  /getbrain  /brain  /clear")
        elif cmd == "/clear":
            self.clear()
        elif cmd == "/focus":
            mins = float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "").isdigit() else FOCUS_MIN
            p.start_focus(mins)
            self.system_line(f"Focus timer started: {mins:g} min.")
        elif cmd == "/remind" and len(parts) == 3 and parts[1].replace(".", "").isdigit():
            p.add_reminder(float(parts[1]), parts[2])
            self.system_line(f"Okay, I'll ping you in {float(parts[1]):g} min.")
        elif cmd == "/name" and len(parts) >= 2:
            p.mind.user_name = " ".join(parts[1:])
            p.save_settings()
            self.system_line(f"Okay, I'll call you {p.mind.user_name}.")
        elif cmd == "/mood":
            self.system_line(f"Mood: {p.mind.mood(time.time())}. Affection: {p.mind.affection:.0f}/100.")
        elif cmd == "/key" and len(parts) >= 2:
            save_api_key(parts[1])
            self.drop_keybar()
            self.system_line("Key saved. Real chat unlocked.")
        elif cmd == "/watch":
            arg = parts[1].lower() if len(parts) > 1 else ""
            sp = p.spotter
            if arg == "on":
                if p.settings.get("ai_vision") or p.enable_vision(parent=self.win):
                    ok = p.start_spotter(manual=True)
                    self.system_line("Watching your screen. A little eye shows while I look." if ok
                                     else "Couldn't start. Do I have an AI key?", err=not ok)
                else:
                    self.system_line("Okay, I left it off.")
            elif arg == "off":
                p.stop_spotter()
                self.system_line("Stopped watching.")
            else:
                if sp and sp.active:
                    self.system_line(f"Watching: on ({'paused right now' if not sp.allowed else 'looking'}), every "
                                     f"{sp.interval:g}s. Sent {sp.stats['sent']}, skipped {sp.stats['static']} static. "
                                     f"Used today: {sp.budget.used_today() if sp.budget else 0}.")
                else:
                    self.system_line("Watching: off.  /watch on | off    (AI sees small screenshots; see Settings > AI)")
        elif cmd == "/look":
            if p.settings.get("ai_vision") or p.enable_vision(parent=self.win):
                p.look(text.split(None, 1)[1] if len(parts) > 1 else "")
                self.system_line("Looking...")
            else:
                self.system_line("Okay, I won't look.")
        elif cmd == "/ailines":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("on", "off"):
                p.settings["ai_lines"] = arg == "on"
                p.save_settings()
                self.system_line("AI-written lines: " + arg + ("" if arg == "off" else ("" if ai_available()
                                 else "  (needs an AI key; using presets until you add one)")))
            else:
                self.system_line("AI-written lines: " + ("on" if p.settings.get("ai_lines", True) else "off")
                                 + f"   used today: {p.ai_budget.used_today()}   /ailines on | off")
        elif cmd in GAME_COMMANDS:
            kind, count = GAME_COMMANDS[cmd]
            if cmd == "/kill" and len(parts) > 1 and parts[1].isdigit():
                count = max(1, min(5, int(parts[1])))
            p.game_event(kind, count)
            self.system_line(p.game.status())
        elif cmd == "/gg":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("win", "w", "loss", "l", "lose"):
                p.game_event("match_win" if arg in ("win", "w") else "match_loss")
                self.system_line(p.game.status())
                p.root.after(9000, p.end_game)                     # the recap comes after her reaction
            elif p.game:
                p.end_game()
                self.system_line("Game session over.")
            else:
                self.system_line("/gg win | loss    (ends the game session with a recap)", err=True)
        elif cmd == "/kd":
            self.system_line(p.game.status() if p.game else
                             "No game session. Launch a game, or start one with /kill or /death.")
        elif cmd == "/roast":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in gamemode.LEVELS:
                p.settings["roast"] = arg
                p.save_settings()
                if p.game:
                    p.game.level = arg
                self.system_line(f"Roast level: {arg}.")
            else:
                self.system_line("/roast off | mild | spicy    (now: " + p.settings.get("roast", "mild")
                                 + ")   off = only supportive, spicy = she'll tell you that was ass.")
        elif cmd == "/match":
            res = gamemode.parse_match(text.split(None, 1)[1] if len(parts) > 1 else "")
            if res:
                if not p.game:
                    p.start_game("other", manual=True)
                p.game.apply_result(res.get("rounds"), res.get("kd"))
                self.system_line(p.game.recap())
                g = p.game
                p.say_ai("recap", {"game": g.name, "kills": g.kills, "deaths": g.deaths, "rw": g.rounds_w,
                                   "rl": g.rounds_l, "minutes": int(g.minutes())}, g.recap(), 12, speak="priority")
                p.end_game(quiet=True)
            else:
                self.system_line("Tell me like /match 13-7 15/12   (rounds won-lost, then kills/deaths)", err=True)
        elif cmd == "/game":
            if len(parts) > 1 and parts[1].lower() == "end":
                p.end_game()
                self.system_line("Game session over.")
            else:
                self.system_line(p.game.status() if p.game else "No game running.")
                detectors = sum(len(v) for v in p.game_cfg.values())
                self.system_line(f"Automatic detection: {detectors} detector(s) loaded for "
                                 + (", ".join(p.game_cfg) or "no games") + ". Manual: /kill /death /rw /rl /ace /clutch.")
                for w in p.game_cfg_warnings[:3]:
                    self.system_line("game_events.json: " + w, err=True)
        elif cmd == "/sit":
            p.sit_somewhere()
        elif cmd == "/ledges":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg == "on":
                self.system_line("Screen ledges: on." if p.enable_ledges(parent=self.win)
                                 else "Okay, I left it off.")
            elif arg == "off":
                p.disable_ledges()
                self.system_line("Screen ledges: off. I stopped looking.")
            else:
                self.system_line(f"Screen ledges: {'on' if p.settings.get('ledges') else 'off'} "
                                 f"({len(p.ledges)} spot(s) in view).  /ledges on | off    /sit = perch on one")
        elif cmd == "/simon":
            p.open_simon()
        elif cmd == "/habit":
            today = time.strftime("%Y-%m-%d")
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "add" and len(parts) > 2:
                name = p.habits.add(text.split(None, 2)[2])
                p.save_settings()
                self.system_line(f"Habit added: {name}. Check it off with /did <number>." if name
                                 else "Couldn't add that (empty, duplicate, or you have 8 already).", err=not name)
            elif sub in ("rm", "remove", "del") and len(parts) > 2 and parts[2].isdigit():
                name = p.habits.remove(int(parts[2]))
                p.save_settings()
                self.system_line(f"Removed: {name}" if name else "Which one? /habit shows the numbers.", err=not name)
            else:
                for line in p.habits.lines(today):
                    self.system_line(line)
        elif cmd == "/did":
            today = time.strftime("%Y-%m-%d")
            ok, name = p.habits.check(int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0, today)
            if ok:
                p.save_settings()
                self.system_line(f"{name}: done.")
                p.react("happy")
            elif name:
                self.system_line(f"You already did {name} today.", err=True)
            else:
                self.system_line("Which one? /habit shows the numbers.", err=True)
        elif cmd == "/remember":
            fact = p.memory.remember(text.split(None, 1)[1]) if len(parts) > 1 else None
            p.save_settings()
            self.system_line(f"Got it: {fact}" if fact else "Tell me something new: /remember I have a dog named Rex",
                             err=not fact)
        elif cmd == "/forget":
            gone = p.memory.forget(int(parts[1])) if len(parts) > 1 and parts[1].isdigit() else None
            p.save_settings()
            self.system_line(f"Forgot: {gone}" if gone else "Which one? /facts shows the numbers.", err=not gone)
        elif cmd == "/facts":
            for line in p.memory.lines():
                self.system_line(line)
        elif cmd == "/note":
            body = text.split(None, 1)[1] if len(parts) > 1 else ""
            saved = p.add_note(body)
            self.system_line(f"Noted: {saved}" if saved else
                             ("Already in your notes." if body.strip() else "What should I note? /note <text>"),
                             err=not saved)
        elif cmd == "/notes":
            if len(parts) > 2 and parts[1].lower() in ("rm", "remove", "del") and parts[2].isdigit():
                gone = p.notes.remove(int(parts[2]))
                p.save_settings()
                self.system_line(f"Deleted note: {gone}" if gone else "Which one? /notes shows the numbers.",
                                 err=not gone)
            else:
                for line in p.notes.lines(text.split(None, 1)[1] if len(parts) > 1 else ""):
                    self.system_line(line)
        elif cmd == "/feel":
            today = time.strftime("%Y-%m-%d")
            if len(parts) > 1 and parts[1].isdigit() and 1 <= int(parts[1]) <= 5:
                p.journal.add(today, int(parts[1]), text.split(None, 2)[2] if len(parts) > 2 else "")
                p.save_settings()
                p.mind.chatted(time.time())
                self.system_line(p.journal.reply(int(parts[1]), p.rng))
            else:
                self.system_line("/feel 1-5 [note]   for example: /feel 4 good day", err=True)
        elif cmd == "/journal":
            for line in p.journal.lines():
                self.system_line(line)
        elif cmd == "/day":
            self.system_line(p.daylog.summary(time.strftime("%Y-%m-%d")))
            if not (p.aware and p.settings.get("track_time", True)) or not p.win32.ok:
                self.system_line("(Time tracking needs Windows, Awareness on, and 'Track time' on in Settings.)")
        elif cmd == "/horoscope":
            self.system_line(fun.horoscope(time.strftime("%Y-%m-%d"), p.settings.get("birthday", "")))
        elif cmd == "/lore":
            self.system_line(p.rng.choice(fun.LORE))
        elif cmd == "/hack":
            p.open_breach()
        elif cmd == "/feed":
            p.feed()
            self.system_line("Ramen served. Slurp.")
        elif cmd in ("/radio", "/sfx"):
            key = cmd[1:]
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("on", "off"):
                p.settings[key] = arg == "on"
                if key == "sfx":
                    p.sfx.enabled = arg == "on"
                p.save_settings()
                self.system_line(f"{key}: {arg}")
            else:
                self.system_line(f"/{key} on | off   (now: {'on' if p.settings.get(key, key == 'sfx') else 'off'})")
        elif cmd == "/birthday":
            bd = world.parse_birthday(parts[1] if len(parts) > 1 else "")
            if bd:
                p.settings["birthday"] = bd
                p.save_settings()
                self.system_line(f"Birthday saved: {bd}. I'll remember, choom.")
            else:
                self.system_line("Tell me like /birthday 03-27 (month-day).", err=True)
        elif cmd == "/tag":
            p.start_tag()
        elif cmd == "/roll":
            self.system_line(fun.roll(parts[1] if len(parts) > 1 else "", p.rng))
        elif cmd == "/coin":
            self.system_line(fun.coin(p.rng))
        elif cmd == "/8ball":
            self.system_line(fun.eight_ball(text.split(None, 1)[1] if len(parts) > 1 else "", p.rng))
        elif cmd == "/todo":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "add" and len(parts) > 2:
                added = p.todos.add(text.split(None, 2)[2])
                p.save_settings()
                self.system_line(f"Added: {added}" if added else "Couldn't add that.", err=not added)
            elif sub == "clear":
                self.system_line(f"Cleared {p.todos.clear_done()} finished item(s).")
                p.save_settings()
            else:
                for line in p.todos.lines():
                    self.system_line(line)
        elif cmd == "/done":
            done = p.todos.finish(int(parts[1])) if len(parts) > 1 and parts[1].isdigit() else None
            if done:
                self.system_line(f"Done: {done}")
                p.react("happy")
            else:
                self.system_line("Which one? /todo shows the numbers.", err=True)
        elif cmd == "/settings":
            p.open_settings()
        elif cmd in HAND_COMMANDS:
            ok, msg = p.hands_do(*HAND_COMMANDS[cmd])
            self.system_line(msg, err=not ok)
        elif cmd in ("/press", "/type", "/click"):
            arg = text.split(None, 1)[1] if len(parts) > 1 else None
            action = cmd[1:]
            label = {"press": "Pressing keys", "type": "Typing", "click": "Clicking"}[action]
            ok, msg = p.queue_action(action, arg, label, 5)
            self.system_line(msg, err=not ok)
        elif cmd == "/hands":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("visual", "media"):
                p.set_hands(arg)
                self.system_line("Hands: " + hands.LEVEL_NAMES[arg])
            else:
                self.system_line("/hands visual | media   (Full control is switched on in Settings)   now: "
                                 + hands.LEVEL_NAMES[p.hands.level])
        elif cmd in ("/fly", "/zoom", "/orbit"):
            p.start_fly(cmd[1:])
        elif cmd == "/party":
            p.party()
        elif cmd == "/aware":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("on", "off"):
                p.set_aware(arg == "on")
            else:
                self.system_line("/aware on | off   (now: " + ("on" if p.aware else "off") + ")")
        elif cmd == "/fishkey":
            arg = parts[1] if len(parts) > 1 else ""
            if arg.lower() in ("off", "clear", "remove"):
                clear_fish_key()
                msg = "Fish Audio key removed. Back to the system voice."
            elif len(arg) >= 16:
                save_fish_key(arg)
                msg = "Fish Audio key saved. Using Capri's real voice (her lines get sent to Fish Audio)."
            else:
                return self.system_line("/fishkey <Fish Audio API key>   or   /fishkey off   (voice now: "
                                        + p.speaker.engine + ")")
            p.speaker.stop()
            p.speaker = make_speaker()
            self.system_line(msg)
            p.say("Testing, one two. Is this the real me?", 5, speak="priority")
        elif cmd == "/do":
            ok, why = p.start_agent(text.split(None, 1)[1] if len(parts) > 1 else "")
            if not ok:
                self.system_line(why, err=True)
        elif cmd == "/stop":
            if p.agent is not None:
                p.stop_agent()
                self.system_line("Stopping...")
            else:
                self.system_line("I'm not doing anything.")
        elif cmd == "/agent":
            sub = parts[1].lower() if len(parts) > 1 else ""
            if sub == "on":
                self.system_line("Tasks are on. Try /do ..." if p.enable_agent(self.win)
                                 else "Okay, tasks stay off.")
            elif sub == "off":
                p.settings["agent"] = False
                p.save_settings()
                p.stop_agent()
                self.system_line("Tasks are off.")
            else:
                self.system_line("Tasks: " + ("on" if p.settings.get("agent") else "off")
                                 + "  (/agent on | off).  Needs Full control and a Claude or Gemini key.  Then: /do <task>")
        elif cmd == "/talk":
            p.start_listening()
        elif cmd == "/open" or cmd == "/search":
            what = " ".join(parts[1:])
            if not what:
                self.system_line("/open discord   /open youtube   /search best crosshair for valorant   "
                                 "(opens apps and sites directly, no AI)", err=True)
            else:
                p.open_thing(("search " if cmd == "/search" else "open ") + what)
        elif cmd == "/desktop":
            p.do_control("desktop")
        elif cmd == "/brief":
            p.run_brief()
        elif cmd == "/call":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("on", "join"):
                if p.enable_call(self.win, join=arg == "join"):
                    self.system_line("Call mode: starting. Say 'Capri ...' in the call.")
            elif arg == "off":
                if p.call_active():
                    p.stop_call()
                self.system_line("Call mode is off.")
            elif arg == "setup":
                self.system_line(CABLE_HELP)
            else:
                ok, why = p.call_ready()
                self.system_line("Call mode: " + ("ON, in the call" if p.call_active() else "off")
                                 + ("" if ok else "\nNot ready: " + why)
                                 + "\n/call on (listen where you already are)   /call join (she joins Discord, needs tasks)"
                                   "   /call off   /call setup")
        elif cmd == "/hear":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg == "on":
                self.system_line("I can hear your PC." if p.enable_hear(self.win) else "Okay, not listening to the PC.")
            elif arg == "off":
                p.disable_hear()
            elif arg in ("last", "summarize", "summary", "recap"):
                p.hear_now("last" if arg == "last" else "summarize")
            else:
                on = p.hear is not None and p.hear.running
                self.system_line("Hearing the PC: " + ("ON" if on else "off")
                                 + (f"  (holding {p.hear.ring.seconds_held():.0f}s of audio in memory)" if on else "")
                                 + "\n/hear on | off | last (what they just said) | summarize")
        elif cmd == "/gethear":
            if hearing.installed():
                self.system_line("The PC-audio helper is already installed. /hear on")
            else:
                p.install_hear()
        elif cmd == "/boot":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("on", "off"):
                p.settings["boot_anim"] = arg == "on"
                p.save_settings()
                self.system_line("Launch animation: " + arg)
            else:
                p.start_boot(first=arg == "first", greet=False)
        elif cmd == "/neon":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg == "outline":
                on = (parts[2].lower() if len(parts) > 2 else "") == "on"
                p.settings["outline"] = on
                p.save_settings()
                p.clear_sprite_caches()
                self.system_line("Glowing outline: " + ("on (needs a neon colour)" if on else "off"))
            elif arg in neon.COLORS or arg == "off":
                p.set_neon(arg)
                self.system_line("Neon: " + arg)
            else:
                self.system_line("/neon cyan | magenta | yellow | green | red | white | off   /neon outline on | off   (now: "
                                 + p.neon_name + ", outline " + ("on" if p.outline_on() else "off") + ")")
        elif cmd == "/preset":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in presets.PRESETS:
                if p.apply_preset(arg, self.win):
                    self.system_line(f"Preset {presets.LABELS[arg]}: " + presets.SUMMARY[arg])
                else:
                    self.system_line("Okay, nothing changed.")
            else:
                for name in presets.ORDER:
                    self.system_line(f"/preset {name}  ({presets.LABELS[name]}): {presets.SUMMARY[name]}")
                self.system_line("Right now: " + presets.LABELS[presets.detect(p.settings)])
        elif cmd == "/powers":
            for line in presets.table(p.settings):
                self.system_line(line)
        elif cmd == "/size":
            arg = " ".join(parts[1:]).lower() if len(parts) > 1 else ""
            if arg in ("auto on", "auto off", "auto"):
                p.set_auto_size(arg != "auto off")
                self.system_line("Auto size: " + ("on" if p.auto_size else "off"))
            elif arg in ("bigger", "larger", "smaller"):
                p.set_size(sizing.step(p.size_base, -1 if arg == "smaller" else 1))
            elif sizing.parse(arg):
                p.set_size(sizing.parse(arg))
            else:
                self.system_line(f"Size: {int(p.size_base * 100)}%  (now showing {int(p.size_now * 100)}%)   "
                                 "/size tiny | small | normal | large | huge | 70% | bigger | smaller | auto on | auto off")
        elif cmd == "/clip":
            pm = clip.parse_mode(" ".join(parts[1:]))
            if pm:
                p.run_clip(*pm)
            else:
                self.system_line("/clip  (explain)   /clip summarize   /clip translate french   /clip fix   /clip reply",
                                 err=True)
        elif cmd == "/wake":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg == "on":
                self.system_line("Listening for my name." if p.enable_wake(self.win) else "Okay, staying deaf.")
            elif arg == "off":
                p.disable_wake()
                self.system_line("Wake word listening is off.")
            else:
                self.system_line("Wake word: " + ("ON" if p.wake is not None and p.wake.running else "off")
                                 + "   /wake on | off   (say 'Hey Capri ...' or 'Choom ...')")
        elif cmd == "/getears":
            p.install_ears()
        elif cmd == "/getbrain":
            arg = parts[1].lower() if len(parts) > 1 else "small"
            if arg == "remove":
                p.remove_brain()
            elif arg in localai.MODELS:
                p.install_brain(arg)
            else:
                self.system_line("/getbrain  (small, 1.1 GB)   /getbrain big  (3B, 2.1 GB, smarter)   /getbrain remove\n"
                                 "Or install Ollama and she'll use it automatically.", err=True)
        elif cmd == "/brain":
            arg = parts[1].lower() if len(parts) > 1 else ""
            if arg in ("auto", "cloud", "local"):
                p.set_brain(arg)
            self.system_line(f"AI brain: {BRAIN['mode']}  (/brain auto | cloud | local)\n"
                             f"Cloud key: {'yes' if read_api_key() else 'no'}   Local AI: {LOCAL_AI.status()}\n"
                             "auto = cloud when you have a key (local if you're offline), local if no key.")
        elif cmd == "/getvoice":
            if voice.edge_installed():
                p.speaker = make_speaker()
                self.system_line(f"The free neural voice is already installed. Voice engine: {p.speaker.engine}.")
                p.say("Testing, one two. Is this the real me?", 5, speak="priority")
            else:
                self.system_line("Installing the free neural voice (edge-tts)... this takes a few seconds.")
                threading.Thread(target=p.install_voice, daemon=True).start()
        elif cmd == "/voice":
            lvl = parts[1].lower() if len(parts) > 1 else ""
            if lvl in ("off", "replies", "chatty"):
                p.set_voice(lvl)
            else:
                self.system_line("/voice off | replies | chatty   (now: " + p.settings.get("voice", "chatty") + ")")
        elif cmd == "/tp":
            p.teleport()
        elif cmd == "/dance":
            p.go("dance", 3.5)
        elif cmd == "/sleep":
            p.go("sleep")
        elif cmd == "/calm":
            p.toggle_calm()
        else:
            self.system_line("Unknown command. Try /help")

    # ---- misc
    def clear(self):
        self.history = []
        self.save_history()
        for ch in self.inner.winfo_children():
            ch.destroy()
        self.bubbles = []
        self.add_bubble("assistant", "Fresh start. What's up?", animate=False)

    def toggle_pin(self):
        self.topmost = not self.topmost
        self.win.attributes("-topmost", self.topmost)
        self.pin_btn.config(text="[PINNED]" if self.topmost else "[PIN]")
        self.pet.settings["chat_topmost"] = self.topmost
        self.pet.save_settings()

    def save_history(self):
        save_json(os.path.join(data_dir(), "chat_history.json"), self.history[-200:])

    def alive(self):
        try:
            return bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def rect(self):
        try:
            if not self.alive() or self.win.state() == "withdrawn":
                return None
            x, y = self.win.winfo_rootx(), self.win.winfo_rooty()
            return (x, y, x + self.win.winfo_width(), y + self.win.winfo_height(), "chat")
        except tk.TclError:
            return None

    def close(self):
        try:
            self.pet.settings["chat_geom"] = self.win.geometry()
            self.pet.save_settings()
            self.save_history()
            self.win.destroy()
        except tk.TclError:
            pass
        self.pet.chat = None


class SettingsWindow:
    """One place for everything: hands (what she may press/click), voice, behaviour and keys."""

    def __init__(self, pet):
        self.pet = pet
        self.fam = f = ui.mono_font(pet.root)
        self.acc = ui.acc()
        w = self.win = tk.Toplevel(pet.root)
        w.title("CAPRI//CONFIG")
        w.configure(bg=C_BG)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", self.close)
        ui.rule(w, 12, self.acc, C_BG).pack(fill="x")
        head = tk.Frame(w, bg=C_PANEL)
        head.pack(fill="x")
        col = tk.Frame(head, bg=C_PANEL)
        col.pack(side="left", padx=14, pady=8)
        tk.Label(col, text="CAPRI//CONFIG", bg=C_PANEL, fg=self.acc, font=(f, 14, "bold")).pack(anchor="w")
        tk.Label(col, text="SYSTEM PERMISSIONS  ·  VOICE  ·  AI", bg=C_PANEL, fg=ui.DIM, font=(f, 7)).pack(anchor="w")
        ui.rule(w, 8, ui.blend(self.acc, C_BG, 0.5), C_BG, notch=False).pack(fill="x")
        foot = tk.Frame(w, bg=C_PANEL)
        foot.pack(side="bottom", fill="x")
        ui.rule(foot, 8, self.acc, C_PANEL, notch=False).pack(fill="x")
        ui.button(foot, "[ DONE ]", self.close, (f, 9, "bold"), filled=True, padx=22, pady=6).pack(pady=8)
        mid = tk.Frame(w, bg=C_BG)
        mid.pack(fill="both", expand=True)
        canvas = tk.Canvas(mid, bg=C_BG, highlightthickness=0, bd=0, width=430)
        bar = tk.Scrollbar(mid, orient="vertical", command=canvas.yview, bg=C_PANEL2, troughcolor=C_BG,
                           activebackground=self.acc, bd=0, relief="flat", width=10, highlightthickness=0)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        body = tk.Frame(canvas, bg=C_BG)
        canvas.create_window(0, 0, window=body, anchor="nw", width=410)
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self.canvas = canvas
        for wd in (canvas, body, w):
            wd.bind("<MouseWheel>", lambda e: canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
            wd.bind("<Button-4>", lambda e: canvas.yview_scroll(-2, "units"))
            wd.bind("<Button-5>", lambda e: canvas.yview_scroll(2, "units"))
        pad = tk.Frame(body, bg=C_BG)
        pad.pack(fill="x", padx=8, pady=(0, 8))
        self.build_presets(pad)
        self.build_size(pad)
        self.build_hands(pad)
        self.build_voice(pad)
        self.build_gaming(pad)
        self.build_ai(pad)
        self.build_local(pad)
        self.build_behavior(pad)
        self.build_keys(pad)
        w.update_idletasks()
        h = min(700, pet.sh - 80)
        w.geometry(f"460x{h}+{max(0, pet.sw // 2 - 230)}+{max(0, pet.sh // 2 - h // 2)}")

    # ---- small widgets
    def section(self, parent, title, note=""):
        head, _, sub = title.partition(":")
        outer = tk.Frame(parent, bg=ui.blend(self.acc, C_BG, 0.78))
        outer.pack(fill="x", pady=(10, 0))
        box = tk.Frame(outer, bg=C_PANEL)
        box.pack(fill="x", padx=1, pady=1)
        bar = tk.Frame(box, bg=C_PANEL)
        bar.pack(fill="x", padx=0, pady=(8, 2))
        tk.Frame(bar, bg=self.acc, width=4, height=16).pack(side="left", padx=(0, 8))
        tk.Label(bar, text=">> " + head.strip().upper(), bg=C_PANEL, fg=self.acc, font=(self.fam, 10, "bold")).pack(
            side="left")
        tk.Frame(bar, bg=ui.blend(self.acc, C_PANEL, 0.7), height=1).pack(side="left", fill="x", expand=True,
                                                                            padx=(8, 10))
        if sub.strip():
            sub = sub.strip()
            note = sub[0].upper() + sub[1:] + (". " if note else "") + note
        if note:
            tk.Label(box, text=note, bg=C_PANEL, fg=ui.DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(
                anchor="w", padx=12, pady=(0, 4))
        return box

    def check(self, parent, text, key, default, command=None, state="normal"):
        var = tk.BooleanVar(value=bool(self.pet.settings.get(key, default)))

        def changed():
            self.pet.settings[key] = var.get()
            self.pet.save_settings()
            if command:
                command(var.get())
        cb = ui.NeonCheck(parent, text=text, variable=var, command=changed, font=(self.fam, 9), state=state,
                          wraplength=335)
        cb.pack(fill="x", padx=12, pady=2)
        return cb

    def radio(self, parent, text, var, value, command, note=""):
        rb = ui.NeonRadio(parent, text=text, variable=var, value=value, command=command, font=(self.fam, 9, "bold"))
        rb.pack(fill="x", padx=12, pady=(3, 0))
        if note:
            tk.Label(parent, text=note, bg=C_PANEL, fg=ui.DIM, font=(self.fam, 8), wraplength=320,
                     justify="left", anchor="w").pack(fill="x", padx=(40, 10))
        return rb

    def entry_row(self, parent, label, command, button="SAVE"):
        tk.Label(parent, text=label, bg=C_PANEL, fg=ui.DIM, font=(self.fam, 8), wraplength=345,
                 justify="left").pack(anchor="w", padx=12, pady=(6, 0))
        row = tk.Frame(parent, bg=C_PANEL)
        row.pack(fill="x", padx=12, pady=(2, 10))
        e = tk.Entry(row, bg=C_PANEL2, fg=ui.TEXT, insertbackground=self.acc, relief="flat", show="*",
                     font=(self.fam, 9), highlightthickness=1, highlightbackground=ui.LINE, highlightcolor=self.acc)
        e.pack(side="left", fill="x", expand=True, ipady=4)
        ui.button(row, button, lambda: command(e), (self.fam, 8, "bold"), filled=True, padx=10, pady=4).pack(
            side="left", padx=(6, 0))
        return e

    # ---- sections
    def build_hands(self, parent):
        box = self.section(parent, "HANDS: what Capri may do on your computer",
                           "Real key presses only ever come from your own commands or from reflexes you switch on. "
                           "Never from what the AI says. Lowering the level takes effect instantly.")
        self.hands_var = tk.StringVar(value=self.pet.hands.level)
        for value, label, note in (
                ("visual", "Visual only", "She mimes typing along with you. Sends nothing to your computer."),
                ("media", "Media keys", "Play/pause, next/prev, volume, mute, screenshot, lock screen, when you ask "
                                        "(/pause /mute /volup /shot /lock ...)."),
                ("full", "Full control", "Also presses any key combo, types text and clicks when you ask "
                                         "(/press ctrl+s, /type hello, /click). 5-second countdown first. "
                                         "Needs your confirmation.")):
            self.radio(box, label, self.hands_var, value, self.pick_hands, note)
        tk.Label(box, text="Reflexes: things she does by herself (Full control only). She warns you 10 seconds "
                           "ahead and you can cancel by clicking her.", bg=C_PANEL, fg=C_DIM, font=(self.fam, 8),
                 wraplength=345, justify="left").pack(anchor="w", padx=10, pady=(8, 2))
        self.reflex_boxes = [
            self.check(box, "Lock my screen when I've been away for 15 minutes", "reflex_lock", False),
            self.check(box, "Pause video/music when I step away for 5 minutes (needs Awareness)", "reflex_pause", False)]
        self.refresh_reflexes()
        self.check(box, "Mime typing along while I'm busy (Windows)", "type_along", True)
        tk.Frame(box, bg=C_PANEL, height=6).pack()

    def pick_hands(self):
        value = self.hands_var.get()
        if value == "full" and self.pet.hands.level != "full":
            from tkinter import messagebox
            ok = messagebox.askyesno(
                "Turn on Full control?",
                "Full control lets Capri press any keys, type text and click in ANY app when you tell her to, "
                "and run any reflexes you switch on.\n\nA wrong command can send a message, close something or "
                "lose work. She never acts because of what the AI says, and you can lower this at any time.\n\n"
                "Turn on Full control?", parent=self.win, default="no", icon="warning")
            if not ok:
                self.hands_var.set(self.pet.hands.level)
                return
        self.pet.set_hands(value)
        self.refresh_reflexes()

    def refresh_reflexes(self):
        for cb in self.reflex_boxes:
            cb.config(state="normal" if self.pet.hands.level == "full" else "disabled")

    def build_voice(self, parent):
        box = self.section(parent, "VOICE")
        self.voice_var = tk.StringVar(value=self.pet.settings.get("voice", "chatty"))
        for value, label in (("off", "Off"), ("replies", "Replies & alerts only"), ("chatty", "Chatty")):
            self.radio(box, label, self.voice_var, value, lambda: self.pet.set_voice(self.voice_var.get()))
        row = tk.Frame(box, bg=C_PANEL)
        row.pack(fill="x", padx=10, pady=(6, 0))
        flat_button(row, "TEST VOICE", lambda: self.pet.say("Testing, one two. Is this the real me?", 5, speak="priority"),
                    C_PANEL2, C_GREEN, "#26263a", (self.fam, 8, "bold"), 10, 4).pack(side="left")
        self.engine_lbl = tk.Label(row, text="", bg=C_PANEL, fg=C_DIM, font=(self.fam, 8))
        self.engine_lbl.pack(side="left", padx=8)
        self.entry_row(box, "Fish Audio key for Capri's real voice (blank + SAVE removes it). Her lines are sent "
                            "to Fish Audio.", self.save_fish)
        self.show_engine()

    def show_engine(self):
        self.engine_lbl.config(text="Engine: " + {"fish": "Capri's voice (Fish Audio)", "system": "system voice"}.get(
            self.pet.speaker.engine, "none found"))

    def save_fish(self, entry):
        self.pet.set_fish_key(entry.get().strip())
        entry.delete(0, "end")
        self.show_engine()

    def build_gaming(self, parent):
        box = self.section(parent, "GAMING",
                           "When a game is in front (Windows, Awareness on) she keeps small and quiet and comments on "
                           "your play. Tell her what happened with /kill /death /rw /rl, or set up automatic "
                           "detection (see the README).")
        self.roast_var = tk.StringVar(value=self.pet.settings.get("roast", "mild"))
        for value, label, note in (
                ("off", "Supportive only", "Hype when you do well, kind words when you die."),
                ("mild", "Light roasts (default)", "Playful teasing when you die: tragic, gonk, skill issue."),
                ("spicy", "Spicy", "She'll tell you that was ass. Mild swearing, no slurs.")):
            self.radio(box, label, self.roast_var, value, self.pick_roast, note)
        self.check(box, "Stay small and quiet while a game is in front", "game_quiet", True)
        self.check(box, "Go quiet during calls and meetings (Windows: Zoom/Meet/Teams in front, or Discord, Zoom "
                        "etc. using your mic)", "meeting_quiet", True)
        tk.Frame(box, bg=C_PANEL, height=6).pack()

    def pick_roast(self):
        v = self.roast_var.get()
        self.pet.settings["roast"] = v
        self.pet.save_settings()
        if self.pet.game:
            self.pet.game.level = v
        self.pet.say({"off": "Only nice words. For now.", "mild": "Light roasts it is.",
                      "spicy": "Spicy mode. Don't cry."}[v], 4, speak=None)

    def build_ai(self, parent):
        box = self.section(parent, "AI",
                           "With a key (Claude or Gemini) she writes her own lines instead of preset ones. Presets "
                           "are only used with no key, no internet, or when the daily limit is hit.")
        self.check(box, "AI-written lines (pokes, chatter, check-ins, game comments)", "ai_lines", True)
        self.vision_var = tk.BooleanVar(value=bool(self.pet.settings.get("ai_vision", False)))
        ui.NeonCheck(box, text="AI Spotter: let her watch my screen and comment (sends screenshots to the AI)",
                       variable=self.vision_var, command=self.toggle_vision, bg=C_PANEL, fg=C_TEXT,
                       selectcolor=C_PANEL2, activebackground=C_PANEL, activeforeground=C_TEXT, anchor="w",
                       font=(self.fam, 9), highlightthickness=0, bd=0, wraplength=335, justify="left").pack(
            fill="x", padx=12, pady=2)
        tk.Label(box, text="While watching, a small shrunken screenshot is SENT to your AI provider every few seconds "
                           "(only when the screen changed). It uses your API credits (roughly $1-3 an hour with "
                           "Claude), is never saved by Capri, and pauses on banking, password and private windows. "
                           "It starts by itself when a game is in front; /watch on works for anything else.",
                 bg=C_PANEL, fg=C_DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(
            anchor="w", padx=10, pady=(2, 4))
        tk.Label(box, text="Look every:", bg=C_PANEL, fg=C_DIM, font=(self.fam, 8)).pack(anchor="w", padx=10)
        self.interval_var = tk.IntVar(value=int(self.pet.settings.get("vision_interval", 6)))
        row = tk.Frame(box, bg=C_PANEL)
        row.pack(anchor="w", padx=10, pady=(0, 8))
        for secs in (4, 6, 10):
            ui.NeonRadio(row, text=f"{secs}s", variable=self.interval_var, value=secs, command=self.pick_interval,
                           bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2, activebackground=C_PANEL,
                           activeforeground=C_TEXT, font=(self.fam, 9), highlightthickness=0, bd=0).pack(side="left",
                                                                                                         padx=(0, 10))

    def build_presets(self, parent):
        pet = self.pet
        cur = presets.detect(pet.settings)
        box = self.section(parent, "QUICK SETUP",
                           "One button for how much she's allowed to do (control, microphone, screen). You can still "
                           "switch every single thing on or off below.")
        row = tk.Frame(box, bg=C_PANEL)
        row.pack(anchor="w", padx=10, pady=(2, 4))
        for name in presets.ORDER:
            on = cur == name
            flat_button(row, presets.LABELS[name], lambda n=name: pet.apply_preset(n, self.win),
                        C_GREEN if on else C_PANEL2, C_BLACK if on else C_TEXT, "#3dffa0",
                        (self.fam, 10, "bold"), 20, 8).pack(side="left", padx=(0, 6))
        what = presets.SUMMARY.get(cur, "You've set the switches yourself. Pick a preset to set them all at once.")
        tk.Label(box, text=f"Now: {presets.LABELS[cur]}. {what}", bg=C_PANEL, fg=C_DIM, font=(self.fam, 8),
                 wraplength=345, justify="left").pack(anchor="w", padx=10, pady=(2, 2))
        tk.Label(box, text="Auto-lock / auto-pause when you walk away (Reflexes) are never part of a preset.",
                 bg=C_PANEL, fg=C_DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(
            anchor="w", padx=10, pady=(0, 6))

    def build_size(self, parent):
        pet = self.pet
        box = self.section(parent, "SIZE & LOOK", "How big she is. You can also say 'Capri, get bigger / smaller / tiny' "
                                           "or type /size.")
        sizes = (("tiny", 0.5), ("small", 0.8), ("normal", 1.0), ("large", 1.5), ("huge", 2.0))
        near = min(sizes, key=lambda kv: abs(kv[1] - pet.size_base))[0]
        self.size_var = tk.StringVar(value=near)
        for chunk in (sizes[:3], sizes[3:]):
            row = tk.Frame(box, bg=C_PANEL)
            row.pack(anchor="w", padx=12, pady=(2, 0))
            for name, val in chunk:
                ui.NeonRadio(row, text=f"{name.title()} {int(val * 100)}%", variable=self.size_var, value=name,
                             font=(self.fam, 8), command=lambda v=val: pet.set_size(v, announce=False)).pack(
                    side="left", padx=(0, 12))
        self.check(box, "Let her resize herself (smaller while you game or focus, bigger when she's excited)",
                   "auto_size", True, pet.set_auto_size)
        tk.Label(box, text="Neon look: a glowing outline, speed ghosts when she flies, and coloured speech bubbles.",
                 bg=C_PANEL, fg=ui.DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(
            anchor="w", padx=12, pady=(6, 0))
        self.neon_var = tk.StringVar(value=pet.neon_name)
        names = ("off",) + tuple(neon.COLORS)
        for chunk in (names[:4], names[4:]):                         # two rows so nothing is cut off
            nrow = tk.Frame(box, bg=C_PANEL)
            nrow.pack(anchor="w", padx=12, pady=(2, 4))
            for name in chunk:
                ui.NeonRadio(nrow, text=name.title(), variable=self.neon_var, value=name, font=(self.fam, 8),
                             swatch=None if name == "off" else neon.hex_of(neon.COLORS[name]),
                             command=lambda n=name: pet.set_neon(n)).pack(side="left", padx=(0, 10))
        self.check(box, "Glowing outline around her (off by default; needs a neon colour above)", "outline", False,
                   lambda v: pet.clear_sprite_caches())
        tk.Frame(box, bg=C_PANEL, height=4).pack()

    def build_local(self, parent):
        pet = self.pet
        box = self.section(parent, "LOCAL AI & VOICE INPUT",
                           "A free AI that runs on YOUR computer (no key, works offline, nothing sent anywhere) and "
                           "talking to her with your voice (speech is turned into text on your computer too).")
        self.brain_var = tk.StringVar(value=BRAIN["mode"])
        for value, label, note in (
                ("auto", "Automatic", "Cloud AI when you have a key (local AI if you're offline); local AI otherwise."),
                ("cloud", "Cloud only", "Always your Claude/Gemini key."),
                ("local", "Local only", "Always the AI on this computer. Nothing leaves it.")):
            self.radio(box, label, self.brain_var, value, lambda: pet.set_brain(self.brain_var.get()), note)
        tk.Label(box, text="Local AI now: " + LOCAL_AI.status(), bg=C_PANEL, fg=C_DIM, font=(self.fam, 8),
                 wraplength=340, justify="left").pack(anchor="w", padx=10, pady=(6, 2))
        row = tk.Frame(box, bg=C_PANEL)
        row.pack(anchor="w", padx=10, pady=(2, 4))
        flat_button(row, "INSTALL LOCAL AI (1.1 GB)", lambda: pet.install_brain("small"), C_PANEL2, C_GREEN,
                    "#26263a", (self.fam, 8), 8, 4).pack(side="left", padx=(0, 6))
        flat_button(row, "BIGGER (2.1 GB)", lambda: pet.install_brain("big"), C_PANEL2, C_TEXT, "#26263a",
                    (self.fam, 8), 8, 4).pack(side="left")
        tk.Label(box, text="Voice input: " + ("installed. Ctrl+Alt+C, the MIC button or /talk."
                                              if listen.installed() else "not installed yet."),
                 bg=C_PANEL, fg=C_DIM, font=(self.fam, 8), wraplength=340, justify="left").pack(
            anchor="w", padx=10, pady=(6, 2))
        flat_button(box, "INSTALL VOICE INPUT", pet.install_ears, C_PANEL2, C_GREEN, "#26263a", (self.fam, 8), 8, 4).pack(
            anchor="w", padx=10, pady=(0, 6))
        self.hear_var = tk.BooleanVar(value=pet.hear is not None and pet.hear.running)

        def toggle_hear():
            if self.hear_var.get():
                if not pet.enable_hear(self.win):
                    self.hear_var.set(False)
            else:
                pet.disable_hear()
        ui.NeonCheck(box, text="Let her hear my PC's audio (music, videos, calls: she dances to the beat and can "
                                 "tell you what was just said)", variable=self.hear_var, command=toggle_hear,
                       bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2, activebackground=C_PANEL, activeforeground=C_TEXT,
                       anchor="w", justify="left", font=(self.fam, 9), highlightthickness=0, bd=0,
                       wraplength=335).pack(fill="x", padx=12, pady=2)
        self.check(box, "Dance to music when she hears it", "hear_dance", True)
        tk.Label(box, text="Call mode: she listens to your Discord call through the PC audio and answers your friends "
                           "out loud when they say 'Capri'. Needs a virtual audio cable (type /call setup).",
                 bg=C_PANEL, fg=C_DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(
            anchor="w", padx=10, pady=(4, 2))
        flat_button(box, "START / STOP CALL MODE",
                    lambda: pet.stop_call() if pet.call_active() else pet.enable_call(self.win), C_PANEL2, C_GREEN,
                    "#26263a", (self.fam, 8), 8, 4).pack(anchor="w", padx=10, pady=(0, 6))
        self.check(box, "Allow the microphone (push-to-talk: hotkey, MIC button, /talk)", "mic", True)
        self.check(box, "Hotkey Ctrl+Alt+C to talk to her (Windows, restart to apply)", "talk_hotkey", True)
        self.wake_var = tk.BooleanVar(value=self.pet.wake is not None and self.pet.wake.running)

        def toggle_wake():
            if self.wake_var.get():
                if not pet.enable_wake(self.win):
                    self.wake_var.set(False)
            else:
                pet.disable_wake()
        ui.NeonCheck(box, text='Always listen for "Hey Capri" / "Choom" (mic stays open, speech stays on this '
                                 'computer)', variable=self.wake_var, command=toggle_wake, bg=C_PANEL, fg=C_TEXT,
                       selectcolor=C_PANEL2, activebackground=C_PANEL, activeforeground=C_TEXT, anchor="w",
                       justify="left", font=(self.fam, 9), highlightthickness=0, bd=0, wraplength=335).pack(
            fill="x", padx=12, pady=2)
        tk.Frame(box, bg=C_PANEL, height=4).pack()

    def toggle_vision(self):
        if self.vision_var.get():
            if not self.pet.enable_vision(parent=self.win):
                self.vision_var.set(False)
        else:
            self.pet.disable_vision()

    def pick_interval(self):
        self.pet.settings["vision_interval"] = int(self.interval_var.get())
        self.pet.save_settings()

    def build_behavior(self, parent):
        box = self.section(parent, "BEHAVIOUR")
        self.check(box, "Calm mode (she stays put and stops chatting)", "calm", False, self.pet.set_calm)
        self.check(box, "Check-ins (water, stretch, eat reminders)", "checkins", True, self.pet.set_checkins)
        self.check(box, "Fly around the screen", "fly_enabled", True)
        self.check(box, "Launch animation when I start (click her to skip it)", "boot_anim", True)
        self.check(box, "Sound effects (blips and jingles)", "sfx", True,
                   lambda v: setattr(self.pet.sfx, "enabled", bool(v)))
        self.check(box, "Night City Radio chatter (a DJ drop every few minutes)", "radio", False)
        self.check(box, "Track time per kind of app for the daily /day recap (minutes only, no titles)",
                   "track_time", True, state="normal" if self.pet.win32.ok else "disabled")
        self.auto_var = tk.BooleanVar(value=autostart.is_enabled())
        ui.NeonCheck(box, text="Start Capri when I log in (Windows)", variable=self.auto_var,
                       command=self.toggle_autostart, bg=C_PANEL, fg=C_TEXT, selectcolor=C_PANEL2,
                       activebackground=C_PANEL, activeforeground=C_TEXT, anchor="w", font=(self.fam, 9),
                       highlightthickness=0, bd=0, disabledforeground=C_DIM,
                       state="normal" if IS_WIN else "disabled").pack(fill="x", padx=12, pady=2)
        self.ledge_var = tk.BooleanVar(value=bool(self.pet.settings.get("ledges", False)))
        ui.NeonCheck(box, text="Screen ledges: let her look at my screen for boxes to sit on",
                       variable=self.ledge_var, command=self.toggle_ledges, bg=C_PANEL, fg=C_TEXT,
                       selectcolor=C_PANEL2, activebackground=C_PANEL, activeforeground=C_TEXT, anchor="w",
                       font=(self.fam, 9), highlightthickness=0, bd=0, wraplength=335, justify="left").pack(
            fill="x", padx=12, pady=2)
        tk.Label(box, text="She takes a screenshot every few seconds, looks for box edges on your computer, then "
                           "throws it away. Nothing is saved or sent. Pauses on banking, password and private pages.",
                 bg=C_PANEL, fg=C_DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(
            anchor="w", padx=10, pady=(0, 6))
        self.check(box, "Awareness: notice which app is in front, and when I'm away"
                        + ("" if self.pet.win32.ok else " (Windows only)"), "aware", True, self.pet.set_aware,
                   state="normal" if self.pet.win32.ok else "disabled")
        tk.Label(box, text="Awareness only reads the title of the front window. It's never stored, logged or sent.",
                 bg=C_PANEL, fg=C_DIM, font=(self.fam, 8), wraplength=345, justify="left").pack(anchor="w", padx=10,
                                                                                                   pady=(2, 8))

    def toggle_ledges(self):
        if self.ledge_var.get():
            if not self.pet.enable_ledges(parent=self.win):
                self.ledge_var.set(False)
        else:
            self.pet.disable_ledges()

    def toggle_autostart(self):
        ok, msg = autostart.enable() if self.auto_var.get() else autostart.disable()
        if not ok:
            self.auto_var.set(autostart.is_enabled())
        self.pet.say(msg, 5, speak=None)

    def build_keys(self, parent):
        box = self.section(parent, "AI CHAT KEY", "A Claude (sk-ant...) or Gemini key for real AI chat. "
                                                  "Stored only on this computer.")
        self.entry_row(box, "Paste key", self.save_chat_key)

    def save_chat_key(self, entry):
        key = entry.get().strip()
        if len(key) < 20 or " " in key:
            return self.pet.say("That doesn't look like a whole key.", 3, speak=None)
        try:
            save_api_key(key)
        except OSError as exc:
            return self.pet.say(f"Couldn't save the key: {exc}", 5, speak=None)
        entry.delete(0, "end")
        if self.pet.chat and self.pet.chat.alive():
            self.pet.chat.drop_keybar()
        self.pet.say("Key saved. Real chat unlocked.", 4, speak=None)

    def close(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        self.pet.settings_win = None


class BreachWindow:
    """Breach Protocol: fill the buffer so it contains the daemons. First pick is in the top row, then
    alternate column / row."""
    TIME = 45

    def __init__(self, pet):
        self.pet = pet
        self.game = breach.Breach(rng=pet.rng)
        self.over = False
        mono = pick_font(pet.root, "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New")
        self.mono = mono
        w = self.win = tk.Toplevel(pet.root)
        w.title("Breach Protocol")
        w.configure(bg=C_BLACK)
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.protocol("WM_DELETE_WINDOW", self.close)
        top = tk.Frame(w, bg=C_BLACK)
        top.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(top, text="BREACH PROTOCOL", bg=C_BLACK, fg=C_GREEN, font=(mono, 14, "bold")).pack(side="left")
        self.timer = tk.Label(top, text="", bg=C_BLACK, fg=C_RED, font=(mono, 14, "bold"))
        self.timer.pack(side="right")
        mid = tk.Frame(w, bg=C_BLACK)
        mid.pack(padx=14, pady=4)
        grid = tk.Frame(mid, bg=C_BLACK, highlightthickness=1, highlightbackground=C_GREEN)
        grid.pack(side="left", padx=(0, 14))
        self.cells = {}
        for r in range(self.game.size):
            for c in range(self.game.size):
                lb = tk.Label(grid, text=self.game.grid[r][c], width=4, height=2, font=(mono, 13, "bold"),
                              bg=C_BLACK, fg=C_GREEN, cursor="hand2")
                lb.grid(row=r, column=c, padx=1, pady=1)
                lb.bind("<Button-1>", lambda e, r=r, c=c: self.click(r, c))
                self.cells[(r, c)] = lb
        side = tk.Frame(mid, bg=C_BLACK)
        side.pack(side="left", anchor="n")
        tk.Label(side, text="DAEMONS", bg=C_BLACK, fg=C_DIM, font=(mono, 9, "bold")).pack(anchor="w")
        self.daemon_lbls = []
        for d in self.game.daemons:
            lb = tk.Label(side, text="", bg=C_BLACK, fg=C_TEXT, font=(mono, 10), justify="left", anchor="w")
            lb.pack(anchor="w", pady=(6, 0))
            self.daemon_lbls.append(lb)
        tk.Label(w, text="BUFFER", bg=C_BLACK, fg=C_DIM, font=(mono, 9, "bold")).pack(anchor="w", padx=14, pady=(8, 0))
        buf = tk.Frame(w, bg=C_BLACK)
        buf.pack(anchor="w", padx=14, pady=4)
        self.slots = []
        for _ in range(self.game.buffer):
            lb = tk.Label(buf, text="--", width=4, font=(mono, 12, "bold"), bg=C_PANEL2, fg=C_DIM)
            lb.pack(side="left", padx=2)
            self.slots.append(lb)
        self.status = tk.Label(w, text="Pick a code in the TOP row to start.", bg=C_BLACK, fg=C_DIM, font=(mono, 9),
                               wraplength=420, justify="left")
        self.status.pack(anchor="w", padx=14, pady=(6, 4))
        flat_button(w, "CLOSE", self.close, C_PANEL2, C_TEXT, "#2a2a40", (mono, 9, "bold"), 16, 5).pack(pady=(0, 12))
        self.deadline = time.time() + self.TIME
        self.refresh()
        self.tick()
        w.geometry(f"+{max(0, pet.sw // 2 - 230)}+{max(0, pet.sh // 2 - 230)}")

    def refresh(self):
        g = self.game
        legal = g.legal()
        used = set(g.picks)
        for pos, lb in self.cells.items():
            if pos in used:
                lb.config(text="[ ]", fg=C_DIM, bg=C_BLACK)
            elif pos in legal and not self.over:
                lb.config(text=g.grid[pos[0]][pos[1]], fg="#ffd400", bg="#1a2a1f")
            else:
                lb.config(text=g.grid[pos[0]][pos[1]], fg="#2f7a52", bg=C_BLACK)
        codes = g.codes
        for i, lb in enumerate(self.slots):
            lb.config(text=codes[i] if i < len(codes) else "--", fg=C_GREEN if i < len(codes) else C_DIM)
        for d, lb in zip(g.daemons, self.daemon_lbls):
            k = g.progress(d)
            ok = k == len(d.seq)
            lb.config(text=f"{'OK ' if ok else '   '}{d.name}\n   {' '.join(d.seq)}  [{k}/{len(d.seq)}]",
                      fg=C_GREEN if ok else C_TEXT)

    def click(self, r, c):
        if self.over:
            return
        if self.game.pick(r, c):
            self.pet.sfx.play("click")
            self.refresh()
            if self.game.done():
                self.finish()
        else:
            self.status.config(text="Not allowed: pick from the highlighted row/column.", fg=C_RED)

    def tick(self):
        if self.over:
            return
        try:
            left = max(0.0, self.deadline - time.time())
            self.timer.config(text=f"{left:04.1f}")
            if left <= 0:
                return self.finish()
            self.win.after(100, self.tick)
        except tk.TclError:
            pass

    def finish(self):
        if self.over:
            return
        self.over = True
        done, total = self.game.score(), len(self.game.daemons)
        self.refresh()
        self.status.config(text=f"BREACH {'COMPLETE' if done == total else 'ENDED'}: {done}/{total} daemons.",
                           fg=C_GREEN if done else C_RED)
        self.pet.breach_result(done, total)

    def close(self):
        self.over = True
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        self.pet.breach_win = None


class SimonWindow:
    """Simon: watch the colours light up, then repeat them. One more colour every round."""
    COLORS = {"green": ("#0a5a2a", C_GREEN), "red": ("#5a0c22", C_RED), "blue": ("#0d2a5a", "#4b8cff"),
              "yellow": ("#5a4f00", "#ffd400")}

    def __init__(self, pet):
        self.pet = pet
        self.game = None
        self.locked = True
        self.gen = 0
        mono = pick_font(pet.root, "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New")
        w = self.win = tk.Toplevel(pet.root)
        w.title("Simon")
        w.configure(bg=C_BLACK)
        w.attributes("-topmost", True)
        w.resizable(False, False)
        w.protocol("WM_DELETE_WINDOW", self.close)
        top = tk.Frame(w, bg=C_BLACK)
        top.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(top, text="SIMON", bg=C_BLACK, fg=C_GREEN, font=(mono, 14, "bold")).pack(side="left")
        self.round_lbl = tk.Label(top, text="", bg=C_BLACK, fg=C_RED, font=(mono, 14, "bold"))
        self.round_lbl.pack(side="right")
        grid = tk.Frame(w, bg=C_BLACK)
        grid.pack(padx=14, pady=4)
        self.btns = {}
        for i, color in enumerate(simon.COLORS):
            lb = tk.Label(grid, text="", width=11, height=5, bg=self.COLORS[color][0], cursor="hand2")
            lb.grid(row=i // 2, column=i % 2, padx=4, pady=4)
            lb.bind("<Button-1>", lambda e, c=color: self.click(c))
            self.btns[color] = lb
        self.status = tk.Label(w, text="", bg=C_BLACK, fg=C_DIM, font=(mono, 10))
        self.status.pack(pady=(6, 4))
        flat_button(w, "NEW GAME", self.start, C_PANEL2, C_TEXT, "#2a2a40", (mono, 9, "bold"), 16, 5).pack(pady=(0, 12))
        w.geometry(f"+{max(0, pet.sw // 2 - 160)}+{max(0, pet.sh // 2 - 230)}")
        self.start()

    def alive(self, gen):
        try:
            return gen == self.gen and bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def start(self):
        self.gen += 1
        self.game = simon.Simon(self.pet.rng)
        self.next_round()

    def next_round(self):
        seq = self.game.next_round()
        self.locked = True
        self.round_lbl.config(text=f"ROUND {len(seq)}")
        self.status.config(text="Watch...", fg=C_DIM)
        gen = self.gen
        self.win.after(700, lambda: self.play(seq, 0, gen))

    def play(self, seq, i, gen):
        if not self.alive(gen):
            return
        if i >= len(seq):
            self.locked = False
            self.status.config(text="Your turn!", fg=C_GREEN)
            return
        self.flash(seq[i])
        self.win.after(650, lambda: self.play(seq, i + 1, gen))

    def flash(self, color):
        lb = self.btns[color]
        lb.config(bg=self.COLORS[color][1])
        self.pet.sfx.play("simon_" + color)
        gen = self.gen

        def dim():
            try:
                lb.config(bg=self.COLORS[color][0])
            except tk.TclError:
                pass
        self.win.after(380, dim)

    def click(self, color):
        if self.locked or self.game.over:
            return
        self.flash(color)
        res = self.game.press(color)
        if res == "wrong":
            self.finish()
        elif res == "round_done":
            self.locked = True
            self.status.config(text="Nice!", fg=C_GREEN)
            gen = self.gen
            self.win.after(900, lambda: self.alive(gen) and self.next_round())

    def finish(self):
        self.locked = True
        n = self.game.completed
        self.status.config(text=f"Game over: {n} round(s). NEW GAME to try again.", fg=C_RED)
        self.pet.sfx.play("fail")
        self.pet.simon_result(n)

    def close(self):
        self.gen += 1
        try:
            self.win.destroy()
        except tk.TclError:
            pass
        self.pet.simon_win = None


class ReminderDialog:
    def __init__(self, pet):
        self.pet = pet
        f = pet.font_family
        w = self.win = tk.Toplevel(pet.root)
        w.title("Remind me")
        w.configure(bg=C_PANEL)
        w.attributes("-topmost", True)
        w.resizable(False, False)
        tk.Label(w, text="REMIND ME", bg=C_PANEL, fg=C_GREEN, font=(f, 11, "bold")).pack(padx=16, pady=(14, 6), anchor="w")
        self.what = self.field("About what?", "", 32)
        self.mins = self.field("In how many minutes?", "10", 8)
        row = tk.Frame(w, bg=C_PANEL)
        row.pack(fill="x", padx=16, pady=14)
        flat_button(row, "SET", self.ok, C_GREEN, C_BLACK, "#3dffa0", (f, 9, "bold"), 16, 6).pack(side="right")
        flat_button(row, "CANCEL", w.destroy, C_PANEL2, C_TEXT, "#2a2a40", (f, 9), 12, 6).pack(side="right", padx=8)
        w.bind("<Return>", lambda e: self.ok())
        w.bind("<Escape>", lambda e: w.destroy())
        w.geometry(f"+{max(0, int(pet.fx) - 150)}+{max(0, int(pet.fy) - 330)}")
        self.what.focus_force()

    def field(self, label, initial, width):
        f = self.pet.font_family
        tk.Label(self.win, text=label, bg=C_PANEL, fg=C_DIM, font=(f, 8)).pack(padx=16, anchor="w")
        e = tk.Entry(self.win, width=width, bg=C_PANEL2, fg=C_TEXT, insertbackground=C_GREEN, relief="flat",
                     font=(f, 10), highlightthickness=1, highlightbackground="#2a2a40", highlightcolor=C_GREEN)
        e.insert(0, initial)
        e.pack(padx=16, pady=(2, 8), ipady=5, fill="x")
        return e

    def ok(self):
        try:
            m = float(self.mins.get())
        except ValueError:
            return
        what = self.what.get().strip() or "Time's up"
        self.win.destroy()
        self.pet.add_reminder(m, what)


# ------------------------------------------------------------------ the pet
class Capri:
    def __init__(self):
        enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title(NAME)
        self.root.report_callback_exception = lambda *a: log("tk error: " + "".join(traceback.format_exception(*a)))
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.font_family = pick_font(self.root, "Segoe UI", "SF Pro Text", "Helvetica Neue", "Helvetica", "DejaVu Sans")
        self.dpi = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        self.settings = load_json(os.path.join(data_dir(), "settings.json"), {})
        if not isinstance(self.settings, dict):
            self.settings = {}
        self.mind = personality.Mind(self.settings)
        self.todos = fun.Todos(self.settings.setdefault("todos", []))
        self.habits = habits.Habits(self.settings.setdefault("habits", []))
        self.memory = memory.Memory(self.settings.setdefault("memory", []))
        self.notes = notes.Notes(self.settings.setdefault("notes", []))
        self.daylog = daylog.DayLog(self.settings.setdefault("daylog", {}))
        self.journal = journal.Journal(self.settings.setdefault("journal", []))
        self.msgs = []
        self.speaker = make_speaker()
        self.hands = hands.Hands(level=self.settings.get("hands", "visual"), log=log)
        self.sfx = sfx.Sfx(os.path.join(data_dir(), "sfx"), voice.play_file, enabled=bool(self.settings.get("sfx", True)),
                           busy=lambda: self.speaker.speaking, log=log)
        self.art_cache = {}
        size = self.settings.get("size", 1.0)
        self.size_base = sizing.clamp(size) if isinstance(size, (int, float)) else 1.0
        self.auto_size = bool(self.settings.get("auto_size", True))
        self.size_now = sizing.quantize(sizing.cap_for_screen(self.size_base, self.root.winfo_screenheight()))
        self.excited_until, self.next_size = 0.0, 0.0
        self.art = self.art_for(self.size_now)
        self.fw, self.fh = self.art.w, self.art.h
        self.Wd = max(280, int(self.fh * 1.25) + 30)
        self.Hd = self.fh + 150
        self.canvas = tk.Canvas(self.root, width=self.Wd, height=self.Hd, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.setup_transparency()
        self.win32 = Win32()
        self.sw, self.sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()

        self.calm = bool(self.settings.get("calm", False))
        self.checkins = bool(self.settings.get("checkins", True))
        now = time.time()
        self.t_start = now
        self.last_tick = now
        self.last_active = now
        self.fx = float(random.randint(150, max(151, self.sw - 150)))
        self.fy = float(self.ground())
        self.vx = self.vy = 0.0
        self.dir = 1
        self.state, self.state_t0, self.state_dur = "idle", now, 3.0
        self.anim = "idle"
        self.angle = self.angle_t = 0.0
        self.sx = self.sy = self.sxt = self.syt = 1.0
        self.glitch = 0.0
        self.hop_y = 0.0
        self.surf = None            # (id, left_at_last_seen) when standing on a window
        self.surfaces = []
        self.surf_check = 0.0
        self.tp_dest = None
        self.bubble, self.bubble_t0, self.bubble_until = "", 0.0, 0.0
        self.emote = None
        self.timer_end = self.timer_mode = None
        self.reminders = []
        self.next_checkin = now + random.randint(*CHECKIN_EVERY)
        self.next_chatter = now + random.randint(40, 90)
        self.chat = None
        self.talk_until = 0.0
        self.icon = None
        self._voice_err = ""
        self.fly_pts, self.fly_speed, self.fvx, self.fvy, self.orbit_a = [], 380.0, 0.0, 0.0, 0.0
        self.parts = []
        self.aware = bool(self.settings.get("aware", True))
        self.ctx, self.ctx_since, self.ctx_done, self.ctx_cool, self.ctx_nudge = None, now, False, {}, 0.0
        self.next_watch, self.away = now + 5, False
        self.pending, self.reflex_done, self.settings_win = None, {}, None
        self.busy_since, self.typing_along = None, False
        self.twitch_until, self.next_twitch = 0.0, now + 40
        self.tag, self.next_todo = None, now + 3600
        self.battery_state, self.next_battery, self.next_radio = {}, now + 20, now + 300
        self.peek_side, self.peek_said, self.breach_win, self.next_hungry = 0, False, None, now + 3600
        self.simon_win, self.last_watch, self.next_memory_cb = None, now, now + 7200
        self.scanner, self.ledges, self.ledge_counter, self.ledge_next = ledges.Scanner(), [], 0, 0.0
        self.game, self.game_seen, self.game_manual, self.reactor, self.calm_before_game = None, now, False, None, None
        self.meeting, self.calm_before_meeting = meeting.Detector(), None
        self.persona_text = read_first(["persona.txt"]) or DEFAULT_PERSONA
        self.ai_budget = speech.Budget(per_min=14, per_day=int(self.settings.get("ai_daily_cap", 800)),
                                       store=self.settings.setdefault("ai_day", {}))
        self.ai_results, self.ai_pending, self.ai_seq, self.ai_inflight = queue.Queue(), {}, 0, 0
        self.ai_fails, self.ai_pause_until = 0, 0.0
        self.recent_lines = collections.deque(maxlen=8)
        self.agent = None
        self.agent_events = queue.Queue()
        self.brain_events, self.ears_events = queue.Queue(), queue.Queue()
        self.heard_events, self.talk_requests = queue.Queue(), queue.Queue()
        self.brain_busy = self.ears_busy = self.listening = self.listen_stop = self.hotkey_on = False
        self.whisper = None
        self.wake = None
        self.apps, self.apps_at = {}, 0.0
        self.hear, self.hear_ok, self.hear_ok_at = None, True, 0.0
        self.callloop, self.call_events, self.audio_out = None, queue.Queue(), None
        self.call_after_agent = self.route_reply = self.call_started_hear = self.call_err_shown = False
        self.pc_events, self.hear_install_events = queue.Queue(), queue.Queue()
        self.music_talk_at, self.pending_hear, self.hear_installing = 0.0, False, False
        self.boot = None
        self.mono = pick_font(self.root, "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New")
        self.trail = collections.deque(maxlen=40)
        self.pil_cache, self.ghost_cache, self._last_ck = {}, {}, None
        nn = self.settings.get("neon", "off")
        self.neon_name = nn if nn in neon.COLORS else "off"
        ui.THEME["acc"] = neon.hex_of(neon.COLORS[self.neon_name]) if self.neon_name != "off" else "#05f56f"
        self.pending_wake = False
        self.clip_events = queue.Queue()
        BRAIN["mode"] = self.settings.get("brain", "auto") if self.settings.get("brain") in ("auto", "cloud", "local") else "auto"
        LOCAL_AI.which = self.settings.get("brain_model", "small") if self.settings.get("brain_model") in localai.MODELS else "small"
        self.agent_budget = speech.Budget(per_min=40, per_day=250, store=self.settings.setdefault("agent_budget", {}))
        self.voice_install = None
        self.spotter, self.spotter_manual, self.spotter_until = None, False, 0.0
        self.spotter_ctx_at, self.look_results = 0.0, queue.Queue()
        self.game_cfg, self.game_cfg_warnings = {}, []
        for folder in (app_dir(), data_dir()):                     # optional automatic detectors (README)
            cfg, warns = reactor.load_config(os.path.join(folder, "game_events.json"))
            if cfg or warns:
                self.game_cfg, self.game_cfg_warnings = cfg, warns
                break
        self.settings.setdefault("last_fed", time.time())
        lt = time.localtime()
        today = time.strftime("%Y-%m-%d", lt)
        special = world.special_day(lt.tm_mon, lt.tm_mday, self.settings.get("birthday", ""), self.mind.user_name)
        if special and self.settings.get("special_seen") != today:
            self.settings["special_seen"] = today
            self.msgs.append(special[1])
        self.next_save = now + 60
        self.pointer = (0, 0)
        self.pointer_prev = (0, 0, now)
        self.near_since = None
        self.last_startle = 0.0
        self.clicks = []
        self.press = None
        self.drag_hist = []
        self.pcache = {}
        self.cur_img = None
        self.rng = random.Random()
        self.land_squash = 0.0
        self.last_top = 0.0

        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        for seq in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            c.bind(seq, self.show_menu)
        self.place()
        if self.settings.get("boot_anim", True):
            self.start_boot()                          # she greets you when the animation ends
        else:
            self.greet()
        self.warm_brain()
        self.start_hotkey()
        if self.settings.get("wake"):
            self.start_wake()
        if self.settings.get("hear"):
            self.start_hear()
        self.tick()

    # ---- environment
    def setup_transparency(self):
        if IS_WIN:
            self.root.config(bg=KEY)
            self.canvas.config(bg=KEY)
            self.root.attributes("-transparentcolor", KEY)
        elif IS_MAC:
            self.root.attributes("-transparent", True)
            self.root.config(bg="systemTransparent")
            self.canvas.config(bg="systemTransparent")
        else:
            self.root.config(bg="#101018")
            self.canvas.config(bg="#101018")

    def work_area(self):
        wa = self.win32.work_area() if self.win32.ok else None
        return wa or (0, 0, self.sw, self.sh - (0 if IS_MAC else 48))

    def ground(self):
        return self.work_area()[3]

    def save_settings(self):
        self.mind.sync(time.time())
        save_json(os.path.join(data_dir(), "settings.json"), self.settings)

    def update_surfaces(self, now):
        if now - self.surf_check < 0.25:
            return
        self.surf_check = now
        s = []
        if self.chat and self.chat.alive():
            r = self.chat.rect()
            if r:
                s.append(r)
        fg = self.win32.foreground() if self.win32.ok else None
        if fg:
            s.append(fg)
        s += [(d["l"], d["t"], d["r"], d["t"] + 10, d["id"]) for d in self.ledges]
        wa = self.work_area()
        self.surfaces = [r for r in s if wa[1] + 40 < r[1] < wa[3] - 80 and r[2] - r[0] > 160]

    def pointer_xy(self):
        try:
            return self.root.winfo_pointerxy()
        except tk.TclError:
            return self.pointer

    # ---- state machine
    def go(self, state, dur=None, **kw):
        now = time.time()
        if state == "dance" and dur is None:
            dur = 3.0
        self.state, self.state_t0, self.state_dur = state, now, dur
        if state in ("idle", "perch"):
            self.angle_t, self.anim = 0.0, "idle"
        elif state == "sleep":
            self.angle_t, self.anim = 90.0 * self.dir, "sleep"
            self.say("zzz...", 2)
        elif state == "lounge":
            self.angle_t, self.anim = 90.0 * self.dir, "lounge"
        elif state == "walk":
            self.anim = "walk"
            self.angle_t = 0.0
        elif state == "dance":
            self.anim = "dance"
            self.angle_t = 0.0

    def check_voice_install(self):
        res, self.voice_install = self.voice_install, None
        if not res:
            return
        ok, err = res
        refresh_imports()
        if ok and voice.edge_installed():
            self.speaker = make_speaker()
            msg = f"Neural voice installed. Voice engine: {self.speaker.engine}."
            self.say("Voice installed. How do I sound?", 5, speak="priority")
        else:
            msg = "Couldn't install the voice: " + (err or "pip failed") + ". Try: py -m pip install edge-tts"
        if self.chat and self.chat.alive():
            self.chat.system_line(msg, err=not ok)

    def install_voice(self):
        """Background thread: pip install edge-tts, then tell the main thread to switch voices."""
        import subprocess
        try:
            r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "edge-tts"], capture_output=True,
                               text=True, timeout=240, creationflags=0x08000000 if sys.platform.startswith("win") else 0)
            ok = r.returncode == 0
            err = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
        except (OSError, subprocess.SubprocessError) as exc:
            ok, err = False, [str(exc)]
        self.voice_install = (ok, err[0])

    # ---- her size
    def art_for(self, scale):
        if scale not in self.art_cache:
            if len(self.art_cache) >= 5:
                self.art_cache.pop(next(iter(self.art_cache)))
            self.art_cache[scale] = load_art(self.dpi * scale)
        return self.art_cache[scale]

    def size_factor(self, now):
        if not self.auto_size:
            return 1.0
        return sizing.auto_factor(gaming=bool(self.game), focusing=self.timer_mode == "focus" and bool(self.timer_end),
                                  sleeping=self.state == "sleep", excited=now < self.excited_until)

    def apply_size(self, force=False):
        target = sizing.quantize(sizing.cap_for_screen(self.size_base * self.size_factor(time.time()), self.sh))
        if not force and abs(target - self.size_now) < 0.04:
            return False
        self.size_now = target
        self.art = self.art_for(target)
        self.fw, self.fh = self.art.w, self.art.h
        self.Wd = max(280, int(self.fh * 1.25) + 30)
        self.Hd = self.fh + 150
        self.canvas.config(width=self.Wd, height=self.Hd)
        self.clear_sprite_caches()
        self.parts = []
        self._geo = None
        self.place()
        return True

    def set_size(self, scale, announce=True):
        self.size_base = sizing.clamp(scale)
        self.settings["size"] = round(self.size_base, 2)
        self.save_settings()
        self.apply_size(force=True)
        if announce:
            self.say_moment(f"you just changed your own size to {int(self.size_base * 100)} percent of normal at the "
                            "user's request", f"Size {int(self.size_base * 100)}%.", 4, wait=3)

    def set_auto_size(self, on):
        self.auto_size = bool(on)
        self.settings["auto_size"] = self.auto_size
        self.save_settings()
        self.apply_size()

    def watch_size(self, now):
        if now >= self.next_size:
            self.next_size = now + 3.0
            self.apply_size()

    def poke_awake(self):
        self.last_active = time.time()
        if self.state in ("sleep", "lounge"):
            self.angle_t = 0.0
            self.go("idle", 2.0)

    def hop(self, power=9.0):
        self.vy = -power * max(1.0, self.dpi)
        self.go("air")
        self.anim = "jump"

    def set_icon(self, kind, secs=1.6):
        self.icon = (kind, time.time(), time.time() + secs)

    def draw_icon(self, c, now, lfx, top):
        kind, t0, _ = self.icon
        age = now - t0
        x = lfx + self.fw * 0.34
        y = top + self.fh * 0.14 - min(8.0, age * 24) + math.sin(now * 9) * 1.5
        f = self.font_family

        def outlined(text, size, fill):
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                c.create_text(x + dx, y + dy, text=text, font=(f, size, "bold"), fill=C_BLACK)
            c.create_text(x, y, text=text, font=(f, size, "bold"), fill=fill)
        if kind == "!":
            outlined("!", 20, C_RED)
        elif kind == "?":
            outlined("?", 18, C_GREEN)
        elif kind == "heart":
            s = 7 + 3 * min(1.0, age / 0.2)
            c.create_polygon(x, y + s, x - s, y - s * 0.1, x - s * 0.6, y - s * 0.8, x, y - s * 0.35,
                             x + s * 0.6, y - s * 0.8, x + s, y - s * 0.1, fill=C_RED, outline=C_BLACK,
                             smooth=True, width=2)
        elif kind == "note":
            outlined("\u266a", 18, C_GREEN)
        elif kind == "star":
            pts = []
            for i in range(8):
                r = 11 if i % 2 == 0 else 4
                a = math.pi / 4 * i - math.pi / 2
                pts += [x + math.cos(a) * r, y + math.sin(a) * r]
            c.create_polygon(pts, fill="#ffd400", outline=C_BLACK, width=2)
        elif kind == "anger":
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                c.create_line(x + dx * 3, y + dy * 3, x + dx * 10, y + dy * 10, fill=C_RED, width=3)

    def react(self, kind):
        now = time.time()
        if kind in ("happy", "error"):
            self.icon = None
        if kind == "startle":
            self.set_emote("wide", 1.6)
            self.say_moment("someone suddenly swiped the mouse right at you and startled you",
                            self.rng.choice(["Whoa.", "Hey!", "Eep."]), 3, wait=2.5)
            self.set_icon("!", 1.4)
            self.hop(8)
            self.anim = "startle"
        elif kind == "annoyed":
            self.set_emote("angry", 2.4)
            self.say_moment("the user keeps clicking on you over and over and it's annoying you",
                            "Okay, that's enough.", 3.5, wait=3)
            self.set_icon("anger", 2.4)
        elif kind == "think":
            self.anim = "wait"
            self.set_icon("?", 25)
        elif kind == "happy" and self.state in ("idle", "perch", "walk"):
            self.set_emote("talk", 1.4)
            self.anim = "wave"
            self.state_dur = max(self.state_dur or 0, 2.0)
        elif kind == "error":
            self.set_emote("angry", 2.0)
            self.set_icon("anger", 2.0)
            self.anim = "fail"

    def set_emote(self, name, secs):
        if name in self.art.emotes:
            self.emote = (name, time.time(), time.time() + secs)

    def say(self, text, secs=6.0, speak="ambient"):
        """Show a speech bubble and (voice permitting) say it. speak: "ambient", "priority" or None."""
        text = text if len(text) <= 140 else text[:137] + "..."
        self.bubble, self.bubble_t0, self.bubble_until = text, time.time(), time.time() + secs
        if speak:
            self.speak(text, priority=(speak == "priority"))

    def take_route(self):
        r, self.route_reply = self.route_reply, False
        return r

    def speak(self, text, priority=False, call=False):
        if call:                                             # speaking into a voice call ignores the quiet setting
            self.speaker.speak(text, True, True)
            return
        level = self.settings.get("voice", "chatty")
        if level == "off" or (level == "replies" and not priority) or (self.calm and not priority):
            return
        self.speaker.speak(text, priority)

    def set_voice(self, level):
        self.settings["voice"] = level
        self.save_settings()
        msg = {"off": "Okay, I'll be quiet.", "replies": "I'll only speak for replies and alerts.",
               "chatty": "Chatty mode. You asked for it."}[level]
        self.say(msg, 4, speak=None if level == "off" else "priority")

    def bounds(self):
        wa = self.work_area()
        l, r = wa[0], wa[2]
        if self.surf:
            sf = next((s for s in self.surfaces if s[4] == self.surf[0]), None)
            if sf:
                l, r = max(l, sf[0]), min(r, sf[2])
        m = self.fw * 0.35
        return l + m, r - m

    def choose_next(self):
        if self.calm:
            self.go("idle", self.rng.uniform(4, 9))
            return
        opts = [("walk", 30), ("lounge", 12), ("teleport", 14), ("curious", 10), ("dance", 4), ("idle", 14)]
        if "look-a" in getattr(self.art, "map", {}):
            opts.append(("look", 9))
        if self.settings.get("fly_enabled", True):
            opts += [("fly", 9), ("zoom", 3), ("orbit", 5)]
        opts.append(("peek", 6))
        if self.settings.get("ledges", False) and self.ledges and not self.surf:
            opts.append(("ledge", 14))
        if self.surfaces and not self.surf:
            opts.append(("perch", 16))
        if self.surf:
            opts += [("drop", 10)]
        if time.time() - self.last_active > SLEEP_AFTER:
            opts.append(("sleep", 25))
        opts = self.mind.adjust_weights(opts, time.time())
        r = self.rng.uniform(0, sum(w for _, w in opts))
        for name, w in opts:
            r -= w
            if r <= 0:
                break
        if name == "walk":
            self.dir = self.rng.choice((-1, 1))
            self.go("walk", self.rng.uniform(2, 7))
        elif name == "lounge":
            self.dir = self.rng.choice((-1, 1))
            self.go("lounge", self.rng.uniform(8, 22))
        elif name == "teleport":
            self.teleport()
        elif name == "curious":
            self.go("curious", 8)
        elif name in ("fly", "zoom", "orbit"):
            self.start_fly(name)
        elif name == "peek":
            self.start_peek()
        elif name == "ledge":
            self.sit_somewhere(quiet=True)
        elif name == "look":
            self.go("idle", self.rng.uniform(2.5, 4.5))
            self.anim = self.rng.choice(("look-a", "look-b"))
        elif name == "dance":
            self.go("dance", 3.2)
        elif name == "perch":
            self.teleport(mode="perch")
        elif name == "drop":
            self.vx = self.rng.choice((-1, 1)) * 2.5
            self.surf = None
            self.vy = -3
            self.go("air")
        elif name == "sleep":
            self.go("sleep")
        else:
            self.go("idle", self.rng.uniform(2, 6))

    def start_fly(self, kind="fly"):
        """Fly around the screen (fly), dash across it (zoom) or circle the mouse cursor (orbit)."""
        if self.state in ("tp_out", "tp_in", "drag"):
            return
        wa = self.work_area()
        self.surf = None
        self.icon = None
        self.fvx = self.fvy = 0.0
        if kind == "orbit":
            self.orbit_a = self.rng.uniform(0, 6.28)
            self.fly_speed = 520.0
            self.go("orbit", 5.5)
            self.say_moment("you are flying in circles around the user's mouse cursor",
                            self.rng.choice(["Circling you, choom.", "You're my favorite landmark."]), 4, wait=3)
        else:
            n = 1 if kind == "zoom" else self.rng.randint(3, 5)
            lo_x, hi_x = wa[0] + self.fw, wa[2] - self.fw
            lo_y, hi_y = wa[1] + self.fh + 20, wa[3] - self.fh * 0.5
            self.fly_pts = [(self.rng.uniform(lo_x, hi_x), self.rng.uniform(lo_y, max(lo_y + 1, hi_y)))
                            for _ in range(n)]
            self.fly_speed = 1100.0 if kind == "zoom" else 380.0
            self.go("fly", None)
            self.say_moment("you just dashed across the screen at top speed" if kind == "zoom"
                            else "you just took off to fly around the screen",
                            "Gotta go fast!" if kind == "zoom" else self.rng.choice(["Wheee!", "Up we go, choom!", "Nova!"]),
                            3, wait=3)
        self.anim = "jump"

    def spawn_confetti(self, count=60):
        cols = (C_GREEN, C_RED, C_BLUE, "#ffffff", "#ffd400")
        for _ in range(count):
            self.parts.append([self.Wd / 2 + self.rng.uniform(-30, 30), self.Hd * 0.35, self.rng.uniform(-160, 160),
                               self.rng.uniform(-300, -60), self.rng.choice(cols), self.rng.uniform(1.8, 3.2)])
        del self.parts[:-160]

    def party(self):
        self.excited_until = time.time() + 6
        self.sfx.play("success")
        self.spawn_confetti()
        self.start_fly("fly")

    def update_particles(self, dt):
        for p in self.parts:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += 420 * dt
            p[5] -= dt
        self.parts = [p for p in self.parts if p[5] > 0 and p[1] < self.Hd + 10]

    def teleport(self, mode=None):
        if self.state in ("tp_out", "tp_in", "drag"):
            return
        mode = mode or self.rng.choice(["ground", "ground", "sky", "cursor"])
        self.tp_dest = mode
        self.say_moment("you are about to glitch-teleport somewhere else on the screen",
                        self.rng.choice(["Glitching...", "brb", "Don't look."]), 2.5, wait=1.5)
        self.go("tp_out", 0.5)

    def finish_teleport(self):
        wa = self.work_area()
        mode = self.tp_dest
        self.surf = None
        l, r = wa[0] + self.fw * 0.5, wa[2] - self.fw * 0.5
        if mode == "perch" and self.surfaces:
            s = self.rng.choice(self.surfaces)
            self.fx = self.rng.uniform(s[0] + self.fw * 0.4, max(s[0] + self.fw * 0.5, s[2] - self.fw * 0.4))
            self.fy = s[1]
            self.surf = (s[4], s[0])
        elif mode == "sky":
            self.fx = self.rng.uniform(l, r)
            self.fy = self.rng.uniform(wa[1] + self.fh + 20, (wa[1] + wa[3]) * 0.5)
        elif mode == "cursor":
            mx, my = self.pointer_xy()
            self.fx = min(max(l, mx + self.rng.choice((-1, 1)) * 140), r)
            self.fy = self.ground()
        else:
            self.fx = self.rng.uniform(l, r)
            self.fy = self.ground()
        self.vx = self.vy = 0.0
        self.angle = self.angle_t = 0.0
        self.go("tp_in", 0.5)

    def land(self, surface=None):
        self.vy = 0.0
        self.vx *= 0.2
        self.land_squash = 1.0
        if surface:
            self.surf = (surface[4], surface[0])
            self.fy = surface[1]
            self.go("perch", self.rng.uniform(6, 16))
        else:
            self.surf = None
            self.fy = self.ground()
            self.go("idle", self.rng.uniform(1.5, 4))

    def step_state(self, now, dt, age):
        st = self.state
        sp = 2.4 * self.dpi * dt * 25
        lo, hi = self.bounds()
        if st in ("idle", "perch"):
            self.anim = "idle" if self.anim in ("walk", "jump", "startle") else self.anim
            if self.state_dur and age > self.state_dur:
                if self.anim in ("wave", "wait", "fail") and age < 8:
                    pass
                self.anim = "idle"
                self.choose_next()
        elif st == "walk":
            self.fx += self.dir * sp
            if self.fx < lo or self.fx > hi:
                self.fx = min(max(self.fx, lo), hi)
                self.dir *= -1
            self.hop_y = -abs(math.sin(now * 9)) * 3 * self.dpi
            if age > self.state_dur:
                self.hop_y = 0
                self.go("perch" if self.surf else "idle", self.rng.uniform(2, 5))
        elif st in ("lounge", "sleep"):
            if st == "lounge" and age > self.state_dur:
                self.go("idle", 2.0)
            elif st == "lounge" and age > 6 and self.rng.random() < 0.004:
                self.go("sleep")
            if st == "sleep" and now - self.last_active < 3 and age > 1:
                self.go("idle", 2.0)
        elif st == "curious":
            mx, my = self.pointer
            target = mx + (-1 if self.fx > mx else 1) * self.fw * 0.9
            if abs(target - self.fx) > 20:
                self.dir = 1 if target > self.fx else -1
                self.fx = min(max(self.fx + self.dir * sp * 1.8, lo), hi)
                self.anim = "walk"
                self.hop_y = -abs(math.sin(now * 12)) * 3 * self.dpi
            else:
                self.hop_y = 0
                self.anim = "idle"
                self.dir = 1 if mx > self.fx else -1
                self.angle_t = 5.0 * self.dir
            if age > self.state_dur:
                self.hop_y = 0
                self.go("idle", 2.0)
        elif st == "dance":
            self.hop_y = -abs(math.sin(age * 8)) * 18 * self.dpi
            self.angle_t = 10.0 * math.sin(age * 8)
            if age > (self.state_dur or 3):
                self.hop_y = 0
                self.go("perch" if self.surf else "idle", 2.0)
        elif st == "peek":
            wa = self.work_area()
            side = self.peek_side or 1
            inside = wa[0] + self.fw * 0.7 if side < 0 else wa[2] - self.fw * 0.7
            if age > (self.state_dur or 5.0):                 # slide back in, then carry on
                if not self.peek_said:                        # the line waits until the bubble can be read
                    self.peek_said = True
                    self.say_moment("you just peeked out from the edge of the screen and are sliding back in",
                                    self.rng.choice(["Peekaboo.", "Don't mind me.", "Psst. Choom.", "Boo. Kidding."]),
                                    4, wait=3)
                self.fx += (inside - self.fx) * min(1.0, 6.0 * dt)
                if abs(inside - self.fx) < 6:
                    self.go("idle", self.rng.uniform(1.5, 3.5))
        elif st == "flee":
            if not self.tag:
                return self.go("air")
            mx, my = self.pointer
            cx, cy = self.fx, self.fy - self.fh * 0.5
            dx, dy = cx - mx, cy - my
            dist = math.hypot(dx, dy) or 1.0
            t = now - self.tag["t0"]
            if dist < self.fw * 0.45 and t > 1.0:
                return self.end_tag(True, t)
            if t > 25:
                return self.end_tag(False, t)
            v = (420 + min(t, 20) * 15) * self.dpi
            want = v if dist < 420 * self.dpi else v * 0.2
            ux, uy = dx / dist, dy / dist
            k = min(1.0, 6.0 * dt)
            self.fvx += ((ux - uy * 0.35) * want - self.fvx) * k      # run away, curving a little
            self.fvy += ((uy + ux * 0.35) * want - self.fvy) * k
            wa = self.work_area()
            self.fx = min(max(self.fx + self.fvx * dt, wa[0] + self.fw * 0.4), wa[2] - self.fw * 0.4)
            self.fy = min(max(self.fy + self.fvy * dt, wa[1] + self.fh + 6), self.ground())
            self.angle_t = max(-24.0, min(24.0, -self.fvx / max(1.0, v) * 24.0))
            self.hop_y = math.sin(now * 9) * 3 * self.dpi
            if abs(self.fvx) > 25:
                self.dir = 1 if self.fvx > 0 else -1
            cornered = (self.fx < wa[0] + self.fw * 0.6 or self.fx > wa[2] - self.fw * 0.6
                        or self.fy > self.ground() - 4 or self.fy < wa[1] + self.fh + 12)
            if cornered and dist < 220 * self.dpi and now >= self.tag["tp_ok"]:
                self.tag["tp_ok"] = now + 1.8                           # glitch-teleport out of the corner
                self.twitch_until = now + 0.3
                nx, ny = self.fx, self.fy
                for _ in range(10):
                    nx = self.rng.uniform(wa[0] + self.fw, wa[2] - self.fw)
                    ny = self.rng.uniform(wa[1] + self.fh + 20, self.ground())
                    if math.hypot(nx - mx, ny - self.fh * 0.5 - my) > 450 * self.dpi:
                        break
                self.fx, self.fy, self.fvx, self.fvy = nx, ny, 0.0, 0.0
        elif st in ("fly", "orbit"):
            v = self.fly_speed * self.dpi                       # px per second
            done = False
            if st == "orbit":
                self.orbit_a += 2.6 * dt
                mx, my = self.pointer
                tx = mx + math.cos(self.orbit_a) * 170 * self.dpi
                ty = my + math.sin(self.orbit_a) * 90 * self.dpi - self.fh * 0.4
                done = age > (self.state_dur or 5.5)
            else:
                tx, ty = self.fly_pts[0]
            dx, dy = tx - self.fx, ty - self.fy
            dist = math.hypot(dx, dy) or 1.0
            k = min(1.0, 5.0 * dt)
            want = min(v, dist * 5)                              # ease out when arriving
            self.fvx += (dx / dist * want - self.fvx) * k
            self.fvy += (dy / dist * want - self.fvy) * k
            wa = self.work_area()
            self.fx = min(max(self.fx + self.fvx * dt, wa[0] + self.fw * 0.4), wa[2] - self.fw * 0.4)
            self.fy = min(max(self.fy + self.fvy * dt, wa[1] + self.fh + 6), self.ground())
            self.angle_t = max(-24.0, min(24.0, -self.fvx / max(1.0, v) * 24.0))
            self.hop_y = math.sin(now * 7) * 3 * self.dpi
            if abs(self.fvx) > 25:
                self.dir = 1 if self.fvx > 0 else -1
            if st == "fly" and dist < 22 * self.dpi:
                self.fly_pts.pop(0)
                done = not self.fly_pts
            if done:
                self.hop_y, self.angle_t = 0.0, 0.0
                self.vx, self.vy = self.fvx / 25.0 * 0.4, 0.0
                self.go("air")
        elif st == "tp_out":
            self.glitch = min(1.0, age / self.state_dur)
            if age > self.state_dur:
                self.finish_teleport()
        elif st == "tp_in":
            self.glitch = max(0.0, 1 - age / self.state_dur)
            if age > self.state_dur:
                self.glitch = 0
                if self.fy < self.ground() - 2 and not self.surf:
                    self.go("air")
                else:
                    if self.rng.random() < 0.5:
                        self.react("startle" if False else "happy")
                    self.go("perch" if self.surf else "idle", 2.0)
        elif st == "air":
            prev = self.fy
            self.vy = min(self.vy + 1.1 * self.dpi * dt * 25, 38 * self.dpi)
            self.fy += self.vy * dt * 25
            self.fx += self.vx * dt * 25
            wa = self.work_area()
            if self.fx < wa[0] + self.fw * 0.4 or self.fx > wa[2] - self.fw * 0.4:
                self.fx = min(max(self.fx, wa[0] + self.fw * 0.4), wa[2] - self.fw * 0.4)
                self.vx *= -0.6
            if self.fy - self.fh < wa[1]:
                self.fy, self.vy = wa[1] + self.fh, abs(self.vy) * 0.5
            self.angle_t = max(-30, min(30, self.vx * 3))
            if self.vy > 0:
                for s in self.surfaces:
                    if prev <= s[1] + 2 and self.fy >= s[1] and s[0] - 4 <= self.fx <= s[2] + 4:
                        return self.land(s)
            if self.fy >= self.ground():
                self.land()

    # ---- main loop
    def tick(self):
        try:
            self._tick()
        except Exception:
            log("tick error: " + traceback.format_exc())
        self.root.after(TICK_MS, self.tick)

    def _tick(self):
        now = time.time()
        dt = max(0.001, min(0.2, now - self.last_tick))
        self.last_tick = now
        self.update_surfaces(now)
        self.pointer = self.pointer_xy()
        self.react_to_pointer(now, dt)
        # keep following the window we're standing on
        if self.surf and self.state not in ("air", "drag", "tp_out", "tp_in"):
            sf = next((s for s in self.surfaces if s[4] == self.surf[0]), None)
            if not sf or not (sf[0] - 10 <= self.fx <= sf[2] + 10):
                self.surf = None
                self.go("air")
            else:
                self.fx += sf[0] - self.surf[1]
                self.fy = sf[1]
                self.surf = (self.surf[0], sf[0])
        elif self.state in ("idle", "walk", "lounge", "sleep", "curious", "dance") and self.fy < self.ground() - 2:
            self.go("air")
        age = now - self.state_t0
        if self.state != "drag":
            self.step_state(now, dt, age)
        # smoothing
        self.angle += (self.angle_t - self.angle) * min(1.0, 0.22 * dt * 25)
        self.land_squash = max(0.0, self.land_squash - dt * 5)
        self.sy = 1.0 - 0.16 * self.land_squash
        self.sx = 1.0 + 0.12 * self.land_squash
        if self.state in ("tp_out", "tp_in"):
            self.sx = max(0.12, 1.0 - 0.9 * self.glitch ** 1.5)
            self.sy = 1.0 + 0.12 * self.glitch
        self.update_busy(now)
        self.update_twitch(now)
        self.update_boot(now)
        self.update_particles(dt)
        self.scheduled(now)
        self.place()
        self.draw(now)
        if int(now) % 3 == 0 and not self.root.winfo_ismapped():
            self.root.deiconify()
        if int(now * 2) % 6 == 0:
            self.root.attributes("-topmost", True)

    def update_twitch(self, now):
        """Every minute or so she glitches for a moment (RGB split), because she's a glitchy AI."""
        if self.state in ("tp_out", "tp_in"):
            return
        if now >= self.next_twitch and self.state in ("idle", "perch", "lounge"):
            self.next_twitch = now + self.rng.uniform(35, 110)
            self.twitch_until = now + 0.35
        self.glitch = 0.45 if now < self.twitch_until else 0.0

    def start_tag(self):
        """Mini-game: she runs from your cursor for 25 seconds. Touch her to win."""
        if self.state in ("tp_out", "tp_in", "drag"):
            return
        now = time.time()
        self.surf = None
        self.icon = None
        self.fvx = self.fvy = 0.0
        self.tag = {"t0": now, "tp_ok": now + 1.5}
        self.go("flee", 26)
        self.anim = "jump"
        self.say_moment("you're starting a game of tag: the user has 25 seconds to catch you with their mouse cursor",
                        "Tag! Catch me with your cursor, choom. 25 seconds!", 5, wait=3)

    def end_tag(self, caught, t):
        self.tag = None
        self.hop_y, self.angle_t = 0.0, 0.0
        self.vx = self.vy = 0.0
        self.go("air")
        if caught:
            best = self.settings.get("tag_best", 99.0)
            tail = ""
            if t < best:
                self.settings["tag_best"] = round(t, 1)
                tail = " New record!" if best < 99 else ""
            self.say_moment(f"the user caught you in tag in {t:.1f} seconds" + (" and it's a new personal record" if tail else ""),
                            f"Got me in {t:.1f}s! Preem reflexes.{tail}", 7, speak="priority", wait=4)
            self.spawn_confetti(30)
            self.sfx.play("success")
        else:
            self.say_moment("the user failed to catch you in tag for the whole 25 seconds",
                            "You couldn't catch me. Nova.", 5, wait=4)
            self.sfx.play("fail")

    def scan_masks(self):
        """Screen rectangles of her own windows, so she never sits on herself."""
        rects = []
        for w in [self.root] + [c for c in self.root.winfo_children() if isinstance(c, tk.Toplevel)]:
            try:
                if w.winfo_viewable():
                    rects.append((w.winfo_rootx(), w.winfo_rooty(), w.winfo_width(), w.winfo_height()))
            except tk.TclError:
                pass
        return rects

    def watch_ledges(self, now):
        """Look for boxes on screen to sit on. Only when the user switched it on. Nothing is kept."""
        if not self.settings.get("ledges", False):
            if self.ledges:
                self.ledges = []
            return
        if self.game:                                        # never screenshot a game looking for ledges
            self.ledges = []
            return
        result = self.scanner.take()
        if result is not None:
            self.ledges, self.ledge_counter = ledges.track(self.ledges, result, self.ledge_counter)
        if self.scanner.error:
            err, self.scanner.error = self.scanner.error, ""
            self.settings["ledges"] = False
            self.ledges = []
            self.save_settings()
            self.say(f"I can't see the screen ({err}). Screen ledges are off.", 7, speak=None)
            return
        if now < self.ledge_next or self.scanner.busy or self.state == "drag":
            return
        self.ledge_next = now + (2.5 if self.surf else 4.0)
        if self.win32.ok and self.win32.idle_seconds() > 120:
            return                                           # nobody's there: rest, keep the last view
        title = self.win32.foreground_title() if self.win32.ok else ""
        if not ledges.should_scan(title):
            self.ledges = []                                 # looks private: look away completely
            return
        self.scanner.start(self.scan_masks(), (self.sw, self.sh))

    def enable_ledges(self, parent=None, ask=True):
        """Switch screen ledges on, but only after the user agrees to what it does. Returns True if on."""
        if ask:
            from tkinter import messagebox
            if not messagebox.askyesno(
                    "Let Capri look at your screen?",
                    "To find boxes to sit on, Capri takes a screenshot every few seconds and looks for box "
                    "edges, entirely on your computer.\n\n* The screenshot lives in memory for a moment, then "
                    "it's thrown away.\n* Nothing is saved to disk or sent anywhere.\n* She pauses on pages "
                    "that look private (banking, passwords, private browsing).\n\nAnything on your screen is "
                    "briefly visible to her code, so only turn this on if you're comfortable with that. You can "
                    "switch it off any time.\n\nTurn on screen ledges?",
                    parent=parent, default="no", icon="warning"):
                return False
        self.settings["ledges"] = True
        self.ledge_next = 0.0
        self.save_settings()
        self.say("Okay! Let me look around for somewhere to sit.", 5, speak=None)
        return True

    def disable_ledges(self):
        self.settings["ledges"] = False
        self.ledges = []
        self.scanner.take()
        self.save_settings()
        if self.surf and str(self.surf[0]).startswith("L"):
            self.surf = None
            self.go("air")
        self.say("Okay, I stopped looking at your screen.", 4, speak=None)

    def sit_somewhere(self, quiet=False):
        """Fly to a box on screen and land on its top edge."""
        if not self.settings.get("ledges", False):
            if not quiet:
                self.say("Turn on 'Screen ledges' in Settings first.", 5, speak=None)
            return
        spots = [d for d in self.ledges if d["r"] - d["l"] > 160]
        if not spots or self.state in ("tp_out", "tp_in", "drag"):
            if not quiet:
                self.say("I don't see anywhere to sit yet. Looking...", 4, speak=None)
            self.ledge_next = 0.0
            return
        d = self.rng.choice(spots)
        self.surf = None
        self.icon = None
        self.fvx = self.fvy = 0.0
        x = self.rng.uniform(d["l"] + self.fw * 0.5, max(d["l"] + self.fw * 0.5 + 1, d["r"] - self.fw * 0.5))
        self.fly_pts = [(x, d["t"] - 45)]                    # arrive just above it, then drop onto the edge
        self.fly_speed = 620.0
        self.go("fly", None)
        self.anim = "jump"
        if not quiet:
            self.say_moment("you just found a box on the user's screen to sit on",
                            self.rng.choice(["Found a spot!", "That box looks sit-able.", "Ooh, a ledge."]), 4, wait=3)

    # ---- lines the AI writes (presets are only the fallback)
    def ai_enabled(self):
        return bool(self.settings.get("ai_lines", True) and ai_available() and time.time() >= self.ai_pause_until)

    def ai_system(self, now=None):
        now = now or time.time()
        return speech.system_prompt(self.persona_text, self.mind.context(now, self.doing(), self.activity_phrase()),
                                    self.settings.get("roast", "mild"), self.memory.context())

    def say_moment(self, situation, fallback, secs=4.0, speak="ambient", wait=4.0):
        """Tell the AI what just happened and let it write her reaction. `fallback` only if the AI can't."""
        self.say_ai("moment", {"situation": situation}, fallback, secs, speak, wait)

    def say_ai(self, kind, facts, fallback, secs=6.0, speak="ambient", wait=5.0):
        """Let the AI write this line. The preset `fallback` is used only if the AI is off, busy or too slow."""
        if not self.ai_enabled() or self.ai_inflight >= 2 or not self.ai_budget.allow():
            if fallback:
                self.say(fallback, secs, speak=speak)
            return
        now = time.time()
        self.ai_seq += 1
        rid = self.ai_seq
        self.ai_pending[rid] = {"deadline": now + wait, "fallback": fallback, "secs": secs, "speak": speak,
                                "expired": False}
        self.ai_inflight += 1
        system = self.ai_system(now)
        user = speech.user_prompt(kind, facts, list(self.recent_lines))
        threading.Thread(target=self._ai_worker, args=(rid, system, user), daemon=True).start()

    def _ai_worker(self, rid, system, user):
        try:
            text = speech.sanitize(llm_reply([{"role": "user", "content": user}], system, max_tokens=80,
                                             model=LINE_MODEL))
            self.ai_results.put((rid, text, ""))
        except Exception as exc:
            self.ai_results.put((rid, "", str(exc) or type(exc).__name__))

    def drain_ai(self, now):
        while True:
            try:
                rid, text, err = self.ai_results.get_nowait()
            except queue.Empty:
                break
            self.ai_inflight = max(0, self.ai_inflight - 1)
            p = self.ai_pending.pop(rid, None)
            if err:
                self.ai_fails += 1
                log("ai line failed: " + err[:120])
                if self.ai_fails == 3:
                    self.ai_pause_until = now + 300
                    self.say("My AI brain isn't answering (" + err[:50] + "). Preset lines for a few minutes.", 8,
                             speak=None)
            else:
                self.ai_fails = 0
            if p is None or p["expired"]:
                continue                                 # she already said the preset; a late reply is dropped
            line = text or p["fallback"]
            if line:
                self.say(line, p["secs"], speak=p["speak"])
            if text:
                self.recent_lines.append(text)
        for p in self.ai_pending.values():
            if now > p["deadline"] and not p["expired"]:
                p["expired"] = True
                if p["fallback"]:
                    self.say(p["fallback"], p["secs"], speak=p["speak"])
        while True:
            try:
                text, err = self.look_results.get_nowait()
            except queue.Empty:
                break
            if err:
                text = "I couldn't look: " + err[:100]
            if self.chat and self.chat.alive():
                self.chat.add_bubble("assistant", text)
            else:
                self.say(text[:140], 10)

    # ---- the AI spotter: looks at the screen (sends a small screenshot to your AI provider)
    def enable_vision(self, parent=None, ask=True):
        """Switch the AI spotter on, but only after the user agrees to what it does. Returns True if on."""
        if ask:
            from tkinter import messagebox
            if not messagebox.askyesno(
                    "Let Capri watch your screen with AI?",
                    "While she's watching, Capri takes a small shrunken screenshot every few seconds (only when the "
                    "screen changed) and SENDS it to your AI provider (Claude or Gemini, whichever key you use) so "
                    "the AI can see what's happening and react.\n\n* It can include ANYTHING visible on your "
                    "screen at that moment.\n* Capri doesn't save the screenshots. The provider's own data policy "
                    "applies to what it receives.\n* It pauses on banking, password and private-browsing windows "
                    "and while you're away.\n* It uses your API credits: very roughly $1-3 an hour with Claude "
                    "(there is a daily limit).\n* It starts by itself when a game is in front. /watch on works "
                    "for anything else.\n\nOnly turn this on if you're comfortable with that. You can switch it "
                    "off any time. Turn on AI screen watching?", parent=parent, default="no", icon="warning"):
                return False
        self.settings["ai_vision"] = True
        self.save_settings()
        self.say("Okay. I'll watch when you game, if you give me a key.", 5, speak=None)
        return True

    # ---- local AI and voice input
    def add_note(self, text):
        """Save a note (typed or dictated). Text only, kept in settings.json on this PC; never sent to the AI."""
        saved = self.notes.add(text, time.strftime("%m-%d %H:%M"))
        if saved:
            self.save_settings()
        return saved

    def notify(self, text, err=False, secs=6.0):
        self.say(text, secs, speak=None)
        if self.chat and self.chat.alive():
            self.chat.system_line(text, err=err)

    def set_brain(self, mode):
        BRAIN["mode"] = mode
        self.settings["brain"] = mode
        self.save_settings()
        self.warm_brain()

    def warm_brain(self):
        """Start the local engine in the background when it will be used, so the first line isn't late."""
        if (BRAIN["mode"] == "local" or (BRAIN["mode"] == "auto" and not read_api_key())) and LOCAL_AI.available():
            threading.Thread(target=self._warm, daemon=True).start()

    def _warm(self):
        try:
            LOCAL_AI.start()
        except RuntimeError as exc:
            log("local ai: " + str(exc))

    def install_brain(self, which="small"):
        if self.brain_busy:
            return self.notify("I'm already downloading it. Hang on.", err=True)
        self.brain_busy = True
        what = localai.MODELS[which][3]
        self.notify(f"Installing a local AI: {what}. This downloads about {localai.MODELS[which][2]} MB. "
                    "You can keep using me.", secs=9)

        def work():
            try:
                LOCAL_AI.install.progress = lambda m: self.brain_events.put(("note", m))
                LOCAL_AI.install.run(which)
                self.brain_events.put(("ok", which))
            except Exception as exc:
                log("brain install failed: " + str(exc))
                self.brain_events.put(("err", str(exc) or type(exc).__name__))
        threading.Thread(target=work, daemon=True).start()

    def remove_brain(self):
        LOCAL_AI.remove()
        LOCAL_AI.refresh()
        self.notify("Local AI removed.")

    def drain_brain(self):
        while True:
            try:
                item = self.brain_events.get_nowait()
            except queue.Empty:
                break
            if item[0] == "note":
                self.notify(item[1], secs=5)
            elif item[0] == "ok":
                self.brain_busy = False
                self.settings["brain_model"] = LOCAL_AI.which = item[1]
                self.save_settings()
                LOCAL_AI.refresh()
                self.notify("Local AI installed. It runs on your computer, no key needed. /brain shows which AI I use.",
                            secs=9)
                self.warm_brain()
            else:
                self.brain_busy = False
                self.notify("Couldn't install the local AI: " + item[1][:160], err=True, secs=10)
        while True:
            try:
                item = self.ears_events.get_nowait()
            except queue.Empty:
                break
            self.ears_busy = False
            refresh_imports()
            if item[0] == "ok" and listen.installed():
                self.notify("Voice input installed. Press Ctrl+Alt+C, click MIC or type /talk and speak. "
                            "The first time she downloads a speech model (about 150 MB).", secs=10)
                self.start_hotkey()
                if self.pending_wake and self.settings.get("wake"):
                    self.pending_wake = False
                    self.start_wake()
            else:
                self.notify("Couldn't install voice input: " + item[1][:140]
                            + ". Try: py -m pip install faster-whisper sounddevice", err=True, secs=10)
        while True:
            try:
                self.talk_requests.get_nowait()
            except queue.Empty:
                break
            self.start_listening()

    def install_ears(self):
        if listen.installed():
            return self.notify("Voice input is already installed. /talk to try it.")
        if self.ears_busy:
            return self.notify("Already installing. Hang on.", err=True)
        self.ears_busy = True
        self.notify("Installing voice input (faster-whisper + sounddevice). This takes a minute...", secs=8)

        def work():
            import subprocess
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", *listen.PACKAGES],
                                   capture_output=True, text=True, timeout=900,
                                   creationflags=0x08000000 if sys.platform.startswith("win") else 0)
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                self.ears_events.put(("ok" if r.returncode == 0 else "err", tail[0]))
            except (OSError, subprocess.SubprocessError) as exc:
                self.ears_events.put(("err", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def start_hotkey(self):
        if self.hotkey_on or not self.win32.ok or not self.settings.get("talk_hotkey", True) or not listen.installed():
            return
        self.hotkey_on = self.win32.hotkey(str(self.settings.get("talk_key", "C"))[:1] or "C",
                                           lambda: self.talk_requests.put(1))
        if not self.hotkey_on:
            log("talk hotkey could not be registered (another app may use it)")

    # ---- hearing the PC's own audio
    def enable_hear(self, parent=None, ask=True):
        from tkinter import messagebox
        if sys.platform == "darwin":
            self.notify("macOS can't share its audio without a helper (like BlackHole), so I can't hear your Mac.",
                        err=True)
            return False
        if ask and not messagebox.askyesno(
                "Let Capri hear your PC?",
                "While this is on, Capri listens to whatever your PC is PLAYING (music, videos, game sound, voice "
                "calls).\n\n* The audio is kept only in memory (the last minute), never saved to disk.\n* It's "
                "turned into text on your computer, only when you ask (\"what did they just say\", \"summarize "
                "this\"). Nothing is sent anywhere unless you ask for a summary, which sends the TEXT to your AI.\n"
                "* A call can include other people's voices: tell them if that matters.\n* She uses the beat to dance "
                "to music. She pauses on banking/password windows and while she's talking.\n\nTurn on hearing your PC?",
                parent=parent, default="no", icon="warning"):
            return False
        self.settings["hear"] = True
        self.save_settings()
        if not self.start_hear():
            self.install_hear()
        return True

    def disable_hear(self):
        self.settings["hear"] = False
        self.save_settings()
        self.stop_hear()
        self.notify("Okay, I'm not listening to your PC any more.")

    def install_hear(self):
        if self.hear_installing:
            return
        self.hear_installing = True
        self.notify("Installing the PC-audio helper (soundcard). A few seconds...", secs=6)

        def work():
            import subprocess
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", *hearing.PACKAGES],
                                   capture_output=True, text=True, timeout=600,
                                   creationflags=0x08000000 if sys.platform.startswith("win") else 0)
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                self.hear_install_events.put(("ok" if r.returncode == 0 else "err", tail[0]))
            except (OSError, subprocess.SubprocessError) as exc:
                self.hear_install_events.put(("err", str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def start_hear(self):
        if self.hear is not None and self.hear.running:
            return True
        if not hearing.installed() or sys.platform == "darwin":
            return False
        loop = hearing.HearLoop(muted=lambda: self.speaker.speaking or not self.hear_ok)
        loop.start(lambda: hearing.loopback_chunks(lambda: loop._stop.is_set()))
        self.hear = loop
        self.notify("I can hear your PC now. Ask 'what did they just say' or 'summarize this'.", secs=6)
        return True

    def stop_hear(self):
        if self.hear is not None:
            self.hear.stop()
            self.hear = None

    def watch_hear(self, now):
        self.drain_call()
        while True:
            try:
                kind, text = self.hear_install_events.get_nowait()
            except queue.Empty:
                break
            self.hear_installing = False
            refresh_imports()
            if kind == "ok" and hearing.installed():
                if self.settings.get("hear"):
                    self.start_hear()
            else:
                self.notify("Couldn't install the PC-audio helper: " + text[:120] + ". Try: py -m pip install soundcard",
                            err=True, secs=10)
        self.drain_pc()
        h = self.hear
        if h is None:
            return
        if now - self.hear_ok_at > 2.0:                       # pause on private-looking windows
            self.hear_ok_at = now
            title = self.win32.foreground_title() if self.win32.ok else ""
            self.hear_ok = ledges.should_scan(title)
        for kind, val in h.take():
            if kind == "error":
                self.stop_hear()
                self.notify("I can't hear your PC: " + str(val)[:140], err=True, secs=9)
                return
            if kind == "beat":
                self.bop(now)
            elif kind == "music" and val and now - self.music_talk_at > 300 and not self.game and not self.boot:
                self.music_talk_at = now
                self.say_moment("music just started playing on the user's PC and you feel like bopping to the beat",
                                "Ooh, this one slaps.", 5, wait=3)
                if self.state in ("idle", "perch") and self.settings.get("hear_dance", True) and not self.calm:
                    self.go("dance", 6)

    def bop(self, now):
        if (not self.settings.get("hear_dance", True) or self.game or self.boot or self.calm or not self.hear
                or not self.hear.music):
            return
        if self.state in ("idle", "perch", "walk") and self.fy >= self.ground() - 3:
            self.hop(4.5)
            if now > self.icon_free_at(now):
                self.set_icon("note", 0.9)

    def icon_free_at(self, now):
        return self.icon[2] if self.icon else 0.0

    def hear_now(self, mode="last"):
        if self.hear is None or not self.hear.running:
            return self.notify("I'm not listening to your PC. Turn it on: /hear on", err=True)
        if not listen.installed():
            return self.notify("I need voice input to turn speech into text: /getears", err=True)
        pcm = self.hear.ring.last(20 if mode == "last" else 60)
        if len(pcm) < hearing.RATE * 2 * 2:
            return self.notify("I haven't heard anything from your PC lately.", err=True)
        if self.whisper is None:
            self.whisper = listen.Whisper(self.settings.get("ears_model", listen.MODEL))
        whisper = self.whisper
        self.notify("Listening back to the last bit...", secs=4)

        def work():
            try:
                text = whisper.transcribe(pcm)
                if mode == "summarize" and text:
                    reply = llm_reply([{"role": "user", "content": hearing.summary_prompt(text)}],
                                      "You are Capri, a helpful desktop companion.", max_tokens=250)
                    self.pc_events.put(("sum", text, reply))
                else:
                    self.pc_events.put(("last", text, ""))
            except Exception as exc:
                self.pc_events.put(("err", str(exc) or type(exc).__name__, ""))
        threading.Thread(target=work, daemon=True).start()

    def drain_pc(self):
        while True:
            try:
                kind, text, reply = self.pc_events.get_nowait()
            except queue.Empty:
                return
            if kind == "err":
                self.notify("Couldn't make that out: " + text[:140], err=True, secs=8)
            elif not text:
                self.notify("I didn't catch any speech in that.", err=True)
            elif kind == "last":
                if self.chat and self.chat.alive():
                    self.chat.system_line("They said: " + text[:700])
                self.say(text[-220:], 12, speak=None)
            else:
                if self.chat and self.chat.alive():
                    self.chat.add_bubble("assistant", reply, animate=False)
                self.say(reply[:220], 14, speak="priority")

    # ---- being in a voice call with friends (she hears them through the PC audio and answers into the call)
    def call_active(self):
        return self.callloop is not None and self.callloop.running

    def call_ready(self):
        if sys.platform == "darwin":
            return False, "Call mode can't hear a Mac's audio without a helper. It works on Windows and Linux."
        if not hearing.installed():
            return False, "I need the PC-audio helper first: /gethear"
        if not listen.installed():
            return False, "I need voice input to understand your friends: /getears"
        if self.speaker.engine not in ("fish", "edge"):
            return False, "To talk in a call I need my neural voice: /getvoice (the robot voice can't go into a call)."
        if not ai_available():
            return False, "I need an AI to answer with (a key, or /getbrain)."
        if self.audio_out is None:
            self.audio_out = audioout.Player(log=log)
        if self.audio_out.cable() is None:
            return False, CABLE_HELP
        return True, ""

    def enable_call(self, parent=None, ask=True, join=False):
        ok, why = self.call_ready()
        if not ok:
            self.notify(why, err=True, secs=14)
            return False
        if self.call_active():
            return True
        local = BRAIN["mode"] == "local" or (BRAIN["mode"] == "auto" and not read_api_key())
        if ask:
            from tkinter import messagebox
            if not messagebox.askyesno(
                    "Let Capri talk in your call?",
                    "Capri will listen to your voice call through your PC's audio and answer your friends OUT LOUD in "
                    "the call.\n\n* Your friends' voices are turned into text on your PC and never saved.\n* "
                    + ("The local AI writes her answers, so nothing leaves your PC.\n" if local else
                       "The recent TEXT of the conversation is sent to your AI provider to write her answers.\n")
                    + "* She answers only when someone says her name, a few times a minute at most.\n* She "
                    "announces herself to the call when she starts: tell your friends first.\n* Stop her any time "
                    "with /call off or by saying 'leave the call'.\n\nStart call mode?",
                    parent=parent, default="no", icon="warning"):
                return False
        if join:
            okj, whyj = self.agent_ready()
            if okj:
                self.call_after_agent = True
                started, msg = self.start_agent("Open Discord and join the voice channel where my friends are. "
                                                "Do not change any settings and do not type anything.")
                if started:
                    return True
                self.call_after_agent = False
                self.notify(msg, err=True)
            else:
                self.notify("I can't join Discord myself (" + whyj + "). Join the call yourself and I'll listen.",
                            secs=9)
        return self.start_call()

    def start_call(self):
        ok, why = self.call_ready()
        if not ok:
            self.notify(why, err=True, secs=14)
            return False
        if self.call_active():
            return True
        started_hear = self.hear is None or not self.hear.running
        if not self.start_hear():
            self.notify("I couldn't start hearing your PC.", err=True)
            return False
        self.call_started_hear = started_hear
        if self.whisper is None:
            self.whisper = listen.Whisper(self.settings.get("ears_model", listen.MODEL))
        self.speaker.call_player = audioout.call_player(self.audio_out, self.audio_out.cable())
        conv = calls.Conversation()
        self.call_err_shown = False
        self.callloop = calls.CallLoop(self.whisper, conv, self.call_answer,
                                       lambda kind, text: self.call_events.put((kind, text)),
                                       lambda text: self.speaker.speak(text, True, True))
        self.callloop.start()
        self.hear.tap = self.callloop.feed
        self.speaker.speak(calls.ANNOUNCE, True, True)
        self.notify("I'm in the call. Say my name and I'll answer. /call off to leave.", secs=8)
        return True

    def stop_call(self, announce=True):
        if self.callloop is None:
            return
        if self.hear is not None:
            self.hear.tap = None
        self.callloop.stop()
        self.callloop = None
        if announce:
            self.speaker.speak(calls.GOODBYE, True, True)
        if self.call_started_hear:
            self.call_started_hear = False
            self.root.after(8000, self.stop_hear if not self.settings.get("hear") else (lambda: None))
        self.root.after(8000, lambda: setattr(self.speaker, "call_player", None) if self.callloop is None else None)
        self.notify("Left the call.")

    def call_answer(self, conv):
        """Worker thread: ask the AI what Capri says next ('' = nothing)."""
        if not self.ai_budget.allow():
            return ""
        return llm_reply(conv.messages(), self.ai_system() + " " + calls.RULES, max_tokens=70)

    def drain_call(self):
        while True:
            try:
                kind, text = self.call_events.get_nowait()
            except queue.Empty:
                return
            if kind == "error":
                if not self.call_err_shown:
                    self.call_err_shown = True
                    self.notify("Call hiccup: " + text[:120], err=True, secs=7)
                continue
            if self.chat and self.chat.alive():
                self.chat.system_line(("Friend: " if kind == "heard" else "Me: ") + text[:300])
            if kind == "reply":
                self.say(text, 6, speak=None)

    # ---- instant voice/typed controls, opening apps and sites, the briefing
    def do_control(self, action):
        ok, msg = self.hands.do("press", "win+d") if action == "desktop" else self.hands.do(action)
        self.notify("Desktop." if ok and action == "desktop" else msg, err=not ok, secs=3)
        return ok

    def app_index(self):
        if time.time() - self.apps_at > 600 or not self.apps:
            try:
                self.apps = launcher.index_apps()
            except Exception as exc:
                log("app index failed: " + type(exc).__name__)
                self.apps = {}
            self.apps_at = time.time()
        return self.apps

    def open_thing(self, text):
        """'open discord', 'go to youtube', 'search for ...'. True if she handled it."""
        parsed = launcher.parse_open(text)
        if not parsed:
            return False
        if parsed[0] == "search":
            kind, target, label = "site", launcher.search_url(parsed[1], parsed[2]), f"a {parsed[2]} search"
        else:
            m = launcher.match(parsed[1], self.app_index())
            if not m:
                if text.lower().startswith(("open", "launch", "start", "run")) and self.agent_ready()[0]:
                    ok, why = self.start_agent(f"Open {parsed[1]}")
                    if not ok:
                        self.notify(why, err=True)
                else:
                    self.notify(f"I couldn't find '{parsed[1]}' on this computer.", err=True)
                return True
            kind, _name, target = m
            label = _name.title()
        try:
            op = launcher.opener(kind, target)
        except ValueError as exc:
            self.notify(str(exc).capitalize() + ".", err=True)
            return True
        ok, msg = self.hands.do("launch", op)
        self.notify(f"Opening {label}." if ok else msg, err=not ok, secs=3)
        return True

    def run_brief(self):
        now = time.time()
        today = time.strftime("%Y-%m-%d")
        timer = (self.timer_mode, self.timer_end - now) if self.timer_end else None
        lines, facts = brief.build([i["t"] for i in self.todos.open_items()], self.habits.pending(today),
                                   self.reminders, now, timer)
        if self.chat and self.chat.alive():
            for ln in lines:
                self.chat.system_line(ln)
        self.say_moment("the user asked for their daily briefing. What is pending: " + facts
                        + ". Say the gist in one short sentence", brief.fallback(lines), 12, speak="priority", wait=6)

    # ---- presets: one switch for the whole set of powers
    def apply_preset(self, name, parent=None, ask=True):
        if name not in presets.PRESETS:
            return False
        lines = presets.risky(name, self.settings)
        if ask and lines:
            from tkinter import messagebox
            if not messagebox.askyesno(
                    f"Switch to {presets.LABELS[name]}?",
                    "This turns ON:\n\n* " + "\n* ".join(lines) + "\n\nThings she hears or sees can be misread by "
                    "the AI, so don't hand her anything you can't undo. Tasks still ask before she types, she "
                    "stops when you move the mouse, and you can flip any single switch afterwards in Settings.\n\n"
                    f"Switch to {presets.LABELS[name]}?", parent=parent, default="no", icon="warning"):
                return False
        cfg = presets.PRESETS[name]
        self.hands.set_level(cfg["hands"])
        self.settings["hands"] = self.hands.level
        if self.hands.level != "full":
            self.pending = None
        self.settings["mic"] = cfg["mic"]
        self.settings["agent"] = cfg["agent"]
        if not cfg["agent"]:
            self.stop_agent()
        self.settings["ai_vision"] = cfg["ai_vision"]
        if not cfg["ai_vision"]:
            self.stop_spotter()
        self.aware = bool(cfg["aware"])
        self.settings["aware"] = self.aware
        if not self.aware:
            self.ctx = None
        if cfg["ledges"] and not self.settings.get("ledges"):
            self.enable_ledges(ask=False)
        elif not cfg["ledges"] and self.settings.get("ledges"):
            self.disable_ledges()
        self.settings["wake"] = cfg["wake"]
        self.settings["hear"] = cfg["hear"]
        self.save_settings()
        notes = []
        if cfg["hear"] and sys.platform != "darwin":
            if not self.start_hear():
                self.install_hear()
                notes.append("installing the PC-audio helper")
        elif not cfg["hear"]:
            self.stop_hear()
        if cfg["wake"]:
            if listen.installed():
                self.start_wake()
            else:
                self.pending_wake = True
                self.install_ears()
                notes.append("installing voice input so I can hear you")
        else:
            self.stop_wake()
        if (cfg["agent"] or cfg["ai_vision"]) and not read_api_key():
            notes.append("tasks and AI screen-watching need a Claude or Gemini key (Settings)")
        self.notify(f"Preset: {presets.LABELS[name]}." + (" " + "; ".join(notes).capitalize() + "." if notes else ""),
                    secs=8)
        win = self.settings_win
        try:
            if win and win.win.winfo_exists():                       # redraw Settings so every switch shows the truth
                win.win.destroy()
                self.settings_win = None
                self.root.after(150, self.open_settings)
        except tk.TclError:
            pass
        return True

    # ---- clipboard helper
    def run_clip(self, mode="explain", lang=""):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = ""
        if not text.strip():
            return self.notify("Your clipboard is empty (or isn't text). Copy something first.", err=True)
        if not ai_available():
            return self.notify("I need an AI for that (a key, or /getbrain for the local one).", err=True)
        local = BRAIN["mode"] == "local" or (BRAIN["mode"] == "auto" and not read_api_key())
        self.notify(f"Reading your clipboard ({min(len(text), clip.MAX_CHARS)} characters) with "
                    + ("the local AI..." if local else "your AI provider..."), secs=4)
        extra, user = clip.build(mode, text, lang)

        def work():
            try:
                self.clip_events.put(("ok", llm_reply([{"role": "user", "content": user}],
                                                      "You are Capri, a helpful desktop companion. " + extra,
                                                      max_tokens=350)))
            except Exception as exc:
                self.clip_events.put(("err", str(exc) or type(exc).__name__))
        threading.Thread(target=work, daemon=True).start()

    def drain_clip(self):
        while True:
            try:
                kind, text = self.clip_events.get_nowait()
            except queue.Empty:
                return
            if kind == "err":
                self.notify("Couldn't read that: " + text[:140], err=True, secs=8)
                continue
            text = text.strip() or "(nothing came back)"
            if self.chat and self.chat.alive():
                self.chat.add_bubble("assistant", text, animate=False)
            self.say(text[:220], 14, speak="priority")

    def enable_wake(self, parent=None):
        from tkinter import messagebox
        if not listen.installed():
            self.notify("I need ears first. Type /getears and I'll install voice input.", err=True)
            return False
        if not messagebox.askyesno(
                "Let Capri listen for \"Hey Capri\" and \"Choom\"?",
                "While this is on, your MICROPHONE stays open all the time (Windows shows its mic indicator).\n\n"
                "* Everything you say is turned into text ON YOUR COMPUTER. Nothing is sent anywhere and "
                "nothing is saved.\n* Anything that doesn't START with \"Hey Capri\", \"Capri\", \"Hey Choom\" or "
                "\"Choom\" is thrown away immediately.\n* If you chat with friends and say \"choom\" at the start of a "
                "sentence she WILL wake up and answer. Turn this off (right-click her) in calls.\n* It uses some "
                "CPU whenever someone talks near the mic.\n* Tasks she hears still ask for your OK first.\n\n"
                "Turn on wake word listening?", parent=parent, default="no", icon="warning"):
            return False
        self.settings["wake"] = True
        self.save_settings()
        self.start_wake()
        return True

    def disable_wake(self):
        self.settings["wake"] = False
        self.save_settings()
        self.stop_wake()
        self.notify("Okay, I'm not listening for my name any more.")

    def start_wake(self):
        if self.wake is not None and self.wake.running:
            return True
        if not listen.installed():
            return False
        if self.whisper is None:
            self.whisper = listen.Whisper(self.settings.get("ears_model", listen.MODEL))
        q = self.heard_events
        loop = listen.WakeLoop(
            self.whisper,
            lambda kind, text: q.put(("wake",) if kind == "wake" else
                                     (("error", text, "wake") if kind == "error" else ("heard", text, "wake"))),
            paused=lambda: self.speaker.speaking or self.listening)
        loop.start(lambda: listen.mic_chunks(lambda: loop._stop.is_set()))
        self.wake = loop
        self.notify("Listening for \"Hey Capri\" and \"Choom\" now. Right-click me to turn it off.", secs=6)
        return True

    def stop_wake(self):
        if self.wake is not None:
            self.wake.stop()
            self.wake = None

    def start_listening(self):
        """Push-to-talk. The mic is only open while she says 'Listening...', then it closes."""
        if self.listening:
            self.listen_stop = True                     # pressing it again means 'I'm done talking'
            return
        if not self.settings.get("mic", True):
            return self.notify("My microphone is switched off. Turn it on in Settings (or /preset some).", err=True)
        if not listen.installed():
            return self.notify("I need ears first. Type /getears in my chat and I'll install voice input.", err=True)
        self.listening, self.listen_stop = True, False
        self.speaker.stop()                             # never listen to herself
        self.say("Listening... (click me to finish)", 10, speak=None)
        self.sfx.play("blip")
        self.react("think")
        if self.whisper is None:
            self.whisper = listen.Whisper(self.settings.get("ears_model", listen.MODEL))
        whisper = self.whisper

        def work():
            try:
                text, state = listen.listen_once(listen.mic_chunks(lambda: self.listen_stop), whisper)
                self.heard_events.put(("heard", text, state))
            except Exception as exc:                    # no mic, no permission, model download failed...
                log(f"listening failed: {type(exc).__name__}: {exc}")
                self.heard_events.put(("error", str(exc) or type(exc).__name__))
        threading.Thread(target=work, daemon=True).start()

    def drain_heard(self):
        while True:
            try:
                item = self.heard_events.get_nowait()
            except queue.Empty:
                return
            from_wake = len(item) > 2 and item[2] == "wake" or item[0] == "wake"
            if not from_wake:
                self.listening = False
            if item[0] == "wake":                                   # she was called: say she's listening
                self.sfx.play("blip")
                self.react("think")
                self.say("Yeah?", 6, speak=None)
                continue
            if item[0] == "error":
                if from_wake:
                    self.stop_wake()
                self.notify("My ears failed: " + item[1][:140] + " (check your microphone and Windows' mic privacy "
                            "setting)", err=True, secs=9)
                continue
            kind, body = listen.intent(item[1])
            if self.agent is not None and kind != "stop":
                continue                                            # busy doing a task: only 'stop' is accepted
            if kind == "privacy":
                self.apply_preset("none", ask=False)
                continue
            if kind == "control":
                self.do_control(body)
                continue
            if kind == "hear":
                self.hear_now(body)
                continue
            if kind == "call":
                if body == "off":
                    self.stop_call()
                else:
                    self.enable_call(join=True)
                continue
            if kind == "launch":
                self.open_thing(body)
                continue
            if kind == "brief":
                self.run_brief()
                continue
            if kind == "focus":
                self.start_focus()
                continue
            if kind == "note":
                if not body:
                    self.say("What should I note? Say 'note that' and then the note.", 6, speak="priority")
                elif self.add_note(body):
                    self.react("happy")
                    self.notify(f"Noted: {body[:120]}", secs=5)
                    self.speak("Noted.", priority=True)
                else:
                    self.say("That's already in your notes.", 4, speak="priority")
                continue
            if kind == "notes":
                self.say(self.notes.spoken(body), 9, speak="priority")
                if self.chat and self.chat.alive():
                    for line in self.notes.lines(body):
                        self.chat.system_line(line)
                continue
            if kind == "remind":
                mins, what = listen.parse_reminder(body) or (None, "")
                if mins:
                    self.add_reminder(mins, what)
                continue
            if kind == "size":
                sz = sizing.spoken_size(body)
                if sz:
                    self.set_size(sz[1] if sz[0] == "abs" else sizing.step(self.size_base, sz[1]))
                continue
            if kind == "clip":
                pm = clip.parse_mode(re.sub(r".*?\b(explain|summari[sz]e|translate|fix|reply)\b", r"\1", body, count=1)) \
                    if re.search(r"\b(explain|summari[sz]e|translate|fix|reply)\b", body) else ("explain", "")
                self.run_clip(*(pm or ("explain", "")))
                continue
            if kind == "none":
                self.say("Didn't catch that.", 3, speak=None)
            elif kind == "stop":
                if self.agent is not None:
                    self.stop_agent()
                else:
                    self.say("Okay.", 2, speak=None)
            elif kind == "task":
                self.notify(f'Heard: "{body}"', secs=5)
                ok, why = self.start_agent(body)
                if not ok:
                    self.notify(why, err=True, secs=8)
            else:
                self.open_chat(hidden=from_wake)
                if self.chat and self.chat.alive():
                    self.route_reply = self.call_active()           # in a call, her answer goes to the friends too
                    self.chat.submit(body)

    # ---- doing tasks for the user (the agent)
    def agent_ready(self):
        """(ok, why_not) for starting a task right now."""
        if self.agent is not None:
            return False, "I'm already doing something. Click me or /stop to stop it."
        if not read_api_key():
            return False, "I need an AI key first (Settings)."
        if self.hands.level != "full":
            return False, "That needs Full control in Settings."
        if not self.settings.get("agent"):
            return False, "Turn it on first: /agent on"
        return True, ""

    def enable_agent(self, parent=None):
        from tkinter import messagebox
        if not messagebox.askyesno(
                "Let Capri do tasks for you?",
                "When you type /do <task>, Capri will LOOK at your screen (a screenshot is sent to Claude, using your "
                "key and credits), then click, type and press keys in your apps to get it done, for up to 20 steps.\n\n"
                "* She can click and type in ANY app, including sending messages.\n* Every text she wants to type "
                "is shown to you for approval first.\n* She stops the moment you move the mouse, click her, or type "
                "/stop. She also stops on banking/password windows.\n* She never enters passwords or payments.\n"
                "* AI can misread a screen and click the wrong thing. Don't use it for anything you can't undo.\n\n"
                "Turn on tasks?", parent=parent, default="no", icon="warning"):
            return False
        self.settings["agent"] = True
        self.save_settings()
        return True

    def start_agent(self, task):
        ok, why = self.agent_ready()
        if not ok:
            return False, why
        task = " ".join((task or "").split())[:300]
        if not task:
            return False, "Tell me what to do: /do open Discord and tell my friends I'll be on in 15"
        from tkinter import messagebox
        if not messagebox.askyesno(
                "Do this task?",
                f"Capri will try to do this by clicking and typing on your screen:\n\n  {task}\n\n"
                "Move the mouse, click her, or type /stop to take over at any time.", default="no"):
            return False, "Okay, cancelled."
        h = hands.Hands(level=self.hands.level, threaded=False, log=log, per_min=120)
        ag = agent.Agent(
            ledges.capture, self._agent_ask, h,
            title=self.win32.foreground_title, pointer=self.win32.cursor_pos, approve=self._agent_approve,
            blocked=self._agent_blocked, note=lambda t: self.agent_events.put(("note", t)), budget=self.agent_budget)
        self.agent = ag
        if self.chat and self.chat.alive():
            self.chat.win.withdraw()                    # get the chat out of the way of the apps
        self.say("On it.", 3, speak=None)
        self.react("happy")

        def work():
            try:
                res = ag.run(task)
            except Exception as exc:
                log("agent crashed: " + type(exc).__name__)
                res = ("error", "Something broke while I was doing that.")
            self.agent_events.put(("end", res[0], res[1], task))
        threading.Thread(target=work, daemon=True).start()
        return True, ""

    @staticmethod
    def _agent_ask(media_type, b64, system, prompt):
        if detect_provider(read_api_key()) == "gemini":
            return vision_ask(system + GEMINI_AGENT_NOTE, media_type, b64, prompt, 300, room=8)
        return vision_ask(system, media_type, b64, prompt, 300, AGENT_MODEL)

    def stop_agent(self):
        if self.agent is not None:
            self.agent.stop()

    def _agent_blocked(self, x, y):
        """True when (x, y) is on top of Capri herself or her bubble."""
        return (self.fx - self.fw * 0.8 <= x <= self.fx + self.fw * 0.8 and self.fy - self.fh * 1.8 <= y <= self.fy + 20)

    def _agent_approve(self, kind, detail):
        """Called on the agent's thread: ask the user on the main thread and wait for the answer."""
        box = {}
        ev = threading.Event()
        self.agent_events.put(("approve", detail, box, ev))
        ev.wait(90)
        return bool(box.get("ok"))

    def drain_agent(self):
        while True:
            try:
                item = self.agent_events.get_nowait()
            except queue.Empty:
                return
            if item[0] == "note":
                if self.chat and self.chat.alive():
                    self.chat.system_line(item[1])
            elif item[0] == "approve":
                from tkinter import messagebox
                _kind, detail, box, ev = item
                box["ok"] = messagebox.askyesno("Capri wants to type this", f"Type this?\n\n  {detail}", default="no")
                ev.set()
            elif item[0] == "end":
                _kind, status, summary, task = item
                self.agent = None
                if self.call_after_agent:
                    self.call_after_agent = False
                    if status == "done":
                        self.root.after(1500, self.start_call)
                    else:
                        self.notify("I couldn't join the call: " + summary, err=True, secs=9)
                if self.chat and self.chat.alive():
                    self.chat.win.deiconify()
                    self.chat.system_line(("Done: " if status == "done" else "Stopped: ") + summary, err=status != "done")
                self.say_moment(f"you just {'finished' if status == 'done' else 'stopped'} doing a task for the user "
                                f"('{task}'). Result: {summary}", summary, 8, speak="priority", wait=4)

    def disable_vision(self):
        self.settings["ai_vision"] = False
        self.save_settings()
        self.stop_spotter()
        self.say("Okay, I stopped watching your screen.", 4, speak=None)

    def start_spotter(self, manual=False):
        if not read_api_key():
            self.say("I need an AI key to watch. Add one in Settings.", 5, speak=None)
            return False
        if self.spotter and self.spotter.active:
            self.spotter_manual = self.spotter_manual or manual
            return True
        cap = int(self.settings.get("vision_daily_cap", 600))
        self.spotter = vision.Spotter(
            ledges.capture, self._spotter_ask, interval=float(self.settings.get("vision_interval", 6)),
            budget=speech.Budget(per_min=20, per_day=cap, store=self.settings.setdefault("vision_day", {})))
        self.spotter_manual = manual
        self.spotter_until = time.time() + 2 * 3600 if manual else 0.0
        self.refresh_spotter(time.time())          # privacy check + prompts BEFORE the first frame can be sent
        self.spotter.start()
        self.say("I'm watching. A little eye shows whenever I'm looking.", 5, speak=None)
        return True

    def stop_spotter(self):
        if self.spotter:
            self.spotter.stop()
        self.spotter, self.spotter_manual, self.spotter_until = None, False, 0.0

    def _spotter_ask(self, media_type, b64, recent, game, system, question=None):
        return vision_ask(system, media_type, b64, question or vision.spotter_user(game, recent),
                          200 if question else 120)

    def refresh_spotter(self, now, context=True):
        """Decide whether the spotter may look right now, and keep the AI's instructions current."""
        sp = self.spotter
        title = self.win32.foreground_title() if self.win32.ok else ""
        idle = self.win32.idle_seconds() if self.win32.ok else 0.0
        sp.allowed = ledges.should_scan(title) and idle < 120 and (not self.win32.ok or bool(title))
        if context:                                          # what the AI is told about her and the user
            self.spotter_ctx_at = now
            sp.game = self.game.name if self.game else ""
            sp.interval = float(self.settings.get("vision_interval", 6))
            sp.system = vision.spotter_system(self.persona_text, self.mind.context(now, self.doing(),
                                              self.activity_phrase()), self.settings.get("roast", "mild"),
                                              self.memory.context())

    def update_spotter(self, now):
        sp = self.spotter
        if not sp:
            return
        if sp.error:
            err, sp.error = sp.error, ""
            self.stop_spotter()
            self.say(f"I stopped watching: {err}", 8, speak=None)
            return
        if not sp.active:
            return
        if self.spotter_until and now > self.spotter_until:
            self.stop_spotter()
            self.say("That's two hours of watching. I'll stop. /watch on to keep going.", 6, speak=None)
            return
        self.refresh_spotter(now, context=now - self.spotter_ctx_at > 5)
        for res in sp.take():
            if res["event"] != "none":
                self.game_event(res["event"], res["n"], line=res["say"] or None)
            elif res["say"]:
                self.say(res["say"], 6, speak="priority")
                self.recent_lines.append(res["say"])

    def look(self, question=""):
        """One-off: look at the screen now and answer (in the chat if it's open, else in a bubble)."""
        if not read_api_key():
            self.look_results.put(("", "401: no API key"))
            return
        system = (speech.system_prompt(self.persona_text, self.mind.context(time.time(), self.doing()), "off",
                                       self.memory.context())
                  + " Answer the user's question about their screenshot in at most two short sentences.")
        q = question.strip() or "What's going on on my screen? Comment briefly."

        def work():
            try:
                text = vision.look_once(ledges.capture, self._spotter_ask, q, system)
                self.look_results.put((" ".join((text or "").split())[:400] or "I looked but have nothing to say.", ""))
            except Exception as exc:
                self.look_results.put(("", str(exc) or type(exc).__name__))
        threading.Thread(target=work, daemon=True).start()

    def draw_eye(self, c, lfx, top):
        sp = self.spotter
        if not sp or not sp.active:
            return
        x, y = lfx - self.fw * 0.5 - 4, top + 10
        col = C_GREEN if sp.allowed else C_DIM                 # grey while paused
        c.create_oval(x - 9, y - 5, x + 9, y + 5, outline=col, width=2)
        c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=col, outline="")

    def start_game(self, key, manual=False):
        """A game session: she keeps small and quiet and comments on events."""
        self.end_game(quiet=True)
        self.game = gamemode.Session(key, self.rng, self.settings.get("roast", "mild"))
        self.game_manual, self.game_seen = manual, time.time()
        if self.settings.get("game_quiet", True):
            self.calm_before_game, self.calm = self.calm, True
        self.surf, self.icon = None, None
        wa = self.work_area()
        self.fx, self.fy = wa[2] - self.fw * 0.8, float(self.ground())      # tuck into the corner
        self.go("idle", 5)
        self.say_ai("game_start", {"game": self.game.name}, self.game.start_line(), 6, speak="priority")
        dets = self.game_cfg.get(key)
        if dets:
            self.reactor = reactor.Reactor(dets, (self.sw, self.sh))
            self.reactor.start()
        if self.settings.get("ai_vision") and read_api_key():
            self.start_spotter(manual=False)

    def end_game(self, quiet=False):
        g, self.game = self.game, None
        if not g:
            return
        if self.reactor:
            self.reactor.stop()
            self.reactor = None
        if not self.spotter_manual:
            self.stop_spotter()
        if self.calm_before_game is not None:
            self.calm, self.calm_before_game = self.calm_before_game, None
        if g.events or g.minutes() >= 10:
            hist = self.settings.setdefault("games", [])
            hist.append(g.summary())                                   # numbers only
            del hist[:-20]
            self.save_settings()
            if not quiet:
                self.say_ai("recap", {"game": g.name, "kills": g.kills, "deaths": g.deaths, "rw": g.rounds_w,
                                      "rl": g.rounds_l, "minutes": int(g.minutes())}, g.recap(), 14, speak="priority")

    def game_tick(self, now, key, has_title):
        """Start a session when a supported game is in front; end it once it has been gone a while."""
        if key:
            self.game_seen = now
            if not self.game:
                self.start_game(key)
            elif self.game.key == "other":
                self.game.key, self.game_manual = key, False
            elif self.game.key != key:
                self.start_game(key)
        elif self.game and has_title and now - self.game_seen > (3 * 3600 if self.game_manual else 180):
            self.end_game()

    def game_event(self, kind, n=1, line=None):
        """Something happened in the game (you told her, a detector or the AI spotter saw it)."""
        if not self.game:
            self.start_game("other", manual=True)
        g = self.game
        g.level = self.settings.get("roast", "mild")
        preset = g.event(kind, n)                       # counts it. The preset line is only a fallback
        if line:
            self.say(line, 6, speak="priority")
            self.recent_lines.append(line)
        elif preset:
            self.say_ai("game", {"game": g.name, "event": kind, "n": n, "kills": g.kills, "deaths": g.deaths,
                                 "kstreak": g.kstreak, "dstreak": g.dstreak}, preset, 6, speak="priority")
        if kind in ("kill", "ace", "clutch", "round_win", "match_win"):
            self.set_icon("star", 1.6)
            self.sfx.play("success" if kind in ("ace", "clutch", "match_win") else "confirm")
            if kind in ("ace", "clutch", "match_win"):
                self.spawn_confetti(30)
            self.react("happy")
        else:
            self.sfx.play("fail")
            self.react("error")
        return preset

    def drain_reactor(self):
        if not self.reactor:
            return
        for kind, count in self.reactor.take():
            self.game_event(kind, count)
        if self.reactor and self.reactor.error:
            err, self.reactor.error = self.reactor.error, ""
            self.reactor.stop()
            self.reactor = None
            self.say(f"Auto-detect stopped ({err}). You can still tell me with /kill and /death.", 8, speak=None)

    def start_peek(self):
        """Peek out from the side of the screen, then slide back in."""
        if self.state in ("tp_out", "tp_in", "drag"):
            return
        wa = self.work_area()
        self.surf = None
        self.peek_side = self.rng.choice((-1, 1))
        self.fx = wa[0] + self.fw * 0.05 if self.peek_side < 0 else wa[2] - self.fw * 0.05    # half of her shows
        self.fy = self.ground()
        self.dir = 1 if self.peek_side < 0 else -1          # looking back toward the screen
        self.angle = self.angle_t = 0.0
        self.go("peek", self.rng.uniform(4.0, 7.0))
        self.anim = "look-a" if "look-a" in getattr(self.art, "map", {}) else "idle"
        self.peek_said = False

    def feed(self):
        """Ramen: makes her very happy."""
        now = time.time()
        self.settings["last_fed"] = now
        self.mind.fed(now)
        self.say_moment("the user just fed you a bowl of ramen and you love it",
                        self.rng.choice(["Ramen! You're preem.", "Noodles. Nova.", "Slurp. Best gig ever."]), 5,
                        speak="priority", wait=4)
        self.set_icon("heart", 2.0)
        self.spawn_confetti(15)
        self.react("happy")
        self.sfx.play("confirm")
        return True

    def open_breach(self):
        if self.breach_win:
            try:
                if self.breach_win.win.winfo_exists():
                    self.breach_win.win.lift()
                    return
            except tk.TclError:
                pass
        self.breach_win = BreachWindow(self)
        self.say_moment("the user is starting a hacking minigame (Breach Protocol) where they match code sequences",
                        "Jack in, choom. Match the daemons.", 4, wait=3)

    def open_simon(self):
        if self.simon_win:
            try:
                if self.simon_win.win.winfo_exists():
                    self.simon_win.win.lift()
                    return
            except tk.TclError:
                pass
        self.simon_win = SimonWindow(self)
        self.say_moment("the user is starting Simon, the memory game where they copy a growing colour sequence",
                        "Watch the lights, choom. Then copy them.", 4, wait=3)

    def simon_result(self, rounds):
        self.say_moment(f"the user's Simon memory game just ended after {rounds} round(s) (8 or more is great)",
                        f"Simon: {rounds} round(s). " + ("Nova memory!" if rounds >= 8 else "Not bad, choom."), 5,
                        wait=4)

    def breach_result(self, done, total):
        if done == total:
            self.say_moment("the user fully completed the hacking minigame breach", "Breach complete! Preem netrunning.",
                            6, speak="priority", wait=4)
            self.spawn_confetti(40)
            self.sfx.play("success")
        elif done:
            self.say_moment(f"the user partly completed the hacking minigame: {done} of {total} daemons",
                            f"Partial breach: {done}/{total}. Not bad, choom.", 5, wait=4)
            self.sfx.play("confirm")
        else:
            self.say_moment("the user failed the hacking minigame", "Flatlined. The ICE won this round.", 5, wait=4)
            self.sfx.play("fail")

    def watch_world(self, now):
        """Battery, Night City Radio and hunger. All local; nothing is sent anywhere."""
        battery = getattr(self.win32, "battery", None)
        if battery and self.win32.ok and now >= self.next_battery:
            self.next_battery = now + 30
            pct, plugged = battery()
            line = world.battery_event(self.battery_state, pct, plugged)
            if line:
                self.say_moment(f"laptop battery update: {line}", line, 8, speak="priority", wait=4)
                self.set_icon("!" if not plugged else "heart", 3.0)
                self.sfx.play("alert" if not plugged else "confirm")
        if self.settings.get("radio") and now >= self.next_radio and not self.calm:
            self.next_radio = now + self.rng.randint(240, 480)
            self.say_moment("you're the DJ of Night City Radio: do a short, fun radio station drop",
                            self.rng.choice(world.RADIO), 8, wait=4)
        if now >= self.next_hungry and not self.calm:
            self.next_hungry = now + 3 * 3600
            if now - self.settings.get("last_fed", now) > 6 * 3600:
                self.say_moment("you're hungry and want the user to feed you ramen by typing /feed",
                                "Hungry, choom. /feed me ramen?", 8, wait=4)
        lt = time.localtime(now)
        today = time.strftime("%Y-%m-%d", lt)
        if not self.calm and self.state in ("idle", "perch", "walk", "lounge"):
            if lt.tm_hour >= 20 and self.settings.get("habit_nag_day") != today:
                self.settings["habit_nag_day"] = today
                nag = self.habits.nag(today)
                if nag:
                    self.say_moment(f"remind them about habits they still have to do today: {nag}", nag, 9, wait=4)
            elif (lt.tm_hour * 60 + lt.tm_min >= 20 * 60 + 30 and self.settings.get("journal_prompt_day") != today
                  and not self.journal.has(today)):
                self.settings["journal_prompt_day"] = today
                self.say_moment("ask how their day was from 1 to 5 and tell them to answer by typing /feel and a number",
                                "How was today, 1 to 5? Tell me: /feel 4 pretty good", 10, wait=4)
            elif (lt.tm_hour >= 21 and self.settings.get("recap_day") != today
                  and self.settings.get("track_time", True) and self.daylog.total(today) >= 20):
                self.settings["recap_day"] = today
                self.say_moment(f"comment on how they spent their time today: {self.daylog.summary(today)}",
                                self.daylog.summary(today), 12, wait=4)
        if now >= self.next_memory_cb and not self.calm:
            self.next_memory_cb = now + self.rng.randint(5400, 9000)
            line = self.memory.callback(self.rng)
            if line:
                self.say_moment(f"bring this up casually: {line}", line, 8, wait=4)

    def set_hands(self, level):
        self.hands.set_level(level)
        self.settings["hands"] = self.hands.level
        self.save_settings()
        if self.hands.level != "full":
            self.pending = None
        self.say({"visual": "Hands off. I'll just mime.", "media": "Media keys only, on request.",
                  "full": "Full control. Use it wisely, choom."}[self.hands.level], 5, speak=None)

    def open_settings(self):
        if self.settings_win:
            try:
                if self.settings_win.win.winfo_exists():
                    self.settings_win.win.lift()
                    return
            except tk.TclError:
                pass
        self.settings_win = SettingsWindow(self)

    def set_calm(self, on):
        if bool(on) != self.calm:
            self.toggle_calm()

    def set_checkins(self, on):
        if bool(on) != self.checkins:
            self.toggle_checkins()

    def set_fish_key(self, key):
        if key:
            save_fish_key(key)
            msg = "Fish Audio key saved. Using Capri's real voice."
        else:
            clear_fish_key()
            msg = "Fish Audio key removed. Back to the system voice."
        self.speaker.stop()
        self.speaker = make_speaker()
        self.say(msg, 5, speak="priority" if key else None)

    def hands_do(self, action, arg=None):
        """Run a hands action now (media keys). Returns (ok, message)."""
        ok, msg = self.hands.do(action, arg)
        self.say(msg, 4, speak=None)
        if ok:
            self.set_icon("star", 1.4)
            self.sfx.play("click")
        return ok, msg

    def queue_action(self, action, arg, label, secs, cancel_on_input=False):
        """Do `action` after a visible countdown. Click her to cancel."""
        ok, msg = self.hands.check(action, arg)
        if not ok:
            return False, msg
        now = time.time()
        self.pending = {"action": action, "arg": arg, "label": label, "t0": now, "at": now + secs,
                        "shown": None, "cancel_on_input": cancel_on_input}
        self.set_icon("!", secs)
        self.sfx.play("alert")
        return True, f"{label} in {secs} seconds. Click where you want it. Click me to cancel."

    def cancel_pending(self, msg="Okay, cancelled."):
        self.pending = None
        self.icon = None
        self.say(msg, 3, speak=None)

    def tick_pending(self, now):
        p = self.pending
        if p["cancel_on_input"] and now - p["t0"] > 1.0 and self.win32.ok and self.win32.idle_seconds() < 3:
            return self.cancel_pending("You're back, so I stopped.")
        if now >= p["at"]:
            self.pending = None
            self.icon = None
            ok, msg = self.hands.do(p["action"], p["arg"])
            self.say(msg, 5, speak=None)
            return
        left = int(p["at"] - now) + 1
        if left != p["shown"]:
            first = p["shown"] is None
            p["shown"] = left
            self.say(f"{p['label']} in {left}... click me to cancel!", 2, speak="priority" if first else None)

    def reflexes(self, now, idle):
        """Things she does by herself: only at Full control, only if you switched the reflex on, always announced."""
        if idle < 5:
            self.reflex_done = {}
        if self.hands.level != "full" or self.pending:
            return
        if self.settings.get("reflex_lock") and idle > 15 * 60 and not self.reflex_done.get("lock"):
            self.reflex_done["lock"] = True
            self.queue_action("lock", None, "Locking your screen", 10, cancel_on_input=True)
        elif (self.settings.get("reflex_pause") and idle > 5 * 60 and self.ctx in ("video", "music")
              and not self.reflex_done.get("pause")):
            self.reflex_done["pause"] = True
            self.queue_action("playpause", None, "Pausing your media", 10, cancel_on_input=True)

    def update_busy(self, now):
        """Mime typing while you're busy (Windows only; she only knows THAT you're busy, never which keys)."""
        if not (self.win32.ok and self.settings.get("type_along", True)) or self.state not in ("idle", "perch"):
            self.typing_along, self.busy_since = False, None
            return
        idle = self.win32.idle_seconds()
        if idle < 0.8:
            self.busy_since = self.busy_since or now
            self.typing_along = now - self.busy_since > 1.5
        elif idle > 1.6:
            self.busy_since, self.typing_along = None, False

    def draw_keyboard(self, c, cx, base):
        w, h = self.fw * 1.15, 16
        x1, y1 = cx - w / 2, base - h
        round_rect(c, x1, y1, x1 + w, base, 4, fill=C_BLACK, outline=C_GREEN, width=1)
        cols, rows = 11, 3
        kw, kh = (w - 10) / cols, (h - 6) / rows
        lit = {(self.rng.randrange(cols), self.rng.randrange(rows)) for _ in range(3)}
        for r in range(rows):
            for k in range(cols):
                kx, ky = x1 + 5 + k * kw, y1 + 3 + r * kh
                c.create_rectangle(kx + 1, ky + 1, kx + kw - 1, ky + kh - 1,
                                   fill=C_GREEN if (k, r) in lit else C_PANEL2, outline="")

    def activity_phrase(self):
        g = self.game
        if g:
            tone = "be supportive" if g.level == "off" else "cheer their good plays and tease them when they die"
            return f"playing {g.name} (this session: {g.kills} kills, {g.deaths} deaths); {tone}"
        return awareness.PHRASE.get(self.ctx, "") if (self.aware and self.ctx) else ""

    def set_aware(self, on):
        self.aware = bool(on)
        self.settings["aware"] = self.aware
        self.save_settings()
        if not self.aware:
            self.ctx = None
        self.say("I'll keep an eye on which app you're in. Never what you type." if self.aware
                 else "Okay, I'm not watching your apps anymore.", 5)

    def react_context(self, cat):
        self.say_ai("context", {"activity": awareness.PHRASE.get(cat, cat)}, awareness.line(cat, self.rng), 7)
        icon, act = {"cyberpunk": ("star", "dance"), "game": ("star", None), "video": (None, "lounge"),
                     "music": ("note", "dance"), "coding": (None, "perch"), "writing": (None, "perch"),
                     "chat": ("?", "curious"), "social": ("?", None), "school": ("star", None),
                     "ai": ("?", None)}.get(cat, (None, None))
        if icon:
            self.set_icon(icon, 3.0)
        if act == "dance":
            self.go("dance", 4)
        elif act == "lounge":
            self.go("lounge", 20)
        elif act == "curious":
            self.go("curious", 6)
        elif act == "perch" and self.surfaces and not self.surf:
            self.teleport("perch")

    def watch_context(self, now):
        """Notice what kind of app is in front and when you come back from being away (Windows only)."""
        if not self.win32.ok or now < self.next_watch:
            return
        self.next_watch = now + 2.0
        idle = self.win32.idle_seconds()
        if idle > 600 and not self.away:
            self.away = True
            if self.state in ("idle", "perch", "walk", "lounge", "curious"):
                self.go("sleep")
        elif self.away and idle < 5:
            self.away = False
            self.poke_awake()
            self.say_moment("the user just came back to the computer after being away for a while",
                            self.rng.choice(["Welcome back, choom!", "There you are. I counted the minutes.",
                                             "Oh! You're back!"]), 5, wait=3)
            self.react("happy")
            self.set_icon("heart", 1.6)
        self.reflexes(now, idle)
        self.meeting_tick(now)
        if not self.aware:
            return
        if not self.settings.get("aware_notice") and now - self.t_start > 25:
            self.settings["aware_notice"] = True
            self.save_settings()
            self.say("Heads up: I can see which app is in front (never what you type). Only a short hint like "
                     "'coding' goes to the AI when we chat. Right-click me > Awareness to turn it off.", 16)
        title = self.win32.foreground_title()
        cat = awareness.classify(title)                              # the title is not kept anywhere
        self.game_tick(now, gamemode.detect_game(title), bool(title))
        dt, self.last_watch = min(5.0, now - self.last_watch), now
        if self.settings.get("track_time", True) and idle < 60:      # only the category's minutes are saved
            self.daylog.add(time.strftime("%Y-%m-%d"), cat, dt)
        if cat != self.ctx:
            self.ctx, self.ctx_since, self.ctx_done = cat, now, False
            return
        if not cat:
            return
        passive = self.state in ("idle", "perch", "walk")
        if not self.ctx_done and now - self.ctx_since >= 8 and passive and not self.calm:
            self.ctx_done = True
            if now >= self.ctx_cool.get(cat, 0):
                self.ctx_cool[cat] = now + 240
                self.react_context(cat)
        after = awareness.NUDGE_AFTER.get(cat)
        if after and now - self.ctx_since > after and now >= self.ctx_nudge and not self.calm:
            self.ctx_nudge = now + 1200
            self.say_ai("nudge", {"activity": awareness.PHRASE.get(cat, cat), "minutes": int((now - self.ctx_since) / 60)},
                        awareness.nudge(cat), 10)

    def scheduled(self, now):
        self.watch_context(now)
        self.watch_ledges(now)
        self.drain_reactor()
        self.drain_ai(now)
        self.watch_size(now)
        self.watch_hear(now)
        self.drain_agent()
        self.drain_brain()
        self.drain_clip()
        self.drain_heard()
        self.check_voice_install()
        self.update_spotter(now)
        if self.pending:
            self.tick_pending(now)
        if self.msgs and now > self.bubble_until + 0.4 and now - self.t_start > 8:
            text = self.msgs.pop(0)
            self.say_moment(f"it's a special day: {text}", text, 7, speak="priority", wait=4)
            if text.startswith(("Achievement", "Happy", "Merry")):
                self.spawn_confetti(40)
            self.sfx.play("achievement" if text.startswith("Achievement") else "blip")
        if now >= self.next_todo and not self.calm:
            self.next_todo = now + self.rng.randint(3600, 5400)
            nag = self.todos.nag()
            if nag:
                self.say_moment(f"remind them about their to-do list: {nag}", nag, 9, wait=4)
        self.watch_world(now)
        if self.speaker.speaking:
            self.talk_until = now + 0.3          # her mouth moves while she talks
        err = self.speaker.last_error
        if err and err != self._voice_err:
            self._voice_err = err
            self.say("My voice is acting up: " + err[:80], 8, speak=None)
        if now >= self.next_save:
            self.next_save = now + 60
            self.mind.tick(now)
            self.save_settings()
        if self.timer_end and now >= self.timer_end:
            if self.timer_mode == "focus":
                self.say_moment(f"the user's focus timer just finished and they get a {BREAK_MIN} minute break; "
                                "tell them to get up and move around",
                                f"Focus done! {BREAK_MIN} min break. Move around.", 12, speak="priority", wait=4)
                self.timer_mode, self.timer_end = "break", now + BREAK_MIN * 60
                self.poke_awake()
                self.party()
            else:
                self.say_moment("the user's break just ended; ask if they want another focus round",
                                "Break's over. Another round?", 12, speak="priority", wait=4)
                self.timer_mode = self.timer_end = None
                self.react("happy")
        for r in [r for r in self.reminders if now >= r[0]]:
            self.reminders.remove(r)
            self.poke_awake()
            self.say("Reminder: " + r[1], 15, speak="priority")
            self.set_icon("!", 3.0)
            self.sfx.play("alert")
            self.hop(7)
        if self.checkins and now >= self.next_checkin and not self.calm:
            self.next_checkin = now + random.randint(*CHECKIN_EVERY)
            self.poke_awake()
            self.say_ai("checkin", {}, self.mind.line("checkin", now), 10)
        if now >= self.next_chatter and self.state in ("idle", "perch") and not self.calm:
            self.next_chatter = now + random.randint(60, 150)
            self.say_ai("idle", {}, self.mind.line("idle", now), 5)

    def react_to_pointer(self, now, dt):
        mx, my = self.pointer
        px, py, pt = self.pointer_prev
        speed = math.hypot(mx - px, my - py) / max(0.001, now - pt)
        self.pointer_prev = (mx, my, now)
        cx, cy = self.fx, self.fy - self.fh * 0.5
        dist = math.hypot(mx - cx, my - cy)
        passive = self.state in ("idle", "perch", "walk", "lounge", "sleep", "curious")
        if passive and dist < self.fw * 0.8 and speed > 2200 and now - self.last_startle > 10 and self.state != "sleep":
            self.last_startle = now
            self.react("startle")
        if passive and dist < self.fw * 0.7:
            self.near_since = self.near_since or now
            if now - self.near_since > 1.6:
                self.near_since = None
                if self.state in ("sleep", "lounge"):
                    self.say_moment("the user's mouse cursor came close while you were napping and woke you up",
                                    "...hm? Oh. Hi.", 4, wait=2.5)
                    self.poke_awake()
                elif self.state in ("idle", "perch"):
                    self.dir = 1 if mx > self.fx else -1
                    self.say_moment("the user's mouse cursor is hovering near you and you're curious",
                                    "Hm?", 3, wait=2.5)
                    self.angle_t = 5.0 * self.dir
        else:
            self.near_since = None

    # ---- mouse
    def on_press(self, e):
        self.press = (e.x_root, e.y_root, time.time(), False)
        self.drag_hist = []
        self.poke_awake()

    def on_drag(self, e):
        if not self.press:
            return
        x0, y0, t0, dragging = self.press
        if not dragging and math.hypot(e.x_root - x0, e.y_root - y0) > 6:
            dragging = True
            self.press = (x0, y0, t0, True)
            self.surf = None
            self.go("drag")
            self.anim = "jump"
        if dragging:
            now = time.time()
            wa = self.work_area()
            self.fx = min(max(e.x_root, wa[0] + 20), wa[2] - 20)
            self.fy = min(max(e.y_root + self.fh * 0.45, wa[1] + self.fh), self.ground())
            self.drag_hist = (self.drag_hist + [(now, e.x_root, e.y_root)])[-5:]
            if len(self.drag_hist) >= 2:
                a, b = self.drag_hist[0], self.drag_hist[-1]
                vx = (b[1] - a[1]) / max(0.001, b[0] - a[0])
                self.angle_t = max(-28, min(28, -vx * 0.02))
            self.place()

    def on_release(self, e):
        if not self.press:
            return
        dragging = self.press[3]
        self.press = None
        now = time.time()
        if dragging:
            vx = vy = 0.0
            if len(self.drag_hist) >= 2:
                a, b = self.drag_hist[0], self.drag_hist[-1]
                dtm = max(0.001, b[0] - a[0])
                if now - b[0] < 0.15:
                    vx, vy = (b[1] - a[1]) / dtm / 25.0, (b[2] - a[2]) / dtm / 25.0
            self.vx, self.vy = max(-30, min(30, vx * 0.6)), max(-30, min(30, vy * 0.6))
            self.go("air")
            return
        if self.pending:
            return self.cancel_pending("Okay, cancelled.")
        if self.boot:
            self.finish_boot(skipped=True)
            return
        if self.agent is not None:
            self.stop_agent()
            return
        if self.listening:
            self.listen_stop = True
            return
        self.clicks = [t for t in self.clicks if now - t < 6] + [now]
        if len(self.clicks) >= 2 and now - self.clicks[-2] < 0.4:
            self.open_chat()
            return
        if len(self.clicks) >= 6:
            self.clicks = []
            self.mind.annoyed(now)
            self.react("annoyed")
            self.root.after(900, self.teleport)
            return
        self.mind.poke(now)
        self.sfx.play("blip")
        self.say_ai("poke", {}, self.mind.line("poke", now), 4)
        if self.mind.affection > 60 and self.rng.random() < 0.5:
            self.set_icon("heart", 1.6)
        if self.state in ("idle", "perch", "walk", "sleep", "lounge", "curious"):
            self.hop(6)

    # ---- features
    def doing(self):
        return {"sleep": "napping", "lounge": "lounging around", "dance": "dancing", "walk": "wandering around",
                "curious": "checking out the user's cursor", "perch": "perched on a window"}.get(
                    self.state, "hanging out on the user's desktop")

    def start_focus(self, mins=FOCUS_MIN):
        self.timer_mode, self.timer_end = "focus", time.time() + mins * 60
        self.say(f"Focus for {mins:g} min. I'll keep watch.", 5)

    def stop_timer(self):
        self.timer_end = self.timer_mode = None
        self.say("Timer stopped.", 3)

    def add_reminder(self, mins, text):
        self.reminders.append((time.time() + mins * 60, text))
        self.say(f"Got it. Pinging you in {mins:g} min.", 4)

    def meeting_tick(self, now):
        """In a call or meeting (meeting window in front, or another app has the mic open): stay quiet and put."""
        if not self.settings.get("meeting_quiet", True):
            if self.meeting.active:
                self.meeting.active = False
                self.meeting_ended()
            return
        title = self.win32.foreground_title() if self.aware else ""     # title: checked here, never kept
        ev = self.meeting.update(now, title, meeting.mic_users(meeting.read_mic_entries()))
        if ev == "start":
            log(f"meeting quiet on ({self.meeting.why})")
            if self.calm_before_meeting is None:
                self.calm_before_meeting, self.calm = self.calm, True
            self.speaker.stop()
            if self.state == "dance":
                self.go("idle", 4)
            self.say("In a call. I'll keep quiet.", 3, speak=None)
        elif ev == "end":
            self.meeting_ended()

    def meeting_ended(self):
        was, self.calm_before_meeting = self.calm_before_meeting, None
        if was is None:
            return
        log("meeting quiet off")
        if self.game and self.calm_before_game is not None:
            self.calm_before_game = was                              # the game still wants her quiet
        else:
            self.calm = was

    def toggle_calm(self):
        self.calm_before_meeting = None                              # you chose: don't undo it when the call ends
        self.calm = not self.calm
        self.settings["calm"] = self.calm
        self.save_settings()
        self.say("Calm mode on. I'll stay put." if self.calm else "Roaming again!", 3, speak=None)
        if self.calm:
            self.go("idle", 4)

    def toggle_checkins(self):
        self.checkins = not self.checkins
        self.settings["checkins"] = self.checkins
        self.save_settings()
        self.say("Check-ins on." if self.checkins else "Check-ins off.", 3, speak=None)

    def open_chat(self, hidden=False):
        """hidden=True makes the chat window without showing it (voice commands must not steal focus from a game)."""
        self.poke_awake()
        if self.chat and self.chat.alive():
            if not hidden:
                self.chat.win.deiconify()
                self.chat.win.lift()
                self.chat.entry.focus_set()
            return
        self.chat = ChatWindow(self)
        if hidden:
            self.chat.win.withdraw()
        if "chat_geom" not in self.settings or "+" not in self.settings.get("chat_geom", ""):
            w, h = 400, 600
            x = int(self.fx + self.fw) if self.fx < self.sw / 2 else int(self.fx - self.fw - w)
            y = max(20, min(self.sh - h - 60, int(self.fy - h)))
            self.chat.win.geometry(f"{w}x{h}+{max(0, x)}+{y}")

    def show_menu(self, e):
        self.poke_awake()
        m = tk.Menu(self.root, tearoff=0, bg=C_PANEL, fg=C_TEXT, activebackground=C_GREEN,
                    activeforeground=C_BLACK, bd=0, relief="flat", font=(self.font_family, 10))
        m.add_command(label="Chat with Capri", command=self.open_chat)
        m.add_command(label=f"Mood: {self.mind.mood(time.time())}", state="disabled")
        m.add_command(label="Settings...", command=self.open_settings)
        if self.timer_end:
            left = max(0, int(self.timer_end - time.time()))
            m.add_command(label=f"{self.timer_mode.title()}: {left // 60}:{left % 60:02d} left", state="disabled")
            m.add_command(label="Stop timer", command=self.stop_timer)
        else:
            m.add_command(label=f"Start focus timer ({FOCUS_MIN} min)", command=self.start_focus)
        m.add_command(label="Talk to Capri (voice)", command=self.start_listening)
        if self.wake is not None and self.wake.running:
            m.add_command(label="Stop listening for \"Hey Capri\"", command=self.disable_wake)
        else:
            m.add_command(label="Listen for \"Hey Capri\" / \"Choom\"", command=self.enable_wake)
        m.add_command(label="Remind me...", command=lambda: ReminderDialog(self))
        if self.agent is not None:
            m.add_command(label="STOP the task", command=self.stop_agent)
        m.add_separator()
        m.add_command(label="Teleport", command=self.teleport)
        m.add_command(label="Fly around", command=lambda: self.start_fly("fly"))
        m.add_command(label="Orbit my cursor", command=lambda: self.start_fly("orbit"))
        m.add_command(label="Party!", command=self.party)
        m.add_command(label="Play tag", command=self.start_tag)
        m.add_command(label="Hack (Breach Protocol)", command=self.open_breach)
        m.add_command(label="Sit on something (screen ledges)", command=self.sit_somewhere)
        m.add_command(label="Memory game (Simon)", command=self.open_simon)
        m.add_command(label="Feed ramen", command=self.feed)
        m.add_command(label="Dance", command=lambda: self.go("dance", 3.5))
        m.add_command(label="Lounge", command=lambda: self.go("lounge", 15))
        m.add_command(label="Take a nap", command=lambda: self.go("sleep"))
        if self.win32.ok:
            m.add_command(label="Perch on my window", command=lambda: self.teleport("perch"))
        m.add_separator()
        if self.speaker.available:
            vm = tk.Menu(m, tearoff=0, bg=C_PANEL, fg=C_TEXT, activebackground=C_GREEN, activeforeground=C_BLACK,
                         bd=0, relief="flat", font=(self.font_family, 10))
            cur = self.settings.get("voice", "chatty")
            vm.add_command(label="Engine: " + {"fish": "Capri's real voice (Fish Audio)",
                                                "system": "system voice (/fishkey for hers)"}.get(
                                                    self.speaker.engine, "none"), state="disabled")
            vm.add_separator()
            for key, label in (("off", "Off"), ("replies", "Replies & alerts only"), ("chatty", "Chatty")):
                vm.add_command(label=("* " if cur == key else "   ") + label, command=lambda k=key: self.set_voice(k))
            m.add_cascade(label="Voice", menu=vm)
        else:
            m.add_command(label="Voice: no speech engine found", state="disabled")
        m.add_command(label=f"Calm mode: {'on' if self.calm else 'off'}", command=self.toggle_calm)
        m.add_command(label=f"Check-ins: {'on' if self.checkins else 'off'}", command=self.toggle_checkins)
        if self.win32.ok:
            seen = f" (sees: {self.ctx})" if (self.aware and self.ctx) else ""
            m.add_command(label=f"Awareness: {'on' if self.aware else 'off'}{seen}",
                          command=lambda: self.set_aware(not self.aware))
        m.add_separator()
        m.add_command(label="Quit", command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def quit(self):
        self.speaker.stop()
        if self.reactor:
            self.reactor.stop()
        self.stop_spotter()
        self.mind.sync(time.time())
        self.save_settings()
        if self.chat and self.chat.alive():
            self.chat.close()
        self.root.destroy()

    # ---- drawing
    def place(self):
        wa = self.work_area()
        if self.state != "peek":                          # peeking is the one time she may hang off the edge
            self.fx = min(max(self.fx, wa[0] + 10), wa[2] - 10)
        x = int(self.fx - self.Wd / 2)
        y = int(self.fy - (self.Hd - 8))
        g = f"{self.Wd}x{self.Hd}+{x}+{y}"
        if g != getattr(self, "_geo", None):
            self.root.geometry(g)
            self._geo = g

    def sprite_image(self, now):
        if now < self.talk_until and self.state in ("idle", "perch"):
            anim = "talk"
        elif self.typing_along and self.state in ("idle", "perch"):
            anim = "type"
        else:
            anim = self.anim
        key, frame = self.art.frame(anim, now - self.t_start, self.dir)
        flip = self.art.flip_dir and self.dir < 0
        dim = self.state == "sleep"
        if self.glitch > 0.02:
            img, ax, ay = pose(frame, self.angle, self.sx, self.sy, flip, dim, self.glitch, self.rng)
            if self.outline_on():
                img = neon.outline(img, neon.COLORS[self.neon_name], self.neon_px())
            self._last_ck = None
            return ImageTk.PhotoImage(img), ax, ay, img.width, img.height
        ck = (key, round(self.angle / 3), round(self.sx * 25), round(self.sy * 25), flip, dim)
        self._last_ck = ck
        hit = self.pcache.get(ck)
        if hit is None:
            if len(self.pcache) > 500:
                self.clear_sprite_caches()
            img, ax, ay = pose(frame, self.angle, self.sx, self.sy, flip, dim)
            if self.outline_on():
                img = neon.outline(img, neon.COLORS[self.neon_name], self.neon_px())
            hit = (ImageTk.PhotoImage(img), ax, ay, img.width, img.height)
            self.pcache[ck] = hit
            self.pil_cache[ck] = img
        return hit

    # ---- launch animation
    def greet(self):
        now = time.time()
        self.say_ai("greeting", {"away": f"They were away about {self.mind.away_hours:.0f} hours." if self.mind.away_hours >= 3 else ""},
                    self.mind.greeting(now), 7)

    def start_boot(self, first=None, greet=True):
        if self.boot:
            return
        first = (not self.settings.get("booted")) if first is None else first
        D = boot.duration(first)
        self.boot = {"t0": time.time(), "dur": D, "first": first, "lines": boot.lines(first), "greet": greet}
        self.bubble = ""
        self.surf = None
        self.go("idle", D + 10)

    def update_boot(self, now):
        b = self.boot
        if not b:
            return
        t = now - b["t0"]
        pr = boot.progress(t, b["dur"])
        self.glitch = max(self.glitch, pr["flash"] * 0.6)
        if not b.get("s1") and t > 0.05:
            b["s1"] = True
            self.sfx.play("blip")
        if not b.get("s2") and pr["flash"] > 0.5:
            b["s2"] = True
            self.sfx.play("success")
            self.spawn_confetti(30)
        if pr["done"]:
            self.finish_boot()

    def finish_boot(self, skipped=False):
        b, self.boot = self.boot, None
        if not b:
            return
        self.glitch = 0.0
        self.settings["booted"] = True
        self.save_settings()
        self.go("idle", 2.0)
        if not skipped:
            self.react("happy")
        if b.get("greet", True):
            self.greet()

    def draw_boot_under(self, c, pr, lfx, lfy):
        col = self.accent()
        if pr["beam"] > 0.02:
            bw = 2 + 12 * pr["beam"] ** 0.5
            c.create_rectangle(lfx - bw, 0, lfx + bw, lfy, fill=col, outline="")
            c.create_rectangle(lfx - bw / 3, 0, lfx + bw / 3, lfy, fill="#ffffff", outline="")
        if 0.0 < pr["ring"] < 1.0:
            rx = 16 + 100 * pr["ring"]
            c.create_oval(lfx - rx, lfy - rx * 0.22, lfx + rx, lfy + rx * 0.22, outline=col,
                          width=max(1, int(4 * (1 - pr["ring"]))))
        if pr["flash"] > 0.02:
            rx = 30 + 150 * (1 - pr["flash"])
            c.create_oval(lfx - rx, lfy - rx * 0.3, lfx + rx, lfy + rx * 0.3, outline="#ffffff", width=3)
            for i in range(10):
                a = i * 0.628 + 0.3
                r0, r1 = 24 + 40 * (1 - pr["flash"]), 44 + 90 * (1 - pr["flash"])
                cy = lfy - self.fh * 0.5
                c.create_line(lfx + math.cos(a) * r0, cy + math.sin(a) * r0 * 0.8, lfx + math.cos(a) * r1,
                              cy + math.sin(a) * r1 * 0.8, fill=col if i % 2 else "#ffffff", width=2)

    def draw_boot_sprite(self, c, reveal, x0, y0, w, h):
        """Her sprite scanned in from the top down. Returns the y of the scan line (or None)."""
        pil = self.pil_cache.get(self._last_ck)
        vis = int(h * reveal) // 4 * 4
        if pil is None or vis < 4:
            return None
        key = ("boot", self._last_ck, vis, self.neon_name)
        ph = self.ghost_cache.get(key)
        if ph is None:
            if len(self.ghost_cache) > 400:
                self.ghost_cache.clear()
            ph = self.ghost_cache[key] = ImageTk.PhotoImage(pil.crop((0, 0, pil.width, min(pil.height, vis))))
        dx = self.rng.randint(-3, 3) if reveal < 0.85 else 0
        c.create_image(x0 + dx, y0, image=ph, anchor="nw")
        return y0 + vis

    def draw_boot_over(self, c, pr, bt, lfx, y0, w, scan_y):
        col = self.accent()
        if scan_y is not None and pr["reveal"] < 1.0:
            c.create_line(lfx - w / 2 - 14, scan_y, lfx + w / 2 + 14, scan_y, fill=col, width=3)
            c.create_line(lfx - w / 2 - 14, scan_y, lfx + w / 2 + 14, scan_y, fill="#ffffff", width=1)
        shown = boot.typed(self.boot["lines"], bt, self.boot["dur"])
        if shown:
            lh, n = 13, len(self.boot["lines"])
            pw = min(self.Wd - 16, 236)
            y2 = max(14 + lh * n, y0 - 10)
            y1 = y2 - (lh * n + 10)
            chamfer_rect(c, lfx - pw / 2, y1, lfx + pw / 2, y2, 7, fill=C_BLACK, outline=col, width=2)
            for i, line in enumerate(shown):
                last = i == len(shown) - 1 and line.endswith("_")
                ok = "ONLINE" in line
                c.create_text(lfx - pw / 2 + 8, y1 + 6 + i * lh, text=line, anchor="nw", font=(self.mono, 8, "bold"),
                              fill="#ffffff" if (last or ok) else col)

    def outline_on(self):
        """The glowing outline around her is OFF unless you switch it on (/neon outline on) and pick a colour."""
        return bool(self.settings.get("outline", False)) and self.neon_name != "off"

    def neon_px(self):
        return max(1, round(1.5 * self.dpi * self.size_now))

    def clear_sprite_caches(self):
        self.pcache.clear()
        self.pil_cache.clear()
        self.ghost_cache.clear()

    def set_neon(self, name):
        self.neon_name = name if name in neon.COLORS else "off"
        ui.THEME["acc"] = neon.hex_of(neon.COLORS[self.neon_name]) if self.neon_name != "off" else "#05f56f"
        self.settings["neon"] = self.neon_name
        self.save_settings()
        self.clear_sprite_caches()

    def accent(self):
        return neon.hex_of(neon.COLORS[self.neon_name]) if self.neon_name != "off" else C_GREEN

    def draw_ghosts(self, c, now, x0, y0):
        """Neon afterimages behind her while she flies fast."""
        if math.hypot(self.fvx, self.fvy) < 250:
            return
        pil = self.pil_cache.get(self._last_ck)
        if pil is None:
            return
        for level, lag in ((1, 0.06), (2, 0.13), (2, 0.21)):
            old = next((t for t in reversed(self.trail) if t[0] <= now - lag), None)
            if old is None:
                continue
            key = (self._last_ck, level, self.neon_name)
            gp = self.ghost_cache.get(key)
            if gp is None:
                gp = self.ghost_cache[key] = ImageTk.PhotoImage(neon.ghost(pil, neon.COLORS[self.neon_name], level))
            c.create_image(x0 + (old[1] - self.fx), y0 + (old[2] - self.fy), image=gp, anchor="nw")

    def draw(self, now):
        c = self.canvas
        c.delete("all")
        photo, ax, ay, w, h = self.sprite_image(now)
        self.cur_img = photo
        lfx, lfy = self.Wd / 2.0, self.Hd - 8 + self.hop_y
        wgt = max(0.0, min(1.0, (abs(self.angle) - 20) / 50.0))
        x0 = lfx - (ax * (1 - wgt) + (w / 2.0) * wgt)
        y0 = lfy - h
        self.trail.append((now, self.fx, self.fy))
        bt = pr = scan_y = None
        if self.boot:
            bt = now - self.boot["t0"]
            pr = boot.progress(bt, self.boot["dur"])
            self.draw_boot_under(c, pr, lfx, lfy)
        elif self.neon_name != "off" and self.state in ("fly", "orbit") and self._last_ck is not None:
            self.draw_ghosts(c, now, x0, y0)
        if pr is not None and pr["reveal"] < 1.0:
            scan_y = self.draw_boot_sprite(c, pr["reveal"], x0, y0, w, h)
        else:
            c.create_image(x0, y0, image=photo, anchor="nw")
        top = y0
        if self.typing_along:
            self.draw_keyboard(c, lfx, lfy)
        if self.spotter and self.spotter.active:
            self.draw_eye(c, lfx, y0)
        if self.state == "sleep":
            ph = int(now * 2) % 3
            c.create_text(lfx + self.fw * 0.1 + ph * 10, top - 2 - ph * 12, text="z",
                          font=(self.font_family, 10 + ph * 3, "bold"), fill=C_GREEN)
        if self.emote and now < self.emote[2]:
            img = self.art.emotes.get(self.emote[0])
            if img is not None:
                pop = min(1.0, (now - self.emote[1]) / 0.18)
                ei = pose(img, 0, 0.5 + 0.5 * pop, 0.5 + 0.5 * pop)[0]
                self._emote_photo = ImageTk.PhotoImage(ei)
                c.create_image(lfx + self.fw * 0.12, max(0, top - 2 - ei.height * 0.1 + math.sin(now * 8) * 2),
                               image=self._emote_photo, anchor="sw")
        if self.icon and now < self.icon[2]:
            self.draw_icon(c, now, lfx, top)
        if self.state in ("fly", "orbit"):
            sp = math.hypot(self.fvx, self.fvy)
            if sp > 120:
                ux, uy = -self.fvx / sp, -self.fvy / sp
                cx, cy = lfx, y0 + h * 0.5
                for i in range(5):
                    off = (i - 2) * 16
                    ox, oy = -uy * off, ux * off
                    ln = 14 + (i % 3) * 8 + min(30.0, sp / 40.0)
                    c.create_line(cx + ox + ux * 34, cy + oy + uy * 34, cx + ox + ux * (34 + ln), cy + oy + uy * (34 + ln),
                                  fill=C_GREEN if i % 2 else C_RED, width=2)
        for px_, py_, _vx, _vy, col, _life in self.parts:
            c.create_rectangle(px_, py_, px_ + 4, py_ + 4, fill=col, outline="")
        base_y = max(40, top - 6)
        if self.timer_end:
            left = max(0, int(self.timer_end - now))
            label = f"{self.timer_mode.upper()} {left // 60}:{left % 60:02d}"
            tid = c.create_text(lfx, base_y, text=label, font=(self.font_family, 9, "bold"), fill=C_GREEN, anchor="s")
            x1, y1, x2, y2 = c.bbox(tid)
            pill = chamfer_rect(c, x1 - 8, y1 - 3, x2 + 8, y2 + 3, 5, fill=C_BLACK, outline=C_RED, width=2)
            c.tag_lower(pill, tid)
            base_y = y1 - 10
        if pr is not None:
            self.draw_boot_over(c, pr, bt, lfx, y0, w, scan_y)
        if self.bubble and now < self.bubble_until and not self.boot:
            shown = int((now - self.bubble_t0) * 80)
            txt = self.bubble[:max(1, shown)]
            tid = c.create_text(lfx, base_y, text=txt, width=min(210, self.Wd - 50), font=(self.mono, 9),
                                fill=C_TEXT, anchor="s", justify="center")
            x1, y1, x2, y2 = c.bbox(tid)
            full = c.create_text(-999, -999, text=self.bubble, width=min(210, self.Wd - 50), font=(self.mono, 9))
            fx1, fy1, fx2, fy2 = c.bbox(full)
            c.delete(full)
            hx = (fx2 - fx1) / 2 - (x2 - x1) / 2
            bx1, bx2, by1 = lfx - (fx2 - fx1) / 2 - 10, lfx + (fx2 - fx1) / 2 + 10, y2 - (fy2 - fy1) - 6
            acc = self.accent()
            bg = chamfer_rect(c, bx1, by1, bx2, y2 + 6, 7, fill=C_PANEL, outline=acc, width=2)
            tail = c.create_polygon(lfx - 6, y2 + 6, lfx + 6, y2 + 6, lfx, y2 + 14, fill=C_PANEL, outline=acc, width=2)
            cover = c.create_line(lfx - 5, y2 + 6, lfx + 5, y2 + 6, fill=C_PANEL, width=3)
            c.tag_lower(cover)
            c.tag_lower(tail)
            c.tag_lower(bg)
            c.coords(tid, lfx, y2)


# ------------------------------------------------------------------ preview / main
def pet_preview():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title("Capri pet preview")
    art = load_art(1.0)
    if art.kind != "sheet":
        tk.Label(root, text="No Codex/Petdex sheet found.\nInstall one with:  npx petdex install capri",
                 padx=20, pady=20).pack()
        root.mainloop()
        return
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10)
    labels = []
    names = {v: k for k, v in art.map.items()}
    for i, row in enumerate(art.rows):
        if not row:
            continue
        cell = tk.Frame(frame)
        cell.grid(row=i // 5, column=i % 5, padx=6, pady=6)
        lbl = tk.Label(cell)
        lbl.pack()
        tk.Label(cell, text=f"row {i}: {names.get(i, '?')} ({len(row)} frames)", font=("Helvetica", 8)).pack()
        labels.append((lbl, [ImageTk.PhotoImage(f.resize((f.width // 2, f.height // 2), Image.NEAREST)) for f in row]))

    def step(n=0):
        for lbl, frames in labels:
            lbl.config(image=frames[n % len(frames)])
        root.after(120, lambda: step(n + 1))
    step()
    root.mainloop()


def main():
    if "--pet-preview" in sys.argv:
        return pet_preview()
    Capri().root.mainloop()


if __name__ == "__main__":
    main()
