"""Place narration clips at the times recorded in events.json -> stereo wav."""
import json
import sys
import wave

import numpy as np

VO_DIR = sys.argv[1]
OUT = sys.argv[2]
ev = json.load(open("events.json"))
SR = 48000
N = int((ev["total"] + 0.3) * SR)
mix = np.zeros(N)
for t, key in ev["vo"]:
    with wave.open(f"{VO_DIR}/{key}.wav") as w:
        assert w.getframerate() == SR
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768.0
    i = int(t * SR)
    j = min(N, i + len(x))
    mix[i:j] += x[: j - i]
    end = t + len(x) / SR
    print(f"{key:6s} {t:6.2f} -> {end:6.2f}")
mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
pcm = (mix * 32767).astype(np.int16)
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(np.stack([pcm, pcm], 1).tobytes())
