# "Kya Hoga Agar?" — daily What If reel (Instagram Reels only, 22:00 Asia/Dubai)
Owner, 2026-11-21: "a what if reel for my insta page, every day a new story; analyse social media for the last 30 days and post
whatever is going viral related to what if. Make your own story, interesting and eye-catching, with a 2-second hook at the start.
Every day 10 pm." Language: simple Urdu–Hindi–English mix (like Hamid). Voice: full ElevenLabs voice (owner will upgrade the plan when it runs out).

## Every reel
- **One NEW stand-alone "Kya hoga agar…?" story per day**, told as a mini-story with a timeline (e.g. 1 SECOND → 1 GHANTA → 6 GHANTE → 24 GHANTE BAAD)
  that escalates and ends on a twist or a feel-good/funny payoff, then asks the viewer the question. Hamid (from "Hamid: Zero Se Shuru")
  is the recurring host/character who lives through the scenario (crossover keeps the page consistent); narrator N tells it.
- **Topic choice = trend research** (each run): look at the last 30 days — the page's own Instagram reels in Metricool (brand 7980574:
  views, reach, skip rate, shares, saves) and web/news searches for "what if" topics, viral hypotheticals, rumours and news people are
  talking about (e.g. "Earth loses gravity for 7 seconds", internet outages, heatwaves, AI, cricket, prices). Pick the hottest topic that
  suits a simple, relatable story for a Pakistani/Indian audience. Make it ORIGINAL — never copy or repost anyone's video, no real people,
  brands or logos. If the topic is a rumour or hoax, say it clearly in one line ("asal mein yeh afwah hai…"). Facts must be true or clearly
  hypothetical ("shayad", "ho sakta hai"); check facts with a web search. Never repeat a topic in state.json "episodes".
- **45–60 s, 1080x1920, voice-led** (same rules as the Hamid engine: something is always being said; at most 4 wordless beats ≤ 0.6 s,
  never two in a row; whatif_audio.py exits 3 otherwise — rewrite the script).
- **2-second cold-open hook**: line 1 starts on the shock itself (never a slow intro). meta.json `"hook": {"text": "<2-4 BIG Roman words>",
  "emoji", "sub"}` → flash, shake, burst headline + boom sting. Then a title line "Kya hoga agar…?". Check stills at 0.1, 0.4, 1.2 s.
- **Ending (always)**: last line has `"final": true` and asks the viewer: "Aap … kya karoge? Comment karo, aur follow karo!" (meta.json "question"
  is shown on the ending card). A funny line or visual gag at least once.
- ≤ ~600 ElevenLabs characters per reel (voices in studio/whatif/tts.py: N narrator "Kamran M", H Hamid "Raghav" eleven_v4 LOCKED no [tags],
  L Bilal, F young woman, O older man, W older woman).

## Files
studio/whatif/tts.py · whatif_audio.py (reuses studio/hamid/hamid_audio.py + per-line "sfx") · whatif_render.py (reuses the Hamid 2D engine
read-only; HUD "KYA HOGA AGAR? #n" + timeline stamp, ending card, thumbnail; add each episode's scenes there and register them in WI_SC).
Episodes: whatif/epNNN/ (script.json, meta.json {"n", "day": 99, "title", "question", "hook", "thumb"}, KyaHogaAgar_NNN.mp4, thumb.jpg).
State: studio/whatif/state.json. Never change studio/hamid/*.py for this series (two daily Hamid runs depend on it).
