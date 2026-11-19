# Runbook — scheduled runs for "Hamid: Zero Se Shuru"

Read SERIES.md first. All paths below are relative to the Ventus repo root. The repo is PUBLIC: never commit the ElevenLabs key.

## 0. Setup (every run)
- Repo: if `/home/claude/ventus` is missing, attach Hamiduz67/Ventus with push access (add_repo) and clone it there.
  Always `git fetch origin +main:refs/remotes/origin/main && git rebase origin/main` before committing; push to main.
- Save the ElevenLabs key from the task prompt to `~/.secrets/elevenlabs_key` (chmod 600).
- Python needs numpy + pillow + ffmpeg (usually present). The Noto Color Emoji font must exist at /usr/share/fonts/truetype/noto/NotoColorEmoji.ttf.
- If downloads fail with TLS errors, use the proxy CA bundle (~/.ccr/ca-bundle.crt).

## A. Daily reel run (2 per day: posts at 18:00 and 20:00 Asia/Dubai)
> **Owner, 2026-11-19:** the 13:00 slot is gone (13:00 reels got ~80% fewer views than 20:00 ones on Instagram since Day 6). The early slot now posts at
> **18:00** Asia/Dubai (19:00 Pakistan). If an older task prompt still says 13:00, use 18:00. Every reel from Day 15 also needs the cold-open hook
> (SERIES.md "Cold-open hook": problem in the first words + meta.json "hook").
> **Owner, 2026-11-18 (live, newest instruction):** reels are now 45–60 s and voice-led with no silent gaps. If the scheduled task's prompt
> still says "75–90 seconds" or "make the reel longer with wordless visual beats", that text predates this change: follow the 45–60 s
> voice-led format here and in SERIES.md, and keep everything else in the prompt (slot, platforms, secrets, ≤ 600 characters, report).
1. Read `studio/hamid/state.json`. Next day = last_day + 1. Check `python3 studio/hamid/buffer_post.py status` so you never double-post a day.
2. Write `hamid/epNNN/script.json` (NNN = day, 3 digits) + `meta.json` ({"day", "city", "money"}).
   - Follow the format and language rules in SERIES.md and the planned day list; continue from `story_so_far`.
   - Line fields: who (H/A/B/L/R/G/S…), mode ("vo" narration or "talk" on-screen dialogue), scene (a key in hamid_render.py `SC`), dev (Urdu script), rom (Roman caption, same words).
   - **Reel length 45–60 s, VOICE-LED (owner, 2026-11-18: "shorter but entertaining, no gaps, nothing left without a voice").** See SERIES.md "Reel format":
     ~14–20 short spoken lines back to back; at most 4 wordless "beat" lines (never two in a row, auto-capped at 0.6 s) for quick punches only;
     put action/SFX/on-screen text on top of voice lines. hamid_audio.py exits with code 3 if these rules are broken — rewrite the script.
     Keep total `dev` text ≤ 600 characters by keeping lines short. Hamid lines: no [tags].
   - ALWAYS end with the outro hook line (owner's standing rule): last line = {"who": "H", "mode": "vo", "scene": <last scene>, "outro": true, "dev": "آگے حامد کیا کرے گا؟ فالو کریں، اگلے پارٹ کے لیے!", "rom": "Agay Hamid kya karega? Follow karein, agle part ke liye!"}. Check a still during it. tts.py reuses studio/hamid/voice/outro_hamid.wav for it (0 new characters).
   - THUMBNAIL (owner, 2026-11-18 — every reel): add to meta.json `"thumb": {"t": <seconds of the most suspenseful scene, from timeline.json>,
     "l1": "<2-3 word white line>", "l2": "<2-3 word big yellow question/shock line>", "emoji": "<the object at stake: 💊 📝 💸 🏍️ …>",
     "tag": "<short red label, e.g. Rs 1,000 / 90%?>", "mood": "shock"|"sad"|"det"}`.
   - COLD-OPEN HOOK (owner, 2026-11-19 — Day 15+): line 1 opens on the problem/shock (conflict word in the first ~1 s), and meta.json has
     `"hook": {"text": "<2-4 BIG Roman words>", "emoji": "<object at stake>", "sub": "<optional small red line>"}`. Check stills at 0.1, 0.4 and 1.2 s. It must tease the episode's central question
     without giving away the ending (curiosity gap), in simple Roman Urdu, max ~4 words per line.
3. Voices: `python3 studio/hamid/tts.py hamid/epNNN`. Optional check: transcribe with faster-whisper small (language "ur") and redo garbled lines (delete that v##.wav and rerun).
4. Scenes: reuse existing scene functions in `studio/hamid/hamid_render.py`; add new ones (dhaba, street, bus station, Karachi room, rain, etc.) in the same flat 2D style, and new characters/props as needed. Commit renderer changes so later runs reuse them. Keep Hamid/Ammi/Abbu exactly as drawn.
5. Audio + render:
   `python3 studio/hamid/hamid_audio.py hamid/epNNN` then `python3 studio/hamid/hamid_render.py hamid/epNNN still:<4–8 times>` and LOOK at the frames (contact sheet). Fix overlaps/cut-off text. Then full render and mux:
   `python3 studio/hamid/hamid_render.py hamid/epNNN thumb` writes thumb.png/thumb.jpg — LOOK at it (readable at phone-grid size, key elements
   between y 285 and 1635 so 4:5 / 3:4 grid crops keep them, nothing overlapping the face or headline).
   The full render puts 2 frames of the thumbnail at the very start (the cover frame), so the mux delays the audio by 67 ms:
   `python3 studio/hamid/hamid_render.py hamid/epNNN && ffmpeg -i video.tmp.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af adelay=67:all=1 -c:a aac -b:a 192k -shortest -movflags +faststart Hamid_DayNN.mp4`
6. Publish (Buffer free plan — Metricool's free plan is used up; do NOT post through Metricool):
   commit only the final mp4 + thumb.jpg + script.json + meta.json (not wav/mp3/f32/stills/thumb.png) to `hamid/epNNN/`, push, then use the COMMIT-SHA raw URLs
   (https://raw.githubusercontent.com/Hamiduz67/Ventus/<sha>/hamid/epNNN/Hamid_DayNN.mp4 and …/thumb.jpg) and confirm HTTP 200 for both.
   Save the Buffer key from the task prompt to `~/.secrets/buffer_key` (chmod 600), then:
   `python3 studio/hamid/buffer_post.py schedule --url <raw url> --caption "<caption>" --title "Day N: <hook> | Hamid: Zero Se Shuru #shorts" --tiktok-title "Hamid: Zero Se Shuru — Day N" --at "YYYY-MM-DD HH:MM" --thumb-url <raw thumb.jpg url>`
   (thumbnailOffset 20 ms = the thumbnail frames → Instagram Reel cover + TikTok cover. Buffer REJECTS thumbnailUrl (2026-11-18): --thumb-url is optional; the retry drops it but keeps thumbnailOffset.
   YouTube Shorts: Buffer/YouTube give no custom-thumbnail control for Shorts; YouTube picks the frame itself.)
   (time is Asia/Dubai: today 18:00 or 20:00 = the run's slot). This posts to YouTube Shorts + TikTok + Instagram Reel.
   Facebook gets the Reel automatically through Instagram's "share Reels to Facebook" setting — nothing to do.
   Caption: hook line + "Day N+1 kal… follow karo" + #HamidZeroSeShuru #struggle #pakistan #motivation #story #urdu.
   Before scheduling, run `buffer_post.py status` and make sure this day isn't already queued/sent (never double-post).
   After the post time has passed (if the run is still going) or at the start of the NEXT run, check `buffer_post.py status`
   for the previous episode; if a channel shows an error, report it (and for TikTok only, a Metricool post is an emergency fallback).
7. Update state.json (last_day, money, city, story_so_far in 2–4 sentences, append episode) and push.
8. If anything fails and the reel can't meet the bar, do NOT post; report what failed.

## B. Weekly long episode (Wednesday + Sunday, posts 19:00 Asia/Dubai)
Content: built from the daily reels posted since the last weekly episode (state.json "episodes" after the last "weekly" entry; if fewer than 3, skip and report).
New opening narration by Hamid (H), the reels' scenes in order (re-rendered from their script.json/timeline, without per-reel hooks and "follow" endings),
short bridging narration between days, and a closing cliffhanger. New ElevenLabs text <= 300 characters (reuse existing v##.wav lines; never re-generate them).
Title "Hafta N: <title> | Hamid: Zero Se Shuru". Save under `hamid/weekly/wNN/`.

Pick the format from the Metricool free-post budget in state.json "metricool" {month, used, limit}:
- If "month" is not the current month (Asia/Dubai), reset: month = current, used = 0 (Metricool's free plan resets monthly).
- **LONG mode** (used < limit): a full YouTube VIDEO, landscape 1920x1080, 30 fps, 5:00-7:00 long. Post ONLY to YouTube through Metricool
  (createScheduledPost, blogId 7980574, Asia/Dubai, YouTube as a normal video, not a Short: check the tool's schema for the YouTube type/title/privacy
  fields; privacy public, not made for kids; a good description with the story so far + #hamidzerosesshuru). Use a commit-SHA raw GitHub URL (HTTP 200).
  Then used += 1 and save. If Metricool answers with a plan/limit error, set used = limit and fall back to SHORT mode in the same run.
  Landscape look: same 2D style. Preferred: add a landscape mode to the renderer in a SEPARATE file (studio/hamid/hamid_render_wide.py) so the daily
  vertical renderer is never broken; draw scenes on a 1920x1080 canvas with the same characters, HUD (day, money, city) and Roman captions at the bottom.
  Acceptable fallback if that can't reach the bar: a designed 16:9 layout with the vertical episode at 1080 high on the left/centre and a styled side panel
  (series title, "Din N", money counter, city, a one-line diary note) - never plain black bars or a blurred copy. Add a 5 s title card at the start and an
  end card ("Agla hafta..."). Make a 1280x720 thumbnail (Hamid's face + 3-4 big Roman words) and commit it next to the video; attach it if Metricool's tool allows.
- **SHORT mode** (used >= limit): vertical 1080x1920, <= 3:00, posted with `buffer_post.py schedule` (YouTube Shorts + TikTok + Instagram Reel).
- Append to state.json "weekly": {n, title, days, mode, file, posted_at, platform ids, elevenlabs_chars}.

## Report (every run)
SendUserMessage to the owner: what was posted (title, time, platforms) or what failed, characters of ElevenLabs used, next planned day.

## C. Daily thriller reel "Aap Kya Karte?" (YouTube Shorts only, posts 22:00 Asia/Dubai)
Series rules: studio/thriller/SERIES.md. State: studio/thriller/state.json (last_n, episodes with premise + question). Episodes: thriller/epNNN/.
1. `python3 studio/elevenlabs_budget.py` — if remaining < 4,000 characters (about one more day of all three reels + a weekly) and
   state "el_warned_for_reset" != that reset_unix, send a PushNotification reminding the owner to upgrade ElevenLabs before it runs out
   (remaining, reset date), then set el_warned_for_reset = reset_unix. If remaining < 700, do not generate; report instead.
2. `buffer_post.py status` — never post the same n twice.
3. Write thriller/epNNN/script.json ({"shots": {...}, "lines": [...]}) + meta.json ({"n", "title", "hook", "thumb": {"l1", "l2", "emoji"}}); follow ep001 as the template.
   Shot spec: bg (thriller_render.py BG), chars [{k: woman|man|hood|old|guard, x, y (feet), s, wave, eyes, window}], props
   [{k: car_broken|radio|trees|phone|emoji, ...}], fx [rain, rain_glass, headlights, fog, flicker, red, heartbeat], pill, big, clock,
   left/right (split dilemma), choice {a, b}. Line fields: who, shot, dev, rom, optional pop, sfx [heartbeat, sting, knock, brake, baby,
   thunder, phone, whoosh, tick], radio, shake, fade_chars, mode "beat" + dur, final. Add new backgrounds/props in the same style when a story needs them.
4. `python3 studio/thriller/tts.py thriller/epNNN` (optionally transcribe with faster-whisper small, language ur), then
   `python3 studio/thriller/thriller_audio.py thriller/epNNN` (exit 3 = rules broken: rewrite the script).
5. `thriller_render.py thriller/epNNN still:<0.1,0.4,1.2 + one per shot>` and `... thumb` → LOOK at them (figures visible, nothing cut off, text readable),
   then full render + mux (same 67 ms adelay as the Hamid reels) to thriller/epNNN/AapKyaKarte_NNN.mp4.
6. Commit only the mp4 + thumb.jpg + script.json + meta.json, push, check the commit-SHA raw URL is HTTP 200, then
   `buffer_post.py schedule --channels youtube --url <raw mp4> --caption "<hook line> Aap hote toh kya karte? A ya B — comment karo! 👇 #AapKyaKarte #thriller #urdu #suspense #story #shorts"
   --title "<hook, ≤ 70 chars> | Aap Kya Karte? #shorts" --at "<today> 22:00"`.
7. Update studio/thriller/state.json (last_n, episodes += {n, title, premise, question a/b, file, posted_at, buffer_id, elevenlabs_chars, length_s}) and push.
