"""/update: get the newest Capri with git, from chat (pure logic; capri.py runs the commands).

Only ever started by the user typing /update (or the right-click menu). It fast-forwards the copy you already have
from the place it was cloned from: it never switches branches, never overwrites files you changed yourself, and
never asks for a password (git's own saved login is used, or it fails with a clear message).
"""
import os
import re

PULL = ["git", "pull", "--ff-only", "--no-rebase"]
FETCH = ["git", "fetch"]
BEHIND = ["git", "rev-list", "--count", "HEAD..@{u}"]
MAX_NEWS = 6


def is_checkout(app_dir):
    """Was this copy made with git (so git can update it)?"""
    return os.path.exists(os.path.join(app_dir, ".git"))


def git_env(base):
    """Environment for git: English messages (they get parsed) and never an interactive password prompt."""
    env = dict(base)
    env.update({"GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C", "LANG": "C", "LANGUAGE": "en", "GCM_INTERACTIVE": "never"})
    return env


def news_cmd(old, new):
    return ["git", "log", "--no-merges", "--format=%s", f"{old}..{new}", "-n", "40"]


def parse_pull(rc, out, err):
    """(status, detail) from `git pull --ff-only`.
    status: current | updated | local_changes | offline | login | no_branch | not_git | diverged | error.
    For 'updated', detail is (old, new) commit ids ('' when they couldn't be read)."""
    text = (out or "") + "\n" + (err or "")
    low = text.lower()
    if rc == 0:
        m = re.search(r"^Updating ([0-9a-f]{6,40})\.\.([0-9a-f]{6,40})", text, re.M)
        if m:
            return "updated", (m.group(1), m.group(2))
        if "already up to date" in low or "already up-to-date" in low:
            return "current", ""
        return ("updated", ("", "")) if "fast-forward" in low else ("current", "")
    if "not a git repository" in low:
        return "not_git", ""
    if "would be overwritten" in low or "please commit your changes or stash" in low or "local changes" in low:
        return "local_changes", ""
    if ("could not resolve host" in low or "unable to access" in low or "timed out" in low
            or "could not read from remote" in low or "failed to connect" in low or "network is unreachable" in low):
        if "authentication failed" in low or "403" in low or "401" in low:
            return "login", ""
        return "offline", ""
    if ("authentication failed" in low or "could not read username" in low or "terminal prompts disabled" in low
            or "permission denied" in low or "repository not found" in low):
        return "login", ""
    if "no tracking information" in low or "not currently on a branch" in low or "no such ref" in low:
        return "no_branch", ""
    if "not possible to fast-forward" in low or "diverging" in low or "divergent" in low:
        return "diverged", ""
    last = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "error", (last[-1] if last else f"git exit code {rc}")[:160]


def subjects(log_text, limit=MAX_NEWS):
    """The newest change titles, readable: no merge lines, no duplicates, trimmed."""
    out = []
    for ln in (log_text or "").splitlines():
        s = " ".join(ln.split())
        if not s or s.lower().startswith(("merge pull request", "merge branch", "handoff")) or s in out:
            continue
        out.append(s if len(s) <= 110 else s[:107].rstrip() + "...")
    return out[:limit], max(0, len(out) - limit)


MESSAGES = {
    "current": "You already have the newest version.",
    "local_changes": "Some of my files were changed on this PC, so I didn't overwrite them. "
                     "Undo those changes (or download a fresh copy) and try /update again.",
    "offline": "Couldn't reach the download site. Are you online?",
    "login": "The download site wants a login I don't have. Open a terminal in my folder and run: git pull",
    "no_branch": "This copy isn't following a branch, so I don't know what 'newest' is. In my folder run: git pull",
    "not_git": "This copy wasn't made with git, so I can't update it from here. Download the newest version "
               "and replace this folder (your settings and notes are kept: they live in your user folder).",
    "diverged": "This copy has its own changes that the newest version doesn't have, so I left it alone. "
                "Download a fresh copy to get the newest version.",
    "no_git": "Git isn't installed on this PC, so I can't update from here. Download the newest version and "
              "replace this folder (your settings and notes are kept: they live in your user folder).",
    "frozen": "This is the built .exe, which can't update itself. Get the newest Capri.exe from whoever built it.",
}


def report(status, detail="", news=(), more=0):
    """Lines for the chat."""
    if status == "updated":
        lines = ["Updated! Close me and start me again to use the new version."]
        if news:
            lines.append("New:")
            lines += ["  - " + n for n in news]
            if more:
                lines.append(f"  ...and {more} more.")
        return lines
    if status == "behind":
        n = int(detail or 0)
        return [f"{n} update{'s' if n != 1 else ''} waiting. Type /update to get {'them' if n != 1 else 'it'}."
                if n else MESSAGES["current"]]
    if status == "error":
        return ["Update failed: " + (detail or "unknown error")]
    return [MESSAGES.get(status, "Update failed.")]
