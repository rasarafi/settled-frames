#!/usr/bin/env python3
"""Final table: the time-based score, corrected by the visual check of every claimed miss.

score.py marks an item missed when no kept frame falls inside the item's answer-key window. Those
windows are conservative, so each claimed miss was then checked by opening the tool's nearest kept
frames (miss_candidates.py lists them). verdicts.md holds one line per check:
  <run> | <item id> | CONFIRMED MISS | VISIBLE | VISIBLE-UNREADABLE | <frame time> | <evidence>
A VISIBLE verdict turns the miss into a hit. Everything else stays a miss.

Usage: verified.py <benchmark-dir> <times-dir>
"""
import json, os, sys

bench, tdir = sys.argv[1:3]
verdict = {}
for line in open(os.path.join(bench, "verdicts.md")):
    p = [x.strip() for x in line.split("|")]
    if len(p) >= 3 and p[0][:1] == "v" and "-" in p[0]:
        verdict[(p[0], p[1])] = p[2]

LABEL = {"settled-default": "settled-frames (default)", "settled-nofine": "settled-frames, original rule (--fine 0)",
         "settled-ignore": "settled-frames with --ignore on the webcam corner",
         "crv-default": "crv, default", "crv-tuned": "crv, tuned", "crv-max": "crv, sensitive", "crv-fine": "crv, finest",
         "cv-default": "claude-video, default", "cv-tuned": "claude-video, token-burner 1920px",
         "cv-2fps": "claude-video, token-burner 1920px at 2 fps"}
ORDER = list(LABEL)
out = {}
for k in ("v1", "v2", "v3"):
    items = json.load(open(os.path.join(bench, f"{k}-items.json")))
    n = len(items)
    nt = sum(1 for i in items if i["kind"] == "transient")
    print(f"\n### {k}: {n} items ({nt} brief)\n")
    print("| tool and setting | frames kept | items shown | brief items | still missed |")
    print("|---|---|---|---|---|")
    for cfg in ORDER:
        path = os.path.join(tdir, f"{k}-{cfg}.json")
        if not os.path.exists(path):
            continue
        run = json.load(open(path))
        hit, miss, unchecked = [], [], []
        for it in items:
            if any(s - 0.05 <= t <= e + 0.05 for s, e in it["intervals"] for t in run["times"]):
                hit.append(it)
            else:
                v = verdict.get((f"{k}-{cfg}", it["id"]))
                if v == "VISIBLE":
                    hit.append(it)
                else:
                    miss.append(it["id"])
                    if v is None:
                        unchecked.append(it["id"])
        ht = sum(1 for i in hit if i["kind"] == "transient")
        out[f"{k}-{cfg}"] = {"frames": len(run["times"]), "shown": len(hit), "of": n, "transient": ht,
                             "transient_of": nt, "missed": miss, "unchecked": unchecked, "secs": run["secs"]}
        print(f"| {LABEL[cfg]} | {len(run['times'])} | {len(hit)}/{n} | {ht}/{nt} | "
              f"{', '.join(m.split('-')[1] for m in miss) or '-'} |")
json.dump(out, open(os.path.join(bench, "results.json"), "w"), indent=1)
left = {r: v["unchecked"] for r, v in out.items() if v["unchecked"]}
if left:
    print("\nWARNING: claimed misses with no visual check yet:", left)
