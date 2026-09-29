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
  Medium shows answer lengths and more direct flavour, but doesn't name techniques, only
  rarely adds a hidden layer, and uses the gentler metas (fit-in, title diagonal, logbook,
  stowaways). Easy uses 4–6 feeders, no hidden layers, names each puzzle's technique and
  shows answer lengths. Each level has its own final word.
- **Tiered hints**, for feeders and the meta alike. A *nudge* asks a question or points at
  a kind of system; a *pointer* names the family of trick; the *method* spells it out.
  Hard offers the nudge, Medium the nudge then the pointer, Easy the pointer then the
  method. The meta's explanation is no longer printed up front, even on Easy. Word
  searches don't print their word list: a category stands in for it (with the count on
  Medium, and lengths on Easy), and the last hint reveals the words.
- **Feeders**, each built with a different mechanism, and sometimes with a
  second layer (Atbash, reversal or ROT13) hinted only in the flavour:

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

Answers are checked in the browser against salted SHA-256 hashes, so the page
never contains them. Intermediate layers and uncorrected mutations get a
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
real solves count. Times run from 00:00 UTC on the round's date, and each hint
adds a five-minute penalty (once per puzzle, however many hint tiers you open). There are per-round and all-time boards for each
difficulty.

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

Scores live in Postgres via the `DATABASE_URL` environment variable on the API
service (a free Neon or Supabase database works). Without it the API keeps
scores in memory, which is fine locally but resets on every restart or deploy.
`docs/config.js` holds the API's URL.

## How it runs

`.github/workflows/daily.yml` runs at 00:02 UTC. It self-tests the generator,
creates `docs/puzzles/<today>.json` (Medium and Easy go in `docs/puzzles/medium/` and
`docs/puzzles/easy/`) plus yesterday's `docs/solutions/…`,
commits them, and deploys `docs/` to GitHub Pages.

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
on Hard, noticeable on Medium and fairly clear on Easy. The model is told how
the meta works but never sees it printed; a description is rejected (and retried,
then the template kept) if it mentions an answer, describes what a solved grid
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

Add a theme by appending to `generator/themes.json`. Add a mechanism by
subclassing `Mechanism` in `generator/mechanisms.py` with `encode` and
`decode`, give it a nudge and pointer in `generator/hints.py`, then teach `docs/app.js`
any new block type.

## Honesty clause

The theme bank is public, so a determined person could brute-force the final
answer against its hash. Please don't. That's not what it's for.
