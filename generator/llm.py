"""Optional flavour-text polish via IFM's K2 Horizon (OpenAI-compatible API).

The model only ever rewrites prose: the round intro, each feeder's flavour
line and the meta's flavour. Puzzle data, answers and hashes are untouched.
Every rewrite is validated (no answers, no intermediate strings, no naming
the mechanism outright, sane length) and anything that fails keeps the
template text, so a bad or missing API response can never break a round.

Env:
    IFM_API_KEY   required to enable this step
    IFM_MODEL     model id; if unset, the first K2 Horizon model from /models
    IFM_BASE_URL  default https://api.ifm.ai/v1
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("IFM_BASE_URL", "https://api.ifm.ai/v1").rstrip("/")

# Naming the method outright turns a hunt puzzle into an exercise.
BANNED = ["morse", "semaphore", "braille", "vigenere", "vigenère", "atbash", "nato",
          "phonetic alphabet", "ascii", "hexadecimal", "pigpen", "baconian", "dtmf",
          "tap code", "rot13", "rot-13", "caesar", "qwerty", "amino acid", "codon",
          "atomic number", "periodic table", "roman numeral", "prime number",
          "multi-tap", "multitap", "binary", "cipher", "nonogram", "picross",
          "paint by numbers", "word search", "wordsearch", "rail fence", "railfence",
          "cryptogram", "substitution", "book cipher", "signal flag", "semaphore flag",
          "knight's tour", "radix", "base two", "base 2", "sudoku", "drop quote",
          "dropquote", "anagram", "shredded sentence"]

SYSTEM = """You write flavour text for a very hard puzzle hunt, in the style of the MIT Mystery Hunt and tech-company hunts.
Flavour text is an oblique, atmospheric nudge: it must preserve every hint in the original line (a solver should be able to get the same "aha" from it), but it must never name the technique outright, never state an answer, and never give instructions.
Write in the voice of the round's story. British spelling. One to three sentences per line, at most 55 words. No emoji, no markdown, no quotation marks around the whole line.
Reply with a single JSON object and nothing else."""


def _request(path, body=None, key=None, timeout=240):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def pick_model(key):
    if os.environ.get("IFM_MODEL"):
        return os.environ["IFM_MODEL"]
    ids = [m["id"] for m in _request("/models", key=key).get("data", [])]
    horizon = [i for i in ids if "horizon" in i.lower()]
    if not horizon:
        raise RuntimeError("no K2 Horizon model in /models; set IFM_MODEL (available: %s)" % ", ".join(ids))
    # Prefer the biggest model on offer.
    size = lambda i: max([float(x) for x in re.findall(r"(\d+(?:\.\d+)?)B", i, re.I)] or [0])
    return max(horizon, key=size)


def chat(key, model, messages):
    body = {"model": model, "messages": messages, "temperature": 0.9, "max_tokens": 4000,
            "chat_template_kwargs": {"reasoning_effort": "low"}}
    try:
        resp = _request("/chat/completions", body, key)
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
        body.pop("chat_template_kwargs")  # not every deployment accepts it
        resp = _request("/chat/completions", body, key)
    return resp["choices"][0]["message"].get("content") or ""


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def ok(text, forbidden, old, easy=False):
    if not isinstance(text, str):
        return False
    t = text.strip()
    if not 20 <= len(t) <= 420 or len(t) > 3 * len(old) + 120:
        return False
    low = t.lower()
    letters = re.sub(r"[^a-z]", "", low)
    words = set(re.findall(r"[a-z]+", low))
    for w in forbidden:
        w = w.lower()
        # long answers are caught even if spaced out; short ones only as whole words
        if (len(w) >= 6 and w in letters) or w in words:
            return False
    # The easy round names each technique on the page anyway.
    return easy or not any(b in low for b in BANNED if b not in old.lower())


def polish(puzzle, solution, theme, easy=False):
    key = os.environ.get("IFM_API_KEY")
    if not key:
        return None
    try:
        model = pick_model(key)
        forbidden = {solution["final"]}
        for q in solution["puzzles"]:
            forbidden |= {q["answer"], q["encoded"]} | ({q["mutated"]} if q["mutated"] else set())

        lines = {"intro": {"original": puzzle["intro"], "note": "Round introduction: set the scene for the whole round."}}
        for p, q in zip(puzzle["puzzles"], solution["puzzles"]):
            note = "Feeder titled %r. Hidden method (never name it, only allude): %s" % (p["title"], p["hint"])
            if q["transform"]:
                note += " There is a second layer (%s) that the original also hints at; keep that hint." % q["transform"]
            if q["mechanism"].startswith("Vigen"):
                note += " The key is this puzzle's title, so the line must still point at the title/heading."
            lines["p%d" % p["id"]] = {"original": p["flavor"], "note": note}
        lines["meta"] = {"original": puzzle["meta"]["flavor"],
                         "note": "The metapuzzle. How it works (allude, never state plainly): " + solution["explain"]}

        user = ("Round: %s\nSetting: %s, %s.\n%s\nRewrite each line below. Return JSON mapping the same keys to the new text.\n\n%s"
                % (puzzle["round"], theme["place"], theme["crew"],
                   "This is the EASY round, for newcomers: the technique is shown next to each puzzle, so flavour "
                   "can be warmer and more direct. Still never state an answer.\n" if easy else
                   "This is the HARD round: make every line MORE oblique than the original. Allude; never explain, "
                   "never give instructions, never name a person or tool that gives the method away.\n",
                   json.dumps(lines, indent=1, ensure_ascii=False)))
        out = parse_json(chat(key, model, [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]))
    except Exception as e:  # network, auth, bad JSON: keep the templates
        print("llm polish skipped: %s" % e, file=sys.stderr)
        return None

    kept = 0
    if ok(out.get("intro"), forbidden, puzzle["intro"], easy):
        puzzle["intro"], kept = out["intro"].strip(), kept + 1
    for p in puzzle["puzzles"]:
        new = out.get("p%d" % p["id"])
        if ok(new, forbidden, p["flavor"], easy):
            p["flavor"], kept = new.strip(), kept + 1
    if ok(out.get("meta"), forbidden, puzzle["meta"]["flavor"], easy):
        puzzle["meta"]["flavor"], kept = out["meta"].strip(), kept + 1
    total = len(puzzle["puzzles"]) + 2
    print("llm polish (%s): %d/%d lines rewritten" % (model, kept, total))
    return model


if __name__ == "__main__":
    # Preview: python3 generator/llm.py [date]. Builds a throwaway round with the
    # dev secret and prints template vs. K2 Horizon flavour side by side.
    import copy
    import datetime as dt
    import generate
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    puzzle, solution = generate.build("dev-secret", date)
    before = copy.deepcopy(puzzle)
    theme = next(t for t in generate.THEMES if t["name"] == puzzle["round"])
    if not polish(puzzle, solution, theme):
        sys.exit("no rewrite: is IFM_API_KEY set? (see message above)")
    pairs = [("intro", before["intro"], puzzle["intro"])]
    pairs += [(p["title"], b["flavor"], p["flavor"]) for b, p in zip(before["puzzles"], puzzle["puzzles"])]
    pairs.append(("meta", before["meta"]["flavor"], puzzle["meta"]["flavor"]))
    for name, old, new in pairs:
        print("\n## %s\n  template: %s\n  k2:       %s" % (name, old, new if new != old else "(kept template)"))
