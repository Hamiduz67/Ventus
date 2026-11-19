"""ElevenLabs voices for "Aap Kya Karte?" (daily thriller, YouTube Shorts only). Speech only.
Usage: tts.py <episode dir> -> v##.wav for every non-beat line without one. Never commit the key (public repo)."""
import json, os, subprocess, sys
D = sys.argv[1]
KEY = os.environ.get("ELEVENLABS_API_KEY") or open(os.path.expanduser("~/.secrets/elevenlabs_key")).read().strip()
# who -> (voice_id, model, stability). eleven_v3 keeps [tags] like [whispers] [scared] [serious].
VOICES = {
    "N": ("GnmcdQ5D9NktfEwK2h3j", "eleven_v3", 0.5),   # Narrator - "Kamran M", dramatic & suspenseful Urdu (series voice, keep fixed)
    "P": ("FmBhnvP58BK0vz65OOj7", "eleven_v3", 0.5),   # young man (the person in the story) - "Viraj"
    "X": ("ypnkIsDASPgHZuanrF0q", "eleven_v3", 0.5),   # stranger / villain / radio / police - "Rudra", deep
    "F": ("gHu9GtaHOXcSqFTK06ux", "eleven_v3", 0.5),   # young woman - "Anjali"
    "W": ("UT6USLtoAlXHj5k4sOLY", "eleven_v3", 0.5),   # older woman - "Reva"
    "O": ("qsz5tTEjPvsiIJZIpM8S", "eleven_v3", 0.5),   # older man - "Kamal"
}
lines = json.load(open(f"{D}/script.json"))["lines"]; used = 0
for i, l in enumerate(lines):
    if l.get("mode") == "beat" or os.path.exists(f"{D}/v{i:02d}.wav"): continue
    vid, model, stab = VOICES[l["who"]]
    body = {"text": l["dev"], "model_id": model, "language_code": "ur", "voice_settings": {"stability": stab}}
    out = f"{D}/el{i:02d}.mp3"
    r = subprocess.run(["curl", "-sS", "-m", "300", "-X", "POST", "-H", "xi-api-key: " + KEY, "-H", "Content-Type: application/json",
                        "-o", out, "-w", "%{http_code}", "-d", json.dumps(body),
                        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128"], capture_output=True, text=True)
    if r.stdout != "200": print("ERROR line", i, r.stdout, open(out, "rb").read()[:300]); sys.exit(1)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", out, "-ar", "24000", "-ac", "1", f"{D}/v{i:02d}.wav"], check=True)
    used += len(l["dev"]); print("line", i, l["who"], "ok")
print("characters used:", used)
