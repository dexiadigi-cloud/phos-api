#!/usr/bin/env python3
"""Parse CCEL JFB (Commentary Critical and Explanatory, 1871, Proofed, PD)
from /tmp/jfb.txt into structured JSON for V2 staging.

Output: data/raw_v2/jfb/CCEL_JFB.json
Format: {"_meta": {...}, "BOOK_CH": {"book": canonical, "chapter": n,
          "intro": "...", "sections": [{"verse_start","verse_end","title","text"}]}}
"""
import re, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
import parser as parsemod

# JFB abbreviations that parser.resolve_book() does not know (manual aliases,
# sanctioned: canonical books come from api/parser.py plus manual aliases).
JFB_ABBREV_ALIASES = {
    "1Jo": "1 John", "2Jo": "2 John", "3Jo": "3 John",
    "Joe": "Joel", "Lu": "Luke", "Mr": "Mark", "So": "Song of Songs",
}

def resolve_abbrev(abbrev):
    """Canonical book for a JFB header abbreviation, or None if not a book."""
    if abbrev in JFB_ABBREV_ALIASES:
        return JFB_ABBREV_ALIASES[abbrev]
    try:
        return parsemod.resolve_book(abbrev)
    except Exception:
        return None

JFB_TXT = Path(__file__).resolve().parent.parent / "data" / "raw_v2" / "jfb" / "jfb_ccel_1871.txt"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw_v2" / "jfb"
RAW.mkdir(parents=True, exist_ok=True)

# Map CCEL book header -> canonical name (via parser.resolve_book + manual)
BOOK_MAP = {
    "GENESIS": "Genesis", "EXODUS": "Exodus", "LEVITICUS": "Leviticus",
    "NUMBERS": "Numbers", "DEUTERONOMY": "Deuteronomy", "JOSHUA": "Joshua",
    "JUDGES": "Judges", "RUTH": "Ruth",
    "FIRST BOOK OF SAMUEL": "1 Samuel", "SECOND BOOK OF SAMUEL": "2 Samuel",
    "FIRST BOOK OF THE KINGS": "1 Kings", "SECOND BOOK OF THE KINGS": "2 Kings",
    "FIRST BOOK OF THE CHRONICLES": "1 Chronicles",
    "SECOND BOOK OF THE CHRONICLES": "2 Chronicles",
    "EZRA": "Ezra", "NEHEMIAH": "Nehemiah", "ESTHER": "Esther", "JOB": "Job",
    "PSALMS": "Psalms", "PROVERBS": "Proverbs",
    "ECCLESIASTES": "Ecclesiastes", "SONG OF SOLOMON": "Song of Songs",
    "ISAIAH": "Isaiah", "JEREMIAH": "Jeremiah",
    "LAMENTATIONS OF JEREMIAH": "Lamentations", "EZEKIEL": "Ezekiel",
    "DANIEL": "Daniel", "HOSEA": "Hosea", "JOEL": "Joel", "AMOS": "Amos",
    "OBADIAH": "Obadiah", "JONAH": "Jonah", "MICAH": "Micah", "NAHUM": "Nahum",
    "HABAKKUK": "Habakkuk", "ZEPHANIAH": "Zephaniah", "HAGGAI": "Haggai",
    "ZECHARIAH": "Zechariah", "MALACHI": "Malachi",
    "MATTHEW": "Matthew", "MARK": "Mark", "LUKE": "Luke", "JOHN": "John",
    "ACTS OF THE APOSTLES": "Acts", "ROMANS": "Romans",
    "FIRST EPISTLE OF PAUL THE APOSTLE TO THE CORINTHIANS": "1 Corinthians",
    "SECOND EPISTLE OF PAUL THE APOSTLE TO THE CORINTHIANS": "2 Corinthians",
    "GALATIANS": "Galatians", "EPHESIANS": "Ephesians",
    "PHILIPPIANS": "Philippians", "COLOSSIANS": "Colossians",
    "FIRST EPISTLE OF PAUL THE APOSTLE TO THE THESSALONIANS": "1 Thessalonians",
    "SECOND EPISTLE OF PAUL THE APOSTLE TO THE THESSALONIANS": "2 Thessalonians",
    "PASTORAL EPISTLES OF PAUL THE APOSTLE TO TIMOTHY AND TITUS": "1 Timothy",
    "SECOND EPISTLE OF PAUL THE APOSTLE TO TIMOTHY": "2 Timothy",
    "EPISTLE OF PAUL TO TITUS": "Titus", "EPISTLE OF PAUL TO PHILEMON": "Philemon",
    "EPISTLE OF PAUL THE APOSTLE TO THE HEBREWS": "Hebrews",
    "GENERAL EPISTLE OF JAMES": "James",
    "FIRST EPISTLE GENERAL OF PETER": "1 Peter",
    "SECOND EPISTLE GENERAL OF PETER": "2 Peter",
    "FIRST GENERAL EPISTLE OF JOHN": "1 John",
    "SECOND AND THIRD EPISTLES GENERAL OF JOHN": "2 John",  # contains 2Jo commentary
    "THIRD EPISTLE OF JOHN": "3 John",
    "GENERAL EPISTLE OF JUDE": "Jude",
    "REVELATION OF ST. JOHN THE DIVINE": "Revelation",
}

def split_books(text):
    """Split into (book_key, book_text) using 'Commentary by' markers."""
    lines = text.splitlines()
    markers = [i for i, ln in enumerate(lines) if "Commentary by" in ln]
    books = []
    for idx, mi in enumerate(markers):
        # book title: ALL-CAPS lines just above (skip separators)
        title_parts = []
        for j in range(mi - 1, max(0, mi - 5), -1):
            s = lines[j].strip()
            if not s or set(s) == {"_"}:
                continue
            # normalize spaced caps like "E Z E K I E L" -> "EZEKIEL"
            # (collapse runs of single uppercase letters)
            s = re.sub(r"\b(?:[A-Z] ){2,}[A-Z]\b",
                       lambda m: m.group(0).replace(" ", ""), s)
            if s.isupper() or s[:-1].isupper():
                title_parts.insert(0, s.rstrip("."))
            else:
                break
        title = " ".join(title_parts)
        # Special case: Samuel books contain "FIRST/SECOND BOOK OF THE KINGS"
        # as an alias; prioritize SAMUEL.
        if "SAMUEL" in title:
            key = "FIRST BOOK OF SAMUEL" if "FIRST BOOK OF SAMUEL" in title else "SECOND BOOK OF SAMUEL"
        else:
            # find key in BOOK_MAP (longest match first to avoid "JOHN" beating "1 JOHN")
            key = None
            for k in sorted(BOOK_MAP, key=len, reverse=True):
                if k in title:
                    key = k
                    break
        if not key:
            raise RuntimeError(f"unmapped book title: {title}")
        start = mi
        end = markers[idx + 1] if idx + 1 < len(markers) else len(lines)
        # include from the title start
        tstart = mi - len(title_parts) - 2
        books.append((key, "\n".join(lines[tstart:end])))
    return books

def parse_chapters(book_key, book_text, canon):
    """Split book into chapters. Returns list of (chapter_num, chapter_text)."""
    # Chapters marked "CHAPTER N", "PSALM N", or "CHAPTER (ELEGY) N" (Lamentations)
    pat = re.compile(r"^   (?:CHAPTER(?: \(ELEGY\))?|PSALM) (\d+)\s*$", re.M)
    parts = pat.split(book_text)
    # parts[0] = pre-chapter (book intro), then alternating num, text
    chapters = []
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        txt = parts[i + 1]
        chapters.append((num, txt))
    # Single-chapter books (Philemon, Jude, 2/3 John) may lack "CHAPTER 1";
    # treat whole book as chapter 1.
    if not chapters:
        chapters = [(1, book_text)]
    return chapters

def contiguous_groups(vpart):
    """Split a verse ref like '13-22,28' or '4,15,22' into contiguous (vs,ve) groups.
    Adjacent numbers merge: '3,4' -> [(3,4)]; '13-22,28' -> [(13,22),(28,28)];
    '32-38,44-46' -> [(32,38),(44,46)]."""
    vpart = vpart.replace("–", "-").replace(" ", "")
    runs = []
    for chunk in vpart.split(","):
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            runs.append((int(a), int(b)))
        else:
            runs.append((int(chunk), int(chunk)))
    runs.sort()
    merged = []
    for a, b in runs:
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged

def parse_sections(ch_text, ch_num, max_verse):
    """Parse sections from chapter text.
    Section header: 'Ge 1:1, 2. Title.' or 'Ps 119:1-8. ...' etc.
    Cross-chapter header: 'Isa 8:1-9:7.' (stored under start chapter).
    Returns (intro, [(vs, ve, title, text, ref), ...]).
    False-positive guard: a header whose explicit chapter differs from the
    enclosing chapter is a wrapped cross-reference line, not a header
    (verified: all 72 such cases in the 1871 text are wrapped '(See X Y:Z)'
    lines). Title is same-line only (\\s* previously swallowed the first
    body line into the title for 63 untitled sections).
    """
    # Header pattern: ABBREV CH:VERSES. Title  OR  ABBREV VERSES. Title (single-ch books)
    # e.g. "Ge 1:1, 2.", "Ps 119:1-8.", "2Jo 1-13.", "Phm 1-25."
    hdr = re.compile(r"^   ([1-3]?[A-Za-z]+) (?:(\d+):)?([\d,\-– ]+)\.([ \t]*)(.*)$", re.M)
    # Cross-chapter header: "Isa 8:1-9:7.", "Ac 13:1-14:28."
    xchap = re.compile(r"^   ([1-3]?[A-Za-z]+) (\d+):([\d,\-– ]+)-(\d+):([\d,\-– ]+)\.([ \t]*)(.*)$", re.M)
    matches = []
    for m in hdr.finditer(ch_text):
        ch_s = m.group(2)
        if ch_s and int(ch_s) != ch_num:
            continue  # wrapped cross-reference, not a header
        if not resolve_abbrev(m.group(1)):
            continue  # English word matching the pattern, not a book abbrev
        matches.append((m.start(), m.end(), "std", m))
    for m in xchap.finditer(ch_text):
        if int(m.group(2)) != ch_num:
            continue
        if not resolve_abbrev(m.group(1)):
            continue
        matches.append((m.start(), m.end(), "xchap", m))
    matches.sort()
    if not matches:
        return ch_text.strip(), []
    intro = ch_text[:matches[0][0]].strip()
    # intro: drop leading _____ separators
    intro = re.sub(r"^_+\s*", "", intro).strip()
    sections = []
    for idx, (s0, e0, kind, m) in enumerate(matches):
        end = matches[idx + 1][0] if idx + 1 < len(matches) else len(ch_text)
        body = ch_text[e0:end].strip()
        # clean: collapse whitespace, but preserve paragraphs
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n[ \t]+", "\n", body)
        body = re.sub(r"\n{3,}", "\n\n", body)
        if kind == "std":
            abbrev = m.group(1)
            title = m.group(5).strip()
            for vs, ve in contiguous_groups(m.group(3)):
                sections.append((abbrev, vs, ve, title, body,
                                 f"{m.group(1)} {m.group(2)+':' if m.group(2) else ''}{m.group(3).strip()}"))
        else:
            abbrev = m.group(1)
            v1 = contiguous_groups(m.group(3))[0][0]
            title = m.group(7).strip()
            ref = f"{m.group(1)} {m.group(2)}:{m.group(3).strip()}-{m.group(4)}:{m.group(5).strip()}"
            sections.append((abbrev, v1, max_verse, title, body, ref))
    return intro, sections

def main():
    import db as dbmod
    bounds = dbmod.get_bounds("KJV")
    text = JFB_TXT.read_text(encoding="utf-8", errors="replace")
    books = split_books(text)
    print(f"books found: {len(books)}")
    result = {"_meta": {
        "source": "Christian Classics Ethereal Library (ccel.org)",
        "work": "Jamieson, Fausset & Brown, Commentary Critical and Explanatory on the Whole Bible",
        "print_basis": "1871", "rights": "Public Domain", "ccel_status": "Proofed",
        "retrieval_date": "2026-09-20",
        "source_file": "https://ccel.org/ccel/h/jamieson/jfb/cache/jfb.txt",
    }}
    total_chapters = 0
    for book_key, book_text in books:
        canon = BOOK_MAP[book_key]
        chapters = parse_chapters(book_key, book_text, canon)
        for ch_num, ch_text in chapters:
            maxv = bounds[canon]["max_verse"][ch_num]
            intro, sections = parse_sections(ch_text, ch_num, maxv)
            # For "2 John" (combined 2/3 section), keep only 2Jo sections
            if canon == "2 John":
                sections = [s for s in sections if s[0] == "2Jo"]
                if not sections:
                    continue
            key = f"{canon}_{ch_num}"
            result[key] = {
                "book": canon, "chapter": ch_num,
                "intro": intro,
                "sections": [{"verse_start": vs, "verse_end": ve,
                              "title": t, "text": b, "ref": r}
                             for _, vs, ve, t, b, r in sections],
            }
            total_chapters += 1
    out = RAW / "CCEL_JFB.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {out}: {len(result)-1} chapter entries")

if __name__ == "__main__":
    main()
