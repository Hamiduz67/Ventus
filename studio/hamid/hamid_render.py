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
NAMES = {"H": ("HAMID", (60, 150, 255)), "A": ("AMMI", (230, 90, 140)), "B": ("ABBU", (150, 120, 90)), "L": ("BILAL", (255, 130, 40)), "C": ("CHACHA", (110, 140, 170)),
         "G": ("CHACHA GHAFOOR", (120, 150, 80)), "M": ("MANAGER", (80, 110, 170)), "T": ("MASTER SALEEM", (150, 50, 70)), "Z": ("BACHA", (230, 130, 50)), "R": ("SETH RAUF", (40, 110, 70)), "P": ("SIR", (40, 60, 110)), "N": ("AMMA JI", (150, 120, 200)), "J": ("JADUGAR", (110, 50, 170))}

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
SKIN = {"H": (200, 146, 106), "A": (214, 160, 122), "B": (182, 128, 92), "L": (176, 122, 84), "K": (190, 136, 98), "C": (176, 124, 90), "X": (170, 118, 82), "G": (186, 132, 96), "M": (196, 142, 104), "T": (192, 138, 100), "Z": (168, 116, 80), "R": (188, 130, 92), "P": (184, 130, 94), "N": (206, 156, 120), "J": (194, 140, 102)}
HW = 300
@lru_cache(None)
def head(who, eyes, mouth, brows):
    s = SS; c = HW * s; im = Image.new("RGBA", (c, c), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = c / 2, c / 2 + 14 * s, 112 * s; skin = SKIN[who]
    if who in ("A", "N"):  # dupatta / white chaddar behind head
        d.ellipse([cx - r - 34 * s, cy - r - 34 * s, cx + r + 34 * s, cy + r + 70 * s], fill=(40, 140, 110) if who == "A" else (236, 236, 240), outline=INK, width=6 * s)
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
    elif who == "N":  # Amma ji (Seth Rauf's mother, Day 17): white chaddar, grey hair, wrinkles
        d.chord([cx - r - 14 * s, cy - r - 30 * s, cx + r + 14 * s, cy + 2 * s], 180, 360, fill=(245, 245, 248), outline=INK, width=6 * s)
        for sx in (-1, 1): d.chord([cx + sx * 30 * s - 44 * s, cy - r + 6 * s, cx + sx * 30 * s + 44 * s, cy - r + 50 * s], 0, 180, fill=(175, 175, 182), outline=INK, width=3 * s)
        for sx in (-1, 1):
            d.arc([cx + sx * 74 * s - 18 * s, cy + 40 * s, cx + sx * 74 * s + 18 * s, cy + 80 * s], 90 if sx < 0 else 0, 180 if sx < 0 else 90, fill=(150, 100, 75), width=4 * s)
        d.line([(cx - 30 * s, cy - 70 * s), (cx + 30 * s, cy - 70 * s)], fill=(160, 112, 85), width=3 * s)
    elif who == "J":  # Jadugar (Day 19, street "paise double" trickster): slick black hair (top hat = tophat())
        d.chord([cx - r - 6 * s, cy - r - 20 * s, cx + r + 6 * s, cy + 4 * s], 180, 360, fill=(20, 18, 26), outline=INK, width=6 * s)
    elif who == "K":  # Ali, the tuition kid: neat side-parted hair
        d.chord([cx - r - 6 * s, cy - r - 18 * s, cx + r + 6 * s, cy + 10 * s], 180, 360, fill=(40, 30, 28), outline=INK, width=6 * s)
        d.polygon([(cx - r, cy - 30 * s), (cx + 30 * s, cy - r - 8 * s), (cx + r, cy - 40 * s), (cx + r, cy - 70 * s), (cx - r, cy - 70 * s)], fill=(40, 30, 28))
    elif who == "C":  # Chacha (kind stranger): white topi + white beard
        d.chord([cx - 82 * s, cy + 10 * s, cx + 82 * s, cy + r * 1.35], 0, 180, fill=(240, 240, 238), outline=INK, width=5 * s)
        d.rounded_rectangle([cx - r + 8 * s, cy - r - 30 * s, cx + r - 8 * s, cy - r + 34 * s], radius=26 * s, fill=(250, 250, 248), outline=INK, width=6 * s)
        for k in range(5): d.line([(cx - r + 30 * s + k * 40 * s, cy - r - 20 * s), (cx - r + 30 * s + k * 40 * s, cy - r + 26 * s)], fill=(200, 200, 205), width=3 * s)
    elif who == "X":  # station guard: blue peaked cap + thick moustache
        d.chord([cx - r - 6 * s, cy - r - 40 * s, cx + r + 6 * s, cy - 4 * s], 180, 360, fill=(40, 60, 120), outline=INK, width=6 * s)
        d.rounded_rectangle([cx - r - 10 * s, cy - 40 * s, cx + 40 * s, cy - 18 * s], radius=10 * s, fill=(25, 35, 70), outline=INK, width=5 * s)
        d.ellipse([cx - 14 * s, cy - r - 10 * s, cx + 14 * s, cy - r + 18 * s], fill=(255, 210, 60), outline=INK, width=3 * s)
    elif who == "G":  # Chacha Ghafoor (bike + room landlord): bald + shine, grey side tufts
        for sx in (-1, 1):
            d.chord([cx + sx * (r - 8 * s) - 38 * s, cy - 80 * s, cx + sx * (r - 8 * s) + 38 * s, cy + 20 * s], 90 if sx < 0 else -90, 270 if sx < 0 else 90, fill=(175, 175, 180))
        d.ellipse([cx - 62 * s, cy - r + 14 * s, cx - 10 * s, cy - r + 42 * s], fill=(255, 235, 215))
    elif who == "T":  # Master Saleem (retired teacher): swept-back white hair
        for k in range(6):
            x = cx - r + 6 * s + k * 44 * s
            d.ellipse([x - 32 * s, cy - r - 22 * s - (k % 2) * 8 * s, x + 32 * s, cy - r + 36 * s], fill=(236, 236, 232), outline=INK, width=4 * s)
        d.chord([cx - r + 4 * s, cy - r + 4 * s, cx + r - 4 * s, cy - 6 * s], 180, 360, fill=(236, 236, 232))
        for sx in (-1, 1): d.chord([cx + sx * (r - 6 * s) - 34 * s, cy - 60 * s, cx + sx * (r - 6 * s) + 34 * s, cy + 24 * s], 90 if sx < 0 else -90, 270 if sx < 0 else 90, fill=(240, 240, 236))
    elif who == "M":  # delivery office manager: neat side-parted hair + pen behind the ear
        d.chord([cx - r - 6 * s, cy - r - 22 * s, cx + r + 6 * s, cy + 6 * s], 180, 360, fill=(30, 26, 30), outline=INK, width=6 * s)
        d.polygon([(cx - r, cy - 40 * s), (cx - 40 * s, cy - r - 4 * s), (cx + r, cy - 50 * s), (cx + r, cy - 80 * s), (cx - r, cy - 80 * s)], fill=(30, 26, 30))
        d.line([(cx + r - 10 * s, cy - 40 * s), (cx + r + 40 * s, cy + 20 * s)], fill=(40, 90, 200), width=9 * s)
    elif who == "Z":  # street kid (Karachi): messy spiky hair + dust smudge on the cheek
        for k in range(8):
            x = cx - r + 4 * s + k * 30 * s
            d.polygon([(x - 26 * s, cy - r + 30 * s), (x + (k % 3 - 1) * 14 * s, cy - r - 34 * s - (k % 2) * 16 * s), (x + 26 * s, cy - r + 26 * s)], fill=(70, 45, 30), outline=INK)
        d.chord([cx - r - 4 * s, cy - r - 12 * s, cx + r + 4 * s, cy - 20 * s], 180, 360, fill=(70, 45, 30))
        d.ellipse([cx + 50 * s, cy + 30 * s, cx + 92 * s, cy + 52 * s], fill=(140, 100, 75))
    elif who == "R":  # Seth Rauf (Karachi dhaba owner): slicked black hair with a grey streak, chubby cheeks
        d.chord([cx - r - 8 * s, cy - r - 28 * s, cx + r + 8 * s, cy + 0 * s], 180, 360, fill=(22, 20, 26), outline=INK, width=6 * s)
        d.polygon([(cx - r, cy - 40 * s), (cx - 30 * s, cy - r - 16 * s), (cx + r, cy - 30 * s), (cx + r, cy - 80 * s), (cx - r, cy - 80 * s)], fill=(22, 20, 26))
        d.line([(cx + 10 * s, cy - r - 14 * s), (cx + 70 * s, cy - r + 20 * s)], fill=(170, 170, 175), width=12 * s)
        for sx in (-1, 1): d.ellipse([cx + sx * 70 * s - 26 * s, cy + 30 * s, cx + sx * 70 * s + 26 * s, cy + 62 * s], fill=(225, 120, 110))
    elif who == "P":  # college professor (Day 15): receding black hair with grey sides + neat beard
        for sx in (-1, 1): d.chord([cx + sx * (r - 6 * s) - 40 * s, cy - 90 * s, cx + sx * (r - 6 * s) + 40 * s, cy + 24 * s], 90 if sx < 0 else -90, 270 if sx < 0 else 90, fill=(120, 120, 128))
        d.chord([cx - r + 10 * s, cy - r - 10 * s, cx + r - 10 * s, cy - 40 * s], 180, 360, fill=(30, 26, 30), outline=INK, width=5 * s)
        d.chord([cx - 84 * s, cy + 20 * s, cx + 84 * s, cy + r * 1.25], 0, 180, fill=(70, 66, 72), outline=INK, width=5 * s)
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
        bcol = (25, 22, 28) if who not in ("B", "C", "G", "N") else (150, 150, 155)
        if who == "G": bw = 13 * s
        if who == "L": bw = 12 * s
        if brows == "sad":
            d.line([(ex - 22 * s, by + (0 if sx > 0 else 10 * s)), (ex + 22 * s, by + (10 * s if sx > 0 else 0))], fill=bcol, width=bw)
        elif brows == "angry":
            d.line([(ex - 22 * s, by + (12 * s if sx > 0 else 0)), (ex + 22 * s, by + (0 if sx > 0 else 12 * s))], fill=bcol, width=bw)
        elif brows == "up":
            d.arc([ex - 24 * s, by - 14 * s, ex + 24 * s, by + 10 * s], 200, 340, fill=bcol, width=bw)
        else:
            d.line([(ex - 22 * s, by + 4 * s), (ex + 22 * s, by)], fill=bcol, width=bw)
    if who == "T":   # round gold glasses
        for sx in (-1, 1):
            ex = cx + sx * 44 * s; d.ellipse([ex - 36 * s, ey - 34 * s, ex + 36 * s, ey + 34 * s], outline=(200, 150, 40), width=6 * s)
        d.line([(cx - 8 * s, ey), (cx + 8 * s, ey)], fill=(200, 150, 40), width=6 * s)
    if who == "N":   # small round silver glasses
        for sx in (-1, 1):
            ex = cx + sx * 44 * s; d.ellipse([ex - 32 * s, ey - 30 * s, ex + 32 * s, ey + 30 * s], outline=(150, 150, 165), width=5 * s)
        d.line([(cx - 10 * s, ey), (cx + 10 * s, ey)], fill=(150, 150, 165), width=5 * s)
    if who == "J":   # dark round sunglasses
        for sx in (-1, 1):
            ex = cx + sx * 44 * s; d.ellipse([ex - 38 * s, ey - 30 * s, ex + 38 * s, ey + 30 * s], fill=(20, 20, 30), outline=INK, width=6 * s)
            d.ellipse([ex - 22 * s, ey - 20 * s, ex - 6 * s, ey - 6 * s], fill=(120, 120, 170))
        d.line([(cx - 8 * s, ey), (cx + 8 * s, ey)], fill=INK, width=6 * s)
    if who == "P":   # black rectangular glasses
        for sx in (-1, 1):
            ex = cx + sx * 44 * s; d.rounded_rectangle([ex - 38 * s, ey - 28 * s, ex + 38 * s, ey + 28 * s], radius=8 * s, outline=INK, width=7 * s)
        d.line([(cx - 8 * s, ey), (cx + 8 * s, ey)], fill=INK, width=6 * s)
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
    if who == "X":
        d.chord([cx - 56 * s, my - 34 * s, cx + 56 * s, my + 4 * s], 180, 360, fill=(30, 25, 25), outline=INK, width=3 * s)
    if who == "G":   # big curled grey moustache
        d.chord([cx - 74 * s, my - 40 * s, cx + 74 * s, my + 4 * s], 180, 360, fill=(190, 190, 195), outline=INK, width=4 * s)
        for sx in (-1, 1): d.arc([cx + sx * 74 * s - 22 * s, my - 40 * s, cx + sx * 74 * s + 22 * s, my + 4 * s], 270 if sx > 0 else 180, 90 if sx > 0 else 0, fill=INK, width=5 * s)
    if who == "R":   # big black handlebar moustache + double chin
        d.chord([cx - 80 * s, my - 44 * s, cx + 80 * s, my + 6 * s], 180, 360, fill=(22, 20, 26), outline=INK, width=4 * s)
        for sx in (-1, 1): d.arc([cx + sx * 80 * s - 24 * s, my - 52 * s, cx + sx * 80 * s + 24 * s, my - 4 * s], 270 if sx > 0 else 180, 90 if sx > 0 else 0, fill=INK, width=6 * s)
        d.arc([cx - 60 * s, my + 30 * s, cx + 60 * s, my + 60 * s], 20, 160, fill=INK, width=4 * s)
    if who == "J":   # thin curled moustache
        for sx in (-1, 1): d.arc([cx + sx * 34 * s - 34 * s, my - 36 * s, cx + sx * 34 * s + 34 * s, my - 2 * s], 180 if sx < 0 else 270, 270 if sx < 0 else 360, fill=INK, width=7 * s)
        for sx in (-1, 1): d.arc([cx + sx * 72 * s - 12 * s, my - 52 * s, cx + sx * 72 * s + 12 * s, my - 26 * s], 0 if sx > 0 else 180, 180 if sx > 0 else 360, fill=INK, width=6 * s)
    if who == "T":   # neat white moustache
        d.chord([cx - 50 * s, my - 30 * s, cx + 50 * s, my + 2 * s], 180, 360, fill=(245, 245, 242), outline=INK, width=3 * s)
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
    elif who == "X":
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(190, 170, 120), outline=INK, width=7 * s)
        d.line([(w / 2, 60 * s), (w / 2, h)], fill=INK, width=4 * s); d.rectangle([w / 2 + 40 * s, 150 * s, w / 2 + 110 * s, 190 * s], fill=(40, 60, 120), outline=INK, width=3 * s)
        d.line([(70 * s, 120 * s), (w - 90 * s, h)], fill=(120, 90, 50), width=14 * s)
    elif who == "G":   # white banyan + checked gamcha on the shoulder
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(240, 240, 232), outline=INK, width=7 * s)
        d.chord([w / 2 - 110 * s, -40 * s, w / 2 + 110 * s, 170 * s], 0, 180, fill=SKIN["G"], outline=INK, width=5 * s)
        d.polygon([(70 * s, 60 * s), (170 * s, 50 * s), (130 * s, h), (60 * s, h)], fill=(210, 60, 60), outline=INK)
        for k in range(6): d.line([(80 * s, (90 + k * 55) * s), (160 * s, (80 + k * 55) * s)], fill=WHITE, width=5 * s)
    elif who == "M":   # light blue shirt, red tie, ID card
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(170, 205, 240), outline=INK, width=7 * s)
        d.polygon([(w / 2 - 50 * s, 50 * s), (w / 2, 110 * s), (w / 2 + 50 * s, 50 * s)], fill=SKIN["M"], outline=INK)
        d.polygon([(w / 2 - 14 * s, 105 * s), (w / 2 + 14 * s, 105 * s), (w / 2 + 22 * s, 300 * s), (w / 2, 330 * s), (w / 2 - 22 * s, 300 * s)], fill=(200, 40, 50), outline=INK)
        d.line([(w / 2 - 40 * s, 60 * s), (w / 2 + 90 * s, 200 * s)], fill=(40, 90, 200), width=5 * s)
        d.rectangle([w / 2 + 70 * s, 190 * s, w / 2 + 130 * s, 260 * s], fill=WHITE, outline=INK, width=4 * s)
    elif who == "T":   # white shirt + maroon sweater vest + pen
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(240, 240, 235), outline=INK, width=7 * s)
        d.rounded_rectangle([95 * s, 95 * s, w - 95 * s, h + 80 * s], radius=90 * s, fill=(140, 40, 60), outline=INK, width=6 * s)
        d.polygon([(w / 2 - 70 * s, 95 * s), (w / 2, 230 * s), (w / 2 + 70 * s, 95 * s)], fill=(240, 240, 235), outline=INK)
        d.polygon([(w / 2 - 40 * s, 50 * s), (w / 2, 100 * s), (w / 2 + 40 * s, 50 * s)], fill=SKIN["T"], outline=INK)
        d.line([(w / 2 + 80 * s, 140 * s), (w / 2 + 80 * s, 200 * s)], fill=(40, 90, 200), width=8 * s)
    elif who == "Z":   # faded, oversized orange T-shirt with a patch
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(225, 140, 70), outline=INK, width=7 * s)
        d.chord([w / 2 - 70 * s, 10 * s, w / 2 + 70 * s, 110 * s], 0, 180, fill=SKIN["Z"], outline=INK, width=5 * s)
        d.rectangle([w / 2 + 40 * s, 200 * s, w / 2 + 110 * s, 260 * s], fill=(120, 110, 160), outline=INK, width=4 * s)
        for k in range(3): d.line([(w / 2 + 50 * s + k * 22 * s, 205 * s), (w / 2 + 50 * s + k * 22 * s, 255 * s)], fill=INK, width=2 * s)
    elif who == "R":   # cream kameez + dark green waistcoat + gold pen, a little paunch
        d.rounded_rectangle([40 * s, 50 * s, w - 40 * s, h + 80 * s], radius=150 * s, fill=(240, 230, 205), outline=INK, width=7 * s)
        d.rounded_rectangle([70 * s, 90 * s, w - 70 * s, h + 80 * s], radius=110 * s, fill=(30, 100, 70), outline=INK, width=6 * s)
        d.polygon([(w / 2 - 60 * s, 90 * s), (w / 2, 260 * s), (w / 2 + 60 * s, 90 * s)], fill=(240, 230, 205), outline=INK)
        d.polygon([(w / 2 - 40 * s, 50 * s), (w / 2, 100 * s), (w / 2 + 40 * s, 50 * s)], fill=SKIN["R"], outline=INK)
        for k in range(3): d.ellipse([w / 2 - 7 * s, (280 + 40 * k) * s, w / 2 + 7 * s, (294 + 40 * k) * s], fill=(230, 190, 70), outline=INK, width=2 * s)
        d.line([(w / 2 + 90 * s, 150 * s), (w / 2 + 90 * s, 215 * s)], fill=(230, 190, 70), width=9 * s)
    elif who == "N":   # lavender kameez + white chaddar over the shoulders
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(170, 150, 200), outline=INK, width=7 * s)
        for k in range(4): d.ellipse([w / 2 - 70 * s + k * 46 * s, 280 * s, w / 2 - 56 * s + k * 46 * s, 294 * s], fill=(235, 225, 245))
        d.polygon([(40 * s, 70 * s), (w - 40 * s, 70 * s), (w - 110 * s, 250 * s), (w / 2, 200 * s), (110 * s, 250 * s)], fill=(245, 245, 248), outline=INK)
    elif who == "P":   # navy blazer, white shirt, maroon tie
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(40, 55, 95), outline=INK, width=7 * s)
        d.polygon([(w / 2 - 70 * s, 55 * s), (w / 2, 250 * s), (w / 2 + 70 * s, 55 * s)], fill=(245, 245, 240), outline=INK)
        d.polygon([(w / 2 - 40 * s, 50 * s), (w / 2, 100 * s), (w / 2 + 40 * s, 50 * s)], fill=SKIN["P"], outline=INK)
        d.polygon([(w / 2 - 12 * s, 100 * s), (w / 2 + 12 * s, 100 * s), (w / 2 + 18 * s, 230 * s), (w / 2, 252 * s), (w / 2 - 18 * s, 230 * s)], fill=(140, 40, 60), outline=INK)
    elif who == "J":   # black waistcoat with gold stars over a red shirt + bow tie
        d.rounded_rectangle([60 * s, 50 * s, w - 60 * s, h + 80 * s], radius=130 * s, fill=(200, 50, 60), outline=INK, width=7 * s)
        d.rounded_rectangle([90 * s, 90 * s, w - 90 * s, h + 80 * s], radius=100 * s, fill=(30, 28, 40), outline=INK, width=6 * s)
        d.polygon([(w / 2 - 60 * s, 90 * s), (w / 2, 240 * s), (w / 2 + 60 * s, 90 * s)], fill=(200, 50, 60), outline=INK)
        d.polygon([(w / 2 - 40 * s, 50 * s), (w / 2, 100 * s), (w / 2 + 40 * s, 50 * s)], fill=SKIN["J"], outline=INK)
        d.polygon([(w / 2 - 40 * s, 92 * s), (w / 2 + 40 * s, 128 * s), (w / 2 + 40 * s, 92 * s), (w / 2 - 40 * s, 128 * s)], fill=(240, 190, 50), outline=INK)
        for (sx_, sy_) in ((130, 260), (300, 300), (150, 380), (290, 400)): d.regular_polygon((sx_ * s, sy_ * s, 16 * s), 5, fill=(240, 190, 50))
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
    sleeve = {"H": (245, 245, 240), "A": (150, 40, 70), "B": (200, 200, 195), "L": (255, 190, 50), "K": (150, 200, 240), "C": (110, 140, 170), "X": (190, 170, 120), "G": SKIN["G"], "M": (170, 205, 240), "T": (240, 240, 235), "Z": (225, 140, 70), "R": (240, 230, 205), "P": (40, 55, 95), "N": (170, 150, 200), "J": (30, 28, 40)}[who]
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
    if META.get("diary_bg") == "ghafoor":
        img.alpha_composite(bg_ghafoor("night")); bulb_glow(img, 60)
        paste_c(img, bike_img(True), 560, 1230, 0.75)
        draw_char(img, "H", 300, 1000, t, "happy", 0.92, arms=(-20, 20))
        return _diary(img, t, lt)
    if META.get("diary_bg") == "station":
        img.alpha_composite(bg_station("night")); tube_glow(img)
        draw_char(img, "H", W / 2, 1060, t, "det", 0.95, arms=(-30, 30), hold=hold_bag)
        mosquitoes(img, t, 540, 860, 2)
        return _diary(img, t, lt)
    img.alpha_composite(bg_room("night"))
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([200, 700, 1000, 1500], fill=(255, 200, 110, 110))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(90)))
    draw_char(img, "H", W / 2, 900, t, "det", 1.05, arms=(-30, 30))
    d = ImageDraw.Draw(img); d.rectangle([0, 1250, W, 1290], fill=(120, 80, 50), outline=INK, width=4); d.rectangle([0, 1290, W, 1420], fill=(90, 60, 40))
    _diary(img, t, lt)
def _diary(img, t, lt):
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


# ======================= DAY 6+: KABADI, POTLI, BUS, KARACHI BUS STATION, GUARD (reusable)
@lru_cache(None)
def bag_img():
    im = Image.new("RGBA", (300, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.arc([90, 0, 210, 110], 180, 360, fill=INK, width=12)
    d.rounded_rectangle([10, 50, 290, 195], radius=40, fill=(60, 90, 150), outline=INK, width=7)
    d.line([(30, 110), (270, 110)], fill=(40, 60, 110), width=6); d.rectangle([130, 95, 170, 125], fill=(220, 200, 90), outline=INK, width=3)
    return im
@lru_cache(None)
def potli_img(open_=False):
    im = Image.new("RGBA", (300, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if not open_:
        d.ellipse([20, 70, 280, 250], fill=(220, 80, 90), outline=INK, width=7)
        d.polygon([(110, 80), (150, 10), (190, 80)], fill=(220, 80, 90), outline=INK)
        d.line([(110, 82), (190, 82)], fill=(255, 210, 60), width=10)
        for k in range(6): d.ellipse([50 + k * 38, 140 + (k % 2) * 40, 64 + k * 38, 154 + (k % 2) * 40], fill=(255, 230, 120))
    else:
        d.ellipse([0, 120, 300, 260], fill=(220, 80, 90), outline=INK, width=7)
        for k in range(3): d.ellipse([50 + k * 20, 90 - k * 22, 250 - k * 20, 170 - k * 22], fill=(225, 175, 95), outline=INK, width=5)
        d.rounded_rectangle([190, 20, 290, 80], radius=6, fill=(120, 190, 130), outline=INK, width=4)
        d.text((240, 50), "400", font=fnt("Anton-Regular.ttf", 36), fill=INK, anchor="mm")
    return im
def hold_bag(img, x, y, sc): paste_c(img, bag_img(), x + 170 * sc, y + 240 * sc, sc * 0.8, rot=-4)
def hold_potli(img, x, y, sc): paste_c(img, potli_img(False), x - 150 * sc, y + 230 * sc, sc * 0.6, rot=6)

@lru_cache(None)
def bus_img():
    s = SS; im = Image.new("RGBA", (900 * s, 420 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10 * s, 20 * s, 890 * s, 340 * s], radius=40 * s, fill=(245, 200, 60), outline=INK, width=8 * s)
    for k, c in enumerate([(230, 60, 70), (40, 160, 120), (60, 110, 220)]): d.rectangle([14 * s, (250 + k * 22) * s, 886 * s, (268 + k * 22) * s], fill=c)
    for k in range(6): d.rounded_rectangle([(60 + k * 125) * s, 60 * s, (165 + k * 125) * s, 170 * s], radius=14 * s, fill=(40, 50, 80), outline=INK, width=5 * s)
    d.rounded_rectangle([800 * s, 60 * s, 880 * s, 230 * s], radius=14 * s, fill=(70, 90, 130), outline=INK, width=5 * s)
    for k in range(9): d.polygon([((40 + k * 95) * s, 20 * s), ((80 + k * 95) * s, 20 * s), ((60 + k * 95) * s, 50 * s)], fill=(230, 60, 70))
    d.rectangle([340 * s, 190 * s, 560 * s, 236 * s], fill=WHITE, outline=INK, width=4 * s)
    d.text((450 * s, 213 * s), "LAHORE - KARACHI", font=fnt("Poppins-Black.ttf", 26 * s), fill=INK, anchor="mm")
    return ssf(im)
def wheel(img, x, y, t, r=55):
    d = ImageDraw.Draw(img); d.ellipse([x - r, y - r, x + r, y + r], fill=(35, 35, 40), outline=INK, width=6)
    d.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(180, 180, 190))
    a = t * 12
    for k in range(3): d.line([(x, y), (x + math.cos(a + k * 2.1) * 20, y + math.sin(a + k * 2.1) * 20)], fill=INK, width=5)

@lru_cache(None)
def bg_station(mode="night"):
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im)
    top, bot = {"night": ((8, 12, 32), (40, 40, 80)), "dawn": ((120, 150, 210), (255, 200, 150))}[mode]
    for y in range(0, 900 * s, 4): d.rectangle([0, y, W * s, y + 4], fill=mixc(top, bot, y / (900 * s)))
    r = np.random.default_rng(66); x = -30; sil = (25, 28, 55) if mode == "night" else (110, 110, 150)
    while x < W:   # city towers behind the adda
        w = r.uniform(70, 150); h = r.uniform(250, 560)
        d.rectangle([x * s, (900 - h) * s, (x + w) * s, 900 * s], fill=sil)
        if mode == "night":
            for wy in range(int(900 - h) + 20, 880, 40):
                for wx in range(int(x) + 12, int(x + w) - 16, 28):
                    if r.random() < 0.35: d.rectangle([wx * s, wy * s, (wx + 10) * s, (wy + 14) * s], fill=(255, 220, 130))
        x += w + 6
    d.rectangle([0, 900 * s, W * s, H * s], fill=(70, 66, 80) if mode == "night" else (150, 140, 135))
    for x in range(-40, W, 200): d.rectangle([x * s, 1330 * s, (x + 120) * s, 1342 * s], fill=(200, 190, 150))
    # shelter roof + pillars
    d.polygon([(0, 300 * s), (W * s, 300 * s), (W * s, 400 * s), (0, 400 * s)], fill=(150, 160, 170), outline=INK)
    d.rectangle([0, 400 * s, W * s, 420 * s], fill=(90, 95, 110))
    for px in (80, 980): d.rectangle([(px - 25) * s, 420 * s, (px + 25) * s, 1250 * s], fill=(170, 170, 180), outline=INK, width=5 * s)
    d.rounded_rectangle([330 * s, 315 * s, 750 * s, 390 * s], radius=10 * s, fill=(30, 110, 70), outline=INK, width=5 * s)
    d.text((540 * s, 352 * s), "KARACHI BUS ADDA", font=fnt("Anton-Regular.ttf", 46 * s), fill=WHITE, anchor="mm")
    for lx in (250, 830): d.rounded_rectangle([(lx - 70) * s, 430 * s, (lx + 70) * s, 448 * s], radius=8 * s, fill=(240, 250, 255) if mode == "night" else (200, 200, 210))
    # bench
    d.rectangle([260 * s, 1110 * s, 820 * s, 1140 * s], fill=(60, 120, 170), outline=INK, width=5 * s)
    d.rectangle([260 * s, 1040 * s, 820 * s, 1070 * s], fill=(60, 120, 170), outline=INK, width=5 * s)
    for bx in (280, 780): d.rectangle([bx * s, 1140 * s, (bx + 22) * s, 1250 * s], fill=(80, 80, 90), outline=INK, width=4 * s)
    return ssf(im)
def tube_glow(img):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o = ImageDraw.Draw(g)
    for lx in (250, 830): o.ellipse([lx - 300, 380, lx + 300, 1100], fill=(200, 230, 255, 45))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
def mosquitoes(img, t, cx, cy, n=4):
    for k in range(n):
        x = cx + math.sin(t * 7 + k * 1.7) * 120 + math.sin(t * 13 + k) * 20; y = cy + math.cos(t * 6 + k * 2.3) * 90
        paste_c(img, emoji("🦟", 40), x, y, 1.0)

def sc_hook_station(img, t, lt):
    img.alpha_composite(bg_station("night")); tube_glow(img)
    draw_char(img, "H", 540, 1000, t, "sad", 0.95, arms=(-20, 20), hold=hold_bag)
    mosquitoes(img, t, 540, 760, 3)
    paste_c(img, glow_text("KARACHI KI PEHLI RAAT", "Anton-Regular.ttf", 96, WHITE, (90, 160, 255)), W / 2, 520, eob((lt - 0.2) / 0.35))
    paste_c(img, pill("JEB MEIN: Rs 120", 60, RED, WHITE), W / 2, 650, eob((lt - 2.2) / 0.35) * (1 + 0.04 * math.sin(t * 8)), rot=-3)

def sc_ammi(img, t, lt):
    img.alpha_composite(bg_room("night")); bulb_glow(img, 70)
    va, vh = LV("ammi"); b = LB("ammi")[0]
    draw_char(img, "A", 300, 950, t, "det" if t < b["start"] else "sad", 0.98, arms=(-20, -120) if t < va["end"] else (-20, 20))
    draw_char(img, "H", 790, 960, t, "sad" if t < vh["start"] else "det", 0.98, arms=(-20, 20), hold=hold_bag)
    if t < vh["start"] + 0.2: paste_c(img, glow_text("NAHI JAANA!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 330, eob((lt - 0.3) / 0.3), rot=-4)
    else: paste_c(img, pill("Rs 25,000 / MAHINA", 56, WHITE, GRN), W / 2, 330, eob((t - vh["start"] - 0.2) / 0.3), rot=3)
    if t > b["start"]:
        k = t - b["start"]
        paste_c(img, pill("AMMI CHUP… AUR KAMRE SE BAHAR", 40, YEL), W / 2, 460, eob(k / 0.3))
        for j in range(2):
            q = (k * 0.8 + j * 0.5) % 1; paste_c(img, emoji("💧", 30), 300 + (j * 2 - 1) * 44, 900 + q * 90, 1.0, alpha=1 - q)

def sc_kabadi(img, t, lt):
    img.alpha_composite(bg_street("day"))
    b0, b1 = LB("kabadi"); v = LV("kabadi")[0]
    d = ImageDraw.Draw(img)   # kabadi cart
    d.rectangle([700, 1050, 1060, 1200], fill=(150, 100, 60), outline=INK, width=6)
    for k in range(5): d.rectangle([710 + k * 68, 980 - (k % 2) * 40, 770 + k * 68, 1050], fill=[(150, 150, 160), (120, 90, 70), (200, 190, 160), (90, 120, 150), (170, 160, 150)][k], outline=INK, width=4)
    wheel(img, 760, 1220, 0, 50); wheel(img, 1000, 1220, 0, 50)
    d = ImageDraw.Draw(img); d.rectangle([720, 880, 1040, 950], fill=YEL, outline=INK, width=5)
    d.text((880, 915), "PURANA SAMAAN", font=fnt("Poppins-Black.ttf", 34), fill=INK, anchor="mm")
    sold = t > word_t(v, "bech", v["start"] + 1.4)
    cx = lerp(150, 520, eo((t - b0["start"]) / 1.2)) if not sold else lerp(520, 640, eo((t - word_t(v, "bech", 0)) / 0.6))
    paste_c(img, cycle_img(True), cx + 120, 1210, 0.8)
    draw_char(img, "H", 260, 1000, t, "sad" if sold else "det", 0.9, arms=(-20, -40))
    if t < v["start"]: paste_c(img, pill("PURANI CYCLE • TICKET KE LIYE", 46, YEL), W / 2, 330, eob((t - b0["start"] - 0.2) / 0.3), rot=-3)
    if t > v["start"] + 1.0: paste_c(img, bubble([("BAS 300!", RED)], 54, tail="right"), 840, 640, eob((t - v["start"] - 1.0) / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, notes_img(300, 180), 330, 1250, eob(k / 0.3) * 0.8, rot=-8)
        paste_c(img, pill("ABHI BHI KAMI: Rs 250", 54, RED, WHITE), W / 2, 330, eob((k - 0.3) / 0.3), rot=3)

def sc_potli(img, t, lt):
    img.alpha_composite(bg_room("night"))
    lamp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lamp).ellipse([200, 600, 1000, 1400], fill=(255, 200, 110, 100))
    img.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(90)))
    b0, b1 = LB("potli"); v = LV("potli")[0]
    paste_c(img, bag_img(), 820, 1230, 0.8)
    draw_char(img, "H", 720, 960, t, "sad" if t < v["start"] else ("shock" if t < b1["start"] + 0.4 else "happy"), 0.95, arms=(-20, 20))
    ax = lerp(-200, 300, eo((t - b0["start"] - 0.2) / 1.0))
    draw_char(img, "A", ax, 970, t, "sad", 0.95, arms=(-15, -95 if t > v["start"] else 15), hold=None)
    if t < b1["start"]: paste_c(img, potli_img(False), ax + 230, 1120, 0.55, rot=6)
    if t < v["start"]: paste_c(img, pill("RAAT 1 BAJE…", 48, WHITE, INK), W / 2, 330, eob((t - b0["start"] - 0.2) / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, potli_img(True), 540, 760, eob(k / 0.3) * 1.1)
        paste_c(img, pill("AMMI KI BACHAT: Rs 400", 52, WHITE, GRN), W / 2, 330, eob((k - 0.2) / 0.3), rot=-3)
        paste_c(img, pill("+ 6 PARATHAY", 44, YEL), W / 2, 450, eob((k - 0.6) / 0.3), rot=3)

def sc_abbu_door(img, t, lt):
    img.alpha_composite(bg_room("eve"))
    d = ImageDraw.Draw(img); d.rectangle([110, 520, 520, 1250], fill=(255, 225, 160), outline=INK, width=8)
    b = LB("abbu_door")[0]; k = t - b["start"]
    draw_char(img, "B", 315, 950, t, "sad" if k < 0.8 else "n", 0.95, arms=(-15, -50 if k > 0.6 else 15))
    draw_char(img, "H", 780, 960, t, "sad" if k < 0.8 else "happy", 0.95, arms=(-20, 20), hold=hold_bag)
    paste_c(img, pill("ABBU KUCH NAHI BOLE…", 50, WHITE, INK), W / 2, 300, eob(k / 0.3))
    if k > 0.7: paste_c(img, pill("…BAS SAR PE HAATH RAKHA", 50, YEL), W / 2, 420, eob((k - 0.7) / 0.3), rot=-2)

def sc_bus(img, t, lt):
    img.alpha_composite(grad((10, 14, 40), (50, 40, 90)))
    d = ImageDraw.Draw(img)
    for k in range(30):
        r = np.random.default_rng(k + 90)
        x_ = r.uniform(0, W); y_ = r.uniform(80, 700); d.ellipse([x_, y_, x_ + 4, y_ + 4], fill=(230, 230, 255))
    d.ellipse([820, 180, 920, 280], fill=(250, 245, 210))
    d.rectangle([0, 1200, W, H], fill=(45, 45, 55)); d.rectangle([0, 1180, W, 1200], fill=(90, 90, 100))
    for k in range(8):   # road dashes + poles scroll by
        x = W - ((t * 700 + k * 300) % (W + 300)); d.rectangle([x, 1420, x + 140, 1436], fill=(240, 220, 120))
        px = W - ((t * 420 + k * 380) % (W + 400)); d.rectangle([px, 760, px + 14, 1180], fill=(80, 80, 95))
    b0, b1 = LB("bus"); bob = math.sin(t * 9) * 5
    hx = 540 + 25 * math.sin(t * 0.8)
    paste_c(img, bus_img(), hx, 1020 + bob, 1.0)
    paste_c(img, head("H", "down" if t < b1["start"] else "open", 0, "sad"), hx + 35, 885 + bob, 0.32)
    wheel(img, hx - 280, 1185 + bob * 0.3, t); wheel(img, hx + 270, 1185 + bob * 0.3, t)
    if t < LV("bus")[0]["start"] + 0.2:
        k = t - b0["start"]
        paste_c(img, pill("TICKET: -Rs 1,500", 56, RED, WHITE), W / 2, 330, eob(k / 0.3), rot=-3)
    if t > b1["start"] - 0.3:
        k = t - b1["start"] + 0.3; km = int(lerp(1200, 0, eio(k / 1.6)))
        sign = Image.new("RGBA", (420, 200), (0, 0, 0, 0)); sd = ImageDraw.Draw(sign)
        sd.rounded_rectangle([0, 0, 419, 199], radius=18, fill=(30, 120, 70), outline=WHITE, width=8)
        sd.text((210, 60), "KARACHI", font=fnt("Anton-Regular.ttf", 64), fill=WHITE, anchor="mm")
        sd.text((210, 145), f"{km} KM", font=fnt("Anton-Regular.ttf", 70), fill=YEL, anchor="mm")
        paste_c(img, sign, W / 2, 400, eob(k / 0.3))

def chai_stall(img, t):
    d = ImageDraw.Draw(img)
    d.rectangle([700, 960, 1040, 1250], fill=(150, 100, 60), outline=INK, width=6)
    d.rectangle([690, 900, 1050, 960], fill=(230, 60, 70), outline=INK, width=5)
    d.text((870, 930), "CHAI • Rs 30", font=fnt("Poppins-Black.ttf", 34), fill=WHITE, anchor="mm")
    paste_c(img, kettle_img(), 870, 1070, 0.45); steam(img, 870, 1010, t, 3, 0.6)

def sc_station(img, t, lt):
    img.alpha_composite(bg_station("night")); tube_glow(img); chai_stall(img, t)
    b0, b1 = LB("station"); v = LV("station")[0]
    hx = lerp(-150, 380, eo(lt / 1.4))
    sip = t > v["start"] + 1.2
    draw_char(img, "H", hx, 1000, t, "shock" if t < v["start"] + 0.5 else ("sad" if not sip else "n"), 0.9, arms=(-20, -60 if sip else 20), hold=hold_bag)
    if sip: paste_c(img, cup_img(), hx + 140, 1000, 0.9); steam(img, hx + 140, 960, t, 2, 0.4)
    paste_c(img, pill("RAAT 2 BAJE • KARACHI", 52, YEL), W / 2, 540, eob((lt - 0.4) / 0.3), rot=-3)
    if t > v["start"] + 1.4: paste_c(img, pill("-Rs 30", 60, RED, WHITE), 860, 760, eob((t - v["start"] - 1.4) / 0.3), rot=5)
    if t > b1["start"] + 0.2: paste_c(img, pill("BACHE: Rs 120", 56, WHITE, GRN), W / 2, 660, eob((t - b1["start"] - 0.2) / 0.3), rot=2)

def guard_char(img, x, y, t, sc=0.95, whistle=False, arm_up=False):
    draw_char(img, "X", x, y, t, "det", sc, arms=(-20, -120 if arm_up else 20))
    if whistle:
        d = ImageDraw.Draw(img); d.rounded_rectangle([x - 20 * sc, y - 10 * sc, x + 50 * sc, y + 15 * sc], radius=8, fill=(200, 200, 210), outline=INK, width=4)

def sc_guard(img, t, lt):
    img.alpha_composite(bg_station("night")); tube_glow(img)
    b0, b1 = LB("guard"); v = LV("guard")[0]
    up = t > word_t(v, "guard", v["start"] + 1.4)
    if not up:
        draw_char(img, "H", 420, 990, t, "sleep", 0.9, arms=(-40, 40), hold=hold_bag)
        zzz(img, 470, 760, t)
    else:
        draw_char(img, "H", 420, 990, t, "shock", 0.9, arms=(-20, 20), hold=hold_bag)
    gx = lerp(1350, 840, eo((t - b0["start"] - 0.1) / 1.0))
    guard_char(img, gx, 990, t, 0.95, whistle=t > v["start"], arm_up=up)
    if t > v["start"] and t < v["start"] + 1.4:
        paste_c(img, pill("PHREEET!", 56, WHITE, INK), gx - 120, 640, eob((t - v["start"]) / 0.2), rot=-8)
    if t > b1["start"] - 0.2:
        paste_c(img, bubble([("YAHAN SONA", INK), ("MANA HAI!", RED)], 52, tail="right"), 720, 470, eob((t - b1["start"] + 0.2) / 0.3))

def sc_floor(img, t, lt):
    img.alpha_composite(bg_station("night")); tube_glow(img)
    b0, b1 = LB("floor"); v = LV("floor")[0]
    d = ImageDraw.Draw(img); d.rectangle([60, 420, 140, 1260], fill=(170, 170, 180), outline=INK, width=5)
    opened = t > word_t(v, "potli", v["start"] + 1.6) + 0.2
    draw_char(img, "H", 330, 1080, t, "sad" if not opened else ("shock" if t < b1["start"] + 0.5 else "happy"), 0.9, arms=(-60, -40), hold=hold_bag)
    mosquitoes(img, t, 330, 800, 4 if not opened else 2)
    # a shady guy eyeing the bag
    sx = lerp(1250, 900, eo((t - b0["start"]) / 1.0)) if t < v["start"] + 1.2 else lerp(900, 1300, eo((t - v["start"] - 1.2) / 0.8))
    if sx < 1200:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); o = ImageDraw.Draw(ov)
        o.ellipse([sx - 90, 700, sx + 90, 880], fill=(20, 18, 30, 235)); o.rounded_rectangle([sx - 110, 850, sx + 110, 1260], radius=90, fill=(20, 18, 30, 235))
        o.ellipse([sx - 50, 770, sx - 20, 790], fill=(255, 240, 120, 255)); o.ellipse([sx + 10, 770, sx + 40, 790], fill=(255, 240, 120, 255))
        img.alpha_composite(ov)
        if t < v["start"] + 1.2: paste_c(img, pill("KOI BAG DEKH RAHA HAI…", 46, RED, WHITE), W / 2, 330, eob((t - b0["start"] - 0.3) / 0.3), rot=-3)
    if opened:
        k = t - word_t(v, "potli", v["start"] + 1.6) - 0.2
        paste_c(img, potli_img(True), 700, 1080, eob(k / 0.3) * 0.9)
    if t > b1["start"]:
        k = t - b1["start"]
        note = Image.new("RGBA", (560, 230), (0, 0, 0, 0)); nd = ImageDraw.Draw(note)
        nd.rounded_rectangle([0, 0, 559, 229], radius=14, fill=(250, 245, 225), outline=INK, width=6)
        nd.text((280, 80), "ROZ PHONE KARNA.", font=fnt("Anton-Regular.ttf", 58), fill=(40, 60, 170), anchor="mm")
        nd.text((280, 170), "— AMMI", font=fnt("Anton-Regular.ttf", 54), fill=RED, anchor="mm")
        paste_c(img, note, W / 2, 480, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("🥹", 110), 880, 760, eob((k - 0.5) / 0.3))

def sc_morning(img, t, lt):
    img.alpha_composite(bg_station("dawn"))
    bs = LB("morning"); b0, b1 = bs[0], bs[1]; v = LV("morning")[0]
    awake = t > v["start"]
    draw_char(img, "H", 330, 1060, t, "shock" if awake else "sleep", 0.9, arms=(-60, -40) if not awake else (-110, -150), hold=hold_bag if not awake else None)
    if not awake: zzz(img, 360, 820, t)
    clock(img, 800, 820, 8 + 40 / 60)
    if t < v["start"] + 0.3: paste_c(img, pill("SUBAH…", 50, WHITE, INK), 800, 980, eob((lt - 0.1) / 0.3))
    if awake:
        k = t - v["start"]; shake = math.sin(t * 50) * 4 if k < 0.8 else 0
        paste_c(img, glow_text("8:40!", "Anton-Regular.ttf", 160, YEL, (230, 60, 70)), 800 + shake, 1010, eob(k / 0.3))
    ol = next((l for l in LINES if l.get("outro")), None)
    if t > b1["start"] and not (ol and t > ol["start"] - 0.15):
        k = t - b1["start"]
        paste_c(img, pill("INTERVIEW: 9 AM", 50, WHITE, INK), W / 2, 260, eob(k / 0.25), rot=-3)
        paste_c(img, pill("ADDRESS: 25 KM DOOR", 50, YEL), W / 2, 370, eob((k - 0.25) / 0.25), rot=2)
        paste_c(img, pill("RICKSHAW: Rs 400", 50, RED, WHITE), W / 2, 480, eob((k - 0.5) / 0.25), rot=-2)
        paste_c(img, pill("JEB: Rs 120", 50, WHITE, GRN), W / 2, 590, eob((k - 0.75) / 0.25), rot=3)
    if len(bs) > 2 and t > bs[2]["start"]:
        k = t - bs[2]["start"]
        paste_c(img, glow_text("AB KYA?!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), 760, 1250, eob(k / 0.3), rot=-4)

# ======================= DAY 7+: RICKSHAW, GHAFOOR BIKE CENTER, MOTORBIKE RIDES, TRAFFIC, GALI, OFFICE, DELIVERY (reusable)
@lru_cache(None)
def bike_img(dent=False, box=False):
    """Rented 70cc motorbike, side view facing right. 620x380."""
    s = SS; im = Image.new("RGBA", (620 * s, 380 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda *xy: [v * s for v in xy]
    if box:   # delivery box on the carrier
        d.rounded_rectangle(P(15, 0, 165, 140), radius=12 * s, fill=(230, 60, 70), outline=INK, width=6 * s)
        d.text((90 * s, 50 * s), "TEZ", font=fnt("Anton-Regular.ttf", 50 * s), fill=WHITE, anchor="mm")
        d.text((90 * s, 102 * s), "DELIVERY", font=fnt("Poppins-Black.ttf", 20 * s), fill=YEL, anchor="mm")
    d.arc(P(40, 200, 220, 380), 180, 330, fill=(60, 60, 70), width=14 * s)                # rear mudguard
    d.line(P(90, 300, 330, 268), fill=(200, 200, 210), width=16 * s)                          # exhaust
    d.line(P(70, 306, 120, 300), fill=(120, 120, 130), width=20 * s)
    for cx in (130, 500):
        d.ellipse(P(cx - 82, 208, cx + 82, 372), fill=(30, 30, 36), outline=INK, width=6 * s)
        d.ellipse(P(cx - 54, 236, cx + 54, 344), fill=(170, 170, 180), outline=INK, width=4 * s)
        d.ellipse(P(cx - 16, 274, cx + 16, 306), fill=INK)
    d.line(P(130, 290, 280, 220), fill=(50, 50, 60), width=16 * s)                           # swing arm
    d.rounded_rectangle(P(230, 205, 370, 300), radius=22 * s, fill=(90, 90, 100), outline=INK, width=6 * s)  # engine
    for k in range(4): d.line(P(250 + k * 28, 220, 250 + k * 28, 285), fill=(60, 60, 70), width=5 * s)
    d.line(P(500, 290, 440, 110), fill=(160, 160, 170), width=18 * s)                        # front fork
    d.arc(P(410, 205, 590, 385), 200, 340, fill=(200, 40, 50), width=14 * s)                 # front mudguard
    d.polygon(P(230, 210, 260, 140, 410, 130, 430, 200, 360, 215), fill=(210, 40, 50), outline=INK)   # tank + side panel
    d.line(P(260, 140, 410, 130), fill=INK, width=5 * s)
    d.rounded_rectangle(P(275, 160, 345, 190), radius=8 * s, fill=WHITE, outline=INK, width=3 * s)
    d.text((310 * s, 175 * s), "70cc", font=fnt("Poppins-Black.ttf", 20 * s), fill=INK, anchor="mm")
    d.rounded_rectangle(P(100, 132, 300, 170), radius=18 * s, fill=(25, 25, 30), outline=INK, width=5 * s)   # seat
    d.ellipse(P(450, 120, 520, 190), fill=(255, 230, 120), outline=INK, width=6 * s)          # headlight
    d.line(P(400, 95, 470, 100), fill=INK, width=12 * s)                                     # handlebar
    d.rounded_rectangle(P(386, 86, 420, 108), radius=8 * s, fill=(40, 40, 45))
    d.line(P(445, 105, 440, 60), fill=(160, 160, 170), width=5 * s); d.ellipse(P(425, 40, 460, 70), fill=(200, 220, 240), outline=INK, width=4 * s)  # mirror
    d.rectangle(P(10, 200, 70, 240), fill=(250, 250, 240), outline=INK, width=4 * s)
    d.text((40 * s, 220 * s), "KHI 7", font=fnt("Poppins-Black.ttf", 16 * s), fill=INK, anchor="mm")
    if dent:
        d.chord(P(330, 120, 420, 190), 200, 340, fill=(120, 20, 30), outline=INK, width=4 * s)
        for a_, b_ in [((360, 140), (340, 175)), ((375, 140), (395, 178)), ((368, 140), (368, 182))]: d.line(P(*a_, *b_), fill=INK, width=4 * s)
        d.line(P(560, 250, 600, 225), fill=(200, 40, 50), width=12 * s)                       # bent mudguard
    return ssf(im)

def ride(img, x, y, t, mood="det", sc=1.0, tilt=0.0, dent=False, box=False, bounce=True, arms=(70, 38), helmet=False):
    """Hamid riding the bike; (x, y) = bike centre. tilt in degrees (counter-clockwise)."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bob = math.sin(t * 22) * 4 * sc if bounce else 0
    draw_char(lay, "H", x - 70 * sc, y - 310 * sc + bob, t, mood, 0.78 * sc, arms=arms)
    paste_c(lay, bike_img(dent, box), x, y + bob * 0.4, sc)
    if tilt: lay = lay.rotate(tilt, Image.BICUBIC, center=(x, y))
    img.alpha_composite(lay)

def speedlines(img, t, n=10, y0=300, y1=1350, col=(255, 255, 255)):
    d = ImageDraw.Draw(img)
    for k in range(n):
        r = np.random.default_rng(k + 300); y_ = r.uniform(y0, y1); ln = r.uniform(120, 300)
        x_ = W - ((t * 1900 + r.uniform(0, 2000)) % (W + 600))
        d.line([(x_, y_), (x_ + ln, y_)], fill=col + (170,), width=6)

def dust(img, x, y, t, n=3, sc=1.0):
    for k in range(n):
        q = (t * 1.6 + k / n) % 1
        paste_c(img, emoji("💨", 60), x - q * 160 * sc, y - q * 20, (0.6 + q) * sc, alpha=1 - q)

@lru_cache(None)
def rickshaw_img():
    s = SS; im = Image.new("RGBA", (560 * s, 460 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda *xy: [v * s for v in xy]
    d.rounded_rectangle(P(30, 30, 520, 120), radius=40 * s, fill=(250, 200, 40), outline=INK, width=7 * s)   # canopy
    for k in range(7): d.polygon(P(60 + k * 66, 110, 92 + k * 66, 110, 76 + k * 66, 140), fill=(230, 60, 70))
    d.line(P(80, 120, 80, 330), fill=INK, width=10 * s); d.line(P(480, 120, 470, 300), fill=INK, width=10 * s)
    d.polygon(P(40, 250, 520, 240, 540, 380, 30, 380), fill=(40, 160, 110), outline=INK)
    d.rounded_rectangle(P(240, 160, 470, 260), radius=20 * s, fill=(40, 50, 80), outline=INK, width=5 * s)   # back seat
    for k, c in enumerate([(230, 60, 70), (60, 110, 220), (250, 200, 40)]): d.rectangle(P(40, 300 + k * 18, 535, 312 + k * 18), fill=c)
    for cx in (110, 440):
        d.ellipse(P(cx - 60, 340, cx + 60, 455), fill=(30, 30, 36), outline=INK, width=6 * s); d.ellipse(P(cx - 20, 378, cx + 20, 418), fill=(170, 170, 180))
    # driver silhouette in front
    d.ellipse(P(100, 140, 190, 230), fill=(60, 40, 40), outline=INK, width=4 * s); d.rounded_rectangle(P(90, 220, 200, 300), radius=30 * s, fill=(90, 110, 90), outline=INK, width=4 * s)
    return ssf(im)

@lru_cache(None)
def bg_ghafoor(mode="day"):
    im = bg_street(mode).copy(); d = ImageDraw.Draw(im)
    dark = mode == "night"
    d.rectangle([60, 470, 1020, 1180], fill=(70, 55, 60) if not dark else (40, 32, 40), outline=INK, width=8)
    d.rectangle([90, 600, 990, 1180], fill=(120, 100, 90) if not dark else (70, 58, 60))
    d.rectangle([70, 480, 1010, 600], fill=(250, 200, 40) if not dark else (190, 150, 40), outline=INK, width=6)
    d.text((540, 520), "GHAFOOR BIKE CENTER", font=fnt("Anton-Regular.ttf", 60), fill=INK, anchor="mm")
    d.text((540, 575), "KIRAYE PAR BIKE • KAMRE BHI", font=fnt("Poppins-Black.ttf", 28), fill=(150, 40, 40), anchor="mm")
    for k in range(3):   # old tyres stacked
        d.ellipse([120, 1040 - k * 60, 260, 1100 - k * 60], fill=(35, 35, 40), outline=INK, width=5); d.ellipse([165, 1055 - k * 60, 215, 1085 - k * 60], fill=(120, 100, 90))
    d.rectangle([780, 640, 960, 700], fill=WHITE, outline=INK, width=4)
    d.text((870, 670), "Rs 100 / DIN", font=fnt("Poppins-Black.ttf", 28), fill=RED, anchor="mm")
    return im

@lru_cache(None)
def bg_road(mode="day"):
    im = bg_street(mode).copy(); d = ImageDraw.Draw(im)
    d.rectangle([0, 1180, W, H], fill=(70, 70, 78)); d.rectangle([0, 1170, W, 1190], fill=(170, 170, 160))
    return im

def car_img(col, kind=0):
    im = Image.new("RGBA", (420, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if kind == 0:
        d.rounded_rectangle([90, 20, 330, 110], radius=30, fill=col, outline=INK, width=6)
        d.rounded_rectangle([115, 35, 200, 100], radius=10, fill=(170, 210, 240), outline=INK, width=4); d.rounded_rectangle([215, 35, 305, 100], radius=10, fill=(170, 210, 240), outline=INK, width=4)
        d.rounded_rectangle([10, 90, 410, 180], radius=30, fill=col, outline=INK, width=6)
    else:   # mini truck / suzuki
        d.rounded_rectangle([250, 10, 400, 180], radius=20, fill=col, outline=INK, width=6); d.rectangle([270, 30, 380, 90], fill=(170, 210, 240), outline=INK, width=4)
        d.rectangle([10, 60, 255, 180], fill=mixc(col, (255, 255, 255), 0.3), outline=INK, width=6)
    for cx in (90, 330): d.ellipse([cx - 45, 140, cx + 45, 228], fill=(30, 30, 36), outline=INK, width=5); d.ellipse([cx - 15, 170, cx + 15, 200], fill=(170, 170, 180))
    return im

def timer_pill(t):
    """Delivery countdown: 30:00 at the start of 'delivery', stops at 01:12 at the door."""
    sd = next(x for x in SCENES if x["scene"] == "delivery")["vstart"]; dr = next(x for x in SCENES if x["scene"] == "door")
    stop = dr["vstart"] + 0.9
    q = eio((min(t, stop) - sd) / (stop - sd)); sec = int(1800 - q * (1800 - 72))
    col = GRN if t >= stop else (RED if sec < 600 else WHITE)
    return pill(f"⏱ {sec // 60:02d}:{sec % 60:02d}".replace("⏱ ", "TIMER "), 46, col, INK if col != RED else WHITE)

def sc_hook_bike(img, t, lt):
    img.alpha_composite(bg_road("day"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 14, 250, 1300, (255, 255, 255)); img.alpha_composite(lay)
    ride(img, 560, 1110, t, "shock", 1.0, tilt=-6 + 3 * math.sin(t * 9), arms=(100, 70))
    dust(img, 250, 1250, t, 3)
    paste_c(img, glow_text("KIRAYE KI BIKE…", "Anton-Regular.ttf", 112, WHITE, (90, 160, 255)), W / 2, 260, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("BRAKE HI NAHI!", "Anton-Regular.ttf", 124, YEL, (230, 60, 70)), W / 2, 400, eob((lt - 1.7) / 0.35) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
    if lt > 2.2: paste_c(img, emoji("😱", 120), 860, 640, eob((lt - 2.2) / 0.3))

def sc_rickshaw(img, t, lt):
    img.alpha_composite(bg_station("dawn"))
    b0, b1 = LB("rickshaw"); v = LV("rickshaw")[0]
    rx = 760 if t < b1["start"] + 0.2 else lerp(760, 1500, eo((t - b1["start"] - 0.2) / 1.0) ** 1.5)
    hx = lerp(-150, 330, eo((t - b0["start"]) / 0.9))
    draw_char(img, "H", hx, 1000, t, "shock" if t < v["start"] + 1.6 else "sad", 0.9, arms=(-20, -100) if t < v["start"] else (-20, 20), hold=hold_bag)
    paste_c(img, rickshaw_img(), rx, 1110, 0.95)
    if t > b1["start"] + 0.2: dust(img, rx - 260, 1260, t, 3)
    clock(img, 170, 560, 8 + 43 / 60); paste_c(img, pill("8:43 AM", 38, YEL), 170, 690, 1.0)
    if t > b0["start"] + 0.5 and t < b1["start"] + 0.3:
        paste_c(img, bubble([("Rs 400!", RED), ("KAM NAHI HOGA.", INK)], 46, tail="right"), 640, 640, eob((t - b0["start"] - 0.5) / 0.3))
    if t > v["start"] + 1.6: paste_c(img, pill("JEB: Rs 120", 54, WHITE, GRN), W / 2, 225, eob((t - v["start"] - 1.6) / 0.3), rot=-4)
    if t > b1["start"] + 0.4: paste_c(img, glow_text("AB KYA?!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), 640, 560, eob((t - b1["start"] - 0.4) / 0.3), rot=3)

def sc_ghafoor(img, t, lt):
    img.alpha_composite(bg_ghafoor("day"))
    b0, b1 = LB("ghafoor"); vg, vh = LV("ghafoor")
    paste_c(img, bike_img(), 560, 1220, 0.72)
    draw_char(img, "G", 820, 960, t, "n" if t < vg["end"] else "happy", 0.92, arms=(-20, -130) if (vg["start"] < t < vg["end"]) else (-20, 20))
    pay = b1["start"]
    hx = lerp(-150, 250, eo((t - b0["start"]) / 0.9))
    draw_char(img, "H", hx, 980, t, "sad" if t < vh["start"] else "det", 0.92, arms=(-20, 95 if abs(t - pay - 0.4) < 0.6 else 20), hold=hold_bag)
    if t < vg["start"] + 0.2: paste_c(img, pill("KARACHI KA JUGAAD?", 50, YEL), W / 2, 330, eob((t - b0["start"] - 0.3) / 0.3), rot=-3)
    if vg["start"] + 1.4 < t < pay + 0.2: paste_c(img, bubble([("BRAKE?", INK), ("NO GUARANTEE!", RED)], 44, tail="right"), 760, 330, eob((t - vg["start"] - 1.4) / 0.3))
    if t > pay:
        k = t - pay
        if k < 0.9: paste_c(img, notes_img(100, 180), lerp(400, 760, eo(k / 0.6)), 1060 - 70 * math.sin(min(1, k / 0.6) * math.pi), 0.8, rot=-8)
        paste_c(img, pill("KIRAYA: -Rs 100", 56, RED, WHITE), W / 2, 330, eob(k / 0.3), rot=-3)
        if k > 0.6: paste_c(img, pill("KICK! KICK! PHAT-PHAT!", 46, WHITE, INK), 560, 1000, eob((k - 0.6) / 0.25) * (1 + 0.05 * math.sin(t * 30)), rot=4)

def sc_traffic(img, t, lt):
    img.alpha_composite(bg_road("day"))
    b0, b1 = LB("traffic"); v = LV("traffic")[0]
    cars = [((230, 60, 70), 0, 160), ((60, 110, 220), 1, 560), ((250, 200, 40), 0, 950)]
    for j, (c, kd, cx) in enumerate(cars):
        paste_c(img, car_img(c, kd), cx + math.sin(t * 3 + j) * 3, 1090, 0.9)
    for j, (c, kd, cx) in enumerate(cars):
        paste_c(img, car_img(mixc(c, (40, 40, 60), 0.3), (kd + 1) % 2), cx + 180, 1280, 1.0)
    weave = t > b1["start"]
    bx = 300 if not weave else lerp(300, 1250, eio((t - b1["start"]) / 1.3))
    ride(img, bx, 1250, t, "shock" if not weave else "det", 0.62, bounce=weave, tilt=0 if not weave else -4)
    for j in range(3):
        if (t * 2.3 + j * 0.7) % 1 < 0.5: paste_c(img, pill(["PEEP!", "POM POM!", "HATO!"][j], 40, YEL), 220 + j * 330, 900 - (j % 2) * 60, 1.0, rot=(-6, 5, -3)[j])
    clock(img, 170, 330, 8 + 50 / 60); paste_c(img, pill("8:50!", 46, RED, WHITE), 170, 460, 1.0)
    paste_c(img, pill("TRAFFIC JAM", 60, RED, WHITE), 620, 330, eob((t - b0["start"] - 0.2) / 0.3), rot=-3)
    if weave: paste_c(img, pill("GALI SE SHORTCUT!", 54, YEL), 620, 470, eob((t - b1["start"]) / 0.3), rot=3)

def sc_gali(img, t, lt):
    img.alpha_composite(bg_street("day"))
    d = ImageDraw.Draw(img); d.rectangle([0, 1180, W, H], fill=(140, 120, 100))
    for k in range(3): d.line([(0, 380 + k * 34), (W, 330 + k * 40)], fill=INK, width=3)
    v = LV("gali")[0]; b0, b1 = LB("gali")
    stop = v["start"] + 1.4
    bx = lerp(-200, 330, eo((t - LINES[LINES.index(v)]["start"] + 0.3) / 1.1)) if t < b1["start"] else lerp(330, 1300, eio((t - b1["start"]) / 1.3))
    by = 1200
    bxx = 760 if t < b1["start"] else lerp(760, 960, eo((t - b1["start"]) / 0.6))
    paste_c(img, emoji("🐃", 380), bxx, 1080, 1.0, rot=0 if t < b0["start"] else 4 * math.sin(t * 6))
    squeeze = t > b1["start"]
    ride(img, bx, by, t, "shock" if t > stop and not squeeze else ("happy" if squeeze else "det"), 0.62, tilt=0 if not squeeze else 6 * math.sin(t * 8))
    if t > stop - 0.3 and t < b1["start"] + 0.2:
        paste_c(img, glow_text("BHAINS!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 300, eob((t - stop + 0.3) / 0.3), rot=-4)
    if t > b0["start"] + 0.3 and t < b1["start"]:
        paste_c(img, pill("MOOOO…", 50, WHITE, INK), 820, 800, eob((t - b0["start"] - 0.3) / 0.3), rot=5)
        paste_c(img, pill("8:54!", 46, RED, WHITE), 200, 450, 1.0)
    if squeeze:
        paste_c(img, pill("SORRY BHAINS JI!", 56, YEL), W / 2, 330, eob((t - b1["start"]) / 0.3), rot=-3)
        paste_c(img, emoji("😂", 100), 900, 520, eob((t - b1["start"] - 0.4) / 0.3))

def sc_downhill(img, t, lt):
    b0, b1 = LB("downhill"); v = LV("downhill")[0]
    span = next(x for x in SCENES if x["scene"] == "downhill")
    fail = t > word_t(v, "kuch", v["start"] + 2.2) - 0.1
    sp = 1.0 if not fail else 1.0 + 1.2 * eo((t - word_t(v, "kuch", v["start"] + 2.2)) / 1.0)
    bg = bg_road("day").rotate(-9, Image.BICUBIC, center=(W / 2, H / 2)).resize((int(W * 1.25), int(H * 1.25)), Image.BILINEAR)
    img.alpha_composite(bg.crop((int(W * 0.125), int(H * 0.125), int(W * 0.125) + W, int(H * 0.125) + H)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t * sp, int(8 + 10 * (sp - 1)), 200, 1350); img.alpha_composite(lay)
    shake = math.sin(t * 50) * 8 * (sp - 1)
    ride(img, 520 + shake, 1150, t, "shock" if fail else "det", 0.95, tilt=-9 + shake * 0.3, arms=(100, 60) if fail else (70, 38))
    dust(img, 200, 1300, t * sp, 3)
    if t < v["start"] + 0.3: paste_c(img, pill("DHALWAAN ↓".replace("↓", "AAGE"), 54, YEL), W / 2, 330, eob((t - b0["start"] - 0.2) / 0.3), rot=-4)
    # brake lever close-up inset
    if t > word_t(v, "brake", v["start"] + 1.0) - 0.2:
        k = t - word_t(v, "brake", v["start"] + 1.0) + 0.2
        ins = Image.new("RGBA", (320, 320), (0, 0, 0, 0)); o = ImageDraw.Draw(ins)
        o.ellipse([0, 0, 319, 319], fill=(250, 245, 230), outline=INK, width=8)
        o.line([(40, 150), (280, 140)], fill=INK, width=24); o.line([(120, 175), (270, 215 - 30 * eio(k / 0.4))], fill=(160, 160, 170), width=16)
        o.ellipse([170, 150, 290, 260], fill=SKIN["H"], outline=INK, width=6)
        o.text((160, 75), "BRAKE", font=fnt("Anton-Regular.ttf", 56), fill=RED, anchor="mm")
        paste_c(img, ins, 860, 640, eob(k / 0.25) * 0.9)
        if fail: paste_c(img, emoji("❌", 120), 860, 640, eob((t - word_t(v, "kuch", v["start"] + 2.2)) / 0.25))
    if fail:
        k = t - word_t(v, "kuch", v["start"] + 2.2)
        paste_c(img, glow_text("BRAKE FAIL!", "Anton-Regular.ttf", 140, WHITE, (230, 60, 70)), W / 2 + shake, 330, eob(k / 0.3), rot=-5)
        if t > b1["start"] + 0.3: paste_c(img, pill("SPEED: 60… 70… 80!", 50, YEL), 380, 520, eob((t - b1["start"] - 0.3) / 0.3), rot=3)

@lru_cache(None)
def bg_office():
    im = bg_road("day").copy(); d = ImageDraw.Draw(im)
    d.rectangle([60, 300, 1020, 1180], fill=(225, 225, 230), outline=INK, width=8)
    for r_ in range(3):
        for c_ in range(4): d.rectangle([110 + c_ * 230, 560 + r_ * 150, 260 + c_ * 230, 660 + r_ * 150], fill=(150, 200, 235), outline=INK, width=5)
    d.rectangle([60, 300, 1020, 470], fill=(230, 60, 70), outline=INK, width=8)
    d.text((540, 365), "TEZ DELIVERY", font=fnt("Anton-Regular.ttf", 92), fill=WHITE, anchor="mm")
    d.text((540, 440), "HEAD OFFICE • KARACHI", font=fnt("Poppins-Black.ttf", 30), fill=YEL, anchor="mm")
    d.rectangle([380, 900, 700, 1180], fill=(90, 70, 60), outline=INK, width=6)   # gate
    for k in range(6): d.line([(400 + k * 55, 900), (400 + k * 55, 1180)], fill=INK, width=5)
    return im

def box_stack(img, t, hit=None):
    cols = [(200, 150, 90), (180, 130, 80), (215, 165, 100)]
    pos = [(780, 1130), (900, 1130), (840, 1030), (780, 930), (900, 930)]
    for j, (x, y) in enumerate(pos):
        if hit is not None and t > hit:
            k = t - hit; r = np.random.default_rng(j + 70); vx = r.uniform(-500, 600); vy = r.uniform(-900, -400)
            x, y = x + vx * k, min(1250, y + vy * k + 1600 * k * k); ang = (j * 40 + 300 * k) * (1 if j % 2 else -1)
        else: ang = 0
        b = Image.new("RGBA", (130, 110), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rectangle([2, 2, 127, 107], fill=cols[j % 3], outline=INK, width=5); bd.line([(65, 2), (65, 40)], fill=(240, 220, 160), width=12)
        paste_c(img, b, x, y, 1.0, rot=ang)

def sc_crash(img, t, lt):
    img.alpha_composite(bg_office())
    b0, b1 = LB("crash"); v = LV("crash")[0]
    hit = b0["start"] + 0.75
    if t < hit:
        bx = lerp(-300, 700, eio((t - b0["start"] + 0.1) / 0.85)); ride(img, bx, 1180, t, "shock", 0.8, tilt=-4, arms=(100, 60)); dust(img, bx - 220, 1300, t, 3)
        box_stack(img, t)
    else:
        k = t - hit
        box_stack(img, t, hit)
        paste_c(img, bike_img(True), 700, 1240, 0.7, rot=-14)
        draw_char(img, "H", 560, 1010, t, "shock" if t < v["start"] + 1.6 else "happy", 0.85, arms=(-150, 150) if k < 0.6 else (-20, -120))
        if k < 1.4: paste_c(img, glow_text("DHADAAM!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 620, eob(k / 0.2), rot=-6)
        if k < 0.25: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(170 * (1 - k / 0.25)))))
        if k > 0.3: paste_c(img, emoji("💫", 90), 560, 760, 1.0, rot=t * 200)
    if t > v["start"] + 1.4:
        k = t - v["start"] - 1.4
        clock(img, 180, 620, 9.0); paste_c(img, pill("9:00 AM!", 50, GRN, WHITE), 180, 750, eob(k / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]; mx = lerp(1300, 880, eo(k / 0.8))
        draw_char(img, "M", mx, 990, t, "shock", 0.9, arms=(-20, -60))

def clipboard(img, x, y, sc):
    c = Image.new("RGBA", (170, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 10, 169, 219], radius=10, fill=(150, 100, 60), outline=INK, width=5); d.rectangle([18, 30, 151, 205], fill=WHITE, outline=INK, width=3)
    d.rounded_rectangle([55, 0, 115, 26], radius=6, fill=(160, 160, 170), outline=INK, width=3)
    for k in range(5): d.line([(30, 60 + k * 28), (140, 60 + k * 28)], fill=(170, 170, 180), width=4)
    paste_c(img, c, x - 140 * sc, y + 200 * sc, sc * 0.9, rot=8)

def sc_manager(img, t, lt):
    img.alpha_composite(bg_office())
    vh, vo = LV("manager"); b = LB("manager")[0]
    paste_c(img, bike_img(True), 830, 1260, 0.55, rot=-8)
    draw_char(img, "M", 790, 960, t, "shock" if t < b["start"] else "happy", 0.95, arms=(-20, 20), hold=clipboard, laugh=b["start"] < t < b["start"] + 1.0)
    draw_char(img, "H", 300, 980, t, "sad" if t < b["start"] else "det", 0.95, arms=(-20, -150) if t < vh["end"] else (-20, 20))
    # cardboard box stuck on Hamid's head (funny)
    if t < b["start"] + 0.4:
        bx = Image.new("RGBA", (170, 120), (0, 0, 0, 0)); bd = ImageDraw.Draw(bx); bd.rectangle([2, 2, 167, 117], fill=(200, 150, 90), outline=INK, width=5)
        paste_c(img, bx, 300, 760, 1.0, rot=-12)
    if t < vh["start"] + 0.1: paste_c(img, bubble([("YEH KYA", INK), ("ENTRY THI?!", RED)], 50, tail="right"), 760, 400, eob((lt - 0.1) / 0.3))
    if t > b["start"]:
        k = t - b["start"]
        if t < vo["start"] + 0.2:
            paste_c(img, bubble([("HAHA! BIKE TOH", INK), ("CHALA LETE HO.", INK), ("TEST DO!", GRN)], 46, tail="right"), 720, 420, eob(k / 0.3))
    if t > vo["start"]:
        k = t - vo["start"]
        paste_c(img, pill("PEHLA ORDER: 30 MINUTE", 54, YEL), W / 2, 560, eob(k / 0.3), rot=-3)
        if t > word_t(vo, "baghair", vo["start"] + 2.4) - 0.1: paste_c(img, pill("BINA BRAKE KE!", 54, RED, WHITE), W / 2, 680, eob((t - word_t(vo, "baghair", vo["start"] + 2.4) + 0.1) / 0.3), rot=3)

def sparks(img, x, y, t, n=6):
    d = ImageDraw.Draw(img)
    for k in range(n):
        q = (t * 3 + k / n) % 1; a = math.pi + 0.4 + k * 0.25
        x0, y0 = x + math.cos(a) * q * 150, y + math.sin(a) * q * 70 - 10
        d.line([(x0, y0), (x0 + 22, y0 + 6)], fill=(255, 200 - int(120 * q), 40), width=6)

def sc_delivery(img, t, lt):
    img.alpha_composite(bg_road("day"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 10, 300, 1300); img.alpha_composite(lay)
    b0, b1 = LB("delivery"); va = LV("delivery")[0]
    ride(img, 520, 1200, t, "det", 0.95, box=True, tilt=-3 * math.sin(t * 3))
    sparks(img, 470, 1360, t)   # foot dragging on the road = brake
    paste_c(img, timer_pill(t), W / 2, 300, 1.0)
    if t < va["start"]: paste_c(img, pill("CHAPPAL = BRAKE", 52, YEL), W / 2, 420, eob((t - b0["start"] - 0.3) / 0.3), rot=-3)
    if t > va["start"] - 0.2:
        k = t - va["start"] + 0.2
        vn = Image.new("RGBA", (560, 150), (0, 0, 0, 0)); o = ImageDraw.Draw(vn)
        o.rounded_rectangle([0, 0, 559, 149], radius=40, fill=(225, 250, 215), outline=INK, width=6)
        o.ellipse([20, 25, 120, 125], fill=(230, 90, 140), outline=INK, width=4); o.text((70, 75), "A", font=fnt("Anton-Regular.ttf", 60), fill=WHITE, anchor="mm")
        for j in range(14): hh = 12 + 40 * abs(math.sin(j * 1.7 + (t * 6 if t < va["end"] else 0))); o.rounded_rectangle([150 + j * 24, 75 - hh / 2, 162 + j * 24, 75 + hh / 2], radius=5, fill=(40, 140, 90))
        o.text((520, 120), "0:04", font=fnt("Poppins-Black.ttf", 24), fill=INK, anchor="rm")
        paste_c(img, vn, W / 2, 540, eob(k / 0.3))
        paste_c(img, pill("AMMI KA VOICE NOTE", 40, (230, 90, 140), WHITE), W / 2, 430, eob(k / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, glow_text("ABHI NAHI AMMI!", "Anton-Regular.ttf", 110, YEL, (230, 90, 140)), W / 2, 760, eob(k / 0.3), rot=-4)
        paste_c(img, emoji("😅", 100), 880, 900, eob((k - 0.3) / 0.3))

def sc_stairs(img, t, lt):
    img.alpha_composite(grad((235, 225, 205), (200, 185, 165)))
    d = ImageDraw.Draw(img)
    for k in range(9):   # diagonal stairs
        x0 = 60 + k * 110; y0 = 1360 - k * 90
        d.polygon([(x0, y0), (x0 + 110, y0), (x0 + 110, H), (x0, H)], fill=(170, 160, 150), outline=INK)
        d.line([(x0, y0), (x0 + 110, y0)], fill=INK, width=6)
    d.line([(60, 1200), (1050, 390)], fill=(120, 80, 50), width=12)
    b0, b1 = LB("stairs")
    q = eio((t - b0["start"]) / (b1["end"] - b0["start"]))
    hx = lerp(150, 900, q); hy = lerp(1040, 390, q) - abs(math.sin(t * 14)) * 30
    draw_char(img, "H", hx, hy, t, "det", 0.7, arms=(-150, 120), hold=None)
    paste_c(img, bag_img(), hx + 110, hy + 170, 0.5)
    d = ImageDraw.Draw(img); d.rectangle([700, 1100, 1010, 1250], fill=WHITE, outline=INK, width=6)
    d.text((855, 1145), "LIFT", font=fnt("Anton-Regular.ttf", 52), fill=INK, anchor="mm"); d.text((855, 1210), "KHARAB HAI", font=fnt("Poppins-Black.ttf", 32), fill=RED, anchor="mm")
    fl = 1 + int(q * 4.99)
    paste_c(img, pill(f"FLOOR {fl} / 5", 50, YEL), 260, 420, 1.0, rot=-3)
    paste_c(img, timer_pill(t), W / 2, 300, 1.0)
    if t > b1["start"] + 0.5: paste_c(img, emoji("🥵", 100), hx - 140, hy - 160, eob((t - b1["start"] - 0.5) / 0.3))

def review_card(stars_k):
    c = Image.new("RGBA", (640, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 639, 419], radius=40, fill=WHITE, outline=INK, width=7)
    d.rectangle([7, 7, 632, 90], fill=(230, 60, 70)); d.text((320, 50), "TEZ DELIVERY • RATING", font=fnt("Poppins-Black.ttf", 32), fill=WHITE, anchor="mm")
    for j in range(5):
        cx, cy = 110 + j * 105, 170; on = stars_k > j
        pts = [(cx + math.cos(math.pi / 2 + m * math.pi / 5) * (44 if m % 2 == 0 else 19), cy - math.sin(math.pi / 2 + m * math.pi / 5) * (44 if m % 2 == 0 else 19)) for m in range(10)]
        d.polygon(pts, fill=(255, 200, 40) if on else (220, 220, 225), outline=INK)
    d.text((320, 270), '"Bohat tez! Shukriya beta."', font=fnt("Poppins-Black.ttf", 30), fill=INK, anchor="mm")
    d.text((320, 350), "TIP: + Rs 50", font=fnt("Anton-Regular.ttf", 58), fill=GRN, anchor="mm")
    return c

def sc_door(img, t, lt):
    img.alpha_composite(grad((235, 225, 205), (200, 185, 165)))
    d = ImageDraw.Draw(img); d.rectangle([0, 1250, W, H], fill=(170, 160, 150))
    b0, b1 = LB("door"); v = LV("door")[0]
    d.rectangle([600, 360, 960, 1250], fill=(130, 85, 60), outline=INK, width=8)
    op = eo((t - b0["start"] - 0.1) / 0.4)
    d.rectangle([600, 360, 600 + 360 * (1 - 0.7 * op), 1250], fill=(150, 100, 70), outline=INK, width=6)
    d.rectangle([640, 300, 920, 350], fill=WHITE, outline=INK, width=4); d.text((780, 325), "FLAT 5-B", font=fnt("Poppins-Black.ttf", 28), fill=INK, anchor="mm")
    hand_k = eo((t - b0["start"] - 0.4) / 0.4)
    draw_char(img, "H", 300, 1010, t, "det" if t < v["start"] else "happy", 0.95, arms=(-20, 90 if t < b0["start"] + 1.2 else 20))
    if t < b0["start"] + 1.2:
        paste_c(img, bag_img(), lerp(520, 640, max(0, (t - b0["start"] - 0.8) / 0.4)), 1080, 0.55)
    if op > 0.3:   # aunty's hand from the door
        d = ImageDraw.Draw(img); hx = lerp(700, 560, hand_k)
        d.rounded_rectangle([hx, 1040, 720, 1090], radius=24, fill=(150, 40, 70), outline=INK, width=5); d.ellipse([hx - 30, 1035, hx + 30, 1095], fill=SKIN["A"], outline=INK, width=5)
    paste_c(img, timer_pill(t), W / 2, 230, 1.0)
    if t > b0["start"] + 0.9: paste_c(img, pill("DELIVERED ✓".replace(" ✓", "!"), 50, GRN, WHITE), W / 2, 340, eob((t - b0["start"] - 0.9) / 0.3), rot=3)
    if t > v["start"] - 0.2:
        k = t - v["start"] + 0.2
        paste_c(img, review_card(int(k / 0.22) + 1 if k > 0 else 0), W / 2, 590, eob(k / 0.3) * 0.95, rot=-2)
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, glow_text("NAUKRI PAKKI!", "Anton-Regular.ttf", 120, WHITE, (40, 190, 110)), W / 2, 1230, eob(k / 0.3), rot=-3)
        for j in range(12):
            r = np.random.default_rng(j); x = r.uniform(80, 1000); y = 250 + ((k * r.uniform(250, 420) + r.uniform(0, 500)) % 900)
            ImageDraw.Draw(img).rectangle([x, y, x + 14, y + 22], fill=[(255, 200, 40), (230, 60, 70), (60, 150, 255), (40, 190, 110)][j % 4])

def sc_dent(img, t, lt):
    img.alpha_composite(bg_ghafoor("night")); bulb_glow(img, 60)
    b0, b1 = LB("dent"); v = LV("dent")[0]
    ol = next((l for l in LINES if l.get("outro")), None); pre = not (ol and t > ol["start"] - 0.15)
    look = t < v["start"]
    gx = lerp(1250, 870, eo((t - b0["start"]) / 0.8))
    draw_char(img, "G", gx, 940, t, "shock" if look else "det", 0.92, arms=(-20, 20) if look else (-100, 20))
    draw_char(img, "H", 210, 960, t, "n" if look else "shock", 0.9, arms=(-20, 20))
    paste_c(img, bike_img(True), 560, 1240, 0.85)
    if look and t > b0["start"] + 0.5:
        g_ = Image.new("RGBA", (200, 260), (0, 0, 0, 0)); o = ImageDraw.Draw(g_)
        o.ellipse([10, 10, 170, 170], fill=(200, 230, 255, 120), outline=INK, width=10); o.line([(140, 150), (190, 250)], fill=(120, 80, 50), width=22)
        paste_c(img, g_, 620, 1120, eob((t - b0["start"] - 0.5) / 0.3))
    if t > v["start"] + 0.5 and pre: paste_c(img, pill("DENT!", 60, RED, WHITE), 470, 1070, eob((t - v["start"] - 0.5) / 0.3), rot=8)
    if t > b1["start"] and pre:
        k = t - b1["start"]
        paste_c(img, pill("JURMANA: Rs 500", 60, RED, WHITE), W / 2, 300, eob(k / 0.3), rot=-3)
        paste_c(img, pill("JEB: Rs 70", 60, WHITE, GRN), W / 2, 430, eob((k - 0.4) / 0.3), rot=3)
        paste_c(img, emoji("😰", 110), 380, 700, eob((k - 0.7) / 0.3))

# ======================= DAY 8+: RAIN, FLOODED ROAD, CAKE ORDER, MASTER SALEEM'S HOME (reusable)
def rain(img, t, n=70, dark=90, col=(200, 220, 255)):
    if dark: img.alpha_composite(Image.new("RGBA", (W, H), (20, 30, 60, dark)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for k in range(n):
        r = np.random.default_rng(k + 900); x0 = r.uniform(-200, W + 100); sp = r.uniform(1800, 2600); ln = r.uniform(50, 110)
        y = (r.uniform(0, H) + t * sp) % (H + 200) - 100; x = x0 + (y / H) * 160
        d.line([(x, y), (x + ln * 0.3, y + ln)], fill=col + (170,), width=4)
    img.alpha_composite(lay)

def clouds(img, t, k=1.0, y=230):
    d = ImageDraw.Draw(img)
    for j in range(5):
        cx = (j * 260 + t * 25) % (W + 400) - 200; c = (70, 75, 95) if j % 2 else (90, 95, 115)
        for dx, dy, rr in ((0, 0, 110), (110, -30, 90), (-110, -10, 80), (60, 40, 90)):
            d.ellipse([cx + dx - rr, y + dy - rr * k, cx + dx + rr, y + dy + rr * k], fill=c)

def drips(img, x, y, t, n=5):
    d = ImageDraw.Draw(img)
    for k in range(n):
        q = (t * 1.8 + k / n) % 1; dx = (k - n / 2) * 40
        d.ellipse([x + dx - 9, y + q * 160 - 14, x + dx + 9, y + q * 160 + 14], fill=(150, 200, 255, int(255 * (1 - q))), outline=INK, width=3)

def water(img, t, top=1150, col=(90, 120, 150)):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    pts = [(x, top + 14 * math.sin(x / 70 + t * 4)) for x in range(0, W + 20, 20)]
    d.polygon(pts + [(W, H), (0, H)], fill=col + (225,))
    for k in range(8):
        r = np.random.default_rng(k + 50); x = (r.uniform(0, W) + t * 60) % W; yy = r.uniform(top + 60, H - 100)
        d.arc([x - 60, yy - 10, x + 60, yy + 10], 200, 340, fill=(200, 225, 245, 200), width=5)
    img.alpha_composite(lay)

@lru_cache(None)
def cake_img(ruined=False):
    s = SS; im = Image.new("RGBA", (420 * s, 360 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); P = lambda *xy: [v * s for v in xy]
    d.polygon(P(10, 150, 410, 150, 380, 350, 40, 350), fill=(210, 160, 100), outline=INK)   # open box
    d.line(P(10, 150, 410, 150), fill=INK, width=6 * s)
    if not ruined:
        d.rounded_rectangle(P(80, 120, 340, 300), radius=30 * s, fill=(255, 180, 200), outline=INK, width=6 * s)
        d.rounded_rectangle(P(80, 120, 340, 170), radius=24 * s, fill=(255, 245, 250), outline=INK, width=5 * s)
        d.text((210 * s, 235 * s), "HAPPY B'DAY", font=fnt("Poppins-Black.ttf", 34 * s), fill=(200, 40, 90), anchor="mm")
    else:   # melted, slumped cake
        d.polygon(P(60, 300, 90, 210, 160, 240, 230, 190, 300, 250, 360, 230, 370, 300), fill=(255, 180, 200), outline=INK)
        for x_ in (110, 200, 290): d.rounded_rectangle(P(x_, 270, x_ + 22, 340), radius=10 * s, fill=(255, 180, 200))
        d.text((210 * s, 270 * s), "HAP. . Y B'..Y", font=fnt("Poppins-Black.ttf", 28 * s), fill=(200, 40, 90), anchor="mm")
        for k in range(6): d.ellipse(P(60 + k * 55, 160 + (k % 2) * 20, 80 + k * 55, 185 + (k % 2) * 20), fill=(150, 200, 255), outline=INK, width=3 * s)
    return ssf(im)

def order_card(t0, t):
    c = Image.new("RGBA", (620, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 619, 559], radius=40, fill=(25, 25, 32), outline=INK, width=8)
    d.rounded_rectangle([24, 24, 595, 535], radius=24, fill=WHITE)
    d.rectangle([24, 24, 595, 110], fill=(230, 60, 70)); d.text((310, 67), "NEW ORDER!", font=fnt("Anton-Regular.ttf", 54), fill=WHITE, anchor="mm")
    rows = [("BIRTHDAY CAKE • 3 KG", INK), ("DOOR: FLAT 2-A, PECHS", (90, 90, 100)), ("TIME: 25 MINUTE", RED), ('"DHYAAN SE! NAAZUK HAI"', (40, 90, 200))]
    for j, (tx, col) in enumerate(rows):
        if t > t0 + 0.25 * j: d.text((310, 170 + j * 85), tx, font=fnt("Poppins-Black.ttf", 36), fill=col, anchor="mm")
    return c

def sc_hook_rain(img, t, lt):
    img.alpha_composite(bg_road("day")); clouds(img, t, 1.0, 200)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 8, 300, 1250); img.alpha_composite(lay)
    water(img, t, 1300)
    ride(img, 540, 1150, t, "shock", 1.0, box=True, tilt=-4 + 3 * math.sin(t * 7), arms=(100, 70))
    drips(img, 470, 760, t, 4)
    rain(img, t, 80, 70)
    if (lt % 2.3) < 0.08: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 140)))
    paste_c(img, glow_text("BARISH MEIN CAKE…", "Anton-Regular.ttf", 104, WHITE, (90, 160, 255)), W / 2, 330, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("DABBA GEELA!", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 470, eob((lt - 1.8) / 0.35) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
    if lt > 2.3: paste_c(img, emoji("🎂", 110), 870, 700, eob((lt - 2.3) / 0.3), rot=-12)

def sc_deal(img, t, lt):
    img.alpha_composite(bg_ghafoor("day"))
    b0, b1 = LB("deal"); vg, vh = LV("deal")
    paste_c(img, bike_img(True), 560, 1230, 0.72)
    draw_char(img, "G", 820, 960, t, "det" if t < vh["start"] else "happy", 0.92, arms=(-20, -120) if vg["start"] < t < vg["end"] else (-20, 20))
    draw_char(img, "H", 250, 980, t, "sad" if t < vh["start"] else "det", 0.92, arms=(-20, 20) if t < b1["start"] else (-20, 100))
    if t < vg["start"] + 0.1: paste_c(img, bubble([("DENT KA", INK), ("Rs 500 KAB?", RED)], 46, tail="right"), 760, 380, eob((lt - 0.2) / 0.3))
    if vg["start"] + 0.4 < t: paste_c(img, pill("QIST: Rs 50 ROZ", 56, YEL), W / 2, 330, eob((t - vg["start"] - 0.4) / 0.3), rot=-3)
    if vg["start"] + 1.4 < t: paste_c(img, pill("+ KIRAYA Rs 100", 50, RED, WHITE), W / 2, 450, eob((t - vg["start"] - 1.4) / 0.3), rot=3)
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, emoji("🤝", 150), 540, 760, eob(k / 0.3))
        paste_c(img, pill("DEAL PAKKI!", 54, GRN, WHITE), 540, 600, eob((k - 0.3) / 0.3), rot=-4)

def sc_order(img, t, lt):
    img.alpha_composite(bg_office())
    b0, v, b1 = L("order")
    sky = eio((t - b1["start"]) / 1.0)
    if sky > 0:
        img.alpha_composite(Image.new("RGBA", (W, H), (30, 35, 60, int(110 * sky)))); clouds(img, t, sky, 150)
    paste_c(img, bike_img(True, True), 760, 1240, 0.62)
    draw_char(img, "H", 300, 990, t, "shock" if t < v["start"] else "happy", 0.9, arms=(-20, 110) if t < b1["start"] else (-20, 20), hold=hold_phone)
    if t < b1["start"]: paste_c(img, order_card(b0["start"] + 0.2, t), 640, 650, eob((t - b0["start"] - 0.1) / 0.3) * 0.95, rot=3)
    if t > word_t(v, "saalgirah", v["start"] + 1.2) - 0.1 and t < b1["start"]: paste_c(img, emoji("🎂", 130), 900, 380, eob((t - word_t(v, "saalgirah", v["start"] + 1.2) + 0.1) / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, pill("MAUSAM: BARISH 90%", 52, (60, 110, 220), WHITE), W / 2, 450, eob((k - 0.3) / 0.3), rot=-3)
        paste_c(img, emoji("⛈️", 140), 820, 620, eob((k - 0.6) / 0.3))
        paste_c(img, emoji("😬", 100), 420, 720, eob((k - 0.8) / 0.3))

def sc_rain(img, t, lt):
    img.alpha_composite(bg_road("day")); clouds(img, t, 1.0, 180)
    b0, v, b1 = L("rain")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 8, 300, 1250); img.alpha_composite(lay)
    ride(img, 540, 1160, t, "shock" if t < b1["start"] else "det", 0.95, box=True, tilt=-3 * math.sin(t * 3), arms=(70, 38) if t < b1["start"] else (60, 150))
    heavy = eo((t - b0["start"] - 0.3) / 1.0)
    rain(img, t, int(20 + 80 * heavy), int(40 + 60 * heavy))
    fl = t - b0["start"] - 0.5
    if 0 < fl < 0.25: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - fl / 0.25)))))
    if fl > 0 and t < v["start"] + 0.2: paste_c(img, glow_text("KADAK!", "Anton-Regular.ttf", 140, YEL, (90, 160, 255)), W / 2, 380, eob(fl / 0.2), rot=-6)
    if t > word_t(v, "barish", v["start"] + 1.4) - 0.1: paste_c(img, glow_text("KARACHI KI BARISH!", "Anton-Regular.ttf", 100, WHITE, (60, 110, 220)), W / 2, 330, eob((t - word_t(v, "barish", v["start"] + 1.4) + 0.1) / 0.3), rot=-3)
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, pill("SHIRT SE DABBA DHAKO!", 50, YEL), W / 2, 500, eob(k / 0.3), rot=3)
        drips(img, 470, 760, t, 4)

def sc_flood(img, t, lt):
    img.alpha_composite(bg_road("day")); clouds(img, t, 1.0, 180)
    v, b0, b1 = L("flood")
    rise = eo((t - v["start"]) / 1.2)
    walk = 0 if t < b1["start"] else eio((t - b1["start"]) / 1.4)
    hx = lerp(380, 640, walk)
    draw_char(img, "H", hx - 170, 980 + 10 * math.sin(t * 5), t, "shock" if t < b0["start"] else ("sad" if t < b1["start"] else "det"), 0.9, arms=(-20, 70), hold=None)
    paste_c(img, bike_img(False, True), hx + 160, 1230 + 6 * math.sin(t * 3), 0.7)
    water(img, t, int(lerp(1330, 1150, rise)))
    rain(img, t, 80, 70)
    if t > word_t(v, "engine", v["start"] + 1.4) - 0.1 and t < b0["start"] + 0.2:
        paste_c(img, pill("ENGINE BAND!", 62, RED, WHITE), W / 2, 330, eob((t - word_t(v, "engine", v["start"] + 1.4) + 0.1) / 0.3), rot=-4)
        paste_c(img, pill("PHUT… PHUT… PHUSS", 42, WHITE, INK), 760, 860, eob((t - word_t(v, "engine", v["start"] + 1.4)) / 0.3), rot=5)
    if b0["start"] < t:   # chappal floats away (funny)
        k = t - b0["start"]
        paste_c(img, emoji("🩴", 110), lerp(hx - 120, 1250, eio(k / 2.4)), 1170 + 12 * math.sin(t * 6), 1.0, rot=20 * math.sin(t * 4))
        if t < b1["start"]:
            paste_c(img, glow_text("CHAPPAL BEH GAYI!", "Anton-Regular.ttf", 104, YEL, (230, 60, 70)), W / 2, 340, eob(k / 0.3), rot=-3)
            paste_c(img, emoji("😭", 100), 820, 560, eob((k - 0.3) / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, pill("2 KM PAIDAL… DHAKKA!", 52, YEL), W / 2, 340, eob(k / 0.3), rot=3)
        paste_c(img, pill("TIMER 06:40", 46, RED, WHITE), W / 2, 460, eob((k - 0.3) / 0.3))

def sc_vnote(img, t, lt):
    img.alpha_composite(bg_road("day")); clouds(img, t, 1.0, 180)
    va, b = L("vnote")
    draw_char(img, "H", 420, 980 + 10 * math.sin(t * 5), t, "shock" if t < b["start"] else "happy", 0.9, arms=(-20, 120), hold=hold_phone)
    paste_c(img, bike_img(False, True), 760, 1240, 0.62)
    water(img, t, 1150); rain(img, t, 80, 70)
    k = t - va["start"] + 0.2
    vn = Image.new("RGBA", (560, 150), (0, 0, 0, 0)); o = ImageDraw.Draw(vn)
    o.rounded_rectangle([0, 0, 559, 149], radius=40, fill=(225, 250, 215), outline=INK, width=6)
    o.ellipse([20, 25, 120, 125], fill=(230, 90, 140), outline=INK, width=4); o.text((70, 75), "A", font=fnt("Anton-Regular.ttf", 60), fill=WHITE, anchor="mm")
    for j in range(14): hh = 12 + 40 * abs(math.sin(j * 1.7 + (t * 6 if t < va["end"] else 0))); o.rounded_rectangle([150 + j * 24, 75 - hh / 2, 162 + j * 24, 75 + hh / 2], radius=5, fill=(40, 140, 90))
    paste_c(img, pill("AMMI KA VOICE NOTE", 40, (230, 90, 140), WHITE), W / 2, 330, eob(k / 0.3))
    paste_c(img, vn, W / 2, 450, eob(k / 0.3))
    if t > b["start"]:
        kb = t - b["start"]
        paste_c(img, glow_text("BAHAR HI HOON AMMI…", "Anton-Regular.ttf", 96, YEL, (230, 90, 140)), W / 2, 640, eob(kb / 0.3), rot=-3)
        paste_c(img, emoji("😅", 100), 860, 800, eob((kb - 0.3) / 0.3))

def sc_cake(img, t, lt):
    img.alpha_composite(bg_street("day"))
    d = ImageDraw.Draw(img); d.rectangle([0, 1180, W, H], fill=(110, 110, 120))
    d.polygon([(0, 360), (W, 360), (W - 40, 470), (40, 470)], fill=(40, 140, 110), outline=INK)   # shop awning
    for k in range(8): d.line([(60 + k * 130, 360), (50 + k * 130, 470)], fill=(250, 240, 220), width=10)
    b0, v, b1 = L("cake")
    opened = t > b0["start"] + 0.6
    draw_char(img, "H", 300, 980, t, "det" if not opened else "shock", 0.92, arms=(-20, 70))
    drips(img, 300, 700, t, 3)
    paste_c(img, cake_img(opened), 720, 1150, 1.05 if not opened else 1.15)
    if not opened: paste_c(img, pill("DHEERE… DHEERE…", 52, WHITE, INK), W / 2, 560, eob((t - b0["start"]) / 0.3), rot=-3)
    if opened and t < b1["start"] + 0.2:
        k = t - b0["start"] - 0.6
        paste_c(img, glow_text("CAKE KA HALWA!", "Anton-Regular.ttf", 112, WHITE, (230, 90, 140)), W / 2, 560, eob(k / 0.3), rot=-4)
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, pill("CAKE: Rs 1,200", 58, RED, WHITE), W / 2, 540, eob(k / 0.3), rot=-3)
        paste_c(img, pill("PAISE KATENGE?!", 54, YEL), W / 2, 660, eob((k - 0.35) / 0.3), rot=3)
        paste_c(img, emoji("😨", 110), 880, 820, eob((k - 0.6) / 0.3))
    rain(img, t, 60, 30)

def bg_flat_door(img, t, op):
    img.alpha_composite(grad((215, 205, 190), (180, 170, 160)))
    d = ImageDraw.Draw(img); d.rectangle([0, 1250, W, H], fill=(150, 140, 130))
    d.rectangle([560, 360, 960, 1250], fill=(250, 220, 150), outline=INK, width=8)   # warm light inside
    d.rectangle([560, 360, 560 + 400 * (1 - 0.75 * op), 1250], fill=(120, 80, 60), outline=INK, width=6)
    d.rectangle([620, 290, 900, 345], fill=WHITE, outline=INK, width=4); d.text((760, 318), "FLAT 2-A", font=fnt("Poppins-Black.ttf", 30), fill=INK, anchor="mm")

def sc_tdoor(img, t, lt):
    b0, vh, vt = L("tdoor")
    op = eo((t - b0["start"] - 0.2) / 0.5); bg_flat_door(img, t, op)
    if op > 0.4: draw_char(img, "T", 780, 960, t, "shock" if t < vt["start"] else "happy", 0.92, arms=(-20, 20) if t < vt["end"] - 1.0 else (-20, -110))
    draw_char(img, "H", 280, 1000, t, "sad", 0.92, arms=(-20, 70))
    paste_c(img, cake_img(True), 330, 1260, 0.55)
    drips(img, 280, 720, t, 4)
    paste_c(img, pill("DING DONG", 46, YEL), 760, 230, eob((t - b0["start"]) / 0.25) if t < b0["end"] + 0.4 else 0)
    if op > 0.4 and t < vh["start"]: paste_c(img, pill("MASTER SALEEM • RETIRED TEACHER", 38, (150, 50, 70), WHITE), W / 2, 330, eob((t - b0["start"] - 0.6) / 0.3))
    if t > vt["start"] + 1.0:
        paste_c(img, emoji("☕", 100), 640, 700, eob((t - vt["start"] - 1.0) / 0.3))

@lru_cache(None)
def bg_troom():
    im = bg_room("eve").copy(); d = ImageDraw.Draw(im)
    d.rectangle([640, 330, 1020, 1100], fill=(120, 80, 50), outline=INK, width=8)   # bookshelf
    cols = [(200, 60, 70), (60, 110, 220), (40, 160, 110), (250, 200, 40), (150, 90, 160)]
    for r_ in range(4):
        d.line([(640, 520 + r_ * 190), (1020, 520 + r_ * 190)], fill=INK, width=8)
        for c_ in range(9): d.rectangle([660 + c_ * 38, 400 + r_ * 190, 690 + c_ * 38, 515 + r_ * 190], fill=cols[(r_ + c_) % 5], outline=INK, width=3)
    d.rectangle([90, 400, 470, 650], fill=(250, 245, 230), outline=INK, width=6)   # framed certificate
    d.text((280, 470), "BEST TEACHER", font=fnt("Anton-Regular.ttf", 44), fill=(150, 50, 70), anchor="mm"); d.text((280, 540), "1998", font=fnt("Anton-Regular.ttf", 50), fill=INK, anchor="mm")
    return im

def tip_card(k):
    c = Image.new("RGBA", (640, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 639, 399], radius=40, fill=WHITE, outline=INK, width=7)
    d.rectangle([7, 7, 632, 90], fill=(230, 60, 70)); d.text((320, 50), "TEZ DELIVERY • RATING", font=fnt("Poppins-Black.ttf", 32), fill=WHITE, anchor="mm")
    for j in range(5):
        cx, cy = 110 + j * 105, 170; on = k > j * 0.2
        pts = [(cx + math.cos(math.pi / 2 + m * math.pi / 5) * (44 if m % 2 == 0 else 19), cy - math.sin(math.pi / 2 + m * math.pi / 5) * (44 if m % 2 == 0 else 19)) for m in range(10)]
        d.polygon(pts, fill=(255, 200, 40) if on else (220, 220, 225), outline=INK)
    d.text((320, 262), '"Mehnati bacha hai."', font=fnt("Poppins-Black.ttf", 32), fill=INK, anchor="mm")
    d.text((320, 335), "TIP: + Rs 200", font=fnt("Anton-Regular.ttf", 60), fill=GRN, anchor="mm")
    return c

def sc_troom(img, t, lt):
    img.alpha_composite(bg_troom())
    b0, vt, vh, b1, v, b2 = L("troom")
    draw_char(img, "T", 780, 1000, t, "n" if t < vh["end"] else "shock", 0.92, arms=(-20, 20))
    draw_char(img, "H", 300, 1010, t, "sad" if t < v["start"] else "happy", 0.92, arms=(-20, 70) if t < b1["start"] else (-20, 20))
    d = ImageDraw.Draw(img); d.rounded_rectangle([190, 800, 410, 860], radius=28, fill=WHITE, outline=INK, width=5)   # towel on head
    for k in range(4): d.line([(220 + k * 55, 808), (220 + k * 55, 852)], fill=(200, 200, 210), width=5)
    paste_c(img, cup_img(), 470, 1110, 0.8)
    if t < vt["start"]: paste_c(img, pill("GARAM CHAI + TOWEL", 50, YEL), W / 2, 330, eob((lt - 0.2) / 0.3), rot=-3)
    if t > word_t(vh, "bayaasi", vh["start"] + 0.2) and t < v["start"]:
        k = t - word_t(vh, "bayaasi", vh["start"] + 0.2)
        paste_c(img, glow_text("82%?!", "Anton-Regular.ttf", 170, YEL, (230, 60, 70)), 780, 400, eob(k / 0.3), rot=-5)
    if t > b1["start"] and t < v["start"]:
        paste_c(img, bubble([("CAKE KI FIKAR MAT KARO,", INK), ("MITHAAS WOHI HAI!", GRN)], 40, tail="right"), 650, 600, eob((t - b1["start"]) / 0.3))
    if t > v["start"] - 0.2:
        k = t - v["start"] + 0.2
        paste_c(img, tip_card(k), W / 2, 560, eob(k / 0.3) * 0.95, rot=-2)
    if t > b2["start"]:
        k = t - b2["start"]
        paste_c(img, pill('"KAL SUBAH AANA…"', 50, (150, 50, 70), WHITE), W / 2, 830, eob(k / 0.3), rot=3)
        paste_c(img, emoji("✉️", 100), 820, 880, eob((k - 0.3) / 0.3))

def chit_img():
    c = Image.new("RGBA", (440, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 439, 329], radius=12, fill=(250, 245, 225), outline=INK, width=6)
    for j, (tx, col) in enumerate([("KAL SUBAH 8 BAJE", RED), ("AANA. EK IMTIHAAN", INK), ("HAI. — M. SALEEM", (150, 50, 70))]):
        d.text((220, 70 + j * 90), tx, font=fnt("Poppins-Black.ttf", 34), fill=col, anchor="mm")
    return c

def msg_img():
    c = Image.new("RGBA", (440, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 439, 329], radius=36, fill=(25, 25, 32), outline=INK, width=6)
    d.rounded_rectangle([20, 20, 419, 309], radius=22, fill=(225, 250, 215))
    d.text((220, 70), "MANAGER", font=fnt("Anton-Regular.ttf", 46), fill=(80, 110, 170), anchor="mm")
    d.text((220, 150), "KAL 8 BAJE DUTY.", font=fnt("Poppins-Black.ttf", 34), fill=INK, anchor="mm")
    d.text((220, 230), "LATE = NAUKRI KHATAM", font=fnt("Poppins-Black.ttf", 30), fill=RED, anchor="mm")
    return c

def sc_cliff(img, t, lt):
    img.alpha_composite(bg_ghafoor("night")); bulb_glow(img, 60)
    b0, v, b1, vo = L("cliff")
    pre = t < vo["start"] - 0.15
    paste_c(img, bike_img(True), 760, 1250, 0.6)
    draw_char(img, "H", W / 2, 1000, t, "n" if t < v["start"] else "shock", 0.9, arms=(-110, 110))
    if pre:
        paste_c(img, chit_img(), 270, 520, eob((t - b0["start"] - 0.1) / 0.3) * 0.95, rot=-5)
        if t > word_t(v, "duty", v["start"] + 2.0) - 0.4: paste_c(img, msg_img(), 810, 560, eob((t - word_t(v, "duty", v["start"] + 2.0) + 0.4) / 0.3) * 0.95, rot=5)
        if t > b1["start"]:
            k = t - b1["start"]
            clock(img, W / 2, 820, 8.0); paste_c(img, glow_text("DONO 8 BAJE?!", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), W / 2, 280, eob(k / 0.3), rot=-3)


# ======================= DAY 9+: FORK SIGNPOST, KICK-START, OFFICE BRIEFING, DOORSTEP TEST, HUNGER RUSH, STREET KID (reusable)
def signpost(img, x, y, left="IMTIHAAN", right="NAUKRI", hl=None):
    d = ImageDraw.Draw(img)
    d.rectangle([x - 16, y - 40, x + 16, 1185], fill=(120, 80, 50), outline=INK, width=5)
    for j, (txt, sd) in enumerate(((left, -1), (right, 1))):
        yy = y + j * 120; tw = fnt("Anton-Regular.ttf", 58).getlength(txt) + 70
        x0, x1 = (x - tw - 10, x + 30) if sd < 0 else (x - 30, x + tw + 10)
        tip = x0 - 45 if sd < 0 else x1 + 45
        col = (250, 245, 225) if hl != j else (255, 210, 60)
        pts = [(x0, yy), (x1, yy), (tip, yy + 45), (x1, yy + 90), (x0, yy + 90)] if sd > 0 else [(x1, yy), (x0, yy), (tip, yy + 45), (x0, yy + 90), (x1, yy + 90)]
        d.polygon(pts, fill=col, outline=INK); d.line(pts + [pts[0]], fill=INK, width=6)
        d.text(((x0 + x1) / 2, yy + 45), txt, font=fnt("Anton-Regular.ttf", 58), fill=INK if j == 0 else (180, 40, 50), anchor="mm")

def phone_card(title, rows, t0, t, col=(230, 60, 70), w=620):
    h = 150 + 82 * len(rows); c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=40, fill=(25, 25, 32), outline=INK, width=8)
    d.rounded_rectangle([24, 24, w - 25, h - 25], radius=24, fill=WHITE)
    d.rectangle([24, 24, w - 25, 110], fill=col); d.text((w / 2, 67), title, font=fnt("Anton-Regular.ttf", 52), fill=WHITE, anchor="mm")
    for j, (tx, cc) in enumerate(rows):
        if t > t0 + 0.25 * j: d.text((w / 2, 165 + j * 82), tx, font=fnt("Poppins-Black.ttf", 34), fill=cc, anchor="mm")
    return c

def petrol_bottle():
    c = Image.new("RGBA", (120, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([10, 50, 110, 195], radius=20, fill=(240, 200, 60, 200), outline=INK, width=5)
    d.rectangle([40, 10, 80, 55], fill=(200, 50, 50), outline=INK, width=4); d.rectangle([20, 110, 100, 150], fill=WHITE, outline=INK, width=3)
    d.text((60, 130), "PETROL", font=fnt("Poppins-Black.ttf", 18), fill=INK, anchor="mm")
    return c
def hold_bottle(img, x, y, sc): paste_c(img, petrol_bottle(), x - 150 * sc, y + 170 * sc, sc, rot=10)

def sc_hook_fork(img, t, lt):
    img.alpha_composite(bg_road("day")); signpost(img, 540, 640, hl=int(lt * 2) % 2)
    look = math.sin(lt * 5)
    ride(img, 560, 1260, t, "shock", 0.9, bounce=False, tilt=look * 2)
    paste_c(img, pill("7:50 AM", 44, YEL), 200, 1120, 1.0, rot=-4)
    paste_c(img, glow_text("NAUKRI…", "Anton-Regular.ttf", 120, WHITE, (90, 160, 255)), 540, 300, eob((lt - 0.2) / 0.35))
    paste_c(img, glow_text("YA IMTIHAAN?", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), 540, 440, eob((lt - 1.5) / 0.35) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
    paste_c(img, emoji("🤯" if lt > 2.4 else "😟", 100), 880, 940, eob((lt - 0.6) / 0.3))

def sc_kick(img, t, lt):
    img.alpha_composite(bg_ghafoor("day"))
    b0, b1, vg, vh, b2 = L("kick")
    paid = vh["start"] + 0.8
    kick_on = t < vg["start"]
    jolt = -abs(math.sin((t - b0["start"]) * math.pi / 0.42)) * 28 if kick_on else 0
    started = t > b2["start"]
    ride(img, 470, 1230 + jolt, t, "det" if kick_on else ("happy" if started else "sad"), 0.78, bounce=started, dent=True)
    draw_char(img, "G", 870, 960, t, "happy", 0.85, arms=(-20, 20) if t < vg["start"] else (-20, -110), laugh=vg["start"] < t < vg["start"] + 0.6 or (b1["start"] + 0.4 < t < vg["start"]),
              hold=hold_bottle if t > vg["start"] + 0.5 else None)
    if kick_on:
        n = int((t - b0["start"]) / 0.42)
        for j in range(min(n + 1, 4)):
            paste_c(img, pill(["KICK!", "KICK!!", "KICK!!!", "PHUSS…"][j], 48, YEL if j < 3 else WHITE, INK), 200 + (j % 2) * 220, 700 + j * 90, 1.0, rot=(-6, 5, -3, 4)[j])
        if t > b1["start"] + 0.3: paste_c(img, emoji("😤", 100), 640, 760, eob((t - b1["start"] - 0.3) / 0.3))
    if vg["start"] < t < vh["start"]:
        paste_c(img, pill("TANKI: KHAALI", 56, RED, WHITE), W / 2, 330, eob((t - vg["start"]) / 0.3), rot=-3)
    if t > vh["start"]:
        k = t - vh["start"]
        paste_c(img, pill("PETROL: -Rs 100", 58, RED, WHITE), W / 2, 330, eob(k / 0.3), rot=-3)
        if k < 1.2: paste_c(img, notes_img(100, 180), lerp(380, 760, eo(k / 0.8)), 960 - 80 * math.sin(min(1, k / 0.8) * math.pi), 0.8, rot=-8)
    if started:
        k = t - b2["start"]
        paste_c(img, pill("JEB: Rs 20", 58, WHITE, GRN), W / 2, 450, eob(k / 0.3), rot=3)
        paste_c(img, pill("PHAT-PHAT-PHAT!", 46, WHITE, INK), 470, 860, eob((k - 0.2) / 0.25) * (1 + 0.05 * math.sin(t * 30)), rot=4)
        dust(img, 220, 1330, t, 3, 0.8)

def sc_fork(img, t, lt):
    img.alpha_composite(bg_road("day"))
    b0, v, b1 = L("fork")
    go = t > b1["start"]
    signpost(img, 540, 600, hl=1 if t > word_t(v, "duty", v["start"] + 2.5) - 0.1 else None)
    bx = 560 if not go else lerp(560, 1400, eio((t - b1["start"] - 0.15) / 1.0))
    ride(img, bx, 1260, t, "sad" if t < v["start"] + 1.2 else "det", 0.9, bounce=go, tilt=-3 if go else 0)
    if go: dust(img, bx - 280, 1380, t, 3)
    clock(img, 170, 330, 7 + 52 / 60); paste_c(img, pill("7:52 AM", 40, YEL), 170, 460, 1.0)
    if not go:
        paste_c(img, chit_img(), 190, 920, eob((t - b0["start"] - 0.1) / 0.3) * 0.52, rot=-5)
        paste_c(img, msg_img(), 890, 920, eob((t - b0["start"] - 0.4) / 0.3) * 0.52, rot=5)
        if t > word_t(v, "dawai", v["start"] + 1.4) - 0.1: paste_c(img, emoji("💊", 90), 900, 760, eob((t - word_t(v, "dawai", v["start"] + 1.4) + 0.1) / 0.3))
    else:
        k = t - b1["start"]
        paste_c(img, glow_text("PEHLE DUTY!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 330, eob(k / 0.3), rot=-3)
        paste_c(img, pill("SORRY MASTER SAHAB…", 44, (150, 50, 70), WHITE), W / 2, 470, eob((k - 0.3) / 0.3) * (1 - eo((k - 0.9) / 0.3)), rot=-4)

def sc_briefing(img, t, lt):
    img.alpha_composite(bg_office())
    b0, b1, b2, vh, b3 = L("briefing")
    growl = b2["start"] < t < vh["end"]
    shake = math.sin(t * 70) * 8 if b2["start"] < t < b2["start"] + 0.7 else 0
    draw_char(img, "M", 790, 970, t, "det" if t < b2["start"] else ("shock" if t < b3["start"] else "happy"), 0.95, arms=(-20, -120) if b0["start"] < t < b2["start"] else (-20, 20),
              hold=clipboard, laugh=t > b3["start"])
    draw_char(img, "H", 290 + shake, 990, t, "det" if t < b2["start"] else ("shock" if t < vh["start"] else "happy"), 0.95, arms=(-20, 20) if t < b2["start"] else (-60, 40))
    if t < b2["start"]:
        paste_c(img, bubble([("AAJ 10 ORDER!", INK)], 52, tail="right"), 700, 600, eob((t - b0["start"] - 0.1) / 0.3))
        if t > b1["start"]: paste_c(img, pill("EK BHI LATE = BAHAR!", 56, RED, WHITE), W / 2, 790, eob((t - b1["start"]) / 0.3) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
    if growl:
        k = t - b2["start"]
        paste_c(img, glow_text("GRRRRRR…", "Anton-Regular.ttf", 120, YEL, (150, 90, 40)), 330 + shake, 620, eob(k / 0.25), rot=-6)
        paste_c(img, emoji("😳", 100), 900, 600, eob((k - 0.3) / 0.3))
    if t > b3["start"]:
        k = t - b3["start"]
        paste_c(img, pill("HAHAHA! CHALO, KAAM PE!", 50, YEL), W / 2, 620, eob(k / 0.3), rot=3)
        paste_c(img, emoji("😂", 100), 900, 470, eob((k - 0.2) / 0.3))

def sc_montage(img, t, lt):
    img.alpha_composite(bg_road("day"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 12, 300, 1300); img.alpha_composite(lay)
    b0, b1 = L("montage")
    ride(img, 520, 1200, t, "det", 0.95, box=True, dent=True, tilt=-3 * math.sin(t * 3))
    sparks(img, 470, 1360, t); dust(img, 220, 1330, t, 3)
    n = 1 if t < b1["start"] else 2
    paste_c(img, pill(f"ORDER {n}/10", 62, YEL), W / 2, 330, 1.0, rot=-3)
    for j, b in enumerate((b0, b1)):
        k = t - b["start"] - 0.45
        if k > 0 and t < b["end"] + 0.1:
            paste_c(img, pill("DELIVERED!", 56, GRN, WHITE), W / 2, 480, eob(k / 0.25), rot=4 - 8 * j)
            paste_c(img, emoji("📦", 100), 860, 640, eob(k / 0.25))
    clock(img, 170, 600, 8.5 + 0.8 * eio((t - b0["start"]) / 2.2))

def sc_order3(img, t, lt):
    img.alpha_composite(bg_road("day"))
    b0, v = L("order3")
    paste_c(img, bike_img(True, True), 760, 1240, 0.62)
    mt = word_t(v, "master", v["start"] + 1.6)
    draw_char(img, "H", 300, 990, t, "n" if t < mt else "shock", 0.9, arms=(-20, 110), hold=hold_phone)
    rows = [("DOOR: FLAT 2-A, PECHS", INK), ("NAAM: M. SALEEM", (150, 50, 70)), ("TIME: 20 MINUTE", RED)]
    paste_c(img, phone_card("ORDER 3/10", rows, b0["start"] + 0.2, t), 650, 640, eob((t - b0["start"] - 0.1) / 0.3) * 0.9, rot=3)
    if t > mt - 0.1:
        k = t - mt + 0.1
        paste_c(img, glow_text("MASTER SAHAB?!", "Anton-Regular.ttf", 112, YEL, (230, 60, 70)), W / 2, 300, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("😳", 110), 860, 980, eob((k - 0.2) / 0.3))

def qpaper_img(n_ans, ink_out=False, stamp=0.0, t=0.0):
    c = Image.new("RGBA", (760, 820), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 759, 819], radius=18, fill=(252, 250, 240), outline=INK, width=7)
    d.text((380, 62), "TEST • M. SALEEM", font=fnt("Anton-Regular.ttf", 54), fill=(150, 50, 70), anchor="mm")
    d.line([(40, 110), (720, 110)], fill=(150, 50, 70), width=5)
    qs = [("1)  15 x 12 =", "180"), ("2)  800 ka 25% =", "200"), ("3)  3/4 + 1/4 =", "1"), ("4)  144 ka square root =", "12"), ("5)  1200 ÷ 16 =", "75")]
    for j, (q, a) in enumerate(qs):
        y = 175 + j * 118
        d.text((50, y), q, font=fnt("Poppins-Black.ttf", 40), fill=INK, anchor="lm")
        qx = 60 + fnt("Poppins-Black.ttf", 40).getlength(q)
        if j < int(n_ans):
            d.text((qx + 10, y), a, font=fnt("Anton-Regular.ttf", 58), fill=(40, 70, 200), anchor="lm")
            if stamp > 0: d.line([(690, y - 5), (705, y + 20), (740, y - 30)], fill=(220, 40, 50), width=8)
        elif j == int(n_ans) and ink_out:
            d.line([(qx + 10, y + 5), (qx + 50, y - 2)], fill=(150, 170, 220), width=6)   # faded stroke: pen dried up
    if stamp > 0:
        st = Image.new("RGBA", (300, 200), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.ellipse([10, 10, 290, 190], outline=(220, 40, 50), width=12); sd.text((150, 100), "5/5", font=fnt("Anton-Regular.ttf", 110), fill=(220, 40, 50), anchor="mm")
        paste_c(c, st, 520, 690, eob(stamp / 0.3) * (1.6 - 0.6 * eo(stamp / 0.3)), rot=-12)
    return c

def sc_exam(img, t, lt):
    b0, vt, vh, vt2 = L("exam")
    op = eo((t - b0["start"] - 0.1) / 0.5); bg_flat_door(img, t, op)
    if op > 0.4: draw_char(img, "T", 780, 960, t, "shock" if t < vt["start"] + 0.6 else "det", 0.92, arms=(-20, 20) if t < vt["start"] + 1.0 else (-20, -120))
    draw_char(img, "H", 280, 1000, t, "shock" if t > vt["start"] + 0.8 else "n", 0.92, arms=(-20, 70))
    paste_c(img, bag_img(), 420, 1230, 0.5)
    paste_c(img, pill("DING DONG", 46, YEL), 760, 230, eob((t - b0["start"]) / 0.25) if t < b0["end"] + 0.3 else 0)
    pt = word_t(vt, "paanch", vt["start"] + 1.6)
    if t > pt - 0.1 and t < vh["start"] + 0.2: paste_c(img, pill("TEST: 5 SAWAAL • 5 MINUTE", 46, (150, 50, 70), WHITE), W / 2, 330, eob((t - pt + 0.1) / 0.3), rot=-3)
    if t > vh["start"]:
        paste_c(img, pill("ORDER TIMER: 14:00", 50, RED, WHITE), W / 2, 330, eob((t - vh["start"]) / 0.3), rot=3)
    if t > vt2["start"]:
        paste_c(img, glow_text("JALDI!", "Anton-Regular.ttf", 140, YEL, (230, 60, 70)), W / 2, 520, eob((t - vt2["start"]) / 0.3), rot=-5)

def sc_paper(img, t, lt):
    img.alpha_composite(grad((245, 225, 190), (205, 175, 140)))
    b0, b1, b2, b3 = L("paper")
    span = b3["start"] - b0["start"]
    sec = int(300 - 230 * eio((min(t, b3["start"]) - b0["start"]) / span))
    if t < b1["start"]: n = 2 * eio((t - b0["start"] - 0.1) / 0.8)
    elif t < b2["start"]: n = 2
    else: n = 2 + 3 * eio((t - b2["start"] - 0.25) / 0.8)
    ink_out = b1["start"] + 0.2 < t < b2["start"] + 0.3
    stamp = max(0.0, t - b3["start"] - 0.1)
    paste_c(img, qpaper_img(n, ink_out, stamp, t), W / 2, 820, 1.0, rot=-1.5)
    paste_c(img, pill(f"TIMER {sec // 60:02d}:{sec % 60:02d}", 50, RED if sec < 120 else WHITE, WHITE if sec < 120 else INK), W / 2, 280, 1.0)
    draw_char(img, "H", 190, 1330, t, "det" if t < b1["start"] or t > b2["start"] else "shock", 0.72, arms=(-20, -60))
    draw_char(img, "T", 900, 1340, t, "n" if t < b3["start"] else "happy", 0.72, arms=(-20, 20) if not (b2["start"] < t < b2["start"] + 0.9) else (-120, 20))
    if ink_out:
        k = t - b1["start"] - 0.2
        paste_c(img, glow_text("INK KHATAM!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 1530, eob(k / 0.3) * (1 + 0.04 * math.sin(t * 20)), rot=-4)
        paste_c(img, emoji("🖊️", 110), 760, 1080, eob(k / 0.3), rot=20 * math.sin(t * 8)); paste_c(img, emoji("❌", 80), 800, 1040, eob((k - 0.3) / 0.3))
    if b2["start"] < t < b3["start"] + 0.1:
        k = t - b2["start"]
        pen = Image.new("RGBA", (300, 50), (0, 0, 0, 0)); pd = ImageDraw.Draw(pen)
        pd.rounded_rectangle([0, 10, 260, 40], radius=14, fill=(220, 170, 50), outline=INK, width=5); pd.polygon([(258, 14), (298, 25), (258, 36)], fill=INK)
        paste_c(img, pen, lerp(1100, 700, eo(k / 0.4)), 1150, 1.0, rot=25)
        paste_c(img, pill("LO, MERA KALAM!", 54, (150, 50, 70), WHITE), W / 2, 1530, eob(k / 0.3), rot=3)
    if t > b3["start"] + 0.3:
        paste_c(img, emoji("🎉", 110), 180, 470, eob((t - b3["start"] - 0.3) / 0.3)); paste_c(img, emoji("🎉", 110), 900, 470, eob((t - b3["start"] - 0.4) / 0.3))

def sc_result(img, t, lt):
    bg_flat_door(img, t, 1.0)
    vt, vh, b = L("result")
    run = t > b["start"] + 0.5
    draw_char(img, "T", 780, 960, t, "happy", 0.92, arms=(-20, -130) if t < vt["end"] else (-20, 20))
    hx = 280 if not run else lerp(280, -250, eio((t - b["start"] - 0.5) / 0.6))
    draw_char(img, "H", hx, 1000, t, "shock" if t < b["start"] else "happy", 0.92, arms=(-20, 20) if t < vh["start"] else (-150, 150))
    st = word_t(vt, "scholarship", vt["start"] + 1.3)
    if t > st - 0.1 and t < b["start"] + 0.2:
        paste_c(img, glow_text("SCHOLARSHIP?!", "Anton-Regular.ttf", 120, YEL, (90, 160, 255)), W / 2, 330, eob((t - st + 0.1) / 0.3), rot=-3)
        paste_c(img, emoji("🎓", 120), 540, 520, eob((t - st - 0.2) / 0.3))
    if t > vh["start"] + 0.3 and t < b["start"] + 0.2: paste_c(img, pill("COLLEGE KA SAPNA… WAPAS?", 46, WHITE, (150, 50, 70)), W / 2, 660, eob((t - vh["start"] - 0.3) / 0.3), rot=3)
    if t > b["start"]:
        k = t - b["start"]
        paste_c(img, pill("ORDER! 3 MINUTE BAAKI!", 56, RED, WHITE), W / 2, 330, eob(k / 0.3) * (1 + 0.04 * math.sin(t * 14)), rot=-3)
        paste_c(img, emoji("🏃", 110), 540, 560, eob((k - 0.3) / 0.3))

def sc_rush(img, t, lt):
    b0, v, b1, b2 = L("rush")
    dizzy = t > b1["start"]
    wob = math.sin(t * 6) * 4 * (1 if b1["start"] < t < b2["start"] + 0.3 else 0)
    img.alpha_composite(bg_road("day"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 14, 300, 1300); img.alpha_composite(lay)
    ride(img, 520, 1200, t, "det" if not dizzy else ("sad" if t < b2["start"] + 0.3 else "happy"), 0.95, box=True, dent=True, tilt=-3 * math.sin(t * 3) + wob)
    dust(img, 220, 1330, t, 3)
    q = eio((t - b0["start"]) / (b2["end"] - b0["start"]))
    n = min(10, 3 + int(q * 7.99))
    done = t > b2["start"] + 0.3
    paste_c(img, pill(f"ORDER {10 if done else n}/10", 62, GRN if done else YEL, WHITE if done else INK), W / 2, 330, 1.0, rot=-3)
    clock(img, 170, 560, 10 + 8 * q); paste_c(img, pill("6 PM" if done else "DOPEHAR", 40, YEL), 170, 690, 1.0)
    if t > word_t(v, "khaali", v["start"] + 1.2) - 0.1 and not dizzy:
        paste_c(img, pill("PET: KHAALI", 50, RED, WHITE), 820, 520, eob((t - word_t(v, "khaali", v["start"] + 1.2) + 0.1) / 0.3), rot=4)
    if b1["start"] < t < b2["start"] + 0.3:
        k = t - b1["start"]
        paste_c(img, glow_text("CHAKKAR…", "Anton-Regular.ttf", 120, WHITE, (150, 90, 200)), W / 2, 470, eob(k / 0.3), rot=wob)
        paste_c(img, emoji("😵", 110), 380, 700, eob((k - 0.2) / 0.3), rot=t * 120)
        if k < 0.9: img.alpha_composite(Image.new("RGBA", (W, H), (60, 30, 90, int(70 * math.sin(k / 0.9 * math.pi)))))
    if done:
        k = t - b2["start"] - 0.3
        paste_c(img, glow_text("10/10 DONE!", "Anton-Regular.ttf", 130, WHITE, (40, 190, 110)), W / 2, 480, eob(k / 0.3), rot=-3)

def biscuit_img(open_=False):
    c = Image.new("RGBA", (220, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    if not open_:
        d.rounded_rectangle([0, 10, 219, 110], radius=14, fill=(250, 200, 40), outline=INK, width=5)
        d.text((110, 45), "BISKUT", font=fnt("Anton-Regular.ttf", 40), fill=(180, 40, 50), anchor="mm"); d.text((110, 88), "Rs 20", font=fnt("Poppins-Black.ttf", 22), fill=INK, anchor="mm")
    else:
        for k in range(4): d.ellipse([10 + k * 50, 30, 70 + k * 50, 90], fill=(220, 160, 80), outline=INK, width=4)
    return c
def hold_biscuit(img, x, y, sc): paste_c(img, biscuit_img(), x + 150 * sc, y + 170 * sc, sc * 0.9, rot=-8)
def hold_half(img, x, y, sc): paste_c(img, biscuit_img(True), x + 150 * sc, y + 170 * sc, sc * 0.6, rot=-8)
def hold_half_l(img, x, y, sc): paste_c(img, biscuit_img(True), x - 150 * sc, y + 170 * sc, sc * 0.6, rot=8)

def kiosk(img):
    d = ImageDraw.Draw(img)
    d.rectangle([20, 760, 330, 1190], fill=(80, 120, 160), outline=INK, width=7)
    d.rectangle([10, 700, 340, 780], fill=(230, 60, 70), outline=INK, width=6); d.text((175, 740), "KHOKHA", font=fnt("Anton-Regular.ttf", 48), fill=WHITE, anchor="mm")
    for r_ in range(3):
        for c_ in range(4): d.rectangle([45 + c_ * 70, 810 + r_ * 70, 100 + c_ * 70, 860 + r_ * 70], fill=[(250, 200, 40), (230, 60, 70), (60, 150, 255), (40, 190, 110)][(r_ + c_) % 4], outline=INK, width=3)

def sc_end_kid(img, t, lt):
    img.alpha_composite(bg_street("dawn")); kiosk(img)
    b0, b1, v, b2 = L("end_kid")
    shared = t > word_t(v, "aadhe", v["start"] + 1.2) - 0.1
    kx = lerp(1250, 830, eo((t - b1["start"]) / 0.8))
    draw_char(img, "H", 460, 990, t, "n" if t < b1["start"] + 0.5 else ("det" if not shared else "happy"), 0.9,
              arms=(-20, 20) if t < b0["start"] + 0.3 else (-20, 100), hold=(hold_half if shared else (hold_biscuit if t > b0["start"] + 0.6 else None)))
    if t > b1["start"]:
        draw_char(img, "Z", kx, 1090, t, "sad" if not shared else "happy", 0.7, arms=(-20, 20) if not shared else (-90, 20), hold=hold_half_l if shared else None)
    if t < b1["start"]:
        k = t - b0["start"]
        if k < 0.9: paste_c(img, notes_img(20, 150), lerp(600, 200, eo(k / 0.6)), 1180 - 60 * math.sin(min(1, k / 0.6) * math.pi), 0.7, rot=-8)
        paste_c(img, pill("AAKHRI Rs 20", 54, RED, WHITE), W / 2, 330, eob(k / 0.3), rot=-3)
    if b1["start"] < t < v["start"] + 0.2: paste_c(img, emoji("🥺", 90), kx + 110, 760, eob((t - b1["start"] - 0.5) / 0.3))
    if shared:
        k = t - word_t(v, "aadhe", v["start"] + 1.2) + 0.1
        paste_c(img, pill("AADHA AADHA", 54, YEL), W / 2, 330, eob(k / 0.3), rot=3)
        paste_c(img, emoji("💛", 90), 650, 760, eob((k - 0.3) / 0.3) * (1 + 0.08 * math.sin(t * 6)))
    if t > b2["start"] - 0.4:
        paste_c(img, glow_text("AAJ BHI BACH GAYE", "Anton-Regular.ttf", 100, WHITE, (40, 190, 110)), W / 2, 480, eob((t - b2["start"] + 0.4) / 0.3), rot=-3)

def sc_cliff9(img, t, lt):
    img.alpha_composite(bg_street("night"))
    b0, v, b1, vo = L("cliff9")
    pre = t < vo["start"] - 0.15
    draw_char(img, "H", 300, 1000, t, "n" if t < v["start"] else "shock", 0.92, arms=(-20, 110), hold=hold_phone)
    if pre:
        rows = [("SCHOLARSHIP TEST: PARSON", INK), ("FORM FEE: Rs 1,000", RED), ("AAKHRI DIN: KAL!", (150, 50, 70))]
        fade = 1 - eo((t - b1["start"]) / 0.25) if t > b1["start"] else 1
        paste_c(img, phone_card("MASTER SALEEM", rows, b0["start"] + 0.2, t, (150, 50, 70), 640), 680, 620, eob((t - b0["start"] - 0.1) / 0.3) * 0.88 * max(0.01, fade), rot=3)
        if t > b1["start"]:
            k = t - b1["start"]
            paste_c(img, pill("JEB: Rs 0", 60, WHITE, RED), W / 2, 300, eob(k / 0.3), rot=-3)
            paste_c(img, glow_text("Rs 1,000", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 520, eob((k - 0.2) / 0.3), rot=-3)
            paste_c(img, glow_text("KAHAN SE?!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 690, eob((k - 0.3) / 0.3), rot=-3)


# ======================= DAY 10+: CALL INSET, SETH RAUF'S HOTEL, CHAI TRAY, PAY SCREEN (reusable)
def call_inset(img, who, cx, cy, t, mood="n", bg=((250, 225, 180), (230, 190, 150)), label="", k=1.0, arms=(-20, 20), laugh=False, hold=None):
    """Video-call style framed inset with a character (Ammi/Bilal/... on the phone)."""
    if k <= 0.01: return
    fw, fh = 440, 520
    cv = Image.new("RGBA", (fw, fh), (0, 0, 0, 0)); cv.alpha_composite(grad(bg[0], bg[1], fh).crop((0, 0, fw, fh)))
    draw_char(cv, who, fw / 2, 230, t, mood, 0.72, arms=arms, laugh=laugh, hold=hold)
    m = Image.new("L", (fw, fh), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, fw - 1, fh - 1], radius=40, fill=255)
    fr = Image.new("RGBA", (fw + 24, fh + 24), (0, 0, 0, 0)); fd = ImageDraw.Draw(fr)
    fd.rounded_rectangle([0, 0, fw + 23, fh + 23], radius=50, fill=(25, 25, 32), outline=INK, width=6)
    fr.paste(cv, (12, 12), m)
    if label:
        lb = pill(label, 30, NAMES[who][1], WHITE); fr.alpha_composite(lb, ((fr.width - lb.width) // 2, fr.height - lb.height - 22))
    paste_c(img, fr, cx, cy, k)

@lru_cache(None)
def bg_rauf(mode="night"):
    im = bg_dhaba(mode).copy(); d = ImageDraw.Draw(im)
    d.rounded_rectangle([250, 240, 830, 410], radius=20, fill=(30, 100, 70), outline=INK, width=8)
    d.text((540, 305), "SETH RAUF HOTEL", font=fnt("Anton-Regular.ttf", 74), fill=(255, 230, 120), anchor="mm")
    d.text((540, 375), "CHAI • PARATHA • KARACHI", font=fnt("Poppins-Black.ttf", 26), fill=WHITE, anchor="mm")
    return im

def helper_sign(img, x, y, sc=1.0, rot=4):
    c = Image.new("RGBA", (360, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.polygon([(6, 10), (354, 0), (350, 196), (0, 188)], fill=(205, 160, 105), outline=INK); d.line([(6, 10), (354, 0), (350, 196), (0, 188), (6, 10)], fill=INK, width=6)
    d.text((180, 70), "HELPER CHAHIYE", font=fnt("Anton-Regular.ttf", 46), fill=INK, anchor="mm")
    d.text((180, 140), "RAAT KI SHIFT", font=fnt("Poppins-Black.ttf", 32), fill=RED, anchor="mm")
    paste_c(img, c, x, y, sc, rot=rot)

def tray_cups(img, x, y, sc, n=6, gone=-1):
    d = ImageDraw.Draw(img)
    d.ellipse([x - 150 * sc, y - 20 * sc, x + 150 * sc, y + 24 * sc], fill=(200, 200, 210), outline=INK, width=5)
    for j in range(n):
        if j == gone: continue
        paste_c(img, cup_img(), x + (j - (n - 1) / 2) * 50 * sc, y - 38 * sc - (j % 2) * 6 * sc, sc * 0.62)

def pay_screen(state, sel=0.0):
    """state: pick | sent. sel: 0..1 highlight of the AMMI button."""
    c = Image.new("RGBA", (600, 860), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 599, 859], radius=56, fill=(25, 25, 32), outline=INK, width=8)
    d.rounded_rectangle([22, 22, 577, 837], radius=40, fill=(246, 248, 242))
    d.rectangle([22, 60, 577, 150], fill=(40, 150, 100)); d.rounded_rectangle([22, 22, 577, 100], radius=40, fill=(40, 150, 100))
    d.text((300, 100), "PAISE BHEJO", font=fnt("Anton-Regular.ttf", 58), fill=WHITE, anchor="mm")
    d.text((300, 205), "BALANCE", font=fnt("Poppins-Black.ttf", 30), fill=(120, 120, 130), anchor="mm")
    d.text((300, 275), "Rs 40" if state == "sent" else "Rs 1,040", font=fnt("Anton-Regular.ttf", 96), fill=RED if state == "sent" else (40, 140, 80), anchor="mm")
    for j, (lab, sub) in enumerate((("FORM FEE", "M. SALEEM"), ("AMMI", "ABBU KI DAWAI"))):
        y0 = 370 + j * 220
        on = j == 1 and (sel > 0.5 or state == "sent")
        col = (40, 190, 110) if on else (235, 236, 240)
        d.rounded_rectangle([60, y0, 540, y0 + 180], radius=30, fill=col, outline=INK, width=6)
        d.text((340, y0 + 70), lab, font=fnt("Anton-Regular.ttf", 64), fill=WHITE if on else INK, anchor="mm")
        d.text((340, y0 + 135), ("SENT!  Rs 1,000" if (on and state == "sent") else sub), font=fnt("Poppins-Black.ttf", 28), fill=WHITE if on else (120, 120, 130), anchor="mm")
        c.alpha_composite(emoji("🎓" if j == 0 else "💊", 90), (80, y0 + 45))
    return c

def sc_hook10(img, t, lt):
    img.alpha_composite(bg_street("dawn"))
    v, b = L("hook10")
    draw_char(img, "H", W / 2, 1000, t, "shock", 1.0, arms=(-20, 110), hold=hold_phone)
    paste_c(img, glow_text("Rs 1,000", "Anton-Regular.ttf", 160, YEL, (230, 60, 70)), W / 2, 300, eob((lt - 0.1) / 0.35) * (1 + 0.03 * math.sin(t * 10)), rot=-3)
    dt = word_t(v, "do", v["start"] + 1.6, exact=True)
    if t > dt - 0.15:
        k = t - dt + 0.15
        paste_c(img, pill("FORM FEE", 52, (150, 50, 70), WHITE), 260, 520, eob(k / 0.3), rot=-6)
        paste_c(img, pill("???", 52, RED, WHITE), 820, 520, eob((k - 0.3) / 0.3), rot=6)
        paste_c(img, emoji("🎓", 90), 260, 640, eob((k - 0.1) / 0.3)); paste_c(img, emoji("💊", 90), 820, 640, eob((k - 0.4) / 0.3))
    if t > b["start"]:
        k = t - b["start"]
        paste_c(img, pill("JEB: Rs 0", 64, WHITE, RED), W / 2, 760, eob(k / 0.3) * (1 + 0.04 * math.sin(t * 14)), rot=3)
        paste_c(img, emoji("😰", 100), 830, 900, eob((k - 0.2) / 0.3))

def sc_advance10(img, t, lt):
    img.alpha_composite(bg_office())
    b0, vh, b1, b2 = L("advance10")
    no = t > b1["start"]
    draw_char(img, "M", 790, 970, t, "n" if t < b1["start"] else "happy", 0.95, arms=(-20, -120) if b2["start"] < t else (-20, 20), hold=clipboard, laugh=b1["start"] < t < b2["start"] + 0.2)
    draw_char(img, "H", 290, 990, t, "n" if t < vh["start"] else ("det" if not no else "sad"), 0.95, arms=(-20, 20) if t < vh["start"] else (-60, 60))
    if t < vh["start"]:
        paste_c(img, pill("9 AM • TEZ DELIVERY", 46, YEL), W / 2, 560, eob((t - b0["start"]) / 0.3), rot=-3)
        paste_c(img, emoji("🙏", 100), 300, 650, eob((t - b0["start"] - 0.4) / 0.3))
    if vh["start"] - 0.1 < t < b1["start"] + 0.1:
        at = word_t(vh, "advance", vh["start"] + 1.6)
        if t > at - 0.1: paste_c(img, pill("ADVANCE: Rs 1,000?", 54, WHITE, INK), W / 2, 560, eob((t - at + 0.1) / 0.3), rot=-3)
    if no:
        k = t - b1["start"]
        paste_c(img, bubble([("ADVANCE?", INK), ("HAHAHA!", RED)], 54, tail="right"), 730, 560, eob(k / 0.3))
        paste_c(img, emoji("😂", 90), 950, 420, eob((k - 0.2) / 0.3))
    if t > b2["start"]:
        k = t - b2["start"]
        paste_c(img, pill("PEHLE MAHINA POORA KARO!", 48, RED, WHITE), W / 2, 230, eob(k / 0.3), rot=3)
        st = Image.new("RGBA", (360, 220), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([10, 10, 350, 210], radius=24, outline=RED, width=16); sd.text((180, 110), "NO", font=fnt("Anton-Regular.ttf", 150), fill=RED, anchor="mm")
        paste_c(img, st, 300, 610, eob((k - 0.15) / 0.25) * (1.5 - 0.5 * eo((k - 0.15) / 0.25)), rot=-14)

def sc_bilal10(img, t, lt):
    img.alpha_composite(bg_road("day"))
    b0, vl, vh, b1 = L("bilal10")
    cut = t > b1["start"]
    paste_c(img, bike_img(True, True), 260, 1250, 0.55)
    draw_char(img, "H", 300, 1000, t, "n" if t < vl["start"] + 1.0 else ("det" if t < b1["start"] + 0.5 else "sad"), 0.9, arms=(-20, 110), hold=hold_phone)
    kin = eob((t - b0["start"] - 0.1) / 0.35) * (1 - eo((t - b1["start"] - 0.15) / 0.3) if cut else 1)
    call_inset(img, "L", 770, 760, t, "happy", ((255, 220, 120), (250, 170, 80)), "BILAL • VIDEO CALL", kin, arms=(-20, -120) if t > vl["start"] else (-20, 20))
    if t < vl["start"]: paste_c(img, pill("RING RING…", 46, YEL), 770, 420, eob((t - b0["start"]) / 0.3) * (1 + 0.05 * math.sin(t * 25)), rot=-4)
    if vl["start"] < t < vh["start"] + 0.2:
        st = word_t(vl, "scheme", vl["start"] + 1.8)
        if t > st - 0.1:
            paste_c(img, pill("SCHEME 2.0: PAISE TRIPLE!", 44, (255, 130, 40), WHITE), W / 2, 330, eob((t - st + 0.1) / 0.3), rot=-3)
            paste_c(img, emoji("🤑", 100), 960, 470, eob((t - st) / 0.3))
    if t > vh["start"]:
        k = t - vh["start"]
        paste_c(img, glow_text("NO SCHEME!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 330 if not cut else 330, eob(k / 0.3), rot=-4)
    if cut:
        k = t - b1["start"]
        paste_c(img, pill("CALL CUT", 52, RED, WHITE), 770, 760, eob((k - 0.2) / 0.3), rot=5)
        paste_c(img, emoji("🤦", 110), 560, 620, eob((k - 0.3) / 0.3))

def sc_tips10(img, t, lt):
    img.alpha_composite(bg_road("day"))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 12, 300, 1300); img.alpha_composite(lay)
    bs = L("tips10")
    ride(img, 520, 1200, t, "det", 0.95, box=True, dent=True, tilt=-3 * math.sin(t * 3)); dust(img, 220, 1330, t, 3)
    j = max([i for i, b in enumerate(bs) if t >= b["start"] - 0.05] or [0])
    paste_c(img, pill(f"ORDER {(4, 7, 10)[j]}/10", 62, YEL), W / 2, 330, 1.0, rot=-3)
    k = t - bs[j]["start"] - 0.2
    if k > 0: paste_c(img, pill(f"TIP +Rs {(120, 170, 150)[j]}", 60, GRN, WHITE), W / 2, 470, eob(k / 0.25), rot=4 - 8 * (j % 2))
    if k > 0.15: paste_c(img, emoji(("🙂", "⭐", "🤩")[j], 100), 860, 640, eob((k - 0.15) / 0.25))
    clock(img, 170, 600, 10 + 8 * eio((t - bs[0]["start"]) / (bs[-1]["end"] - bs[0]["start"])))

def sc_call10(img, t, lt):
    img.alpha_composite(bg_street("dawn"))
    b0, va, vh, b1, v = L("call10")
    paste_c(img, bike_img(True, True), 260, 1250, 0.55)
    mood = "happy" if t < va["start"] + 0.3 else ("sad" if t < vh["start"] else ("det" if t < b1["start"] else "shock"))
    draw_char(img, "H", 300, 1000, t, mood, 0.9, arms=(-20, 110), hold=hold_phone)
    paste_c(img, pill("6 PM", 40, YEL), 140, 440, 1.0)
    if t < va["start"]:
        k = t - b0["start"]
        paste_c(img, pill("AMMI CALLING…", 50, (230, 90, 140), WHITE), 740, 560, eob(k / 0.3) * (1 + 0.05 * math.sin(t * 25)), rot=-4)
        paste_c(img, emoji("❤️", 90), 740, 700, eob((k - 0.2) / 0.3))
    if va["start"] - 0.2 < t < b1["start"] + 0.1:
        kin = eob((t - va["start"] + 0.2) / 0.35) * (1 - eo((t - b1["start"] + 0.2) / 0.3))
        call_inset(img, "A", 770, 720, t, "sad", ((240, 210, 170), (210, 170, 130)), "AMMI • LAHORE", kin)
        dt = word_t(va, "dawai", va["start"] + 1.5)
        if t > dt - 0.1: paste_c(img, pill("ABBU KI DAWAI: Rs 1,000", 46, RED, WHITE), W / 2, 330, eob((t - dt + 0.1) / 0.3), rot=-3)
        if t > dt: paste_c(img, emoji("💊", 90), 960, 450, eob((t - dt) / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        rows = [("FORM FEE      Rs 1,000", (150, 50, 70)), ("ABBU KI DAWAI  Rs 1,000", RED), ("JEB MEIN        Rs 440", (40, 140, 80))]
        card = phone_card("HISAAB", rows, b1["start"] + 0.1, t, (60, 110, 200), 660)
        paste_c(img, card, 650, 600, eob(k / 0.3) * 0.98, rot=3)
    if t > v["start"]:
        k = t - v["start"]; dt = word_t(v, "do", v["start"] + 1.4, exact=True)
        if t > dt - 0.1: paste_c(img, glow_text("Rs 2,000?!", "Anton-Regular.ttf", 140, YEL, (230, 60, 70)), W / 2, 300, eob((t - dt + 0.1) / 0.3) * (1 + 0.03 * math.sin(t * 12)), rot=-3)

def sc_rauf10(img, t, lt):
    img.alpha_composite(bg_rauf("night")); bulb_glow(img, 70)
    b0, vr, vh = L("rauf10")
    helper_sign(img, 230, 820, 0.85, 5)
    hx = lerp(-150, 270, eo((t - b0["start"]) / 0.8))
    loud = vr["start"] < t < vr["end"]
    draw_char(img, "R", 790, 960 + (math.sin(t * 40) * 4 if loud else 0), t, "det" if t < vh["start"] else "happy", 1.0, arms=(-20, -130) if loud else (-20, 20))
    draw_char(img, "H", hx, 1010, t, "n" if t < vr["start"] else ("shock" if t < vh["start"] else "happy"), 0.9, arms=(-20, 20) if t < vh["start"] else (-20, 120))
    if t < vr["start"]: paste_c(img, pill("RAAT 9 BAJE", 46, YEL), W / 2, 560, eob((t - b0["start"] - 0.2) / 0.3), rot=-3)
    if loud or (vr["end"] <= t < vh["start"] + 0.1):
        k = t - vr["start"]
        paste_c(img, pill("RAAT KI SHIFT: Rs 500", 52, YEL), W / 2, 500, eob(k / 0.3), rot=-3)
        ct = word_t(vr, "cup", vr["start"] + 2.5)
        if t > ct - 0.1:
            paste_c(img, pill("CUP TOOTA = PAISE KATENGE!", 44, RED, WHITE), W / 2, 620, eob((t - ct + 0.1) / 0.3) * (1 + 0.04 * math.sin(t * 16)), rot=3)
            paste_c(img, emoji("☕", 90), 990, 720, eob((t - ct) / 0.3))
    if t > vh["start"]:
        k = t - vh["start"]
        paste_c(img, pill("DEAL!", 60, GRN, WHITE), W / 2, 600, eob((k - 0.2) / 0.3), rot=-4)
        paste_c(img, emoji("🤝", 110), W / 2, 740, eob((k - 0.4) / 0.3))

def sc_shift10(img, t, lt):
    img.alpha_composite(bg_rauf("night")); bulb_glow(img, 70)
    b0, b1, b2, b3, b4, vr = L("shift10")
    fall0 = b2["start"]; land = b3["start"] + 0.35
    hx, hy, sc_ = 360, 1000, 0.95
    shock = fall0 < t < land
    draw_char(img, "R", 860, 1010, t, "shock" if fall0 < t < b4["start"] else "happy", 0.85, arms=(-20, -140) if t > vr["start"] else (-20, 20),
              laugh=b4["start"] < t < vr["start"])
    tx, ty = hx + 160 * sc_, hy + 150 * sc_
    draw_char(img, "H", hx + math.sin(t * 7) * (8 if t < fall0 else 0), hy, t, "det" if t < fall0 else ("shock" if shock else "happy"), sc_, arms=(-20, 95))
    gone = 5 if t > fall0 else -1
    tray_cups(img, tx, ty, 1.0, 6, gone)
    clock(img, 170, 330, 21.5 + 4.5 * eio((t - b0["start"]) / (b2["start"] - b0["start"])))
    if t < fall0:   # orders fly in
        orders = [("10 CHAI!", YEL, 760, 470), ("4 PARATHA!", WHITE, 300, 560), ("JALDI KARO!", RED, 760, 640), ("2 DOODH PATTI!", YEL, 330, 420)]
        for j, (tx_, col, x_, y_) in enumerate(orders):
            kk = t - b0["start"] - j * 0.55
            if kk > 0: paste_c(img, pill(tx_, 44, col, WHITE if col == RED else INK), x_, y_, eob(kk / 0.25), rot=(-5, 4, -3, 6)[j])
        steam(img, tx, ty - 60, t, 3, 0.7)
    if fall0 <= t < land:   # the cup flips off the tray, spins high and drops
        q = (t - fall0) / (land - fall0)
        cx_ = lerp(tx + 125, hx, q); cy_ = lerp(ty - 40, hy - 250, q) - 420 * math.sin(q * math.pi)
        paste_c(img, cup_img(), cx_, cy_, 0.9, rot=q * 720)
        if t < b3["start"]:
            paste_c(img, glow_text("NAHIIII!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 300, eob((t - fall0) / 0.25), rot=-4)
            img.alpha_composite(Image.new("RGBA", (W, H), (20, 10, 40, int(60 * math.sin(min(1, (t - fall0) / 0.9) * math.pi)))))
            paste_c(img, pill("SLOW MOTION…", 40, WHITE), W / 2, 430, eob((t - fall0 - 0.2) / 0.25))
    if t >= land:   # lands on Hamid's head - not one drop spilled
        paste_c(img, cup_img(), hx, hy - 240 + 4 * math.sin(t * 6), 0.9, rot=3 * math.sin(t * 5))
        k = t - land
        paste_c(img, glow_text("LAHORE KI TRAINING!", "Anton-Regular.ttf", 96, YEL, (40, 190, 110)), W / 2, 300, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("😎", 90), hx + 150, hy - 260, eob((k - 0.2) / 0.3))
    if t > b4["start"]:
        k = t - b4["start"]
        paste_c(img, pill("EK BOOND BHI NAHI GIRI!", 44, WHITE, GRN), W / 2, 430, eob(k / 0.3), rot=3)
        for j in range(3): paste_c(img, emoji("👏", 70), 640 + j * 90, 640 + 15 * math.sin(t * 12 + j), eob((k - 0.1 * j) / 0.3))
    if t > vr["start"]:
        k = t - vr["start"]; st = word_t(vr, "sau", vr["start"] + 1.0)
        if t > st - 0.1 and t - st < 1.4: paste_c(img, notes_img(600, 200), lerp(840, 520, eo((t - st) / 0.7)), 760, 0.75, rot=-8)
        if t > st + 0.6: paste_c(img, pill("Rs 500 + Rs 100 INAAM", 46, GRN, WHITE), W / 2, 560, eob((t - st - 0.6) / 0.3), rot=-3)

def sc_choice10(img, t, lt):
    img.alpha_composite(bg_street("night"))
    b0, v, b1, b2 = L("choice10")
    sent = t > b1["start"] + 0.55
    draw_char(img, "H", 230, 1080, t, "n" if t < v["start"] else ("det" if not sent else ("sad" if t > b2["start"] else "det")), 0.85, arms=(-20, 110))
    sel = 1.0 if t > b1["start"] + 0.45 else 0.0
    paste_c(img, pay_screen("sent" if sent else "pick", sel), 680, 820, eob((t - b0["start"] - 0.05) / 0.3) * 0.9, rot=2)
    hrs = 23 + 58 / 60 + (2 / 60) * eio((t - b2["start"]) / 0.6)
    clock(img, 170, 330, hrs); paste_c(img, pill("12:00 AM" if t > b2["start"] + 0.5 else "11:58 PM", 40, YEL), 170, 460, 1.0)
    if b0["start"] < t < b1["start"]:   # finger hovers between the two buttons
        fy = 820 + 0 * math.sin(t * 3) ; fx = 680 + 130 * math.sin(t * 2.6)
        paste_c(img, emoji("👆", 110), fx + 120, 1120 + 40 * math.sin(t * 3.2), 1.0)
    if b1["start"] <= t:
        q = eo((t - b1["start"]) / 0.45); paste_c(img, emoji("👆", 110), 800, lerp(1120, 1020, q), 1.0 if t < b1["start"] + 0.9 else max(0.01, 1 - (t - b1["start"] - 0.9) / 0.3))
    if sent and t < b2["start"]:
        k = t - b1["start"] - 0.55
        paste_c(img, glow_text("DAWAI PEHLE.", "Anton-Regular.ttf", 120, WHITE, (40, 190, 110)), W / 2, 300, eob(k / 0.3), rot=-3)
    if t > b2["start"] + 0.4:
        k = t - b2["start"] - 0.4
        st = Image.new("RGBA", (760, 230), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([10, 10, 750, 220], radius=28, fill=(255, 255, 255, 220), outline=RED, width=14); sd.text((380, 115), "FORM: BAND", font=fnt("Anton-Regular.ttf", 130), fill=RED, anchor="mm")
        paste_c(img, st, 600, 540, eob(k / 0.25) * (1.4 - 0.4 * eo(k / 0.25)), rot=-10)

def sc_end10(img, t, lt):
    img.alpha_composite(bg_street("night"))
    v, b0, b1 = L("end10")
    draw_char(img, "H", 300, 1000, t, "sad" if t < word_t(v, "dawai", v["start"] + 1.2) else "happy", 0.92, arms=(-20, 110), hold=hold_phone)
    rows = [("DAWAI LE AAYE BETA.", INK), ("ABBU NE KHA LI.", (40, 140, 80)), ("JEETE RAHO ❤", (230, 90, 140))]
    rows = [(a.replace(" ❤", ""), c) for a, c in rows]
    paste_c(img, phone_card("AMMI", rows, v["start"] + 1.0, t, (230, 90, 140), 640), 690, 620, eob((t - v["start"] - 0.9) / 0.3) * 0.98, rot=3)
    if t > v["start"] + 1.6: paste_c(img, emoji("❤️", 80), 920, 860, eob((t - v["start"] - 1.6) / 0.3) * (1 + 0.08 * math.sin(t * 6)))
    if t > b0["start"] - 0.5:
        paste_c(img, glow_text("AAJ BHI BACH GAYE", "Anton-Regular.ttf", 100, WHITE, (40, 190, 110)), W / 2, 300, eob((t - b0["start"] + 0.5) / 0.3), rot=-3)
    if t > b1["start"]:
        paste_c(img, pill("JEB: Rs 40 • FORM: GAYA", 46, WHITE, INK), W / 2, 1230, eob((t - b1["start"]) / 0.3), rot=-2)

def sc_cliff10(img, t, lt):
    img.alpha_composite(bg_street("night"))
    b0, v, b1, vo = L("cliff10")
    draw_char(img, "H", 300, 1000, t, "n" if t < b0["start"] + 0.5 else "shock", 0.92, arms=(-20, 110), hold=hold_phone)
    paste_c(img, pill("12:07 AM", 40, YEL), 170, 300, 1.0)
    if t < vo["start"] - 0.15:
        rows = [("FORM MAINE BHAR DIYA.", (40, 140, 80)), ("KAL SUBAH 9 BAJE TEST.", INK), ("PAR EK SHART HAI…", RED)]
        paste_c(img, phone_card("MASTER SALEEM", rows, b0["start"] + 0.2, t, (150, 50, 70), 660), 680, 610, eob((t - b0["start"] - 0.05) / 0.3) * 0.98, rot=3)
        if t > b1["start"]:
            k = t - b1["start"]
            paste_c(img, glow_text("EK SHART?!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 300, eob(k / 0.3) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
            paste_c(img, emoji("🤔", 110), 860, 1000, eob((k - 0.2) / 0.3))

# ======================= DAY 11+: TEST CENTER, PRINT SHOP, CITY BUS, EXAM HALL (blackout), RESULT NOTICE BOARD (reusable)
@lru_cache(None)
def bg_center(mode="day"):
    im = bg_road(mode).copy(); d = ImageDraw.Draw(im)
    d.rectangle([40, 330, 700, 1180], fill=(235, 225, 200), outline=INK, width=8)
    d.rectangle([40, 330, 700, 500], fill=(40, 90, 160), outline=INK, width=8)
    d.text((370, 395), "SCHOLARSHIP", font=fnt("Anton-Regular.ttf", 84), fill=WHITE, anchor="mm")
    d.text((370, 465), "TEST CENTER • KARACHI", font=fnt("Poppins-Black.ttf", 30), fill=YEL, anchor="mm")
    for c_ in range(3): d.rectangle([90 + c_ * 200, 560, 210 + c_ * 200, 680], fill=(150, 200, 235), outline=INK, width=5)
    d.rectangle([230, 860, 520, 1180], fill=(90, 70, 60), outline=INK, width=6)   # gate
    for k in range(6): d.line([(250 + k * 50, 860), (250 + k * 50, 1180)], fill=INK, width=5)
    d.rectangle([740, 640, 1050, 1180], fill=(200, 110, 80), outline=INK, width=7)   # print shop
    d.rectangle([730, 580, 1060, 660], fill=YEL, outline=INK, width=6)
    d.text((895, 620), "PHOTOCOPY", font=fnt("Anton-Regular.ttf", 50), fill=INK, anchor="mm")
    d.rectangle([770, 700, 1020, 780], fill=WHITE, outline=INK, width=4)
    d.text((895, 740), "PRINT Rs 20", font=fnt("Poppins-Black.ttf", 34), fill=RED, anchor="mm")
    return im

@lru_cache(None)
def city_bus_img():
    im = bus_img().copy(); d = ImageDraw.Draw(im)
    d.rectangle([340, 190, 560, 236], fill=WHITE, outline=INK, width=4)
    d.text((450, 213), "ROUTE 11 • SADDAR", font=fnt("Poppins-Black.ttf", 24), fill=INK, anchor="mm")
    return im

@lru_cache(None)
def admit_card():
    c = Image.new("RGBA", (420, 280), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, 419, 279], radius=16, fill=(252, 250, 240), outline=INK, width=6)
    d.rectangle([6, 6, 413, 70], fill=(40, 90, 160)); d.text((210, 38), "ADMIT CARD", font=fnt("Anton-Regular.ttf", 46), fill=WHITE, anchor="mm")
    d.rectangle([30, 100, 130, 230], fill=(200, 210, 225), outline=INK, width=4)
    d.text((270, 130), "HAMID", font=fnt("Anton-Regular.ttf", 50), fill=INK, anchor="mm")
    d.text((270, 195), "ROLL NO: 0011", font=fnt("Poppins-Black.ttf", 28), fill=(150, 50, 70), anchor="mm")
    return c

@lru_cache(None)
def bg_hall():
    im = grad((215, 200, 170), (190, 170, 140)).copy(); d = ImageDraw.Draw(im)
    d.rectangle([300, 230, 1000, 560], fill=(40, 70, 55), outline=(120, 80, 50), width=14)   # blackboard
    d.text((650, 330), "SCHOLARSHIP TEST", font=fnt("Anton-Regular.ttf", 66), fill=WHITE, anchor="mm")
    d.text((650, 430), "50 SAWAAL • 60 MINUTE", font=fnt("Poppins-Black.ttf", 36), fill=YEL, anchor="mm")
    d.rectangle([40, 300, 240, 700], fill=(170, 215, 245), outline=INK, width=8)   # window
    d.line([(140, 300), (140, 700)], fill=INK, width=6); d.line([(40, 500), (240, 500)], fill=INK, width=6)
    d.rectangle([0, 1180, W, H], fill=(150, 120, 95))
    for r_ in range(2):   # back rows of desks with other students
        y = 820 + r_ * 150
        for c_ in range(4):
            x = 140 + c_ * 250 + r_ * 60
            d.ellipse([x - 40, y - 90, x + 40, y - 10], fill=(70, 50, 40), outline=INK, width=4)
            d.rectangle([x - 90, y, x + 90, y + 40], fill=(150, 100, 60), outline=INK, width=4)
    return im

def front_desk(img, y=1230):
    d = ImageDraw.Draw(img)
    d.rectangle([180, y, 900, y + 70], fill=(170, 115, 70), outline=INK, width=7)
    d.rectangle([220, y + 70, 250, 1420], fill=(120, 80, 50), outline=INK, width=5); d.rectangle([830, y + 70, 860, 1420], fill=(120, 80, 50), outline=INK, width=5)

def answer_sheet(n):
    c = Image.new("RGBA", (360, 230), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 359, 229], fill=(252, 250, 240), outline=INK, width=5)
    for j in range(5):
        for k in range(10):
            on = j * 10 + k < n
            d.ellipse([22 + k * 33, 22 + j * 40, 46 + k * 33, 46 + j * 40], fill=(40, 70, 200) if on else (252, 250, 240), outline=INK, width=2)
    return c

@lru_cache(None)
def notice_board(hl=False):
    c = Image.new("RGBA", (820, 760), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 819, 759], fill=(150, 100, 60), outline=INK, width=8)
    d.rectangle([30, 30, 789, 729], fill=(250, 248, 238), outline=INK, width=4)
    d.text((410, 90), "RESULT • SCHOLARSHIP TEST", font=fnt("Anton-Regular.ttf", 52), fill=(40, 90, 160), anchor="mm")
    d.line([(60, 140), (760, 140)], fill=INK, width=4)
    rows = [("ALI RAZA", "94%"), ("SANA KHAN", "91%"), ("HAMID", "89%"), ("FAHAD MIRZA", "86%"), ("NIDA ASIF", "83%")]
    for j, (nm, p) in enumerate(rows):
        y = 200 + j * 90
        if hl and nm == "HAMID": d.rectangle([50, y - 38, 770, y + 38], fill=(255, 220, 80))
        d.text((90, y), nm, font=fnt("Poppins-Black.ttf", 42), fill=INK, anchor="lm")
        d.text((730, y), p, font=fnt("Anton-Regular.ttf", 54), fill=RED if nm == "HAMID" else INK, anchor="rm")
    d.text((410, 680), "SCHOLARSHIP: 90% YA ZYADA", font=fnt("Poppins-Black.ttf", 34), fill=(150, 50, 70), anchor="mm")
    return c

def sc_hook11(img, t, lt):
    img.alpha_composite(bg_street("dawn"))
    v, b = L("hook11")
    draw_char(img, "H", W / 2, 1000, t, "shock", 1.0, arms=(-20, 110), hold=hold_phone)
    paste_c(img, glow_text("90%", "Anton-Regular.ttf", 220, YEL, (230, 60, 70)), W / 2, 320, eob((lt - 0.1) / 0.35) * (1 + 0.03 * math.sin(t * 10)), rot=-3)
    ht = word_t(v, "hazaar", v["start"] + 1.4)
    if t > ht - 0.15:
        k = t - ht + 0.15
        paste_c(img, pill("YA Rs 1,000 KARZA!", 60, RED, WHITE), W / 2, 540, eob(k / 0.3), rot=3)
        paste_c(img, emoji("💸", 100), 880, 680, eob((k - 0.2) / 0.3))
    if t > b["start"]:
        k = t - b["start"]
        st = Image.new("RGBA", (520, 220), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([10, 10, 510, 210], radius=24, fill=(255, 255, 255, 220), outline=(150, 50, 70), width=14)
        sd.text((260, 112), "EK SHART", font=fnt("Anton-Regular.ttf", 120), fill=(150, 50, 70), anchor="mm")
        paste_c(img, st, 300, 720, eob(k / 0.25) * (1.4 - 0.4 * eo(k / 0.25)), rot=-10)
        paste_c(img, emoji("😰", 100), 830, 900, eob((k - 0.2) / 0.3))

def sc_shart11(img, t, lt):
    img.alpha_composite(bg_rauf("night")); bulb_glow(img, 70)
    b0, b1, vh, b2 = L("shart11")
    tray_cups(img, 820, 1150, 0.9, 5)
    clock(img, 170, 330, 6.0)
    if t < b1["start"]: paste_c(img, pill("SUBAH 6 BAJE", 40, YEL), 170, 460, 1.0)
    mood = "n" if t < b1["start"] else ("shock" if t < vh["start"] else ("det" if t < b2["start"] else "sad"))
    draw_char(img, "H", 300, 1000, t, mood, 0.92, arms=(-20, 110) if t < b2["start"] else (-20, 20), hold=hold_phone if t < b2["start"] else None)
    if t < b2["start"]:
        rows = [("SHART: 90% SE KAM AAYE…", INK), ("…TOH Rs 1,000 WAPAS!", RED), ("TEST: AAJ SUBAH 9 BAJE", (150, 50, 70))]
        paste_c(img, phone_card("MASTER SALEEM", rows, b0["start"] + 0.15, t, (150, 50, 70), 660), 680, 720, eob((t - b0["start"] - 0.05) / 0.3) * 0.95, rot=3)
    if b1["start"] < t < vh["start"] + 0.3:
        k = t - b1["start"]
        paste_c(img, glow_text("90% SE KAM = KARZA", "Anton-Regular.ttf", 96, YEL, (230, 60, 70)), W / 2, 470, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("😳", 100), 300, 700, eob((k - 0.2) / 0.3))
    if vh["start"] + 0.3 < t < b2["start"]:
        k = t - vh["start"] - 0.3
        paste_c(img, glow_text("MANZOOR!", "Anton-Regular.ttf", 120, WHITE, (40, 190, 110)), W / 2, 470, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("💪", 100), 120, 760, eob((k - 0.3) / 0.3))
    if t > b2["start"]:
        k = t - b2["start"]
        paste_c(img, pill("RAAT BHAR SHIFT", 54, (40, 110, 70), WHITE), W / 2, 520, eob(k / 0.3), rot=-3)
        paste_c(img, pill("NEEND: 0 GHANTE", 54, RED, WHITE), W / 2, 640, eob((k - 0.25) / 0.3), rot=3)
        paste_c(img, emoji("🥱", 110), 470, 820, eob((k - 0.4) / 0.3))

def sc_sleep11(img, t, lt):
    img.alpha_composite(bg_rauf("night")); bulb_glow(img, 70)
    b0, b1, vr, b2 = L("sleep11")
    up = t > b2["start"]
    if not up:
        draw_char(img, "H", 330, 1060, t, "sleep", 0.9, arms=(-60, 60)); zzz(img, 380, 820, t)
    else:
        k = t - b2["start"]
        hx = lerp(330, -300, eio((k - 0.6) / 0.6)); hy = 1000 - 120 * math.sin(min(1, k / 0.4) * math.pi)
        draw_char(img, "H", hx, hy, t, "shock", 0.9, arms=(-120, 120))
    d = ImageDraw.Draw(img); d.rectangle([80, 1230, 620, 1290], fill=(160, 110, 70), outline=INK, width=6)   # bench
    hrs = 6.08 + (8.25 - 6.08) * eio((t - b1["start"]) / 1.1) if t > b1["start"] else 6.08
    clock(img, 170, 330, hrs)
    if t < b1["start"]: paste_c(img, bubble([("BAS 5 MINUTE…", INK)], 44, tail="left"), 460, 560, eob((t - b0["start"]) / 0.3))
    if b1["start"] <= t < vr["start"]:
        k = t - b1["start"]
        paste_c(img, pill("2 GHANTE BAAD…", 56, WHITE), W / 2, 460, eob(k / 0.3), rot=-3)
        img.alpha_composite(Image.new("RGBA", (W, H), (255, 220, 150, int(50 * eo(k / 1.0)))))
    if t > vr["start"] - 0.3:
        rx = lerp(1300, 820, eo((t - vr["start"] + 0.3) / 0.5)); loud = vr["start"] < t < vr["end"]
        draw_char(img, "R", rx, 980 + (math.sin(t * 40) * 4 if loud else 0), t, "det", 0.95, arms=(-20, -130) if loud else (-20, 20))
        if loud: paste_c(img, pill("AATH BAJ GAYE!", 56, RED, WHITE), W / 2, 460, eob((t - vr["start"]) / 0.3), rot=3)
    if up:
        k = t - b2["start"]
        paste_c(img, glow_text("8:15!!", "Anton-Regular.ttf", 170, YEL, (230, 60, 70)), W / 2, 540, eob(k / 0.25), rot=-4)
        paste_c(img, pill("TEST 9 BAJE • 12 KM DOOR", 46, WHITE, RED), W / 2, 700, eob((k - 0.2) / 0.3), rot=3)
        paste_c(img, emoji("😱", 110), 560, 830, eob((k - 0.1) / 0.3))

def sc_ghafoor11(img, t, lt):
    img.alpha_composite(bg_ghafoor("day"))
    b0, vg, b1 = L("ghafoor11")
    paste_c(img, bike_img(True), 760, 1290, 0.55)
    hx = lerp(-200, 300, eo((t - b0["start"]) / 0.6))
    draw_char(img, "G", 790, 990, t, "det" if t > vg["start"] else "n", 0.92, arms=(-20, -120) if vg["start"] < t < vg["end"] else (-20, 20))
    draw_char(img, "H", hx, 1000, t, "det" if t < vg["start"] else ("shock" if t < b1["start"] else "sad"), 0.9, arms=(-20, 90) if t < vg["start"] else (-20, 20))
    if t < vg["start"]:
        paste_c(img, bubble([("CHACHA, BIKE DO!", INK), ("JALDI HAI!", RED)], 46, tail="left"), 440, 560, eob((t - b0["start"] - 0.3) / 0.3))
    if vg["start"] < t < b1["start"] + 0.1:
        k = t - vg["start"]
        paste_c(img, pill("PEHLE JURMANA: Rs 450", 50, RED, WHITE), W / 2, 330, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("😤", 100), 930, 720, eob((k - 0.2) / 0.3))
    if t > b1["start"]:
        k = t - b1["start"]
        paste_c(img, pill("JEB: Rs 40", 56, WHITE, RED), 300, 250, eob(k / 0.3), rot=-4)
        paste_c(img, pill("JURMANA: Rs 450", 56, RED, WHITE), 760, 370, eob((k - 0.2) / 0.3), rot=4)
        st = Image.new("RGBA", (560, 220), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
        sd.rounded_rectangle([10, 10, 550, 210], radius=24, fill=(255, 255, 255, 220), outline=RED, width=14); sd.text((280, 112), "NO BIKE", font=fnt("Anton-Regular.ttf", 120), fill=RED, anchor="mm")
        paste_c(img, st, W / 2, 680, eob((k - 0.45) / 0.25) * (1.4 - 0.4 * eo((k - 0.45) / 0.25)), rot=-8)

def sc_bus11(img, t, lt):
    img.alpha_composite(bg_road("day"))
    b0, b1, va, b2, vh, b3 = L("bus11")
    run = t > b3["start"]
    if not run:
        moving = t < b2["start"] or t > vh["start"] + 1.2
        if moving and t > b0["start"] + 0.8: lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 10, 300, 900); img.alpha_composite(lay)
        if t > b2["start"]:   # jam: cars ahead
            for j, (cx_, col) in enumerate(((-60, (230, 60, 70)), (1120, (60, 110, 220)))): paste_c(img, car_img(col, j), cx_, 1230, 0.8)
        bx = lerp(1500, 520, eo((t - b0["start"]) / 0.8)); bob = math.sin(t * 9) * 5 if moving else 0
        paste_c(img, city_bus_img(), bx, 1010 + bob, 1.0)
        for j, who in enumerate(("C", "K", "X", "M", "C", "K")):   # packed windows
            paste_c(img, head(who, "open", 0, "n"), bx - 340 + j * 125, 900 + bob, 0.26)
        wheel(img, bx - 300, 1180 + bob * 0.3, t if moving else 0); wheel(img, bx + 250, 1180 + bob * 0.3, t if moving else 0)
        off = vh["start"] + 0.5 < t
        if not off: draw_char(img, "H", bx + 420, 870 + bob, t, "shock" if t < b1["start"] + 0.6 else ("happy" if va["start"] < t < b2["start"] else "det"), 0.5, arms=(-20, -150))
        else:
            k = t - vh["start"] - 0.5
            draw_char(img, "H", lerp(bx + 420, 760, eo(k / 0.4)), lerp(870, 1030, eo(k / 0.4)), t, "det", lerp(0.5, 0.8, eo(k / 0.4)), arms=(60, -60))
        if t < b1["start"]:
            k = t - b0["start"]
            paste_c(img, pill("KIRAYA: -Rs 30", 58, RED, WHITE), W / 2, 330, eob((k - 0.5) / 0.3), rot=-3)
        if b1["start"] <= t < va["start"]:
            k = t - b1["start"]
            paste_c(img, pill("BUS FULL… LATAK KE!", 56, YEL), W / 2, 330, eob(k / 0.3), rot=3)
            paste_c(img, emoji("😬", 100), 940, 560, eob((k - 0.2) / 0.3))
        if va["start"] - 0.2 < t < va["end"] + 0.3:
            kin = eob((t - va["start"] + 0.2) / 0.3) * (1 - eo((t - va["end"]) / 0.3) if t > va["end"] else 1)
            call_inset(img, "A", 540, 470, t, "happy", ((240, 210, 170), (210, 170, 130)), "AMMI • VOICE NOTE", kin * 0.85, arms=(-20, -100))
            if t > va["start"] + 1.2: paste_c(img, emoji("🤲", 90), 820, 330, eob((t - va["start"] - 1.2) / 0.3))
        if b2["start"] <= t < vh["start"] + 1.2:
            k = t - b2["start"]
            paste_c(img, glow_text("JAM!", "Anton-Regular.ttf", 160, WHITE, (230, 60, 70)), W / 2, 300, eob(k / 0.25) * (1 + 0.04 * math.sin(t * 16)), rot=-4)
            paste_c(img, pill("8:40 AM", 50, YEL), W / 2, 470, eob((k - 0.2) / 0.3))
            clock(img, 160, 620, 8 + 40 / 60)
    else:
        img.alpha_composite(bg_road("day"))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 14, 300, 1350); img.alpha_composite(lay)
        k = t - b3["start"]
        draw_char(img, "H", 540 + 20 * math.sin(t * 12), 1000 - abs(math.sin(t * 12)) * 30, t, "det", 1.0, arms=(-60 + 50 * math.sin(t * 12), 60 - 50 * math.sin(t * 12)))
        dust(img, 300, 1330, t, 3)
        paste_c(img, pill("BHAAG HAMID BHAAG!", 58, YEL), W / 2, 330, eob(k / 0.3), rot=-3)
        clock(img, 170, 520, 8 + 40 / 60 + 10 / 60 * eio(k / 1.2)); paste_c(img, pill("8:50", 40, RED, WHITE), 170, 650, 1.0)

def sc_gate11(img, t, lt):
    img.alpha_composite(bg_center("day"))
    b0, b1, vh, b2 = L("gate11")
    hx = lerp(-200, 260, eo((t - b0["start"]) / 0.6))
    guard_char(img, 560, 1000, t, 0.9, arm_up=t < b1["start"] + 0.5)
    mood = "det" if t < b0["start"] + 0.6 else ("shock" if t < b2["start"] else "sad")
    draw_char(img, "H", hx, 1010, t, mood, 0.88, arms=(-20, 110) if t > b1["start"] else (-20, 20), hold=hold_phone if t > b1["start"] else None)
    if t < b0["start"] + 1.0:
        for j in range(3): paste_c(img, emoji("💦", 50), hx + 120 + j * 30, 720 - ((t * 2 + j * 0.3) % 1) * -60, 1.0)
    if b0["start"] + 0.3 < t < vh["start"]:
        paste_c(img, bubble([("ADMIT CARD KA", INK), ("PRINT DIKHAO!", RED)], 46, tail="right"), 650, 520, eob((t - b0["start"] - 0.3) / 0.3))
    if b1["start"] < t < vh["start"] + 0.2:
        k = t - b1["start"]
        paste_c(img, pill("SIRF PHONE PE HAI…", 46, WHITE), 330, 230, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("👉", 90), 900, 820, eob((k - 0.4) / 0.3) * (1 + 0.1 * math.sin(t * 10)), rot=180)
    if vh["start"] < t < b2["start"]:
        k = t - vh["start"]
        paste_c(img, pill("PRINT: Rs 20", 54, YEL), 760, 210, eob(k / 0.3), rot=3)
        paste_c(img, pill("JEB: Rs 10", 54, RED, WHITE), 320, 300, eob((k - 0.6) / 0.3), rot=-3)
    if t > b2["start"]:
        k = t - b2["start"]
        clock(img, 900, 580, 8 + 55 / 60)
        paste_c(img, glow_text("5 MINUTE BAAQI!", "Anton-Regular.ttf", 110, WHITE, (230, 60, 70)), W / 2, 230, eob(k / 0.3) * (1 + 0.03 * math.sin(t * 14)), rot=-3)

def sc_kid11(img, t, lt):
    img.alpha_composite(bg_center("day"))
    b0, b1, vh, b2 = L("kid11")
    guard_char(img, 560, 1000, t, 0.9, arm_up=t < b2["start"] + 0.3)
    kx = lerp(1300, 880, eo((t - b0["start"]) / 0.7))
    given = t > b1["start"] + 0.5
    draw_char(img, "H", 260, 1010, t, "sad" if t < b0["start"] + 0.5 else ("shock" if not given else "happy"), 0.88, arms=(-20, 20) if not given else (-20, 90))
    draw_char(img, "Z", kx, 1100, t, "happy", 0.7, arms=(-20, -100) if t < b1["start"] else (-90, 20))
    if t < b1["start"]:
        paste_c(img, bubble([("BHAIYAAA!", (230, 130, 50))], 54, tail="right"), kx - 120, 640, eob((t - b0["start"] - 0.2) / 0.3))
    if b1["start"] <= t < vh["start"] + 0.3:
        k = t - b1["start"]
        paste_c(img, emoji("🪙", 80), lerp(kx - 120, 400, eo(k / 0.5)), 1050 - 120 * math.sin(min(1, k / 0.5) * math.pi), 1.0)
        paste_c(img, pill("+Rs 10", 64, GRN, WHITE), W / 2, 230, eob((k - 0.4) / 0.3), rot=-3)
    if t > vh["start"] and t < b2["start"]:
        bt = word_t(vh, "biscuit", vh["start"] + 1.3)
        paste_c(img, pill("WOHI BACHA!", 58, (230, 130, 50), WHITE), W / 2, 200, eob((t - vh["start"]) / 0.3), rot=3)
        if t > bt - 0.1:
            paste_c(img, pill("BISCUIT KA BADLA", 50, YEL), W / 2, 300, eob((t - bt + 0.1) / 0.3), rot=-3)
            paste_c(img, emoji("💛", 90), kx, 760, eob((t - bt) / 0.3) * (1 + 0.08 * math.sin(t * 6)))
    if t > b2["start"]:
        k = t - b2["start"]
        paste_c(img, admit_card(), 300, 640, eob(k / 0.3) * 0.95, rot=-5)
        clock(img, 900, 580, 8 + 59 / 60); paste_c(img, pill("8:59", 44, YEL), 900, 710, 1.0)
        paste_c(img, glow_text("ANDAR!", "Anton-Regular.ttf", 150, YEL, (40, 190, 110)), W / 2, 260, eob((k - 0.3) / 0.3), rot=-3)

def sc_hall11(img, t, lt):
    b0, b1, b2, vh, b3, b4 = L("hall11")
    dark = b2["start"] < t
    img.alpha_composite(bg_hall())
    fan(img, 540, 160, t if not dark else 1.0, (120, 120, 130))
    cnt = (0 if t < b1["start"] else 24 * eio((t - b1["start"]) / 1.1)) if t < vh["start"] else (24 + 8 * eio((t - vh["start"]) / 1.5) if t < b3["start"] else (32 + 18 * eio((t - b3["start"]) / 1.1)))
    if dark:   # blackout + window light on Hamid's desk
        img.alpha_composite(Image.new("RGBA", (W, H), (10, 10, 30, int(170 * eo((t - b2["start"]) / 0.2)))))
        if t > vh["start"]:
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).polygon([(40, 300), (240, 300), (900, 1300), (200, 1400)], fill=(255, 240, 190, 70))
            img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
            ImageDraw.Draw(img).rectangle([40, 300, 240, 700], fill=(200, 230, 250), outline=INK, width=8)
    hx = 540 if t < vh["start"] else lerp(540, 420, eo((t - vh["start"]) / 0.6))
    mood = "det" if t < b2["start"] else ("shock" if t < vh["start"] else "det")
    wr = math.sin(t * 18) * 15 if (b1["start"] < t < b2["start"] or t > vh["start"]) and t < b4["start"] else 0
    draw_char(img, "H", hx, 1000, t, mood, 0.95, arms=(-30, -40 + wr))
    front_desk(img); paste_c(img, answer_sheet(int(cnt)), 640, 1225, 0.62, rot=-2)
    clock(img, 900, 680, 9 + 50 / 60 * eio((t - b0["start"]) / (b4["start"] - b0["start"] + 0.5)))
    paste_c(img, pill(f"{int(cnt)}/50", 56, GRN if cnt >= 50 else WHITE, WHITE if cnt >= 50 else INK), 900, 830, 1.0)
    if t < b1["start"]: paste_c(img, pill("PAPER SHURU!", 56, YEL), W / 2, 620, eob((t - b0["start"] - 0.2) / 0.3), rot=-3)
    if b1["start"] < t < b2["start"]: paste_c(img, emoji("✍️", 100), 760, 1130, 1.0, rot=10 * math.sin(t * 14))
    if b2["start"] < t < vh["start"] + 0.3:
        k = t - b2["start"]
        paste_c(img, glow_text("BIJLI GAYI!", "Anton-Regular.ttf", 140, WHITE, (230, 60, 70)), W / 2, 420, eob(k / 0.25) * (1 + 0.04 * math.sin(t * 16)), rot=-4)
        paste_c(img, pill("PANKHA BAND • ANDHERA", 46, RED, WHITE), W / 2, 580, eob((k - 0.3) / 0.3), rot=3)
    if b3["start"] < t < b4["start"]:
        k = t - b3["start"]
        paste_c(img, pill("KHIDKI KI ROSHNI", 54, YEL), W / 2, 420, eob(k / 0.3), rot=-3)
        for j in range(3): paste_c(img, emoji("💦", 50), hx - 120 + j * 110, 760 + ((t * 1.5 + j * 0.33) % 1) * 80, 1.0)
    if t > b4["start"]:
        k = t - b4["start"]
        paste_c(img, glow_text("TIME UP!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 420, eob(k / 0.25), rot=-3)
        paste_c(img, emoji("🔔", 100), 860, 470, eob((k - 0.1) / 0.3), rot=15 * math.sin(t * 20))

def sc_end11(img, t, lt):
    img.alpha_composite(bg_center("day"))
    vt, vh, b0, v, b1 = L("end11")
    draw_char(img, "T", 790, 990, t, "happy" if t > vh["end"] else "n", 0.92, arms=(-20, 20) if t < b0["start"] else (-140, 20))
    draw_char(img, "H", 300, 1010, t, "sad" if t < vh["start"] else "happy", 0.9, arms=(-20, 20))
    if t < vh["start"]: paste_c(img, pill("PAPER KHATAM", 50, YEL), W / 2, 230, eob((t - vt["start"]) / 0.3), rot=-3)
    if vh["start"] < t < b0["start"]:
        paste_c(img, emoji("💪", 100), 300, 680, eob((t - vh["start"] - 0.5) / 0.3))
    if b0["start"] < t < v["start"] - 0.2:
        k = t - b0["start"]
        paste_c(img, pill("RESULT: SHAAM 6 BAJE", 50, (150, 50, 70), WHITE), W / 2, 230, eob(k / 0.3), rot=3)
        paste_c(img, emoji("🤞", 90), 560, 760, eob((k - 0.3) / 0.3))
    if t > v["start"] - 0.2:
        paste_c(img, glow_text("AAJ BHI BACH GAYE", "Anton-Regular.ttf", 100, WHITE, (40, 190, 110)), W / 2, 240, eob((t - v["start"] + 0.2) / 0.3), rot=-3)
    if t > b1["start"]:
        paste_c(img, pill("JEB: Rs 0 • TEST: DE DIYA", 46, WHITE, INK), W / 2, 1300, eob((t - b1["start"]) / 0.3), rot=-2)

def sc_cliff11(img, t, lt):
    img.alpha_composite(bg_center("day")); img.alpha_composite(Image.new("RGBA", (W, H), (120, 60, 40, 90)))
    b0, b1, v, b2, vo = L("cliff11")
    hl = t > b1["start"]
    paste_c(img, notice_board(hl), 600, 700, eob((t - b0["start"]) / 0.35) * 0.95)
    draw_char(img, "H", 220, 1150, t, "n" if t < b1["start"] else "shock", 0.75, arms=(-20, -150) if t < b1["start"] + 0.3 else (-20, 20))
    if t < v["start"]: paste_c(img, pill("SHAAM 6 BAJE", 40, YEL), 880, 1180, 1.0)
    if t < b1["start"]:
        fy = 520 + 180 * eio((t - b0["start"] - 0.3) / 0.9)
        paste_c(img, emoji("👆", 90), 900, fy, 1.0, rot=90)
    if hl and t < vo["start"] - 0.15:
        k = t - b1["start"]
        paste_c(img, glow_text("89%?!", "Anton-Regular.ttf", 170, YEL, (230, 60, 70)), W / 2, 230, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
        if t > v["start"]:
            k2 = t - v["start"]
            paste_c(img, pill("SHART: 90%", 56, WHITE, (150, 50, 70)), 560, 1180, eob(k2 / 0.3), rot=3)
            paste_c(img, pill("Rs 1,000 KARZA?", 56, RED, WHITE), 640, 1300, eob((k2 - 0.5) / 0.3), rot=-3)
        if t > b2["start"]: paste_c(img, emoji("😨", 110), 400, 1000, eob((t - b2["start"]) / 0.3))

# ======================= DAY 12: Ek Number Kam (karza + no bike, Rauf's day shift, chase, Saleem's tuition deal, bike back, recheck call)
def hold_notes550(img, x, y, sc): paste_c(img, notes_img(550, 200), x + 130 * sc, y + 200 * sc, sc * 0.9, rot=-8)
def hold_notes450(img, x, y, sc): paste_c(img, notes_img(450, 200), x + 130 * sc, y + 200 * sc, sc * 0.9, rot=-8)
def stamp(img, txt, x, y, k, col=RED, rot=-10, size=120):
    f = fnt("Anton-Regular.ttf", size); tw = int(f.getlength(txt)) + 80
    st = Image.new("RGBA", (tw, size + 100), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([10, 10, tw - 10, size + 90], radius=24, fill=(255, 255, 255, 220), outline=col, width=14)
    sd.text((tw / 2, (size + 100) / 2), txt, font=f, fill=col, anchor="mm")
    paste_c(img, st, x, y, eob(k / 0.25) * (1.4 - 0.4 * eo(k / 0.25)), rot=rot)

def sc_hook12(img, t, lt):
    img.alpha_composite(bg_center("day")); img.alpha_composite(Image.new("RGBA", (W, H), (120, 60, 40, 70)))
    v, b = L("hook12")
    paste_c(img, notice_board(True), 600, 760, 0.8)
    draw_char(img, "H", 200, 1150, t, "shock", 0.75, arms=(-20, 20))
    paste_c(img, glow_text("89%", "Anton-Regular.ttf", 210, YEL, (230, 60, 70)), W / 2, 300, eob((lt - 0.1) / 0.35) * (1 + 0.03 * math.sin(t * 10)), rot=-3)
    ht = word_t(v, "hazaar", v["start"] + 1.4)
    if t > ht - 0.15:
        k = t - ht + 0.15
        paste_c(img, pill("Rs 1,000 KA KARZA!", 60, RED, WHITE), W / 2, 470, eob(k / 0.3), rot=3)
        paste_c(img, emoji("💸", 100), 900, 1180, eob((k - 0.2) / 0.3))
    if t > b["start"]:
        stamp(img, "EK NUMBER KAM", W / 2, 1270, t - b["start"], (150, 50, 70), -6, 100)
        paste_c(img, emoji("😰", 100), 360, 960, eob((t - b["start"] - 0.2) / 0.3))

def sc_msg12(img, t, lt):
    img.alpha_composite(bg_rauf("day"))
    b0, b1, vh, b2 = L("msg12")
    mood = "n" if t < b0["start"] + 0.5 else ("shock" if t < b2["start"] else "sad")
    draw_char(img, "H", 540 if t > vh["start"] else 300, 1010, t, mood, 0.9, arms=(-20, 110) if t < b2["start"] else (-20, 20), hold=hold_phone if t < b2["start"] else None)
    if t < vh["start"]:
        rows = [("SHART YAAD HAI?", INK), ("Rs 1,000 WAPAS…", RED), ("…ITWAAR TAK", (150, 50, 70))]
        c1 = phone_card("MASTER SALEEM", rows, b0["start"] + 0.15, t, (150, 50, 70), 620)
        if t < b1["start"]: paste_c(img, c1, 700, 640, eob((t - b0["start"] - 0.05) / 0.3) * 0.95, rot=3)
        else:
            rows2 = [("BIKE KE BINA DUTY NAHI!", INK), ("KAL TAK BIKE LAO…", RED), ("…WARNA NAUKRI KHATAM", RED)]
            paste_c(img, phone_card("TEZ DELIVERY", rows2, b1["start"] + 0.15, t, (40, 90, 200), 660), 700, 680, eob((t - b1["start"] - 0.05) / 0.3) * 0.95, rot=-3)
            paste_c(img, emoji("📳", 90), 250, 560, 1.0, rot=10 * math.sin(t * 30))
    elif t < b2["start"]:
        k = t - vh["start"]
        paste_c(img, pill("KARZA", 64, (150, 50, 70), WHITE), 230, 540, eob(k / 0.3), rot=-6)
        paste_c(img, pill("NAUKRI", 64, (40, 90, 200), WHITE), 850, 520, eob((k - 0.6) / 0.3), rot=6)
        paste_c(img, emoji("😵", 100), 540, 640, eob((k - 1.0) / 0.3))
    else:
        k = t - b2["start"]
        paste_c(img, pill("KARZA      Rs 1,000", 50, WHITE), W / 2, 470, eob(k / 0.3), rot=-2)
        paste_c(img, pill("+ JURMANA  Rs 450", 50, WHITE, RED), W / 2, 565, eob((k - 0.25) / 0.3), rot=2)
        paste_c(img, glow_text("= Rs 1,450", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 690, eob((k - 0.5) / 0.3), rot=-3)
        paste_c(img, pill("JEB: Rs 0", 56, RED, WHITE), 860, 860, eob((k - 0.8) / 0.3), rot=4)

def sc_rauf12(img, t, lt):
    img.alpha_composite(bg_rauf("day"))
    b0, vr, b1, b2, b3 = L("rauf12")
    loud = vr["start"] < t < vr["end"]
    rush = t > b1["start"]
    if rush:   # customer at a table on the right (he will run later)
        d = ImageDraw.Draw(img)
        draw_char(img, "K", 880, 1060, t, "happy", 0.7, arms=(-20, -60))
        d.rectangle([720, 1180, 1060, 1215], fill=(160, 110, 70), outline=INK, width=6); paste_c(img, cup_img(), 820, 1150, 0.6)
        paste_c(img, emoji("🍛", 70), 950, 1150, 1.0)
    if not rush:
        draw_char(img, "R", 790, 960 + (math.sin(t * 40) * 4 if loud else 0), t, "det", 1.0, arms=(-20, -130) if loud else (-20, 20))
        hx = lerp(-150, 270, eo((t - b0["start"]) / 0.7))
        draw_char(img, "H", hx, 1010, t, "det" if t < vr["start"] else "shock", 0.9, arms=(-20, 20))
        if t < vr["start"]: paste_c(img, bubble([("SETH JI…", INK), ("DIN KI SHIFT?", RED)], 46, tail="left"), 450, 560, eob((t - b0["start"] - 0.3) / 0.3))
        if t > vr["start"]:
            k = t - vr["start"]
            paste_c(img, pill("DIN KI SHIFT: Rs 500", 52, YEL), W / 2, 480, eob(k / 0.3), rot=-3)
            tt = word_t(vr, "toota", vr["start"] + 2.2)
            if t > tt - 0.1: paste_c(img, pill("TOOTA = KATEGA!", 50, RED, WHITE), W / 2, 600, eob((t - tt + 0.1) / 0.3) * (1 + 0.04 * math.sin(t * 16)), rot=3)
    else:
        wob = 0 if t < b2["start"] or t > b3["start"] else 14 * math.sin(t * 18)
        hx = 330 + 60 * math.sin(t * 3.2) if t < b2["start"] else 330
        draw_char(img, "H", hx, 1010, t, "det" if t < b2["start"] else ("shock" if t < b3["start"] else "happy"), 0.9, arms=(-20, -110))
        tray_cups(img, hx + 10 + wob, 590 + abs(wob) * 0.5, 0.9, 6)
        if t < b2["start"]:
            k = t - b1["start"]
            paste_c(img, glow_text("LUNCH RUSH!", "Anton-Regular.ttf", 130, WHITE, (230, 120, 40)), W / 2, 490, eob(k / 0.25), rot=-3)
            for j, e in enumerate(("🍛", "☕", "🫓")): paste_c(img, emoji(e, 70), 700 + j * 130, 620 + 20 * math.sin(t * 6 + j), eob((k - 0.2 - j * 0.15) / 0.3))
        elif t < b3["start"]:
            k = t - b2["start"]
            paste_c(img, pill("TRAY HIL GAYI!", 60, RED, WHITE), W / 2, 480, eob(k / 0.25) * (1 + 0.05 * math.sin(t * 20)), rot=4)
            paste_c(img, emoji("😬", 100), 580, 760, eob((k - 0.2) / 0.3))
        else:
            k = t - b3["start"]
            paste_c(img, pill("12 TABLE • 40 CHAI", 52, YEL), W / 2, 470, eob(k / 0.3), rot=-3)
            paste_c(img, pill("1 HAMID", 60, (40, 110, 70), WHITE), 760, 580, eob((k - 0.3) / 0.3), rot=3)

def sc_chase12(img, t, lt):
    b0, vr, b1, vh, b2, b3, b4, b5 = L("chase12")
    if t < b1["start"]:
        img.alpha_composite(bg_rauf("day"))
        kx = lerp(880, 1300, eio((t - b0["start"] - 0.4) / 0.7))
        draw_char(img, "K", kx, 1010, t, "det", 0.85, arms=(60, -60))
        d = ImageDraw.Draw(img); d.rectangle([720, 1180, 1060, 1215], fill=(160, 110, 70), outline=INK, width=6)
        paste_c(img, pill("BILL: Rs 300", 50, WHITE, INK), 880, 1110, 1.0, rot=-4)
        loud = vr["start"] < t < vr["end"]
        if t > vr["start"] - 0.3:
            rx = lerp(-200, 260, eo((t - vr["start"] + 0.3) / 0.4))
            draw_char(img, "R", rx, 960 + (math.sin(t * 40) * 4 if loud else 0), t, "det", 0.95, arms=(-20, -130) if loud else (-20, 20))
            draw_char(img, "H", 560, 1010, t, "shock", 0.85, arms=(-20, 20))
        else:
            draw_char(img, "H", 330, 1010, t, "shock", 0.88, arms=(-20, -110)); tray_cups(img, 340, 640, 0.9, 6)
        if t < vr["start"]:
            k = t - b0["start"]
            paste_c(img, glow_text("BINA PAISE?!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 500, eob((k - 0.4) / 0.25), rot=-3)
            paste_c(img, emoji("🏃", 100), 960, 760, eob((k - 0.5) / 0.3))
        else:
            k = t - vr["start"]
            paste_c(img, pill("Rs 300 TERE KATENGE!", 52, RED, WHITE), W / 2, 470, eob(k / 0.3), rot=-3)
            paste_c(img, glow_text("-Rs 300?", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), W / 2, 600, eob((k - 0.6) / 0.3), rot=3)
        return
    img.alpha_composite(bg_road("day"))
    if t < b4["start"]:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 14, 300, 1350); img.alpha_composite(lay)
        jump = 0
        if b2["start"] < t < b3["start"]:
            jk = (t - b2["start"] - 0.35) / 0.6
            if 0 < jk < 1: jump = 220 * math.sin(jk * math.pi)
        run = math.sin(t * 13)
        draw_char(img, "K", 860 + 15 * math.sin(t * 11), 1030 - abs(math.sin(t * 11)) * 25, t, "shock", 0.72, arms=(-60 + 50 * run, 60 - 50 * run))
        draw_char(img, "H", 330 + 15 * run, 1010 - abs(run) * 30 - jump, t, "det" if t < b3["start"] else "shock", 0.9, arms=(-60 + 50 * run, 60 - 50 * run))
        dust(img, 200, 1330, t, 3)
        if t < vh["start"]: paste_c(img, glow_text("PAKRO!!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 330, eob((t - b1["start"]) / 0.25), rot=-4)
        if vh["start"] <= t < b2["start"]:
            paste_c(img, pill("POORA BAZAAR…", 56, WHITE), W / 2, 300, eob((t - vh["start"]) / 0.3), rot=3)
        if b2["start"] <= t < b3["start"]:
            k = t - b2["start"]
            gx = lerp(1250, -200, k / 1.3)
            paste_c(img, emoji("🐐", 200), gx, 1230, 1.0)
            paste_c(img, pill("BAKRI!", 70, YEL), W / 2, 300, eob(k / 0.25), rot=-4)
            if k > 0.5: paste_c(img, pill("JUMP!", 56, GRN, WHITE), W / 2, 430, eob((k - 0.5) / 0.25), rot=4)
        if t >= b3["start"]:
            k = t - b3["start"]
            paste_c(img, emoji("🩴", 110), lerp(330, 700, k / 1.1), 1300 - 500 * math.sin(min(1, k / 1.1) * math.pi), 1.0, rot=k * 500)
            paste_c(img, pill("CHAPPAL GAYI!", 62, RED, WHITE), W / 2, 300, eob(k / 0.25), rot=-3)
            paste_c(img, emoji("😂", 90), 900, 560, eob((k - 0.3) / 0.3))
    else:
        d = ImageDraw.Draw(img)   # bus stop
        d.rectangle([600, 760, 1060, 800], fill=(40, 110, 70), outline=INK, width=6); d.rectangle([620, 800, 640, 1180], fill=(90, 90, 100)); d.rectangle([1020, 800, 1040, 1180], fill=(90, 90, 100))
        d.text((830, 780), "BUS STOP", font=fnt("Anton-Regular.ttf", 34), fill=WHITE, anchor="mm")
        draw_char(img, "K", 820, 1020, t, "sad" if t < b5["start"] else "happy", 0.88, arms=(-20, 20) if t < b5["start"] else (-20, -100))
        draw_char(img, "H", 330, 1010, t, "det" if t < b5["start"] else "happy", 0.9, arms=(-20, 90))
        for j in range(3): paste_c(img, emoji("💦", 50), 450 + j * 30, 700 - ((t * 2 + j * 0.3) % 1) * -60, 1.0)
        if t < b5["start"]:
            k = t - b4["start"]
            paste_c(img, bubble([("ANKAL… BILL?", RED)], 50, tail="left"), 360, 520, eob(k / 0.3))
            paste_c(img, bubble([("ARRE! JALDI MEIN", INK), ("BHOOL GAYA!", INK)], 44, tail="right"), 760, 380, eob((k - 0.5) / 0.3))
        else:
            k = t - b5["start"]
            paste_c(img, notes_img(350, 200), lerp(760, 470, eo(k / 0.5)), 760, 0.9, rot=-6)
            paste_c(img, pill("Rs 300 + Rs 50 TIP", 56, GRN, WHITE), W / 2, 330, eob((k - 0.3) / 0.3), rot=-3)
            paste_c(img, glow_text("PAKRA!", "Anton-Regular.ttf", 120, YEL, (40, 190, 110)), W / 2, 470, eob((k - 0.1) / 0.25), rot=3)

def sc_paid12(img, t, lt):
    img.alpha_composite(bg_rauf("night")); bulb_glow(img, 70)
    b0, b1 = L("paid12")
    draw_char(img, "R", 790, 960, t, "happy", 1.0, arms=(-20, -100) if t < b1["start"] else (-140, 20))
    draw_char(img, "H", 300, 1010, t, "happy", 0.9, arms=(-20, 90), hold=hold_notes550)
    paste_c(img, pill("SHIFT Rs 500 + TIP Rs 50", 50, GRN, WHITE), W / 2, 480, eob((t - b0["start"]) / 0.3), rot=-3)
    paste_c(img, emoji("🩴", 70), 220, 1340, 1.0, rot=20)
    if t > b1["start"]:
        paste_c(img, bubble([("BHAAG BHI LETA HAI…", INK), ("KAL BHI AANA!", GRN)], 44, tail="right"), 680, 640, eob((t - b1["start"]) / 0.3))

def sc_saleem12(img, t, lt):
    img.alpha_composite(bg_troom())
    b0, vh, vt, b1, v, b2 = L("saleem12")
    draw_char(img, "T", 780, 1000, t, "n" if t < vt["start"] else "happy", 0.92, arms=(-20, 20) if t < b1["start"] else (-140, 20))
    give = t < vt["start"] + 0.5
    hx = lerp(-150, 300, eo((t - b0["start"]) / 0.6))
    draw_char(img, "H", hx, 1010, t, "sad" if t < vt["start"] else ("shock" if t < b1["start"] else "happy"), 0.92, arms=(-20, 90) if give else (-20, 20), hold=hold_notes550 if give else None)
    if t < vh["start"]: paste_c(img, pill("MASTER SAHAB KA GHAR", 48, (150, 50, 70), WHITE), W / 2, 260, eob((t - b0["start"]) / 0.3), rot=-3)
    if vh["start"] <= t < vt["start"]:
        paste_c(img, pill("Rs 550 / Rs 1,000", 56, YEL), W / 2, 260, eob((t - vh["start"]) / 0.3), rot=3)
    if vt["start"] <= t < b1["start"]:
        k = t - vt["start"]
        paste_c(img, pill("PAISE RAKHO!", 60, GRN, WHITE), W / 2, 260, eob(k / 0.3), rot=-3)
        pt = word_t(vt, "parhao", vt["start"] + 2.6)
        if t > pt - 0.6: paste_c(img, pill("MOHALLE KE BACHE • ROZ SHAAM", 42, WHITE, (150, 50, 70)), W / 2, 380, eob((t - pt + 0.6) / 0.3), rot=2)
    if t >= b1["start"]:
        k = t - b1["start"]
        c = Image.new("RGBA", (760, 260), (0, 0, 0, 0)); cd = ImageDraw.Draw(c)
        cd.rounded_rectangle([0, 0, 759, 259], radius=28, fill=(252, 250, 240), outline=INK, width=8)
        cd.text((380, 80), "10 DIN TUITION", font=fnt("Anton-Regular.ttf", 80), fill=(150, 50, 70), anchor="mm")
        cd.text((380, 180), "= KARZA KHATAM", font=fnt("Anton-Regular.ttf", 80), fill=GRN, anchor="mm")
        paste_c(img, c, W / 2, 330, eob(k / 0.3) * 0.95, rot=-2)
        paste_c(img, emoji("🤝", 110), W / 2, 560, eob((k - 0.3) / 0.3))
    if t >= b2["start"]:
        paste_c(img, emoji("📚", 100), 160, 640, eob((t - b2["start"]) / 0.3), rot=-10)
        paste_c(img, pill("KAL SE CLASS!", 50, YEL), 300, 760, eob((t - b2["start"] - 0.2) / 0.3), rot=-4)

def sc_ghafoor12(img, t, lt):
    img.alpha_composite(bg_ghafoor("day"))
    b0, vg, b1, v, b2 = L("ghafoor12")
    if t < b1["start"]:
        paste_c(img, bike_img(True), 760, 1290, 0.55)
        draw_char(img, "G", 790, 990, t, "n" if t < vg["start"] else "happy", 0.92, arms=(-20, 20) if t < vg["start"] else (-20, -120))
        hx = lerp(-200, 300, eo((t - b0["start"]) / 0.5))
        paid = t > b0["start"] + 0.9
        draw_char(img, "H", hx, 1000, t, "det", 0.9, arms=(-20, 90) if not paid else (-20, 20), hold=hold_notes450 if not paid else None)
        if t < vg["start"]:
            paste_c(img, pill("JURMANA: Rs 450", 56, RED, WHITE), W / 2, 300, eob((t - b0["start"] - 0.2) / 0.3), rot=-3)
            if paid: stamp(img, "PAID", W / 2, 470, t - b0["start"] - 0.9, GRN, -8, 110)
        else:
            k = t - vg["start"]
            paste_c(img, emoji("🔑", 100), lerp(700, 380, eo(k / 0.6)), 760 - 120 * math.sin(min(1, k / 0.6) * math.pi), 1.0, rot=k * 300)
            kt = word_t(vg, "kiraya", vg["end"] - 0.8)
            if t > kt - 0.1: paste_c(img, pill("KIRAYA: Rs 100 ROZ", 50, YEL), W / 2, 300, eob((t - kt + 0.1) / 0.3), rot=3)
    else:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 8, 300, 1000); img.alpha_composite(lay)
        ride(img, 560, 1230, t, "happy", 1.0, dent=True)
        k = t - b1["start"]
        if t < v["start"]:
            paste_c(img, pill("BIKE WAPAS!", 64, GRN, WHITE), W / 2, 300, eob(k / 0.3), rot=-3)
            paste_c(img, pill("NAUKRI BACH GAYI", 54, YEL), W / 2, 420, eob((k - 0.3) / 0.3), rot=3)
        else:
            paste_c(img, glow_text("AAJ BHI BACH GAYE", "Anton-Regular.ttf", 100, WHITE, (40, 190, 110)), W / 2, 300, eob((t - v["start"]) / 0.3), rot=-3)
        if t > b2["start"]:
            paste_c(img, pill("JEB: Rs 100 • KARZA: TUITION SE", 40, WHITE, INK), W / 2, 440, eob((t - b2["start"]) / 0.3), rot=-2)

def sc_cliff12(img, t, lt):
    img.alpha_composite(bg_room("night"))
    b0, va, b1, b2, v, b3, vo = L("cliff12")
    d = ImageDraw.Draw(img); d.rectangle([80, 1230, 620, 1290], fill=(160, 110, 70), outline=INK, width=6)
    if t < v["start"]: clock(img, 900, 230, 11.75 if t < b2["start"] else 12.0)
    if t < b2["start"]:
        draw_char(img, "H", 330, 1030, t, "sad", 0.9, arms=(-20, 110), hold=hold_phone)
        if t < va["start"]: paste_c(img, pill("RAAT 11:45", 50, YEL), W / 2, 260, eob((t - b0["start"]) / 0.3), rot=-3)
        if va["start"] - 0.2 < t < b1["start"] + 0.2:
            kin = eob((t - va["start"] + 0.2) / 0.3)
            call_inset(img, "A", 720, 640, t, "happy", ((240, 210, 170), (210, 170, 130)), "AMMI • VOICE NOTE", kin * 0.8, arms=(-20, -100))
        if t > b1["start"]:
            k = t - b1["start"]
            paste_c(img, pill('"AMMI, 89%…"', 52, WHITE, INK), W / 2, 260, eob(k / 0.3), rot=-3)
            if k > 0.6: stamp(img, "DELETE", W / 2, 400, k - 0.6, RED, 6, 90)
            paste_c(img, emoji("😔", 90), 560, 700, eob((k - 0.3) / 0.3))
    else:
        up = t > v["start"]
        draw_char(img, "H", 330, 1030 - (40 if up else 0), t, "shock", 0.9, arms=(-20, 110), hold=hold_phone)
        rows = [("AAPKI COPY RECHECK HUI…", INK), ("SAWAAL 37 MEIN GHALTI", RED), ("NAYA RESULT: ??%", (150, 50, 70))]
        paste_c(img, phone_card("SCHOLARSHIP OFFICE", rows, b2["start"] + 0.3, t, (40, 90, 160), 660), 680, 620, eob((t - b2["start"]) / 0.3) * 0.92, rot=3)
        if t < b2["start"] + 0.8: paste_c(img, emoji("📳", 90), 560, 870, 1.0, rot=12 * math.sin(t * 30))
        if up:
            k = t - v["start"]
            paste_c(img, glow_text("89% → ??%", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 250, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
        if t > b3["start"]: paste_c(img, emoji("😳", 110), 560, 900, eob((t - b3["start"]) / 0.3))


# ======================= DAY 13: Asli Certificate (90% -> scholarship, original certificate in Lahore, Bilal's bus scheme, dummy phone)
@lru_cache(None)
def lifafa_img(open_=False):
    c = Image.new("RGBA", (300, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rectangle([6, 50, 294, 214], fill=(215, 180, 120), outline=INK, width=6)
    if open_: d.polygon([(6, 50), (150, -0), (294, 50)], fill=(230, 200, 145), outline=INK)
    else: d.polygon([(6, 50), (150, 140), (294, 50)], fill=(230, 200, 145), outline=INK)
    d.line([(6, 214), (130, 120)], fill=(170, 135, 85), width=4); d.line([(294, 214), (170, 120)], fill=(170, 135, 85), width=4)
    d.text((150, 185), "HAMID • KARACHI", font=fnt("Poppins-Black.ttf", 22), fill=INK, anchor="mm")
    return c
@lru_cache(None)
def cert_img():
    c = Image.new("RGBA", (300, 380), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 299, 379], fill=(252, 248, 230), outline=(150, 110, 40), width=10)
    d.text((150, 60), "CERTIFICATE", font=fnt("Anton-Regular.ttf", 46), fill=(150, 50, 70), anchor="mm")
    d.text((150, 120), "12th CLASS • LAHORE", font=fnt("Poppins-Black.ttf", 22), fill=INK, anchor="mm")
    d.text((150, 200), "HAMID", font=fnt("Anton-Regular.ttf", 56), fill=INK, anchor="mm")
    d.text((150, 265), "82%", font=fnt("Anton-Regular.ttf", 50), fill=GRN, anchor="mm")
    d.ellipse([200, 290, 270, 360], fill=(230, 60, 70), outline=INK, width=4)
    return c
def hold_lifafa(img, x, y, sc): paste_c(img, lifafa_img(False), x + 150 * sc, y + 170 * sc, sc * 0.75, rot=-8)
def plane(img, x, y, rot=0, sc=1.0):
    p = Image.new("RGBA", (160, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    d.polygon([(0, 45), (160, 10), (60, 60)], fill=WHITE, outline=INK); d.polygon([(60, 60), (160, 10), (80, 88)], fill=(220, 225, 235), outline=INK)
    paste_c(img, p, x, y, sc, rot=rot)
def kids(img, t, lt, wild=1.0, laugh=False):
    for j, (who, x, ph) in enumerate((("Z", 150, 0.0), ("K", 400, 1.3), ("Z", 680, 2.1), ("K", 930, 0.7))):
        jump = abs(math.sin(t * 7 + ph)) * 40 * wild
        draw_char(img, who, x, 1180 - jump, t, "happy", 0.5, arms=(-60 - 50 * math.sin(t * 9 + ph) * wild, 60 + 50 * math.sin(t * 8 + ph) * wild), laugh=laugh or wild > 0.5)

def sc_hook13(img, t, lt):
    img.alpha_composite(bg_room("night"))
    v = L("hook13")[0]
    st = word_t(v, "scholarship", v["start"] + 1.2); kt = word_t(v, "bas", v["start"] + 2.4)
    draw_char(img, "H", 330, 1030, t, "happy" if t < kt else "shock", 0.92, arms=(-20, 110), hold=hold_phone)
    rows = [("NAYA RESULT…", INK), ("HAMID: 90%", GRN), ("SCHOLARSHIP: MANZOOR", (40, 90, 160))]
    paste_c(img, phone_card("SCHOLARSHIP OFFICE", rows, v["start"] + 0.1, t, (40, 90, 160), 660), 680, 700, eob((t - v["start"]) / 0.3) * 0.88, rot=3)
    paste_c(img, glow_text("90%!", "Anton-Regular.ttf", 210, YEL, (40, 190, 110)), W / 2, 280, eob((lt - 0.1) / 0.3) * (1 + 0.03 * math.sin(t * 10)), rot=-3)
    if t > st - 0.1 and t < kt: paste_c(img, pill("SCHOLARSHIP PAKKI!", 60, GRN, WHITE), W / 2, 450, eob((t - st + 0.1) / 0.3), rot=3)
    if t > kt - 0.1:
        k = t - kt + 0.1
        stamp(img, "EK KAGHAZ KAM!", W / 2, 460, k, RED, 4, 100)
        paste_c(img, cert_img(), 880, 1110, eob((k - 0.2) / 0.3) * 0.55, rot=10)
        paste_c(img, glow_text("?", "Anton-Regular.ttf", 160, YEL, (230, 60, 70)), 980, 950, eob((k - 0.4) / 0.3), rot=12)

def sc_office13(img, t, lt):
    img.alpha_composite(bg_hall()); front_desk(img, 1190)
    vt, vh, b = L("office13")
    draw_char(img, "T", 760, 960, t, "happy" if t < vh["start"] else "shock", 0.9, arms=(-20, -110) if t < vh["start"] else (-20, 20))
    draw_char(img, "H", 300, 1000, t, "happy" if t < vh["start"] else "shock", 0.9, arms=(-20, 20))
    if t < vh["start"]:
        k = t - vt["start"]
        paste_c(img, pill("MUBARAK! 90%", 60, GRN, WHITE), W / 2, 640, eob(k / 0.3), rot=-3)
        ct = word_t(vt, "certificate", vt["start"] + 2.0)
        if t > ct - 0.3:
            paste_c(img, cert_img(), 820, 560, eob((t - ct + 0.3) / 0.3) * 0.7, rot=6)
            paste_c(img, pill("ASAL CERTIFICATE", 46, (150, 50, 70), WHITE), 760, 790, eob((t - ct) / 0.3), rot=3)
    elif t < b["start"]:
        k = t - vh["start"]
        lt_ = word_t(vh, "lahore", vh["start"] + 1.4)
        paste_c(img, glow_text("ASAL?!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 640, eob(k / 0.25), rot=-3)
        if t > lt_ - 0.1:
            paste_c(img, pill("LAHORE - 1,200 KM - KARACHI", 40, YEL), W / 2, 790, eob((t - lt_ + 0.1) / 0.3), rot=2)
            paste_c(img, emoji("📍", 90), 180, 640, eob((t - lt_) / 0.3))
    else:
        k = t - b["start"]
        paste_c(img, pill("ASAL CERTIFICATE: LAHORE", 44, WHITE, INK), W / 2, 650, 1.0, rot=-2)
        stamp(img, "DEADLINE: KAL 5 BAJE", W / 2, 800, k, RED, -5, 84)
        clock(img, 900, 300, 5.0)

def sc_tuition13(img, t, lt):
    tuition_room(img, t, board=False)
    d = ImageDraw.Draw(img)
    d.rectangle([110, 280, 600, 540], fill=(40, 70, 60), outline=(150, 100, 60), width=12)
    d.text((355, 370), "A B C • 2 + 2", font=fnt("Anton-Regular.ttf", 70), fill=(240, 240, 230), anchor="mm")
    d.text((355, 470), "PEHLI CLASS", font=fnt("Poppins-Black.ttf", 34), fill=YEL, anchor="mm")
    v0, va, vh, b = L("tuition13")
    calm = t > va["start"] - 0.2 and t < b["start"]
    phone = t > va["start"] - 0.3
    draw_char(img, "H", 540, 900, t, "shock" if (t < v0["start"] + 1.4 or t > vh["start"]) else ("sad" if calm else "det"), 0.82,
              arms=(-20, 110) if phone else (-90 - 40 * math.sin(t * 6), 90 + 40 * math.sin(t * 6)), hold=hold_phone if phone else None)
    kids(img, t, lt, 0.35 if calm else 1.0, laugh=t > b["start"])
    if t < va["start"]:
        k = t - v0["start"]
        paste_c(img, pill("10 BACHAY", 60, YEL), 820, 330, eob(k / 0.3), rot=4)
        for j, e in enumerate(("📢", "🥁", "🔊")): paste_c(img, emoji(e, 80), 720 + j * 120, 470 + 18 * math.sin(t * 9 + j), eob((k - 0.6 - j * 0.2) / 0.3), rot=10 * math.sin(t * 12 + j))
        if k > 1.6: paste_c(img, glow_text("SHOR!!", "Anton-Regular.ttf", 110, WHITE, (230, 120, 40)), 820, 640, eob((k - 1.6) / 0.25) * (1 + 0.05 * math.sin(t * 20)), rot=-4)
    elif t < b["start"]:
        call_inset(img, "A", 820, 520, t, "sad", ((240, 210, 170), (210, 170, 130)), "AMMI • LAHORE", eob((t - va["start"] + 0.2) / 0.3) * 0.75, arms=(-20, -100))
        if t > va["start"] + 0.6: paste_c(img, pill("COURIER: 3 DIN", 52, RED, WHITE), 300, 640, eob((t - va["start"] - 0.6) / 0.3), rot=-4)
        if t > vh["start"]:
            paste_c(img, pill("DEADLINE: 1 DIN!", 52, WHITE, (150, 50, 70)), 300, 760, eob((t - vh["start"]) / 0.3), rot=3)
            paste_c(img, emoji("😰", 90), 300, 860, eob((t - vh["start"] - 0.4) / 0.3))
    else:
        k = t - b["start"]
        q = min(1, k / 0.35)
        if q < 1: plane(img, lerp(150, 590, q), lerp(1150, 790, q), rot=30, sc=0.9)
        else:
            plane(img, 610, 760, rot=-40, sc=0.9)
            paste_c(img, glow_text("TAK!", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), 790, 620, eob((k - 0.35) / 0.15), rot=8)
            paste_c(img, emoji("😂", 80), 200, 900, eob((k - 0.35) / 0.2))

def sc_bilal13(img, t, lt):
    img.alpha_composite(bg_room("night"))
    v1, vh, v2 = L("bilal13")
    draw_char(img, "H", 280, 1050, t, "det" if t < vh["start"] else ("det" if t < v2["start"] else "sad"), 0.85, arms=(-20, 110), hold=hold_phone)
    call_inset(img, "L", 760, 620, t, "happy", ((255, 220, 150), (240, 170, 90)), "BILAL • VIDEO CALL", eob((t - v1["start"] + 0.2) / 0.3) * 0.95,
               arms=(-20, -120), laugh=t > v2["start"])
    if t < vh["start"]:
        k = t - v1["start"]
        paste_c(img, pill("BILAL KI SCHEME 3.0", 52, (255, 130, 40), WHITE), W / 2, 250, eob(k / 0.3), rot=-3)
        bt = word_t(v1, "bus", v1["start"] + 1.6)
        if t > bt - 0.2:
            paste_c(img, bus_img(), 560, 1260, eob((t - bt + 0.2) / 0.3) * 0.5, rot=0)
            paste_c(img, pill("RAAT KI BUS • CONDUCTOR COUSIN", 38, YEL), W / 2, 1060, eob((t - bt) / 0.3), rot=2)
    elif t < v2["start"]:
        k = t - vh["start"]
        th = Image.new("RGBA", (420, 300), (0, 0, 0, 0)); ImageDraw.Draw(th).ellipse([0, 0, 419, 299], fill=WHITE, outline=INK, width=6)
        for j, rr in enumerate((-20, 5, 30)): paste_c(th, phone_img(True), 130 + j * 80, 150, 0.8, rot=rr)
        paste_c(img, th, 300, 470, eob(k / 0.3) * 0.9)
        if k > 0.7: stamp(img, "DUMMY!", 300, 300, k - 0.7, RED, -8, 90)
        paste_c(img, emoji("🤨", 90), 470, 820, eob((k - 0.4) / 0.3))
    else:
        k = t - v2["start"]
        paste_c(img, pill("IS BAAR PAKKA!", 56, GRN, WHITE), W / 2, 250, eob(k / 0.3), rot=-3)
        paste_c(img, pill("CHAI-PAANI: Rs 100", 48, WHITE, RED), 330, 420, eob((k - 0.8) / 0.3), rot=3)
        paste_c(img, lifafa_img(False), 560, 1220, eob((k - 1.4) / 0.3) * 0.7, rot=-6)
        paste_c(img, pill("AMMI > BILAL > BUS", 40, YEL), 560, 1090, eob((k - 1.6) / 0.3), rot=2)

def sc_adda13(img, t, lt):
    v1, b, v2 = L("adda13")
    ft = word_t(v2, "full", v2["start"] + 1.0)
    if t < ft - 0.1:
        img.alpha_composite(bg_station("dawn"))
        if t < b["start"]:
            k = t - v1["start"]
            draw_char(img, "H", 540, 1000, t, "det", 0.85, arms=(-20, 20) if (t * 2) % 2 < 1 else (-20, -40))
            clock(img, 880, 560, 4.0 + 0.4 * eio(k / 2.6))
            paste_c(img, pill("AGLE DIN • 4:00 PM", 50, YEL), W / 2, 220, eob(k / 0.3), rot=-3)
            if k > 1.0: paste_c(img, pill("BUS LATE!", 66, RED, WHITE), 300, 600, eob((k - 1.0) / 0.25) * (1 + 0.04 * math.sin(t * 14)), rot=-5)
            paste_c(img, emoji("⏳", 80), 200, 760, eob((k - 0.6) / 0.3))
        else:
            bx = lerp(1500, 600, eo((t - b["start"]) / 0.45)) if t < v2["start"] else 600
            paste_c(img, bus_img(), bx, 1080, 1.0)
            for wx in (-280, 300): wheel(img, bx + wx, 1265, t if t < v2["start"] else 0, 55)
            draw_char(img, "H", 200, 1040, t, "shock" if t < v2["start"] else "happy", 0.75, arms=(-20, 110) if t > v2["start"] else (-20, 20), hold=hold_lifafa if t > v2["start"] else None)
            if t < v2["start"]: stamp(img, "AA GAYI!", W / 2, 360, t - b["start"], GRN, -6, 110)
            else:
                k = t - v2["start"]
                paste_c(img, pill("LIFAFA MILA!", 64, GRN, WHITE), W / 2, 300, eob(k / 0.3), rot=-3)
                paste_c(img, pill("-Rs 100 CHAI-PAANI", 44, WHITE, RED), W / 2, 420, eob((k - 0.3) / 0.3), rot=3)
    else:
        img.alpha_composite(bg_road("day"))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 16, 300, 1350); img.alpha_composite(lay)
        ride(img, 560, 1230, t, "det", 1.0, tilt=4, dent=True)
        dust(img, 260, 1330, t, 3)
        k = t - ft + 0.1
        paste_c(img, glow_text("FULL SPEED!", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 300, eob(k / 0.25), rot=-4)
        paste_c(img, pill("4:35 PM • 25 KM", 50, WHITE, INK), W / 2, 450, eob((k - 0.3) / 0.3), rot=3)

def sc_cliff13(img, t, lt):
    img.alpha_composite(bg_hall()); front_desk(img, 1190)
    vt, vo, b, vd, outro_l = L("cliff13")
    opened = t > vo["start"] + 0.6
    shock = t > b["start"]
    draw_char(img, "T", 780, 960, t, "happy" if not shock else "shock", 0.85, arms=(-20, -110) if t < vo["start"] else (-20, 20))
    draw_char(img, "H", 290, 990, t, "happy" if t < vo["start"] else ("det" if not shock else "shock"), 0.88, arms=(-20, 20))
    if t < vo["start"]:
        clock(img, 900, 300, 4 + 59 / 60)
        k = t - vt["start"]
        paste_c(img, pill("4:59 PM", 70, GRN, WHITE), 380, 300, eob(k / 0.3), rot=-4)
        paste_c(img, glow_text("BILKUL WAQT PAR!", "Anton-Regular.ttf", 100, WHITE, (40, 190, 110)), W / 2, 500, eob((k - 0.6) / 0.3), rot=3)
        paste_c(img, lifafa_img(False), 540, 1170, 0.7, rot=-4)
    else:
        paste_c(img, lifafa_img(opened), 540, 1170, 0.75, rot=-4)
        if not shock:
            k = t - vo["start"]
            paste_c(img, pill("LIFAFA KHOLA…", 60, YEL), W / 2, 330, eob(k / 0.3), rot=-3)
            if k > 1.4: paste_c(img, pill("CERTIFICATE NAHI!", 64, RED, WHITE), W / 2, 470, eob((k - 1.4) / 0.25) * (1 + 0.04 * math.sin(t * 16)), rot=3)
            paste_c(img, glow_text("?", "Anton-Regular.ttf", 160, YEL, (230, 60, 70)), 540, 920, eob((k - 0.8) / 0.3) * (1 + 0.06 * math.sin(t * 8)))
        else:
            k = t - b["start"]
            py = lerp(1150, 760, eo(k / 0.35)); paste_c(img, phone_img(True), 540, py, 1.25, rot=-12 + 6 * math.sin(min(k, 1) * 12) * (1 - min(k, 1)))
            stamp(img, "DUMMY PHONE!", W / 2, 360, k, RED, -6, 100)
            if t > vd["start"]:
                k2 = t - vd["start"]
                bt = word_t(vd, "bilal", vd["start"] + 1.0)
                if t > bt - 0.1: paste_c(img, pill("BILAAAL!!", 70, (255, 130, 40), WHITE), W / 2, 540, eob((t - bt + 0.1) / 0.25) * (1 + 0.05 * math.sin(t * 18)), rot=4)
                paste_c(img, emoji("😱", 100), 160, 700, eob(k2 / 0.3))
                paste_c(img, emoji("📜", 80), 900, 640, eob((k2 - 0.4) / 0.3)); paste_c(img, glow_text("?", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), 960, 580, eob((k2 - 0.5) / 0.3))


# ======================= DAY 14: Dummy Phone (envelopes swapped, Bilal in Karachi, race to the adda, afsar's chai, class vs duty)
@lru_cache(None)
def cert_oily():
    c = cert_img().copy(); o = Image.new("RGBA", c.size, (0, 0, 0, 0)); od = ImageDraw.Draw(o)
    for (x, y, r) in ((70, 300, 46), (230, 150, 34), (120, 90, 26)): od.ellipse([x - r, y - r, x + r, y + r], fill=(200, 150, 40, 110))
    c.alpha_composite(o); return c
def hold_cert(img, x, y, sc): paste_c(img, cert_oily(), x + 150 * sc, y + 170 * sc, sc * 0.55, rot=-8)
def hold_cert_l(img, x, y, sc): paste_c(img, cert_oily(), x - 150 * sc, y + 170 * sc, sc * 0.55, rot=8)
def hold_samosa(img, x, y, sc):
    s = Image.new("RGBA", (130, 120), (0, 0, 0, 0)); ImageDraw.Draw(s).polygon([(6, 112), (65, 6), (124, 112)], fill=(220, 160, 70), outline=INK)
    ImageDraw.Draw(s).line([(6, 112), (65, 6), (124, 112), (6, 112)], fill=INK, width=6)
    paste_c(img, s, x + 150 * sc, y + 150 * sc, sc * 0.9, rot=-10)
def hold_cup(img, x, y, sc): paste_c(img, cup_img(), x + 150 * sc, y + 120 * sc, sc * 0.9); steam(img, x + 150 * sc, y + 60 * sc, 0, 2, 0.4 * sc)
def afsar_door(img, cups=1):
    d = ImageDraw.Draw(img)
    d.rectangle([800, 560, 1060, 1190], fill=(120, 80, 55), outline=INK, width=7)
    d.rounded_rectangle([815, 600, 1045, 680], radius=10, fill=(40, 90, 160), outline=INK, width=4)
    d.text((930, 640), "AFSAR", font=fnt("Anton-Regular.ttf", 50), fill=WHITE, anchor="mm")
    d.ellipse([1010, 860, 1034, 884], fill=YEL, outline=INK, width=3)
    for j in range(cups): paste_c(img, cup_img(), 850 + j * 70, 1150, 0.5)
def signal(img, x, y, red=True):
    d = ImageDraw.Draw(img)
    d.rectangle([x - 12, y + 150, x + 12, y + 520], fill=(60, 60, 70), outline=INK, width=4)
    d.rounded_rectangle([x - 60, y - 160, x + 60, y + 160], radius=24, fill=(30, 30, 38), outline=INK, width=6)
    for j, c in enumerate(((230, 40, 50), (240, 190, 40), (40, 200, 90))):
        on = (j == 0) == red if j != 1 else False
        d.ellipse([x - 40, y - 140 + j * 98, x + 40, y - 60 + j * 98], fill=c if on else mixc(c, (20, 20, 25), 0.75), outline=INK, width=4)
def gauge(img, x, y, k):
    g = Image.new("RGBA", (300, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.pieslice([10, 10, 290, 290], 180, 360, fill=WHITE, outline=INK, width=8)
    d.text((40, 150), "E", font=fnt("Anton-Regular.ttf", 46), fill=RED, anchor="mm"); d.text((260, 150), "F", font=fnt("Anton-Regular.ttf", 46), fill=INK, anchor="mm")
    a = math.pi * (1 - 0.3 * (1 - k)); d.line([(150, 150), (150 + math.cos(a) * 110, 150 - math.sin(a) * 110)], fill=RED, width=10)
    d.ellipse([136, 136, 164, 164], fill=INK)
    paste_c(img, g, x, y, 1.0)

def sc_hook14(img, t, lt):
    img.alpha_composite(bg_hall()); front_desk(img, 1190)
    v0, vt = L("hook14")
    draw_char(img, "T", 790, 960, t, "shock", 0.85, arms=(-20, 20) if t < vt["start"] else (-20, -110))
    draw_char(img, "H", 290, 990, t, "shock", 0.88, arms=(-20, 20))
    paste_c(img, lifafa_img(True), 540, 1170, 0.75, rot=-4)
    paste_c(img, phone_img(True), 540, 760 + 10 * math.sin(t * 3), 1.25, rot=-12)
    dp = word_t(v0, "dummy", v0["start"] + 1.3)
    if t < dp: paste_c(img, glow_text("CERTIFICATE?", "Anton-Regular.ttf", 110, WHITE, (90, 160, 255)), W / 2, 300, eob((lt - 0.05) / 0.25), rot=-3)
    else: stamp(img, "DUMMY PHONE!", W / 2, 300, t - dp, RED, -5, 100)
    et = word_t(v0, "ek", v0["start"] + 2.4, exact=True)
    if t > et - 0.1:
        clock(img, 930, 520, 4 + 59 / 60)
        paste_c(img, pill("4:59 PM • 1 MINUTE!", 50, RED, WHITE), 470, 480, eob((t - et + 0.1) / 0.25) * (1 + 0.04 * math.sin(t * 14)), rot=3)
    if t > vt["start"]:
        k = t - vt["start"]
        paste_c(img, pill("DAFTAR BAND: 5:00", 56, (150, 50, 70), WHITE), 470, 610, eob(k / 0.3), rot=-2)
        paste_c(img, emoji("🔒", 90), 900, 640, eob((k - 0.3) / 0.3))

def sc_call14(img, t, lt):
    img.alpha_composite(bg_hall()); front_desk(img, 1190)
    vl1, vh, vl2, b, vt = L("call14")
    if t < vt["start"]:
        draw_char(img, "H", 280, 1020, t, "shock" if t < vl2["start"] else ("det" if t < b["start"] else "shock"), 0.85,
                  arms=(-20, 110) if t < b["start"] else (-150, 110), hold=hold_phone)
        ks = eob((t - vl1["start"] + 0.2) / 0.3) * 0.95
        call_inset(img, "L", 760, 620, t, "shock" if t < vl2["start"] else "happy", ((150, 200, 240), (255, 200, 150)), "BILAL • VIDEO CALL", ks,
                   arms=(-20, 20), laugh=t > vl2["start"], hold=hold_cert)
        if t < vh["start"]:
            k = t - vl1["start"]
            paste_c(img, pill("LIFAFAY BADAL GAYE!", 54, (255, 130, 40), WHITE), W / 2, 250, eob(k / 0.3), rot=-3)
            if k > 1.6: paste_c(img, pill("CERTIFICATE: BILAL KE PAAS", 40, YEL), W / 2, 1000, eob((k - 1.6) / 0.3), rot=2)
        elif t < vl2["start"]:
            paste_c(img, glow_text("KAHAN?!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 260, eob((t - vh["start"]) / 0.25), rot=-3)
        elif t < b["start"]:
            k = t - vl2["start"]
            paste_c(img, glow_text("SURPRISE!", "Anton-Regular.ttf", 130, YEL, (255, 120, 40)), W / 2, 260, eob(k / 0.25), rot=-3)
            if k > 0.9: paste_c(img, pill("BILAL • KARACHI BUS ADDA", 44, (30, 110, 70), WHITE), W / 2, 1000, eob((k - 0.9) / 0.3), rot=2)
            paste_c(img, emoji("🚌", 90), 180, 560, eob((k - 0.5) / 0.3))
        else:
            k = t - b["start"]
            paste_c(img, emoji("🤦", 170), 300, 640, eob(k / 0.2), rot=-8)
            stamp(img, "BILAAAL!", W / 2, 280, k, (255, 130, 40), 5, 110)
    else:
        k = t - vt["start"]
        afsar_door(img, 1)
        draw_char(img, "T", 640, 960, t, "det", 0.85, arms=(-20, 110), hold=hold_cup)
        hx = lerp(300, -260, eo((k - 1.6) / 0.8)) if k > 1.6 else 300
        draw_char(img, "H", hx, 1000, t, "det", 0.85, arms=(-80, 80) if k > 1.6 else (-20, 20))
        paste_c(img, pill("PLAN: AFSAR KO CHAI", 54, (30, 110, 70), WHITE), W / 2, 260, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("🤫", 90), 470, 560, eob((k - 0.3) / 0.3))
        if k > 1.6: paste_c(img, glow_text("BHAAGO!", "Anton-Regular.ttf", 140, YEL, (230, 60, 70)), W / 2, 420, eob((k - 1.6) / 0.25), rot=4)

def sc_race14(img, t, lt):
    v1, v2, b = L("race14")
    img.alpha_composite(bg_road("day"))
    st = word_t(v2, "signal", v2["start"]) ; pt = word_t(v2, "petrol", v2["start"] + 1.4)
    moving = t < st or (t > st + 0.9 and t < pt)
    if t > st - 0.1: signal(img, 920, 600, red=t < st + 0.9)
    if moving:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 16, 300, 1350); img.alpha_composite(lay); dust(img, 260, 1330, t, 3)
    stopped = t > b["start"]
    ride(img, 520, 1230, t, "det" if t < pt else "shock", 1.0, tilt=4 if moving else 0, dent=True, bounce=moving)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, pill("ADDA: 5 KM", 60, YEL), W / 2, 260, eob(k / 0.3), rot=-3)
        clock(img, 160, 470, 5 + 2 / 60); paste_c(img, pill("5:02", 44, RED, WHITE), 160, 600, 1.0)
        if k > 1.0: paste_c(img, glow_text("FULL SPEED!", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 420, eob((k - 1.0) / 0.25), rot=-4)
    elif t < pt:
        paste_c(img, pill("SIGNAL LAAL!", 64, RED, WHITE), 440, 280, eob((t - st) / 0.25), rot=-4)
    elif not stopped:
        gauge(img, 360, 360, 0.0)
        paste_c(img, pill("PETROL KHATAM!", 64, RED, WHITE), 600, 560, eob((t - pt) / 0.25) * (1 + 0.04 * math.sin(t * 16)), rot=3)
    else:
        k = t - b["start"]
        gauge(img, 360, 360, 0.0)
        paste_c(img, emoji("💨", 130), 180, 1200, eob(k / 0.2))
        paste_c(img, glow_text("PHUT… PHUT…", "Anton-Regular.ttf", 110, WHITE, (120, 120, 140)), W / 2, 580, eob(k / 0.2), rot=-3)

def sc_adda14(img, t, lt):
    img.alpha_composite(bg_station("dawn")); chai_stall(img, t)
    v1, vl, b, vr = L("adda14")
    if t < vr["start"]:
        hx = lerp(-200, 260, eo((t - v1["start"]) / 0.9))
        draw_char(img, "H", hx, 1000, t, "shock" if t < vl["start"] else ("det" if t < b["start"] else "shock"), 0.85,
                  arms=(-70, 70) if t < v1["start"] + 0.9 else (-20, 20), hold=hold_cert_l if t > vl["start"] + 1.0 else None)
        draw_char(img, "L", 640, 1000, t, "happy", 0.85, arms=(-20, 110), hold=hold_samosa if t < vl["start"] + 1.0 else None, laugh=t > vl["start"])
        if t < vl["start"]:
            k = t - v1["start"]
            paste_c(img, pill("5:10 PM • BUS ADDA", 50, YEL), W / 2, 230, eob(k / 0.3), rot=-3)
            st_ = word_t(v1, "samosay", v1["start"] + 2.4)
            if t > st_ - 0.2: paste_c(img, pill("SAMOSA PARTY!", 60, (255, 130, 40), WHITE), 640, 560, eob((t - st_ + 0.2) / 0.25), rot=4); paste_c(img, emoji("😋", 90), 820, 700, eob((t - st_) / 0.3))
        elif t < b["start"]:
            k = t - vl["start"]
            paste_c(img, cert_oily(), 460, 600, eob((k - 0.6) / 0.3) * 0.9, rot=6)
            paste_c(img, pill("ASAL CERTIFICATE!", 50, GRN, WHITE), 460, 330, eob(k / 0.3), rot=-3)
        else:
            k = t - b["start"]
            paste_c(img, cert_oily(), 460, 600, 0.9 + 0.25 * eob(k / 0.25), rot=6)
            stamp(img, "TEL!", 820, 760, k, (200, 140, 30), 8, 110); paste_c(img, emoji("😂", 100), 200, 560, eob((k - 0.1) / 0.2))
    else:
        k = t - vr["start"]
        rx = lerp(1500, 700, eo(k / 0.6))
        paste_c(img, rickshaw_img(), rx, 1110, 0.95)
        draw_char(img, "H", 200, 1000, t, "happy", 0.8, arms=(-20, -120), hold=hold_cert_l)
        draw_char(img, "L", 420, 1020, t, "sad", 0.78, arms=(-20, 20))
        paste_c(img, glow_text("RICKSHAW!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 250, eob(k / 0.25), rot=-3)
        if k > 1.0: paste_c(img, pill("KIRAYA: BILAL", 60, WHITE, (255, 130, 40)), W / 2, 410, eob((k - 1.0) / 0.25), rot=3); paste_c(img, emoji("😭", 90), 420, 700, eob((k - 1.2) / 0.3))

def sc_back14(img, t, lt):
    img.alpha_composite(bg_hall()); front_desk(img, 1190)
    v1, vt, b, va = L("back14")
    cups = 3 if t > v1["start"] + 1.6 else 2
    afsar_door(img, cups)
    draw_char(img, "T", 600, 960, t, "happy" if t > vt["start"] else "det", 0.85, arms=(-20, 110) if t < vt["start"] else (-20, -120), hold=hold_cup if t < vt["start"] else None)
    draw_char(img, "H", 260, 990, t, "happy" if t > vt["start"] else "det", 0.88, arms=(-20, 110), hold=hold_cert if t < b["start"] else None)
    if t < vt["start"]:
        k = t - v1["start"]
        clock(img, 160, 360, 5 + 20 / 60); paste_c(img, pill("5:20 PM", 50, RED, WHITE), 160, 490, eob(k / 0.3))
        if k > 1.6: paste_c(img, pill("CHAI #3", 70, (150, 90, 50), WHITE), 920, 470, eob((k - 1.6) / 0.25) * (1 + 0.05 * math.sin(t * 12)), rot=5); paste_c(img, emoji("☕", 100), 700, 470, eob((k - 1.8) / 0.3))
    elif t < b["start"]:
        k = t - vt["start"]
        paste_c(img, cert_oily(), 450, 1130, 0.6, rot=-5)
        paste_c(img, glow_text("JAMA HO GAYA!", "Anton-Regular.ttf", 120, WHITE, (40, 190, 110)), W / 2, 330, eob(k / 0.25), rot=-3)
    else:
        paste_c(img, cert_oily(), 450, 1130, 0.6, rot=-5)
        k = t - b["start"]
        stamp(img, "SCHOLARSHIP: PAKKI", W / 2, 330, k, GRN, -5, 90)
        if t > va["start"]: paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 520, eob((t - va["start"]) / 0.25), rot=3)
        for j in range(8):
            q = ((t - b["start"]) * 0.8 + j * 0.13) % 1
            paste_c(img, emoji(["🎉", "⭐"][j % 2], 60), 120 + j * 120, 200 + q * 900, 0.9, rot=q * 200)

def sc_cliff14(img, t, lt):
    img.alpha_composite(bg_street("dawn"))
    vl, vh, ol = L("cliff14")
    if t < vh["start"]:
        k = t - vl["start"]
        draw_char(img, "H", 300, 1000, t, "shock", 0.85, arms=(-20, 20))
        draw_char(img, "L", 760, 1000, t, "happy", 0.85, arms=(-20, -130), hold=hold_bag, laugh=True)
        paste_c(img, pill("MAIN BHI YAHIN RAHUNGA!", 50, (255, 130, 40), WHITE), W / 2, 260, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("😅", 100), 300, 640, eob((k - 0.6) / 0.3))
    else:
        k = t - vh["start"]
        draw_char(img, "H", 300, 1030, t, "shock", 0.88, arms=(-20, 110), hold=hold_phone)
        draw_char(img, "L", 860, 1060, t, "shock", 0.7, arms=(-20, 20))
        rows = [("CLASSES SHURU: KAL", INK), ("SUBAH 8 BAJE", RED)]
        paste_c(img, phone_card("SCHOLARSHIP LETTER", rows, vh["start"] + 0.1, t, (40, 90, 160), 600), 650, 520, eob(k / 0.3) * 0.85, rot=3)
        dt = word_t(vh, "duty", vh["start"] + 2.0)
        if t > dt - 0.2:
            k2 = t - dt + 0.2
            clock(img, 300, 700, 8.0); clock(img, 780, 820, 8.0)
            paste_c(img, pill("CLASS 8:00", 44, (40, 90, 160), WHITE), 300, 830, eob(k2 / 0.25), rot=-3)
            paste_c(img, pill("DUTY 8:00", 44, RED, WHITE), 780, 950, eob((k2 - 0.2) / 0.25), rot=3)
            paste_c(img, glow_text("DONO 8 BAJE?!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 230, eob((k2 - 0.3) / 0.25), rot=-3)


# ======================= DAY 15: Class Ya Duty (Bilal does Hamid's duty in a helmet, phone confiscated, samosa complaint, new shift, Abbu in hospital)
@lru_cache(None)
def helmet_img(visor_up=False):
    s = SS; im = Image.new("RGBA", (300 * s, 300 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda *xy: [v * s for v in xy]
    d.chord(P(22, 6, 278, 300), 180, 360, fill=(230, 60, 70), outline=INK, width=7 * s)          # shell (top half)
    d.rectangle(P(26, 150, 274, 186), fill=(230, 60, 70), outline=INK, width=7 * s)              # rim
    d.rectangle(P(26, 150, 274, 186), fill=(230, 60, 70))
    d.line(P(26, 186, 274, 186), fill=INK, width=7 * s)
    d.rounded_rectangle(P(110, 30, 190, 60), radius=12 * s, fill=WHITE, outline=INK, width=4 * s)
    d.text((150 * s, 45 * s), "TEZ", font=fnt("Anton-Regular.ttf", 24 * s), fill=RED, anchor="mm")
    if visor_up: d.rounded_rectangle(P(40, 70, 260, 120), radius=20 * s, fill=(70, 90, 120, 200), outline=INK, width=5 * s)
    else: d.rounded_rectangle(P(36, 120, 264, 250), radius=40 * s, fill=(40, 55, 80, 215), outline=INK, width=6 * s)   # dark visor over the eyes
    if not visor_up: d.line(P(70, 140, 120, 140), fill=(200, 220, 255, 180), width=8 * s)
    return ssf(im)
def helmet_on(img, x, y, sc, k=1.0, visor_up=False):
    """Helmet on a character drawn with draw_char(x, y, sc); k<1 drops it in from above."""
    if k <= 0: return
    paste_c(img, helmet_img(visor_up), x, y - 70 * sc - 60 * sc - (1 - eo(k)) * 500, sc * 1.02)
def ride_who(img, who, x, y, t, mood="det", sc=1.0, tilt=0.0, helmet=False, bounce=True):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bob = math.sin(t * 22) * 4 * sc if bounce else 0
    draw_char(lay, who, x - 70 * sc, y - 310 * sc + bob, t, mood, 0.78 * sc, arms=(70, 38))
    if helmet: helmet_on(lay, x - 70 * sc, y - 310 * sc + bob, 0.78 * sc)
    paste_c(lay, bike_img(True, True), x, y + bob * 0.4, sc)
    if tilt: lay = lay.rotate(tilt, Image.BICUBIC, center=(x, y))
    img.alpha_composite(lay)
@lru_cache(None)
def bg_class():
    im = bg_hall().copy(); d = ImageDraw.Draw(im)
    d.rectangle([307, 237, 993, 553], fill=(40, 70, 55))
    d.text((650, 320), "BBA • CLASS 1", font=fnt("Anton-Regular.ttf", 70), fill=WHITE, anchor="mm")
    d.text((650, 420), "WELCOME, SCHOLARS!", font=fnt("Poppins-Black.ttf", 40), fill=YEL, anchor="mm")
    d.text((650, 500), "8:00 AM", font=fnt("Poppins-Black.ttf", 34), fill=(200, 230, 210), anchor="mm")
    return im
def hold_book(img, x, y, sc):
    b = Image.new("RGBA", (190, 140), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
    bd.rounded_rectangle([0, 0, 189, 139], radius=10, fill=(40, 90, 160), outline=INK, width=6); bd.line([(95, 0), (95, 139)], fill=INK, width=5)
    paste_c(img, b, x + 150 * sc, y + 190 * sc, sc * 0.9, rot=-6)

def sc_hook15(img, t, lt):
    img.alpha_composite(bg_street("dawn"))
    (v0,) = L("hook15")
    d = ImageDraw.Draw(img); d.line([(540, 200), (540, 1400)], fill=WHITE, width=10)
    paste_c(img, pill("CLASS", 70, (40, 90, 160), WHITE), 270, 300, eob((t - 0.3) / 0.3), rot=-4)
    paste_c(img, pill("DUTY", 70, RED, WHITE), 810, 300, eob((t - 1.0) / 0.3), rot=4)
    clock(img, 270, 520, 8.0); clock(img, 810, 520, 8.0)
    paste_c(img, emoji("📚", 120), 270, 760, eob((t - 0.4) / 0.3)); paste_c(img, bike_img(True, True), 810, 820, 0.45 * eob((t - 1.1) / 0.3))
    draw_char(img, "H", 540, 1030, t, "shock", 0.9, arms=(-120, 120) if t > 1.5 else (-20, 20))
    dt = word_t(v0, "duty", v0["start"] + 1.3)
    if t > dt: paste_c(img, glow_text("DONO 8 BAJE!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 1330, eob((t - dt) / 0.25) * (1 + 0.03 * math.sin(t * 14)), rot=-3)

def sc_plan15(img, t, lt):
    img.alpha_composite(bg_ghafoor("day"))
    vl, vh, vl2, b = L("plan15")
    if t < b["start"]:
        paste_c(img, bike_img(True, True), 820, 1250, 0.6)
        draw_char(img, "H", 290, 1000, t, "happy" if t < vh["start"] else ("shock" if t < vl2["start"] else "sad"), 0.85,
                  arms=(-20, 20) if t < vh["start"] else (-110, 20), hold=hold_book)
        draw_char(img, "L", 760, 1000, t, "happy", 0.85, arms=(-20, -130) if t < vh["start"] else (-20, 20), laugh=t > vl2["start"] + 1.0)
        hk = (t - vl2["start"] - 0.5) / 0.35 if t > vl2["start"] else 0
        helmet_on(img, 760, 1000, 0.85, hk)
        paste_c(img, pill("7:15 AM", 44, YEL), 150, 420, 1.0)
        if t < vh["start"]:
            k = t - vl["start"]
            paste_c(img, pill("BILAL KA PLAN", 60, (255, 130, 40), WHITE), W / 2, 260, eob(k / 0.3), rot=-3)
            if k > 0.8: paste_c(img, bubble([("TERI DUTY", INK), ("MAIN KARUNGA!", RED)], 44, tail="right"), 720, 560, eob((k - 0.8) / 0.3))
        elif t < vl2["start"]:
            k = t - vh["start"]
            paste_c(img, glow_text("TU?!", "Anton-Regular.ttf", 150, WHITE, (90, 160, 255)), 300, 520, eob(k / 0.25), rot=-6)
            paste_c(img, emoji("🗺️", 100), 760, 560, eob((k - 0.4) / 0.3)); paste_c(img, glow_text("?", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), 860, 500, eob((k - 0.6) / 0.3), rot=10)
        else:
            k = t - vl2["start"]
            paste_c(img, pill("HELMET = DISGUISE", 56, RED, WHITE), W / 2, 260, eob((k - 0.6) / 0.3), rot=-3)
            if k > 1.2: paste_c(img, emoji("😎", 100), 900, 560, eob((k - 1.2) / 0.3)); paste_c(img, emoji("🤦", 110), 300, 560, eob((k - 1.4) / 0.3), rot=-8)
    else:
        k = t - b["start"]
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 10, 500, 1350); img.alpha_composite(lay)
        draw_char(img, "H", 230, 1000, t, "shock", 0.8, arms=(-20, 20), hold=hold_book)
        ride_who(img, "L", lerp(720, 1250, eio(k / 0.7)), 1240, t, "happy", 0.85, tilt=6 * math.sin(t * 9), helmet=True)
        stamp(img, "VROOOM!", 620, 420, k, (255, 130, 40), -6, 110)
        dust(img, lerp(500, 1200, eo(k / 0.6)), 1330, t, 3)

def sc_class15(img, t, lt):
    img.alpha_composite(bg_class())
    v1, vl, vh, v2, b = L("class15")
    took = t > v2["start"] + 0.6
    # the professor at the blackboard
    px = 820 if t < v2["start"] else lerp(820, 600, eo((t - v2["start"]) / 0.4))
    draw_char(img, "P", px, 860, t, "happy" if t < vl["start"] else ("det" if t < v2["start"] else "det"), 0.75,
              arms=(-20, -120) if t < vl["start"] else ((-20, 20) if not took else (-20, 110)), hold=hold_phone if took else None)
    front_desk(img, 1230)
    draw_char(img, "H", 330, 1000, t, "happy" if t < vl["start"] else ("shock" if t < vh["start"] or t > v2["start"] else "det"), 0.88,
              arms=(-20, 20) if t < vl["start"] or took else (-20, 110), hold=hold_phone if (vl["start"] - 0.4 < t and not took) else None)
    if t < vl["start"]:
        k = t - v1["start"]
        paste_c(img, pill("PEHLI CLASS!", 60, GRN, WHITE), 300, 640, eob(k / 0.3), rot=-4)
        for j in range(5):
            q = (k * 0.6 + j * 0.2) % 1
            paste_c(img, emoji("⭐", 50), 120 + j * 200, 700 - q * 300, 0.9, alpha=1 - q)
        if k > 1.8: paste_c(img, glow_text("SAPNA SACH!", "Anton-Regular.ttf", 110, YEL, (255, 120, 40)), W / 2, 1150, eob((k - 1.8) / 0.25), rot=-3)
    if vl["start"] - 0.4 < t < vh["start"]:
        k = t - vl["start"] + 0.4
        paste_c(img, emoji("📳", 90), 470, 960, 1.0, rot=12 * math.sin(t * 30))
        kin = eob((k - 0.2) / 0.3)
        call_inset(img, "L", 760, 1000 - 460, t, "shock", ((150, 200, 240), (255, 200, 150)), "BILAL • DUTY PE", kin, arms=(-20, 20))
        # helmet on the inset's Bilal: canvas (440x520, head at x=220, y=230) framed with a 12 px border
        helmet_on(img, 760, 540 + (230 + 12 - 272) * kin, 0.72 * kin, 1.0)
        if k > 0.9: paste_c(img, pill("GHAR NAHI MIL RAHA!", 50, RED, WHITE), W / 2, 220, eob((k - 0.9) / 0.3), rot=-3)
    elif vh["start"] <= t < v2["start"]:
        k = t - vh["start"]
        paste_c(img, emoji("🤫", 110), 160, 640, eob(k / 0.25))
        paste_c(img, pill("LOCATION SENT", 50, (40, 90, 200), WHITE), 330, 780, eob((k - 0.3) / 0.3), rot=3)
        paste_c(img, emoji("📍", 80), 600, 760, eob((k - 0.4) / 0.3))
        if k > 1.0: paste_c(img, emoji("👀", 90), 760, 560, eob((k - 1.0) / 0.3))
    elif t >= v2["start"]:
        k = t - v2["start"]
        stamp(img, "PHONE ZABT!", W / 2, 260, k - 0.4, RED, -6, 110)
        paste_c(img, emoji("😱", 110), 150, 640, eob((k - 0.5) / 0.3))
        if t > b["start"]: paste_c(img, bubble([("CLASS MEIN", INK), ("PHONE?!", RED)], 46, tail="right"), 700, 520, eob((t - b["start"]) / 0.25))

def sc_msg15(img, t, lt):
    img.alpha_composite(bg_center("day"))
    v1, v2, b = L("msg15")
    draw_char(img, "H", 300, 1010, t, "shock" if t < b["start"] else "det", 0.9, arms=(-20, 110) if t < b["start"] else (-120, 120), hold=hold_phone if t < b["start"] else None)
    paste_c(img, pill("BREAK • 10:30 AM", 44, YEL), 300, 640, eob((t - v1["start"]) / 0.3), rot=-3)
    if t < v2["start"]:
        rows = [("BILAL  (5)", (255, 130, 40)), ("MANAGER  (4)", RED), ("9 MISSED CALLS", INK)]
        paste_c(img, phone_card("MISSED CALLS", rows, v1["start"] + 0.2, t, RED, 600), 720, 620, eob((t - v1["start"] - 0.1) / 0.3) * 0.92, rot=3)
        paste_c(img, emoji("📵", 90), 900, 300, eob((t - v1["start"] - 0.6) / 0.3))
    elif t < b["start"]:
        rows = [("CUSTOMER COMPLAINT:", INK), ("RIDER NE SAMOSAY", RED), ("KHA LIYE!", RED), ("OFFICE AAO - ABHI!", (40, 90, 200))]
        paste_c(img, phone_card("TEZ DELIVERY", rows, v2["start"] + 0.1, t, (40, 90, 200), 660), 700, 640, eob((t - v2["start"]) / 0.3) * 0.92, rot=-3)
        paste_c(img, emoji("🥟", 90), 980, 330, eob((t - v2["start"] - 1.2) / 0.3), rot=10)
    else:
        k = t - b["start"]
        stamp(img, "BILAAAL!", W / 2, 360, k, (255, 130, 40), -5, 140)
        paste_c(img, emoji("🤦", 160), 760, 760, eob(k / 0.2), rot=-8)

def sc_office15(img, t, lt):
    img.alpha_composite(bg_office())
    v1, vl, vh, v2, b, va = L("office15")
    hx = lerp(-200, 190, eo((t - v1["start"]) / 0.7))
    mm = "det" if t < vh["start"] else ("n" if t < v2["start"] else "happy")
    draw_char(img, "M", 880, 980, t, mm, 0.85, arms=(-20, 20) if t < v2["start"] else (-20, -120), hold=clipboard)
    draw_char(img, "L", 520, 1010, t, "happy" if t < vl["start"] else ("shock" if t < vh["start"] else "sad"), 0.82,
              arms=(-20, 110) if t < v2["start"] else (-20, 20), hold=hold_samosa if t < v2["start"] else None, laugh=vl["start"] < t < vl["end"])
    helmet_on(img, 520, 1010, 0.82, 1.0, visor_up=t > vl["start"])
    draw_char(img, "H", hx, 1000, t, "shock" if t < vh["start"] else ("det" if t < v2["start"] else "happy"), 0.85,
              arms=(-70, 70) if t < v1["start"] + 0.7 else (-20, 20))
    if t < vl["start"]:
        k = t - v1["start"]
        paste_c(img, pill("10:45 AM • OFFICE", 46, YEL), W / 2, 230, eob(k / 0.3), rot=-3)
        if k > 1.3: paste_c(img, bubble([("YEH KAUN HAI?!", RED)], 48, tail="right"), 820, 560, eob((k - 1.3) / 0.3))
        if k > 1.0: paste_c(img, emoji("😬", 80), 520, 560, eob((k - 1.0) / 0.3))
    elif t < vh["start"]:
        k = t - vl["start"]
        paste_c(img, pill("SAMOSA QUALITY CHECK", 50, (255, 130, 40), WHITE), W / 2, 260, eob(k / 0.3), rot=-3)
        if k > 1.6: paste_c(img, emoji("😂", 90), 180, 560, eob((k - 1.6) / 0.3)); paste_c(img, emoji("😡", 90), 900, 560, eob((k - 1.8) / 0.3))
    elif t < v2["start"]:
        k = t - vh["start"]
        paste_c(img, pill("SUBAH: CLASS", 56, (40, 90, 160), WHITE), W / 2, 260, eob((k - 0.6) / 0.3), rot=-3)
        ct = word_t(vh, "shaam", vh["start"] + 2.2)
        if t > ct - 0.1: paste_c(img, pill("SHAAM: DOUBLE DUTY", 56, RED, WHITE), W / 2, 380, eob((t - ct + 0.1) / 0.3), rot=3)
        paste_c(img, emoji("🙏", 90), 200, 600, eob((k - 0.2) / 0.3))
    elif t < b["start"]:
        k = t - v2["start"]
        paste_c(img, bubble([("THEEK HAI!", GRN)], 52, tail="right"), 820, 560, eob(k / 0.3))
        paste_c(img, pill("DUTY: 2 PM - 10 PM", 54, GRN, WHITE), W / 2, 260, eob((k - 0.3) / 0.3), rot=-3)
        st_ = word_t(v2, "samoson", v2["start"] + 1.8)
        if t > st_ - 0.1: paste_c(img, pill("SAMOSAY: -Rs 150 (TANKHWAH SE)", 40, RED, WHITE), W / 2, 380, eob((t - st_ + 0.1) / 0.3) * (1 + 0.03 * math.sin(t * 12)), rot=2)
    else:
        k = t - b["start"]
        stamp(img, "CLASS + NAUKRI: BACH GAYE", W / 2, 300, k, GRN, -5, 76)
        if t > va["start"]: paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 530, eob((t - va["start"]) / 0.25), rot=3)
        for j in range(8):
            q = (k * 0.8 + j * 0.13) % 1
            paste_c(img, emoji(["🎉", "⭐"][j % 2], 60), 120 + j * 120, 200 + q * 900, 0.9, rot=q * 200)

def sc_cliff15(img, t, lt):
    img.alpha_composite(bg_street("night"))
    va, vh, ol = L("cliff15")
    paste_c(img, bike_img(True, True), 820, 1260, 0.55)
    draw_char(img, "H", 300, 1000, t, "shock", 0.9, arms=(-20, 110) if t < vh["start"] else (-20, 20), hold=hold_phone if t < vh["start"] else None)
    paste_c(img, pill("10:15 PM", 44, YEL), 150, 420, 1.0)
    if t < vh["start"] + 0.2:
        kin = eob((t - va["start"] + 0.3) / 0.35) * (1 - eo((t - vh["start"]) / 0.2))
        call_inset(img, "A", 760, 640, t, "sad", ((240, 210, 170), (210, 170, 130)), "AMMI • LAHORE", kin)
        ht = word_t(va, "hospital", va["start"] + 1.0)
        if t > ht - 0.1: paste_c(img, pill("ABBU: HOSPITAL", 60, RED, WHITE), W / 2, 260, eob((t - ht + 0.1) / 0.3) * (1 + 0.04 * math.sin(t * 14)), rot=-3); paste_c(img, emoji("🏥", 90), 940, 360, eob((t - ht) / 0.3))
    else:
        k = t - vh["start"]
        paste_c(img, pill("ABBU: HOSPITAL", 60, RED, WHITE), W / 2, 260, 1.0, rot=-3)
        paste_c(img, glow_text("JEB: Rs 0", "Anton-Regular.ttf", 140, YEL, (230, 60, 70)), 680, 600, eob((k - 0.6) / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
        paste_c(img, emoji("😰", 110), 300, 640, eob((k - 0.3) / 0.3))


# ======================= DAY 16 (Paanch Hazaar): night office tint, packet prop, Rs 5,000 notes (reusable)
def night_tint(img, a=110): img.alpha_composite(Image.new("RGBA", (W, H), (12, 14, 40, a)))
@lru_cache(None)
def packet_img():
    s = SS; im = Image.new("RGBA", (300 * s, 220 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    P = lambda *xy: [v * s for v in xy]
    d.rounded_rectangle(P(8, 8, 292, 212), radius=14 * s, fill=(176, 128, 78), outline=INK, width=7 * s)
    d.line(P(150, 8, 150, 212), fill=(240, 225, 190), width=10 * s); d.line(P(8, 110, 292, 110), fill=(240, 225, 190), width=10 * s)
    d.ellipse(P(124, 84, 176, 136), fill=(190, 30, 40), outline=INK, width=5 * s)
    d.text((40 * s, 40 * s), "?", font=fnt("Anton-Regular.ttf", 56 * s), fill=(110, 70, 40), anchor="mm")
    return ssf(im)
def hold_packet(img, x, y, sc): paste_c(img, packet_img(), x - 150 * sc, y + 170 * sc, sc * 0.75, rot=8)
def hold_notes5000(img, x, y, sc): paste_c(img, notes_img(5000, 240), x - 140 * sc, y + 200 * sc, sc * 0.9, rot=8)

def sc_hook16(img, t, lt):
    img.alpha_composite(bg_street("night"))
    (v0,) = L("hook16")
    draw_char(img, "H", 330, 1010, t, "shock", 0.95, arms=(-20, 110), hold=hold_phone)
    paste_c(img, pill("10:15 PM", 44, YEL), 150, 420, 1.0)
    paste_c(img, emoji("🏥", 150), 800, 560, eob((t - 1.4) / 0.3) * (1 + 0.04 * math.sin(t * 8)))
    paste_c(img, pill("ABBU: HOSPITAL", 60, RED, WHITE), W / 2, 260, eob((t - 1.5) / 0.3), rot=-3)
    zt = word_t(v0, "zero", v0["start"] + 2.4)
    if t > zt - 0.1:
        k = t - zt + 0.1
        paste_c(img, glow_text("JEB: Rs 0", "Anton-Regular.ttf", 140, YEL, (230, 60, 70)), 720, 820, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-4)
        paste_c(img, emoji("😰", 100), 900, 1000, eob((k - 0.2) / 0.3))

def sc_call16(img, t, lt):
    img.alpha_composite(bg_street("night"))
    va, vh = L("call16")
    draw_char(img, "H", 280, 1010, t, "shock" if t < vh["start"] else "det", 0.9, arms=(-20, 110), hold=hold_phone)
    call_inset(img, "A", 770, 640, t, "sad", ((240, 210, 170), (210, 170, 130)), "AMMI • HOSPITAL", eob((t - va["start"] + 0.3) / 0.35) * 0.95)
    if t < vh["start"]:
        pt = word_t(va, "paanch", va["start"] + 1.4)
        if t > pt - 0.1:
            k = t - pt + 0.1
            paste_c(img, glow_text("Rs 5,000", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 250, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
            paste_c(img, pill("SUBAH TAK!", 52, RED, WHITE), 300, 420, eob((k - 0.3) / 0.3), rot=-5)
            paste_c(img, emoji("💉", 90), 960, 1000, eob((k - 0.2) / 0.3), rot=-15)
    else:
        k = t - vh["start"]
        paste_c(img, pill("Rs 5,000 • SUBAH TAK", 50, RED, WHITE), W / 2, 250, 1.0, rot=-3)
        paste_c(img, bubble([("MAIN", INK), ("BHEJUNGA!", (40, 140, 80))], 48, tail="left"), 330, 560, eob(k / 0.3))
        bt = word_t(vh, "bhejunga", vh["start"] + 1.6)
        if t > bt: paste_c(img, pill("PAR KAHAN SE?!", 48, WHITE, RED), 330, 1240, eob((t - bt) / 0.3) * (1 + 0.04 * math.sin(t * 14)), rot=3); paste_c(img, emoji("😬", 80), 560, 1240, eob((t - bt - 0.2) / 0.3))

def sc_office16(img, t, lt):
    img.alpha_composite(bg_office()); night_tint(img, 120)
    v1, v2, b = L("office16")
    draw_char(img, "H", 280, 1020, t, "det" if t < v2["start"] else ("shock" if t < b["start"] else "sad"), 0.9, arms=(-20, 110), hold=hold_phone)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, pill("KOSHISH #1: MANAGER", 48, YEL), W / 2, 240, eob(k / 0.3), rot=-3)
        rows = [("SIR, Rs 5,000", INK), ("ADVANCE MIL SAKTA HAI?", INK), ("ABBU HOSPITAL MEIN HAIN", RED)]
        paste_c(img, phone_card("HAMID → MANAGER", rows, v1["start"] + 0.2, t, (40, 90, 200), 660), 700, 680, eob((k - 0.1) / 0.3) * 0.9, rot=3)
        paste_c(img, emoji("🙏", 80), 520, 1000, eob((k - 0.6) / 0.3))
    else:
        k = t - v2["start"]
        rows = [("SAMOSAY WALAY KO?", (255, 130, 40)), ("ADVANCE?", INK), ("BILKUL NAHI!", RED)]
        paste_c(img, phone_card("MANAGER", rows, v2["start"] + 0.3, t, RED, 640), 700, 660, eob(k / 0.3) * 0.9, rot=-3)
        paste_c(img, emoji("🥟", 90), 960, 380, eob((k - 0.4) / 0.3), rot=12)
        if t > b["start"] - 0.1: stamp(img, "REJECTED!", W / 2, 260, t - b["start"] + 0.1, RED, -8, 120)

def sc_bilal16(img, t, lt):
    img.alpha_composite(bg_room("night"))
    vl, vh = L("bilal16")
    draw_char(img, "H", 290, 1010, t, "sad" if t < vh["start"] else "det", 0.88, arms=(-20, 20) if t < vh["start"] else (-120, 20))
    draw_char(img, "L", 770, 1000, t, "happy", 0.88, arms=(-130, 20) if t < vh["start"] else (-20, 20), hold=hold_phone if t < vh["start"] + 0.6 else None,
              laugh=t > vh["start"] + 0.9)
    if t < vh["start"]:
        k = t - vl["start"]
        paste_c(img, pill("KOSHISH #2: BILAL", 52, (255, 130, 40), WHITE), W / 2, 240, eob(k / 0.3), rot=-3)
        bt = word_t(vl, "phone", vl["start"] + 1.2)
        if t > bt - 0.1:
            paste_c(img, pill("PHONE BECHO = Rs 5,000!", 46, GRN, WHITE), W / 2, 380, eob((t - bt + 0.1) / 0.3), rot=3)
            paste_c(img, emoji("🤑", 90), 960, 560, eob((t - bt) / 0.3))
    else:
        k = t - vh["start"]
        paste_c(img, pill("KOSHISH #2: BILAL", 52, (255, 130, 40), WHITE), W / 2, 240, 1.0, rot=-3)
        # the phone pops: it's plastic
        paste_c(img, phone_img(False), 620, lerp(1120, 560, eo(k / 0.4)), 1.2, rot=-20 + 360 * eo(k / 0.6))
        if k > 0.5: stamp(img, "DUMMY!", 620, 420, k - 0.5, RED, -8, 110)
        paste_c(img, emoji("🤦", 110), 180, 620, eob((k - 0.3) / 0.3), rot=-8)
        if k > 1.1: paste_c(img, emoji("😂", 90), 940, 620, eob((k - 1.1) / 0.3))
        if k > 1.2: paste_c(img, pill("DAY 3 WALA!", 44, YEL), 820, 1260, eob((k - 1.2) / 0.3), rot=-3)

def sc_rauf16(img, t, lt):
    img.alpha_composite(bg_rauf("night")); bulb_glow(img)
    v1, vr, vh, b, vr2 = L("rauf16")
    loud = vr["start"] < t < vr["end"]
    gave = t > vr2["start"]
    draw_char(img, "R", 790, 960 + (math.sin(t * 40) * 5 if loud else 0), t, "det" if t < vr2["start"] else "n", 1.0,
              arms=(-130, 20) if loud else ((-20, 20) if not gave else (-110, 20)), hold=hold_notes5000 if gave else None)
    hx = lerp(-150, 270, eo((t - v1["start"]) / 0.7))
    draw_char(img, "H", hx, 1010, t, "det" if t < vr["start"] else ("shock" if t < vh["start"] else ("sad" if t < vr2["start"] else "happy")), 0.9,
              arms=(-20, 20) if t < vh["start"] or gave else (-100, -100))
    if t < vr["start"]:
        k = t - v1["start"]
        paste_c(img, pill("KOSHISH #3", 54, (40, 110, 70), WHITE), W / 2, 470, eob(k / 0.3), rot=-3)
        clock(img, 150, 640, 0.0); paste_c(img, pill("12:00 AM", 40, YEL), 150, 770, eob(k / 0.3))
    elif t < vh["start"]:
        k = t - vr["start"]
        pt = word_t(vr, "pagal", vr["start"] + 1.0)
        paste_c(img, glow_text("Rs 5,000?!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 500, eob(k / 0.25), rot=-3)
        if t > pt - 0.1: paste_c(img, glow_text("PAGAL HO?!", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), 760, 650, eob((t - pt + 0.1) / 0.25) * (1 + 0.04 * math.sin(t * 16)), rot=5)
    elif t < b["start"]:
        k = t - vh["start"]
        paste_c(img, pill("ABBU KA ILAAJ", 54, RED, WHITE), W / 2, 480, eob(k / 0.3), rot=-3)
        mt = word_t(vh, "muft", vh["start"] + 1.6)
        if t > mt - 0.1: paste_c(img, pill("MUFT KAAM • HAR RAAT", 50, YEL), W / 2, 600, eob((t - mt + 0.1) / 0.3), rot=3)
    elif t < vr2["start"]:
        k = t - b["start"]
        paste_c(img, bubble([("…", INK)], 70, tail="right"), 760, 560, eob(k / 0.2))
        paste_c(img, emoji("😟", 80), 280, 640, eob(k / 0.2))
    else:
        k = t - vr2["start"]
        paste_c(img, glow_text("ADVANCE: Rs 5,000", "Anton-Regular.ttf", 110, WHITE, (40, 190, 110)), W / 2, 490, eob(k / 0.3), rot=-3)
        rt = word_t(vr2, "rona", vr2["start"] + 1.4)
        if t > rt - 0.1: paste_c(img, pill("RONA BAND KARO!", 50, (40, 110, 70), WHITE), W / 2, 620, eob((t - rt + 0.1) / 0.3), rot=3)
        if k > 0.6: paste_c(img, emoji("🥹", 90), 470, 700, eob((k - 0.6) / 0.3))

def sc_send16(img, t, lt):
    img.alpha_composite(bg_street("night"))
    v1, va, b, vb = L("send16")
    draw_char(img, "H", 290, 1010, t, "det" if t < va["start"] else "happy", 0.9, arms=(-20, 110) if t < b["start"] else (-120, 120),
              hold=hold_phone if t < b["start"] else None)
    clock(img, 150, 330, 1.0); paste_c(img, pill("1:00 AM", 40, YEL), 150, 460, 1.0)
    if t < va["start"]:
        k = t - v1["start"]
        rows = [("AMMI • LAHORE", INK), ("Rs 5,000", (40, 140, 80)), ("SENT!", (40, 140, 80))]
        paste_c(img, phone_card("PAISE BHEJO", rows, v1["start"] + 0.3, t, (40, 150, 100), 620), 720, 660, eob(k / 0.3) * 0.9, rot=3)
        if k > 1.0: paste_c(img, emoji("✅", 100), 930, 900, eob((k - 1.0) / 0.3))
    elif t < b["start"]:
        k = t - va["start"]
        call_inset(img, "A", 770, 640, t, "happy", ((240, 210, 170), (210, 170, 130)), "AMMI • HOSPITAL", eob(k / 0.3) * 0.95)
        it = word_t(va, "abbu", va["start"] + 1.2)
        if t > it - 0.1: paste_c(img, pill("ABBU THEEK HAIN!", 56, GRN, WHITE), W / 2, 250, eob((t - it + 0.1) / 0.3), rot=-3); paste_c(img, emoji("❤️", 80), 960, 1000, eob((t - it) / 0.3) * (1 + 0.08 * math.sin(t * 6)))
    else:
        k = t - b["start"]
        paste_c(img, pill("ABBU THEEK HAIN!", 56, GRN, WHITE), W / 2, 250, 1.0, rot=-3)
        paste_c(img, emoji("🙏", 130), 760, 700, eob(k / 0.3))
        if t > vb["start"] - 0.1: paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 450, eob((t - vb["start"] + 0.1) / 0.25), rot=3)
        for j in range(8):
            q = (k * 0.8 + j * 0.13) % 1
            paste_c(img, emoji(["⭐", "🎉"][j % 2], 56), 120 + j * 120, 200 + q * 900, 0.9, rot=q * 200)

def sc_cliff16(img, t, lt):
    img.alpha_composite(bg_rauf("night")); night_tint(img, 130)
    v1, v2, vh, ol = L("cliff16")
    lean = 0.0 if t < v1["start"] else eo((t - v1["start"]) / 0.5)
    draw_char(img, "R", 760 - 60 * lean, 980, t, "det", 1.0, arms=(-110, 20), hold=hold_packet)
    draw_char(img, "H", 280, 1010, t, "n" if t < v1["start"] + 1.0 else "shock", 0.9, arms=(-20, 20))
    paste_c(img, pill("RAAT 1:30 AM", 40, YEL), 200, 560, 1.0)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, glow_text("EK SHART…", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 260, eob(k / 0.3), rot=-3)
        dt = word_t(v1, "kal", v1["start"] + 1.6)
        if t > dt - 0.1: paste_c(img, pill("KAL RAAT 2 BAJE", 54, RED, WHITE), W / 2, 420, eob((t - dt + 0.1) / 0.3), rot=3)
    elif t < vh["start"]:
        k = t - v2["start"]
        paste_c(img, pill("KAL RAAT 2 BAJE", 54, RED, WHITE), W / 2, 420, 1.0, rot=3)
        stamp(img, "KHOLNA MAT!", W / 2, 260, k - 0.1, RED, -6, 110)
        bt = word_t(v2, "batana", v2["start"] + 1.4)
        if t > bt - 0.1: paste_c(img, emoji("🤫", 110), 470, 620, eob((t - bt + 0.1) / 0.3))
    else:
        k = t - vh["start"]
        paste_c(img, glow_text("PACKET MEIN", "Anton-Regular.ttf", 120, WHITE, (90, 160, 255)), W / 2, 250, eob(k / 0.3), rot=-3)
        paste_c(img, glow_text("KYA HAI?!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 410, eob((k - 0.4) / 0.3) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
        paste_c(img, glow_text("?", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), 760, 1150, eob((k - 0.6) / 0.3) * (1 + 0.06 * math.sin(t * 9)), rot=12)



# ======================= DAY 17: Raat 2 Baje (the sealed packet; Amma ji = Seth Rauf's mother; police naka)
@lru_cache(None)
def packet_open_img():
    """Opened packet: dawai boxes + strips and a folded chit. 420x300."""
    im = Image.new("RGBA", (420, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(20, 110), (400, 110), (370, 290), (50, 290)], fill=(176, 128, 78), outline=INK)
    d.polygon([(20, 110), (90, 30), (150, 110)], fill=(196, 148, 98), outline=INK); d.polygon([(400, 110), (330, 30), (270, 110)], fill=(196, 148, 98), outline=INK)
    d.rounded_rectangle([80, 70, 190, 200], radius=8, fill=WHITE, outline=INK, width=5); d.rectangle([80, 100, 190, 130], fill=(60, 150, 255))
    d.text((135, 165), "+", font=fnt("Anton-Regular.ttf", 50), fill=RED, anchor="mm")
    d.rounded_rectangle([200, 60, 300, 190], radius=8, fill=(250, 240, 200), outline=INK, width=5); d.rectangle([200, 90, 300, 115], fill=(40, 190, 110))
    for k in range(2):
        for j in range(3): d.ellipse([214 + j * 28, 130 + k * 26, 234 + j * 28, 150 + k * 26], fill=(230, 60, 70), outline=INK, width=2)
    d.polygon([(300, 80), (390, 60), (400, 160), (310, 175)], fill=WHITE, outline=INK); d.line([(320, 100), (380, 88)], fill=(90, 90, 110), width=4); d.line([(322, 125), (385, 113)], fill=(90, 90, 110), width=4)
    return im
@lru_cache(None)
def chit17():
    im = Image.new("RGBA", (760, 440), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 750, 430], radius=16, fill=(252, 248, 230), outline=INK, width=7)
    for y in range(110, 420, 70): d.line([(40, y), (720, y)], fill=(180, 200, 230), width=3)
    d.text((380, 150), "AMMI,", font=fnt("Anton-Regular.ttf", 90), fill=(40, 60, 150), anchor="mm")
    d.text((380, 260), "MAAF KARNA…", font=fnt("Anton-Regular.ttf", 90), fill=(40, 60, 150), anchor="mm")
    d.text((520, 370), "— AAPKA RAUF", font=fnt("Anton-Regular.ttf", 64), fill=(170, 40, 50), anchor="mm")
    return im
@lru_cache(None)
def bg_haveli():
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im); P = lambda *xy: [v * s for v in xy]
    for y in range(0, 1200 * s, 4): d.rectangle([0, y, W * s, y + 4], fill=mixc((8, 10, 28), (40, 36, 70), y / (1200 * s)))
    d.ellipse(P(820, 140, 920, 240), fill=(250, 245, 210))
    rs = np.random.default_rng(9)
    for _ in range(30):
        x_, y_ = rs.uniform(0, W), rs.uniform(40, 420); d.ellipse(P(x_, y_, x_ + 4, y_ + 4), fill=(230, 230, 255))
    d.rectangle(P(60, 420, 1020, 1200), fill=(92, 70, 72), outline=INK, width=8)
    for x in range(60, 1020, 80): d.rectangle(P(x, 400, x + 50, 440), fill=(92, 70, 72), outline=INK, width=4)   # battlements
    for y in range(470, 1200, 60):
        for x in range(60 + (y // 60 % 2) * 40, 1020, 80): d.rectangle(P(x, y, x + 78, y + 58), outline=(72, 54, 58), width=2)
    for wx in (140, 800):   # arched windows, one with a candle glow
        d.rectangle(P(wx, 560, wx + 140, 760), fill=(30, 26, 40) if wx == 140 else (240, 190, 90), outline=INK, width=6); d.chord(P(wx, 490, wx + 140, 630), 180, 360, fill=(30, 26, 40) if wx == 140 else (240, 190, 90), outline=INK, width=6)
        d.line(P(wx + 70, 500, wx + 70, 760), fill=INK, width=5)
    d.chord(P(330, 640, 750, 1000), 180, 360, fill=(20, 16, 24), outline=INK, width=8); d.rectangle(P(330, 820, 750, 1200), fill=(20, 16, 24), outline=INK, width=8)
    d.rectangle(P(0, 1200, W, H), fill=(50, 46, 58))
    d.rectangle(P(300, 1200, 780, 1240), fill=(110, 100, 105), outline=INK, width=4)
    return ssf(im)
def haveli_door(img, k):
    """Two wooden door leaves in the arch; k = 0 closed .. 1 open."""
    d = ImageDraw.Draw(img); half = 210 * (1 - 0.8 * eo(k))
    for sx, x0 in ((1, 330), (-1, 750)):
        xa, xb = (x0, x0 + half) if sx > 0 else (x0 - half, x0)
        d.rectangle([xa, 820, xb, 1200], fill=(110, 66, 40), outline=INK, width=6)
        for j in range(3): d.ellipse([(xa + xb) / 2 - 10, 900 + j * 100, (xa + xb) / 2 + 10, 920 + j * 100], fill=(210, 170, 70), outline=INK, width=2)
def lantern(img, x, y, t):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([x - 200, y - 200, x + 200, y + 200], fill=(255, 200, 90, int(90 + 20 * math.sin(t * 9))))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    d = ImageDraw.Draw(img); d.line([(x, y - 90), (x, y - 50)], fill=INK, width=6)
    d.rounded_rectangle([x - 40, y - 50, x + 40, y + 50], radius=10, fill=(255, 220, 120), outline=INK, width=6); d.ellipse([x - 12, y - 20, x + 12, y + 20], fill=(255, 140, 40))
def hold_lantern(img, x, y, sc): lantern(img, x - 150 * sc, y + 210 * sc, 0.0)
def hold_packet_r(img, x, y, sc): paste_c(img, packet_img(), x + 150 * sc, y + 170 * sc, sc * 0.75, rot=-8)
def hold_notes500(img, x, y, sc): paste_c(img, notes_img(500, 200), x + 130 * sc, y + 200 * sc, sc * 0.9, rot=-8)
def barrier(img, y=1180):
    d = ImageDraw.Draw(img)
    for x in (560, 1060): d.rectangle([x - 14, y - 160, x + 14, y + 60], fill=(200, 200, 205), outline=INK, width=4)
    for k in range(6): d.rectangle([560 + k * 84, y - 150, 560 + (k + 1) * 84, y - 110], fill=RED if k % 2 == 0 else WHITE, outline=INK, width=3)
def torch_beam(img, x, y, tx, ty, a=110):
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).polygon([(x, y - 12), (x, y + 12), (tx + 150, ty + 160), (tx - 150, ty - 160)], fill=(255, 240, 170, a))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(14)))
def dogs(img, x, t, n=3, y=1290):
    for j in range(n):
        paste_c(img, emoji("🐕", 150 - j * 15), x - j * 190, y - abs(math.sin(t * 14 + j)) * 30 - j * 20)
        if ((t + j * 0.2) % 0.5) < 0.3: paste_c(img, pill("BHOW!", 40, WHITE, INK), x - j * 190 - 30, y - 150 - j * 20, 1.0, rot=-10 + j * 8)

def sc_hook17(img, t, lt):
    img.alpha_composite(bg_road("night")); night_tint(img, 60)
    (v0,) = L("hook17")
    draw_char(img, "H", 330, 1010, t, "shock", 0.95, arms=(-110, 20), hold=hold_packet)
    clock(img, 160, 420, 2.0); paste_c(img, pill("2:00 AM", 44, YEL), 160, 550, 1.0)
    paste_c(img, packet_img(), 780, 700, eob((t - 1.4) / 0.3) * 1.5 * (1 + 0.04 * math.sin(t * 8)), rot=-8)
    kt = word_t(v0, "kholna", v0["start"] + 2.2)
    if t > kt - 0.1: stamp(img, "KHOLNA MAT!", 760, 960, t - kt + 0.1, RED, -8, 100)
    if t > 1.6: paste_c(img, pill("SETH KA PACKET", 54, (30, 100, 70), WHITE), W / 2, 250, eob((t - 1.6) / 0.3), rot=-3)

def sc_bilal17(img, t, lt):
    img.alpha_composite(bg_room("night")); bulb_glow(img, 40)
    v1, vh, v2, b = L("bilal17")
    sn = t > b["start"]; k = t - b["start"]
    lean = eo((t - v2["start"]) / 0.4) if t > v2["start"] and not sn else 0
    draw_char(img, "L", 790 - 140 * lean, 1000 + (math.sin(t * 50) * 8 if sn and k < 0.4 else 0), t, "happy" if not sn else "shock", 0.88,
              arms=(-130, 20) if t < vh["start"] else (-20, 20), laugh=sn and k > 0.3)
    # packet: in Hamid's hand, flies up on the sneeze and lands back
    if not sn: draw_char(img, "H", 290, 1010, t, "n" if t < vh["start"] else "det", 0.88, arms=(-110, 20), hold=hold_packet)
    else:
        q = min(1, k / 0.6); px = lerp(150, 330, q); py = 1180 - 700 * 4 * q * (1 - q) - 0 * q
        draw_char(img, "H", 290, 1010, t, "shock", 0.88, arms=(-140, 140))
        paste_c(img, packet_img(), px + 40, py - 120 * q, 0.9, rot=q * 360)
    if t < vh["start"]:
        k1 = t - v1["start"]
        paste_c(img, pill("BILAL KA IDEA", 52, (255, 130, 40), WHITE), W / 2, 240, eob(k1 / 0.3), rot=-3)
        nt = word_t(v1, "note", v1["start"] + 1.0)
        if t > nt - 0.1: paste_c(img, glow_text("NOTE HONGE?!", "Anton-Regular.ttf", 110, YEL, (40, 150, 90)), W / 2, 420, eob((t - nt + 0.1) / 0.25), rot=3); paste_c(img, emoji("🤑", 90), 900, 600, eob((t - nt) / 0.3))
    elif t < v2["start"]:
        k2 = t - vh["start"]
        paste_c(img, glow_text("NAHI!", "Anton-Regular.ttf", 150, WHITE, (230, 60, 70)), W / 2, 330, eob(k2 / 0.25), rot=-4)
        paste_c(img, emoji("🙅", 100), 170, 600, eob((k2 - 0.2) / 0.3))
        paste_c(img, pill("SETH NE MANA KIYA HAI", 46, RED, WHITE), W / 2, 480, eob((k2 - 0.4) / 0.3), rot=3)
    elif not sn:
        k3 = t - v2["start"]
        paste_c(img, pill("SOONGH TOH LE!", 52, YEL), W / 2, 280, eob(k3 / 0.3), rot=-3)
        paste_c(img, emoji("👃", 90), 560, 640, eob((k3 - 0.3) / 0.3) * (1 + 0.1 * math.sin(t * 20)))
        if k3 > 0.5: paste_c(img, text_img("SNIFF… SNIFF…", "Poppins-Black.ttf", 50, WHITE, 6, INK), 620, 480, eob((k3 - 0.5) / 0.3), rot=-6)
    else:
        paste_c(img, glow_text("AAACHHOO!", "Anton-Regular.ttf", 150, WHITE, (255, 130, 40)), W / 2, 330, eob(k / 0.2) * (1 + 0.05 * math.sin(t * 30)), rot=-5)
        paste_c(img, emoji("🤧", 110), 860, 560, eob(k / 0.2))

def sc_ride17(img, t, lt):
    v1, v2, b, v3, v4 = L("ride17")
    img.alpha_composite(bg_road("night")); night_tint(img, 70)
    pt = word_t(v2, "puncture", v2["start"] + 1.3)
    if t < pt:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); speedlines(lay, t, 14, 300, 1350); img.alpha_composite(lay); dust(img, 260, 1330, t, 3)
        ride(img, 520, 1230, t, "det", 1.0, tilt=4, dent=True, box=True)
        if t < v2["start"]:
            k = t - v1["start"]
            clock(img, 160, 420, 1.5); paste_c(img, pill("1:30 AM", 44, YEL), 160, 550, 1.0)
            paste_c(img, pill("PURANI HAVELI • 10 KM", 52, YEL), W / 2, 260, eob(k / 0.3), rot=-3)
            paste_c(img, packet_img(), 860, 560, eob((k - 0.4) / 0.3) * 0.8, rot=8)
        else:
            paste_c(img, pill("AADHA RAASTA…", 52, WHITE, INK), W / 2, 260, eob((t - v2["start"]) / 0.3), rot=-3)
    elif t < v3["start"]:
        k = t - pt; sh = math.sin(t * 60) * 10 * max(0, 1 - k / 0.5)
        ride(img, 520 + sh, 1240, t, "shock", 1.0, tilt=-3, dent=True, box=True, bounce=False)
        paste_c(img, glow_text("PUNCTURE!", "Anton-Regular.ttf", 140, WHITE, (230, 60, 70)), W / 2, 300, eob(k / 0.25), rot=-4)
        if t > b["start"] - 0.05:
            paste_c(img, emoji("💨", 120), 300, 1330, eob((t - b["start"]) / 0.2), rot=10)
            paste_c(img, glow_text("PHUSSS…", "Anton-Regular.ttf", 110, YEL, (120, 120, 140)), 380, 470, eob((t - b["start"]) / 0.2), rot=4)
    elif t < v4["start"]:
        k = t - v3["start"]
        ride(img, 600, 1240, t, "shock", 1.0, dent=True, box=True, bounce=False)
        dogs(img, lerp(-120, 330, eo(k / 0.8)), t)
        paste_c(img, glow_text("TEEN KUTTAY!", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 300, eob((k - 0.3) / 0.25) * (1 + 0.03 * math.sin(t * 14)), rot=-3)
        if k > 0.9: paste_c(img, emoji("😱", 100), 880, 560, eob((k - 0.9) / 0.3))
    else:   # pushing the bike at a run, dogs chasing, clock ticks to 2:00
        k = t - v4["start"]; q = k / max(0.1, v4["end"] - v4["start"])
        bx = lerp(380, 820, eio(q)); jmp = abs(math.sin(t * 13)) * 20
        paste_c(img, bike_img(True, True), bx, 1250, 0.85)
        draw_char(img, "H", bx - 300, 960 - jmp, t, "shock", 0.82, arms=(-70, -70))
        dogs(img, bx - 560, t, 3, 1320)
        clock(img, 160, 420, 1.0 + 59 / 60 + q / 60); paste_c(img, pill("1:59 AM" if q < 0.85 else "2:00 AM ✓", 44, YEL if q < 0.85 else GRN, INK if q < 0.85 else WHITE), 160, 550, 1.0)
        paste_c(img, pill("DHAKKA DO… BHAAGO!", 48, RED, WHITE), W / 2, 260, eob(k / 0.3), rot=-3)
        speedlines(img, t, 8, 600, 1100)

def sc_haveli17(img, t, lt):
    v1, b, v2 = L("haveli17")
    img.alpha_composite(bg_haveli())
    ok = eo((t - v1["start"] - 1.0) / 1.2)
    haveli_door(img, ok)
    paste_c(img, pill("PURANI HAVELI", 52, YEL), W / 2, 280, eob((t - v1["start"]) / 0.3), rot=-3)
    if t > v1["start"] + 1.0 and t < v2["start"]:
        paste_c(img, text_img("CHARRR…", "Anton-Regular.ttf", 110, WHITE, 8, INK), 760, 560, eob((t - v1["start"] - 1.0) / 0.3), rot=8)
    if t > b["start"] and t < v2["start"]:   # two glowing eyes in the dark doorway
        k = t - b["start"]
        for sx in (-1, 1):
            ImageDraw.Draw(img).ellipse([540 + sx * 50 - 18, 930 - 12, 540 + sx * 50 + 18, 930 + 12], fill=(255, 230, 120))
        paste_c(img, emoji("😨", 110), 230, 720, eob(k / 0.2))
    if t > v2["start"]:
        k = t - v2["start"]
        draw_char(img, "N", 560, 1000 + 40 * (1 - eo(k / 0.5)), t, "n", 0.8, arms=(-110, 15), hold=hold_lantern)
        paste_c(img, pill("BOORHI AMMA?!", 50, (150, 120, 200), WHITE), W / 2, 420, eob((k - 0.6) / 0.3), rot=3)
    draw_char(img, "H", 170, 1060, t, "shock", 0.85, arms=(-110, 20), hold=hold_packet)

def sc_inside17(img, t, lt):
    v1, v2, v3, v4, v5 = L("inside17")
    img.alpha_composite(bg_room("night")); bulb_glow(img, 70)
    gave = t > word_t(v4, "paanch", v4["start"] + 1.2) - 0.1
    draw_char(img, "N", 780, 1000, t, "sad" if t < v3["start"] else ("happy" if t > v4["start"] else "sad"), 0.85,
              arms=(-20, 20) if not (v4["start"] < t < v5["start"] + 0.5) else (-20, -60), hold=hold_notes500 if v4["start"] + 0.4 < t < v5["start"] else None)
    draw_char(img, "H", 280, 1010, t, "n" if t < v2["start"] else ("sad" if t < v3["start"] else "happy"), 0.88,
              arms=(-20, 20) if t < v5["start"] else (-130, 130), hold=hold_notes500 if t > v5["start"] else None)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, packet_open_img(), W / 2, 560, eob(k / 0.3) * 1.25)
        dt = word_t(v1, "dawaiyan", v1["start"] + 1.2)
        if t > dt - 0.1: paste_c(img, pill("DAWAIYAN!", 56, (60, 150, 255), WHITE), 300, 300, eob((t - dt + 0.1) / 0.3), rot=-4); paste_c(img, emoji("💊", 90), 860, 330, eob((t - dt) / 0.3))
        ct = word_t(v1, "chit", v1["end"] - 0.5)
        if t > ct - 0.1: paste_c(img, pill("…AUR EK CHIT", 50, YEL), 760, 780, eob((t - ct + 0.1) / 0.3), rot=4)
    elif t < v3["start"]:
        k = t - v2["start"]
        paste_c(img, chit17(), W / 2, 520, eob(k / 0.35) * 0.95, rot=-3)
        if k > 1.6:   # Amma's tears
            for sx in (-1, 1):
                q = ((k - 1.6) * 1.2 + (sx + 1) * 0.3) % 1
                ImageDraw.Draw(img).ellipse([780 + sx * 38 - 8, 950 + q * 70, 780 + sx * 38 + 8, 970 + q * 70], fill=(120, 190, 255))
    elif t < v4["start"]:
        k = t - v3["start"]
        call_inset(img, "R", 540, 560, t, "det", ((60, 120, 90), (30, 80, 60)), "SETH RAUF", eob(k / 0.3) * 0.85)
        paste_c(img, pill("SAKHT", 50, RED, WHITE), 200, 330, eob((k - 0.2) / 0.3), rot=-6); paste_c(img, emoji("😠", 80), 200, 440, eob((k - 0.3) / 0.3))
        nt = word_t(v3, "naram", v3["start"] + 1.6)
        if t > nt - 0.1: paste_c(img, pill("ANDAR SE NARAM", 50, GRN, WHITE), 800, 860, eob((t - nt + 0.1) / 0.3), rot=5); paste_c(img, emoji("🥹", 80), 960, 760, eob((t - nt) / 0.3))
    elif t < v5["start"]:
        k = t - v4["start"]
        paste_c(img, emoji("🤲", 120), 560, 400, eob(k / 0.3))
        paste_c(img, pill("DUA + Rs 500", 60, GRN, WHITE), W / 2, 250, eob((k - 0.4) / 0.3), rot=-3)
    else:
        k = t - v5["start"]
        paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 380, eob(k / 0.25), rot=3)
        for j in range(8):
            q = (k * 0.8 + j * 0.13) % 1
            paste_c(img, emoji(["⭐", "🎉"][j % 2], 56), 120 + j * 120, 200 + q * 900, 0.9, rot=q * 200)

def sc_cliff17(img, t, lt):
    v1, v2, ol = L("cliff17")
    img.alpha_composite(bg_road("night")); night_tint(img, 90)
    barrier(img)
    fl = (t * 3) % 1 < 0.5   # police light flash
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([700, 200, 1100, 600], fill=((230, 40, 50, 90) if fl else (40, 90, 255, 90)))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    guard_char(img, 820, 960, t, 0.95, arm_up=True)
    paste_c(img, pill("POLICE", 34, (40, 60, 120), WHITE), 820, 1180, 1.0)
    torch_beam(img, 680, 1080, 300, 900, 90)
    paste_c(img, bike_img(True, True), 330, 1260, 0.7)
    draw_char(img, "H", 260, 1000, t, "shock", 0.85, arms=(-60, -60))
    if t < v2["start"]:
        k = t - v1["start"]
        clock(img, 160, 420, 2.75); paste_c(img, pill("2:45 AM", 44, YEL), 160, 550, 1.0)
        nt = word_t(v1, "police", v1["start"] + 0.9)
        if t > nt - 0.1: paste_c(img, glow_text("POLICE NAKA!", "Anton-Regular.ttf", 130, WHITE, (40, 90, 255)), W / 2, 260, eob((t - nt + 0.1) / 0.25), rot=-3); paste_c(img, emoji("🚨", 100), 960, 420, eob((t - nt) / 0.3) * (1 + 0.08 * math.sin(t * 12)))
    else:
        k = t - v2["start"]
        paste_c(img, bubble([("KAGHAZ", INK), ("DIKHAO!", RED)], 50, tail="right"), 780, 520, eob(k / 0.25))
        gt = word_t(v2, "ghafoor", v2["start"] + 1.4)
        if t > gt - 0.1: paste_c(img, pill("KAGHAZ: GHAFOOR KE PAAS!", 46, RED, WHITE), W / 2, 260, eob((t - gt + 0.1) / 0.3) * (1 + 0.04 * math.sin(t * 14)), rot=-3); paste_c(img, emoji("😰", 90), 470, 700, eob((t - gt) / 0.3))

# ======================= DAY 18: Kaghaz Dikhao (police naka, Ghafoor asleep, Seth Rauf comes in pajamas, Bilal takes the Rs 500)
def police_light(img, t, cx=900, cy=400):
    fl = (t * 3) % 1 < 0.5
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([cx - 200, cy - 200, cx + 200, cy + 200], fill=((230, 40, 50, 90) if fl else (40, 90, 255, 90)))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
def naka_bg(img, t):
    img.alpha_composite(bg_road("night")); night_tint(img, 90); barrier(img); police_light(img, t)
def nightcap(img, x, y, sc, t):
    """Striped night cap with a pom-pom on a character's head (x, y = draw_char anchor)."""
    d = ImageDraw.Draw(img); hy = y - 70 * sc - 150 * sc; sw = math.sin(t * 3) * 10 * sc
    pts = [(x - 120 * sc, hy + 40 * sc), (x + 120 * sc, hy + 40 * sc), (x + 150 * sc + sw, hy - 110 * sc)]
    d.polygon(pts, fill=(90, 140, 230), outline=INK); d.line(pts + [pts[0]], fill=INK, width=int(6 * sc))
    for j in (0.35, 0.65):
        a = (lerp(pts[0][0], pts[2][0], j), lerp(pts[0][1], pts[2][1], j)); b = (lerp(pts[1][0], pts[2][0], j), lerp(pts[1][1], pts[2][1], j))
        d.line([a, b], fill=WHITE, width=int(14 * sc))
    d.rounded_rectangle([x - 130 * sc, hy + 20 * sc, x + 130 * sc, hy + 60 * sc], radius=int(18 * sc), fill=WHITE, outline=INK, width=int(5 * sc))
    d.ellipse([pts[2][0] - 26 * sc, pts[2][1] - 26 * sc, pts[2][0] + 26 * sc, pts[2][1] + 26 * sc], fill=WHITE, outline=INK, width=int(5 * sc))
@lru_cache(None)
def pillow_img():
    im = Image.new("RGBA", (520, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 20, 510, 200], radius=70, fill=(235, 235, 250), outline=INK, width=8)
    for x in range(60, 480, 70): d.line([(x, 40), (x + 20, 180)], fill=(200, 205, 235), width=6)
    return im
@lru_cache(None)
def chit18():
    im = Image.new("RGBA", (780, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 770, 410], radius=16, fill=(252, 248, 230), outline=INK, width=7)
    for y in range(100, 400, 70): d.line([(40, y), (740, y)], fill=(180, 200, 230), width=3)
    d.text((390, 130), "PAISE DOUBLE", font=fnt("Anton-Regular.ttf", 92), fill=(40, 60, 150), anchor="mm")
    d.text((390, 240), "KARKE LAATA HOON!", font=fnt("Anton-Regular.ttf", 80), fill=(40, 60, 150), anchor="mm")
    d.text((520, 345), "— BILAL ;)", font=fnt("Anton-Regular.ttf", 64), fill=(200, 110, 20), anchor="mm")
    return im

def sc_hook18(img, t, lt):
    naka_bg(img, t)
    (v0,) = L("hook18")
    guard_char(img, 820, 960, t, 0.95, arm_up=True); paste_c(img, pill("POLICE", 34, (40, 60, 120), WHITE), 820, 1180, 1.0)
    torch_beam(img, 680, 1080, 300, 900, 100)
    paste_c(img, bike_img(True, True), 330, 1260, 0.7)
    draw_char(img, "H", 260, 1000, t, "shock", 0.85, arms=(-60, -60))
    paste_c(img, pill("2:45 AM", 44, YEL), 160, 420, 1.0)
    kt = word_t(v0, "kaghaz", v0["start"] + 2.0)
    if t > 1.5: paste_c(img, bubble([("KAGHAZ", INK), ("DIKHAO!", RED)], 50, tail="right"), 780, 520, eob((t - 1.5) / 0.25))
    if t > kt - 0.1:
        k = t - kt + 0.1
        paste_c(img, glow_text("KAGHAZ: NAHI!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 260, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
        paste_c(img, emoji("📄", 100), 470, 700, eob((k - 0.1) / 0.3), rot=-10); paste_c(img, emoji("❌", 70), 500, 720, eob((k - 0.3) / 0.3))

def sc_naka18(img, t, lt):
    naka_bg(img, t)
    v1, v2 = L("naka18")
    guard_char(img, 820, 960, t, 0.95, arm_up=t < v2["start"]); paste_c(img, pill("HAVALDAR", 34, (40, 60, 120), WHITE), 820, 1180, 1.0)
    paste_c(img, bike_img(True, True), 330, 1260, 0.7)
    draw_char(img, "H", 260, 1000, t, "shock" if t < v2["start"] else "sad", 0.85, arms=(-60, -60) if t < v2["start"] else (-20, 20))
    if t < v2["start"]:
        k = t - v1["start"]
        tt = word_t(v1, "thane", v1["start"] + 1.3)
        paste_c(img, bubble([("BIKE THANE", INK), ("JAYEGI!", RED)], 50, tail="right"), 760, 500, eob(k / 0.25))
        if t > tt - 0.1:
            q = eo((t - tt + 0.1) / 0.6)
            paste_c(img, emoji("🚓", 170), lerp(1250, 830, q), 1330, 1.0)
            stamp(img, "THANA!", W / 2, 250, t - tt + 0.1, RED, -8, 120)
    else:
        k = t - v2["start"]
        paste_c(img, emoji("🚓", 170), 830, 1330, 1.0)
        paste_c(img, pill("BIKE GAYI =", 56, WHITE, INK), W / 2, 230, eob(k / 0.25), rot=-3)
        nt = word_t(v2, "naukri", v2["start"] + 1.0)
        if t > nt - 0.1:
            paste_c(img, glow_text("NAUKRI GAYI!", "Anton-Regular.ttf", 130, YEL, (230, 60, 70)), W / 2, 370, eob((t - nt + 0.1) / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=3)
            paste_c(img, emoji("😰", 100), 470, 640, eob((t - nt) / 0.3))

def sc_call18(img, t, lt):
    img.alpha_composite(bg_road("night")); night_tint(img, 110); police_light(img, t, 980, 300)
    v1, b1, v2, v3, vr, vh, b2, vr2 = L("call18")
    sad = t > vr["start"]
    draw_char(img, "H", 260, 1010, t, "det" if t < b1["start"] else ("shock" if t < v3["start"] else ("det" if t < vh["start"] else "sad" if t < vr2["start"] else "happy")), 0.88,
              arms=(-20, 110), hold=hold_phone)
    if t < v2["start"]:
        k = t - v1["start"]
        rows = [("GHAFOOR CHACHA", INK), ("CALLING…", (90, 90, 110))]
        paste_c(img, phone_card("CALLING", rows, v1["start"] + 0.2, t, (120, 150, 80), 600), 720, 640, eob(k / 0.3) * 0.9, rot=3)
        if t > b1["start"] - 0.1:
            kb = t - b1["start"] + 0.1
            paste_c(img, text_img("TRING… TRING…", "Anton-Regular.ttf", 90, WHITE, 8, INK), W / 2, 260, eob(kb / 0.2) * (1 + 0.05 * math.sin(t * 30)), rot=-4)
    elif t < v3["start"]:
        k = t - v2["start"]
        call_inset(img, "G", 760, 640, t, "sleep", ((70, 80, 120), (40, 45, 80)), "CHACHA GHAFOOR", eob(k / 0.3) * 0.95)
        zzz(img, 860, 420, t)
        stamp(img, "BAND!", 300, 300, k, RED, -8, 120)
        if k > 0.7: paste_c(img, text_img("KHURRR… KHURRR…", "Anton-Regular.ttf", 80, YEL, 8, INK), 700, 1000, eob((k - 0.7) / 0.25) * (1 + 0.05 * math.sin(t * 8)), rot=4); paste_c(img, emoji("😴", 90), 960, 1120, eob((k - 0.8) / 0.3))
    elif t < vr["start"]:
        k = t - v3["start"]
        paste_c(img, pill("AAKHRI UMEED…", 54, YEL), W / 2, 240, eob(k / 0.3), rot=-3)
        rows = [("SETH RAUF", (40, 110, 70)), ("CALLING… 3:00 AM", (90, 90, 110))]
        paste_c(img, phone_card("CALLING", rows, v3["start"] + 0.4, t, (40, 110, 70), 600), 720, 640, eob((k - 0.3) / 0.3) * 0.9, rot=3)
        paste_c(img, emoji("🙏", 90), 560, 1020, eob((k - 0.8) / 0.3))
    else:
        mood = "det" if t < vh["start"] else ("sad" if t < vr2["start"] else "n")
        loud = vr["start"] < t < vr["end"]
        call_inset(img, "R", 760, 620, t + (math.sin(t * 40) * 0.0), mood, ((60, 120, 90), (30, 80, 60)), "SETH RAUF", 0.95 * (1 + (0.02 * math.sin(t * 40) if loud else 0)))
        if t < vh["start"]:
            k = t - vr["start"]
            paste_c(img, glow_text("3 BAJE?!", "Anton-Regular.ttf", 130, WHITE, (230, 60, 70)), W / 2, 250, eob(k / 0.25), rot=-3)
            pt = word_t(vr, "pagal", vr["start"] + 1.0)
            if t > pt - 0.1: paste_c(img, glow_text("PAGAL HO?!", "Anton-Regular.ttf", 100, YEL, (230, 60, 70)), 700, 1000, eob((t - pt + 0.1) / 0.25) * (1 + 0.04 * math.sin(t * 16)), rot=5)
        elif t < b2["start"]:
            k = t - vh["start"]
            paste_c(img, bubble([("AAPKI AMMI KE", INK), ("GHAR SE…", (150, 120, 200))], 46, tail="left"), 330, 470, eob(k / 0.3))
            if k > 1.0: paste_c(img, emoji("🏠", 90), 560, 1040, eob((k - 1.0) / 0.3))
        elif t < vr2["start"]:
            k = t - b2["start"]
            paste_c(img, glow_text("…", "Anton-Regular.ttf", 160, WHITE, (90, 160, 255)), W / 2, 250, eob(k / 0.2))
        else:
            k = t - vr2["start"]
            paste_c(img, pill("10 MINUTE • WAHIN RUKO", 50, (40, 110, 70), WHITE), W / 2, 250, eob(k / 0.3), rot=-3)
            paste_c(img, emoji("😮", 90), 520, 1020, eob((k - 0.4) / 0.3))

def sc_rauf18(img, t, lt):
    naka_bg(img, t)
    v1, vr, v2 = L("rauf18")
    laugh = t > v2["start"]
    draw_char(img, "X", 840, 960, t, "happy" if laugh else "det", 0.9, arms=(-20, 20) if not laugh else (-20, -60), laugh=laugh)
    paste_c(img, pill("HAVALDAR", 34, (40, 60, 120), WHITE), 840, 1170, 1.0)
    paste_c(img, bike_img(True, True), 250, 1290, 0.6)
    draw_char(img, "H", 200, 1020, t, "shock" if t < vr["start"] else ("n" if t < v2["start"] else "happy"), 0.8, arms=(-20, 20))
    rx = lerp(1300, 520, eo((t - v1["start"]) / 0.9)); loud = vr["start"] < t < vr["end"]
    draw_char(img, "R", rx, 980 + (math.sin(t * 40) * 4 if loud else 0), t, "det" if t < v2["start"] else "happy", 0.9,
              arms=(-130, 20) if loud else (-20, 20), hold=hold_cup if t > word_t(vr, "chai", vr["start"] + 1.6) - 0.1 else None)
    nightcap(img, rx, 980, 0.9, t)
    paste_c(img, emoji("🩴", 70), rx + 70, 1400, 1.0, rot=-10)
    if t < vr["start"]:
        k = t - v1["start"]
        paste_c(img, pill("SETH RAUF AAYE!", 54, (40, 110, 70), WHITE), W / 2, 230, eob(k / 0.3), rot=-3)
        pt = word_t(v1, "pajame", v1["start"] + 1.2)
        if t > pt - 0.1:
            paste_c(img, glow_text("PAJAMA +", "Anton-Regular.ttf", 100, WHITE, (90, 160, 255)), W / 2, 370, eob((t - pt + 0.1) / 0.25), rot=3)
            paste_c(img, glow_text("EK CHAPPAL!", "Anton-Regular.ttf", 110, YEL, (255, 130, 40)), W / 2, 490, eob((t - pt - 0.3) / 0.25), rot=-3)
            if t > pt + 0.6: paste_c(img, emoji("😂", 90), 960, 640, eob((t - pt - 0.6) / 0.3))
    elif t < v2["start"]:
        k = t - vr["start"]
        paste_c(img, bubble([("YEH MERA", INK), ("BANDA HAI!", (40, 110, 70))], 50, tail="left"), 560, 330, eob(k / 0.25))
        ct = word_t(vr, "chai", vr["start"] + 1.6)
        if t > ct - 0.1: paste_c(img, pill("CHAI MERI TARAF SE!", 46, YEL), W / 2, 560, eob((t - ct + 0.1) / 0.3), rot=3); paste_c(img, emoji("☕", 80), 860, 660, eob((t - ct) / 0.3))
    else:
        k = t - v2["start"]
        paste_c(img, text_img("HA HA HA!", "Anton-Regular.ttf", 90, WHITE, 8, INK), 840, 560, eob(k / 0.25), rot=6)
        jt = word_t(v2, "jaane", v2["start"] + 1.4)
        if t > jt - 0.1: stamp(img, "JAANE DIYA!", W / 2, 280, t - jt + 0.1, GRN, -6, 110)

def sc_end18(img, t, lt):
    img.alpha_composite(bg_road("night")); night_tint(img, 70)
    vr, vh, b, va = L("end18")
    turned = b["start"] < t < va["start"]
    rx = 780 + (40 * eo((t - b["start"]) / 0.3) if turned else 0)
    draw_char(img, "R", rx, 980, t, "sad" if t < va["start"] else "happy", 0.9, arms=(-20, 20) if not turned else (-20, -150), hold=None)
    nightcap(img, rx, 980, 0.9, t)
    draw_char(img, "H", 280, 1010, t, "n" if t < va["start"] else "happy", 0.88, arms=(-20, 20) if t < va["start"] else (-130, 130))
    if t < vh["start"]: paste_c(img, pill("3:15 AM", 44, YEL), 160, 420, 1.0)
    if t < vh["start"]:
        k = t - vr["start"]
        paste_c(img, bubble([("AMMI…", INK), ("KAISI THIN?", (150, 120, 200))], 52, tail="right"), 740, 470, eob(k / 0.3))
    elif t < b["start"]:
        k = t - vh["start"]
        paste_c(img, bubble([("AAPKO BOHAT", INK), ("YAAD KAR RAHI THIN", (150, 120, 200))], 44, tail="left"), 380, 470, eob(k / 0.3))
        if k > 0.8: paste_c(img, emoji("❤️", 80), 560, 680, eob((k - 0.8) / 0.3) * (1 + 0.08 * math.sin(t * 6)))
    elif t < va["start"]:
        k = t - b["start"]
        for sx in (-1, 1):   # Seth's tears
            q = (k * 1.4 + (sx + 1) * 0.3) % 1
            ImageDraw.Draw(img).ellipse([rx + sx * 34 - 8, 930 + q * 70, rx + sx * 34 + 8, 950 + q * 70], fill=(120, 190, 255))
        paste_c(img, emoji("🥹", 110), 540, 560, eob(k / 0.2))
        paste_c(img, pill("SAKHT SETH…", 48, (40, 110, 70), WHITE), W / 2, 260, eob(k / 0.2), rot=-3)
    else:
        k = t - va["start"]
        paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 380, eob(k / 0.25), rot=3)
        for j in range(8):
            q = (k * 0.8 + j * 0.13) % 1
            paste_c(img, emoji(["⭐", "🎉"][j % 2], 56), 120 + j * 120, 200 + q * 900, 0.9, rot=q * 200)

def sc_cliff18(img, t, lt):
    img.alpha_composite(bg_room("day"))
    v1, v2, ol = L("cliff18")
    gt = word_t(v1, "ghayab", v1["end"] - 0.6)
    d = ImageDraw.Draw(img); d.rounded_rectangle([90, 1120, 990, 1290], radius=20, fill=(150, 100, 70), outline=INK, width=7)   # charpai/bed
    d.rectangle([110, 1090, 970, 1140], fill=(230, 220, 200), outline=INK, width=5)
    lift = eo((t - v1["start"] - 0.4) / 0.5)
    paste_c(img, pillow_img(), 720, 1050 - 220 * lift, 0.8, rot=-12 * lift)
    draw_char(img, "H", 300, 980, t, "n" if t < gt - 0.1 else "shock", 0.88, arms=(-20, 20) if lift < 0.1 else (-20, -110))
    clock(img, 150, 330, 8.0); paste_c(img, pill("SUBAH", 40, YEL), 150, 460, 1.0)
    if t < v2["start"]:
        if t > gt - 0.1:
            k = t - gt + 0.1
            paste_c(img, glow_text("Rs 500 GHAYAB!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 260, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
            paste_c(img, emoji("😱", 100), 900, 560, eob((k - 0.2) / 0.3))
    else:
        k = t - v2["start"]
        paste_c(img, chit18(), W / 2, 520, eob(k / 0.35) * 0.95, rot=-3)
        if k > 1.2: paste_c(img, pill("BILAL SCHEME 4.0?!", 50, (255, 130, 40), WHITE), W / 2, 800, eob((k - 1.2) / 0.3) * (1 + 0.04 * math.sin(t * 14)), rot=3)

# ======================= DAY 19: Jadugar Ka Dabba (Bilal's Scheme 4.0 at Sea View, the "double box" trickster, a camel, Ammi: Abbu ka ilaaj Karachi mein)
@lru_cache(None)
def bg_beach():
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im)
    for y in range(0, 900 * s, 4): d.rectangle([0, y, W * s, y + 4], fill=mixc((110, 190, 245), (235, 245, 250), y / (900 * s)))
    d.ellipse([760 * s, 560 * s, 920 * s, 720 * s], fill=(255, 225, 140))
    for cx_, cy_ in ((200, 330), (620, 240)):   # clouds
        for dx, dy, rr in ((-60, 10, 50), (0, -10, 65), (60, 10, 50)): d.ellipse([(cx_ + dx - rr) * s, (cy_ + dy - rr) * s, (cx_ + dx + rr) * s, (cy_ + dy + rr) * s], fill=WHITE)
    d.rectangle([0, 880 * s, W * s, 1120 * s], fill=(40, 130, 190))
    for k in range(5):
        y = 900 + k * 45
        for x in range(-40 + (k % 2) * 60, W, 120): d.arc([x * s, y * s, (x + 80) * s, (y + 30) * s], 200, 340, fill=(200, 235, 250), width=4 * s)
    d.polygon([(0, 1120 * s), (W * s, 1090 * s), (W * s, 1150 * s), (0, 1170 * s)], fill=(245, 250, 250))   # foam line
    d.rectangle([0, 1150 * s, W * s, H * s], fill=(236, 206, 150)); d.polygon([(0, 1170 * s), (W * s, 1150 * s), (W * s, 1160 * s), (0, 1180 * s)], fill=(236, 206, 150))
    r = np.random.default_rng(19)
    for _ in range(140):
        x_, y_ = r.uniform(0, W), r.uniform(1180, H); d.ellipse([x_ * s, y_ * s, (x_ + 6) * s, (y_ + 4) * s], fill=(210, 178, 120))
    for ux, col in ((120, (230, 60, 70)), (960, (255, 200, 60))):   # beach umbrellas far away
        d.line([(ux * s, 1060 * s), (ux * s, 1200 * s)], fill=INK, width=5 * s)
        d.chord([(ux - 80) * s, 1010 * s, (ux + 80) * s, 1110 * s], 180, 360, fill=col, outline=INK, width=4 * s)
    return ssf(im)

def tophat(img, x, y, sc, t=0.0, rot=0.0, cx=None, cy=None):
    """Jadugar's tall purple top hat (x, y = draw_char anchor) or free-standing at (cx, cy)."""
    hat = Image.new("RGBA", (340, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(hat)
    d.rectangle([80, 20, 260, 210], fill=(110, 50, 170), outline=INK, width=7)
    d.rectangle([84, 150, 256, 185], fill=(240, 190, 50))
    d.regular_polygon((170, 90, 28), 5, fill=(255, 220, 80), outline=INK)
    d.rounded_rectangle([20, 200, 320, 240], radius=16, fill=(70, 30, 110), outline=INK, width=7)
    if cx is None: cx, cy = x, y - 70 * sc - 112 * sc - 85 * sc + math.sin(t * 2.1 + hash("J") % 3) * 4 * sc
    paste_c(img, hat, cx, cy, sc, rot=rot)

@lru_cache(None)
def dabba_img(broken=False):
    im = Image.new("RGBA", (420, 340), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if not broken:
        d.rounded_rectangle([20, 60, 400, 320], radius=20, fill=(120, 50, 180), outline=INK, width=8)
        d.rectangle([20, 60, 400, 110], fill=(90, 30, 140), outline=INK, width=6); d.rounded_rectangle([150, 76, 270, 94], radius=8, fill=INK)  # note slot
        d.text((210, 185), "DOUBLE", font=fnt("Anton-Regular.ttf", 80), fill=(255, 220, 80), anchor="mm", stroke_width=4, stroke_fill=INK)
        d.text((210, 270), "BOX", font=fnt("Poppins-Black.ttf", 44), fill=WHITE, anchor="mm")
        for sx_, sy_ in ((60, 150), (360, 150), (70, 290), (350, 290)): d.regular_polygon((sx_, sy_, 18), 5, fill=(255, 220, 80))
    else:
        d.polygon([(20, 160), (190, 120), (200, 320), (30, 320)], fill=(120, 50, 180), outline=INK)
        d.line([(20, 160), (190, 120), (200, 320), (30, 320), (20, 160)], fill=INK, width=8)
        d.polygon([(230, 130), (400, 170), (390, 320), (220, 320)], fill=(120, 50, 180), outline=INK)
        d.line([(230, 130), (400, 170), (390, 320), (220, 320), (230, 130)], fill=INK, width=8)
        d.text((110, 240), "DOU", font=fnt("Anton-Regular.ttf", 60), fill=(255, 220, 80), anchor="mm"); d.text((310, 250), "BLE", font=fnt("Anton-Regular.ttf", 60), fill=(255, 220, 80), anchor="mm")
    return im
@lru_cache(None)
def raddi_img(k=0):
    im = Image.new("RGBA", (150, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([4, 4, 146, 106], fill=(232, 228, 210), outline=INK, width=4)
    for y in range(22, 100, 16): d.line([(16, y), (16 + 110 - (y * 7 + k * 13) % 40, y)], fill=(150, 150, 150), width=5)
    return im
def hold_dabba(img, x, y, sc): paste_c(img, dabba_img(), x, y + 250 * sc, sc * 0.75)

@lru_cache(None)
def camel_img(chew=0):
    """Beach camel with a colourful saddle cloth, side view facing LEFT. 640x700."""
    s = SS; im = Image.new("RGBA", (640 * s, 700 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); P = lambda *xy: [v * s for v in xy]
    fur, dk = (205, 160, 100), (170, 125, 75)
    for lx in (230, 290, 450, 510):   # legs
        d.rounded_rectangle(P(lx - 22, 400, lx + 22, 680), radius=18 * s, fill=fur if lx in (290, 510) else dk, outline=INK, width=6 * s)
        d.ellipse(P(lx - 34, 650, lx + 34, 696), fill=dk, outline=INK, width=5 * s)
    d.ellipse(P(190, 250, 590, 470), fill=fur, outline=INK, width=7 * s)       # body
    d.ellipse(P(300, 140, 480, 330), fill=fur, outline=INK, width=7 * s)       # hump
    d.chord(P(300, 150, 480, 330), 180, 360, fill=fur)
    d.polygon(P(240, 300, 300, 330, 320, 420, 250, 440), fill=(230, 60, 90), outline=INK)   # saddle cloth
    d.rectangle(P(320, 250, 470, 410), fill=(230, 60, 90), outline=INK, width=6 * s)
    for k in range(4): d.rectangle(P(330 + k * 36, 360, 350 + k * 36, 410), fill=(255, 210, 60))
    for k in range(6): d.ellipse(P(320 + k * 26, 404, 336 + k * 26, 422), fill=(60, 160, 220), outline=INK, width=2 * s)
    d.polygon(P(230, 300, 120, 120, 70, 130, 175, 330), fill=fur, outline=INK)    # neck
    d.line(P(230, 300, 120, 120), fill=INK, width=7 * s); d.line(P(70, 130, 175, 330), fill=INK, width=7 * s)
    d.ellipse(P(20, 60, 170, 170), fill=fur, outline=INK, width=7 * s)          # head
    d.ellipse(P(-10, 100, 80, 175), fill=fur, outline=INK, width=6 * s)          # snout
    d.ellipse(P(100, 40, 130, 80), fill=dk, outline=INK, width=4 * s)            # ear
    d.ellipse(P(70, 85, 104, 121), fill=WHITE, outline=INK, width=4 * s); d.ellipse(P(78, 97, 96, 115), fill=INK)
    d.line(P(66, 84, 108, 92), fill=INK, width=5 * s)                           # lazy eyelid
    d.arc(P(0, 140 + chew * 6, 60, 170 + chew * 6), 20, 160, fill=INK, width=5 * s)
    d.line(P(560, 300, 600, 420), fill=dk, width=12 * s)                        # tail
    return ssf(im)

@lru_cache(None)
def status_img():
    w, h = 560, 760; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=44, fill=(25, 25, 32), outline=INK, width=8)
    pic = grad((110, 190, 245), (40, 130, 190), 520).crop((0, 0, w - 48, 520)); im.alpha_composite(pic, (24, 110))
    d.rectangle([24, 500, w - 25, 630], fill=(236, 206, 150))
    d.rectangle([24, 24, w - 25, 110], fill=(30, 30, 40)); d.rounded_rectangle([40, 44, w - 40, 54], radius=4, fill=(200, 200, 210))
    d.text((w / 2, 85), "BILAL • STATUS", font=fnt("Poppins-Black.ttf", 26), fill=WHITE, anchor="mm")
    d.rectangle([24, 630, w - 25, h - 25], fill=(25, 25, 32))
    d.text((w / 2, 668), "PAISE DOUBLE", font=fnt("Anton-Regular.ttf", 46), fill=YEL, anchor="mm")
    d.text((w / 2, 712), "HO RAHE HAIN!", font=fnt("Anton-Regular.ttf", 40), fill=WHITE, anchor="mm")
    im.alpha_composite(head("L", "happy", 0, "up").resize((260, 260)), (150, 250))
    paste_c(im, emoji("😎", 70), 420, 260, 1.0)
    paste_c(im, pill("SEA VIEW", 30, RED, WHITE), w / 2, 570, 1.0)
    return im

def sand_puff(img, x, y, k, n=9, spread=160):
    if k < 0 or k > 1: return
    d = ImageDraw.Draw(img)
    for j in range(n):
        a = j / n * math.pi; rr = 30 + 40 * k
        px, py = x + math.cos(a) * spread * k * (0.6 + 0.4 * ((j * 7) % 3) / 2), y - math.sin(a) * spread * 0.6 * k
        al = int(220 * (1 - k)); d.ellipse([px - rr, py - rr * 0.7, px + rr, py + rr * 0.7], fill=(230, 200, 140, al))

def sc_hook19(img, t, lt):
    img.alpha_composite(bg_room("day"))
    (v0,) = L("hook19")
    d = ImageDraw.Draw(img); d.rounded_rectangle([90, 1120, 990, 1290], radius=20, fill=(150, 100, 70), outline=INK, width=7)
    d.rectangle([110, 1090, 970, 1140], fill=(230, 220, 200), outline=INK, width=5)
    paste_c(img, pillow_img(), 760, 860, 0.7, rot=-12)
    draw_char(img, "H", 300, 980, t, "shock", 0.9, arms=(-20, -110))
    paste_c(img, chit18(), 740, 640, 0.62, rot=-5)
    bt = word_t(v0, "bilal", v0["start"] + 1.6)
    if t > bt - 0.1:
        k = t - bt + 0.1
        paste_c(img, glow_text("Rs 500 GAYAB!", "Anton-Regular.ttf", 120, YEL, (230, 60, 70)), W / 2, 260, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
        paste_c(img, emoji("💸", 110), 860, 980, eob((k - 0.2) / 0.3), rot=10 * math.sin(t * 6))

def sc_status19(img, t, lt):
    img.alpha_composite(bg_room("day"))
    v1, v2 = L("status19")
    draw_char(img, "H", 260, 1010, t, "det" if t < v2["start"] else "shock", 0.88, arms=(-20, 110), hold=hold_phone)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, phone_card("CALLING", [("BILAL 😜" if False else "BILAL", INK), ("SWITCHED OFF", RED)], v1["start"] + 0.2, t, (255, 130, 40), 600), 720, 640, eob(k / 0.3) * 0.9, rot=3)
        bt = word_t(v1, "band", v1["start"] + 0.8)
        if t > bt - 0.1: stamp(img, "BAND!", 300, 300, t - bt + 0.1, RED, -8, 120)
    else:
        k = t - v2["start"]
        paste_c(img, status_img(), 720, 760, eob(k / 0.3) * 0.95, rot=3)
        st = word_t(v2, "sea", v2["start"] + 1.3)
        if t > st - 0.1:
            paste_c(img, glow_text("SEA VIEW!", "Anton-Regular.ttf", 130, YEL, (40, 130, 190)), W / 2, 250, eob((t - st + 0.1) / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
            paste_c(img, emoji("🏖️", 90), 300, 600, eob((t - st) / 0.3))

def sc_beach19(img, t, lt):
    img.alpha_composite(bg_beach())
    v1, vb1, vb2, vh, b = L("beach19")
    sweat = t > b["start"]
    # Jadugar + table with the box
    d = ImageDraw.Draw(img); d.rounded_rectangle([640, 1300, 960, 1330], radius=8, fill=(150, 100, 60), outline=INK, width=6)
    for lx in (670, 930): d.rectangle([lx - 8, 1330, lx + 8, 1500], fill=(120, 80, 50), outline=INK, width=4)
    jx = 800 + (math.sin(t * 30) * 4 if sweat else 0)
    draw_char(img, "J", jx, 930, t, "shock" if sweat else "happy", 0.85, arms=(-60, -130) if not sweat else (-20, 20))
    tophat(img, jx, 930, 0.85, t)
    paste_c(img, dabba_img(), 800, 1210, 0.5 * (1 + 0.04 * math.sin(t * 5)))
    for j in range(5):   # sparkles around the box
        a = t * 2 + j * 1.26; paste_c(img, emoji("✨", 40), 800 + math.cos(a) * 140, 1200 + math.sin(a) * 80, 1.0)
    hx = lerp(-200, 170, eo((t - vh["start"] + 0.3) / 0.5))
    draw_char(img, "L", 440, 1000, t, "happy" if t < vh["start"] else ("shock" if sweat else "n"), 0.85, arms=(-130, -60) if t < vh["start"] else (-20, 20))
    if t > vh["start"] - 0.3: draw_char(img, "H", hx, 1020, t, "det", 0.85, arms=(-20, -120))
    if t < vb1["start"]:
        k = t - v1["start"]
        paste_c(img, pill("SEA VIEW • 11 AM", 48, (40, 130, 190), WHITE), W / 2, 230, eob(k / 0.3), rot=-3)
        jt = word_t(v1, "jadugar", v1["start"] + 1.4)
        if t > jt - 0.1: paste_c(img, glow_text("JADUGAR?!", "Anton-Regular.ttf", 120, YEL, (110, 50, 170)), W / 2, 380, eob((t - jt + 0.1) / 0.25), rot=3); paste_c(img, emoji("🎩", 80), 940, 470, eob((t - jt) / 0.3))
    elif t < vb2["start"]:
        k = t - vb1["start"]
        paste_c(img, bubble([("500 DAALO…", INK), ("1000 NIKALO!", (110, 50, 170))], 50, tail="left"), 470, 470, eob(k / 0.25))
        dt = word_t(vb1, "daalo", vb1["start"] + 0.8)
        q = eo((t - dt) / 0.6)
        if 0 < q < 1: paste_c(img, notes_img(500, 200), lerp(470, 800, q), lerp(1150, 1170, q), 0.7 * (1 - 0.7 * q), rot=-20 * q)
        if t > dt + 0.6: paste_c(img, text_img("GULP!", "Anton-Regular.ttf", 70, WHITE, 7, INK), 800, 1080, eob((t - dt - 0.6) / 0.2), rot=-6)
    elif t < vh["start"]:
        k = t - vb2["start"]
        paste_c(img, glow_text("1 GHANTE MEIN", "Anton-Regular.ttf", 100, WHITE, (110, 50, 170)), W / 2, 260, eob(k / 0.25), rot=-3)
        paste_c(img, glow_text("DOUBLE!", "Anton-Regular.ttf", 140, YEL, (255, 120, 40)), W / 2, 400, eob((k - 0.2) / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=3)
        paste_c(img, emoji("🤑", 90), 470, 640, eob((k - 0.3) / 0.3))
    elif t < b["start"]:
        k = t - vh["start"]
        paste_c(img, bubble([("OYE JADUGAR!", INK), ("PEHLE DABBA KHOLO!", RED)], 46, tail="left"), 420, 470, eob(k / 0.25))
    else:
        k = t - b["start"]
        for sx in (-1, 1):   # sweat drops
            q = (k * 2 + (sx + 1) * 0.25) % 1
            ImageDraw.Draw(img).ellipse([jx + sx * 120 - 10, 860 + q * 60, jx + sx * 120 + 10, 886 + q * 60], fill=(120, 190, 255), outline=INK)
        paste_c(img, glow_text("…GULP", "Anton-Regular.ttf", 110, WHITE, (110, 50, 170)), W / 2, 300, eob(k / 0.2), rot=-3)
        paste_c(img, emoji("😰", 100), 960, 620, eob(k / 0.2))

def sc_chase19(img, t, lt):
    img.alpha_composite(bg_beach())
    v1, v2, v3 = L("chase19")
    if t < v2["start"]:
        k = t - v1["start"]
        jx = lerp(300, 1250, k / (v1["end"] - v1["start"] + 0.3))
        for j in range(4): ImageDraw.Draw(img).line([(jx - 220 - j * 40, 1000 + j * 60), (jx - 120 - j * 40, 1000 + j * 60)], fill=WHITE, width=10)
        draw_char(img, "J", jx, 980 + abs(math.sin(t * 14)) * -30, t, "shock", 0.8, arms=(60, 60), hold=hold_dabba)
        tophat(img, jx, 980 + abs(math.sin(t * 14)) * -30, 0.8, t, rot=-10)
        sand_puff(img, jx - 150, 1400, (k * 3) % 1, 6, 120)
        paste_c(img, glow_text("BHAAGA!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 280, eob(k / 0.25) * (1 + 0.04 * math.sin(t * 14)), rot=-4)
        paste_c(img, emoji("🏃", 100), 200, 520, eob((k - 0.2) / 0.3))
    elif t < v3["start"]:
        k = t - v2["start"]
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ride_who(lay, "H", 560, 1300, t, "shock", 1.0, tilt=6 * math.sin(t * 18), bounce=False)
        img.alpha_composite(lay)
        d = ImageDraw.Draw(img); d.chord([200, 1360, 920, 1560], 180, 360, fill=(236, 206, 150), outline=(200, 170, 110), width=6)   # sand swallowing the wheels
        sand_puff(img, 300, 1400, (k * 2.5) % 1, 8, 200)
        paste_c(img, glow_text("BIKE PHANS GAYI!", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), W / 2, 270, eob(k / 0.25), rot=-3)
        paste_c(img, text_img("VROOOM… VROOOM…", "Anton-Regular.ttf", 70, WHITE, 7, INK), W / 2, 420, eob((k - 0.3) / 0.25) * (1 + 0.05 * math.sin(t * 30)), rot=3)
        paste_c(img, emoji("😫", 90), 880, 760, eob((k - 0.4) / 0.3))
    else:
        k = t - v3["start"]
        gt = word_t(v3, "gira", v3["start"] + 1.8)
        fall = eo((t - gt + 0.25) / 0.3)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bx = lerp(150, 400, min(1, k / max(0.1, gt - v3["start"])))
        draw_char(lay, "L", bx, 1060 + abs(math.sin(t * 14)) * -25 * (1 - fall), t, "shock" if fall > 0 else "det", 0.85, arms=(70, -70) if fall < 0.5 else (-160, 160))
        lay = lay.rotate(-82 * fall, Image.BICUBIC, center=(bx, 1380))
        img.alpha_composite(lay)
        if fall > 0:
            sand_puff(img, bx + 300, 1400, (t - gt + 0.05) / 0.8, 10, 220)
            stamp(img, "DHADAAM!", W / 2, 300, t - gt + 0.05, (255, 130, 40), -8, 120)
            if t > gt + 0.4: paste_c(img, emoji("😂", 100), 900, 620, eob((t - gt - 0.4) / 0.3))
        else:
            paste_c(img, pill("BILAL BHI BHAAGA!", 54, (255, 130, 40), WHITE), W / 2, 260, eob(k / 0.3), rot=-3)

def sc_camel19(img, t, lt):
    img.alpha_composite(bg_beach())
    v1, b, v2 = L("camel19")
    cx = lerp(1300, 720, eo((t - v1["start"]) / 0.9))
    chew = int(t * 6) % 2
    if t < b["start"]:
        k = t - v1["start"]
        paste_c(img, camel_img(chew), cx, 1080, 0.85)
        jx = lerp(-150, 260, min(1, k / 2.0))
        draw_char(img, "J", jx, 980 + abs(math.sin(t * 14)) * -30, t, "det", 0.75, arms=(60, 60), hold=hold_dabba)
        tophat(img, jx, 980 + abs(math.sin(t * 14)) * -30, 0.75, t, rot=-10)
        ot = word_t(v1, "oont", v1["start"] + 1.4)
        paste_c(img, pill("TABHI SAAMNE…", 50, WHITE, INK), W / 2, 240, eob(k / 0.3), rot=-3)
        if t > ot - 0.1: paste_c(img, glow_text("OONT!", "Anton-Regular.ttf", 170, YEL, (255, 120, 40)), W / 2, 400, eob((t - ot + 0.1) / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=4); paste_c(img, emoji("🐪", 90), 900, 560, eob((t - ot) / 0.3))
    elif t < v2["start"]:
        k = t - b["start"]
        sh = 18 * (1 - min(1, k / 0.5)); ox, oy = math.sin(t * 90) * sh, math.cos(t * 70) * sh
        paste_c(img, camel_img(0), 720 + ox, 1080 + oy, 0.85)
        jx = lerp(260, 460, eo(k / 0.15))
        draw_char(img, "J", jx + ox, 980 + oy, t, "shock", 0.75, arms=(-150, 150))
        stamp(img, "DHAMM!", W / 2, 320, k, RED, -8, 150)
        for j in range(5):
            a = t * 6 + j * 1.26; paste_c(img, emoji("⭐", 50), jx + math.cos(a) * 150, 760 + math.sin(a) * 40, 1.0)
    else:
        k = t - v2["start"]
        paste_c(img, camel_img(chew), 800, 1080, 0.85)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_char(lay, "J", 430, 1000, t, "sleep", 0.7, arms=(-160, 160))
        lay = lay.rotate(80, Image.BICUBIC, center=(430, 1250)); img.alpha_composite(lay)
        tophat(img, 0, 0, 0.6, t, rot=30, cx=240, cy=1340)
        for j in range(4):
            a = t * 5 + j * 1.57; paste_c(img, emoji("⭐", 44), 230 + math.cos(a) * 110, 1100 + math.sin(a) * 30, 1.0)
        tt = word_t(v2, "dabba", v2["start"] + 1.8)
        if t < tt - 0.1:
            paste_c(img, dabba_img(), 560, 1360, 0.45, rot=-10)
            paste_c(img, glow_text("OONT SE TAKKAR!", "Anton-Regular.ttf", 110, WHITE, (255, 120, 40)), W / 2, 270, eob(k / 0.25), rot=-3)
        else:
            q = t - tt + 0.1
            paste_c(img, dabba_img(True), 560, 1370, 0.5)
            for j in range(10):   # raddi papers fly out
                a = -math.pi / 2 + (j - 4.5) * 0.28; r_ = 420 * eo(q / 0.8)
                paste_c(img, raddi_img(j), 560 + math.cos(a) * r_, 1330 + math.sin(a) * r_ + 300 * max(0, q - 0.8) ** 2, 0.6, rot=(j * 37 + q * 200) % 360)
            paste_c(img, glow_text("DABBA TOOT GAYA!", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), W / 2, 270, eob(q / 0.25), rot=-3)
        paste_c(img, text_img("chap… chap…", "Poppins-Black.ttf", 40, WHITE, 5, INK), 660, 860, 1.0, rot=-4)

def sc_box19(img, t, lt):
    img.alpha_composite(bg_beach())
    v1, vb, va = L("box19")
    d = ImageDraw.Draw(img)
    for j in range(6): paste_c(img, raddi_img(j), 120 + (j * 173) % 860, 1180 + (j * 37) % 60, 0.6, rot=(j * 53) % 360)
    nt = word_t(v1, "hamara", v1["start"] + 2.0)
    got = t > nt - 0.1
    draw_char(img, "H", 300, 1000, t, "shock" if t < nt - 0.1 else ("happy" if t < vb["start"] or t > va["start"] else "n"), 0.88,
              arms=(-20, 20) if not got else (-20, -120), hold=hold_notes500 if got else None)
    bl_sandy = True
    draw_char(img, "L", 780, 1010, t, "sad" if t > vb["start"] - 0.2 else "shock", 0.85, arms=(-20, 20))
    if bl_sandy:
        for j in range(7): d.ellipse([780 - 70 + j * 22, 930 + (j % 3) * 18, 780 - 58 + j * 22, 942 + (j % 3) * 18], fill=(215, 180, 120))
    for j in range(7): paste_c(img, raddi_img(j + 3), 150 + j * 130, 1400 + (j % 2) * 30, 0.6, rot=(j * 41) % 60 - 30)
    paste_c(img, dabba_img(True), 540, 1360, 0.5)
    if t < vb["start"]:
        k = t - v1["start"]
        paste_c(img, glow_text("SIRF RADDI!", "Anton-Regular.ttf", 130, WHITE, (150, 150, 150)), W / 2, 250, eob(k / 0.25), rot=-3)
        if got:
            q = t - nt + 0.1
            paste_c(img, glow_text("Rs 500 WAPAS!", "Anton-Regular.ttf", 120, YEL, (40, 190, 110)), W / 2, 400, eob(q / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=3)
            paste_c(img, emoji("💵", 90), 560, 620, eob((q - 0.2) / 0.3))
    elif t < va["start"]:
        k = t - vb["start"]
        paste_c(img, bubble([("SORRY YAAR…", INK), ("SCHEME 4.0 FAIL!", (255, 130, 40))], 46, tail="right"), 700, 470, eob(k / 0.25))
        if k > 0.9: stamp(img, "FAIL", 300, 300, k - 0.9, RED, -10, 110)
    else:
        k = t - va["start"]
        paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 380, eob(k / 0.25), rot=3)
        for j in range(8):
            q = (k * 0.8 + j * 0.13) % 1
            paste_c(img, emoji(["⭐", "🎉"][j % 2], 56), 120 + j * 120, 200 + q * 900, 0.9, rot=q * 200)

def sc_cliff19(img, t, lt):
    img.alpha_composite(bg_beach()); img.alpha_composite(Image.new("RGBA", (W, H), (230, 110, 60, 70)))
    va1, va2, vh, ol = L("cliff19")
    draw_char(img, "H", 260, 1010, t, "n" if t < va1["start"] + 0.6 else "shock", 0.88, arms=(-20, 110), hold=hold_phone)
    call_inset(img, "A", 760, 640, t, "sad", ((250, 225, 180), (230, 190, 150)), "AMMI", eob((t - va1["start"] + 0.3) / 0.3) * 0.95)
    if t < va2["start"]:
        k = t - va1["start"]
        kt = word_t(va1, "karachi", va1["start"] + 1.8)
        paste_c(img, pill("SHAAM 5 BAJE", 44, YEL), 230, 420, 1.0)
        if t > kt - 0.1:
            paste_c(img, glow_text("ABBU KARACHI!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 250, eob((t - kt + 0.1) / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
            paste_c(img, emoji("🏥", 90), 470, 700, eob((t - kt) / 0.3))
    elif t < vh["start"]:
        k = t - va2["start"]
        paste_c(img, glow_text("KAL SUBAH!", "Anton-Regular.ttf", 140, YEL, (230, 60, 70)), W / 2, 250, eob(k / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=3)
        clock(img, 170, 460, 8.0)
        paste_c(img, emoji("🚌", 90), 470, 700, eob((k - 0.2) / 0.3))
    else:
        k = t - vh["start"]
        paste_c(img, pill("ILAAJ: Rs ???", 60, RED, WHITE), W / 2, 240, eob(k / 0.3), rot=-3)
        pt = word_t(vh, "paanch", vh["start"] + 2.3)
        if t > pt - 0.1: paste_c(img, pill("JEB: Rs 500", 60, WHITE, GRN), W / 2, 370, eob((t - pt + 0.1) / 0.3), rot=3); paste_c(img, emoji("😰", 100), 470, 640, eob((t - pt) / 0.3))

# ======================= DAY 20: Hospital Ki Line (Abbu collapses at the bus adda, rickshaw Rs 400, hospital queue + parchi Rs 300, Bilal's garland, Abbu's folded Rs 200, operation Rs 50,000)
@lru_cache(None)
def bg_hospital(mode="day"):
    s = SS; im = Image.new("RGBA", (W * s, H * s)); d = ImageDraw.Draw(im); P = lambda *xy: [v * s for v in xy]
    wall = (200, 230, 215) if mode == "day" else (120, 140, 140)
    d.rectangle(P(0, 0, W, 1180), fill=wall)
    d.rectangle(P(0, 820, W, 1180), fill=mixc(wall, (90, 150, 130), 0.35))      # dado paint
    d.rectangle(P(0, 812, W, 826), fill=(70, 120, 105))
    for y in range(1180, H, 90):                                                   # tiled floor
        d.rectangle(P(0, y, W, y + 90), fill=(225, 225, 220) if (y // 90) % 2 else (205, 208, 205))
    for x in range(0, W, 120): d.line(P(x, 1180, x - 160, H), fill=(180, 182, 180), width=3 * s)
    for lx in (220, 860): d.rounded_rectangle(P(lx - 120, 40, lx + 120, 64), radius=10 * s, fill=(250, 255, 250), outline=INK, width=4 * s)   # tube lights
    d.rounded_rectangle(P(300, 110, 780, 210), radius=16 * s, fill=(30, 110, 160), outline=INK, width=6 * s)
    d.text(P(540, 160), "CITY HOSPITAL • OPD", font=fnt("Anton-Regular.ttf", 56 * s), fill=WHITE, anchor="mm")
    d.ellipse(P(800, 110, 900, 210), fill=WHITE, outline=INK, width=5 * s)        # red cross
    d.rectangle(P(838, 124, 862, 196), fill=RED); d.rectangle(P(814, 148, 886, 172), fill=RED)
    # parchi window (right)
    d.rectangle(P(700, 400, 1060, 820), fill=(240, 230, 200), outline=INK, width=7 * s)
    d.rectangle(P(740, 470, 1020, 700), fill=(60, 80, 100), outline=INK, width=6 * s)
    for gx in range(760, 1020, 40): d.line(P(gx, 470, gx, 700), fill=(170, 180, 190), width=4 * s)
    d.rectangle(P(700, 700, 1060, 740), fill=(150, 100, 70), outline=INK, width=5 * s)
    d.rounded_rectangle(P(720, 410, 1040, 462), radius=10 * s, fill=RED, outline=INK, width=4 * s)
    d.text(P(880, 436), "PARCHI • Rs 300", font=fnt("Anton-Regular.ttf", 40 * s), fill=WHITE, anchor="mm")
    # poster + door (left)
    d.rectangle(P(60, 330, 300, 640), fill=WHITE, outline=INK, width=5 * s)
    d.text(P(180, 380), "SAAF HAATH", font=fnt("Poppins-Black.ttf", 28 * s), fill=(30, 110, 160), anchor="mm")
    paste_c(im, emoji("🧼", 120 * s // 2), 180 * s, 510 * s, 1.0)
    return ssf(im)

def waiting_people(img, t, n=7, x0=120, x1=1040, y=1050, sc=0.75, seed=20):
    """Simple faceless queue of patients/relatives (back/side view) to show a long line."""
    r = np.random.default_rng(seed); d = ImageDraw.Draw(img)
    cols = [(150, 110, 160), (90, 140, 190), (200, 150, 90), (120, 160, 110), (180, 90, 90), (110, 110, 140), (210, 180, 120)]
    for j in range(n):
        x = lerp(x0, x1, j / max(1, n - 1)); s_ = sc * r.uniform(0.85, 1.05); bob = math.sin(t * 1.5 + j) * 3
        c = cols[j % len(cols)]
        d.rounded_rectangle([x - 70 * s_, y - 60 * s_ + bob, x + 70 * s_, y + 330 * s_], radius=int(50 * s_), fill=c, outline=INK, width=5)
        d.ellipse([x - 55 * s_, y - 190 * s_ + bob, x + 55 * s_, y - 70 * s_ + bob], fill=(60, 45, 40) if j % 3 else (230, 230, 230), outline=INK, width=5)

@lru_cache(None)
def haar_img():
    """Marigold garland (phoolon ka haar), worn/hanging loop. 380x520."""
    s = SS; im = Image.new("RGBA", (380 * s, 520 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for j in range(26):
        a = j / 26 * 2 * math.pi; x = 190 + math.sin(a) * 150; y = 240 + math.cos(a) * 220
        c = (255, 140, 20) if j % 2 else (255, 205, 40); r = 30
        d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=c, outline=(160, 70, 10), width=3 * s)
        d.ellipse([(x - 8) * s, (y - 8) * s, (x + 8) * s, (y + 8) * s], fill=(200, 80, 10))
    for j in range(3):   # tassel
        d.ellipse([(170 - 10 + j * 10) * s, (470 + j * 14) * s, (210 - 10 + j * 10) * s, (505 + j * 14) * s], fill=(230, 40, 60), outline=INK, width=2 * s)
    return ssf(im)
def hold_haar(img, x, y, sc): paste_c(img, haar_img(), x, y + 150 * sc, sc * 0.72)
def hold_notes200(img, x, y, sc): paste_c(img, notes_img(200, 180), x + 140 * sc, y + 190 * sc, sc * 0.8, rot=-12)
def hold_parchi(img, x, y, sc):
    p = Image.new("RGBA", (220, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(p)
    d.rectangle([4, 4, 216, 156], fill=(255, 250, 230), outline=INK, width=5); d.text((110, 46), "PARCHI", font=fnt("Anton-Regular.ttf", 46), fill=(30, 110, 160), anchor="mm")
    d.text((110, 110), "No. 101", font=fnt("Poppins-Black.ttf", 30), fill=INK, anchor="mm")
    paste_c(img, p, x + 140 * sc, y + 180 * sc, sc * 0.9, rot=-8)

def sc_hook20(img, t, lt):
    img.alpha_composite(bg_station("dawn"))
    (v0,) = L("hook20")
    paste_c(img, bus_img(), 640, 880, 0.9)
    gt = word_t(v0, "gir", v0["start"] + 1.6)
    fall = eo((t - gt + 0.3) / 0.35)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_char(img, "A", 880, 980, t, "shock" if fall > 0 else "n", 0.78, arms=(-20, 20) if fall <= 0 else (-120, -60))
    draw_char(lay, "B", 420, 960, t, "sleep" if fall > 0.5 else "sad", 0.78, arms=(-30, 30) if fall < 0.5 else (-150, 150))
    lay = lay.rotate(-72 * fall, Image.BICUBIC, center=(420, 1340)); img.alpha_composite(lay)
    draw_char(img, "H", 150, 1020, t, "shock" if fall > 0 else "happy", 0.82, arms=(-20, 20) if fall <= 0 else (-130, 40))
    paste_c(img, pill("SUBAH 7 BAJE", 48, YEL), W / 2, 250, 1.0, rot=-2)
    if fall > 0:
        q = t - gt + 0.3
        stamp(img, "DHAPP!", W / 2, 560, q, RED, -8, 130)
        paste_c(img, emoji("😱", 100), 200, 700, eob((q - 0.2) / 0.3))

def sc_adda20(img, t, lt):
    img.alpha_composite(bg_station("dawn"))
    va, vr, vp = L("adda20")
    # Abbu sitting weak on the bench, Ammi beside him, Hamid in front
    draw_char(img, "B", 420, 900, t, "sad", 0.75, arms=(-10, 10))
    draw_char(img, "A", 640, 900, t, "sad", 0.75, arms=(-20, -70))
    rx = lerp(1500, 860, eo((t - vr["start"] + 0.2) / 0.6)) if t > vr["start"] - 0.2 else 1600
    if t > vr["start"] - 0.2: paste_c(img, rickshaw_img(), rx, 1150, 0.95)
    draw_char(img, "H", 200, 1030, t, "shock" if va["start"] <= t < vp["start"] else "det", 0.85, arms=(-20, 20) if t < vp["start"] else (-20, 110),
              hold=(hold_notes500 if t < vp["start"] + 0.4 else None))
    if t < vr["start"]:
        k = t - va["start"]
        paste_c(img, glow_text("JALDI HOSPITAL!", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 260, eob(k / 0.25), rot=-3)
        paste_c(img, emoji("🚑", 100), 900, 470, eob((k - 0.2) / 0.3))
    elif t < vp["start"]:
        k = t - vr["start"]
        paste_c(img, bubble([("Rs 400!", RED), ("KAM NAHI HOGA.", INK)], 46, tail="right"), 720, 620, eob((k - 0.3) / 0.3))
        paste_c(img, pill("RICKSHAW", 46, (250, 200, 40)), W / 2, 250, eob(k / 0.3), rot=-3)
    else:
        k = t - vp["start"]
        q = eo(k / 0.6)
        if q < 1: paste_c(img, notes_img(400, 200), lerp(320, 760, q), lerp(1200, 1050, q), 0.7, rot=-20 * q)
        paste_c(img, pill("-Rs 400", 60, RED, WHITE), W / 2, 250, eob(k / 0.3), rot=-3)
        paste_c(img, pill("JEB: Rs 100", 60, WHITE, GRN), W / 2, 520, eob((k - 0.4) / 0.3), rot=3)

def sc_hosp20(img, t, lt):
    img.alpha_composite(bg_hospital())
    v1, v2, b, v3 = L("hosp20")
    waiting_people(img, t, 8, 160, 1000, 1060, 0.72)
    draw_char(img, "H", 230 if t < v2["start"] else 300, 1060, t, "shock" if t > v2["start"] else "sad", 0.85,
              arms=(-20, 20) if t < v3["start"] else (-150, 150))
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, glow_text("LAMBI LINE!", "Anton-Regular.ttf", 140, YEL, (30, 110, 160)), W / 2, 300, eob(k / 0.25) * (1 + 0.03 * math.sin(t * 10)), rot=-3)
        st = word_t(v1, "sau", v1["start"] + 1.0)
        if t > st - 0.1: paste_c(img, pill("100+ LOG", 56, RED, WHITE), W / 2, 450, eob((t - st + 0.1) / 0.3), rot=3); paste_c(img, emoji("😩", 90), 160, 620, eob((t - st) / 0.3))
    elif t < b["start"]:
        k = t - v2["start"]
        ring = Image.new("RGBA", (380, 120), (0, 0, 0, 0)); ImageDraw.Draw(ring).rounded_rectangle([4, 4, 376, 116], radius=30, outline=YEL, width=12)
        paste_c(img, ring, 880, 436, 1 + 0.06 * math.sin(t * 12))
        tt = word_t(v2, "teen", v2["start"] + 1.6)
        if t > tt - 0.1: paste_c(img, glow_text("PARCHI Rs 300", "Anton-Regular.ttf", 120, WHITE, (230, 60, 70)), W / 2, 280, eob((t - tt + 0.1) / 0.25), rot=-3)
    elif t < v3["start"]:
        k = t - b["start"]
        stamp(img, "Rs 200 KAM!", W / 2, 320, k, RED, -8, 130)
    else:
        k = t - v3["start"]
        paste_c(img, pill("JEB: Rs 100", 56, WHITE, GRN), 300, 260, 1.0, rot=-3)
        paste_c(img, pill("PARCHI: Rs 300", 56, RED, WHITE), 760, 260, 1.0, rot=3)
        paste_c(img, glow_text("AB KYA?!", "Anton-Regular.ttf", 150, YEL, (230, 60, 70)), W / 2, 450, eob(k / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=-3)
        paste_c(img, emoji("😰", 100), 560, 640, eob((k - 0.2) / 0.3))

def sc_bilal20(img, t, lt):
    img.alpha_composite(bg_hospital())
    v1, v2, v3 = L("bilal20")
    waiting_people(img, t, 4, 640, 1020, 1060, 0.68, seed=7)
    bx = lerp(1300, 720, eo((t - v1["start"] + 0.2) / 0.6))
    draw_char(img, "H", 280, 1040, t, "happy" if t < v2["start"] else "shock", 0.85, arms=(-20, 20) if t < v2["start"] else (-150, 150))
    draw_char(img, "L", bx, 1030, t, "happy" if t < v3["start"] else "n", 0.85, arms=(-130, -60) if t < v3["start"] else (-60, -130), hold=hold_haar)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, glow_text("BILAL AA GAYA!", "Anton-Regular.ttf", 120, YEL, (255, 130, 40)), W / 2, 280, eob(k / 0.25), rot=-3)
        paste_c(img, emoji("😎", 90), 920, 560, eob((k - 0.2) / 0.3))
    elif t < v3["start"]:
        k = t - v2["start"]
        paste_c(img, pill("PAISE? ❌", 56, RED, WHITE) if False else pill("PAISE? NAHI!", 56, RED, WHITE), W / 2, 240, eob(k / 0.3), rot=-3)
        ht = word_t(v2, "phoolon", v2["start"] + 1.4)
        if t > ht - 0.1:
            paste_c(img, glow_text("PHOOLON KA HAAR!", "Anton-Regular.ttf", 110, YEL, (255, 120, 40)), W / 2, 390, eob((t - ht + 0.1) / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=3)
            paste_c(img, emoji("🌼", 80), 160, 560, eob((t - ht) / 0.3))
    else:
        k = t - v3["start"]
        paste_c(img, bubble([("ABBU KA WELCOME", INK), ("TOH BANTA HAI!", (255, 130, 40))], 46, tail="right"), 650, 470, eob(k / 0.25))
        paste_c(img, emoji("🤦", 100), 200, 620, eob((k - 0.6) / 0.3), rot=-8)

def sc_abbu20(img, t, lt):
    img.alpha_composite(bg_hospital())
    v1, v2, vb, b, v3 = L("abbu20")
    d = ImageDraw.Draw(img)   # waiting bench
    d.rectangle([90, 1180, 700, 1220], fill=(60, 120, 170), outline=INK, width=6)
    for lx in (120, 660): d.rectangle([lx, 1220, lx + 22, 1330], fill=(80, 80, 90), outline=INK, width=4)
    nt = word_t(v1, "nikala", v1["start"] + 1.8)
    has = t > nt - 0.2
    given = t > b["start"] - 0.05
    draw_char(img, "A", 560, 880, t, "sad", 0.72, arms=(-20, 20))
    draw_char(img, "B", 260, 880, t, "n" if t > vb["start"] else "sad", 0.78, arms=(-15, -60) if has and not given else (-15, 15),
              hold=hold_notes200 if has and not given else None)
    draw_char(img, "H", 830, 1020, t, "happy" if t > v3["start"] else ("sad" if t > v2["start"] else "n"), 0.85,
              arms=(-110, 20) if given else (-20, 20), hold=(hold_parchi if t > v3["start"] else None))
    if given and t < v3["start"]: paste_c(img, notes_img(200, 180), 700, 1180, 0.7, rot=10)
    if t < v2["start"]:
        k = t - v1["start"]
        paste_c(img, pill("TABHI…", 56, WHITE, INK), W / 2, 250, eob(k / 0.3), rot=-3)
        if has: paste_c(img, emoji("✨", 70), 420, 1020, eob((t - nt + 0.2) / 0.3))
    elif t < vb["start"]:
        k = t - v2["start"]
        paste_c(img, glow_text("ABBU KI BACHAT", "Anton-Regular.ttf", 110, YEL, (150, 120, 90)), W / 2, 270, eob(k / 0.25), rot=-3)
        paste_c(img, pill("Rs 200 • TEH KIYE HUE", 46, WHITE, GRN), W / 2, 410, eob((k - 0.3) / 0.3), rot=3)
    elif t < b["start"]:
        k = t - vb["start"]
        paste_c(img, bubble([("RAKH LO…", INK), ("BETA.", (150, 120, 90))], 50, tail="left"), 360, 480, eob(k / 0.25))
    elif t < v3["start"]:
        k = t - b["start"]
        paste_c(img, emoji("🥹", 130), 820, 560, eob(k / 0.25))
        paste_c(img, emoji("❤️", 70), 560, 700 - k * 120, eob(k / 0.2))
    else:
        k = t - v3["start"]
        stamp(img, "PARCHI BAN GAYI!", W / 2, 260, k, GRN, -6, 100)
        at = word_t(v3, "aaj", v3["start"] + 1.0)
        if t > at - 0.1:
            paste_c(img, glow_text("AAJ BHI BACH GAYE!", "Anton-Regular.ttf", 100, YEL, (255, 120, 40)), W / 2, 430, eob((t - at + 0.1) / 0.25), rot=3)

def sc_cliff20(img, t, lt):
    img.alpha_composite(bg_hospital("eve")); img.alpha_composite(Image.new("RGBA", (W, H), (150, 20, 40, 60)))
    va1, va2, vh, ol = L("cliff20")
    d = ImageDraw.Draw(img); d.rectangle([60, 330, 380, 820], fill=(240, 240, 235), outline=INK, width=7)   # doctor's door
    d.rounded_rectangle([90, 360, 350, 420], radius=10, fill=(30, 110, 160)); d.text((220, 390), "DOCTOR", font=fnt("Anton-Regular.ttf", 44), fill=WHITE, anchor="mm")
    draw_char(img, "A", 330, 1010, t, "sad", 0.85, arms=(-20, -100))
    for sx in (-1, 1):   # tears
        q = (t * 1.5 + (sx + 1) * 0.3) % 1
        d.ellipse([330 + sx * 50 - 9, 960 + q * 70, 330 + sx * 50 + 9, 984 + q * 70], fill=(120, 190, 255), outline=INK, width=2)
    draw_char(img, "H", 790, 1020, t, "shock" if t > va1["start"] + 1.0 else "sad", 0.85, arms=(-20, 20) if t < vh["start"] else (-150, 150))
    if t < va2["start"]:
        k = t - va1["start"]
        ot = word_t(va1, "operation", va1["start"] + 1.6)
        if t > ot - 0.1:
            paste_c(img, glow_text("OPERATION!", "Anton-Regular.ttf", 160, WHITE, (230, 60, 70)), W / 2, 270, eob((t - ot + 0.1) / 0.25) * (1 + 0.03 * math.sin(t * 12)), rot=-3)
            paste_c(img, emoji("🏥", 100), 640, 520, eob((t - ot) / 0.3))
    elif t < vh["start"]:
        k = t - va2["start"]
        paste_c(img, glow_text("Rs 50,000", "Anton-Regular.ttf", 170, YEL, (230, 60, 70)), W / 2, 270, eob(k / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=3)
        ht = word_t(va2, "ek", va2["start"] + 1.5)
        if t > ht - 0.1: paste_c(img, pill("SIRF 1 HAFTA!", 60, RED, WHITE), W / 2, 450, eob((t - ht + 0.1) / 0.3), rot=-3); clock(img, 900, 600, 7.0)
    else:
        k = t - vh["start"]
        paste_c(img, pill("CHAHIYE: Rs 50,000", 58, RED, WHITE), W / 2, 250, eob(k / 0.3), rot=-3)
        st = word_t(vh, "sifar", vh["start"] + 2.0)
        if t > st - 0.1: paste_c(img, pill("JEB: Rs 0", 66, WHITE, GRN), W / 2, 390, eob((t - st + 0.1) / 0.3), rot=3); paste_c(img, emoji("😰", 100), 600, 600, eob((t - st) / 0.3))

# ======================= OUTRO HOOK (owner, 2026-11-15): every reel ends with "Agay Hamid kya karega? Follow karein…"
# Mark the last line of the script with "outro": true (Hamid vo). It plays over the cliffhanger frame.
def outro(img, t):
    ol = next((l for l in LINES if l.get("outro")), None)
    if not ol or t < ol["start"] - 0.15: return
    k = t - ol["start"] + 0.15
    img.alpha_composite(Image.new("RGBA", (W, H), (8, 6, 20, int(200 * eo(k / 0.3)))))
    paste_c(img, glow_text("AGAY HAMID", "Anton-Regular.ttf", 140, WHITE, (90, 160, 255)), W / 2, 560, eob(k / 0.3), rot=-3)
    paste_c(img, glow_text("KYA KAREGA?", "Anton-Regular.ttf", 150, YEL, (255, 120, 40)), W / 2, 720, eob((k - 0.25) / 0.3), rot=-3)
    paste_c(img, pill(f"FOLLOW KAREIN • DAY {META['day'] + 1} NEXT PART", 46, RED, WHITE), W / 2, 920, eob((k - 0.6) / 0.35) * (1 + 0.05 * math.sin(t * 8)))
    paste_c(img, emoji("👉", 110), W / 2, 1080, eob((k - 0.9) / 0.3) * (1 + 0.08 * math.sin(t * 10)))

SC = {"hook": sc_hook, "daycard": sc_daycard, "home": sc_home, "fees": sc_fees, "abbu": sc_abbu, "night": sc_night, "end": sc_end,
      "hook_dhaba": sc_hook_dhaba, "dhaba": sc_dhaba, "burn": sc_burn, "pay": sc_pay, "bilal": sc_bilal, "end_diary": sc_end_diary,
      "hook_scheme": sc_hook_scheme, "market": sc_market, "dummy": sc_dummy, "rooftop": sc_rooftop,
      "hook_tuition": sc_hook_tuition, "alarm": sc_alarm, "paper": sc_paper, "chain": sc_chain, "late": sc_late,
      "tuition": sc_tuition, "asleep": sc_asleep, "wake": sc_wake, "end_call": sc_end_call,
      "hook_dead": sc_hook_dead, "bijli": sc_bijli, "run": sc_run, "bilal_door": sc_bilal_door, "shop": sc_shop, "balance": sc_balance,
      "stranger": sc_stranger, "callback": sc_callback, "ticket": sc_ticket,
      "hook_station": sc_hook_station, "ammi": sc_ammi, "kabadi": sc_kabadi, "potli": sc_potli, "abbu_door": sc_abbu_door, "bus": sc_bus,
      "station": sc_station, "guard": sc_guard, "floor": sc_floor, "morning": sc_morning,
      "hook_bike": sc_hook_bike, "rickshaw": sc_rickshaw, "ghafoor": sc_ghafoor, "traffic": sc_traffic, "gali": sc_gali, "downhill": sc_downhill,
      "crash": sc_crash, "manager": sc_manager, "delivery": sc_delivery, "stairs": sc_stairs, "door": sc_door, "dent": sc_dent,
      "hook_rain": sc_hook_rain, "deal": sc_deal, "order": sc_order, "rain": sc_rain, "flood": sc_flood, "cake": sc_cake,
      "tdoor": sc_tdoor, "troom": sc_troom, "cliff": sc_cliff, "vnote": sc_vnote,
      "hook_fork": sc_hook_fork, "kick": sc_kick, "fork": sc_fork, "briefing": sc_briefing, "montage": sc_montage, "order3": sc_order3,
      "exam": sc_exam, "paper": sc_paper, "result": sc_result, "rush": sc_rush, "end_kid": sc_end_kid, "cliff9": sc_cliff9,
      "hook10": sc_hook10, "advance10": sc_advance10, "bilal10": sc_bilal10, "tips10": sc_tips10, "call10": sc_call10, "rauf10": sc_rauf10,
      "shift10": sc_shift10, "choice10": sc_choice10, "end10": sc_end10, "cliff10": sc_cliff10,
      "hook11": sc_hook11, "shart11": sc_shart11, "sleep11": sc_sleep11, "ghafoor11": sc_ghafoor11, "bus11": sc_bus11, "gate11": sc_gate11,
      "kid11": sc_kid11, "hall11": sc_hall11, "end11": sc_end11, "cliff11": sc_cliff11,
      "hook12": sc_hook12, "msg12": sc_msg12, "rauf12": sc_rauf12, "chase12": sc_chase12, "paid12": sc_paid12, "saleem12": sc_saleem12,
      "ghafoor12": sc_ghafoor12, "cliff12": sc_cliff12,
      "hook13": sc_hook13, "office13": sc_office13, "tuition13": sc_tuition13, "bilal13": sc_bilal13, "adda13": sc_adda13, "cliff13": sc_cliff13,
      "hook14": sc_hook14, "call14": sc_call14, "race14": sc_race14, "adda14": sc_adda14, "back14": sc_back14, "cliff14": sc_cliff14,
      "hook15": sc_hook15, "plan15": sc_plan15, "class15": sc_class15, "msg15": sc_msg15, "office15": sc_office15, "cliff15": sc_cliff15,
      "hook16": sc_hook16, "call16": sc_call16, "office16": sc_office16, "bilal16": sc_bilal16, "rauf16": sc_rauf16, "send16": sc_send16, "cliff16": sc_cliff16,
      "hook17": sc_hook17, "bilal17": sc_bilal17, "ride17": sc_ride17, "haveli17": sc_haveli17, "inside17": sc_inside17, "cliff17": sc_cliff17,
      "hook18": sc_hook18, "naka18": sc_naka18, "call18": sc_call18, "rauf18": sc_rauf18, "end18": sc_end18, "cliff18": sc_cliff18,
      "hook19": sc_hook19, "status19": sc_status19, "beach19": sc_beach19, "chase19": sc_chase19, "camel19": sc_camel19, "box19": sc_box19, "cliff19": sc_cliff19,
      "hook20": sc_hook20, "adda20": sc_adda20, "hosp20": sc_hosp20, "bilal20": sc_bilal20, "abbu20": sc_abbu20, "cliff20": sc_cliff20}


# ======================= COLD-OPEN HOOK (owner, 2026-11-19: "add an eye / ear catching hook in the start so people won't skip")
# Day 15+: meta.json "hook": {"text": "<2-4 BIG Roman words: the problem>", "emoji": "<object at stake>", "sub": "<optional small red line>"}.
# First ~1.5 s: white flash, screen shake, rotating burst behind a slammed-in headline (+ boom/whoosh sting in hamid_audio.py).
HOOK_LEN = 1.5
def hook_on(): return META.get("day", 0) >= 15 or "hook" in META
def hook_fx(img, t):
    hk = META.get("hook")
    if not hk or t >= HOOK_LEN: return img
    out = 1 - eio((t - (HOOK_LEN - 0.3)) / 0.3)
    if t < 0.55:   # shake
        a = 26 * (1 - t / 0.55); dx, dy = int(a * math.sin(t * 95)), int(a * math.cos(t * 71))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 255)); sh.alpha_composite(img, (max(dx, 0), max(dy, 0)), (max(-dx, 0), max(-dy, 0))); img = sh
    img.alpha_composite(Image.new("RGBA", (W, H), (10, 6, 20, int(110 * out))))   # dim the scene so the headline pops
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cx, cy = W / 2, 820
    for k in range(16):   # rotating burst
        a0 = k / 16 * 2 * math.pi + t * 0.9; a1 = a0 + math.pi / 16
        col = (255, 210, 40, int(150 * out)) if k % 2 else (230, 50, 60, int(150 * out))
        d.polygon([(cx, cy), (cx + math.cos(a0) * 1500, cy + math.sin(a0) * 1500), (cx + math.cos(a1) * 1500, cy + math.sin(a1) * 1500)], fill=col)
    img.alpha_composite(lay)
    k = min(1, t / 0.18); sc = (2.4 - 1.4 * eo(k)) * (1 + 0.03 * math.sin(t * 14))
    if hk.get("emoji"): paste_c(img, emoji(hk["emoji"], 220), W / 2, 560, eob((t - 0.1) / 0.2) * out, rot=-10 + 6 * math.sin(t * 9))
    paste_c(img, fit_text(hk["text"], 190, YEL, (230, 60, 70), 980), cx, cy, sc * out, rot=-4, alpha=max(0.0, min(1.0, out)))
    if hk.get("sub"): paste_c(img, pill(hk["sub"], 58, RED, WHITE), cx, cy + 190, eob((t - 0.3) / 0.2) * out, rot=3)
    if t < 0.09: img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - t / 0.09)))))
    return img

def frame(t, plain=False):
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
    if plain: return img.convert("RGB")
    if hook_on(): img = hook_fx(img, t)
    outro(img, t); hud(img, t); caption(img, t)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([80, 1868, W - 80, 1878], radius=5, fill=(70, 70, 90)); d.rounded_rectangle([80, 1868, 80 + (W - 160) * t / TOTAL, 1878], radius=5, fill=YEL)
    return img.convert("RGB")

# ======================= THUMBNAIL / COVER (owner, 2026-11-18: an eye-catching suspense thumbnail on every reel)
# meta.json "thumb": {"t": <seconds: the scene behind it>, "l1": "<white line>", "l2": "<big yellow line>",
#                     "emoji": "<the object of the suspense>", "tag": "<short red label, e.g. Rs 1,000>", "mood": "shock"}
# Writes thumb.png (1080x1920) + thumb.jpg, and the full render starts with THUMB_FRAMES frames of it, so the
# platforms' cover frame (Buffer thumbnailOffset ~0 ms on Instagram + TikTok) shows the thumbnail.
THUMB_FRAMES = 2
def fit_text(txt, size, color, glow, maxw=1000):
    while size > 60:
        im = glow_text(txt, "Anton-Regular.ttf", size, color, glow)
        if im.width - 80 <= maxw: return im
        size -= 8
    return glow_text(txt, "Anton-Regular.ttf", size, color, glow)
def make_thumb():
    th = META.get("thumb", {})
    t = float(th.get("t", LINES[0]["start"] + 0.8))
    bg = frame(t, plain=True).convert("RGBA").filter(ImageFilter.GaussianBlur(4))
    img = Image.new("RGBA", (W, H)); img.alpha_composite(bg)
    img.alpha_composite(Image.new("RGBA", (W, H), (10, 6, 20, 120)))
    vg = Image.new("L", (W, H), 0); ImageDraw.Draw(vg).ellipse([-260, 140, W + 260, H - 140], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(160)); red = Image.new("RGBA", (W, H), (150, 10, 30, 230)); red.putalpha(vg.point(lambda v: 230 - int(v * 0.9)))
    img.alpha_composite(red)
    # series + day badge (inside the 4:5 / 3:4 grid-crop safe zone)
    paste_c(img, pill(f"DAY {META['day']}", 64, YEL), W / 2, 330, 1.0, rot=-3)
    paste_c(img, text_img("HAMID: ZERO SE SHURU", "Poppins-Black.ttf", 40, WHITE, 5, INK), W / 2, 430, 1.0)
    # the object of the suspense, ringed in red
    ex, ey = 790, 790
    ring = Image.new("RGBA", (420, 420), (0, 0, 0, 0)); rd = ImageDraw.Draw(ring)
    rd.ellipse([10, 10, 410, 410], fill=(255, 255, 255, 40), outline=RED, width=18)
    paste_c(img, ring, ex, ey, 1.0)
    if th.get("emoji"): paste_c(img, emoji(th["emoji"], 230), ex, ey, 1.0, rot=-8)
    if th.get("tag"): paste_c(img, pill(th["tag"], 58, RED, WHITE), ex, ey + 250, 1.0, rot=4)
    paste_c(img, glow_text("?", "Anton-Regular.ttf", 200, YEL, (230, 60, 70)), ex + 200, ey - 190, 1.0, rot=12)
    # Hamid's big shocked face with a white rim
    mood = th.get("mood", "shock")
    hd = head("H", {"shock": "wide", "sad": "down", "happy": "happy", "det": "open"}.get(mood, "wide"),
              {"shock": 3, "sad": "sad", "happy": 0, "det": 1}.get(mood, 3), {"shock": "up", "sad": "sad", "happy": "up", "det": "angry"}.get(mood, "up"))
    hd = hd.resize((hd.width * 2, hd.height * 2), Image.LANCZOS)
    rim = Image.new("RGBA", (hd.width + 60, hd.height + 60), (0, 0, 0, 0)); a = hd.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    big = Image.new("L", rim.size, 0); big.paste(a, (30, 30)); big = big.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(3))
    rim.paste(Image.new("RGBA", rim.size, WHITE), (0, 0), big)
    sk = Image.new("RGBA", hd.size, SKIN["H"] + (255,)); sk.putalpha(hd.getchannel("A").point(lambda v: 255 if v > 100 else 0))
    rim.alpha_composite(sk, (30, 30)); rim.alpha_composite(hd, (30, 30))   # opaque skin under the semi-transparent stubble
    paste_c(img, rim, 330, 900, 1.0, rot=6)
    # sweat drops / shock lines
    d = ImageDraw.Draw(img)
    for k, (x1, y1, x2, y2) in enumerate(((90, 560, 150, 620), (60, 700, 140, 720), (560, 560, 510, 620))):
        d.line([(x1, y1), (x2, y2)], fill=YEL, width=14)
    # headline
    if th.get("l1"): paste_c(img, fit_text(th["l1"], 150, WHITE, (90, 160, 255)), W / 2, 1300, 1.0, rot=-3)
    paste_c(img, fit_text(th.get("l2", META.get("title", "").upper() + "?"), 200, YEL, (230, 60, 70)), W / 2, 1480, 1.0, rot=-3)
    paste_c(img, pill("POORI KAHANI DEKHO", 44, WHITE, INK), W / 2, 1690, 1.0)
    out = img.convert("RGB"); out.save(f"{D}/thumb.png"); out.save(f"{D}/thumb.jpg", quality=92)
    return out

if ONLY == "thumb":
    make_thumb(); print("thumb written:", f"{D}/thumb.png"); sys.exit()
if ONLY and ONLY.startswith("still:"):
    for tt in ONLY[6:].split(","): frame(float(tt)).save(f"{D}/still_{tt}.png")
    sys.exit()
THUMB = make_thumb()
n = int(TOTAL * FPS)
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", f"{D}/video.tmp.mp4"], stdin=subprocess.PIPE)
for k in range(THUMB_FRAMES): p.stdin.write(THUMB.tobytes())   # cover frames (audio is delayed to match at mux)
for k in range(n):
    p.stdin.write(frame(k / FPS).tobytes())
    if k % 300 == 0: print("frame", k, "/", n, flush=True)
p.stdin.close(); p.wait(); print("rc", p.returncode)
