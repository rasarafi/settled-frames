---
name: watch-video
description: Use when the user asks Claude to watch, understand, summarise, break down, or answer questions about a video or screen recording (local file or URL, e.g. mp4/mov/webm, YouTube, Zoom/Meet/Loom recordings, demos, tutorials), or to find what was shown or said at a moment in one.
---

# Watch Video

Claude can't take video directly. This turns a video into timestamped frames plus a local Whisper
transcript aligned to each frame, has Haiku agents caption the frames in parallel, and lets the main
model reason over the captions instead of hundreds of images.

**Why 2 fps + settled frames:** tools that pick frames by scene change skip forms that fill in after
a spinner, and drop small popups, dropdowns and tooltips. This samples twice a second and keeps the
last frame of every stretch where the screen held still, so it keeps what the screen settled on.
Pairing each frame with its speech also catches homophones ("Murray" said, "Marie" on screen) and
said-vs-done gaps.

**Paths:** `<skill-dir>` below is this skill's base directory (shown when the skill loads).
`<venv>` is `~/.local/share/watch-video-venv` unless the user set it up elsewhere.

## Steps

1. **Prepare** (local, nothing uploaded). Write output to a scratch or temp folder, never into a repo:
   ```bash
   <venv>/bin/python -I <skill-dir>/scripts/prepare.py "<file or URL>" --out <scratch>/watch-<slug> \
     [--start MM:SS --end MM:SS] [--lang en] [--ignore x0,y0,x1,y1]
   ```
   It prints raw/kept frame counts, speech segments, batch count and timings. `--help` lists the
   other flags (`--threshold`, `--fine`, `--hold`, `--fps`, `--batch`, `--whisper-model`, `--no-audio`).
   If the venv is missing: `python3 -m venv <venv> && <venv>/bin/pip install faster-whisper pillow numpy yt-dlp`.

   **Check the kept count before captioning.** If most raw frames were kept (say over 60%), something
   on screen never stops moving, usually a presenter webcam. Open one frame, find the moving
   rectangle, and re-run with `--ignore` (fractions of the frame, e.g. `0.74,0.52,1,1` for the
   bottom-right corner).

2. **Caption**: one Agent per `batchN.txt`, all in ONE message so they run in parallel,
   `model: "haiku"`. Prompt = `<skill-dir>/caption-prompt.md` with placeholders filled:
   `{context}` one line on what the video is; `{batch_file}`/`{captions_file}` =
   `<out>/batchN.txt` / `<out>/captionsN.md`; `{focus}` = the user's question if any
   ("Pay special attention to: ..."), else empty.

3. **Check coverage**: `<venv>/bin/python -I <skill-dir>/scripts/check.py <out>`.
   Missing or mismatched frames → re-run that batch's agent. Do not synthesise from a failed check.

4. **Synthesise**: read `captionsN.md` (+ `transcript.txt` for exact quotes). Answer the user's
   question or write the breakdown with video timestamps. **Before stating a detail that matters
   (a field list, a number, a name, whether a popup was open), open that frame's image yourself**
   (path in `manifest.json`). Label claims that come only from speech as "said, not shown".

## Quick reference

| Situation | Do |
|---|---|
| Screen share / slides / demo | defaults (2 fps, 1% threshold, 0.3% fine) |
| Presenter webcam or other always-moving region | `--ignore x0,y0,x1,y1` |
| Too many frames kept | `--threshold 0.02`–`0.03`, or `--fine 0` |
| Long video, one question | `--start/--end` around the part that matters, or `{focus}` |
| No speech / music only | `--no-audio` |
| Non-English | `--lang <code>` or leave autodetect |
| Camera / live-action footage | not what this is built for: expect nearly every frame kept; use `--fps 1 --threshold 0.03` |

## Common mistakes

- Reading all frame images in the main context — use the captions; open only frames you cite.
- Trusting a caption over the image for a key fact — a Haiku agent sometimes describes the next
  frame under the current frame's id. `check.py` catches wrong file names, not wrong descriptions;
  only opening the frame does.
- Treating transcript names as correct — speech-to-text can't spell names; the screen wins.
- Writing outputs into the repo — scratch folder only.
