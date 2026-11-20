"""Hamid series: timeline + lip-sync envelopes + free synthesized score/SFX mix.
Usage: hamid_audio.py <episode dir>"""
import json, subprocess, sys
import numpy as np

D = sys.argv[1]
SR = 48000; FPS = 30
lines = json.load(open(f"{D}/script.json"))
rng = np.random.default_rng(11)
import os
EARTH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx") + "/"  # free reusable SFX

def load(p, tempo=1.0):
    af = ["-af", f"atempo={tempo}"] if abs(tempo - 1) > 1e-3 else []
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", p] + af + ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()

def trim(x, th=0.02):
    k = int(0.02 * SR); e = np.convolve(np.abs(x), np.ones(k) / k, mode="same")
    idx = np.where(e > th * e.max())[0] if e.max() > 0 else []
    if len(idx) == 0: return x
    return x[max(0, idx[0] - int(0.03 * SR)): min(len(x), idx[-1] + int(0.08 * SR))]

INTRO = 0.2
# Pacing (owner, 2026-11-14 + 2026-11-15 "reel sounds a bit slow, make it a little bit fast"):
# voices are sped up a little, gaps are tight and wordless beats are shortened + capped.
VOICE_TEMPO = 1.12 # speech speed-up (pitch kept) - applied to every voice line
GAP = 0.06         # silence after every line
SCENE_GAP = 0.1    # extra breath at a scene cut
BEAT_SCALE = 0.85  # every wordless beat is shortened by this factor ...
BEAT_MAX = 1.3     # ... and capped (s)
# Owner, 2026-11-18: "reels are getting slow and sloppy, some things are left without a voice - make it shorter but
# entertaining, no gaps". From Day 13 on: voice-led reels, 45-60 s, at most 4 wordless beats (never two in a row),
# each capped at 0.6 s, tighter scene cuts. The checks below stop the run if a script breaks these rules.
_DAY = json.load(open(f"{D}/meta.json")).get("day", 0) if os.path.exists(f"{D}/meta.json") else 0
VOICE_LED = _DAY >= 13
if VOICE_LED:
    BEAT_MAX = 0.6; SCENE_GAP = 0.04
t = INTRO; tl = []; clips = []
prev_scene = None
for i, l in enumerate(lines):
    if l.get("mode") == "beat":   # wordless visual beat: silence of fixed length (music + SFX carry it)
        v = np.zeros(int(min(float(l.get("dur", 1.2)) * BEAT_SCALE, BEAT_MAX) * SR), np.float32)
    else:
        v = trim(load(f"{D}/v{i:02d}.wav", VOICE_TEMPO)); v = v / (np.abs(v).max() + 1e-9) * 0.9
    if prev_scene is not None and l["scene"] != prev_scene: t += SCENE_GAP   # breath between scenes
    d = len(v) / SR
    words = l["rom"].split() if l.get("mode") != "beat" else []
    wts = np.array([max(2, len(w.strip(".,!?…\""))) + 1.5 for w in words] or [1.0], float)
    cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum()
    rw = [{"w": w, "t": t + 0.03 + cum[k] * (d - 0.12)} for k, w in enumerate(words)]
    tl.append({**l, "start": t, "end": t + d, "words": rw})
    clips.append((t, v, l["who"], l.get("mode")))
    t += d + GAP; prev_scene = l["scene"]
TOTAL = t + (0.8 if VOICE_LED else 1.2)
if VOICE_LED:
    _beats = [i for i, l in enumerate(lines) if l.get("mode") == "beat"]
    _errs = []
    if len(_beats) > 4: _errs.append(f"{len(_beats)} wordless beats (max 4)")
    if any(b + 1 in _beats for b in _beats): _errs.append("two wordless beats in a row")
    if not 45 <= TOTAL <= 62: _errs.append(f"length {TOTAL:.1f} s (want 45-60 s)")
    _meta = json.load(open(f"{D}/meta.json"))
    if _DAY >= 15 and not (_meta.get("hook") or {}).get("text"):
        _errs.append('meta.json needs "hook": {"text", "emoji"} (cold-open hook, owner 2026-11-19)')
    if _errs: print("REEL RULES BROKEN (owner 2026-11-18):", "; ".join(_errs), "- rewrite script.json"); sys.exit(3)
# scene spans
scenes = []
for l in tl:
    if not scenes or scenes[-1]["scene"] != l["scene"]:
        scenes.append({"scene": l["scene"], "start": l["start"], "end": l["end"]})
    else:
        scenes[-1]["end"] = l["end"]
for k in range(len(scenes)):
    scenes[k]["vstart"] = 0 if k == 0 else (scenes[k - 1]["end"] + scenes[k]["start"]) / 2
    scenes[k]["vend"] = TOTAL if k == len(scenes) - 1 else (scenes[k]["end"] + scenes[k + 1]["start"]) / 2
json.dump({"total": TOTAL, "lines": tl, "scenes": scenes}, open(f"{D}/timeline.json", "w"), ensure_ascii=False, indent=1)

N = int(TOTAL * SR)
voice = np.zeros(N, np.float32); tracks = {}
for st, v, who, mode in clips:
    a = int(st * SR); m = min(len(v), N - a)
    voice[a:a + m] += v[:m]
    if mode == "talk":
        tracks.setdefault(who, np.zeros(N, np.float32))[a:a + m] += v[:m]
nf = int(TOTAL * FPS) + 1; hop = SR // FPS; envs = {}
for who, tr in tracks.items():
    e = np.array([np.sqrt(np.mean(tr[k * hop:(k + 1) * hop] ** 2)) if k * hop < N else 0 for k in range(nf)])
    nz = e[e > 0]
    envs[who] = np.clip(e / (np.percentile(nz, 95) + 1e-9), 0, 1.2) if len(nz) else e
np.savez(f"{D}/lipsync.npz", **envs)

def env(n, a=0.005, dcy=0.3):
    x = np.arange(n) / SR
    return (np.minimum(x / a, 1) * np.exp(-x / dcy)).astype(np.float32)
def add(buf, sig, at, g=1.0):
    st = int(at * SR)
    if st < 0: sig = sig[-st:]; st = 0
    if st >= len(buf): return
    m = min(len(sig), len(buf) - st); buf[st:st + m] += sig[:m] * g
def hz(m): return 440 * 2 ** ((m - 69) / 12)
def piano(f, length, dcy=1.2):
    n = int(length * SR); x = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * h * x + h) for h, a in [(1, 1), (2, 0.45), (3, 0.2), (4, 0.1), (5, 0.05)])
    return (s * env(n, 0.003, dcy) * np.exp(-x * 0.4)).astype(np.float32)
def pad(f, length):
    n = int(length * SR); x = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * dt * x) for dt in (0.997, 1.0, 1.004)) / 3
    a = np.minimum(x / 0.8, 1) * np.minimum((length - x) / 0.8, 1)
    return (s * np.clip(a, 0, 1)).astype(np.float32)
def kick():
    n = int(0.3 * SR); x = np.arange(n) / SR
    return (np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-x * 30)) / SR) * np.exp(-x * 10)).astype(np.float32)

# ---- score: A minor, 72 BPM; last scene lifts to C major with a soft beat
BPM = 72; beat = 60 / BPM; music = np.zeros(N, np.float32)
end_scene = next((s for s in scenes if s["scene"].startswith("end")), None)
lift_t = end_scene["vstart"] if end_scene else TOTAL
sad = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]       # Am F C G
hope = [[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]]      # C G Am F
bars = int(TOTAL / (4 * beat)) + 1
for b in range(bars):
    t0 = INTRO * 0.5 + b * 4 * beat
    lifted = t0 >= lift_t - 0.1
    ch = (hope if lifted else sad)[b % 4]
    for m in ch: add(music, pad(hz(m - 12), 4 * beat), t0, 0.05)
    add(music, piano(hz(ch[0] - 12), 4 * beat, 2.0), t0, 0.22)
    arp = [ch[0], ch[1], ch[2], ch[1] + 12 if lifted else ch[1]]
    for k in range(8 if lifted else 4):
        step = beat / 2 if lifted else beat
        add(music, piano(hz(arp[k % 4] + 12), 1.4, 0.8), t0 + k * step, 0.12 if lifted else 0.10)
    if lifted:
        for k in range(4):
            add(music, kick(), t0 + k * beat, 0.35)

# ---- SFX
sfx = np.zeros(N, np.float32)
def noise(n_s, dcy):
    n = int(n_s * SR); s = rng.standard_normal(n).astype(np.float32)
    return s * env(n, 0.002, dcy)
def tear():
    n = int(0.9 * SR); s = rng.standard_normal(n).astype(np.float32)
    s = np.diff(s, prepend=0) * (0.5 + 0.5 * np.abs(np.sin(np.arange(n) / SR * 90)))
    return s * env(n, 0.01, 0.35) * 0.7
def crickets(len_s):
    n = int(len_s * SR); x = np.arange(n) / SR
    chirp = np.sin(2 * np.pi * 4400 * x) * (np.sin(2 * np.pi * 28 * x) > 0.3) * (np.sin(2 * np.pi * 0.9 * x) > 0.2)
    return (chirp * 0.035).astype(np.float32)
def try_load(p):
    try: return load(p)
    except Exception: return np.zeros(1, np.float32)
WHOOSH = try_load(EARTH + "sfx_whoosh.mp3"); CHIME = try_load(EARTH + "sfx_chime.mp3"); TICK = try_load(EARTH + "sfx_tick.mp3")
for s in scenes[1:]:
    add(sfx, WHOOSH, s["vstart"] - 0.2, 0.35)
for l in tl:
    if l["scene"] == "night" and "PLAN" in l["rom"]:
        add(sfx, tear(), l["start"] + 0.9, 0.8)
        pw = [w for w in l["words"] if w["w"].startswith("PLAN")]
        if pw: add(sfx, CHIME, pw[0]["t"], 0.6)
    if l["scene"] == "fees":
        for k in range(6): add(sfx, TICK, l["start"] + k * 0.5, 0.25)
    if l["scene"] == "burn":   # kettle sizzle + cup smash
        sz = rng.standard_normal(int(1.2 * SR)).astype(np.float32); sz = np.diff(sz, prepend=0) * env(len(sz), 0.02, 0.6) * 0.35
        add(sfx, sz, l["start"] + 0.5, 0.8)
        cw = [w for w in l["words"] if w["w"].lower().startswith("cup")]
        if cw: add(sfx, noise(0.5, 0.08), cw[0]["t"] + 0.1, 0.9); add(sfx, CHIME, cw[0]["t"] + 0.15, 0.25)
    if l["scene"] == "market" and l["who"] == "H":   # notes handed over
        for k in range(3): add(sfx, TICK, l["start"] + 0.4 + k * 1.2, 0.3)
    if l["scene"] == "dummy" and l["who"] == "H":   # box opens, phones tumble
        add(sfx, noise(0.25, 0.05), l["start"] + 0.8, 0.5)
        nw = [w for w in l["words"] if w["w"].lower().startswith("naqli")]
        if nw: add(sfx, kick(), nw[0]["t"], 0.7)
    if l["scene"] == "pay":   # coins counted
        for k in range(5): add(sfx, TICK, l["start"] + 0.3 + k * 0.22, 0.35)
def beep(f, n_s, g=1.0):
    n = int(n_s * SR); x = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * x) * np.minimum(1, (n_s - x) / 0.01) * np.minimum(1, x / 0.005) * g).astype(np.float32)
def bark():
    n = int(0.22 * SR); x = np.arange(n) / SR; f = 520 - 900 * x
    s_ = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.5 + rng.standard_normal(n) * 0.3
    return (s_ * env(n, 0.004, 0.08)).astype(np.float32)
def bell():
    n = int(0.9 * SR); x = np.arange(n) / SR
    return ((np.sin(2 * np.pi * 2350 * x) + 0.6 * np.sin(2 * np.pi * 3530 * x)) * np.exp(-x * 5)).astype(np.float32) * 0.5
def buzz(n_s):
    n = int(n_s * SR); x = np.arange(n) / SR
    return (np.sign(np.sin(2 * np.pi * 150 * x)) * ((x % 0.8) < 0.45) * 0.25).astype(np.float32)
def snore(n_s):
    n = int(n_s * SR); x = np.arange(n) / SR; s_ = rng.standard_normal(n).astype(np.float32)
    s_ = np.convolve(s_, np.ones(60) / 60, mode="same") * 4
    return (s_ * np.clip(np.sin(2 * np.pi * x / 2.2), 0, 1) ** 2 * 0.5).astype(np.float32)
SPN = {x["scene"]: x for x in scenes}
if "alarm" in SPN:
    a0 = SPN["alarm"]["vstart"]
    for k in range(10): add(sfx, beep(1900, 0.09, 0.5), a0 + 0.2 + k * 0.17)
    add(sfx, kick(), a0 + 2.0, 0.6)          # hand slaps the alarm
if "paper" in SPN:
    p0 = SPN["paper"]["vstart"]; add(sfx, bell(), p0 + 0.3, 0.7)
    for k in range(7): add(sfx, noise(0.12, 0.03), p0 + 0.9 + k * 0.55, 0.5)   # papers land
if "chain" in SPN:
    c0 = SPN["chain"]["vstart"]; add(sfx, noise(0.3, 0.06), c0 + 0.5, 0.9); add(sfx, kick(), c0 + 0.5, 0.8)
    run = [l for l in tl if l["scene"] == "chain"][-1]
    for k in range(5): add(sfx, bark(), run["start"] + 0.5 + k * 0.45, 0.6)
    add(sfx, CHIME, run["end"] - 0.9, 0.5)
if "late" in SPN:
    l0 = SPN["late"]["vstart"]
    for k in range(4): add(sfx, TICK, l0 + 0.2 + k * 0.35, 0.4)
    add(sfx, kick(), l0 + 1.4, 0.6)
    mont = [l for l in tl if l["scene"] == "late"][-1]
    for k in range(12): add(sfx, TICK, mont["start"] + k * 0.25, 0.3)
    add(sfx, CHIME, mont["end"] - 1.0, 0.5)
if "asleep" in SPN:
    s0 = SPN["asleep"]; add(sfx, snore(2.6), s0["vstart"] + 0.1, 0.7)
    sl = [l for l in tl if l["scene"] == "asleep"]
    add(sfx, kick(), sl[1]["start"] + 0.3, 0.8)
if "tuition" in SPN:
    tb = [l for l in tl if l["scene"] == "tuition"][-1]; add(sfx, snore(1.8), tb["start"] + 2.0, 0.4)
if "wake" in SPN:
    wb = [l for l in tl if l["scene"] == "wake"][-1]
    add(sfx, CHIME, wb["start"] + 0.3, 0.6)
    for k in range(3): add(sfx, TICK, wb["start"] + 1.6 + k * 0.2, 0.4)
if "end_call" in SPN:
    e0 = SPN["end_call"]["vstart"]; add(sfx, buzz(2.4), e0 + 0.3, 0.6)
    vl = [l for l in tl if l["scene"] == "end_call" and l.get("mode") != "beat"][0]
    add(sfx, beep(880, 0.12, 0.4), vl["end"] - 0.3); add(sfx, beep(440, 0.5, 0.4), vl["end"] - 0.1)
# ---- Day 5+: dead phone, loadshedding, run, shop generator, no balance, offer, Ammi
def hum(n_s, f=55):
    n = int(n_s * SR); x = np.arange(n) / SR
    return ((np.sin(2 * np.pi * f * x) + 0.5 * np.sin(2 * np.pi * 2 * f * x)) * (1 + 0.3 * np.sin(2 * np.pi * 7 * x)) * 0.25).astype(np.float32)
def sad_trombone():
    out = [beep(f, 0.32, 0.5) for f in (392, 370, 349)] + [beep(330, 0.9, 0.5)]
    return np.concatenate(out)
if "hook_dead" in SPN:
    h0 = SPN["hook_dead"]["vstart"]; add(sfx, buzz(1.4), h0 + 0.1, 0.5); add(sfx, beep(440, 0.5, 0.4), h0 + 1.6)
if "bijli" in SPN:
    bl = [l for l in tl if l["scene"] == "bijli"]; v = [l for l in bl if l.get("mode") != "beat"][0]
    add(sfx, kick(), bl[0]["start"] + 0.4, 0.4); add(sfx, CHIME, bl[0]["start"] + 0.7, 0.4)
    w = [x for x in v["words"] if x["w"].lower().startswith("bijli")]; off = w[0]["t"] if w else v["start"] + 1.2
    add(sfx, hum(off - bl[0]["start"] + 0.0, 50) * 0.6, bl[0]["start"], 0.5); add(sfx, kick(), off, 0.9); add(sfx, noise(0.2, 0.04), off, 0.6)
if "run" in SPN:
    r0 = SPN["run"]["vstart"]
    for k in range(int((SPN["run"]["vend"] - r0) / 0.3)): add(sfx, noise(0.05, 0.01), r0 + 0.1 + k * 0.3, 0.5)
if "bilal_door" in SPN:
    bd = [l for l in tl if l["scene"] == "bilal_door"]; add(sfx, kick(), SPN["bilal_door"]["vstart"] + 0.3, 0.5)
    add(sfx, sad_trombone(), bd[-1]["start"] + 0.1, 0.5)
if "shop" in SPN:
    s0 = SPN["shop"]; add(sfx, hum(s0["vend"] - s0["vstart"], 70), s0["vstart"], 0.35)
    mont = [l for l in tl if l["scene"] == "shop"][-1]
    for k in range(3): add(sfx, TICK, mont["start"] + 0.2 + k * 0.2, 0.4)
    for k in range(10): add(sfx, TICK, mont["start"] + 1.0 + k * 0.22, 0.25)
if "balance" in SPN:
    bv = [l for l in tl if l["scene"] == "balance"][0]
    add(sfx, CHIME, bv["start"] + 0.6, 0.5)
    for k in range(3): add(sfx, beep(425, 0.35, 0.35), bv["start"] + 1.2 + k * 0.6)
    w = [x for x in bv["words"] if x["w"].lower().startswith("balance")]; nb = w[0]["t"] if w else bv["end"] - 0.8
    add(sfx, sad_trombone(), nb + 0.2, 0.55)
if "stranger" in SPN:
    st = [l for l in tl if l["scene"] == "stranger"]; add(sfx, hum(SPN["stranger"]["vend"] - SPN["stranger"]["vstart"], 70), SPN["stranger"]["vstart"], 0.3)
    for k in range(2): add(sfx, TICK, st[0]["start"] + 0.6 + k * 0.25, 0.5)
    add(sfx, CHIME, st[1]["start"] + 1.0, 0.5)
if "callback" in SPN:
    cv = [l for l in tl if l["scene"] == "callback"][0]; add(sfx, CHIME, cv["start"] + 0.1, 0.7)
    w = [x for x in cv["words"] if x["w"].lower().startswith("karachi")]
    if w: add(sfx, kick(), w[0]["t"], 0.8); add(sfx, noise(0.4, 0.1), w[0]["t"], 0.4)
if "ticket" in SPN:
    tk = [l for l in tl if l["scene"] == "ticket"]
    for k in range(4): add(sfx, TICK, tk[0]["start"] + 0.3 + k * 0.3, 0.4)
    add(sfx, kick(), tk[2]["start"] - 0.2, 0.8); add(sfx, kick(), tk[3]["start"] + 0.1, 0.6)
# ---- Day 6+: Ammi, kabadi, potli, bus, station, guard whistle, mosquitoes, 8:40 alarm
def whistle(n_s=0.8):
    n = int(n_s * SR); x = np.arange(n) / SR; f = 2800 + 120 * np.sin(2 * np.pi * 30 * x)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, (n_s - x) / 0.05) * np.minimum(1, x / 0.01) * 0.4).astype(np.float32)
def mozzie(n_s):
    n = int(n_s * SR); x = np.arange(n) / SR; f = 600 + 40 * np.sin(2 * np.pi * 3 * x)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * x)) * 0.06).astype(np.float32)
def engine(n_s):
    n = int(n_s * SR); x = np.arange(n) / SR; s_ = rng.standard_normal(n).astype(np.float32)
    s_ = np.convolve(s_, np.ones(200) / 200, mode="same") * 6
    return ((s_ + 0.4 * np.sin(2 * np.pi * 42 * x)) * 0.3).astype(np.float32)
for nm in ("hook_station", "floor"):
    if nm in SPN: add(sfx, mozzie(SPN[nm]["vend"] - SPN[nm]["vstart"]), SPN[nm]["vstart"], 0.8)
if "ammi" in SPN:
    am = [l for l in tl if l["scene"] == "ammi"]; add(sfx, kick(), am[0]["start"] + 0.1, 0.7); add(sfx, noise(0.3, 0.08), am[-1]["start"] + 0.6, 0.5)
if "kabadi" in SPN:
    kb = [l for l in tl if l["scene"] == "kabadi"]
    for k in range(4): add(sfx, TICK, kb[0]["start"] + 0.2 + k * 0.3, 0.35)
    add(sfx, sad_trombone(), kb[-1]["start"] + 0.2, 0.4)
if "potli" in SPN:
    pt = [l for l in tl if l["scene"] == "potli"]; add(sfx, noise(0.3, 0.1), pt[0]["start"] + 0.3, 0.4); add(sfx, CHIME, pt[-1]["start"] + 0.05, 0.7)
if "abbu_door" in SPN: add(sfx, CHIME, SPN["abbu_door"]["vstart"] + 1.0, 0.4)
if "bus" in SPN:
    b_ = SPN["bus"]; add(sfx, engine(b_["vend"] - b_["vstart"]), b_["vstart"], 0.7)
    for k in range(3): add(sfx, beep(330, 0.25, 0.4), b_["vstart"] + 0.3 + k * 0.32)
if "station" in SPN:
    st_ = [l for l in tl if l["scene"] == "station"]
    for k in range(5): add(sfx, TICK, st_[1]["start"] + 1.4 + k * 0.15, 0.4)
if "guard" in SPN:
    gv = [l for l in tl if l["scene"] == "guard" and l.get("mode") != "beat"][0]
    add(sfx, snore(1.6), SPN["guard"]["vstart"] + 0.1, 0.5); add(sfx, whistle(), gv["start"] + 0.1, 0.7); add(sfx, kick(), gv["end"] - 0.6, 0.7)
if "floor" in SPN:
    fl = [l for l in tl if l["scene"] == "floor"]; add(sfx, CHIME, fl[-1]["start"] + 0.1, 0.5)
if "morning" in SPN:
    mv = [l for l in tl if l["scene"] == "morning" and l.get("mode") != "beat"][0]
    for k in range(8): add(sfx, beep(1900, 0.09, 0.5), mv["start"] - 0.2 + k * 0.17)
    ml = [l for l in tl if l["scene"] == "morning"]
    for k in range(4): add(sfx, kick(), ml[-2]["start"] + k * 0.35, 0.5)
    add(sfx, kick(), ml[-1]["start"], 0.8)
# ---- Day 7+: rickshaw, kick-start, bike engine, traffic horns, buffalo, brake fail, crash, stairs, door, rating, dent
def moo():
    n = int(1.1 * SR); x = np.arange(n) / SR; f = 125 - 35 * x
    s_ = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.3 + np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5
    return (s_ * np.minimum(1, x / 0.15) * np.minimum(1, (1.1 - x) / 0.3) * 0.5).astype(np.float32)
def scrape(n_s):
    n = int(n_s * SR); s_ = rng.standard_normal(n).astype(np.float32); s_ = np.diff(s_, prepend=0)
    return (s_ * (0.5 + 0.5 * np.abs(np.sin(np.arange(n) / SR * 40))) * 0.25).astype(np.float32)
def LS_(nm): return [l for l in tl if l["scene"] == nm]
for nm, g in (("hook_bike", 0.8), ("traffic", 0.4), ("gali", 0.5), ("downhill", 0.9), ("delivery", 0.7)):
    if nm in SPN: add(sfx, engine(SPN[nm]["vend"] - SPN[nm]["vstart"]), SPN[nm]["vstart"], g)
if "hook_bike" in SPN: add(sfx, beep(2600, 0.3, 0.3), SPN["hook_bike"]["vstart"] + 1.7)
if "rickshaw" in SPN:
    rk = LS_("rickshaw"); add(sfx, beep(520, 0.18, 0.4), rk[0]["start"] + 0.5); add(sfx, beep(520, 0.18, 0.4), rk[0]["start"] + 0.75)
    add(sfx, engine(1.4), rk[-1]["start"] + 0.2, 0.6); add(sfx, sad_trombone(), rk[-1]["start"] + 0.5, 0.35)
if "ghafoor" in SPN:
    gf = LS_("ghafoor")
    for k in range(3): add(sfx, TICK, gf[-1]["start"] + 0.1 + k * 0.2, 0.4)
    for k in range(2): add(sfx, kick(), gf[-1]["start"] + 0.6 + k * 0.35, 0.7)
    add(sfx, engine(1.0), gf[-1]["start"] + 1.3, 0.6)
if "traffic" in SPN:
    tr = SPN["traffic"]
    for k in range(int((tr["vend"] - tr["vstart"]) / 0.43)): add(sfx, beep([440, 520, 380][k % 3], 0.2, 0.35), tr["vstart"] + 0.2 + k * 0.43)
if "gali" in SPN:
    gl = LS_("gali"); add(sfx, moo(), gl[0]["start"] + 1.3, 0.8); add(sfx, moo(), gl[1]["start"] + 0.3, 0.6)
if "downhill" in SPN:
    dh = LS_("downhill"); dv = [l for l in dh if l.get("mode") != "beat"][0]
    w = [x for x in dv["words"] if x["w"].lower().startswith("brake")]; bt = w[0]["t"] if w else dv["start"] + 1.0
    add(sfx, beep(2400, 0.15, 0.25), bt); add(sfx, TICK, bt + 0.3, 0.5); add(sfx, TICK, bt + 0.5, 0.5)
    add(sfx, noise(1.6, 0.9) * 0.4, dh[-1]["start"], 0.6)
if "crash" in SPN:
    cr = LS_("crash"); hit = cr[0]["start"] + 0.75
    add(sfx, kick(), hit, 1.0); add(sfx, noise(0.6, 0.15), hit, 0.9)
    for k in range(5): add(sfx, TICK, hit + 0.2 + k * 0.12, 0.5)
    add(sfx, CHIME, cr[1]["start"] + 1.4, 0.5)
if "manager" in SPN:
    mg = LS_("manager"); add(sfx, CHIME, mg[-1]["start"], 0.5)
if "delivery" in SPN:
    dl = SPN["delivery"]; add(sfx, scrape(dl["vend"] - dl["vstart"]), dl["vstart"], 0.5)
    av = [l for l in LS_("delivery") if l.get("mode") != "beat"][0]; add(sfx, beep(1200, 0.08, 0.4), av["start"] - 0.25); add(sfx, beep(1600, 0.08, 0.4), av["start"] - 0.12)
if "stairs" in SPN:
    st2 = SPN["stairs"]
    for k in range(int((st2["vend"] - st2["vstart"]) / 0.19)): add(sfx, TICK, st2["vstart"] + 0.1 + k * 0.19, 0.45)
if "door" in SPN:
    dr = LS_("door")
    for k in range(3): add(sfx, kick(), dr[0]["start"] + k * 0.15, 0.35)
    add(sfx, CHIME, dr[0]["start"] + 0.9, 0.6)
    for k in range(5): add(sfx, TICK, dr[1]["start"] - 0.2 + k * 0.22, 0.5)
    add(sfx, CHIME, dr[-1]["start"], 0.7)
if "dent" in SPN:
    dn = LS_("dent"); add(sfx, kick(), dn[1]["start"] + 0.5, 0.8); add(sfx, sad_trombone(), dn[2]["start"] + 0.1, 0.5)
# ---- Day 8+: rain, thunder, flood splash, doorbell, tip, deal handshake
def rainfx(n_s):
    n = int(n_s * SR); s_ = rng.standard_normal(n).astype(np.float32)
    s_ = np.convolve(s_, np.ones(6) / 6, mode="same"); a = np.minimum(1, np.arange(n) / SR / 0.4) * np.minimum(1, (n_s - np.arange(n) / SR) / 0.4)
    return (s_ * a * 0.35).astype(np.float32)
def thunder():
    n = int(2.2 * SR); x = np.arange(n) / SR; s_ = rng.standard_normal(n).astype(np.float32)
    s_ = np.convolve(s_, np.ones(60) / 60, mode="same")
    return (s_ * np.exp(-x * 1.6) * 6 * (0.6 + 0.4 * np.sin(x * 9) ** 2)).astype(np.float32)
for nm, g in (("hook_rain", 0.8), ("rain", 0.9), ("flood", 0.9), ("vnote", 0.6), ("cake", 0.45), ("tdoor", 0.25)):
    if nm in SPN: add(sfx, rainfx(SPN[nm]["vend"] - SPN[nm]["vstart"]), SPN[nm]["vstart"], g)
if "hook_rain" in SPN:
    add(sfx, engine(SPN["hook_rain"]["vend"] - SPN["hook_rain"]["vstart"]), SPN["hook_rain"]["vstart"], 0.5); add(sfx, thunder(), SPN["hook_rain"]["vstart"] + 0.05, 0.9)
if "deal" in SPN:
    dl_ = LS_("deal"); add(sfx, CHIME, dl_[-1]["start"] + 0.3, 0.6); add(sfx, kick(), dl_[-1]["start"] + 0.1, 0.4)
if "order" in SPN:
    od = LS_("order"); add(sfx, beep(1200, 0.08, 0.5), od[0]["start"] + 0.1); add(sfx, beep(1600, 0.1, 0.5), od[0]["start"] + 0.25)
    add(sfx, thunder(), od[-1]["start"] + 0.3, 0.5)
if "rain" in SPN:
    rn = LS_("rain"); add(sfx, engine(SPN["rain"]["vend"] - SPN["rain"]["vstart"]), SPN["rain"]["vstart"], 0.5)
    add(sfx, kick(), rn[0]["start"] + 0.5, 1.0); add(sfx, thunder(), rn[0]["start"] + 0.5, 1.0)
if "flood" in SPN:
    fd = LS_("flood"); fv = fd[0]; w = [x for x in fv["words"] if x["w"].lower().startswith("engine")]
    et = w[0]["t"] if w else fv["start"] + 1.4
    add(sfx, engine(max(0.3, et - SPN["flood"]["vstart"])), SPN["flood"]["vstart"], 0.6)
    for k in range(3): add(sfx, kick(), et + 0.2 + k * 0.35, 0.5)
    add(sfx, sad_trombone(), fd[1]["start"] + 0.2, 0.5)
    for k in range(int((fd[-1]["end"] - fd[-1]["start"]) / 0.4)): add(sfx, noise(0.15, 0.04), fd[-1]["start"] + k * 0.4, 0.45)
if "vnote" in SPN:
    vq = LS_("vnote"); add(sfx, beep(1200, 0.08, 0.4), vq[0]["start"] - 0.25); add(sfx, beep(1600, 0.08, 0.4), vq[0]["start"] - 0.12)
if "cake" in SPN:
    ck = LS_("cake"); add(sfx, noise(0.3, 0.06), ck[0]["start"] + 0.6, 0.6); add(sfx, sad_trombone(), ck[-1]["start"] + 0.1, 0.4)
if "tdoor" in SPN:
    td = LS_("tdoor"); add(sfx, beep(880, 0.35, 0.5), td[0]["start"] + 0.05); add(sfx, beep(700, 0.45, 0.5), td[0]["start"] + 0.4)
if "troom" in SPN:
    trm = LS_("troom"); tv = [l for l in trm if l.get("mode") != "beat"][-1]
    for k in range(5): add(sfx, TICK, tv["start"] - 0.1 + k * 0.2, 0.5)
    add(sfx, CHIME, tv["start"] + 1.0, 0.7)
if "cliff" in SPN:
    cf = LS_("cliff"); add(sfx, kick(), cf[2]["start"] + 0.05, 0.8)
    for k in range(6): add(sfx, TICK, cf[2]["start"] + 0.2 + k * 0.2, 0.4)
# ---- Day 9+: kick-start, signpost tick, stomach growl, doorbell, pen scratch, stamp, dizzy, biscuit crinkle, message
def growl(n_s=0.9):
    n = int(n_s * SR); x = np.arange(n) / SR; f = 70 + 25 * np.sin(x * 23) + 15 * np.sin(x * 7)
    s_ = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sin(x * 31) ** 2)
    return (s_ * np.minimum(1, x / 0.1) * np.minimum(1, (n_s - x) / 0.25) * 0.8).astype(np.float32)
def scratch(n_s):
    n = int(n_s * SR); s_ = np.diff(rng.standard_normal(n).astype(np.float32), prepend=0)
    return (s_ * (np.sin(np.arange(n) / SR * 2 * np.pi * 6) > 0) * 0.18).astype(np.float32)
if "hook_fork" in SPN:
    hf = SPN["hook_fork"]
    for k in range(int((hf["vend"] - hf["vstart"]) / 0.5)): add(sfx, TICK, hf["vstart"] + 0.1 + k * 0.5, 0.45)
    add(sfx, kick(), LS_("hook_fork")[0]["start"] + 1.5, 0.6)
if "kick" in SPN:
    kk = LS_("kick")
    for k in range(5): add(sfx, kick(), kk[0]["start"] + k * 0.42, 0.7); add(sfx, noise(0.15, 0.04), kk[0]["start"] + 0.08 + k * 0.42, 0.4)
    add(sfx, sad_trombone(), kk[1]["start"] + 0.3, 0.45)
    add(sfx, noise(0.8, 0.5) * 0.4, kk[3]["start"] + 0.6, 0.5)   # petrol glug
    add(sfx, engine(SPN["kick"]["vend"] - kk[4]["start"]), kk[4]["start"], 0.7)
if "fork" in SPN:
    fk = LS_("fork")
    for k in range(4): add(sfx, TICK, fk[0]["start"] + 0.1 + k * 0.3, 0.45)
    add(sfx, engine(SPN["fork"]["vend"] - fk[-1]["start"]), fk[-1]["start"], 0.7); add(sfx, CHIME, fk[-1]["start"] + 0.1, 0.5)
if "briefing" in SPN:
    bf = LS_("briefing"); add(sfx, kick(), bf[0]["start"] + 0.1, 0.4); add(sfx, beep(330, 0.3, 0.4), bf[1]["start"] + 0.05)
    add(sfx, growl(1.0), bf[2]["start"] + 0.05, 1.0); add(sfx, CHIME, bf[-1]["start"] + 0.1, 0.4)
for nm, g in (("montage", 0.7), ("rush", 0.7)):
    if nm in SPN: add(sfx, engine(SPN[nm]["vend"] - SPN[nm]["vstart"]), SPN[nm]["vstart"], g)
if "montage" in SPN:
    for b_ in LS_("montage"): add(sfx, CHIME, b_["start"] + 0.45, 0.5)
if "order3" in SPN:
    o3 = LS_("order3"); add(sfx, beep(1200, 0.08, 0.5), o3[0]["start"] + 0.1); add(sfx, beep(1600, 0.1, 0.5), o3[0]["start"] + 0.25)
    add(sfx, kick(), o3[1]["start"] + 1.6, 0.6)
if "exam" in SPN:
    ex = LS_("exam"); add(sfx, beep(880, 0.35, 0.5), ex[0]["start"] + 0.02); add(sfx, beep(700, 0.45, 0.5), ex[0]["start"] + 0.37)
    add(sfx, kick(), ex[-1]["start"] + 0.05, 0.6)
if "paper" in SPN:
    pp = LS_("paper"); sp_ = SPN["paper"]
    for k in range(int((sp_["vend"] - sp_["vstart"]) / 0.5)): add(sfx, TICK, sp_["vstart"] + k * 0.5, 0.35)
    add(sfx, scratch(0.8), pp[0]["start"] + 0.1, 0.8); add(sfx, sad_trombone(), pp[1]["start"] + 0.2, 0.4)
    add(sfx, scratch(0.9), pp[2]["start"] + 0.3, 0.8); add(sfx, kick(), pp[3]["start"] + 0.1, 1.0); add(sfx, CHIME, pp[3]["start"] + 0.2, 0.7)
if "result" in SPN:
    rs = LS_("result"); add(sfx, CHIME, rs[0]["start"] + 1.2, 0.5)
    for k in range(3): add(sfx, beep(1500, 0.1, 0.45), rs[-1]["start"] + k * 0.2)
if "rush" in SPN:
    ru = LS_("rush"); add(sfx, growl(0.9), ru[2]["start"] + 0.05, 0.8); add(sfx, CHIME, ru[3]["start"] + 0.3, 0.7)
if "end_kid" in SPN:
    ek = LS_("end_kid"); add(sfx, TICK, ek[0]["start"] + 0.2, 0.5); add(sfx, TICK, ek[0]["start"] + 0.4, 0.5)
    add(sfx, noise(0.35, 0.08), ek[2]["start"] + 1.0, 0.4); add(sfx, CHIME, ek[3]["start"] - 0.3, 0.6)
if "cliff9" in SPN:
    c9 = LS_("cliff9"); add(sfx, beep(1200, 0.08, 0.5), c9[0]["start"] + 0.05); add(sfx, beep(1600, 0.1, 0.5), c9[0]["start"] + 0.2)
    add(sfx, kick(), c9[2]["start"] + 0.05, 0.8)
    for k in range(6): add(sfx, TICK, c9[2]["start"] + 0.2 + k * 0.2, 0.4)
# ---- Day 10+: phone rings, NO stamp, call cut, tips, Seth Rauf's hotel, cup flip, payment sent, form closed
def ring(n_s):
    n = int(n_s * SR); x = np.arange(n) / SR
    return ((np.sin(2 * np.pi * 1300 * x) + np.sin(2 * np.pi * 1650 * x)) * ((x % 0.5) < 0.3) * 0.25).astype(np.float32)
if "hook10" in SPN:
    h10 = LS_("hook10"); add(sfx, kick(), h10[0]["start"] + 0.1, 0.6)
    for k in range(4): add(sfx, TICK, h10[1]["start"] + k * 0.25, 0.4)
if "advance10" in SPN:
    a10 = LS_("advance10"); add(sfx, sad_trombone(), a10[2]["start"] + 0.2, 0.4); add(sfx, kick(), a10[3]["start"] + 0.2, 1.0)
if "bilal10" in SPN:
    b10 = LS_("bilal10"); add(sfx, ring(1.0), b10[0]["start"], 0.6)
    add(sfx, beep(500, 0.12, 0.5), b10[3]["start"] + 0.15); add(sfx, beep(400, 0.18, 0.5), b10[3]["start"] + 0.3)
if "tips10" in SPN:
    add(sfx, engine(SPN["tips10"]["vend"] - SPN["tips10"]["vstart"]), SPN["tips10"]["vstart"], 0.6)
    for b_ in LS_("tips10"): add(sfx, CHIME, b_["start"] + 0.2, 0.5)
if "call10" in SPN:
    c10 = LS_("call10"); add(sfx, ring(1.0), c10[0]["start"], 0.6)
    for k in range(3): add(sfx, TICK, c10[3]["start"] + 0.1 + k * 0.25, 0.45)
    add(sfx, kick(), c10[4]["start"] + 1.2, 0.6)
if "rauf10" in SPN:
    r10 = LS_("rauf10"); add(sfx, kick(), r10[1]["start"] + 0.05, 0.5); add(sfx, CHIME, r10[2]["start"] + 0.4, 0.5)
if "shift10" in SPN:
    s10 = LS_("shift10")
    for k in range(6): add(sfx, TICK, s10[0]["start"] + k * 0.4, 0.35)
    add(sfx, WHOOSH, s10[2]["start"], 0.8); add(sfx, sad_trombone(), s10[2]["start"] + 0.3, 0.3)
    add(sfx, bell(), s10[3]["start"] + 0.35, 0.6); add(sfx, CHIME, s10[3]["start"] + 0.4, 0.6)
    for k in range(6): add(sfx, noise(0.08, 0.02), s10[4]["start"] + k * 0.15, 0.4)   # claps
    for k in range(4): add(sfx, TICK, s10[5]["start"] + 1.0 + k * 0.2, 0.4)
if "choice10" in SPN:
    ch10 = LS_("choice10")
    for k in range(int((SPN["choice10"]["vend"] - SPN["choice10"]["vstart"]) / 0.5)): add(sfx, TICK, SPN["choice10"]["vstart"] + k * 0.5, 0.3)
    add(sfx, beep(1200, 0.08, 0.5), ch10[2]["start"] + 0.45); add(sfx, CHIME, ch10[2]["start"] + 0.55, 0.6)
    add(sfx, kick(), ch10[3]["start"] + 0.4, 1.0); add(sfx, sad_trombone(), ch10[3]["start"] + 0.5, 0.35)
if "end10" in SPN:
    e10 = LS_("end10"); add(sfx, beep(1200, 0.08, 0.4), e10[0]["start"] + 0.9); add(sfx, beep(1600, 0.08, 0.4), e10[0]["start"] + 1.0)
    add(sfx, CHIME, e10[1]["start"] - 0.4, 0.6)
if "cliff10" in SPN:
    cl10 = LS_("cliff10"); add(sfx, beep(1200, 0.08, 0.5), cl10[0]["start"] + 0.05); add(sfx, beep(1600, 0.1, 0.5), cl10[0]["start"] + 0.2)
    add(sfx, kick(), cl10[2]["start"] + 0.05, 0.8)
    for k in range(5): add(sfx, TICK, cl10[2]["start"] + 0.2 + k * 0.2, 0.4)
# ---- Day 11+: shart text, snooze + shout, no bike, city bus + jam honks, run, gate whistle, coin, exam hall blackout, bell, result
def honk(n_s=0.35):
    n = int(n_s * SR); x = np.arange(n) / SR
    return (np.sign(np.sin(2 * np.pi * 420 * x)) * 0.18 * np.exp(-x * 2)).astype(np.float32)
if "hook11" in SPN:
    h11 = LS_("hook11"); add(sfx, kick(), h11[0]["start"] + 0.1, 0.6); add(sfx, kick(), h11[1]["start"] + 0.05, 1.0)
if "shart11" in SPN:
    s11 = LS_("shart11"); add(sfx, beep(1200, 0.08, 0.5), s11[0]["start"] + 0.05); add(sfx, beep(1600, 0.1, 0.5), s11[0]["start"] + 0.2)
    add(sfx, kick(), s11[1]["start"] + 0.05, 0.7); add(sfx, CHIME, s11[2]["end"] - 0.2, 0.5)
if "sleep11" in SPN:
    z11 = LS_("sleep11"); add(sfx, snore(2.4), z11[0]["start"] + 0.1, 0.6)
    for k in range(10): add(sfx, TICK, z11[1]["start"] + k * 0.11, 0.4)
    add(sfx, kick(), z11[2]["start"], 0.8); add(sfx, WHOOSH, z11[3]["start"] + 0.5, 0.7)
if "ghafoor11" in SPN:
    g11 = LS_("ghafoor11")
    for k in range(4): add(sfx, noise(0.05, 0.01), g11[0]["start"] + k * 0.15, 0.5)
    add(sfx, kick(), g11[2]["start"] + 0.45, 1.0); add(sfx, sad_trombone(), g11[2]["start"] + 0.55, 0.35)
if "bus11" in SPN:
    u11 = LS_("bus11"); sp_ = SPN["bus11"]
    add(sfx, engine(u11[3]["start"] - sp_["vstart"]), sp_["vstart"], 0.6)
    for k in range(3): add(sfx, TICK, u11[0]["start"] + 0.5 + k * 0.15, 0.45)
    add(sfx, beep(1200, 0.08, 0.4), u11[2]["start"] - 0.2)
    for k in range(3): add(sfx, honk(), u11[3]["start"] + k * 0.35, 0.8)
    for k in range(int((sp_["vend"] - u11[5]["start"]) / 0.18)): add(sfx, noise(0.04, 0.01), u11[5]["start"] + k * 0.18, 0.45)
if "gate11" in SPN:
    q11 = LS_("gate11"); add(sfx, whistle(0.6), q11[0]["start"] + 0.2, 0.6)
    for k in range(6): add(sfx, TICK, q11[3]["start"] + k * 0.2, 0.45)
if "kid11" in SPN:
    k11 = LS_("kid11"); add(sfx, bell(), k11[1]["start"] + 0.5, 0.5); add(sfx, CHIME, k11[2]["start"] + 1.2, 0.5)
    add(sfx, kick(), k11[3]["start"] + 0.3, 0.6); add(sfx, CHIME, k11[3]["start"] + 0.35, 0.6)
if "hall11" in SPN:
    l11 = LS_("hall11"); sp_ = SPN["hall11"]
    add(sfx, hum(l11[2]["start"] - sp_["vstart"], 60) * 0.5, sp_["vstart"], 0.4)
    for k in range(int((sp_["vend"] - sp_["vstart"]) / 0.5)): add(sfx, TICK, sp_["vstart"] + k * 0.5, 0.25)
    for k in range(5): add(sfx, scratch(0.2), l11[1]["start"] + k * 0.25, 0.4)
    add(sfx, kick(), l11[2]["start"], 1.0); add(sfx, sad_trombone(), l11[2]["start"] + 0.15, 0.35)
    add(sfx, bell(), l11[5]["start"] + 0.05, 0.8)
if "end11" in SPN:
    e11 = LS_("end11"); add(sfx, CHIME, e11[3]["start"] - 0.2, 0.6)
if "cliff11" in SPN:
    c11 = LS_("cliff11"); add(sfx, noise(0.25, 0.06), c11[0]["start"] + 0.1, 0.4)
    add(sfx, kick(), c11[1]["start"] + 0.05, 1.0)
    for k in range(5): add(sfx, TICK, c11[1]["start"] + 0.2 + k * 0.2, 0.4)
# ---- Day 12: result shock, two texts, lunch rush, runaway customer + chase (goat, chappal), paid, deal, keys, recheck call
if "hook12" in SPN:
    h12 = LS_("hook12"); add(sfx, kick(), h12[0]["start"] + 0.1, 0.6); add(sfx, kick(), h12[1]["start"] + 0.05, 1.0)
if "msg12" in SPN:
    m12 = LS_("msg12")
    for j in (0, 1): add(sfx, beep(1200, 0.08, 0.5), m12[j]["start"] + 0.05); add(sfx, beep(1600, 0.1, 0.5), m12[j]["start"] + 0.2)
    for k in range(3): add(sfx, TICK, m12[3]["start"] + 0.1 + k * 0.25, 0.45)
    add(sfx, kick(), m12[3]["start"] + 0.55, 0.7)
if "rauf12" in SPN:
    r12 = LS_("rauf12"); add(sfx, kick(), r12[2]["start"], 0.6)
    for k in range(6): add(sfx, noise(0.04, 0.01), r12[3]["start"] + k * 0.18, 0.4)
    add(sfx, CHIME, r12[4]["start"] + 0.1, 0.4)
if "chase12" in SPN:
    c12 = LS_("chase12"); sp_ = SPN["chase12"]
    add(sfx, WHOOSH, c12[0]["start"] + 0.5, 0.7); add(sfx, kick(), c12[2]["start"], 0.8)
    for k in range(int((c12[6]["start"] - c12[2]["start"]) / 0.18)): add(sfx, noise(0.04, 0.01), c12[2]["start"] + k * 0.18, 0.45)
    add(sfx, WHOOSH, c12[4]["start"] + 0.35, 0.8); add(sfx, WHOOSH, c12[5]["start"], 0.6); add(sfx, sad_trombone(), c12[5]["start"] + 0.3, 0.3)
    add(sfx, CHIME, c12[7]["start"] + 0.3, 0.6)
if "paid12" in SPN:
    p12 = LS_("paid12"); add(sfx, CHIME, p12[0]["start"] + 0.1, 0.5)
if "saleem12" in SPN:
    s12 = LS_("saleem12"); add(sfx, kick(), s12[3]["start"], 0.6); add(sfx, CHIME, s12[3]["start"] + 0.3, 0.6)
if "ghafoor12" in SPN:
    g12 = LS_("ghafoor12"); add(sfx, kick(), g12[0]["start"] + 0.9, 0.7); add(sfx, bell(), g12[1]["start"] + 0.3, 0.4)
    add(sfx, engine(g12[3]["start"] - g12[2]["start"]), g12[2]["start"], 0.5); add(sfx, CHIME, g12[3]["start"] - 0.2, 0.6)
if "cliff12" in SPN:
    q12 = LS_("cliff12"); add(sfx, beep(1200, 0.08, 0.4), q12[1]["start"] - 0.2); add(sfx, kick(), q12[2]["start"] + 0.6, 0.5)
    add(sfx, ring(1.2), q12[3]["start"], 0.6); add(sfx, kick(), q12[4]["start"] + 0.05, 1.0)
    for k in range(5): add(sfx, TICK, q12[4]["start"] + 0.2 + k * 0.2, 0.4)
# ---- Day 13: 90% chime, deadline stamp + ticks, tuition chaos + paper plane, video call, bus horn, ride, dummy phone reveal
if "hook13" in SPN:
    h13 = LS_("hook13"); add(sfx, beep(1200, 0.08, 0.5), h13[0]["start"] + 0.02); add(sfx, CHIME, h13[0]["start"] + 0.3, 0.6)
    add(sfx, kick(), h13[0]["start"] + 2.3, 0.9)
if "office13" in SPN:
    o13 = LS_("office13"); add(sfx, CHIME, o13[0]["start"] + 0.1, 0.4); add(sfx, kick(), o13[1]["start"] + 0.05, 0.7)
    add(sfx, kick(), o13[2]["start"], 1.0)
    for k in range(4): add(sfx, TICK, o13[2]["start"] + 0.1 + k * 0.15, 0.45)
if "tuition13" in SPN:
    u13 = LS_("tuition13"); sp_ = SPN["tuition13"]
    for k in range(int((u13[1]["start"] - sp_["vstart"]) / 0.22)): add(sfx, noise(0.05, 0.015), sp_["vstart"] + k * 0.22, 0.35)
    add(sfx, ring(0.6), u13[1]["start"] - 0.3, 0.4)
    add(sfx, WHOOSH, u13[3]["start"], 0.6); add(sfx, kick(), u13[3]["start"] + 0.35, 0.8)
if "bilal13" in SPN:
    b13 = LS_("bilal13"); add(sfx, beep(1000, 0.1, 0.4), b13[0]["start"] - 0.15); add(sfx, kick(), b13[1]["start"] + 1.0, 0.6)
    add(sfx, CHIME, b13[2]["start"] + 1.3, 0.4)
if "adda13" in SPN:
    a13 = LS_("adda13")
    for k in range(6): add(sfx, TICK, a13[0]["start"] + 0.2 + k * 0.35, 0.35)
    add(sfx, honk(0.5), a13[1]["start"], 0.9); add(sfx, honk(0.3), a13[1]["start"] + 0.35, 0.8)
    add(sfx, CHIME, a13[2]["start"] + 0.1, 0.5); add(sfx, engine(a13[2]["end"] - a13[2]["start"] + 0.2), a13[2]["start"] + 0.6, 0.6)
if "cliff13" in SPN:
    c13 = LS_("cliff13"); add(sfx, bell(), c13[0]["start"] + 0.1, 0.5); add(sfx, noise(0.3, 0.08), c13[1]["start"] + 0.5, 0.5)
    add(sfx, kick(), c13[2]["start"], 1.0); add(sfx, sad_trombone(), c13[2]["start"] + 0.15, 0.35)
    for k in range(5): add(sfx, TICK, c13[3]["end"] - 0.2 + k * 0.2, 0.4)
# ---- Day 14: dummy phone sting, ticking deadline, video call, facepalm, ride + red light + engine dies, samosa laugh, rickshaw, stamp, two clocks
if "hook14" in SPN:
    h14 = LS_("hook14"); add(sfx, kick(), h14[0]["start"] + 1.3, 0.9); add(sfx, sad_trombone(), h14[0]["start"] + 1.5, 0.3)
    for k in range(8): add(sfx, TICK, h14[1]["start"] + k * 0.25, 0.4)
if "call14" in SPN:
    c14 = LS_("call14"); add(sfx, ring(0.6), c14[0]["start"] - 0.3, 0.4); add(sfx, kick(), c14[3]["start"], 0.9)
    add(sfx, WHOOSH, c14[4]["start"] + 1.6, 0.7)
if "race14" in SPN:
    r14 = LS_("race14"); add(sfx, engine(r14[1]["start"] + 1.4 - SPN["race14"]["vstart"]), SPN["race14"]["vstart"], 0.6)
    add(sfx, honk(0.4), r14[1]["start"] + 0.2, 0.7); add(sfx, kick(), r14[2]["start"], 0.8); add(sfx, sad_trombone(), r14[2]["start"] + 0.1, 0.35)
if "adda14" in SPN:
    a14 = LS_("adda14")
    for k in range(5): add(sfx, noise(0.04, 0.01), a14[0]["start"] + k * 0.18, 0.45)
    add(sfx, kick(), a14[2]["start"], 0.7); add(sfx, honk(0.3), a14[3]["start"] + 0.1, 0.8); add(sfx, honk(0.3), a14[3]["start"] + 0.45, 0.7)
if "back14" in SPN:
    b14 = LS_("back14")
    for k in range(4): add(sfx, TICK, b14[0]["start"] + k * 0.3, 0.4)
    add(sfx, CHIME, b14[1]["start"] + 0.1, 0.6); add(sfx, kick(), b14[2]["start"], 1.0); add(sfx, CHIME, b14[2]["start"] + 0.1, 0.6)
if "cliff14" in SPN:
    q14 = LS_("cliff14"); add(sfx, beep(1200, 0.08, 0.5), q14[1]["start"] + 0.02); add(sfx, beep(1600, 0.1, 0.5), q14[1]["start"] + 0.17)
    add(sfx, kick(), q14[1]["end"] - 1.2, 1.0)
    for k in range(5): add(sfx, TICK, q14[1]["end"] - 1.0 + k * 0.2, 0.4)
# ---- Day 15: two clocks tick, helmet drop, bike zooms off, class bell, phone buzz, confiscation stamp, missed-call beeps, office stamp, Ammi ring
if "hook15" in SPN:
    h15 = LS_("hook15")
    for k in range(6): add(sfx, TICK, h15[0]["start"] + 1.4 + k * 0.22, 0.4)
if "plan15" in SPN:
    p15 = LS_("plan15"); add(sfx, kick(), p15[2]["start"] + 0.75, 0.6); add(sfx, sad_trombone(), p15[3]["start"] - 0.3, 0.0)
    add(sfx, engine(0.8), p15[3]["start"], 0.7); add(sfx, honk(0.3), p15[3]["start"] + 0.1, 0.6)
if "class15" in SPN:
    c15 = LS_("class15"); add(sfx, bell(), c15[0]["start"], 0.5); add(sfx, buzz(1.2), c15[1]["start"] - 0.4, 0.5)
    add(sfx, kick(), c15[3]["start"] + 0.4, 0.9); add(sfx, kick(), c15[4]["start"], 0.6)
if "msg15" in SPN:
    m15 = LS_("msg15")
    for k in range(4): add(sfx, beep(1200, 0.07, 0.4), m15[0]["start"] + 0.2 + k * 0.18)
    add(sfx, beep(1600, 0.1, 0.5), m15[1]["start"] + 0.05); add(sfx, kick(), m15[2]["start"], 1.0); add(sfx, sad_trombone(), m15[2]["start"] + 0.1, 0.3)
if "office15" in SPN:
    o15 = LS_("office15")
    for k in range(5): add(sfx, noise(0.04, 0.01), o15[0]["start"] + k * 0.15, 0.45)
    add(sfx, CHIME, o15[3]["start"] + 0.1, 0.5); add(sfx, kick(), o15[4]["start"], 1.0); add(sfx, CHIME, o15[4]["start"] + 0.1, 0.6)
if "cliff15" in SPN:
    q15 = LS_("cliff15"); add(sfx, ring(0.8), q15[0]["start"] - 0.5, 0.5); add(sfx, kick(), q15[0]["start"] + 1.0, 0.8)
    for k in range(5): add(sfx, TICK, q15[1]["start"] + 0.5 + k * 0.25, 0.4)
# ---- Day 16: hospital beeps, Ammi ring, message pings + REJECTED stamp, dummy-phone toss + trombone, Rauf's table slam, notes, payment chime, packet whisper ticks
if "hook16" in SPN:
    h16 = LS_("hook16")
    for k in range(4): add(sfx, beep(1000, 0.08, 0.35), h16[0]["start"] + 1.4 + k * 0.45)
    add(sfx, kick(), h16[0]["end"] - 0.6, 0.8)
if "call16" in SPN:
    c16 = LS_("call16"); add(sfx, ring(0.8), c16[0]["start"] - 0.5, 0.5); add(sfx, kick(), c16[0]["start"] + 1.6, 0.7)
if "office16" in SPN:
    o16 = LS_("office16"); add(sfx, beep(1600, 0.1, 0.5), o16[0]["start"] + 0.3); add(sfx, beep(1200, 0.08, 0.5), o16[1]["start"] + 0.2)
    add(sfx, kick(), o16[2]["start"], 1.0); add(sfx, sad_trombone(), o16[2]["start"] + 0.1, 0.3)
if "bilal16" in SPN:
    b16 = LS_("bilal16"); add(sfx, CHIME, b16[0]["start"] + 1.0, 0.4); add(sfx, WHOOSH, b16[1]["start"], 0.7)
    add(sfx, kick(), b16[1]["start"] + 0.5, 0.8); add(sfx, sad_trombone(), b16[1]["start"] + 0.7, 0.35)
if "rauf16" in SPN:
    r16 = LS_("rauf16"); add(sfx, kick(), r16[1]["start"] + 0.05, 0.9); add(sfx, kick(), r16[1]["start"] + 1.0, 0.6)
    for k in range(3): add(sfx, TICK, r16[3]["start"] + k * 0.18, 0.45)
    for k in range(5): add(sfx, noise(0.05, 0.012), r16[4]["start"] + 0.2 + k * 0.12, 0.45)
    add(sfx, CHIME, r16[4]["start"] + 0.5, 0.6)
if "send16" in SPN:
    s16 = LS_("send16"); add(sfx, beep(1400, 0.08, 0.5), s16[0]["start"] + 0.4); add(sfx, CHIME, s16[0]["start"] + 1.2, 0.7)
    add(sfx, ring(0.6), s16[1]["start"] - 0.4, 0.4); add(sfx, kick(), s16[2]["start"], 0.8); add(sfx, CHIME, s16[2]["start"] + 0.1, 0.6)
if "cliff16" in SPN:
    q16 = LS_("cliff16"); add(sfx, kick(), q16[0]["start"] + 0.3, 0.7); add(sfx, kick(), q16[1]["start"] + 0.1, 1.0)
    for k in range(6): add(sfx, TICK, q16[2]["start"] + 0.2 + k * 0.25, 0.4)
# ---- Cold-open hook sting (owner, 2026-11-19: ear-catching start so people don't skip): boom + crack + brass stab + whoosh at 0 s
HOOK = _DAY >= 15 or "hook" in (json.load(open(f"{D}/meta.json")) if os.path.exists(f"{D}/meta.json") else {})
if HOOK:
    n_ = int(0.9 * SR); x_ = np.arange(n_) / SR
    boom = (np.sin(2 * np.pi * (48 + 60 * np.exp(-x_ * 18)) * x_) * np.exp(-x_ * 4.5)).astype(np.float32)
    crack = (rng.standard_normal(int(0.12 * SR)) * np.exp(-np.arange(int(0.12 * SR)) / SR * 40)).astype(np.float32)
    def stab(f0, n_s=0.32):
        m = int(n_s * SR); xx = np.arange(m) / SR
        return (sum(((xx * f) % 1 * 2 - 1) for f in (f0, f0 * 1.26, f0 * 1.5, f0 * 2)) * 0.18 * np.minimum(1, xx / 0.006) * np.exp(-xx * 7)).astype(np.float32)
    add(sfx, boom, 0.0, 1.0); add(sfx, kick(), 0.0, 1.0); add(sfx, crack, 0.0, 0.7)
    add(sfx, stab(220), 0.02, 0.9); add(sfx, stab(277), 0.55, 0.8)
    add(sfx, WHOOSH, 1.15, 0.6)   # out of the cold open into the story
night = next((s for s in scenes if s["scene"] == "night"), None)
if night: add(sfx, crickets(night["vend"] - night["vstart"]), night["vstart"])

venv = np.convolve(np.abs(voice), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
duck = 1 - 0.5 * np.clip(venv / (venv.max() * 0.25 + 1e-9), 0, 1)
fade = np.ones(N, np.float32)
if not HOOK: fade[:int(0.4 * SR)] = np.linspace(0, 1, int(0.4 * SR))
fade[-int(1.4 * SR):] = np.linspace(1, 0, int(1.4 * SR)); 
mix = voice + music * 0.55 * duck * fade + sfx * 0.6
mix = mix / (np.abs(mix).max() + 1e-9) * 0.95
mix.astype(np.float32).tofile(f"{D}/mix.f32")
subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f"{D}/mix.f32",
                       "-af", "highpass=f=60,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,loudnorm=I=-14:TP=-1.5:LRA=9",
                       "-ar", str(SR), "-ac", "2", f"{D}/mix.wav"])
print("total", round(TOTAL, 2), [(s["scene"], round(s["vstart"], 1)) for s in scenes])
