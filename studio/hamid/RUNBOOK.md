# Runbook — scheduled runs for "Hamid: Zero Se Shuru"

Read SERIES.md first. All paths below are relative to the Ventus repo root. The repo is PUBLIC: never commit the ElevenLabs key.

## 0. Setup (every run)
- Repo: if `/home/claude/ventus` is missing, attach Hamiduz67/Ventus with push access (add_repo) and clone it there.
  Always `git fetch origin +main:refs/remotes/origin/main && git rebase origin/main` before committing; push to main.
- Save the ElevenLabs key from the task prompt to `~/.secrets/elevenlabs_key` (chmod 600).
- Python needs numpy + pillow + ffmpeg (usually present). The Noto Color Emoji font must exist at /usr/share/fonts/truetype/noto/NotoColorEmoji.ttf.
- If downloads fail with TLS errors, use the proxy CA bundle (~/.ccr/ca-bundle.crt).

## A. Daily reel run (2 per day: posts at 13:00 and 20:00 Asia/Dubai)
1. Read `studio/hamid/state.json`. Next day = last_day + 1. Check Metricool (brand 7980574) getScheduledPosts for today/tomorrow so you never double-post a day.
2. Write `hamid/epNNN/script.json` (NNN = day, 3 digits) + `meta.json` ({"day", "city", "money"}).
   - Follow the format and language rules in SERIES.md and the planned day list; continue from `story_so_far`.
   - Line fields: who (H/A/B/L/R/G/S…), mode ("vo" narration or "talk" on-screen dialogue), scene (a key in hamid_render.py `SC`), dev (Urdu script), rom (Roman caption, same words).
   - Keep total `dev` text ≤ 500 characters. Hamid lines: no [tags].
3. Voices: `python3 studio/hamid/tts.py hamid/epNNN`. Optional check: transcribe with faster-whisper small (language "ur") and redo garbled lines (delete that v##.wav and rerun).
4. Scenes: reuse existing scene functions in `studio/hamid/hamid_render.py`; add new ones (dhaba, street, bus station, Karachi room, rain, etc.) in the same flat 2D style, and new characters/props as needed. Commit renderer changes so later runs reuse them. Keep Hamid/Ammi/Abbu exactly as drawn.
5. Audio + render:
   `python3 studio/hamid/hamid_audio.py hamid/epNNN` then `python3 studio/hamid/hamid_render.py hamid/epNNN still:<4–8 times>` and LOOK at the frames (contact sheet). Fix overlaps/cut-off text. Then full render and mux:
   `python3 studio/hamid/hamid_render.py hamid/epNNN && ffmpeg -i video.tmp.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart Hamid_DayNN.mp4`
6. Publish: commit only the final mp4 + script.json + meta.json (not wav/mp3/f32/stills) to `hamid/epNNN/`, push, then use the COMMIT-SHA raw URL
   (https://raw.githubusercontent.com/Hamiduz67/Ventus/<sha>/hamid/epNNN/Hamid_DayNN.mp4) and confirm HTTP 200.
   Metricool createScheduledPost, brand 7980574, autoPublish true, providers youtube + tiktok + instagram + facebook:
   youtubeData {type "short", privacy "public", category "FILM_ANIMATION", madeForKids false, title "Day N: <hook> | Hamid: Zero Se Shuru #shorts"},
   tiktokData {privacyOption "PUBLIC_TO_EVERYONE", isAigc true}, instagramData {type "REEL", showReelOnFeed true, isAiGenerated true},
   facebookData {type "REEL", title}. Caption: hook line + "Day N+1 kal… follow karo" + #HamidZeroSeShuru #struggle #pakistan #motivation #story #urdu.
   Post time = the run's slot (13:00 or 20:00 Asia/Dubai, today).
7. Update state.json (last_day, money, city, story_so_far in 2–4 sentences, append episode) and push.
8. If anything fails and the reel can't meet the bar, do NOT post; report what failed.

## B. Weekly long episode (Wednesday + Sunday, posts 19:00 Asia/Dubai)
- Build a ~3 minute episode from the reels posted since the last weekly episode: a new opening narration by Hamid (H), the reels' scenes in order
  (re-render from their script.json/timeline without per-reel hooks/"follow" endings, or cut the mp4s), short bridging narration, and a closing cliffhanger.
  New voice text ≤ 1,000 characters. Title "Hafta N: <title> | Hamid: Zero Se Shuru". Save under `hamid/weekly/wNN/`.
- Post to YouTube as type "video" (public), plus TikTok, Instagram (REEL), Facebook (REEL) if the platform accepts the length; report any platform that rejects it.
- Append to state.json "weekly".

## Report (every run)
SendUserMessage to the owner: what was posted (title, time, platforms) or what failed, characters of ElevenLabs used, next planned day.
