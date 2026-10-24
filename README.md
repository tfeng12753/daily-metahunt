# Daily Metahunt

Three new puzzle-hunt rounds every day, **Easy**, **Medium** and **Hard**, on the
same theme, in the spirit of MIT Mystery Hunt and the tech-company hunts. Each round has five to eight **feeder puzzles** and one
**metapuzzle**, all on a theme. Every feeder hides a word, the meta turns those
words into a single final answer, and nothing tells you how. The flavour text,
titles and shape of the data are the only clues.

**Play:** https://daily-metahunt.onrender.com (mirror: https://tfeng12753.github.io/daily-metahunt/)

## What's in a round

- **A theme**, drawn from 22 rounds (Bletchley's Hut Eight, a bathysphere, a
  night train, a clockmaker's will, a CTF…), each with its own story, titles,
  Morse glyphs and a set of themed final answers.
- **An epigraph.** Each round opens with a line under its story that alludes
  to the final answer. It shouldn't give the answer away, but it clicks once
  you've solved it.
- **Three levels.** Hard gives you nothing but oblique flavour: it alludes and never explains.
  Medium keeps the oblique flavour but shows answer lengths, doesn't name techniques, only
  rarely adds a hidden layer, and uses the gentler metas (fit-in, title diagonal, logbook,
  stowaways). Easy uses 4–6 feeders, no hidden layers, names each puzzle's technique and
  shows answer lengths. Each level has its own final word.
- **Tiered hints**, for feeders and the meta alike, on a ladder where each rung says more
  than the one before: story → flavour → *nudge* (names the kind of system, or the
  observation that unlocks it) → *pointer* (names the trick and the step) → *method* (spells
  it out) → *worked start* (the first letter you should be getting). Hard offers the nudge,
  Medium the nudge then the pointer. Easy's flavour and technique label already say as much
  as a pointer, so its hints are the method and then the worked start. `selftest.py` fails
  if a first hint mostly repeats its own flavour. The meta's explanation is no longer
  printed up front, even on Easy. Word
  searches don't print their word list: a category stands in for it (with the count on
  Medium, and lengths on Easy), and a hint reveals the words.
- **Feeders**, each built with a different mechanism, and sometimes with a
  second layer (Atbash, reversal or ROT13) hinted in the flavour, obliquely on Hard:

  | | | |
  |---|---|---|
  | Binary codons (2-bit bases → codons → amino acids) | Template-strand DNA | Morse in themed glyphs |
  | Flag semaphore drawn as stopped clocks | Braille as 6-bit numbers | Atomic numbers |
  | DTMF multi-tap phone tones | Vigenère keyed by the puzzle title | Mirrored NATO alphabet |
  | Tap code | QWERTY keyboard shift | Hex colours as ASCII |
  | Resistor colour bands | Pigpen | Punched paper tape |
  | Primes in Roman numerals | Baconian cipher in the typesetting | Nonogram (interactive, line-solvable) |
  | Word search: leftover letters | Cryptogram of a cluephrase | Rail fence of a cluephrase |
  | Book cipher on a recovered page | Knight's path on a letter board | Maritime signal flags |
  | Numbers in mixed bases | Anagrams with an extra letter | Letter sudoku (numbered squares) |
  | Drop quote | Shredded sentence | Missing letters (not on Hard) |
  | Number trivia | Scrambled sentence | Caesar shift (not on Hard) |
  | Seating plan: a logic puzzle, then seat k gives letter k | Gapless Morse: find the theme word, then index into it | Element spelling: atomic numbers as symbols |
  | Playfair keyed by the title (Hard only) | Spiral route through a letter grid | |

  Word and logic puzzles are weighted to appear about three times as often as
  pure encodings. Classic codes also come in variations: Morse as symbols, a
  signal lamp or audio; semaphore as clocks, compass bearings or stick figures;
  Braille as numbers, bit strings or drawn cells; elements by name, symbol or
  atomic mass; phone codes as tones, keypad presses or audio; tap code and
  resistor codes as pictures, text or sound; cryptograms in letters or symbols.

- **A meta**, which is one of:
  - *Mutation*: each feeder decodes with exactly one wrong letter; the wrong letters spell the answer.
  - *Stowaways*: each feeder decodes with one extra letter; the extras spell the answer.
  - *Fit-in grid*: answers slot into rows by length; the shaded squares spell the answer.
  - *Diagonal*: order the answers (alphabetically, or by their puzzles' titles) and read the k-th letter of the k-th.
  - *Logbook*: the meta gives (puzzle, letter) indices disguised as ship's bells, verses, seats…
  - *Initials*: a Vigenère ciphertext whose key is the feeders' first letters.

- **Solving in the page.** Word searches take a drag (or a click on the first and last
  letters) and show the leftover letters live; cryptograms and shift ciphers get a
  substitution grid where one keystroke fills every copy of a symbol (Easy shift ciphers
  also get a cipher wheel); shredded sentences are laid out by clicking strips; knight
  boards take clicks to mark the path. Encodings drawn one item per letter get a note box
  under each item, and every puzzle has a notes pad. Older rounds get these tools too.
  Everything is saved in the browser.

Answers are checked in the browser against salted hashes, so the page never
contains them. Rounds from late October 2026 on use PBKDF2 (100,000 rounds,
`"hashv": 2` in the round file), so testing a word list against a round takes
real time; older rounds keep the plain SHA-256 they were published with. Each
round picks its meta at random from every meta type that fits its words. Intermediate layers and uncorrected mutations get a
"keep going" response. Solutions are published the day after.

## Hosting on Render

`render.yaml` is a Render Blueprint with two services:

- **daily-metahunt**: a free static site serving `docs/`.
- **daily-metahunt-api**: the leaderboard (`server/index.mjs`, Node, one dependency).

Every daily bot commit redeploys both. The GitHub Pages deploy in the workflow
still runs as a mirror; delete its last three steps if you only want Render.

## Leaderboard

Players pick a display name (no accounts). Each correct answer is sent to the
API, which re-checks it against the round's hash before recording it, so only
real solves count. The round board ranks each player on **their own clock**, from
pressing Begin to solving the meta, plus a five-minute penalty for each puzzle
they took a hint on, so nobody is punished for living far from UTC. A run whose
solves were sent the moment its player joined (they'd played before signing up)
wasn't timed by the server, so it's listed after the timed runs, by time since
the round opened. There are per-round and all-time boards for each difficulty.

Results go through an outbox in the browser: if the free server is asleep or the
connection drops, they're kept and resent (with the moment they happened, which
the server accepts if it's under three minutes old). The page wakes the server as
soon as it opens, notices if the server has forgotten a player and signs them
back in under the same name, and says plainly when the server has no database.

Everyone also gets a **personal timer**. It starts the first time you open a
round and records a split at every solve. When you finish, you get a split
table and a **share link** (`share.html#run=…`) with your time, a solve
timeline and splits, plus Wordle-style share text. If you're on the
leaderboard, the share page cross-checks the run against the server's record
and shows a "verified" badge. `share.html?player=NAME` shows a player's stored
history: every round, their times, and their best and average clock.

Everything you do is also saved **in your browser**. `progress.html` ("My
rounds") shows every day you've played: totals, your streak, a calendar with
Easy/Medium/Hard status, and a list of each round's solves, clock and hints. The date
picker marks rounds ✓ (solved) or ◐ (in progress). Progress can be exported
to a JSON file and imported on another device; imports merge and never delete.

**Scores need a database.** Without one the API keeps scores in memory, and Render
restarts it on every daily deploy and whenever the free plan sleeps (after about
15 idle minutes), so the board keeps emptying. To make it permanent:

1. Create a free Postgres database at [neon.tech](https://neon.tech) (or Supabase).
2. Copy its connection string (`postgresql://…?sslmode=require`).
3. On Render, open the `daily-metahunt-api` service → Environment → add
   `DATABASE_URL` with that value. The tables are created on first start.

`/api/health` on the API reports `"store": "postgres"` once it's working.
`docs/config.js` holds the API's URL.

## How it runs

`.github/workflows/daily.yml` runs at 00:02 UTC. It self-tests the generator,
creates `docs/puzzles/<today>.json` (Medium and Easy go in `docs/puzzles/medium/` and
`docs/puzzles/easy/`) plus yesterday's `docs/solutions/…`,
commits them, and deploys `docs/` to GitHub Pages.

**On-time release.** GitHub starts scheduled runs late when it's busy (five hours
has happened). So a second run at 12:07 UTC builds tomorrow's rounds early and
commits them encrypted to `docs/locked/`. From 00:00 UTC the leaderboard API
releases that day's key (`/api/unlock`, which refuses any earlier), and the site
decrypts the round in the browser. When the daily run does start, it publishes
exactly the same rounds in the clear and removes the locked copies. To turn it on,
generate a random value (e.g. `openssl rand -hex 32`) and set it as
`RELEASE_SECRET` in both the repository's Actions secrets and the API service's
environment on Render. Without it, rounds simply appear when the daily run finishes.

Each day's solution is also written to `generator/sealed/`, encrypted with a
key derived from `PUZZLE_SECRET`, and decrypted and published the next day.
That way, changing the generator never loses a solution.

Puzzles are deterministic in `(PUZZLE_SECRET, date)`. The secret lives in the
repository's Actions secrets, so the public source can't be used to generate
tomorrow's answers. Every encoding is round-tripped through its decoder, and
every meta is re-solved, before a round is written. A broken puzzle fails the
build and is never published.

## K2 Horizon round descriptions (optional)

If the `IFM_API_KEY` Actions secret is set, IFM's K2 Horizon (`api.ifm.ai`,
OpenAI-compatible) writes each new round's opening story: a longer paragraph in
the voice of the theme that also hints at how the meta works. The hint is faint
on Hard, light on Medium and noticeable on Easy, and the model is given the meta's
first hint as a ceiling the story must stay below. The model is told how
the meta works, given a few images that point at that mechanism truthfully, the
puzzles' titles, and a calibration example at the right strength, and writes three
candidates. A second call judges them for leaks, accuracy against the real
mechanism, hint strength (1–5, with a target band per level) and prose, and the
best one in band wins. A candidate is dropped before judging if it mentions an answer, describes what a solved grid
looks like, falls outside 250–1200 characters, or, on Medium and Hard, names a
technique. Clue lines are never rewritten: when they were, the model explained
methods outright and once stated a wrong fact about one, so clues stay
hand-written. An API outage just means a template-flavoured day. Pin a model
with the `IFM_MODEL` repository variable; otherwise the largest K2 Horizon model
listed by `/models` is used.

A run also gives today's already-published rounds a description if they don't
have one yet (only the intro changes; puzzles and answers are untouched), and
marks them `"described": true` so it happens once.

```bash
IFM_API_KEY=... python3 generator/llm.py 2026-10-02   # preview each level's description, writes nothing
```

## Local development

```bash
python3 generator/selftest.py 365          # build a year of rounds in memory, verifying each
python3 generator/generate.py --date 2026-10-01 --days 3   # writes into docs/
npm install && node server/index.mjs        # site + leaderboard on http://localhost:8791
```

Without `PUZZLE_SECRET`, the generator falls back to an insecure dev secret.
Don't commit rounds made that way.

Add a public theme by appending to `generator/themes.json`, or (better) a
private one to the bank, below. Add a mechanism by
subclassing `Mechanism` in `generator/mechanisms.py` with `encode` and
`decode`, give it a nudge and pointer in `generator/hints.py`, then teach `docs/app.js`
any new block type.

## The private theme bank

Every word in `themes.json` is public, so every answer drawn from it can be
found by hashing the word list against the round, no solving needed. New
themes go into an encrypted bank instead (`generator/bank.py`):

- **Set-up (once).** `python3 generator/bank.py keygen --out ~/metahunt-bank-key.pem`
  writes `generator/bank/public_key.pem` (commit it) and a private key outside
  the repo. Put the private key's full text in an Actions secret named
  `BANK_PRIVATE_KEY`, and keep a copy somewhere safe.
- **Adding a theme.** Write a draft in the `themes.json` format, in `drafts/`
  (git-ignored) or outside the repo, then `python3 generator/bank.py add drafts/x.json`.
  It checks the draft (no final printed anywhere a player can read, enough
  words, cluephrases that read one way only), test-builds every level, and
  encrypts it to `generator/bank/themes/<random id>.json`. Only the public key is
  needed, so a Claude Code session can write and add themes without any secret.
  A draft can bring its own `cluephrases`, `flavors`/`easy_flavors` per puzzle
  type and `meta_flavors`/`easy_meta_flavors`, so it reads as its own world;
  see the docstring at the top of `bank.py`.
- **Nightly.** Each new date takes an unused bank theme (one use by default;
  `max_uses` allows more, each avoiding every answer already published) and
  records it in `generator/bank/schedule.json`. With the bank empty, or no
  key, rounds come from the public themes as before.
- `bank.py list` and `bank.py check` (with `BANK_PRIVATE_KEY` set) show what's
  left and re-test every theme.

## Honesty clause

The public themes are public, so a determined person could still brute-force
their answers against the hash. Please don't. That's not what it's for.
