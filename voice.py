"""Capri's voice: speaks through the computer's built-in text-to-speech (no keys, no downloads).

Windows -> PowerShell + System.Speech      macOS -> `say`      Linux -> espeak-ng / espeak / spd-say
Text is sent on stdin (never on the command line), so nothing a user types can be run as a command.
Set CAPRI_VOICE to pick a specific installed voice name.
"""
import os
import re
import shutil
import subprocess
import sys
import time

CREATE_NO_WINDOW = 0x08000000

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


class Speaker:
    def __init__(self, platform=None, which=shutil.which, popen=subprocess.Popen, clock=time.time, min_gap=3.0):
        self.platform = platform or sys.platform
        self.argv = build_command(self.platform, which)
        self.popen, self.clock, self.min_gap = popen, clock, min_gap
        self.proc = None
        self.last_start = -1e9

    @property
    def available(self):
        return self.argv is not None

    @property
    def speaking(self):
        return self.proc is not None and self.proc.poll() is None

    def speak(self, text, priority=False):
        """Say `text`. Priority lines interrupt; others are dropped if she is busy or spoke just now."""
        if not self.available:
            return False
        line = clean(text)
        if not line:
            return False
        now = self.clock()
        if self.speaking:
            if not priority:
                return False
            self.stop()
        elif not priority and now - self.last_start < self.min_gap:
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
        self.last_start = now
        return True

    def stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
            except OSError:
                pass
            self.proc = None
