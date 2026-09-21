#!/usr/bin/env python3
"""Parse Project Gutenberg Weymouth NT ebooks into data/staging/weymouth.db.

Source: Gutenberg ebooks 8828-8854 (per-book "Weymouth New Testament in
Modern Speech"), "Third Edition 1913", each marked "Copyright: Public
domain in the USA." Files: data/raw_v2/weymouth/pgNNNN.txt.

Per-file layout: Gutenberg license header, "*** START OF ..." marker,
5 header lines, "Book NN Name", then verses "NNN:NNN text" with
8-space-indented continuation lines and blank separators, then
"*** END OF ..." marker. No inline markup (verified across all 27 files).

Output: data/staging/weymouth.db, table verses
(translation TEXT, book TEXT, book_order INTEGER, chapter INTEGER,
verse INTEGER, text TEXT), all rows translation='WEYMOUTH'.
book_order follows the canonical 0-based convention of
scripts/ingest_translations_batch2.py (Genesis=0 .. Revelation=65).

Stdlib + sqlite3 only.
"""
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "weymouth"
STAGE = ROOT / "data" / "staging" / "weymouth.db"

# ebook id -> (canonical book name, 0-based book_order)
BOOKS = [
    (8828, "Matthew", 39), (8829, "Mark", 40), (8830, "Luke", 41),
    (8831, "John", 42), (8832, "Acts", 43), (8833, "Romans", 44),
    (8834, "1 Corinthians", 45), (8835, "2 Corinthians", 46),
    (8836, "Galatians", 47), (8837, "Ephesians", 48),
    (8838, "Philippians", 49), (8839, "Colossians", 50),
    (8840, "1 Thessalonians", 51), (8841, "2 Thessalonians", 52),
    (8842, "1 Timothy", 53), (8843, "2 Timothy", 54), (8844, "Titus", 55),
    (8845, "Philemon", 56), (8846, "Hebrews", 57), (8847, "James", 58),
    (8848, "1 Peter", 59), (8849, "2 Peter", 60), (8850, "1 John", 61),
    (8851, "2 John", 62), (8852, "3 John", 63), (8853, "Jude", 64),
    (8854, "Revelation", 65),
]

VERSE_RE = re.compile(r"^(\d{3}):(\d{3}) (.*)$")
CONT_RE = re.compile(r"^ {8}\S")  # 8-space-indented continuation line

# Source-typo corrections, verified against surrounding verses.
# ebook id -> ((wrong_ch, wrong_v, text_prefix), (right_ch, right_v)):
# pg8830.txt (Luke) line 1301 labels Luke 8:23 as "002:023" (it sits
# between 008:022 and 008:024; the true 2:23 is the Exodus quotation at
# line 365). Recorded in PROVENANCE.md.
CORRECTIONS = {
    8830: (((2, 23, "During the passage He fell asleep"), (8, 23)),),
}


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def parse_book(path: Path, ebook_id: int = None):
    """Return list of (chapter, verse, text) for one ebook file."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.startswith("*** START OF"))
    end = next(i for i, l in enumerate(lines)
               if l.startswith("*** END OF"))
    body = lines[start + 1:end]
    fixes = CORRECTIONS.get(ebook_id, ())
    verses = []
    cur = None
    buf = []
    for l in body:
        m = VERSE_RE.match(l)
        if m:
            if cur is not None:
                text = clean(" ".join(buf))
                if text:
                    verses.append((cur[0], cur[1], text))
            ch, v, first = int(m.group(1)), int(m.group(2)), m.group(3)
            for (w_ch, w_v, prefix), (r_ch, r_v) in fixes:
                if (ch, v) == (w_ch, w_v) and first.startswith(prefix):
                    ch, v = r_ch, r_v
            cur = (ch, v)
            buf = [first]
        elif cur is not None and CONT_RE.match(l):
            buf.append(l.strip())
        elif not l.strip():
            continue  # blank separator
        else:
            pass  # header lines before first verse (title, "Book NN Name", etc.)
    if cur is not None:
        text = clean(" ".join(buf))
        if text:
            verses.append((cur[0], cur[1], text))
    return verses


def main() -> int:
    rows = []
    for eid, name, order in BOOKS:
        path = RAW / f"pg{eid}.txt"
        if not path.exists():
            print(f"MISSING {path}", file=sys.stderr)
            return 1
        verses = parse_book(path, ebook_id=eid)
        for ch, v, t in verses:
            rows.append(("WEYMOUTH", name, order, ch, v, t))
        print(f"{name}: {len(verses)} verses")
    # Audit: duplicate keys?
    seen = set()
    dupes = 0
    for r in rows:
        key = (r[1], r[3], r[4])
        if key in seen:
            dupes += 1
        seen.add(key)
    if STAGE.exists():
        STAGE.unlink()
    con = sqlite3.connect(STAGE)
    con.execute(
        "CREATE TABLE verses(translation TEXT, book TEXT, book_order INTEGER,"
        " chapter INTEGER, verse INTEGER, text TEXT)"
    )
    con.execute("CREATE INDEX idx_weymouth_key"
                " ON verses(translation, book, chapter, verse)")
    con.executemany(
        "INSERT INTO verses(translation, book, book_order, chapter, verse,"
        " text) VALUES (?,?,?,?,?,?)",
        rows,
    )
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    con.execute("PRAGMA integrity_check")
    con.close()
    nbooks = len({r[1] for r in rows})
    print(f"WEYMOUTH: {n} rows, {nbooks} books, dupes={dupes}")
    return 0 if (dupes == 0 and n == len(rows)) else 2


if __name__ == "__main__":
    sys.exit(main())
