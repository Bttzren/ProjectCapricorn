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
FILLER = re.compile(r"^(can you|could you|please|would you|go ahead and|just|for me)\s+", re.I)


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
    words = re.findall(r"[a-z']+", low)
    first = words[0] if words else ""
    second = words[1] if len(words) > 1 else ""
    is_task = first in TASK_WORDS and not (first == "tell" and second in ("me", "us", "you")) \
        and not (first == "go" and second != "to") and not (first == "start" and second in ("to", "feeling"))
    return ("task", t[0].upper() + t[1:]) if is_task else ("chat", t)


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
