#!/usr/bin/env python3
"""For one run, list the kept frames closest to each item the time-based score says it missed.

score.py only compares timestamps with the answer-key windows, and those windows can be too narrow.
This prints, per missed item, the run's kept frames nearest to the item's windows, so a person or a
model can open them and confirm the item really is not shown. Usage:
  miss_candidates.py <items.json> <times-dir>/<run>.json [--pad 6] [--max 4]
"""
import json, sys

items = json.load(open(sys.argv[1]))
run = json.load(open(sys.argv[2]))
pad = float(sys.argv[sys.argv.index("--pad") + 1]) if "--pad" in sys.argv else 6.0
top = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 4
for it in items:
    iv = it["intervals"]
    if any(s - 0.05 <= t <= e + 0.05 for s, e in iv for t in run["times"]):
        continue
    dist = lambda t: min(max(s - t, t - e, 0) for s, e in iv)
    near = sorted((dist(t), t, f) for t, f in zip(run["times"], run["files"]) if dist(t) <= pad)[:top]
    print(f"## {run['run']} | {it['id']}: {it['what']}")
    print(f"(on screen {', '.join(f'{s:.1f}-{e:.1f}s' for s, e in iv)})")
    for _, t, f in sorted(near, key=lambda x: x[1]):
        print(f"- t={t:.1f}s: {f}")
    if not near:
        print(f"- no kept frame within {pad:.0f} s")
    print()
