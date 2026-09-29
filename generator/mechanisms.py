"""Encoding mechanisms for feeder puzzles.

Every mechanism turns a word into a list of render "blocks" (consumed by
docs/app.js) and can decode those same blocks back into the word. The
generator round-trips every puzzle through decode() so a broken encoding
can never ship.
"""
import string

ALPHA = string.ascii_uppercase

# --------------------------------------------------------------------------
# Reference tables
# --------------------------------------------------------------------------

# NCBI standard genetic code, bases in TCAG order.
_GENETIC = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
_BASES = "TCAG"
CODON_TO_AA = {}
AA_TO_CODONS = {}
for _i, _aa in enumerate(_GENETIC):
    _c = _BASES[_i // 16] + _BASES[(_i // 4) % 4] + _BASES[_i % 4]
    CODON_TO_AA[_c] = _aa
    if _aa != "*":
        AA_TO_CODONS.setdefault(_aa, []).append(_c)
BASE_BITS = {"A": "00", "C": "01", "G": "10", "T": "11"}
BITS_BASE = {v: k for k, v in BASE_BITS.items()}
COMPLEMENT = {"A": "T", "T": "A", "C": "G", "G": "C"}

MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
}
MORSE_REV = {v: k for k, v in MORSE.items()}

# Flag semaphore as two arm directions, 0 = N (up), clockwise in 45° steps,
# seen from the observer's side.
SEMAPHORE = {
    "A": (4, 5), "B": (4, 6), "C": (4, 7), "D": (4, 0), "E": (4, 1), "F": (4, 2), "G": (4, 3),
    "H": (5, 6), "I": (5, 7), "K": (5, 0), "L": (5, 1), "M": (5, 2), "N": (5, 3),
    "O": (6, 7), "P": (6, 0), "Q": (6, 1), "R": (6, 2), "S": (6, 3),
    "T": (7, 0), "U": (7, 1), "Y": (7, 2),
    "J": (0, 2), "V": (0, 3),
    "W": (1, 2), "X": (1, 3),
    "Z": (2, 3),
}
SEMAPHORE_REV = {frozenset(v): k for k, v in SEMAPHORE.items()}

BRAILLE_DOTS = {
    "A": "1", "B": "12", "C": "14", "D": "145", "E": "15", "F": "124", "G": "1245",
    "H": "125", "I": "24", "J": "245", "K": "13", "L": "123", "M": "134", "N": "1345",
    "O": "135", "P": "1234", "Q": "12345", "R": "1235", "S": "234", "T": "2345",
    "U": "136", "V": "1236", "W": "2456", "X": "1346", "Y": "13456", "Z": "1356",
}
BRAILLE_VAL = {k: sum(1 << (int(d) - 1) for d in v) for k, v in BRAILLE_DOTS.items()}
BRAILLE_REV = {v: k for k, v in BRAILLE_VAL.items()}

ELEMENTS = [
    "hydrogen", "helium", "lithium", "beryllium", "boron", "carbon", "nitrogen",
    "oxygen", "fluorine", "neon", "sodium", "magnesium", "aluminium", "silicon",
    "phosphorus", "sulfur", "chlorine", "argon", "potassium", "calcium",
    "scandium", "titanium", "vanadium", "chromium", "manganese", "iron",
]

KEYPAD = {"2": "ABC", "3": "DEF", "4": "GHI", "5": "JKL", "6": "MNO",
          "7": "PQRS", "8": "TUV", "9": "WXYZ"}
DTMF_ROW = {"1": 697, "2": 697, "3": 697, "4": 770, "5": 770, "6": 770,
            "7": 852, "8": 852, "9": 852}
DTMF_COL = {"1": 1209, "4": 1209, "7": 1209, "2": 1336, "5": 1336, "8": 1336,
            "3": 1477, "6": 1477, "9": 1477}
DTMF_REV = {(DTMF_ROW[k], DTMF_COL[k]): k for k in DTMF_ROW}

NATO = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel",
        "India", "Juliett", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa",
        "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey",
        "X-ray", "Yankee", "Zulu"]

TAP_GRID = ["ABCDE", "FGHIJ", "LMNOP", "QRSTU", "VWXYZ"]

QWERTY = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]

RESISTOR = ["black", "brown", "red", "orange", "yellow", "green", "blue",
            "violet", "grey", "white"]

PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61,
          67, 71, 73, 79, 83, 89, 97, 101]


def roman(n):
    out = ""
    for v, s in [(100, "C"), (90, "XC"), (50, "L"), (40, "XL"), (10, "X"),
                 (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            out += s
            n -= v
    return out


def unroman(s):
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total = 0
    for i, ch in enumerate(s):
        v = vals[ch]
        if i + 1 < len(s) and vals[s[i + 1]] > v:
            total -= v
        else:
            total += v
    return total


def idx(ch):
    return ALPHA.index(ch)


# --------------------------------------------------------------------------
# Pre-transforms (an optional extra layer applied before encoding)
# --------------------------------------------------------------------------

TRANSFORMS = {
    "atbash": {
        "fn": lambda w: "".join(ALPHA[25 - idx(c)] for c in w),
        "inv": lambda w: "".join(ALPHA[25 - idx(c)] for c in w),
        "hints": [
            "Something in here has been through the looking glass.",
            "Alpha and Omega traded places before this was written down.",
            "Whoever transcribed it held the alphabet up to a mirror.",
        ],
        "name": "Atbash (A↔Z mirror)",
    },
    "reverse": {
        "fn": lambda w: w[::-1],
        "inv": lambda w: w[::-1],
        "hints": [
            "The tape was spooled back onto the wrong reel.",
            "Whatever you find, it was said on the way out, not the way in.",
            "Start from the end; that's where it started.",
        ],
        "name": "Reversal",
    },
    "rot13": {
        "fn": lambda w: "".join(ALPHA[(idx(c) + 13) % 26] for c in w),
        "inv": lambda w: "".join(ALPHA[(idx(c) + 13) % 26] for c in w),
        "hints": [
            "Half a turn of the wheel and you'd have it.",
            "A baker's dozen steps separate this from the truth, in either direction.",
            "Unlucky for some: the letters were all nudged by the same unlucky amount.",
        ],
        "name": "ROT13",
    },
}


# --------------------------------------------------------------------------
# Mechanisms
# --------------------------------------------------------------------------

class Mechanism:
    key = ""
    name = ""
    hint = ""
    flavors = []        # hard round: oblique
    easy_flavors = []   # easy round: more direct (falls back to flavors)
    allow_transform = True
    weight = 1      # relative pick frequency; word/logic puzzles are weighted up
    easy = True     # allowed in the easy round
    medium = True   # allowed in the medium round
    hard = True     # allowed in the hard round

    def can(self, word, ctx=None):
        return all(c in ALPHA for c in word)

    def encode(self, word, rng, ctx):
        raise NotImplementedError

    def decode(self, blocks, ctx):
        raise NotImplementedError


class DnaBinary(Mechanism):
    easy = False
    medium = False
    key = "dna_binary"
    name = "Binary codons"
    hint = "Pairs of bits are nucleotides (A=00, C=01, G=10, T=11). Six bits = one codon; translate codons to amino-acid one-letter codes."
    easy_flavors = [
        "Life keeps its books in a four-letter ledger. The machines that copied this one could only count to two, and they insisted on reading everything in threes.",
        "Every rung of the ladder became a pair of switches. {Crew} swear that, three rungs at a time, something begins to fold.",
        "The sequencer {at} ran out of ink and fell back to its native tongue. Its alphabet has four letters; its vocabulary, sixty-four words.",
    ]
    flavors = [
        'Somewhere between the lab and the server room, four became two, and two became three.',
        "It isn't text. It was never text. It was always going to fold into something.",
        "The machine keeps its diary in your cells' alphabet, if your cells could only say yes or no.",
    ]

    def can(self, word, ctx=None):
        return all(c in AA_TO_CODONS for c in word)

    def encode(self, word, rng, ctx):
        groups = []
        for c in word:
            codon = rng.choice(AA_TO_CODONS[c])
            groups.append("".join(BASE_BITS[b] for b in codon))
        return [{"type": "mono", "text": " ".join(groups)}]

    def decode(self, blocks, ctx):
        out = ""
        for g in blocks[0]["text"].split():
            codon = "".join(BITS_BASE[g[i:i + 2]] for i in range(0, 6, 2))
            out += CODON_TO_AA[codon]
        return out


class DnaTemplate(Mechanism):
    easy = False
    medium = False
    key = "dna_template"
    name = "Template strand"
    hint = "This is the template (antisense) strand written 5′→3′. Reverse-complement it to get the coding strand, then translate codons to amino-acid one-letter codes."
    easy_flavors = [
        "We only kept the strand nobody reads. Find its partner, turn it around, and let the ribosome do the rest.",
        "The photograph {at} was of the negative, and the negative was hung upside down.",
        "Recovered: the wrong half of a helix, carefully labelled from head to tail.",
    ]
    flavors = [
        'We kept the wrong half, and we kept it backwards.',
        'A negative, hung upside down, of something that only reads in threes.',
        'Half a ladder, read from the far end.',
    ]

    def can(self, word, ctx=None):
        return all(c in AA_TO_CODONS for c in word)

    def encode(self, word, rng, ctx):
        coding = "".join(rng.choice(AA_TO_CODONS[c]) for c in word)
        template = "".join(COMPLEMENT[b] for b in reversed(coding))
        return [{"type": "mono", "text": "5′–" + template + "–3′"}]

    def decode(self, blocks, ctx):
        t = blocks[0]["text"][3:-3]
        coding = "".join(COMPLEMENT[b] for b in reversed(t))
        return "".join(CODON_TO_AA[coding[i:i + 3]] for i in range(0, len(coding), 3))


class Morse(Mechanism):
    key = "morse"
    name = "Morse code"
    hint = "Morse code: two symbols stand for dot and dash; gaps separate letters."
    easy_flavors = [
        "{Crew} tapped this out against the hull: short, long, and the silence in between.",
        "Two kinds of thing kept passing {at}, in an order that felt far too deliberate.",
        "Samuel would have recognised the rhythm at once, whatever it happened to be wearing.",
    ]
    flavors = [
        'Some visitors stayed briefly; others lingered.',
        'Two kinds of footprint on the sand, in no particular hurry.',
        'Listen to the rhythm, not the picture.',
    ]
    VARIANTS = {
        "lamp": ("Morse code (signal lamp)", "Morse code: short flashes are dots, long flashes are dashes; each row is a letter.", [
            "A light on the far shore that refuses to stay on.",
            "Someone across the water is impatient, and has a lamp.",
        ]),
        "audio": ("Morse code (audio)", "Morse code, played as beeps. Short = dot, long = dash; longer silences separate letters.", [
            "Static, then something that isn't static.",
            "Turn it up. It's saying something, just not in words.",
        ]),
    }

    def encode(self, word, rng, ctx):
        variant = rng.choice(["glyphs", "glyphs", "lamp", "audio"])
        if variant != "glyphs":
            ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.VARIANTS[variant]
            groups = [MORSE[c] for c in word]
            if variant == "lamp":
                return [{"type": "lamp", "groups": groups}]
            return [{"type": "audio", "kind": "morse", "groups": groups}]
        dot, dash = ctx["glyphs"]["dot"], ctx["glyphs"]["dash"]
        if rng.random() < 0.5:
            dot, dash = dash, dot  # which glyph is the dot is part of the puzzle
        letters = ["".join(dot if s == "." else dash for s in MORSE[c]) for c in word]
        return [{"type": "glyphs", "groups": letters, "legend": [dot, dash]}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        if b["type"] in ("lamp", "audio"):
            return "".join(MORSE_REV[g] for g in b["groups"])
        for dot, dash in (b["legend"], b["legend"][::-1]):
            out = ""
            for g in b["groups"]:
                code = g.replace(dot, ".").replace(dash, "-")
                if code not in MORSE_REV:
                    break
                out += MORSE_REV[code]
            else:
                if out == ctx.get("expect", out):
                    return out
        return None


class Semaphore(Mechanism):
    key = "semaphore"
    name = "Semaphore clocks"
    hint = "Each clock's two hands are the two arms of a flag-semaphore signaller (hand length doesn't matter)."
    easy_flavors = [
        "Every clock {at} stopped at a different moment, and not one of them can agree which hand is which.",
        "A signaller with no flags and no sense of time left these behind.",
        "The hands aren't telling the time. They're waving.",
    ]
    flavors = [
        'None of these clocks is broken. None of them tells the time.',
        'Every one stopped at a different moment, and none can agree which hand is which.',
        'Stopped hands, raised arms.',
    ]
    COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    VARIANTS = {
        "bearings": ("Semaphore (compass bearings)", "Flag semaphore, with each arm given as a compass direction as you face the signaller (N = straight up).", [
            "Two directions at a time, and never a destination.",
            "The navigator keeps pointing two ways at once.",
        ]),
        "figures": ("Semaphore (figures)", "Flag semaphore: read each figure's arm positions.", [
            "Someone on the pier is trying very hard to get your attention.",
            "Arms out, arms up, arms down: a dance with no music.",
        ]),
    }

    def encode(self, word, rng, ctx):
        variant = rng.choice(["clocks", "bearings", "figures"])
        items = []
        for c in word:
            a, b = SEMAPHORE[c]
            items.append([a, b] if rng.random() < 0.5 else [b, a])
        if variant == "clocks":
            return [{"type": "clocks", "items": items}]
        ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.VARIANTS[variant]
        if variant == "bearings":
            return [{"type": "list", "items": ["%s & %s" % (self.COMPASS[a], self.COMPASS[b]) for a, b in items], "inline": True}]
        return [{"type": "semaphore", "items": items}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        if b["type"] == "list":
            pairs = [[self.COMPASS.index(x) for x in it.split(" & ")] for it in b["items"]]
        else:
            pairs = b["items"]
        return "".join(SEMAPHORE_REV[frozenset(p)] for p in pairs)


class BrailleDecimal(Mechanism):
    key = "braille"
    name = "Braille as numbers"
    hint = "Each number is a 6-bit value: bit k set means Braille dot k+1 is raised (dot 1 = 1, dot 2 = 2, dot 3 = 4, dot 4 = 8, ...)."
    easy_flavors = [
        "Room numbers from a hotel where every guest reads with their fingertips.",
        "These readings came from a sensor with six raised pins. It reports in powers of two, and it reports in order.",
        "Sixty-four ways to press a fingertip into paper. Louis numbered his from one to six; we just added them up.",
    ]
    flavors = [
        'Room numbers in a hotel where nobody reads with their eyes.',
        "Small numbers, none above sixty-three. What matters is what's raised.",
        'Every value here was once something you could touch.',
    ]
    VARIANTS = {
        "bits": ("Braille as bit strings", "Six-bit strings: the k-th character is 1 if Braille dot k is raised (dots 1-2-3 down the left, 4-5-6 down the right).", [
            "Six switches at a time, some pressed, some not.",
            "A sensor that only knows up and down, six times over.",
        ]),
        "cells": ("Braille (drawn)", "Braille cells, drawn as raised and flat dots.", [
            "Rubbings from a handrail.",
            "Bumps on a lift button, copied carefully.",
        ]),
    }

    def encode(self, word, rng, ctx):
        variant = rng.choice(["numbers", "bits", "cells"])
        if variant == "numbers":
            return [{"type": "numbers", "items": [BRAILLE_VAL[c] for c in word]}]
        ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.VARIANTS[variant]
        bits = ["".join("1" if str(d) in BRAILLE_DOTS[c] else "0" for d in range(1, 7)) for c in word]
        if variant == "bits":
            return [{"type": "list", "items": bits, "inline": True}]
        return [{"type": "braille", "items": bits}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        if b["type"] == "numbers":
            return "".join(BRAILLE_REV[n] for n in b["items"])
        return "".join(BRAILLE_REV[int(x[::-1], 2)] for x in b["items"])


class Elements(Mechanism):
    key = "elements"
    name = "Atomic numbers"
    hint = "Each element's atomic number is a letter position (hydrogen = 1 = A)."
    easy_flavors = [
        "An inventory from the stores {at}, listed by order of arrival rather than by weight.",
        "Mendeleev would have lined these up by number without a second thought.",
        "The chemist only ever shopped from the first twenty-six shelves.",
    ]
    flavors = [
        'An inventory of the stores, in order of arrival.',
        'Only the first shelves of the cabinet were ever opened.',
        'The smallest things there are, listed by rank.',
    ]
    SYMBOLS = ["H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P",
               "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe"]
    MASSES = ["1.008", "4.003", "6.94", "9.012", "10.81", "12.011", "14.007", "15.999", "18.998",
              "20.180", "22.990", "24.305", "26.982", "28.085", "30.974", "32.06", "35.45", "39.95",
              "39.098", "40.078", "44.956", "47.867", "50.942", "51.996", "54.938", "55.845"]
    VARIANTS = {
        "symbols": ("Atomic numbers (symbols)", "Element symbols; each atomic number is a letter position (H = 1 = A).", [
            "Labels peeled from bottles, in the order they were used.",
            "A formula no chemist would sign.",
        ]),
        "masses": ("Atomic numbers (by mass)", "Standard atomic masses: identify each element, then use its atomic number as a letter position.", [
            "Everything here has been weighed, not counted.",
            "The scale is very precise; the list is very short.",
        ]),
    }

    def encode(self, word, rng, ctx):
        variant = rng.choice(["names", "symbols", "masses"])
        if variant == "names":
            return [{"type": "list", "items": [ELEMENTS[idx(c)] for c in word]}]
        ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.VARIANTS[variant]
        table = self.SYMBOLS if variant == "symbols" else self.MASSES
        return [{"type": "list", "items": [table[idx(c)] for c in word], "inline": True, "variant": variant}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        table = {"symbols": self.SYMBOLS, "masses": self.MASSES}.get(b.get("variant"), ELEMENTS)
        return "".join(ALPHA[table.index(e)] for e in b["items"])


class Dtmf(Mechanism):
    key = "dtmf"
    name = "DTMF multi-tap"
    hint = "Each frequency pair is a phone keypad key (DTMF). The ×n is how many times it was pressed: old-school multi-tap texting."
    easy_flavors = [
        "Recovered from an old answering machine: two notes at once, some pressed more insistently than others.",
        "Before phones were smart, you had to be patient with the seven key.",
        "Every chord is a button. Every button remembers how many times it was hit.",
    ]
    flavors = [
        'Two notes at once, some pressed more insistently than others.',
        'Chords from a very dull instrument that everyone once owned.',
        'Somebody leaned on a few of these.',
    ]
    VARIANTS = {
        "keys": ("Phone multi-tap", "Old phone multi-tap: the digit is the key, and how many times it repeats picks the letter.", [
            "Thumbs, patience, and no predictive text.",
            "Some buttons are more worn than others.",
        ]),
        "audio": ("DTMF multi-tap (audio)", "Touch-tone (DTMF) key presses, played as sound. Identify each key; repeated presses pick the letter, multi-tap style.", [
            "A voicemail with no voice.",
            "Beeps, pauses and more beeps, from a payphone that should be disconnected.",
        ]),
    }

    def encode(self, word, rng, ctx):
        variant = rng.choice(["tones", "keys", "audio"])
        presses = []
        for c in word:
            for k, letters in KEYPAD.items():
                if c in letters:
                    presses.append((k, letters.index(c) + 1))
        if variant == "tones":
            items = ["%d Hz + %d Hz  ×%d" % (DTMF_ROW[k], DTMF_COL[k], n) for k, n in presses]
            return [{"type": "list", "items": items, "mono": True}]
        ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.VARIANTS[variant]
        if variant == "keys":
            return [{"type": "list", "items": [k * n for k, n in presses], "inline": True, "variant": "keys"}]
        return [{"type": "audio", "kind": "dtmf", "groups": [k * n for k, n in presses]}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        if b["type"] == "audio" or b.get("variant") == "keys":
            key = "groups" if b["type"] == "audio" else "items"
            return "".join(KEYPAD[g[0]][len(g) - 1] for g in b[key])
        out = ""
        for it in b["items"]:
            parts = it.replace("Hz", "").replace("+", "").replace("×", " ").split()
            k = DTMF_REV[(int(parts[0]), int(parts[1]))]
            out += KEYPAD[k][int(parts[2]) - 1]
        return out


class Vigenere(Mechanism):
    easy = False
    medium = False
    key = "vigenere"
    name = "Vigenère keyed by the title"
    hint = "Vigenère cipher; the key is this puzzle's title (letters only)."
    allow_transform = False
    easy_flavors = [
        "The name on the door is also the key to it.",
        "Blaise left the lock. The heading of this page is his combination.",
        "Read the title carefully, then use it for more than reading.",
    ]
    flavors = [
        'The name on the door is also the key to it.',
        'Read the heading twice: once to learn what this is called, and once to open it.',
        'The label is not decoration.',
    ]

    @staticmethod
    def _key(ctx):
        return "".join(c for c in ctx["title"].upper() if c in ALPHA)

    def encode(self, word, rng, ctx):
        k = self._key(ctx)
        ct = "".join(ALPHA[(idx(c) + idx(k[i % len(k)])) % 26] for i, c in enumerate(word))
        return [{"type": "mono", "text": ct, "big": True}]

    def decode(self, blocks, ctx):
        k = self._key(ctx)
        ct = blocks[0]["text"]
        return "".join(ALPHA[(idx(c) - idx(k[i % len(k)])) % 26] for i, c in enumerate(ct))


class AtbashNato(Mechanism):
    easy = False
    key = "atbash_nato"
    name = "Mirrored NATO"
    hint = "NATO phonetic alphabet, then Atbash (A↔Z, B↔Y, ...)."
    allow_transform = False
    easy_flavors = [
        "Heard over the radio {at}, read aloud by someone standing in front of a mirror.",
        "Zulu comes first, Alfa comes last, and the call signs never noticed.",
        "Call signs, looking-glass edition.",
    ]
    flavors = [
        'Call signs, reflected.',
        'The radio operator had everything back to front, but only from A to Z.',
        'Heard over the radio from the other side of the glass.',
    ]

    def encode(self, word, rng, ctx):
        return [{"type": "list", "items": [NATO[25 - idx(c)] for c in word]}]

    def decode(self, blocks, ctx):
        return "".join(ALPHA[25 - NATO.index(w)] for w in blocks[0]["items"])


class TapCode(Mechanism):
    key = "tapcode"
    name = "Tap code"
    hint = "Tap code: first burst = row, second = column, in a 5×5 grid without K."
    easy_flavors = [
        "Heard through the wall of the next cell: bursts of knocks, always in pairs, and a grid of twenty-five that someone kept in their head.",
        "{Crew} kept each other sane with a knuckle and a five-by-five memory.",
        "Knock, knock. Pause. Knock knock knock.",
    ]
    flavors = [
        'Through the wall: bursts of knocks, always in pairs.',
        'Five rows, five columns, and one letter nobody needed.',
        'Knock, knock. Pause. Knock knock knock.',
    ]
    AUDIO = ("Tap code (audio)", "Tap code, as knocks: a burst for the row, a burst for the column, in a 5×5 grid without K.", [
        "Recorded through a wall. Count carefully.",
        "The pipes have been knocking all night, and not at random.",
    ])

    def can(self, word, ctx=None):
        return "K" not in word

    def encode(self, word, rng, ctx):
        groups = []
        for c in word:
            for r, row in enumerate(TAP_GRID):
                if c in row:
                    groups.append(["•" * (r + 1), "•" * (row.index(c) + 1)])
        if rng.random() < 0.35:
            ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.AUDIO
            return [{"type": "audio", "kind": "taps", "groups": [[len(a), len(b)] for a, b in groups]}]
        return [{"type": "taps", "groups": groups}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        if b["type"] == "audio":
            return "".join(TAP_GRID[a - 1][c - 1] for a, c in b["groups"])
        return "".join(TAP_GRID[len(a) - 1][len(c) - 1] for a, c in b["groups"])


class Keyboard(Mechanism):
    key = "keyboard"
    name = "Keyboard shift"
    hint = "Every letter was typed one key to the side on a QWERTY keyboard."
    easy_flavors = [
        "Typed in the dark, with one hand resting a single key out of place.",
        "The typist {at} was consistently, reliably, one step off.",
        "Nothing was lost in transcription; everything simply moved over.",
    ]
    flavors = [
        'Typed in the dark, with one hand resting a key out of place.',
        'Nothing was lost; everything simply moved over.',
        "The typist's hands were fine. Their aim was not.",
    ]

    @staticmethod
    def _shift(c, d):
        for row in QWERTY:
            if c in row:
                j = row.index(c) + d
                return row[j] if 0 <= j < len(row) else None
        return None

    def can(self, word, ctx=None):
        return any(all(self._shift(c, d) for c in word) for d in (1, -1))

    def encode(self, word, rng, ctx):
        dirs = [d for d in (1, -1) if all(self._shift(c, d) for c in word)]
        d = rng.choice(dirs)
        return [{"type": "mono", "text": "".join(self._shift(c, d) for c in word), "big": True, "shift": d}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        return "".join(self._shift(c, -b["shift"]) for c in b["text"])


class Swatches(Mechanism):
    key = "swatches"
    name = "Hex colour ASCII"
    hint = "Each hex colour code is three ASCII bytes."
    easy_flavors = [
        "Paint chips left behind {at}. The labels matter more than the colours.",
        "Each colour whispers three characters, if you ask in the right code.",
        "A designer's palette, specified in the language of 1963.",
    ]
    flavors = [
        'The labels matter more than the colours.',
        'A paint chart for a room nobody will ever decorate.',
        'Three characters to a colour, if you ask the right way.',
    ]

    def encode(self, word, rng, ctx):
        s = word + " " * ((-len(word)) % 3)
        items = ["#" + "".join("%02X" % ord(ch) for ch in s[i:i + 3]) for i in range(0, len(s), 3)]
        return [{"type": "swatches", "items": items}]

    def decode(self, blocks, ctx):
        out = ""
        for h in blocks[0]["items"]:
            out += "".join(chr(int(h[i:i + 2], 16)) for i in (1, 3, 5))
        return out.strip()


class Resistors(Mechanism):
    key = "resistors"
    name = "Resistor colour bands"
    hint = "Read the first two bands of each resistor as digits (black 0 … white 9) and use the number as a letter position."
    easy_flavors = [
        "Pulled from a burnt-out board. Only the first two stripes on each part were ever meant to be read.",
        "The engineer colour-coded everything, then numbered the alphabet.",
        "Every component on this board offers exactly the same resistance: somewhere between one and twenty-six.",
    ]
    flavors = [
        'Components from a dead board, stripes and all.',
        'Every part here resists a little, and never more than twenty-six.',
        'Only the first two stripes on each were ever meant to be read.',
    ]
    TEXT = ("Resistor colour code (written)", "Resistor colour code: each pair of colours is two digits (black 0 … white 9), a letter position.", [
        "A parts list read aloud by someone who only knew the stripes.",
        "Every part described by its first two stripes, and nothing else.",
    ])

    def encode(self, word, rng, ctx):
        items = []
        for c in word:
            n = idx(c) + 1
            items.append([RESISTOR[n // 10], RESISTOR[n % 10], "black", "gold"])
        if rng.random() < 0.35:
            ctx["_name"], ctx["_hint"], ctx["_flavors"] = self.TEXT
            return [{"type": "list", "items": ["%s–%s" % (a, b) for a, b, _, _ in items]}]
        return [{"type": "resistors", "items": items}]

    def decode(self, blocks, ctx):
        b = blocks[0]
        pairs = [it.split("–") for it in b["items"]] if b["type"] == "list" else [it[:2] for it in b["items"]]
        return "".join(ALPHA[RESISTOR.index(x) * 10 + RESISTOR.index(y) - 1] for x, y in pairs)


class Pigpen(Mechanism):
    key = "pigpen"
    name = "Pigpen cipher"
    hint = "Pigpen (Freemason's) cipher: A–I in a # grid, J–R the same with dots, S–V in an X, W–Z the X with dots."
    easy_flavors = [
        "Scratched into the wall of a Masonic lodge. Or a pig pen; the caretaker wasn't sure.",
        "Noughts and crosses, with a few stray dots where someone pressed too hard.",
        "Fences and corners. Some of them have an animal inside.",
    ]
    flavors = [
        'Fences and corners; some have an animal inside.',
        'Noughts and crosses, with a few stray dots.',
        'Scratched into the wall of a very old lodge.',
    ]

    def encode(self, word, rng, ctx):
        items = []
        for c in word:
            i = idx(c)
            if i < 9:
                items.append({"g": "hash", "p": i, "dot": False})
            elif i < 18:
                items.append({"g": "hash", "p": i - 9, "dot": True})
            elif i < 22:
                items.append({"g": "x", "p": i - 18, "dot": False})
            else:
                items.append({"g": "x", "p": i - 22, "dot": True})
        return [{"type": "pigpen", "items": items}]

    def decode(self, blocks, ctx):
        out = ""
        for it in blocks[0]["items"]:
            if it["g"] == "hash":
                out += ALPHA[it["p"] + (9 if it["dot"] else 0)]
            else:
                out += ALPHA[18 + it["p"] + (4 if it["dot"] else 0)]
        return out


class Tape(Mechanism):
    key = "tape"
    name = "Punched tape"
    hint = "Each row of the paper tape is a 7-bit ASCII character (hole = 1, most significant bit on the left)."
    easy_flavors = [
        "A strip of paper tape, seven holes wide, fed through the teletype {at}.",
        "Holes where there ought to be ones. The little sprocket keeps count.",
        "The machine spoke American Standard. Every row is one character.",
    ]
    flavors = [
        'A strip of paper full of holes, seven across.',
        'The sprocket keeps count; the holes do the talking.',
        'What the teletype said, before anyone could read it.',
    ]

    def encode(self, word, rng, ctx):
        rows = [[int(b) for b in format(ord(c), "07b")] for c in word]
        return [{"type": "tape", "rows": rows}]

    def decode(self, blocks, ctx):
        return "".join(chr(int("".join(map(str, r)), 2)) for r in blocks[0]["rows"])


class PrimesRoman(Mechanism):
    easy = False
    key = "primes_roman"
    name = "Prime indices in Roman numerals"
    hint = "Each Roman numeral is a prime; its position in the list of primes (2 is 1st) is a letter position."
    easy_flavors = [
        "The Senate admitted only the indivisible, and numbered each new member in its own fashion.",
        "Caesar counted only indivisible things. We wrote down which ones he counted.",
        "A list only a Roman number theorist could love.",
    ]
    flavors = [
        'The Senate admitted only the indivisible.',
        'Numbers that nothing divides, written the old way.',
        'Caesar counted only things that could not be shared.',
    ]

    def encode(self, word, rng, ctx):
        return [{"type": "list", "items": [roman(PRIMES[idx(c)]) for c in word], "inline": True}]

    def decode(self, blocks, ctx):
        return "".join(ALPHA[PRIMES.index(unroman(r))] for r in blocks[0]["items"])


class Bacon(Mechanism):
    easy = False
    key = "bacon"
    name = "Baconian cipher"
    hint = "Baconian cipher: in groups of five letters, lowercase = a/0 and uppercase = b/1; A = aaaaa, B = aaaab, … (26-letter version). Leftover letters at the end are padding."
    allow_transform = True
    easy_flavors = [
        "Francis would have adored this paragraph. Pay attention to how it stands, not what it says.",
        "Some letters stand tall and some stay low. In groups of five, that's all that matters.",
        "The words are nonsense. The typesetting isn't.",
    ]
    flavors = [
        'Pay attention to how it stands, not what it says.',
        "The words are nonsense. The typesetting isn't.",
        'Some letters stand tall; most stay low.',
    ]
    FILLER = ["a", "an", "the", "of", "and", "to", "in", "by", "on", "at", "for", "from"]

    def encode(self, word, rng, ctx):
        need = 5 * len(word)
        pool = [w.lower() for w in ctx["carrier"]]
        chosen = []
        total = 0
        while need - total > 12:
            w = rng.choice(pool)
            chosen.append(w)
            total += len(w)
        # finish with words that overshoot by fewer than 5 letters
        while total < need:
            r = need - total
            fits = [w for w in pool + self.FILLER if r <= len(w) <= r + 4]
            w = rng.choice(fits) if fits else rng.choice([f for f in self.FILLER if len(f) <= r] or self.FILLER)
            chosen.append(w)
            total += len(w)
        bits = "".join(format(idx(c), "05b") for c in word)
        out, k = [], 0
        for w in chosen:
            s = ""
            for ch in w:
                if k < len(bits) and bits[k] == "1":
                    s += ch.upper()
                else:
                    s += ch
                k += 1
            out.append(s)
        return [{"type": "prose", "text": " ".join(out) + "."}]

    def decode(self, blocks, ctx):
        letters = [ch for ch in blocks[0]["text"] if ch.isalpha()]
        out = ""
        for i in range(0, len(letters) - 4, 5):
            n = int("".join("1" if ch.isupper() else "0" for ch in letters[i:i + 5]), 2)
            if n < 26:
                out += ALPHA[n]
        return out.rstrip("A") if ctx.get("strip") else out


MECHANISMS = [DnaBinary(), DnaTemplate(), Morse(), Semaphore(), BrailleDecimal(),
              Elements(), Dtmf(), Vigenere(), AtbashNato(), TapCode(), Keyboard(),
              Swatches(), Resistors(), Pigpen(), Tape(), PrimesRoman(), Bacon()]
BY_KEY = {m.key: m for m in MECHANISMS}
