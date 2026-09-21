#!/usr/bin/env python3
"""Verify batch-2 translations: seeded raw-to-database exact comparisons.

Deterministic seed 20260920. For each translation:
  - 10 fixed famous passages + 2 DRB deuterocanon passages (DRB only)
  - 4 additional pseudo-random verses drawn with the seeded RNG
Each check re-extracts the verse text from the RAW source file with an
independent minimal extractor (string search, not the ingest regex) and
compares exactly against data/scripture.db.

Usage: python3 verification/v2/verify_translations_batch2.py
Exit code 0 = all pass.
"""
import html
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw_v2" / "translations_batch2"
DB = ROOT / "data" / "scripture.db"
SEED = 20260920

SOURCES = {  # code -> (kind, path or dir)
    "YLT": ("usfx", RAW / "engylt" / "engylt_usfx.xml"),
    "DARBY": ("usfx", RAW / "engDBY" / "engDBY_usfx.xml"),
    "DRB": ("usfx", RAW / "engDRA" / "engDRA_usfx.xml"),
    "BBE": ("usfx", RAW / "engBBE" / "engBBE_usfx.xml"),
    "GENEVA": ("usfx", RAW / "enggnv" / "enggnv_usfx.xml"),
    "OEB": ("usfx", RAW / "engoebus" / "engoebus_usfx.xml"),
    "AKJV": ("psfm", RAW / "akjv_psfm"),
}

BOOK_IDS = {
    "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM",
    "Deuteronomy": "DEU", "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT",
    "1 Samuel": "1SA", "2 Samuel": "2SA", "1 Kings": "1KI", "2 Kings": "2KI",
    "1 Chronicles": "1CH", "2 Chronicles": "2CH", "Ezra": "EZR",
    "Nehemiah": "NEH", "Esther": "EST", "Job": "JOB", "Psalms": "PSA",
    "Proverbs": "PRO", "Ecclesiastes": "ECC", "Song of Songs": "SNG",
    "Isaiah": "ISA", "Jeremiah": "JER", "Lamentations": "LAM",
    "Ezekiel": "EZK", "Daniel": "DAN", "Hosea": "HOS", "Joel": "JOL",
    "Amos": "AMO", "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC",
    "Nahum": "NAM", "Habakkuk": "HAB", "Zephaniah": "ZEP", "Haggai": "HAG",
    "Zechariah": "ZEC", "Malachi": "MAL", "Matthew": "MAT", "Mark": "MRK",
    "Luke": "LUK", "John": "JHN", "Acts": "ACT", "Romans": "ROM",
    "1 Corinthians": "1CO", "2 Corinthians": "2CO", "Galatians": "GAL",
    "Ephesians": "EPH", "Philippians": "PHP", "Colossians": "COL",
    "1 Thessalonians": "1TH", "2 Thessalonians": "2TH", "1 Timothy": "1TI",
    "2 Timothy": "2TI", "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB",
    "James": "JAS", "1 Peter": "1PE", "2 Peter": "2PE", "1 John": "1JN",
    "2 John": "2JN", "3 John": "3JN", "Jude": "JUD", "Revelation": "REV",
    "Tobit": "TOB", "Judith": "JDT", "Wisdom": "WIS", "Sirach": "SIR",
    "Baruch": "BAR", "1 Maccabees": "1MA", "2 Maccabees": "2MA",
}

FAMOUS = [
    ("Genesis", 1, "1"), ("John", 3, "16"), ("Psalms", 23, "1"),
    ("Romans", 8, "28"), ("Psalms", 119, "105"), ("Philippians", 4, "13"),
    ("Proverbs", 3, "5"), ("Matthew", 5, "3"), ("Isaiah", 40, "31"),
    ("1 Corinthians", 13, "4"),
]
DRB_EXTRA = [("Tobit", 12, "7"), ("Wisdom", 3, "1"), ("Sirach", 1, "1")]


def clean_usfx_text(raw: str) -> str:
    # Independent minimal cleaner: drop footnotes, unwrap other tags.
    t = re.sub(r"<f\b.*?</f\s*>", " ", raw, flags=re.S)
    t = re.sub(r"<s\b.*?</s\s*>", " ", t, flags=re.S)
    t = re.sub(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>", "", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def raw_usfx_verse(path: Path, book: str, ch: int, v: str) -> str:
    t = path.read_text(encoding="utf-8-sig", errors="replace")
    bid = BOOK_IDS[book]
    needle = f'bcv="{bid}.{ch}.{v}"'
    i = t.find(needle)
    if i < 0:
        raise ValueError(f"verse not found in raw: {book} {ch}:{v}")
    vstart = t.rfind("<v ", 0, i)
    vend = t.find("<ve", i)
    seg = t[vstart:vend]
    body = seg[seg.find("/>") + 2:]
    return clean_usfx_text(body)


def raw_akjv_verse(d: Path, book: str, ch: int, v: str) -> str:
    bid = BOOK_IDS[book]
    for path in d.glob("*.p.sfm"):
        head = path.read_text(encoding="utf-8-sig", errors="replace").split("\\id ", 1)
        if len(head) < 2 or not head[1].startswith(bid + " "):
            continue
        cur_ch = None
        for line in head[1].splitlines():
            line = line.strip()
            m = re.match(r"\\c\s+(\d+)", line)
            if m:
                cur_ch = int(m.group(1))
                continue
            m = re.match(r"\\v\s+(\S+)\s?(.*)$", line)
            if m and cur_ch == ch and m.group(1) == v:
                t = re.sub(r"\\[a-zA-Z]+\d*\*?", "", m.group(2))
                return re.sub(r"\s+", " ", html.unescape(t.replace("¶", " "))).strip()
    raise ValueError(f"verse not found in raw AKJV: {book} {ch}:{v}")


def main():
    con = sqlite3.connect(DB)
    rng = random.Random(SEED)
    total = passed = 0
    failures = []
    for code, (kind, src) in sorted(SOURCES.items()):
        refs = list(FAMOUS)
        if code == "DRB":
            refs += DRB_EXTRA[:2]
            # DRB Psalms follow Vulgate numbering (KJV 119 = DRB 118).
            refs = [(b, 118 if b == "Psalms" and c == 119 else c, v)
                    for b, c, v in refs]
        # OEB lacks many OT books; only test refs present in DB.
        if code == "OEB":
            refs = [r for r in refs if r[0] in
                    ("Genesis", "Psalms", "Matthew", "John", "Romans",
                     "1 Corinthians", "Philippians")]
        # 4 seeded random verses from the DB itself.
        rows = con.execute(
            "SELECT book, chapter, verse FROM verses WHERE translation=?",
            (code,)).fetchall()
        rand_refs = [(b, c, v) for b, c, v in rng.sample(rows, 4)]
        for book, ch, v in refs + rand_refs:
            total += 1
            db_text = con.execute(
                "SELECT text FROM verses WHERE translation=? AND book=? "
                "AND chapter=? AND verse=?",
                (code, book, ch, v)).fetchone()
            if not db_text:
                failures.append((code, book, ch, v, "missing in DB"))
                continue
            try:
                raw_text = (raw_usfx_verse(src, book, ch, v) if kind == "usfx"
                            else raw_akjv_verse(src, book, ch, v))
            except ValueError as e:
                failures.append((code, book, ch, v, f"raw extract failed: {e}"))
                continue
            if raw_text == db_text[0]:
                passed += 1
            else:
                failures.append((code, book, ch, v,
                                 f"MISMATCH raw={raw_text[:60]!r} db={db_text[0][:60]!r}"))
    con.close()
    print(f"seed={SEED}: {passed}/{total} raw-to-database comparisons passed")
    for f in failures:
        print("FAIL:", f)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
