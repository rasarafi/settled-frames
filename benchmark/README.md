# Benchmark: which frames does each tool keep?

Run on 2026-11-12. Tools compared:

- **settled-frames** (this repo), `prepare.py` defaults.
- **crv**: [claude-real-video](https://github.com/HUANGCHIHHUNGLeo/claude-real-video) v0.10.7, commit `ab4b9b2`.
- **claude-video**: [bradautomates/claude-video](https://github.com/bradautomates/claude-video), commit `03ceb42`,
  local engine only. Its Gemini engine sends the whole video to Gemini and was not tested.

## The question

Every one of these tools reduces a video to a set of frames. A model can only read what is in a kept
frame. So the benchmark asks one thing: **for each thing shown in the video, did the tool keep a frame
that shows it?**

It does not measure how well a model reads the frames, and it does not measure the transcript.

## The videos

Public YouTube screen recordings. They are not redistributed here; no frame from them is in this repo.

| Key | Video | Length | Why |
|---|---|---|---|
| v1 | [ServiceNow FSM: Work Order Task](https://www.youtube.com/watch?v=f5ubJySWrvE), Palni Inc | 6:02 | lookup popups, date pickers, dropdowns |
| v2 | [Walkthrough of Work Orders in Dynamics 365 Field Service](https://www.youtube.com/watch?v=ojmBluvAe9A), Stoneridge Software | 7:48 | mostly white interface, tabs, flyouts, tooltips |
| v3 | [How to create Sales Order in ERPNext](https://www.youtube.com/watch?v=8yd8qHb_gfk), Techsolvo | 3:39 | presenter webcam in the corner |

v1 and v2 were picked first. **v3 was picked after the keep rule was frozen** (see "What changed
because of this benchmark"), so v3 is the only independent test of the current rule.

## The answer key

1. `gt_states.py` samples each video at 5 fps and splits it into stable states wherever 0.3% of the
   pixels change. That is much denser than any tool here, so the key does not lean on any tool's choices.
   For v3 the webcam corner is masked when building the key (not when running the tools).
2. Every state that lasts at least one second was described from its screenshot by a model
   (Haiku for v1 and v2, Sonnet for v3).
3. From those descriptions I wrote the checklist: every screen, tab, filled-in value, popup, dropdown
   and tooltip that carries information. Items are marked **brief** (popups, dropdowns, tooltips, hover
   cards, pickers) or lasting. Files: `v1-items.src.json`, `v2-items.src.json`, `v3-items.src.json`.
4. A second model (Sonnet) then opened the screenshots for each item and confirmed the item is
   really there. This step mattered: in v1, 8 of 28 items needed correcting, most because the first
   model had described the next image under some ids. v2 needed 1 correction and v3 needed 2.
5. `build_items.py` turns each item into the time window(s) it is on screen.

73 items in total: v1 28 (12 brief), v2 23 (7 brief), v3 22 (6 brief).

## Scoring

1. `run_all.sh` runs every tool and setting on a video. `collect_times.py` reads the timestamp of each
   kept frame.
2. `score.py` gives a tool an item if a kept frame falls inside the item's window.
3. **Every claimed miss was then checked by eye.** The windows in step 2 are conservative, so a tool can
   show an item with a frame just outside its window. `miss_candidates.py` lists the tool's kept frames
   nearest to each missed item, and a model (Sonnet) opened them and ruled VISIBLE, VISIBLE-UNREADABLE
   or CONFIRMED MISS. Of 223 claimed misses, 82 were overturned as VISIBLE, 4 were on screen but too
   small to read (still counted as misses) and 137 were confirmed. The rulings, with a line of evidence
   each, are in `verdicts.md`.
4. As a matching check on this repo's own tool, all 25 brief items it was credited with were also
   opened. All 25 were visible.
5. `verified.py` prints the final tables below from steps 2 and 3.

Borderline rulings went to the other tools (for example, a date counted as shown when it was readable
in a table row but its own field was off screen).

## Results

"Still missed" lists item numbers; look them up in `vN-items.json`.

### v1: ServiceNow, 28 items (12 brief)

| tool and setting | frames kept | items shown | brief items | still missed |
|---|---|---|---|---|
| settled-frames (default) | 201 | 28/28 | 12/12 | - |
| settled-frames, original rule (`--fine 0`) | 155 | 28/28 | 12/12 | - |
| crv, default | 81 | 25/28 | 10/12 | 14, 17, 21 |
| crv, tuned | 101 | 26/28 | 11/12 | 17, 21 |
| crv, sensitive | 147 | 27/28 | 12/12 | 21 |
| crv, finest | 162 | 28/28 | 12/12 | - |
| claude-video, default | 28 | 16/28 | 3/12 | 06, 08, 11, 13, 14, 15, 17, 21, 23, 24, 26, 27 |
| claude-video, token-burner 1920px | 28 | 16/28 | 3/12 | 06, 08, 11, 13, 14, 15, 17, 21, 23, 24, 26, 27 |
| claude-video, token-burner 1920px at 2 fps | 74 | 25/28 | 9/12 | 15, 26, 27 |

### v2: Dynamics 365, 23 items (7 brief)

| tool and setting | frames kept | items shown | brief items | still missed |
|---|---|---|---|---|
| settled-frames (default) | 167 | 23/23 | 7/7 | - |
| settled-frames, original rule (`--fine 0`) | 139 | 21/23 | 6/7 | 16, 20 |
| crv, default | 21 | 11/23 | 0/7 | 03, 04, 05, 06, 07, 08, 10, 13, 15, 17, 19, 20 |
| crv, tuned | 28 | 14/23 | 0/7 | 03, 05, 06, 08, 13, 15, 17, 19, 20 |
| crv, sensitive | 39 | 14/23 | 0/7 | 03, 06, 07, 08, 13, 15, 17, 19, 20 |
| crv, finest | 49 | 16/23 | 1/7 | 03, 06, 07, 08, 15, 19, 20 |
| claude-video, default | 21 | 13/23 | 0/7 | 01, 03, 06, 08, 13, 15, 17, 19, 20, 23 |
| claude-video, token-burner 1920px | 21 | 13/23 | 0/7 | 01, 03, 06, 08, 13, 15, 17, 19, 20, 23 |
| claude-video, token-burner 1920px at 2 fps | 47 | 16/23 | 2/7 | 01, 06, 10, 15, 17, 19, 20 |

### v3: ERPNext, 22 items (6 brief). The independent test.

| tool and setting | frames kept | items shown | brief items | still missed |
|---|---|---|---|---|
| settled-frames (default) | 340 | 22/22 | 6/6 | - |
| settled-frames, original rule (`--fine 0`) | 336 | 22/22 | 6/6 | - |
| settled-frames with `--ignore` on the webcam corner | 87 | 22/22 | 6/6 | - |
| crv, default | 36 | 12/22 | 3/6 | 04, 05, 06, 08, 09, 10, 14, 17, 18, 22 |
| crv, tuned | 40 | 14/22 | 3/6 | 04, 05, 08, 09, 14, 17, 18, 22 |
| crv, sensitive | 64 | 17/22 | 4/6 | 04, 05, 08, 17, 18 |
| crv, finest | 70 | 18/22 | 4/6 | 07, 08, 18, 22 |
| claude-video, default | 27 | 17/22 | 3/6 | 04, 05, 07, 09, 14 |
| claude-video, token-burner 1920px | 27 | 17/22 | 3/6 | 04, 05, 07, 09, 14 |
| claude-video, token-burner 1920px at 2 fps | 54 | 17/22 | 2/6 | 02, 07, 08, 09, 14 |

### Settings used

| Label | Flags |
|---|---|
| crv, default | `--no-transcribe` |
| crv, tuned | `--adaptive --text-anchors --frame-width 1920 --max-frames 600` |
| crv, sensitive | tuned + `--scene 0.1 --dedup-threshold 2 --fps-floor 0.5` |
| crv, finest | tuned + `--scene 0.1 --dedup-threshold 0.5 --fps-floor 0.5` |
| claude-video, default | `--engine local --no-whisper` (512 px frames) |
| claude-video, token-burner | `--engine local --no-whisper --detail token-burner --resolution 1920` |
| claude-video, 2 fps | token-burner + `--fps 2` |

I am not the author of either tool. These are the strongest settings I found in their help text; their
authors may know better ones.

## What the results say

- **Brief things are where frame selection fails.** Across the three videos the other tools, at their
  best setting per tool, showed 17 and 13 of the 25 brief items.
- **A mostly white interface is the hard case for pixel-difference dedup.** On v2, crv kept 21 to 49
  frames of a 7:48 video: it treats a tab change on a sparse page as "nearly the same frame".
- **On a dense interface the gap closes.** On v1, crv at its finest setting showed all 28 items with
  162 frames, fewer than settled-frames used.
- **settled-frames pays for coverage in frames:** 708 frames across the three videos against 138 to 281.
- **A webcam overlay is its weak spot.** On v3 it kept 77% of all sampled frames until the corner was ignored.

## What changed because of this benchmark

The original rule kept only the last frame of each run of near-identical frames (a run ends when 1% of
the pixels change). On v2 that missed two items: a row deselected and a tooltip, both under 1%. The
frame kept was the one after the small thing was gone.

The rule now also keeps the frame of a smaller change (0.3%) if it holds for a second. That fix was
designed on v1 and v2, so the "default" rows for v1 and v2 are not an independent result. The
"original rule" rows show what the tool scored before the fix. `--ignore` was added after seeing v3 and
is reported as its own row.

## End to end

The tables above are about frames. As a separate check, the whole skill was run on v2 from a fresh
install (by URL, 167 frames, 7 Haiku caption agents, coverage check passed). A model then compared the
captions with the v2 checklist: all 23 items were reported in a caption, each within 3 seconds of the
item's window. See `end-to-end-v2.md`. That is one run on one video.

## Known weaknesses of this benchmark

- I wrote the checklist and I wrote one of the tools. The checklist rule (everything informative that
  stays for a second) is meant to limit that, and the files are here to argue with.
- Models did the describing and the checking. Steps 4 (key) and 3 (scoring) exist because the first pass
  made mistakes. Some rulings may still be wrong.
- Items that stay under one second are not in the key, for any tool.
- Three videos, all business software. Nothing here says anything about camera footage, slides or games.
- Frame count is only a rough stand-in for cost: claude-video's default frames are 512 px wide and far
  cheaper per frame than full-resolution ones.
- Run times are not compared: settled-frames' time includes transcription, the others ran without it.

## Rerun it

Scoring only (no model, no video needed):

```bash
python3 benchmark/verified.py benchmark benchmark/times
```

Everything from the videos (needs ffmpeg, yt-dlp, and both other tools installed):

```bash
mkdir -p benchmark/videos
yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]" -o benchmark/videos/v1.mp4 "https://www.youtube.com/watch?v=f5ubJySWrvE"
# same for v2 (ojmBluvAe9A) and v3 (8yd8qHb_gfk)

export SETTLED_PY=~/.local/share/watch-video-venv/bin/python
export CRV_PY=/path/to/crv-venv/bin/python        # pip install claude-real-video
export CV_DIR=/path/to/claude-video               # git clone
for k in v1 v2 v3; do benchmark/run_all.sh $k benchmark/videos/$k.mp4 benchmark/runs; done

$SETTLED_PY benchmark/collect_times.py benchmark/runs benchmark/videos benchmark/work/times
$SETTLED_PY benchmark/score.py benchmark/v1-items.json benchmark/work/times --video v1
$SETTLED_PY benchmark/miss_candidates.py benchmark/v1-items.json benchmark/work/times/v1-crv-default.json
```

To rebuild the answer key windows: `gt_states.py <video> <out-dir>` (add `--mask 0.74,0.52,1,1` for v3),
then `build_items.py v1-items.src.json <out-dir>/states.json <out-dir>/frames v1-items.json`.
YouTube re-encodes videos over time, so timestamps may shift by a frame or two.
