# Daily Metahunt

A new puzzle-hunt round every day, in the spirit of MIT Mystery Hunt and the
tech-company hunts. Each round has five to eight **feeder puzzles** and one
**metapuzzle**, all on a theme. Every feeder hides a word, the meta turns those
words into a single final answer, and nothing tells you how. The flavour text,
titles and shape of the data are the only clues.

**Play:** https://tfeng12753.github.io/daily-metahunt/

## What's in a round

- **A theme**, drawn from 22 rounds (Bletchley's Hut Eight, a bathysphere, a
  night train, a clockmaker's will, a CTF…), each with its own story, titles,
  Morse glyphs and a set of themed final answers.
- **Feeders**, each built with a different mechanism, and sometimes with a
  second layer (Atbash, reversal or ROT13) hinted only in the flavour:

  | | | |
  |---|---|---|
  | Binary codons (2-bit bases → codons → amino acids) | Template-strand DNA | Morse in themed glyphs |
  | Flag semaphore drawn as stopped clocks | Braille as 6-bit numbers | Atomic numbers |
  | DTMF multi-tap phone tones | Vigenère keyed by the puzzle title | Mirrored NATO alphabet |
  | Tap code | QWERTY keyboard shift | Hex colours as ASCII |
  | Resistor colour bands | Pigpen | Punched paper tape |
  | Primes in Roman numerals | Baconian cipher in the typesetting | |

- **A meta**, which is one of:
  - *Mutation*: each feeder decodes with exactly one wrong letter; the wrong letters spell the answer.
  - *Diagonal*: order the answers (alphabetically, or by their puzzles' titles) and read the k-th letter of the k-th.
  - *Logbook*: the meta gives (puzzle, letter) indices disguised as ship's bells, verses, seats…
  - *Initials*: a Vigenère ciphertext whose key is the feeders' first letters.

Answers are checked in the browser against salted SHA-256 hashes, so the page
never contains them. Intermediate layers and uncorrected mutations get a
"keep going" response. Solutions are published the day after.

## How it runs

`.github/workflows/daily.yml` runs at 00:02 UTC. It self-tests the generator,
creates `docs/puzzles/<today>.json` plus yesterday's `docs/solutions/…`,
commits them, and deploys `docs/` to GitHub Pages.

Puzzles are deterministic in `(PUZZLE_SECRET, date)`. The secret lives in the
repository's Actions secrets, so the public source can't be used to generate
tomorrow's answers. Every encoding is round-tripped through its decoder, and
every meta is re-solved, before a round is written. A broken puzzle fails the
build and is never published.

## Local development

```bash
python3 generator/selftest.py 365          # build a year of rounds in memory, verifying each
python3 generator/generate.py --date 2026-10-01 --days 3   # writes into docs/
node serve.mjs                              # http://localhost:8791
```

Without `PUZZLE_SECRET`, the generator falls back to an insecure dev secret.
Don't commit rounds made that way.

Add a theme by appending to `generator/themes.json`. Add a mechanism by
subclassing `Mechanism` in `generator/mechanisms.py` with `encode` and
`decode`, then teach `docs/app.js` any new block type.

## Honesty clause

The theme bank is public, so a determined person could brute-force the final
answer against its hash. Please don't. That's not what it's for.
