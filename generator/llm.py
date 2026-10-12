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
Good hunt flavour works by a single, concrete, true image that a solver can later recognise: a habit of the people, an object in the scene, a ritual. It never explains, and it never points the wrong way: an image that suggests a different mechanism is worse than no hint at all.
Rules: never state or spell any answer; never name the technique of any individual puzzle; never describe what a solved grid, picture or decoded message looks like; never give numbered or step-by-step instructions.
Write in the voice of the round's setting, with specific sensory detail rather than generic mystery words. British spelling. One paragraph of 4 to 6 sentences, 90 to 170 words. No emoji, no markdown, no headings.
Reply with a single JSON object and nothing else."""

# What each meta really does, and images that point at it truthfully. The model picks or adapts one,
# so hints are on-theme without steering solvers towards the wrong mechanism.
META_IMAGERY = {
    "diagonal": ("The answers, sorted alphabetically, each give one letter: the 1st letter of the 1st, the 2nd of the 2nd, and so on.",
                 ["a roll call taken alphabetically", "a staircase where each step goes one further", "a queue sorted by surname"]),
    "title_diagonal": ("The puzzles, sorted by their titles, each give one letter: the 1st letter of the 1st answer, the 2nd of the 2nd, and so on.",
                       ["an archivist who files everything by its heading", "a drawer of labelled folders read on the slant",
                        "a library shelf in title order"]),
    "mutation": ("Each feeder first decodes with exactly one wrong letter; those wrong letters, in puzzle order, spell the final answer.",
                 ["a careful copyist who makes exactly one slip per page", "smudges that are oddly consistent",
                  "a proof-reader who keeps the errors in a separate notebook"]),
    "stowaway": ("Each feeder first decodes with one extra letter; those extra letters, in puzzle order, spell the final answer.",
                 ["one passenger too many on every boat", "a stowaway in every crate", "a census that always counts one extra"]),
    "fitin": ("Each answer fits exactly one row of a grid by its length; shaded squares spell the final answer.",
              ["pigeonholes cut to fit one thing each", "a rack of slots of different sizes", "a type case where every piece has its place"]),
    "logbook": ("The meta lists pairs of numbers: puzzle number, then letter position in that puzzle's answer.",
                ["a ledger where every entry is two numbers", "a watch-keeper who writes only the day and the bell",
                 "a ticket stamped with a carriage and a seat"]),
    "initials": ("The final answer is Vigenère-encrypted; the key is the feeder answers' first letters, in puzzle order.",
                 ["letters signed with a single initial", "a lock that needs every signature at once", "a register of monograms"]),
    "first_letters": ("The answers' first letters, in puzzle order, spell the final answer.",
                      ["people introducing themselves in turn", "how each voice begins", "the first word of every song"]),
}

# Calibration examples, set in places no theme uses so the model can't copy them into a round.
EXAMPLES = {
    "hard": ("a lighthouse round whose meta reads the k-th letter of each answer in title order",
             "The relief boat has not come for nine days, and the keeper has stopped expecting it. He passes the long "
             "watches the way he always has: oiling the brass, logging the weather, and keeping the store-room as orderly "
             "as a chapel, every tin and coil shelved under the name painted on its lid. The last boat left a satchel of "
             "letters that nobody has claimed, each in a different hand. He has put them away with everything else, in his "
             "own particular way, and gone back to watching the dark."),
    "medium": ("a bakery round whose meta is one wrong letter in each feeder",
               "The bakery on Wren Street has used the same recipe book for a hundred years, and the family guard it like "
               "scripture. Each page is copied out fresh every spring by the youngest apprentice, in careful copperplate. "
               "This year's copies arrived on the counter with the flour still on them, and old Mrs Ashdown, who has never "
               "found an error in her life, found exactly one on every page. She has started keeping a list of them."),
    "easy": ("a choir round whose meta takes the first letter of each answer, in order",
             "The village choir rehearses in the church hall on Thursdays, and the choirmaster insists on the old ritual: "
             "before a note is sung, every member stands in turn and introduces themselves, though they have known each "
             "other for decades. He says you can tell everything about a voice from how it begins. Tonight the folded notes "
             "being passed along the back row will need the same treatment: take them in turn, and listen to how each one starts."),
}

BAND = {"hard": (1, 2), "medium": (2, 3), "easy": (3, 4)}

JUDGE_SYSTEM = """You review flavour text for a puzzle hunt. For each candidate, judge:
- leak: true if it states an answer, names a puzzle technique, gives step-by-step instructions, or describes what the solved output looks like.
- accurate: true if any hint it contains is consistent with how the meta really works (a hint that suggests a different mechanism is NOT accurate). A candidate with no discernible hint is accurate.
- strength: how much it gives away about the final step, 1 (nothing a solver could use) to 5 (all but tells you what to do).
- quality: prose quality and atmosphere, 1 to 5.
Reply with a single JSON object {"scores": [{"i": 0, "leak": false, "accurate": true, "strength": 2, "quality": 4}, ...]} and nothing else."""

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


def rejection(text, forbidden, level):
    """Why a description can't be used, or None if it can."""
    if not isinstance(text, str):
        return "not text"
    t = text.strip()
    if not 250 <= len(t) <= 1200:
        return "length %d" % len(t)
    low = t.lower()
    letters = re.sub(r"[^a-z]", "", low)
    words = set(re.findall(r"[a-z]+", low))
    for w in forbidden:
        w = w.lower()
        if (len(w) >= 6 and w in letters) or w in words:
            return "answer %s" % w.upper()
    tell = next((x for x in OUTPUT_TELLS if x in low), None)
    if tell:
        return "output tell '%s'" % tell
    hard = sorted(words & set(HARD_TELLS)) if level == "hard" else []
    if hard:
        return "explains ('%s')" % hard[0]
    # Easy names its techniques on the page anyway; the other levels must not.
    named = next((b for b in BANNED if b in low), None) if level != "easy" else None
    return "names '%s'" % named if named else None


def ok_description(text, forbidden, level):
    return rejection(text, forbidden, level) is None


def _pick(cands, scores, level):
    """Best candidate: no leak, accurate, strength inside the level's band; then by quality."""
    lo, hi = BAND[level]
    best, best_key = None, None
    for sc in scores:
        try:
            i, leak, acc, st, q = int(sc["i"]), bool(sc["leak"]), bool(sc["accurate"]), float(sc["strength"]), float(sc["quality"])
        except (KeyError, TypeError, ValueError):
            continue
        if not 0 <= i < len(cands) or leak or not acc:
            continue
        off = 0 if lo <= st <= hi else min(abs(st - lo), abs(st - hi))
        if off > 1:
            continue
        key = (off, -q)
        if best_key is None or key < best_key:
            best, best_key = cands[i], key
    return best


def describe(puzzle, solution, theme, level="hard", attempts=2):
    """Replace puzzle["intro"] with a longer story that hints at the meta. Returns the model id, or None.

    Each attempt asks for three candidates, drops any that fail the local checks, then has the model
    judge the rest for leaks, accuracy against the real mechanism, hint strength and prose, and keeps
    the best one inside this level's strength band.
    """
    key = os.environ.get("IFM_API_KEY")
    if not key:
        return None
    forbidden = {solution["final"]}
    for q in solution["puzzles"]:
        forbidden |= {q["answer"], q["encoded"]} | ({q["mutated"]} if q.get("mutated") else set())
    truth, images = META_IMAGERY.get(solution["metaType"], (solution["explain"], []))
    # The answers are ordinary theme words ("tent", "seal"), so a story set in the same place reaches
    # for them naturally. Tell the model which ones are off limits instead of discarding its drafts.
    avoid = sorted({solution["final"]} | {q["answer"] for q in solution["puzzles"]})
    banned_here = sorted(set(HARD_TELLS)) if level == "hard" else []
    ex_what, ex_text = EXAMPLES[level]
    n = len(puzzle["puzzles"])
    user = ("Round: %s\nSetting: %s; the people there are %s.\nCurrent opening (keep its facts and mood, expand it): %s\n"
            "The feeder puzzles are titled: %s.\n"
            "How the metapuzzle works (for you only; never quote it): %s\n"
            "Images that point at it truthfully (pick one, or invent one in the same spirit that fits this setting): %s.\n"
            "Hint strength: %s\nCeiling: the solver can later open this hint about the final step. Your story must "
            "say clearly less than it, never as much: \"%s\"\n"
            "Don't state how many messages, notes or puzzles there are unless the number is exactly %d.\n"
            "Never use any of these words, in any form, even in passing (they are answers); if the current opening "
            "uses one, rephrase that part: %s.\n"
            "%s"
            "For calibration, a story at this strength for a different round (%s):\n\"%s\"\n"
            "Write three different candidates, each built around a different image. Return JSON "
            "{\"candidates\": [{\"intro\": \"...\", \"image\": \"the image you used\"}, ...]}."
            % (puzzle["round"], theme["place"], theme["crew"], theme["intro"],
               ", ".join(p["title"] for p in puzzle["puzzles"]), truth, "; ".join(images) or "your choice",
               STRENGTH[level], puzzle["meta"]["hints"][0], n, ", ".join(avoid),
               ("Also never use these words: %s.\n" % ", ".join(banned_here)) if banned_here else "",
               ex_what, ex_text))
    try:
        model = pick_model(key)
    except Exception as e:
        print("llm describe skipped: %s" % e, file=sys.stderr)
        return None
    fallback = None
    for _ in range(attempts):
        try:
            out = parse_json(chat(key, model, [{"role": "system", "content": DESCRIBE_SYSTEM},
                                               {"role": "user", "content": user}]))
            raw = out.get("candidates") or ([{"intro": out["intro"]}] if out.get("intro") else [])
        except Exception as e:  # network, auth, bad JSON: try again, then keep the template
            print("llm describe attempt failed: %s" % e, file=sys.stderr)
            continue
        cands, why = [], []
        for c in raw:
            r = rejection(c.get("intro") if isinstance(c, dict) else None, forbidden, level)
            (why.append(r) if r else cands.append(c["intro"].strip()))
        if why:
            print("llm describe (%s): dropped %d of %d drafts: %s" % (level, len(why), len(raw), "; ".join(why)), file=sys.stderr)
        if not cands:
            continue
        fallback = fallback or cands[0]
        try:
            verdict = parse_json(chat(key, model, [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": "How the meta really works: %s\nTarget strength for this %s round: %d to %d.\n\n%s"
                    % (truth, level, BAND[level][0], BAND[level][1],
                       "\n\n".join("Candidate %d:\n%s" % (i, c) for i, c in enumerate(cands)))}]))
            chosen = _pick(cands, verdict.get("scores") or [], level)
        except Exception as e:
            print("llm judge failed: %s" % e, file=sys.stderr)
            chosen = None
        if chosen:
            puzzle["intro"] = chosen
            print("llm describe (%s, %s): intro rewritten (judged best of %d)" % (model, level, len(cands)))
            return model
    if fallback:
        # Every candidate passed the hard local checks; the judge just couldn't place one in the band.
        puzzle["intro"] = fallback
        print("llm describe (%s, %s): intro rewritten (unjudged)" % (model, level))
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
