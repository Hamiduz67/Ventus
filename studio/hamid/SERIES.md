# Hamid: Zero Se Shuru — series rules (approved by the owner)

Full series bible (owner's doc): https://claude.ai/artifact/2rXV1bBpFpxq8akf1dCGGT
The story is inspired by the owner's own journey. Treat it with care: real struggle, real hope, never mocking poverty.

## Story
A Lahore boy, Hamid, scores 82% in 12th but can't go to college (no money). He takes odd jobs (up to 3 a day),
moves to Karachi, faces a new obstacle every day (phone dies, rented bike breaks, no work, no food, rent due...),
and after years of struggle makes it. Tone: mixed — suspense + one funny moment + hope or a cliffhanger.

## Seasons (story days; 2 reels a day = the story moves 2 days per calendar day; day counter may jump)
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
New characters may be added (draw them in hamid_render.py `head()/torso()/arm()`, add a voice in tts.py).

## First 10 days (planned)
1 Result Wala Din (DONE) · 2 Pehli Naukri (tea dhaba, 12 h for Rs 500, burns hand, paid Rs 450 "for the broken cup"; Bilal has a scheme)
· 3 Bilal Ka Scheme (dummy phones, lose Rs 2,000, laugh on a rooftop) · 4 Teen Naukriyan (newspapers, dhaba, night tuition; falls asleep teaching)
· 5 Phone Mar Gaya (phone dies when a delivery job calls; borrows a stranger's phone; job is in Karachi)
· 6 Station Ki Raat (first night in Karachi at the bus station; Rs 120 left) · 7 Kiraye Ki Bike (Chacha Ghafoor's bike, no brakes; first 5-star review)
· 8 Barish (monsoon soaks an order; retired teacher tips him, asks why he isn't studying) · 9 Khana Nahi (no food; shares last biscuits with a street kid; a dhaba owner hires him)
· 10 Ammi Ki Call (Abbu needs Rs 3,000 medicine; double shift; Rs 40 left). After day 10, continue the arc yourself.

## Reel format (65–85 s, 1080x1920) — a complete mini-story, not just a moment
**Pacing (owner, 2026-11-14): pauses were breaking viewer attention. No dead air.** Lines follow each other with ~0.1 s gaps
(0.15 s extra at a scene cut); every wordless beat is ≤ 1.6 s (hamid_audio.py caps it) and must have motion + SFX + on-screen text.
A few seconds shorter is fine — never pad with pauses.
Owner feedback: 40 s reels ended just as they got engaging. Each reel must now tell a whole small story:
1. Hook (0–3 s): the problem first, on screen + in voice.  2. Day card: "DAY n · CITY · JEB MEIN: Rs x".
3. Setup (who/where/what he needs today).  4. Struggle that ESCALATES — at least two obstacles, the second worse than the first.
5. Turn (jugaad / stranger's help / funny accident / a choice he has to make).  6. Payoff (small win or loss, money counter moves).
7. Cliffhanger hook for the next day, then "Day n+1 kal… follow karo".
Keep momentum: something changes every 3–5 s (cut, new scene, money counter, SFX, on-screen text). Use short wordless beats (≤ 1.6 s each)
(action + music + SFX + on-screen text like diary lines, phone messages, price tags) to carry the story without paid voice.
Recurring: day counter + money counter (top corners), Ammi's voice notes, Hamid's diary, his winning line "Aaj bhi bach gaye."

## Language + cost rules (owner's standing instructions)
- Simple everyday Urdu–Hindi–English mix, the way young people talk. No difficult/formal words. Write voice text in Urdu script; captions in Roman (Hinglish/Urdu) script.
- ElevenLabs ONLY for speech. Music + SFX are generated in code (free). Max 600 characters of voice per reel and ≤ 300 new characters per weekly episode (Starter plan: 40,000/month; 60 reels × 600 = 36,000). Make reels longer with visuals, not more voice.
- Hamid's voice is locked: Raghav on eleven_v4 (no [tags] in his text; use "…" for pauses).
- 2D cartoon style (same characters/look as Day 1). Fully original: no real brands/logos, no real people, no copyrighted music.
