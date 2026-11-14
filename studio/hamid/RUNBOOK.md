# Runbook — scheduled runs for "Hamid: Zero Se Shuru"

Read SERIES.md first. All paths below are relative to the Ventus repo root. The repo is PUBLIC: never commit the ElevenLabs key.

## 0. Setup (every run)
- Repo: if `/home/claude/ventus` is missing, attach Hamiduz67/Ventus with push access (add_repo) and clone it there.
  Always `git fetch origin +main:refs/remotes/origin/main && git rebase origin/main` before committing; push to main.
- Save the ElevenLabs key from the task prompt to `~/.secrets/elevenlabs_key` (chmod 600).
- Python needs numpy + pillow + ffmpeg (usually present). The Noto Color Emoji font must exist at /usr/share/fonts/truetype/noto/NotoColorEmoji.ttf.
- If downloads fail with TLS errors, use the proxy CA bundle (~/.ccr/ca-bundle.crt).

## A. Daily reel run (2 per day: posts at 13:00 and 20:00 Asia/Dubai)
1. Read `studio/hamid/state.json`. Next day = last_day + 1. Check `python3 studio/hamid/buffer_post.py status` so you never double-post a day.
2. Write `hamid/epNNN/script.json` (NNN = day, 3 digits) + `meta.json` ({"day", "city", "money"}).
   - Follow the format and language rules in SERIES.md and the planned day list; continue from `story_so_far`.
   - Line fields: who (H/A/B/L/R/G/S…), mode ("vo" narration or "talk" on-screen dialogue), scene (a key in hamid_render.py `SC`), dev (Urdu script), rom (Roman caption, same words).
   - Reel length 75–90 s with the full story structure in SERIES.md "Reel format". Keep total `dev` text ≤ 600 characters (length comes from wordless visual beats, not more voice). Hamid lines: no [tags].
3. Voices: `python3 studio/hamid/tts.py hamid/epNNN`. Optional check: transcribe with faster-whisper small (language "ur") and redo garbled lines (delete that v##.wav and rerun).
4. Scenes: reuse existing scene functions in `studio/hamid/hamid_render.py`; add new ones (dhaba, street, bus station, Karachi room, rain, etc.) in the same flat 2D style, and new characters/props as needed. Commit renderer changes so later runs reuse them. Keep Hamid/Ammi/Abbu exactly as drawn.
5. Audio + render:
   `python3 studio/hamid/hamid_audio.py hamid/epNNN` then `python3 studio/hamid/hamid_render.py hamid/epNNN still:<4–8 times>` and LOOK at the frames (contact sheet). Fix overlaps/cut-off text. Then full render and mux:
   `python3 studio/hamid/hamid_render.py hamid/epNNN && ffmpeg -i video.tmp.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart Hamid_DayNN.mp4`
6. Publish (Buffer free plan — Metricool's free plan is used up; do NOT post through Metricool):
   commit only the final mp4 + script.json + meta.json (not wav/mp3/f32/stills) to `hamid/epNNN/`, push, then use the COMMIT-SHA raw URL
   (https://raw.githubusercontent.com/Hamiduz67/Ventus/<sha>/hamid/epNNN/Hamid_DayNN.mp4) and confirm HTTP 200.
   Save the Buffer key from the task prompt to `~/.secrets/buffer_key` (chmod 600), then:
   `python3 studio/hamid/buffer_post.py schedule --url <raw url> --caption "<caption>" --title "Day N: <hook> | Hamid: Zero Se Shuru #shorts" --tiktok-title "Hamid: Zero Se Shuru — Day N" --at "YYYY-MM-DD HH:MM"`
   (time is Asia/Dubai: today 13:00 or 20:00 = the run's slot). This posts to YouTube Shorts + TikTok + Instagram Reel.
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
