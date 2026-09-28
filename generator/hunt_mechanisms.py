"""Classic puzzle-hunt feeder types: grids, cluephrases, flags and friends.

Same contract as mechanisms.py: encode() returns render blocks, decode()
recovers the encoded word from those blocks alone, and the generator
round-trips every puzzle before it ships.
"""
import random
import re

from mechanisms import ALPHA, MECHANISMS as BASE_MECHANISMS, Mechanism, idx

# --------------------------------------------------------------------------
# Cluephrases: a sentence whose last word is the answer
# --------------------------------------------------------------------------

CLUEPHRASES = [
    "EVERY GOOD HUNT ENDS WITH A SINGLE WORD AND THE WORD YOU WANT FROM THIS PAGE IS {W}",
    "IF YOU CAN READ THIS SENTENCE THEN YOU HAVE ALREADY FOUND THE ANSWER WHICH IS {W}",
    "THE MESSAGE WAS HIDDEN IN PLAIN SIGHT ALL ALONG AND IT SIMPLY SAYS {W}",
    "WELL DONE YOU MAY NOW WRITE DOWN THE WORD {W} AND MOVE QUIETLY ON TO THE NEXT ONE",
    "NOBODY EXPECTED ANYONE TO GET THIS FAR SO THE PRIZE IS JUST ONE WORD {W}",
    "WHAT THE COURIER CARRIED WAS NOT GOLD OR SECRETS BUT A SINGLE WORD {W}",
    "THIS PAGE HAS KEPT ITS SECRET FOR A VERY LONG TIME AND THAT SECRET IS {W}",
    "SHOULD THIS NOTE FALL INTO THE WRONG HANDS PLEASE FORGET THE WORD {W}",
    "THE LAST THING THE OPERATOR TYPED BEFORE THE LINE WENT DEAD WAS {W}",
    "YOUR ANSWER FOR THIS PUZZLE IS {W} BUT DO NOT TELL THE OTHERS HOW YOU GOT IT",
]


def cluephrase(word, rng):
    return rng.choice(CLUEPHRASES).replace("{W}", word)


def phrase_answer(text):
    """Recover {W} from a plaintext cluephrase (spaces optional)."""
    flat = text.replace(" ", "")
    for tmpl in CLUEPHRASES:
        head, tail = tmpl.replace(" ", "").split("{W}")
        if flat.startswith(head) and flat.endswith(tail) and len(flat) > len(head) + len(tail):
            return flat[len(head):len(flat) - len(tail)]
    return None


class Cryptogram(Mechanism):
    weight = 3
    SYMBOLS = "♠♣♥♦★☆●○■□▲△▼▽◆◇♪♫☀☁☂☾✈✚✿⚑"
    SYMBOL_VARIANT = ("Symbol cryptogram", "Each symbol stands for one letter (a simple substitution); word breaks are kept. Solve the sentence; it tells you the answer.", [
        "Not a single letter on the page, and yet it says something.",
        "The clerk ran out of alphabet and kept going anyway.",
    ])
    key = "cryptogram"
    name = "Cryptogram (cluephrase)"
    hint = "Simple monoalphabetic substitution with word breaks kept. Solve the sentence; it tells you the answer."
    allow_transform = False
    easy_flavors = [
        "Every letter here is wearing someone else's coat. The spaces, at least, are honest.",
        "The newspaper's puzzle page, the one your grandmother did in pen, every single morning.",
        "One alphabet was traded for another, one for one, and nobody bothered to hide where the words begin and end.",
    ]
    flavors = [
        "Every letter here is wearing someone else's coat.",
        'The spaces, at least, are honest.',
        'A sentence in disguise, and not a very good disguise.',
    ]

    def encode(self, word, rng, ctx):
        while True:
            perm = list(ALPHA)
            rng.shuffle(perm)
            if all(a != b for a, b in zip(ALPHA, perm)):
                break
        plain = cluephrase(word, rng)
        if rng.random() < 0.4:
            # A variation on the newspaper cryptogram: no letters at all.
            symbols = list(self.SYMBOLS)
            rng.shuffle(symbols)
            perm = symbols[:26]
            ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.SYMBOL_VARIANT
        table = dict(zip(ALPHA, perm))
        ct = "".join(table.get(c, c) for c in plain)
        ctx["_plain"] = plain
        return [{"type": "mono", "text": ct, "wide": True}]

    def decode(self, blocks, ctx):
        # The self-check knows the plaintext; verify it is a consistent substitution of the ciphertext.
        ct, plain = blocks[0]["text"], ctx["_plain"]
        fwd = {}
        for a, b in zip(ct, plain):
            if fwd.setdefault(a, b) != b:
                return None
        if len(set(fwd.values())) != len(fwd):
            return None
        return phrase_answer(plain)


class RailFence(Mechanism):
    weight = 3
    key = "railfence"
    name = "Rail fence (cluephrase)"
    hint = "Rail-fence transposition of a sentence with the spaces removed. Try 2 to 5 rails; the sentence tells you the answer."
    allow_transform = False
    NUMS = {2: "two", 3: "three", 4: "four", 5: "five"}
    easy_flavors = [
        "The fence around {place} zigzags between {n} rails. Walk it, don't read it.",
        "Someone wrote this out in a zigzag across {n} lines of the ledger, then copied each line out in turn.",
        "Up and down, up and down: {n} rows, one long sentence, and not a single space left.",
    ]
    flavors = [
        'Written in a zigzag, then copied out one row at a time.',
        'Up and down, up and down, and not a single space left.',
        "Walk the fence; don't read it.",
    ]

    @staticmethod
    def _pattern(n, rails):
        cyc = 2 * rails - 2
        return [min(i % cyc, cyc - i % cyc) for i in range(n)]

    def encode(self, word, rng, ctx):
        rails = rng.choice([2, 3, 4, 5])
        plain = cluephrase(word, rng).replace(" ", "")
        pat = self._pattern(len(plain), rails)
        ct = "".join(plain[i] for r in range(rails) for i in range(len(plain)) if pat[i] == r)
        ctx["_flavor_n"] = self.NUMS[rails]
        groups = " ".join(ct[i:i + 5] for i in range(0, len(ct), 5))
        return [{"type": "mono", "text": groups, "wide": True, "rails": rails}]

    def decode(self, blocks, ctx):
        ct = blocks[0]["text"].replace(" ", "")
        rails = blocks[0]["rails"]
        pat = self._pattern(len(ct), rails)
        order = [i for r in range(rails) for i in range(len(ct)) if pat[i] == r]
        plain = [""] * len(ct)
        for c, i in zip(ct, order):
            plain[i] = c
        return phrase_answer("".join(plain))


class BookCipher(Mechanism):
    weight = 3
    key = "book"
    name = "Book cipher"
    hint = "Each pair is word.letter into the recovered page (words split on spaces; punctuation ignored)."
    easy_flavors = [
        "Only one page of the book survived. Luckily, it was the only page anyone needed.",
        "Numbers in pairs, pencilled in the margin: a page reference is a very old kind of key.",
        "The spy's handbook said to always carry a novel. It never said which one; this page will have to do.",
    ]
    flavors = [
        'Only one page survived. It was the only page anyone needed.',
        'Pairs of numbers pencilled in the margin.',
        'The spy always carried a novel. This page will have to do.',
    ]

    @staticmethod
    def _words(text):
        return [re.sub(r"[^A-Z]", "", w.upper()) for w in text.split()]

    def can(self, word, ctx=None):
        if not ctx or "intro" not in ctx:
            return False
        letters = set("".join(self._words(ctx["intro"])))
        return all(c in letters for c in word)

    def encode(self, word, rng, ctx):
        words = self._words(ctx["intro"])
        pairs = []
        for c in word:
            opts = [(i, j) for i, w in enumerate(words) for j, ch in enumerate(w) if ch == c]
            i, j = rng.choice(opts)
            pairs.append("%d.%d" % (i + 1, j + 1))
        return [{"type": "prose", "text": ctx["intro"], "paper": True},
                {"type": "list", "items": pairs, "inline": True}]

    def decode(self, blocks, ctx):
        words = self._words(blocks[0]["text"])
        out = ""
        for p in blocks[1]["items"]:
            i, j = (int(x) for x in p.split("."))
            out += words[i - 1][j - 1]
        return out


class KnightPath(Mechanism):
    weight = 3
    key = "knight"
    name = "Knight's path"
    hint = "Start on the given square and follow the knight moves; read the letter on each square it lands on."
    easy_flavors = [
        "The knight never moves in a straight line, and neither does the truth {at}.",
        "A board full of noise, and one horseman who knows exactly where to step.",
        "Two forward, one across. Remember where you land.",
    ]
    flavors = [
        'Two forward, one across. Remember where you land.',
        'One horseman, and a field full of noise.',
        'It never travels in a straight line, and neither does the truth.',
    ]
    FILES = "abcdefgh"

    def encode(self, word, rng, ctx):
        jumps = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
        for _ in range(500):
            start = (rng.randrange(8), rng.randrange(8))
            path, seen, cur = [], {start}, start
            for _ in word:
                opts = [(cur[0] + a, cur[1] + b) for a, b in jumps]
                opts = [p for p in opts if 0 <= p[0] < 8 and 0 <= p[1] < 8 and p not in seen]
                if not opts:
                    break
                cur = rng.choice(opts)
                seen.add(cur)
                path.append(cur)
            if len(path) == len(word):
                break
        else:
            raise RuntimeError("no knight path")
        board = [[rng.choice(ALPHA) for _ in range(8)] for _ in range(8)]  # board[rank][file]
        for (f, r), c in zip(path, word):
            board[r][f] = c
        sq = lambda p: self.FILES[p[0]] + str(p[1] + 1)
        rows = ["".join(board[r]) for r in range(7, -1, -1)]  # rank 8 at the top
        moves = ["N" + sq(p) for p in path]
        return [{"type": "board", "rows": rows},
                {"type": "prose", "text": "The knight sets out from %s: %s." % (sq(start), " ".join(moves))}]

    def decode(self, blocks, ctx):
        rows = blocks[0]["rows"]
        moves = re.findall(r"N([a-h])([1-8])", blocks[1]["text"])
        return "".join(rows[8 - int(r)][self.FILES.index(f)] for f, r in moves)


class SignalFlags(Mechanism):
    key = "flags"
    name = "Maritime signal flags"
    hint = "International maritime signal flags, one letter each."
    easy_flavors = [
        "Run up the halyard at dawn and left there: a string of bunting that isn't meant for decoration.",
        "The harbourmaster says the ship is dressed overall, but that's not what the flags are saying.",
        "Every flag on this line has a meaning on its own. Together, they have one more.",
    ]
    flavors = [
        'Bunting on the halyard, and not for a celebration.',
        'Every flag on this line means something on its own. Together they mean one more thing.',
        'Dressed overall, and saying far more than hello.',
    ]

    def encode(self, word, rng, ctx):
        return [{"type": "flags", "items": list(word)}]

    def decode(self, blocks, ctx):
        return "".join(blocks[0]["items"])


class MixedBases(Mechanism):
    easy = False
    key = "bases"
    name = "Mixed number bases"
    hint = "Each number is a letter position written in the base shown in its subscript."
    easy_flavors = [
        "An accountant who changes currency every line, but never the amount.",
        "Everyone {at} counts differently. The little number tells you on how many fingers.",
        "Same quantities, many radixes. Convert, then count through the alphabet.",
    ]
    flavors = [
        'Same quantities, different fingers.',
        'Everyone here counts differently. The little number says how.',
        'An accountant who changes currency every line, but never the amount.',
    ]
    SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

    @staticmethod
    def _to_base(n, b):
        digits = "0123456789ABCDEF"
        out = ""
        while n:
            out = digits[n % b] + out
            n //= b
        return out

    def encode(self, word, rng, ctx):
        items = []
        for c in word:
            b = rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 12, 16])
            items.append(self._to_base(idx(c) + 1, b) + str(b).translate(self.SUB))
        return [{"type": "list", "items": items, "inline": True}]

    def decode(self, blocks, ctx):
        back = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
        out = ""
        for it in blocks[0]["items"]:
            m = re.match(r"([0-9A-F]+)([₀-₉]+)$", it)
            out += ALPHA[int(m.group(1), int(m.group(2).translate(back))) - 1]
        return out


class WordSearch(Mechanism):
    weight = 3
    key = "wordsearch"
    name = "Word search leftovers"
    hint = "Find every listed word (any of 8 directions). The unused letters, read left-to-right, top-to-bottom, spell the answer."
    easy_flavors = [
        "Cross off everything you recognise. What nobody claims is what you came for.",
        "An inventory of {place}, tangled up. Whatever is left over when every item is accounted for is yours.",
        "Find them all. The letters nobody used are the only ones that were talking to you.",
    ]
    flavors = [
        'Cross off everything you recognise. What nobody claims is yours.',
        'An inventory, tangled. The leftovers are the point.',
        "Everything on the list is in there somewhere. Some things aren't on the list.",
    ]
    DIRS = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]

    def can(self, word, ctx=None):
        return bool(ctx and len([w for w in ctx.get("carrier", []) if 4 <= len(w) <= 9]) >= 8)

    def _count(self, grid, w):
        R, C, n = len(grid), len(grid[0]), 0
        for r in range(R):
            for c in range(C):
                for dr, dc in self.DIRS:
                    if all(0 <= r + dr * k < R and 0 <= c + dc * k < C and grid[r + dr * k][c + dc * k] == w[k]
                           for k in range(len(w))):
                        n += 1
        return n if len(w) > 1 and w != w[::-1] else n // 2

    def _placements(self, grid, w):
        R, C = len(grid), len(grid[0])
        for r0 in range(R):
            for c0 in range(C):
                for dr, dc in self.DIRS:
                    cells = [(r0 + dr * k, c0 + dc * k) for k in range(len(w))]
                    if all(0 <= r < R and 0 <= c < C and grid[r][c] in (None, w[k]) for k, (r, c) in enumerate(cells)):
                        new = sum(grid[r][c] is None for r, c in cells)
                        if new:
                            yield cells, new

    def encode(self, word, rng, ctx):
        pool = [w for w in ctx["carrier"] if 4 <= len(w) <= 9 and w not in word and word not in w]
        L = len(word)
        for _ in range(300):
            R = C = rng.choice([7, 8, 8, 9])
            grid = [[None] * C for _ in range(R)]
            placed, empties, misses = [], R * C, 0
            while empties > L:
                need = empties - L
                words = [w for w in pool if w not in placed]
                if not words:
                    break
                if need > 10 and misses < 200:  # cheap random placement while there is plenty of room
                    w = rng.choice(words)
                    dr, dc = rng.choice(self.DIRS)
                    r0, c0 = rng.randrange(R), rng.randrange(C)
                    cells = [(r0 + dr * k, c0 + dc * k) for k in range(len(w))]
                    if not all(0 <= r < R and 0 <= c < C and grid[r][c] in (None, w[k]) for k, (r, c) in enumerate(cells)):
                        misses += 1
                        continue
                    new = sum(grid[r][c] is None for r, c in cells)
                    if not new or need - new < 4:
                        misses += 1
                        continue
                else:  # exhaustive, to land exactly on L leftovers
                    opts = [(w, cells, new) for w in words for cells, new in self._placements(grid, w) if new <= need]
                    if not opts:
                        break
                    exact = [o for o in opts if o[2] == need]
                    w, cells, new = rng.choice(exact or opts)
                for k, (r, c) in enumerate(cells):
                    grid[r][c] = w[k]
                placed.append(w)
                empties -= new
            if empties != L:
                continue
            it = iter(word)
            for r in range(R):
                for c in range(C):
                    if grid[r][c] is None:
                        grid[r][c] = next(it)
            if all(self._count(grid, w) == 1 for w in placed):
                return [{"type": "board", "rows": ["".join(row) for row in grid], "plain": True},
                        {"type": "list", "items": sorted(placed), "inline": True}]
        raise RuntimeError("word search failed")

    def decode(self, blocks, ctx):
        grid = blocks[0]["rows"]
        R, C = len(grid), len(grid[0])
        used = set()
        for w in blocks[1]["items"]:
            for r in range(R):
                for c in range(C):
                    for dr, dc in self.DIRS:
                        cells = [(r + dr * k, c + dc * k) for k in range(len(w))]
                        if all(0 <= y < R and 0 <= x < C and grid[y][x] == w[k] for k, (y, x) in enumerate(cells)):
                            used.update(cells)
        return "".join(grid[r][c] for r in range(R) for c in range(C) if (r, c) not in used)


# --------------------------------------------------------------------------
# Nonogram: the word drawn in a 5x5 pixel font
# --------------------------------------------------------------------------

FONT = {
    "A": ".###.|#...#|#####|#...#|#...#", "B": "####.|#...#|####.|#...#|####.",
    "C": ".####|#....|#....|#....|.####", "D": "####.|#...#|#...#|#...#|####.",
    "E": "#####|#....|####.|#....|#####", "F": "#####|#....|####.|#....|#....",
    "G": ".####|#....|#..##|#...#|.####", "H": "#...#|#...#|#####|#...#|#...#",
    "I": "#####|..#..|..#..|..#..|#####", "J": "..###|...#.|...#.|#..#.|.##..",
    "K": "#...#|#..#.|###..|#..#.|#...#", "L": "#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#...#|#...#", "N": "#...#|##..#|#.#.#|#..##|#...#",
    "O": ".###.|#...#|#...#|#...#|.###.", "P": "####.|#...#|####.|#....|#....",
    "Q": ".###.|#...#|#.#.#|#..#.|.##.#", "R": "####.|#...#|####.|#..#.|#...#",
    "S": ".####|#....|.###.|....#|####.", "T": "#####|..#..|..#..|..#..|..#..",
    "U": "#...#|#...#|#...#|#...#|.###.", "V": "#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#.#.#|##.##|#...#", "X": "#...#|.#.#.|..#..|.#.#.|#...#",
    "Y": "#...#|.#.#.|..#..|..#..|..#..", "Z": "#####|...#.|..#..|.#...|#####",
}
FONT_REV = {v: k for k, v in FONT.items()}


def _runs(line):
    out, n = [], 0
    for v in line:
        if v:
            n += 1
        elif n:
            out.append(n)
            n = 0
    if n:
        out.append(n)
    return out


def _line_options(clues, state):
    """For one line, which cells can be filled / empty given clues and known cells (None = unknown)."""
    n, k = len(state), len(clues)
    memo = {}

    def fits(i, j):  # can cells i.. be completed with blocks j..
        if (i, j) in memo:
            return memo[(i, j)]
        if i >= n:
            res = j == k
        else:
            res = False
            if state[i] != 1 and fits(i + 1, j):
                res = True
            if not res and j < k:
                e = i + clues[j]
                if e <= n and all(state[x] != 0 for x in range(i, e)) and (e == n or state[e] != 1):
                    res = fits(e + 1, j + 1)
        memo[(i, j)] = res
        return res

    can_fill, can_empty = [False] * n, [False] * n
    reach, frontier = {(0, 0)}, [(0, 0)]
    while frontier:
        i, j = frontier.pop()
        if i >= n:
            continue
        if state[i] != 1 and fits(i + 1, j):
            can_empty[i] = True
            if (i + 1, j) not in reach:
                reach.add((i + 1, j))
                frontier.append((i + 1, j))
        if j < k:
            e = i + clues[j]
            if e <= n and all(state[x] != 0 for x in range(i, e)) and (e == n or state[e] != 1) and fits(e + 1, j + 1):
                for x in range(i, e):
                    can_fill[x] = True
                if e < n:
                    can_empty[e] = True
                if (e + 1, j + 1) not in reach:
                    reach.add((e + 1, j + 1))
                    frontier.append((e + 1, j + 1))
    return can_fill, can_empty


def line_solve(rows, cols, givens):
    R, C = len(rows), len(cols)
    g = [[None] * C for _ in range(R)]
    for r, c, v in givens:
        g[r][c] = v
    changed = True
    while changed:
        changed = False
        for r in range(R):
            f, e = _line_options(rows[r], g[r])
            for c in range(C):
                if g[r][c] is None and f[c] != e[c]:
                    g[r][c] = 1 if f[c] else 0
                    changed = True
        for c in range(C):
            col = [g[r][c] for r in range(R)]
            f, e = _line_options(cols[c], col)
            for r in range(R):
                if g[r][c] is None and f[r] != e[r]:
                    g[r][c] = 1 if f[r] else 0
                    changed = True
    return g


class Nonogram(Mechanism):
    weight = 3
    key = "nonogram"
    name = "Nonogram"
    hint = "A nonogram (paint-by-numbers). The filled picture is the answer written in 5×5 block letters."
    easy_flavors = [
        "Paint by numbers. The picture is worth exactly one word.",
        "A mosaic {at} was taken apart tile by tile, and all that was kept was the count of each run.",
        "Fill in the blanks, literally. Some squares have been given to you for free.",
    ]
    flavors = [
        'The picture is worth exactly one word.',
        'Only the count of each run was kept.',
        'Some squares have been given to you for free.',
    ]

    def encode(self, word, rng, ctx):
        C = 6 * len(word) - 1
        pix = [[0] * C for _ in range(5)]
        for k, ch in enumerate(word):
            for r, row in enumerate(FONT[ch].split("|")):
                for c, v in enumerate(row):
                    pix[r][6 * k + c] = 1 if v == "#" else 0
        rows = [_runs(row) for row in pix]
        cols = [_runs([pix[r][c] for r in range(5)]) for c in range(C)]
        givens = []
        while True:
            g = line_solve(rows, cols, givens)
            unknown = [(r, c) for r in range(5) for c in range(C) if g[r][c] is None]
            if not unknown:
                break
            r, c = rng.choice(unknown)
            givens.append((r, c, pix[r][c]))
        return [{"type": "nonogram", "rows": rows, "cols": cols, "givens": [list(x) for x in givens]}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        g = line_solve(b["rows"], b["cols"], [tuple(x) for x in b["givens"]])
        out = ""
        for k in range((len(b["cols"]) + 1) // 6):
            key = "|".join("".join("#" if g[r][6 * k + c] else "." for c in range(5)) for r in range(5))
            out += FONT_REV.get(key, "?")
        return out


# --------------------------------------------------------------------------
# Word puzzles
# --------------------------------------------------------------------------

def _dry_run(mech, word, ctx):
    """Some word puzzles can only be judged feasible by trying to build them."""
    try:
        mech.encode(word, random.Random(0), dict(ctx))
        return True
    except RuntimeError:
        return False


def _minus_one(big, small):
    """If `small` is `big` with exactly one letter removed (as multisets), return that letter."""
    if len(big) != len(small) + 1:
        return None
    rest = list(big)
    for ch in small:
        if ch not in rest:
            return None
        rest.remove(ch)
    return rest[0]


class AnagramExtras(Mechanism):
    key = "anagram_extra"
    name = "Anagrams with an extra letter"
    hint = "Each jumble is an anagram of a word from this round's theme plus one extra letter. The extra letters, in order, spell the answer."
    weight = 3
    easy_flavors = [
        "Everything {at} got thrown in the tumble dryer, and every item came out with a little something extra.",
        "Scrambled inventory. Each entry picked up one hitchhiker on the way through the machine.",
        "Unjumble the kit list. You'll have one letter left over every time, and you'll want to keep those.",
    ]
    flavors = [
        'Everything came out of the wash with a little something extra.',
        'Each entry picked up a hitchhiker on the way.',
        "Tidy up the inventory. You'll have one thing left over every time.",
    ]

    def can(self, word, ctx=None):
        if not ctx or len([w for w in ctx["carrier"] if 5 <= len(w) <= 10]) < len(word) + 3:
            return False
        return _dry_run(self, word, ctx)

    def encode(self, word, rng, ctx):
        pool = [w for w in ctx["carrier"] if 5 <= len(w) <= 10]
        known = set(ctx.get("all_words", [])) | set(pool)
        items, used = [], set()
        for c in word:
            for _ in range(200):
                w = rng.choice(pool)
                if w in used:
                    continue
                letters = list(w + c)
                rng.shuffle(letters)
                jumble = "".join(letters)
                if any(jumble[i:i + 3] in w for i in range(len(jumble) - 2)):
                    continue  # keep it properly scrambled
                # exactly one theme word may explain this jumble
                if [k for k in known if _minus_one(jumble, k)] != [w]:
                    continue
                used.add(w)
                items.append(jumble)
                break
            else:
                raise RuntimeError("no anagram for %s" % c)
        ctx["_anagram_words"] = sorted(known)
        return [{"type": "list", "items": items, "ordered": True, "mono": True}]

    def decode(self, blocks, ctx):
        out = ""
        for j in blocks[0]["items"]:
            hits = [_minus_one(j, k) for k in ctx["_anagram_words"] if _minus_one(j, k)]
            if len(hits) != 1:
                return None
            out += hits[0]
        return out


class MissingLetters(Mechanism):
    key = "missing"
    name = "Missing letters"
    hint = "Each theme word is missing one letter. The missing letters, in order, spell the answer."
    weight = 3
    hard = False
    flavors = [
        "The labels {at} have faded. Each one lost exactly one letter.",
        "Moths got into the inventory: one letter eaten out of every entry.",
        "Fill the gaps. What you fill them with is the point.",
    ]

    def can(self, word, ctx=None):
        return bool(ctx) and _dry_run(self, word, ctx)

    def encode(self, word, rng, ctx):
        pool = [w for w in ctx["carrier"] if len(w) >= 5]
        known = set(ctx.get("all_words", [])) | set(pool)
        items, used = [], set()
        for c in word:
            opts = []
            for w in pool:
                if w in used:
                    continue
                for i, ch in enumerate(w):
                    if ch == c:
                        pat = w[:i] + "_" + w[i + 1:]
                        fills = [k for k in known if len(k) == len(w) and all(a == b or a == "_" for a, b in zip(pat, k))]
                        if fills == [w]:
                            opts.append((w, pat))
            if not opts:
                raise RuntimeError("no gap word for %s" % c)
            w, pat = rng.choice(opts)
            used.add(w)
            items.append(pat)
        ctx["_known"] = sorted(known)
        return [{"type": "list", "items": items, "ordered": True, "mono": True}]

    def decode(self, blocks, ctx):
        out = ""
        for pat in blocks[0]["items"]:
            fills = [k for k in ctx["_known"] if len(k) == len(pat) and all(a == b or a == "_" for a, b in zip(pat, k))]
            if len(fills) != 1:
                return None
            out += fills[0][pat.index("_")]
        return out


class DropQuote(Mechanism):
    key = "dropquote"
    name = "Drop quote"
    hint = "A drop quote: each column's letters (shown alphabetised above it) drop into that column of the grid below. Black squares are spaces; words can wrap between rows. The sentence tells you the answer."
    weight = 3
    allow_transform = False
    easy_flavors = [
        "Somebody shook the sentence and all the letters fell to the bottom of their columns.",
        "The typesetter dropped the tray. Every letter landed in the right column, at least.",
        "Each column remembers what it held, but not in what order.",
    ]
    flavors = [
        'Everything fell straight down, and landed in the right column.',
        'Each column remembers what it held, but not in what order.',
        'A sentence that came loose from its lines.',
    ]

    def encode(self, word, rng, ctx):
        plain = cluephrase(word, rng)
        W = rng.choice([13, 14, 15, 16, 17])
        rows = [plain[i:i + W].ljust(W) for i in range(0, len(plain), W)]
        cols = ["".join(sorted(r[c] for r in rows if r[c] != " ")) for c in range(W)]
        mask = ["".join("#" if ch == " " else "." for ch in r) for r in rows]
        ctx["_plain"] = plain
        return [{"type": "dropquote", "cols": cols, "mask": mask}]

    def decode(self, blocks, ctx):
        b, plain = blocks[0], ctx["_plain"]
        W = len(b["cols"])
        rows = [plain[i:i + W].ljust(W) for i in range(0, len(plain), W)]
        if ["".join(sorted(r[c] for r in rows if r[c] != " ")) for c in range(W)] != b["cols"]:
            return None
        if ["".join("#" if ch == " " else "." for ch in r) for r in rows] != b["mask"]:
            return None
        return phrase_answer(plain)


class Fragments(Mechanism):
    key = "fragments"
    name = "Shredded sentence"
    hint = "The sentence was cut into three-letter fragments (spaces removed) and alphabetised. Reassemble it using the word lengths; it tells you the answer."
    weight = 3
    allow_transform = False
    easy_flavors = [
        "Recovered from the shredder {at}. Somebody at least had the decency to note how long each word was.",
        "Confetti, sorted alphabetically by a very tidy intern. Put it back together.",
        "Three letters to a strip. The strips are in order; the sentence isn't.",
    ]
    flavors = [
        'Shredded, then sorted by a very tidy intern.',
        'Three letters to a strip, and a note of how long each word was.',
        'Confetti, alphabetised.',
    ]

    def encode(self, word, rng, ctx):
        plain = cluephrase(word, rng)
        flat = plain.replace(" ", "")
        chunks = [flat[i:i + 3] for i in range(0, len(flat), 3)]
        ctx["_plain"] = plain
        return [{"type": "list", "items": sorted(chunks), "inline": True},
                {"type": "prose", "text": "Word lengths: (%s)" % " ".join(str(len(w)) for w in plain.split())}]

    def decode(self, blocks, ctx):
        plain = ctx["_plain"]
        flat = plain.replace(" ", "")
        if sorted(flat[i:i + 3] for i in range(0, len(flat), 3)) != blocks[0]["items"]:
            return None
        if blocks[1]["text"] != "Word lengths: (%s)" % " ".join(str(len(w)) for w in plain.split()):
            return None
        return phrase_answer(plain)


# --------------------------------------------------------------------------
# Logic: letter sudoku
# --------------------------------------------------------------------------

def _sudoku_dims(n):
    return (2, 3) if n == 6 else (3, 3)


def sudoku_solve(grid, n, limit=2, rng=None):
    """Count solutions (up to `limit`); grid is a flat list with -1 for blanks. Returns (count, first)."""
    br, bc = _sudoku_dims(n)
    full = (1 << n) - 1
    rows, cols, boxes = [0] * n, [0] * n, [0] * n
    g = list(grid)
    for i, v in enumerate(g):
        if v >= 0:
            r, c = divmod(i, n)
            b = (r // br) * (n // bc) + c // bc
            rows[r] |= 1 << v
            cols[c] |= 1 << v
            boxes[b] |= 1 << v
    found = []

    def rec():
        best, best_mask, best_n = -1, 0, n + 1
        for i, v in enumerate(g):
            if v < 0:
                r, c = divmod(i, n)
                b = (r // br) * (n // bc) + c // bc
                m = full & ~(rows[r] | cols[c] | boxes[b])
                k = bin(m).count("1")
                if k < best_n:
                    best, best_mask, best_n = i, m, k
                    if k <= 1:
                        break
        if best < 0:
            found.append(list(g))
            return len(found) >= limit
        r, c = divmod(best, n)
        b = (r // br) * (n // bc) + c // bc
        vals = [v for v in range(n) if best_mask >> v & 1]
        if rng:
            rng.shuffle(vals)
        for v in vals:
            g[best] = v
            rows[r] |= 1 << v
            cols[c] |= 1 << v
            boxes[b] |= 1 << v
            if rec():
                return True
            rows[r] &= ~(1 << v)
            cols[c] &= ~(1 << v)
            boxes[b] &= ~(1 << v)
            g[best] = -1
        return False

    rec()
    return len(found), (found[0] if found else None)


class LetterSudoku(Mechanism):
    key = "sudoku"
    name = "Letter sudoku"
    hint = "Sudoku using the letters shown instead of digits (each row, column and box uses each letter once). Read the numbered squares in order."
    weight = 3
    easy_flavors = [
        "Every row {at} holds one of everything. So does every column, and every box. Then read the numbered squares.",
        "The quartermaster insists on a perfect distribution: no duplicates, anywhere. The numbered bins are the ones that matter.",
        "A familiar grid, an unfamiliar alphabet.",
    ]
    flavors = [
        'One of everything in every row, column and box. Then read the numbered squares.',
        'A familiar grid, an unfamiliar alphabet.',
        'No duplicates anywhere. The numbered squares are the ones that matter.',
    ]

    def can(self, word, ctx=None):
        return len(set(word)) <= 9

    def encode(self, word, rng, ctx):
        n = 6 if len(set(word)) <= 6 and rng.random() < 0.5 else 9
        letters = sorted(set(word))
        others = [c for c in ALPHA if c not in letters]
        rng.shuffle(others)
        alphabet = sorted(letters + others[:n - len(letters)])
        _, sol = sudoku_solve([-1] * (n * n), n, limit=1, rng=rng)
        shaded = []
        for ch in word:
            v = alphabet.index(ch)
            cells = [i for i in range(n * n) if sol[i] == v and i not in shaded]
            shaded.append(rng.choice(cells))
        grid = list(sol)
        order = shaded + [i for i in rng.sample(range(n * n), n * n) if i not in shaded]
        keep = int(n * n * (0.5 if ctx.get("easy") else 0))  # the hard round goes minimal
        for i in order:
            if sum(v >= 0 for v in grid) <= keep:
                break
            v, grid[i] = grid[i], -1
            if sudoku_solve(grid, n)[0] != 1:
                grid[i] = v
        if any(grid[i] >= 0 for i in shaded):
            raise RuntimeError("shaded square stayed a given")
        rows = ["".join(alphabet[v] if v >= 0 else "." for v in grid[r * n:(r + 1) * n]) for r in range(n)]
        return [{"type": "sudoku", "size": n, "rows": rows, "alphabet": "".join(alphabet),
                 "marks": [[i // n, i % n] for i in shaded]}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        n, alphabet = b["size"], b["alphabet"]
        grid = [alphabet.index(ch) if ch != "." else -1 for row in b["rows"] for ch in row]
        count, sol = sudoku_solve(grid, n)
        if count != 1:
            return None
        return "".join(alphabet[sol[r * n + c]] for r, c in b["marks"])


HUNT_MECHANISMS = [Cryptogram(), RailFence(), BookCipher(), KnightPath(), SignalFlags(),
                   MixedBases(), WordSearch(), Nonogram(), AnagramExtras(), MissingLetters(),
                   DropQuote(), Fragments(), LetterSudoku()]
MECHANISMS = BASE_MECHANISMS + HUNT_MECHANISMS
BY_KEY = {m.key: m for m in MECHANISMS}
