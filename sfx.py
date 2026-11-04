"""Tiny synthesized sound effects (no audio files needed). Pure Python, no Tk.

Jingles are generated once into WAV files in a cache folder and played with the OS audio player.
"""
import math
import os
import random
import struct
import wave

RATE = 22050
# name -> [(frequency_hz, milliseconds)], frequency 0 = silence, negative = noise burst
PATTERNS = {
    "blip": [(880, 40)],
    "click": [(1500, 14)],
    "confirm": [(660, 60), (880, 90)],
    "success": [(523, 70), (659, 70), (784, 70), (1047, 170)],
    "fail": [(247, 130), (185, 230)],
    "achievement": [(784, 80), (988, 80), (1175, 80), (1568, 240)],
    "alert": [(880, 90), (0, 50), (880, 90)],
    "glitch": [(-1, 70), (330, 40), (-1, 50)],
}


def synth(notes, vol=0.22, seed=1):
    """16-bit little-endian mono PCM for a list of (freq, ms) notes."""
    rnd = random.Random(seed)
    out = bytearray()
    for freq, ms in notes:
        n = int(RATE * ms / 1000.0)
        fade = max(1, min(n // 4, int(RATE * 0.008)))
        for i in range(n):
            if freq == 0:
                s = 0.0
            elif freq < 0:
                s = rnd.uniform(-1, 1)
            else:
                s = 1.0 if math.sin(2 * math.pi * freq * i / RATE) >= 0 else -1.0     # square wave
            edge = min(1.0, i / fade, (n - 1 - i) / fade) if n > 1 else 1.0            # no clicks at the ends
            out += struct.pack("<h", int(max(-1.0, min(1.0, s * edge)) * vol * 32767))
    return bytes(out)


def write_wav(path, notes):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(synth(notes))


class Sfx:
    def __init__(self, cache_dir, player, enabled=True, busy=lambda: False, log=None):
        self.cache_dir, self.player, self.enabled = cache_dir, player, enabled
        self.busy, self.log = busy, log or (lambda m: None)

    def path(self, name):
        p = os.path.join(self.cache_dir, name + ".wav")
        if not os.path.isfile(p):
            os.makedirs(self.cache_dir, exist_ok=True)
            tmp = p + ".part"
            write_wav(tmp, PATTERNS[name])
            os.replace(tmp, p)
        return p

    def play(self, name):
        """Play a sound effect. Silent if disabled, unknown, or she is speaking (so voice isn't cut off)."""
        if not self.enabled or name not in PATTERNS or self.busy():
            return False
        try:
            return self.player(self.path(name)) is not None
        except Exception as exc:                  # sound must never break the pet
            self.log("sfx failed: " + type(exc).__name__)
            return False
