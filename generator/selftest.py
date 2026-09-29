#!/usr/bin/env python3
"""Build a couple of years of puzzles in memory; every build self-verifies."""
import collections, datetime as dt, sys
from generate import build, EPOCH, LEVELS

counts, mechs = collections.Counter(), collections.Counter()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 730
for k in range(n):
    d = (EPOCH + dt.timedelta(days=k)).isoformat()
    for secret in ("dev-secret", "another-secret"):
        for level in LEVELS:
            p, s = build(secret, d, level=level)
            assert p["meta"]["hints"] and all(q["hints"] for q in p["puzzles"])
            counts[(level, s["metaType"])] += 1
            for q in s["puzzles"]:
                mechs[q["mechanism"]] += 1
print("ok:", 2 * n * len(LEVELS), "rounds (every level, two secrets)")
print(dict(sorted(counts.items())))
print(dict(mechs))
