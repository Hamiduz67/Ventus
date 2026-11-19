"""ElevenLabs character budget check (shared by all series).
Usage: elevenlabs_budget.py [--warn N]  -> prints used/limit/remaining/reset; with --warn exits 2 when remaining < N.
Key: ~/.secrets/elevenlabs_key (never commit it)."""
import datetime as dt, json, os, subprocess, sys
KEY = os.environ.get("ELEVENLABS_API_KEY") or open(os.path.expanduser("~/.secrets/elevenlabs_key")).read().strip()
r = subprocess.run(["curl", "-sS", "-m", "60", "-H", "xi-api-key: " + KEY, "https://api.elevenlabs.io/v1/user/subscription"], capture_output=True, text=True)
d = json.loads(r.stdout)
used, lim = d["character_count"], d["character_limit"]; rem = lim - used
reset = dt.datetime.fromtimestamp(d.get("next_character_count_reset_unix", 0), dt.timezone.utc)
print(json.dumps({"tier": d.get("tier"), "used": used, "limit": lim, "remaining": rem, "reset_utc": reset.isoformat(), "reset_unix": d.get("next_character_count_reset_unix")}))
if "--warn" in sys.argv and rem < int(sys.argv[sys.argv.index("--warn") + 1]): sys.exit(2)
