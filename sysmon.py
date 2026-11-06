"""Her senses for the PC itself (no Tk): how hard it's working, and USB sticks coming and going.

Reads only a CPU load percentage and the names of removable drives / USB devices. Nothing is stored or sent;
the AI is told generically ("a USB drive was plugged in"), never the device's name.
"""
import os
import sys
import threading
import time

CPU_HIGH = 90.0           # percent
CPU_HIGH_FOR = 20.0       # seconds above it before she says something
CPU_CALM = 45.0
CPU_CALM_FOR = 20.0
CPU_COOLDOWN = 15 * 60    # she complains about the CPU at most this often
USB_COOLDOWN = 4.0

LINES = {
    "cpu_high": ["Your CPU's screaming, choom. What are you running?!", "Fans are about to take off. Is that you?",
                 "Whoa, the whole machine's sweating. Something's hogging everything."],
    "cpu_calm": ["Phew. CPU's chilling again.", "Okay, it stopped screaming. Preem."],
    "usb_in": ["Ooh, something plugged in! What is it?", "New hardware! Is it chrome? Tell me it's chrome.",
               "Something just jacked in, choom."],
    "usb_out": ["Pulled the plug, huh. Hope you ejected it properly.", "Whatever that was, it's gone now."],
}
SITUATION = {
    "cpu_high": "the user's computer has been running at near 100 percent CPU for a while",
    "cpu_calm": "the user's computer calmed down after a long stretch of heavy CPU load",
    "usb_in": "the user just plugged a USB device or drive into the computer",
    "usb_out": "the user just unplugged a USB device or drive",
}


# ------------------------------------------------------------------ readers
def read_cpu_times():
    """(idle, total) cumulative CPU time, or None where unavailable."""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            from ctypes import wintypes

            class FT(ctypes.Structure):
                _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]
            idle, kern, user = FT(), FT(), FT()
            if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
                return None
            v = lambda f: (f.hi << 32) | f.lo          # noqa: E731
            return v(idle), v(kern) + v(user)          # kernel time already includes idle
        if sys.platform == "darwin":
            return None
        with open("/proc/stat", encoding="ascii") as fh:
            parts = [int(x) for x in fh.readline().split()[1:9]]
        return parts[3] + parts[4], sum(parts)
    except Exception:
        return None


def read_devices():
    """{id: label} of removable USB things plugged in right now. Names only; never touches their contents."""
    out = {}
    try:
        if sys.platform.startswith("win"):
            import ctypes
            mask = ctypes.windll.kernel32.GetLogicalDrives()
            for i in range(26):
                if mask & (1 << i):
                    root = f"{chr(65 + i)}:\\"
                    if ctypes.windll.kernel32.GetDriveTypeW(root) == 2:          # DRIVE_REMOVABLE
                        out[root] = f"USB drive {chr(65 + i)}:"
        elif sys.platform.startswith("linux"):
            base = "/sys/bus/usb/devices"
            for name in os.listdir(base):
                if name.startswith("usb") or ":" in name:                       # root hubs and interfaces
                    continue
                try:
                    with open(os.path.join(base, name, "product"), encoding="utf-8", errors="ignore") as fh:
                        label = fh.read().strip()
                except OSError:
                    continue
                if label and "hub" not in label.lower():
                    out[name] = label
    except Exception:
        pass
    return out


class CpuMeter:
    def __init__(self, reader=read_cpu_times):
        self.reader, self.prev = reader, None

    def sample(self):
        """CPU load 0-100 since the previous call, or None (first call, or unreadable)."""
        cur = self.reader()
        prev, self.prev = self.prev, cur
        if not cur or not prev:
            return None
        di, dt = cur[0] - prev[0], cur[1] - prev[1]
        if dt <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - di / dt)))


class Reactor:
    """Turns raw readings into a few rare events: ('cpu_high',), ('cpu_calm',), ('usb_in', label), ('usb_out', label)."""

    def __init__(self):
        self.devices = None              # first reading is the baseline: things already plugged in don't count
        self.hot_since = self.cool_since = None
        self.hot_announced = False
        self.last_cpu = -1e9
        self.last_usb = -1e9

    def feed(self, now, cpu, devices):
        ev = []
        if cpu is not None:
            if cpu >= CPU_HIGH:
                self.cool_since = None
                self.hot_since = self.hot_since or now
                if now - self.hot_since >= CPU_HIGH_FOR and not self.hot_announced and now - self.last_cpu >= CPU_COOLDOWN:
                    self.hot_announced, self.last_cpu = True, now
                    ev.append(("cpu_high", ""))
            else:
                self.hot_since = None
                if self.hot_announced:
                    if cpu < CPU_CALM:
                        self.cool_since = self.cool_since or now
                        if now - self.cool_since >= CPU_CALM_FOR:
                            self.hot_announced, self.cool_since = False, None
                            ev.append(("cpu_calm", ""))
                    else:
                        self.cool_since = None
        if devices is not None:
            if self.devices is None:
                self.devices = dict(devices)
            else:
                added = [devices[k] for k in devices if k not in self.devices]
                removed = [self.devices[k] for k in self.devices if k not in devices]
                self.devices = dict(devices)
                if (added or removed) and now - self.last_usb >= USB_COOLDOWN:
                    self.last_usb = now
                    if added:
                        ev.append(("usb_in", added[0]))
                    elif removed:
                        ev.append(("usb_out", removed[0]))
        return ev


class Watch:
    """Background poller. Events land in a thread-safe list the app drains on its own thread."""

    def __init__(self, interval=3.0, cpu_reader=read_cpu_times, dev_reader=read_devices, clock=time.time):
        self.interval, self.clock = interval, clock
        self.meter, self.dev_reader = CpuMeter(cpu_reader), dev_reader
        self.reactor = Reactor()
        self.events, self.lock = [], threading.Lock()
        self.running, self._thread = False, None

    def poll(self):
        ev = self.reactor.feed(self.clock(), self.meter.sample(), self.dev_reader())
        if ev:
            with self.lock:
                self.events += ev
        return ev

    def drain(self):
        with self.lock:
            out, self.events = self.events, []
        return out

    def start(self):
        if self.running:
            return
        self.running = True

        def run():
            while self.running:
                try:
                    self.poll()
                except Exception:
                    pass
                time.sleep(self.interval)
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
