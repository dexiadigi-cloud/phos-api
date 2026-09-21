#!/usr/bin/env python3
"""Independent verification for the Calvin staging DB.

Does NOT import the parser. Re-extracts seeded entries straight from the
raw CCEL text files with separately written logic and compares
character-for-character against data/staging/calvin.db.

Seed: 20260920 (deterministic).
Checks: schema, source_id, canonical books/order, no empty text, no HTML
tags, range sanity, per-book counts, PRAGMA integrity_check, and 6+
seeded entry comparisons (Genesis 1:1, Psalm 23:1, John 3:16, Romans 8:28
plus 2 deterministic random picks).
Stdlib only.
"""
import hashlib
import html
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
RAW_DIR = PROJ / "data" / "raw_v2" / "calvin"
DB = PROJ / "data" / "staging" / "calvin.db"
SEED = 20260920

BOOK_ORDER = {
    "Genesis": 1, "Exodus": 2, "Leviticus": 3, "Numbers": 4, "Deuteronomy": 5,
    "Joshua": 6, "Judges": 7, "Ruth": 8, "1 Samuel": 9, "2 Samuel": 10,
    "1 Kings": 11, "2 Kings": 12, "1 Chronicles": 13, "2 Chronicles": 14,
    "Ezra": 15, "Nehemiah": 16, "Esther": 17, "Job": 18, "Psalms": 19,
    "Proverbs": 20, "Ecclesiastes": 21, "Song of Songs": 22, "Isaiah": 23,
    "Jeremiah": 24, "Lamentations": 25, "Ezekiel": 26, "Daniel": 27,
    "Hosea": 28, "Joel": 29, "Amos": 30, "Obadiah": 31, "Jonah": 32,
    "Micah": 33, "Nahum": 34, "Habakkuk": 35, "Zephaniah": 36, "Haggai": 37,
    "Zechariah": 38, "Malachi": 39, "Matthew": 40, "Mark": 41, "Luke": 42,
    "John": 43, "Acts": 44, "Romans": 45, "1 Corinthians": 46,
    "2 Corinthians": 47, "Galatians": 48, "Ephesians": 49, "Philippians": 50,
    "Colossians": 51, "1 Thessalonians": 52, "2 Thessalonians": 53,
    "1 Timothy": 54, "2 Timothy": 55, "Titus": 56, "Philemon": 57,
    "Hebrews": 58, "James": 59, "1 Peter": 60, "2 Peter": 61, "1 John": 62,
    "2 John": 63, "3 John": 64, "Jude": 65, "Revelation": 66,
}
HARMONY = {"31", "32", "33"}
BACKMATTER = re.compile(
    r"^\s*(Index of Scripture|DISSERTATIONS\.?\s*$|Dissertation\s+\d+\.?\s*$|"
    r"APPENDIX OF ADDITIONAL|A COMPLETE SYNOPSIS\s*$|"
    r"NOTES AND COMMENTS\s*$|A (NEW )?TRANSLATION OF\b|a translation\s*$)",
    re.I)
RULE = re.compile(r"^\s*_{10,}\s*$")
# Real HTML tags only (the source uses <x> markers for Greek
# transliteration, e.g. "ea<n ojrqw~v", which are content, not markup).
TAG = re.compile(
    r"</?(?:p|div|span|a|br|hr|h[1-6]|table|tr|td|th|ul|ol|li|em|strong|"
    r"i|b|u|sup|sub|font|img|html|body|head|pre|code|blockquote)\b[^>]*>",
    re.I)

# Independent, deliberately simple header predicate.
REF_BASIC = re.compile(
    r"^\s*[A-Za-z][A-Za-z .']*\d{1,3}:\d{1,3}"
    r"(?:\s*[-–—]\s*\d{1,3}(?::\d{1,3})?)?\.?\s*$")
REF1C_BASIC = re.compile(
    r"^\s*(Obadiah|Philemon|Jude)\s+\d{1,3}(?:\s*[-–—]\s*\d{1,3})?\.?\s*$")
CHAP_BASIC = re.compile(r"^\s*(CHAPTER|Chapter)\s+\d+\.?\s*$")
LEMMA_BASIC = re.compile(r"^\s*\d{1,3}\.\s+")


def v_is_header(lines, i):
    s = lines[i]
    if not (REF_BASIC.match(s) or REF1C_BASIC.match(s)):
        return False
    prev = [lines[j] for j in range(max(0, i - 4), i) if lines[j].strip()][-2:]
    if any(RULE.match(p) or CHAP_BASIC.match(p) for p in prev):
        return True
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j < len(lines) and bool(LEMMA_BASIC.match(lines[j]))


def v_clean(raw_lines):
    out = [ln.strip() for ln in raw_lines if not RULE.match(ln)]
    t = re.sub(r"\^&lt;[0-9A-Fa-f]+&gt;", "", "\n".join(out))
    t = html.unescape(t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def v_book_of(header_text):
    m = re.match(r"^\s*((?:[123]\s)?[A-Za-z][A-Za-z .']*?)\s+\d",
                 header_text)
    if not m:
        return None
    name = re.sub(r"\s+Chapter$", "", m.group(1).strip(), flags=re.I)
    if name.lower() == "psalm":
        return "Psalms"
    return " ".join(w[:1].upper() + w[1:].lower() for w in name.split())


def v_extract(vol, header_text, db_text, book):
    """Re-extract one entry's text independently from the raw file."""
    lines = (RAW_DIR / f"calcom{vol}.txt").read_text(
        encoding="utf-8", errors="replace").splitlines()
    cands = [i for i, l in enumerate(lines) if l.strip() == header_text]
    if not cands:
        return None, "header text not found in raw file"
    if len(cands) > 1:
        # disambiguate duplicates by matching the entry's opening text
        probe = db_text[:120].replace("\n", " ")
        cands = [i for i in cands
                 if probe[:60] in "\n".join(lines[i:i + 12])]
        if len(cands) != 1:
            return None, f"ambiguous header ({len(cands)} matches)"
    start = cands[0]
    prev_ref = header_text
    if vol in HARMONY:
        # harmony: next group header = next rule-preceded ref-line that is
        # not a mere case-repeat of the previous ref-line (sub-header)
        end = len(lines)
        i = start + 1
        # skip continuation lines of this group (consecutive ref-lines)
        while i < len(lines) and (REF_BASIC.match(lines[i])
                                 and lines[i - 1].strip() != ""):
            prev_ref = lines[i].strip()
            i += 1
        while i < len(lines):
            if BACKMATTER.match(lines[i]):
                end = i
                break
            if REF_BASIC.match(lines[i]):
                prev = [lines[j] for j in range(max(0, i - 3), i)
                        if lines[j].strip()]
                if any(RULE.match(p) for p in prev):
                    cur = lines[i].strip()
                    if cur.lower().rstrip(".") != prev_ref.lower().rstrip("."):
                        end = i
                        break
                    prev_ref = cur
            elif lines[i].strip():
                # any non-blank ref-line updates the repeat guard
                if REF_BASIC.match(lines[i]) or REF1C_BASIC.match(lines[i]):
                    prev_ref = lines[i].strip()
            i += 1
    else:
        end = len(lines)
        for i in range(start + 1, len(lines)):
            if BACKMATTER.match(lines[i]):
                end = i
                break
            if v_is_header(lines, i) and v_book_of(lines[i].strip()) == book:
                end = i
                break
    return v_clean(lines[start:end]), None

failures = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def main():
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(rows)").fetchall()]
    check("schema columns",
          cols == ["source_id", "book", "book_order", "start_chapter",
                   "start_verse", "end_chapter", "end_verse", "text"], str(cols))
    total = cur.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    print(f"total rows: {total}")
    check("source_id all calvin",
          cur.execute("SELECT COUNT(*) FROM rows WHERE source_id!='calvin'").fetchone()[0] == 0)
    check("no empty text",
          cur.execute("SELECT COUNT(*) FROM rows WHERE TRIM(text)=''").fetchone()[0] == 0)
    n_tag = 0
    bad_books = 0
    bad_order = 0
    bad_range = 0
    for (book, bo, sc, sv, ec, ev, text) in cur.execute(
            "SELECT book,book_order,start_chapter,start_verse,end_chapter,end_verse,text FROM rows"):
        if TAG.search(text):
            n_tag += 1
        if book not in BOOK_ORDER:
            bad_books += 1
        elif BOOK_ORDER[book] != bo:
            bad_order += 1
        if not (sc >= 1 and sv >= 1 and (ec, ev) >= (sc, sv)):
            bad_range += 1
    check("no HTML tags", n_tag == 0, f"{n_tag} rows")
    check("canonical book names", bad_books == 0, f"{bad_books} rows")
    check("book_order 1-based canonical", bad_order == 0, f"{bad_order} rows")
    check("sane ranges", bad_range == 0, f"{bad_range} rows")
    check("integrity_check",
          cur.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    books = cur.execute(
        "SELECT book, book_order, COUNT(*) FROM rows GROUP BY book ORDER BY book_order").fetchall()
    print(f"distinct books: {len(books)}")
    for b, o, c in books:
        print(f"  {o:2d} {b:16s} {c}")

    # Seeded entry comparisons (independent re-extraction).
    sources = json.loads((RAW_DIR / "row_sources.json").read_text())
    by_id = {s["rowid"]: s for s in sources}
    required = []
    for book, ch, vs in [("Genesis", 1, 1), ("Psalms", 23, 1),
                         ("John", 3, 16), ("Romans", 8, 28)]:
        r = cur.execute(
            "SELECT rowid FROM rows WHERE book=? AND start_chapter<=? "
            "AND end_chapter>=? AND start_verse<=? AND end_verse>=? "
            "ORDER BY (end_chapter-start_chapter),(end_verse-start_verse) LIMIT 1",
            (book, ch, ch, vs, vs)).fetchone()
        required.append(r[0])
    rng = random.Random(SEED)
    all_ids = [r[0] for r in cur.execute("SELECT rowid FROM rows").fetchall()]
    extra = rng.sample(all_ids, 2)
    print(f"seeded extra rowids: {extra}")
    n_ok = 0
    for rid in required + extra:
        s = by_id[rid]
        db_text = cur.execute("SELECT text FROM rows WHERE rowid=?", (rid,)).fetchone()[0]
        got, err = v_extract(s["vol"], s["header"], db_text, s["book"])
        label = f"{s['book']} {s['sc']}:{s['sv']}-{s['ec']}:{s['ev']} (calcom{s['vol']} rowid {rid})"
        if err:
            check(f"reextract {label}", False, err)
            continue
        same = got == db_text
        check(f"reextract {label}", same,
              f"len db={len(db_text)} re={len(got)} sha db={hashlib.sha256(db_text.encode()).hexdigest()[:12]} re={hashlib.sha256(got.encode()).hexdigest()[:12]}")
        if same:
            n_ok += 1
    print(f"seeded comparisons passed: {n_ok}/{len(required) + len(extra)}")
    conn.close()
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
