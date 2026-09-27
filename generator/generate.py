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
import hashlib
import hmac
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm  # noqa: E402
from mechanisms import ALPHA, BY_KEY, MECHANISMS, TRANSFORMS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
EPOCH = dt.date(2026, 9, 27)  # puzzle #1

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
            "Roll call is always taken alphabetically. The first to answer gives up a single letter; each one after gives up exactly one more than whoever came before, and keeps only the last one given.",
            "Stand {crew} in a line, A to Z. Each steps forward one pace further than the last, and each has something written on the ground in front of them.",
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
            "File the reports the way any archivist would: by their headings, A to Z. The first report surrenders its first letter, the second its second, and so on down the drawer.",
            "Shelve everything by title. Then walk down the shelf, reaching one step further into each report than the last.",
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
            "Every transmission that reached {place} arrived with exactly one corrupted character. Repair each one to find its true answer. But don't throw the damage away: in order, the damage is the message.",
            "Nothing survives the journey intact. Each report picked up one mutation on the way; the mutations, read in order, are the only part that wasn't an accident.",
        ],
        "explain": "Each feeder decodes to its answer with a single wrong letter. Those substituted letters, in puzzle order, spell the final answer.",
        "body": [],
    }


def meta_logbook(final, pool, rng):
    """5-6 feeders; each final letter is (feeder #, letter #), disguised as a log."""
    for _ in range(300):
        k = rng.choice([5, 6])
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
        ("Day {i}, {j} bells", "The watch-keeper wrote nothing down but the day and how many bells had rung. Days are counted from the first report on this page."),
        ("Ch. {i} v. {j}", "A well-thumbed book of scripture, and a list of verses someone underlined. Its chapters are the reports on this page."),
        ("Platform {i}, car {j}", "The porter's notes list where each passenger boarded. The platforms are numbered as the reports on this page are."),
        ("Row {i}, seat {j}", "Tonight's seating chart. Each row is one of the reports on this page, and every seat is one letter wide."),
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
            "Each report was signed with nothing but an initial. The last lock {at} takes all of the signatures at once, in order, the way Blaise would have wanted.",
            "Nobody {at} signs their full name. Put the initials together and turn the wheel.",
        ],
        "explain": "The ciphertext is Vigenère-encrypted with the first letters of the feeder answers (in puzzle order) as the key.",
        "body": [{"type": "mono", "text": ct, "big": True}],
    }


METAS = [meta_diagonal, meta_title_diagonal, meta_mutation, meta_logbook, meta_initials]


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


def assign_mechanisms(feeders, rng):
    """Give each feeder a distinct mechanism (plus an optional transform layer)."""
    mechs = list(MECHANISMS)
    for _ in range(200):
        rng.shuffle(mechs)
        used, plan, ok = set(), [], True
        for fd in feeders:
            src = fd.get("encode", fd["answer"])
            choice = None
            for m in mechs:
                if m.key in used:
                    continue
                tkey = None
                if m.allow_transform and rng.random() < 0.4:
                    tkey = rng.choice(sorted(TRANSFORMS))
                enc = TRANSFORMS[tkey]["fn"](src) if tkey else src
                if m.can(enc):
                    choice = (m, tkey, enc)
                    break
                if tkey and m.can(src):
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


def build(secret, date):
    theme, final, number = pick_theme_and_final(secret, date)
    rng = random.Random(seed_for(secret, date))
    pool = [w for w in theme["feeders"] if w != final and final not in w and w not in final]
    metas = list(METAS)
    rng.shuffle(metas)
    meta = None
    for fn in metas:
        meta = fn(final, pool, rng)
        if meta:
            break
    if not meta:
        raise RuntimeError("no meta fits %s" % final)

    feeders = meta["feeders"]
    titles = rng.sample(theme["titles"], len(feeders))
    if meta.get("title_order"):
        titles.sort(key=lambda t: t.upper())  # feeder k gets the k-th title alphabetically
    if meta["type"] in ("diagonal", "title_diagonal"):
        order = list(range(len(feeders)))
        rng.shuffle(order)  # the meta itself imposes the order, so hide it
        feeders = [feeders[i] for i in order]
        titles = [titles[i] for i in order]
    plan = assign_mechanisms(feeders, rng)
    used_words = {fd["answer"] for fd in feeders} | {final}
    carrier = [w for w in theme["feeders"] if w not in used_words]

    puzzles, solutions = [], []
    for i, (fd, (mech, tkey, enc), title) in enumerate(zip(feeders, plan, titles)):
        ctx = {"title": title, "glyphs": theme["glyphs"], "carrier": carrier}
        blocks = mech.encode(enc, rng, ctx)
        flavor = fmt(rng.choice(mech.flavors), theme)
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
            partials[answer_hash(date, enc)] = "You've decoded it, but it's not finished. One more layer."
        if src != fd["answer"]:
            partials[answer_hash(date, src)] = "So close. Exactly one thing is wrong here. Fix it (and remember what you fixed)."

        puzzles.append({
            "id": i + 1,
            "title": title,
            "flavor": flavor,
            "blocks": blocks,
            "hash": answer_hash(date, fd["answer"]),
            "partials": partials,
            "hint": mech.hint + ((" Then undo: " + TRANSFORMS[tkey]["name"] + ".") if tkey else ""),
        })
        solutions.append({
            "id": i + 1, "title": title, "answer": fd["answer"], "mechanism": mech.name,
            "transform": TRANSFORMS[tkey]["name"] if tkey else None,
            "encoded": enc, "mutated": fd.get("encode"),
        })

    meta["titles"] = titles
    verify_meta(meta, [fd["answer"] for fd in feeders], [fd.get("encode") for fd in feeders], final)

    puzzle = {
        "date": date,
        "number": number,
        "round": theme["name"],
        "intro": theme["intro"],
        "puzzles": puzzles,
        "meta": {
            "title": "Meta: " + theme["name"],
            "flavor": fmt(rng.choice(meta["flavor"]), theme),
            "blocks": meta["body"],
            "length": len(final),
            "hash": answer_hash(date, final),
        },
    }
    solution = {
        "date": date, "number": number, "final": final, "metaType": meta["type"],
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


def seal(secret, date, solution):
    """Store a solution encrypted with a key derived from PUZZLE_SECRET, so it can be
    published tomorrow even if the generator code changes in between."""
    raw = json.dumps(solution, ensure_ascii=False).encode()
    data = bytes(a ^ b for a, b in zip(raw, _keystream(secret, date, len(raw))))
    mac = hmac.new(secret.encode(), b"mac|" + data, hashlib.sha256).hexdigest()
    write_json(os.path.join(SEALED, date + ".json"), {"data": data.hex(), "mac": mac})


def unseal(secret, date):
    path = os.path.join(SEALED, date + ".json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        box = json.load(f)
    data = bytes.fromhex(box["data"])
    if not hmac.compare_digest(box["mac"], hmac.new(secret.encode(), b"mac|" + data, hashlib.sha256).hexdigest()):
        return None
    return json.loads(bytes(a ^ b for a, b in zip(data, _keystream(secret, date, len(data)))).decode())


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
    pdir, sdir = os.path.join(DOCS, "puzzles"), os.path.join(DOCS, "solutions")
    for k in range(args.days - 1, -1, -1):
        d = end - dt.timedelta(days=k)
        if d < EPOCH:
            continue
        ds = d.isoformat()
        path = os.path.join(pdir, ds + ".json")
        if os.path.exists(path) and not args.force:
            continue
        puzzle, solution = build(secret, ds)
        if not args.no_llm:
            theme = next(t for t in THEMES if t["name"] == puzzle["round"])
            llm.polish(puzzle, solution, theme)
        write_json(path, puzzle)
        seal(secret, ds, solution)
        print("wrote", path, "-", puzzle["round"])

    # Index + solutions for every puzzle older than the newest one.
    dates = sorted(f[:-5] for f in os.listdir(pdir) if f.endswith(".json") and f[0].isdigit())
    index = []
    for ds in dates:
        with open(os.path.join(pdir, ds + ".json")) as f:
            p = json.load(f)
        index.append({"date": ds, "number": p["number"], "round": p["round"]})
        spath = os.path.join(sdir, ds + ".json")
        if os.path.exists(spath):
            continue
        sol = unseal(secret, ds)
        if sol is None:
            _, sol = build(secret, ds)
            if answer_hash(ds, sol["final"]) != p["meta"]["hash"]:
                print("no solution for %s: not sealed, and the generator changed since it was published" % ds, file=sys.stderr)
                continue
            seal(secret, ds, sol)
            print("sealed", ds)
        if ds < dates[-1]:
            write_json(spath, sol)
            print("wrote", spath)
    write_json(os.path.join(pdir, "index.json"), {"latest": dates[-1], "puzzles": index})


if __name__ == "__main__":
    main()
