"""Synthesise narration lines (Open JTalk, Mei voice) and write timing.json."""
import json
import os
import sys
import wave

import numpy as np
import pyopenjtalk

OUT = sys.argv[1] if len(sys.argv) > 1 else "vo"
SPEED, PITCH = 1.22, 1.5

# key -> narration (kana spelling where the reading must be forced)
LINES = {
    "hook": "プロテクター、なんとなくで、選んでない？",
    "ramp": "ミニランプ特有の、転び方は？",
    "knee": "ニースライド。ひざから転ぶ！",
    "life": "だから、ひざパッドが、命綱！",
    "cmp": "比べてみると、",
    "hard": "厚め、ハードキャップ！",
    "cover": "覆う部分が大きいものが、安心。",
    "ng1": "柔らかくて小さいタイプは、おすすめしません！",
    "ng2": "安くても弱いと、守れない。",
    "wr1": "ひじ、手首も、セットで安心！",
    "wr2": "かたい方を、手のひらにしてね！",
    "buy": "買う場所は、4つ。",
    "b1": "プロショップ、",
    "b2": "大型スポーツショップ、",
    "b3": "ネット通販、",
    "b4": "ネットフリマ。",
    "money": "でも、お金をかける必要は、ありません！",
    "end1": "プロテクターは、思いきり、",
    "end2": "練習するための、道具！",
    "next": "次回は、ヘルメット編。お楽しみに！",
    "dm": "分からないことがあれば、コメント、ディーエム、お待ちしてます！",
}

os.makedirs(OUT, exist_ok=True)
timing = {}
for k, text in LINES.items():
    x, sr = pyopenjtalk.tts(text, speed=SPEED, half_tone=PITCH)
    x = x / (np.abs(x).max() + 1e-9)
    # trim leading/trailing silence
    idx = np.where(np.abs(x) > 0.02)[0]
    x = x[max(0, idx[0] - int(0.02 * sr)): idx[-1] + int(0.06 * sr)]
    pcm = (x * 0.9 * 32767).astype(np.int16)
    with wave.open(f"{OUT}/{k}.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    timing[k] = round(len(x) / sr, 3)
    print(k, timing[k], pyopenjtalk.g2p(text, kana=True))
json.dump(timing, open(f"{OUT}/timing.json", "w"), ensure_ascii=False, indent=1)
