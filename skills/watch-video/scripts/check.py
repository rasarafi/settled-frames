#!/usr/bin/env python3
"""Verify captions cover every frame with the right image file. Usage: check.py <out_dir>"""
import json, os, re, sys

out = sys.argv[1]
m = json.load(open(os.path.join(out, "manifest.json")))
expect = {f["id"]: f["file"] for f in m["frames"]}
got, files = {}, {}
for b in range(1, m["batches"] + 1):
    p = os.path.join(out, f"captions{b}.md")
    if not os.path.exists(p):
        print(f"MISSING captions{b}.md -> re-run batch{b}")
        continue
    cur = None
    for line in open(p):
        h = re.match(r"###\s+(F\d{4})", line)
        if h:
            cur = h.group(1)
            got[cur] = b
        f = re.search(r"File:\s*(f_\d+\.jpg)", line)
        if f and cur:
            files[cur] = f.group(1)
missing = [i for i in expect if i not in got]
wrong = [i for i in got if i in expect and files.get(i) and files[i] != expect[i]]
nofile = [i for i in got if i in expect and i not in files]
print(f"frames {len(expect)}, captioned {len([i for i in got if i in expect])}, "
      f"missing {len(missing)}, file mismatch {len(wrong)}, no File line {len(nofile)}")
for i in missing[:20]:
    print(f"  missing {i} ({expect[i]})")
for i in wrong[:20]:
    print(f"  mismatch {i}: caption says {files[i]}, manifest {expect[i]}")
sys.exit(1 if missing or wrong else 0)
