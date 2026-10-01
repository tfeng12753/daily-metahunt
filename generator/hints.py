"""Tiered hints.

Every puzzle climbs one ladder, and each rung must say more than the one before:

    flavour  ->  tier 1  ->  tier 2  ->  tier 3

- flavour: on the page. Oblique on Hard and Medium; on Easy it is direct and
           the technique is named beside it.
- nudge:   names the kind of system, or the observation that unlocks it, in a
           way the oblique flavour does not. Never just rephrases the flavour.
- pointer: names the trick and the step to take with it.
- method:  the full explanation (the mechanism's own `hint`).
- first:   a worked start: the first letter you should be getting. Easy only;
           it puts one letter of the answer in the page, which is accepted
           there because the round is for beginners.

Easy already shows the technique and a direct flavour, which together say
as much as a pointer, so its hints start at the method.
"""

TIERS = {
    "hard": ("nudge",),
    "medium": ("nudge", "pointer"),
    "easy": ("method", "first"),
}

FEEDER = {
    "dna_binary": (
        "How many different things can a pair of bits say? Four is a very biological number.",
        "Each pair of bits is a DNA base; three bases make a codon, and every codon is an amino acid with a one-letter code.",
    ),
    "dna_template": (
        "This is DNA, but not the strand a cell would read. What is its partner, and which end does reading start from?",
        "Complement it, reverse it, then translate three bases at a time into amino-acid letters.",
    ),
    "morse": (
        "Only two kinds of mark, in groups of one to four. Which old alphabet is built from exactly that?",
        "Morse code: one mark is a dot, the other a dash. Try it both ways round.",
    ),
    "semaphore": (
        "Imagine each of these as a person holding two flags out at arm's length. Sailors had an alphabet for that.",
        "Flag semaphore: the two hands are the two arms, and each pair of angles is a letter.",
    ),
    "braille": (
        "Write each number in binary. Six yes-or-no choices: is there an alphabet built from exactly that?",
        "Braille: each bit is one of the six dots (1, 2, 4 down the left column; 8, 16, 32 down the right).",
    ),
    "elements": (
        "Everything here has a number in a famous chemical line-up. What number does each one have?",
        "Atomic numbers, then count through the alphabet (hydrogen = 1 = A).",
    ),
    "dtmf": (
        "Two frequencies at once is the sound of a phone key being pressed. What letters did those keys carry?",
        "Old phone keypads: find each key, then press it the number of times shown to move along its letters.",
    ),
    "vigenere": (
        "A cipher with a word for a key. Which famous one works like that, and what word on this page could open it?",
        "Vigenère, keyed with this puzzle's own title.",
    ),
    "atbash_nato": (
        "Each word stands for a letter, the way radio operators spell. Do those letters read? If not, try the alphabet backwards.",
        "Take the NATO call signs' initials, then swap each letter for its mirror: A for Z, B for Y.",
    ),
    "tapcode": (
        "Always two numbers, never more than five. How would two prisoners spell through a wall with a 5×5 grid?",
        "Tap code: the first count is the row, the second the column, in a 5×5 alphabet with no K.",
    ),
    "keyboard": (
        "Every letter is close to the right one. Close on what? Look down at your hands.",
        "QWERTY: every letter was typed one key to the side. Try shifting each one back, both directions.",
    ),
    "swatches": (
        "Split each colour code into three pairs of hex digits. What else is a two-digit hex number?",
        "Each pair of hex digits is an ASCII code: three characters per colour.",
    ),
    "resistors": (
        "Engineers read stripes like these as numbers. What number does each part give, and what is a number up to 26?",
        "Resistor colour code: the first two bands are two digits; that number is a letter position.",
    ),
    "pigpen": (
        "Picture the alphabet written into a couple of #-grids and X-grids. Which cell would each shape be?",
        "Pigpen cipher: the shape of each cell, and whether it has a dot, picks the letter.",
    ),
    "tape": (
        "Seven positions a row, each punched or not. What were seven bits once enough for?",
        "Seven-bit ASCII: a hole is 1, the leftmost hole is the highest bit.",
    ),
    "primes_roman": (
        "Read the numerals. They're all prime. Is there a natural way to number the primes?",
        "Find each prime's place in the list of primes (2 is 1st, 3 is 2nd…), then count through the alphabet.",
    ),
    "bacon": (
        "Two kinds of letter, big and small. How many of them would you need to spell twenty-six different things?",
        "Baconian cipher: groups of five, lowercase = a, uppercase = b; aaaaa is A.",
    ),
    "cryptogram": (
        "Which short words are most common in English? Could any of them be hiding here?",
        "Each symbol always stands for the same letter. The finished sentence tells you what to submit.",
    ),
    "railfence": (
        "All the right letters are here, just out of order. Could they have been written along a path that goes up and down?",
        "Rail fence: written in a zigzag over a few rows, then copied out row by row. Try two to five rows.",
    ),
    "book": (
        "The first number in each pair never goes past the number of words on the page. What does the second count?",
        "The first number finds a word on the page; the second finds a letter in it.",
    ),
    "knight": (
        "Those are chess moves. Which squares does the piece land on, and what's written there?",
        "Start on the given square, play each move, and read the letter on every square it lands on.",
    ),
    "flags": (
        "Ships carry a flag for every letter of the alphabet. Do you know them?",
        "International maritime signal flags: one letter each, left to right.",
    ),
    "bases": (
        "The subscript is a base. Once everything is in ordinary decimal, what range are the numbers in?",
        "Convert each one to base ten; each is a letter position (A = 1).",
    ),
    "wordsearch": (
        "Once every theme word is found, is anything left unclaimed? Read it in order.",
        "Find the theme words; the letters no word uses, read row by row, are the answer.",
    ),
    "nonogram": (
        "The numbers describe runs of filled squares. What picture could they be drawing?",
        "Paint by numbers. The picture is written, not drawn.",
    ),
    "anagram_extra": (
        "Each jumble is almost a word from this round, but with a letter to spare. Which letter, every time?",
        "Rearrange each into a theme word; the spare letters, in order, are the answer.",
    ),
    "missing": (
        "Every gap takes exactly one letter. Is there a pattern in what you filled in?",
        "Read the letters you supplied, in order.",
    ),
    "dropquote": (
        "Black squares are spaces. Which two- and three-letter words fit, using only the letters each column allows?",
        "Each column's letters drop into that column of the grid; cross them off as you place them. The sentence tells you what to submit.",
    ),
    "fragments": (
        "The strips are alphabetised, not in order. The word lengths say where the breaks fall. Which strip could start the sentence?",
        "Chain the strips into one string and split it by the word lengths; the sentence tells you what to submit.",
    ),
    "sudoku": (
        "A familiar grid puzzle in unfamiliar clothes. Once it's done, are some squares more important than others?",
        "Solve it like a sudoku, then read the numbered squares in order.",
    ),
    "trivia": (
        "Every line has a number for an answer. Could those numbers be counting through something else?",
        "They're all between 1 and 26: A = 1, B = 2…",
    ),
    "scramble": (
        "Each word is complete but shuffled. Start with the shortest ones: does a sentence appear?",
        "Unscramble each word where it stands; the sentence tells you what to submit.",
    ),
    "caesar": (
        "Try moving every letter the same distance. How far turns the short words into English?",
        "A Caesar shift: find the one shift that fixes a short word, then apply it everywhere.",
    ),
}


META = {
    "diagonal": (
        "Is there a natural order these answers could stand in? And does every answer have to give the same letter position?",
        "Alphabetise the answers; take the 1st letter of the 1st, the 2nd of the 2nd, and so on.",
    ),
    "title_diagonal": (
        "The puzzles' titles might be more than labels. What order would they put the answers in, and where would you read?",
        "Sort the puzzles by title, A to Z; take the 1st letter of the 1st answer, the 2nd of the 2nd, and so on.",
    ),
    "mutation": (
        "Did every answer come out clean the first time? Each had exactly one wrong letter. Did you keep them?",
        "Take the wrong letter from each feeder, in puzzle order.",
    ),
    "stowaway": (
        "Did every answer come out the right size the first time? Each had one letter too many. Did you keep them?",
        "Take the extra letter from each feeder, in puzzle order.",
    ),
    "fitin": (
        "The grid's rows are all different lengths. So are your answers.",
        "Put each answer in the row its length fits; read the shaded squares top to bottom.",
    ),
    "logbook": (
        "Every entry has two numbers. What in this round is numbered, and what could the second number count?",
        "The first number picks a puzzle; the second picks a letter inside its answer.",
    ),
    "initials": (
        "Blaise de Vigenère needed a key to open this. Has every answer signed its work?",
        "It's a Vigenère cipher, and the key is your answers' first letters, in puzzle order.",
    ),
    "first_letters": (
        "Is there anything the answers share, in the order they came?",
        "Look at how each answer begins.",
    ),
}


def tiers(level, nudge, pointer, method, first=None):
    text = {"nudge": nudge, "pointer": pointer, "method": method, "first": first}
    return [text[t] for t in TIERS[level] if text[t]]


def first_step(word):
    return "To check you're on track: the answer begins with %s." % word[0]


def feeder_hints(level, key, method, transform=None, extra=None, answer=None):
    """transform: a TRANSFORMS entry, or None. answer: the feeder's answer (Easy's worked start)."""
    nudge, pointer = FEEDER[key]
    if transform:
        nudge = nudge + " And if what you get still isn't a word, reread the flavour text."
        pointer = pointer + " Then one more layer: " + transform["pointer"]
        method = method + " Then undo: " + transform["name"] + "."
    out = tiers(level, nudge, pointer, method)
    if extra:
        out.append(extra)  # word lists come before the letter check: they're the bigger help
    if level == "easy" and answer:
        out.append(first_step(answer))
    return out


def meta_hints(level, meta_type, method, final=None):
    nudge, pointer = META[meta_type]
    first = "To check you're on track: the final answer begins with %s." % final[0] if final else None
    return tiers(level, nudge, pointer, method, first)
