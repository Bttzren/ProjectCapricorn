"""Are you in a call or meeting right now? Then Capri stays quiet. Pure logic + a Windows registry reader.

Two signals, both local:
- the TITLE of the front window looks like a meeting (Zoom Meeting, Google Meet, a Teams call, Webex...).
  Only used while Awareness is on; the title is not stored.
- Windows says a CALL APP is using the microphone right now (Discord voice, Zoom, Teams, Meet in a browser).
  Windows keeps this in the registry for its own mic-privacy icon; we only read app names + "in use or not".
  Only known call apps count (an allow-list): OBS, NVIDIA Broadcast, Voicemeeter, Sonar, Krisp etc. hold the
  mic all day and must not make her go quiet forever. Capri's own mic use is never on the list.
Nothing here records audio or is sent anywhere.
"""
import re

TITLE_PATTERNS = [
    r"\bzoom (meeting|webinar)\b", r"^zoom$",
    r"\bgoogle meet\b", r"^meet\s*[-–—|:]", r"\bmeet\.google\.com\b",
    r"\bmicrosoft teams\b.*\b(meeting|call)\b", r"\b(meeting|call)\b.*\bmicrosoft teams\b",
    r"\bwebex\b", r"\bgotomeeting\b", r"\bskype\b.*\bcall\b",
]
CALL_APPS = ("discord", "discordptb", "discordcanary", "zoom", "teams", "msteams", "ms-teams", "skype", "webex",
             "ciscocollabhost", "slack", "whatsapp", "telegram", "signal", "facetime",
             # browsers: Google Meet / Teams web / Discord web. A browser only holds the mic while a site uses it.
             "chrome", "msedge", "firefox", "brave", "opera", "vivaldi", "arc")
GRACE = 45.0                                            # seconds without a signal before she talks again
MIC_MAX = 4 * 3600.0     # a mic held this long with no meeting window is probably a stale entry: stop trusting it

MIC_KEY = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"


def title_is_meeting(title):
    t = (title or "").lower().strip()
    return bool(t) and any(re.search(p, t) for p in TITLE_PATTERNS)


def app_name(key_name):
    """'C:#Program Files#Discord#app-1.0#Discord.exe' -> 'discord'; packaged 'Microsoft.Teams_8wekyb' -> 'teams'."""
    last = (key_name or "").replace("\\", "#").split("#")[-1]
    last = re.sub(r"\.exe$", "", last, flags=re.I)
    m = re.fullmatch(r"(.+)_[a-z0-9]{13}", last, re.I)  # packaged app family name: Publisher.App_<13-char id>
    if m:
        last = m.group(1).split(".")[-1]
    return last.lower()


def mic_users(entries, apps=CALL_APPS):
    """Call apps using the mic right now, from [(key_name, last_used_start, last_used_stop)].
    Windows sets stop to 0 while the app still has the mic open."""
    out = []
    for key, start, stop in entries:
        name = app_name(key)
        if start and not stop and name in apps and name not in out:
            out.append(name)
    return out


def read_mic_entries():
    """[(key_name, start, stop)] from HKCU on Windows; [] anywhere else or on any error."""
    try:
        import winreg
    except ImportError:
        return []
    out = []

    def scan(path):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as k:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(k, i)
                    except OSError:
                        break
                    i += 1
                    if sub == "NonPackaged":
                        continue
                    try:
                        with winreg.OpenKey(k, sub) as s:
                            start = winreg.QueryValueEx(s, "LastUsedTimeStart")[0]
                            stop = winreg.QueryValueEx(s, "LastUsedTimeStop")[0]
                        out.append((sub, int(start or 0), int(stop or 0)))
                    except OSError:
                        continue
        except OSError:
            pass

    scan(MIC_KEY)
    scan(MIC_KEY + r"\NonPackaged")
    return out


class Detector:
    """Turns the signals into 'start' / 'end' events, with a grace period so alt-tabbing out of a Zoom
    window or a short mute doesn't make her chatty mid-meeting."""

    def __init__(self, grace=GRACE, mic_max=MIC_MAX):
        self.grace, self.active, self.last_seen, self.why = grace, False, 0.0, ""
        self.mic_max, self.mic_since, self.mic_ignored = mic_max, None, ()

    def update(self, now, title="", mic=()):
        mic = tuple(mic or ())
        if not mic:
            self.mic_since, self.mic_ignored = None, ()          # signal cleared: trust the mic again
        elif self.mic_since is None:
            self.mic_since = now
        if mic and mic == self.mic_ignored:
            mic = ()
        elif mic and now - self.mic_since >= self.mic_max:
            self.mic_ignored, mic = mic, ()                      # stuck for hours: ignore until it changes
        why = ""
        if title_is_meeting(title):
            why = "a meeting window"
        elif mic:
            why = f"{mic[0]} is using the mic"
        if why:
            self.last_seen, self.why = now, why
            if not self.active:
                self.active = True
                return "start"
            return None
        if self.active and now - self.last_seen >= self.grace:
            self.active = False
            return "end"
        return None
