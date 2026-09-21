#!/usr/bin/env python3
"""Parse CCEL Calvin commentary volumes (calcom01..calcom45 cache txt) into
the Phos staging SQLite db data/staging/calvin.db.

Entry granularity follows the source's own structure:
  - Most volumes: one entry per section headed by an explicit scripture-range
    line (e.g. "Genesis 1:1-31", "Psalm 1:4", "Romans 8:28-30").
  - Harmony of the Gospels vols (31-33): one entry per pericope group; one
    DB row per parallel ref in the group header (same text), since the
    commentary expounds the parallels together.
Front matter (translator prefaces, TOCs) and back matter (indexes,
dissertations, translation appendices, link lists) are excluded.
Stdlib only.
"""
import html
import re
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parents[1]
RAW_DIR = PROJ / "data" / "raw_v2" / "calvin"
STAGING_DB = PROJ / "data" / "staging" / "calvin.db"
SOURCE_ID = "calvin"

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

BOOKS = [b for b in BOOK_ORDER if b != "Psalms"] + ["Psalm"]
B = "|".join(b.replace(" ", "\\ ") for b in BOOKS)
REF = re.compile(
    rf"^\s*(?:{B})\s+(?:Chapter\s+)?\d{{1,3}}:\d{{1,3}}"
    rf"(?:\s*[-–—]\s*\d{{1,3}}(?::\d{{1,3}})?)?\.?\s*$", re.I)
# Single-chapter books use chapter-less headers, e.g. "Jude 1-2", "Obadiah 5".
ONECH = {"Obadiah", "Philemon", "Jude", "2 John", "3 John"}
REF1C = re.compile(
    r"^\s*((?:[123]\s)?[A-Za-z]+)\s+(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\.?\s*$")
RULE = re.compile(r"^\s*_{10,}\s*$")
CHAP = re.compile(
    rf"^\s*(?:(?:CHAPTER|Chapter)\s+\d+\.?|(?:{B})\s+\d{{1,3}})\s*$", re.I)
LEMMA = re.compile(r"^\s*\d{1,3}\.\s+")
LINK = re.compile(r"^\s*\d+\.\s+file:///ccel")
BODY_END_MARK = re.compile(
    r"^\s*(Index of Scripture|DISSERTATIONS\.?\s*$|Dissertation\s+\d+\.?\s*$|"
    r"APPENDIX OF ADDITIONAL|A COMPLETE SYNOPSIS\s*$|"
    r"NOTES AND COMMENTS\s*$|"
    r"A (NEW )?TRANSLATION OF\b|a translation\s*$)", re.I)

# Expected books per volume, verified empirically from the section headers
# on 2026-09-20. A header naming any other book is a scripture citation
# inside the commentary, not a section, and is dropped.
VOL_BOOKS = {
    "01": {"Genesis"}, "02": {"Genesis"},
    "03": {"Exodus", "Leviticus", "Numbers", "Deuteronomy"},
    "04": {"Exodus", "Leviticus", "Numbers", "Deuteronomy"},
    "05": {"Exodus", "Leviticus", "Numbers", "Deuteronomy"},
    "06": {"Exodus", "Leviticus", "Numbers", "Deuteronomy"},
    "07": {"Joshua"},
    "08": {"Psalms"}, "09": {"Psalms"}, "10": {"Psalms"},
    "11": {"Psalms"}, "12": {"Psalms"},
    "13": {"Isaiah"}, "14": {"Isaiah"}, "15": {"Isaiah"}, "16": {"Isaiah"},
    "17": {"Jeremiah"}, "18": {"Jeremiah"}, "19": {"Jeremiah"},
    "20": {"Jeremiah"}, "21": {"Jeremiah", "Lamentations"},
    "22": {"Ezekiel"}, "23": {"Ezekiel"},
    "24": {"Daniel"}, "25": {"Daniel"},
    "26": {"Hosea"},
    "27": {"Joel", "Amos", "Obadiah"},
    "28": {"Jonah", "Micah", "Nahum"},
    "29": {"Habakkuk", "Zephaniah", "Haggai"},
    "30": {"Zechariah", "Malachi"},
    "31": {"Matthew", "Mark", "Luke"}, "32": {"Matthew", "Mark", "Luke"},
    "33": {"Matthew", "Mark", "Luke"},
    "34": {"John"}, "35": {"John"},
    "36": {"Acts"}, "37": {"Acts"},
    "38": {"Romans"},
    "39": {"1 Corinthians"}, "40": {"1 Corinthians", "2 Corinthians"},
    "41": {"Galatians", "Ephesians"},
    "42": {"Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians"},
    "43": {"1 Timothy", "2 Timothy", "Titus", "Philemon"},
    "44": {"Hebrews"},
    "45": {"James", "1 Peter", "2 Peter", "1 John", "Jude"},
}

HARMONY_VOLS = {"31", "32", "33"}


def norm_book(name):
    name = name.strip()
    if name.lower() == "psalm":
        return "Psalms"
    # title-case each word, keep leading digits ("1 corinthians" -> "1 Corinthians")
    return " ".join(w[:1].upper() + w[1:].lower() for w in name.split())


def parse_single_ref(text, default_book=None):
    """'Genesis 1:1-31' -> (book, sc, sv, ec, ev).

    Single-chapter books (Obadiah, Philemon, Jude) use chapter-less
    headers like 'Jude 1-2', meaning chapter 1, verses 1-2.
    """
    m1 = REF1C.match(text)
    if m1 and norm_book(m1.group(1)) in ONECH:
        book = norm_book(m1.group(1))
        v1, v2 = int(m1.group(2)), int(m1.group(3) or m1.group(2))
        return (book, 1, v1, 1, v2)
    m = re.match(
        r"^\s*(?:((?:[123]\s)?[A-Za-z][A-Za-z .']*?)\s+)?(?:Chapter\s+)?"
        r"(\d{1,3}):(\d{1,3})"
        r"(?:\s*[-–—]\s*(\d{1,3})(?::(\d{1,3}))?)?\.?\s*$", text)
    if not m:
        return None
    book = norm_book(m.group(1)) if m.group(1) else default_book
    if not book:
        return None
    sc, sv = int(m.group(2)), int(m.group(3))
    if m.group(4) is None:
        ec, ev = sc, sv
    elif m.group(5) is None:
        ec, ev = sc, int(m.group(4))
    else:
        ec, ev = int(m.group(4)), int(m.group(5))
    return (book, sc, sv, ec, ev)


def parse_group_refs(header_text):
    """'MATTHEW 23:29-39; LUKE 11:47-51; 13:34-35' -> list of ref tuples."""
    refs = []
    book = None
    for part in header_text.split(";"):
        part = part.strip().rstrip(".")
        if not part:
            continue
        r = parse_single_ref(part, default_book=book)
        if r is None:
            return None
        book = r[0]
        refs.append(r)
    return refs or None


def next_nonblank(lines, i):
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j if j < len(lines) else None


def body_end(lines, last_header):
    cands = [i for i, l in enumerate(lines)
             if BODY_END_MARK.match(l) and i > last_header]
    links = [i for i, l in enumerate(lines) if LINK.match(l) and i > last_header]
    if links:
        cands.append(links[0])
    cands.append(len(lines))
    return min(cands)


def is_header_line(l):
    if REF.match(l):
        return True
    m = REF1C.match(l)
    return bool(m and norm_book(m.group(1)) in ONECH)


def find_headers_plain(lines):
    """Section headers for non-harmony volumes: (line_idx, header_text)."""
    idxs = [i for i, l in enumerate(lines) if is_header_line(l)]
    good = []
    for i in idxs:
        prev = [lines[j] for j in range(max(0, i - 4), i) if lines[j].strip()]
        tail = prev[-2:]
        ruled = any(RULE.match(p) for p in tail)
        chapm = any(CHAP.match(p) for p in tail)
        n = next_nonblank(lines, i)
        lemma = n is not None and bool(LEMMA.match(lines[n]))
        if ruled or chapm or lemma:
            good.append((i, lines[i].strip()))
    return good


def find_headers_harmony(lines):
    """Pericope group headers: (first_line_idx, group_header_text).

    A pericope opens with a group header: one or more consecutive ref-lines
    with NO blank line between them (e.g. 'MATTHEW 23:29-39' followed
    directly by 'LUKE 11:47-51; 13:34-35; 11:53-54'), rule-preceded, or the
    first ref-line of the volume. Sub-headers below it repeat the same refs
    in mixed case and are always blank-separated, so they never merge in.
    A rule-preceded ref-line that merely repeats (case-insensitively) the
    ref-line before the rule is a sub-header, not a new pericope.
    """
    n = len(lines)
    isref = [parse_group_refs(l.strip()) is not None
             for l in lines]
    groups = []
    i = 0
    started = False
    prev_ref_text = None  # last ref-line seen (any kind)
    while i < n:
        if not isref[i]:
            if lines[i].strip():
                pass
            i += 1
            continue
        cur_text = lines[i].strip()
        prev = [lines[j] for j in range(max(0, i - 3), i) if lines[j].strip()]
        ruled = any(RULE.match(p) for p in prev)
        is_repeat = (prev_ref_text is not None
                     and cur_text.lower().rstrip(".") == prev_ref_text.lower().rstrip("."))
        opens = (ruled and not is_repeat) or (not started)
        # consume run of consecutive ref-lines (no blank between)
        parts = [cur_text]
        j = i + 1
        while j < n and isref[j] and lines[j - 1].strip() != "":
            parts.append(lines[j].strip())
            j += 1
        header_text = " ".join(parts)
        if opens:
            if parse_group_refs(header_text) is None:
                # shouldn't happen; be safe
                i = j
                prev_ref_text = cur_text
                continue
            groups.append((i, header_text))
            started = True
        prev_ref_text = parts[-1]
        i = j
    return groups


def clean_text(raw_lines):
    out = []
    for ln in raw_lines:
        if RULE.match(ln):
            continue
        out.append(ln.strip())
    text = "\n".join(out)
    # CCEL footnote-anchor artifacts like ^&lt;19B601&gt; (not content)
    text = re.sub(r"\^&lt;[0-9A-Fa-f]+&gt;", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_volume(vol):
    path = RAW_DIR / f"calcom{vol}.txt"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    warnings = []
    if vol in HARMONY_VOLS:
        headers = find_headers_harmony(lines)
    else:
        headers = find_headers_plain(lines)
    if not headers:
        return [], [f"{vol}: no headers found"]
    last = headers[-1][0]
    end = body_end(lines, last)
    headers = [(i, t) for i, t in headers if i < end]
    entries = []  # (book, sc, sv, ec, ev, text, header)
    expected = VOL_BOOKS[vol]
    for k, (hi, htext) in enumerate(headers):
        lo = hi
        hi2 = headers[k + 1][0] if k + 1 < len(headers) else end
        text = clean_text(lines[lo:hi2])
        if not text:
            warnings.append(f"{vol}: empty text at header {htext!r}")
            continue
        if vol in HARMONY_VOLS:
            refs = parse_group_refs(htext)
            if not refs:
                warnings.append(f"{vol}: unparseable group {htext!r}")
                continue
            for (book, sc, sv, ec, ev) in refs:
                if book not in expected:
                    warnings.append(f"{vol}: unexpected book {book} in {htext!r}")
                entries.append((book, sc, sv, ec, ev, text, htext))
        else:
            r = parse_single_ref(htext)
            if not r:
                warnings.append(f"{vol}: unparseable header {htext!r}")
                continue
            book, sc, sv, ec, ev = r
            if book not in BOOK_ORDER:
                warnings.append(f"{vol}: unknown book {book}")
                continue
            if book not in expected:
                # A scripture citation inside the commentary that happens
                # to sit on its own line, not a section: drop it.
                warnings.append(f"{vol}: dropped citation-as-header {htext!r}")
                continue
            entries.append((book, sc, sv, ec, ev, text, htext))
    return entries, warnings


def main():
    STAGING_DB.parent.mkdir(parents=True, exist_ok=True)
    if STAGING_DB.exists():
        STAGING_DB.unlink()
    conn = sqlite3.connect(str(STAGING_DB))
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE rows(source_id TEXT NOT NULL, book TEXT NOT NULL, "
        "book_order INT NOT NULL, start_chapter INT NOT NULL, "
        "start_verse INT NOT NULL, end_chapter INT NOT NULL, "
        "end_verse INT NOT NULL, text TEXT NOT NULL)")
    total = 0
    all_warnings = []
    per_vol = {}
    row_sources = []  # (rowid, vol, header_text) for independent verification
    for v in range(1, 46):
        vol = f"{v:02d}"
        entries, warnings = parse_volume(vol)
        all_warnings.extend(warnings)
        per_vol[vol] = len(entries)
        for (book, sc, sv, ec, ev, text, htext) in entries:
            cur.execute(
                "INSERT INTO rows VALUES (?,?,?,?,?,?,?,?)",
                (SOURCE_ID, book, BOOK_ORDER[book], sc, sv, ec, ev, text))
            row_sources.append(
                {"rowid": cur.lastrowid, "vol": vol, "header": htext,
                 "book": book, "sc": sc, "sv": sv, "ec": ec, "ev": ev})
        total += len(entries)
        print(f"[calcom{vol}] {len(entries)} entries", flush=True)
    conn.commit()
    cur.execute("PRAGMA integrity_check")
    print("integrity_check:", cur.fetchone()[0], flush=True)
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT book) FROM rows")
    print("rows, distinct books:", cur.fetchone(), flush=True)
    conn.close()
    print("TOTAL:", total, flush=True)
    import json
    (RAW_DIR / "row_sources.json").write_text(
        json.dumps(row_sources, indent=1), encoding="utf-8")
    print(f"row_sources.json: {len(row_sources)} mappings", flush=True)
    if all_warnings:
        print(f"WARNINGS ({len(all_warnings)}):", flush=True)
        for w in all_warnings[:40]:
            print("  -", w, flush=True)


if __name__ == "__main__":
    main()
