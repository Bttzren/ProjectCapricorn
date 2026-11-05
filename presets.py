"""One-click permission presets (pure logic, no Tk). NONE / SOME / FULL, each still toggleable one by one.

A preset is just a set of the same settings the individual switches change, so after picking one you can
flip any single switch and the label becomes 'Custom'. Reflexes (auto-lock / auto-pause when you walk away)
are NOT part of any preset: they act by themselves while you're gone, so they stay a separate choice.
"""

# setting -> value. 'hands' is the control level (visual | media | full).
PRESETS = {
    "none": {"hands": "visual", "wake": False, "mic": False, "ai_vision": False, "agent": False,
             "aware": False, "ledges": False},
    "some": {"hands": "media", "wake": False, "mic": True, "ai_vision": False, "agent": False,
             "aware": True, "ledges": True},
    "full": {"hands": "full", "wake": True, "mic": True, "ai_vision": True, "agent": True,
             "aware": True, "ledges": True},
}
ORDER = ("none", "some", "full")
LABELS = {"none": "NONE", "some": "SOME", "full": "FULL", "custom": "CUSTOM"}
DEFAULTS = {"hands": "visual", "wake": False, "mic": True, "ai_vision": False, "agent": False,
            "aware": True, "ledges": False}      # what the app does with a brand-new settings file

SUMMARY = {
    "none": "Pure desktop pet. Can't press keys, click, listen, or look at your screen. Everything off.",
    "some": "Media keys when you ask (play/pause, volume), knows what kind of app you're in, sits on screen boxes, "
            "push-to-talk. No always-on mic, no screen sending, no clicking for you.",
    "full": "Everything: presses keys, types and clicks for you (/do tasks), listens for 'Hey Capri', and lets AI see "
            "your screen. Each thing still asks you before it types or acts.",
}

# plain-language lines used in the one confirmation dialog
EFFECTS = {
    "hands": {"visual": "Can't press keys or click", "media": "Media keys (play/pause, volume, lock screen) on request",
              "full": "Press any keys, type and click in ANY app (including sending messages)"},
    "wake": "Microphone stays open to hear 'Hey Capri' / 'Choom' (speech is turned into text on your PC)",
    "mic": "Push-to-talk microphone (hotkey Ctrl+Alt+C, MIC button, /talk)",
    "ai_vision": "Sends small screenshots to your AI provider so she can watch games and react",
    "agent": "/do tasks: she looks at your screen and clicks/types to do things you ask",
    "aware": "Knows what kind of app you're using (games, browser, editor...), never saves titles",
    "ledges": "Looks at your screen (on your PC only) to find boxes she can sit on",
}


def current(settings):
    """The settings view the presets care about, with defaults filled in."""
    return {k: settings.get(k, d) for k, d in DEFAULTS.items()}


def detect(settings):
    """'none' | 'some' | 'full' | 'custom'."""
    cur = current(settings)
    for name in ORDER:
        if all(cur[k] == v for k, v in PRESETS[name].items()):
            return name
    return "custom"


def changes(settings, name):
    """{setting: new_value} for what applying `name` would actually change."""
    cur = current(settings)
    return {k: v for k, v in PRESETS[name].items() if cur[k] != v}


def risky(name, settings):
    """Plain-language lines for everything this preset turns ON that wasn't on already."""
    out = []
    for k, v in changes(settings, name).items():
        if k == "hands":
            if v != "visual":
                out.append(EFFECTS["hands"][v])
        elif v is True:
            out.append(EFFECTS[k])
    return out


def table(settings):
    """Status lines for /powers."""
    cur = current(settings)
    names = {"hands": "Control", "wake": "Always-listen (Hey Capri)", "mic": "Push-to-talk microphone",
             "ai_vision": "AI sees your screen", "agent": "Tasks (/do)", "aware": "Awareness",
             "ledges": "Screen ledges"}
    out = [f"Preset: {LABELS[detect(settings)]}"]
    for k, label in names.items():
        v = cur[k]
        out.append(f"  {label}: " + (v if k == "hands" else ("ON" if v else "off")))
    return out
