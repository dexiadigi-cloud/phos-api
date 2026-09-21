#!/usr/bin/env python3
"""Parse PG #1653 (The Imitation of Christ, Benham translation) into a staging DB.

Deterministic: stdlib + sqlite3 only. Reads data/raw_v2/imitation_christ/1653-0.txt
read-only; writes data/staging/imitation_christ.db with the exact required tables:
  devotionals(id, source_id, day, part, title, anchor_ref, body)
  sources(source_id, kind, title, rights, rights_basis, version, sha256)

Chapter plan (verified against this edition): Book 1: 25, Book 2: 12,
Book 3: 59, Book 4: 18 -> days 1..114. The Book 4 preface
("A devout exhortation to the Holy Communion") is not a numbered chapter and
is excluded.
"""

import hashlib
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "data", "raw_v2", "imitation_christ")
RAW_FILE = os.path.join(RAW_DIR, "1653-0.txt")
STAGING_DB = os.path.join(ROOT, "data", "staging", "imitation_christ.db")

SOURCE_ID = "imitation_christ"

ROMAN_VALS = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
ROMAN_RE = re.compile(r"^CHAPTER ([IVXLCDM]+)$")
BOOK_MARKERS = ["THE FIRST BOOK", "THE SECOND BOOK", "THE THIRD BOOK", "THE FOURTH BOOK"]


def roman_to_int(s):
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN_VALS[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse(raw):
    lines = raw.split("\n")
    # Bound the content to the PG body (excludes license header/footer).
    start = next(i for i, ln in enumerate(lines)
                 if ln.startswith("*** START OF THE PROJECT GUTENBERG EBOOK"))
    end = next(i for i, ln in enumerate(lines)
               if ln.startswith("*** END OF THE PROJECT GUTENBERG EBOOK"))
    lines = lines[start + 1:end]

    book_starts = []
    for i, ln in enumerate(lines):
        if ln in BOOK_MARKERS:
            assert ln == BOOK_MARKERS[len(book_starts)], (
                "book marker order mismatch at line %d: %r" % (i, ln))
            book_starts.append(i)
    assert len(book_starts) == 4, book_starts

    rows = []
    day = 0
    for book_no in range(1, 5):
        seg_start = book_starts[book_no - 1]
        seg_end = book_starts[book_no] if book_no < 4 else len(lines)
        seg = lines[seg_start:seg_end]
        ch_idx = [i for i, ln in enumerate(seg) if ROMAN_RE.match(ln)]
        for ci, cpos in enumerate(ch_idx):
            m = ROMAN_RE.match(seg[cpos])
            ch_num = roman_to_int(m.group(1))
            assert ch_num == ci + 1, (
                "book %d chapter sequence broken at index %d (%r)"
                % (book_no, ci, seg[cpos]))
            # Title: contiguous non-blank lines after the CHAPTER marker.
            j = cpos + 1
            while j < len(seg) and seg[j].strip() == "":
                j += 1
            title_lines = []
            while j < len(seg) and seg[j].strip() != "":
                title_lines.append(seg[j].strip())
                j += 1
            assert title_lines, "empty chapter title book %d ch %d" % (book_no, ch_num)
            title = " ".join(title_lines)
            # Body: blank-skip then verbatim lines until next chapter marker.
            while j < len(seg) and seg[j].strip() == "":
                j += 1
            body_start = j
            body_end = ch_idx[ci + 1] if ci + 1 < len(ch_idx) else len(seg)
            body_lines = seg[body_start:body_end]
            while body_lines and body_lines[-1].strip() == "":
                body_lines.pop()
            assert body_lines, "empty chapter body book %d ch %d" % (book_no, ch_num)
            body = "\n".join(body_lines)
            day += 1
            rows.append({
                "source_id": SOURCE_ID,
                "day": day,
                "part": "morning",
                "title": "Book %d, Chapter %d: %s" % (book_no, ch_num, title),
                "anchor_ref": "",
                "body": body,
            })
    expected = [25, 12, 59, 18]
    for book_no, exp in enumerate(expected, 1):
        n = sum(1 for r in rows if r["title"].startswith("Book %d," % book_no))
        assert n == exp, (book_no, n, exp)
    assert len(rows) == 114, len(rows)
    assert [r["day"] for r in rows] == list(range(1, 115))
    return rows


HTML_TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")
HTML_ENTITY_RE = re.compile(r"&(#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);")


def leak_check(rows):
    problems = []
    for r in rows:
        where = "day=%d" % r["day"]
        for field in ("title", "body"):
            text = r[field] or ""
            if HTML_TAG_RE.search(text):
                problems.append((where, field, "HTML tag"))
            if HTML_ENTITY_RE.search(text):
                problems.append((where, field, "HTML entity"))
    assert not problems, "leak check failures: %r" % problems[:5]
    print("leak checks: 0 HTML tags, 0 HTML entities")


SCHEMA_DEV = """CREATE TABLE devotionals (
  id INTEGER PRIMARY KEY,
  source_id TEXT NOT NULL,
  day INTEGER NOT NULL,
  part TEXT NOT NULL,
  title TEXT,
  anchor_ref TEXT NOT NULL,
  body TEXT NOT NULL
);"""
IDX_DEV = "CREATE UNIQUE INDEX ux_devotionals ON devotionals(source_id, day, part);"
SCHEMA_SRC = """CREATE TABLE sources (
  source_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  rights TEXT NOT NULL,
  rights_basis TEXT NOT NULL,
  version TEXT,
  sha256 TEXT
);"""

RIGHTS_BASIS = (
    "Thomas a Kempis d. 1471 (15th century); English translation by "
    "Rev. William Benham (1831-1910), first published 1874 (new ed. 1905), "
    "public domain by age. Digital edition: Project Gutenberg eBook #1653, "
    "cataloged 'Public domain in the USA' with translator listed as "
    "'Benham, William, 1831-1910'. PG notes its eBooks are confirmed as not "
    "protected by copyright in the U.S. Retrieved 2026-09-20."
)


def main():
    digest = sha256_of(RAW_FILE)
    print("sha256 of raw: %s" % digest)
    with open(RAW_FILE, encoding="utf-8-sig") as f:
        raw = f.read()
    rows = parse(raw)
    leak_check(rows)

    os.makedirs(os.path.dirname(STAGING_DB), exist_ok=True)
    if os.path.exists(STAGING_DB):
        os.remove(STAGING_DB)
    con = sqlite3.connect(STAGING_DB)
    cur = con.cursor()
    cur.execute(SCHEMA_DEV)
    cur.execute(IDX_DEV)
    cur.execute(SCHEMA_SRC)
    cur.executemany(
        "INSERT INTO devotionals (source_id, day, part, title, anchor_ref, body)"
        " VALUES (:source_id, :day, :part, :title, :anchor_ref, :body)", rows)
    cur.execute(
        "INSERT INTO sources (source_id, kind, title, rights, rights_basis,"
        " version, sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (SOURCE_ID, "devotional",
         "Thomas a Kempis, The Imitation of Christ",
         "Public Domain", RIGHTS_BASIS,
         "PG ebook 1653 (2023-05-05 update)", digest))
    con.commit()

    n = cur.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    assert n == 114, n
    days = [r[0] for r in cur.execute("SELECT day FROM devotionals ORDER BY day")]
    assert days == list(range(1, 115)), days
    ns = cur.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    assert ns == 1, ns
    integ = cur.execute("PRAGMA integrity_check").fetchone()[0]
    assert integ == "ok", integ
    con.close()
    print("wrote %s: 114 devotional rows + 1 source row, integrity_check ok"
          % STAGING_DB)


if __name__ == "__main__":
    main()
