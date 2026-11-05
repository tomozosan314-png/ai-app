"""Render the protector-guide reel (1080x1920, 30fps) -> silent mp4 + sfx event list."""
import json
import math
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from fx import *  # noqa
from illus import kneeslide, shop_icon, coin, helmet, ng_mark, ok_mark, ff_badge

UP = "/root/.claude/uploads/4d0dac7b-7b1e-524e-acb0-cc9ba3078324/"
HOOK = UP + "95b265ae-IMG_5872.mov"      # kids drop + knee slide
KIDFALL = UP + "86d93044-IMG_7145.mov"   # night knee slide
ADULT = UP + "772db450-IMG_7159.mov"     # adult knee slide demo
SMALL = UP + "02e1da26-IMG_7157.mov"     # small pads on knees
BIG = UP + "fd9a5b7f-IMG_7157.mov"       # big hard-cap pads
SOFT = UP + "c89d510c-IMG_7163.mov"      # soft pad close-up (NG)
WRIST = UP + "8adbd52e-My_Movie_2.mov"   # wrist guard (landscape w/ pillarbox)

OUT = sys.argv[1] if len(sys.argv) > 1 else "video.mp4"
PREVIEW = "--preview" in sys.argv

CAP_BOTTOM = 1590   # captions are pinned to the lower area (above IG UI)
CAP_X = 530
CAP_W = 920

events = []  # (time, kind) for the audio pass


class Clip:
    def __init__(self, path, ss, dur, speed=1.0, crop=None, w=W, h=H, eq=True):
        self.n = int(round(dur / speed * FPS))
        vf = []
        if crop:
            vf.append(f"crop={crop}")
        vf.append(f"setpts=(PTS-STARTPTS)/{speed}")
        vf.append(f"fps={FPS}")
        vf.append(f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos")
        vf.append(f"crop={w}:{h}")
        if eq:
            vf.append("eq=saturation=1.18:contrast=1.04:brightness=0.015")
        self.w, self.h = w, h
        self.cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-t", str(dur), "-i", path,
                    "-an", "-vf", ",".join(vf), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = None
        self.last = None

    def next(self):
        if self.p is None:
            self.p = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
        size = self.w * self.h * 3
        buf = self.p.stdout.read(size)
        if len(buf) == size:
            self.last = Image.frombuffer("RGB", (self.w, self.h), buf, "raw", "RGB", 0, 1)
        return self.last.copy()


def card_bg(color, dot):
    img = Image.new("RGB", (W, H), color)
    d = ImageDraw.Draw(img)
    for yy in range(0, H + 60, 60):
        for xx in range(0 if (yy // 60) % 2 else 30, W + 60, 60):
            d.ellipse([xx - 7, yy - 7, xx + 7, yy + 7], fill=dot)
    # frame
    d.rounded_rectangle([28, 28, W - 28, H - 28], radius=50, outline=WHITE, width=14)
    return img


CREAM_BG = card_bg((255, 244, 220), (250, 228, 190))
MINT_BG = card_bg((212, 239, 233), (190, 228, 220))


def punch(img, t, amt=0.07, dur=0.3):
    k = 1 + amt * (1 - ease_out_cubic(t / dur))
    if k <= 1.001:
        return img
    cw, ch = int(W / k), int(H / k)
    x, y = (W - cw) // 2, (H - ch) // 2
    return img.crop((x, y, x + cw, y + ch)).resize((W, H), Image.BILINEAR)


def top_tag(img, t):
    pill(img, W / 2, 232, "子どものプロテクターの選び方", size=40, fg=BROWN,
         alpha=1.0, scale=1.0)


def L(segs, size=88, delay=0.0, marker=None):
    return dict(segs=segs, size=size, delay=delay, marker=marker)


def caption(img, t, lines, start=0.12, end=None, **kw):
    lines = [dict(l, size=int(l["size"] * 1.12)) for l in lines]
    draw_text_block(img, lines, t, start, CAP_X, cy_bottom=CAP_BOTTOM, maxw=CAP_W,
                    end=end, **kw)


def sticker(img, t, spr, cx, cy, start, rot=0, wobble=True, end=None):
    lt = t - start
    if lt < 0:
        return
    sc = ease_out_back(lt / 0.3, 2.6)
    r = rot + (3 * math.sin(lt * 6) if wobble else 0)
    a = 1.0
    if end is not None:
        a = 1 - clamp((t - (end - 0.15)) / 0.15)
    paste_scaled(img, spr, cx, cy, sc, a, r)


_text_spr_cache = {}


def text_sprite(text, size, color, rot=0):
    key = (text, size, color)
    if key not in _text_spr_cache:
        f = font(POP, size)
        sw = int(size * 0.16)
        w = int(f.getlength(text) + sw * 2 + 20)
        h = int(size * 1.5 + sw * 2)
        s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(s)
        d.text((sw + 10, sw + size * 0.15), text, font=f, fill=color, stroke_width=sw,
               stroke_fill=WHITE)
        _text_spr_cache[key] = s
    return _text_spr_cache[key]


def decor_stars(img, t, pts):
    d = ImageDraw.Draw(img)
    for (x, y, r, ph) in pts:
        rr = r * (1 + 0.15 * math.sin(t * 5 + ph))
        star(d, x, y, rr, 8, WHITE, rot=-90 + 10 * math.sin(t * 2 + ph))


# ---------------------------------------------------------------- scenes
scenes = []


def scene(dur, bg, *ov, punch_in=True, tag=True, sfx=None):
    scenes.append(dict(dur=dur, bg=bg, ov=ov, punch=punch_in, tag=tag, sfx=sfx or []))


# 1. Hook
c1 = Clip(HOOK, 2.6, 3.09)
scene(3.1, lambda t: c1.next(),
      lambda img, t: caption(img, t, [
          L([("プロテクター、", BLACK)], 96),
          L([("なんとなく", ORANGE, 1.1), ("で", BLACK), ("選んでない？", BLACK)], 84,
            delay=0.45, marker=YELLOW)]),
      lambda img, t: sticker(img, t, text_sprite("？", 200, CORAL), 900, 930, 1.0, rot=-12),
      sfx=[(0.12, "pop"), (0.57, "pop"), (1.0, "boing")])

# 2a. Mini-ramp falls
c2 = Clip(KIDFALL, 0.0, 2.45, speed=0.75)
scene(c2.n / FPS, lambda t: c2.next(),
      lambda img, t: caption(img, t, [
          L([("ミニランプ", ORANGE), ("特有の", BLACK)], 92),
          L([("転び方は…？", BLACK)], 92, delay=0.4)]),
      sfx=[(0.12, "pop"), (0.52, "pop")])

# 2b. Knee slide = fall onto knees
c3 = Clip(ADULT, 0.0, 2.4, speed=0.8)
scene(c3.n / FPS, lambda t: c3.next(),
      lambda img, t: sticker(img, t, text_sprite("ズザーッ！", 120, ORANGE), 560, 760, 0.25,
                             rot=-10),
      lambda img, t: caption(img, t, [
          L([("ニースライド", CORAL, 1.2)], 104, marker=YELLOW),
          L([("＝", BLACK), ("膝", ORANGE, 1.25), ("から転ぶ！", BLACK)], 92, delay=0.55)]),
      sfx=[(0.25, "whoosh"), (0.12, "pop"), (0.67, "pop")])

# 3. "Lifeline" text card (no illustration)
def s3_ov(img, t):
    d = ImageDraw.Draw(img)
    p = ease_out_back((t - 0.9) / 0.35)
    if p > 0:
        burst(d, W / 2, 1190, 400 * p, 470 * p, [188, 198, 208, -8, -18, -28], 16, ORANGE)
    decor_stars(img, t, [(150, 420, 44, 0), (930, 380, 38, 1.5), (140, 1500, 36, 3),
                         (940, 1460, 42, 2)])
    draw_text_block(img, [
        L([("だから", BLACK)], 110),
        L([("膝パッド", ORANGE), ("が", BLACK)], 150, delay=0.35),
        L([("“命綱”！", CORAL)], 200, delay=0.85, marker=YELLOW)],
        t, 0.1, W / 2, cy_top=540, maxw=960)


scene(3.4, lambda t: CREAM_BG.copy(), s3_ov,
      sfx=[(0.0, "whoosh"), (0.1, "pop"), (0.45, "pop"), (0.95, "boing")], tag=False)

# 4a. Split comparison
c4l = Clip(SMALL, 2.0, 2.6, w=540, h=H, crop="540:1920:216:0")
c4r = Clip(BIG, 0.7, 1.35, speed=0.5, w=540, h=H, crop="540:1920:120:0")


def split_bg(t):
    img = Image.new("RGB", (W, H))
    img.paste(c4l.next(), (0, 0))
    img.paste(c4r.next(), (540, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([534, 0, 546, H], fill=WHITE)
    return img


def s4a_ov(img, t):
    if t > 0.15:
        pill(img, 270, 420, "小さめ", size=54, fg=WHITE, bg=(120, 120, 130), border=WHITE,
             scale=ease_out_back((t - 0.15) / 0.3))
    if t > 0.55:
        pill(img, 810, 420, "しっかり", size=54, fg=WHITE, bg=ORANGE, border=WHITE,
             scale=ease_out_back((t - 0.55) / 0.3))
    caption(img, t, [L([("比べてみると…", BLACK)], 96)], start=0.9)


scene(2.8, split_bg, s4a_ov, sfx=[(0.15, "pop"), (0.55, "pop"), (0.9, "pop")])

# 4b. Good pads close
c5 = Clip(BIG, 0.7, 1.35, speed=0.37, crop="760:1351:10:200")
scene(c5.n / FPS, lambda t: c5.next(),
      lambda img, t: sticker(img, t, ok_mark(200), 900, 420, 0.3, rot=0),
      lambda img, t: caption(img, t, [
          L([("厚め", ORANGE), ("・", BLACK), ("ハードキャップ", ORANGE), ("！", BLACK)], 92,
            marker=YELLOW),
          L([("覆う部分が", BLACK)], 84, delay=1.1),
          L([("大きい", CORAL, 1.15), ("ものが", BLACK), ("安心", CORAL, 1.15)], 84, delay=1.4)]),
      sfx=[(0.12, "pop"), (0.3, "ding"), (1.22, "pop"), (1.52, "pop")])

# 5. NG example
c6 = Clip(SOFT, 0.0, 2.25, speed=0.5)


def s5_ov(img, t):
    sticker(img, t, ng_mark(300), 820, 560, 0.25, rot=0, wobble=False)
    if t > 0.25:
        pill(img, 820, 760, "NG", size=60, fg=WHITE, bg=CORAL, border=WHITE,
             scale=ease_out_back((t - 0.35) / 0.3))
    caption(img, t, [
        L([("柔らかくて", BLACK), ("小さい", CORAL), ("タイプは", BLACK)], 84),
        L([("お勧めしません！", CORAL)], 100, delay=0.5, marker=YELLOW)], end=2.4)
    caption(img, t, [
        L([("安くても", BLACK), ("弱い", ORANGE), ("と", BLACK)], 92),
        L([("守れない。", CORAL)], 120, delay=0.45, marker=YELLOW)], start=2.45)


scene(c6.n / FPS, lambda t: c6.next(), s5_ov,
      sfx=[(0.12, "pop"), (0.25, "buzz"), (0.62, "pop"), (2.45, "pop"), (2.9, "pop")])

# 6. Wrist guard (fast-forward)
c7 = Clip(WRIST, 0.0, 11.2, speed=2.5, crop="608:1080:656:0")
FF = ff_badge()
scene(c7.n / FPS, lambda t: c7.next(),
      lambda img, t: sticker(img, t, FF, 840, 380, 0.1, wobble=False),
      lambda img, t: caption(img, t, [
          L([("肘", ORANGE, 1.15), ("・", BLACK), ("手首", ORANGE, 1.15), ("も", BLACK)], 96),
          L([("セットで", BLACK), ("安心！", CORAL, 1.15)], 96, delay=0.45, marker=YELLOW)],
          start=0.35),
      sfx=[(0.1, "whoosh"), (0.35, "pop"), (0.8, "pop")])

# 7. Where to buy (card)
ICONS = [shop_icon(k, 150).resize((180, 180), Image.LANCZOS) for k in range(3)]
ROWS = ["プロショップ", "大型\nスポーツショップ", "ネットフリマ"]
ROW_COL = [CORAL, (70, 150, 230), (60, 180, 120)]
ROW_T = [1.0, 1.8, 2.6]


def row_card(i):
    w, h = 920, 250
    s = Image.new("RGBA", (w + 20, h + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle([10, 18, w + 10, h + 18], radius=50, fill=(200, 160, 110, 120))
    d.rounded_rectangle([6, 6, w + 6, h + 6], radius=50, fill=WHITE, outline=BROWN, width=6)
    cx, cy = 100, h / 2 + 6
    d.ellipse([cx - 64, cy - 64, cx + 64, cy + 64], fill=ROW_COL[i], outline=BROWN, width=5)
    d.text((cx, cy + 2), str(i + 1), font=font(POP, 78), fill=WHITE, anchor="mm")
    s.alpha_composite(ICONS[i], (185, int(cy - 90)))
    parts = ROWS[i].split("\n")
    if len(parts) == 1:
        items, tw, sz = layout_line([(parts[0], BLACK)], 84, 530)
        d.text((385, cy + 4), parts[0], font=font(POP, sz), fill=BLACK, anchor="lm")
    else:
        d.text((385, cy - 40), parts[0], font=font(POP, 62), fill=BLACK, anchor="lm")
        items, tw, sz = layout_line([(parts[1], BLACK)], 72, 530)
        d.text((385, cy + 42), parts[1], font=font(POP, sz), fill=BLACK, anchor="lm")
    return s


ROW_SPR = [row_card(i) for i in range(3)]


def s7_ov(img, t):
    d = ImageDraw.Draw(img)
    p = ease_out_back(t / 0.4)
    if p > 0:
        burst(d, W / 2, 400, 330 * p, 400 * p, [190, 205, 220, -10, -25, -40], 14, ORANGE)
    draw_text_block(img, [
        L([("買う場所は", BLACK), ("3つ", CORAL, 1.45)], 120, marker=YELLOW)],
        t, 0.1, W / 2, cy_top=310, maxw=920)
    for i in range(3):
        lt = t - ROW_T[i]
        if lt < 0:
            continue
        e = ease_out_back(lt / 0.42, 1.8)
        x = W / 2 + (1 - e) * 700
        paste_scaled(img, ROW_SPR[i], x, 820 + i * 330, 1.0, clamp(lt / 0.12))
    decor_stars(img, t, [(130, 1720, 40, 0), (950, 1740, 34, 2)])


scene(5.4, lambda t: CREAM_BG.copy(), s7_ov, tag=False,
      sfx=[(0.0, "whoosh"), (0.1, "pop")] + [(x, "ding") for x in ROW_T])

# 8. You don't need to spend much (card)
COIN = coin(72)
random.seed(4)
COINS = [(random.uniform(150, 930), random.uniform(1.3, 2.2), random.uniform(-30, 30),
          random.uniform(1380, 1560)) for _ in range(9)]


def s8_ov(img, t):
    for (x, t0, rot, ground) in COINS:
        lt = t - t0
        if lt < 0:
            continue
        # fall then bounce
        y0 = -100
        g = 5200
        tf = math.sqrt(2 * (ground - y0) / g)
        if lt < tf:
            y = y0 + 0.5 * g * lt * lt
        else:
            u = lt - tf
            v = 0.45 * g * tf
            y = ground - max(0, v * u - 0.5 * g * u * u)
            if v * u - 0.5 * g * u * u < 0:
                y = ground
        paste_scaled(img, COIN, x, y, 1.0, 1.0, rot + lt * 60 * (1 if lt < tf else 0))
    draw_text_block(img, [L([("でも、", BLACK)], 120)], t, 0.1, W / 2, cy_top=360, maxw=900,
                    anim="drop")
    draw_text_block(img, [
        L([("お金", ORANGE, 1.15), ("をかける", BLACK)], 104),
        L([("必要は", BLACK)], 104, delay=0.3),
        L([("ありません！", CORAL)], 150, delay=0.7, marker=YELLOW)],
        t, 0.55, W / 2, cy_top=620, maxw=940)
    decor_stars(img, t, [(140, 330, 42, 0), (950, 420, 36, 1), (930, 1200, 30, 2)])


scene(4.2, lambda t: MINT_BG.copy(), s8_ov, tag=False,
      sfx=[(0.0, "whoosh"), (0.1, "pop"), (0.55, "pop"), (0.85, "pop"), (1.25, "boing")]
      + [(c[1] + 0.3, "coin") for c in COINS[::2]])

# 9. Closing
c9 = Clip(HOOK, 3.6, 2.09, speed=0.5)
scene(c9.n / FPS, lambda t: c9.next(),
      lambda img, t: caption(img, t, [
          L([("プロテクターは、", BLACK)], 88),
          L([("思いきり", ORANGE, 1.15), ("練習するための", BLACK)], 84, delay=0.45),
          L([("道具！", CORAL)], 140, delay=1.0, marker=YELLOW)]),
      lambda img, t: decor_stars(img, t, [(150, 1000, 38, 0), (930, 960, 32, 2)])
      if t > 1.3 else None,
      sfx=[(0.12, "pop"), (0.57, "pop"), (1.12, "boing")])

# 10. Next time: helmet
HELM = helmet(440)


def s10_ov(img, t):
    d = ImageDraw.Draw(img)
    lt = t - 0.15
    if lt > 0:
        y = 760 - 40 * abs(math.sin(lt * 4)) * max(0, 1 - lt / 2)
        paste_scaled(img, HELM, W / 2, y, ease_out_back(lt / 0.4, 2.0), 1.0,
                     4 * math.sin(lt * 3))
        burst(d, W / 2, 760, 270, 340, [200, 220, 240, -20, -40, -60, 300, 320, 340], 12, YELLOW)
    pill(img, W / 2, 380, "次回予告", size=60, fg=WHITE, bg=NAVY, border=WHITE,
         scale=ease_out_back(t / 0.3))
    draw_text_block(img, [
        L([("ヘルメット", CORAL), ("編", BLACK)], 140, marker=YELLOW),
        L([("お楽しみに！", ORANGE)], 100, delay=0.4)],
        t, 0.5, W / 2, cy_top=1060, maxw=940)
    if t > 1.3:
        pill(img, W / 2, 1520, "フォローして待っててね", size=50, fg=BROWN,
             scale=ease_out_back((t - 1.3) / 0.35))
    decor_stars(img, t, [(160, 560, 40, 0), (930, 560, 36, 1.5)])


scene(3.4, lambda t: CREAM_BG.copy(), s10_ov, tag=False,
      sfx=[(0.0, "whoosh"), (0.15, "boing"), (0.5, "pop"), (0.9, "pop"), (1.3, "ding")])

# ---------------------------------------------------------------- render
total = sum(s["dur"] for s in scenes)
print(f"scenes={len(scenes)} total={total:.2f}s", file=sys.stderr)

enc = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
     "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
     "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)

T = 0.0
preview_frames = []
for si, sc in enumerate(scenes):
    nf = int(round(sc["dur"] * FPS))
    for (st, kind) in sc["sfx"]:
        events.append((round(T + st, 3), kind))
    for i in range(nf):
        t = i / FPS
        bg = sc["bg"](t)
        if sc["punch"]:
            bg = punch(bg, t)
        img = bg.convert("RGBA")
        if sc["tag"]:
            top_tag(img, t)
        for ov in sc["ov"]:
            ov(img, t)
        out = img.convert("RGB")
        enc.stdin.write(out.tobytes())
        if PREVIEW and i == int(nf * 0.85):
            out.resize((360, 640)).save(f"prev_{si:02d}.jpg")
    T += nf / FPS
    print(f"scene {si} done t={T:.2f}", file=sys.stderr)

enc.stdin.close()
enc.wait()
json.dump(dict(total=T, events=sorted(events)), open("events.json", "w"))
