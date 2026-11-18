"""Hamid: Zero Se Shuru — weekly LANDSCAPE episode builder (1920x1080, 30 fps). Separate from the daily vertical renderer.
Usage: hamid_render_wide.py <weekly dir> [still]      (weekly dir holds week.json + vo.json + vo/v##.wav)
Layout: each day's finished vertical reel (cut before its "follow" ending) sits at 1080 high on the left, a styled panel on the right
(series title, DIN n, title, city, money, diary note, week tracker with a moving Hamid head). New cards: title, opening, bridges,
closing cliffhanger, end card — drawn with the same characters/fonts as hamid_render.py. Music/SFX synthesized here (free)."""
import json, math, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
WD = sys.argv[1]; MODE = sys.argv[2] if len(sys.argv) > 2 else "full"
WEEK = json.load(open(f"{WD}/week.json")); VO = json.load(open(f"{WD}/vo.json"))
OUT = f"{WD}/build"; os.makedirs(OUT, exist_ok=True)

# ---- borrow the drawing kit (characters, fonts, pills) from the vertical renderer without running it
_stub = tempfile.mkdtemp()
json.dump({"total": 1, "lines": [], "scenes": []}, open(f"{_stub}/timeline.json", "w")); json.dump({"day": 0, "money": 0}, open(f"{_stub}/meta.json", "w"))
np.savez(f"{_stub}/lipsync.npz", H=np.zeros(1))
_src = open(f"{HERE}/hamid_render.py").read().split("\nif ONLY and ONLY.startswith")[0]
_argv = sys.argv; sys.argv = ["x", _stub]; K = {"__file__": f"{HERE}/hamid_render.py"}; exec(compile(_src, "hamid_render.py", "exec"), K); sys.argv = _argv
fnt, text_img, pill, paste_c, emoji, draw_char, head = K["fnt"], K["text_img"], K["pill"], K["paste_c"], K["emoji"], K["draw_char"], K["head"]
eo, eob, eio, lerp, mixc = K["eo"], K["eob"], K["eio"], K["lerp"], K["mixc"]
YEL, WHITE, RED, GRN, INK = K["YEL"], K["WHITE"], K["RED"], K["GRN"], K["INK"]
_ENV = K["ENV"]

W, H, FPS, SR = 1920, 1080, 30, 48000
VX, VW = 170, 608           # reel position/size on the canvas
PX = 880                    # panel left edge
TEMPO = 1.12
NW = WEEK.get("n", 1); ND = len(WEEK["days"])
def dnum(k): return WEEK["days"][k - 1].get("day", k)      # k = 1-based index in the week
def dcity(k): return "Karachi" if "Karachi" in WEEK["days"][k - 1]["city"] else "Lahore"
TX = WEEK.get("text", {})

def rs(n): return f"Rs {n:,}"

# ======================= backgrounds
def sky(top, bot, h=H):
    a = np.linspace(0, 1, h)[:, None]
    g = (np.array(top)[None, None, :] * (1 - a[..., None]) + np.array(bot)[None, None, :] * a[..., None])
    return Image.fromarray(np.repeat(g, W, 1).astype(np.uint8), "RGB").convert("RGBA")

_bgc = {}
def night_bg(city="Lahore"):
    if city in _bgc: return _bgc[city].copy()
    im = sky((10, 12, 34), (52, 44, 88)); d = ImageDraw.Draw(im); r = np.random.default_rng(7)
    for _ in range(140):
        x, y = r.uniform(0, W), r.uniform(0, 620); s = r.uniform(1, 3); d.ellipse([x, y, x + s, y + s], fill=(255, 255, 255, int(r.uniform(80, 220))))
    d.ellipse([1640, 90, 1760, 210], fill=(255, 236, 190))
    sil = (24, 22, 48)
    if city == "Karachi":
        x = -20
        while x < W:
            w = r.uniform(70, 150); h = r.uniform(180, 420); d.rectangle([x, H - h, x + w, H], fill=sil)
            for wy in range(int(H - h) + 18, H - 20, 34):
                for wx in range(int(x) + 12, int(x + w) - 14, 26):
                    if r.random() < 0.3: d.rectangle([wx, wy, wx + 9, wy + 12], fill=(255, 214, 120))
            x += w + 6
    else:   # Lahore: minar + domes + rooftops
        x = -20
        while x < W:
            w = r.uniform(80, 180); h = r.uniform(90, 200); d.rectangle([x, H - h, x + w, H], fill=sil); x += w + 4
        mx = 1500; d.polygon([(mx - 34, H - 150), (mx - 18, H - 520), (mx + 18, H - 520), (mx + 34, H - 150)], fill=sil)
        d.polygon([(mx - 26, H - 520), (mx, H - 610), (mx + 26, H - 520)], fill=sil); d.rectangle([mx - 38, H - 400, mx + 38, H - 384], fill=sil)
        for cx, rr in ((1180, 120), (1300, 80), (1060, 80)): d.ellipse([cx - rr, H - 230 - rr, cx + rr, H - 230 + rr], fill=sil); d.rectangle([cx - rr, H - 230, cx + rr, H], fill=sil)
    _bgc[city] = im
    return im.copy()

def shadow_box(img, x, y, w, h, rad=0, blur=26, a=160):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0)); ImageDraw.Draw(g).rounded_rectangle([x, y, x + w, y + h], radius=rad, fill=(0, 0, 0, a))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(blur)))

def diary_card(txt, w=600):
    im = Image.new("RGBA", (w, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, 149], radius=12, fill=(252, 246, 228), outline=INK, width=5)
    for ly in range(48, 150, 34): d.line([(18, ly), (w - 18, ly)], fill=(170, 200, 230), width=2)
    d.line([(64, 6), (64, 144)], fill=(230, 120, 120), width=3)
    d.text((86, 18), "DIARY", font=fnt("Poppins-Black.ttf", 24), fill=(230, 60, 70))
    f = fnt("Anton-Regular.ttf", 46)
    while f.getlength(txt) > w - 110 and f.size > 28: f = fnt("Anton-Regular.ttf", f.size - 2)
    d.text((86, 54), txt, font=f, fill=(40, 60, 170))
    return im

TRACK_Y = 960; TRACK_X0 = PX + 70; TRACK_DX = 132
def tracker(img, cur, days=ND):
    d = ImageDraw.Draw(img)
    d.line([(TRACK_X0, TRACK_Y), (TRACK_X0 + TRACK_DX * days, TRACK_Y)], fill=(90, 90, 130), width=8)
    if cur > 1: d.line([(TRACK_X0, TRACK_Y), (TRACK_X0 + TRACK_DX * (cur - 1), TRACK_Y)], fill=YEL, width=8)
    for k in range(1, days + 2):
        x = TRACK_X0 + TRACK_DX * (k - 1); last = k == days + 1
        done = k < cur; now = k == cur
        r = 30 if now else 24
        d.ellipse([x - r, TRACK_Y - r, x + r, TRACK_Y + r], fill=YEL if (done or now) else (60, 60, 96), outline=INK, width=5)
        d.text((x, TRACK_Y + 1), "?" if last else str(dnum(k)), font=fnt("Poppins-Black.ttf", (28 if now else 24) - (4 if dnum(min(k, days)) > 9 else 0)), fill=INK if (done or now) else WHITE, anchor="mm")
    d.text((TRACK_X0 - 30, TRACK_Y - 70), f"HAFTA {NW} KA SAFAR", font=fnt("Poppins-Black.ttf", 26), fill=(180, 180, 220))

def marker():
    h = head("H", "open", 0, "n"); return h.resize((h.width * 2 // 5 // 2 * 2, h.height * 2 // 5 // 2 * 2), Image.LANCZOS)  # SS=2 head -> ~120 px

def panel(day):
    c = WEEK["days"][day - 1]; img = night_bg(dcity(day))
    shadow_box(img, VX, 0, VW, H, 0, 30, 200)
    d = ImageDraw.Draw(img)
    img.alpha_composite(text_img("HAMID: ZERO SE SHURU", "Anton-Regular.ttf", 50, YEL, 5, INK), (PX, 46))
    paste_c(img, pill(f"HAFTA {NW}", 30, WHITE, INK), PX + 640, 82, 1.0)
    img.alpha_composite(text_img(f"DIN {dnum(day)}", "Anton-Regular.ttf", 170, WHITE, 8, INK), (PX - 4, 120))
    t = text_img(c["title"].upper(), "Anton-Regular.ttf", 84, YEL, 7, INK)
    if t.width > 900: t = t.resize((900, int(t.height * 900 / t.width)), Image.LANCZOS)
    img.alpha_composite(t, (PX, 340))
    paste_c(img, pill(c["city"].upper(), 34, (60, 150, 255), WHITE), PX + 20 + pill(c["city"].upper(), 34, (60, 150, 255), WHITE).width / 2, 488, 1.0)
    # money: start -> end
    y = 560; d.text((PX, y), "JEB", font=fnt("Poppins-Black.ttf", 30), fill=(180, 180, 220))
    up = c["money_end"] >= c["money_start"]
    a = pill(rs(c["money_start"]), 42, WHITE, INK); b = pill(rs(c["money_end"]), 42, GRN if up else RED, WHITE)
    img.alpha_composite(a, (PX, y + 44)); ax = PX + a.width + 22
    ay = y + 44 + a.height / 2 - 4
    d.polygon([(ax, ay - 9), (ax + 36, ay - 9), (ax + 36, ay - 24), (ax + 64, ay), (ax + 36, ay + 24), (ax + 36, ay + 9), (ax, ay + 9)], fill=WHITE, outline=INK)
    img.alpha_composite(b, (ax + 84, y + 44))
    dc = diary_card(c["diary"], 680).rotate(-2, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(dc, (PX, 700))
    tracker(img, day)
    return img

# ======================= card frames
def caption(img, txt, t, t0, t1):
    if not (t0 - 0.05 <= t < t1 + 0.2): return
    words = txt.split(); n = len(words)
    wts = np.array([max(2, len(w.strip(".,!?…"))) + 1.5 for w in words]); cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum()
    hl = max([i for i in range(n) if t0 + 0.03 + cum[i] * (t1 - t0 - 0.12) <= t] or [0])
    band = Image.new("RGBA", (W, 230), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
    for y in range(230): bd.line([(0, y), (W, y)], fill=(10, 8, 20, int(min(210, y * 1.6))))
    img.alpha_composite(band, (0, H - 230))
    parts = [text_img(w.upper(), "Poppins-Black.ttf", 46, YEL if i == hl else WHITE, 6, INK) for i, w in enumerate(words)]
    rows, row, rw = [], [], 0
    for p in parts:
        if row and rw + p.width > 1760: rows.append(row); row, rw = [], 0
        row.append(p); rw += p.width - 10
    if row: rows.append(row)
    y = H - 40 - 60 * len(rows)
    for r in rows[:3]:
        x = (W - sum(p.width - 10 for p in r)) / 2
        for p in r: img.alpha_composite(p, (int(x), int(y))); x += p.width - 10
        y += 60

_thumb = {}
def thumb(day, w):
    if (day, w) not in _thumb:
        src = Image.open(f"{OUT}/key{day}.png").convert("RGBA").crop((0, 0, 1080, 1400))
        im = src.resize((w, int(1400 * w / 1080)), Image.LANCZOS)
        m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=18, fill=255)
        fr = Image.new("RGBA", (im.width + 12, im.height + 12), (0, 0, 0, 0)); ImageDraw.Draw(fr).rounded_rectangle([0, 0, fr.width - 1, fr.height - 1], radius=22, fill=WHITE)
        fr.paste(im, (6, 6), m); _thumb[(day, w)] = fr
    return _thumb[(day, w)]

def set_lip(env):   # drive Hamid's mouth from the new narration
    _ENV.clear()
    if env is not None: _ENV["H"] = env

def card_title(img, t, D):
    img.alpha_composite(night_bg(TX.get("title_city", "Lahore")), (0, 0)); d = ImageDraw.Draw(img)
    for k, (kx, ky, kc) in enumerate(((980, 180, (230, 70, 80)), (1240, 120, (255, 200, 60)), (1400, 250, (70, 140, 230)))):
        kx += math.sin(t * 1.5 + k) * 14; ky += math.cos(t * 1.2 + k) * 10
        d.polygon([(kx, ky - 28), (kx + 22, ky), (kx, ky + 28), (kx - 22, ky)], fill=kc, outline=INK)
    k = eob((t - 0.2) / 0.5); paste_c(img, text_img("HAMID", "Anton-Regular.ttf", 210, YEL, 10, INK), 560, 300, k)
    paste_c(img, text_img("ZERO SE SHURU", "Anton-Regular.ttf", 150, WHITE, 9, INK), 560, 500, eob((t - 0.5) / 0.5))
    paste_c(img, pill(TX.get("title_pill", "HAFTA 1 • LAHORE SE KARACHI"), 46, RED, WHITE), 560, 680, eob((t - 0.9) / 0.4))
    paste_c(img, pill(TX.get("title_sub", "DIN 1 – 6 • POORI KAHANI"), 34, WHITE, INK), 560, 770, eob((t - 1.2) / 0.4))
    x = lerp(2300, 1440, eo((t - 0.1) / 0.8)); draw_char(img, "H", x, 600, t, "det", 1.25, arms=(-20, 40))

def card_open(img, t, D, vt):
    img.alpha_composite(night_bg(TX.get("title_city", "Lahore")), (0, 0))
    paste_c(img, text_img("IS HAFTE…", "Anton-Regular.ttf", 90, YEL, 7, INK), W / 2, 90, eob(t / 0.4))
    for k in range(ND):
        tk = 0.3 + k * 0.35; x = 190 + k * 308; y = lerp(1300, 420, eo((t - tk) / 0.6)) + math.sin(t * 1.6 + k) * 6
        paste_c(img, thumb(k + 1, 270), x, y, 1.0, rot=(-3 if k % 2 else 3))
        paste_c(img, pill(f"DIN {dnum(k + 1)}", 30, YEL), x, y - 200, eob((t - tk - 0.3) / 0.3))
        paste_c(img, pill(WEEK["days"][k]["title"].upper(), 22, WHITE, INK), x, y + 220, eob((t - tk - 0.4) / 0.3))
    caption(img, VO[0]["rom"], t, vt[0], vt[1])

def card_bridge(img, t, D, vt, day):
    c = WEEK["days"][day - 1]; img.alpha_composite(night_bg(dcity(day)), (0, 0))
    x0 = lerp(-400, 470, eo(t / 0.5)); paste_c(img, thumb(day, 420), x0, 470, 1.0, rot=-3)
    paste_c(img, text_img(f"DIN {dnum(day)}", "Anton-Regular.ttf", 200, WHITE, 9, INK), 1240, 300, eob((t - 0.15) / 0.4))
    tt = text_img(c["title"].upper(), "Anton-Regular.ttf", 110, YEL, 8, INK)
    paste_c(img, tt, 1240, 480, eob((t - 0.35) / 0.4) * min(1, 900 / tt.width))
    paste_c(img, pill(f"JEB: {rs(c['money_start'])}", 40, WHITE, GRN), 1240, 620, eob((t - 0.55) / 0.3))
    caption(img, VO[day - 1]["rom"], t, vt[0], vt[1])

def card_close(img, t, D, vt):
    base = Image.open(f"{OUT}/last.png").convert("RGBA")
    img.alpha_composite(panel_close(), (0, 0))
    img.alpha_composite(base.resize((VW, H), Image.LANCZOS), (VX, 0))
    dk = Image.new("RGBA", (VW, H), (0, 0, 0, int(120 * eio(t / 0.8)))); img.alpha_composite(dk, (VX, 0))
    items = [tuple(x) for x in TX["close_items"]] if "close_items" in TX else [("INTERVIEW: 9 AM", WHITE, INK), ("ADDRESS: 25 KM DOOR", YEL, INK), ("RICKSHAW: Rs 400", RED, WHITE), ("JEB: Rs 120", GRN, WHITE)]
    items = [(s, tuple(b), tuple(f)) for s, b, f in items]
    for k, (s, bg, fg) in enumerate(items):
        paste_c(img, pill(s, 50, bg, fg), PX + 400, 500 + k * 92, eob((t - 0.6 - k * 0.9) / 0.35), rot=(-2 if k % 2 else 2))
    caption(img, VO[ND]["rom"], t, vt[0], vt[1])

_pc = None
def panel_close():
    global _pc
    if _pc is None:
        img = night_bg("Karachi"); shadow_box(img, VX, 0, VW, H, 0, 30, 200)
        img.alpha_composite(text_img("HAMID: ZERO SE SHURU", "Anton-Regular.ttf", 50, YEL, 5, INK), (PX, 46))
        img.alpha_composite(text_img(TX.get("close_l1", "SUBAH 8:40…"), "Anton-Regular.ttf", 150, WHITE, 8, INK), (PX - 4, 130))
        img.alpha_composite(text_img(TX.get("close_l2", "AB KYA HOGA?"), "Anton-Regular.ttf", 90, YEL, 7, INK), (PX, 320))
        _pc = img
    return _pc

def card_end(img, t, D):
    img.alpha_composite(night_bg("Karachi"), (0, 0))
    paste_c(img, text_img("AGLA HAFTA…", "Anton-Regular.ttf", 120, YEL, 8, INK), 640, 260, eob((t - 0.1) / 0.4))
    paste_c(img, text_img(TX.get("end_l2", "KARACHI KA PEHLA DIN"), "Anton-Regular.ttf", 110, WHITE, 8, INK), 640, 420, eob((t - 0.4) / 0.4))
    paste_c(img, pill("SUBSCRIBE KAREIN • ROZ NAYI REEL", 44, RED, WHITE), 640, 590, eob((t - 0.8) / 0.4) * (1 + 0.04 * math.sin(t * 6)))
    paste_c(img, text_img("AAJ BHI BACH GAYE.", "Anton-Regular.ttf", 60, (200, 200, 240), 5, INK), 640, 720, eob((t - 1.3) / 0.4))
    draw_char(img, "H", 1450, 620, t, "happy", 1.2, arms=(-20, 130 + 25 * math.sin(t * 8)))
    if t > D - 0.6: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * eio((t - D + 0.6) / 0.6)))))

# ======================= audio helpers
def load(p, tempo=1.0):
    af = ["-af", f"atempo={tempo}"] if abs(tempo - 1) > 1e-3 else []
    return np.frombuffer(subprocess.check_output(["ffmpeg", "-v", "error", "-i", p] + af + ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]), np.float32).copy()
def trim(x, th=0.02):
    k = int(0.02 * SR); e = np.convolve(np.abs(x), np.ones(k) / k, mode="same"); idx = np.where(e > th * e.max())[0]
    return x[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.08 * SR)] if len(idx) else x
def envl(n, a=0.005, dcy=0.3): x = np.arange(n) / SR; return (np.minimum(x / a, 1) * np.exp(-x / dcy)).astype(np.float32)
def add(buf, sig, at, g=1.0):
    st = int(at * SR)
    if st >= len(buf): return
    m = min(len(sig), len(buf) - st); buf[st:st + m] += sig[:m] * g
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def piano(f, length, dcy=1.2):
    n = int(length * SR); x = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * h * x + h) for h, a in [(1, 1), (2, 0.45), (3, 0.2), (4, 0.1), (5, 0.05)])
    return (s * envl(n, 0.003, dcy) * np.exp(-x * 0.4)).astype(np.float32)
def pad(f, length):
    n = int(length * SR); x = np.arange(n) / SR; s = sum(np.sin(2 * np.pi * f * dt * x) for dt in (0.997, 1.0, 1.004)) / 3
    return (s * np.clip(np.minimum(x / 0.6, 1) * np.minimum((length - x) / 0.6, 1), 0, 1)).astype(np.float32)
def kick():
    n = int(0.3 * SR); x = np.arange(n) / SR
    return (np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-x * 30)) / SR) * np.exp(-x * 10)).astype(np.float32)
def music(D, hopeful, seed=0):
    buf = np.zeros(int(D * SR) + SR, np.float32); beat = 60 / 72
    prog = [[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]] if hopeful else [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    for b in range(int(D / (4 * beat)) + 1):
        ch = prog[(b + seed) % 4]; t0 = b * 4 * beat
        for m in ch: add(buf, pad(hz(m - 12), 4 * beat), t0, 0.05)
        add(buf, piano(hz(ch[0] - 12), 4 * beat, 2.0), t0, 0.22)
        arp = [ch[0], ch[1], ch[2], ch[1] + 12]
        for k in range(8 if hopeful else 4):
            add(buf, piano(hz(arp[k % 4] + 12), 1.4, 0.8), t0 + k * (beat / 2 if hopeful else beat), 0.11)
        if hopeful:
            for k in range(4): add(buf, kick(), t0 + k * beat, 0.3)
    return buf[:int(D * SR)]
WHOOSH = load(f"{HERE}/sfx/sfx_whoosh.mp3"); CHIME = load(f"{HERE}/sfx/sfx_chime.mp3")

# ======================= segment writers
def write_card(name, fn, D, vo_idx=None, hopeful=False, sfx=(), lip=False):
    a = music(D, hopeful, seed=len(name)); vt = (0, 0); env = None
    if vo_idx is not None:
        v = trim(load(f"{WD}/vo/v{vo_idx:02d}.wav", TEMPO)); v = v / (np.abs(v).max() + 1e-9) * 0.9
        add(a, v, 0.45); vt = (0.45, 0.45 + len(v) / SR)
        if lip:
            hop = SR // FPS; e = np.array([np.sqrt(np.mean(v[i:i + hop] ** 2)) for i in range(0, len(v), hop)])
            e = np.clip(e / (np.percentile(e[e > 0.01], 95) + 1e-9), 0, 1.2) if (e > 0.01).any() else e
            env = np.concatenate([np.zeros(int(0.45 * FPS)), e, np.zeros(int(D * FPS))])
    for at, s, g in sfx: add(a, {"whoosh": WHOOSH, "chime": CHIME}[s], at, g)
    fo = int(0.25 * SR); a[:fo] *= np.linspace(0, 1, fo); a[-fo:] *= np.linspace(1, 0, fo)
    a = np.clip(a, -1, 1); wav = f"{OUT}/{name}.f32"; a.astype(np.float32).tofile(wav)
    set_lip(env)
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", f"{OUT}/{name}.mp4"], stdin=subprocess.PIPE)
    for k in range(int(round(D * FPS))):
        t = k / FPS; img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        fn(img, t, D, vt) if vo_idx is not None else fn(img, t, D)
        if t < 0.25: img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t / 0.25)))))
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close(); p.wait(); set_lip(None); print("card", name, round(D, 2), "s", flush=True)
    return vt

def vo_len(i): return len(trim(load(f"{WD}/vo/v{i:02d}.wav", TEMPO))) / SR

def write_day(day):
    c = WEEK["days"][day - 1]; src = f"{ROOT}/{c['file']}"; S0 = c.get("start", 0.0); SP = WEEK.get("speed", 1.0); D = round((c["cut"] - S0) / SP, 3)
    panel(day).convert("RGB").save(f"{OUT}/panel{day}.png"); marker().save(f"{OUT}/marker.png")
    x0 = TRACK_X0 + TRACK_DX * (day - 1) - 60; x1 = x0 + TRACK_DX; my = TRACK_Y - 62
    fc = (f"[0:v]trim={S0}:{c['cut']},setpts=(PTS-STARTPTS)/{SP},scale={VW}:{H}:flags=lanczos[v];[1:v][v]overlay={VX}:0[b];"
          f"[b][2:v]overlay=x='{x0}+{x1 - x0}*t/{D}':y='{my}+4*sin(t*6)'[c];[c]fade=in:st=0:d=0.3,fade=out:st={D - 0.3}:d=0.3,format=yuv420p[o];"
          f"[0:a]atrim={S0}:{c['cut']},asetpts=PTS-STARTPTS,atempo={SP},aresample={SR},afade=in:st=0:d=0.15,afade=out:st={D - 0.35}:d=0.35[a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-loop", "1", "-framerate", str(FPS), "-i", f"{OUT}/panel{day}.png",
                    "-loop", "1", "-framerate", str(FPS), "-i", f"{OUT}/marker.png", "-filter_complex", fc, "-map", "[o]", "-map", "[a]",
                    "-t", str(D), "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "-ac", "2",
                    f"{OUT}/day{day}.mp4"], check=True)
    print("day", day, D, "s", flush=True)

def grab(day, t, out):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-i", f"{ROOT}/{WEEK['days'][day - 1]['file']}", "-frames:v", "1", out], check=True)

def thumbnail():
    img = night_bg("Karachi").resize((W, H)); d = ImageDraw.Draw(img)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([1050, 150, 1850, 1050], fill=(255, 200, 80, 90)); img.alpha_composite(g.filter(ImageFilter.GaussianBlur(80)))
    set_lip(None); draw_char(img, "H", 1440, 560, 0.5, "shock", 1.9, arms=(-30, 40))
    th = TX.get("thumb", [["Rs 120", 260, "GRN", 4], ["MEIN", 170, "WHITE", -2], ["KARACHI?!", 230, "YEL", -3]])
    for (s, sz, col, rot), y in zip(th, (300, 520, 760)):
        tt = text_img(s, "Anton-Regular.ttf", sz, {"GRN": GRN, "WHITE": WHITE, "YEL": YEL, "RED": RED}[col], 12, INK)
        paste_c(img, tt, 540, y, min(1.0, 1000 / tt.width), rot=rot)
    paste_c(img, pill(f"HAFTA {NW}", 60, RED, WHITE), 300, 960, 1.0)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(f"{WD}/thumbnail.jpg", quality=92)

if __name__ == "__main__":
    for k, dd in enumerate(WEEK["days"]): grab(k + 1, dd["key"], f"{OUT}/key{k + 1}.png")
    grab(ND, WEEK["days"][-1]["cut"] - 0.05, f"{OUT}/last.png")
    if MODE == "still":
        thumbnail()
        for k in range(1, ND + 1): panel(k).convert("RGB").save(f"{OUT}/panel{k}.png")
        for name, fn, ts, vi in (("title", card_title, (0.4, 1.2, 3.0), None), ("open", card_open, (1.0, 3.0, 6.0), 0),
                                 ("bridge3", lambda i, t, D, vt: card_bridge(i, t, D, vt, 3), (0.6, 1.5), 2),
                                 ("close", card_close, (1.5, 5.0), ND), ("end", card_end, (0.5, 2.5), None)):
            for t in ts:
                img = Image.new("RGBA", (W, H), (0, 0, 0, 255)); vt = (0.45, 0.45 + vo_len(vi)) if vi is not None else None
                fn(img, t, 5, vt) if vi is not None else fn(img, t, 5); img.convert("RGB").save(f"{OUT}/still_{name}_{t}.png")
        sys.exit()
    segs = []
    write_card("s00_title", card_title, 5.0, sfx=((0.15, "whoosh", 0.5), (1.0, "chime", 0.4))); segs.append("s00_title")
    write_card("s01_open", card_open, vo_len(0) + 1.4, 0, sfx=((0.3, "whoosh", 0.35),)); segs.append("s01_open")
    for day in range(1, ND + 1):
        if day > 1:
            write_card(f"s{day:02d}a_bridge", lambda i, t, D, vt, dd=day: card_bridge(i, t, D, vt, dd), vo_len(day - 1) + 1.15, day - 1,
                       sfx=((0.05, "whoosh", 0.45),)); segs.append(f"s{day:02d}a_bridge")
        write_day(day); segs.append(f"day{day}")
    write_card("s07_close", card_close, vo_len(ND) + 1.3, ND, sfx=((0.4, "chime", 0.35),)); segs.append("s07_close")
    write_card("s08_end", card_end, 5.5, hopeful=True, sfx=((0.1, "whoosh", 0.4),)); segs.append("s08_end")
    n = len(segs); ins = sum([["-i", f"{OUT}/{s}.mp4"] for s in segs], [])
    fc = "".join(f"[{i}:v][{i}:a]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a0];[a0]loudnorm=I=-14:TP=-1.5:LRA=11,aresample={SR}[a]"
    out = f"{WD}/{WEEK['out']}"
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + ins + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", out], check=True)
    thumbnail(); print("done", out)
