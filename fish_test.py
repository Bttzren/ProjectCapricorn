#!/usr/bin/env python3
"""Checks Capri's Fish Audio voice step by step and tells you exactly what's wrong.

Run:   py fish_test.py YOUR_FISH_KEY          (or set FISH_API_KEY first)
"""
import json
import os
import sys
import urllib.error
import urllib.request
import wave

import voice

key = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FISH_API_KEY", "")).strip()
if len(key) < 16:
    sys.exit("Give me your Fish Audio key:  py fish_test.py YOUR_KEY")
text = "Hey choom. It's me, Capri. Can you hear me?"
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fish_test.wav")
print(f"1. Key looks right ({len(key)} characters, starts '{key[:4]}...')")
print(f"2. Asking Fish Audio ({voice.FISH_URL}) for voice {voice.DEFAULT_FISH_VOICE} ...")

data = None
for label, model in (("model header 's1'", "s1"), ("model header 'speech-1.6'", "speech-1.6"),
                     ("model header 'speech-1.5'", "speech-1.5"), ("no model header", None)):
    body = json.dumps({"text": text, "reference_id": voice.DEFAULT_FISH_VOICE, "format": "wav",
                       "normalize": True, "latency": "normal"}).encode()
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if model:
        headers["model"] = model
    req = urllib.request.Request(voice.FISH_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            print(f"   OK with {label}: HTTP {r.status}, {len(data)} bytes, type {r.headers.get('Content-Type')}")
            break
    except urllib.error.HTTPError as e:
        print(f"   FAILED with {label}: HTTP {e.code} -> {e.read()[:300]!r}")
        if e.code in (401, 402, 403, 404, 429):
            break
    except urllib.error.URLError as e:
        sys.exit(f"   Can't reach Fish Audio: {e.reason}\n   Check your internet / firewall / antivirus.")
if data is None:
    sys.exit("\nNo audio came back. Send me the FAILED lines above.")

print(f"3. Got {len(data)} bytes; first bytes: {data[:12]!r}")
if data[:4] != b"RIFF":
    sys.exit("   That is not a WAV file. Send me the line above.")
open(out, "wb").write(data)
try:
    with wave.open(out, "rb") as w:
        print(f"4. WAV: {w.getnchannels()} channel(s), {w.getframerate()} Hz, {8 * w.getsampwidth()}-bit, "
              f"{w.getnframes() / w.getframerate():.1f}s  (saved to {out})")
except wave.Error as e:
    print(f"4. Python can't read this WAV ({e}). Windows' player may refuse it too. Send me this line.")

print("5. Playing it now - listen...")
res = voice.play_file(out)
if res is None:
    print("   No audio player worked here. Open fish_test.wav yourself to check that the voice is right.")
else:
    import time
    time.sleep((res[1] or 3) + 0.5)
    print("   Done. If you heard her: the voice works and the problem is inside the app - send me capri.log.")
    print("   If you heard nothing: check Windows volume/output device, then open fish_test.wav manually.")
