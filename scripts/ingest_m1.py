#!/usr/bin/env python3
"""M1 ingest: parse BSB USFM + KJV JSON into data/scripture.db.

Usage: python3 scripts/ingest_m1.py
Verifies verse counts and spot-checks rendering.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
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
]
BOOK_ORDER = {name: i for i, (_, name) in enumerate(BOOKS)}
# Source variants that mean the same book.
BOOK_ALIASES = {"Song of Solomon": "Song of Songs"}


def clean_usfm_text(t: str) -> str:
    t = re.sub(r"\\[a-zA-Z]+\d*\*?", "", t)  # \p \pmo \fqa \fr \ft \f* ...
    t = t.replace("|", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_bsb_usfm(path: Path):
    """Return list of (book, chapter:int, verse:str, text)."""
    raw = path.read_text(encoding="utf-8")
    # Drop footnotes entirely (may span lines; contain \ref and \ft).
    raw = re.sub(r"\\f\b.*?\\f\*", "", raw, flags=re.DOTALL)
    # Drop line-level headings/markers that are never verse text.
    raw = re.sub(r"^\\(?:s\d|r|mt\d|h|toc\d|ms\d|mr|cl|cp)\b.*$",
                 "", raw, flags=re.MULTILINE)
    code = path.stem
    book = dict(BOOKS)[code]
    verses = []
    cur_ch = None
    cur_v = None
    buf = []
    # Tokenize on \c N and \v N(-M).
    prev_end = 0
    for m in re.finditer(r"\\([cv])\s+(\d+(?:-\d+)?)", raw):
        kind, num = m.group(1), m.group(2)
        buf.append(raw[prev_end:m.start()])
        if cur_ch is not None and cur_v is not None:
            text = clean_usfm_text("".join(buf))
            if text:
                verses.append((book, cur_ch, cur_v, text))
        buf = []
        if kind == "c":
            cur_ch, cur_v = int(num), None
        else:
            cur_v = num
        prev_end = m.end()
    buf.append(raw[prev_end:])
    if cur_ch is not None and cur_v is not None:
        text = clean_usfm_text("".join(buf))
        if text:
            verses.append((book, cur_ch, cur_v, text))
    return verses


def parse_kjv(kjv_dir: Path):
    verses = []
    files = sorted(kjv_dir.glob("*.json"))
    for f in files:
        if f.name == "kjv.json":
            continue
        book = BOOK_ALIASES.get(f.stem, f.stem)
        data = json.loads(f.read_text(encoding="utf-8"))
        for ch, vmap in data.items():
            for vnum, text in vmap.items():
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    verses.append((book, int(ch), vnum, text))
    return verses


def parse_getbible(path: Path):
    """getBible v2 whole-translation JSON -> list of (book, chapter, verse, text)."""
    d = json.loads(path.read_text(encoding="utf-8"))
    verses = []
    for book in d["books"]:
        bname = book["name"]
        for ch in book["chapters"]:
            for v in ch["verses"]:
                text = re.sub(r"\s+", " ", v["text"]).strip()
                if text:
                    verses.append((bname, int(v["chapter"]),
                                   str(v["verse"]), text))
    return verses


def main() -> int:
    bsb_dir = RAW / "bsb_usfm"
    kjv_dir = RAW / "kjv_src"
    assert bsb_dir.is_dir(), f"missing {bsb_dir}"
    assert kjv_dir.is_dir(), f"missing {kjv_dir}"

    print("Parsing BSB USFM...")
    bsb = []
    for code, _ in BOOKS:
        bsb.extend(parse_bsb_usfm(bsb_dir / f"{code}.usfm"))
    print(f"  BSB verses: {len(bsb)} (expect ~31086 text-bearing)")

    print("Parsing KJV JSON...")
    kjv = parse_kjv(kjv_dir)
    print(f"  KJV verses: {len(kjv)} (expect 31102)")

    print("Parsing WEB (getBible)...")
    web = parse_getbible(RAW / "web.json")
    print(f"  WEB verses: {len(web)} (expect ~31102)")

    print("Parsing ASV (getBible)...")
    asv = parse_getbible(RAW / "asv.json")
    print(f"  ASV verses: {len(asv)} (expect ~31102)")

    # Spot checks
    def find(verses, book, ch, v):
        return next(t for b, c, vv, t in verses
                    if b == book and c == ch and vv == v)

    print("Spot checks:")
    print("  BSB Gen 1:1:", find(bsb, "Genesis", 1, "1")[:60])
    print("  BSB Gen 1:5:", find(bsb, "Genesis", 1, "5")[:80])
    print("  BSB John 3:16:", find(bsb, "John", 3, "16")[:70])
    print("  KJV Gen 1:1:", find(kjv, "Genesis", 1, "1")[:60])
    print("  KJV John 3:16:", find(kjv, "John", 3, "16")[:70])
    print("  WEB Gen 1:1:", find(web, "Genesis", 1, "1")[:60])
    print("  WEB John 3:16:", find(web, "John", 3, "16")[:70])
    print("  ASV Gen 1:1:", find(asv, "Genesis", 1, "1")[:60])
    print("  ASV John 3:16:", find(asv, "John", 3, "16")[:70])
    # Footnote leakage check: Gen 1:5 must not contain footnote text
    g15 = find(bsb, "Genesis", 1, "5")
    assert "Literally" not in g15, f"footnote leaked: {g15}"
    assert "\\" not in g15, f"marker leaked: {g15}"
    print("  footnote/marker leakage check: PASS")
    for tr, rows in (("WEB", web), ("ASV", asv)):
        bad = [r for r in rows if "<" in r[3] or "\\" in r[3]]
        assert not bad, f"{tr} markup leaked in {len(bad)} verses"

    # Ranges report
    ranges = [v for v in bsb if "-" in v[2]]
    print(f"  BSB ranged verses (e.g. 3-4): {len(ranges)}")

    # Write SQLite
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE verses(
        translation TEXT, book TEXT, book_order INT,
        chapter INT, verse TEXT, text TEXT)""")
    for tr, rows in (("BSB", bsb), ("KJV", kjv), ("WEB", web), ("ASV", asv)):
        unknown = {b for b, _, _, _ in rows} - set(BOOK_ORDER)
        assert not unknown, f"{tr} unknown books: {unknown}"
        con.executemany(
            "INSERT INTO verses VALUES (?,?,?,?,?,?)",
            [(tr, b, BOOK_ORDER.get(b, 999), c, v, t)
             for b, c, v, t in rows])
    con.execute("""CREATE VIRTUAL TABLE verses_fts USING fts5(
        text, content='verses', content_rowid='rowid',
        tokenize='porter unicode61')""")
    con.execute("""INSERT INTO verses_fts(rowid, text)
                   SELECT rowid, text FROM verses""")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    print(f"Wrote {DB} with {n} verse rows")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
