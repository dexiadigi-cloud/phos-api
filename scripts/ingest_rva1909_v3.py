#!/usr/bin/env python3
"""v3 translation ingest: parse eBible spaRV1909 USFM into a staging DB.

Translation: RVA1909 (Santa Biblia, Reina Valera 1909, Spanish, eBible.org
spaRV1909 USFM, Public Domain per the eBible.org edition copyright page:
'Public Domain' / 'Dominio Publico', eBible.org certified).

Conventions match scripts/ingest_luther1912_v3.py: 0-based book_order,
canonical book names ('Song of Songs', '1 Chronicles', ...).

Stages into data/staging/rva1909.db (table `verses`) for later merge into
data/scripture.db. Does NOT touch data/scripture.db.

USFM specifics of this edition: words carry Strong's tags as
`\\w word|strong="H7225"\\w*`; the tag attribute is dropped and the word
kept (matches the batch-2 USFX convention of keeping tag inner text).
Cross-references `\\x ... \\x*` and footnotes `\\f ... \\f*` are dropped.

Usage: python3 scripts/ingest_rva1909_v3.py
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "rva1909"
STAGING = ROOT / "data" / "staging" / "rva1909.db"

BOOKS = [
    ("GEN", "Genesis"), ("EXO", "Exodus"), ("LEV", "Leviticus"),
    ("NUM", "Numbers"), ("DEU", "Deuteronomy"), ("JOS", "Joshua"),
    ("JDG", "Judges"), ("RUT", "Ruth"), ("1SA", "1 Samuel"),
    ("2SA", "2 Samuel"), ("1KI", "1 Kings"), ("2KI", "2 Kings"),
    ("1CH", "1 Chronicles"), ("2CH", "2 Chronicles"), ("EZR", "Ezra"),
    ("NEH", "Nehemiah"), ("EST", "Esther"), ("JOB", "Job"),
    ("PSA", "Psalms"), ("PRO", "Proverbs"), ("ECC", "Ecclesiastes"),
    ("SNG", "Song of Songs"), ("ISA", "Isaiah"), ("JER", "Jeremiah"),
    ("LAM", "Lamentations"), ("EZK", "Ezekiel"), ("DAN", "Daniel"),
    ("HOS", "Hosea"), ("JOL", "Joel"), ("AMO", "Amos"), ("OBA", "Obadiah"),
    ("JON", "Jonah"), ("MIC", "Micah"), ("NAM", "Nahum"),
    ("HAB", "Habakkuk"), ("ZEP", "Zephaniah"), ("HAG", "Haggai"),
    ("ZEC", "Zechariah"), ("MAL", "Malachi"), ("MAT", "Matthew"),
    ("MRK", "Mark"), ("LUK", "Luke"), ("JHN", "John"), ("ACT", "Acts"),
    ("ROM", "Romans"), ("1CO", "1 Corinthians"), ("2CO", "2 Corinthians"),
    ("GAL", "Galatians"), ("EPH", "Ephesians"), ("PHP", "Philippians"),
    ("COL", "Colossians"), ("1TH", "1 Thessalonians"),
    ("2TH", "2 Thessalonians"), ("1TI", "1 Timothy"), ("2TI", "2 Timothy"),
    ("TIT", "Titus"), ("PHM", "Philemon"), ("HEB", "Hebrews"),
    ("JAS", "James"), ("1PE", "1 Peter"), ("2PE", "2 Peter"),
    ("1JN", "1 John"), ("2JN", "2 John"), ("3JN", "3 John"),
    ("JUD", "Jude"), ("REV", "Revelation"),
]
BOOK_ID2NAME = dict(BOOKS)
BOOK_ORDER = {name: i for i, (_, name) in enumerate(BOOKS)}

FOOTNOTE_RE = re.compile(r"\\f\b.*?\\f\*", re.S)   # \f ... \f* spans
XREF_RE = re.compile(r"\\x\b.*?\\x\*", re.S)       # \x ... \x* spans
STRONG_ATTR_RE = re.compile(r'\|strong="[^"]*"')   # |strong="H7225"
PLUSW_RE = re.compile(r"\\\+[a-zA-Z]+\*?")     # \+w ... \+w* (plus-markers)
# Any remaining USFM marker, opening or closing (\w, \w*, \add, \q1, ...).
MARKER_RE = re.compile(r"\\[a-zA-Z]+\d*\*?")
# Structural markers that carry no verse text (section heads, titles, etc.).
SKIP_PREFIXES = ("\\s", "\\r", "\\d", "\\qa", "\\ms", "\\mr", "\\mi",
                 "\\cl", "\\cp", "\\cd", "\\mt", "\\imt", "\\h", "\\toc",
                 "\\id", "\\ide", "\\usfm", "\\rem", "\\sts", "\\ip",
                 "\\ipi", "\\im", "\\ib", "\\iot", "\\io1", "\\io2",
                 "\\io3", "\\ili", "\\is", "\\iq")

ID_RE = re.compile(r"^\\id\s+(\S+)")
CH_RE = re.compile(r"^\\c\s+(\d+)")
V_RE = re.compile(r"^\\v\s+(\S+)\s?(.*)$")


def clean_verse_text(body: str) -> str:
    """Strip USFM markup from a verse body, keeping words (incl. Strong-tagged)."""
    t = FOOTNOTE_RE.sub(" ", body)
    t = XREF_RE.sub(" ", t)
    t = STRONG_ATTR_RE.sub("", t)
    t = PLUSW_RE.sub("", t)
    t = MARKER_RE.sub("", t)
    t = t.replace("¶", " ").replace("|", " ")
    return re.sub(r"\s+", " ", t).strip()


def parse_book(path: Path):
    """Return (book_id, list of (book_name, book_order, chapter:int,
    verse:int, text))."""
    book_id = None
    cur_ch = None
    cur_v = None
    buf = []
    verses = []
    empty = 0

    def flush():
        nonlocal cur_v, buf, empty
        if cur_v is not None:
            text = clean_verse_text(" ".join(buf))
            if not text:
                empty += 1
            else:
                name = BOOK_ID2NAME[book_id]
                verses.append((name, BOOK_ORDER[name], cur_ch, int(cur_v), text))
        cur_v, buf = None, []

    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        m = ID_RE.match(line)
        if m:
            if book_id is not None:
                raise ValueError(f"second \\id in {path}")
            book_id = m.group(1)
            if book_id not in BOOK_ID2NAME:
                raise ValueError(f"unknown book id {book_id} in {path}")
            continue
        if book_id is None:
            continue
        m = CH_RE.match(line)
        if m:
            flush()
            cur_ch, cur_v = int(m.group(1)), None
            continue
        m = V_RE.match(line)
        if m:
            flush()
            vid = m.group(1)
            if not vid.isdigit():
                raise ValueError(f"non-numeric verse id {vid!r} in {path}")
            cur_v, buf = vid, [m.group(2)]
            continue
        if line.startswith("\\"):
            if line.startswith(SKIP_PREFIXES):
                continue
            # Any other marker line (\q1, \m, \p, ...) contributes its
            # inner text to the current verse, if one is open.
            if cur_v is not None:
                buf.append(line)
            continue
        if cur_v is not None:
            buf.append(line)
    flush()
    if book_id is None:
        raise ValueError(f"no \\id in {path}")
    if not verses:
        raise ValueError(f"no verses parsed in {path}")
    return book_id, verses, empty


def main() -> int:
    files = sorted(RAW.glob("*-*spaRV1909.usfm"))
    if len(files) != 66:
        print(f"ERROR: expected 66 book files, found {len(files)}", file=sys.stderr)
        return 1
    all_verses = []
    seen_ids = set()
    total_empty = 0
    for path in files:
        book_id, verses, empty = parse_book(path)
        if book_id in seen_ids:
            print(f"ERROR: duplicate book {book_id}", file=sys.stderr)
            return 1
        seen_ids.add(book_id)
        all_verses.extend(verses)
        total_empty += empty
        print(f"  {book_id:>4} {BOOK_ID2NAME[book_id]:<16} {len(verses):>5} verses")
    missing = set(BOOK_ID2NAME) - seen_ids
    if missing:
        print(f"ERROR: missing books {sorted(missing)}", file=sys.stderr)
        return 1
    # Duplicate-key audit.
    seen = set()
    dupes = 0
    for b, _o, c, v, _t in all_verses:
        if (b, c, v) in seen:
            dupes += 1
        seen.add((b, c, v))
    # Stage.
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    if STAGING.exists():
        STAGING.unlink()
    con = sqlite3.connect(STAGING)
    con.execute(
        "CREATE TABLE verses(translation TEXT, book TEXT, book_order INTEGER,"
        " chapter INTEGER, verse INTEGER, text TEXT)"
    )
    con.executemany(
        "INSERT INTO verses(translation, book, book_order, chapter, verse, text)"
        " VALUES ('RVA1909',?,?,?,?,?)",
        [(b, o, c, v, t) for b, o, c, v, t in all_verses],
    )
    con.commit()
    nbooks = len({b for b, _o, _c, _v, _t in all_verses})
    n = con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    con.close()
    print(f"RVA1909: {n} rows staged in {STAGING}, {nbooks} books, "
          f"dupes={dupes}, empty-dropped={total_empty}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
