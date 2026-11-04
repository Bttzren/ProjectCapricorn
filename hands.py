"""Capri's hands: pressing keys and clicking for you (no Tk).

Three levels, chosen by the user in Settings and enforced HERE (not just in the UI):
  visual : nothing is ever sent to the computer (she only mimes typing)
  media  : play/pause, next/prev, volume, mute, screenshot, lock screen
  full   : also press any key combo, type text, and click at the mouse position

Safety rails: actions come only from the user's own commands or from reflexes the user switched on
(never from the AI's replies); a few system-killing shortcuts are blocked; typed text is capped and
can't press Enter; at most 12 actions a minute. Only the action name is ever logged, never typed text.
"""
import shutil
import subprocess
import sys
import threading
import time
from collections import deque

LEVELS = ("visual", "media", "full")
LEVEL_NAMES = {"visual": "Visual only", "media": "Media keys", "full": "Full control"}

ACTION_LEVEL = {"playpause": "media", "next": "media", "prev": "media", "volup": "media", "voldown": "media",
                "mute": "media", "screenshot": "media", "lock": "media",
                "press": "full", "type": "full", "click": "full"}
ACTION_LABEL = {"playpause": "Play/pause", "next": "Next track", "prev": "Previous track", "volup": "Volume up",
                "voldown": "Volume down", "mute": "Mute", "screenshot": "Screenshot", "lock": "Locking the screen",
                "press": "Pressing keys", "type": "Typing", "click": "Clicking"}

MODIFIERS = ("ctrl", "shift", "alt", "win")
VK = {"ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B, "enter": 0x0D, "esc": 0x1B, "tab": 0x09,
      "space": 0x20, "backspace": 0x08, "delete": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23,
      "pageup": 0x21, "pagedown": 0x22, "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
      "printscreen": 0x2C}
VK.update({f"f{i}": 0x6F + i for i in range(1, 13)})
MEDIA_VK = {"playpause": 0xB3, "next": 0xB0, "prev": 0xB1, "volup": 0xAF, "voldown": 0xAE, "mute": 0xAD}
EXTENDED = {"win", "insert", "delete", "home", "end", "pageup", "pagedown", "left", "up", "right", "down",
            "printscreen"}
NAMED_KEYS = set(VK) - set(MODIFIERS)
BLOCKED = {"alt+f4", "ctrl+alt+delete", "ctrl+alt+del", "ctrl+shift+esc", "win+r", "win+x"}
ALIASES = {"control": "ctrl", "ctl": "ctrl", "windows": "win", "cmd": "win", "super": "win", "meta": "win",
           "return": "enter", "escape": "esc", "del": "delete", "ins": "insert", "pgup": "pageup",
           "pgdn": "pagedown", "pgdown": "pagedown", "prtsc": "printscreen", "prtscn": "printscreen",
           "spacebar": "space", "bksp": "backspace"}
MAX_TYPE = 200
MAX_PER_MIN = 12


def normalize_combo(text):
    """'Ctrl+Shift+T' -> ['ctrl', 'shift', 't']. Raises ValueError with a friendly reason."""
    parts = [ALIASES.get(p.strip().lower(), p.strip().lower()) for p in text.strip().split("+")]
    if not text.strip() or any(not p for p in parts):
        raise ValueError("I need keys like ctrl+s or f5")
    *mods, key = parts
    for m in mods:
        if m not in MODIFIERS:
            raise ValueError(f"'{m}' isn't a modifier key (ctrl, shift, alt, win)")
    if len(set(mods)) != len(mods):
        raise ValueError("a modifier is repeated")
    if not (len(key) == 1 or key in NAMED_KEYS):
        raise ValueError(f"I don't know the key '{key}'")
    mods.sort(key=MODIFIERS.index)
    if "+".join(mods + [key]) in BLOCKED:
        raise ValueError("that shortcut is blocked for safety")
    return mods + [key]


def clean_text(text):
    """What she is allowed to type: no Enter/Tab/control characters, capped length."""
    t = "".join(" " if ch in "\r\n\t" else ch for ch in text)
    t = "".join(ch for ch in t if ch.isprintable())
    return t.strip()[:MAX_TYPE]


# ------------------------------------------------------------------ backends
class WinBackend:
    def __init__(self, user32=None, sleep=time.sleep):
        if user32 is None:
            import ctypes
            user32 = ctypes.windll.user32
        self.u, self.sleep = user32, sleep

    def _event(self, vk, up=False, ext=False):
        self.u.keybd_event(vk, 0, (1 if ext else 0) | (2 if up else 0), 0)

    def _vk(self, key):
        if len(key) == 1:
            r = self.u.VkKeyScanW(ord(key))
            if r == -1:
                raise ValueError(f"can't type '{key}' on this keyboard")
            return r & 0xFF, bool(r & 0x100)
        return VK[key], False

    def _tap(self, key):
        vk, shift = self._vk(key)
        if shift:
            self._event(VK["shift"])
        self._event(vk, ext=key in EXTENDED)
        self._event(vk, up=True, ext=key in EXTENDED)
        if shift:
            self._event(VK["shift"], up=True)

    def press(self, combo):
        *mods, key = combo
        for m in mods:
            self._event(VK[m], ext=m in EXTENDED)
        try:
            self._tap(key)
        finally:
            for m in reversed(mods):
                self._event(VK[m], up=True, ext=m in EXTENDED)

    def type_text(self, text):
        for ch in text:
            try:
                self._tap(ch if ch != " " else "space")
            except ValueError:
                continue
            self.sleep(0.015)

    def click(self, button="left", double=False):
        down, up = (0x8, 0x10) if button == "right" else (0x2, 0x4)
        for _ in range(2 if double else 1):
            self.u.mouse_event(down, 0, 0, 0, 0)
            self.u.mouse_event(up, 0, 0, 0, 0)

    def media(self, name):
        vk = MEDIA_VK[name]
        self._event(vk)
        self._event(vk, up=True)

    def screenshot(self):
        self.press(["win", "printscreen"])

    def lock(self):
        self.u.LockWorkStation()


class CmdBackend:
    """macOS / Linux: shells out to tools that are already there (osascript, xdotool, playerctl, pactl)."""

    def __init__(self, platform, which=shutil.which, run=subprocess.run):
        self.platform, self.which, self.run = platform, which, run

    def _need(self, exe):
        path = self.which(exe)
        if not path:
            raise NotImplementedError(f"needs '{exe}' installed")
        return path

    def _go(self, argv):
        self.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)

    @property
    def mac(self):
        return self.platform == "darwin"

    def media(self, name):
        if self.mac:
            osa = self._need("osascript")
            script = {"volup": "set volume output volume ((output volume of (get volume settings)) + 10)",
                      "voldown": "set volume output volume ((output volume of (get volume settings)) - 10)",
                      "mute": "set volume output muted not (output muted of (get volume settings))"}.get(name)
            if not script:
                raise NotImplementedError("play/pause and track keys aren't supported on Mac yet")
            return self._go([osa, "-e", script])
        if name in ("playpause", "next", "prev"):
            return self._go([self._need("playerctl"), {"playpause": "play-pause", "next": "next",
                                                      "prev": "previous"}[name]])
        pactl = self._need("pactl")
        args = {"volup": ["set-sink-volume", "@DEFAULT_SINK@", "+5%"],
                "voldown": ["set-sink-volume", "@DEFAULT_SINK@", "-5%"],
                "mute": ["set-sink-mute", "@DEFAULT_SINK@", "toggle"]}[name]
        self._go([pactl] + args)

    def screenshot(self):
        if self.mac:
            return self._go([self._need("screencapture"), "-c"])
        raise NotImplementedError("screenshots aren't supported on this system yet")

    def lock(self):
        if self.mac:
            return self._go([self._need("pmset"), "displaysleepnow"])
        self._go([self._need("loginctl"), "lock-session"])

    def press(self, combo):
        if self.mac:
            osa = self._need("osascript")
            *mods, key = combo
            codes = {"enter": 36, "tab": 48, "space": 49, "esc": 53, "backspace": 51, "left": 123, "right": 124,
                     "down": 125, "up": 126}
            using = ", ".join({"ctrl": "control down", "shift": "shift down", "alt": "option down",
                               "win": "command down"}[m] for m in mods)
            tail = f" using {{{using}}}" if using else ""
            if key in codes:
                body = f"key code {codes[key]}{tail}"
                return self._go([osa, "-e", f'tell application "System Events" to {body}'])
            if len(key) != 1:
                raise NotImplementedError(f"'{key}' isn't supported on Mac yet")
            script = ["-e", "on run argv", "-e",
                      f'tell application "System Events" to keystroke (item 1 of argv){tail}', "-e", "end run"]
            return self._go([osa] + script + [key])
        xdo = self._need("xdotool")
        names = {"ctrl": "ctrl", "shift": "shift", "alt": "alt", "win": "super", "enter": "Return", "esc": "Escape",
                 "backspace": "BackSpace", "delete": "Delete", "pageup": "Prior", "pagedown": "Next",
                 "printscreen": "Print", "left": "Left", "right": "Right", "up": "Up", "down": "Down",
                 "tab": "Tab", "space": "space", "home": "Home", "end": "End", "insert": "Insert"}
        self._go([xdo, "key", "--", "+".join(names.get(k, k) for k in combo)])

    def type_text(self, text):
        if self.mac:
            osa = self._need("osascript")
            return self._go([osa, "-e", "on run argv", "-e",
                             'tell application "System Events" to keystroke (item 1 of argv)', "-e", "end run", text])
        self._go([self._need("xdotool"), "type", "--delay", "40", "--", text])

    def click(self, button="left", double=False):
        if self.mac:
            cl = self._need("cliclick")
            return self._go([cl, ("rc:." if button == "right" else ("dc:." if double else "c:."))])
        xdo = self._need("xdotool")
        self._go([xdo, "click"] + (["--repeat", "2"] if double else []) + ["3" if button == "right" else "1"])


def make_backend(platform=None, which=shutil.which):
    platform = platform or sys.platform
    if platform.startswith("win"):
        return WinBackend()
    return CmdBackend(platform, which)


# ------------------------------------------------------------------ the hands
class Hands:
    def __init__(self, level="visual", backend=None, clock=time.time, threaded=True, log=None, platform=None):
        self.level = level if level in LEVELS else "visual"
        self._backend, self._platform = backend, platform
        self.clock, self.threaded, self.log = clock, threaded, log or (lambda m: None)
        self.recent = deque()

    @property
    def backend(self):
        if self._backend is None:
            self._backend = make_backend(self._platform)
        return self._backend

    def set_level(self, level):
        self.level = level if level in LEVELS else "visual"

    def allowed(self, action):
        need = ACTION_LEVEL.get(action)
        return need is not None and LEVELS.index(self.level) >= LEVELS.index(need)

    def do(self, action, arg=None):
        """Perform `action`. Returns (ok, message_for_the_bubble). Never raises."""
        if action not in ACTION_LEVEL:
            return False, "I don't know how to do that."
        if not self.allowed(action):
            return False, f"That needs '{LEVEL_NAMES[ACTION_LEVEL[action]]}' switched on in my Settings."
        now = self.clock()
        while self.recent and now - self.recent[0] > 60:
            self.recent.popleft()
        if len(self.recent) >= MAX_PER_MIN:
            return False, "Whoa, that's a lot of button pressing. Give me a minute."
        try:
            run, msg = self._prepare(action, arg)
        except ValueError as exc:
            return False, str(exc).capitalize() + "."
        self.recent.append(now)
        self.log("hands: " + action)                       # the action name only, never typed text
        try:
            if action == "type" and self.threaded:
                threading.Thread(target=self._safe, args=(run,), daemon=True).start()
            else:
                run()
        except NotImplementedError as exc:
            return False, f"Can't do that here: {exc}."
        except Exception as exc:                                  # a failed key press must never crash her
            self.log(f"hands failed: {action}: {type(exc).__name__}")
            return False, "My hands slipped. Check the log."
        return True, msg

    def check(self, action, arg=None):
        """Would `do(action, arg)` be accepted right now? Nothing is pressed. Returns (ok, message)."""
        if action not in ACTION_LEVEL:
            return False, "I don't know how to do that."
        if not self.allowed(action):
            return False, f"That needs '{LEVEL_NAMES[ACTION_LEVEL[action]]}' switched on in my Settings."
        try:
            self._prepare(action, arg)
        except ValueError as exc:
            return False, str(exc).capitalize() + "."
        return True, ""

    def _safe(self, run):
        try:
            run()
        except Exception as exc:
            self.log(f"hands failed: {type(exc).__name__}")

    def _prepare(self, action, arg):
        b = self.backend
        if action == "press":
            combo = normalize_combo(arg or "")
            return (lambda: b.press(combo)), "Pressed " + "+".join(combo) + "."
        if action == "type":
            text = clean_text(arg or "")
            if not text:
                raise ValueError("there's nothing to type")
            return (lambda: b.type_text(text)), f"Typing {len(text)} characters..."
        if action == "click":
            kind = (arg or "left").lower()
            if kind not in ("left", "right", "double"):
                raise ValueError("click can be left, right or double")
            return ((lambda: b.click("right" if kind == "right" else "left", kind == "double")),
                    f"Clicked ({kind}).")
        if action in MEDIA_VK:
            return (lambda: b.media(action)), ACTION_LABEL[action] + "."
        if action == "screenshot":
            return b.screenshot, "Screenshot taken."
        return b.lock, "Locking the screen."
