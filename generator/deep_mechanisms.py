"""Feeders that take more than one idea to crack.

Same contract as mechanisms.py: encode() returns render blocks, decode()
recovers the encoded word from those blocks alone (plus the round's word
list where a puzzle depends on it), and the generator round-trips every
puzzle before it ships.

- Seating plan: a genuine deduction puzzle with exactly one solution, then
  an extraction step (seat k gives the k-th letter of its occupant's name).
- Gapless Morse: theme words in Morse with the letter gaps lost; work out
  which word each line is, then index into it.
- Element spelling: atomic numbers that only make sense as chemical symbols
  spelled out end to end.
- Playfair: the classic digraph cipher, keyed by the puzzle's title.
- Spiral: a sentence laid along a spiral; find the corner and the direction.
"""
import itertools
import random

from hunt_mechanisms import CLUEPHRASES, MECHANISMS as HUNT_MECHANISMS, phrase_answer
from mechanisms import ALPHA, MORSE, Mechanism


def _dry_run(mech, word, ctx):
    try:
        mech.encode(word, random.Random(0), dict(ctx))
        return True
    except RuntimeError:
        return False


# --------------------------------------------------------------------------
# Seating plan
# --------------------------------------------------------------------------

NAMES = """
AARON ABIGAIL ADELINE ADRIAN AGATHA AHMED AIDAN ALBERT ALEXIS ALFRED ALICE ALISTAIR AMARA AMELIA ANDREA
ANDREW ANGELA ANITA ANTHONY ANTONIA ARCHIBALD ARIADNE ARTHUR ASHLEY ASTRID AUBREY AUGUSTA AURELIO BARNABY
BARTHOLOMEW BEATRICE BENEDICT BERNARD BERTRAND BIANCA BRIDGET CAMILLA CASPIAN CATHERINE CECILIA CEDRIC
CHARLES CHARLOTTE CHIARA CLARENCE CLAUDIA CLEMENT CORDELIA CORNELIUS CYPRIAN DAMIAN DANIEL DAPHNE DARIUS
DELPHINE DESMOND DOMINIC DOROTHY DUNCAN EDGAR EDMUND EDWARD ELEANOR ELIJAH ELOISE EMERSON EMILIA ERASMUS
ERNEST ESTELLE EUGENE EVANGELINE EZEKIEL FABIAN FELICITY FERDINAND FIONA FLORENCE FRANCIS FREDERICK
GABRIEL GEMMA GEOFFREY GEORGINA GERALD GERTRUDE GIDEON GILBERT GISELLE GRETA GRISELDA GUSTAV HAMISH HANNAH
HARRIET HECTOR HELENA HENRIETTA HORATIO HUBERT HUMPHREY IGNATIUS IMOGEN INGRID IRENE ISADORA ISAAC ISOBEL
IVANKA JACINTA JASPER JEMIMA JEREMIAH JOCASTA JONATHAN JOSEPHINE JULIAN JULIET JUSTINE KATHLEEN KENDRICK
KIRSTEN LAVINIA LEANDER LEOPOLD LETITIA LORENZO LUCIANA LUDWIG MADELEINE MAGNUS MALCOLM MARGARET MARIGOLD
MATILDA MAXIMILIAN MELANIE MERCEDES MEREDITH MICHAEL MIRANDA MORDECAI MORGANA NATHANIEL NICHOLAS NOEMI
OCTAVIA OLIVER OPHELIA ORLANDO OSWALD PATRICK PENELOPE PERCIVAL PHILIPPA PHINEAS PRISCILLA PRUDENCE
QUENTIN RAPHAEL REGINALD ROSALIND RUPERT SABRINA SAMUEL SEBASTIAN SERAPHINA SIMONE SOLOMON SOPHIA STANLEY
STEPHANIE SYLVESTER TABITHA THADDEUS THEODORE THOMASINA TOBIAS TRISTAN URSULA VALENTINE VERONICA VICTORIA
VIVIENNE WALTER WILHELMINA WINIFRED XANTHE XAVIER YOLANDA YVETTE ZACHARY ZENOBIA ZEPHYR ZOLTAN
""".split()

_ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh"]


def _seat_names(word, rng):
    """Distinct names so that seat k's occupant has word[k] as their k-th letter."""
    options = [[n for n in NAMES if len(n) > k and n[k] == c] for k, c in enumerate(word)]
    if any(not o for o in options):
        return None
    order = sorted(range(len(word)), key=lambda k: len(options[k]))
    chosen = {}

    def dfs(i):
        if i == len(order):
            return True
        k = order[i]
        opts = options[k][:]
        rng.shuffle(opts)
        for n in opts:
            if n not in chosen.values():
                chosen[k] = n
                if dfs(i + 1):
                    return True
                del chosen[k]
        return False

    return [chosen[k] for k in range(len(word))] if dfs(0) else None


def _holds(clue, pos, n):
    """pos: name -> seat (1-based). Clues are tuples so they can be checked and rendered."""
    t = clue[0]
    if t == "at":
        return pos[clue[1]] == clue[2]
    if t == "not_at":
        return pos[clue[1]] != clue[2]
    if t == "right_of":       # X immediately right of Y
        return pos[clue[1]] == pos[clue[2]] + 1
    if t == "beside":
        return abs(pos[clue[1]] - pos[clue[2]]) == 1
    if t == "apart":
        return abs(pos[clue[1]] - pos[clue[2]]) != 1
    if t == "left_of":        # X somewhere left of Y
        return pos[clue[1]] < pos[clue[2]]
    if t == "end":
        return pos[clue[1]] in (1, n)
    if t == "between":        # Y strictly between X and Z
        a, b, c = pos[clue[1]], pos[clue[2]], pos[clue[3]]
        return min(a, c) < b < max(a, c)
    if t == "gap":            # exactly k people between X and Y
        return abs(pos[clue[1]] - pos[clue[2]]) == clue[3] + 1
    raise ValueError(t)


def _say(clue, n):
    t, x = clue[0], clue[1].title()
    if t == "at":
        return "%s has seat %d." % (x, clue[2])
    if t == "not_at":
        return "%s is not in seat %d." % (x, clue[2])
    if t == "right_of":
        return "%s sits immediately to the right of %s." % (x, clue[2].title())
    if t == "beside":
        return "%s and %s sit side by side." % (x, clue[2].title())
    if t == "apart":
        return "%s and %s are not neighbours." % (x, clue[2].title())
    if t == "left_of":
        return "%s sits somewhere to the left of %s." % (x, clue[2].title())
    if t == "end":
        return "%s has an end seat." % x
    if t == "between":
        return "%s sits somewhere between %s and %s." % (clue[2].title(), x, clue[3].title())
    if t == "gap":
        k = clue[3]
        return "Exactly %s between %s and %s." % ("one person sits" if k == 1 else "%d people sit" % k, x, clue[2].title())
    raise ValueError(t)


def _all_true_clues(names, pos, n, anchors):
    out = []
    for x in names:
        if anchors:
            out.append(("at", x, pos[x]))
        for s in range(1, n + 1):
            if s != pos[x]:
                out.append(("not_at", x, s))
        if pos[x] in (1, n):
            out += [("end", x)] * 2
    for x, y in itertools.permutations(names, 2):
        if pos[x] == pos[y] + 1:
            out += [("right_of", x, y)] * 2
        if pos[x] < pos[y]:
            out.append(("left_of", x, y))
        if x < y:
            out.append(("beside", x, y) if abs(pos[x] - pos[y]) == 1 else ("apart", x, y))
            g = abs(pos[x] - pos[y]) - 1
            if 1 <= g <= n - 3:
                out += [("gap", x, y, g)] * 2
    for x, y, z in itertools.permutations(names, 3):
        if x < z and min(pos[x], pos[z]) < pos[y] < max(pos[x], pos[z]):
            out += [("between", x, y, z)] * 2
    return out


def seating_solutions(names, clues, limit=2):
    n, found = len(names), []
    for perm in itertools.permutations(range(1, n + 1)):
        pos = dict(zip(names, perm))
        if all(_holds(c, pos, n) for c in clues):
            found.append(pos)
            if len(found) >= limit:
                break
    return found


class SeatingPlan(Mechanism):
    key = "seating"
    name = "Seating plan (logic)"
    hint = ("A logic puzzle: use the clues to find the one seating that works (seats are numbered 1 to n from the left). "
            "Then the guest in seat k gives the k-th letter of their name.")
    weight = 3
    allow_transform = False
    easy_flavors = [
        "The host {at} fussed over the seating plan for days. Every guest pays for their chair with one letter of their name: the further along the row, the deeper into the name.",
        "Seat them correctly first. Then each guest owes you the letter of their name that matches their seat number.",
        "Place cards, a long table and a host who counts: seat one, first letter; seat two, second letter; and so on down the row.",
    ]
    flavors = [
        "The host was particular about the seating, and more particular still about what each chair was worth.",
        "Everyone has a place. Everyone pays for it in their own name.",
        "One table, one arrangement that offends nobody, and a toll that rises seat by seat.",
    ]

    def can(self, word, ctx=None):
        return 4 <= len(word) <= 7 and len(set(word)) >= 2 and _seat_names(word, random.Random(0)) is not None

    def encode(self, word, rng, ctx):
        n = len(word)
        names = _seat_names(word, rng)
        if not names:
            raise RuntimeError("no names for %s" % word)
        pos = {nm: k + 1 for k, nm in enumerate(names)}
        level = ctx.get("level", "hard")
        perms = [dict(zip(names, p)) for p in itertools.permutations(range(1, n + 1))]
        for _ in range(40):
            pool = _all_true_clues(names, pos, n, anchors=level != "hard")
            rng.shuffle(pool)
            clues, live = [], perms
            for c in pool:
                if c in clues or (c[0] == "at" and any(x[0] == "at" for x in clues)):
                    continue
                nxt = [p for p in live if _holds(c, p, n)]
                if len(nxt) < len(live):
                    clues.append(c)
                    live = nxt
                if len(live) == 1:
                    break
            if len(live) != 1:
                continue
            # Drop any clue the others already imply, so every line earns its place.
            for c in clues[:]:
                rest = [x for x in clues if x is not c]
                if len([p for p in perms if all(_holds(x, p, n) for x in rest)]) == 1:
                    clues = rest
            if len(clues) <= n + 4:
                break
        else:
            raise RuntimeError("no seating clue set")
        shown = names[:]
        rng.shuffle(shown)
        return [{"type": "seating", "seats": n, "names": [x.title() for x in shown],
                 "clues": [_say(c, n) for c in clues], "logic": [list(c) for c in clues]}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        names = [x.upper() for x in b["names"]]
        clues = [tuple(c) for c in b["logic"]]
        if [_say(c, b["seats"]) for c in clues] != b["clues"]:
            return None
        sols = seating_solutions(names, clues)
        if len(sols) != 1:
            return None
        pos = sols[0]
        by_seat = {s: nm for nm, s in pos.items()}
        return "".join(by_seat[k][k - 1] for k in range(1, b["seats"] + 1))


# --------------------------------------------------------------------------
# Gapless Morse
# --------------------------------------------------------------------------

def gapless(word):
    return "".join(MORSE[c] for c in word)


class GaplessMorse(Mechanism):
    key = "morse_gapless"
    name = "Gapless Morse"
    hint = ("Each line is a word from this round's theme in Morse code with the gaps between letters lost. "
            "Work out which word fits the dots, dashes and letter count, then take the letter at the position shown.")
    weight = 2
    easy_flavors = [
        "The telegraphist {at} never paused between letters. You'll have to work out where one ends and the next begins, and the word bank will help.",
        "Every line is a word you'd expect {at}, keyed without a single gap. Find the word, then take the letter the number points to.",
        "Short, long, short: no spaces. Match each run to a word from the list, then count along it.",
    ]
    flavors = [
        "The operator never once took a breath.",
        "Every word ran into itself. The little numbers know where to look.",
        "Rhythm without rests, and a finger pointing into each line.",
    ]

    def _bank_size(self, ctx):
        return {"easy": 4, "medium": 4}.get(ctx.get("level", "hard"), 0)

    def can(self, word, ctx=None):
        if not ctx or not 4 <= len(word) <= 8:
            return False
        return _dry_run(self, word, ctx)

    def encode(self, word, rng, ctx):
        lexicon = sorted(set(ctx.get("all_words", [])))
        pool = [w for w in ctx["carrier"] if 4 <= len(w) <= 9]
        decoys = self._bank_size(ctx)

        def unique(w, among):
            return [x for x in among if len(x) == len(w) and gapless(x) == gapless(w)] == [w]

        for _ in range(60):
            used, lines = set(), []
            for c in word:
                opts = [(w, j) for w in pool if w not in used and unique(w, lexicon)
                        for j, ch in enumerate(w) if ch == c]
                if not opts:
                    break
                w, j = rng.choice(opts)
                used.add(w)
                lines.append((w, j + 1))
            if len(lines) == len(word):
                break
        else:
            raise RuntimeError("no gapless morse lines")
        items = [{"code": gapless(w), "len": len(w), "index": j} for w, j in lines]
        block = {"type": "morselines", "items": items}
        if decoys:
            extra = [w for w in pool if w not in used]
            rng.shuffle(extra)
            block["bank"] = sorted([w for w, _ in lines] + extra[:decoys])
        return [block]

    def decode(self, blocks, ctx):
        b = blocks[0]
        among = b.get("bank") or sorted(set(ctx.get("all_words", [])))
        out = ""
        for it in b["items"]:
            fits = [w for w in among if len(w) == it["len"] and gapless(w) == it["code"]]
            if len(fits) != 1:
                return None
            out += fits[0][it["index"] - 1]
        return out


# --------------------------------------------------------------------------
# Element spelling
# --------------------------------------------------------------------------

SYMBOLS = ("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr "
           "Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb "
           "Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf "
           "Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()
assert len(SYMBOLS) == 118
_SYM_NUM = {s.upper(): i + 1 for i, s in enumerate(SYMBOLS)}


def element_parses(word, limit=50):
    """Every way to write `word` as consecutive element symbols (as lists of atomic numbers)."""
    out = []

    def go(i, acc):
        if len(out) >= limit:
            return
        if i == len(word):
            out.append(acc)
            return
        for L in (1, 2):
            s = word[i:i + L]
            if len(s) == L and s in _SYM_NUM:
                go(i + L, acc + [_SYM_NUM[s]])

    go(0, [])
    return out


class ElementSpelling(Mechanism):
    key = "element_spell"
    name = "Element spelling"
    hint = "Each number is an atomic number. Write down each element's chemical symbol and read the symbols together as one word."
    weight = 2
    easy_flavors = [
        "The chemist {at} spelled the word out with the periodic table, one or two letters at a time.",
        "Look up each atomic number, keep the symbol, and run the symbols together.",
        "Some numbers here are far too big for the alphabet. They're not too big for the periodic table.",
    ]
    flavors = [
        "Some of these are far too big to be letters.",
        "A shopping list for a very small, very specific chemist.",
        "Matter, counted, and then spelled.",
    ]

    def can(self, word, ctx=None):
        parses = element_parses(word)
        # Needs at least one number above 26, or it reads as A1Z26 and that's a different puzzle.
        return any(any(n > 26 for n in p) for p in parses)

    def encode(self, word, rng, ctx):
        parses = [p for p in element_parses(word) if any(n > 26 for n in p)]
        p = rng.choice(parses)
        return [{"type": "numbers", "items": p, "tray": 2}]

    def decode(self, blocks, ctx):
        return "".join(SYMBOLS[n - 1].upper() for n in blocks[0]["items"])


# --------------------------------------------------------------------------
# Playfair keyed by the title
# --------------------------------------------------------------------------

def playfair_square(key):
    seen = []
    for c in (key.upper().replace("J", "I") + ALPHA):
        if c in ALPHA and c != "J" and c not in seen:
            seen.append(c)
    return seen  # 25 letters, row-major 5x5


def playfair_prepare(text):
    t = [c for c in text.upper().replace("J", "I") if c in ALPHA]
    out, i = [], 0
    while i < len(t):
        a = t[i]
        b = t[i + 1] if i + 1 < len(t) else None
        if b is None or a == b:
            out += [a, "Q" if a == "X" else "X"]
            i += 1
        else:
            out += [a, b]
            i += 2
    return "".join(out)


def _playfair(text, square, d):
    where = {c: divmod(i, 5) for i, c in enumerate(square)}
    out = ""
    for i in range(0, len(text), 2):
        (r1, c1), (r2, c2) = where[text[i]], where[text[i + 1]]
        if r1 == r2:
            out += square[r1 * 5 + (c1 + d) % 5] + square[r2 * 5 + (c2 + d) % 5]
        elif c1 == c2:
            out += square[((r1 + d) % 5) * 5 + c1] + square[((r2 + d) % 5) * 5 + c2]
        else:
            out += square[r1 * 5 + c2] + square[r2 * 5 + c1]
    return out


class Playfair(Mechanism):
    key = "playfair"
    name = "Playfair keyed by the title"
    hint = ("Playfair cipher. Build the 5×5 square from this puzzle's title (letters only, I and J share a cell, no repeats), "
            "then the rest of the alphabet. Decrypt in pairs; X (or Q) was slipped between doubled letters and at the end.")
    weight = 2
    easy = False
    medium = False
    allow_transform = False
    flavors = [
        "Everything travels in pairs here, and no pair is ever a twin.",
        "Lord Playfair's friend got the credit, but the square is built from whatever is written above it.",
        "Two by two, out of a square that the heading laid out.",
    ]

    def can(self, word, ctx=None):
        return "J" not in word  # titles are assigned later, and every title has letters to key with

    def encode(self, word, rng, ctx):
        plain = rng.choice([t for t in CLUEPHRASES if "J" not in t.replace("{W}", "")]).replace("{W}", word)
        prepared = playfair_prepare(plain)
        ct = _playfair(prepared, playfair_square(ctx["title"]), 1)
        ctx["_plain"], ctx["_prepared"] = plain, prepared
        return [{"type": "mono", "text": " ".join(ct[i:i + 2] for i in range(0, len(ct), 2)), "wide": True}]

    def decode(self, blocks, ctx):
        ct = blocks[0]["text"].replace(" ", "")
        if _playfair(ct, playfair_square(ctx["title"]), -1) != ctx["_prepared"]:
            return None
        return phrase_answer(ctx["_plain"])


# --------------------------------------------------------------------------
# Spiral route
# --------------------------------------------------------------------------

def spiral_path(R, C, corner, clockwise):
    """Cells of an R x C grid, spiralling inward from a corner (0 TL, 1 TR, 2 BR, 3 BL)."""
    right, down, left, up = (0, 1), (1, 0), (0, -1), (-1, 0)
    order = [right, down, left, up] if clockwise else [right, up, left, down]
    first = ([right, down, left, up] if clockwise else [down, left, up, right])[corner]
    di = order.index(first)
    r, c = [(0, 0), (0, C - 1), (R - 1, C - 1), (R - 1, 0)][corner]
    seen, path = set(), []
    for _ in range(R * C):
        path.append((r, c))
        seen.add((r, c))
        for turn in range(4):
            dr, dc = order[(di + turn) % 4]
            if 0 <= r + dr < R and 0 <= c + dc < C and (r + dr, c + dc) not in seen:
                di = (di + turn) % 4
                r, c = r + dr, c + dc
                break
    return path


class Spiral(Mechanism):
    key = "spiral"
    name = "Spiral route"
    hint = ("A sentence was written into the grid along a spiral, starting in one corner and winding inward. "
            "Find the corner and the direction, read the sentence (dots are padding), and it tells you the answer.")
    weight = 2
    allow_transform = False
    easy_flavors = [
        "The note {at} was written round and round the page, from the edge towards the middle.",
        "Start in a corner, follow the edge, and keep turning inward. Which corner, and which way, is up to you to find.",
        "A snail's route through the letters: around the outside first, then tighter and tighter.",
    ]
    flavors = [
        "A snail wrote this.",
        "It goes round and round, and only gets anywhere in the middle.",
        "Around the edges first; the point comes last.",
    ]

    def encode(self, word, rng, ctx):
        plain = rng.choice(CLUEPHRASES).replace("{W}", word).replace(" ", "")
        L = len(plain)
        for _ in range(50):
            C = rng.choice(range(max(5, int(L ** 0.5)), int(L ** 0.5) + 4))
            R = -(-L // C)
            if R * C - L > C:
                continue
            corner, cw = rng.randrange(4), rng.random() < 0.5
            grid = [["·"] * C for _ in range(R)]
            for ch, (r, c) in zip(plain, spiral_path(R, C, corner, cw)):
                grid[r][c] = ch
            rows = ["".join(row) for row in grid]
            reads = {self._read(rows, k, d) for k in range(4) for d in (True, False)}
            if len([x for x in reads if x]) == 1:  # exactly one route reads as a sentence
                ctx["_plain"] = plain
                return [{"type": "lettergrid", "rows": rows}]
        raise RuntimeError("no spiral")

    @staticmethod
    def _read(rows, corner, cw):
        R, C = len(rows), len(rows[0])
        text = "".join(rows[r][c] for r, c in spiral_path(R, C, corner, cw)).rstrip("·")
        return phrase_answer(text) if "·" not in text else None

    def decode(self, blocks, ctx):
        rows = blocks[0]["rows"]
        got = {self._read(rows, k, d) for k in range(4) for d in (True, False)} - {None}
        return got.pop() if len(got) == 1 else None


DEEP_MECHANISMS = [SeatingPlan(), GaplessMorse(), ElementSpelling(), Playfair(), Spiral()]
MECHANISMS = HUNT_MECHANISMS + DEEP_MECHANISMS
BY_KEY = {m.key: m for m in MECHANISMS}
