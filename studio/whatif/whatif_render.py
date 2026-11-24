"""Kya Hoga Agar? — daily What If reel renderer (Instagram Reels, 1080x1920).
Reuses the Hamid 2D engine (studio/hamid/hamid_render.py: characters, backgrounds, props, captions, cold-open hook fx)
WITHOUT changing it: the engine's code is loaded up to its render/main block, then this file overrides the HUD,
the ending card and the thumbnail, adds What If scenes to SC, and runs the same main block.
Usage: whatif_render.py <episode dir> [still:t1,t2,... | thumb]

Script line fields (script.json): who, mode (vo/talk/beat), scene (key in SC), dev (Urdu), rom (Roman caption),
optional "stamp" (timeline label shown top-right from this line on, e.g. "1 GHANTA BAAD"), "sfx" (see whatif_audio.py),
"pop": {"big": "...", "pill": "...", "emoji": "..."} (auto overlay at the top for that line), "final": true on the last line
(question to the viewer -> ending card "AAP KYA KAROGE? COMMENT KARO").
Add new scenes for each episode below (sc_<name>(img, t, lt)) and register them in WI_SC. Keep the flat 2D look."""
import os, sys
HR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hamid", "hamid_render.py")
_src = open(HR).read()
_MAIN = 'if ONLY == "thumb":'
assert _MAIN in _src, "hamid_render.py changed: main-block marker not found"
_eng, _main = _src.split(_MAIN, 1)
__file__ = os.path.abspath(HR)   # the engine finds its fonts/ next to itself
exec(compile(_eng, HR, "exec"), globals())

NAMES["N"] = ("NARRATOR", (90, 90, 120)); NAMES["H"] = ("HAMID", (60, 150, 255))
WI_BLUE = (60, 120, 255)

# ======================= HUD: series badge + timeline stamp
def hud(img, t):
    if t < HOOK_LEN + 0.2: return
    paste_c(img, pill(f"KYA HOGA AGAR? #{META['n']}", 36, YEL), 230, 110, 1.0)
    st = None; st0 = 0
    for l in LINES:
        if l.get("stamp") and l["start"] - 0.1 <= t: st, st0 = l["stamp"], l["start"]
    if st:
        k = t - st0 + 0.1
        paste_c(img, pill("⏱ " + st if False else st, 40, WHITE, RED), W - 220, 110, eob(k / 0.25) * (1 + 0.08 * max(0, 1 - k / 0.4)))

def pops(img, t):
    for l in LINES:
        p = l.get("pop")
        if not p or not (l["start"] - 0.05 <= t < l["end"] + 0.15): continue
        k = t - l["start"] + 0.05
        if p.get("big"): paste_c(img, fit_text(p["big"], 120, YEL, (230, 60, 70), 980), W / 2, 300, eob(k / 0.25), rot=-3)
        if p.get("pill"): paste_c(img, pill(p["pill"], 48, WHITE, INK), W / 2, 440, eob((k - 0.2) / 0.25), rot=2)
        if p.get("emoji"): paste_c(img, emoji(p["emoji"], 120), 900, 620, eob((k - 0.3) / 0.25))

# captions: same look as the Hamid engine, but long lines (4 rows) start higher so nothing hits the progress bar
def caption(img, t):
    cur = next((l for l in LINES if l.get("mode") != "beat" and l["start"] - 0.05 <= t < l["end"] + 0.2), None)
    if not cur: return
    ws = cur["words"]; hl = max([i for i, w in enumerate(ws) if w["t"] <= t] or [0])
    band = Image.new("RGBA", (W, 460), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
    for y in range(460): bd.line([(0, y), (W, y)], fill=(10, 8, 20, int(min(200, y * 1.2))))
    img.alpha_composite(band, (0, 1380))
    parts = [text_img(w["w"].replace('"', "").upper(), "Poppins-Black.ttf", 60, YEL if i == hl else WHITE, 6, INK) for i, w in enumerate(ws)]
    rows, row, rw = [], [], 0
    for p in parts:
        if row and rw + p.width > 980: rows.append(row); row, rw = [], 0
        row.append(p); rw += p.width - 10
    if row: rows.append(row)
    y = 1580 - 76 * max(0, len(rows) - 3)
    if cur["mode"] == "talk":
        nm, col = NAMES[cur["who"]]; paste_c(img, pill(nm, 34, col, WHITE), W / 2, y - 60, eob((t - cur["start"]) / 0.2))
    for r in rows[:5]:
        x = (W - sum(p.width - 10 for p in r)) / 2
        for p in r: img.alpha_composite(p, (int(x), int(y))); x += p.width - 10
        y += 76

# ======================= ending card: the question to the viewer
def outro(img, t):
    pops(img, t)
    fl = next((l for l in LINES if l.get("final")), None)
    if not fl or t < fl["start"] - 0.1: return
    k = t - fl["start"] + 0.1
    img.alpha_composite(Image.new("RGBA", (W, H), (8, 6, 20, int(190 * eo(k / 0.3)))))
    paste_c(img, glow_text("AAP KYA", "Anton-Regular.ttf", 150, WHITE, (90, 160, 255)), W / 2, 520, eob(k / 0.3), rot=-3)
    paste_c(img, glow_text("KAROGE?", "Anton-Regular.ttf", 170, YEL, (255, 120, 40)), W / 2, 690, eob((k - 0.2) / 0.3), rot=-3)
    if META.get("question"): paste_c(img, pill(META["question"].upper(), 40, WHITE, INK), W / 2, 870, eob((k - 0.5) / 0.3))
    paste_c(img, pill("COMMENT KARO • FOLLOW KARO", 46, RED, WHITE), W / 2, 980, eob((k - 0.8) / 0.35) * (1 + 0.05 * math.sin(t * 8)))
    paste_c(img, emoji("💬", 110), W / 2 - 120, 1140, eob((k - 1.0) / 0.3)); paste_c(img, emoji("👉", 110), W / 2 + 120, 1140, eob((k - 1.1) / 0.3) * (1 + 0.08 * math.sin(t * 10)))

# ======================= thumbnail / cover (first 2 frames of the video)
def make_thumb():
    th = META.get("thumb", {})
    t = float(th.get("t", LINES[0]["start"] + 0.8))
    bg = frame(t, plain=True).convert("RGBA").filter(ImageFilter.GaussianBlur(5))
    img = Image.new("RGBA", (W, H)); img.alpha_composite(bg)
    img.alpha_composite(Image.new("RGBA", (W, H), (8, 10, 40, 140)))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); cx, cy = W / 2, 820
    for k in range(16):
        a0 = k / 16 * 2 * math.pi; a1 = a0 + math.pi / 16
        d.polygon([(cx, cy), (cx + math.cos(a0) * 1500, cy + math.sin(a0) * 1500), (cx + math.cos(a1) * 1500, cy + math.sin(a1) * 1500)],
                  fill=(255, 210, 40, 60) if k % 2 else (60, 120, 255, 60))
    img.alpha_composite(lay)
    paste_c(img, pill(f"KYA HOGA AGAR? #{META['n']}", 56, YEL), W / 2, 330, 1.0, rot=-3)
    ex, ey = 790, 800
    ring = Image.new("RGBA", (420, 420), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([10, 10, 410, 410], fill=(255, 255, 255, 50), outline=YEL, width=18)
    paste_c(img, ring, ex, ey, 1.0)
    if th.get("emoji"): paste_c(img, emoji(th["emoji"], 230), ex, ey, 1.0, rot=-8)
    if th.get("tag"): paste_c(img, pill(th["tag"], 58, RED, WHITE), ex, ey + 250, 1.0, rot=4)
    paste_c(img, glow_text("?", "Anton-Regular.ttf", 200, YEL, (230, 60, 70)), ex + 200, ey - 190, 1.0, rot=12)
    mood = th.get("mood", "shock")
    hd = head("H", {"shock": "wide", "sad": "down", "happy": "happy", "det": "open"}.get(mood, "wide"),
              {"shock": 3, "sad": "sad", "happy": 0, "det": 1}.get(mood, 3), {"shock": "up", "sad": "sad", "happy": "up", "det": "angry"}.get(mood, "up"))
    hd = hd.resize((hd.width * 2, hd.height * 2), Image.LANCZOS)
    rim = Image.new("RGBA", (hd.width + 60, hd.height + 60), (0, 0, 0, 0)); a = hd.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    big = Image.new("L", rim.size, 0); big.paste(a, (30, 30)); big = big.filter(ImageFilter.MaxFilter(25)).filter(ImageFilter.GaussianBlur(3))
    rim.paste(Image.new("RGBA", rim.size, WHITE), (0, 0), big)
    sk = Image.new("RGBA", hd.size, SKIN["H"] + (255,)); sk.putalpha(hd.getchannel("A").point(lambda v: 255 if v > 100 else 0))
    rim.alpha_composite(sk, (30, 30)); rim.alpha_composite(hd, (30, 30))
    paste_c(img, rim, 330, 900, 1.0, rot=6)
    if th.get("l1"): paste_c(img, fit_text(th["l1"], 150, WHITE, WI_BLUE), W / 2, 1300, 1.0, rot=-3)
    paste_c(img, fit_text(th.get("l2", META.get("title", "").upper() + "?"), 190, YEL, (230, 60, 70)), W / 2, 1480, 1.0, rot=-3)
    paste_c(img, pill("END TAK DEKHO 👀" if False else "END TAK DEKHO", 44, WHITE, INK), W / 2, 1690, 1.0)
    out = img.convert("RGB"); out.save(f"{D}/thumb.png"); out.save(f"{D}/thumb.jpg", quality=92)
    return out

# ======================= shared What If helpers
def sky_stars(img, t, n=60, seed=3, y1=900):
    rs = np.random.default_rng(seed); d = ImageDraw.Draw(img)
    for j in range(n):
        x, y, r = rs.uniform(0, W), rs.uniform(150, y1), rs.uniform(2, 6)
        a = 0.5 + 0.5 * math.sin(t * rs.uniform(2, 5) + j)
        d.ellipse([x - r, y - r, x + r, y + r], fill=mixc((80, 90, 140), (255, 250, 220), a))
def globe(img, cx, cy, r, t, dark=0.0):
    g = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.ellipse([10, 10, 2 * r + 10, 2 * r + 10], fill=mixc((60, 140, 230), (20, 30, 60), dark), outline=INK, width=8)
    off = (t * 40) % (2 * r)
    for k, (bx, by, bw, bh) in enumerate(((0.2, 0.3, 0.35, 0.25), (0.55, 0.2, 0.3, 0.4), (0.3, 0.62, 0.25, 0.2), (0.75, 0.65, 0.2, 0.15))):
        x = 10 + ((bx * 2 * r + off) % (2 * r + 80)) - 40
        d.ellipse([x, 10 + by * 2 * r, x + bw * 2 * r, 10 + (by + bh) * 2 * r], fill=mixc((70, 190, 110), (25, 50, 40), dark))
    m = Image.new("L", g.size, 0); ImageDraw.Draw(m).ellipse([10, 10, 2 * r + 10, 2 * r + 10], fill=255)
    out = Image.new("RGBA", g.size, (0, 0, 0, 0)); out.paste(g, (0, 0), m)
    ImageDraw.Draw(out).ellipse([10, 10, 2 * r + 10, 2 * r + 10], outline=INK, width=8)
    paste_c(img, out, cx, cy, 1.0)
@lru_cache(None)
def nosignal_phone():
    im = phone_img(True).copy(); d = ImageDraw.Draw(im); w, h = im.size
    d.rectangle([w * 0.15, h * 0.2, w * 0.85, h * 0.8], fill=(30, 30, 40))
    d.text((w / 2, h * 0.42), "NO", font=fnt("Anton-Regular.ttf", int(w * 0.22)), fill=RED, anchor="mm")
    d.text((w / 2, h * 0.6), "SIGNAL", font=fnt("Anton-Regular.ttf", int(w * 0.16)), fill=WHITE, anchor="mm")
    return im
def hold_nosig(img, x, y, sc): paste_c(img, nosignal_phone(), x + 140 * sc, y + 150 * sc, sc * 0.9, rot=-10)
@lru_cache(None)
def card_machine(dead=True):
    im = Image.new("RGBA", (220, 340), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, 210, 330], radius=26, fill=(60, 60, 75), outline=INK, width=6)
    d.rounded_rectangle([34, 34, 186, 130], radius=10, fill=(30, 30, 40) if dead else (160, 230, 180))
    d.text((110, 82), "ERROR", font=fnt("Anton-Regular.ttf", 40), fill=RED, anchor="mm")
    for r in range(3):
        for c in range(3): d.rounded_rectangle([40 + c * 50, 160 + r * 50, 80 + c * 50, 196 + r * 50], radius=8, fill=(200, 200, 210), outline=INK, width=3)
    return im

# ======================= EPISODE 1: Internet Band (24 ghante bina internet)
def sc_hook_net(img, t, lt):
    img.alpha_composite(bg_room("night")); bulb_glow(img, 40)
    (v0,) = L("hook_net")
    globe(img, 540, 520, 230, t, dark=eo((t - 1.2) / 1.0))
    draw_char(img, "H", 300, 1010, t, "shock", 0.95, arms=(-20, 110), hold=hold_nosig)
    bt = word_t(v0, "band", v0["end"] - 0.5)
    if t > bt - 0.1:
        stamp(img, "BAND!", 760, 900, t - bt + 0.1, RED, -8, 130)
        for j in range(6):
            a = j / 6 * 2 * math.pi + t
            paste_c(img, emoji("📵", 70), 540 + math.cos(a) * 300, 520 + math.sin(a) * 300, eob((t - bt - j * 0.05) / 0.2))

def sc_title(img, t, lt):
    img.alpha_composite(grad((15, 20, 60), (60, 40, 120))); sky_stars(img, t, 50)
    globe(img, 540, 1150, 330, t, dark=0.5)
    paste_c(img, glow_text("KYA HOGA", "Anton-Regular.ttf", 170, WHITE, WI_BLUE), W / 2, 420, eob(lt / 0.3), rot=-3)
    paste_c(img, glow_text("AGAR…", "Anton-Regular.ttf", 190, YEL, (255, 120, 40)), W / 2, 600, eob((lt - 0.3) / 0.3), rot=-3)
    paste_c(img, pill(META.get("title_pill", "24 GHANTE • NO INTERNET"), 54, RED, WHITE), W / 2, 780, eob((lt - 1.0) / 0.3) * (1 + 0.04 * math.sin(t * 8)), rot=2)

def sc_room_net(img, t, lt):
    img.alpha_composite(bg_room("night")); bulb_glow(img, 50)
    vh, vn = L("room_net")
    if t < vn["start"]:
        k = t - vh["start"]
        draw_char(img, "H", 330, 1010, t, "shock", 0.95, arms=(-130, 110), hold=hold_nosig)
        paste_c(img, pill("WiFi ❌" if False else "WIFI: GAYA", 52, RED, WHITE), 780, 420, eob(k / 0.3), rot=4)
        dt_ = word_t(vh, "data", vh["start"] + 1.2)
        if t > dt_ - 0.1: paste_c(img, pill("DATA: 0", 52, RED, WHITE), 780, 540, eob((t - dt_ + 0.1) / 0.3), rot=-3); paste_c(img, emoji("😱", 100), 860, 700, eob((t - dt_) / 0.3))
        paste_c(img, emoji("📶", 110), 780, 290, eob(k / 0.3) * (0.6 + 0.4 * abs(math.sin(t * 6))))
    else:
        k = t - vn["start"]
        img.alpha_composite(grad((10, 12, 30), (30, 30, 60)))
        for r in range(4):
            for c in range(5):
                x, y = 140 + c * 200, 450 + r * 260
                q = eob((k - (r * 5 + c) * 0.04) / 0.25)
                paste_c(img, nosignal_phone(), x, y, 0.75 * q, rot=(r + c) % 3 * 6 - 6)
        paste_c(img, glow_text("ARBON PHONE…", "Anton-Regular.ttf", 110, WHITE, WI_BLUE), W / 2, 260, eob(k / 0.3), rot=-3)
        kt = word_t(vn, "khamosh", vn["end"] - 0.6)
        if t > kt - 0.1: stamp(img, "KHAMOSH", W / 2, 1300, t - kt + 0.1, RED, -6, 120)

def sc_shop_net(img, t, lt):
    img.alpha_composite(bg_bazaar())
    v1, vh, v2, b = L("shop_net")
    draw_char(img, "C", 800, 990, t, "n" if t < v2["start"] else "happy", 0.9, arms=(-20, 20) if t < v2["start"] else (-140, 20), laugh=v2["start"] < t < b["end"])
    draw_char(img, "H", 280, 1010, t, "det" if t < v2["start"] else "shock", 0.88, arms=(-20, 110), hold=hold_phone if t < v2["start"] else hold_notes)
    if t < vh["start"]:
        k = t - v1["start"]
        paste_c(img, card_machine(), 560, 620, eob(k / 0.3) * 0.9, rot=-6)
        at = word_t(v1, "atm", v1["start"] + 1.6)
        if t > at - 0.1: paste_c(img, pill("ATM: OUT OF SERVICE", 46, RED, WHITE), W / 2, 420, eob((t - at + 0.1) / 0.3), rot=-3)
        st = word_t(v1, "sab", v1["end"] - 0.5)
        if t > st - 0.1: stamp(img, "SAB BAND!", W / 2, 230, t - st + 0.1, RED, -6, 110)
    elif t < v2["start"]:
        k = t - vh["start"]
        paste_c(img, bubble([("ONLINE", INK), ("PAYMENT?", WI_BLUE)], 50, tail="left"), 330, 520, eob(k / 0.3))
        paste_c(img, emoji("🥺", 90), 560, 700, eob((k - 0.3) / 0.3))
    else:
        k = t - v2["start"]
        paste_c(img, glow_text("SIRF CASH!", "Anton-Regular.ttf", 150, YEL, (40, 150, 90)), W / 2, 330, eob((k - 0.6) / 0.25) * (1 + 0.04 * math.sin(t * 12)), rot=-4)
        paste_c(img, text_img("HA HA HA!", "Anton-Regular.ttf", 80, WHITE, 8, INK), 820, 560, eob(k / 0.25), rot=6)
        if t > b["start"] - 0.05:
            for j in range(8):
                q = ((t - b["start"]) * 1.2 + j * 0.13) % 1
                paste_c(img, emoji("💵", 60), 120 + j * 120, 200 + q * 700, 0.9, rot=q * 200)

def sc_city_net(img, t, lt):
    img.alpha_composite(bg_street("day"))
    v1, v2, vh = L("city_net")
    if t < v2["start"]:
        k = t - v1["start"]
        rows = [("ORDER #4471", INK), ("PENDING…", (230, 130, 40)), ("PENDING…", (230, 130, 40)), ("FAILED ✕" if False else "FAILED", RED)]
        paste_c(img, phone_card("ONLINE ORDER", rows, v1["start"] + 0.2, t, (230, 60, 70), 600), 300, 700, eob(k / 0.3) * 0.85, rot=-4)
        dt_ = word_t(v1, "daftar", v1["start"] + 1.8)
        if t > dt_ - 0.1:
            paste_c(img, pill("DAFTAR: KHAALI", 50, WHITE, INK), 780, 1100, eob((t - dt_ + 0.1) / 0.3), rot=4)
            paste_c(img, emoji("🏢", 150), 780, 900, eob((t - dt_) / 0.3)); paste_c(img, emoji("🦗", 70), 900, 980, eob((t - dt_ - 0.3) / 0.3))
    elif t < vh["start"]:
        k = t - v2["start"]
        draw_char(img, "K", 300, 1000, t, "shock", 0.82, arms=(-130, 20)); draw_char(img, "Z", 760, 1060, t, "n", 0.7, arms=(-130, 20))
        paste_c(img, pill("MAP: LOADING…", 48, RED, WHITE), W / 2, 300, eob(k / 0.3), rot=-3)
        paste_c(img, emoji("🗺️" if False else "🧭", 110), 540, 520, eob((k - 0.2) / 0.3) * (1 + 0.1 * math.sin(t * 10)), rot=20 * math.sin(t * 7))
        paste_c(img, bubble([("RAASTA?", INK)], 46, tail="right"), 760, 680, eob((k - 0.6) / 0.3))
    else:
        k = t - vh["start"]
        draw_char(img, "H", 300, 1010, t, "det", 0.88, arms=(-20, -100)); draw_char(img, "O" if False else "C", 790, 1000, t, "happy", 0.88, arms=(-140, 20))
        paste_c(img, bubble([("CHACHA, SADDAR", INK), ("KIDHAR HAI?", WI_BLUE)], 44, tail="left"), 330, 470, eob(k / 0.3))
        if k > 1.0: paste_c(img, text_img("SEEDHA… PHIR ULTA… PHIR SEEDHA!", "Poppins-Black.ttf", 40, YEL, 6, INK), W / 2, 330, eob((k - 1.0) / 0.3), rot=-3); paste_c(img, emoji("😵‍💫" if False else "😵", 90), 560, 720, eob((k - 1.2) / 0.3))

def sc_roof_net(img, t, lt):
    v1, v2, vh, b = L("roof_net")
    img.alpha_composite(bg_street("night")); sky_stars(img, t, 40 if t < vh["start"] else 160, y1=1000)
    if t < v2["start"]:
        k = t - v1["start"]
        draw_char(img, "H", W / 2, 1010, t, "n", 0.9, arms=(-20, 20))
        paste_c(img, glow_text("KUCH AISA HUA…", "Anton-Regular.ttf", 120, WHITE, (150, 90, 255)), W / 2, 320, eob((k - 0.8) / 0.3), rot=-3)
        paste_c(img, emoji("🤔", 100), 820, 620, eob((k - 1.0) / 0.3))
    elif t < vh["start"]:
        k = t - v2["start"]
        draw_char(img, "Z", 230, 1060, t, "happy", 0.7, arms=(-140, 60), laugh=True)
        draw_char(img, "K", 820, 1000, t, "happy", 0.8, arms=(-20, -120), laugh=True)
        paste_c(img, emoji("🏏", 120), 330, 860, eob(k / 0.3), rot=-30 + 20 * math.sin(t * 8))
        q = (k * 1.5) % 1; paste_c(img, emoji("⚾" if False else "🔴", 40), lerp(380, 900, q), 700 - 300 * 4 * q * (1 - q), 1.0)
        ct = word_t(v2, "cricket", v2["start"] + 1.4)
        if t > ct - 0.1: paste_c(img, pill("GALI CRICKET!", 52, GRN, WHITE), W / 2, 300, eob((t - ct + 0.1) / 0.3), rot=-3)
        pt = word_t(v2, "padosiyon", v2["end"] - 1.0)
        if t > pt - 0.1: paste_c(img, pill("PADOSI = DOST", 48, YEL), W / 2, 420, eob((t - pt + 0.1) / 0.3), rot=3)
    else:
        k = t - vh["start"]
        draw_char(img, "H", W / 2, 1010, t, "happy", 0.9, arms=(-150, 150))
        paste_c(img, bubble([("ITNE TAARE?!", INK)], 52, tail="left"), 380, 450, eob(k / 0.3))
        if t > b["start"] - 0.05: paste_c(img, emoji("✨", 120), 800, 400, eob((t - b["start"]) / 0.2) * (1 + 0.1 * math.sin(t * 9)))

def sc_back_net(img, t, lt):
    vw, b, v2, vh, fq = L("back_net")
    img.alpha_composite(bg_room("day"))
    draw_char(img, "H", 300, 1010, t, "shock" if t < vh["start"] else "happy", 0.9, arms=(-20, 110), hold=hold_phone)
    if t < b["start"]:
        k = t - vw["start"]
        globe(img, 760, 560, 200, t, dark=1 - eo((k - 0.8) / 0.6))
        wt = word_t(vw, "wapis", vw["end"] - 0.6)
        if t > wt - 0.1: paste_c(img, glow_text("WAPIS!", "Anton-Regular.ttf", 160, YEL, (40, 190, 110)), W / 2, 260, eob((t - wt + 0.1) / 0.25), rot=-4); paste_c(img, emoji("📶", 110), 900, 860, eob((t - wt) / 0.3))
    elif t < vh["start"]:
        k = t - b["start"]
        n_ = int(min(14, k * 9))
        for j in range(n_):
            rs = np.random.default_rng(j); x, y = rs.uniform(560, 960), rs.uniform(250, 1150)
            paste_c(img, pill(["🔔 99+", "💬 NEW", "❤️ LIKE", "📩 MSG"][j % 4] if False else ["99+", "NEW MSG", "LIKE", "TAG"][j % 4], 34, [RED, WI_BLUE, (230, 90, 140), GRN][j % 4], WHITE), x, y, eob((k - j / 9) / 0.15), rot=rs.uniform(-10, 10))
        if t > v2["start"]:
            st = word_t(v2, "scroll", v2["end"] - 0.6)
            paste_c(img, pill("HAZAAROn NOTIFICATIONS" if False else "HAZAARON NOTIFICATIONS", 46, RED, WHITE), W / 2, 230, eob((t - v2["start"]) / 0.3), rot=-3)
            if t > st - 0.1: stamp(img, "SCROLL…", 680, 1200, t - st + 0.1, WI_BLUE, -6, 110)
    else:
        k = t - vh["start"]
        sky_stars(img, t, 0)
        paste_c(img, bubble([("PAR WOH RAAT…", INK), ("YAAD RAHEGI", (150, 90, 255))], 48, tail="left"), 380, 470, eob(k / 0.3))
        paste_c(img, emoji("🌌", 120), 800, 700, eob((k - 0.4) / 0.3))


# ======================= EPISODE 2: Gravity Gayab (7 second bina gravity; the 12 August 2026 hoax)
def drift(t, t0, amp, dur=2.0, seed=0): return -amp * eio((t - t0) / dur) + 10 * math.sin(t * 2.3 + seed)
def floaters(img, t, t0, items, amp=520, y0=1330, spin=60):
    for j, (e, x, sz) in enumerate(items):
        y = y0 + drift(t, t0 + j * 0.12, amp * (0.6 + 0.4 * ((j * 37) % 10) / 10), 2.2, j)
        paste_c(img, emoji(e, int(sz * 1.7)), x, y, eob((t - t0 + 0.3) / 0.3), rot=math.sin(t * 1.5 + j) * spin)
def shake(img, t, t0, a=22, dur=0.5):
    k = t - t0
    if 0 <= k < dur:
        a = a * (1 - k / dur); dx, dy = int(a * math.sin(k * 90)), int(a * math.cos(k * 70))
        sh = img.copy(); img.paste((0, 0, 0, 255), [0, 0, W, H]); img.alpha_composite(sh, (max(dx, 0), max(dy, 0)), (max(-dx, 0), max(-dy, 0)))
def drops(img, x, y, t, n=6):
    d = ImageDraw.Draw(img)
    for j in range(n):
        a = j / n * 2 * math.pi + t * 0.8; r = 70 + 20 * math.sin(t * 2 + j); q = 10 + 6 * (j % 3)
        cx, cy = x + math.cos(a) * r, y + math.sin(a) * r * 0.7
        d.ellipse([cx - q, cy - q, cx + q, cy + q], fill=(150, 90, 50), outline=INK, width=3)
def ruler(img, x, y_floor, h_px, k):
    d = ImageDraw.Draw(img); top = y_floor - h_px * eo(k / 0.4)
    d.line([(x, y_floor), (x, top)], fill=YEL, width=10)
    for yy in (y_floor, top): d.line([(x - 40, yy), (x + 40, yy)], fill=YEL, width=10)

def sc_hook_grav(img, t, lt):
    img.alpha_composite(bg_room("day"))
    floaters(img, t, 0.0, [("☕", 180, 70), ("📱", 880, 64), ("👟", 300, 80), ("📚", 760, 80), ("🍎", 520, 60), ("🧢", 960, 70)], amp=700)
    draw_char(img, "H", 540, 1000 + drift(t, 0.3, 120, 2.5), t, "shock", 0.92, arms=(-150, 150))
    (v0,) = L("hook_grav")
    st = word_t(v0, "sirf", v0["end"] - 1.0)
    if t > st - 0.1: stamp(img, "7 SECOND!", W / 2, 300, t - st + 0.1, RED, -6, 120)

def sc_room_grav(img, t, lt):
    vh, vn, b = L("room_grav")
    img.alpha_composite(bg_room("day"))
    if t < vn["start"]:
        k = t - vh["start"]
        draw_char(img, "H", 330, 1010, t, "shock", 0.95, arms=(-20, -120))
        cy = 1060 + drift(t, vh["start"], 520, 1.8)
        paste_c(img, emoji("☕", 170), 540, cy, 1.0, rot=k * 40)
        drops(img, 520, cy - 40, t, int(min(6, k * 6)))
        paste_c(img, pill("CUP: UD GAYA!", 52, RED, WHITE), 780, 300, eob((k - 0.6) / 0.3), rot=4)
    else:
        k = t - vn["start"]
        lift = 260 * eio(k / 2.5) + 12 * math.sin(t * 2)
        floaters(img, t, vn["start"] - 0.5, [("☕", 820, 90), ("📱", 160, 70), ("🧸", 900, 80)], amp=500, y0=1200)
        d = ImageDraw.Draw(img); sw = 200 * (1 - 0.3 * eio(k / 2.5))
        d.ellipse([330 - sw, 1395, 330 + sw, 1430], fill=(60, 40, 30, 120))
        draw_char(img, "H", 330, 1010 - lift, t, "shock" if t < b["start"] else "happy", 0.95, arms=(-160, 160))
        ht = word_t(vn, "hawa", vn["end"] - 0.6)
        if t > ht - 0.1: stamp(img, "HAWA MEIN!", 760, 300, t - ht + 0.1, WI_BLUE, -6, 110)
        if t > b["start"] - 0.05: paste_c(img, emoji("😵", 110), 760, 560, eob((t - b["start"]) / 0.25), rot=10 * math.sin(t * 6))

def sc_street_grav(img, t, lt):
    v1, vh = L("street_grav")
    img.alpha_composite(bg_street("day"))
    if t < vh["start"]:
        k = t - v1["start"]
        floaters(img, t, v1["start"], [("🩴", 150, 80), ("🐈", 420, 110), ("🩴", 650, 70), ("🐈", 900, 100), ("⚽", 280, 70), ("🪣", 780, 80)], amp=650, y0=1380)
        draw_char(img, "Z", 560, 1060 + drift(t, v1["start"] + 0.4, 220, 2.0), t, "happy", 0.7, arms=(-160, 160), laugh=True)
        st = word_t(v1, "sab", v1["end"] - 0.6)
        if t > st - 0.1: stamp(img, "SAB UPAR!", W / 2, 300, t - st + 0.1, RED, -5, 120)
    else:
        k = t - vh["start"]
        cyc = 1000 + drift(t, vh["start"] - 1.0, 280, 1.5, 2)
        draw_char(img, "C", 780, cyc, t, "shock", 0.85, arms=(-160, 160))
        paste_c(img, emoji("🪁", 120), 930, cyc - 330, 1.0, rot=15 * math.sin(t * 3))
        draw_char(img, "H", 300, 1010 + drift(t, vh["start"] - 1.0, 160, 1.5), t, "happy", 0.88, arms=(-20, -130))
        paste_c(img, bubble([("CHACHA! PATANG NAHI…", INK), ("AAP UD RAHE HO!", WI_BLUE)], 44, tail="left"), 420, 380, eob(k / 0.3))
        if k > 1.2: paste_c(img, emoji("😂", 100), 560, 640, eob((k - 1.2) / 0.3))

def sc_sky_grav(img, t, lt):
    vn, vh, b = L("sky_grav")
    img.alpha_composite(bg_street("day"))
    lift = 230 + 14 * math.sin(t * 2)
    d = ImageDraw.Draw(img); d.ellipse([340, 1395, 740, 1430], fill=(60, 40, 30, 110))
    draw_char(img, "H", 540, 1000 - lift, t, "shock" if t < vh["start"] else "happy", 0.9, arms=(-160, 160), laugh=t > vh["start"])
    floaters(img, t, vn["start"] - 3, [("🩴", 160, 70), ("🐈", 900, 100), ("🪁", 820, 90)], amp=420, y0=1300)
    if t < vh["start"]:
        k = t - vn["start"]
        ruler(img, 880, 1410, 300, k - 1.2)
        ft = word_t(vn, "foot", vn["end"] - 1.2)
        if t > ft - 0.1: paste_c(img, pill("SIRF 1-2 FOOT", 58, YEL), W / 2, 300, eob((t - ft + 0.1) / 0.3), rot=-3)
        paste_c(img, pill("ZAMEEN GOL HAI • NEECHE MUDTI HAI", 36, WHITE, INK), W / 2, 420, eob((k - 2.4) / 0.3))
    else:
        k = t - vh["start"]
        paste_c(img, bubble([("MAZAA AA", INK), ("RAHA HAI!", GRN)], 50, tail="left"), 300, 380, eob(k / 0.3))
        if t > b["start"] - 0.05:
            for j in range(5): paste_c(img, emoji("✨", 70), 300 + j * 130, 250 + 60 * math.sin(t * 4 + j), eob((t - b["start"] - j * 0.05) / 0.2))

def sc_fall_grav(img, t, lt):
    v1, b, vh = L("fall_grav")
    img.alpha_composite(bg_room("day"))
    dt_ = word_t(v1, "dharaam", v1["end"] - 0.7)
    if t < dt_:
        k = t - v1["start"]
        floaters(img, t, v1["start"] - 4, [("☕", 820, 90), ("📱", 160, 70), ("👟", 900, 80), ("📚", 260, 80)], amp=520, y0=1200)
        draw_char(img, "H", 540, 760 + 12 * math.sin(t * 2), t, "shock", 0.9, arms=(-160, 160))
        n = 5 + min(2, int(k / 0.7))
        paste_c(img, glow_text(str(n), "Anton-Regular.ttf", 260, YEL, (230, 60, 70)), 850, 330, eob(((k % 0.7)) / 0.2), rot=-6)
    else:
        k = t - dt_
        fall = eio(k / 0.18)
        draw_char(img, "H", 540, lerp(760, 1080, fall), t, "shock" if t < vh["start"] else "sad", 0.9, arms=(-40, 40) if k > 0.2 else (-160, 160))
        for j, (e, x) in enumerate((("📱", 160), ("👟", 900), ("📚", 260))):
            paste_c(img, emoji(e, 130), x, lerp(800, 1340, fall), 1.0, rot=20 * j)
        stamp(img, "DHARAAM!", W / 2, 300, k, RED, -6, 140)
        if t > vh["start"] - 0.3:
            kk = t - vh["start"] + 0.3
            hy = 1080 - 70 * 0.9 - 150
            paste_c(img, emoji("☕", 150), 540, lerp(400, hy, eio(kk / 0.25)), 1.0, rot=180)
            if kk > 0.25:
                d = ImageDraw.Draw(img)
                for j in range(5): x = 470 + j * 35; d.line([(x, hy + 40), (x, hy + 80 + 30 * ((j * 7) % 3) * min(1, kk - 0.25))], fill=(150, 90, 50), width=10)
            paste_c(img, pill("CHAI… SAR PAR!", 52, (150, 90, 50), WHITE), W / 2, 480, eob((kk - 0.6) / 0.3), rot=3)
        shake(img, t, dt_, 28, 0.6)

def sc_truth_grav(img, t, lt):
    v1, fq = L("truth_grav")
    img.alpha_composite(grad((20, 20, 50), (70, 40, 110))); sky_stars(img, t, 40)
    k = t - v1["start"]
    draw_char(img, "H", 300, 1010, t, "shock", 0.9, arms=(-20, 110), hold=hold_phone)
    paste_c(img, pill("12 AUGUST 2026: KUCH NAHI HUA", 44, WHITE, INK), W / 2, 260, eob((k - 0.8) / 0.3), rot=-2)
    at = word_t(v1, "afwah", v1["start"] + 3.0)
    if t > at - 0.1: stamp(img, "AFWAH!", 760, 560, t - at + 0.1, RED, -8, 150)
    gt = word_t(v1, "scientists", v1["start"] + 4.0)
    if t > gt - 0.1:
        paste_c(img, pill("GRAVITY BAND NAHI HO SAKTI", 44, GRN, WHITE), W / 2, 400, eob((t - gt + 0.1) / 0.3), rot=2)
        paste_c(img, emoji("🌍", 160), 780, 850, eob((t - gt) / 0.3))

# ======================= EPISODE 3: Future Se Message (a message from yourself, 1 saal baad; the "Remember November 2026" AI meme)
def chat_card(sender, rows, col=(30, 90, 170), w=520):
    """Phone chat card: header with sender, then message bubbles (list of (text, colour))."""
    ts = [text_img(x, "Poppins-Black.ttf", 34, c) for x, c in rows]
    h = 150 + sum(t_.height + 34 for t_ in ts) + 40
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=44, fill=(25, 25, 30), outline=INK, width=7)
    d.rounded_rectangle([16, 16, w - 17, h - 17], radius=32, fill=(236, 240, 232))
    d.rounded_rectangle([16, 16, w - 17, 120], radius=32, fill=col); d.rectangle([16, 80, w - 17, 120], fill=col)
    d.text((w / 2, 68), sender, font=fnt("Poppins-Black.ttf", 36), fill=WHITE, anchor="mm")
    y = 150
    for t_ in ts:
        d.rounded_rectangle([36, y - 12, 36 + t_.width + 40, y + t_.height + 12], radius=20, fill=(215, 250, 200), outline=INK, width=3)
        im.alpha_composite(t_, (56, int(y))); y += t_.height + 34
    return im
@lru_cache(None)
def card_future(): return chat_card("HAMID (1 SAAL BAAD)", [("MAIN TUM HOON…", INK), ("FUTURE SE! ⏳" if False else "FUTURE SE!", (150, 50, 200))], (120, 50, 180))
@lru_cache(None)
def card_q3(): return chat_card("HAMID (1 SAAL BAAD)", [("KAL KE PAPER MEIN…", INK), ("SAWAAL NO. 3 AAYEGA!", RED)], (120, 50, 180))
@lru_cache(None)
def card_bilal(): return chat_card("BILAL", [("HAHA! PRANK THA 😂" if False else "HAHA! PRANK THA!", INK), ("Q3 HAR SAAL AATA HAI", RED)], (255, 130, 40))
def hold_fphone(img, x, y, sc): paste_c(img, phone_img(True), x + 140 * sc, y + 150 * sc, sc * 0.9, rot=-10)
@lru_cache(None)
def meme_post(seed):
    w, h = 300, 360; im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=(250, 250, 255), outline=INK, width=6)
    d.rounded_rectangle([18, 18, w - 19, 230], radius=16, fill=[(40, 50, 90), (70, 40, 110), (30, 70, 90)][seed % 3])
    d.text((w / 2, 95), "REMEMBER", font=fnt("Anton-Regular.ttf", 50), fill=WHITE, anchor="mm")
    d.text((w / 2, 165), "NOVEMBER", font=fnt("Anton-Regular.ttf", 50), fill=YEL, anchor="mm")
    d.text((w / 2, 280), "♥ 2.1M  💬" if False else "♥ 2.1M   ↻ 90K", font=fnt("Poppins-Black.ttf", 28), fill=RED, anchor="mm")
    return im
@lru_cache(None)
def cal_page(day=23):
    im = Image.new("RGBA", (420, 460), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 419, 459], radius=30, fill=(255, 250, 235), outline=INK, width=8)
    d.rounded_rectangle([0, 0, 419, 120], radius=30, fill=RED); d.rectangle([0, 80, 419, 120], fill=RED)
    d.text((210, 62), "NOVEMBER 2026", font=fnt("Anton-Regular.ttf", 54), fill=WHITE, anchor="mm")
    d.text((210, 290), str(day), font=fnt("Anton-Regular.ttf", 220), fill=INK, anchor="mm")
    return im
@lru_cache(None)
def paper_q3(tick=False):
    im = Image.new("RGBA", (640, 620), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 639, 619], radius=16, fill=(252, 250, 240), outline=INK, width=7)
    d.text((320, 60), "PAPER • 9:00 AM", font=fnt("Anton-Regular.ttf", 54), fill=(150, 50, 70), anchor="mm")
    d.line([(36, 104), (604, 104)], fill=(150, 50, 70), width=5)
    for j, q in enumerate(("Q1.  ___________", "Q2.  ___________", "Q3.  SAWAAL NO. 3", "Q4.  ___________")):
        y = 170 + j * 110
        if j == 2: d.rounded_rectangle([24, y - 44, 616, y + 44], radius=14, fill=(255, 240, 150), outline=RED, width=5)
        d.text((60, y), q, font=fnt("Poppins-Black.ttf", 40), fill=INK, anchor="lm")
    if tick: d.text((560, 390), "✓" if False else "OK", font=fnt("Anton-Regular.ttf", 60), fill=GRN, anchor="mm")
    return im

def sc_hook_fut(img, t, lt):
    img.alpha_composite(bg_room("night")); bulb_glow(img, 40)
    (v0,) = L("hook_fut")
    clock(img, 880, 330, 0.0)
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(g).ellipse([520, 520, 1060, 1180], fill=(160, 120, 255, int(70 + 40 * math.sin(t * 6))))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    draw_char(img, "H", 300, 1010, t, "shock", 0.95, arms=(-20, 110), hold=hold_fphone)
    paste_c(img, card_future(), 760, 850, eob((t - 0.15) / 0.3), rot=4 + 2 * math.sin(t * 3))
    st = word_t(v0, "saal", v0["end"] - 1.2)
    if t > st - 0.1: stamp(img, "1 SAAL BAAD SE!", W / 2, 1240, t - st + 0.1, (120, 50, 180), -5, 100)
    if t > 0.2: paste_c(img, emoji("😳", 100), 520, 640, eob((t - 0.3) / 0.25))

def sc_meme_fut(img, t, lt):
    (v1,) = L("meme_fut"); k = t - v1["start"]
    img.alpha_composite(grad((25, 20, 60), (80, 40, 130))); sky_stars(img, t, 40)
    for j, (x, y, r) in enumerate(((190, 420, -8), (540, 380, 4), (890, 440, 9), (190, 790, 6), (890, 800, -6))):
        paste_c(img, meme_post(j), x, y + 8 * math.sin(t * 2 + j), 0.85 * eob((k - j * 0.18) / 0.25), rot=r)
    nt = word_t(v1, "november", v1["start"] + 2.6, exact=False)
    nt2 = [w["t"] for w in v1["words"] if w["w"].lower().strip(".,…!?'") .startswith("november")]
    at = nt2[-1] if len(nt2) > 1 else v1["end"] - 1.2
    draw_char(img, "H", 470, 1110, t, "shock" if t > at else "n", 0.8, arms=(-20, 110), hold=hold_fphone)
    if t > at - 0.1:
        paste_c(img, cal_page(23), 820, 1120, eob((t - at + 0.1) / 0.3), rot=-5)
        paste_c(img, emoji("😨", 110), 940, 880, eob((t - at - 0.2) / 0.25))
    paste_c(img, pill("SAB KEH RAHE THE…", 46, YEL), W / 2, 240, eob(k / 0.3), rot=-2)

def sc_room_fut(img, t, lt):
    vh, vn, b = L("room_fut")
    img.alpha_composite(bg_room("night")); bulb_glow(img, 50)
    if t < vn["start"]:
        k = t - vh["start"]
        draw_char(img, "H", 300, 1010, t, "shock", 0.95, arms=(-20, 110), hold=hold_fphone)
        paste_c(img, card_q3(), 770, 760, eob(k / 0.3), rot=3)
        qt = word_t(vh, "3", vh["end"] - 1.0)
        if t > qt - 0.1: stamp(img, "Q3!", 800, 1220, t - qt + 0.1, RED, -8, 140)
    else:
        k = t - vn["start"]
        hrs = 0.0 + 8.0 * eio(min(1, k / (b["end"] - vn["start"])))
        clock(img, 880, 330, hrs)
        d = ImageDraw.Draw(img); d.rectangle([140, 1180, 940, 1220], fill=(120, 80, 50), outline=INK, width=5)
        sleepy = t > b["start"]
        draw_char(img, "H", 540, 1000 + (40 if sleepy else 0), t, "sleep" if sleepy else "det", 0.9, arms=(-60, 60), hold=hold_book)
        for j in range(min(6, int(k * 1.6))):
            paste_c(img, pill("SAWAAL 3", 34, WHITE, INK), 230 + (j % 2) * 620, 620 + (j // 2) * 120, eob((k - j / 1.6) / 0.2), rot=(-6, 6)[j % 2])
        if k > 1.0: paste_c(img, emoji("☕", 90), 260, 1130, 1.0)
        if k > 2.0: paste_c(img, emoji("☕", 90), 340, 1130, 1.0, rot=8)
        if sleepy: zzz(img, 660, 760, t); paste_c(img, pill("RAAT 3 BAJE…", 44, YEL), W / 2, 260, eob((t - b["start"]) / 0.2), rot=-3)

def sc_exam_fut(img, t, lt):
    v1, vh = L("exam_fut")
    img.alpha_composite(bg_hall()); d = ImageDraw.Draw(img)
    d.rectangle([300, 230, 1000, 560], fill=(40, 70, 55), outline=(120, 80, 50), width=14)
    d.text((650, 340), "IMTIHAAN", font=fnt("Anton-Regular.ttf", 80), fill=WHITE, anchor="mm")
    d.text((650, 450), "9:00 AM", font=fnt("Poppins-Black.ttf", 44), fill=YEL, anchor="mm")
    gt = word_t(v1, "gaya", v1["end"] - 0.6)
    happy = t > gt
    if t < vh["start"]:
        k = t - v1["start"]
        paste_c(img, paper_q3(False), W / 2, 1010, eob((k - 0.3) / 0.3) * 0.95, rot=-2)
        draw_char(img, "H", 170, 1250, t, "happy" if happy else "shock", 0.6, arms=(-20, 20))
        if happy:
            stamp(img, "AA GAYA!", W / 2, 680, t - gt, GRN, -6, 130); shake(img, t, gt, 18, 0.4)
    else:
        k = t - vh["start"]
        draw_char(img, "H", 540, 1000 + 25 * abs(math.sin(t * 6)), t, "happy", 0.95, arms=(-160, 160), laugh=True)
        paste_c(img, bubble([("FUTURE WALA HAMID…", INK), ("ZINDABAD!", GRN)], 46, tail="left"), 430, 690, eob(k / 0.3))
        for j in range(5): paste_c(img, emoji("✨", 70), 220 + j * 160, 620 + 50 * math.sin(t * 4 + j), eob((k - j * 0.08) / 0.2))

def sc_twist_fut(img, t, lt):
    v1, vl, b = L("twist_fut")
    img.alpha_composite(bg_street("day"))
    if t < vl["start"]:
        k = t - v1["start"]
        draw_char(img, "H", 300, 1010, t, "happy" if k < 1.2 else "shock", 0.92, arms=(-20, 110), hold=hold_fphone)
        bt = word_t(v1, "bilal", v1["end"] - 1.2)
        if t > bt - 0.1:
            paste_c(img, card_bilal(), 770, 760, eob((t - bt + 0.1) / 0.3), rot=-3)
            stamp(img, "BILAL?!", 760, 1260, t - bt + 0.1, (255, 130, 40), 6, 110)
        else:
            paste_c(img, pill("NAYA MESSAGE…", 50, WHITE, INK), 760, 520, eob(k / 0.3) * (1 + 0.05 * math.sin(t * 9)), rot=3)
    else:
        k = t - vl["start"]
        draw_char(img, "L", 780, 1010, t, "happy", 0.92, arms=(-150, 20), hold=hold_fphone, laugh=t < b["start"])
        draw_char(img, "H", 290, 1010, t, "shock" if t < b["start"] else "sad", 0.92, arms=(-20, 20))
        paste_c(img, pill("HAR SAAL AATA HAI! 😂" if False else "HAR SAAL AATA HAI!", 48, YEL), W / 2, 300, eob(k / 0.3), rot=-3)
        if k > 0.8: paste_c(img, emoji("😂", 110), 900, 560, eob((k - 0.8) / 0.25), rot=10 * math.sin(t * 6))
        if t > b["start"] - 0.05:
            stamp(img, "PRANK!", 300, 560, t - b["start"] + 0.05, RED, -8, 140); shake(img, t, b["start"], 20, 0.4)
            paste_c(img, emoji("😑", 110), 300, 760, eob((t - b["start"]) / 0.25))

def sc_truth_fut(img, t, lt):
    v1, fq = L("truth_fut")
    img.alpha_composite(grad((20, 20, 50), (70, 40, 110))); sky_stars(img, t, 40)
    k = t - v1["start"]
    draw_char(img, "H", 300, 1010, t, "n", 0.9, arms=(-20, 110), hold=hold_fphone)
    paste_c(img, meme_post(1), 780, 760, eob((k - 0.2) / 0.3) * 0.9, rot=5)
    mt = word_t(v1, "meme", v1["start"] + 2.5)
    if t > mt - 0.1:
        stamp(img, "SIRF AI MEME!", W / 2, 300, t - mt + 0.1, RED, -5, 110)
        paste_c(img, pill("KUCH NAHI HONE WALA", 46, GRN, WHITE), W / 2, 470, eob((t - mt - 0.6) / 0.3), rot=2)

# ======================= EPISODE 4: Smog Ghayab (ek din bilkul saaf hawa; Lahore AQI 500+ in November 2026)
def smog(img, a, t=0.0):
    if a <= 0.01: return
    lay = Image.new("RGBA", (W, H), (150, 140, 120, int(200 * min(a, 1)))); d = ImageDraw.Draw(lay)
    rs = np.random.default_rng(7)
    for j in range(14):
        x, y, r = rs.uniform(-100, W + 100) + 40 * math.sin(t * 0.7 + j), rs.uniform(100, 1400), rs.uniform(160, 320)
        d.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(185, 175, 150, int(110 * min(a, 1))))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(40)))
@lru_cache(None)
def minar_img():
    im = Image.new("RGBA", (260, 900), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c, sh = (236, 232, 222), (200, 196, 186)
    d.polygon([(70, 890), (190, 890), (160, 240), (100, 240)], fill=c, outline=INK, width=6)
    for y in (700, 520, 330):
        d.rounded_rectangle([60, y - 18, 200, y + 14], radius=8, fill=sh, outline=INK, width=5)
    d.rectangle([108, 150, 152, 240], fill=c, outline=INK, width=5)
    d.ellipse([86, 70, 174, 170], fill=c, outline=INK, width=6); d.line([(130, 20), (130, 72)], fill=INK, width=6)
    d.rounded_rectangle([20, 870, 240, 900], radius=8, fill=sh, outline=INK, width=5)
    return im
@lru_cache(None)
def aqi_card(v):
    col = GRN if v < 100 else ((230, 160, 40) if v < 200 else ((200, 60, 60) if v < 300 else (120, 30, 70)))
    im = Image.new("RGBA", (520, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 519, 399], radius=40, fill=(250, 248, 240), outline=INK, width=8)
    d.rounded_rectangle([0, 0, 519, 110], radius=40, fill=INK); d.rectangle([0, 70, 519, 110], fill=INK)
    d.text((260, 58), "LAHORE • AQI", font=fnt("Anton-Regular.ttf", 58), fill=WHITE, anchor="mm")
    d.text((260, 240), str(v), font=fnt("Anton-Regular.ttf", 170), fill=col, anchor="mm")
    d.text((260, 360), "HAZARDOUS" if v >= 300 else ("GOOD" if v < 100 else "UNHEALTHY"), font=fnt("Poppins-Black.ttf", 36), fill=col, anchor="mm")
    return im
@lru_cache(None)
def air_bottle():
    im = Image.new("RGBA", (200, 380), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([70, 0, 130, 50], radius=10, fill=(60, 120, 255), outline=INK, width=5)
    d.rounded_rectangle([20, 46, 180, 370], radius=40, fill=(210, 235, 255), outline=INK, width=7)
    d.rounded_rectangle([20, 150, 180, 270], radius=6, fill=YEL, outline=INK, width=5)
    d.text((100, 185), "TAAZA", font=fnt("Anton-Regular.ttf", 40), fill=INK, anchor="mm")
    d.text((100, 235), "HAWA", font=fnt("Anton-Regular.ttf", 40), fill=RED, anchor="mm")
    return im
def hold_air(img, x, y, sc): paste_c(img, air_bottle(), x + 150 * sc, y + 150 * sc, sc * 0.75, rot=-10)

def sc_hook_smog(img, t, lt):
    (v0,) = L("hook_smog")
    img.alpha_composite(bg_street("day"))
    gt = word_t(v0, "ghayab", v0["end"] - 0.8)
    paste_c(img, minar_img(), 900, 700, 0.7)
    smog(img, 0.95 * (1 - eo((t - gt + 0.4) / 0.7)), t)
    draw_char(img, "H", 330, 1010, t, "shock" if t > gt - 0.3 else "n", 0.95, arms=(-150, 150) if t > gt else (-20, 20))
    if t < gt: paste_c(img, emoji("😷", 120), 740, 1000, eob((t - 0.1) / 0.25))
    if t > gt - 0.1:
        stamp(img, "GHAYAB!", 720, 1180, t - gt + 0.1, GRN, -8, 140)
        for j in range(6): paste_c(img, emoji("✨", 70), 160 + j * 160, 480 + 40 * math.sin(t * 5 + j), eob((t - gt - j * 0.05) / 0.2))

def sc_fact_smog(img, t, lt):
    (v1,) = L("fact_smog"); k = t - v1["start"]
    img.alpha_composite(bg_street("day")); smog(img, 1.0, t)
    v = int(535 * eio(min(1, k / 2.2)))
    paste_c(img, aqi_card(min(535, max(20, v // 5 * 5))), W / 2, 610, eob(k / 0.3), rot=-3)
    draw_char(img, "H", 300, 1060, t, "sad", 0.85, arms=(-20, 20))
    paste_c(img, emoji("😷", 120), 720, 1060, eob((k - 0.3) / 0.3))
    if k > 1.0: paste_c(img, text_img("KHAANS… KHAANS…", "Poppins-Black.ttf", 44, WHITE, 6, INK), 700, 900, eob((k - 1.0) / 0.3), rot=4)
    dt_ = word_t(v1, "duniya", v1["end"] - 1.6)
    if t > dt_ - 0.1: stamp(img, "DUNIYA MEIN #1", W / 2, 260, t - dt_ + 0.1, RED, -4, 100)

def sc_roof_smog(img, t, lt):
    (vh,) = L("roof_smog"); k = t - vh["start"]
    img.alpha_composite(bg_street("day")); smog(img, 0.5 * (1 - eo(k / 0.8)), t)
    paste_c(img, minar_img(), 840, 650, 0.85 * eob((k - 0.1) / 0.4))
    draw_char(img, "H", 300, 1010, t, "happy", 0.95, arms=(-20, -120))
    mt = word_t(vh, "minar", vh["start"] + 1.4)
    if t > mt - 0.1:
        paste_c(img, pill("SAAF NAZAR AA RAHA HAI!", 48, GRN, WHITE), W / 2, 250, eob((t - mt + 0.1) / 0.3), rot=-3)
        paste_c(img, emoji("😍", 100), 560, 600, eob((t - mt) / 0.3))

def sc_street_smog(img, t, lt):
    v1, vl, b = L("street_smog")
    img.alpha_composite(bg_street("day"))
    if t < vl["start"]:
        k = t - v1["start"]
        draw_char(img, "K", 280, 1010, t, "happy", 0.85, arms=(-150, 150)); draw_char(img, "Z", 790, 1060, t, "happy", 0.72, arms=(-150, 150))
        for j, x in enumerate((200, 380, 700, 880)):
            q = max(0, k - 0.4 - j * 0.15)
            if q > 0: paste_c(img, emoji("😷", 80), x, 700 - q * 260, 1.0, rot=q * 160)
        paste_c(img, pill("LAMBI SAANS…", 50, WHITE, INK), W / 2, 280, eob((k - 1.2) / 0.3), rot=-2)
        kt = word_t(v1, "ghayab", v1["end"] - 0.6)
        if t > kt - 0.1: stamp(img, "KHAANSI: 0", W / 2, 430, t - kt + 0.1, GRN, -5, 110)
    else:
        k = t - vl["start"]
        draw_char(img, "L", 760, 1010, t, "happy", 0.92, arms=(-150, 20), hold=None, laugh=t < b["start"])
        for j in range(3): paste_c(img, air_bottle(), 620 + j * 150, 1300, 0.55, rot=(-6, 3, 8)[j])
        draw_char(img, "H", 290, 1010, t, "shock" if t < b["start"] else "sad", 0.92, arms=(-20, 20))
        paste_c(img, air_bottle(), 760, 560, eob(k / 0.3) * 0.8, rot=8 * math.sin(t * 4))
        rt = word_t(vl, "100", vl["end"] - 1.0)
        if t > rt - 0.1: paste_c(img, pill("Rs 100 KI EK!", 52, YEL), 760, 300, eob((t - rt + 0.1) / 0.3) * (1 + 0.05 * math.sin(t * 9)), rot=4)
        if t > b["start"] - 0.05:
            stamp(img, "BILAL!!", 300, 560, t - b["start"] + 0.05, RED, -8, 130); shake(img, t, b["start"], 20, 0.4)
            paste_c(img, emoji("🤦", 110), 540, 700, eob((t - b["start"]) / 0.25))

def sc_night_smog(img, t, lt):
    v1, vh, b = L("night_smog")
    img.alpha_composite(bg_street("night"))
    n = int(40 + 160 * eio((t - v1["start"] - 1.0) / 2.5))
    sky_stars(img, t, n, seed=11, y1=1000)
    if t < vh["start"]:
        k = t - v1["start"]
        draw_char(img, "H", W / 2, 1010, t, "n", 0.9, arms=(-20, 20))
        paste_c(img, glow_text("UPAR DEKHO…", "Anton-Regular.ttf", 110, WHITE, (150, 90, 255)), W / 2, 280, eob((k - 1.4) / 0.3), rot=-3)
    else:
        k = t - vh["start"]
        draw_char(img, "H", W / 2, 1010, t, "happy", 0.92, arms=(-150, 150), laugh=t > b["start"])
        paste_c(img, bubble([("ITNE SAARE", INK), ("TAARE?!", (150, 90, 255))], 50, tail="left"), 380, 460, eob(k / 0.3))
        if t > b["start"] - 0.05:
            q = eo((t - b["start"]) / 0.6)
            for j in range(8): paste_c(img, emoji("✨", 60), 600 + (j % 4) * 120, 360 + (j // 4) * 200 + 60 * math.sin(j * 1.3) * q, eob((t - b["start"] - j * 0.03) / 0.2))
            paste_c(img, pill("YEH LAHORE HAI?!", 52, YEL), W / 2, 230, eob((t - b["start"]) / 0.25), rot=-3)

def sc_twist_smog(img, t, lt):
    v1, v2 = L("twist_smog")
    img.alpha_composite(bg_street("day"))
    wt = word_t(v1, "wapis", v1["end"] - 0.6)
    smog(img, eo((t - wt + 0.5) / 0.6) if t < v2["start"] else 1.0, t)
    if t < v2["start"]:
        draw_char(img, "H", 330, 1010, t, "happy" if t < wt else "shock", 0.95, arms=(-20, 20) if t < wt else (-150, 150))
        if t < wt: paste_c(img, pill("AGLI SUBAH…", 50, WHITE, INK), W / 2, 300, eob((t - v1["start"]) / 0.3), rot=-2)
        else:
            stamp(img, "SMOG WAPIS!", W / 2, 300, t - wt + 0.1, RED, -5, 120); shake(img, t, wt, 24, 0.5)
            paste_c(img, emoji("😩", 110), 760, 760, eob((t - wt) / 0.25))
    else:
        k = t - v2["start"]
        draw_char(img, "H", 300, 1010, t, "det", 0.92, arms=(-20, -110))
        for j, (e, txt) in enumerate((("🚗", "GAARI KA DHUAAN"), ("🔥", "FASAL KI AAG"), ("🏭", "FACTORY"))):
            y = 470 + j * 190; q = eob((k - 0.8 - j * 0.35) / 0.25)
            paste_c(img, emoji(e, 90), 600, y, q); paste_c(img, pill(txt, 42, WHITE, INK), 830, y, q, rot=(-3, 2, -2)[j])
        paste_c(img, glow_text("JAADU NAHI!", "Anton-Regular.ttf", 110, YEL, (230, 60, 70)), W / 2, 260, eob(k / 0.3), rot=-3)

def sc_end_smog(img, t, lt):
    img.alpha_composite(bg_street("day")); smog(img, 0.4, t)
    paste_c(img, minar_img(), 860, 700, 0.7)
    draw_char(img, "H", 330, 1010, t, "det", 0.92, arms=(-20, 20))


WI_SC = {"hook_net": sc_hook_net, "title": sc_title, "room_net": sc_room_net, "shop_net": sc_shop_net, "city_net": sc_city_net,
         "roof_net": sc_roof_net, "back_net": sc_back_net,
         "hook_grav": sc_hook_grav, "room_grav": sc_room_grav, "street_grav": sc_street_grav, "sky_grav": sc_sky_grav,
         "fall_grav": sc_fall_grav, "truth_grav": sc_truth_grav,
         "hook_fut": sc_hook_fut, "meme_fut": sc_meme_fut, "room_fut": sc_room_fut, "exam_fut": sc_exam_fut, "twist_fut": sc_twist_fut,
         "truth_fut": sc_truth_fut,
         "hook_smog": sc_hook_smog, "fact_smog": sc_fact_smog, "roof_smog": sc_roof_smog, "street_smog": sc_street_smog,
         "night_smog": sc_night_smog, "twist_smog": sc_twist_smog, "end_smog": sc_end_smog}
SC.update(WI_SC)

exec(compile(_MAIN + _main, HR, "exec"), globals())
