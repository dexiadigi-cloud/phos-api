#!/usr/bin/env python3
"""Ingest John Gill's Exposition of the Entire Bible (1763) into study.db.

Source: Internet Archive djvu.txt OCR
  data/raw_v2/gill/gill_commentary.txt
  SHA-256: 0bd13225955a61956d826299122e7d8946a7c7b81a17e9e70395576e32c073ea
  Retrieved: 2026-09-20
Rights: John Gill d. 1771; 1763 edition is public domain. The IA OCR text is a
mechanical reproduction of a PD work and creates no new copyright.
Commercial use OK, no attribution required.

Document structure (verified 2026-09-20):
  - Verse headings: "Genesis 1:1" (full book names; "Song of Solomon" for
    Song of Songs). No range headings exist in this edition.
  - Book introductions: "INTRODUCTION TO GENESIS" etc. Titles vary wildly:
    "INTRODUCTION TO THE FIRST BOOK OF SAMUEL OTHERWISE", "INTRODUCTION TO
    REVELATIONS", "INTRODUCTION TO ECCLESIASTES, OR THE PREACHER", plus OCR
    junk ("INTRODUCTION TO RUTH l" = Ruth 1, "INTRODUCTION TO H PETER l" =
    1 Peter 1, "ISATAH", "PSALM" for Psalms, "DANIAL", ...). The book AND
    chapter are parsed from the title itself, because the IA file has
    scrambled page regions (whole Job displaced to a late chunk, Isaiah 64 +
    Isaiah book intro appended at EOF, single pages interleaved across books,
    e.g. a Revelation page inside Numbers 1) so positional anchors lie.
  - Chapter introductions: "INTRODUCTION TO GENESIS 1" (usually); three
    combined intros exist ("INTRODUCTION TO 2 CHRONICLES 3 & 4" etc.).
  - Order per chapter: "B C:1" heading -> [book intro] -> chapter intro ->
    verse-1 commentary (starts "Ver. 1.") -> "B C:2" heading ...
  - In-text scripture citations ("see\\nJob 39:5") can mimic headings on
    their own line. A heading is accepted only if the next content line is
    an INTRODUCTION line, a "Ver. N." marker for its verse, or it is exactly
    the expected next verse for its book. Everything else is logged+skipped.
  - Page markers ("Page N of 21577") and running heads are stripped, never
    stored.

Schema (exact PLAN.md commentaries schema, source_id='gill'):
  - book intro    -> (book, order, 0, 0, 0, 0)
  - chapter intro -> (book, order, C, 0, C2, 0)  (verse 0 = whole chapter;
                    C2>C only for the three combined intros)
  - verse note    -> (book, order, C, V, C, V)

Re-runnable: deletes existing source_id='gill' rows before insert.
Reads data/scripture.db READ-ONLY (KJV bounds) for ref validation.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "gill" / "gill_commentary.txt"
STUDY_DB = ROOT / "data" / "study.db"
LOG_PATH = ROOT / "verification" / "v2" / "raw" / "gill_skips.log"

import difflib
sys.path.insert(0, str(ROOT / "api"))
from db import get_bounds, get_verse  # noqa: E402  (read-only access)

SOURCE_ID = "gill"
EXPECTED_SHA256 = "0bd13225955a61956d826299122e7d8946a7c7b81a17e9e70395576e32c073ea"

CANON = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
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
         "3 John", "Jude", "Revelation"]
CSET = set(CANON)
BOOK_ALIASES = {"Song of Solomon": "Song of Songs"}

VPAT = re.compile(r"^\s*([0-9A-Za-z][A-Za-z0-9 .'\-]*?) (\d+):(\d+)\s*$")
IPAT = re.compile(r"^\s*INTRODUCTION (?:TO|OF) (.*\S)\s*$")
PGPAT = re.compile(r"^\s*Page \$?\d+ of \d+\s*$")
PGINLINE = re.compile(r"Page \$?\d+ of \d+")
RUNHEAD = re.compile(r'^(<ALIGN="CENTER")?John Gill\'s Exposition of the Entire Bible\.\s*$')
VERPAT = re.compile(r"^Ver[.,]?\s*(\d+)[.,]")

_ORD = {"FIRST": "1", "SECOND": "2", "THIRD": "3"}
_ROM = {"I": "1", "II": "2", "III": "3", "H": "1"}  # H = OCR junk for I
_BOOK_FIX = {"CORTHINIANS": "CORINTHIANS", "DANIAL": "DANIEL",
             "ISATAH": "ISAIAH", "LEVEITICUS": "LEVITICUS",
             "REVALATION": "REVELATION", "REVEALTION": "REVELATION"}

# Gill's in-text reference abbreviations, for the intro-title tiebreaker.
_BOOK_ABBR = {
 "Genesis": ["Ge", "Gen"], "Exodus": ["Ex"], "Leviticus": ["Le", "Lev"],
 "Numbers": ["Nu"], "Deuteronomy": ["De"], "Joshua": ["Jos"],
 "Judges": ["Jud"], "Ruth": ["Ru"], "1 Samuel": ["1Sa"],
 "2 Samuel": ["2Sa"], "1 Kings": ["1Ki"], "2 Kings": ["2Ki"],
 "1 Chronicles": ["1Ch"], "2 Chronicles": ["2Ch"],
 "Ezra": ["Ezr", "Ezra"], "Nehemiah": ["Ne"], "Esther": ["Es", "Est"],
 "Job": ["Job"], "Psalms": ["Ps"], "Proverbs": ["Pr", "Pro"],
 "Ecclesiastes": ["Ec"], "Song of Songs": ["So"], "Isaiah": ["Isa"],
 "Jeremiah": ["Jer"], "Lamentations": ["La"], "Ezekiel": ["Eze"],
 "Daniel": ["Da", "Dan"], "Hosea": ["Ho", "Hos"], "Joel": ["Joe"],
 "Amos": ["Am", "Amos"], "Obadiah": ["Ob"], "Jonah": ["Jon"],
 "Micah": ["Mic"], "Nahum": ["Na"], "Habakkuk": ["Hab"],
 "Zephaniah": ["Zep"], "Haggai": ["Hag"], "Zechariah": ["Zec"],
 "Malachi": ["Mal"], "Matthew": ["Mt"], "Mark": ["Mr", "Mk", "Mark"],
 "Luke": ["Lu", "Lk", "Luke"], "John": ["Joh", "John"],
 "Acts": ["Ac", "Acts"], "Romans": ["Ro", "Rom"],
 "1 Corinthians": ["1Co"], "2 Corinthians": ["2Co"],
 "Galatians": ["Ga", "Gal"], "Ephesians": ["Eph"],
 "Philippians": ["Php"], "Colossians": ["Col"],
 "1 Thessalonians": ["1Th"], "2 Thessalonians": ["2Th"],
 "1 Timothy": ["1Ti"], "2 Timothy": ["2Ti"], "Titus": ["Tit"],
 "Philemon": ["Phm"], "Hebrews": ["Heb"], "James": ["Jas"],
 "1 Peter": ["1Pe"], "2 Peter": ["2Pe"], "1 John": ["1Jo"],
 "2 John": ["2Jo"], "3 John": ["3Jo"], "Jude": ["Jude"],
 "Revelation": ["Re", "Rev"],
}


def count_refs(text: str, book: str, ch: int) -> int:
    """How often the text cites verses of (book, ch) in Gill's abbreviated
    style ("Nu 23:1"). Used to resolve mislabeled intro titles."""
    pat = r"\b(?:" + "|".join(_BOOK_ABBR[book]) + rf") {ch}:\d+"
    return len(re.findall(pat, text))


def normalize_book_name(name: str) -> str | None:
    n = name.upper().strip()
    n = re.sub(r",.*$", "", n)                      # ECCLESIASTES, OR THE PREACHER
    n = re.sub(r"^THE ", "", n)
    n = n.replace("BOOK OF ", "")
    n = n.replace("GENERAL EPISTLE OF ", "").replace("EPISTLE OF PAUL TO ", "")
    n = n.replace(" CAHPTER", "")                   # JEREMIAH CAHPTER 42
    n = re.sub(r"^(FIRST|SECOND|THIRD)\b", lambda m: _ORD[m.group(1)], n)
    n = re.sub(r"^([IV]+|H)\b", lambda m: _ROM[m.group(1)], n)
    n = re.sub(r"\bKING\b", "KINGS", n)              # FIRST KING 2
    n = re.sub(r"\bNUMBER\b", "NUMBERS", n)
    n = re.sub(r"\bPSALM\b", "PSALMS", n)
    n = re.sub(r"\bREVELATIONS\b", "REVELATION", n)
    n = re.sub(r"\s+(OTHERWISE|COMMONLY)\s*$", "", n)
    for bad, good in _BOOK_FIX.items():
        n = re.sub(r"\b" + bad + r"\b", good, n)
    if n == "SONG OF SOLOMON":
        n = "SONG OF SONGS"
    return next((b for b in CANON if b.upper() == n), None)


def parse_intro_title(title: str):
    """-> (book|None, chapter|None, end_chapter|None, extra_text).

    extra_text: for the one title line the OCR merged with the start of the
    intro prose ("INTRODUCTION TO I PETER 1 In this chapter, ...").
    """
    t = title.strip()
    extra = ""
    m = re.match(r"^(I PETER 1) (In this chapter.*)$", t)
    if m:
        t, extra = m.group(1), m.group(2)
    cands = []
    m = re.match(r"^(.*?) (\d+) & (\d+)\s*$", t)          # 2 CHRONICLES 3 & 4
    if m:
        cands.append((m.group(1), int(m.group(2)), int(m.group(3))))
    m = re.match(r"^(.*?) (\d+)\.?\s*$", t)               # NUMBERS 1 / ISAIAH 60.
    if m and "&" not in t:
        cands.append((m.group(1), int(m.group(2)), None))
    m = re.match(r"^(.*?) ([lI])\s*$", t)                 # RUTH l / H PETER l
    if m:
        cands.append((m.group(1), 1, None))
    cands.append((t, None, None))                         # book intro
    for name, ch, ch2 in cands:
        book = normalize_book_name(name)
        if book is not None:
            return book, ch, ch2, extra
    return None, None, None, extra


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def next_content(lines, i, limit=10):
    """First meaningful line after line i (skips blanks, page markers,
    running heads). Returns (line_number, stripped_text) or (None, '')."""
    for j in range(i + 1, min(i + 1 + limit, len(lines))):
        s = lines[j].strip()
        if not s or PGPAT.match(lines[j]) or RUNHEAD.match(lines[j]):
            continue
        return j, s
    return None, ""


def clean_text(raw_lines) -> str:
    """Rebuild paragraphs: drop page markers/running heads, join wrapped
    lines, keep blank-line paragraph breaks."""
    paras, cur = [], []
    for ln in raw_lines:
        if PGPAT.match(ln) or RUNHEAD.match(ln):
            continue
        s = PGINLINE.sub("", ln).strip()
        if not s:
            if cur:
                paras.append(" ".join(cur))
                cur = []
        else:
            cur.append(s)
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras).strip()


_kjv_cache: dict[tuple, str | None] = {}

def kjv_text(book: str, ch: int, v: int) -> str | None:
    key = (book, ch, v)
    if key not in _kjv_cache:
        kv = get_verse("KJV", book, ch, v)
        _kjv_cache[key] = kv["text"] if kv else None
    return _kjv_cache[key]

def _pn(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

def kjv_match(head: str, book: str, ch: int, v: int, thresh: float = 0.25) -> bool:
    """Does the head of a candidate note match the KJV verse text?
    Gill quotes (then truncates with '....') the verse he comments on, so a
    low difflib ratio means the text is NOT his note on this verse (foreign
    interleaved page). For Psalms, Gill's 'Ver. 1.' is the first content
    verse while KJV v1 is the superscription, so v2 is tried as fallback."""
    kt = kjv_text(book, ch, v)
    if not kt:
        return False
    if difflib.SequenceMatcher(None, _pn(kt[:80]), _pn(head[:150])).ratio() >= thresh:
        return True
    if book == "Psalms":
        kt2 = kjv_text(book, ch, 2)
        if kt2 and difflib.SequenceMatcher(
                None, _pn(kt2[:80]), _pn(head[:150])).ratio() >= thresh:
            return True
    return False


def main() -> None:
    digest = sha256_of(RAW)
    assert digest == EXPECTED_SHA256, f"SHA-256 mismatch: {digest}"
    print(f"raw sha256 OK: {digest[:16]}...")

    lines = RAW.read_text(encoding="utf-8", errors="replace").split("\n")
    print(f"lines: {len(lines)}")

    bounds = get_bounds("KJV")
    maxverse = {b: info["max_verse"] for b, info in bounds.items()}
    chapters_of = {b: info["chapters"] for b, info in bounds.items()}

    skips: list[str] = []

    # ---- Pass A: candidate verse headings, filtered ---------------------
    cands = []  # (lineno, book, ch, v)
    for i, ln in enumerate(lines):
        m = VPAT.match(ln)
        if not m:
            continue
        b = BOOK_ALIASES.get(m.group(1), m.group(1))
        if b not in CSET:
            continue
        cands.append((i, b, int(m.group(2)), int(m.group(3))))

    kept = []  # (lineno, book, ch, v)
    expected: dict[str, tuple[int, int] | None] = defaultdict(lambda: None)
    for i, b, ch, v in cands:
        _, nc = next_content(lines, i)
        is_intro = nc.startswith("INTRODUCTION ")
        mver = VERPAT.match(nc)
        ver_ok = bool(mver and int(mver.group(1)) == v)
        seq_ok = expected[b] == (ch, v)
        if is_intro or ver_ok or seq_ok:
            kept.append((i, b, ch, v))
            mv = maxverse[b].get(ch)
            if mv is None:
                expected[b] = None
            elif v < mv:
                expected[b] = (ch, v + 1)
            else:
                expected[b] = (ch + 1, 1)
        else:
            skips.append(f"citation-like heading line {i}: {b} {ch}:{v} "
                         f"-> next: {nc[:60]!r}")

    kept.sort(key=lambda t: t[0])
    print(f"verse headings kept: {len(kept)} (skipped {len(cands) - len(kept)})")

    # ---- Pass B: intro tokens, book+chapter parsed from the title --------
    events = []  # dicts: lino, kind, book, ch, v, ech, extra
    for i, ln in enumerate(lines):
        m = IPAT.match(ln)
        if not m:
            continue
        book, ch, ch2, extra = parse_intro_title(m.group(1))
        if book is None:
            skips.append(f"unparsed intro title line {i}: {m.group(1)[:60]!r}")
            continue
        if ch is None:
            events.append({"lino": i, "kind": "bookintro", "book": book,
                           "ch": 0, "v": 0, "ech": 0, "extra": extra})
        else:
            ech = ch2 or ch
            if not (1 <= ch <= ech <= chapters_of[book]):
                skips.append(f"intro chapter out of range line {i}: "
                             f"{book} {ch}" + (f" & {ch2}" if ch2 else ""))
                continue
            events.append({"lino": i, "kind": "chapintro", "book": book,
                           "ch": ch, "v": 0, "ech": ech, "extra": extra})

    # verse heading events; drop a "B C:1" heading immediately followed by an
    # intro event (its commentary is recovered via the Ver.1 split below)
    intro_linenos = {e["lino"] for e in events}
    for idx, (lino, b, ch, v) in enumerate(kept):
        nxts = [e["lino"] for e in events if e["lino"] > lino]
        if idx + 1 < len(kept):
            nxts.append(kept[idx + 1][0])
        first_next = min(nxts) if nxts else None
        if v == 1 and first_next in intro_linenos:
            intro_ev = next(e for e in events if e["lino"] == first_next)
            if (intro_ev["book"], intro_ev["ch"]) not in ((b, ch), (b, 0)):
                # Scrambled region: intro title disagrees with the verse-1
                # heading right before it (e.g. "Exodus 3:1" followed by
                # "INTRODUCTION TO EXODUS 2" whose text is all "Ex 3:x").
                # Let the intro's own verse references decide.
                after = next((e["lino"] for e in events
                              if e["lino"] > first_next), len(lines))
                block = "\n".join(lines[first_next + 1:after])
                h_refs = count_refs(block, b, ch)
                t_refs = count_refs(block, intro_ev["book"], intro_ev["ch"])
                if h_refs >= 2 and h_refs > t_refs:
                    skips.append(f"retitled intro line {first_next}: "
                                 f"{intro_ev['book']} {intro_ev['ch']} -> "
                                 f"{b} {ch} (refs {h_refs}:{t_refs})")
                    intro_ev["book"], intro_ev["ch"], intro_ev["ech"] = b, ch, ch
                    intro_linenos = {e["lino"] for e in events}
                else:
                    skips.append(f"dropped {b} {ch}:1 before mismatched intro "
                                 f"line {first_next}: {intro_ev['book']} "
                                 f"{intro_ev['ch']} (refs {h_refs}:{t_refs})")
            continue  # commentary recovered via Ver.1 split below
        events.append({"lino": lino, "kind": "verse", "book": b,
                       "ch": ch, "v": v, "ech": ch, "extra": ""})
    events.sort(key=lambda e: e["lino"])
    print(f"events: {len(events)} "
          f"({sum(1 for e in events if e['kind']=='bookintro')} bookintros, "
          f"{sum(1 for e in events if e['kind']=='chapintro')} chapintros, "
          f"{sum(1 for e in events if e['kind']=='verse')} verses)")

    # ---- Pass C: build rows ----------------------------------------------
    seen_keys: dict[tuple, tuple[int, str]] = {}  # key -> (score, text)

    def add_row(key, text):
        if not text:
            skips.append(f"empty text: {key}")
            return
        starts_ver = bool(re.match(r"^Ver[.,]?\s*\d+[.,]", text))
        score = (100000 if starts_ver else 0) + len(text)
        if key in seen_keys and seen_keys[key][0] >= score:
            skips.append(f"duplicate dropped: {key}")
            return
        if key in seen_keys:
            skips.append(f"duplicate replaced (longer): {key}")
        seen_keys[key] = (score, text)

    VERLINE = re.compile(r"^Ver[.,]?\s*(\d+)\b")
    last_intro = None  # (book, ch) of most recent intro event (ch=0: bookintro)

    for ei, ev in enumerate(events):
        lino, kind = ev["lino"], ev["kind"]
        end = events[ei + 1]["lino"] if ei + 1 < len(events) else len(lines)
        span = ([ev["extra"]] if ev["extra"] else []) + lines[lino + 1:end]
        if kind == "bookintro":
            b = ev["book"]
            last_intro = (b, 0)
            # The book intro may contain "Ver. 1." for chapter 1 verse 1:
            # - Single-chapter books: no chapter intro exists (3 John).
            # - Scrambled order: "[Book] 1:1" heading comes BEFORE the book
            #   intro (Matthew, Mark, Luke, John, Acts). Split it out if
            #   KJV-valid and (b,1,1) has no row yet.
            need_split = (chapters_of.get(b, 0) == 1
                          or (b, 1, 1, 1, 1) not in seen_keys)
            split_at = None
            if need_split:
                cands = []
                for j, ln in enumerate(span):
                    s = ln.strip()
                    if not s or PGPAT.match(ln) or RUNHEAD.match(ln):
                        continue
                    mver = VERLINE.match(s)
                    if mver and int(mver.group(1)) == 1:
                        cands.append(j)
                for j in cands:
                    if kjv_match(clean_text(span[j:j + 12]), b, 1, 1):
                        split_at = j
                        break
                if cands and split_at is None:
                    skips.append(f"no KJV-valid Ver.1 in bookintro {b} "
                                 f"(line {lino + 1}); verse 1 left missing")
            if split_at is not None:
                add_row((b, 0, 0, 0, 0), clean_text(span[:split_at]))
                add_row((b, 1, 1, 1, 1), clean_text(span[split_at:]))
            else:
                add_row((b, 0, 0, 0, 0), clean_text(span))
        elif kind == "chapintro":
            b, ch, ech = ev["book"], ev["ch"], ev["ech"]
            last_intro = (b, ch)
            # All "Ver. 1." candidates: foreign pages interleave, so the
            # first one may be another verse's note (e.g. Ephesians 5:1
            # inside the Leviticus 19 intro). Use the first candidate whose
            # text matches this verse's KJV text (Psalms: v2 fallback).
            cands = []
            for j, ln in enumerate(span):
                s = ln.strip()
                if not s or PGPAT.match(ln) or RUNHEAD.match(ln):
                    continue
                mver = VERLINE.match(s)
                if mver and int(mver.group(1)) == 1:
                    cands.append(j)
            split_at = None
            for j in cands:
                if kjv_match(clean_text(span[j:j + 12]), b, ch, 1):
                    split_at = j
                    break
            if cands and split_at is None:
                skips.append(f"no KJV-valid Ver.1 in chapintro {b} {ch} "
                             f"(line {lino + 1}); verse 1 left missing")
            elif len(cands) > 1 and split_at != cands[0]:
                skips.append(f"chapintro {b} {ch}: skipped foreign Ver.1 "
                             f"at line {lino + 1 + cands[0]}")
            if split_at is not None:
                add_row((b, ch, 0, ech, 0), clean_text(span[:split_at]))
                add_row((b, ch, 1, ch, 1), clean_text(span[split_at:]))
            else:
                add_row((b, ch, 0, ech, 0), clean_text(span))
        else:  # verse
            b, ch, v = ev["book"], ev["ch"], ev["v"]
            # Line-start "Ver. N." markers in this span, in order.
            marks = []
            for j, ln in enumerate(span):
                s = ln.strip()
                if not s:
                    continue
                mver = VERLINE.match(s)
                if mver:
                    marks.append((j, int(mver.group(1))))
            own_at = next((j for j, w in marks if w == v), None)
            foreign_marks = [(j, w) for j, w in marks if w != v]
            if own_at is not None:
                # Host note runs from its own marker to the first foreign
                # marker after it. Leading foreign pages are cut.
                # (Foreign PROSE without a Ver. marker, e.g. an intro
                # fragment interleaved before a foreign Ver., cannot be
                # reliably separated: legitimate notes cite other books
                # and continuations carry no refs. Left in place.)
                host_end = next((j for j, w in foreign_marks if j > own_at),
                                len(span))
                host_lines = span[own_at:host_end]
            else:
                # No own marker: the block may be a foreign interleaved
                # page (e.g. Revelation text under "Exodus 18:5"). Keep it
                # only if it quotes the verse or clearly discusses it.
                host_end = next((j for j, w in marks if w != v), len(span))
                host_lines = span[:host_end]
                htext = clean_text(host_lines)
                if htext and not kjv_match(htext, b, ch, v, thresh=0.2) \
                        and count_refs(htext, b, ch) < 2:
                    skips.append(f"unverified verse block dropped: {b} "
                                 f"{ch}:{v} (line {lino + 1}, "
                                 f"head {htext[:60]!r})")
                    host_lines = []
            if host_lines:
                add_row((b, ch, v, ch, v), clean_text(host_lines))
            # Orphan segments: foreign "Ver. W." markers. Each runs to the
            # next marker of any kind. Try to rehome via KJV text match,
            # preferring the most recent intro's (book, chapter).
            for j, w in foreign_marks:
                seg_end = next((jj for jj, ww in marks if jj > j), len(span))
                if own_at is not None and own_at <= j < host_end:
                    continue  # inside host range (should not happen)
                otext = clean_text(span[j:seg_end])
                if not otext:
                    continue
                cands = []
                if last_intro is not None and last_intro[1] != 0:
                    cands.append(last_intro)
                cands.append((b, ch))
                placed = False
                for ib, ich in cands:
                    if not (1 <= ich <= chapters_of.get(ib, 0)):
                        continue
                    if not (1 <= w <= maxverse[ib].get(ich, 0)):
                        continue
                    if not kjv_match(otext, ib, ich, w, thresh=0.4):
                        continue
                    key = (ib, ich, w, ich, w)
                    if key in seen_keys:
                        skips.append(f"orphan Ver.{w} at line "
                                     f"{lino + 1 + j}: {ib} {ich}:{w} "
                                     f"already has row, dropped")
                    else:
                        add_row(key, otext)
                        skips.append(f"rehomed orphan Ver.{w} at line "
                                     f"{lino + 1 + j} -> {ib} {ich}:{w}")
                    placed = True
                    break
                if not placed:
                    skips.append(f"orphan Ver.{w} at line {lino + 1 + j} "
                                 f"dropped (no KJV match; head "
                                 f"{otext[:60]!r})")

    rows = [(book, CANON.index(book) + 1, sc, sv, ec, ev, text)
            for (book, sc, sv, ec, ev), (score, text) in seen_keys.items()]

    # ---- Pass D: validate bounds ------------------------------------------
    valid = []
    for book, order, sc, sv, ec, ev, text in rows:
        if sc == 0 and sv == 0:  # book intro
            valid.append((book, order, sc, sv, ec, ev, text))
            continue
        if not (1 <= sc <= ec <= chapters_of[book]):
            skips.append(f"bad chapter: {book} {sc}-{ec}")
            continue
        if sv == 0:  # chapter intro
            valid.append((book, order, sc, sv, ec, ev, text))
            continue
        mv = maxverse[book].get(sc)
        if mv is None or not (1 <= sv <= mv):
            skips.append(f"verse out of bounds: {book} {sc}:{sv} "
                         f"(max {mv})")
            continue
        valid.append((book, order, sc, sv, ec, ev, text))
    print(f"valid rows: {len(valid)} (rejected {len(rows) - len(valid)})")

    # ---- Merge into study.db ----------------------------------------------
    con = sqlite3.connect(STUDY_DB)
    cur = con.cursor()
    cur.execute("DELETE FROM commentaries WHERE source_id = ?", (SOURCE_ID,))
    cur.execute("DELETE FROM sources WHERE source_id = ?", (SOURCE_ID,))
    cur.executemany(
        "INSERT INTO commentaries "
        "(source_id, book, book_order, start_chapter, start_verse, "
        " end_chapter, end_verse, text) VALUES (?,?,?,?,?,?,?,?)",
        [(SOURCE_ID, b, o, sc, sv, ec, ev, t)
         for b, o, sc, sv, ec, ev, t in valid],
    )
    cur.execute(
        "INSERT INTO sources "
        "(source_id, kind, title, rights, rights_basis, version, sha256) "
        "VALUES (?,?,?,?,?,?,?)",
        (SOURCE_ID, "commentary",
         "John Gill's Exposition of the Entire Bible (1763)",
         "Public Domain",
         "John Gill d. 1771; 1763 edition text is public domain. Internet "
         "Archive djvu.txt OCR is a mechanical reproduction of a PD work "
         "and creates no new copyright. Commercial use OK, no attribution "
         "required. Retrieved 2026-09-20.",
         "1763 edition / IA djvu.txt",
         digest),
    )
    con.commit()
    n_ins = cur.execute(
        "SELECT COUNT(*) FROM commentaries WHERE source_id = ?",
        (SOURCE_ID,)).fetchone()[0]
    con.close()
    print(f"inserted gill rows: {n_ins}")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(skips) + "\n")
    print(f"skips logged: {len(skips)} -> {LOG_PATH}")

    by_kind = defaultdict(int)
    for (book, sc, sv, ec, ev) in seen_keys:
        by_kind["bookintro" if sc == 0 else
                "chapintro" if sv == 0 else "verse"] += 1
    print("row kinds:", dict(by_kind))
    cov = defaultdict(set)
    for (book, sc, sv, ec, ev) in seen_keys:
        if sv == 0 and sc > 0:
            cov[book].add(sc)
    print("books with bookintro:",
          sum(1 for b in CANON
              if (b, 0, 0, 0, 0) in seen_keys), "/", len(CANON))


if __name__ == "__main__":
    main()
