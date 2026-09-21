#!/usr/bin/env python3
"""Parse Keil & Delitzsch combined OCR volumes into commentary rows.

Source files: data/raw_v2/keil_delitzsch/0{1..6}.*._djvu.txt
  (Google/Cornell scans of T&T Clark 1864-1892 English translation;
   underlying work is public domain.)

Output: staging SQLite DB with `commentaries` rows
  (source_id, book, book_order, start_chapter, start_verse,
   end_chapter, end_verse, text).

Segmentation rules (match the granularity of the existing v2 ingest):
  - A "Chap." header starts a chapter section.
  - A "Ver."/"Vers." header starts a verse subsection.
  - Each row's text begins with its header line and runs to the next
    header (chapter or verse), with running heads, page numbers,
    "Digitized by Google" markers and similar artifacts removed and
    whitespace normalized (double spaces -> single).

Only the Keil/Delitzsch exposition is parsed. Front matter that belongs
to other works bound into the same scan (e.g. Zockler/Lange material in
vol. 4, duplicate Exodus copy in vol. 1, Daniel portion of vol. 6) is
excluded via explicit segment boundaries below.
"""

import re
import sqlite3
import sys

DATA = "data/raw_v2/keil_delitzsch"

ROMAN_VALS = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}


def roman_to_int(s):
    """Parse a roman numeral, tolerating common OCR confusions."""
    s = s.lower().strip().rstrip('.')
    # common OCR substitutions
    s = s.replace('j', 'i')
    # 'l' misread for 'i' after i/v (never valid in real numerals there):
    # "xvil" -> "xvii" (17), but "xl" (40) is kept.
    s = re.sub(r'(?<=[iv])l', 'i', s)
    total = 0
    vals = [ROMAN_VALS.get(ch, 0) for ch in s]
    if not vals or any(v == 0 for v in vals):
        return None
    for i, v in enumerate(vals):
        nxt = vals[i + 1] if i + 1 < len(vals) else 0
        total += -v if v < nxt else v
    return total if total > 0 else None


def clean_line(s):
    s = s.replace('\u00a0', ' ')
    s = re.sub(r'[ \t]+', ' ', s).strip()
    return s


ARTIFACT_RES = [
    re.compile(r'^Digitized\s+by\s+\S+\s*$', re.I),
    re.compile(r'^ *[0-9]{1,4} +[A-Z][A-Z ,;:\-\.\(\)\']{8,}$'),  # "418 THE SECOND BOOK OF MOSES."
    re.compile(r'^ *[0-9]{1,4}\s*$'),  # bare page number
    re.compile(r'^Google\s*$', re.I),
    re.compile(r'^V\s*$'),
    re.compile(r'^■+\s*$'),
]


def is_artifact(s):
    return any(rx.match(s) for rx in ARTIFACT_RES)


# A running head: "CHAP. I. 8-14. 419" or "CHAP. XII. 1-3. 193"
# (reference only, no title; ends with a page number). Used to track the
# current chapter when exposition lacks a Chap. header. Tolerates OCR
# noise in the verse-range portion; only the chapter numeral is used.
RUNNING_HEAD_RE = re.compile(
    r'^(CHAP|Chap)[\.,]\s+([ivxlcj]+)\b.{0,40}?\s(\d{1,4})\s*$', re.I)


def parse_running_head(s):
    """Return the chapter number from a running head, or None."""
    if len(s) > 70:
        return None
    m = RUNNING_HEAD_RE.match(s)
    if not m:
        return None
    # must not contain title words: strip the "Chap." keyword, the roman
    # numeral, and all numbers; whatever letter-words remain are a title.
    rest = re.sub(r'^(CHAP|Chap)[\.,]\s+[ivxlcj]+\b', '', s, flags=re.I)
    rest = re.sub(r'[\d\.\,\-\s\(\)xX]+', ' ', rest)
    if re.search(r'[A-Za-z]{3,}', rest):
        return None
    ch = roman_to_int(m.group(2))
    if ch is None or ch > 150:
        return None
    return ch


# Chapter section header, e.g.:
#   "Chap. i. 1."  "Chap. ii. 1-3. The Sabbath of Creation. -"
#   "Chap. ii. 4-iv. 26."  "Chap. v. Pharaoh's answer ..."
#   "CHAP. III. AND IV."
CHAP_RE = re.compile(
    r'^(Chap|CHAP|ohap|JIHAP)[\.,]\s+'
    r'([ivxlcj]+)\s*\.?\s*'
    r'(?:(\d+)\s*(?:[-xX]\s*([ivxlcj]+)?\.?\s*(\d+)?)?)?'
    r'\s*\.?\s*(.*)$', re.I)


def parse_chap_header(s):
    """Return (start_ch, start_v, end_ch, end_v, title) or None."""
    # Psalm headers: "PSALM I." (Delitzsch uses this, not "Chap.")
    s_clean = re.sub(r'\s+', ' ', s).strip()
    m_ps = re.match(r'^PSALM\s+([ivxlcj]+)\.?\s*(.*)$', s_clean, re.I)
    if m_ps:
        try:
            ch = roman_to_int(m_ps.group(1))
        except ValueError:
            pass
        else:
            title = m_ps.group(2).strip()
            return (ch, 1, ch, None, title)
    # A title may precede the header on the same line, e.g.
    # "MACHPELAH. CHAP. XXIII." -> parse from "CHAP." onward.
    # Only for UPPERCASE "CHAP." with an all-caps title (not lowercase
    # "chap." citations inside prose like "In chap. i. 27 the creation").
    m0 = re.search(r'\b(CHAP)[\.,]\s+[ivxlcj]+\b', s, re.I)
    if m0 and m0.start() > 0:
        title_part = s[:m0.start()].strip()
        if title_part and re.fullmatch(r'[A-Z0-9\s\.\,\;\:\-\—\'\"]+', title_part):
            s = s[m0.start():]
    m = CHAP_RE.match(s)
    if not m:
        return None
    ch1 = roman_to_int(m.group(2))
    if ch1 is None:
        return None
    # Guard against prose cross-references like
    # "chap. xiii. 16, xv. 4, 5, with regard to Isaac" or
    # "chap. xxii. 20-23), and Haran as the father of Lot":
    # a real header names a single range and is followed by end-of-line,
    # a period+title, or an em dash -- not by a comma+another reference,
    # a closing paren, or lowercase prose continuation.
    rest = m.group(0)[m.end(2):]
    if re.match(r'\s*\.?\s*\d+\s*,\s*([ivxlc]+\.|(Ex|Gen|Lev|Num|Deut)\.)', rest, re.I):
        return None
    # find where the verse-range part ends, then inspect what follows
    m2 = re.match(r'\s*\.?\s*(\d+\s*(?:[-xX]\s*(?:[ivxlcj]+\.?)?\s*\d+)?)?\s*\.?', rest, re.I)
    after = rest[m2.end():] if m2 else rest
    if after and after[0] in ',;)]':
        return None
    if after and re.match(r'^[a-z]', after) and not re.match(r'^(sq|ff)\b', after, re.I):
        # lowercase continuation word (not sq./ff.) => prose citation
        # (real titles start uppercase or with a dash/quote)
        if len(after.split()) > 2:
            return None
    v1_s, ch2_s, v2_s, title = m.group(3), m.group(4), m.group(5), m.group(6).strip()
    start_v = int(v1_s) if v1_s else 1
    if ch2_s:
        end_ch = roman_to_int(ch2_s)
        if end_ch is None:
            return None
    else:
        end_ch = ch1
    end_v = int(v2_s) if v2_s else (None if not v1_s else start_v)
    # reject running heads that slipped through (title is just a page number)
    if title and re.fullmatch(r'\d{1,4}', title):
        return None
    return (ch1, start_v, end_ch, end_v, title)


# Verse header, e.g.: "Ver. 1.", "Vers. 1, 2.", "Vers. 7 sq.", "Ver. 5. "text""
# Requires UPPERCASE "V" to avoid prose citations like "ver. 2 to commence"
# that wrap to line start.
VERS_RE = re.compile(
    r'^(Vers?|Vens)\.\s+(\d+)\s*'
    r'(?:([,\-xX]|sq\.?|sqq\.?)\s*(\d+)?)?'
    r'\s*\.?\s*(.*)$')


def parse_vers_header(s, cur_ch):
    """Return (start_v, end_v, rest) or None. cur_ch may be None."""
    m = VERS_RE.match(s)
    if not m:
        return None
    v1 = int(m.group(2))
    sep, v2_s = m.group(3), m.group(4)
    rest = m.group(5).strip()
    if v2_s and sep and sep.strip() not in ('sq.', 'sq', 'sqq.', 'sqq'):
        end_v = int(v2_s)
    else:
        end_v = v1
    # guard: "Ver." inside ordinary prose, e.g. "(cf. ver. 5)" won't be at line start;
    # also reject lines where the "verse" number is implausibly large
    if v1 > 176:
        return None
    return (v1, end_v, rest)


def load_verse_counts(db_path="data/scripture.db"):
    """Map (book_order, chapter) -> verse count from the scripture DB."""
    con = sqlite3.connect(db_path)
    counts = {}
    try:
        # Use a single translation (KJV has complete 66-book coverage);
        # the verses table holds 11 translations, so an unfiltered
        # COUNT(*) would multiply by translation.
        rows = con.execute(
            "SELECT book_order, chapter, COUNT(*) FROM verses "
            "WHERE translation='KJV' "
            "GROUP BY book_order, chapter").fetchall()
        for bo, ch, n in rows:
            counts[(bo, ch)] = n
    except Exception:
        pass
    con.close()
    return counts


BOOK_MAX_CHAPTERS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36,
    'Deuteronomy': 34, 'Joshua': 24, 'Judges': 21, 'Ruth': 4,
    '1 Samuel': 31, '2 Samuel': 24, '1 Kings': 22, '2 Kings': 25,
    '1 Chronicles': 29, '2 Chronicles': 36, 'Ezra': 10, 'Nehemiah': 13,
    'Esther': 10, 'Job': 42, 'Psalms': 150, 'Proverbs': 31,
    'Ecclesiastes': 12, 'Song of Songs': 8, 'Isaiah': 66, 'Jeremiah': 52,
    'Lamentations': 5, 'Ezekiel': 48, 'Daniel': 12, 'Hosea': 14,
    'Joel': 3, 'Amos': 9, 'Obadiah': 1, 'Jonah': 4, 'Micah': 7,
    'Nahum': 3, 'Habakkuk': 3, 'Zephaniah': 3, 'Haggai': 2,
    'Zechariah': 14, 'Malachi': 4,
}


BOOK_ORDERS = {
    # scripture.db verses.book_order is 0-indexed; subtract 1 for lookups.
    'Genesis': 1, 'Exodus': 2, 'Leviticus': 3, 'Numbers': 4, 'Deuteronomy': 5,
    'Joshua': 6, 'Judges': 7, 'Ruth': 8, '1 Samuel': 9, '2 Samuel': 10,
    '1 Kings': 11, '2 Kings': 12, '1 Chronicles': 13, '2 Chronicles': 14,
    'Ezra': 15, 'Nehemiah': 16, 'Esther': 17, 'Job': 18, 'Psalms': 19,
    'Proverbs': 20, 'Ecclesiastes': 21, 'Song of Songs': 22,
    'Isaiah': 23, 'Jeremiah': 24, 'Lamentations': 25, 'Ezekiel': 26,
    'Daniel': 27, 'Hosea': 28, 'Joel': 29, 'Amos': 30, 'Obadiah': 31,
    'Jonah': 32, 'Micah': 33, 'Nahum': 34, 'Habakkuk': 35,
    'Zephaniah': 36, 'Haggai': 37, 'Zechariah': 38, 'Malachi': 39,
}


def parse_segment(lines, book, book_order, verse_counts, start_ch=1):
    """Parse one book's exposition lines into row dicts."""
    rows = []
    cur = None  # current open row
    cur_ch = None
    prev_ch = start_ch - 1
    # Single-chapter books (Obadiah): default to chapter 1
    if BOOK_MAX_CHAPTERS.get(book) == 1:
        cur_ch = 1
        prev_ch = 1

    def note_chapter(ch):
        """Adopt a chapter from a running head if plausible in context."""
        nonlocal cur_ch, prev_ch
        if ch is None:
            return
        max_ch = BOOK_MAX_CHAPTERS.get(book, 150)
        if ch > max_ch:
            return  # OCR error (e.g. "L" for "I")
        # Plausible if we have no chapter yet, or it advances modestly.
        # (Rejects OCR errors like "CHAP. L" (=50) when expecting ch. 2.)
        if cur_ch is None or (cur_ch <= ch <= cur_ch + 3):
            cur_ch = ch
            if ch > prev_ch:
                prev_ch = ch

    def flush():
        nonlocal cur
        if cur and cur['parts']:
            text = ' '.join(cur['parts']).strip()
            text = re.sub(r'\s+', ' ', text)
            if len(text) >= 40:
                end_v = cur['end_v']
                if end_v is None:
                    # scripture.db book_order is 0-indexed; ours is 1-indexed
                    end_v = verse_counts.get((book_order - 1, cur['end_ch']),
                                             cur['start_v'])
                rows.append({
                    'book': book, 'book_order': book_order,
                    'start_chapter': cur['start_ch'], 'start_verse': cur['start_v'],
                    'end_chapter': cur['end_ch'], 'end_verse': end_v,
                    'text': text,
                })
        cur = None

    def new_row(sch, sv, ech, ev, header):
        nonlocal cur
        flush()
        cur = {'start_ch': sch, 'start_v': sv, 'end_ch': ech, 'end_v': ev,
               'parts': [header]}

    # Precompute ALL running-head chapters by line index (no plausibility
    # filter here; the main loop validates against current chapter context).
    rh_by_line = {}
    for idx, raw in enumerate(lines):
        s = clean_line(raw)
        if not s:
            continue
        ch = parse_running_head(s)
        if ch is not None:
            rh_by_line[idx] = ch

    def chapter_ahead(from_idx, max_dist=45):
        """Chapter of the next running head within max_dist lines."""
        for idx in range(from_idx + 1, min(from_idx + max_dist, len(lines))):
            if idx in rh_by_line:
                return rh_by_line[idx]
        return None

    prev_v = 0  # previous verse number (to detect resets)
    for idx, raw in enumerate(lines):
        s = clean_line(raw)
        if not s or is_artifact(s):
            continue
        if idx in rh_by_line:
            note_chapter(rh_by_line[idx])
            continue
        ch = parse_chap_header(s)
        if ch:
            sch, sv, ech, ev, title = ch
            # Reject chapters beyond the book's max (OCR "L" for "I", etc.)
            max_ch = BOOK_MAX_CHAPTERS.get(book, 150)
            if sch > max_ch:
                # OCR heuristic: "L" (50) at book start is often "I" (1)
                if sch == 50 and cur_ch is None:
                    sch = 1
                    ech = 1 if ech == 50 else ech
                else:
                    continue
            if ech > max_ch:
                continue
            # sanity: chapter numbers plausible for this book
            if sch > 150 or ech > 150 or (ev is not None and ev > 176):
                pass  # keep; validated later
            else:
                # Cap verses at canonical max (OCR may misread, e.g. 26 for 25).
                maxv_sch = verse_counts.get((book_order - 1, sch))
                if maxv_sch and sv > maxv_sch:
                    # verse exceeds chapter max: wrong chapter; skip line
                    continue
                else:
                    if maxv_sch and ev is not None and ech == sch and ev > maxv_sch:
                        ev = maxv_sch
                    cur_ch = sch
                    prev_ch = max(prev_ch, sch)
                    prev_v = 0
                    new_row(sch, sv, ech, ev, s)
                    continue
        if cur_ch is not None:
            vh = parse_vers_header(s, cur_ch)
            if vh:
                v1, v2, rest = vh
                use_ch = cur_ch
                maxv = verse_counts.get((book_order - 1, cur_ch))
                # If verses exceed the current chapter's max, the chapter may
                # be misassigned (running-head OCR error). Try next chapters.
                if maxv and (v1 > maxv or (v2 is not None and v2 > maxv)):
                    for cand in range(cur_ch + 1, cur_ch + 4):
                        cand_max = verse_counts.get((book_order - 1, cand))
                        if cand_max and v1 <= cand_max and (v2 is None or v2 <= cand_max):
                            use_ch = cand
                            cur_ch = cand
                            prev_ch = max(prev_ch, cand)
                            maxv = cand_max
                            break
                    else:
                        # No fitting chapter: cap verses at max, keep content.
                        if v1 > maxv:
                            continue  # skip; verse not in this chapter
                        if v2 is not None and v2 > maxv:
                            v2 = maxv
                # Chapter may have turned without an explicit Chap. header:
                # if the verse number is small (chapter start) and a running
                # head just ahead names a higher chapter, adopt it.
                if v1 <= 3:
                    ahead = chapter_ahead(idx)
                    if (ahead is not None and ahead > cur_ch
                            and ahead <= cur_ch + 3):
                        use_ch = ahead
                        cur_ch = ahead
                        prev_ch = max(prev_ch, ahead)
                prev_v = v1
                new_row(use_ch, v1, use_ch, v2, s)
                continue
        if cur is not None:
            cur['parts'].append(s)
        # text before the first header is introduction/front matter: dropped
    flush()
    return rows


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data/staging/kd_complete.db"
    verse_counts = load_verse_counts()
    print(f"loaded verse counts for {len(verse_counts)} chapters")
    # Segments: (file, book, book_order, start_line_1idx, end_line_1idx)
    # Line numbers are 1-indexed as reported by grep/sed.
    F01 = "01.BCOT.KD.PentateuchMoses.vol.1.Law._djvu.txt"
    F02 = "02.BCOT.KD.HistoricalBooks.A.vol.2.EarlyProphets._djvu.txt"
    F03 = "03.BCOT.KD.HistoricalBooks.B.vol.3.LaterProphets._djvu.txt"
    F04 = "04.BCOT.KD.PoeticalBooks.vol.4.Writings._djvu.txt"
    F05 = "05.BCOT.KD.PropheticalBooks.A.vol.5.GreaterProphets._djvu.txt"
    F06 = "06.CBOT.KD.PropheticalBooks.B.vol.6.LesserProphets._djvu.txt"
    segments = [
        # File 01: Pentateuch
        # Genesis exposition starts ~1581 (after introduction)
        (F01, "Genesis", 1, 1581, 20961),
        # Exodus: two physical copies. First has ch 1-11, second has ch 12-40.
        (F01, "Exodus", 2, 20962, 26300),
        (F01, "Exodus", 2, 26516, 39391),
        # Leviticus, Numbers, Deuteronomy
        (F01, "Leviticus", 3, 39391, 51531),
        (F01, "Numbers", 4, 51531, 65969),
        (F01, "Deuteronomy", 5, 65969, 79634),
        # File 02: Early Prophets (Joshua, Judges, Ruth, Samuel, Kings)
        # Boundaries from subagent mapping 2026-09-20
        (F02, "Joshua", 6, 1685, 11945),
        (F02, "Judges", 7, 12535, 23402),
        (F02, "Ruth", 8, 23659, 25566),
        (F02, "1 Samuel", 9, 26209, 39169),
        (F02, "2 Samuel", 10, 39241, 51058),
        (F02, "1 Kings", 11, 51807, 66242),
        (F02, "2 Kings", 12, 66245, 78781),
        # File 03: Later Prophets (Chronicles, Ezra, Nehemiah, Esther, Job)
        # Boundaries from subagent mapping 2026-09-20
        (F03, "1 Chronicles", 13, 2858, 16312),
        (F03, "2 Chronicles", 14, 16312, 27598),
        (F03, "Ezra", 15, 28525, 33919),
        (F03, "Nehemiah", 16, 34557, 40875),
        (F03, "Esther", 17, 41613, 45442),
        # Job: two volumes. Vol I (47823-67059), Vol II (67736-85824)
        (F03, "Job", 18, 47823, 67059),
        (F03, "Job", 18, 67736, 86000),
        # File 04: Poetical Books (Psalms, Proverbs, Song, Ecclesiastes)
        # Boundaries from subagent mapping 2026-09-20
        # Psalms: 3 volumes
        # NOTE: Exclude Wetzstein excursus (L65685-65860, non-Delitzsch appendix)
        (F04, "Psalms", 19, 4436, 23998),
        (F04, "Psalms", 19, 24100, 45495),
        (F04, "Psalms", 19, 45633, 65685),
        (F04, "Psalms", 19, 65860, 66564),
        # Proverbs: 2 volumes
        (F04, "Proverbs", 20, 69606, 86936),
        (F04, "Proverbs", 20, 87005, 105189),
        # Song of Songs, Ecclesiastes
        # NOTE: Exclude Wetzstein appendix (L114441-115280, non-Delitzsch)
        (F04, "Song of Songs", 21, 106445, 114441),
        (F04, "Ecclesiastes", 22, 117474, 130483),
        # File 05: Greater Prophets (Isaiah, Jeremiah, Lamentations, Ezekiel)
        # Boundaries from subagent mapping 2026-09-20
        # Isaiah: 2 volumes (Vol I: 1-27, Vol II: 28-66)
        (F05, "Isaiah", 23, 3653, 25702),
        (F05, "Isaiah", 23, 25970, 51559),
        (F05, "Jeremiah", 24, 53316, 88859),
        (F05, "Lamentations", 25, 89844, 96670),
        (F05, "Ezekiel", 26, 97286, 133260),
        # File 06: Daniel (bound-in) + Minor Prophets
        # Boundaries from subagent mapping 2026-09-20
        # Daniel is Keil's commentary, bound before Minor Prophets
        (F06, "Daniel", 27, 3273, 24359),
        (F06, "Hosea", 28, 26813, 34161),
        (F06, "Joel", 29, 34665, 37399),
        (F06, "Amos", 30, 37742, 42728),
        (F06, "Obadiah", 31, 43378, 44804),
        (F06, "Jonah", 32, 45321, 46679),
        (F06, "Micah", 33, 46950, 51601),
        (F06, "Nahum", 34, 52910, 54882),
        (F06, "Habakkuk", 35, 55165, 58144),
        (F06, "Zephaniah", 36, 58566, 60458),
        (F06, "Haggai", 37, 60788, 62767),
        (F06, "Zechariah", 38, 63078, 72526),
        (F06, "Malachi", 39, 72823, 75013),
    ]
    import os
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    con = sqlite3.connect(out)
    con.execute("""CREATE TABLE IF NOT EXISTS kd_rows (
        book TEXT, book_order INT,
        start_chapter INT, start_verse INT,
        end_chapter INT, end_verse INT,
        text TEXT)""")
    con.execute("DELETE FROM kd_rows")
    total = 0
    for fname, book, bo, s1, s2 in segments:
        path = os.path.join(DATA, fname)
        lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
        # convert 1-indexed inclusive to 0-indexed slice
        seg = lines[s1 - 1:s2]
        rows = parse_segment(seg, book, bo, verse_counts)
        for r in rows:
            con.execute(
                "INSERT INTO kd_rows VALUES (?,?,?,?,?,?,?)",
                (r["book"], r["book_order"], r["start_chapter"],
                 r["start_verse"], r["end_chapter"], r["end_verse"],
                 r["text"]))
        total += len(rows)
        print(f"{book} ({s1}-{s2}): {len(rows)} rows")
    con.commit()
    con.close()
    print(f"total: {total} rows -> {out}")
    return 0


if __name__ == "__main__":
    main()
