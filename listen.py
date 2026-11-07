"""Voice input: she listens when YOU ask (hotkey, /talk or the menu), never in the background.

Push-to-talk: the mic opens, waits for you to start speaking, stops when you go quiet, then the audio is
turned into text ON YOUR COMPUTER (faster-whisper, no key, nothing uploaded) and handed to her like a typed
message. The audio only lives in memory and is thrown away right after.

Pure logic + two optional packages (sounddevice for the mic, faster-whisper for the words). No Tk.
"""
import array
import importlib.util
import math
import re
import threading
import time

import launcher
import sizing

RATE = 16000
CHUNK = 1600                    # 0.1 s of audio per chunk
MODEL = "base.en"               # ~150 MB download the first time; "tiny.en" is smaller and a bit worse
PACKAGES = ("faster-whisper", "sounddevice")


def installed():
    try:
        return all(importlib.util.find_spec(m) is not None for m in ("faster_whisper", "sounddevice"))
    except (ImportError, ValueError):
        return False


def rms(pcm):
    """Loudness of a chunk of 16-bit little-endian mono PCM bytes."""
    a = array.array("h")
    a.frombytes(pcm[: len(pcm) // 2 * 2])
    if not a:
        return 0.0
    return math.sqrt(sum(s * s for s in a) / len(a))


class Endpointer:
    """Decides when you've started and finished talking. feed(loudness) once per chunk -> state.

    states: waiting (hasn't started) | speech | done (you finished) | timeout (never started) | max (too long)
    """

    def __init__(self, chunk_s=CHUNK / RATE, quiet_s=1.0, wait_s=7.0, max_s=15.0, min_speech_s=0.35,
                 calibrate_s=0.3, floor=350.0):
        self.chunk_s, self.quiet_s, self.wait_s, self.max_s = chunk_s, quiet_s, wait_s, max_s
        self.min_speech_s, self.calibrate_s, self.floor = min_speech_s, calibrate_s, floor
        self.t = self.speech_s = self.quiet = 0.0
        self.noise, self.n_cal = 0.0, 0
        self.threshold = floor
        self.state = "waiting"

    def feed(self, level):
        if self.state in ("done", "timeout", "max"):
            return self.state
        self.t += self.chunk_s
        if self.t <= self.calibrate_s:                       # measure the room's noise before judging
            self.noise = max(self.noise, level)
            self.n_cal += 1
            if self.t + self.chunk_s > self.calibrate_s:
                self.threshold = max(self.floor, self.noise * 2.5)
            return self.state
        loud = level >= self.threshold
        if loud:
            self.speech_s += self.chunk_s
            self.quiet = 0.0
            if self.speech_s >= self.min_speech_s:
                self.state = "speech"
        elif self.state == "speech":
            self.quiet += self.chunk_s
            if self.quiet >= self.quiet_s:
                self.state = "done"
        elif self.t >= self.wait_s:
            self.state = "timeout"
        if self.t >= self.max_s and self.state == "speech":
            self.state = "max"
        return self.state


def record(chunks, endpointer=None, level=rms):
    """Consume an iterator of PCM chunks until the Endpointer says stop. Returns (pcm_bytes, state)."""
    ep = endpointer or Endpointer()
    out = []
    try:
        for c in chunks:
            out.append(c)
            st = ep.feed(level(c))
            if st in ("done", "timeout", "max"):
                return b"".join(out), st
        return b"".join(out), ep.state
    finally:
        close = getattr(chunks, "close", None)           # releases the microphone straight away
        if close:
            close()


JUNK = re.compile(r"^(thanks? for watching[.!]*|thank you[.!]*|you[.!]*|bye[.!]*|\.+|\[.*?\]|\(.*?\)|♪.*)$", re.I)


def clean_transcript(text):
    """Whisper invents words on silence ('Thank you.'). Drop those and tidy the rest. '' = nothing heard."""
    t = " ".join((text or "").split()).strip()
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", t)
    t = " ".join(t.split())
    if not t or JUNK.match(t) or len(re.findall(r"[A-Za-z]", t)) < 2:
        return ""
    return t[:300]


TASK_WORDS = {"open", "join", "tell", "send", "play", "launch", "start", "search", "close", "message", "mute",
              "unmute", "load", "go"}
CONTROLS = [
    ("playpause", r"(pause|resume|unpause|continue)( the)?( music| song| track| video| playback| it)?|play( the| some)? music"),
    ("next", r"(next|skip)( the)?( song| track| video)?|skip this( song| track)?|next one"),
    ("prev", r"(previous|last|go back)( a)?( song| track)?|play the previous( song| track)?|previous one"),
    ("volup", r"volume up|louder|turn (it|the volume|the music|this) up|(raise|increase|up)( the)? volume"),
    ("voldown", r"volume down|quieter|turn (it|the volume|the music|this) down|(lower|decrease|down)( the)? volume"),
    ("mute", r"(mute|unmute)( the)?( sound| volume| audio| it| computer| pc)?"),
    ("screenshot", r"(take a |grab a )?screenshot( this| please)?"),
    ("lock", r"lock( the| my)?( screen| computer| pc| it)?"),
    ("desktop", r"show( the)? desktop|minimi[sz]e (everything|all|all windows)"),
]
FILLER = re.compile(r"^(can you|could you|please|would you|go ahead and|just|for me)\s+", re.I)


_ABOUT = r"(?:\s+(?:about|on|for|regarding|with))?"
NOTE_FIND = [
    r"(?:what|which)(?: notes?)? (?:did|have) i (?:note|noted|write down|wrote down|written down|jot down|jotted down|"
    r"save|saved)(?: down)?" + _ABOUT + r"\s*(.*)",
    r"(?:read|show|list|check|find|search|open)(?: me)? (?:my|the) notes?" + _ABOUT + r"\s*(.*)",
    r"(?:do i have|have i got|is there|are there)(?: any| a)? notes?" + _ABOUT + r"\s+(.+)",
    r"(?:what are|what were|what's in|whats in) my notes" + _ABOUT + r"\s*(.*)",
    r"my notes" + _ABOUT + r"\s*(.*)",
]
NOTE_ADD = r"(?:(?:take|make|save|add|leave)(?: a| me a)? note(?: that| of| to self| saying)?|note to self|" \
           r"note(?: that| down)?|(?:write|jot|put)(?: this| that| it)? down(?: that)?)\b[\s:,-]*(.*)"


def note_intent(t):
    """('notes', query) for 'what did I note about X' / 'read my notes', ('note', text) for 'note that X' /
    'take a note: X', or None. Checked on the cleaned phrase, so 'open notepad' is not a note."""
    low = t.lower().strip(" .!?")
    for pat in NOTE_FIND:
        m = re.fullmatch(pat, low)
        if m:
            return ("notes", m.group(1).strip(" .!?"))
    m = re.fullmatch(NOTE_ADD, t.strip(" ."), re.I | re.S)
    if m:
        return ("note", m.group(1).strip(" .!?"))
    return None


def intent(text):
    """What did the user say? ('stop',) | ('task', text) | ('chat', text) | ('none', ''). 'Hey Capri' is optional.

    Tasks never run just because she heard them: the caller still shows the usual confirmation."""
    t = clean_transcript(text)
    if not t:
        return ("none", "")
    t = re.sub(r"^(hey|hi|yo|ok|okay)[, ]+capri[,.!]*\s*", "", t, flags=re.I)
    t = re.sub(r"^capri[,.!]*\s*", "", t, flags=re.I).strip()
    while True:
        t2 = FILLER.sub("", t).strip()
        if t2 == t:
            break
        t = t2
    low = t.lower().strip(" .!?")
    if low in ("stop", "stop it", "cancel", "never mind", "nevermind", "stop that", "abort"):
        return ("stop", "")
    if not t:
        return ("none", "")
    if re.search(r"\bprivacy mode\b|\bturn everything off\b|\bturn off everything\b", low):
        return ("privacy", "")
    if re.search(r"what'?s on my plate|my briefing|daily briefing|brief me|what do i have (to do|today)|what'?s my day|"
                 r"what is on my plate", low):
        return ("brief", "")
    if re.match(r"(start|begin|do)( a| an)? (focus|pomodoro)( timer| session| mode)?$", low):
        return ("focus", "")
    note = note_intent(t)
    if note:
        return note
    for action, pat in CONTROLS:
        if re.fullmatch(pat, low):
            return ("control", action)
    if re.match(r"(remind me|set (a|an) (timer|alarm)|start (a|an) timer|timer\b)", low) and parse_reminder(t):
        return ("remind", t)
    if sizing.spoken_size(low):
        return ("size", low)
    if re.search(r"\b(copied|clipboard)\b", low) and re.search(r"\b(explain|summari[sz]e|translate|fix|reply|what)\b", low):
        return ("clip", low)
    if re.search(r"what (did|was)( he| she| they| that| the)?( that| they)?( guy| person| man| woman)? (just )?(say|said)|"
                 r"what are (they|he|she) saying|say that again|transcribe (that|this)|what did i miss", low):
        return ("hear", "last")
    if re.fullmatch(r"(summari[sz]e|recap|tldr)( this| that| it)?( call| video| meeting| stream| conversation| lecture| clip)?", low):
        return ("hear", "summarize")
    if re.search(r"\b(leave|exit|end|quit)\b.*\b(call|vc|voice chat)\b|stop talking to (my )?friends|\bcall mode off\b", low):
        return ("call", "off")
    if re.search(r"\bcall mode( on)?\b|talk (to|with) my friends|(join|jump in|hop in|get in).*\b(call|vc|voice (chat|channel))"
                 r"\b.*\b(talk|chat|hang)\b|(talk|chat|hang out)( to| with)? (my )?friends (in|on) (the )?(discord|call|vc)", low):
        return ("call", "join")
    if launcher.parse_open(t):
        return ("launch", t)
    words = re.findall(r"[a-z']+", low)
    first = words[0] if words else ""
    second = words[1] if len(words) > 1 else ""
    is_task = first in TASK_WORDS and not (first == "tell" and second in ("me", "us", "you")) \
        and not (first == "go" and second != "to") and not (first == "start" and second in ("to", "feeling"))
    return ("task", t[0].upper() + t[1:]) if is_task else ("chat", t)


NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
                "thirty": 30, "forty": 40, "forty five": 45, "fifty": 50, "sixty": 60, "ninety": 90}
_UNIT = r"(second|sec|minute|min|hour|hr)s?"
_NUM = r"(\d+(?:\.\d+)?|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r"|half an|half a)"


def parse_duration(text):
    """Minutes from '20 minutes', 'an hour', 'half an hour', 'five min', '1.5 hours'. None if there isn't one."""
    t = (text or "").lower()
    if re.search(r"\bhalf an? hour\b", t):
        return 30.0
    m = re.search(_NUM + r"\s*" + _UNIT + r"\b", t)
    if not m:
        return None
    n = m.group(1)
    val = float(n) if n[0].isdigit() else NUMBER_WORDS.get(n, 0.5)
    unit = m.group(2)
    mins = val * (60 if unit.startswith(("hour", "hr")) else (1 / 60.0 if unit.startswith("sec") else 1))
    return round(mins, 2) if 0.1 <= mins <= 24 * 60 else None


def parse_reminder(text):
    """(minutes, what) for 'remind me in 20 minutes to call mom' / 'remind me to call mom in an hour' /
    'set a timer for 10 minutes'. what is 'Timer is up!' for timers. None if it isn't a reminder."""
    t = " ".join((text or "").split()).strip(" .!?")
    low = t.lower()
    mins = parse_duration(low)
    if mins is None:
        return None
    if re.match(r"(set (a|an) |start (a|an) )?(timer|alarm)\b", low) or re.search(r"\btimer for\b", low):
        return mins, "Timer is up!"
    m = re.match(r"remind me\s+(?:in\s+(.+?)\s+)?(?:to|about|that)\s+(.+)$", t, re.I)
    if m:
        what = m.group(2)
        what = re.sub(r"\s+in\s+" + _NUM + r"\s*" + _UNIT + r"$", "", what, flags=re.I).strip()
        return (mins, what[:120]) if what else None
    return None


class Whisper:
    """Speech to text with faster-whisper. The model loads on first use and is reused."""

    def __init__(self, model=MODEL, loader=None):
        self.model_name, self._loader, self._model = model, loader, None
        self._lock = threading.Lock()

    def _load(self):
        if self._loader:
            return self._loader(self.model_name)
        from faster_whisper import WhisperModel
        return WhisperModel(self.model_name, device="cpu", compute_type="int8")

    def transcribe(self, pcm):
        with self._lock:
            if self._model is None:
                self._model = self._load()
            model = self._model
        import numpy as np
        audio = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = model.transcribe(audio, language="en", beam_size=1, condition_on_previous_text=False)
        return clean_transcript("".join(s.text for s in segments))


def mic_chunks(stop=lambda: False, rate=RATE, chunk=CHUNK):
    """Yield PCM chunks from the default microphone until stop() or the generator is closed."""
    import sounddevice as sd
    with sd.RawInputStream(samplerate=rate, channels=1, dtype="int16", blocksize=chunk) as stream:
        while not stop():
            data, _overflow = stream.read(chunk)
            yield bytes(data)


def listen_once(chunks, whisper, endpointer=None, min_bytes=RATE * 2 // 4):
    """(text, state). The mic audio goes in, words come out. state is how the recording ended."""
    pcm, state = record(chunks, endpointer)
    if state == "timeout" or len(pcm) < min_bytes:
        return "", state
    return whisper.transcribe(pcm), state


# ================================================================== wake word ("Hey Capri" / "Choom")
# The mic stays open ONLY while wake mode is on (the user switched it on). Every phrase is turned into text on
# the user's computer and thrown away right away unless it starts with a wake word. Nothing is saved or sent.
import difflib
import queue

WAKE_NAMES = {
    "capri": {"capri", "kapri", "capree", "caprie", "cafri", "copri", "cabri", "capry", "kaprie", "caprii", "cappri",
              "capi", "caprice", "capris"},
    "choom": {"choom", "chum", "choomb", "shoom", "chuum", "choum", "choome", "chume", "choon", "tchoom"},
}
GREETINGS = {"hey", "hi", "yo", "ok", "okay", "hello", "ay", "oi", "hay", "a"}


def _is_name(word, ratio=0.8):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return None
    for name, aliases in WAKE_NAMES.items():
        if w in aliases or difflib.SequenceMatcher(None, w, name).ratio() >= ratio:
            return name
    return None


def strip_wake(text):
    """(matched, rest): does the phrase START with 'Hey Capri' / 'Choom' (fuzzy, Whisper mishears names)?
    A name later in a sentence doesn't count, so talking ABOUT her doesn't wake her."""
    t = " ".join((text or "").split())
    if not t:
        return False, ""
    parts = t.split(" ")
    i = 0
    if parts[0].strip(",.!?").lower() in GREETINGS and len(parts) > 1:
        i = 1
    if _is_name(parts[i]):
        rest = " ".join(parts[i + 1:])
        rest = re.sub(r"^[\s,.:;!?-]+", "", rest)
        return True, rest.strip()
    return False, ""


class Segmenter:
    """Cuts a never-ending mic stream into spoken phrases. feed(pcm_chunk) -> phrase bytes when one ends, else None."""

    def __init__(self, chunk_s=CHUNK / RATE, quiet_s=0.8, min_speech_s=0.4, max_s=15.0, floor=350.0, preroll=3):
        self.chunk_s, self.quiet_s, self.min_speech_s, self.max_s = chunk_s, quiet_s, min_speech_s, max_s
        self.floor, self.preroll = floor, preroll
        self.reset()
        self.noise = 0.0

    def reset(self):
        self.buf, self.pre = [], []
        self.speaking, self.speech_s, self.quiet = False, 0.0, 0.0
        self.total = 0.0

    @property
    def threshold(self):
        return max(self.floor, self.noise * 2.5)

    def feed(self, pcm, level=None):
        lv = rms(pcm) if level is None else level
        loud = lv >= self.threshold
        if not self.speaking:
            if not loud:
                self.noise = lv if self.noise == 0 else self.noise * 0.95 + lv * 0.05     # learn the room's hum
            self.pre = (self.pre + [pcm])[-self.preroll:]
            if loud:
                self.speech_s += self.chunk_s
                if self.speech_s >= self.min_speech_s:
                    self.speaking, self.buf, self.quiet = True, list(self.pre), 0.0
                    self.total = self.chunk_s * len(self.buf)
            else:
                self.speech_s = 0.0
            return None
        self.buf.append(pcm)
        self.total += self.chunk_s
        self.quiet = 0.0 if loud else self.quiet + self.chunk_s
        if self.quiet >= self.quiet_s or self.total >= self.max_s:
            out = b"".join(self.buf)
            self.reset()
            return out
        return None


class WakeLoop:
    """Reads the mic, finds phrases, transcribes them (off the audio thread) and reacts to wake words.

    emit(kind, text): kind 'wake' (she was called, no command yet), 'command' (text to act on) or 'error'.
    paused() -> True while she is talking or the mic is busy: audio is dropped. After 'wake' the next phrase,
    within `follow_s` seconds, is the command even without the wake word.
    """

    def __init__(self, whisper, emit, paused=lambda: False, clock=time.time, follow_s=8.0, holdoff_s=1.2,
                 per_min=15, max_phrase_s=12.0, segmenter=None):
        self.whisper, self.emit, self.paused, self.clock = whisper, emit, paused, clock
        self.follow_s, self.holdoff_s, self.per_min, self.max_phrase_s = follow_s, holdoff_s, per_min, max_phrase_s
        self.seg = segmenter or Segmenter()
        self.jobs = queue.Queue(maxsize=4)
        self.expect_until, self.hold_until = 0.0, 0.0
        self.stamps = []
        self._stop = threading.Event()
        self.threads = []

    # ---- audio side: never blocks on the AI
    def read(self, chunks):
        try:
            for c in chunks:
                if self._stop.is_set():
                    break
                now = self.clock()
                if self.paused():
                    self.seg.reset()
                    self.hold_until = now + self.holdoff_s
                    continue
                if now < self.hold_until:
                    continue
                utt = self.seg.feed(c)
                if utt is not None:
                    try:
                        self.jobs.put_nowait(utt)
                    except queue.Full:
                        pass                                  # too busy: drop it rather than lag behind
        finally:
            close = getattr(chunks, "close", None)
            if close:
                close()

    # ---- text side
    def process(self, utt):
        secs = len(utt) / 2.0 / RATE
        now = self.clock()
        following = now < self.expect_until
        if secs > self.max_phrase_s and not following:
            return                                            # music, a video, a long chat: not a command
        self.stamps = [t for t in self.stamps if now - t < 60]
        if len(self.stamps) >= self.per_min:
            return
        self.stamps.append(now)
        try:
            text = self.whisper.transcribe(utt)
        except Exception as exc:
            self.emit("error", str(exc) or type(exc).__name__)
            return
        del utt
        matched, rest = strip_wake(text)
        if following and not matched:
            self.expect_until = 0.0
            self.emit("command", text)
        elif matched and rest:
            self.expect_until = 0.0
            self.emit("command", rest)
        elif matched:
            self.expect_until = self.clock() + self.follow_s
            self.emit("wake", "")
        # anything else was just talking: it is dropped here and never stored

    def work(self):
        while not self._stop.is_set():
            try:
                utt = self.jobs.get(timeout=0.3)
            except queue.Empty:
                continue
            self.process(utt)

    def start(self, chunk_source):
        """chunk_source() -> iterator of PCM chunks (opens the mic). Runs on two daemon threads."""
        self._stop.clear()

        def reader():
            try:
                self.read(chunk_source())
            except Exception as exc:
                self.emit("error", str(exc) or type(exc).__name__)
        self.threads = [threading.Thread(target=reader, daemon=True), threading.Thread(target=self.work, daemon=True)]
        for t in self.threads:
            t.start()

    def stop(self):
        self._stop.set()

    @property
    def running(self):
        return bool(self.threads) and self.threads[0].is_alive() and not self._stop.is_set()
