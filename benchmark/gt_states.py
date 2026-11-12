#!/usr/bin/env python3
"""Split a source video into stable on-screen states. This is the base of the answer key.

It samples far more densely than any tool under test (5 fps, 0.3% of pixels) so the key does not
depend on any tool's frame choice. Each state's last frame is saved for a human or model to describe.

Usage: gt_states.py <video> <out-dir> [--mask x0,y0,x1,y1]
  --mask  fraction-of-frame rectangle to ignore when comparing (e.g. a webcam overlay of the presenter,
          which moves all the time and would otherwise split every state). Tools under test get no mask.
Writes <out-dir>/frames/*.jpg and <out-dir>/states.json: [{"id", "file", "t", "span": [start, end]}]
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image

FPS, THRESHOLD = 5.0, 0.003
video, out = sys.argv[1], sys.argv[2]
mask = [float(x) for x in sys.argv[sys.argv.index("--mask") + 1].split(",")] if "--mask" in sys.argv else None
raw = os.path.join(out, "frames")
os.makedirs(raw, exist_ok=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-vf", f"fps={FPS}", "-q:v", "2",
                os.path.join(raw, "f_%05d.jpg")], check=True)
files = sorted(os.listdir(raw))


def load(f):
    a = np.asarray(Image.open(os.path.join(raw, f)).convert("L").resize((480, 270)), dtype=np.int16).copy()
    if mask:
        a[int(mask[1] * 270):int(mask[3] * 270), int(mask[0] * 480):int(mask[2] * 480)] = 0
    return a


def changed(a, b):
    return float((np.abs(a - b) > 12).mean())


groups, first, prev, cur = [], None, None, []
for i, f in enumerate(files):
    a = load(f)
    if cur and changed(first, a) < THRESHOLD and changed(prev, a) < THRESHOLD:
        cur.append(i)
    else:
        if cur:
            groups.append(cur)
        cur, first = [i], a
    prev = a
groups.append(cur)
keep = {files[g[-1]] for g in groups}
for f in files:
    if f not in keep:
        os.remove(os.path.join(raw, f))
states = [{"id": f"F{n:04d}", "file": files[g[-1]], "t": round(g[-1] / FPS, 2),
           "span": [round(g[0] / FPS, 2), round((g[-1] + 1) / FPS, 2)]} for n, g in enumerate(groups, 1)]
json.dump(states, open(os.path.join(out, "states.json"), "w"))
long = sum(1 for s in states if s["span"][1] - s["span"][0] >= 1.0)
print(f"{len(files)} frames at {FPS} fps -> {len(states)} states, {long} stable for >= 1 s")
