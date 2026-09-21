#!/usr/bin/env python3
"""v3 translation ingest: parse Almeida Recebida MySQL dump into a staging DB.

Translation: ALMEIDA (Portuguese; Biblia Almeida Recebida v1.7,
almeidarecebida.org, "A Traducao do Texto Recebido (Textus Receptus)".
Publisher's download page states: "This Bible (PorAR) is in the Public
Domain." See verification/v2/almeida-ingest-report.md for the full rights
note, including the generic BY-NC-SA site notice also present on the page.)

Conventions match scripts/ingest_luther1912_v3.py: 0-based book_order,
canonical book names ('Song of Songs', '1 Chronicles', ...).

Stages into data/staging/almeida.db (table `verses`) for later merge into
data/scripture.db. Does NOT touch data/scripture.db.

Source specifics: phpMyAdmin SQL dump, table `pt_nar`
(id, book_id, chapter, verse, pt_nar). book_id 1-66 = Genesis-Revelation
(verified: book_id 43 / chapter 3 / verse 16 reads John 3:16 in Portuguese).
Verse text uses doubled single-quotes (d''agua) and backslash escapes;
both are unescaped. No markup in this edition (plain text).

Usage: python3 scripts/ingest_almeida_v3.py
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "almeida" / "pt_nar.sql"
STAGING = ROOT / "data" / "staging" / "almeida.db"

BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
    "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
    "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
    "Jude", "Revelation",
]
BOOK_ORDER = {name: i for i, name in enumerate(BOOKS)}

# MySQL string literal: backslash escapes and doubled single-quotes.
STR_RE = r"'(?:[^'\\]|\\.|'')*'"
ROW_RE = re.compile(
    r"\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(" + STR_RE + r")\)"
)
MARKUP_RE = re.compile(r"[<\\]|&(amp|lt|gt|quot);|strong=")


def unescape_mysql(s: str) -> str:
    """Unquote a MySQL string literal (strip quotes, resolve escapes)."""
    s = s[1:-1]
    s = s.replace("''", "\x00")
    s = (s.replace("\\'", "'").replace('\\"', '"').replace("\\\\", "\\")
           .replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t"))
    s = s.replace("\x00", "'")
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    sql = RAW.read_text(encoding="utf-8", errors="replace")
    matches = ROW_RE.findall(sql)
    rows = []
    for _id, book_id, ch, vs, lit in matches:
        book_id = int(book_id)
        if not 1 <= book_id <= 66:
            print(f"ERROR: book_id out of range: {book_id}", file=sys.stderr)
            return 1
        rows.append((BOOKS[book_id - 1], int(ch), int(vs), unescape_mysql(lit)))
    n = len(rows)
    print(f"parsed {n} rows from {RAW.name}")
    if n != 31102:
        print(f"ERROR: expected 31102 rows, got {n}", file=sys.stderr)
        return 1
    # Audits.
    seen, dupes = set(), 0
    empty, markup = 0, 0
    for b, c, v, t in rows:
        if (b, c, v) in seen:
            dupes += 1
        seen.add((b, c, v))
        if not t:
            empty += 1
        if MARKUP_RE.search(t):
            markup += 1
            print(f"  MARKUP? {b} {c}:{v}: {t[:80]!r}")
    nbooks = len({b for b, _c, _v, _t in rows})
    print(f"books={nbooks} dupes={dupes} empty={empty} markup_hits={markup}")
    if dupes or empty or nbooks != 66:
        print("ERROR: audit failed", file=sys.stderr)
        return 1
    # Stage.
    if STAGING.exists():
        STAGING.unlink()
    con = sqlite3.connect(STAGING)
    con.execute(
        "CREATE TABLE verses(translation TEXT, book TEXT, book_order INTEGER,"
        " chapter INTEGER, verse INTEGER, text TEXT)"
    )
    con.executemany(
        "INSERT INTO verses(translation, book, book_order, chapter, verse, text)"
        " VALUES ('ALMEIDA',?,?,?,?,?)",
        [(b, BOOK_ORDER[b], c, v, t) for b, c, v, t in rows],
    )
    con.commit()
    staged = con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    con.close()
    print(f"ALMEIDA: {staged} rows staged in {STAGING}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
