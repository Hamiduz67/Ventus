"""'Aap Kya Karte?' — daily Urdu thriller reel renderer (YouTube Shorts only). Flat 2D noir look, fully original.
Usage: thriller_render.py <episode dir> [still:t1,t2,... | thumb]
Shots are data (script.json "shots"): bg + chars + props + fx + optional big/pill/clock/choice. Add new backgrounds to BG and
new props to PROPS (same flat style) when a story needs them, and commit them so later runs reuse them."""
import json, math, os, subprocess, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = sys.argv[1]; ONLY = sys.argv[2] if len(sys.argv) > 2 else None
W, H, FPS = 1080, 1920, 30
TL = json.load(open(f"{D}/timeline.json")); TOTAL = TL["total"]; LINES = TL["lines"]; SHOTL = TL["shots"]
S = json.load(open(f"{D}/script.json")); SHOTS = S["shots"]; META = json.load(open(f"{D}/meta.json"))
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hamid", "fonts") + "/"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
YEL = (255, 210, 60); WHITE = (255, 255, 255); RED = (225, 40, 55); INK = (12, 12, 20); TEAL = (90, 220, 230)
SIL = (34, 38, 60); RIM = (150, 225, 255)
NAMES = {"N": None, "P": ("WOH LADKA", (60, 150, 255)), "X": ("AJNABI", (170, 40, 50)), "F": ("AURAT", (210, 80, 140)),
         "W": ("AMMA JI", (180, 110, 160)), "O": ("BUZURG", (130, 120, 90))}

@lru_cache(None)
def fnt(name, size): return ImageFont.truetype(F + name, size)
@lru_cache(None)
def emoji(ch, size):
    f = ImageFont.truetype(EMOJI, 109); im = Image.new("RGBA", (170, 170), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((85, 85), ch, font=f, embedded_color=True, anchor="mm")
    im = im.crop(im.getbbox()); r = size / max(im.size)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
def eob(x):
    x = min(max(x, 0), 1); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def eo(x): x = min(max(x, 0), 1); return 1 - (1 - x) ** 3
def eio(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x
def mixc(c1, c2, x): return tuple(int(lerp(c1[i], c2[i], x)) for i in range(3))
def paste_c(base, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01: return
    if scale != 1: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1: im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))
@lru_cache(None)
def text_img(txt, name, size, color, stroke=0, sfill=INK):
    f = fnt(name, size); l, t, r, b = f.getbbox(txt, stroke_width=stroke)
    im = Image.new("RGBA", (r - l + 24, b - t + 24), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((12 - l, 12 - t), txt, font=f, fill=color, stroke_width=stroke, stroke_fill=sfill)
    return im
@lru_cache(None)
def glow_text(txt, name, size, color, glow):
    base = text_img(txt, name, size, color, 6, INK)
    g = Image.new("RGBA", (base.width + 80, base.height + 80), (0, 0, 0, 0))
    g.alpha_composite(text_img(txt, name, size, glow, 10, glow), (40, 40)); g = g.filter(ImageFilter.GaussianBlur(16))
    g.alpha_composite(base, (40, 40)); return g
def fit_text(txt, size, color, glow, maxw=980):
    while size > 50:
        im = glow_text(txt, "Anton-Regular.ttf", size, color, glow)
        if im.width - 80 <= maxw: return im
        size -= 8
    return glow_text(txt, "Anton-Regular.ttf", size, color, glow)
@lru_cache(None)
def pill(txt, size, bg, fg=WHITE, name="Poppins-Black.ttf"):
    ti = text_img(txt, name, size, fg); pw, ph = ti.width + 56, ti.height + 22
    im = Image.new("RGBA", (pw + 10, ph + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 8, pw + 6, ph + 8], radius=ph // 2, fill=(0, 0, 0, 100))
    d.rounded_rectangle([0, 0, pw, ph], radius=ph // 2, fill=bg, outline=INK, width=5)
    im.alpha_composite(ti, ((pw - ti.width) // 2, (ph - ti.height) // 2)); return im
def stamp(img, txt, x, y, k, col=RED, rot=-6, size=100):
    f = fnt("Anton-Regular.ttf", size); tw = int(f.getlength(txt)) + 80
    st = Image.new("RGBA", (tw, size + 90), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([8, 8, tw - 8, size + 82], radius=20, fill=(10, 10, 16, 220), outline=col, width=12)
    sd.text((tw / 2, (size + 90) / 2), txt, font=f, fill=col, anchor="mm")
    paste_c(img, st, x, y, eob(k / 0.22) * (1.35 - 0.35 * eo(k / 0.22)), rot=rot)
def grad(c1, c2, h=H, w=W):
    a = np.linspace(0, 1, h)[:, None, None]; c = np.array(c1)[None, None] * (1 - a) + np.array(c2)[None, None] * a
    return Image.fromarray(np.repeat(c, w, axis=1).astype(np.uint8)).convert("RGBA")

# ======================= BACKGROUNDS (all night / noir, cached)
@lru_cache(None)
def bg_highway_night():
    im = grad((6, 10, 28), (30, 40, 70), H); d = ImageDraw.Draw(im)
    r = np.random.default_rng(3)
    for _ in range(60): x, y = r.uniform(0, W), r.uniform(40, 700); d.ellipse([x, y, x + 3, y + 3], fill=(200, 210, 255))
    d.ellipse([780, 180, 900, 300], fill=(230, 230, 210)); d.ellipse([800, 170, 920, 290], fill=(6, 10, 28))   # crescent
    for k in range(9):   # distant hills
        x0 = k * 160 - 80; d.polygon([(x0, 1000), (x0 + 120, 870 - (k % 3) * 40), (x0 + 260, 1000)], fill=(14, 18, 36))
    d.rectangle([0, 1000, W, H], fill=(10, 12, 22))
    d.polygon([(470, 1000), (610, 1000), (W + 500, H), (-500, H)], fill=(34, 36, 48))   # road in perspective
    for k in range(7):
        y0 = 1000 + (k ** 1.7) * 30; y1 = y0 + 12 + k * 14; wd = 4 + k * 5
        d.polygon([(540 - wd, y0), (540 + wd, y0), (540 + wd * 1.3, y1), (540 - wd * 1.3, y1)], fill=(220, 210, 150))
    for side in (-1, 1):   # roadside poles
        for k in range(4):
            x = 540 + side * (120 + k ** 1.6 * 110); y = 1000 + k ** 1.6 * 60; h_ = 120 + k * 90
            d.rectangle([x - 3 - k, y - h_, x + 3 + k, y], fill=(20, 22, 34))
    return im
@lru_cache(None)
def bg_car_inside():
    im = grad((8, 12, 30), (22, 30, 56)); d = ImageDraw.Draw(im)
    d.rectangle([60, 300, 1020, 1060], fill=(18, 26, 52))                          # side window (outside night)
    for k in range(5): d.polygon([(60 + k * 220, 1060), (160 + k * 220, 760 - (k % 2) * 60), (280 + k * 220, 1060)], fill=(12, 16, 34))
    d.rectangle([0, 0, W, 300], fill=(10, 10, 16)); d.rectangle([0, 1060, W, H], fill=(14, 14, 22))   # roof + door panel
    d.rectangle([0, 300, 60, 1060], fill=(10, 10, 16)); d.rectangle([1020, 300, W, 1060], fill=(10, 10, 16))
    d.rounded_rectangle([60, 300, 1020, 1060], radius=40, outline=(40, 40, 56), width=18)
    d.rounded_rectangle([140, 1160, 940, 1480], radius=60, fill=(22, 22, 32), outline=(40, 40, 56), width=10)   # dashboard
    d.ellipse([-260, 1250, 380, 1890], outline=(30, 30, 44), width=46)               # steering wheel
    d.rounded_rectangle([760, 1110, 900, 1160], radius=12, fill=(30, 30, 40))
    d.text((830, 1135), "LOCK", font=fnt("Poppins-Black.ttf", 26), fill=(120, 120, 140), anchor="mm")
    return im
@lru_cache(None)
def bg_room_night():
    im = grad((14, 16, 30), (26, 28, 46)); d = ImageDraw.Draw(im)
    d.rectangle([600, 330, 960, 820], fill=(30, 50, 90), outline=(8, 8, 14), width=16); d.line([(780, 330), (780, 820)], fill=(8, 8, 14), width=10)
    d.line([(600, 575), (960, 575)], fill=(8, 8, 14), width=10)
    d.rectangle([0, 1250, W, H], fill=(18, 16, 24)); d.rectangle([90, 520, 360, 1250], fill=(30, 24, 30), outline=(8, 8, 14), width=10)   # door
    d.ellipse([310, 880, 336, 906], fill=(160, 140, 90))
    return im
@lru_cache(None)
def bg_street_night():
    im = grad((8, 10, 26), (34, 30, 52)); d = ImageDraw.Draw(im); r = np.random.default_rng(9); x = -20
    while x < W:
        w = r.uniform(170, 260); h = r.uniform(380, 640); d.rectangle([x, 1180 - h, x + w, 1180], fill=(18, 18, 34), outline=(6, 6, 12), width=5)
        for wy in range(int(1210 - h), 1120, 90):
            for wx in range(int(x) + 30, int(x + w) - 50, 80):
                if r.random() < 0.25: d.rectangle([wx, wy, wx + 36, wy + 46], fill=(250, 210, 120))
        x += w
    d.rectangle([0, 1180, W, H], fill=(24, 24, 32))
    d.rectangle([840, 560, 856, 1180], fill=(30, 30, 40)); d.polygon([(800, 560), (900, 560), (848, 600)], fill=(60, 60, 70))
    return im
@lru_cache(None)
def bg_corridor():
    im = grad((14, 18, 26), (30, 34, 44)); d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (380, 600), (380, 1100), (0, H)], fill=(24, 28, 38)); d.polygon([(W, 0), (700, 600), (700, 1100), (W, H)], fill=(20, 24, 34))
    d.rectangle([380, 600, 700, 1100], fill=(8, 10, 16)); d.polygon([(0, H), (380, 1100), (700, 1100), (W, H)], fill=(30, 30, 38))
    for k in range(3): x = 120 + k * 80; d.rectangle([x, 760 - k * 40, x + 40, 1300 - k * 80], fill=(40, 30, 30))
    return im
@lru_cache(None)
def bg_split():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (640, 0), (440, H), (0, H)], fill=(90, 14, 24)); d.polygon([(640, 0), (W, 0), (W, H), (440, H)], fill=(14, 30, 80))
    d.line([(640, 0), (440, H)], fill=WHITE, width=10); return im
@lru_cache(None)
def bg_choice():
    im = grad((10, 6, 20), (40, 8, 20)); return im
BG = {"highway_night": bg_highway_night, "car_inside": bg_car_inside, "room_night": bg_room_night, "street_night": bg_street_night,
      "corridor": bg_corridor, "split": bg_split, "choice": bg_choice}

# ======================= CHARACTERS (silhouettes with a cold rim light; glowing eyes for threats)
@lru_cache(None)
def person_img(kind, wave_ph=0, eyes=False, close=False):
    """Flat noir silhouette, 600x1000 (feet at the bottom). Supersampled for smooth edges."""
    Z = 2; c = Image.new("RGBA", (600 * Z, 1000 * Z), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    P = lambda *v: [q * Z for q in v]
    col = (8, 8, 14) if kind == "hood" else SIL
    cx = 300; hy = 120 if kind != "old" else 140
    def limb(x0, y0, x1, y1, w):
        d.line(P(x0, y0, x1, y1), fill=col, width=w * Z); d.ellipse(P(x1 - w / 2, y1 - w / 2, x1 + w / 2, y1 + w / 2), fill=col)
    # legs
    if kind == "woman":
        d.polygon(P(cx - 60, 760, cx - 10, 760, cx - 25, 985, cx - 70, 985), fill=col); d.polygon(P(cx + 10, 760, cx + 60, 760, cx + 70, 985, cx + 25, 985), fill=col)
    else:
        d.polygon(P(cx - 75, 520, cx - 5, 520, cx - 20, 985, cx - 72, 985), fill=col); d.polygon(P(cx + 5, 520, cx + 75, 520, cx + 72, 985, cx + 20, 985), fill=col)
        d.ellipse(P(cx - 90, 965, cx - 10, 1000), fill=col); d.ellipse(P(cx + 10, 965, cx + 90, 1000), fill=col)
    # torso
    if kind == "woman":
        d.polygon(P(cx - 85, 210, cx + 85, 210, cx + 70, 430, cx + 150, 800, cx - 150, 800, cx - 70, 430), fill=col)   # long kameez
    elif kind == "hood":
        d.polygon(P(cx - 115, 215, cx + 115, 215, cx + 105, 560, cx - 105, 560), fill=col)
    else:
        d.polygon(P(cx - 105, 215, cx + 105, 215, cx + 80, 540, cx - 80, 540), fill=col)
    d.ellipse(P(cx - 120, 190, cx - 60, 260), fill=col); d.ellipse(P(cx + 60, 190, cx + 120, 260), fill=col)   # rounded shoulders
    d.rectangle(P(cx - 28, 160, cx + 28, 220), fill=col)   # neck
    # head
    d.ellipse(P(cx - 58, hy - 68, cx + 58, hy + 62), fill=col)
    if kind == "woman":   # dupatta over the head, falling behind the shoulders
        d.chord(P(cx - 74, hy - 84, cx + 74, hy + 70), 160, 380, fill=(44, 40, 70))
        d.polygon(P(cx - 74, hy - 5, cx - 125, 520, cx - 70, 470, cx - 50, hy + 40), fill=(44, 40, 70))
        d.polygon(P(cx + 74, hy - 5, cx + 125, 520, cx + 70, 470, cx + 50, hy + 40), fill=(44, 40, 70))
    elif kind == "hood":
        d.polygon(P(cx - 85, hy + 80, cx - 80, hy - 40, cx - 30, hy - 95, cx + 30, hy - 95, cx + 80, hy - 40, cx + 85, hy + 80), fill=col)
        d.ellipse(P(cx - 46, hy - 50, cx + 46, hy + 55), fill=(0, 0, 0))
    elif kind == "old":
        d.chord(P(cx - 56, hy - 78, cx + 56, hy - 10), 180, 360, fill=(70, 70, 90))   # topi
        d.polygon(P(cx - 35, hy + 30, cx + 35, hy + 30, cx, hy + 110), fill=(80, 80, 96))   # white beard (dim)
    elif kind == "guard":
        d.rectangle(P(cx - 62, hy - 78, cx + 62, hy - 40), fill=(10, 10, 20)); d.rectangle(P(cx - 90, hy - 48, cx + 70, hy - 34), fill=(10, 10, 20))
    else:   # man: short hair tuft
        d.chord(P(cx - 60, hy - 74, cx + 62, hy - 4), 180, 360, fill=(14, 14, 24))
    # arms
    if kind == "hood": limb(cx - 105, 230, cx - 120, 470, 46); limb(cx + 105, 230, cx + 120, 470, 46)   # hands in pockets
    else:
        limb(cx - 100, 230, cx - 130, 400, 44); limb(cx - 130, 400, cx - 120, 540, 40)
        if wave_ph:
            a1 = -0.75 + 0.05 * math.sin(wave_ph); a2 = -1.55 + 0.4 * math.sin(wave_ph)
            ex, ey = cx + 100 + math.cos(a1) * 160, 230 + math.sin(a1) * 160
            limb(cx + 100, 230, ex, ey, 44); hx, hy2 = ex + math.cos(a2) * 150, ey + math.sin(a2) * 150; limb(ex, ey, hx, hy2, 40)
            d.ellipse(P(hx - 30, hy2 - 30, hx + 30, hy2 + 30), fill=col)
        else: limb(cx + 100, 230, cx + 130, 400, 44); limb(cx + 130, 400, cx + 120, 540, 40)
    if kind == "old": d.line(P(cx + 150, 520, cx + 175, 990), fill=col, width=16 * Z)
    c = c.resize((600, 1000), Image.LANCZOS)
    # cold rim light on the right edge
    a = c.getchannel("A"); sh = Image.new("L", c.size, 0); sh.paste(a, (-10, 0))
    m = Image.fromarray(np.clip(np.array(a, np.int16) - np.array(sh, np.int16), 0, 255).astype(np.uint8))
    rim = Image.new("RGBA", c.size, RIM + (0,)); rim.putalpha(m.filter(ImageFilter.GaussianBlur(2)))
    out = Image.new("RGBA", c.size, (0, 0, 0, 0)); out.alpha_composite(c); out.alpha_composite(rim)
    if eyes:
        dd = ImageDraw.Draw(out)
        for ex_ in (cx - 22, cx + 22): dd.ellipse([ex_ - 11, hy - 4, ex_ + 11, hy + 9], fill=(255, 40, 40))
    return out
@lru_cache(None)
def halo():
    g = Image.new("RGBA", (700, 1100), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([80, 60, 620, 1040], fill=(90, 140, 200, 70))
    return g.filter(ImageFilter.GaussianBlur(70))
def person(img, ch, t, speaking=False, fade=1.0):
    kind = ch["k"]; s = ch.get("s", 1.0); x, y = ch["x"], ch.get("y", 1250)
    ph = (round(t * 6) % 12) / 12 * 2 * math.pi if ch.get("wave") else 0
    im = person_img(kind, ph if ch.get("wave") else 0, ch.get("eyes", False))
    bob = math.sin(t * 2.0 + x) * 4 * s + (math.sin(t * 14) * 6 * s if speaking else 0)
    if not ch.get("eyes"):   # soft cold backlight so dark figures read against the night
        paste_c(img, halo(), x, y - 500 * s + bob, s, alpha=fade * 0.9)
    paste_c(img, im, x, y - 500 * s + bob, s, rot=-6 if ch.get("lean") else 0, alpha=fade)
    if ch.get("eyes") and fade > 0.2:
        gl = Image.new("RGBA", (120, 60), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([10, 10, 110, 50], fill=(255, 30, 30, 120))
        paste_c(img, gl.filter(ImageFilter.GaussianBlur(10)), x, y - 880 * s + bob, s, alpha=fade * (0.6 + 0.4 * math.sin(t * 5)))
    if ch.get("label"): paste_c(img, pill(ch["label"], 34, (40, 120, 220)), x, y - 1060 * s, 1.0)

# ======================= PROPS
@lru_cache(None)
def car_broken_img(hazard_on=False, baby=False):
    c = Image.new("RGBA", (640, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([20, 120, 620, 270], radius=40, fill=(30, 34, 48), outline=(6, 6, 10), width=8)
    d.polygon([(130, 125), (200, 30), (450, 30), (530, 125)], fill=(24, 28, 40), outline=(6, 6, 10))
    d.polygon([(215, 115), (240, 50), (330, 50), (330, 115)], fill=(60, 80, 110)); d.polygon([(345, 115), (345, 50), (430, 50), (480, 115)], fill=(60, 80, 110))
    for wx in (150, 490): d.ellipse([wx - 55, 215, wx + 55, 325], fill=(8, 8, 12)); d.ellipse([wx - 25, 245, wx + 25, 295], fill=(60, 60, 70))
    hl = (255, 160, 30) if hazard_on else (90, 60, 20)
    for hx in (40, 600): d.ellipse([hx - 22, 150, hx + 22, 190], fill=hl)
    d.polygon([(560, 30), (600, 30), (640, 0)], fill=None)
    d.rectangle([300, 60, 360, 70], fill=(6, 6, 10))   # bonnet open line
    if baby:
        d.ellipse([360, 62, 400, 102], fill=(255, 220, 160, 200))
    return c
@lru_cache(None)
def radio_img(on=False):
    c = Image.new("RGBA", (520, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 519, 159], radius=24, fill=(20, 20, 28), outline=(50, 50, 66), width=6)
    d.rounded_rectangle([30, 30, 330, 120], radius=12, fill=(40, 200, 160) if on else (20, 70, 60))
    d.text((180, 75), "FM 98.6", font=fnt("Anton-Regular.ttf", 58), fill=(10, 30, 26) if on else (30, 90, 80), anchor="mm")
    for k in range(2): d.ellipse([370 + k * 70, 50, 420 + k * 70, 100], fill=(60, 60, 76))
    return c
@lru_cache(None)
def trees_img():
    c = Image.new("RGBA", (620, 760), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    for k, (x, h) in enumerate(((90, 700), (260, 620), (430, 740), (560, 560))):
        d.rectangle([x - 18, 760 - h * 0.45, x + 18, 760], fill=(6, 8, 14))
        for j in range(4): w = 150 - j * 30; y = 760 - h + j * h * 0.13; d.polygon([(x - w, y + h * 0.3), (x, y), (x + w, y + h * 0.3)], fill=(8, 12, 20))
    return c
@lru_cache(None)
def phone_img(text="UNKNOWN", sub=""):
    c = Image.new("RGBA", (420, 800), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 419, 799], radius=56, fill=(14, 14, 20), outline=(60, 60, 76), width=8)
    d.rounded_rectangle([22, 22, 397, 777], radius=40, fill=(20, 26, 44))
    d.text((210, 260), text, font=fnt("Anton-Regular.ttf", 54), fill=WHITE, anchor="mm")
    if sub: d.text((210, 330), sub, font=fnt("Poppins-Black.ttf", 28), fill=(180, 180, 200), anchor="mm")
    d.ellipse([70, 620, 170, 720], fill=(40, 190, 90)); d.ellipse([250, 620, 350, 720], fill=(220, 40, 50))
    return c
def prop(img, p, t, ls):
    k = p["k"]; s = p.get("s", 1.0)
    if k == "car_broken":
        on = p.get("hazard") and (t * 1.6) % 1 < 0.5
        paste_c(img, car_broken_img(on, p.get("baby", False)), p["x"], p["y"] - 140 * s, s)
        if on:
            g = Image.new("RGBA", (300, 300), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([60, 60, 240, 240], fill=(255, 150, 30, 90))
            for hx in (-280, 280): paste_c(img, g.filter(ImageFilter.GaussianBlur(30)), p["x"] + hx * s, p["y"] - 135 * s, s)
    elif k == "radio": paste_c(img, radio_img(p.get("on", False) or ls.get("radio", False)), p["x"], p["y"], s)
    elif k == "trees": paste_c(img, trees_img(), p["x"], p["y"] - 380 * s, s)
    elif k == "phone": paste_c(img, phone_img(p.get("text", "UNKNOWN"), p.get("sub", "")), p["x"], p["y"], s, rot=p.get("rot", -6))
    elif k == "emoji": paste_c(img, emoji(p["e"], p.get("size", 160)), p["x"], p["y"], s)
PROPS = ("car_broken", "radio", "trees", "phone", "emoji")

# ======================= FX
def rain(img, t, n=90, glass=False):
    d = ImageDraw.Draw(img)
    for k in range(n):
        r = np.random.default_rng(k); x = r.uniform(0, W); sp = r.uniform(1400, 2200); y = (r.uniform(0, H) + t * sp) % (H + 200) - 100
        if glass:
            gx = 80 + x * 0.85; gy = (r.uniform(0, 760) + t * 40 * r.uniform(0.3, 1.5)) % 700 + 330
            d.ellipse([gx, gy, gx + 7, gy + 16], fill=(150, 180, 220, 140)); d.line([(gx + 3, gy - 30), (gx + 3, gy)], fill=(150, 180, 220, 60), width=2)
        else: d.line([(x, y), (x - 8, y + 40)], fill=(150, 170, 210, 110), width=3)
def headlights(img, t):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.polygon([(200, H), (470, 1000), (610, 1000), (880, H)], fill=(255, 240, 190, 60)); img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
def fog(img, t):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for k in range(4): x = (k * 400 + t * 40) % (W + 600) - 300; d.ellipse([x - 400, 1000 + k * 50, x + 400, 1300 + k * 50], fill=(150, 160, 190, 40))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(40)))
def vignette(img, col=(0, 0, 0), strength=230):
    v = vignette_mask(); lay = Image.new("RGBA", (W, H), col + (0,)); lay.putalpha(v.point(lambda a: int(a * strength / 255))); img.alpha_composite(lay)
@lru_cache(None)
def vignette_mask():
    m = Image.new("L", (W, H), 255); ImageDraw.Draw(m).ellipse([-200, 150, W + 200, H - 150], fill=0); return m.filter(ImageFilter.GaussianBlur(180))
def grain(img, t):
    # light, slow film grain (changes 6x a second, coarse) - fine per-frame noise made the mp4 ~6x bigger
    r = np.random.default_rng(int(t * 6)); n = (r.random((H // 8, W // 8)) * 40).astype(np.uint8)
    g = Image.fromarray(n, "L").resize((W, H), Image.BILINEAR); lay = Image.new("RGBA", (W, H), (255, 255, 255, 0)); lay.putalpha(g.point(lambda v: v // 4)); img.alpha_composite(lay)

# ======================= CAPTIONS + HUD
def caption(img, t):
    cur = next((l for l in LINES if l.get("mode") != "beat" and l["start"] - 0.05 <= t < l["end"] + 0.2), None)
    if not cur or cur.get("final"): return
    ws = cur["words"]; hl = max([i for i, w in enumerate(ws) if w["t"] <= t] or [0])
    band = Image.new("RGBA", (W, 440), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
    for y in range(440): bd.line([(0, y), (W, y)], fill=(4, 4, 10, int(min(215, y * 1.2))))
    img.alpha_composite(band, (0, 1400))
    if NAMES.get(cur["who"]): nm, col = NAMES[cur["who"]]; paste_c(img, pill(nm, 34, col), W / 2, 1515, eob((t - cur["start"]) / 0.2))
    parts = [text_img(w["w"].replace('"', "").upper(), "Poppins-Black.ttf", 60, YEL if i == hl else WHITE, 6, INK) for i, w in enumerate(ws)]
    rows, row, rw = [], [], 0
    for p in parts:
        if row and rw + p.width > 980: rows.append(row); row, rw = [], 0
        row.append(p); rw += p.width - 10
    if row: rows.append(row)
    y = 1575
    for r in rows[:4]:
        x = (W - sum(p.width - 10 for p in r)) / 2
        for p in r: img.alpha_composite(p, (int(x), int(y))); x += p.width - 10
        y += 76
def hud(img, t):
    if t < 1.6 or "choice" in SHOTS[next((x for x in SHOTL if x["vstart"] <= t < x["vend"]), SHOTL[-1])["shot"]]: return
    paste_c(img, pill(f"KAHANI #{META['n']}", 36, RED), 170, 110, 1.0)
    paste_c(img, text_img("AAP KYA KARTE?", "Anton-Regular.ttf", 44, WHITE, 5, INK), W - 200, 110, 1.0)

# ======================= SHOT DRAW
def clock_pill(img, txt, lt): paste_c(img, pill("🕑 " + txt if False else txt, 50, (20, 20, 30), YEL), W / 2, 260, eob((lt - 0.2) / 0.3), rot=-3)
def choice_screen(img, t, lt, sh, line):
    c = sh["choice"]
    paste_c(img, fit_text("AAP KYA KARTE?", 190, YEL, (230, 40, 50)), W / 2, 330, eob(lt / 0.3) * (1 + 0.02 * math.sin(t * 6)), rot=-3)
    wa = [w for w in line["words"] if w["w"].upper().startswith("A:")]; wb = [w for w in line["words"] if w["w"].upper().startswith("B:")]
    ta = wa[0]["t"] if wa else line["start"] + 2.0; tb = wb[0]["t"] if wb else line["start"] + 4.0
    ta = min(ta, line["start"] + 1.0); tb = min(tb, ta + 0.6)   # options on screen early, so the viewer reads while the question is asked
    for j, (lab, txt, col, tt) in enumerate((("A", c["a"], (200, 40, 50), ta), ("B", c["b"], (40, 90, 200), tb))):
        k = t - tt + 0.15
        if k <= 0: continue
        card = Image.new("RGBA", (960, 230), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
        cd.rounded_rectangle([0, 0, 959, 229], radius=40, fill=col + (235,), outline=WHITE, width=8)
        cd.ellipse([30, 40, 180, 190], fill=WHITE); cd.text((105, 115), lab, font=fnt("Anton-Regular.ttf", 110), fill=col, anchor="mm")
        f = 64
        while fnt("Anton-Regular.ttf", f).getlength(txt) > 720 and f > 36: f -= 4
        cd.text((575, 115), txt, font=fnt("Anton-Regular.ttf", f), fill=WHITE, anchor="mm")
        paste_c(img, card, W / 2, 700 + j * 290, eob(k / 0.3))
    cm = [w for w in line["words"] if w["w"].lower().startswith("comment")]
    if cm and t > cm[0]["t"] - 0.1:
        k = t - cm[0]["t"] + 0.1
        paste_c(img, pill("COMMENT MEIN LIKHO: A YA B 👇" if False else "COMMENT MEIN LIKHO: A YA B", 52, YEL, INK), W / 2, 1320, eob(k / 0.3) * (1 + 0.04 * math.sin(t * 8)))
    kl = [w for w in line["words"] if w["w"].lower().startswith("kal")]
    if kl and t > kl[0]["t"]: paste_c(img, text_img("KAL: NAYI KAHANI • NAYA SAWAAL", "Poppins-Black.ttf", 46, WHITE, 5, INK), W / 2, 1480, eob((t - kl[0]["t"]) / 0.3))
    paste_c(img, emoji("🤔", 150), 930, 180, eob((lt - 0.4) / 0.3), rot=10 * math.sin(t * 3))

def draw_shot(img, t, sh_l):
    sh = SHOTS[sh_l["shot"]]; lt = t - sh_l["vstart"]
    lines_here = [l for l in LINES if l["shot"] == sh_l["shot"]]
    cur = next((l for l in lines_here if l["start"] - 0.05 <= t < l["end"] + 0.07), None) or max([l for l in lines_here if l["start"] <= t] or lines_here[:1], key=lambda l: l["start"])
    img.alpha_composite(BG[sh["bg"]]())
    fx = sh.get("fx", [])
    if "headlights" in fx: headlights(img, t)
    fade_t = next((l["start"] for l in lines_here if l.get("fade_chars")), None)
    for p in sh.get("props", []):
        if p["k"] == "trees": prop(img, p, t, cur)
    for ch in sh.get("chars", []):
        fade = 1.0 if fade_t is None or t < fade_t + 0.6 else max(0.0, 1 - (t - fade_t - 0.6) / 0.8)
        if ch.get("window"):   # seen through the car window: clip to window + bluish
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); person(lay, ch, t, speaking=cur.get("who") in ("F", "X", "W", "O") and cur["start"] <= t <= cur["end"])
            m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([78, 318, 1002, 1042], radius=30, fill=255)
            lay.putalpha(Image.fromarray(np.minimum(np.array(lay.getchannel("A")), np.array(m)))); img.alpha_composite(lay)
        else: person(img, ch, t, speaking=cur.get("who") in ("F", "X", "W", "O", "P") and cur["start"] <= t <= cur["end"], fade=fade)
    for p in sh.get("props", []):
        if p["k"] != "trees": prop(img, p, t, cur)
    if "rain" in fx: rain(img, t)
    if "rain_glass" in fx: rain(img, t, 40, glass=True)
    if "fog" in fx: fog(img, t)
    if "flicker" in fx and (t * 7.3) % 1 < 0.18: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 120)))
    vignette(img)
    if "red" in fx: vignette(img, (150, 0, 10), int(120 + 60 * math.sin(t * 6)))
    if "heartbeat" in fx:
        ph = (t % 0.85); k = math.exp(-ph * 10) + 0.6 * math.exp(-max(0, ph - 0.24) * 10) * (ph > 0.24)
        vignette(img, (170, 0, 20), int(min(255, 90 + 140 * k)))
    if "choice" in sh: choice_screen(img, t, lt, sh, lines_here[-1])
    if sh.get("left"):   # split screen: two sides of the dilemma
        L_, R_ = sh["left"], sh["right"]
        paste_c(img, emoji(L_["e"], 230), 290, 650, eob((lt - 0.1) / 0.3), rot=-6)
        paste_c(img, fit_text(L_["t"], 100, WHITE, (230, 40, 50), 480), 290, 900, eob((lt - 0.2) / 0.3), rot=-4)
        rt = cur["words"][len(cur["words"]) // 2]["t"] if cur.get("words") else sh_l["start"] + 1.5
        if t > rt - 0.2:
            paste_c(img, emoji(R_["e"], 230), 790, 1000, eob((t - rt + 0.2) / 0.3), rot=6)
            paste_c(img, fit_text(R_["t"], 100, WHITE, (40, 90, 230), 480), 790, 1250, eob((t - rt) / 0.3), rot=4)
        paste_c(img, fit_text("VS", 150, YEL, (0, 0, 0)), 540, 1060, eob((lt - 0.5) / 0.3))
    if sh.get("clock"): clock_pill(img, sh["clock"], lt)
    if sh.get("pill"): paste_c(img, pill(sh["pill"], 46, RED), W / 2, 260, eob((lt - 0.3) / 0.3), rot=-2)
    if sh.get("big"): paste_c(img, fit_text(sh["big"], 130, WHITE, (230, 40, 50)), W / 2, 420, eob((lt - 0.2) / 0.3), rot=-3)
    for l in lines_here:   # per-line pop texts
        if "pop" in l and l["start"] - 0.05 <= t < l["end"] + 0.8:
            k = t - l["start"] + 0.05
            if l.get("mode") == "beat" or "THAK" in l["pop"]: stamp(img, l["pop"], W / 2, 560, k, YEL, -8, 120)
            else: paste_c(img, pill(l["pop"], 50, RED), W / 2, 420, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=3)
    return img

# ======================= COLD-OPEN HOOK (eye + ear catching first 1.5 s; the audio sting is in thriller_audio.py)
HOOK_LEN = 1.5
def hook_fx(img, t):
    hk = META.get("hook")
    if not hk or t >= HOOK_LEN: return img
    out = 1 - eio((t - (HOOK_LEN - 0.3)) / 0.3)
    if t < 0.55:
        a = 26 * (1 - t / 0.55); dx, dy = int(a * math.sin(t * 95)), int(a * math.cos(t * 71))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 255)); sh.alpha_composite(img, (max(dx, 0), max(dy, 0)), (max(-dx, 0), max(-dy, 0))); img = sh
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(120 * out))))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); cx, cy = W / 2, 820
    for k in range(16):
        a0 = k / 16 * 2 * math.pi + t * 0.9; a1 = a0 + math.pi / 16
        d.polygon([(cx, cy), (cx + math.cos(a0) * 1500, cy + math.sin(a0) * 1500), (cx + math.cos(a1) * 1500, cy + math.sin(a1) * 1500)],
                  fill=(200, 20, 40, int(150 * out)) if k % 2 else (20, 10, 30, int(170 * out)))
    img.alpha_composite(lay)
    sc = (2.4 - 1.4 * eo(min(1, t / 0.18))) * (1 + 0.03 * math.sin(t * 14))
    if hk.get("emoji"): paste_c(img, emoji(hk["emoji"], 220), W / 2, 560, eob((t - 0.1) / 0.2) * out, rot=-10 + 6 * math.sin(t * 9))
    paste_c(img, fit_text(hk["text"], 180, WHITE, (230, 30, 50)), cx, cy, sc * out, rot=-4, alpha=max(0.0, min(1.0, out)))
    if hk.get("sub"): paste_c(img, pill(hk["sub"], 58, RED), cx, cy + 190, eob((t - 0.3) / 0.2) * out, rot=3)
    if t < 0.09: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - t / 0.09)))))
    return img

def frame(t, plain=False):
    s = next((x for x in SHOTL if x["vstart"] <= t < x["vend"]), SHOTL[-1]); lt = t - s["vstart"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255)); img = draw_shot(img, t, s)
    z = 1 + 0.06 * eio(lt / max(1.0, s["vend"] - s["vstart"]))   # slow creeping push-in
    beat_shake = any(l.get("shake") and l["start"] <= t < l["end"] + 0.3 for l in LINES)
    if beat_shake: z += 0.03
    cw, ch = W / z, H / z
    ox = (math.sin(t * 60) * 14) if beat_shake else 0
    img = img.resize((W, H), Image.BILINEAR, box=((W - cw) / 2 + ox, (H - ch) / 2 * 0.6, (W + cw) / 2 + ox, (H - ch) / 2 * 0.6 + ch))
    if lt < 0.2 and s is not SHOTL[0]: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - lt / 0.2)))))
    grain(img, t)
    if plain: return img.convert("RGB")
    img = hook_fx(img, t); hud(img, t); caption(img, t)
    d = ImageDraw.Draw(img); d.rounded_rectangle([80, 1868, W - 80, 1878], radius=5, fill=(50, 50, 66)); d.rounded_rectangle([80, 1868, 80 + (W - 160) * t / TOTAL, 1878], radius=5, fill=RED)
    return img.convert("RGB")

# ======================= THUMBNAIL (first 2 frames = cover)
THUMB_FRAMES = 2
def make_thumb():
    th = META.get("thumb", {}); t = float(th.get("t", SHOTL[min(1, len(SHOTL) - 1)]["vstart"] + 1.0))
    img = frame(t, plain=True).convert("RGBA").filter(ImageFilter.GaussianBlur(3))
    img.alpha_composite(Image.new("RGBA", (W, H), (10, 0, 6, 110))); vignette(img, (140, 0, 20), 230)
    paste_c(img, pill("AAP KYA KARTE?", 60, RED), W / 2, 330, 1.0, rot=-3)
    paste_c(img, text_img(f"KAHANI #{META['n']}", "Poppins-Black.ttf", 42, WHITE, 5, INK), W / 2, 430, 1.0)
    if th.get("emoji"):
        ring = Image.new("RGBA", (440, 440), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([10, 10, 430, 430], fill=(255, 255, 255, 30), outline=RED, width=18)
        paste_c(img, ring, W / 2, 820, 1.0); paste_c(img, emoji(th["emoji"], 250), W / 2, 820, 1.0, rot=-8)
        paste_c(img, fit_text("?", 220, YEL, (230, 40, 50)), W / 2 + 230, 620, 1.0, rot=12)
    if th.get("l1"): paste_c(img, fit_text(th["l1"], 150, WHITE, (230, 40, 50)), W / 2, 1220, 1.0, rot=-3)
    paste_c(img, fit_text(th.get("l2", "AAP KYA KARTE?"), 200, YEL, (230, 40, 50)), W / 2, 1420, 1.0, rot=-3)
    out = img.convert("RGB"); out.save(f"{D}/thumb.png"); out.save(f"{D}/thumb.jpg", quality=92); return out

if ONLY == "thumb": make_thumb(); print("thumb written"); sys.exit()
if ONLY and ONLY.startswith("still:"):
    for tt in ONLY[6:].split(","): frame(float(tt)).save(f"{D}/still_{tt}.png")
    sys.exit()
THUMB = make_thumb(); n = int(TOTAL * FPS)
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", f"{D}/video.tmp.mp4"], stdin=subprocess.PIPE)
for k in range(THUMB_FRAMES): p.stdin.write(THUMB.tobytes())
for k in range(n):
    p.stdin.write(frame(k / FPS).tobytes())
    if k % 300 == 0: print("frame", k, "/", n, flush=True)
p.stdin.close(); p.wait(); print("rc", p.returncode)
