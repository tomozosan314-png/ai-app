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
VO_DIR = "/tmp/claude-0/-home-user-ai-app/4d0dac7b-7b1e-524e-acb0-cc9ba3078324/scratchpad/vo"
VO = json.load(open(VO_DIR + "/timing.json"))  # narration line lengths (s)
vo_events = []
PREVIEW = "--preview" in sys.argv

CAP_BOTTOM = 1590   # captions are pinned to the lower area (above IG UI)
CAP_X = 540
CAP_W = 980

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


def _title_telop():
    """Big title telop shown only on the opening hook."""
    w, h = 1000, 330
    s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    # main banner
    bx0, by0, bx1, by1 = 20, 95, w - 20, 265
    d.rounded_rectangle([bx0 + 8, by0 + 12, bx1 + 8, by1 + 12], radius=36, fill=(60, 30, 15, 120))
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=36, fill=ORANGE, outline=WHITE, width=10)
    f = font(GOTH, 96)
    txt = "プロテクターの選び方"
    tw = f.getlength(txt)
    if tw > bx1 - bx0 - 50:
        f = font(GOTH, int(96 * (bx1 - bx0 - 50) / tw))
    d.text(((bx0 + bx1) / 2, (by0 + by1) / 2 + 4), txt, font=f, fill=WHITE, anchor="mm",
           stroke_width=6, stroke_fill=BROWN)
    # small tab on top-left
    f2 = font(GOTH, 58)
    tab = "子どもの"
    tw2 = f2.getlength(tab)
    tx0, ty0 = 60, 18
    d.rounded_rectangle([tx0, ty0, tx0 + tw2 + 60, ty0 + 96], radius=26, fill=NAVY,
                        outline=WHITE, width=8)
    d.text((tx0 + 30 + tw2 / 2, ty0 + 50), tab, font=f2, fill=WHITE, anchor="mm")
    return s


TITLE = _title_telop()


def top_tag(img, t):
    sc = ease_out_back(t / 0.35, 1.6)
    paste_scaled(img, TITLE, W / 2, 330, sc, clamp(t / 0.1), -2)


def L(segs, size=88, delay=0.0, marker=None):
    return dict(segs=segs, size=size, delay=delay, marker=marker)


def caption(img, t, lines, start=0.12, end=None, **kw):
    lines = [dict(l) for l in lines]
    draw_text_block(img, lines, t, start, CAP_X, cy_bottom=CAP_BOTTOM, maxw=CAP_W,
                    end=end, scale=0.8, **kw)


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
        items, w, sz = layout_line([(text, color)], size, 2000)
        pad = int(size * 0.5)
        s = Image.new("RGBA", (int(w + pad * 2), int(size * 1.6 + pad)), (0, 0, 0, 0))
        for layer in (0, 1):
            for ch, cs, col, x in items:
                o, f, gp, adv = glyph(ch, cs, col)
                spr = f if layer else o
                s.alpha_composite(spr, (int(pad + x + adv / 2 - spr.width / 2),
                                        int(s.height / 2 - spr.height / 2)))
        _text_spr_cache[key] = s
    return _text_spr_cache[key]


def decor_stars(img, t, pts):
    d = ImageDraw.Draw(img)
    for (x, y, r, ph) in pts:
        rr = r * (1 + 0.15 * math.sin(t * 5 + ph))
        star(d, x, y, rr, 8, WHITE, rot=-90 + 10 * math.sin(t * 2 + ph))


# ---------------------------------------------------------------- scenes
scenes = []


def scene(dur, bg, *ov, punch_in=True, tag=False, sfx=None, vo=None):
    scenes.append(dict(dur=dur, bg=bg, ov=ov, punch=punch_in, tag=tag, sfx=sfx or [],
                       vo=vo or []))


# 1. Hook
d1 = 0.15 + VO["hook"] + 0.3
c1 = Clip(HOOK, 3.0, 2.6, speed=2.6 / d1)
scene(c1.n / FPS, lambda t: c1.next(),
      lambda img, t: caption(img, t, [
          L([("プロテクター、", BLACK)], 140),
          L([("なんとなく", ORANGE), ("で", BLACK)], 150, delay=0.25),
          L([("選んでない？", BLACK)], 150,
            delay=0.45, marker=YELLOW)]),
      lambda img, t: sticker(img, t, text_sprite("？", 200, CORAL), 890, 740, 0.8, rot=-12),
      sfx=[(0.12, "pop"), (0.57, "pop"), (1.0, "boing")], tag=True, vo=[(0.15, "hook")])

# 2a. Mini-ramp falls
c2 = Clip(KIDFALL, 0.0, 2.45, speed=2.45 / (0.1 + VO["ramp"] + 0.25))
scene(c2.n / FPS, lambda t: c2.next(),
      lambda img, t: caption(img, t, [
          L([("ミニランプ", ORANGE)], 160),
          L([("特有の", BLACK)], 150, delay=0.2),
          L([("転び方は…？", BLACK)], 150, delay=0.4)]),
      sfx=[(0.12, "pop"), (0.52, "pop")], vo=[(0.1, "ramp")])

# 2b. Knee slide = fall onto knees
c3 = Clip(ADULT, 0.0, 2.4, speed=2.4 / (0.1 + VO["knee"] + 0.3))
scene(c3.n / FPS, lambda t: c3.next(),
      lambda img, t: sticker(img, t, text_sprite("ズザーッ！", 120, ORANGE), 560, 760, 0.25,
                             rot=-10),
      lambda img, t: caption(img, t, [
          L([("ニースライド", CORAL)], 155, marker=YELLOW),
          L([("＝", BLACK), ("膝", ORANGE), ("から転ぶ！", BLACK)], 140, delay=0.35)]),
      sfx=[(0.25, "whoosh"), (0.12, "pop"), (0.67, "pop")], vo=[(0.1, "knee")])

# 3. "Lifeline" text card (no illustration)
def s3_ov(img, t):
    d = ImageDraw.Draw(img)
    p = ease_out_back((t - 0.6) / 0.35)
    if p > 0:
        burst(d, W / 2, 1150, 475 * p, 530 * p, [188, 198, 208, -8, -18, -28], 16, ORANGE)
    decor_stars(img, t, [(150, 420, 44, 0), (930, 380, 38, 1.5), (140, 1500, 36, 3),
                         (940, 1460, 42, 2)])
    draw_text_block(img, [
        L([("だから", BLACK)], 150),
        L([("膝パッド", ORANGE), ("が", BLACK)], 175, delay=0.2),
        L([("“命綱”！", CORAL)], 215, delay=0.55, marker=YELLOW)],
        t, 0.1, W / 2, cy_top=580, maxw=980, scale=0.88)


scene(0.1 + VO["life"] + 0.3, lambda t: CREAM_BG.copy(), s3_ov, vo=[(0.1, "life")],
      sfx=[(0.0, "whoosh"), (0.1, "pop"), (0.45, "pop"), (0.95, "boing")], tag=False)

# 4a. Split comparison
c4l = Clip(SMALL, 2.4, 2.1, w=540, h=H, crop="540:1920:216:0")
c4r = Clip(BIG, 0.7, 1.35, speed=0.65, w=540, h=H, crop="540:1920:120:0")


def split_bg(t):
    img = Image.new("RGB", (W, H))
    img.paste(c4l.next(), (0, 0))
    img.paste(c4r.next(), (540, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([534, 0, 546, H], fill=WHITE)
    return img


def s4a_ov(img, t):
    sc = 0.9 + 0.1 * ease_out_back(t / 0.3)
    pill(img, 270, 330, "小さめ", size=70, fg=WHITE, bg=(120, 120, 130), border=WHITE,
         scale=sc)
    pill(img, 810, 292, "しっかり", size=76, fg=WHITE, bg=ORANGE, border=WHITE, scale=sc,
         pady=44)
    caption(img, t, [L([("比べて", BLACK)], 155),
                     L([("みると…", BLACK)], 155, delay=0.15)], start=0.45)


scene(max(2.0, 0.45 + VO["cmp"] + 0.3), split_bg, s4a_ov, vo=[(0.45, "cmp")])

# 4b. Good pads close
OKM = ok_mark(360, 40)
T5B = 0.1 + VO["hard"] + 0.1
c5 = Clip(BIG, 0.7, 1.35, speed=1.35 / (T5B + VO["cover"] + 0.3), crop="760:1351:10:200")
scene(c5.n / FPS, lambda t: c5.next(),
      lambda img, t: sticker(img, t, OKM, 860, 560, 0.3, rot=0),
      lambda img, t: (pill(img, 540, 150, "しっかり", size=82, fg=WHITE, bg=ORANGE, border=WHITE,
                           scale=0.9 + 0.1 * ease_out_back(t / 0.3)),
                      pill(img, 540, 282, "おすすめ！", size=66, fg=WHITE, bg=(60, 190, 120),
                           border=WHITE, scale=0.9 + 0.1 * ease_out_back(t / 0.3))),
      lambda img, t: caption(img, t, [
          L([("厚め", ORANGE), ("・", BLACK)], 160),
          L([("ハードキャップ", ORANGE), ("！", BLACK)], 125, delay=0.2, marker=YELLOW)],
          end=T5B - 0.03),
      lambda img, t: caption(img, t, [
          L([("覆う部分が", BLACK)], 155),
          L([("大きい", CORAL), ("ものが", BLACK)], 150, delay=0.2),
          L([("安心", CORAL)], 185, delay=0.4, marker=YELLOW)], start=T5B),
      vo=[(0.1, "hard"), (T5B, "cover")],
      sfx=[(0.12, "pop"), (0.3, "ding"), (0.42, "pop"), (1.95, "pop"), (2.3, "pop"),
           (2.65, "boing")])

# 5. NG example
T6B = 0.1 + VO["ng1"] + 0.1
c6 = Clip(SOFT, 0.0, 2.25, speed=2.25 / (T6B + VO["ng2"] + 0.3))


def s5_ov(img, t):
    sticker(img, t, ng_mark(300), 820, 560, 0.25, rot=0, wobble=False)
    if t > 0.25:
        pill(img, 820, 760, "NG", size=60, fg=WHITE, bg=CORAL, border=WHITE,
             scale=ease_out_back((t - 0.35) / 0.3))
    caption(img, t, [
        L([("柔らかくて", BLACK)], 150),
        L([("小さい", CORAL), ("タイプは", BLACK)], 135, delay=0.2),
        L([("お勧めしません！", CORAL)], 120, delay=0.4, marker=YELLOW)], end=T6B - 0.03)
    caption(img, t, [
        L([("安くても", BLACK), ("弱い", ORANGE), ("と", BLACK)], 135),
        L([("守れない。", CORAL)], 175, delay=0.3, marker=YELLOW)], start=T6B)


scene(c6.n / FPS, lambda t: c6.next(), s5_ov, vo=[(0.1, "ng1"), (T6B, "ng2")],
      sfx=[(0.12, "pop"), (0.25, "buzz"), (0.42, "pop"), (0.77, "pop"), (2.7, "pop"), (3.15, "pop")])

# 6. Wrist guard (fast-forward)
T7B = 0.35 + VO["wr1"] + 0.1
c7 = Clip(WRIST, 0.7, 10.5, speed=min(1.5, 10.5 / (T7B + VO["wr2"] + 0.3)), crop="608:1080:656:0")
FF = ff_badge()
WR_SHIFT = 630  # move footage up so the wrist/strap stays clear of the captions


def wrist_bg(t):
    fr = c7.next()
    img = Image.new("RGB", (W, H))
    top = H - WR_SHIFT
    # blurred fill behind, whole frame (zoomed out) on top
    bgf = fr.resize((W // 10, top // 10)).filter(ImageFilter.GaussianBlur(3)).resize((W, top))
    bgf = Image.blend(bgf, Image.new("RGB", (W, top), (40, 30, 25)), 0.25)
    img.paste(bgf, (0, 0))
    fw = int(top * W / H)
    img.paste(fr.resize((fw, top), Image.BILINEAR), ((W - fw) // 2, 0))
    img.paste(CREAM_BG.crop((0, H - WR_SHIFT, W, H)), (0, H - WR_SHIFT))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - WR_SHIFT - 6, W, H - WR_SHIFT + 6], fill=WHITE)
    return img


scene(c7.n / FPS, wrist_bg,
      lambda img, t: sticker(img, t, FF, 840, 380, 0.1, wobble=False),
      lambda img, t: draw_text_block(img, [
          L([("肘", ORANGE), ("・", BLACK), ("手首", ORANGE), ("も", BLACK)], 130),
          L([("セットで", BLACK), ("安心！", CORAL)], 130, delay=0.4, marker=YELLOW)],
          t, 0.35, CAP_X, cy_top=H - WR_SHIFT + 50, maxw=CAP_W, end=T7B - 0.03),
      lambda img, t: draw_text_block(img, [
          L([("硬い方", ORANGE), ("を", BLACK)], 130),
          L([("手のひら", CORAL), ("にしてね！", BLACK)], 130, delay=0.35, marker=YELLOW)],
          t, T7B, CAP_X, cy_top=H - WR_SHIFT + 50, maxw=CAP_W),
      vo=[(0.35, "wr1"), (T7B, "wr2")], sfx=[(0.1, "whoosh"), (0.35, "pop"), (0.8, "pop")])

# 7. Where to buy (card)
ICONS = [shop_icon(k, 150).resize((160, 160), Image.LANCZOS) for k in (0, 1, 3, 2)]
ROWS = ["プロショップ", "大型\nスポーツショップ", "ネット通販", "ネットフリマ"]
ROW_COL = [CORAL, (70, 150, 230), (245, 160, 40), (60, 180, 120)]
ROW_T = []
_t = 0.1 + VO["buy"] + 0.05
for _k in ("b1", "b2", "b3", "b4"):
    ROW_T.append(_t)
    _t += VO[_k] + 0.05
D7 = _t + 0.35


def row_card(i):
    w, h = 920, 210
    s = Image.new("RGBA", (w + 20, h + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    d.rounded_rectangle([10, 18, w + 10, h + 18], radius=50, fill=(200, 160, 110, 120))
    d.rounded_rectangle([6, 6, w + 6, h + 6], radius=50, fill=WHITE, outline=BROWN, width=6)
    cx, cy = 100, h / 2 + 6
    d.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=ROW_COL[i], outline=BROWN, width=5)
    d.text((cx, cy + 2), str(i + 1), font=font(POP, 68), fill=WHITE, anchor="mm")
    s.alpha_composite(ICONS[i], (185, int(cy - 80)))
    parts = ROWS[i].split("\n")
    if len(parts) == 1:
        items, tw, sz = layout_line([(parts[0], BLACK)], 80, 530, POP)
        d.text((375, cy + 4), parts[0], font=font(POP, sz), fill=BLACK, anchor="lm")
    else:
        d.text((375, cy - 36), parts[0], font=font(POP, 56), fill=BLACK, anchor="lm")
        items, tw, sz = layout_line([(parts[1], BLACK)], 68, 530, POP)
        d.text((375, cy + 38), parts[1], font=font(POP, sz), fill=BLACK, anchor="lm")
    return s


ROW_SPR = [row_card(i) for i in range(4)]


def s7_ov(img, t):
    d = ImageDraw.Draw(img)
    p = ease_out_back(t / 0.4)
    if p > 0:
        burst(d, W / 2, 400, 330 * p, 400 * p, [190, 205, 220, -10, -25, -40], 14, ORANGE)
    draw_text_block(img, [
        L([("買う場所は", BLACK), ("4つ", CORAL, 1.45)], 120, marker=YELLOW)],
        t, 0.1, W / 2, cy_top=310, maxw=920)
    for i in range(4):
        lt = t - ROW_T[i]
        if lt < 0:
            continue
        e = ease_out_back(lt / 0.42, 1.8)
        x = W / 2 + (1 - e) * 700
        paste_scaled(img, ROW_SPR[i], x, 720 + i * 255, 1.0, clamp(lt / 0.12))
    decor_stars(img, t, [(130, 1760, 36, 0), (950, 1770, 30, 2)])


scene(D7, lambda t: CREAM_BG.copy(), s7_ov, tag=False,
      vo=[(0.1, "buy")] + [(ROW_T[i], "b%d" % (i + 1)) for i in range(4)],
      sfx=[(0.0, "whoosh"), (0.1, "pop")] + [(x, "ding") for x in ROW_T])

# 8. You don't need to spend much (card)
COIN = coin(72)
random.seed(4)
COINS = [(random.uniform(150, 930), random.uniform(0.9, 1.6), random.uniform(-30, 30),
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
    draw_text_block(img, [L([("でも、", BLACK)], 160)], t, 0.1, W / 2, cy_top=320, maxw=980, scale=0.88,
                    anim="drop")
    draw_text_block(img, [
        L([("お金", ORANGE), ("をかける", BLACK)], 145),
        L([("必要は", BLACK)], 160, delay=0.2),
        L([("ありません！", CORAL)], 150, delay=0.45, marker=YELLOW)],
        t, 0.55, W / 2, cy_top=600, maxw=980, scale=0.88)
    decor_stars(img, t, [(140, 330, 42, 0), (950, 420, 36, 1), (930, 1200, 30, 2)])


scene(0.1 + VO["money"] + 0.3, lambda t: MINT_BG.copy(), s8_ov, tag=False, vo=[(0.1, "money")],
      sfx=[(0.0, "whoosh"), (0.1, "pop"), (0.55, "pop"), (0.85, "pop"), (1.25, "boing")]
      + [(c[1] + 0.3, "coin") for c in COINS[::2]])

# 9. Closing
T9B = 0.12 + VO["end1"] + 0.05
c9 = Clip(HOOK, 3.6, 2.09, speed=2.09 / (T9B + VO["end2"] + 0.35))
scene(c9.n / FPS, lambda t: c9.next(),
      lambda img, t: caption(img, t, [
          L([("プロテクターは、", BLACK)], 120),
          L([("思いきり", ORANGE)], 165, delay=0.3)], end=T9B - 0.03),
      lambda img, t: caption(img, t, [
          L([("練習するための", BLACK)], 135),
          L([("道具！", CORAL)], 195, delay=0.3, marker=YELLOW)], start=T9B),
      lambda img, t: decor_stars(img, t, [(150, 880, 38, 0), (930, 840, 32, 2)])
      if t > 1.9 else None,
      vo=[(0.12, "end1"), (T9B, "end2")], sfx=[(0.12, "pop"), (0.52, "pop"), (2.25, "pop"), (2.7, "boing")])

# 10. Next time: helmet (clean, editorial look)
HELM = helmet(400, straps=False)
NX_BG = (250, 246, 238)
NX_INK = (52, 44, 40)
NX_ACC = (226, 96, 78)


def _nx_base():
    img = Image.new("RGB", (W, H), NX_BG)
    d = ImageDraw.Draw(img)
    # soft accent shapes
    d.ellipse([190, 430, 890, 1130], fill=(247, 222, 212))
    d.ellipse([-180, 1560, 260, 2000], fill=(236, 230, 214))
    d.ellipse([840, -160, 1260, 260], fill=(236, 230, 214))
    # thin frame
    d.rectangle([56, 56, W - 56, H - 56], outline=(210, 196, 176), width=3)
    return img


NX_BASE = _nx_base()


def _spaced(text, size, color, track, fp=GOTH):
    f = font(fp, size)
    w = sum(f.getlength(c) for c in text) + track * (len(text) - 1)
    sp = Image.new("RGBA", (int(w + 20), int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    x = 10
    for c in text:
        d.text((x, size * 0.75), c, font=f, fill=color, anchor="lm")
        x += f.getlength(c) + track
    return sp


NX_NEXT = _spaced("NEXT", 64, NX_ACC, 26)
NX_SMALL = _spaced("次回は", 58, NX_INK, 10)
NX_BIG = _spaced("ヘルメット編", 150, NX_INK, 6)
NX_SOON = _spaced("お楽しみに", 52, NX_ACC, 18)
NX_FOLLOW = _spaced("フォローして待っててね", 40, NX_INK, 4)


def _rise(img, spr, y, t, t0, dist=40):
    lt = t - t0
    if lt <= 0:
        return
    e = ease_out_cubic(lt / 0.45)
    paste_scaled(img, spr, W / 2, y + dist * (1 - e), 1.0, e)


def s10_ov(img, t):
    d = ImageDraw.Draw(img)
    # NEXT with lines either side
    e = ease_out_cubic((t - 0.05) / 0.5)
    if e > 0:
        half = NX_NEXT.width / 2
        d.line([(W / 2 - half - 30 - 150 * e, 290), (W / 2 - half - 30, 290)], fill=NX_ACC, width=4)
        d.line([(W / 2 + half + 30, 290), (W / 2 + half + 30 + 150 * e, 290)], fill=NX_ACC, width=4)
    _rise(img, NX_NEXT, 290, t, 0.05, 20)
    lt = t - 0.15
    if lt > 0:
        e = ease_out_cubic(lt / 0.5)
        y = 790 + 60 * (1 - e) + 12 * math.sin(lt * 2.6)
        paste_scaled(img, HELM, W / 2, y, 0.9 + 0.1 * e, e, -4 + 2 * math.sin(lt * 2))
    _rise(img, NX_SMALL, 1220, t, 0.35)
    _rise(img, NX_BIG, 1350, t, 0.5)
    e = ease_out_cubic((t - 0.8) / 0.5)
    if e > 0:
        d.line([(W / 2 - 200 * e, 1460), (W / 2 + 200 * e, 1460)], fill=NX_INK, width=3)
    _rise(img, NX_SOON, 1540, t, 0.9, 20)
    lt = t - 1.15
    if lt > 0:
        e = ease_out_cubic(lt / 0.4)
        bw, bh = NX_FOLLOW.width + 50, 84
        box = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(box).rounded_rectangle([2, 2, bw - 3, bh - 3], radius=bh // 2,
                                              fill=WHITE, outline=NX_INK, width=3)
        box.alpha_composite(NX_FOLLOW, (25, int(bh / 2 - NX_FOLLOW.height / 2)))
        paste_scaled(img, box, W / 2, 1670 + 20 * (1 - e), 1.0, e)


scene(max(2.9, 0.3 + VO["next"] + 0.35), lambda t: NX_BASE.copy(), s10_ov, punch_in=False,
      vo=[(0.3, "next")])

# 11. Closing card in the style of the shop's chicken notice
CHICK_SRC = UP + "eddc9882-image.jpg"
END_BG = (254, 253, 249)
END_RED = (196, 88, 72)
END_INK = (58, 44, 38)


def _end_card_base():
    img = Image.new("RGB", (W, H), END_BG)
    src = Image.open(CHICK_SRC).convert("RGB")
    top = src.crop((0, 0, src.width, 476))
    th = int(476 * W / src.width)
    top = top.resize((W, th), Image.LANCZOS).filter(
        ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    img.paste(top, (0, 0))
    d = ImageDraw.Draw(img)
    # soft corner blobs at the bottom
    d.ellipse([-260, 1640, 330, 2140], fill=(242, 224, 184))
    d.ellipse([760, 1700, 1340, 2200], fill=(232, 195, 179))
    for (x0, y0, x1, y1) in [(60, 1800, 90, 1770), (110, 1830, 150, 1810),
                             (960, 1830, 990, 1800), (1010, 1860, 1045, 1840)]:
        d.line([(x0, y0), (x1, y1)], fill=WHITE, width=10)
    # yellow wavy blob behind the headline
    blob = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    col = (250, 236, 199, 255)
    bd.rounded_rectangle([40, 1040, W - 40, 1380], radius=120, fill=col)
    for k in range(7):
        cx = 120 + k * 140
        bd.ellipse([cx - 110, 1000 + (k % 2) * 20, cx + 110, 1150 + (k % 2) * 20], fill=col)
        bd.ellipse([cx - 110, 1280 - (k % 2) * 20, cx + 110, 1420 - (k % 2) * 20], fill=col)
    img = Image.alpha_composite(img.convert("RGBA"), blob).convert("RGB")
    d = ImageDraw.Draw(img)
    # dotted separators for the small lines
    for y in (1572, 1682):
        for x in range(150, 940, 22):
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(225, 205, 170))
    return img


END_BASE = _end_card_base()


def _line_sprite(segs, size):
    f = font(ROUND, size)
    w = sum(f.getlength(t) for t, c in segs)
    sp = Image.new("RGBA", (int(w + 20), int(size * 1.5)), (0, 0, 0, 0))
    d = ImageDraw.Draw(sp)
    x = 10
    for t, c in segs:
        d.text((x, size * 0.75), t, font=f, fill=c, anchor="lm")
        x += f.getlength(t)
    return sp


END_LINES = [
    (_line_sprite([("コメント・DM", END_RED)], 112), 1140, 0.15),
    (_line_sprite([("お待ちしてます！", END_INK)], 100), 1290, 0.4),
    (_line_sprite([("分からないことがあれば、", END_INK)], 58), 1520, 0.8),
    (_line_sprite([("お気軽にどうぞ♪", END_INK)], 58), 1630, 1.0),
]


def s11_ov(img, t):
    for spr, y, t0 in END_LINES:
        lt = t - t0
        if lt > 0:
            paste_scaled(img, spr, W / 2, y, ease_out_back(lt / 0.3, 1.4), clamp(lt / 0.1))
    p = ease_out_cubic((t - 0.6) / 0.35)
    if p > 0:
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([160, 1372, 160 + 760 * p, 1386], radius=7, fill=WHITE)


scene(0.3 + VO["dm"] + 0.5, lambda t: END_BASE.copy(), s11_ov, punch_in=False,
      vo=[(0.3, "dm")])

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
    for (st, key) in sc["vo"]:
        vo_events.append((round(T + st, 3), key))
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
json.dump(dict(total=T, events=sorted(events), vo=sorted(vo_events)), open("events.json", "w"))
