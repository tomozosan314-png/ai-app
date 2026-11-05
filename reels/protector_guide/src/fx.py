"""Shared drawing helpers: text sprites, easing, decorations."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIR = "/tmp/claude-0/-home-user-ai-app/4d0dac7b-7b1e-524e-acb0-cc9ba3078324/scratchpad/fonts/"
POP = FONT_DIR + "MochiyPopOne-Regular.ttf"
ROUND = FONT_DIR + "MPLUSRounded1c-Black.ttf"

W, H, FPS = 1080, 1920, 30

BLACK = (30, 22, 18)
WHITE = (255, 255, 255)
ORANGE = (255, 122, 26)
CORAL = (240, 84, 72)
YELLOW = (255, 214, 64)
CREAM = (255, 248, 230)
MINT = (214, 240, 236)
BROWN = (92, 56, 30)
NAVY = (40, 52, 90)


@lru_cache(maxsize=64)
def font(path, size):
    return ImageFont.truetype(path, size)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_back(x, s=2.2):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


@lru_cache(maxsize=2048)
def glyph(ch, size, color, stroke_ratio=0.17, fontpath=POP, shadow=True):
    """A single character with a thick white outline and soft drop shadow."""
    f = font(fontpath, size)
    sw = max(2, int(size * stroke_ratio))
    pad = sw + int(size * 0.12)
    adv = f.getlength(ch)
    w = int(adv + pad * 2)
    h = int(size * 1.45 + pad * 2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y0 = pad + int(size * 0.05)
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad, y0 + size * 0.07), ch, font=f,
                                fill=(40, 25, 15, 150), stroke_width=sw,
                                stroke_fill=(40, 25, 15, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.04))
        img.alpha_composite(sh)
    ImageDraw.Draw(img).text((pad, y0), ch, font=f, fill=color,
                             stroke_width=sw, stroke_fill=WHITE)
    return img, pad, adv


def layout_line(segs, size, maxw, fontpath=POP):
    """segs: list of (text, color[, scale]). Returns (items, width, size_used)."""
    while True:
        items, x = [], 0.0
        for seg in segs:
            text, color = seg[0], seg[1]
            sc = seg[2] if len(seg) > 2 else 1.0
            s = int(size * sc)
            f = font(fontpath, s)
            for ch in text:
                items.append((ch, s, color, x))
                x += f.getlength(ch)
        if x <= maxw or size < 30:
            return items, x, size
        size = int(size * 0.95)


def paste_scaled(dst, spr, cx, cy, scale, alpha=1.0, rot=0.0):
    """Paste sprite centred at (cx, cy) with scale/alpha/rotation."""
    if scale <= 0.01 or alpha <= 0.01:
        return
    s = spr
    if abs(scale - 1) > 0.01:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))),
                     Image.BICUBIC)
    if abs(rot) > 0.1:
        s = s.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        a = s.getchannel("A").point(lambda v: int(v * alpha))
        s = s.copy()
        s.putalpha(a)
    dst.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


def draw_text_block(img, lines, t, start, cx, cy_bottom=None, cy_top=None,
                    maxw=900, stagger=0.035, gap=1.2, end=None,
                    fontpath=POP, anim="pop", marker=None, align="center"):
    """Animated multi-line text.

    lines: list of dict(segs=[(text,color[,scale])], size=int, delay=float,
                        marker=color or None)
    """
    laid = []
    for ln in lines:
        items, w, s = layout_line(ln["segs"], ln["size"], maxw, fontpath)
        lh = max(it[1] for it in items) * gap
        laid.append((ln, items, w, lh))
    total_h = sum(l[3] for l in laid)
    if cy_bottom is not None:
        y = cy_bottom - total_h
    elif cy_top is not None:
        y = cy_top
    else:
        y = cy - total_h / 2  # noqa
    out_a = 1.0
    if end is not None:
        out_a = 1 - clamp((t - (end - 0.18)) / 0.18)
    for ln, items, w, lh in laid:
        ls = start + ln.get("delay", 0.0)
        x0 = cx - w / 2 if align == "center" else cx
        base = y + lh / 2
        mk = ln.get("marker")
        if mk is not None:
            p = ease_out_cubic((t - ls) / 0.35)
            if p > 0:
                mh = lh * 0.32
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([x0 - 10, base + lh * 0.08, x0 - 10 + (w + 20) * p,
                                     base + lh * 0.08 + mh], radius=int(mh / 2),
                                    fill=mk + (int(235 * out_a),))
        for i, (ch, s, color, x) in enumerate(items):
            lt = t - ls - i * stagger
            if lt < 0:
                continue
            spr, pad, adv = glyph(ch, s, color, fontpath=fontpath)
            if anim == "pop":
                sc = ease_out_back(lt / 0.28)
                dy = 0
            elif anim == "drop":
                sc = 1.0
                dy = -60 * (1 - ease_out_back(lt / 0.32))
            else:
                sc = 1.0
                dy = 0
            a = clamp(lt / 0.08) * out_a
            ccx = x0 + x + adv / 2
            # spr centre maps to glyph centre approx
            paste_scaled(img, spr, ccx, base + dy, sc, a)
        y += lh


def star(d, cx, cy, r, width, color=WHITE, rot=-90):
    pts = []
    for k in range(11):
        ang = math.radians(rot + k * 144)
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    d.line(pts, fill=color, width=width, joint="curve")


def burst(d, cx, cy, r0, r1, angles, width, color=YELLOW):
    for a in angles:
        ra = math.radians(a)
        d.line([(cx + r0 * math.cos(ra), cy + r0 * math.sin(ra)),
                (cx + r1 * math.cos(ra), cy + r1 * math.sin(ra))],
               fill=color, width=width)
        for p in [(cx + r0 * math.cos(ra), cy + r0 * math.sin(ra)),
                  (cx + r1 * math.cos(ra), cy + r1 * math.sin(ra))]:
            d.ellipse([p[0] - width / 2, p[1] - width / 2, p[0] + width / 2,
                       p[1] + width / 2], fill=color)


def pill(img, cx, cy, text, size=44, fg=BLACK, bg=CREAM, border=BROWN,
         fontpath=POP, padx=34, pady=16, alpha=1.0, scale=1.0):
    f = font(fontpath, size)
    tw = f.getlength(text)
    w, h = int(tw + padx * 2), int(size * 1.3 + pady * 2)
    spr = Image.new("RGBA", (w + 12, h + 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(spr)
    d.rounded_rectangle([6, 10, w + 6, h + 10], radius=h // 2, fill=(60, 35, 20, 110))
    d.rounded_rectangle([4, 4, w + 4, h + 4], radius=h // 2, fill=bg,
                        outline=border, width=5)
    d.text((4 + padx, 4 + pady + size * 0.08), text, font=f, fill=fg)
    paste_scaled(img, spr, cx, cy, scale, alpha)
