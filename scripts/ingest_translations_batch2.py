#!/usr/bin/env python3
"""Batch-2 translation ingest: parse eBible USFX into data/scripture.db.

Translations: YLT, DARBY, DRB (73 books), BBE, GENEVA, AKJV, OEB.
Conventions match scripts/ingest_m1.py: 0-based book_order, canonical
book names ('Song of Songs', '1 Chronicles', ...), verse as TEXT.

Usage: python3 scripts/ingest_translations_batch2.py [--only CODE ...]
"""
import html
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "translations_batch2"
DB = ROOT / "data" / "scripture.db"

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
    # Deuterocanon (DRB only), appended after the 66-book ordering.
    ("TOB", "Tobit"), ("JDT", "Judith"), ("WIS", "Wisdom"),
    ("SIR", "Sirach"), ("BAR", "Baruch"),
    ("1MA", "1 Maccabees"), ("2MA", "2 Maccabees"),
]
BOOK_ID2NAME = dict(BOOKS)
BOOK_ORDER = {name: i for i, (_, name) in enumerate(BOOKS)}

# eBible dir -> (Phos code, USFX filename stem)
SOURCES = {
    "engylt": ("YLT", "engylt_usfx"),
    "engDBY": ("DARBY", "engDBY_usfx"),
    "engDRA": ("DRB", "engDRA_usfx"),
    "engBBE": ("BBE", "engBBE_usfx"),
    "enggnv": ("GENEVA", "enggnv_usfx"),
    "engoebus": ("OEB", "engoebus_usfx"),
}

VERSE_RE = re.compile(r'<v\s+id="([^"]+)"[^>]*bcv="([^"]+)"[^>]*/>(.*?)<ve\s*/>', re.S)
FOOTNOTE_RE = re.compile(r"<f\b.*?</f\s*>", re.S)
SECTION_RE = re.compile(r"<s\b.*?</s\s*>", re.S)
TAG_RE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>")
USFM_MARKER_RE = re.compile(r"\\[a-zA-Z]+\d*\*?")
AKJV_DIR = RAW / "akjv_psfm"


def clean_verse_text(raw: str) -> str:
    t = FOOTNOTE_RE.sub(" ", raw)   # drop footnotes incl. fr/ft content
    t = SECTION_RE.sub(" ", t)      # drop stray section heads inside verse spans
    t = TAG_RE.sub("", t)           # unwrap w/wj/nd/q/bd/p/etc, keep inner text
    t = html.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_usfx(path: Path):
    """Return list of (book_name, book_order, chapter:int, verse:str, text)."""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    verses = []
    for m in VERSE_RE.finditer(raw):
        vid, bcv, body = m.group(1), m.group(2), m.group(3)
        parts = bcv.split(".")
        if len(parts) != 3:
            continue
        book_id, ch, _v = parts
        if book_id == "FRT":
            continue
        if book_id not in BOOK_ID2NAME:
            raise ValueError(f"unknown book id {book_id} in {path}")
        text = clean_verse_text(body)
        if not text:
            continue
        name = BOOK_ID2NAME[book_id]
        verses.append((name, BOOK_ORDER[name], int(ch), vid, text))
    return verses


def parse_akjv():
    """Parse BibleCorps AKJV p.sfm files.

    Returns list of (book_name, book_order, chapter:int, verse:str, text).
    """
    verses = []
    for path in sorted(AKJV_DIR.glob("*.p.sfm")):
        book_id = None
        cur_ch = None
        cur_v = None
        buf = []
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("\\id "):
                book_id = line.split()[1]
                if book_id not in BOOK_ID2NAME:
                    break  # FRT / INT / GLO peripheral files are not ingested
                continue
            if book_id is None:
                continue
            m = re.match(r"\\c\s+(\d+)", line)
            if m:
                if cur_v is not None:
                    text = clean_usfm_verse(" ".join(buf))
                    if text:
                        verses.append((_bname(book_id), BOOK_ORDER[_bname(book_id)],
                                       cur_ch, cur_v, text))
                cur_ch, cur_v, buf = int(m.group(1)), None, []
                continue
            m = re.match(r"\\v\s+(\S+)\s?(.*)$", line)
            if m:
                if cur_v is not None:
                    text = clean_usfm_verse(" ".join(buf))
                    if text:
                        verses.append((_bname(book_id), BOOK_ORDER[_bname(book_id)],
                                       cur_ch, cur_v, text))
                cur_v, buf = m.group(1), [m.group(2)]
                continue
            if cur_v is not None and not line.startswith("\\"):
                buf.append(line)
        if book_id and book_id in BOOK_ID2NAME and cur_v is not None:
            text = clean_usfm_verse(" ".join(buf))
            if text:
                verses.append((_bname(book_id), BOOK_ORDER[_bname(book_id)],
                               cur_ch, cur_v, text))
    return verses


def _bname(book_id):
    return BOOK_ID2NAME[book_id]


def clean_usfm_verse(t: str) -> str:
    t = USFM_MARKER_RE.sub("", t)
    t = t.replace("¶", " ").replace("|", " ")
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    only = set(a.upper() for a in sys.argv[1:] if not a.startswith("-"))
    codes = sorted({code for _, (code, _) in SOURCES.items()})
    if only:
        codes = [c for c in codes if c in only]
    con = sqlite3.connect(DB)
    for ebdir, (code, stem) in sorted(SOURCES.items(), key=lambda kv: kv[1][0]):
        if code not in codes:
            continue
        path = RAW / ebdir / f"{stem}.xml"
        if not path.exists():
            print(f"SKIP {code}: {path} not found")
            continue
        verses = parse_usfx(path)
        # Audit: duplicate keys?
        seen = set()
        dupes = 0
        for book, order, ch, v, _t in verses:
            key = (book, ch, v)
            if key in seen:
                dupes += 1
            seen.add(key)
        con.execute("DELETE FROM verses WHERE translation = ?", (code,))
        con.executemany(
            "INSERT INTO verses(translation, book, book_order, chapter, verse, text)"
            " VALUES (?,?,?,?,?,?)",
            [(code, b, o, c, v, t) for b, o, c, v, t in verses],
        )
        con.commit()
        nbooks = len({b for b, _o, _c, _v, _t in verses})
        print(f"{code}: {len(verses)} rows, {nbooks} books, dupes={dupes}")
    if not only or "AKJV" in only:
        verses = parse_akjv()
        seen = set()
        dupes = sum(1 for b, _o, c, v, _t in verses
                    if (b, c, v) in seen or seen.add((b, c, v)))
        con.execute("DELETE FROM verses WHERE translation = ?", ("AKJV",))
        con.executemany(
            "INSERT INTO verses(translation, book, book_order, chapter, verse, text)"
            " VALUES (?,?,?,?,?,?)",
            [("AKJV", b, o, c, v, t) for b, o, c, v, t in verses],
        )
        con.commit()
        nbooks = len({b for b, _o, _c, _v, _t in verses})
        print(f"AKJV: {len(verses)} rows, {nbooks} books, dupes={dupes}")
    con.close()


if __name__ == "__main__":
    main()
