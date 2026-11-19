"""'Aap Kya Karte?' daily thriller: timeline + dark synthesized score/SFX mix (all free, made in code).
Usage: thriller_audio.py <episode dir>  -> timeline.json + mix.wav. Exits 3 if the reel breaks the format rules."""
import json, os, subprocess, sys
import numpy as np
D = sys.argv[1]; SR = 48000
S = json.load(open(f"{D}/script.json")); lines = S["lines"]; SHOTS = S["shots"]
META = json.load(open(f"{D}/meta.json"))
rng = np.random.default_rng(7)
HSFX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hamid", "sfx") + "/"
def load(p, tempo=1.0):
    af = ["-af", f"atempo={tempo}"] if abs(tempo - 1) > 1e-3 else []
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", p] + af + ["-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()
def trim(x, th=0.02):
    k = int(0.02 * SR); e = np.convolve(np.abs(x), np.ones(k) / k, mode="same")
    idx = np.where(e > th * e.max())[0] if e.max() > 0 else []
    return x if len(idx) == 0 else x[max(0, idx[0] - int(0.03 * SR)): min(len(x), idx[-1] + int(0.08 * SR))]
TEMPO = 1.0; GAP = 0.07; SHOT_GAP = 0.05; INTRO = 0.25
t = INTRO; tl = []; clips = []; prev = None
for i, l in enumerate(lines):
    if l.get("mode") == "beat": v = np.zeros(int(min(float(l.get("dur", 0.6)), 0.7) * SR), np.float32)
    else: v = trim(load(f"{D}/v{i:02d}.wav", TEMPO)); v = v / (np.abs(v).max() + 1e-9) * 0.9
    if prev is not None and l["shot"] != prev: t += SHOT_GAP
    d = len(v) / SR
    words = l["rom"].split() if l.get("mode") != "beat" else []
    wts = np.array([max(2, len(w.strip(".,!?…\""))) + 1.5 for w in words] or [1.0], float)
    cum = np.concatenate([[0], np.cumsum(wts)]) / wts.sum()
    tl.append({**l, "i": i, "start": t, "end": t + d, "words": [{"w": w, "t": t + 0.03 + cum[k] * (d - 0.12)} for k, w in enumerate(words)]})
    clips.append((t, v, l)); t += d + GAP; prev = l["shot"]
TOTAL = t + 1.2
# ---- format rules (owner, 2026-11-19): 45-60 s, voice always going (max 3 short beats, never 2 in a row), cold-open hook, ends on the question
beats = [i for i, l in enumerate(lines) if l.get("mode") == "beat"]; errs = []
if len(beats) > 3: errs.append(f"{len(beats)} wordless beats (max 3)")
if any(b + 1 in beats for b in beats): errs.append("two beats in a row")
if not 45 <= TOTAL <= 62: errs.append(f"length {TOTAL:.1f} s (want 45-60)")
if not (META.get("hook") or {}).get("text"): errs.append('meta.json needs "hook": {"text", "emoji", "sub"}')
if not lines[-1].get("final") or "choice" not in SHOTS[lines[-1]["shot"]]: errs.append("last line must be the 'final' question on a shot with \"choice\": {a, b}")
if errs: print("THRILLER RULES BROKEN:", "; ".join(errs), "- rewrite script.json"); sys.exit(3)
shots = []
for l in tl:
    if not shots or shots[-1]["shot"] != l["shot"]: shots.append({"shot": l["shot"], "start": l["start"], "end": l["end"]})
    else: shots[-1]["end"] = l["end"]
for k in range(len(shots)):
    shots[k]["vstart"] = 0 if k == 0 else (shots[k - 1]["end"] + shots[k]["start"]) / 2
    shots[k]["vend"] = TOTAL if k == len(shots) - 1 else (shots[k]["end"] + shots[k + 1]["start"]) / 2
json.dump({"total": TOTAL, "lines": tl, "shots": shots}, open(f"{D}/timeline.json", "w"), ensure_ascii=False, indent=1)

N = int(TOTAL * SR); voice = np.zeros(N, np.float32); music = np.zeros(N, np.float32); sfx = np.zeros(N, np.float32)
def add(buf, sig, at, g=1.0):
    a = int(at * SR)
    if a >= len(buf) or a + len(sig) <= 0: return
    if a < 0: sig = sig[-a:]; a = 0
    m = min(len(sig), len(buf) - a); buf[a:a + m] += sig[:m] * g
for st, v, l in clips:
    if l.get("radio"):   # radio voice: band-pass + crackle
        f = np.fft.rfft(v); fr = np.fft.rfftfreq(len(v), 1 / SR); f[(fr < 350) | (fr > 3200)] = 0
        v = np.fft.irfft(f, len(v)).astype(np.float32); v = v / (np.abs(v).max() + 1e-9) * 0.85 + rng.standard_normal(len(v)).astype(np.float32) * 0.015
    add(voice, v, st)
x = np.arange(N) / SR
def env(n, a, r): e = np.ones(n, np.float32); ai = max(1, int(a * SR)); e[:ai] = np.linspace(0, 1, ai); e *= np.exp(-np.arange(n) / SR / r); return e
# score: low drone (D minor), slow pulse, high eerie tone
for f0, g in ((36.7, 0.30), (73.4, 0.18), (110.0, 0.08), (87.3, 0.07)):
    music += (np.sin(2 * np.pi * f0 * x + np.sin(2 * np.pi * 0.07 * x) * 2) * g).astype(np.float32)
music += (np.sin(2 * np.pi * 1174.7 * x) * 0.012 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * x))).astype(np.float32)
def kick():
    n = int(0.35 * SR); xx = np.arange(n) / SR
    return (np.sin(2 * np.pi * (45 + 90 * np.exp(-xx * 30)) * xx) * np.exp(-xx * 9)).astype(np.float32)
def heartbeat(at):
    add(sfx, kick(), at, 0.9); add(sfx, kick(), at + 0.24, 0.6)
def noise(n_s, r): n = int(n_s * SR); return (rng.standard_normal(n) * env(n, 0.002, r)).astype(np.float32)
def try_load(p):
    try: return load(p)
    except Exception: return np.zeros(1, np.float32)
WHOOSH = try_load(HSFX + "sfx_whoosh.mp3"); TICK = try_load(HSFX + "sfx_tick.mp3")
def sting():
    n = int(1.6 * SR); xx = np.arange(n) / SR
    return (sum(np.sin(2 * np.pi * f * xx) for f in (146.8, 155.6, 311.1, 466.2)) * 0.12 * np.minimum(1, xx / 0.01) * np.exp(-xx * 1.8)).astype(np.float32)
def knock(at):
    for k in range(2): add(sfx, (noise(0.09, 0.02) * 0.6 + kick()[:int(0.09 * SR)] * 0.9), at + k * 0.22, 1.0)
def brake(at):
    n = int(0.9 * SR); xx = np.arange(n) / SR
    add(sfx, (np.sin(2 * np.pi * (2400 - 600 * xx) * xx) * 0.08 * np.exp(-xx * 2.5) + noise(0.9, 0.4) * 0.1).astype(np.float32), at, 0.7)
def baby(at, n_s=2.2):
    n = int(n_s * SR); xx = np.arange(n) / SR; f = 520 + 120 * np.sin(2 * np.pi * 1.6 * xx)
    s_ = np.sin(2 * np.pi * np.cumsum(f) / SR) * (np.sin(2 * np.pi * 0.9 * xx) > -0.2) * 0.12
    add(sfx, s_.astype(np.float32), at, 0.5)
def thunder(at): add(sfx, (noise(2.0, 0.7) * 0.35), at, 0.8); add(sfx, kick(), at, 0.8)
def ring(at, n_s=1.5):
    n = int(n_s * SR); xx = np.arange(n) / SR
    add(sfx, ((np.sin(2 * np.pi * 1300 * xx) + np.sin(2 * np.pi * 1650 * xx)) * ((xx % 0.5) < 0.3) * 0.2).astype(np.float32), at, 0.6)
SFXF = {"heartbeat": heartbeat, "sting": lambda a: add(sfx, sting(), a, 0.8), "knock": knock, "brake": brake, "baby": baby, "thunder": thunder,
        "phone": ring, "whoosh": lambda a: add(sfx, WHOOSH, a, 0.6), "tick": lambda a: [add(sfx, TICK, a + k * 0.5, 0.4) for k in range(6)]}
# cold-open hook sting (eye + ear catching start): boom + crack + dissonant stab at 0 s
add(sfx, kick(), 0.0, 1.2); add(sfx, noise(0.15, 0.03), 0.0, 0.7); add(sfx, sting(), 0.02, 1.0); add(sfx, WHOOSH, 1.15, 0.6)
for s in shots[1:]: add(sfx, WHOOSH, s["vstart"] - 0.2, 0.25)
for l in tl:
    for nm in l.get("sfx", []):
        if nm in SFXF: SFXF[nm](l["start"])
    if "pop" in l and "UAAA" in l["pop"]: baby(l["start"] + 0.4, max(1.0, l["end"] - l["start"]))
for s in shots:
    fx = SHOTS[s["shot"]].get("fx", [])
    if "heartbeat" in fx:
        for k in range(int((s["vend"] - s["vstart"]) / 0.85)): heartbeat(s["vstart"] + 0.1 + k * 0.85)
    if "rain" in fx or "rain_glass" in fx:
        n = int((s["vend"] - s["vstart"]) * SR); r_ = rng.standard_normal(n).astype(np.float32); r_ = np.convolve(r_, np.ones(6) / 6, mode="same") * 0.05
        add(sfx, r_, s["vstart"])
    if "choice" in SHOTS[s["shot"]]: add(sfx, sting(), s["vstart"] + 0.05, 0.8); [add(sfx, TICK, s["vstart"] + 1.0 + k * 0.5, 0.3) for k in range(int((s["vend"] - s["vstart"] - 1.5) / 0.5))]
venv = np.convolve(np.abs(voice), np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")
duck = 1 - 0.5 * np.clip(venv / (venv.max() * 0.25 + 1e-9), 0, 1)
fade = np.ones(N, np.float32); fade[-int(1.2 * SR):] = np.linspace(1, 0, int(1.2 * SR))
mix = voice + music * 0.5 * duck * fade + sfx * 0.6
mix = mix / (np.abs(mix).max() + 1e-9) * 0.95
mix.astype(np.float32).tofile(f"{D}/mix.f32")
subprocess.check_call(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", f"{D}/mix.f32",
                       "-af", "highpass=f=35,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,loudnorm=I=-14:TP=-1.5:LRA=9",
                       "-ar", str(SR), "-ac", "2", f"{D}/mix.wav"])
os.remove(f"{D}/mix.f32")
print("total", round(TOTAL, 2), [(s["shot"], round(s["vstart"], 1)) for s in shots])
