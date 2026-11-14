"""Hamid: Zero Se Shuru — 2D episode renderer (reusable across episodes).
Usage: hamid_render.py <episode dir> [still:t1,t2,...]"""
import json, math, subprocess, sys
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = sys.argv[1]; ONLY = sys.argv[2] if len(sys.argv) > 2 else None
W, H, FPS, SS = 1080, 1920, 30, 2
TL = json.load(open(f"{D}/timeline.json")); TOTAL = TL["total"]; LINES = TL["lines"]; SCENES = TL["scenes"]
META = json.load(open(f"{D}/meta.json"))
LS = np.load(f"{D}/lipsync.npz"); ENV = {k: LS[k] for k in LS.files}
import os
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"; EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
YEL = (255, 210, 60); WHITE = (255, 255, 255); RED = (230, 60, 70); GRN = (40, 190, 110); INK = (34, 28, 40)
NAMES = {"H": ("HAMID", (60, 150, 255)), "A": ("AMMI", (230, 90, 140)), "B": ("ABBU", (150, 120, 90)), "L": ("BILAL", (255, 130, 40)), "C": ("CHACHA", (110, 140, 170))}

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
@lru_cache(None)
def pill(txt, size, bg, fg=INK, name="Poppins-Black.ttf"):
    ti = text_img(txt, name, size, fg); pw, ph = ti.width + 56, ti.height + 22
    im = Image.new("RGBA", (pw + 10, ph + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 8, pw + 6, ph + 8], radius=ph // 2, fill=(0, 0, 0, 80))
    d.rounded_rectangle([0, 0, pw, ph], radius=ph // 2, fill=bg, outline=INK, width=5)
    im.alpha_composite(ti, ((pw - ti.width) // 2, (ph - ti.height) // 2)); return im
def ssf(im): return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)

# ======================= CHARACTERS
SKIN = {"H": (200, 146, 106), "A": (214, 160, 122), "B": (182, 128, 92), "L": (176, 122, 84), "K": (190, 136, 98), "C": (176, 124, 90)}
HW = 300
@lru_cache(None)
def head(who, eyes, mouth, brows):
    s = SS; c = HW * s; im = Image.new("RGBA", (c, c), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = c / 2, c / 2 + 14 * s, 112 * s; skin = SKIN[who]
    if who == "A":  # dupatta behind head
        d.ellipse([cx - r - 34 * s, cy - r - 34 * s, cx + r + 34 * s, cy + r + 70 * s], fill=(40, 140, 110), outline=INK, width=6 * s)
    for sx in (-1, 1):
        d.ellipse([cx + sx * r - 24 * s, cy - 6 * s, cx + sx * r + 24 * s, cy + 44 * s], fill=skin, outline=INK, width=6 * s)
    d.ellipse([cx - r, cy - r * 1.02, cx + r, cy + r * 1.08], fill=skin, outline=INK, width=7 * s)
    if who == "H":
        d.chord([cx - r - 4 * s, cy - r - 26 * s, cx + r + 4 * s, cy + 6 * s], 180, 360, fill=(25, 22, 28), outline=INK, width=6 * s)
        for k in range(7):
            x = cx - r + 18 * s + k * 32 * s
            d.polygon([(x - 22 * s, cy - r + 14 * s), (x + 4 * s, cy - r - 38 * s - (k % 2) * 10 * s), (x + 24 * s, cy - r + 10 * s)], fill=(25, 22, 28))
        d.chord([cx - 70 * s, cy + 40 * s, cx + 70 * s, cy + r * 1.08], 20, 160, fill=(150, 105, 75, 120))  # stubble
    elif who == "A":
        d.chord([cx - r - 14 * s, cy - r - 30 * s, cx + r + 14 * s, cy + 2 * s], 180, 360, fill=(48, 160, 125), outline=INK, width=6 * s)
        d.line([(cx, cy - r + 8 * s), (cx, cy - r + 30 * s)], fill=(30, 22, 25), width=8 * s)
        d.ellipse([cx + 22 * s, cy + 22 * s, cx + 30 * s, cy + 30 * s], fill=(255, 220, 90))  # nose pin
    elif who == "K":  # Ali, the tuition kid: neat side-parted hair
        d.chord([cx - r - 6 * s, cy - r - 18 * s, cx + r + 6 * s, cy + 10 * s], 180, 360, fill=(40, 30, 28), outline=INK, width=6 * s)
        d.polygon([(cx - r, cy - 30 * s), (cx + 30 * s, cy - r - 8 * s), (cx + r, cy - 40 * s), (cx + r, cy - 70 * s), (cx - r, cy - 70 * s)], fill=(40, 30, 28))
    elif who == "C":  # Chacha (kind stranger): white topi + white beard
        d.chord([cx - 82 * s, cy + 10 * s, cx + 82 * s, cy + r * 1.35], 0, 180, fill=(240, 240, 238), outline=INK, width=5 * s)
        d.rounded_rectangle([cx - r + 8 * s, cy - r - 30 * s, cx + r - 8 * s, cy - r + 34 * s], radius=26 * s, fill=(250, 250, 248), outline=INK, width=6 * s)
        for k in range(5): d.line([(cx - r + 30 * s + k * 40 * s, cy - r - 20 * s), (cx - r + 30 * s + k * 40 * s, cy - r + 26 * s)], fill=(200, 200, 205), width=3 * s)
    elif who == "L":  # Bilal: curly hair puffs + backwards red cap
        for k in range(6):
            x = cx - r + 10 * s + k * 42 * s
            d.ellipse([x - 30 * s, cy - r - 10 * s, x + 30 * s, cy - r + 46 * s], fill=(45, 30, 25), outline=INK, width=4 * s)
        d.chord([cx - r + 6 * s, cy - r - 30 * s, cx + r - 6 * s, cy - 10 * s], 180, 360, fill=(220, 50, 60), outline=INK, width=6 * s)
        d.rounded_rectangle([cx - r - 40 * s, cy - 44 * s, cx - r + 40 * s, cy - 22 * s], radius=10 * s, fill=(190, 35, 45), outline=INK, width=5 * s)
        d.ellipse([cx - 10 * s, cy - r - 38 * s, cx + 10 * s, cy - r - 18 * s], fill=(255, 210, 60), outline=INK, width=3 * s)
    else:
        for sx in (-1, 1):
            d.chord([cx + sx * (r - 8 * s) - 38 * s, cy - 70 * s, cx + sx * (r - 8 * s) + 38 * s, cy + 24 * s], 90 if sx < 0 else -90, 270 if sx < 0 else 90, fill=(170, 170, 175))
        d.chord([cx - 82 * s, cy + 18 * s, cx + 82 * s, cy + r * 1.22], 0, 180, fill=(185, 185, 190), outline=INK, width=5 * s)
    ey = cy - 2 * s
    for sx in (-1, 1):
        ex = cx + sx * 44 * s
        if eyes == "closed":
            d.arc([ex - 22 * s, ey - 12 * s, ex + 22 * s, ey + 12 * s], 10, 170, fill=INK, width=7 * s)
        elif eyes == "happy":
            d.arc([ex - 22 * s, ey - 4 * s, ex + 22 * s, ey + 22 * s], 200, 340, fill=INK, width=8 * s)
        else:
            rr = 28 if eyes == "wide" else 22
            d.ellipse([ex - rr * s, ey - (rr + 4) * s, ex + rr * s, ey + (rr + 4) * s], fill=WHITE, outline=INK, width=5 * s)
            dy = 8 * s if eyes == "down" else 0
            pr = 8 if eyes == "wide" else 11
            d.ellipse([ex - pr * s, ey - pr * s + dy, ex + pr * s, ey + pr * s + dy], fill=INK)
            d.ellipse([ex - 3 * s, ey - 8 * s + dy, ex + 4 * s, ey - 1 * s + dy], fill=WHITE)
        by = ey - 42 * s; bw = 10 * s if who != "A" else 7 * s
        bcol = (25, 22, 28) if who not in ("B", "C") else (150, 150, 155)
        if who == "L": bw = 12 * s
        if brows == "sad":
            d.line([(ex - 22 * s, by + (0 if sx > 0 else 10 * s)), (ex + 22 * s, by + (10 * s if sx > 0 else 0))], fill=bcol, width=bw)
        elif brows == "angry":
            d.line([(ex - 22 * s, by + (12 * s if sx > 0 else 0)), (ex + 22 * s, by + (0 if sx > 0 else 12 * s))], fill=bcol, width=bw)
        elif brows == "up":
            d.arc([ex - 24 * s, by - 14 * s, ex + 24 * s, by + 10 * s], 200, 340, fill=bcol, width=bw)
        else:
            d.line([(ex - 22 * s, by + 4 * s), (ex + 22 * s, by)], fill=bcol, width=bw)
    if who == "B":
        for sx in (-1, 1):
            ex = cx + sx * 44 * s; d.ellipse([ex - 34 * s, ey - 32 * s, ex + 34 * s, ey + 32 * s], outline=INK, width=6 * s)
        d.line([(cx - 10 * s, ey), (cx + 10 * s, ey)], fill=INK, width=6 * s)
    d.arc([cx - 14 * s, cy + 6 * s, cx + 14 * s, cy + 34 * s], 300, 80, fill=INK, width=5 * s)
    my = cy + 62 * s
    if mouth == "sad":
        d.arc([cx - 28 * s, my - 2 * s, cx + 28 * s, my + 26 * s], 200, 340, fill=INK, width=7 * s)
    elif mouth == 0:
        d.arc([cx - 30 * s, my - 22 * s, cx + 30 * s, my + 12 * s], 20, 160, fill=INK, width=7 * s)
    else:
        h = {1: 14, 2: 26, 3: 38}[mouth]; w = {1: 28, 2: 34, 3: 30}[mouth]
        d.rounded_rectangle([cx - w * s, my - h * s / 2, cx + w * s, my + h * s / 2 + 8 * s], radius=min(h, w) * s * 0.9, fill=(110, 20, 35), outline=INK, width=6 * s)
        if h > 18: d.ellipse([cx - 13 * s, my + h * s / 2 - 8 * s, cx + 13 * s, my + h * s / 2 + 6 * s], fill=(235, 90, 110))
        d.rectangle([cx - (w - 8) * s, my - h * s / 2 + 3 * s, cx + (w - 8) * s, my - h * s / 2 + 10 * s], fill=WHITE)
    if who == "C":
        for sx in (-1, 1): d.ellipse([cx + sx * 4 * s - (50 * s if sx < 0 else 0), my - 28 * s, cx + sx * 4 * s + (50 * s if sx > 0 else 0), my - 8 * s], fill=(235, 235, 235), outline=INK, width=3 * s)
    if who == "B":
        for sx in (-1, 1):
            d.ellipse([cx + sx * 4 * s - (56 * s if sx < 0 else 0), my - 30 * s, cx + sx * 4 * s + (56 * s if sx > 0 else 0), my - 6 * s], fill=(160, 160, 165))
    return ssf(im)

@lru_cache(None)
def torso(who):
    s = SS; w, h = 440 * s, 440 * s; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if who == "H":
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(245, 245, 240), outline=INK, width=7 * s)
        d.polygon([(w / 2 - 50 * s, 50 * s), (w / 2, 110 * s), (w / 2 + 50 * s, 50 * s)], fill=SKIN["H"], outline=INK)
        d.line([(w / 2, 110 * s), (w / 2, 220 * s)], fill=INK, width=4 * s)
        for k in range(3): d.ellipse([w / 2 - 7 * s, (130 + 30 * k) * s, w / 2 + 7 * s, (144 + 30 * k) * s], fill=(200, 200, 205), outline=INK, width=2 * s)
    elif who == "A":
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(150, 40, 70), outline=INK, width=7 * s)
        d.polygon([(40 * s, 70 * s), (w - 40 * s, 70 * s), (w - 120 * s, 230 * s), (140 * s, 240 * s)], fill=(48, 160, 125), outline=INK)
    elif who == "K":
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(150, 200, 240), outline=INK, width=7 * s)
        d.polygon([(w / 2 - 50 * s, 50 * s), (w / 2, 110 * s), (w / 2 + 50 * s, 50 * s)], fill=SKIN["K"], outline=INK)
        d.rectangle([w / 2 - 70 * s, 150 * s, w / 2 - 20 * s, 190 * s], outline=INK, width=4 * s)
    elif who == "C":
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(110, 140, 170), outline=INK, width=7 * s)
        d.polygon([(50 * s, 90 * s), (w / 2 - 20 * s, 60 * s), (120 * s, h), (60 * s, h)], fill=(150, 95, 60), outline=INK)   # shawl
        d.polygon([(w - 50 * s, 90 * s), (w / 2 + 20 * s, 60 * s), (w - 120 * s, h), (w - 60 * s, h)], fill=(150, 95, 60), outline=INK)
    elif who == "L":
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(255, 190, 50), outline=INK, width=7 * s)
        d.chord([w / 2 - 60 * s, 20 * s, w / 2 + 60 * s, 100 * s], 0, 180, fill=SKIN["L"], outline=INK, width=5 * s)
        d.rectangle([90 * s, 200 * s, w - 90 * s, 240 * s], fill=(230, 60, 70))
    else:
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(200, 200, 195), outline=INK, width=7 * s)
        d.polygon([(85 * s, 110 * s), (w / 2 - 30 * s, 70 * s), (w / 2 - 30 * s, h), (75 * s, h)], fill=(120, 80, 50), outline=INK)
        d.polygon([(w - 85 * s, 110 * s), (w / 2 + 30 * s, 70 * s), (w / 2 + 30 * s, h), (w - 75 * s, h)], fill=(120, 80, 50), outline=INK)
    return ssf(im)

@lru_cache(None)
def arm(who):
    s = SS; L = 220; im = Image.new("RGBA", (66 * s, (L + 66) * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sleeve = {"H": (245, 245, 240), "A": (150, 40, 70), "B": (200, 200, 195), "L": (255, 190, 50), "K": (150, 200, 240), "C": (110, 140, 170)}[who]
    d.rounded_rectangle([6 * s, 6 * s, 60 * s, (L - 40) * s], radius=26 * s, fill=sleeve, outline=INK, width=6 * s)
    d.ellipse([4 * s, (L - 58) * s, 62 * s, L * s], fill=SKIN[who], outline=INK, width=6 * s)
    return ssf(im)
def rot_arm(img, who, sx, sy, angle, sc=1.0):
    a = arm(who); big = Image.new("RGBA", (a.height * 2, a.height * 2), (0, 0, 0, 0))
    big.alpha_composite(a, (big.width // 2 - a.width // 2, big.height // 2 - 20)); big = big.rotate(angle, Image.BICUBIC)
    paste_c(img, big, sx, sy, sc)

def speaking(who, t):
    e = ENV.get(who); k = int(t * FPS)
    return float(e[k]) if e is not None and k < len(e) else 0.0
def blink(t, seed): return (t + seed) % 3.6 < 0.11

def draw_char(img, who, x, y, t, mood="n", sc=1.0, arms=(-15, 15), hold=None, laugh=False):
    amp = speaking(who, t)
    if laugh: amp = max(amp, 0.35 + 0.5 * abs(math.sin(t * 11 + x)))
    talking = amp > 0.08
    breathe = math.sin(t * 2.1 + hash(who) % 3) * 4 * sc
    bob = math.sin(t * 9) * 5 * min(1, amp * 1.5) * sc if talking else 0
    ga = (math.sin(t * 4.2) * 0.5 + 0.5) * 40 if talking else 0
    rot_arm(img, who, x - 150 * sc, y + 110 * sc + breathe, arms[0] - ga * 0.3, sc)
    rot_arm(img, who, x + 150 * sc, y + 110 * sc + breathe, arms[1] + ga, sc)
    paste_c(img, torso(who), x, y + 190 * sc + breathe, sc)
    if hold: hold(img, x, y, sc)
    eyes = {"sad": "down", "happy": "happy" if (not talking or laugh) else "open", "shock": "wide", "det": "open"}.get(mood, "open")
    if blink(t, hash(who) % 5 * 0.7) and eyes in ("open", "down"): eyes = "closed"
    if mood == "sleep": eyes = "closed"
    brows = {"sad": "sad", "shock": "up", "det": "angry", "happy": "up"}.get(mood, "n")
    if talking: mouth = 1 if amp < 0.3 else (2 if amp < 0.6 else 3)
    else: mouth = "sad" if mood in ("sad",) else (2 if mood == "shock" else 0)
    paste_c(img, head(who, eyes, mouth, brows), x, y - 70 * sc + breathe + bob, sc, rot=math.sin(t * 1.3 + x) * 2)

# ======================= BACKGROUNDS
def grad(c1, c2, h=H):
    im = Image.new("RGBA", (W, h)); d = ImageDraw.Draw(im)
    for y in range(h): d.line([(0, y), (W, y)], fill=mixc(c1, c2, y / h) + (255,))
    return im

@lru_cache(None)
def bg_room(mode):
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im)
    wall = {"day": (120, 200, 190), "night": (40, 60, 95), "eve": (205, 150, 110)}[mode]
    floor = {"day": (190, 140, 100), "night": (60, 50, 60), "eve": (150, 100, 70)}[mode]
    d.rectangle([0, 0, W * s, 1250 * s], fill=wall)
    for y in range(0, 1250, 70): d.line([(0, y * s), (W * s, y * s)], fill=mixc(wall, (0, 0, 0), 0.06), width=2 * s)
    d.rectangle([0, 1250 * s, W * s, H * s], fill=floor)
    if mode != "eve":
        wx = 640; sky = (150, 210, 250) if mode == "day" else (20, 30, 60)
        d.rectangle([wx * s, 330 * s, (wx + 330) * s, 700 * s], fill=sky, outline=INK, width=10 * s)
        for k in range(1, 6): d.line([((wx + k * 55) * s, 330 * s), ((wx + k * 55) * s, 700 * s)], fill=(60, 60, 70), width=5 * s)
        d.line([(wx * s, 515 * s), ((wx + 330) * s, 515 * s)], fill=(60, 60, 70), width=5 * s)
        if mode == "night":
            d.ellipse([(wx + 230) * s, 370 * s, (wx + 290) * s, 430 * s], fill=(250, 245, 210))
        # calendar
        d.rectangle([120 * s, 360 * s, 300 * s, 560 * s], fill=(250, 250, 245), outline=INK, width=6 * s)
        d.rectangle([120 * s, 360 * s, 300 * s, 410 * s], fill=RED, outline=INK, width=6 * s)
        for r in range(4):
            for c in range(5): d.rectangle([(138 + c * 32) * s, (430 + r * 30) * s, (156 + c * 32) * s, (446 + r * 30) * s], fill=(200, 200, 200))
    else:
        # courtyard evening: brick wall + string light + plant
        for y in range(300, 1250, 60):
            off = 0 if (y // 60) % 2 else 60
            for x in range(-60 + off, W, 120): d.rectangle([x * s, y * s, (x + 112) * s, (y + 52) * s], fill=mixc(wall, (150, 70, 50), 0.35))
        d.rectangle([0, 0, W * s, 300 * s], fill=(250, 170, 110))
        d.ellipse([760 * s, 90 * s, 900 * s, 230 * s], fill=(255, 220, 140))
    return ssf(im)

def fan(img, cx, cy, t, col=(240, 240, 240)):
    ov = Image.new("RGBA", (360, 360), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for k in range(3):
        a = t * 6 + k * 2.094
        x2, y2 = 180 + math.cos(a) * 170, 180 + math.sin(a) * 40
        d.line([(180, 180), (x2, y2)], fill=col + (255,), width=26)
    d.ellipse([160, 165, 200, 195], fill=(120, 120, 130), outline=INK, width=3)
    img.alpha_composite(ov, (int(cx - 180), int(cy - 180)))
    ImageDraw.Draw(img).line([(cx, 0), (cx, cy - 10)], fill=(100, 100, 110), width=8)

@lru_cache(None)
def skyline(mode):
    top, bot = {"golden": ((255, 150, 90), (255, 215, 150)), "dawn": ((90, 120, 190), (255, 190, 150))}[mode]
    im = grad(top, bot, H)
    d = ImageDraw.Draw(im)
    sun = (255, 230, 150) if mode == "golden" else (255, 210, 170)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([600, 520, 900, 820], fill=sun + (255,))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(6)))
    sil = (70, 40, 60) if mode == "golden" else (50, 50, 80)
    base = 1180
    # Minar-style tower silhouette
    d.polygon([(230, base), (250, 820), (268, 470), (276, 470), (294, 820), (314, base)], fill=sil)
    for k in range(5): d.polygon([(190 + k * 30, base), (215 + k * 30, 1060), (240 + k * 30, base)], fill=sil)
    d.rectangle([262, 440, 282, 470], fill=sil); d.polygon([(266, 440), (272, 400), (278, 440)], fill=sil)
    # mosque domes + minarets
    for (x, r) in [(560, 70), (660, 95), (760, 70)]:
        d.pieslice([x - r, 980 - r, x + r, 980 + r], 180, 360, fill=sil); d.polygon([(x - 4, 980 - r), (x, 980 - r - 40), (x + 4, 980 - r)], fill=sil)
    d.rectangle([480, 980, 840, base], fill=sil)
    for x in (465, 855):
        d.rectangle([x - 14, 760, x + 14, base], fill=sil); d.polygon([(x - 20, 760), (x, 700), (x + 20, 760)], fill=sil)
    # rooftops + water tanks
    r = np.random.default_rng(3); x = -20
    while x < W:
        w = r.uniform(80, 160); h = r.uniform(60, 220)
        d.rectangle([x, base - h + 120, x + w, H], fill=mixc(sil, (0, 0, 0), 0.15))
        if r.random() < 0.6: d.rounded_rectangle([x + 20, base - h + 80, x + 70, base - h + 122], radius=8, fill=mixc(sil, (0, 0, 0), 0.15))
        x += w + 4
    d.rectangle([0, 1300, W, H], fill=mixc(sil, (0, 0, 0), 0.3))
    for k in range(3): d.line([(0, 1060 + k * 22), (W, 1110 + k * 30)], fill=mixc(sil, (0, 0, 0), 0.4), width=3)
    return im

def kites(img, t, n=4):
    d = ImageDraw.Draw(img)
    cols = [(230, 60, 70), (60, 150, 255), (255, 200, 40), (40, 190, 110)]
    for k in range(n):
        x = 150 + k * 230 + math.sin(t * 0.7 + k) * 40; y = 200 + (k % 2) * 160 + math.cos(t * 0.9 + k * 2) * 30
        a = math.sin(t * 1.5 + k) * 0.3; sz = 46
        pts = [(x + math.sin(a) * sz, y - math.cos(a) * sz), (x + math.cos(a) * sz * 0.8, y + math.sin(a) * sz * 0.8),
               (x - math.sin(a) * sz, y + math.cos(a) * sz), (x - math.cos(a) * sz * 0.8, y - math.sin(a) * sz * 0.8)]
        d.polygon(pts, fill=cols[k % 4] + (255,), outline=INK)
        tail = [(pts[2][0] + math.sin(t * 5 + j + k) * 10, pts[2][1] + j * 14) for j in range(6)]
        d.line([pts[2]] + tail, fill=(250, 250, 250), width=3)
        d.line([pts[2], (x + 300, 1400)], fill=(255, 255, 255, 90), width=1)

# ======================= PROPS
@lru_cache(None)
def result_card():
    im = Image.new("RGBA", (260, 180), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 259, 179], radius=14, fill=(252, 250, 240), outline=INK, width=5)
    d.text((18, 14), "RESULT", font=fnt("Poppins-Black.ttf", 30), fill=INK)
    d.text((18, 58), "82%", font=fnt("Anton-Regular.ttf", 86), fill=GRN)
    return im
def hold_card(img, x, y, sc): paste_c(img, result_card(), x + 120 * sc, y + 200 * sc, sc * 0.9, rot=-6)

@lru_cache(None)
def phone_screen():
    w, h = 560, 900; im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w + 39, h + 39], radius=60, fill=(25, 25, 30), outline=INK, width=6)
    d.rounded_rectangle([20, 20, w + 19, h + 19], radius=44, fill=(245, 247, 252))
    d.rectangle([20, 70, w + 19, 190], fill=(30, 90, 170))
    d.text((50, 100), "UNIVERSITY ADMISSIONS", font=fnt("Poppins-Black.ttf", 30), fill=WHITE)
    d.text((50, 240), "BS Engineering", font=fnt("Poppins-Black.ttf", 40), fill=INK)
    d.text((50, 310), "Fee per year", font=fnt("Poppins-Bold.ttf" if False else "Poppins-Black.ttf", 28), fill=(120, 120, 130))
    d.rounded_rectangle([50, 600, w - 10, 690], radius=20, fill=(30, 90, 170)); d.text((150, 618), "APPLY NOW", font=fnt("Poppins-Black.ttf", 38), fill=WHITE)
    return im

@lru_cache(None)
def form_paper():
    im = Image.new("RGBA", (300, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 299, 399], fill=(250, 250, 245), outline=INK, width=4)
    d.text((22, 18), "ADMISSION", font=fnt("Poppins-Black.ttf", 34), fill=INK); d.text((22, 60), "FORM", font=fnt("Poppins-Black.ttf", 34), fill=INK)
    for k in range(9): d.line([(22, 130 + k * 28), (276, 130 + k * 28)], fill=(170, 170, 180), width=3)
    return im

# ======================= HUD + CAPTIONS
def hud(img, t):
    if t < SCENES[1]["vstart"] + 1.6: return
    paste_c(img, pill(f"DAY {META['day']}", 40, YEL), 140, 110, 1.0)
    m = META["money"]
    pay = ([l for l in LINES if l["scene"] == META.get("money_scene", "pay")] or [None])[-1]
    if "money_steps" in META:   # [[line index, amount, delay s], ...] — counter rolls to each amount
        m = META["money_start"]
        for idx, amt, dl in META["money_steps"]:
            k = eo((t - LINES[idx]["start"] - dl) / 0.8)
            if k > 0: m = int(lerp(m, amt, k))
    elif "money_start" in META and pay:
        k = eo((t - pay["end"] + 0.6) / 1.0); m = int(lerp(META["money_start"], META["money"], k))
    paste_c(img, pill(f"Rs {m}", 40, WHITE, GRN), W - 150, 110, 1.0)

def caption(img, t):
    cur = next((l for l in LINES if l.get("mode") != "beat" and l["start"] - 0.05 <= t < l["end"] + 0.2), None)
    if not cur: return
    ws = cur["words"]; hl = max([i for i, w in enumerate(ws) if w["t"] <= t] or [0])
    band = Image.new("RGBA", (W, 420), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
    for y in range(420): bd.line([(0, y), (W, y)], fill=(10, 8, 20, int(min(200, y * 1.2))))
    img.alpha_composite(band, (0, 1420))
    if cur["mode"] == "talk":
        nm, col = NAMES[cur["who"]]; paste_c(img, pill(nm, 34, col, WHITE), W / 2, 1520, eob((t - cur["start"]) / 0.2))
    parts = [text_img(w["w"].replace('"', "").upper(), "Poppins-Black.ttf", 60, YEL if i == hl else WHITE, 6, INK) for i, w in enumerate(ws)]
    rows, row, rw = [], [], 0
    for p in parts:
        if row and rw + p.width > 980: rows.append(row); row, rw = [], 0
        row.append(p); rw += p.width - 10
    if row: rows.append(row)
    y = 1580
    for r in rows[:4]:
        x = (W - sum(p.width - 10 for p in r)) / 2
        for p in r: img.alpha_composite(p, (int(x), int(y))); x += p.width - 10
        y += 76

# ======================= SCENES
def L(scene): return [l for l in LINES if l["scene"] == scene]

def sc_hook(img, t, lt):
    img.alpha_composite(bg_room("night")); fan(img, 360, 210, t, (90, 100, 130))
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([300, 600, 900, 1300], fill=(255, 200, 120, 70))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(80)))
    draw_char(img, "H", W / 2, 900, t, "sad", 1.25, arms=(-10, 40), hold=hold_card)
    paste_c(img, glow_text("82% NUMBER…", "Anton-Regular.ttf", 120, WHITE, (90, 160, 255)), W / 2, 330, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("PHIR BHI COLLEGE NAHI?", "Anton-Regular.ttf", 84, YEL, (255, 120, 40)), W / 2, 460, eob((lt - 1.6) / 0.35))

def sc_daycard(img, t, lt):
    img.alpha_composite(skyline("golden")); kites(img, t)
    paste_c(img, glow_text(f"DAY {META['day']}", "Anton-Regular.ttf", 230, WHITE, (255, 120, 40)), W / 2, 560, eob((lt - 0.2) / 0.4))
    paste_c(img, text_img(META["city"].upper(), "Anton-Regular.ttf", 110, YEL, 7, INK), W / 2, 760, eob((lt - 0.7) / 0.35))
    paste_c(img, pill(f"JEB MEIN: Rs {META.get('money_start', META['money'])}", 52, WHITE, GRN), W / 2, 900, eob((lt - 1.4) / 0.35))

def sc_home(img, t, lt):
    img.alpha_composite(bg_room("day")); fan(img, 540, 200, t)
    ls = L("home"); happy_t = ls[1]["start"] if len(ls) > 1 else 1e9
    draw_char(img, "A", 300, 930, t, "happy" if t > happy_t else "n", 1.0)
    draw_char(img, "H", 790, 920, t, "happy" if t > happy_t else "n", 1.0, arms=(-10, 40), hold=hold_card)
    if t > happy_t:
        k = t - happy_t
        for j in range(14):
            r = np.random.default_rng(j); x = r.uniform(80, 1000); sp = r.uniform(250, 420)
            y = 250 + ((k * sp + r.uniform(0, 600)) % 900)
            ImageDraw.Draw(img).rectangle([x, y, x + 14, y + 22], fill=[(255, 200, 40), (230, 60, 70), (60, 150, 255), (40, 190, 110)][j % 4] + (255,))
        paste_c(img, glow_text("82%!", "Anton-Regular.ttf", 160, GRN, (60, 255, 140)), W / 2, 360, eob(k / 0.35) * (1 + 0.04 * math.sin(t * 8)))
    if len(ls) > 2 and t > ls[2]["start"] + 0.6:
        for j in range(2):
            q = ((t - ls[2]["start"]) * 0.8 + j * 0.5) % 1
            paste_c(img, emoji("💧", 30), 300 + (j * 2 - 1) * 46, 900 + q * 90, 1.0, alpha=1 - q)
        paste_c(img, pill("ENGINEER BANEGA!", 46, YEL), 300, 600, eob((t - ls[2]["start"] - 0.6) / 0.3), rot=-6)

def sc_fees(img, t, lt):
    img.alpha_composite(grad((30, 40, 70), (10, 12, 30)))
    zoom = 1.0 + 0.08 * eio(lt / 4)
    ph = phone_screen().copy(); d = ImageDraw.Draw(ph)
    val = int(200000 * eo((lt - 1.3) / 1.8)); s = f"{val:,}"
    # Pakistani grouping 2,00,000
    if val >= 100000: s = f"{val // 100000},{(val % 100000) // 1000:02d},{val % 1000:03d}"
    d.text((50, 360), f"Rs {s}", font=fnt("Anton-Regular.ttf", 100), fill=RED)
    paste_c(img, ph, W / 2, 760, zoom * eob(lt / 0.4))
    if lt > 3.0: paste_c(img, emoji("😳", 150), W / 2 + 300, 1250, eob((lt - 3.0) / 0.3))

def charpai(img):
    d = ImageDraw.Draw(img)
    d.rectangle([90, 1150, 560, 1180], fill=(150, 100, 60), outline=INK, width=4)
    for x in range(100, 560, 22): d.line([(x, 1150), (x + 10, 1180)], fill=(230, 210, 170), width=4)
    for x in (100, 540): d.rectangle([x, 1180, x + 22, 1320], fill=(150, 100, 60), outline=INK, width=4)

def sc_abbu(img, t, lt):
    img.alpha_composite(bg_room("eve"))
    draw_char(img, "B", 320, 900, t, "sad" if t > L("abbu")[0]["end"] else "n", 0.95)
    charpai(img)
    draw_char(img, "H", 820, 880, t, "sad", 1.0)
    vo = L("abbu")[1] if len(L("abbu")) > 1 else None
    if vo and t > vo["start"] + 0.8:
        k = t - vo["start"] - 0.8
        bub = Image.new("RGBA", (420, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(bub)
        d.ellipse([0, 0, 419, 239], fill=(255, 255, 255, 235), outline=INK, width=5)
        for (cx, cy, r) in [(60, 262, 18), (30, 290, 10)]: d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 235), outline=INK, width=4)
        bub.alpha_composite(emoji("🏠", 90), (60, 70)); d.text((170, 70), "KIRAYA", font=fnt("Poppins-Black.ttf", 40), fill=INK)
        d.text((170, 120), "BAAQI!", font=fnt("Poppins-Black.ttf", 40), fill=RED)
        paste_c(img, bub, 470, 470, eob(k / 0.35))

def sc_night(img, t, lt):
    img.alpha_composite(bg_room("night"))
    d = ImageDraw.Draw(img)
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([200, 700, 1000, 1500], fill=(255, 200, 110, 110))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(90)))
    draw_char(img, "H", W / 2, 860, t, "det", 1.1, arms=(-30, 30))
    d = ImageDraw.Draw(img); d.rectangle([0, 1250, W, 1290], fill=(120, 80, 50), outline=INK, width=4); d.rectangle([0, 1290, W, 1420], fill=(90, 60, 40))
    ln = L("night")[0]; tear_t = ln["start"] + 0.9
    if t < tear_t: paste_c(img, form_paper(), W / 2, 1150, 1.0, rot=math.sin(t * 2) * 2)
    else:
        k = t - tear_t; p = form_paper()
        lft = p.crop((0, 0, 150, 400)); rgt = p.crop((150, 0, 300, 400))
        paste_c(img, lft, W / 2 - 75 - k * 260, 1150 + k * k * 300, 1.0, rot=k * 70)
        paste_c(img, rgt, W / 2 + 75 + k * 260, 1150 + k * k * 300, 1.0, rot=-k * 70)
    pw = [w for w in ln["words"] if w["w"].startswith("PLAN")]
    if pw and t > pw[0]["t"] - 0.6:
        k = t - (pw[0]["t"] - 0.6)
        diary = Image.new("RGBA", (520, 330), (0, 0, 0, 0)); dd = ImageDraw.Draw(diary)
        dd.rounded_rectangle([0, 0, 519, 329], radius=16, fill=(250, 245, 225), outline=INK, width=6)
        for j in range(6): dd.line([(30, 70 + j * 44), (490, 70 + j * 44)], fill=(180, 200, 230), width=3)
        txt = text_img("PLAN B", "Anton-Regular.ttf", 150, (40, 60, 170))
        rev = eo(k / 1.0); cw = int(txt.width * rev)
        if cw > 2: diary.alpha_composite(txt.crop((0, 0, cw, txt.height)), (50, 70))
        paste_c(img, diary, W / 2, 470, eob(k / 0.35), rot=-3)

def sc_end(img, t, lt):
    img.alpha_composite(skyline("dawn")); kites(img, t, 3)
    draw_char(img, "H", W / 2, 1000, t, "det", 1.15, arms=(-20, 20))
    paste_c(img, glow_text("ZERO SE SHURU", "Anton-Regular.ttf", 140, WHITE, (255, 140, 40)), W / 2, 330, eob((lt - 0.4) / 0.4))
    paste_c(img, pill(f"DAY {META['day'] + 1} KAL • FOLLOW +", 50, RED, WHITE), W / 2, 480, eob((lt - 2.2) / 0.35) * (1 + 0.04 * math.sin(t * 8)))

# ======================= DAY 2+: DHABA WORLD (reusable)
@lru_cache(None)
def bg_dhaba(mode):
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im)
    sky = {"day": ((255, 200, 120), (250, 230, 180)), "night": ((25, 30, 60), (60, 50, 80))}[mode]
    for y in range(0, 700 * s, 4): d.rectangle([0, y, W * s, y + 4], fill=mixc(sky[0], sky[1], y / (700 * s)))
    wall = (200, 120, 70) if mode == "day" else (110, 70, 55); dark = mixc(wall, (0, 0, 0), 0.25)
    d.rectangle([0, 520 * s, W * s, 1250 * s], fill=wall)
    for y in range(540, 1250, 50): d.line([(0, y * s), (W * s, y * s)], fill=dark, width=2 * s)
    # tin roof awning
    d.polygon([(-20 * s, 420 * s), (W * s + 20 * s, 420 * s), (W * s + 20 * s, 540 * s), (-20 * s, 540 * s)], fill=(150, 160, 170), outline=INK)
    for x in range(0, W, 60): d.line([(x * s, 420 * s), (x * s, 540 * s)], fill=(110, 120, 130), width=4 * s)
    # sign board (original, no brand)
    d.rounded_rectangle([290 * s, 250 * s, 790 * s, 400 * s], radius=20 * s, fill=(40, 120, 80), outline=INK, width=8 * s)
    d.text((540 * s, 325 * s), "CHAI DHABA", font=fnt("Anton-Regular.ttf", 90 * s), fill=(255, 230, 120), anchor="mm")
    for x in (310, 770): d.line([(x * s, 180 * s), (x * s, 250 * s)], fill=INK, width=5 * s)
    # shelf with cups
    d.rectangle([60 * s, 640 * s, 460 * s, 660 * s], fill=(120, 80, 50), outline=INK, width=4 * s)
    for k in range(6):
        x = 80 + k * 64; d.rounded_rectangle([x * s, 590 * s, (x + 44) * s, 640 * s], radius=6 * s, fill=(245, 245, 240, 220), outline=INK, width=3 * s)
    # counter + stove
    d.rectangle([0, 1180 * s, W * s, H * s], fill=(90, 70, 60) if mode == "day" else (50, 40, 45))
    d.rectangle([600 * s, 960 * s, 1060 * s, 1180 * s], fill=(160, 110, 70), outline=INK, width=6 * s)
    d.rectangle([660 * s, 900 * s, 980 * s, 960 * s], fill=(70, 70, 80), outline=INK, width=5 * s)
    # bulb
    d.line([(540 * s, 420 * s), (540 * s, 560 * s)], fill=INK, width=4 * s)
    d.ellipse([515 * s, 555 * s, 565 * s, 610 * s], fill=(255, 235, 150), outline=INK, width=3 * s)
    return ssf(im)

def bulb_glow(img, a=60):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([340, 380, 740, 780], fill=(255, 220, 120, a))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(70)))

@lru_cache(None)
def kettle_img():
    im = Image.new("RGBA", (300, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.arc([180, 60, 290, 190], 270, 90, fill=INK, width=14)
    d.polygon([(40, 120), (0, 60), (14, 54), (70, 110)], fill=(190, 190, 200), outline=INK)
    d.ellipse([40, 70, 230, 250], fill=(190, 190, 200), outline=INK, width=7)
    d.rectangle([90, 50, 180, 90], fill=(170, 170, 180), outline=INK, width=6)
    d.ellipse([120, 30, 150, 58], fill=INK)
    return im

def steam(img, x, y, t, n=3, sc=1.0):
    d = ImageDraw.Draw(img)
    for k in range(n):
        q = (t * 0.7 + k / n) % 1
        cx = x + math.sin(t * 3 + k * 2) * 20 * sc; cy = y - q * 220 * sc; r = (18 + q * 30) * sc
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, int(150 * (1 - q))))

@lru_cache(None)
def cup_img(broken=False):
    im = Image.new("RGBA", (90, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(8, 10), (82, 10), (70, 95), (20, 95)], fill=(245, 240, 230, 235), outline=INK)
    d.rectangle([14, 26, 76, 50], fill=(180, 120, 70))
    return im

@lru_cache(None)
def notes_img(amount, w=260):
    im = Image.new("RGBA", (w + 30, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k in range(3):
        d.rounded_rectangle([k * 12, 30 - k * 12, w + k * 12, 140 - k * 12], radius=10, fill=(120, 190, 130) if k < 2 else (150, 210, 150), outline=INK, width=4)
    d.text((w // 2 + 24, 76), f"Rs {amount}", font=fnt("Anton-Regular.ttf", 56), fill=INK, anchor="mm")
    return im
def hold_notes(img, x, y, sc): paste_c(img, notes_img(450, 200), x + 130 * sc, y + 200 * sc, sc * 0.9, rot=-8)
def hold_tray(img, x, y, sc):
    d = ImageDraw.Draw(img); tx, ty = x + 150 * sc, y + 170 * sc
    d.ellipse([tx - 120 * sc, ty - 18 * sc, tx + 120 * sc, ty + 22 * sc], fill=(200, 200, 210), outline=INK, width=5)
    for k in (-1, 0, 1): paste_c(img, cup_img(), tx + k * 70 * sc, ty - 40 * sc, sc * 0.75)

def clock(img, cx, cy, hours):
    d = ImageDraw.Draw(img); r = 90
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 245), outline=INK, width=8)
    for k in range(12):
        a = k / 12 * 2 * math.pi; d.line([(cx + math.sin(a) * 70, cy - math.cos(a) * 70), (cx + math.sin(a) * 80, cy - math.cos(a) * 80)], fill=INK, width=4)
    ah = hours / 12 * 2 * math.pi; am = (hours % 1) * 2 * math.pi
    d.line([(cx, cy), (cx + math.sin(ah) * 45, cy - math.cos(ah) * 45)], fill=INK, width=10)
    d.line([(cx, cy), (cx + math.sin(am) * 68, cy - math.cos(am) * 68)], fill=RED, width=6)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=INK)

def word_t(line, prefix, default=None, exact=False):
    w = [x for x in line["words"] if (x["w"].lower().strip(".,…!?") == prefix.lower() if exact else x["w"].lower().strip(".,…!?").startswith(prefix.lower()))]
    return w[0]["t"] if w else default

def sc_hook_dhaba(img, t, lt):
    img.alpha_composite(bg_dhaba("night")); bulb_glow(img, 90)
    draw_char(img, "H", W / 2, 1040, t, "sad", 1.15, arms=(-10, 40), hold=hold_notes)
    paste_c(img, glow_text("12 GHANTE KAAM…", "Anton-Regular.ttf", 110, WHITE, (90, 160, 255)), W / 2, 560, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("SIRF Rs 450?", "Anton-Regular.ttf", 120, YEL, (255, 120, 40)), W / 2, 690, eob((lt - 1.8) / 0.35))

def sc_dhaba(img, t, lt):
    img.alpha_composite(bg_dhaba("day"))
    paste_c(img, kettle_img(), 820, 830, 0.8); steam(img, 760, 760, t)
    ln = L("dhaba")[0]; k = eio((t - ln["start"]) / max(1, ln["end"] - ln["start"]))
    clock(img, 170, 300, 6 + 12 * k)
    paste_c(img, pill("6 AM" if k < 0.5 else "6 PM", 40, YEL), 170, 430, 1.0)
    hx = 360 + math.sin(t * 2.2) * 120
    draw_char(img, "H", hx, 960, t, "n", 1.0, arms=(-10, -60), hold=hold_tray)
    for i, (wd, col, y) in enumerate([("chai", YEL, 600), ("bartan", WHITE, 700), ("table", (120, 200, 255), 800)]):
        wt = word_t(ln, wd)
        if wt and t > wt - 0.1:
            paste_c(img, pill(wd.upper() + ("!" if i == 2 else ""), 54, col), 800 - i * 10, y - 120, eob((t - wt + 0.1) / 0.3), rot=(-6, 4, -3)[i])

def sc_burn(img, t, lt):
    img.alpha_composite(bg_dhaba("day"))
    shake = math.sin(t * 60) * 10 * max(0, 1 - (lt - 1.0) / 0.6) if lt > 1.0 else 0
    ln = L("burn")[0]; ct = word_t(ln, "cup", ln["end"] - 0.6)
    draw_char(img, "H", 380 + shake, 900, t, "shock" if lt > 1.0 else "n", 1.15, arms=(-10, -95))
    paste_c(img, kettle_img(), 720 + shake, 900, 1.15, rot=-15 if lt < 1.0 else 10); steam(img, 640, 820, t, 4, 1.2)
    if lt > 1.0:
        paste_c(img, emoji("🔥", 110), 600, 760, eob((lt - 1.0) / 0.25))
        paste_c(img, glow_text("AAAH!", "Anton-Regular.ttf", 130, WHITE, (255, 80, 40)), W / 2, 560, eob((lt - 1.0) / 0.3), rot=-5)
    if t < ct:
        q = max(0, (t - (ct - 0.7)) / 0.7); paste_c(img, cup_img(), 760, 1060 + q * q * 160, 1.1, rot=q * 120)
    else:
        k = t - ct; d = ImageDraw.Draw(img)
        for j in range(7):
            r = np.random.default_rng(j + 40); vx = r.uniform(-260, 260); vy = r.uniform(-380, -120)
            px = 760 + vx * k; py = min(1300, 1220 + vy * k + 900 * k * k)
            d.polygon([(px, py), (px + 22, py + 8), (px + 6, py + 26)], fill=(245, 240, 230), outline=INK)
        paste_c(img, pill("CRASH!", 60, RED, WHITE), 760, 1000, eob(k / 0.25), rot=8)

def sc_pay(img, t, lt):
    img.alpha_composite(bg_dhaba("night")); bulb_glow(img, 70)
    draw_char(img, "H", 820, 960, t, "sad", 0.95)
    ln = L("pay")[0]; t450 = word_t(ln, "450", ln["start"] + 1.8); t50 = word_t(ln, "50", ln["end"] - 1.0, exact=True)
    paste_c(img, notes_img(500), 360, 620, eob((lt - 0.3) / 0.35), rot=-4)
    if t > t450 - 0.2:
        k = t - t450 + 0.2; d = ImageDraw.Draw(img)
        d.line([(200, 680), (200 + 330 * eo(k / 0.3), 560)], fill=RED, width=16)
        paste_c(img, notes_img(450), 360, 850, eob((k - 0.3) / 0.35), rot=3)
    if t > t50 - 0.1:
        k = t - t50 + 0.1
        paste_c(img, pill("-50 CUP KE", 56, RED, WHITE), 360, 1060, eob(k / 0.3), rot=-5)
        paste_c(img, cup_img(), 600, 1060, eob(k / 0.3) * 0.8, rot=20)

def sc_bilal(img, t, lt):
    img.alpha_composite(bg_room("eve"))
    ls = L("bilal"); ht = ls[1]["start"] if len(ls) > 1 else 1e9
    jump = abs(math.sin(t * 6)) * 25 if t < ht else 0
    draw_char(img, "L", 300, 930 - jump, t, "happy", 1.0, arms=(-150, 150) if t < ht else (-20, 20))
    draw_char(img, "H", 790, 930, t, "n" if t < ht else "sad", 1.0, arms=(-15, 15))
    if t > ls[0]["start"] + 0.4:
        k = t - ls[0]["start"] - 0.4
        paste_c(img, pill("PAISE DOUBLE!", 58, YEL), 330, 470, eob(k / 0.3) * (1 + 0.04 * math.sin(t * 9)), rot=-6)
        paste_c(img, emoji("🤑", 110), 600, 400, eob((k - 0.3) / 0.3))
    if t > ht + 0.3: paste_c(img, emoji("🙄", 120), 900, 560, eob((t - ht - 0.3) / 0.3))

def sc_end_diary(img, t, lt):
    img.alpha_composite(bg_room("night"))
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([200, 700, 1000, 1500], fill=(255, 200, 110, 110))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(90)))
    draw_char(img, "H", W / 2, 900, t, "det", 1.05, arms=(-30, 30))
    d = ImageDraw.Draw(img); d.rectangle([0, 1250, W, 1290], fill=(120, 80, 50), outline=INK, width=4); d.rectangle([0, 1290, W, 1420], fill=(90, 60, 40))
    diary = Image.new("RGBA", (620, 380), (0, 0, 0, 0)); dd = ImageDraw.Draw(diary)
    dd.rounded_rectangle([0, 0, 619, 379], radius=16, fill=(250, 245, 225), outline=INK, width=6)
    for j in range(7): dd.line([(30, 60 + j * 44), (590, 60 + j * 44)], fill=(180, 200, 230), width=3)
    rows = [(r[0], tuple(r[1])) for r in META["diary"]] if "diary" in META else [(f"DAY {META['day']}: +Rs 450", (40, 60, 170)), ("AAJ BHI BACH GAYE", GRN), ("KAL: BILAL KI SCHEME?!", RED)]
    for j, (txt, col) in enumerate(rows):
        ti = text_img(txt, "Anton-Regular.ttf", 62, col); rev = eo((lt - 0.6 - j * 1.2) / 0.9); cw = int(ti.width * rev)
        if cw > 2: diary.alpha_composite(ti.crop((0, 0, cw, ti.height)), (36, 30 + j * 110))
    paste_c(img, diary, W / 2, 460, eob(lt / 0.35), rot=-2)
    if META.get("diary_follow", True):
        paste_c(img, pill(f"DAY {META['day'] + 1} KAL • FOLLOW +", 50, RED, WHITE), W / 2, 1180, eob((lt - 4.0) / 0.35) * (1 + 0.04 * math.sin(t * 8)))


# ======================= DAY 3+: BAZAAR, PHONES, ROOFTOP (reusable)
@lru_cache(None)
def bg_bazaar():
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im)
    for y in range(0, 900 * s, 4): d.rectangle([0, y, W * s, y + 4], fill=mixc((250, 170, 100), (255, 225, 170), y / (900 * s)))
    r = np.random.default_rng(7); x = -30
    while x < W:   # back buildings
        w = r.uniform(140, 220); h = r.uniform(380, 640); col = mixc((190, 120, 90), (120, 100, 140), r.random())
        d.rectangle([x * s, (900 - h) * s, (x + w) * s, 1250 * s], fill=col, outline=INK, width=4 * s)
        for wy in range(int(900 - h + 40), 820, 110):
            for wx in range(int(x + 25), int(x + w - 40), 70): d.rectangle([wx * s, wy * s, (wx + 36) * s, (wy + 50) * s], fill=(255, 225, 150), outline=INK, width=3 * s)
        x += w
    # wires
    for k in range(3): d.line([(0, (230 + k * 40) * s), (W * s, (300 + k * 30) * s)], fill=INK, width=3 * s)
    # stall awnings (striped)
    cols = [(230, 60, 70), (60, 150, 255), (40, 190, 110), (255, 200, 40)]
    for i, ax in enumerate((-40, 360, 760)):
        c1 = cols[i]; 
        for k in range(6):
            d.polygon([((ax + k * 60) * s, 760 * s), ((ax + k * 60 + 60) * s, 760 * s), ((ax + k * 60 + 70) * s, 860 * s), ((ax + k * 60 + 10) * s, 860 * s)], fill=c1 if k % 2 == 0 else (250, 245, 235), outline=INK)
        d.rectangle([ax * s, 860 * s, (ax + 370) * s, 1250 * s], fill=mixc(c1, (60, 40, 40), 0.55), outline=INK, width=4 * s)
    # string lights
    for x in range(20, W, 70):
        yy = 700 + 30 * math.sin(x / 90)
        d.ellipse([(x - 10) * s, (yy - 10) * s, (x + 10) * s, (yy + 10) * s], fill=cols[(x // 70) % 4], outline=INK, width=2 * s)
    d.rectangle([0, 1250 * s, W * s, H * s], fill=(130, 115, 105))
    for x in range(0, W, 120): d.line([(x * s, 1250 * s), ((x - 80) * s, H * s)], fill=(115, 100, 92), width=4 * s)
    # phone stall table with phones + sign (original, no brands)
    d.rectangle([520 * s, 1120 * s, 1060 * s, 1170 * s], fill=(150, 100, 60), outline=INK, width=5 * s)
    d.rectangle([540 * s, 1170 * s, 1040 * s, 1330 * s], fill=(120, 80, 50), outline=INK, width=5 * s)
    for k in range(6): d.rounded_rectangle([(550 + k * 82) * s, 1050 * s, (610 + k * 82) * s, 1120 * s], radius=10 * s, fill=(30, 30, 40), outline=INK, width=3 * s)
    d.rounded_rectangle([340 * s, 560 * s, 740 * s, 650 * s], radius=14 * s, fill=(255, 235, 120), outline=INK, width=5 * s)
    for x in (360, 720): d.line([(x * s, 500 * s), (x * s, 560 * s)], fill=INK, width=5 * s)
    d.text((540 * s, 605 * s), "SASTA MOBILE", font=fnt("Anton-Regular.ttf", 58 * s), fill=RED, anchor="mm")
    return ssf(im)

@lru_cache(None)
def phone_img(lit=False):
    s = SS; w, h = 120, 220; im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=20 * s, fill=(35, 35, 45), outline=INK, width=5 * s)
    d.rounded_rectangle([10 * s, 22 * s, (w - 10) * s, (h - 26) * s], radius=8 * s, fill=(90, 160, 230) if lit else (20, 22, 30))
    if lit:   # printed sticker "screen" of a dummy phone
        for r_ in range(3):
            for c in range(3):
                d.rounded_rectangle([(20 + c * 30) * s, (40 + r_ * 34) * s, (42 + c * 30) * s, (62 + r_ * 34) * s], radius=5 * s, fill=[(255, 200, 40), (230, 60, 70), (40, 190, 110)][(r_ + c) % 3])
    d.ellipse([(w / 2 - 8) * s, (h - 20) * s, (w / 2 + 8) * s, (h - 6) * s], fill=(70, 70, 80))
    return ssf(im)

@lru_cache(None)
def box_img(open_=False):
    im = Image.new("RGBA", (420, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([20, 110, 400, 290], fill=(200, 150, 95), outline=INK, width=6)
    d.line([(20, 160), (400, 160)], fill=(170, 120, 75), width=4)
    if open_:
        d.polygon([(20, 110), (-0, 40), (150, 30), (180, 110)], fill=(215, 165, 110), outline=INK)
        d.polygon([(400, 110), (420, 40), (270, 30), (240, 110)], fill=(215, 165, 110), outline=INK)
    else:
        d.rectangle([20, 90, 400, 120], fill=(215, 165, 110), outline=INK, width=6)
    d.text((210, 225), "10 PCS", font=fnt("Anton-Regular.ttf", 56), fill=INK, anchor="mm")
    return im

def hold_phone(img, x, y, sc): paste_c(img, phone_img(True), x + 140 * sc, y + 150 * sc, sc * 0.9, rot=-10)

def sc_hook_scheme(img, t, lt):
    img.alpha_composite(bg_room("night")); fan(img, 360, 210, t, (90, 100, 130))
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([300, 600, 900, 1300], fill=(255, 200, 120, 70))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(80)))
    paste_c(img, box_img(True), 250, 1290, 0.9)
    for k, (px, rr) in enumerate([(820, 20), (900, -35), (760, 60)]): paste_c(img, phone_img(True), px, 1300 + k * 20, 0.8, rot=rr)
    draw_char(img, "H", W / 2, 960, t, "shock", 1.15, arms=(-10, 40), hold=hold_phone)
    paste_c(img, glow_text("Rs 2000 KE PHONE…", "Anton-Regular.ttf", 108, WHITE, (90, 160, 255)), W / 2, 380, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("EK BHI ON NAHI!", "Anton-Regular.ttf", 120, YEL, (255, 120, 40)), W / 2, 510, eob((lt - 2.0) / 0.35))

def sc_market(img, t, lt):
    img.alpha_composite(bg_bazaar())
    ls = L("market"); ht = ls[1]["start"] if len(ls) > 1 else 1e9
    jump = abs(math.sin(t * 6)) * 22 if t < ht else 0
    draw_char(img, "L", 290, 1000 - jump, t, "happy", 0.95, arms=(-140, 140) if t < ht else (-20, 60))
    draw_char(img, "H", 780, 1000, t, "n" if t < ht else "det", 0.95, arms=(-15, 15) if t < ht else (-60, 15))
    if t > ls[0]["start"] + 0.3 and t < ht:
        k = t - ls[0]["start"] - 0.3
        paste_c(img, pill("10 PHONE = Rs 2000!", 54, YEL), W / 2, 330, eob(k / 0.3) * (1 + 0.04 * math.sin(t * 9)), rot=-4)
        paste_c(img, emoji("🤑", 110), 880, 300, eob((k - 0.3) / 0.3))
    if t >= ht:
        k = t - ht
        for j, (sx, d0) in enumerate([(780, 0.2), (290, 1.4)]):
            q = eio((k - d0) / 0.8)
            if k > d0: paste_c(img, notes_img(1000, 200), lerp(sx, W / 2, q), lerp(1120, 760, q) - 160 * math.sin(q * math.pi), 0.8 * (1 - 0.3 * q), rot=(1 - q) * 20)
        if k > 2.4: paste_c(img, pill("PLAN PAKKA!", 56, GRN, WHITE), W / 2, 330, eob((k - 2.4) / 0.3), rot=3)

def sc_dummy(img, t, lt):
    img.alpha_composite(bg_room("day")); fan(img, 540, 200, t)
    ls = L("dummy"); lt_ = ls[1]["start"] if len(ls) > 1 else 1e9
    ln = ls[0]; tn = word_t(ln, "naqli", ln["start"] + 2.4)
    d = ImageDraw.Draw(img); d.rectangle([140, 1180, 940, 1230], fill=(120, 80, 50), outline=INK, width=5)
    draw_char(img, "H", 760, 900, t, "shock" if t > tn - 0.2 else "n", 0.95, arms=(-15, -70))
    draw_char(img, "L", 280, 940, t, "sad" if t >= lt_ else "n", 0.9, arms=(-20, 20) if t < lt_ else (-150, -30))
    opened = lt > 0.8
    paste_c(img, box_img(opened), W / 2, 1100, 0.85)
    if opened:
        for j in range(4):
            q = eo((lt - 0.8 - j * 0.15) / 0.5)
            paste_c(img, phone_img(True), W / 2 + (j - 1.5) * 85 * q, 1060 - 110 * q + 25 * abs(j - 1.5), 0.62, rot=(j - 1.5) * 22 * q)
    if t > tn - 0.2:
        k = t - tn + 0.2
        paste_c(img, glow_text("NAQLI!", "Anton-Regular.ttf", 150, WHITE, (230, 60, 70)), W / 2, 440, eob(k / 0.3), rot=-6)
        paste_c(img, pill("PLASTIC KE KHILONE!", 50, RED, WHITE), W / 2, 590, eob((k - 0.6) / 0.3))
    if t >= lt_ + 0.2: paste_c(img, emoji("😅", 110), 150, 700, eob((t - lt_ - 0.2) / 0.3))

def sc_rooftop(img, t, lt):
    img.alpha_composite(skyline("golden")); kites(img, t)
    ln = L("rooftop")[0]; th = word_t(ln, "phir", ln["start"] + 1.4)
    d = ImageDraw.Draw(img); d.rectangle([0, 1250, W, 1300], fill=(170, 120, 90), outline=INK, width=5); d.rectangle([0, 1300, W, 1420], fill=(120, 85, 70))
    angry = t < th
    sh = abs(math.sin(t * 9)) * 18 if not angry else 0
    draw_char(img, "H", 720, 980 - sh, t, "det" if angry else "happy", 1.0, arms=(-20, 20) if angry else (-60, 140), laugh=not angry)
    draw_char(img, "L", 330, 980 - sh * 0.8, t, "sad" if angry else "happy", 1.0, arms=(-15, 15) if angry else (-140, 60), laugh=not angry)
    if angry: paste_c(img, emoji("😤", 120), 720, 640, eob((lt - 0.2) / 0.3))
    else:
        k = t - th
        paste_c(img, emoji("😂", 130), 520, 560, eob(k / 0.3) * (1 + 0.08 * math.sin(t * 10)))
        paste_c(img, glow_text("HAHAHA!", "Anton-Regular.ttf", 120, WHITE, (255, 140, 40)), W / 2, 380, eob((k - 0.3) / 0.3), rot=-4)
        q = (k * 0.9) % 1.6   # a dummy phone flips in the air
        paste_c(img, phone_img(True), 540 + q * 80, 860 - 380 * math.sin(min(q, 1) * math.pi), 0.7, rot=q * 400)

# ======================= DAY 4+: STREET AT DAWN, CYCLE, TUITION ROOM, PHONE CALL (reusable)
def LB(scene): return [l for l in LINES if l["scene"] == scene and l.get("mode") == "beat"]
def LV(scene): return [l for l in LINES if l["scene"] == scene and l.get("mode") != "beat"]

@lru_cache(None)
def bg_street(mode="dawn"):
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im)
    top, bot = {"dawn": ((90, 70, 140), (255, 170, 120)), "day": ((120, 190, 240), (230, 240, 250)), "night": ((10, 14, 35), (45, 45, 85))}[mode]
    for y in range(0, 1000 * s, 4): d.rectangle([0, y, W * s, y + 4], fill=mixc(top, bot, y / (1000 * s)))
    if mode == "night":
        d.ellipse([780 * s, 200 * s, 880 * s, 300 * s], fill=(250, 245, 210))
        rs = np.random.default_rng(5)
        for _ in range(40):
            x_, y_ = rs.uniform(0, W), rs.uniform(60, 600); d.ellipse([x_ * s, y_ * s, (x_ + 4) * s, (y_ + 4) * s], fill=(230, 230, 255))
    else: d.ellipse([700 * s, 640 * s, 900 * s, 840 * s], fill=(255, 220, 140))
    r = np.random.default_rng(21); x = -20
    while x < W:   # row of mohalla houses with doors
        w = r.uniform(200, 260); h = r.uniform(420, 560); col = mixc((210, 160, 120), (150, 130, 170), r.random())
        if mode == "night": col = mixc(col, (20, 20, 50), 0.55)
        d.rectangle([x * s, (1180 - h) * s, (x + w) * s, 1180 * s], fill=col, outline=INK, width=5 * s)
        d.rectangle([x * s, (1180 - h) * s, (x + w) * s, (1180 - h + 26) * s], fill=mixc(col, (0, 0, 0), 0.25), outline=INK, width=4 * s)
        dx = x + w / 2 - 45; d.rounded_rectangle([dx * s, 1020 * s, (dx + 90) * s, 1180 * s], radius=10 * s, fill=(110, 70, 50), outline=INK, width=4 * s)
        lit = r.random() < 0.5
        d.rectangle([(x + 24) * s, (1180 - h + 70) * s, (x + 84) * s, (1180 - h + 140) * s], fill=(255, 220, 150) if lit and mode != "night" else ((60, 70, 100) if mode != "night" else (40, 45, 70)), outline=INK, width=3 * s)
        x += w
    for k in range(2): d.line([(0, (360 + k * 40) * s), (W * s, (420 + k * 30) * s)], fill=INK, width=3 * s)
    d.rectangle([0, 1180 * s, W * s, H * s], fill=(120, 110, 115) if mode != "night" else (60, 58, 75))
    for x in range(-40, W, 160): d.rectangle([x * s, 1320 * s, (x + 90) * s, 1334 * s], fill=(230, 225, 210))
    return ssf(im)

@lru_cache(None)
def cycle_img(broken=False):
    s = SS; im = Image.new("RGBA", (460 * s, 300 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for cx in (100, 360):
        d.ellipse([(cx - 90) * s, 110 * s, (cx + 90) * s, 290 * s], outline=INK, width=12 * s)
        d.ellipse([(cx - 12) * s, 188 * s, (cx + 12) * s, 212 * s], fill=INK)
        for a in range(0, 180, 30):
            ra = math.radians(a); d.line([((cx - 80 * math.cos(ra)) * s, (200 - 80 * math.sin(ra)) * s), ((cx + 80 * math.cos(ra)) * s, (200 + 80 * math.sin(ra)) * s)], fill=(90, 90, 100), width=2 * s)
    fr = (40, 110, 200)
    for a_, b_ in [((100, 200), (220, 200)), ((220, 200), (300, 90)), ((300, 90), (170, 90)), ((170, 90), (100, 200)), ((170, 90), (220, 200)), ((300, 90), (360, 200)), ((300, 90), (310, 50))]:
        d.line([(a_[0] * s, a_[1] * s), (b_[0] * s, b_[1] * s)], fill=fr, width=12 * s)
    d.line([(280 * s, 50 * s), (340 * s, 40 * s)], fill=INK, width=10 * s)
    d.rounded_rectangle([140 * s, 70 * s, 210 * s, 88 * s], radius=8 * s, fill=INK)
    d.ellipse([200 * s, 180 * s, 240 * s, 220 * s], outline=INK, width=6 * s)
    if broken:
        d.line([(100 * s, 230 * s), (40 * s, 290 * s)], fill=(150, 150, 160), width=5 * s); d.line([(240 * s, 220 * s), (300 * s, 296 * s)], fill=(150, 150, 160), width=5 * s)
    else:
        d.line([(100 * s, 190 * s), (220 * s, 182 * s)], fill=(150, 150, 160), width=5 * s); d.line([(100 * s, 210 * s), (220 * s, 218 * s)], fill=(150, 150, 160), width=5 * s)
    d.rectangle([20 * s, 70 * s, 110 * s, 110 * s], fill=(250, 245, 235), outline=INK, width=4 * s)   # paper bundle on the carrier
    return ssf(im)

@lru_cache(None)
def paper_roll():
    im = Image.new("RGBA", (110, 50), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 4, 108, 46], radius=20, fill=(245, 242, 230), outline=INK, width=4)
    for k in range(3): d.line([(24 + k * 26, 12), (24 + k * 26, 38)], fill=(150, 150, 160), width=3)
    return im

@lru_cache(None)
def alarm_img():
    im = Image.new("RGBA", (260, 280), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for x in (40, 220): d.ellipse([x - 38, 10, x + 38, 80], fill=(230, 60, 70), outline=INK, width=5)
    d.ellipse([20, 40, 240, 260], fill=(230, 60, 70), outline=INK, width=7)
    d.ellipse([45, 65, 215, 235], fill=(252, 250, 240), outline=INK, width=5)
    d.text((130, 150), "5:00", font=fnt("Anton-Regular.ttf", 64), fill=INK, anchor="mm")
    return im

def bubble(lines_, size=44, col=INK, tail="left"):
    ts = [text_img(x, "Poppins-Black.ttf", size, c) for x, c in lines_]
    w = max(t_.width for t_ in ts) + 70; h = sum(t_.height for t_ in ts) + 60
    im = Image.new("RGBA", (w + 20, h + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    tx = 60 if tail == "left" else w - 60
    d.polygon([(tx - 25, h - 10), (tx + 25, h - 10), (tx + (-40 if tail == "left" else 40), h + 60)], fill=WHITE, outline=INK)
    d.rounded_rectangle([0, 0, w, h], radius=40, fill=WHITE, outline=INK, width=6)
    d.polygon([(tx - 22, h - 12), (tx + 22, h - 12), (tx + (-34 if tail == "left" else 34), h + 46)], fill=WHITE)
    y = 30
    for t_ in ts: im.alpha_composite(t_, ((w - t_.width) // 2, y)); y += t_.height
    return im

def hold_paper(img, x, y, sc):
    for k in range(3): paste_c(img, paper_roll(), x + 140 * sc, y + 160 * sc + k * 26 * sc, sc * 0.9, rot=-10)
def hold_copy(img, x, y, sc):
    c = Image.new("RGBA", (220, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 219, 159], fill=(250, 250, 245), outline=INK, width=5)
    d.text((110, 80), "10/10", font=fnt("Anton-Regular.ttf", 76), fill=GRN, anchor="mm")
    paste_c(img, c, x + 20 * sc, y - 330 * sc, sc, rot=-6)

def zzz(img, x, y, t, n=3):
    for k in range(n):
        q = (t * 0.6 + k / n) % 1
        paste_c(img, text_img("Z", "Anton-Regular.ttf", int(50 + 40 * q), (200, 220, 255), 5, INK), x + q * 90 + math.sin(t * 3 + k) * 10, y - q * 200, 1.0, alpha=1 - q)


def tuition_room(img, t, board=True):
    img.alpha_composite(bg_room("night"))
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([180, 560, 900, 1280], fill=(255, 200, 110, 120))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(img)
    if not board: return
    d.rectangle([120, 300, 560, 560], fill=(40, 70, 60), outline=(150, 100, 60), width=12)   # small blackboard
    d.text((340, 400), "7 x 8 = ?", font=fnt("Anton-Regular.ttf", 76), fill=(240, 240, 230), anchor="mm")
    d.text((340, 490), "Ali • Class 5", font=fnt("Poppins-Black.ttf", 30), fill=(200, 210, 200), anchor="mm")
def tuition_table(img):
    d = ImageDraw.Draw(img); d.rectangle([60, 1170, W - 60, 1215], fill=(150, 100, 60), outline=INK, width=5); d.rectangle([100, 1215, W - 100, 1420], fill=(120, 80, 50), outline=INK, width=5)
    d.rectangle([380, 1140, 560, 1172], fill=(250, 250, 245), outline=INK, width=3); d.rectangle([600, 1150, 700, 1170], fill=(230, 60, 70), outline=INK, width=3)
def mom_door(img, t, k):
    if k <= 0: return
    d = ImageDraw.Draw(img); x0 = 760
    d.rectangle([x0, 300, x0 + 300, 1170], fill=(255, 230, 170), outline=INK, width=8)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o = ImageDraw.Draw(ov); cx = x0 + 150; a = int(235 * min(1, k))
    o.ellipse([cx - 120, 380, cx + 120, 640], fill=(40, 30, 50, a)); o.rounded_rectangle([cx - 130, 560, cx + 130, 1170], radius=110, fill=(40, 30, 50, a))
    o.ellipse([cx - 50, 470, cx - 20, 500], fill=(255, 255, 255, a)); o.ellipse([cx + 20, 470, cx + 50, 500], fill=(255, 255, 255, a))
    o.line([(cx - 60, 450), (cx - 15, 465)], fill=(255, 255, 255, a), width=8); o.line([(cx + 60, 450), (cx + 15, 465)], fill=(255, 255, 255, a), width=8)
    img.alpha_composite(ov)

def sc_hook_tuition(img, t, lt):
    tuition_room(img, t, board=False)
    draw_char(img, "K", 280, 930, t, "shock", 0.8, arms=(-15, -80))
    draw_char(img, "H", 700, 900 + 10 * math.sin(t * 1.5), t, "sleep", 1.05, arms=(-20, 20))
    tuition_table(img); zzz(img, 800, 700, t)
    paste_c(img, glow_text("TEEN NAUKRIYAN…", "Anton-Regular.ttf", 112, WHITE, (90, 160, 255)), W / 2, 230, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("TEESRI PE SO GAYA?!", "Anton-Regular.ttf", 96, YEL, (255, 120, 40)), W / 2, 360, eob((lt - 2.0) / 0.35))

def sc_alarm(img, t, lt):
    img.alpha_composite(bg_room("night")); charpai(img)
    b = LB("alarm")[0]; slap = b["start"] + 1.6
    awake = t > slap
    draw_char(img, "H", 330, 860, t, "shock" if awake else "sleep", 0.95, arms=(-15, -110 if abs(t - slap) < 0.35 else 15))
    shake = 0 if awake else math.sin(t * 70) * 14
    paste_c(img, alarm_img(), 760 + shake, 1060, 1.0, rot=shake * 0.6)
    if not awake:
        paste_c(img, pill("TRRRING!", 60, RED, WHITE), 760, 830, eob((lt - 0.1) / 0.25), rot=-8)
        zzz(img, 420, 650, t)
    else:
        k = t - slap; paste_c(img, emoji("😵", 100), 560, 560, eob(k / 0.3))
    v = LV("alarm")[0]
    if t > v["start"] + 1.4:
        paste_c(img, pill("JOB 1: AKHBAAR • 5 AM", 54, YEL), W / 2, 330, eob((t - v["start"] - 1.4) / 0.3), rot=-4)

def paper_count(lt_t0, t, a, b, dur):
    return int(lerp(a, b, eio((t - lt_t0) / dur)))

def sc_paper(img, t, lt):
    img.alpha_composite(bg_street("dawn"))
    span = next(x for x in SCENES if x["scene"] == "paper"); dur = span["vend"] - span["vstart"]
    cx = 300 + 140 * math.sin(lt * 0.9); bob = abs(math.sin(t * 10)) * 6
    paste_c(img, cycle_img(), cx, 1250 - bob, 1.0)
    draw_char(img, "H", cx + 20, 920 - bob, t, "det" if lt < dur * 0.6 else "happy", 0.8, arms=(-70, -150 if (lt % 1.1) < 0.3 else -40))
    for k in range(int(lt / 1.1) + 1):   # thrown papers fly to doors
        q = (lt - k * 1.1) / 0.8
        if 0 < q < 1.6:
            qq = min(q, 1); tx = 700 + (k % 3) * 120
            paste_c(img, paper_roll(), lerp(cx + 120, tx, qq), lerp(880, 1120, qq) - 260 * math.sin(qq * math.pi), 0.9, rot=q * 600 if q < 1 else 0)
    n = paper_count(span["vstart"], t, 1, 60, dur)
    paste_c(img, pill(f"AKHBAAR: {n}/100", 50, WHITE, INK), W / 2, 300, eob(lt / 0.3))

def sc_chain(img, t, lt):
    img.alpha_composite(bg_street("day"))
    b0, b1 = LB("chain"); v = LV("chain")[0]; snap = b0["start"] + 0.5
    if t < b1["start"]:
        sh = math.sin(t * 60) * 10 * max(0, 1 - (t - snap) / 0.5) if t > snap else 0
        paste_c(img, cycle_img(t > snap), 420 + sh, 1250, 1.0, rot=4 if t > snap else 0)
        draw_char(img, "H", 440 + sh, 920, t, "shock" if t < v["start"] else "sad", 0.8, arms=(-60, -60))
        if t > snap:
            k = t - snap
            paste_c(img, glow_text("CHAIN TOOTI!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 360, eob(k / 0.3), rot=-5)
            for j in range(6):   # papers spill
                r = np.random.default_rng(j + 70); vx = r.uniform(-300, 300); vy = r.uniform(-500, -200)
                paste_c(img, paper_roll(), 360 + vx * min(k, 1.2), min(1340, 1150 + vy * min(k, 1.2) + 700 * min(k, 1.2) ** 2), 0.8, rot=j * 50 + k * 200)
        if t > v["start"]:
            paste_c(img, pill("BAAKI 40 GHAR… PAIDAL", 52, YEL), W / 2, 520, eob((t - v["start"] - 1.2) / 0.3), rot=3)
        paste_c(img, pill("AKHBAAR: 60/100", 50, WHITE, INK), W / 2, 230, 1.0)
    else:   # running on foot, dog chasing
        k = t - b1["start"]; q = k / (b1["end"] - b1["start"])
        hx = lerp(-80, 1180, eio(q * 1.05)); jmp = abs(math.sin(t * 13)) * 30
        draw_char(img, "H", hx, 950 - jmp, t, "shock", 0.8, arms=(-150, 150), hold=hold_paper)
        dx = hx - 360; paste_c(img, emoji("🐕", 170), dx, 1250 - abs(math.sin(t * 14)) * 30)
        if (k % 0.45) < 0.3: paste_c(img, pill("BHOW!", 46, WHITE, INK), dx - 40, 1070, 1.0, rot=-10)
        n = int(lerp(60, 100, eio(q * 1.2)))
        paste_c(img, pill(f"AKHBAAR: {n}/100", 50, GRN if n >= 100 else WHITE, WHITE if n >= 100 else INK), W / 2, 230, 1.0)
        if q > 0.6: paste_c(img, pill("+Rs 150", 62, GRN, WHITE), W / 2, 400, eob((q - 0.6) / 0.12), rot=-4)

def sc_late(img, t, lt):
    img.alpha_composite(bg_dhaba("day"))
    b0, b1 = LB("late"); v = LV("late")[0]
    paste_c(img, kettle_img(), 820, 830, 0.8); steam(img, 760, 760, t)
    if t < b1["start"]:
        clock(img, 170, 300, 9 + 40 / 60); paste_c(img, pill("9:40 AM", 40, RED, WHITE), 170, 430, 1.0)
        hx = lerp(-100, 420, eo((t - b0["start"]) / 1.0))
        draw_char(img, "H", hx, 960, t, "shock" if t < v["start"] + 2 else "sad", 1.0, arms=(-120, 120) if t < b0["end"] else (-15, 15))
        if t > b0["start"] + 1.2:
            paste_c(img, pill("DER SE AAYE?!", 56, RED, WHITE), 640, 640, eob((t - b0["start"] - 1.2) / 0.25), rot=6)
        wt = word_t(v, "kat", None)
        if wt and t > wt - 0.2:
            paste_c(img, glow_text("-Rs 100", "Anton-Regular.ttf", 140, WHITE, (230, 60, 70)), W / 2, 1180, eob((t - wt + 0.2) / 0.3), rot=-4)
    else:   # montage: tray, cups, clock to 6 PM, pay
        k = t - b1["start"]; q = k / (b1["end"] - b1["start"])
        hrs = 10 + 8 * eio(min(q / 0.7, 1)); clock(img, 170, 300, hrs)
        paste_c(img, pill(f"{int(hrs) if hrs < 13 else int(hrs) - 12}:00 {'AM' if hrs < 12 else 'PM'}", 40, YEL), 170, 430, 1.0)
        hx = 380 + math.sin(t * 4) * 170
        draw_char(img, "H", hx, 960, t, "det", 1.0, arms=(-10, -60), hold=hold_tray)
        for j, (txt, col) in enumerate([("CHAI x 80", YEL), ("BARTAN x 200", WHITE)]):
            if q > 0.1 + j * 0.25 and q < 0.75: paste_c(img, pill(txt, 50, col), 760, 560 + j * 110, eob((q - 0.1 - j * 0.25) / 0.08), rot=(-5, 4)[j])
        if q > 0.72:
            paste_c(img, notes_img(450), W / 2, 620, eob((q - 0.72) / 0.1), rot=-4)
            paste_c(img, pill("450 - 100 = +Rs 350", 54, GRN, WHITE), W / 2, 800, eob((q - 0.8) / 0.1), rot=3)

def sc_tuition(img, t, lt):
    tuition_room(img, t)
    v = LV("tuition")[0]; b = LB("tuition")[0]
    sleepy = 0 if t < b["start"] else (t - b["start"]) / (b["end"] - b["start"])
    nod = 0 if sleepy < 0.3 else max(0, math.sin((t - b["start"]) * 4)) * 40 * sleepy
    draw_char(img, "K", 280, 930, t, "n", 0.8, arms=(-15, -80))
    mood = "det" if sleepy == 0 else ("sad" if (t * 2) % 1.4 > 0.5 or sleepy < 0.3 else "sleep")
    draw_char(img, "H", 700, 900 + nod, t, mood, 1.05, arms=(-120 if sleepy == 0 else -20, 20))
    tuition_table(img)
    if sleepy > 0.2:
        txt = ["7 x 8 =", "7 x 8 = 5…", "7 x 8 = Zzz…"][min(2, int((sleepy - 0.2) / 0.27))]
        paste_c(img, bubble([(txt, INK)], 46, tail="right"), 700, 520, eob((sleepy - 0.2) / 0.1))
    if sleepy > 0.75: zzz(img, 820, 700, t)
    paste_c(img, pill("JOB 3: TUITION • 9 PM", 50, YEL), W / 2, 230, eob((t - v["start"] - 0.4) / 0.3), rot=-3)

def sc_asleep(img, t, lt):
    tuition_room(img, t)
    b0, b1 = LB("asleep"); v = LV("asleep")[0]
    wt = word_t(v, "khuli", v["start"] + 0.8)
    awake = t > wt
    mom_door(img, t, (t - v["start"] - 0.2) / 0.6 if t > v["start"] else 0)
    draw_char(img, "K", 280, 930, t, "shock" if t > v["start"] else "happy", 0.8, arms=(-60, -140) if t < v["start"] else (-15, 15))
    draw_char(img, "H", 560, 920, t, "shock" if awake else "sleep", 1.0, arms=(-20, 20))
    tuition_table(img)
    if not awake:
        zzz(img, 650, 720, t)
        if t > b0["start"] + 0.6: paste_c(img, bubble([("SIR…?", INK), ("AAP SO GAYE!", RED)], 44), 300, 470, eob((t - b0["start"] - 0.6) / 0.25))
    else:
        k = t - wt
        paste_c(img, emoji("😱", 120), 420, 560, eob(k / 0.25))
        if t > v["start"] + 1.6: paste_c(img, bubble([("YEH KYA", INK), ("HO RAHA HAI?!", RED)], 46, tail="right"), 720, 340, eob((t - v["start"] - 1.6) / 0.25))
        if t > b1["start"]:
            for j in range(3):
                q = ((t - b1["start"]) * 1.2 + j / 3) % 1
                paste_c(img, emoji("💦", 46), 470 + j * 40, 700 + q * 100, 1.0, alpha=1 - q)
            paste_c(img, pill("NAUKRI GAYI?!", 56, RED, WHITE), W / 2, 1100, eob((t - b1["start"]) / 0.25), rot=-4)

def sc_wake(img, t, lt):
    tuition_room(img, t)
    v = LV("wake")[0]; b = LB("wake")[0]
    mom_door(img, t, 1.0)
    draw_char(img, "K", 280, 920, t, "happy", 0.8, arms=(-15, -170), hold=hold_copy)
    draw_char(img, "H", 560, 920, t, "sad" if t < b["start"] else "happy", 1.0, arms=(-20, 20))
    tuition_table(img)
    if t > v["start"] + 0.8: paste_c(img, emoji("😉", 100), 130, 800, eob((t - v["start"] - 0.8) / 0.3))
    if t > b["start"] + 0.2:
        k = t - b["start"] - 0.2
        paste_c(img, bubble([("SHABASH!", GRN), ("KAL BHI AANA.", INK)], 46, tail="right"), 720, 340, eob(k / 0.25))
    if t > b["start"] + 1.2:
        k = t - b["start"] - 1.2; q = eio(k / 0.8)
        paste_c(img, notes_img(300, 200), lerp(900, 600, q), lerp(700, 640, q) - 120 * math.sin(q * math.pi), 0.85, rot=(1 - q) * 25)
        if k > 0.8: paste_c(img, pill("+Rs 300", 62, GRN, WHITE), 600, 520, eob((k - 0.8) / 0.25), rot=-4)

def sc_end_call(img, t, lt):
    img.alpha_composite(bg_room("night"))
    v = LV("end_call")[0]; b = LB("end_call"); dead = word_t(v, "percent", v["end"] - 0.5) + 0.3
    draw_char(img, "H", 290, 1000, t, "shock" if t > b[0]["start"] + 0.6 else "n", 0.95, arms=(-20, -120))
    sh = math.sin(t * 50) * 8 if (t < dead and ((t - b[0]["start"]) % 0.8) < 0.45) else 0
    ph = Image.new("RGBA", (420, 700), (0, 0, 0, 0)); d = ImageDraw.Draw(ph)
    d.rounded_rectangle([0, 0, 419, 699], radius=50, fill=(25, 25, 30), outline=INK, width=6)
    if t < dead:
        d.rounded_rectangle([18, 18, 401, 681], radius=36, fill=(30, 40, 70))
        d.text((210, 130), "UNKNOWN", font=fnt("Poppins-Black.ttf", 40), fill=WHITE, anchor="mm")
        d.text((210, 180), "NUMBER", font=fnt("Poppins-Black.ttf", 40), fill=WHITE, anchor="mm")
        d.text((210, 250), "+92 3XX XXXXXXX", font=fnt("Poppins-Black.ttf", 26), fill=(170, 180, 210), anchor="mm")
        d.text((210, 330), "\"Delivery job?…\"", font=fnt("Poppins-Black.ttf", 30), fill=YEL, anchor="mm")
        d.ellipse([60, 520, 160, 620], fill=GRN); d.ellipse([260, 520, 360, 620], fill=RED)
        if (t * 2.5) % 1 < 0.6 or t > v["start"]:
            d.rounded_rectangle([300, 40, 380, 76], radius=8, outline=RED, width=4); d.rectangle([306, 46, 312, 70], fill=RED)
            d.text((290, 58), "1%", font=fnt("Poppins-Black.ttf", 30), fill=RED, anchor="rm")
    else:
        d.rounded_rectangle([18, 18, 401, 681], radius=36, fill=(5, 5, 8))
    paste_c(img, ph, 720 + sh, 800, eob((lt - 0.1) / 0.3) * 0.85, rot=-6 + sh * 0.5)
    if t > dead:
        k = t - dead
        paste_c(img, emoji("📵", 120), 720, 800, eob(k / 0.3))
        paste_c(img, glow_text("PHONE MAR GAYA?!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 280, eob((k - 0.2) / 0.3), rot=-3)
        paste_c(img, pill(f"DAY {META['day'] + 1} KAL • FOLLOW +", 50, RED, WHITE), W / 2, 1240, eob((k - 0.9) / 0.35) * (1 + 0.04 * math.sin(t * 8)))

# ======================= DAY 5+: DEAD PHONE, LOADSHEDDING, NIGHT STREET, MOBILE SHOP, CHACHA (reusable)
def phone_big(state, t=0.0, batt=None):
    """Big phone screen card. state: dead | charging | calling | nobal | offer | fare"""
    ph = Image.new("RGBA", (440, 760), (0, 0, 0, 0)); d = ImageDraw.Draw(ph)
    d.rounded_rectangle([0, 0, 439, 759], radius=52, fill=(25, 25, 30), outline=INK, width=7)
    scr = {"dead": (5, 5, 8), "charging": (5, 5, 8), "calling": (30, 40, 70), "nobal": (40, 20, 30), "offer": (245, 248, 240), "fare": (245, 248, 240)}[state]
    d.rounded_rectangle([18, 18, 421, 741], radius=38, fill=scr)
    f = lambda n: fnt("Poppins-Black.ttf", n)
    if state == "charging":
        b = batt if batt is not None else 0
        d.rounded_rectangle([120, 300, 320, 420], radius=14, outline=WHITE, width=8); d.rectangle([320, 335, 340, 385], fill=WHITE)
        if b > 0: d.rectangle([132, 312, 132 + int(176 * b / 100), 408], fill=GRN if b > 10 else RED)
        d.text((220, 480), f"{int(b)}%", font=f(64), fill=WHITE, anchor="mm")
        d.polygon([(230, 250), (190, 330), (222, 330), (205, 400), (255, 310), (222, 310)], fill=YEL)
    elif state == "calling":
        d.text((220, 150), "CALLING…", font=f(44), fill=WHITE, anchor="mm")
        d.text((220, 220), "+92 3XX XXXXXXX", font=f(28), fill=(170, 180, 210), anchor="mm")
        for k in range(3):
            q = (t * 1.2 + k / 3) % 1; rr = 60 + q * 90
            d.ellipse([220 - rr, 430 - rr, 220 + rr, 430 + rr], outline=(90, 160, 255, int(255 * (1 - q))), width=6)
        d.ellipse([170, 600, 270, 700], fill=RED)
    elif state == "nobal":
        d.text((220, 200), "BALANCE", font=f(56), fill=WHITE, anchor="mm")
        d.text((220, 300), "Rs 0.00", font=fnt("Anton-Regular.ttf", 110), fill=RED, anchor="mm")
        for k, ln in enumerate(["Call nahi ho", "sakti. Recharge", "karein."]): d.text((220, 450 + k * 50), ln, font=f(34), fill=(230, 200, 210), anchor="mm")
    elif state == "offer":
        d.rectangle([18, 18, 421, 120], fill=(40, 190, 110)); d.text((220, 70), "JOB OFFER", font=f(46), fill=WHITE, anchor="mm")
        rows = [("DELIVERY RIDER", INK, 38), ("Rs 25,000 / MAHINA", (40, 140, 80), 34), ("KARACHI", RED, 64), ("PARSON • 9 AM", INK, 38)]
        for k, (txt, c, n) in enumerate(rows): d.text((220, 210 + k * 120), txt, font=f(n) if n < 60 else fnt("Anton-Regular.ttf", n), fill=c, anchor="mm")
    elif state == "fare":
        d.rectangle([18, 18, 421, 120], fill=(60, 110, 200)); d.text((220, 70), "BUS TICKET", font=f(46), fill=WHITE, anchor="mm")
        d.text((220, 220), "LAHORE", font=fnt("Anton-Regular.ttf", 70), fill=INK, anchor="mm")
        d.polygon([(195, 280), (245, 280), (245, 300), (265, 300), (220, 335), (175, 300), (195, 300)], fill=(120, 120, 130))
        d.text((220, 380), "KARACHI", font=fnt("Anton-Regular.ttf", 70), fill=INK, anchor="mm")
        d.text((220, 520), "Rs 1,500", font=fnt("Anton-Regular.ttf", 100), fill=RED, anchor="mm")
        d.text((220, 630), "18 GHANTE", font=f(36), fill=(120, 120, 130), anchor="mm")
    return ph

def hold_dead(img, x, y, sc): paste_c(img, phone_img(False), x + 140 * sc, y + 150 * sc, sc * 0.9, rot=-10)
def candle(img, x, y, t):
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).ellipse([x - 380, y - 420, x + 380, y + 340], fill=(255, 170, 70, 90 + int(15 * math.sin(t * 13))))
    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(70)))
    d = ImageDraw.Draw(img); d.rectangle([x - 22, y - 60, x + 22, y + 60], fill=(250, 245, 230), outline=INK, width=4)
    fl = 1 + 0.15 * math.sin(t * 17)
    d.ellipse([x - 13, y - 60 - 50 * fl, x + 13, y - 62], fill=(255, 200, 60), outline=(255, 140, 40), width=3)
def socket(img, x, y):
    d = ImageDraw.Draw(img); d.rounded_rectangle([x - 60, y - 70, x + 60, y + 70], radius=10, fill=(240, 238, 230), outline=INK, width=5)
    for dx in (-20, 20): d.ellipse([x + dx - 8, y - 18, x + dx + 8, y - 2], fill=INK)
def generator(img, x, y, t):
    sh = math.sin(t * 50) * 3; d = ImageDraw.Draw(img)
    d.rounded_rectangle([x - 110 + sh, y - 90, x + 110 + sh, y + 90], radius=16, fill=(220, 70, 60), outline=INK, width=6)
    d.rectangle([x - 70 + sh, y - 50, x + 70 + sh, y + 10], fill=(60, 60, 70), outline=INK, width=4)
    for k in range(4):
        q = (t * 0.7 + k / 4) % 1
        paste_c(img, emoji("💨", 50), x + 120 + q * 60, y - 100 - q * 160, 0.6 + q, alpha=1 - q)
def shop_front(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle([90, 420, 990, 1180], fill=(50, 45, 70), outline=INK, width=8)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).rectangle([130, 560, 950, 1170], fill=(255, 230, 150, 255)); img.alpha_composite(gl)
    d = ImageDraw.Draw(img)
    d.rectangle([110, 430, 970, 560], fill=(40, 190, 110), outline=INK, width=6)
    d.text((540, 470), "MOBILE POINT", font=fnt("Anton-Regular.ttf", 66), fill=WHITE, anchor="mm")
    d.text((540, 530), "CHARGING • RECHARGE • REPAIR", font=fnt("Poppins-Black.ttf", 28), fill=INK, anchor="mm")
    for k in range(6):   # phones on charge on a shelf
        x = 200 + k * 130; d.rounded_rectangle([x, 640, x + 70, 770], radius=10, fill=(30, 30, 40), outline=INK, width=4)
        d.rectangle([x + 22, 690, x + 48, 720], fill=GRN if (t * 2 + k) % 2 > 0.6 else (90, 200, 120))
        d.line([(x + 35, 770), (x + 35, 820)], fill=INK, width=4)
    d.rectangle([110, 960, 970, 1000], fill=(150, 100, 60), outline=INK, width=5)
    for k in range(5):
        r = np.random.default_rng(k); q = (t * 0.5 + k / 5) % 1
        d.ellipse([140 + k * 180, 420 - 6, 152 + k * 180, 432 - 6], fill=(255, 220, 90) if (t * 3 + k) % 2 > 1 else (255, 150, 60))

def sc_hook_dead(img, t, lt):
    img.alpha_composite(bg_room("night"))
    paste_c(img, phone_big("calling" if lt < 1.6 else "dead", t), 760, 760, eob(lt / 0.3) * 0.75, rot=-6 + (math.sin(t * 50) * 3 if lt < 1.6 else 0))
    draw_char(img, "H", 330, 960, t, "shock", 1.05, arms=(-20, -110))
    if lt > 1.6:
        paste_c(img, emoji("📵", 140), 760, 760, eob((lt - 1.6) / 0.3))
    paste_c(img, glow_text("NAUKRI KI CALL…", "Anton-Regular.ttf", 112, WHITE, (90, 160, 255)), W / 2, 230, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("PHONE MAR GAYA!", "Anton-Regular.ttf", 112, YEL, (230, 60, 70)), W / 2, 360, eob((lt - 1.7) / 0.35), rot=-3)

def sc_bijli(img, t, lt):
    b0, b1 = LB("bijli"); v = LV("bijli")[0]
    off = word_t(v, "bijli", v["start"] + 1.2)
    img.alpha_composite(bg_room("night"))
    if t < off:
        bulb_glow(img, 90)
        socket(img, 840, 900); d = ImageDraw.Draw(img); d.line([(840, 900), (760, 1050)], fill=INK, width=6)
        batt = 1 + 2 * eio((t - b0["start"]) / 2.5)
        paste_c(img, phone_big("charging", t, batt), 700, 1120, 0.42, rot=-4)
        draw_char(img, "H", 330, 930, t, "happy" if t > b0["start"] + 0.8 else "n", 1.0, arms=(-20, -60))
        if t > b0["start"] + 0.6: paste_c(img, pill("CHARGING…", 54, GRN, WHITE), W / 2, 360, eob((t - b0["start"] - 0.6) / 0.3), rot=-3)
    else:
        k = t - off
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 10, 225)))
        if k < 0.25: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(160 * (1 - k / 0.25)))))
        if k > 0.9: candle(img, 760, 1100, t)
        draw_char(img, "H", 330, 930, t, "shock" if t < b1["start"] else "sad", 1.0, arms=(-20, 20))
        ov = Image.new("RGBA", (W, H), (0, 0, 15, 60 if k > 0.9 else 150)); img.alpha_composite(ov)
        paste_c(img, glow_text("BIJLI GAYI!", "Anton-Regular.ttf", 130, WHITE, (90, 120, 255)), W / 2, 330, eob(k / 0.3), rot=-4)
        if t > b1["start"] + 0.2:
            paste_c(img, pill("LOADSHEDDING: 3 GHANTE", 50, YEL), W / 2, 520, eob((t - b1["start"] - 0.2) / 0.3), rot=3)
        if t > b1["start"] + 1.2:
            paste_c(img, pill("PHONE: 0%", 50, RED, WHITE), W / 2, 640, eob((t - b1["start"] - 1.2) / 0.3))

def sc_run(img, t, lt):
    img.alpha_composite(bg_street("night"))
    span = next(x for x in SCENES if x["scene"] == "run"); q = lt / (span["vend"] - span["vstart"])
    hx = lerp(-60, 1140, q); jmp = abs(math.sin(t * 13)) * 30
    draw_char(img, "H", hx, 960 - jmp, t, "det", 0.8, arms=(-150, 150))
    for k in range(3): paste_c(img, emoji("💨", 50), hx - 170 - k * 50, 1300 - k * 10, 0.8, alpha=0.7 - k * 0.2)
    paste_c(img, pill("CHALO, BILAL KE GHAR!", 54, YEL), W / 2, 330, eob(lt / 0.3), rot=-3)
    paste_c(img, pill("RAAT 10 BAJE", 40, WHITE, INK), W / 2, 450, eob((lt - 0.4) / 0.3))

def sc_bilal_door(img, t, lt):
    img.alpha_composite(bg_street("night"))
    d = ImageDraw.Draw(img); d.rectangle([150, 620, 520, 1190], fill=(255, 225, 150), outline=INK, width=8)
    v = LV("bilal_door")[0]; b = LB("bilal_door")[0]
    draw_char(img, "L", 335, 940, t, "happy", 0.95, arms=(-20, 140) if t < v["end"] else (-20, 20), laugh=t < v["start"] + 0.6 and t > v["start"])
    face = t > word_t(v, "bech", v["end"] - 0.6)
    draw_char(img, "H", 770, 950, t, "sad" if face else "n", 1.0, arms=(-20, -165) if face else (-20, 20))
    if t > v["start"] + 0.3: paste_c(img, emoji("🔌", 90), 470, 560, eob((t - v["start"] - 0.3) / 0.3), rot=10)
    if face: paste_c(img, emoji("🤦", 130), 900, 620, eob((t - word_t(v, "bech", v["end"] - 0.6)) / 0.3))
    if t > b["start"] + 0.1:
        k = t - b["start"] - 0.1
        paste_c(img, glow_text("BILAL KI SCHEME #2", "Anton-Regular.ttf", 92, WHITE, (255, 130, 40)), W / 2, 260, eob(k / 0.3), rot=-3)
        paste_c(img, pill("CHARGER BECH DIYA: Rs 80", 48, YEL), W / 2, 400, eob((k - 0.6) / 0.3), rot=3)

def sc_shop(img, t, lt):
    img.alpha_composite(bg_street("night")); shop_front(img, t); generator(img, 880, 1250, t)
    b0, b1 = LB("shop"); v = LV("shop")[0]
    pay = b1["start"]
    draw_char(img, "H", 380, 1000, t, "n" if t < b1["start"] else "det", 0.9, arms=(-20, -90 if abs(t - pay - 0.3) < 0.6 else 20))
    if t < pay: paste_c(img, pill("CHARGING: Rs 50 / GHANTA", 50, RED, WHITE), W / 2, 330, eob((t - b0["start"] - 0.4) / 0.3), rot=-3)
    else:
        k = t - pay; q = min(1, k / (b1["end"] - pay))
        if k < 1.0: paste_c(img, notes_img(50, 180), lerp(500, 700, eo(k / 0.6)), 1100 - 60 * math.sin(min(1, k / 0.6) * math.pi), 0.8, rot=-8)
        clock(img, 180, 330, 22 + q * 1.0)
        paste_c(img, pill(f"{10 + int(q * 59) // 60}:{int(q * 59) % 60:02d} PM", 40, YEL), 180, 460, 1.0)
        paste_c(img, phone_big("charging", t, 15 * eio(q)), 800, 700, 0.42, rot=4)
        paste_c(img, pill("-Rs 50", 58, RED, WHITE), 560, 300, eob(k / 0.3), rot=-4)
        if q > 0.3: zzz(img, 470, 700, t)

def sc_balance(img, t, lt):
    img.alpha_composite(grad((40, 30, 60), (12, 10, 25)))
    v = LV("balance")[0]; b = LB("balance")[0]; nob = word_t(v, "balance", v["end"] - 0.8)
    if t < v["start"] + 0.9: st = "charging"
    elif t < nob: st = "calling"
    else: st = "nobal"
    paste_c(img, phone_big(st, t, 15), W / 2, 760, eob(lt / 0.3) * 1.15 * (1 + 0.03 * eio(lt / 4)), rot=(math.sin(t * 50) * 2 if st == "nobal" and t < nob + 0.4 else 0))
    if st == "charging": paste_c(img, pill("PHONE ON!", 56, GRN, WHITE), W / 2, 230, eob((lt - 0.2) / 0.3))
    if st == "nobal":
        k = t - nob
        paste_c(img, glow_text("BALANCE ZERO!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 280, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("😭", 150), 880, 1250, eob((k - 0.4) / 0.3))
        if t > b["start"] + 0.4: paste_c(img, pill("RECHARGE WALI DUKAAN BAND!", 40, YEL), W / 2, 1300, eob((t - b["start"] - 0.4) / 0.3))

def sc_stranger(img, t, lt):
    img.alpha_composite(bg_street("night")); shop_front(img, t); generator(img, 880, 1250, t)
    b0, b1 = LB("stranger"); v = LV("stranger")[0]
    cx = lerp(1250, 760, eo((t - b0["start"] - 0.1) / 1.2))
    draw_char(img, "H", 330, 1000, t, "sad" if t < v["start"] + 1.2 else "shock" if t < b1["start"] else "happy", 0.9, arms=(-20, 20) if t < b1["start"] + 0.6 else (-20, -110))
    hand = t > v["start"] + 1.0
    draw_char(img, "C", cx, 990, t, "happy" if hand else "n", 0.92, arms=(-15 if not hand else -95, 15))
    if t > b0["start"] + 0.6 and t < v["start"] + 0.4: paste_c(img, pill("TAP TAP", 40, WHITE, INK), cx - 180, 700, 1.0, rot=-8)
    if hand:
        k = t - v["start"] - 1.0; q = eio(k / 1.0)
        paste_c(img, phone_img(True), lerp(cx - 230, 470, q), lerp(1060, 1130, q), 0.8, rot=-10)
        paste_c(img, bubble([("LO BETA,", INK), ("KAR LO CALL.", GRN)], 48, tail="right"), 760, 450, eob((k - 0.2) / 0.3))
    if t > b1["start"] + 0.8: paste_c(img, emoji("🥹", 110), 200, 650, eob((t - b1["start"] - 0.8) / 0.3))

def sc_callback(img, t, lt):
    img.alpha_composite(bg_street("night"))
    v = LV("callback")[0]; b = LB("callback")[0]; kar = word_t(v, "karachi", v["start"] + 1.4)
    happy = t < kar
    jmp = abs(math.sin(t * 9)) * 40 if t < kar and t > v["start"] + 0.2 else 0
    draw_char(img, "H", 300, 1000 - jmp, t, "happy" if happy else "shock", 0.95, arms=(-20, -150) if happy else (-110, -150))
    draw_char(img, "C", 860, 1010, t, "happy", 0.85, arms=(-15, 15))
    paste_c(img, phone_big("offer", t), 600, 680, eob((lt - 0.2) / 0.35) * 0.72, rot=4)
    if happy and t > v["start"] + 0.2: paste_c(img, glow_text("NAUKRI PAKKI!", "Anton-Regular.ttf", 110, WHITE, (40, 190, 110)), W / 2, 270, eob((t - v["start"] - 0.2) / 0.3), rot=-3)
    if not happy:
        k = t - kar
        paste_c(img, glow_text("PAR… KARACHI?!", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), W / 2, 270, eob(k / 0.3), rot=-3)
        if t > b["start"] + 0.4: paste_c(img, pill("LAHORE SE KARACHI: 1,200 KM", 46, WHITE, INK), W / 2, 1250, eob((t - b["start"] - 0.4) / 0.3))
        if t > b["start"] + 1.4: paste_c(img, emoji("😳", 110), 140, 640, eob((t - b["start"] - 1.4) / 0.3))

def sc_ticket(img, t, lt):
    img.alpha_composite(bg_room("night"))
    b0, b1 = LB("ticket"); v, va = LV("ticket")
    draw_char(img, "H", 300, 980, t, "sad" if t < va["start"] else "shock", 0.95, arms=(-20, -100))
    paste_c(img, phone_big("fare", t), 700, 700, eob((lt - 0.2) / 0.35) * 0.7, rot=-4)
    jt = word_t(v, "jeb", v["start"] + 1.6)
    if t > jt: 
        paste_c(img, pill("JEB: Rs 950", 56, WHITE, GRN), 300, 400, eob((t - jt) / 0.3), rot=-4)
        paste_c(img, pill("KAMI: Rs 550!", 56, RED, WHITE), 300, 520, eob((t - jt - 0.6) / 0.3), rot=3)
    if t > va["start"] - 0.3:
        k = t - va["start"] + 0.3
        ax = lerp(1300, 860, eo(k / 0.6))
        draw_char(img, "A", ax, 1000, t, "shock", 0.92, arms=(-60, 20))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, glow_text("AMMI NE SUN LIYA!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 290, eob(k / 0.3), rot=-3)
        paste_c(img, pill(f"DAY {META['day'] + 1} KAL • FOLLOW +", 50, RED, WHITE), W / 2, 1290, eob((k - 0.7) / 0.35) * (1 + 0.04 * math.sin(t * 8)))


SC = {"hook": sc_hook, "daycard": sc_daycard, "home": sc_home, "fees": sc_fees, "abbu": sc_abbu, "night": sc_night, "end": sc_end,
      "hook_dhaba": sc_hook_dhaba, "dhaba": sc_dhaba, "burn": sc_burn, "pay": sc_pay, "bilal": sc_bilal, "end_diary": sc_end_diary,
      "hook_scheme": sc_hook_scheme, "market": sc_market, "dummy": sc_dummy, "rooftop": sc_rooftop,
      "hook_tuition": sc_hook_tuition, "alarm": sc_alarm, "paper": sc_paper, "chain": sc_chain, "late": sc_late,
      "tuition": sc_tuition, "asleep": sc_asleep, "wake": sc_wake, "end_call": sc_end_call,
      "hook_dead": sc_hook_dead, "bijli": sc_bijli, "run": sc_run, "bilal_door": sc_bilal_door, "shop": sc_shop, "balance": sc_balance,
      "stranger": sc_stranger, "callback": sc_callback, "ticket": sc_ticket}

def frame(t):
    s = next((x for x in SCENES if x["vstart"] <= t < x["vend"]), SCENES[-1])
    lt = t - s["vstart"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    SC[s["scene"]](img, t, lt)
    # slow push-in per scene
    z = 1 + 0.045 * eio(lt / max(1.0, s["vend"] - s["vstart"]))
    if z > 1.001:
        cw, ch = W / z, H / z
        img = img.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2 * 0.6, (W + cw) / 2, (H - ch) / 2 * 0.6 + ch))
    # scene fade from black
    if lt < 0.25 and s is not SCENES[0]:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - lt / 0.25)))))
    hud(img, t); caption(img, t)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([80, 1868, W - 80, 1878], radius=5, fill=(70, 70, 90)); d.rounded_rectangle([80, 1868, 80 + (W - 160) * t / TOTAL, 1878], radius=5, fill=YEL)
    return img.convert("RGB")

if ONLY and ONLY.startswith("still:"):
    for tt in ONLY[6:].split(","): frame(float(tt)).save(f"{D}/still_{tt}.png")
    sys.exit()
n = int(TOTAL * FPS)
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", f"{D}/video.tmp.mp4"], stdin=subprocess.PIPE)
for k in range(n):
    p.stdin.write(frame(k / FPS).tobytes())
    if k % 300 == 0: print("frame", k, "/", n, flush=True)
p.stdin.close(); p.wait(); print("rc", p.returncode)
