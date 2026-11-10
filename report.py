"""/report: a bug report the user can paste to whoever is fixing Capri (pure logic, no Tk).

It holds versions, which features are on, and recent errors from capri.log. It never holds API keys, notes,
memory, journal, to-dos, chat text or window titles; key-like strings and the user's home folder are scrubbed
even if they somehow got into the log.
"""
import os
import re

# settings that are safe to show (on/off switches, levels, numbers). Anything else is left out.
SAFE_SETTINGS = ("skin", "tiny", "intro", "boot_anim", "size", "auto_size", "hands", "voice", "brain", "brain_model",
                 "aware", "ledges", "ai_vision", "glance", "vision_interval", "expressive", "faces", "cutins",
                 "meeting_quiet", "game_quiet", "agent", "wake", "hear", "mic", "calm", "checkins", "neon", "outline",
                 "roast", "track_time", "sfx", "radio", "talk_hotkey", "ai_lines")

SECRET_PATTERNS = [
    r"(?<=://)[^/\s:@]+(?::[^/\s@]*)?@",    # user:password@ inside a URL (before the e-mail rule)
    r"sk-ant-[A-Za-z0-9_\-]{8,}",          # Anthropic
    r"sk-[A-Za-z0-9_\-]{20,}",             # other sk- keys
    r"AIza[0-9A-Za-z_\-]{20,}",            # Google / Gemini
    r"\b[0-9a-f]{32,}\b",                  # long hex tokens (Fish Audio etc.)
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",   # emails
    r"(?i)(x-api-key|authorization|api[_-]?key)\s*[:=]\s*\S+",
    r"gh[pousr]_[A-Za-z0-9]{20,}",         # GitHub tokens
    r"github_pat_[A-Za-z0-9_]{20,}",
]
ERROR_WORDS = ("error", "failed", "traceback", "exception", "can't", "couldn't")
MAX_LOG_LINES = 80


def scrub(text, home=None):
    """Remove anything key-like and the user's home folder path."""
    t = text or ""
    for pat in SECRET_PATTERNS:
        t = re.sub(pat, "[removed]", t)
    home = home if home is not None else os.path.expanduser("~")
    if home and len(home) > 3:
        t = t.replace(home, "~").replace(home.replace("\\", "/"), "~")
    return t


def safe_settings(settings):
    out = {}
    for k in SAFE_SETTINGS:
        if k in settings:
            v = settings[k]
            if isinstance(v, (bool, int, float)) or (isinstance(v, str) and len(v) <= 24):
                out[k] = v
    return out


def recent_log(text, max_lines=MAX_LOG_LINES):
    """The interesting part of the log: the last error blocks (with their tracebacks) plus the last lines."""
    lines = (text or "").splitlines()
    keep = set(range(max(0, len(lines) - 25), len(lines)))
    for i, line in enumerate(lines):
        low = line.lower()
        if any(w in low for w in ERROR_WORDS):
            keep.update(range(i, min(len(lines), i + 12)))
    picked = [lines[i] for i in sorted(keep)]
    if len(picked) > max_lines:
        picked = ["... (older lines cut)"] + picked[-max_lines:]
    return picked


def build(info, settings, log_text, home=None):
    """The whole report as plain text."""
    parts = ["=== CAPRI BUG REPORT ==="]
    for k, v in info.items():
        parts.append(f"{k}: {v}")
    parts.append("--- settings ---")
    for k, v in safe_settings(settings).items():
        parts.append(f"{k}: {v}")
    parts.append("--- recent log ---")
    parts += recent_log(log_text) or ["(empty)"]
    parts.append("=== END ===")
    return scrub("\n".join(parts), home)


def rotate(path, max_bytes=1_000_000):
    """Keep capri.log from growing forever: over max_bytes it becomes capri.log.1 (one old copy kept)."""
    try:
        if os.path.getsize(path) > max_bytes:
            old = path + ".1"
            if os.path.exists(old):
                os.remove(old)
            os.replace(path, old)
            return True
    except OSError:
        pass
    return False
