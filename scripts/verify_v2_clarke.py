#!/usr/bin/env python3
"""Seeded verification for the clarke staging db (source_id=clarke).

Independent of scripts/ingest_v2_clarke.py: raw entries are re-extracted
with this file's own cleaning routine and compared character-for-character
to data/staging/clarke.db. Writes data/raw_v2/clarke/VERIFY.md.
Deterministic seed: 20260920.
"""
import html as H
import json
import random
import re
import sqlite3
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
RAW = PROJ / "data" / "raw_v2" / "clarke"
STAGING = PROJ / "data" / "staging" / "clarke.db"

USFM_TO_BOOK = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Songs", "ISA": "Isaiah",
    "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel",
    "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah",
    "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk",
    "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John",
    "ACT": "Acts", "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians",
    "GAL": "Galatians", "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy",
    "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John",
    "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}


def indep_clean(s):
    """Independently written plain-text normalizer (not from ingest script)."""
    s = re.sub(r"<[^>]*>", "", s)
    s = H.unescape(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n"))
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def raw_verse_text(usfm, ch, verse):
    """Independent re-extraction of one verse entry from the raw file."""
    d = json.loads((RAW / f"{usfm}.json").read_text(encoding="utf-8"))
    chobj = d["chapters"][str(ch)]["chapter"]
    for item in chobj.get("content", []):
        if int(item.get("number", -1)) == int(verse):
            raw = "\n".join(str(s) for s in item.get("content", []))
            return indep_clean(raw)
    return None


def main():
    conn = sqlite3.connect(str(STAGING))
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    src_ids = [r[0] for r in cur.execute("SELECT DISTINCT source_id FROM rows")]
    empties = cur.execute("SELECT COUNT(*) FROM rows WHERE text = '' OR text IS NULL").fetchone()[0]
    books = cur.execute(
        "SELECT book, book_order, COUNT(*) FROM rows GROUP BY book ORDER BY book_order"
    ).fetchall()
    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    # zero-hit markup scan on a sample + full pass for tags
    tag_hits = cur.execute(
        "SELECT COUNT(*) FROM rows WHERE text LIKE '%<%' OR text LIKE '%&%;%'").fetchone()[0]
    book_ch_verse = [(b, o) for b, o, _ in books]

    # seeded comparison
    rng = random.Random(20260920)
    named = [("Genesis", "GEN", 1, 1), ("John", "JHN", 1, 1), ("Romans", "ROM", 8, 28)]
    # Psalm 23:1 is required by the task but Psalms is absent from the source edition
    psalms_present = any(b == "Psalms" for b, _ in book_ch_verse)
    pool = []
    for usfm, book in sorted(USFM_TO_BOOK.items()):
        p = RAW / f"{usfm}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for chnum, chwrap in d["chapters"].items():
            for item in chwrap["chapter"].get("content", []):
                v = item.get("number")
                if v is not None:
                    pool.append((book, usfm, int(chnum), int(v)))
    rng.shuffle(pool)
    seeds = list(named)
    seen = set(named)
    for s in pool:
        if len(seeds) >= 8:
            break
        if s in seen:
            continue
        seeds.append(s)
        seen.add(s)

    results = []
    for book, usfm, ch, v in seeds:
        expected = raw_verse_text(usfm, ch, v)
        row = cur.execute(
            "SELECT text FROM rows WHERE book=? AND start_chapter=? AND start_verse=? "
            "AND end_chapter=? AND end_verse=? AND source_id='clarke'",
            (book, ch, v, ch, v)).fetchone()
        got = row[0] if row else None
        ok = (expected is not None) and (got == expected)
        results.append((book, ch, v, "PASS" if ok else "FAIL",
                        None if ok else (f"expected_len={len(expected) if expected else -1} "
                                         f"got_len={len(got) if got else -1}")))
    passes = sum(1 for r in results if r[3] == "PASS")

    # spot texts of the famous three (first 120 chars, for the record)
    snippets = []
    for book, usfm, ch, v in named:
        row = cur.execute(
            "SELECT text FROM rows WHERE book=? AND start_chapter=? AND start_verse=?",
            (book, ch, v)).fetchone()
        snippets.append((f"{book} {ch}:{v}", (row[0][:120] + "...") if row else "MISSING"))

    lines = []
    A = lines.append
    A("# VERIFY — clarke staging db")
    A("")
    A(f"Generated: 2026-09-20. Staging db: data/staging/clarke.db")
    A("")
    A("## 1. Row count and coverage")
    A("")
    A(f"- Total rows: {total}")
    A(f"- Distinct source_id values: {src_ids}")
    A(f"- Distinct books: {len(books)}")
    A(f"- Rows with empty/NULL text: {empties}")
    A(f"- Rows possibly containing markup ('<' or '&...;'): {tag_hits}")
    A("")
    A("Per-book entry counts (book_order: book = entries):")
    for b, o, c in books:
        A(f"- {o}: {b} = {c}")
    A("")
    A("## 2. Seeded raw-to-staging comparisons (seed 20260920)")
    A("")
    A("Each entry re-extracted independently from the raw JSON (own extraction + "
      "cleaning code path, not via the ingest script) and compared character-for-character "
      "to the staging text.")
    A("")
    for book, ch, v, verdict, detail in results:
        A(f"- {book} {ch}:{v}: {verdict}" + (f" ({detail})" if detail else ""))
    A("")
    A(f"Result: {passes}/{len(results)} PASS")
    if not psalms_present:
        A("- Psalms 23:1: N/A — the source digital edition does not include Psalms "
          "(see coverage notes); no raw text exists to compare.")
    A("")
    A("Staging text snippets for the named seeds (first 120 chars):")
    for ref, snip in snippets:
        A(f"- {ref}: {snip}")
    A("")
    A("## 3. Staging integrity")
    A("")
    A(f"- PRAGMA integrity_check: {integrity}")
    A("")
    A("## 4. Coverage notes")
    A("")
    A("- Source edition (HelloAO adam-clarke) covers 57 of 66 canonical books.")
    A("- Missing books (no data in the digital edition): Deuteronomy, Judges, Psalms, "
      "Proverbs, Ecclesiastes, Jeremiah, Joel, Malachi, Matthew.")
    A("- All 57 present books fetched with 100% of their chapters (no 404s).")
    A("- Entry granularity follows the source: book introductions (0/0/0/0), chapter "
      "introductions (ch/0/ch/0), and per-verse notes (ch/v/ch/v). The source does not "
      "comment on every verse, so verse entries are a subset of each chapter's verses.")
    (RAW / "VERIFY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"VERIFY.md written: {total} rows, {passes}/{len(results)} seeds PASS, "
          f"integrity={integrity}")
    conn.close()


if __name__ == "__main__":
    main()
