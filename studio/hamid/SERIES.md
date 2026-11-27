# Hamid: Zero Se Shuru — series rules (approved by the owner)

Full series bible (owner's doc): https://claude.ai/artifact/2rXV1bBpFpxq8akf1dCGGT
The story is inspired by the owner's own journey. Treat it with care: real struggle, real hope, never mocking poverty.

## Story
A Lahore boy, Hamid, scores 82% in 12th but can't go to college (no money). He takes odd jobs (up to 3 a day),
moves to Karachi, faces a new obstacle every day (phone dies, rented bike breaks, no work, no food, rent due...),
and after years of struggle makes it. Tone: mixed — suspense + one funny moment + hope or a cliffhanger.

## Seasons (story days; 2 reels a day at 18:00 + 20:00 Asia/Dubai = the story moves 2 days per calendar day; day counter may jump)
| Season | Story days | Arc |
| --- | --- | --- |
| 1 Lahore | 1–60 | no money for college, three jobs a day, Bilal's schemes |
| 2 Karachi | 61–180 | deliveries, rent, rain, Seth Rauf's dhaba, **meets Sadia in Karachi** (love interest) |
| 3 Gulf Ka Sapna | 181–300 | visa agent scam, labour camp friends, sending money home |
| 4 Apna Kaam | 301+ | his own small business, Abbu finally says shabash, helps the next Hamid |
Turning points (weekly episodes): bus ticket out of Lahore, visa arrives, first own shop.

## Characters (code letter = voice in tts.py and character in hamid_render.py)
- H **Hamid** (18 at start): sharp, stubborn, funny under pressure; old phone, one good shirt, a notebook of plans. Narrator + lead.
- A **Ammi**: worried but proud; calls at the worst moments; her voice notes can end an episode.
- B **Abbu**: ill / out of work, quiet, rarely says "shabash". Winning his respect is the long arc.
- L **Bilal**: best friend from the mohalla, always has a "scheme" (comic relief, causes half the trouble).
- R **Seth Rauf**: first boss in Karachi; stingy, loud, secretly fair; becomes a mentor.
- G **Chacha Ghafoor**: rents bikes and rooms; always asking for kiraya.
- S **Sadia**: Hamid meets her in **Karachi**; works at a shop he delivers to, ambitious, studies at night. Love interest.
  Look (owner, 2026-11-27: "make Sadia slim and attractive, she should be very pretty" — every reel from now on): an adult (about 19–20),
  slim figure in a fitted sky-blue kurta with a narrow waist, pink dupatta over the head and in a slim fold over her left shoulder (not a sash), slim oval face, soft
  centre-parted hair with a long braid, thin arched brows, long lashes + kohl, rosy cheeks, pink lips, small gold earrings and nose stud, warm brown eyes, gold bangles.
  Already built into hamid_render.py (head/torso/draw_char for "S") — use draw_char("S", …) as is, don't redraw her bulkier.
  Keep it tasteful and in character (modest clothes, pretty-cartoon, never sexualised).
New characters may be added (draw them in hamid_render.py `head()/torso()/arm()`, add a voice in tts.py).

## First 10 days (planned)
1 Result Wala Din (DONE) · 2 Pehli Naukri (tea dhaba, 12 h for Rs 500, burns hand, paid Rs 450 "for the broken cup"; Bilal has a scheme)
· 3 Bilal Ka Scheme (dummy phones, lose Rs 2,000, laugh on a rooftop) · 4 Teen Naukriyan (newspapers, dhaba, night tuition; falls asleep teaching)
· 5 Phone Mar Gaya (phone dies when a delivery job calls; borrows a stranger's phone; job is in Karachi)
· 6 Station Ki Raat (first night in Karachi at the bus station; Rs 120 left) · 7 Kiraye Ki Bike (Chacha Ghafoor's bike, no brakes; first 5-star review)
· 8 Barish (monsoon soaks an order; retired teacher tips him, asks why he isn't studying) · 9 Khana Nahi (no food; shares last biscuits with a street kid; a dhaba owner hires him)
· 10 Ammi Ki Call (Abbu needs Rs 3,000 medicine; double shift; Rs 40 left). After day 10, continue the arc yourself.

## Reel format (45–60 s, 1080x1920, VOICE-LED) — a complete mini-story, told fast
**Owner, 2026-11-18 (latest, overrides the older pacing notes): "reels are getting slow and sloppy as some things are left without a voice —
make the reel shorter but entertaining, don't keep a lot of gaps."** So, from Day 13 on:
- **45–60 s total.** Cut a scene rather than stretch one. ~14–20 short spoken lines (each 3–8 words), one after another.
- **Something is always being said.** Every story beat is carried by a voice line (Hamid's narration or a character talking).
  Put the action, SFX, on-screen text, phone messages and price tags ON TOP of voice lines, not in silent gaps.
- **Wordless beats: at most 4 per reel, never two in a row,** only for a quick punch (a crash, a stamp, a reveal). hamid_audio.py caps them
  at 0.6 s, scene cuts get 0.04 s, voices run 1.12x — and it STOPS the run (exit 3) if a Day 13+ script has >4 beats, two beats in a row,
  or a length outside 45–62 s. Fix the script, don't work around the check.
- Fewer scenes (5–7), each with a clear reason; something changes every 2–3 s. Cut setup talk; open in the middle of the problem.
- Funny line or visual gag at least once; the cliffhanger lands in the last ~6 s before the outro.
Earlier owner feedback (still applies, just told faster): reels must not end just as they get engaging — each reel tells a whole small story:
1. Hook (0–3 s): the problem first, on screen + in voice.  2. Day card: "DAY n · CITY · JEB MEIN: Rs x".
3. Setup (who/where/what he needs today).  4. Struggle that ESCALATES — at least two obstacles, the second worse than the first.
5. Turn (jugaad / stranger's help / funny accident / a choice he has to make).  6. Payoff (small win or loss, money counter moves).
7. Cliffhanger hook for the next day, then the **outro hook (owner, 2026-11-15 — every reel, always)**: the script's LAST line is a Hamid vo line
   with `"outro": true`: "آگے حامد کیا کرے گا؟ فالو کریں، اگلے پارٹ کے لیے!" / "Agay Hamid kya karega? Follow karein, agle part ke liye!".
   The renderer darkens the cliffhanger frame and shows "AGAY HAMID KYA KAREGA?" + "FOLLOW KAREIN • DAY n+1 NEXT PART" (outro() in hamid_render.py).
   Don't also show the old "DAY n+1 KAL • FOLLOW" pill in the same scene.
**Cold-open hook (owner, 2026-11-19 — "add an eye / ear catching hook in the start so people won't skip"; Day 15+):**
Instagram showed 50% of viewers swiping away in the first 3 s on Day 13, which opened on good news. So every reel now:
- opens on the PROBLEM / danger / shock in the very first words of line 1 (never good news, never a recap first) — the conflict word lands in the first ~1 s;
- sets meta.json `"hook": {"text": "<2-4 BIG Roman words: the problem, e.g. DUMMY PHONE?!>", "emoji": "<object at stake>", "sub": "<optional small red line, e.g. 1 MINUTE BAAKI>"}`.
  The renderer plays a 1.5 s cold open over line 1 (white flash, screen shake, rotating red/yellow burst, slammed-in headline) and hamid_audio.py
  starts with a boom + crack + brass-stab sting at 0 s with no music fade-in. hamid_audio.py exits 3 if a Day 15+ meta.json has no "hook".
Keep momentum: something changes every 2–3 s (cut, new scene, money counter, SFX, on-screen text) — always under a voice line.
**Thumbnail on every reel (owner, 2026-11-18):** an eye-catching suspense cover — the episode's key moment blurred behind, red vignette,
Hamid's big shocked face, the object at stake ringed in red with a "?", a red tag (amount/score) and a 2-line Roman headline that asks the
episode's question without spoiling it (e.g. "FORM YA / ABBU KI DAWAI?"). Set in meta.json "thumb" (see RUNBOOK A.2); it is also the video's first 2 frames.
Recurring: day counter + money counter (top corners), Ammi's voice notes, Hamid's diary, his winning line "Aaj bhi bach gaye."

## Language + cost rules (owner's standing instructions)
- Simple everyday Urdu–Hindi–English mix, the way young people talk. No difficult/formal words. Write voice text in Urdu script; captions in Roman (Hinglish/Urdu) script.
- ElevenLabs ONLY for speech. Music + SFX are generated in code (free). Max 600 characters of voice per reel and ≤ 300 new characters per weekly episode (Starter plan: 40,000/month; 60 reels × 600 = 36,000). A 45–60 s voice-led reel needs ~450–600 characters (≈12 chars per second of speech); stay ≤ 600 by keeping lines short, not by adding silent beats. The outro line is free (reused recording).
- Hamid's voice is locked: Raghav on eleven_v4 (no [tags] in his text; use "…" for pauses).
- 2D cartoon style (same characters/look as Day 1). Fully original: no real brands/logos, no real people, no copyrighted music.
