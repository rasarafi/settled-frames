#!/usr/bin/env python3
"""Turn a checklist source (items + the answer-key states that show each one) into items.json with time intervals.

Usage: build_items.py <items.src.json> <states.json> <state-frames-dir> <items.json> [--mask x0,y0,x1,y1]
  states.json : [{"id": "F0001", "file": "f_00008.jpg", "span": [start, end]}, ...] every stable state of the source
  items.src   : [{"id", "what", "kind", "states": [["F0003","F0013"], ["F0028"]]}]  each entry is a first-last range

Only states that last >= 1 s were described, so a range is first widened through the short neighbouring states
that still look the same (under TOL of pixels differ, i.e. only the mouse pointer moved); a blip under GAP
seconds between two matching states is stepped over. Without this an item
that stays on screen while the pointer moves would get an interval that is too short.
"""
import json, os, sys
import numpy as np
from PIL import Image

TOL = 0.001
GAP = 0.5
src, states_p, fdir, out = sys.argv[1:5]
mask = [float(x) for x in sys.argv[sys.argv.index("--mask") + 1].split(",")] if "--mask" in sys.argv else None  # same as gt_states.py
states = json.load(open(states_p))
idx = {s["id"]: i for i, s in enumerate(states)}
_img = {}


def img(i):
    if i not in _img:
        a = np.asarray(Image.open(os.path.join(fdir, states[i]["file"])).convert("L").resize((480, 270)), dtype=np.int16).copy()
        if mask:
            a[int(mask[1] * 270):int(mask[3] * 270), int(mask[0] * 480):int(mask[2] * 480)] = 0
        _img[i] = a
    return _img[i]


def same(i, j):
    return float((np.abs(img(i) - img(j)) > 12).mean()) < TOL


def widen(pos, ref, step):
    """Walk outwards from pos while states still match ref; a blip shorter than GAP seconds may be stepped over."""
    while True:
        j, gap, found = pos + step, 0.0, None
        while 0 <= j < len(states) and gap <= GAP:
            if same(j, ref):
                found = j
                break
            gap += states[j]["span"][1] - states[j]["span"][0]
            j += step
        if found is None:
            return pos
        pos = found


items = []
for it in json.load(open(src)):
    iv = []
    for r in it["states"]:
        a, b = idx[r[0]], idx[r[-1]]
        a, b = widen(a, idx[r[0]], -1), widen(b, idx[r[-1]], 1)
        iv.append([states[a]["span"][0], states[b]["span"][1]])
    iv.sort()
    merged = [iv[0]]
    for s, e in iv[1:]:
        if s <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    items.append({"id": it["id"], "what": it["what"], "kind": it["kind"], "intervals": merged,
                  "visible_s": round(sum(e - s for s, e in merged), 1)})
json.dump(items, open(out, "w"), indent=1)
for i in items:
    print(f'{i["id"]} {i["kind"][:5]:5} {i["visible_s"]:6.1f}s  {i["intervals"]}  {i["what"][:50]}')
