#!/usr/bin/env python3
"""Ingest raw HelloAO Adam Clarke commentary into data/staging/clarke.db.

Source dir: data/raw_v2/clarke/<USFM>.json (written by fetch_v2_clarke.py).
Staging db: data/staging/clarke.db, table `rows`:
  (source_id, book, book_order, start_chapter, start_verse,
   end_chapter, end_verse, text)

Entry model (follows the source's own structure):
- book introduction   -> (0,0,0,0)
- chapter introduction-> (ch,0,ch,0)
- verse note          -> (ch,v,ch,v)

Cleaning: strip HTML tags, decode HTML entities, normalize whitespace.
No empty text rows. Does NOT touch data/study.db or api/.
"""
import html as H
import json
import re
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
RAW = PROJ / "data" / "raw_v2" / "clarke"
STAGING = PROJ / "data" / "staging" / "clarke.db"

BOOK_ORDER = [
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
    "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]
ORDER = {name: i + 1 for i, name in enumerate(BOOK_ORDER)}

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


def clean_text(text):
    """Plain-text cleanup: strip tags, decode entities, normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = H.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def check_clean(text, ref):
    """Zero-hit check: no HTML tags, entities, or USFM markers may remain."""
    issues = []
    if re.search(r"<[^>]+>", text):
        issues.append("HTML tag")
    if re.search(r"&[a-zA-Z]+;|&#\d+;", text):
        issues.append("HTML entity")
    if re.search(r"(?<!\\\\)\\\\(?!\\\\)[a-zA-Z]+\b", text):
        issues.append("USFM marker")
    if issues:
        print(f"  WARNING clarke {ref}: {', '.join(issues)}", flush=True)
    return not issues


def main():
    study_db = PROJ / "data" / "study.db"
    if not study_db.exists():
        print("note: data/study.db absent (fine; we never write it)")
    warnings = 0
    entries = []
    files = sorted(RAW.glob("*.json"), key=lambda p: p.name)
    files = [p for p in files if p.name not in ("MANIFEST.json",)]
    print(f"raw files: {len(files)}")
    for path in files:
        usfm = path.stem
        if usfm not in USFM_TO_BOOK:
            print(f"  SKIP unknown USFM code: {usfm}")
            continue
        book = USFM_TO_BOOK[usfm]
        order = ORDER[book]
        d = json.loads(path.read_text(encoding="utf-8"))
        binfo = d["book"]
        bintro = (binfo.get("introduction") or "").strip()
        if bintro:
            t = clean_text(bintro)
            if t:
                entries.append((book, order, 0, 0, 0, 0, t))
            if not check_clean(t, f"{book} intro"):
                warnings += 1
        for chnum in sorted(d["chapters"], key=int):
            ch = d["chapters"][chnum]["chapter"]
            cn = int(chnum)
            cintro = (ch.get("introduction") or "").strip()
            if cintro:
                t = clean_text(cintro)
                if t:
                    entries.append((book, order, cn, 0, cn, 0, t))
                if not check_clean(t, f"{book} {cn} intro"):
                    warnings += 1
            for item in ch.get("content", []):
                vnum = item.get("number")
                if vnum is None:
                    continue
                raw_parts = item.get("content", [])
                raw = "\n".join(str(s) for s in raw_parts)
                t = clean_text(raw)
                if not t:
                    continue
                entries.append((book, order, cn, int(vnum), cn, int(vnum), t))
                if not check_clean(t, f"{book} {cn}:{vnum}"):
                    warnings += 1
        print(f"  {usfm} {book}: done")

    print(f"entries: {len(entries)}, markup warnings: {warnings}")
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    if STAGING.exists():
        STAGING.unlink()
    conn = sqlite3.connect(str(STAGING))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE rows(
            source_id TEXT NOT NULL,
            book TEXT NOT NULL,
            book_order INT NOT NULL,
            start_chapter INT NOT NULL,
            start_verse INT NOT NULL,
            end_chapter INT NOT NULL,
            end_verse INT NOT NULL,
            text TEXT NOT NULL
        )
    """)
    cur.executemany(
        "INSERT INTO rows(source_id, book, book_order, start_chapter, start_verse,"
        " end_chapter, end_verse, text) VALUES ('clarke', ?, ?, ?, ?, ?, ?, ?)",
        entries,
    )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    nb = cur.execute("SELECT COUNT(DISTINCT book) FROM rows").fetchone()[0]
    print(f"staging rows: {n}, distinct books: {nb}")
    print("integrity_check:", cur.execute("PRAGMA integrity_check").fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
