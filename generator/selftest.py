#!/usr/bin/env python3
"""Build a couple of years of puzzles in memory; every build self-verifies."""
import collections, copy, datetime as dt, json, os, re, sys
import generate
from generate import build, EPOCH, LEVELS

generate.HASH_ITER = 1  # the real count only slows the self-test down; the scheme is checked below

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


# ---- answer hashes: old rounds still check with the scheme they were published with
docs = os.path.join(generate.DOCS)
with open(os.path.join(docs, "puzzles", "2026-09-27.json")) as f:
    old = json.load(f)
with open(os.path.join(docs, "solutions", "2026-09-27.json")) as f:
    assert generate.round_hash(old, json.load(f)["final"]) == old["meta"]["hash"], "v1 hashes broke"
p, s = build("dev-secret", "2026-10-01")
assert p["hashv"] == 2 and generate.round_hash(p, s["final"]) == p["meta"]["hash"]

# ---- the private bank: schedule, reuse without repeating answers, fall back when it runs dry
import bank  # noqa: E402
src = copy.deepcopy(next(t for t in generate.THEMES if t["id"] == "deep-sea"))
theme = dict(src, id="trial-sea", name="Trial Sea", max_uses=2,
             titles=[t for t in src["titles"] if not any(f in re.sub(r"[^A-Z]", "", t.upper()) for f in src["finals"])],
             cluephrases=["THE DIVERS SURFACED HOLDING A SLATE THAT SAID {W}",
                          "SCRAWLED ON THE INSIDE OF THE PORTHOLE WAS {W}"],
             flavors={"cryptogram": ["Salt water got into the type case."]})
assert not bank.problems(theme), bank.problems(theme)
assert bank.problems(dict(theme, intro=theme["intro"] + " " + theme["finals"][0])), "a printed final went unnoticed"
sealed = {}
generate.unseal = lambda secret, date, level="hard": sealed.get((date, level))
generate.BANK.update({"themes": {"t1": theme}, "schedule": {}})
first, second, third = "2031-01-01", "2031-01-20", "2031-02-20"
used = []
for d in (first, second):
    generate.plan_day("dev-secret", d, save=False)
    assert generate.BANK["schedule"][d]["theme"] == "t1"
    words = set()
    for level in LEVELS:
        p, s = build("dev-secret", d, level=level)
        assert p["round"] == "Trial Sea"
        sealed[(d, level)] = s
        words |= {s["final"]} | {q["answer"] for q in s["puzzles"]}
    used.append(words)
assert not used[0] & used[1], "a reused bank theme repeated answers: %s" % (used[0] & used[1])
generate.plan_day("dev-secret", third, save=False)
assert third not in generate.BANK["schedule"], "max_uses ignored"
assert build("dev-secret", third)[0]["round"] != "Trial Sea"
print("ok: hashes (v1 and v2) and the bank's schedule")
