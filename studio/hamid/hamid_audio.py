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

def load(p):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()

def trim(x, th=0.02):
    k = int(0.02 * SR); e = np.convolve(np.abs(x), np.ones(k) / k, mode="same")
    idx = np.where(e > th * e.max())[0] if e.max() > 0 else []
    if len(idx) == 0: return x
    return x[max(0, idx[0] - int(0.03 * SR)): min(len(x), idx[-1] + int(0.08 * SR))]

INTRO = 0.35
t = INTRO; tl = []; clips = []
prev_scene = None
for i, l in enumerate(lines):
    v = trim(load(f"{D}/v{i:02d}.wav")); v = v / (np.abs(v).max() + 1e-9) * 0.9
    if prev_scene is not None and l["scene"] != prev_scene: t += 0.45   # breath between scenes
    d = len(v) / SR
    words = l["rom"].split()
    wts = np.array([max(2, len(w.strip(".,!?…\""))) + 1.5 for w in words], float)
    cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum()
    rw = [{"w": w, "t": t + 0.03 + cum[k] * (d - 0.12)} for k, w in enumerate(words)]
    tl.append({**l, "start": t, "end": t + d, "words": rw})
    clips.append((t, v, l["who"], l.get("mode")))
    t += d + 0.28; prev_scene = l["scene"]
TOTAL = t + 1.6
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
night = next((s for s in scenes if s["scene"] == "night"), None)
if night: add(sfx, crickets(night["vend"] - night["vstart"]), night["vstart"])

venv = np.convolve(np.abs(voice), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
duck = 1 - 0.5 * np.clip(venv / (venv.max() * 0.25 + 1e-9), 0, 1)
fade = np.ones(N, np.float32); fade[:int(0.4 * SR)] = np.linspace(0, 1, int(0.4 * SR)); fade[-int(1.4 * SR):] = np.linspace(1, 0, int(1.4 * SR))
mix = voice + music * 0.55 * duck * fade + sfx * 0.6
mix = mix / (np.abs(mix).max() + 1e-9) * 0.95
mix.astype(np.float32).tofile(f"{D}/mix.f32")
subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f"{D}/mix.f32",
                       "-af", "highpass=f=60,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,loudnorm=I=-14:TP=-1.5:LRA=9",
                       "-ar", str(SR), "-ac", "2", f"{D}/mix.wav"])
print("total", round(TOTAL, 2), [(s["scene"], round(s["vstart"], 1)) for s in scenes])
