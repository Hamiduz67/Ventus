# "Aap Kya Karte?" — daily Urdu thriller reel (YouTube Shorts only)
Owner, 2026-11-19: "one more reel on YouTube only, a thriller story, and in the end ask what will you do if you were in that situation —
every day a new story, a new question to keep people hooked. Same Urdu language."

## Every reel
- **One complete, NEW stand-alone thriller story per day** (no continuing characters needed). Never repeat a premise already in state.json "episodes".
- **45–60 s, 1080x1920, voice-led**: a dramatic Urdu narrator (N) tells it in second person ("aap…") or third person, with 1–3 short lines from the people
  in the story. Something is always being said; at most 3 wordless beats of ≤ 0.7 s (never two in a row) for a knock, a crash, a reveal.
- **Cold-open hook (first 1.5 s)**: line 1 starts on the danger / the strange thing (never a slow intro). meta.json `"hook": {"text": "<2-4 BIG Roman words>",
  "emoji": "<object>", "sub": "<small red line, e.g. RAAT 2 BAJE>"}` → flash, shake, red burst headline + boom/stab sting.
- **Shape**: hook → situation (who/where, 1–2 lines) → escalation (2+ new pieces of information that make it worse — a radio warning, a message,
  a sound, a second figure) → a doubt/twist that makes BOTH choices reasonable → split screen of the dilemma → the question.
- **Ending (always)**: the last line (`"final": true`) asks the viewer: "Aap hote toh kya karte? A: … B: … Comment mein likho… kal nayi kahani, naya sawaal!"
  on a shot with `"choice": {"a": "...", "b": "..."}` (two short Roman options, ≤ 28 characters each). Both options must be defensible — a real dilemma,
  not a trick question. Do NOT reveal what happened.
- **Language**: simple everyday Urdu–Hindi–English mix, Urdu script in `dev`, Roman captions in `rom` (same words). No difficult words.
- **Content limits**: suspense, not gore. No blood, no weapons used on people, no self-harm, no sexual content, nothing involving harm to children
  beyond "a child needs help". No real people, places' real businesses, brands or logos; no real crimes or news. Original music/SFX only (made in code).
- **Look**: flat 2D noir — night palettes, silhouettes with a cold rim light, red accents, rain/fog/flicker, slow push-ins, film grain.
  Same template every day (HUD "KAHANI #n" + "AAP KYA KARTE?") so the series is recognisable.

## Voices (studio/thriller/tts.py; ElevenLabs eleven_v3, [tags] allowed: [whispers] [scared] [serious] [crying] [desperate])
N narrator "Kamran M" (fixed series voice) · P young man "Viraj" · X stranger/villain/radio/police "Rudra" · F young woman "Anjali" ·
W older woman "Reva" · O older man "Kamal". Mark radio/phone voices with `"radio": true` (band-pass filter).
ElevenLabs budget: owner said "use it all you want, but don't overuse it for no reason" — keep a reel ≤ ~600 characters, never regenerate lines
that are fine. Check `python3 studio/elevenlabs_budget.py` every run (see RUNBOOK).

## Story ideas (pick fresh ones; add your own; mark used ones in state.json)
highway woman asking for a lift (USED #1) · 3 AM call from your own number · lift stops between floors with a stranger · parcel left at your door with your name
but you ordered nothing · babysitting and the baby monitor shows someone else · ATM at night, card stuck, a "helpful" stranger · found a wallet with
Rs 5 lakh and a threatening note · night bus, the driver takes a wrong road · friend's message "don't open the door, it's not me" · hospital night shift,
patient asks for a dead relative · old-house rent too cheap · knock at 2 AM, voice of your mother who is in another city · stranded in the desert, a car with
no lights following · your CCTV shows you sleeping while you're at work · neighbour's house lights blinking in a pattern · a job offer abroad, passport
"kept for safety" · exam paper leaked to you the night before · a child alone at the train station holding your photo.
