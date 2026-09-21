"""Reference parser for the Phos (Dexia Bible API).

Parses human-written Bible references such as::

    John 14            -> whole chapter
    John 3:16          -> single verse
    Ps 23:1-3          -> verse range within a chapter
    Romans 8:28-30     -> verse range within a chapter
    Genesis 1-2        -> chapter range
    John 3:16-4:2      -> multi-chapter verse range
    Ps 23:1,3,5        -> comma-separated verses

Book aliases are resolved to the 66 canonical English names (``Ps``,
``Psalm``, ``Psalms`` -> ``Psalms``; ``Song of Solomon`` -> ``Song of
Songs``; ``1John`` / ``1 John`` -> ``1 John``).

Bounds validation needs per-translation chapter/verse limits from the
database; pass the mapping returned by ``db.get_bounds(translation)``::

    {"Genesis": {"order": 0, "chapters": 50, "max_verse": {1: 31, ...}}, ...}

Out-of-range chapters/verses and unknown books raise :class:`RefError`,
which the API layer turns into HTTP 400 responses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


class RefError(ValueError):
    """A reference string could not be parsed or is out of bounds."""


CANONICAL_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke",
    "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy",
    "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
    # Deuterocanon (present in DRB as book_order 66-72).
    "Tobit", "Judith", "Wisdom", "Sirach", "Baruch",
    "1 Maccabees", "2 Maccabees",
]

# Common abbreviations / alternate names -> canonical name (all lowercase keys).
_ABBREV = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis",
    "ex": "Exodus", "exo": "Exodus", "exod": "Exodus",
    "lev": "Leviticus", "le": "Leviticus", "lv": "Leviticus",
    "num": "Numbers", "nu": "Numbers", "nm": "Numbers", "nb": "Numbers",
    "deut": "Deuteronomy", "de": "Deuteronomy", "dt": "Deuteronomy",
    "josh": "Joshua", "jos": "Joshua",
    "judg": "Judges", "jdg": "Judges", "jg": "Judges",
    "rth": "Ruth", "ru": "Ruth",
    "1sa": "1 Samuel", "1sm": "1 Samuel", "1sam": "1 Samuel",
    "2sa": "2 Samuel", "2sm": "2 Samuel", "2sam": "2 Samuel",
    "1ki": "1 Kings", "1kgs": "1 Kings", "1kings": "1 Kings",
    "2ki": "2 Kings", "2kgs": "2 Kings", "2kings": "2 Kings",
    "1ch": "1 Chronicles", "1chr": "1 Chronicles", "1chron": "1 Chronicles",
    "2ch": "2 Chronicles", "2chr": "2 Chronicles", "2chron": "2 Chronicles",
    "ezr": "Ezra", "ezra": "Ezra",
    "neh": "Nehemiah", "ne": "Nehemiah",
    "est": "Esther", "esth": "Esther", "es": "Esther",
    "jb": "Job",
    "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms", "pslm": "Psalms",
    "prov": "Proverbs", "pr": "Proverbs", "prv": "Proverbs", "pro": "Proverbs",
    "eccl": "Ecclesiastes", "ecc": "Ecclesiastes", "ec": "Ecclesiastes",
    "qoh": "Ecclesiastes", "qohelet": "Ecclesiastes",
    "song": "Song of Songs", "songs": "Song of Songs",
    "song of solomon": "Song of Songs", "canticles": "Song of Songs",
    "sos": "Song of Songs", "cant": "Song of Songs",
    "isa": "Isaiah", "is": "Isaiah",
    "jer": "Jeremiah", "je": "Jeremiah",
    "lam": "Lamentations", "la": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel", "ezk": "Ezekiel",
    "dan": "Daniel", "da": "Daniel", "dn": "Daniel",
    "hos": "Hosea", "ho": "Hosea",
    "jl": "Joel",
    "am": "Amos",
    "obad": "Obadiah", "obd": "Obadiah", "ob": "Obadiah",
    "jon": "Jonah", "jnh": "Jonah",
    "mi": "Micah", "mic": "Micah",
    "nah": "Nahum", "na": "Nahum",
    "hab": "Habakkuk",
    "zeph": "Zephaniah", "zep": "Zephaniah",
    "hag": "Haggai", "hg": "Haggai",
    "zech": "Zechariah", "zec": "Zechariah", "zc": "Zechariah",
    "mal": "Malachi", "ml": "Malachi",
    "matt": "Matthew", "mt": "Matthew", "mat": "Matthew",
    "mk": "Mark", "mrk": "Mark",
    "lk": "Luke", "luk": "Luke",
    "jn": "John", "joh": "John", "jhn": "John",
    "ac": "Acts", "act": "Acts",
    "rom": "Romans", "ro": "Romans", "rm": "Romans",
    "1cor": "1 Corinthians", "1co": "1 Corinthians",
    "2cor": "2 Corinthians", "2co": "2 Corinthians",    "gal": "Galatians", "ga": "Galatians",
    "eph": "Ephesians", "ephes": "Ephesians",
    "phil": "Philippians", "php": "Philippians", "phl": "Philippians",
    "col": "Colossians", "co": "Colossians",
    "1thess": "1 Thessalonians", "1thes": "1 Thessalonians", "1th": "1 Thessalonians",
    "2thess": "2 Thessalonians", "2thes": "2 Thessalonians", "2th": "2 Thessalonians",
    "1tim": "1 Timothy", "1ti": "1 Timothy",
    "2tim": "2 Timothy", "2ti": "2 Timothy",
    "tit": "Titus", "ti": "Titus",
    "phlm": "Philemon", "phm": "Philemon",
    "heb": "Hebrews", "he": "Hebrews",
    "jas": "James", "jm": "James",
    "1pet": "1 Peter", "1pe": "1 Peter", "1pt": "1 Peter",
    "2pet": "2 Peter", "2pe": "2 Peter", "2pt": "2 Peter",
    "1jn": "1 John", "2jn": "2 John", "3jn": "3 John",
    "jud": "Jude", "jd": "Jude",
    "rev": "Revelation", "re": "Revelation", "apocalypse": "Revelation",
    "tob": "Tobit", "tobit": "Tobit", "tb": "Tobit",
    "jdt": "Judith", "judith": "Judith",
    "wis": "Wisdom", "wisdom": "Wisdom", "ws": "Wisdom",
    "sir": "Sirach", "sirach": "Sirach", "ecclesiasticus": "Sirach",
    "bar": "Baruch", "baruch": "Baruch",
    "1ma": "1 Maccabees", "1mac": "1 Maccabees", "1macc": "1 Maccabees",
    "1maccabees": "1 Maccabees",
    "2ma": "2 Maccabees", "2mac": "2 Maccabees", "2macc": "2 Maccabees",
    "2maccabees": "2 Maccabees",
}

_ALIAS = {name.lower(): name for name in CANONICAL_BOOKS}
_ALIAS.update(_ABBREV)

_ROMAN_RE = re.compile(r"^(i{1,3})\s+")
_LEAD_NUM_RE = re.compile(r"^([123])(?:st|nd|rd)?\s*")
_BOOK_SPLIT_RE = re.compile(r"^(.+?)\s+(\d[\d\s:,\-–—]*)$")


def resolve_book(raw: str) -> str | None:
    """Map a book name/abbreviation to its canonical name, or None."""
    s = raw.strip().lower().replace(".", "")
    s = re.sub(r"\s+", " ", s)
    s = _LEAD_NUM_RE.sub(r"\1 ", s)          # "1john" -> "1 john", "1st john" -> "1 john"
    s = _ROMAN_RE.sub(lambda m: str(len(m.group(1))) + " ", s)  # "ii john" -> "2 john"
    s = re.sub(r"\s+", " ", s).strip()
    hit = _ALIAS.get(s)
    if hit is None:
        # Spaced numbered-book abbreviations: "1 sam" -> "1sam", "1 jn" -> "1jn".
        hit = _ALIAS.get(re.sub(r"^([123]) ", r"\1", s))
    return hit


@dataclass
class ResolvedRef:
    """A fully parsed and bounds-validated reference."""
    book: str
    book_order: int
    # Each span is (chapter, first_verse, last_verse), fully concrete.
    spans: list[tuple[int, int, int]] = field(default_factory=list)
    display: str = ""

    @property
    def chapter(self) -> int:
        return self.spans[0][0]


def _check_chapter(book: str, ch: int, info: dict) -> None:
    if not 1 <= ch <= info["chapters"]:
        raise RefError(
            f"Chapter {ch} out of range for {book} "
            f"(valid chapters: 1-{info['chapters']})."
        )


def _check_verse(book: str, ch: int, v: int, info: dict) -> None:
    _check_chapter(book, ch, info)
    vmax = info["max_verse"][ch]
    if not 1 <= v <= vmax:
        raise RefError(
            f"Verse {v} out of range for {book} {ch} "
            f"(valid verses: 1-{vmax})."
        )


def _display(book: str, spans: list[tuple[int, int, int]], info: dict) -> str:
    if len(spans) == 1:
        ch, vs, ve = spans[0]
        vmax = info["max_verse"][ch]
        if vs == 1 and ve == vmax:
            return f"{book} {ch}"
        if vs == ve:
            return f"{book} {ch}:{vs}"
        return f"{book} {ch}:{vs}-{ve}"
    first_ch = spans[0][0]
    last_ch = spans[-1][0]
    if first_ch == last_ch:
        parts = [str(vs) if vs == ve else f"{vs}-{ve}" for _, vs, ve in spans]
        return f"{book} {first_ch}:{','.join(parts)}"
    if all(info["max_verse"][c] == spans[i][2] and spans[i][1] == 1
           for i, c in enumerate(range(first_ch, last_ch + 1))):
        return f"{book} {first_ch}-{last_ch}"
    sc, sv, _ = spans[0]
    ec, _, ev = spans[-1]
    return f"{book} {sc}:{sv}-{ec}:{ev}"


def parse_reference(ref: str, bounds: dict) -> ResolvedRef:
    """Parse ``ref`` and validate it against per-translation ``bounds``.

    ``bounds`` maps canonical book name to
    ``{"order": int, "chapters": int, "max_verse": {chapter: max_verse}}``.
    Raises :class:`RefError` on any problem.
    """
    if not ref or not ref.strip():
        raise RefError("Empty reference. Example: 'John 3:16'.")
    ref = ref.strip().replace("–", "-").replace("—", "-")

    m = _BOOK_SPLIT_RE.match(ref)
    if not m:
        raise RefError(
            f"Could not parse reference '{ref}'. "
            "Expected forms like 'John 3:16', 'Ps 23:1-3', 'Romans 8'."
        )
    book_raw, rest = m.group(1), m.group(2).replace(" ", "")
    book = resolve_book(book_raw)
    if book is None or book not in bounds:
        raise RefError(
            f"Unknown book '{book_raw.strip()}'. "
            "Use a canonical name or common abbreviation, e.g. 'Ps', 'Psalms', "
            "'1 John', 'Song of Songs'."
        )
    info = bounds[book]

    # Cross-chapter verse range: 3:16-4:2
    cm = re.fullmatch(r"(\d+):(\d+)-(\d+):(\d+)", rest)
    if cm:
        sc, sv, ec, ev = (int(x) for x in cm.groups())
        _check_verse(book, sc, sv, info)
        _check_verse(book, ec, ev, info)
        if (sc, sv) > (ec, ev):
            raise RefError(f"Invalid range '{ref}': start is after end.")
        spans: list[tuple[int, int, int]] = []
        for ch in range(sc, ec + 1):
            vmax = info["max_verse"][ch]
            vs = sv if ch == sc else 1
            ve = ev if ch == ec else vmax
            spans.append((ch, vs, ve))
        return ResolvedRef(book, info["order"], spans, _display(book, spans, info))

    # Chapter range: 1-2
    cm = re.fullmatch(r"(\d+)-(\d+)", rest)
    if cm:
        sc, ec = (int(x) for x in cm.groups())
        _check_chapter(book, sc, info)
        _check_chapter(book, ec, info)
        if sc > ec:
            raise RefError(f"Invalid range '{ref}': start chapter is after end chapter.")
        spans = [(ch, 1, info["max_verse"][ch]) for ch in range(sc, ec + 1)]
        return ResolvedRef(book, info["order"], spans, _display(book, spans, info))

    # Whole chapter: 14
    cm = re.fullmatch(r"(\d+)", rest)
    if cm:
        ch = int(cm.group(1))
        _check_chapter(book, ch, info)
        spans = [(ch, 1, info["max_verse"][ch])]
        return ResolvedRef(book, info["order"], spans, _display(book, spans, info))

    # Chapter + verse spec: 23:1-3 / 23:1 / 23:1,3,5
    cm = re.fullmatch(r"(\d+):(.+)", rest)
    if cm:
        ch = int(cm.group(1))
        _check_chapter(book, ch, info)
        vmax = info["max_verse"][ch]
        spans = []
        for part in cm.group(2).split(","):
            pm = re.fullmatch(r"(\d+)-(\d+)", part)
            if pm:
                vs, ve = (int(x) for x in pm.groups())
            elif re.fullmatch(r"\d+", part):
                vs = ve = int(part)
            else:
                raise RefError(
                    f"Could not parse verse part '{part}' in '{ref}'. "
                    "Use 'N', 'N-M', or comma-separated lists like '1,3,5'."
                )
            if not 1 <= vs <= vmax or not 1 <= ve <= vmax:
                raise RefError(
                    f"Verse out of range in '{ref}': {book} {ch} has "
                    f"verses 1-{vmax}."
                )
            if vs > ve:
                raise RefError(f"Invalid range '{part}' in '{ref}': start is after end.")
            spans.append((ch, vs, ve))
        return ResolvedRef(book, info["order"], spans, _display(book, spans, info))

    raise RefError(
        f"Could not parse reference '{ref}'. "
        "Expected forms like 'John 3:16', 'Ps 23:1-3', 'Romans 8'."
    )
