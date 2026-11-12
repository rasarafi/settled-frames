#!/usr/bin/env python3
"""Collect each run's kept-frame timestamps into <times-dir>/<run>.json for score.py.

Usage: collect_times.py <runs-dir> <videos-dir> <times-dir>
Reads <runs-dir>/<key>-<tool>-<config>/ as written by run_all.sh; the source video is <videos-dir>/<key>.mp4.
  settled : out/manifest.json            exact sample times
  crv     : out/frames.json              exact (timestamp_sec)
  cv      : stdout.txt "(t=MM:SS, ...)"  claude-video prints whole seconds only, so each kept frame is
            matched against the source video inside that second to recover its real time
"""
import glob, json, os, re, subprocess, sys
import numpy as np
from PIL import Image

runs, videos, out = sys.argv[1:4]
W, H, FPS = 320, 180, 10
_src = {}


def source(k):
    if k not in _src:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(videos, k + ".mp4"), "-vf",
                              f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, check=True).stdout
        _src[k] = np.frombuffer(raw, dtype=np.uint8).reshape(-1, H, W)
    return _src[k]


def refine(k, path, t):
    """t is cut to a whole second: find the best-matching source frame in [t-0.3, t+1.3]."""
    src = source(k)
    img = np.asarray(Image.open(path).convert("L").resize((W, H)), dtype=np.int16)
    lo, hi = max(0, int((t - 0.3) * FPS)), min(len(src), int((t + 1.3) * FPS) + 1)
    d = [np.abs(src[i].astype(np.int16) - img).mean() for i in range(lo, hi)]
    best = min(d)
    near = [i for i, x in enumerate(d) if x <= best + 0.15]  # a still screen matches many frames: take the middle
    return round((lo + near[len(near) // 2]) / FPS, 2)


os.makedirs(out, exist_ok=True)
for name in sorted(os.listdir(runs)):
    d = os.path.join(runs, name)
    if not os.path.isfile(os.path.join(d, "time.txt")):
        continue
    k, tool = name.split("-")[0], name.split("-")[1]
    tt = open(os.path.join(d, "time.txt")).read()
    secs = float(re.search(r"secs=([\d.]+)", tt).group(1))
    if "rc=0" not in tt:
        print(f"{name}: FAILED ({tt.strip()}), skipped")
        continue
    if tool == "settled":
        fr = [(f["t"], os.path.join(d, "out", "frames", f["file"]))
              for f in json.load(open(os.path.join(d, "out", "manifest.json")))["frames"]]
    elif tool == "crv":
        fr = [(f["timestamp_sec"], os.path.join(d, "out", "frames", f["file"]))
              for f in json.load(open(os.path.join(d, "out", "frames.json")))["frames"]]
    else:
        fr = []
        text = open(os.path.join(d, "stdout.txt")).read()
        for path, stamp in re.findall(r"`([^`]+\.jpg)` \(t=([\d:]+)", text):
            parts = [int(p) for p in stamp.split(":")]
            t = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
            local = glob.glob(os.path.join(d, "out", "*", "frames", os.path.basename(path)))[0]
            fr.append((refine(k, local, t), local))
    fr.sort()
    json.dump({"run": name, "times": [t for t, _ in fr], "files": [os.path.abspath(f) for _, f in fr],
               "secs": round(secs, 1)}, open(os.path.join(out, name + ".json"), "w"))
    print(f"{name}: {len(fr)} frames, {secs:.0f}s")
