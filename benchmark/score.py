#!/usr/bin/env python3
"""Score frame selection: which checklist items does each tool's kept-frame list cover?

An item is a thing shown on screen, with the time interval(s) it is fully visible.
A run covers an item if it kept at least one frame whose timestamp falls inside an interval.
No LLM is involved, so anyone can rerun this.

Usage: score.py <items.json> <times-dir> [--video v1]
  items.json : [{"id": "V1-01", "what": "...", "kind": "persistent|transient", "intervals": [[s, e], ...]}]
  times-dir  : one <run>.json per run: {"tool": "...", "config": "...", "times": [sec, ...], "secs": wall}
"""
import json, os, sys

SLACK = 0.05  # seconds; frame timestamps are sample times, intervals are state spans


def covered(item, times):
    return any(s - SLACK <= t <= e + SLACK for s, e in item["intervals"] for t in times)


def main():
    items = json.load(open(sys.argv[1]))
    tdir = sys.argv[2]
    prefix = sys.argv[sys.argv.index("--video") + 1] + "-" if "--video" in sys.argv else ""
    runs = sorted(f for f in os.listdir(tdir) if f.endswith(".json") and f.startswith(prefix) and not f.endswith("results.json"))
    n = len(items)
    nt = sum(1 for i in items if i["kind"] == "transient")
    print(f"{n} items ({nt} transient, {n - nt} persistent)\n")
    print(f"| run | frames kept | covered | transient | persistent | missed |")
    print(f"|---|---|---|---|---|---|")
    out = {}
    for r in runs:
        d = json.load(open(os.path.join(tdir, r)))
        hit = [i["id"] for i in items if covered(i, d["times"])]
        miss = [i["id"] for i in items if i["id"] not in hit]
        ht = sum(1 for i in items if i["kind"] == "transient" and i["id"] in hit)
        name = r[:-5]
        out[name] = {"frames": len(d["times"]), "covered": len(hit), "missed": miss}
        print(f"| {name} | {len(d['times'])} | {len(hit)}/{n} | {ht}/{nt} | {len(hit) - ht}/{n - nt} | {', '.join(miss) or '-'} |")
    json.dump(out, open(os.path.join(tdir, f"{prefix}results.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
