#!/usr/bin/env python3
"""Build a couple of years of puzzles in memory; every build self-verifies."""
import collections, datetime as dt, re, sys
from generate import build, EPOCH, LEVELS

STOP = set("a an and the of to in on is it its it's as at be by or if for from with this that these those you your "
           "what which each every one two any all are was were has have had not no but so then than there here into "
           "out up down only once more just some something".split())


def words(text):
    return {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}


def echoes(flavor, hint):
    """A hint that mostly repeats its flavour adds nothing: the ladder must climb."""
    h = words(hint)
    return len(h) >= 3 and len(h & words(flavor)) / len(h) >= 0.6


counts, mechs, ladder = collections.Counter(), collections.Counter(), collections.Counter()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 730
for k in range(n):
    d = (EPOCH + dt.timedelta(days=k)).isoformat()
    for secret in ("dev-secret", "another-secret"):
        for level in LEVELS:
            p, s = build(secret, d, level=level)
            assert p["meta"]["hints"] and all(q["hints"] for q in p["puzzles"])
            if level == "easy":  # method first, a worked start last
                assert all(len(q["hints"]) >= 2 and q["hints"][-1].startswith("To check") for q in p["puzzles"])
                assert p["meta"]["hints"][-1].startswith("To check")
            for q in p["puzzles"]:
                if echoes(q["flavor"], q["hints"][0]):
                    ladder[(level, q["hints"][0][:60], q["flavor"][:60])] += 1
            if echoes(p["meta"]["flavor"], p["meta"]["hints"][0]):
                ladder[(level, p["meta"]["hints"][0][:60], p["meta"]["flavor"][:60])] += 1
            counts[(level, s["metaType"])] += 1
            for q in s["puzzles"]:
                mechs[q["mechanism"]] += 1
for (level, hint, flavor), c in sorted(ladder.items()):
    print("first hint repeats its flavour (%s, x%d): %r <- %r" % (level, c, hint, flavor))
assert not ladder, "%d hint/flavour pairs don't climb" % len(ladder)
print("ok:", 2 * n * len(LEVELS), "rounds (every level, two secrets)")
print(dict(sorted(counts.items())))
print(dict(mechs))
