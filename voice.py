"""Capri's voice.

Two engines, picked automatically:
  * Fish Audio (Capri's real character voice) when a Fish API key is set. Each line is sent to
    Fish Audio's text-to-speech API, cached on disk, and played with the OS audio player.
  * The computer's built-in speech otherwise (no keys, nothing to install on Windows/Mac):
    Windows -> PowerShell + System.Speech, macOS -> `say`, Linux -> espeak-ng / espeak / spd-say.
Text for the system engine goes on stdin (never the command line), so nothing a user types can run
as a command. If Fish fails (no internet, bad key, no credits) she falls back to the system voice.
Set CAPRI_VOICE to pick a specific installed system voice name.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import wave

CREATE_NO_WINDOW = 0x08000000
FISH_URL = "https://api.fish.audio/v1/tts"
DEFAULT_FISH_VOICE = "ef387f44931d4ab6a3f959a083c9fbb1"     # Capri's Fish Audio voice model
DEFAULT_FISH_MODEL = "s1"

WIN_SCRIPT = (
    "Add-Type -AssemblyName System.Speech; "
    "[Console]::InputEncoding = [Text.Encoding]::UTF8; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 1; "
    "try { $s.SelectVoice('%s') } catch {}; "
    "$t = [Console]::In.ReadToEnd(); $s.Speak($t)"
)


def clean(text, limit=280):
    """Turn a chat/bubble line into something worth saying aloud ('' means stay quiet)."""
    t = re.sub(r"\*[^*]*\*", " ", text)            # *glitches* stage directions
    t = re.sub(r"\([^)]*\)", " ", t)               # (offline mode notes)
    t = re.sub(r"https?://\S+", " link ", t)
    t = re.sub(r"\.{2,}|…", ", ", t)
    t = re.sub(r"[^\w\s.,!?'\-:;]", " ", t, flags=re.UNICODE)   # emoji, markdown, symbols
    t = t.replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    if len(re.findall(r"[^\W\d_]", t)) < 2:
        return ""
    if re.fullmatch(r"(z+\W*)+", t.lower()):        # "zzz..."
        return ""
    return t[:limit]


def build_command(platform, which=shutil.which, voice=None):
    """argv that reads the text to speak from stdin, or None if this system can't speak."""
    voice = voice or os.environ.get("CAPRI_VOICE", "")
    if platform.startswith("win"):
        ps = which("powershell") or which("pwsh")
        if not ps:
            return None
        name = (voice or "Microsoft Zira Desktop").replace("'", "''")
        return [ps, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", WIN_SCRIPT % name]
    if platform == "darwin":
        say = which("say")
        if not say:
            return None
        return [say, "-r", "190"] + (["-v", voice] if voice else []) + ["-f", "-"]
    for exe, args in (("espeak-ng", ["-s", "165", "-p", "65", "--stdin"]),
                      ("espeak", ["-s", "165", "-p", "65", "--stdin"]),
                      ("spd-say", ["-e"])):
        path = which(exe)
        if path:
            extra = ["-v", voice] if voice and exe.startswith("espeak") else []
            return [path] + extra + args
    return None


# ------------------------------------------------------------------ Fish Audio
class FishVoice:
    """Fetches (and caches) speech from Fish Audio's text-to-speech API as WAV files."""

    def __init__(self, key, voice_id=DEFAULT_FISH_VOICE, cache_dir=None, opener=urllib.request.urlopen,
                 model=None, timeout=25, max_cache=300):
        self.key, self.voice_id = key.strip(), voice_id
        self.cache_dir = cache_dir
        self.opener, self.timeout, self.max_cache = opener, timeout, max_cache
        self.model = model or os.environ.get("CAPRI_FISH_MODEL") or DEFAULT_FISH_MODEL

    def cache_path(self, text):
        h = hashlib.sha1(f"{self.voice_id}|{text}".encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, h + ".wav")

    def _request(self, text, with_model):
        body = json.dumps({"text": text, "reference_id": self.voice_id, "format": "wav",
                           "normalize": True, "latency": "normal"}).encode("utf-8")
        headers = {"Authorization": "Bearer " + self.key, "Content-Type": "application/json"}
        if with_model and self.model:
            headers["model"] = self.model
        return urllib.request.Request(FISH_URL, data=body, headers=headers, method="POST")

    def _post(self, text, with_model=True):
        try:
            with self.opener(self._request(text, with_model), timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if with_model and exc.code in (400, 422):       # model header not accepted: retry without it
                return self._post(text, with_model=False)
            hint = {401: "bad Fish Audio key", 402: "out of Fish Audio credits", 403: "Fish Audio key not allowed",
                    404: "voice model not found", 429: "Fish Audio rate limit"}.get(exc.code, "")
            raise RuntimeError(f"Fish Audio {exc.code}" + (f" ({hint})" if hint else ""))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"can't reach Fish Audio ({exc.reason})")

    def fetch(self, text):
        """Path to a WAV of `text` in Capri's voice (downloaded once, then served from the cache)."""
        os.makedirs(self.cache_dir, exist_ok=True)
        path = self.cache_path(text)
        if os.path.isfile(path) and os.path.getsize(path) > 44:
            return path
        data = self._post(text)
        if data[:4] != b"RIFF":
            raise RuntimeError("Fish Audio sent something that isn't WAV audio")
        tmp = path + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
        self._prune()
        return path

    def _prune(self):
        try:
            files = [os.path.join(self.cache_dir, n) for n in os.listdir(self.cache_dir) if n.endswith(".wav")]
            if len(files) > self.max_cache:
                files.sort(key=os.path.getmtime)
                for old in files[:len(files) - self.max_cache]:
                    os.remove(old)
        except OSError:
            pass


def wav_seconds(path):
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, OSError, EOFError, ZeroDivisionError):
        return 0.0


def play_file(path, platform=None, which=shutil.which, popen=subprocess.Popen, winsound_mod=None):
    """Start playing a WAV without blocking. Returns (process_or_None, seconds) or None if no player."""
    platform = platform or sys.platform
    if platform.startswith("win"):
        try:
            ws = winsound_mod
            if ws is None:
                import winsound as ws
            ws.PlaySound(path, ws.SND_FILENAME | ws.SND_ASYNC)
            return None, wav_seconds(path)
        except (ImportError, RuntimeError):
            return None
    if platform == "darwin":
        cmds = [["afplay", path]]
    else:
        cmds = [["paplay", path], ["aplay", "-q", path], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]]
    for cmd in cmds:
        exe = which(cmd[0])
        if exe:
            try:
                return popen([exe] + cmd[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), 0.0
            except OSError:
                continue
    return None


def stop_playback(platform=None, winsound_mod=None):
    platform = platform or sys.platform
    if platform.startswith("win"):
        try:
            ws = winsound_mod
            if ws is None:
                import winsound as ws
            ws.PlaySound(None, ws.SND_PURGE)
        except (ImportError, RuntimeError):
            pass


# ------------------------------------------------------------------ speaker
class Speaker:
    def __init__(self, platform=None, which=shutil.which, popen=subprocess.Popen, clock=time.time, min_gap=3.0,
                 fish=None, player=None, threaded=True, log=None):
        self.platform = platform or sys.platform
        self.argv = build_command(self.platform, which)
        self.popen, self.clock, self.min_gap = popen, clock, min_gap
        self.fish, self.threaded, self.log = fish, threaded, log or (lambda m: None)
        self.player = player or (lambda p: play_file(p, self.platform, which, popen))
        self.proc = None
        self.last_start = -1e9
        self.last_error = ""
        self._gen = 0
        self._until = 0.0
        self._fetching = False

    @property
    def engine(self):
        return "fish" if self.fish else ("system" if self.argv else "none")

    @property
    def available(self):
        return self.fish is not None or self.argv is not None

    @property
    def speaking(self):
        if self.proc is not None and self.proc.poll() is None:
            return True
        return self.clock() < self._until

    def speak(self, text, priority=False):
        """Say `text`. Priority lines interrupt; others are dropped if she is busy or spoke just now."""
        if not self.available:
            return False
        line = clean(text)
        if not line:
            return False
        now = self.clock()
        if self.speaking or self._fetching:
            if not priority:
                return False
            self.stop()
        elif not priority and now - self.last_start < self.min_gap:
            return False
        self.last_start = now
        if self.fish:
            self._gen += 1
            job = threading.Thread(target=self._fish_job, args=(line, self._gen), daemon=True)
            if self.threaded:
                self._fetching = True
                job.start()
            else:
                self._fish_job(line, self._gen)
            return True
        return self._speak_system(line)

    def _fish_job(self, line, gen):
        self._fetching = True
        try:
            try:
                path = self.fish.fetch(line)
            except Exception as exc:                      # network, key, credits... fall back, but say why
                self.last_error = str(exc)
                self.log("fish audio failed: " + str(exc))
                if gen == self._gen and self.argv:
                    self._speak_system(line)
                return
            if gen != self._gen:                         # stopped or replaced while downloading
                return
            res = self.player(path)
            if res is None:
                self.last_error = "no audio player found for Capri's voice"
                if self.argv:
                    self._speak_system(line)
                return
            self.last_error = ""
            self.proc, secs = res
            self._until = self.clock() + secs if secs else 0.0
        finally:
            self._fetching = False

    def _speak_system(self, line):
        if not self.argv:
            return False
        flags = CREATE_NO_WINDOW if self.platform.startswith("win") else 0
        try:
            self.proc = self.popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, creationflags=flags)
            self.proc.stdin.write(line.encode("utf-8"))
            self.proc.stdin.close()
        except (OSError, ValueError):
            self.argv = None            # this system can't speak; stop trying
            self.proc = None
            return False
        return True

    def stop(self):
        self._gen += 1
        self._until = 0.0
        if self.proc is not None:
            try:
                self.proc.terminate()
            except OSError:
                pass
            self.proc = None
        if self.fish:
            stop_playback(self.platform)
