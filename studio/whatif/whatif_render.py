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
    paste_c(img, pill("24 GHANTE • NO INTERNET", 54, RED, WHITE), W / 2, 780, eob((lt - 1.0) / 0.3) * (1 + 0.04 * math.sin(t * 8)), rot=2)

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

WI_SC = {"hook_net": sc_hook_net, "title": sc_title, "room_net": sc_room_net, "shop_net": sc_shop_net, "city_net": sc_city_net,
         "roof_net": sc_roof_net, "back_net": sc_back_net}
SC.update(WI_SC)

exec(compile(_MAIN + _main, HR, "exec"), globals())
