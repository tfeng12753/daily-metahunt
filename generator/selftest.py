#!/usr/bin/env python3
"""Build a couple of years of puzzles in memory; every build self-verifies."""
import collections, datetime as dt, sys
from generate import build, EPOCH

counts, mechs = collections.Counter(), collections.Counter()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 730
for k in range(n):
    d = (EPOCH + dt.timedelta(days=k)).isoformat()
    for secret in ("dev-secret", "another-secret"):
        p, s = build(secret, d)
        counts[s["metaType"]] += 1
        for q in s["puzzles"]:
            mechs[q["mechanism"]] += 1
print("ok:", 2 * n, "puzzles")
print(dict(counts))
print(dict(mechs))
