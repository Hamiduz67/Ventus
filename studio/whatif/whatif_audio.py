"""Kya Hoga Agar? (What If reels): timeline + lip-sync + free music/SFX mix.
Reuses the Hamid audio engine (studio/hamid/hamid_audio.py: pacing, voice-led rule checks, music, cold-open sting)
and adds per-line SFX from script.json: "sfx": ["kick", "whoosh@1.2", ...]  (name[@seconds after the line starts]).
Names: kick whoosh chime tick beep ring honk hum dings bark cash boom.
meta.json must have "day": 99 (turns on the voice-led checks + cold-open hook in the shared engine) and "hook".
Usage: whatif_audio.py <episode dir>   (exit 3 = reel rules broken: rewrite the script)."""
import os, sys
HA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hamid", "hamid_audio.py")
src = open(HA).read()
MARK = "# ---- Cold-open hook sting"
assert MARK in src, "hamid_audio.py changed: marker not found"
a, b = src.split(MARK, 1)
EXTRA = '''
# ---- What If per-line SFX
def _wi_sfx(name, at):
    if name == "kick": add(sfx, kick(), at, 0.9)
    elif name == "boom": add(sfx, kick(), at, 1.0); add(sfx, hum(0.8, 45), at, 0.6)
    elif name == "whoosh": add(sfx, WHOOSH, at, 0.6)
    elif name == "chime": add(sfx, CHIME, at, 0.6)
    elif name == "tick":
        for k in range(5): add(sfx, TICK, at + k * 0.25, 0.4)
    elif name == "beep":
        for k in range(3): add(sfx, beep(1200, 0.08, 0.5), at + k * 0.18)
    elif name == "ring": add(sfx, ring(0.8), at, 0.5)
    elif name == "honk": add(sfx, honk(0.3), at, 0.7)
    elif name == "hum": add(sfx, hum(1.4, 50), at, 0.5)
    elif name == "bark": add(sfx, bark(), at, 0.6)
    elif name == "cash": add(sfx, beep(2200, 0.06, 0.5), at); add(sfx, CHIME, at + 0.06, 0.7)
    elif name == "dings":
        for k in range(8): add(sfx, beep(1500 + 150 * (k % 3), 0.07, 0.45), at + k * 0.08)
for _l in tl:
    for _s in _l.get("sfx", []):
        _n, _, _d = _s.partition("@"); _wi_sfx(_n, _l["start"] + (float(_d) if _d else 0.0))
'''
# ---- What If pacing (owner, 2026-11-21: "too fast - make it slow with pauses so it gets interesting"):
# natural speed (no speed-up), breathing room between lines and scenes, longer dramatic beats, and a per-line
# "pause": <seconds> (extra silence after that line, for suspense). 50-80 s allowed (Instagram Reels).
PACE = [("VOICE_TEMPO = 1.12", "VOICE_TEMPO = 1.0"), ("GAP = 0.06 ", "GAP = 0.3 "),
        ("BEAT_MAX = 0.6; SCENE_GAP = 0.04", "BEAT_MAX = 1.3; SCENE_GAP = 0.45"),
        ("t += d + GAP; prev_scene", "t += d + GAP + float(l.get('pause', 0)); prev_scene"),
        ("if len(_beats) > 4:", "if len(_beats) > 6:"), ("(max 4)", "(max 6)"),
        ("if not 45 <= TOTAL <= 62:", "if not 45 <= TOTAL <= 80:"), ("(want 45-60 s)", "(want 50-80 s)")]
for _o, _n in PACE:
    assert _o in a, "hamid_audio.py changed: " + _o
    a = a.replace(_o, _n)
sys.argv = [HA, sys.argv[1]]
exec(compile(a + EXTRA + MARK + b, HA, "exec"), {"__name__": "__main__", "__file__": os.path.abspath(HA)})
