"""Optional round descriptions via IFM's K2 Horizon (OpenAI-compatible API).

The model only writes each round's opening story: a longer description that
hints at the meta, faintly on Hard, lightly on Medium and noticeably on Easy,
always saying less than the meta's first hint (it is given as a ceiling). Clue
lines stay hand-written, because rewrites kept explaining methods and once
stated a wrong fact about one. Puzzle data, answers and hashes are untouched.
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

# On Hard the description may only allude; words like these mean it has started explaining.
HARD_TELLS = ["number", "numbers", "numbered", "count", "counted", "counting", "letter", "letters", "heading",
              "headings", "title", "titles", "alphabet", "alphabetical", "order", "ordered", "index", "row", "rows",
              "column", "columns", "pluck", "match", "diagonal", "initial", "initials", "sequence"]

# Descriptions of what the solved output looks like spoil every round, easy included.
OUTPUT_TELLS = ["block letter", "five-by-five", "five by five", "5x5", "5×5", "pixel letter",
                "chunky letter", "will spell", "spells out", "spell something", "spell a word"]

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


# ---------------------------------------------------------------------------
# Round descriptions: a longer opening story that hints at the meta
# ---------------------------------------------------------------------------

DESCRIBE_SYSTEM = """You write the opening story for one round of a puzzle hunt, in the style of the MIT Mystery Hunt and tech-company hunts.
The story sets the scene and, somewhere inside it, hints at how the round's metapuzzle (the final step that turns the feeder answers into one final word) works, at exactly the strength you are asked for.
Rules: never state or spell any answer; never name the technique of any individual puzzle; never describe what a solved grid, picture or decoded message looks like; never give numbered or step-by-step instructions.
Write in the voice of the round's setting. British spelling. One paragraph of 4 to 6 sentences, 90 to 170 words. No emoji, no markdown, no headings.
Reply with a single JSON object {"intro": "..."} and nothing else."""

STRENGTH = {
    "hard": ("VAGUE. At most one sentence may allude to the final step, and only through a single atmospheric image "
             "(a habit of the people, an object in the scene), never by describing a procedure. A solver should only "
             "recognise it in hindsight. Do not mention numbers, counting, letters, headings, titles, order, rows, "
             "columns, matching or picking."),
    "medium": ("A LIGHT HINT. Include one in-story image or detail that relates to the final step (for example a "
               "roll call, a filing drawer, a signature, a seating plan), which a solver could connect to it once "
               "they are already thinking along those lines. Never say what to take from each answer, or in what order."),
    "easy": ("A NOTICEABLE HINT. This is the beginners' round: through the story, point at what kind of thing the "
             "final step involves, so a newcomer has somewhere to start. Keep it as story, never as instructions, and "
             "never say which letter or position to take."),
}


def ok_description(text, forbidden, level):
    if not isinstance(text, str):
        return False
    t = text.strip()
    if not 250 <= len(t) <= 1200:
        return False
    low = t.lower()
    letters = re.sub(r"[^a-z]", "", low)
    words = set(re.findall(r"[a-z]+", low))
    for w in forbidden:
        w = w.lower()
        if (len(w) >= 6 and w in letters) or w in words:
            return False
    if any(x in low for x in OUTPUT_TELLS):
        return False
    if level == "hard" and words & set(HARD_TELLS):
        return False
    # Easy names its techniques on the page anyway; the other levels must not.
    return level == "easy" or not any(b in low for b in BANNED)


def describe(puzzle, solution, theme, level="hard", attempts=4):
    """Replace puzzle["intro"] with a longer story that hints at the meta. Returns the model id, or None."""
    key = os.environ.get("IFM_API_KEY")
    if not key:
        return None
    forbidden = {solution["final"]}
    for q in solution["puzzles"]:
        forbidden |= {q["answer"], q["encoded"]} | ({q["mutated"]} if q.get("mutated") else set())
    user = ("Round: %s\nSetting: %s; the people there are %s.\nCurrent opening (keep its facts and mood, expand it): %s\n"
            "How the metapuzzle works (for you only; never quote it): %s\nThe round has %d feeder puzzles.\n"
            "Hint strength: %s\nCeiling: the solver can later open this hint about the final step. Your story must "
            "say clearly less than it, never as much: \"%s\"\n"
            "Don't state how many messages, notes or puzzles there are unless the number is exactly %d.\n"
            "Return JSON {\"intro\": \"...\"}."
            % (puzzle["round"], theme["place"], theme["crew"], theme["intro"], solution["explain"],
               len(puzzle["puzzles"]), STRENGTH[level], puzzle["meta"]["hints"][0], len(puzzle["puzzles"])))
    try:
        model = pick_model(key)
    except Exception as e:
        print("llm describe skipped: %s" % e, file=sys.stderr)
        return None
    for _ in range(attempts):
        try:
            out = parse_json(chat(key, model, [{"role": "system", "content": DESCRIBE_SYSTEM},
                                               {"role": "user", "content": user}]))
        except Exception as e:  # network, auth, bad JSON: try again, then keep the template
            print("llm describe attempt failed: %s" % e, file=sys.stderr)
            continue
        if ok_description(out.get("intro"), forbidden, level):
            puzzle["intro"] = out["intro"].strip()
            print("llm describe (%s, %s): intro rewritten" % (model, level))
            return model
    print("llm describe (%s, %s): kept template" % (model, level))
    return None


if __name__ == "__main__":
    # Preview: python3 generator/llm.py [date]. Builds throwaway rounds with the dev
    # secret and prints each level's K2 Horizon description.
    import datetime as dt
    import generate
    date = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
    for level in generate.LEVELS:
        puzzle, solution = generate.build("dev-secret", date, level=level)
        theme = next(t for t in generate.THEMES if t["name"] == puzzle["round"])
        if not describe(puzzle, solution, theme, level):
            sys.exit("no rewrite: is IFM_API_KEY set? (see message above)")
        print("\n## %s (%s)\n%s" % (puzzle["round"], level, puzzle["intro"]))
