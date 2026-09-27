"""Classic puzzle-hunt feeder types: grids, cluephrases, flags and friends.

Same contract as mechanisms.py: encode() returns render blocks, decode()
recovers the encoded word from those blocks alone, and the generator
round-trips every puzzle before it ships.
"""
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
    key = "cryptogram"
    name = "Cryptogram (cluephrase)"
    hint = "Simple monoalphabetic substitution with word breaks kept. Solve the sentence; it tells you the answer."
    allow_transform = False
    flavors = [
        "Every letter here is wearing someone else's coat. The spaces, at least, are honest.",
        "The newspaper's puzzle page, the one your grandmother did in pen, every single morning.",
        "One alphabet was traded for another, one for one, and nobody bothered to hide where the words begin and end.",
    ]

    def encode(self, word, rng, ctx):
        while True:
            perm = list(ALPHA)
            rng.shuffle(perm)
            if all(a != b for a, b in zip(ALPHA, perm)):
                break
        table = dict(zip(ALPHA, perm))
        plain = cluephrase(word, rng)
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
    key = "railfence"
    name = "Rail fence (cluephrase)"
    hint = "Rail-fence transposition of a sentence with the spaces removed. Try 2 to 5 rails; the sentence tells you the answer."
    allow_transform = False
    NUMS = {2: "two", 3: "three", 4: "four", 5: "five"}
    flavors = [
        "The fence around {place} zigzags between {n} rails. Walk it, don't read it.",
        "Someone wrote this out in a zigzag across {n} lines of the ledger, then copied each line out in turn.",
        "Up and down, up and down: {n} rows, one long sentence, and not a single space left.",
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
    key = "book"
    name = "Book cipher"
    hint = "Each pair is word.letter into the recovered page (words split on spaces; punctuation ignored)."
    flavors = [
        "Only one page of the book survived. Luckily, it was the only page anyone needed.",
        "Numbers in pairs, pencilled in the margin: a page reference is a very old kind of key.",
        "The spy's handbook said to always carry a novel. It never said which one; this page will have to do.",
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
    key = "knight"
    name = "Knight's path"
    hint = "Start on the given square and follow the knight moves; read the letter on each square it lands on."
    flavors = [
        "The knight never moves in a straight line, and neither does the truth {at}.",
        "A board full of noise, and one horseman who knows exactly where to step.",
        "Two forward, one across. Remember where you land.",
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
    flavors = [
        "Run up the halyard at dawn and left there: a string of bunting that isn't meant for decoration.",
        "The harbourmaster says the ship is dressed overall, but that's not what the flags are saying.",
        "Every flag on this line has a meaning on its own. Together, they have one more.",
    ]

    def encode(self, word, rng, ctx):
        return [{"type": "flags", "items": list(word)}]

    def decode(self, blocks, ctx):
        return "".join(blocks[0]["items"])


class MixedBases(Mechanism):
    key = "bases"
    name = "Mixed number bases"
    hint = "Each number is a letter position written in the base shown in its subscript."
    flavors = [
        "An accountant who changes currency every line, but never the amount.",
        "Everyone {at} counts differently. The little number tells you on how many fingers.",
        "Same quantities, many radixes. Convert, then count through the alphabet.",
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
    key = "wordsearch"
    name = "Word search leftovers"
    hint = "Find every listed word (any of 8 directions). The unused letters, read left-to-right, top-to-bottom, spell the answer."
    flavors = [
        "Cross off everything you recognise. What nobody claims is what you came for.",
        "An inventory of {place}, tangled up. Whatever is left over when every item is accounted for is yours.",
        "Find them all. The letters nobody used are the only ones that were talking to you.",
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
    key = "nonogram"
    name = "Nonogram"
    hint = "A nonogram (paint-by-numbers). The filled picture is the answer written in 5×5 block letters."
    flavors = [
        "Paint by numbers. The picture is worth exactly one word.",
        "A mosaic {at} was taken apart tile by tile, and all that was kept was the count of each run.",
        "Fill in the blanks, literally. Some squares have been given to you for free.",
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


HUNT_MECHANISMS = [Cryptogram(), RailFence(), BookCipher(), KnightPath(), SignalFlags(),
                   MixedBases(), WordSearch(), Nonogram()]
MECHANISMS = BASE_MECHANISMS + HUNT_MECHANISMS
BY_KEY = {m.key: m for m in MECHANISMS}
