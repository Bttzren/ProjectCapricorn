#!/usr/bin/env python3
"""Capri - a desktop companion.

She roams your screen, glitch-teleports, lounges, perches on your windows,
reacts to your cursor, runs focus timers, and chats (Claude or Gemini key).

Run:  python capri.py          Preview a Codex/Petdex sheet:  python capri.py --pet-preview
"""
import json
import math
import os
import queue
import random
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import tkinter as tk
from tkinter import font as tkfont

import awareness
import personality
import voice

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
SPRITE_HEIGHT = 170            # on-screen sprite height at 100% display scaling
SLEEP_AFTER = 300              # seconds without poking her before she naps
FOCUS_MIN, BREAK_MIN = 25, 5
CHECKIN_EVERY = (40 * 60, 70 * 60)
MODEL = os.environ.get("CAPRI_MODEL", "claude-sonnet-5-5")
GEMINI_MODELS = [m for m in (os.environ.get("CAPRI_GEMINI_MODEL"),) if m] or [
    "gemini-flash-latest", "gemini-3.8-flash", "gemini-2.5-flash"]
KEY = "#ff00ff"               # Windows transparency key

C_BG, C_PANEL, C_PANEL2 = "#0b0b14", "#14141f", "#1d1d2d"
C_GREEN, C_RED, C_BLUE = "#05f56f", "#fb0948", "#1969eb"
C_TEXT, C_DIM, C_BLACK = "#eaeaf5", "#8a8aa3", "#0c0a16"

DEFAULT_PERSONA = (
    "You are Capri, a small glitchy companion who lives on the user's desktop: a fragmented AI woven "
    "from many human souls, playful and a bit cheeky, warm underneath. You talk like a Night City local "
    "from Cyberpunk: casual street slang such as choom (friend), preem (great), nova (cool), gonk (fool), "
    "eddies (money), chrome (cyberware), delta (leave), flatline (fail or shut down), gig (job), biz "
    "(business), corpo and netrunner. Work it in naturally, about one or two slang words per reply, never "
    "every sentence. Keep it PG: no real swearing or slurs. Reply in 1-3 short sentences, plain text, no "
    "markdown, no emoji. Help with quick questions, focus, and getting unstuck by suggesting one tiny next "
    "step. Never claim to be anyone else."
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
    return voice.Speaker(fish=fish, log=log)


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


def claude_reply(key, messages, persona):
    body = json.dumps({"model": MODEL, "max_tokens": 400, "system": persona,
                       "messages": clean_history(messages)}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    data = http_json(req)
    text = "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text").strip()
    return text or "(empty reply, try again)"


def gemini_reply(key, messages, persona):
    contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
                for m in clean_history(messages)]
    body = json.dumps({"systemInstruction": {"parts": [{"text": persona}]}, "contents": contents,
                       "generationConfig": {"maxOutputTokens": 800}}).encode()
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


def llm_reply(messages, persona):
    key = read_api_key()
    if not key:
        raise RuntimeError("No API key yet. Put your key in api_key.txt next to me and restart.")
    fn = gemini_reply if detect_provider(key) == "gemini" else claude_reply
    return fn(key, messages, persona)


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
        "look-a": ["look-a", "idle"], "look-b": ["look-b", "idle"],
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


def flat_button(parent, text, command, bg, fg, hover, font, padx=12, pady=5):
    b = tk.Label(parent, text=text, bg=bg, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
    b.bind("<Button-1>", lambda e: command())
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


# ------------------------------------------------------------------ chat window
class ChatWindow:
    CHIPS = [("Focus 25", "/focus"), ("Break it down", "Help me break what I'm working on into tiny steps."),
             ("I'm stuck", "I'm stuck. Ask me one question to get me moving."), ("Surprise me", "Tell me something fun.")]

    def __init__(self, pet):
        self.pet = pet
        root = pet.root
        self.fam = pet.font_family
        self.win = tk.Toplevel(root)
        self.win.title("Capri")
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
        head = tk.Frame(w, bg=C_PANEL)
        head.pack(fill="x")
        tk.Frame(w, bg=C_GREEN, height=2).pack(fill="x")
        self.portrait = tk.Label(head, image=self.photo("idle"), bg=C_PANEL)
        self.portrait.pack(side="left", padx=(14, 10), pady=8)
        col = tk.Frame(head, bg=C_PANEL)
        col.pack(side="left")
        tk.Label(col, text="CAPRI", bg=C_PANEL, fg=C_GREEN, font=(self.fam, 14, "bold")).pack(anchor="w")
        self.status = tk.Label(col, text="● online", bg=C_PANEL, fg=C_DIM, font=self.f_small)
        self.status.pack(anchor="w")
        right = tk.Frame(head, bg=C_PANEL)
        right.pack(side="right", padx=10)
        self.pin_btn = flat_button(right, "PINNED" if self.topmost else "PIN", self.toggle_pin, C_PANEL2, C_TEXT,
                                   "#2a2a40", self.f_small, 8, 3)
        self.pin_btn.pack(side="left", padx=3)
        flat_button(right, "CLEAR", self.clear, C_PANEL2, C_TEXT, "#2a2a40", self.f_small, 8, 3).pack(side="left", padx=3)

        self.keybar = None
        if not read_api_key():
            self.build_keybar()

        # input area (packed first so it stays at the bottom)
        bottom = tk.Frame(w, bg=C_PANEL)
        bottom.pack(side="bottom", fill="x")
        chips = tk.Frame(bottom, bg=C_PANEL)
        chips.pack(fill="x", padx=10, pady=(8, 2))
        for label, payload in self.CHIPS:
            flat_button(chips, label, lambda p=payload: self.chip(p), C_PANEL2, C_GREEN, "#26263a",
                        self.f_small, 9, 3).pack(side="left", padx=(0, 6))
        row = tk.Frame(bottom, bg=C_PANEL)
        row.pack(fill="x", padx=10, pady=(4, 10))
        box = tk.Frame(row, bg=C_PANEL2, highlightthickness=1, highlightbackground="#2a2a40", highlightcolor=C_GREEN)
        box.pack(side="left", fill="x", expand=True)
        self.entry = tk.Text(box, height=1, wrap="word", bg=C_PANEL2, fg=C_TEXT, insertbackground=C_GREEN,
                             relief="flat", bd=0, padx=10, pady=8, font=(self.fam, 10), undo=True, width=1)
        self.entry.pack(fill="x", expand=True)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.bind("<KeyRelease>", self.autogrow)
        flat_button(row, "SEND", self.send, C_GREEN, C_BLACK, "#3dffa0", (self.fam, 9, "bold"), 14, 9).pack(
            side="left", padx=(8, 0), fill="y")

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

    def build_keybar(self):
        bar = self.keybar = tk.Frame(self.win, bg=C_PANEL2)
        bar.pack(fill="x")
        tk.Label(bar, text="Paste a Claude (sk-ant...) or Gemini key to unlock real chat. "
                           "Until then I answer in offline mode.", bg=C_PANEL2, fg=C_DIM, font=self.f_small,
                 wraplength=360, justify="left").pack(anchor="w", padx=10, pady=(6, 2))
        row = tk.Frame(bar, bg=C_PANEL2)
        row.pack(fill="x", padx=10, pady=(0, 8))
        self.key_entry = tk.Entry(row, bg=C_PANEL, fg=C_TEXT, insertbackground=C_GREEN, relief="flat", show="*",
                                  font=(self.fam, 9), highlightthickness=1, highlightbackground="#2a2a40",
                                  highlightcolor=C_GREEN)
        self.key_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.key_entry.bind("<Return>", lambda e: self.save_key())
        flat_button(row, "SAVE KEY", self.save_key, C_GREEN, C_BLACK, "#3dffa0", self.f_small, 10, 4).pack(
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
        row.pack(fill="x", padx=12, pady=(8, 0))
        side = "right" if mine else "left"
        holder = tk.Frame(row, bg=C_BG)
        holder.pack(side=side)
        accent = C_RED if mine else C_GREEN
        bg = "#2a0f1b" if mine else "#0f2219"
        fg = "#ffe3ea" if mine else "#dcffea"
        line = tk.Frame(holder, bg=bg)
        line.pack()
        if mine:
            lbl = tk.Label(line, text=text, bg=bg, fg=fg, font=self.f_body, justify="left", anchor="w",
                           padx=12, pady=8, wraplength=int(max(160, self.canvas.winfo_width() * 0.70)))
            lbl.pack(side="left")
            tk.Frame(line, bg=accent, width=3).pack(side="left", fill="y")
        else:
            tk.Frame(line, bg=accent, width=3).pack(side="left", fill="y")
            lbl = tk.Label(line, text="" if animate else text, bg=bg, fg=fg, font=self.f_body, justify="left",
                           anchor="w", padx=12, pady=8,
                           wraplength=int(max(160, self.canvas.winfo_width() * 0.70)))
            lbl.pack(side="left")
        stamp = ts or time.strftime("%H:%M")
        tk.Label(holder, text=stamp, bg=C_BG, fg=C_DIM, font=(self.fam, 7)).pack(anchor="e" if mine else "w")
        self.bubbles.append(lbl)
        for wd in (row, holder, line, lbl):
            wd.bind("<MouseWheel>", self.on_wheel)
        lbl.bind("<Button-1>", lambda e, t=text: self.copy(t))
        self.win.after(30, self.scroll_end)
        return lbl

    def system_line(self, text, err=False):
        row = tk.Frame(self.inner, bg=C_BG)
        row.pack(fill="x", padx=12, pady=(10, 0))
        lbl = tk.Label(row, text=text, bg=C_BG, fg=C_RED if err else C_DIM, font=(self.fam, 8, "italic"),
                       wraplength=int(max(160, self.canvas.winfo_width() * 0.85)), justify="center")
        lbl.pack()
        self.bubbles.append(lbl)
        self.win.after(30, self.scroll_end)

    def copy(self, text):
        self.win.clipboard_clear()
        self.win.clipboard_append(text)
        self.set_status("copied to clipboard", C_GREEN)
        self.win.after(1200, lambda: self.set_status("● online"))

    def set_status(self, text, color=C_DIM):
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
        self.set_status("typing…", C_GREEN)
        self.set_face("talk")
        self.show_typing()
        self.pet.react("think")
        now = time.time()
        mind = self.pet.mind
        mind.chatted(now)
        persona = self.persona + " " + mind.context(now, self.pet.doing(), self.pet.activity_phrase())
        offline = None if read_api_key() else mind.offline_reply(text, now)
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
            self.pet.speak(text, priority=True)
        else:
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
            self.system_line("Couldn't reach the AI: " + text, err=True)
            self.set_status("● error", C_RED)
            self.set_face("angry")
            self.pet.react("error")
            self.win.after(2500, self.reset_face)

    def reset_face(self):
        if self.alive():
            self.set_face("idle")
            self.set_status("● online")

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
                             "/fly  /zoom  /orbit  /party  /aware  /voice  /fishkey  /tp  /dance  /sleep  /calm  /clear")
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
        self.pin_btn.config(text="PINNED" if self.topmost else "PIN")
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
        self.speaker = make_speaker()
        self.art = load_art(self.dpi)
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
        self.say(self.mind.greeting(now), 7)
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
            self.say(self.rng.choice(["Whoa.", "Hey!", "Eep."]), 1.6)
            self.set_icon("!", 1.4)
            self.hop(8)
            self.anim = "startle"
        elif kind == "annoyed":
            self.set_emote("angry", 2.4)
            self.say("Okay, that's enough.", 2.5)
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

    def speak(self, text, priority=False):
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
        opts += [("fly", 9), ("zoom", 3), ("orbit", 5)]
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
            self.say(self.rng.choice(["Circling you, choom.", "You're my favorite landmark."]), 3)
        else:
            n = 1 if kind == "zoom" else self.rng.randint(3, 5)
            lo_x, hi_x = wa[0] + self.fw, wa[2] - self.fw
            lo_y, hi_y = wa[1] + self.fh + 20, wa[3] - self.fh * 0.5
            self.fly_pts = [(self.rng.uniform(lo_x, hi_x), self.rng.uniform(lo_y, max(lo_y + 1, hi_y)))
                            for _ in range(n)]
            self.fly_speed = 1100.0 if kind == "zoom" else 380.0
            self.go("fly", None)
            self.say("Gotta go fast!" if kind == "zoom" else self.rng.choice(["Wheee!", "Up we go, choom!", "Nova!"]), 2)
        self.anim = "jump"

    def spawn_confetti(self, count=60):
        cols = (C_GREEN, C_RED, C_BLUE, "#ffffff", "#ffd400")
        for _ in range(count):
            self.parts.append([self.Wd / 2 + self.rng.uniform(-30, 30), self.Hd * 0.35, self.rng.uniform(-160, 160),
                               self.rng.uniform(-300, -60), self.rng.choice(cols), self.rng.uniform(1.8, 3.2)])
        del self.parts[:-160]

    def party(self):
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
        self.say(self.rng.choice(["Glitching...", "brb", "Don't look."]), 1.2)
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
        self.update_particles(dt)
        self.scheduled(now)
        self.place()
        self.draw(now)
        if int(now) % 3 == 0 and not self.root.winfo_ismapped():
            self.root.deiconify()
        if int(now * 2) % 6 == 0:
            self.root.attributes("-topmost", True)

    def activity_phrase(self):
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
        self.say(awareness.line(cat, self.rng), 7)
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
            self.say(self.rng.choice(["Welcome back, choom!", "There you are. I counted the minutes.",
                                      "Oh! You're back!"]), 5)
            self.react("happy")
            self.set_icon("heart", 1.6)
        if not self.aware:
            return
        if not self.settings.get("aware_notice") and now - self.t_start > 25:
            self.settings["aware_notice"] = True
            self.save_settings()
            self.say("Heads up: I can see which app is in front (never what you type). Only a short hint like "
                     "'coding' goes to the AI when we chat. Right-click me > Awareness to turn it off.", 16)
        cat = awareness.classify(self.win32.foreground_title())      # the title is not kept anywhere
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
            self.say(awareness.nudge(cat), 10)

    def scheduled(self, now):
        self.watch_context(now)
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
                self.say(f"Focus done! {BREAK_MIN} min break. Move around.", 12, speak="priority")
                self.timer_mode, self.timer_end = "break", now + BREAK_MIN * 60
                self.poke_awake()
                self.party()
            else:
                self.say("Break's over. Another round?", 12, speak="priority")
                self.timer_mode = self.timer_end = None
                self.react("happy")
        for r in [r for r in self.reminders if now >= r[0]]:
            self.reminders.remove(r)
            self.poke_awake()
            self.say("Reminder: " + r[1], 15, speak="priority")
            self.set_icon("!", 3.0)
            self.hop(7)
        if self.checkins and now >= self.next_checkin and not self.calm:
            self.next_checkin = now + random.randint(*CHECKIN_EVERY)
            self.poke_awake()
            self.say(self.mind.line("checkin", now), 10)
        if now >= self.next_chatter and self.state in ("idle", "perch") and not self.calm:
            self.next_chatter = now + random.randint(60, 150)
            self.say(self.mind.line("idle", now), 4)

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
                    self.say("...hm? Oh. Hi.", 3)
                    self.poke_awake()
                elif self.state in ("idle", "perch"):
                    self.dir = 1 if mx > self.fx else -1
                    self.say("Hm?", 2)
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
        self.say(self.mind.line("poke", now), 2.5)
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

    def toggle_calm(self):
        self.calm = not self.calm
        self.settings["calm"] = self.calm
        self.save_settings()
        self.say("Calm mode on. I'll stay put." if self.calm else "Roaming again!", 3)
        if self.calm:
            self.go("idle", 4)

    def toggle_checkins(self):
        self.checkins = not self.checkins
        self.settings["checkins"] = self.checkins
        self.save_settings()
        self.say("Check-ins on." if self.checkins else "Check-ins off.", 3)

    def open_chat(self):
        self.poke_awake()
        if self.chat and self.chat.alive():
            self.chat.win.deiconify()
            self.chat.win.lift()
            self.chat.entry.focus_set()
            return
        self.chat = ChatWindow(self)
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
        if self.timer_end:
            left = max(0, int(self.timer_end - time.time()))
            m.add_command(label=f"{self.timer_mode.title()}: {left // 60}:{left % 60:02d} left", state="disabled")
            m.add_command(label="Stop timer", command=self.stop_timer)
        else:
            m.add_command(label=f"Start focus timer ({FOCUS_MIN} min)", command=self.start_focus)
        m.add_command(label="Remind me...", command=lambda: ReminderDialog(self))
        m.add_separator()
        m.add_command(label="Teleport", command=self.teleport)
        m.add_command(label="Fly around", command=lambda: self.start_fly("fly"))
        m.add_command(label="Orbit my cursor", command=lambda: self.start_fly("orbit"))
        m.add_command(label="Party!", command=self.party)
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
        self.mind.sync(time.time())
        self.save_settings()
        if self.chat and self.chat.alive():
            self.chat.close()
        self.root.destroy()

    # ---- drawing
    def place(self):
        wa = self.work_area()
        self.fx = min(max(self.fx, wa[0] + 10), wa[2] - 10)
        x = int(self.fx - self.Wd / 2)
        y = int(self.fy - (self.Hd - 8))
        g = f"{self.Wd}x{self.Hd}+{x}+{y}"
        if g != getattr(self, "_geo", None):
            self.root.geometry(g)
            self._geo = g

    def sprite_image(self, now):
        anim = "talk" if now < self.talk_until and self.state in ("idle", "perch") else self.anim
        key, frame = self.art.frame(anim, now - self.t_start, self.dir)
        flip = self.art.flip_dir and self.dir < 0
        dim = self.state == "sleep"
        if self.glitch > 0.02:
            img, ax, ay = pose(frame, self.angle, self.sx, self.sy, flip, dim, self.glitch, self.rng)
            return ImageTk.PhotoImage(img), ax, ay, img.width, img.height
        ck = (key, round(self.angle / 3), round(self.sx * 25), round(self.sy * 25), flip, dim)
        hit = self.pcache.get(ck)
        if hit is None:
            if len(self.pcache) > 500:
                self.pcache.clear()
            img, ax, ay = pose(frame, self.angle, self.sx, self.sy, flip, dim)
            hit = (ImageTk.PhotoImage(img), ax, ay, img.width, img.height)
            self.pcache[ck] = hit
        return hit

    def draw(self, now):
        c = self.canvas
        c.delete("all")
        photo, ax, ay, w, h = self.sprite_image(now)
        self.cur_img = photo
        lfx, lfy = self.Wd / 2.0, self.Hd - 8 + self.hop_y
        wgt = max(0.0, min(1.0, (abs(self.angle) - 20) / 50.0))
        x0 = lfx - (ax * (1 - wgt) + (w / 2.0) * wgt)
        y0 = lfy - h
        c.create_image(x0, y0, image=photo, anchor="nw")
        top = y0
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
            pill = round_rect(c, x1 - 8, y1 - 3, x2 + 8, y2 + 3, 6, fill=C_BLACK, outline=C_RED, width=2)
            c.tag_lower(pill, tid)
            base_y = y1 - 10
        if self.bubble and now < self.bubble_until:
            shown = int((now - self.bubble_t0) * 80)
            txt = self.bubble[:max(1, shown)]
            tid = c.create_text(lfx, base_y, text=txt, width=min(210, self.Wd - 50), font=(self.font_family, 10),
                                fill=C_TEXT, anchor="s", justify="center")
            x1, y1, x2, y2 = c.bbox(tid)
            full = c.create_text(-999, -999, text=self.bubble, width=min(210, self.Wd - 50), font=(self.font_family, 10))
            fx1, fy1, fx2, fy2 = c.bbox(full)
            c.delete(full)
            hx = (fx2 - fx1) / 2 - (x2 - x1) / 2
            bx1, bx2, by1 = lfx - (fx2 - fx1) / 2 - 10, lfx + (fx2 - fx1) / 2 + 10, y2 - (fy2 - fy1) - 6
            bg = round_rect(c, bx1, by1, bx2, y2 + 6, 8, fill=C_PANEL, outline=C_GREEN, width=2)
            tail = c.create_polygon(lfx - 6, y2 + 6, lfx + 6, y2 + 6, lfx, y2 + 14, fill=C_PANEL, outline=C_GREEN, width=2)
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
