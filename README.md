# Daily Metahunt

Two new puzzle-hunt rounds every day, a **Hard** one and an **Easy** one on the
same theme, in the spirit of MIT Mystery Hunt and the tech-company hunts. Each round has five to eight **feeder puzzles** and one
**metapuzzle**, all on a theme. Every feeder hides a word, the meta turns those
words into a single final answer, and nothing tells you how. The flavour text,
titles and shape of the data are the only clues.

**Play:** https://daily-metahunt.onrender.com (mirror: https://tfeng12753.github.io/daily-metahunt/)

## What's in a round

- **A theme**, drawn from 22 rounds (Bletchley's Hut Eight, a bathysphere, a
  night train, a clockmaker's will, a CTF…), each with its own story, titles,
  Morse glyphs and a set of themed final answers.
- **Hard vs Easy.** Hard gives you nothing but flavour. Easy uses 4–6 feeders,
  no hidden layers, names each puzzle's technique, shows answer lengths and
  explains its meta (first letters, fit-in grid, title diagonal or logbook).
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
  | Drop quote | Shredded sentence | Missing letters (easy only) |

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
adds a five-minute penalty. There are per-round and all-time boards for each
difficulty.

Everyone also gets a **personal timer**. It starts the first time you open a
round and records a split at every solve. When you finish, you get a split
table and a **share link** (`share.html#run=…`) with your time, a solve
timeline and splits, plus Wordle-style share text. If you're on the
leaderboard, the share page cross-checks the run against the server's record
and shows a "verified" badge. `share.html?player=NAME` shows a player's stored
history: every round, their times, and their best and average clock.

Scores live in Postgres via the `DATABASE_URL` environment variable on the API
service (a free Neon or Supabase database works). Without it the API keeps
scores in memory, which is fine locally but resets on every restart or deploy.
`docs/config.js` holds the API's URL.

## How it runs

`.github/workflows/daily.yml` runs at 00:02 UTC. It self-tests the generator,
creates `docs/puzzles/<today>.json` plus yesterday's `docs/solutions/…`,
commits them, and deploys `docs/` to GitHub Pages.

Each day's solution is also written to `generator/sealed/`, encrypted with a
key derived from `PUZZLE_SECRET`, and decrypted and published the next day.
That way, changing the generator never loses a solution.

Puzzles are deterministic in `(PUZZLE_SECRET, date)`. The secret lives in the
repository's Actions secrets, so the public source can't be used to generate
tomorrow's answers. Every encoding is round-tripped through its decoder, and
every meta is re-solved, before a round is written. A broken puzzle fails the
build and is never published.

## K2 Horizon flavour text (optional)

If the `IFM_API_KEY` Actions secret is set, each new round's intro and
flavour lines are rewritten by IFM's K2 Horizon (`api.ifm.ai`, OpenAI-compatible)
in the voice of that round's story. The model only touches prose. Each rewrite
is rejected, and the template kept, if it mentions an answer or an intermediate
string, names the technique outright, or runs too long. An API outage just means
a template-flavoured day. Pin a model with the `IFM_MODEL` repository variable;
otherwise the largest K2 Horizon model listed by `/models` is used.

```bash
IFM_API_KEY=... python3 generator/llm.py 2026-10-02   # preview rewrites, writes nothing
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
`decode`, then teach `docs/app.js` any new block type.

## Honesty clause

The theme bank is public, so a determined person could brute-force the final
answer against its hash. Please don't. That's not what it's for.
