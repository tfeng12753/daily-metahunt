"""Tiered hints.

Every mechanism has three levels of help:

- nudge:   an oblique question. It points at a kind of system or asks whether
           there's a pattern, and never says what to do.
- pointer: names the family of the trick without spelling out the steps.
- method:  the full explanation (the mechanism's own `hint`).

Which tiers a round offers depends on its level (see TIERS). Nudges and
pointers are written to fit every visual variant of a mechanism.
"""

TIERS = {
    "hard": ("nudge",),
    "medium": ("nudge", "pointer"),
    "easy": ("pointer", "method"),
}

FEEDER = {
    "dna_binary": (
        "How many different things can a pair of bits say? Does that number turn up anywhere in biology?",
        "Four symbols, read three at a time: the way a cell reads a gene.",
    ),
    "dna_template": (
        "Is this the strand a cell would actually read? And which end would it start from?",
        "It's DNA, but the partner strand, and backwards. Genes are read three bases at a time.",
    ),
    "morse": (
        "Only two kinds of mark, in groups of different lengths. Where have you heard a rhythm like that?",
        "Think of the telegraph: short, long, and the gaps between.",
    ),
    "semaphore": (
        "What if each of these were a person holding their arms out at particular angles?",
        "Sailors once spelled messages with two hand-held flags.",
    ),
    "braille": (
        "Each item comes down to six yes-or-no choices. Is there an alphabet built from exactly that?",
        "It's an alphabet you read with your fingertips.",
    ),
    "elements": (
        "Everything listed here has a fixed place in a famous line-up. Where does each one stand?",
        "The periodic table, counted from the top.",
    ),
    "dtmf": (
        "Have you ever listened to the sounds a phone makes while you dial?",
        "Old phone keypads: each key has a few letters, and you pressed it more times to move along.",
    ),
    "vigenere": (
        "Is there anything on this page, besides the puzzle, made of letters you could borrow?",
        "A repeating-key cipher, and the key is in plain view.",
    ),
    "atbash_nato": (
        "These words have an obvious reading. Is that the whole story, or is the alphabet facing the wrong way?",
        "Radio call signs, then turn the alphabet end to end.",
    ),
    "tapcode": (
        "How would two people talk through a wall with nothing but their knuckles?",
        "Prisoners used a small square grid: knock the row, then the column.",
    ),
    "keyboard": (
        "Try typing this. Where are your fingers?",
        "Look at the keyboard in front of you, and at each key's neighbours.",
    ),
    "swatches": (
        "What else could a six-digit colour code be, two digits at a time?",
        "Computers have a standard number for every character.",
    ),
    "resistors": (
        "Where would you see stripes like these, and what do engineers read them as?",
        "Each colour stands for a digit.",
    ),
    "pigpen": (
        "Picture the alphabet written into a couple of simple grids. What shape would each letter's cell be?",
        "A very old cipher associated with the Freemasons.",
    ),
    "tape": (
        "Seven positions a row, each punched or not. What were seven bits once enough for?",
        "Teletype tape carried a standard character code.",
    ),
    "primes_roman": (
        "Once you read these numbers, what do they all have in common?",
        "Every one is prime. Where does each sit in the list of primes?",
    ),
    "bacon": (
        "Look at how the text is set, not what it says. Are there two kinds of something?",
        "Two kinds of letter, in groups of five: a cipher named after a philosopher.",
    ),
    "cryptogram": (
        "Which short words are most common in English? Could any of them be hiding here?",
        "Each symbol always stands for the same letter. The finished sentence tells you what to submit.",
    ),
    "railfence": (
        "All the right letters seem to be here, just out of order. Could they have been written along some path?",
        "Written in a zigzag over a few rows, then copied out row by row.",
    ),
    "book": (
        "Pairs of numbers, and a page of text. How might one point into the other?",
        "The first number finds a word; the second finds a letter in it.",
    ),
    "knight": (
        "Which piece would take a route like that? Where does it stop each time?",
        "Follow the moves and note the letter on every square it lands on.",
    ),
    "flags": (
        "Where would you see a row of flags like these flying?",
        "Ships signal with one flag per letter.",
    ),
    "bases": (
        "What is the little number telling you about how the big one was written?",
        "Convert each one to ordinary base ten.",
    ),
    "wordsearch": (
        "Once everything that belongs here is accounted for, is anything left unclaimed?",
        "Find the theme words; the letters no word uses are the ones that matter.",
    ),
    "nonogram": (
        "The numbers describe runs of something. What picture could they be drawing?",
        "Paint by numbers. The picture is written, not drawn.",
    ),
    "anagram_extra": (
        "Each jumble is almost a familiar word from this round. Almost.",
        "Rearrange each into a theme word; there's always one letter spare.",
    ),
    "missing": (
        "What fills each gap? Is there a pattern in what you filled in?",
        "Collect the letters you had to supply.",
    ),
    "dropquote": (
        "The columns say which letters, but not in what order. Can the shape of the grid help?",
        "Start with the short words; a sentence will emerge.",
    ),
    "fragments": (
        "The pieces are all here, just shuffled. What order would make sense of them?",
        "Use the word lengths to rebuild the sentence.",
    ),
    "sudoku": (
        "A familiar grid puzzle in unfamiliar clothes. Once it's done, are some squares more important than others?",
        "Solve it like a sudoku, then read the numbered squares in order.",
    ),
    "trivia": (
        "Every line has a number for an answer. Could those numbers be counting through something else?",
        "They're all between 1 and 26.",
    ),
    "scramble": (
        "Every word here has exactly the right letters. Are they in the right order?",
        "Unscramble the words; the sentence tells you what to submit.",
    ),
    "caesar": (
        "Could every letter have moved by the same amount?",
        "A shift cipher. There are only 25 shifts to try.",
    ),
}

TRANSFORM_POINTER = "Whatever you get may still need one more twist."

META = {
    "diagonal": (
        "Is there a natural order these answers could stand in? And does every answer have to give the same thing?",
        "Put the answers in alphabetical order, then think of a staircase.",
    ),
    "title_diagonal": (
        "The puzzles' titles might be more than labels. How would an archivist arrange them?",
        "Order by title; then read on the slant.",
    ),
    "mutation": (
        "Did every answer come out clean the first time? Maybe the mistakes have something in common.",
        "Each feeder decoded with one wrong letter before you fixed it. Those letters matter.",
    ),
    "stowaway": (
        "Did every answer come out the right size the first time? What did you have to throw overboard?",
        "Each feeder decoded with one letter too many. Those letters matter.",
    ),
    "fitin": (
        "The grid's rows come in particular sizes. What else do you have that comes in particular sizes?",
        "Each answer fits exactly one row; then look at the shaded squares.",
    ),
    "logbook": (
        "Every entry has two numbers. What in this round is numbered, and what could the second number count?",
        "The first number picks a puzzle; the second picks a letter inside its answer.",
    ),
    "initials": (
        "Who was Blaise, and what would he need to open this? Has anyone signed their work?",
        "It's a Vigenère cipher, and the key comes from how your answers begin.",
    ),
    "first_letters": (
        "Is there anything the answers share, in the order they came?",
        "Look at how each answer begins.",
    ),
}


def tiers(level, nudge, pointer, method):
    text = {"nudge": nudge, "pointer": pointer, "method": method}
    return [text[t] for t in TIERS[level]]


def feeder_hints(level, key, method, transform=None, extra=None):
    nudge, pointer = FEEDER[key]
    if transform:
        pointer = pointer + " " + TRANSFORM_POINTER
        method = method + " Then undo: " + transform + "."
    out = tiers(level, nudge, pointer, method)
    if extra:
        out.append(extra)
    return out


def meta_hints(level, meta_type, method):
    nudge, pointer = META[meta_type]
    return tiers(level, nudge, pointer, method)
