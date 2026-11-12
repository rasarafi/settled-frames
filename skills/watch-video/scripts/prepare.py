#!/usr/bin/env python3
"""Prepare a video for Claude: 2 fps frames -> settled-frame dedup -> local Whisper -> aligned batches.

Run with the skill venv:  ~/.local/share/watch-video-venv/bin/python -I prepare.py <video|url> --out DIR
Nothing is uploaded: ffmpeg, the frame comparison and Whisper all run on this machine.
Writes DIR/frames/*.jpg, DIR/transcript.json, DIR/manifest.json, DIR/batchN.txt
"""
import argparse, json, math, os, shutil, subprocess, sys, time

import numpy as np
from PIL import Image


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd[:3])}...\n{r.stderr[-2000:]}")
    return r.stdout


def hms(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:04.1f}" if t >= 3600 else f"{int(t // 60):02d}:{t % 60:04.1f}"


def parse_t(s):
    if s is None:
        return None
    parts = [float(p) for p in str(s).split(":")]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def fetch(src, out):
    if os.path.exists(src):
        return os.path.abspath(src)
    if not src.startswith(("http://", "https://")):
        sys.exit(f"not a file or URL: {src}")
    ytdlp = os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    dest = os.path.join(out, "source.%(ext)s")
    run([ytdlp, "-q", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4", "-o", dest, src])
    return next(os.path.join(out, f) for f in os.listdir(out) if f.startswith("source."))


def probe(video):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                        "-of", "json", video]))
    dur = float(j["format"]["duration"])
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    has_audio = any(s["codec_type"] == "audio" for s in j["streams"])
    return dur, (v["width"], v["height"]) if v else None, has_audio


def extract_frames(video, start, length, fps, max_width, raw):
    os.makedirs(raw, exist_ok=True)
    vf = f"fps={fps},scale='min({max_width},iw)':-2"
    run(["ffmpeg", "-loglevel", "error", "-ss", str(start), "-t", str(length), "-i", video, "-vf", vf, "-q:v", "2",
         os.path.join(raw, "f_%05d.jpg")])
    return sorted(os.listdir(raw))


def dedup(raw, files, start, fps, threshold, fine, hold, ignore=None):
    """Group near-identical frames into runs and keep the settled frame(s) of each run.

    A run ends when at least `threshold` of the pixels changed. Its LAST frame is kept: that is the
    screen after spinners and half-rendered forms have finished.
    Inside a run, a smaller change (at least `fine` of the pixels: a tooltip, a dropdown, one row
    selected) starts a sub-state. A sub-state that then holds for `hold` seconds also keeps its last
    frame. Without this, a small popup that opens and closes inside one run would be lost, because
    only the frame after it closed would be kept.
    """
    step = 1.0 / fps
    min_len = max(1, math.ceil(hold * fps))

    def load(f):
        a = np.asarray(Image.open(os.path.join(raw, f)).convert("L").resize((480, 270)), dtype=np.int16)
        if ignore:  # blank the ignored rectangle so movement inside it never counts as a change
            a = a.copy()
            a[int(ignore[1] * 270):int(ignore[3] * 270), int(ignore[0] * 480):int(ignore[2] * 480)] = 0
        return a

    def changed(a, b):
        return float((np.abs(a - b) > 12).mean())

    kept = []  # (first index, last index) of each kept segment

    def close_run(subs):
        ends = sorted({s[-1] for s in subs if len(s) >= min_len} | {subs[-1][-1]})
        lo = subs[0][0]
        for e in ends:
            kept.append((lo, e))
            lo = e + 1

    subs, first, sub_first, prev = [], None, None, None
    for i, f in enumerate(files):
        a = load(f)
        if subs and changed(first, a) < threshold and changed(prev, a) < threshold:
            if fine and (changed(sub_first, a) >= fine or changed(prev, a) >= fine):
                subs.append([i])
                sub_first = a
            else:
                subs[-1].append(i)
        else:
            if subs:
                close_run(subs)
            subs, first, sub_first = [[i]], a, a
        prev = a
    if subs:
        close_run(subs)
    return [{"file": files[e], "t": round(start + e * step, 2),
             "span": [round(start + s * step, 2), round(start + (e + 1) * step, 2)]} for s, e in kept]


def transcribe(video, start, length, model, lang, out):
    wav = os.path.join(out, "audio.wav")
    run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(length), "-i", video, "-vn", "-ac", "1",
         "-ar", "16000", wav])
    import wave
    from faster_whisper import WhisperModel
    with wave.open(wav) as w:  # pass samples directly; avoids faster-whisper's PyAV decoder (version clashes)
        audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=max(2, min(8, (os.cpu_count() or 4) // 2)))  # more threads than half the cores ran far slower in testing
    segs, info = m.transcribe(audio, language=lang, vad_filter=True, beam_size=5)
    res = [{"start": round(s.start + start, 2), "end": round(s.end + start, 2), "text": s.text.strip()} for s in segs]
    os.remove(wav)
    return res, info.language


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="video file or URL")
    ap.add_argument("--out", required=True, help="output dir (a scratch or temp folder, not your repo)")
    ap.add_argument("--start", help="start time, seconds or MM:SS or HH:MM:SS")
    ap.add_argument("--end", help="end time")
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--threshold", type=float, default=0.01,
                    help="fraction of pixels that must change to start a new frame (0.01 = 1%%)")
    ap.add_argument("--fine", type=float, default=0.003,
                    help="smaller change that starts a sub-state inside a run (0.003 = 0.3%%); 0 turns this off")
    ap.add_argument("--hold", type=float, default=1.0,
                    help="seconds a sub-state must stay on screen for its frame to be kept")
    ap.add_argument("--ignore", help="x0,y0,x1,y1 as fractions of the frame: a rectangle to ignore when comparing "
                    "frames, e.g. 0.74,0.52,1,1 for a presenter webcam in the bottom-right corner")
    ap.add_argument("--max-width", type=int, default=1920)
    ap.add_argument("--batch", type=int, default=24, help="frames per captioning agent")
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--lang", default=None, help="e.g. en; default autodetect")
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()
    try:
        ignore = [float(x) for x in a.ignore.split(",")] if a.ignore else None
    except ValueError:
        ignore = [-1]
    if ignore and (len(ignore) != 4 or not all(0 <= x <= 1 for x in ignore) or ignore[0] >= ignore[2] or ignore[1] >= ignore[3]):
        sys.exit("--ignore needs x0,y0,x1,y1 between 0 and 1, with x0 < x1 and y0 < y1")

    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    video = fetch(a.src, out)
    dur, size, has_audio = probe(video)
    if size is None:
        sys.exit("no video stream")
    start = parse_t(a.start) or 0.0
    end = min(parse_t(a.end) or dur, dur)
    length = end - start

    raw = os.path.join(out, "frames")
    if os.path.isdir(raw):
        shutil.rmtree(raw)
    files = extract_frames(video, start, length, a.fps, a.max_width, raw)
    t_frames = time.time() - t0
    keep = dedup(raw, files, start, a.fps, a.threshold, a.fine, a.hold, ignore)
    kept = {k["file"] for k in keep}
    for f in files:
        if f not in kept:
            os.remove(os.path.join(raw, f))
    t_dedup = time.time() - t0

    segs, lang = [], None
    if has_audio and not a.no_audio:
        segs, lang = transcribe(video, start, length, a.whisper_model, a.lang, out)
    json.dump({"segments": segs, "language": lang}, open(os.path.join(out, "transcript.json"), "w"), indent=1)
    with open(os.path.join(out, "transcript.txt"), "w") as fh:
        fh.writelines(f"[{hms(s['start'])}-{hms(s['end'])}] {s['text']}\n" for s in segs)
    t_audio = time.time() - t0

    # attach each speech segment to the frame on screen when it starts
    for k in keep:
        k["speech"] = []
    spans = [k["span"][0] for k in keep]
    for s in segs:
        st = max(s["start"], start)
        idx = max(i for i, s0 in enumerate(spans) if s0 <= st) if st >= spans[0] else 0
        keep[idx]["speech"].append(f"[{hms(s['start'])}-{hms(s['end'])}] {s['text']}")

    for i, k in enumerate(keep, 1):
        k["id"] = f"F{i:04d}"
    nb = math.ceil(len(keep) / a.batch)
    per = math.ceil(len(keep) / nb)  # spread evenly, e.g. 73 -> 25/24/24 not 24/24/24/1
    for b in range(nb):
        blocks = []
        for k in keep[b * per:(b + 1) * per]:
            blocks.append(f"### {k['id']} @ {hms(k['t'])} (on screen {hms(k['span'][0])}-{hms(k['span'][1])})\n"
                          f"image: {os.path.join(raw, k['file'])}\n"
                          f"speech starting while on screen: " + (" | ".join(k["speech"]) or "(none)"))
        open(os.path.join(out, f"batch{b + 1}.txt"), "w").write("\n\n".join(blocks) + "\n")

    manifest = {"source": video, "duration": dur, "size": size, "start": start, "end": end, "fps": a.fps,
                "threshold": a.threshold, "fine": a.fine, "hold": a.hold, "ignore": ignore, "raw_frames": len(files), "kept_frames": len(keep), "batches": nb,
                "batch_size": per, "speech_segments": len(segs), "language": lang,
                "timing_s": {"frames": round(t_frames, 1), "dedup": round(t_dedup - t_frames, 1),
                             "audio": round(t_audio - t_dedup, 1)},
                "frames": keep}
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"source: {video}\nrange: {hms(start)}-{hms(end)} ({length:.0f}s) size {size[0]}x{size[1]}\n"
          f"frames: {len(files)} at {a.fps} fps -> {len(keep)} kept ({a.threshold:.1%} threshold)\n"
          f"speech: {len(segs)} segments, language {lang}\n"
          f"batches: {nb} x ~{per} -> {out}/batch1..{nb}.txt\n"
          f"time: frames {t_frames:.0f}s, dedup {t_dedup - t_frames:.0f}s, audio {t_audio - t_dedup:.0f}s")


if __name__ == "__main__":
    main()
