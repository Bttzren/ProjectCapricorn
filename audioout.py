"""Play her voice into a call (pure logic + sounddevice/av, no Tk).

A voice call hears your microphone, so to let friends hear HER she plays into a virtual audio cable
(free: "VB-Audio Virtual Cable" on Windows, BlackHole on a Mac) and the call app uses that cable's output as its
microphone. She also plays on your normal speakers so you hear her too.
"""
import re
import threading
import time

CABLE_HINTS = ("cable input", "vb-audio virtual", "voicemeeter input", "voicemeeter aux input", "hi-fi cable input",
               "blackhole", "virtual cable")
AVOID = re.compile(r"output|monitor|capture|microphone|mic\b", re.I)


def find_cable(devices):
    """Index of the best virtual-cable OUTPUT device in sounddevice's device list, or None."""
    best, best_rank = None, 99
    for i, d in enumerate(devices):
        name = str(d.get("name", "")).lower()
        if d.get("max_output_channels", 0) < 1:
            continue
        for rank, hint in enumerate(CABLE_HINTS):
            if hint in name and not (hint != "cable input" and AVOID.search(name) and "input" not in name):
                if rank < best_rank:
                    best, best_rank = i, rank
                break
    return best


def decode(path, rate, channels=2, gain=0.9):
    """The audio file as float32 samples shaped (frames, channels), resampled to `rate`. Needs `av` and numpy."""
    import av
    import numpy as np
    layout = "stereo" if channels >= 2 else "mono"
    out = []
    with av.open(path) as container:
        resampler = av.AudioResampler(format="flt", layout=layout, rate=rate)
        for frame in container.decode(audio=0):
            for f in resampler.resample(frame):
                out.append(f.to_ndarray())
        for f in resampler.resample(None) or []:
            out.append(f.to_ndarray())
    if not out:
        raise RuntimeError("that audio file was empty")
    data = np.concatenate(out, axis=1)                        # planar-or-packed: (channels or 1, frames)
    if data.shape[0] == 1 and channels >= 2 and data.size % channels == 0 and layout == "stereo":
        data = data.reshape(-1, channels).T                   # packed stereo came back as one row
    return (data.T * gain).astype("float32")


class Player:
    """Plays an audio file on several output devices at once. play() returns the length in seconds right away."""

    def __init__(self, sd=None, decoder=decode, log=lambda m: None, chunk=2048):
        self._sd, self.decoder, self.log, self.chunk = sd, decoder, log, chunk
        self._stop = threading.Event()
        self.threads = []

    @property
    def sd(self):
        if self._sd is None:
            import sounddevice
            self._sd = sounddevice
        return self._sd

    def devices(self):
        return [dict(d) for d in self.sd.query_devices()]

    def cable(self):
        try:
            return find_cable(self.devices())
        except Exception as exc:
            self.log(f"audio devices unavailable: {type(exc).__name__}")
            return None

    def default_output(self):
        try:
            idx = self.sd.default.device[1]
            return idx if idx is not None and idx >= 0 else None
        except Exception:
            return None

    def play(self, path, device_ids):
        """Start playing on every device in `device_ids` (duplicates removed). Returns seconds."""
        self.stop()
        self._stop.clear()
        ids = [i for n, i in enumerate(device_ids) if i is not None and i not in device_ids[:n]]
        if not ids:
            raise RuntimeError("no audio output to play on")
        longest = 0.0
        jobs = []
        for i in ids:
            info = self.sd.query_devices(i)
            rate = int(info.get("default_samplerate", 48000))
            ch = max(1, min(2, int(info.get("max_output_channels", 2))))
            data = self.decoder(path, rate, ch)
            longest = max(longest, len(data) / float(rate))
            jobs.append((i, rate, ch, data))
        self.threads = []
        for i, rate, ch, data in jobs:
            t = threading.Thread(target=self._write, args=(i, rate, ch, data), daemon=True)
            self.threads.append(t)
            t.start()
        return longest

    def _write(self, device, rate, ch, data):
        try:
            with self.sd.OutputStream(device=device, samplerate=rate, channels=ch, dtype="float32") as stream:
                for k in range(0, len(data), self.chunk):
                    if self._stop.is_set():
                        break
                    stream.write(data[k:k + self.chunk])
        except Exception as exc:
            self.log(f"playing on device {device} failed: {type(exc).__name__}: {str(exc)[:80]}")

    def stop(self):
        self._stop.set()

    @property
    def busy(self):
        return any(t.is_alive() for t in self.threads)


def call_player(player, cable_id, also_speakers=True, clock=time.time):
    """A function for Speaker.call_player: file path -> (None, seconds). Plays into the cable (and the speakers)."""
    def play(path):
        ids = [cable_id] + ([player.default_output()] if also_speakers else [])
        secs = player.play(path, ids)
        return None, secs
    return play
