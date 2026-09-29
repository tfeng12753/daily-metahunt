#!/usr/bin/env python3
"""Daily metapuzzle generator.

    python generator/generate.py                 # today's (UTC) puzzle
    python generator/generate.py --date 2026-10-01
    python generator/generate.py --days 30       # today plus 29 days back

Puzzles are deterministic in (PUZZLE_SECRET, date). Set PUZZLE_SECRET as a
GitHub Actions secret so nobody can regenerate tomorrow's answer from the
public source. Solutions are only written for dates strictly before the
newest generated puzzle.
"""
import argparse
import datetime as dt
import functools
import hashlib
import hmac
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hints  # noqa: E402
import llm  # noqa: E402
from hunt_mechanisms import MECHANISMS  # noqa: E402
from mechanisms import ALPHA, TRANSFORMS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
EPOCH = dt.date(2026, 9, 27)  # puzzle #1
LEVELS = ("hard", "medium", "easy")
# Chance that a feeder gets a hidden second layer (Atbash, reversal, ROT13).
TRANSFORM_RATE = {"hard": 0.4, "medium": 0.15, "easy": 0.0}

with open(os.path.join(ROOT, "generator", "themes.json")) as f:
    THEMES = json.load(f)


def answer_hash(date, word):
    return hashlib.sha256(("metahunt|%s|%s" % (date, word)).encode()).hexdigest()


def seed_for(secret, date, salt=""):
    d = hmac.new(secret.encode(), (date + salt).encode(), hashlib.sha256).digest()
    return int.from_bytes(d[:8], "big")


def fmt(text, theme):
    return (text.replace("{place}", theme["place"])
                .replace("{at}", theme["at"])
                .replace("{crew}", theme["crew"])
                .replace("{Crew}", theme["crew"][0].upper() + theme["crew"][1:]))


# --------------------------------------------------------------------------
# Meta mechanisms: choose feeder answers so they resolve to the final word
# --------------------------------------------------------------------------

def meta_diagonal(final, pool, rng):
    """Sorted alphabetically, the k-th feeder's k-th letter spells the final."""
    n = len(final)
    if not 5 <= n <= 8:
        return None

    def dfs(k, prev, chosen):
        if k == n:
            return chosen
        cands = [w for w in pool if len(w) > k and w[k] == final[k] and w > prev and w not in chosen]
        rng.shuffle(cands)
        for w in cands[:6]:
            r = dfs(k + 1, w, chosen + [w])
            if r:
                return r
        return None

    words = dfs(0, "", [])
    if not words:
        return None
    feeders = [{"answer": w} for w in words]
    return {
        "type": "diagonal",
        "feeders": feeders,
        "flavor": [
            "Roll call is taken alphabetically, and each answer goes one step further than the last.",
            "Stand {crew} in a line, A to Z. Then take the stairs.",
        ],
        "explain": "Sort the feeder answers alphabetically and take the k-th letter of the k-th answer (a diagonal read).",
        "body": [],
    }


def meta_title_diagonal(final, pool, rng):
    """Taken in alphabetical order of their titles, the k-th answer's k-th letter spells the final."""
    n = len(final)
    if not 5 <= n <= 8:
        return None
    words = []
    for k, c in enumerate(final):
        cands = [w for w in pool if len(w) > k and w[k] == c and w not in words]
        if not cands:
            return None
        words.append(rng.choice(cands))
    return {
        "type": "title_diagonal",
        "feeders": [{"answer": w} for w in words],
        "flavor": [
            "File everything the way an archivist would, by its heading. Then walk down the drawer.",
            "Shelved by title, and read on the slant.",
        ],
        "explain": "Order the puzzles alphabetically by title; take the k-th letter of the k-th answer.",
        "body": [],
        "title_order": True,
    }


def meta_mutation(final, pool, rng):
    """Each feeder encodes its answer with exactly one wrong letter; the wrong letters spell the final."""
    n = len(final)
    if not 5 <= n <= 8:
        return None
    words = [w for w in pool if len(w) >= 6] or pool
    poolset = set(pool)
    used = set()
    feeders = []
    for c in final:
        opts = []
        for w in words:
            if w in used:
                continue
            for p in range(1, len(w)):  # never the first letter: keeps it recognisable
                if w[p] != c:
                    m = w[:p] + c + w[p + 1:]
                    if m not in poolset:
                        opts.append((w, m))
        if not opts:
            return None
        w, m = rng.choice(opts)
        used.add(w)
        feeders.append({"answer": w, "encode": m})
    return {
        "type": "mutation",
        "feeders": feeders,
        "flavor": [
            "Nothing reached {place} undamaged. The damage, though, was remarkably consistent.",
            "Every report is one slip away from perfect. Keep the slips.",
        ],
        "explain": "Each feeder decodes to its answer with a single wrong letter. Those substituted letters, in puzzle order, spell the final answer.",
        "body": [],
    }


def meta_fitin(final, pool, rng):
    """Answers fit a grid by length (all distinct); one shaded square per row spells the final."""
    n = len(final)
    if not 5 <= n <= 9:
        return None

    def dfs(k, lens, chosen):
        if k == n:
            return chosen
        cands = [w for w in pool if final[k] in w and len(w) not in lens and w not in chosen]
        rng.shuffle(cands)
        for w in cands[:4]:
            r = dfs(k + 1, lens | {len(w)}, chosen + [w])
            if r:
                return r
        return None

    words = dfs(0, set(), [])
    if not words:
        return None
    rows = []
    for w, c in zip(words, final):
        rows.append({"len": len(w), "shade": rng.choice([i for i, ch in enumerate(w) if ch == c])})
    return {
        "type": "fitin",
        "feeders": [{"answer": w} for w in words],
        "flavor": [
            "Everything {at} has a place, and every place is exactly the right size.",
            "Pigeonholes, each cut to fit one thing only.",
        ],
        "explain": "Each answer fits exactly one row of the grid by length; the shaded squares, top to bottom, spell the final answer.",
        "body": [{"type": "fitgrid", "rows": rows}],
        "shuffle": True,
    }


def meta_stowaway(final, pool, rng):
    """Each feeder encodes its answer with one extra letter; the extras spell the final."""
    n = len(final)
    if not 5 <= n <= 8:
        return None
    poolset = set(pool)
    used, feeders = set(), []
    for c in final:
        opts = []
        for w in pool:
            if w in used or len(w) < 5:
                continue
            for p in range(1, len(w) + 1):
                m = w[:p] + c + w[p:]
                # an insertion that duplicates a neighbour is ambiguous about where it went; that's fine,
                # the letter is the same. Just avoid landing on another real word.
                if m not in poolset:
                    opts.append((w, m))
        if not opts:
            return None
        w, m = rng.choice(opts)
        used.add(w)
        feeders.append({"answer": w, "encode": m, "extra": True})
    return {
        "type": "stowaway",
        "feeders": feeders,
        "flavor": [
            "Everything arrived a little heavier than it left.",
            "Count heads at the gangway: one too many on every boat.",
        ],
        "explain": "Each feeder decodes to its answer plus one inserted letter. The inserted letters, in puzzle order, spell the final answer.",
        "body": [],
    }


def meta_first_letters(final, pool, rng):
    """Easy: the answers' first letters, in puzzle order, spell the final."""
    n = len(final)
    if not 4 <= n <= 7:
        return None
    words = []
    for c in final:
        cands = [w for w in pool if w[0] == c and w not in words and len(w) <= 10]
        if not cands:
            return None
        words.append(rng.choice(cands))
    return {
        "type": "first_letters",
        "feeders": [{"answer": w} for w in words],
        "flavor": ["Everyone {at} introduces themselves in turn. Listen to how each of them begins."],
        "explain": "Take the first letter of each feeder answer, in puzzle order.",
        "body": [],
    }


def meta_logbook(final, pool, rng, sizes=(5, 6)):
    """5-6 feeders; each final letter is (feeder #, letter #), disguised as a log."""
    for _ in range(300):
        k = rng.choice(sizes)
        words = rng.sample(pool, k)
        picks = []
        for c in final:
            opts = [(i, j) for i, w in enumerate(words) for j, ch in enumerate(w) if ch == c]
            if not opts:
                break
            picks.append(rng.choice(opts))
        else:
            if len({i for i, _ in picks}) == k:
                break
    else:
        return None
    styles = [
        ("Day {i}, {j} bells", "The watch-keeper wrote down nothing but the day and the bell."),
        ("Ch. {i} v. {j}", "Someone underlined a few verses. This page has its own chapters."),
        ("Platform {i}, car {j}", "The porter only ever noted where each passenger boarded."),
        ("Row {i}, seat {j}", "Tonight's seating chart. Every seat is one letter wide."),
    ]
    fmt_s, flavor = rng.choice(styles)
    entries = [fmt_s.format(i=i + 1, j=j + 1) for i, j in picks]
    return {
        "type": "logbook",
        "feeders": [{"answer": w} for w in words],
        "flavor": [flavor],
        "explain": "Each entry is (puzzle number, letter number): index into that puzzle's answer.",
        "body": [{"type": "list", "items": entries, "ordered": True}],
    }


def meta_initials(final, pool, rng):
    """Final is Vigenère-encrypted; the key is the feeders' initials in order."""
    for _ in range(50):
        k = rng.choice([5, 6])
        words = rng.sample(pool, k)
        key = "".join(w[0] for w in words)
        if "A" * 2 in key or key.count("A") > 1:
            continue  # an 'A' in the key leaves letters unshifted; avoid giveaways
        ct = "".join(ALPHA[(ALPHA.index(c) + ALPHA.index(key[i % k])) % 26] for i, c in enumerate(final))
        if all(a != b for a, b in zip(ct, final)):
            break
    else:
        return None
    return {
        "type": "initials",
        "feeders": [{"answer": w} for w in words],
        "flavor": [
            "Every report is signed with a single initial. Blaise would know what to do with them.",
            "The last lock takes every signature at once.",
        ],
        "explain": "The ciphertext is Vigenère-encrypted with the first letters of the feeder answers (in puzzle order) as the key.",
        "body": [{"type": "mono", "text": ct, "big": True}],
    }


METAS = [meta_diagonal, meta_title_diagonal, meta_mutation, meta_stowaway, meta_fitin, meta_logbook, meta_initials]
MEDIUM_METAS = [meta_fitin, meta_title_diagonal, meta_diagonal, meta_stowaway, meta_logbook]
EASY_METAS = [meta_first_letters, meta_first_letters, meta_fitin, meta_title_diagonal,
              lambda final, pool, rng: meta_logbook(final, pool, rng, sizes=(4, 5))]
METAS_BY_LEVEL = {"hard": METAS, "medium": MEDIUM_METAS, "easy": EASY_METAS}


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def pick_theme_and_final(secret, date):
    day = (dt.date.fromisoformat(date) - EPOCH).days
    order_rng = random.Random(seed_for(secret, "theme-order"))
    order = list(range(len(THEMES)))
    order_rng.shuffle(order)
    theme = THEMES[order[day % len(order)]]
    cycle = day // len(order)
    finals = list(theme["finals"])
    random.Random(seed_for(secret, "finals-" + theme["id"])).shuffle(finals)
    return theme, finals[cycle % len(finals)], day + 1


def assign_mechanisms(feeders, rng, ctx, level="hard"):
    """Give each feeder a distinct mechanism (plus an optional transform layer).

    Mechanisms are drawn in a weighted random order, so word and logic
    puzzles (weight 3) turn up about three times as often as pure encodings.
    """
    allowed = [m for m in MECHANISMS if getattr(m, level)]
    rate = TRANSFORM_RATE[level]
    for _ in range(200):
        mechs = sorted(allowed, key=lambda m: rng.random() ** (1.0 / m.weight), reverse=True)
        used, plan, ok = set(), [], True
        for fd in feeders:
            src = fd.get("encode", fd["answer"])
            choice = None
            for m in mechs:
                if m.key in used:
                    continue
                tkey = None
                if m.allow_transform and rate and rng.random() < rate:
                    tkey = rng.choice(sorted(TRANSFORMS))
                enc = TRANSFORMS[tkey]["fn"](src) if tkey else src
                if m.can(enc, ctx):
                    choice = (m, tkey, enc)
                    break
                if tkey and m.can(src, ctx):
                    choice = (m, None, src)
                    break
            if not choice:
                ok = False
                break
            used.add(choice[0].key)
            plan.append(choice)
        if ok:
            return plan
    raise RuntimeError("could not assign mechanisms")


@functools.lru_cache(maxsize=64)
def _easy_final(secret, date):
    return build(secret, date, level="easy")[1]["final"]


def build(secret, date, easy=False, level=None):
    level = level or ("easy" if easy else "hard")
    easy = level == "easy"
    theme, final, number = pick_theme_and_final(secret, date)
    salt = date if level == "hard" else date + "/" + level
    rng = random.Random(seed_for(secret, date, "" if level == "hard" else "|" + level))
    if easy:
        # Same theme, a different (shorter) final word; fall back through the
        # theme's other finals until an easy meta fits.
        others = sorted((f for f in theme["finals"] if f != final), key=lambda f: (len(f), f))
        short = [f for f in others if len(f) <= 7]
        rng.shuffle(short)
        candidates = short + [f for f in others if f not in short]
    elif level == "medium":
        # A third final word: not the hard one, and not the easy one.
        easy_final = _easy_final(secret, date)
        others = sorted(f for f in theme["finals"] if f not in (final, easy_final))
        rng.shuffle(others)
        candidates = others + [easy_final]
    else:
        candidates = [final]
    meta = None
    for final in candidates:
        pool = [w for w in theme["feeders"] if w != final and final not in w and w not in final]
        metas = list(METAS_BY_LEVEL[level])
        rng.shuffle(metas)
        for fn in metas:
            meta = fn(final, pool, rng)
            if meta:
                break
        if meta:
            break
    if not meta:
        raise RuntimeError("no meta fits %s" % final)

    feeders = meta["feeders"]
    titles = rng.sample(theme["titles"], len(feeders))
    if meta.get("title_order"):
        titles.sort(key=lambda t: t.upper())  # feeder k gets the k-th title alphabetically
    if meta["type"] in ("diagonal", "title_diagonal") or meta.get("shuffle"):
        order = list(range(len(feeders)))
        rng.shuffle(order)  # the meta itself imposes the order, so hide it
        feeders = [feeders[i] for i in order]
        titles = [titles[i] for i in order]
    used_words = {fd["answer"] for fd in feeders} | {final}
    carrier = [w for w in theme["feeders"] if w not in used_words]
    base_ctx = {"glyphs": theme["glyphs"], "carrier": carrier, "intro": theme["intro"],
                "all_words": theme["feeders"] + theme["finals"], "easy": easy, "level": level,
                "place": theme["place"]}
    plan = assign_mechanisms(feeders, rng, base_ctx, level)

    puzzles, solutions = [], []
    for i, (fd, (mech, tkey, enc), title) in enumerate(zip(feeders, plan, titles)):
        ctx = dict(base_ctx, title=title)
        blocks = mech.encode(enc, rng, ctx)
        # Easy and medium get the more direct flavour; hard keeps the oblique one.
        direct = level != "hard" and mech.easy_flavors
        pool_flavors = ctx.get("_flavors") or (mech.easy_flavors if direct else mech.flavors)
        flavor = fmt(rng.choice(pool_flavors), theme).replace("{n}", ctx.get("_flavor_n", ""))
        method = ctx.get("_hint", mech.hint)
        technique = ctx.get("_name", mech.name)
        if tkey:
            flavor += " " + rng.choice(TRANSFORMS[tkey]["hints"])

        # Self-check: the encoding must decode back to exactly what we meant.
        dctx = dict(ctx, expect=enc)
        got = mech.decode(blocks, dctx)
        if got != enc:
            raise AssertionError("%s failed to round-trip %r -> %r" % (mech.key, enc, got))

        partials = {}
        src = fd.get("encode", fd["answer"])
        if tkey and enc != src:
            partials[answer_hash(salt, enc)] = "You've decoded it, but it's not finished. One more layer."
        if src != fd["answer"] and fd.get("extra"):
            partials[answer_hash(salt, src)] = "Nearly. There's a stowaway aboard: one letter too many. Put it ashore, but remember who it was."
        elif src != fd["answer"]:
            partials[answer_hash(salt, src)] = "So close. Exactly one thing is wrong here. Fix it (and remember what you fixed)."

        puzzles.append({
            "id": i + 1,
            "title": title,
            "flavor": flavor,
            "blocks": blocks,
            "hash": answer_hash(salt, fd["answer"]),
            "partials": partials,
            "hints": hints.feeder_hints(level, mech.key, method, TRANSFORMS[tkey]["name"] if tkey else None,
                                        ctx.get("_extra_hint")),
        })
        if easy:
            puzzles[-1]["technique"] = technique
        if level != "hard":
            puzzles[-1]["length"] = len(fd["answer"])
        solutions.append({
            "id": i + 1, "title": title, "answer": fd["answer"], "mechanism": technique,
            "transform": TRANSFORMS[tkey]["name"] if tkey else None,
            "encoded": enc, "mutated": fd.get("encode"),
        })

    meta["titles"] = titles
    verify_meta(meta, [fd["answer"] for fd in feeders], [fd.get("encode") for fd in feeders], final)

    puzzle = {
        "date": date,
        "difficulty": level,
        "salt": salt,
        "number": number,
        "round": theme["name"],
        "intro": theme["intro"],
        "echo": theme.get("echoes", {}).get(final),
        "puzzles": puzzles,
        "meta": {
            "title": "Meta: " + theme["name"],
            "flavor": fmt(rng.choice(meta["flavor"]), theme),
            "blocks": meta["body"],
            "length": len(final),
            "hash": answer_hash(salt, final),
            # The explanation is no longer printed up front, even on easy: it's the last hint.
            "hints": hints.meta_hints(level, meta["type"], meta["explain"]),
        },
    }
    solution = {
        "date": date, "number": number, "difficulty": level, "final": final, "metaType": meta["type"],
        "explain": meta["explain"], "puzzles": solutions,
    }
    return puzzle, solution


def verify_meta(meta, answers, mutated, final):
    t = meta["type"]
    if t == "diagonal":
        s = sorted(answers)
        got = "".join(w[k] for k, w in enumerate(s))
    elif t == "title_diagonal":
        s = [a for _, a in sorted(zip([q.upper() for q in meta["titles"]], answers))]
        got = "".join(w[k] for k, w in enumerate(s))
    elif t == "mutation":
        got = ""
        for a, m in zip(answers, mutated):
            diff = [y for x, y in zip(a, m) if x != y]
            assert len(diff) == 1
            got += diff[0]
    elif t == "stowaway":
        got = ""
        for a, m in zip(answers, mutated):
            extras = {m[p] for p in range(len(m)) if m[:p] + m[p + 1:] == a}
            assert len(extras) == 1, (a, m)
            got += extras.pop()
    elif t == "fitin":
        got = ""
        for row in meta["body"][0]["rows"]:
            fits = [a for a in answers if len(a) == row["len"]]
            assert len(fits) == 1
            got += fits[0][row["shade"]]
    elif t == "first_letters":
        got = "".join(w[0] for w in answers)
    elif t == "logbook":
        got = ""
        for e in meta["body"][0]["items"]:
            nums = [int("".join(ch for ch in part if ch.isdigit())) for part in e.split(",")] \
                if "," in e else [int(x) for x in e.replace("Ch.", "").replace("v.", "").split()]
            got += answers[nums[0] - 1][nums[1] - 1]
    elif t == "initials":
        key = "".join(w[0] for w in answers)
        ct = meta["body"][0]["text"]
        got = "".join(ALPHA[(ALPHA.index(c) - ALPHA.index(key[i % len(key)])) % 26] for i, c in enumerate(ct))
    else:
        raise AssertionError(t)
    if got != final:
        raise AssertionError("meta %s resolves to %s, expected %s" % (t, got, final))


SEALED = os.path.join(ROOT, "generator", "sealed")


def _keystream(secret, date, n):
    out = b""
    ctr = 0
    while len(out) < n:
        out += hmac.new(secret.encode(), ("seal|%s|%d" % (date, ctr)).encode(), hashlib.sha256).digest()
        ctr += 1
    return out[:n]


def _sub(level):
    return () if level == "hard" else (level,)


def _sealed_path(date, level):
    return os.path.join(SEALED, *_sub(level), date + ".json")


def seal(secret, date, solution, level="hard"):
    """Store a solution encrypted with a key derived from PUZZLE_SECRET, so it can be
    published tomorrow even if the generator code changes in between."""
    key = date if level == "hard" else date + "/" + level
    raw = json.dumps(solution, ensure_ascii=False).encode()
    data = bytes(a ^ b for a, b in zip(raw, _keystream(secret, key, len(raw))))
    mac = hmac.new(secret.encode(), b"mac|" + data, hashlib.sha256).hexdigest()
    write_json(_sealed_path(date, level), {"data": data.hex(), "mac": mac})


def unseal(secret, date, level="hard"):
    key = date if level == "hard" else date + "/" + level
    path = _sealed_path(date, level)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        box = json.load(f)
    data = bytes.fromhex(box["data"])
    if not hmac.compare_digest(box["mac"], hmac.new(secret.encode(), b"mac|" + data, hashlib.sha256).hexdigest()):
        return None
    return json.loads(bytes(a ^ b for a, b in zip(data, _keystream(secret, key, len(data)))).decode())


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--days", type=int, default=1, help="also generate this many days ending at --date")
    ap.add_argument("--force", action="store_true", help="overwrite existing puzzle files")
    ap.add_argument("--no-llm", action="store_true", help="skip the K2 Horizon flavour polish even if IFM_API_KEY is set")
    args = ap.parse_args()

    secret = os.environ.get("PUZZLE_SECRET")
    if not secret:
        print("warning: PUZZLE_SECRET not set; using an insecure dev secret", file=sys.stderr)
        secret = "dev-secret"

    end = dt.date.fromisoformat(args.date)
    for level in LEVELS:
        pdir = os.path.join(DOCS, "puzzles", *_sub(level))
        for k in range(args.days - 1, -1, -1):
            d = end - dt.timedelta(days=k)
            if d < EPOCH:
                continue
            ds = d.isoformat()
            path = os.path.join(pdir, ds + ".json")
            if os.path.exists(path) and not args.force:
                continue
            puzzle, solution = build(secret, ds, level=level)
            if not args.no_llm:
                theme = next(t for t in THEMES if t["name"] == puzzle["round"])
                llm.polish(puzzle, solution, theme, easy=level == "easy")
            write_json(path, puzzle)
            seal(secret, ds, solution, level)
            print("wrote", path, "-", puzzle["round"])
    publish_solutions(secret)


def publish_solutions(secret):
    """Rebuild the index and publish every solution older than the newest round."""
    pdir = os.path.join(DOCS, "puzzles")
    dates = sorted(f[:-5] for f in os.listdir(pdir) if f.endswith(".json") and f[0].isdigit())
    index = []
    for ds in dates:
        with open(os.path.join(pdir, ds + ".json")) as f:
            p = json.load(f)
        entry = {"date": ds, "number": p["number"], "round": p["round"], "count": {"hard": len(p["puzzles"])}}
        levels = ["hard"]
        for level in ("medium", "easy"):
            lpath = os.path.join(pdir, level, ds + ".json")
            entry[level] = os.path.exists(lpath)
            if entry[level]:
                levels.append(level)
                with open(lpath) as f:
                    entry["count"][level] = len(json.load(f)["puzzles"])
        index.append(entry)
        for level in levels:
            sub = _sub(level)
            spath = os.path.join(DOCS, "solutions", *sub, ds + ".json")
            if os.path.exists(spath):
                continue
            sol = unseal(secret, ds, level)
            if sol is None:
                with open(os.path.join(pdir, *sub, ds + ".json")) as f:
                    published = json.load(f)
                _, sol = build(secret, ds, level=level)
                if answer_hash(published.get("salt", ds), sol["final"]) != published["meta"]["hash"]:
                    print("no solution for %s (%s): not sealed, and the generator changed since it was published"
                          % (ds, level), file=sys.stderr)
                    continue
                seal(secret, ds, sol, level)
                print("sealed", ds, level)
            if ds < dates[-1]:
                write_json(spath, sol)
                print("wrote", spath)
    write_json(os.path.join(pdir, "index.json"), {"latest": dates[-1], "puzzles": index})


if __name__ == "__main__":
    main()
