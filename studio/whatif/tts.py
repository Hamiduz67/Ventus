"""ElevenLabs voices for "Kya Hoga Agar?" (daily What If reel, Instagram). Speech only.
Usage: tts.py <episode dir> -> v##.wav for every non-beat line without one. Never commit the key (public repo)."""
import json, os, re, subprocess, sys
D = sys.argv[1]
KEY = os.environ.get("ELEVENLABS_API_KEY") or open(os.path.expanduser("~/.secrets/elevenlabs_key")).read().strip()
# who -> (voice_id, model, stability, keep_tags)
VOICES = {
    "N": ("GnmcdQ5D9NktfEwK2h3j", "eleven_v3", 0.5, True),    # Narrator "Kamran M" - dramatic Urdu (series voice, keep fixed)
    "H": ("4BoDaQ6aygOP6fpsUmJe", "eleven_v4", 0.4, False),   # Hamid (crossover host) - "Raghav", LOCKED, no [tags]
    "L": ("7b9mYhmnp0y2qSH1FnBL", "eleven_v3", 0.5, True),    # Bilal - "Bunty"
    "F": ("gHu9GtaHOXcSqFTK06ux", "eleven_v3", 0.5, True),    # young woman - "Anjali"
    "O": ("qsz5tTEjPvsiIJZIpM8S", "eleven_v3", 0.5, True),    # older man / chacha - "Kamal"
    "W": ("UT6USLtoAlXHj5k4sOLY", "eleven_v3", 0.5, True),    # older woman - "Reva"
}
lines = json.load(open(f"{D}/script.json")); used = 0
for i, l in enumerate(lines):
    if l.get("mode") == "beat" or os.path.exists(f"{D}/v{i:02d}.wav"): continue
    vid, model, stab, tags = VOICES[l.get("voice", l["who"])]
    txt = l["dev"] if tags else re.sub(r"\[[^\]]*\]\s*", "", l["dev"]).strip()
    body = {"text": txt, "model_id": model, "language_code": "ur", "voice_settings": {"stability": stab}}
    out = f"{D}/el{i:02d}.mp3"
    r = subprocess.run(["curl", "-sS", "-m", "300", "-X", "POST", "-H", "xi-api-key: " + KEY, "-H", "Content-Type: application/json",
                        "-o", out, "-w", "%{http_code}", "-d", json.dumps(body),
                        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128"], capture_output=True, text=True)
    if r.stdout != "200": print("ERROR line", i, r.stdout, open(out, "rb").read()[:300]); sys.exit(1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-ar", "24000", "-ac", "1", f"{D}/v{i:02d}.wav"], check=True)
    used += len(txt); print("line", i, l["who"], "ok")
print("characters used:", used)
