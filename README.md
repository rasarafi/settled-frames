# settled-frames

A Claude Code skill (`watch-video`) that lets Claude watch screen recordings and product demos
without missing what loads late or shows only briefly.

Claude can't take video directly, so every "watch a video" tool turns the video into a set of frames
plus a transcript. The tools differ in **which frames they keep**, and that is where they fail on
screen recordings: a form that fills in after a spinner, a dropdown that is open for two seconds, a
tooltip, a lookup popup. If the frame isn't kept, no model can read it.

This skill samples the video twice a second and keeps the frame the screen **settled on** each time
it stopped changing.

## What the benchmark found

Three public screen recordings (ServiceNow, Dynamics 365, ERPNext), 73 checklist items in total: every
screen, tab, popup, dropdown and tooltip that stays on screen for at least a second. A tool gets an item
if one of the frames it kept shows it. Every claimed miss was checked by opening the tool's own frames.

| | items shown (of 73) | brief items: popups, dropdowns, tooltips (of 25) | frames kept |
|---|---|---|---|
| **settled-frames**, default | **73** | **25** | 708 |
| [claude-real-video](https://github.com/HUANGCHIHHUNGLeo/claude-real-video) (crv), default | 48 | 13 | 138 |
| crv, finest setting I could find | 62 | 17 | 281 |
| [claude-video](https://github.com/bradautomates/claude-video), local engine, default | 46 | 6 | 76 |
| claude-video, local engine, 2 fps at full resolution | 58 | 13 | 175 |

Read this table with its limits in mind:

- **settled-frames keeps far more frames.** More frames means more tokens. It trades cost for coverage.
- **On one of the three videos, crv at its finest setting ties it** (28/28) with fewer frames (162 vs 201).
  The gap comes from the other two videos, where the interface is mostly white space and small changes.
- **The third video has a presenter webcam in the corner**, which never stops moving. settled-frames kept
  340 of 439 frames there. With `--ignore` on that corner it kept 87 and still showed all 22 items.
- The keep rule was improved using the first two videos (the original rule scored 21/23 on the second).
  The third video was chosen after the rule was frozen, so only that one is an independent test.
- Both other tools are good at what they are built for: general video, including camera footage, at a
  low token cost. claude-video can also hand the whole video to Gemini, which this benchmark did not test.
- Three videos is a small sample.

Method, per-video tables, the answer key and every check are in [`benchmark/`](benchmark/README.md).
You can rerun the scoring without any model.

## How it works

1. **Frames.** ffmpeg takes 2 frames per second at full resolution.
2. **Settled frames.** Consecutive frames are compared. While less than 1% of the pixels change, the
   frames belong to one run, and the **last** frame of the run is kept: the screen after loading
   finished. Inside a run, a smaller change (0.3% of pixels: a tooltip, a dropdown, a selected row)
   that then holds for a second also keeps its frame.
3. **Speech.** faster-whisper transcribes the audio on your machine. Each sentence is attached to the
   frame that was on screen when it started.
4. **Captions.** Haiku subagents caption the frames in parallel, 24 frames each, with the speech beside
   each frame. They note where the speech and the screen disagree.
5. **Check.** A script confirms every frame was captioned against the right image file.
6. **Answer.** The main model reads the captions, and opens a frame itself before stating any detail
   that matters.

Nothing leaves your machine except the frames Claude reads.

## Install

Needs Python 3.10+, `ffmpeg`, and Claude Code.

**As a plugin:**

```
/plugin marketplace add rasarafi/settled-frames
/plugin install settled-frames@settled-frames
```

then create the Python environment once:

```bash
git clone https://github.com/rasarafi/settled-frames && cd settled-frames
./install.sh --no-skill
```

**As a plain skill:**

```bash
git clone https://github.com/rasarafi/settled-frames && cd settled-frames
./install.sh        # venv at ~/.local/share/watch-video-venv, skill at ~/.claude/skills/watch-video
```

## Use

In Claude Code:

> watch this video: ~/Downloads/demo.mp4. What fields does the new order form have?

> watch https://www.youtube.com/watch?v=... from 03:40 to 07:40 and list every step

The frame step can also be run on its own:

```bash
~/.local/share/watch-video-venv/bin/python -I skills/watch-video/scripts/prepare.py demo.mp4 --out /tmp/watch-demo
```

| Flag | Default | Use |
|---|---|---|
| `--start`, `--end` | whole video | watch only part of it |
| `--ignore x0,y0,x1,y1` | none | ignore a region that always moves, e.g. `0.74,0.52,1,1` for a webcam in the bottom-right |
| `--threshold` | `0.01` | share of pixels that must change to start a new run; raise to keep fewer frames |
| `--fine` | `0.003` | the smaller change that is kept if it holds; `0` turns it off |
| `--hold` | `1.0` | seconds a small change must hold |
| `--fps` | `2` | samples per second |
| `--lang`, `--whisper-model`, `--no-audio` | auto, `small`, off | transcription |

## Cost and limits

- **Tokens.** Captioning costs about 6,400 Haiku tokens per kept frame. The 7:48 Dynamics demo kept
  167 frames and used about 1.07 million Haiku tokens. On a subscription plan that is cheap; on
  pay-per-token pricing, check before running it on long videos.
- **Built for screen recordings.** On camera footage nearly every frame differs, so nearly every frame
  is kept. Use another tool for that.
- **Always-moving regions** (a webcam, a clock, an animation) defeat the comparison until you pass `--ignore`.
- **Captions can be wrong.** In testing, Haiku sometimes described the next frame under the current
  frame's id. The coverage check catches wrong file names, not wrong descriptions. That is why step 6
  opens the frame before a key fact is stated.
- **Long videos** mean many subagents at once. Over about 30 minutes, run it in parts with `--start`/`--end`.
- Needs Claude Code subagents. Whisper runs on CPU at roughly 6x real time with the `small` model.

## Credit

The comparison tools are [claude-real-video](https://github.com/HUANGCHIHHUNGLeo/claude-real-video) by
LeoAido and [claude-video](https://github.com/bradautomates/claude-video) by Brad. The idea of dense
sampling with speech aligned to frames came from reading about Liquid AI's omni models.

Built by [rasarafi](https://github.com/rasarafi) with Claude Code. MIT licence.
