#!/usr/bin/env python3
"""Parse CCEL Barnes' New Testament Notes from /tmp/barnes_nt.txt.
Output: data/raw_v2/barnes/CCEL_BARNES_NT.json
Format: per-verse entries (Barnes is verse-by-verse).
"""
import re, json
from pathlib import Path

SRC = Path("/tmp/barnes_nt.txt")
RAW = Path(__file__).resolve().parent.parent / "data" / "raw_v2" / "barnes"
RAW.mkdir(parents=True, exist_ok=True)

BOOK_MAP = {
    "MATTHEW": "Matthew", "MARK": "Mark", "LUKE": "Luke", "JOHN": "John",
    "ACTS": "Acts", "ROMANS": "Romans",
    "1 CORINTHIANS": "1 Corinthians", "2 CORINTHIANS": "2 Corinthians",
    "GALATIANS": "Galatians", "EPHESIANS": "Ephesians",
    "PHILIPPIANS": "Philippians", "COLOSSIANS": "Colossians",
    "1 THESSALONIANS": "1 Thessalonians", "2 THESSALONIANS": "2 Thessalonians",
    "1 TIMOTHY": "1 Timothy", "2 TIMOTHY": "2 Timothy",
    "TITUS": "Titus", "PHILEMON": "Philemon", "HEBREWS": "Hebrews",
    "JAMES": "James", "1 PETER": "1 Peter", "2 PETER": "2 Peter",
    "1 JOHN": "1 John", "2 JOHN": "2 John", "3 JOHN": "3 John",
    "JUDE": "Jude", "REVELATION": "Revelation",
}

def main():
    text = SRC.read_text(encoding="utf-8", errors="replace")
    # Split by book: "THE ... - Chapter 1" headers
    # Book titles appear as "THE GOSPEL ACCORDING TO MATTHEW - Chapter 1"
    book_pat = re.compile(r"^([A-Z0-9 .]+?) - Chapter 1\s*$", re.M)
    books = []
    for m in book_pat.finditer(text):
        title = m.group(1).strip()
        # Normalize: remove "THE GOSPEL ACCORDING TO", "THE EPISTLE OF PAUL...", etc.
        books.append((title, m.start()))
    print(f"book headers: {len(books)}")
    result = {"_meta": {
        "source": "Christian Classics Ethereal Library (ccel.org)",
        "work": "Albert Barnes, Barnes' New Testament Notes",
        "print_basis": "1949 (Baker Book House reprint of 19th-c. original)",
        "rights": "Public Domain (CCEL metadata)",
        "retrieval_date": "2026-09-20",
        "source_file": "https://ccel.org/ccel/h/barnes/ntnotes/cache/ntnotes.txt",
        "coverage": "New Testament only (27 books)",
    }}
    for idx, (title, start) in enumerate(books):
        end = books[idx+1][1] if idx+1 < len(books) else len(text)
        btext = text[start:end]
        # Map to canonical (manual chain; BOOK_MAP loop removed as it
        # prematurely matches "JOHN" for the epistles)
        canon = None
        t = title.upper()
        # Check epistles and Revelation before Gospel (to avoid "JOHN" matching Gospel first)
        if "REVELATION" in t: canon = "Revelation"
        elif "1 JOHN" in t or ("JOHN" in t and "FIRST" in t and "EPISTLE" in t): canon = "1 John"
        elif "2 JOHN" in t or ("JOHN" in t and "SECOND" in t): canon = "2 John"
        elif "3 JOHN" in t or ("JOHN" in t and "THIRD" in t): canon = "3 John"
        elif "MATTHEW" in t: canon = "Matthew"
        elif "MARK" in t: canon = "Mark"
        elif "LUKE" in t: canon = "Luke"
        elif "JOHN" in t: canon = "John"
        elif "ACTS" in t: canon = "Acts"
        elif "ROMANS" in t: canon = "Romans"
        elif "CORINTHIANS" in t: canon = "1 Corinthians" if "FIRST" in t else "2 Corinthians"
        elif "GALATIANS" in t: canon = "Galatians"
        elif "EPHESIANS" in t: canon = "Ephesians"
        elif "PHILIPPIANS" in t: canon = "Philippians"
        elif "COLOSSIANS" in t: canon = "Colossians"
        elif "THESSALONIANS" in t: canon = "1 Thessalonians" if "FIRST" in t else "2 Thessalonians"
        elif "TIMOTHY" in t: canon = "1 Timothy" if "FIRST" in t else "2 Timothy"
        elif "TITUS" in t: canon = "Titus"
        elif "PHILEMON" in t: canon = "Philemon"
        elif "HEBREWS" in t: canon = "Hebrews"
        elif "JAMES" in t: canon = "James"
        elif "PETER" in t: canon = "1 Peter" if "FIRST" in t else "2 Peter"
        elif "JUDE" in t: canon = "Jude"
        if not canon:
            print(f"  UNMAPPED: {title}")
            continue
        # Split into chapters
        ch_pat = re.compile(rf"^{re.escape(title)} - Chapter (\d+)\s*$", re.M)
        ch_parts = ch_pat.split(btext)
        for i in range(1, len(ch_parts), 2):
            ch_num = int(ch_parts[i])
            ctext = ch_parts[i+1]
            # Split into verses: "  TITLE - Chapter N - Verse M"
            v_pat = re.compile(rf"^  {re.escape(title)} - Chapter {ch_num} - Verse (\d+)\s*$", re.M)
            v_parts = v_pat.split(ctext)
            # v_parts[0] = chapter intro (before Verse 1)
            intro = v_parts[0].strip()
            intro = re.sub(r"^_+\s*", "", intro).strip()
            # Remove the repeated book name line (e.g. "GOSPEL ACCORDING TO MATTHEW.")
            intro = re.sub(r"^[A-Z][A-Z .]+\.\s*\n", "", intro).strip()
            key = f"{canon}_{ch_num}"
            entry = result.setdefault(key, {
                "book": canon, "chapter": ch_num, "intro": intro, "verses": []})
            for j in range(1, len(v_parts), 2):
                v_num = int(v_parts[j])
                vtext = v_parts[j+1].strip()
                # Clean: the verse text starts after the header; remove leading book-name echo
                vtext = re.sub(r"[ \t]+", " ", vtext)
                vtext = re.sub(r"\n[ \t]+", "\n", vtext)
                vtext = re.sub(r"\n{3,}", "\n\n", vtext)
                entry["verses"].append({"verse": v_num, "text": vtext})
    out = RAW / "CCEL_BARNES_NT.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(result) - 1
    print(f"saved {out}: {n} chapter entries")

if __name__ == "__main__":
    main()
