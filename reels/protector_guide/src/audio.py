"""Synthesise a light pop BGM + cute SFX matched to events.json."""
import json
import sys
import wave

import numpy as np

SR = 44100
ev = json.load(open("events.json"))
N = int((ev["total"] + 0.5) * SR)
with_bgm = "--no-bgm" not in sys.argv
out_path = sys.argv[1]
rng = np.random.default_rng(1)


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def tone(f, dur, kind="tri", a=0.005, d=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(f, n) if np.ndim(f) else np.full(n, f)) / SR
    if kind == "sine":
        w = np.sin(ph)
    elif kind == "tri":
        w = 2 / np.pi * np.arcsin(np.sin(ph))
    else:  # soft square
        w = np.tanh(3 * np.sin(ph))
    return w * env(n, a, d)


def sfx(kind):
    if kind == "pop":
        n = int(0.09 * SR)
        f = np.linspace(500, 1300, n)
        return 0.5 * tone(f, 0.09, "sine", 0.002, 0.03)
    if kind == "boing":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        f = 300 + 250 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 6) + 200 * t
        return 0.45 * tone(f, 0.35, "tri", 0.003, 0.12)
    if kind == "ding":
        return 0.35 * (tone(1568, 0.6, "sine", 0.002, 0.18) + 0.5 * tone(2349, 0.6, "sine", 0.002, 0.12))
    if kind == "coin":
        a = tone(1976, 0.08, "sq", 0.001, 0.05)
        b = tone(2637, 0.35, "sq", 0.001, 0.12)
        return 0.16 * np.concatenate([a, b])
    if kind == "buzz":
        return 0.28 * tone(140, 0.4, "sq", 0.005, 0.25)
    if kind == "whoosh":
        n = int(0.35 * SR)
        noise = rng.standard_normal(n)
        # crude band sweep via moving average of varying length
        out = np.convolve(noise, np.ones(8) / 8, mode="same")
        t = np.arange(n) / SR
        e = np.sin(np.pi * np.clip(t / 0.35, 0, 1)) ** 2
        return 0.22 * out * e
    return np.zeros(1)


mix = np.zeros(N)
for t, k in ev["events"]:
    s = sfx(k)
    i = int(t * SR)
    j = min(N, i + len(s))
    mix[i:j] += s[: j - i]

if with_bgm:
    bpm = 124
    beat = 60 / bpm
    # I - V - vi - IV in C major, bouncy
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    bass = [36, 31, 33, 29]
    mel = [76, 79, 76, 74, 72, 74, 76, 79, 74, 71, 74, 79, 77, 76, 74, 72,
           72, 76, 79, 81, 79, 76, 72, 76, 77, 76, 74, 72, 74, 72, 71, 67]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    music = np.zeros(N)
    nbeats = int(ev["total"] / beat) + 2
    for b in range(nbeats):
        t0 = b * beat
        ci = (b // 4) % 4
        i = int(t0 * SR)
        def add(sig, at=i, g=1.0):
            j = min(N, at + len(sig))
            if at < N:
                music[at:j] += g * sig[: j - at]
        # kick on 1 & 3, snare-ish clap on 2 & 4
        if b % 2 == 0:
            n = int(0.18 * SR); tt = np.arange(n) / SR
            add(np.sin(2 * np.pi * np.cumsum(120 * np.exp(-tt * 25) + 45) / SR) * np.exp(-tt * 18), g=0.5)
        else:
            n = int(0.12 * SR)
            add(rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 30), g=0.12)
        # hats on off-beats
        n = int(0.04 * SR)
        hat = np.diff(rng.standard_normal(n + 1)) * np.exp(-np.arange(n) / SR * 90)
        add(hat, at=int((t0 + beat / 2) * SR), g=0.05)
        # bass
        add(tone(hz(bass[ci]), beat * 0.9, "tri", 0.005, 0.25), g=0.32)
        add(tone(hz(bass[ci] + 12), beat * 0.45, "tri", 0.005, 0.1),
            at=int((t0 + beat / 2) * SR), g=0.18)
        # chord stabs on off-beats
        for m in chords[ci]:
            add(tone(hz(m), 0.2, "sq", 0.004, 0.07), at=int((t0 + beat / 2) * SR), g=0.045)
        # melody (8th-notes every other bar for breathing room)
        for h in range(2):
            idx = (b * 2 + h) % len(mel)
            if (b // 8) % 2 == 1 or h == 0:
                add(tone(hz(mel[idx]), beat / 2, "tri", 0.004, 0.12),
                    at=int((t0 + h * beat / 2) * SR), g=0.10)
    # fade in/out
    fade = np.ones(N)
    fi, fo = int(0.3 * SR), int(1.5 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    mix += music * fade * 0.8

peak = np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix / peak * 1.3) * 0.85
pcm = (mix * 32767).astype(np.int16)
st = np.stack([pcm, pcm], 1)
with wave.open(out_path, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(st.tobytes())
print("ok", len(ev["events"]), "events")
