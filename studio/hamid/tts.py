"""ElevenLabs voices for Hamid: Zero Se Shuru. Speech only (music/SFX are made for free).
Usage: tts.py <episode dir>   -> writes el##.mp3 + v##.wav for every line in script.json that has no v##.wav yet.
Key: env ELEVENLABS_API_KEY, else ~/.secrets/elevenlabs_key. Never commit the key (the repo is public)."""
import json, os, re, subprocess, sys

D = sys.argv[1]
KEY = os.environ.get("ELEVENLABS_API_KEY") or open(os.path.expanduser("~/.secrets/elevenlabs_key")).read().strip()

# who -> (voice_id, model, stability, keep_tags). Hamid is LOCKED to Raghav on eleven_v4 (approved by the owner).
VOICES = {
    "H": ("4BoDaQ6aygOP6fpsUmJe", "eleven_v4", 0.4, False),  # Hamid - "Raghav", narrator + lead
    "A": ("UT6USLtoAlXHj5k4sOLY", "eleven_v3", 0.5, True),   # Ammi - "Reva", warm Urdu
    "B": ("vH5LP38dcYJ3CIbC2rKX", "eleven_v3", 0.5, True),   # Abbu - "Amjid", deep Urdu
    "L": ("7b9mYhmnp0y2qSH1FnBL", "eleven_v3", 0.5, True),   # Bilal - "Bunty", funny best friend
    "R": ("7eRpHPIAaX3Z8JIv8xfg", "eleven_v3", 0.5, True),   # Seth Rauf - "Yatin", loud boss
    "G": ("qsz5tTEjPvsiIJZIpM8S", "eleven_v3", 0.5, True),   # Chacha Ghafoor - "Kamal", landlord
    "S": ("gHu9GtaHOXcSqFTK06ux", "eleven_v3", 0.5, True),   # Sadia - "Anjali", cheerful (Season 2, Karachi)
}

lines = json.load(open(f"{D}/script.json")); used = 0
for i, l in enumerate(lines):
    if l.get("mode") == "beat" or os.path.exists(f"{D}/v{i:02d}.wav"): continue   # wordless beats: no voice
    vid, model, stab, tags = VOICES[l["who"]]
    txt = l["dev"] if tags else re.sub(r"\[[^\]]*\]\s*", "", l["dev"]).strip()
    body = {"text": txt, "model_id": model, "language_code": "ur", "voice_settings": {"stability": stab}}
    out = f"{D}/el{i:02d}.mp3"
    r = subprocess.run(["curl", "-sS", "-m", "300", "-X", "POST", "-H", "xi-api-key: " + KEY, "-H", "Content-Type: application/json",
                        "-o", out, "-w", "%{http_code}", "-d", json.dumps(body),
                        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128"], capture_output=True, text=True)
    if r.stdout != "200":
        print("ERROR line", i, r.stdout, open(out, "rb").read()[:300]); sys.exit(1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-ar", "24000", "-ac", "1", f"{D}/v{i:02d}.wav"], check=True)
    used += len(txt); print("line", i, l["who"], "ok")
print("characters used:", used)
