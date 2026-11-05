"""Hand-drawn style illustrations rendered with PIL (supersampled)."""
import math
from PIL import Image, ImageDraw
from fx import *  # noqa

SS = 2  # supersampling


def _canvas(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def _down(img):
    return img.resize((img.width // SS, img.height // SS), Image.LANCZOS)


def _cap(d, p, w, col):
    d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=col)


def limb(d, pts, w, col, outline=None, ow=0):
    pts = [(x * SS, y * SS) for x, y in pts]
    w *= SS
    if outline:
        ow *= SS
        d.line(pts, fill=outline, width=int(w + ow * 2), joint="curve")
        for p in pts:
            _cap(d, p, w + ow * 2, outline)
    d.line(pts, fill=col, width=int(w), joint="curve")
    for p in pts:
        _cap(d, p, w, col)


def ell(d, box, fill, outline=None, width=0):
    d.ellipse([v * SS for v in box], fill=fill, outline=outline, width=width * SS)


def kneeslide(w=900, h=700, phase=0.0):
    """Kid doing a knee slide on a ramp with highlighted knee pads.
    phase: 0..1 animation (speed lines / sparkle)."""
    img = _canvas(w, h)
    d = ImageDraw.Draw(img)
    # ramp (quarter pipe on the left, flat to the right)
    ground = h - 130
    ramp = [(0, 60)]
    for k in range(0, 41):
        a = math.radians(180 + k * 90 / 40)
        r = 330
        ramp.append((r + r * math.cos(a) + 0, ground - r - r * math.sin(a) * -1 - 0))
    # simpler explicit curve: from (0,ground-330) down to (330,ground)
    ramp = [(0, ground - 400)]
    for k in range(41):
        a = math.radians(180 + k * 90 / 40)
        ramp.append((330 + 330 * math.cos(a), ground - 330 - 330 * math.sin(a)))
    ramp += [(w, ground), (w, h), (0, h)]
    d.polygon([(x * SS, y * SS) for x, y in ramp], fill=(214, 150, 96))
    surf = [(x * SS, y * SS) for x, y in ramp[:42]] + [(w * SS, ground * SS)]
    d.line(surf, fill=BROWN, width=10 * SS, joint="curve")
    d.line([(0, ground * SS + 40 * SS), (w * SS, ground * SS + 40 * SS)],
           fill=(196, 132, 80), width=6 * SS)

    # kid position (sliding to the right)
    kx = 520 + 30 * math.sin(phase * math.pi * 2) * 0
    knee = (kx, ground - 26)
    hip = (kx - 20, ground - 200)
    neck = (kx - 50, ground - 360)
    head = (kx - 60, ground - 445)
    foot = (kx - 210, ground - 34)
    outline = BLACK
    skin = (255, 214, 180)
    shirt = (52, 58, 70)
    pants = (40, 44, 58)
    # motion lines behind
    for i, yy in enumerate([ground - 300, ground - 210, ground - 120]):
        off = (phase * 90 + i * 30) % 90
        x1 = kx - 330 - off
        d.line([(x1 * SS, yy * SS), ((x1 - 150) * SS, yy * SS)], fill=WHITE,
               width=14 * SS)
        _cap(d, (x1 * SS, yy * SS), 14 * SS, WHITE)
        _cap(d, ((x1 - 150) * SS, yy * SS), 14 * SS, WHITE)
    # dust puffs
    for i, (dx, r) in enumerate([(-250, 34), (-310, 26), (-360, 18)]):
        cx = kx + dx - (phase * 40) % 40
        ell(d, [cx - r, ground - 2 * r, cx + r, ground], WHITE, BROWN, 4)
    # back arm
    limb(d, [neck, (kx - 140, ground - 300), (kx - 190, ground - 360)], 36, shirt, outline, 6)
    # legs: shin lying back, thigh up to hip
    limb(d, [foot, knee], 50, pants, outline, 6)
    limb(d, [knee, hip], 60, pants, outline, 6)
    # shoe
    ell(d, [foot[0] - 60, foot[1] - 28, foot[0] + 20, foot[1] + 28], (236, 72, 150), outline, 6)
    # torso
    limb(d, [hip, neck], 92, shirt, outline, 6)
    # front arm (waving forward)
    limb(d, [neck, (kx + 70, ground - 300), (kx + 150, ground - 360)], 36, shirt, outline, 6)
    ell(d, [kx + 125, ground - 390, kx + 180, ground - 335], skin, outline, 5)
    ell(d, [kx - 218, ground - 390, kx - 163, ground - 335], skin, outline, 5)
    # head + helmet
    ell(d, [head[0] - 78, head[1] - 70, head[0] + 78, head[1] + 82], skin, outline, 6)
    hb = [head[0] - 88, head[1] - 92, head[0] + 88, head[1] + 60]
    d.chord([v * SS for v in hb], 180, 360, fill=CORAL, outline=outline, width=6 * SS)
    d.line([((head[0] - 88) * SS, (head[1] - 16) * SS), ((head[0] + 88) * SS, (head[1] - 16) * SS)],
           fill=outline, width=6 * SS)
    # face: happy eyes + smile, looking right
    for ex in (head[0] + 4, head[0] + 46):
        d.arc([(ex - 13) * SS, (head[1] + 10) * SS, (ex + 13) * SS, (head[1] + 34) * SS],
              200, 340, fill=outline, width=6 * SS)
    d.arc([(head[0] + 4) * SS, (head[1] + 30) * SS, (head[0] + 52) * SS, (head[1] + 66) * SS],
          20, 160, fill=outline, width=6 * SS)
    ell(d, [head[0] - 18, head[1] + 34, head[0] + 4, head[1] + 50], (255, 160, 150))

    # knee pad glow + pad
    pulse = 1 + 0.12 * math.sin(phase * math.pi * 4)
    gr = 95 * pulse
    ell(d, [knee[0] - gr, knee[1] - gr - 40, knee[0] + gr, knee[1] + gr - 40], None, YELLOW, 10)
    pad = [knee[0] - 52, knee[1] - 110, knee[0] + 52, knee[1] + 20]
    d.rounded_rectangle([v * SS for v in pad], radius=44 * SS, fill=ORANGE,
                        outline=outline, width=7 * SS)
    d.rounded_rectangle([(knee[0] - 30) * SS, (knee[1] - 88) * SS, (knee[0] - 6) * SS,
                         (knee[1] - 40) * SS], radius=12 * SS, fill=(255, 190, 120))
    # sparkle burst around the pad
    out = _down(img)
    d2 = ImageDraw.Draw(out)
    burst(d2, knee[0], knee[1] - 45, 110 * pulse, 150 * pulse, [-150, -110, -70, -30, 10],
          10, YELLOW)
    return out


def shop_icon(kind, s=150):
    img = _canvas(s, s)
    d = ImageDraw.Draw(img)
    S = SS
    ol = BLACK
    if kind == 0:  # pro shop: storefront with striped awning + skateboard
        d.rounded_rectangle([20 * S, 60 * S, 130 * S, 135 * S], radius=10 * S, fill=WHITE,
                            outline=ol, width=6 * S)
        for k in range(5):
            col = CORAL if k % 2 == 0 else WHITE
            x0 = 14 + k * 24.4
            d.pieslice([x0 * S, 36 * S, (x0 + 24.4) * S, 74 * S], 0, 180, fill=col,
                       outline=ol, width=4 * S)
            d.rectangle([x0 * S, 30 * S, (x0 + 24.4) * S, 55 * S], fill=col)
        d.rounded_rectangle([14 * S, 22 * S, 136 * S, 56 * S], radius=8 * S, outline=ol,
                            width=6 * S)
        d.rounded_rectangle([58 * S, 88 * S, 92 * S, 135 * S], radius=6 * S, fill=MINT,
                            outline=ol, width=5 * S)
    elif kind == 1:  # big sports shop: tall building with flag
        d.rounded_rectangle([18 * S, 40 * S, 132 * S, 138 * S], radius=10 * S, fill=(140, 200, 255),
                            outline=ol, width=6 * S)
        for r in range(3):
            for c in range(3):
                x = 32 + c * 34
                y = 54 + r * 26
                d.rounded_rectangle([x * S, y * S, (x + 20) * S, (y + 16) * S], radius=4 * S,
                                    fill=WHITE, outline=ol, width=3 * S)
        d.line([(75 * S, 40 * S), (75 * S, 8 * S)], fill=ol, width=5 * S)
        d.polygon([(77 * S, 8 * S), (110 * S, 18 * S), (77 * S, 28 * S)], fill=YELLOW,
                  outline=ol)
    else:  # flea-market app: phone with price tag
        d.rounded_rectangle([40 * S, 12 * S, 110 * S, 138 * S], radius=16 * S, fill=WHITE,
                            outline=ol, width=6 * S)
        d.rounded_rectangle([50 * S, 30 * S, 100 * S, 110 * S], radius=6 * S, fill=MINT)
        d.ellipse([68 * S, 118 * S, 82 * S, 132 * S], outline=ol, width=4 * S)
        d.polygon([(70 * S, 70 * S), (112 * S, 50 * S), (136 * S, 80 * S), (94 * S, 100 * S)],
                  fill=ORANGE, outline=ol)
        d.line([(70 * S, 70 * S), (112 * S, 50 * S), (136 * S, 80 * S), (94 * S, 100 * S),
                (70 * S, 70 * S)], fill=ol, width=5 * S, joint="curve")
        d.ellipse([104 * S, 60 * S, 116 * S, 72 * S], fill=WHITE, outline=ol, width=3 * S)
    return _down(img)


def coin(r=70):
    s = int(r * 2 + 12)
    img = _canvas(s, s)
    d = ImageDraw.Draw(img)
    c = s / 2
    ell(d, [c - r, c - r + 6, c + r, c + r + 6], (200, 140, 20))
    ell(d, [c - r, c - r, c + r, c + r], (255, 205, 60), BLACK, 5)
    ell(d, [c - r * 0.72, c - r * 0.72, c + r * 0.72, c + r * 0.72], None, (230, 160, 30), 5)
    out = _down(img)
    f = font(ROUND, int(r * 1.0))
    ImageDraw.Draw(out).text((c, c + 2), "¥", font=f, fill=(170, 100, 10), anchor="mm")
    return out


def helmet(w=420):
    h = int(w * 0.8)
    img = _canvas(w, h)
    d = ImageDraw.Draw(img)
    S = SS
    ol = BLACK
    box = [20 * S, 30 * S, (w - 20) * S, (h * 2 - 120) * S]
    d.pieslice(box, 180, 360, fill=CORAL, outline=ol, width=8 * S)
    base = (h - 60)
    d.rounded_rectangle([12 * S, (base - 10) * S, (w - 12) * S, (base + 34) * S],
                        radius=20 * S, fill=(60, 60, 70), outline=ol, width=7 * S)
    # vents
    for k, x in enumerate([w * 0.32, w * 0.5, w * 0.68]):
        d.rounded_rectangle([(x - 18) * S, (60 + abs(k - 1) * 18) * S, (x + 18) * S,
                             (base - 70 + abs(k - 1) * 10) * S], radius=18 * S,
                            fill=(255, 150, 140), outline=ol, width=5 * S)
    # shine
    d.arc([60 * S, 60 * S, (w - 60) * S, (h * 2 - 200) * S], 200, 245, fill=WHITE, width=14 * S)
    # strap
    d.line([(w * 0.25 * S, (base + 30) * S), (w * 0.42 * S, (h - 4) * S)], fill=ol, width=8 * S)
    d.line([(w * 0.75 * S, (base + 30) * S), (w * 0.58 * S, (h - 4) * S)], fill=ol, width=8 * S)
    return _down(img)


def ng_mark(s=260, width=34):
    img = _canvas(s, s)
    d = ImageDraw.Draw(img)
    m = 30
    for col, ww in ((WHITE, width + 22), (CORAL, width)):
        d.line([(m * SS, m * SS), ((s - m) * SS, (s - m) * SS)], fill=col, width=ww * SS)
        d.line([((s - m) * SS, m * SS), (m * SS, (s - m) * SS)], fill=col, width=ww * SS)
        for p in [(m, m), (s - m, s - m), (s - m, m), (m, s - m)]:
            _cap(d, (p[0] * SS, p[1] * SS), ww * SS, col)
    return _down(img)


def ok_mark(s=260, width=22):
    img = _canvas(s, s)
    d = ImageDraw.Draw(img)
    m = 34
    for col, ww in ((WHITE, width + 22), ((60, 190, 120), width)):
        d.ellipse([m * SS, m * SS, (s - m) * SS, (s - m) * SS], outline=col, width=ww * SS)
    return _down(img)


def ff_badge(scale=1.0):
    """Fast-forward badge (two triangles)."""
    w, h = 300, 110
    img = _canvas(w, h)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4 * SS, 4 * SS, (w - 4) * SS, (h - 4) * SS], radius=50 * SS,
                        fill=NAVY, outline=WHITE, width=6 * SS)
    for x in (38, 78):
        d.polygon([(x * SS, 30 * SS), ((x + 40) * SS, 55 * SS), (x * SS, 80 * SS)], fill=YELLOW)
    out = _down(img)
    ImageDraw.Draw(out).text((140, 56), "早送り", font=font(POP, 40), fill=WHITE, anchor="lm")
    return out
