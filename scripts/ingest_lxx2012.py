#!/usr/bin/env python3
"""LXX2012 ingest (batch 3, staging only): parse eBible eng-lxx2012 USFX into
data/staging/lxx2012.db, table `verses`.

Conventions:
- 0-based book_order matching scripts/ingest_translations_batch2.py for the
  canonical 39 OT books (0..38) and the 7 DRB deuterocanonical books (66..72).
- 8 additional LXX deuterocanonical/apocryphal books (not in DRB) get
  book_order 73..80, continuing the DRB numbering sequence.
- Verse numbering is kept EXACTLY as the LXX2012 source (Greek
  versification, e.g. Greek Psalm numbering). Source uses merged verse ids
  like "1-12" for single paragraphs covering a verse range; these are stored
  under the range's starting verse number (verse=1) so verse stays INTEGER.
- Verse text: footnotes (<f>) and cross-references (<x>) are stripped; all
  other inline markup (<add>, <q>, <it>, <sc>, <vp>, ...) is kept as plain
  text; whitespace normalized. All rows translation='LXX2012'.

Staging only: never touches data/scripture.db or data/study.db.
The coordinator merges later.

Usage: python3 scripts/ingest_lxx2012.py
"""
import hashlib
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_ZIP = ROOT / "data" / "raw_v2" / "lxx2012" / "eng-lxx2012_usfx.zip"
USFX_NAME = "eng-lxx2012_usfx.xml"
STAGING = ROOT / "data" / "staging" / "lxx2012.db"

# (USFX book id, canonical Phos name, book_order)
BOOKS = [
    # Canonical OT, same 0..38 convention as ingest_translations_batch2.py
    ("GEN", "Genesis", 0), ("EXO", "Exodus", 1), ("LEV", "Leviticus", 2),
    ("NUM", "Numbers", 3), ("DEU", "Deuteronomy", 4), ("JOS", "Joshua", 5),
    ("JDG", "Judges", 6), ("RUT", "Ruth", 7), ("1SA", "1 Samuel", 8),
    ("2SA", "2 Samuel", 9), ("1KI", "1 Kings", 10), ("2KI", "2 Kings", 11),
    ("1CH", "1 Chronicles", 12), ("2CH", "2 Chronicles", 13),
    ("EZR", "Ezra", 14), ("NEH", "Nehemiah", 15), ("EST", "Esther", 16),
    ("JOB", "Job", 17), ("PSA", "Psalms", 18), ("PRO", "Proverbs", 19),
    ("ECC", "Ecclesiastes", 20), ("SNG", "Song of Songs", 21),
    ("ISA", "Isaiah", 22), ("JER", "Jeremiah", 23), ("LAM", "Lamentations", 24),
    ("EZK", "Ezekiel", 25), ("DAN", "Daniel", 26), ("HOS", "Hosea", 27),
    ("JOL", "Joel", 28), ("AMO", "Amos", 29), ("OBA", "Obadiah", 30),
    ("JON", "Jonah", 31), ("MIC", "Micah", 32), ("NAM", "Nahum", 33),
    ("HAB", "Habakkuk", 34), ("ZEP", "Zephaniah", 35), ("HAG", "Haggai", 36),
    ("ZEC", "Zechariah", 37), ("MAL", "Malachi", 38),
    # Deuterocanon shared with DRB: identical names and book_order values
    # as the DRB rows already in scripture.db.
    ("TOB", "Tobit", 66), ("JDT", "Judith", 67), ("WIS", "Wisdom", 68),
    ("SIR", "Sirach", 69), ("BAR", "Baruch", 70),
    ("1MA", "1 Maccabees", 71), ("2MA", "2 Maccabees", 72),
    # LXX-only deuterocanonical/apocryphal books: continue DRB numbering.
    ("LJE", "Epistle of Jeremy", 73),
    ("S3Y", "Prayer of Azarias", 74),
    ("SUS", "Susanna", 75),
    ("BEL", "Bel and the Dragon", 76),
    ("1ES", "1 Esdras", 77),
    ("MAN", "Prayer of Manasses", 78),
    ("3MA", "3 Maccabees", 79),
    ("4MA", "4 Maccabees", 80),
]
BOOK_INFO = {bid: (name, order) for bid, name, order in BOOKS}

DEUTEROCANON_IDS = {
    "TOB", "JDT", "WIS", "SIR", "BAR",
    "LJE", "S3Y", "SUS", "BEL",
    "1MA", "2MA", "1ES", "MAN", "3MA", "4MA",
}

# Source-faithful merged verse ids (a single paragraph covering a range).
# Stored under the range's starting verse so `verse` stays INTEGER.
RANGE_RE = re.compile(r"^(\d+)-\d+$")

# Footnotes and cross-references are dropped entirely (with all content);
# everything else is flattened to plain text.
REMOVE_BLOCK_RE = re.compile(
    r"<(?:f|x)\b[^>]*>.*?</(?:f|x)>", re.DOTALL | re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def load_usfx() -> str:
    import zipfile
    with zipfile.ZipFile(RAW_ZIP) as z:
        return z.read(USFX_NAME).decode("utf-8")


def clean_text(chunk: str) -> str:
    # Footnotes/cross-refs are replaced with a space (block separation);
    # remaining inline markup (<add>, <it>, <q>, ...) is removed without
    # adding spaces so punctuation stays glued to its word
    # (e.g. "<add>servants</add>," -> "servants,").
    chunk = REMOVE_BLOCK_RE.sub(" ", chunk)
    chunk = TAG_RE.sub("", chunk)
    chunk = chunk.replace("\u00a0", " ")
    return WS_RE.sub(" ", chunk).strip()


def parse_verses(src: str):
    """Yield (usfx_id, name, order, chapter, verse, text) for every verse.

    Two segment types exist in this edition:
    - <v id="N"/> ... <ve/> : the source's own (Vatican/LXX) verse numbering.
      Merged ranges like id="1-12" are stored under the starting verse.
    - <vp>M)</vp>-led paragraphs with no <v> marker: appendix paragraphs
      (only in 1 Kings) carrying Brenton's numbering for text the Vatican
      order moves elsewhere (e.g. 1KI 3:36-46, 1KI 7:1-12, 1KI 11).
      These become rows keyed by the vp number. If a vp number collides
      with a <v> verse in the same chapter (1KI 11:1 and 11:6), the vp
      text is appended to that verse's text so no content is lost.
    <vp> markers that appear *inside* an open <v> segment are Brenton
    number annotations only; their text is part of the <v> verse.
    """
    book_splits = list(re.finditer(r'<book id="([A-Z0-9]{2,3})"[^>]*>', src))
    TOKEN_RE = re.compile(
        r'<v id="([^"]+)"[^>]*/>|<ve\s*/>|<vp>\s*(\d+)\)?\s*</vp>|<p\b[^>]*>|</p>',
        re.IGNORECASE)
    rows = []  # (bid, name, order, chapter, verse, text, kind)
    for i, m in enumerate(book_splits):
        bid = m.group(1)
        if bid in ("FRT", "INT"):
            continue  # front matter and introduction, not scripture
        if bid not in BOOK_INFO:
            raise ValueError(f"unknown book id in source: {bid}")
        name, order = BOOK_INFO[bid]
        end = book_splits[i + 1].start() if i + 1 < len(book_splits) else len(src)
        body = src[m.end():end]
        for cm in re.finditer(r'<c id="(\d+)"[^>]*/>', body):
            cstart = cm.end()
            nxt = body.find('<c id="', cstart)
            cbody = body[cstart:] if nxt == -1 else body[cstart:nxt]
            chapter = int(cm.group(1))
            # Footnotes and cross-refs are dropped before marker walking so
            # any <vp>-like text inside them can never open a segment.
            cbody = REMOVE_BLOCK_RE.sub(" ", cbody)
            stack = []  # open segments: [seq, kind, number, [chunks]]; vp nests in v
            para_start = True  # next <vp> would be paragraph-leading
            seq = 0  # segment open order, for document-order merging

            def flush_top():
                if not stack:
                    return
                _seq, kind, number, chunks = stack.pop()
                text = clean_text("".join(chunks))
                rows.append((bid, name, order, chapter, number, text, kind, _seq))

            def flush_all():
                while stack:
                    flush_top()

            pos = 0
            for tm in TOKEN_RE.finditer(cbody):
                chunk = cbody[pos:tm.start()]
                if chunk.strip():
                    para_start = False
                    if stack:
                        stack[-1][3].append(chunk)
                tok = tm.group(0).lower()
                if tm.group(1) is not None:  # <v id=.../>
                    flush_all()
                    vid = tm.group(1)
                    mr = RANGE_RE.match(vid)
                    seq += 1
                    stack.append([seq, "v",
                                  int(mr.group(1)) if mr else int(vid), []])
                    para_start = False
                elif tm.group(2) is not None:  # <vp>
                    num = int(tm.group(2))
                    if para_start or not stack or stack[-1][1] == "vp":
                        # Paragraph-leading <vp> (or one following another):
                        # nested segment; a still-open <v> resumes at </p>.
                        if stack and stack[-1][1] == "vp":
                            flush_top()
                        seq += 1
                        stack.append([seq, "vp", num, []])
                    else:
                        # Inline Brenton-number annotation inside a <v>
                        # segment: its text belongs to that verse.
                        stack[-1][3].append(" ")
                    para_start = False
                elif tok == "</p>":
                    if stack and stack[-1][1] == "vp":
                        flush_top()  # resume any enclosing <v> segment
                    para_start = True
                elif tok.startswith("<p"):
                    para_start = True
                else:  # <ve/>
                    flush_all()
                    para_start = False
                pos = tm.end()
            if pos < len(cbody) and stack:
                stack[-1][3].append(cbody[pos:])
            flush_all()

    # Merge rows sharing (book, chapter, verse): segment texts join in
    # document order (by segment open sequence). An empty <v> placeholder
    # (e.g. 1KI 7:1) contributes nothing, so the vp text naturally
    # replaces it.
    merged = {}
    for bid, name, order, ch, vs, text, kind, seqn in rows:
        key = (bid, ch, vs)
        if key not in merged:
            merged[key] = [bid, name, order, ch, vs, []]
        if text:
            merged[key][5].append((seqn, text))
    multi = sorted(k for k, b in merged.items() if len(b[5]) > 1)

    verses = [(b[0], b[1], b[2], b[3], b[4],
               " ".join(t for _, t in sorted(b[5])))
              for b in merged.values()]
    verses.sort(key=lambda v: (BOOKS.index((v[0], v[1], v[2])), v[3], v[4]))
    return verses, multi


def main():
    assert RAW_ZIP.exists(), f"missing raw file: {RAW_ZIP}"
    sha = hashlib.sha256(RAW_ZIP.read_bytes()).hexdigest()
    print("raw sha256:", sha)

    src = load_usfx()
    verses, multi_keys = parse_verses(src)
    print("parsed verses:", len(verses))
    print("keys merged from multiple source segments:", multi_keys)

    # Duplicate key check (book, chapter, verse must be unique).
    seen = {}
    dupes = []
    for v in verses:
        key = (v[1], v[3], v[4])
        if key in seen:
            dupes.append((key, seen[key], v[0]))
        seen[key] = v[0]
    assert not dupes, f"duplicate verse keys: {dupes[:10]}"

    # Deuterocanon coverage sanity: every mapped book should have verses.
    by_book = {}
    for v in verses:
        by_book.setdefault(v[0], 0)
        by_book[v[0]] += 1
    missing = [bid for bid in BOOK_INFO if bid not in by_book]
    assert not missing, f"mapped books with no verses: {missing}"
    deut_missing = [bid for bid in DEUTEROCANON_IDS if bid not in by_book]
    assert not deut_missing, f"deuterocanonical books missing: {deut_missing}"

    # All verse ids were numeric or N-M ranges (int() would have raised
    # otherwise). Exactly one known source gap has empty text: 1KI 14:1,
    # the placeholder for vv 1-20 whose text this edition does not supply
    # (its footnote says the substance is in the Vatican copy after 12:24).
    empties = [(v[1], v[3], v[4]) for v in verses if not v[5]]
    print("empty-text rows (source gaps):", empties)
    assert empties == [("1 Kings", 14, 1)], f"unexpected empty verses: {empties}"

    STAGING.parent.mkdir(parents=True, exist_ok=True)
    if STAGING.exists():
        STAGING.unlink()
    con = sqlite3.connect(STAGING)
    con.execute("""CREATE TABLE verses (
        translation TEXT, book TEXT, book_order INTEGER,
        chapter INTEGER, verse INTEGER, text TEXT)""")
    con.executemany(
        "INSERT INTO verses(translation, book, book_order, chapter, verse, text)"
        " VALUES ('LXX2012',?,?,?,?,?)",
        [(v[1], v[2], v[3], v[4], v[5]) for v in verses],
    )
    con.execute("CREATE INDEX idx_verses_key ON verses(book, chapter, verse)")
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
    assert total == len(verses)
    per_book = con.execute(
        "SELECT book, book_order, COUNT(*) FROM verses"
        " GROUP BY book, book_order ORDER BY book_order").fetchall()
    print("books staged:", len(per_book))
    for b in per_book:
        print(" ", b)
    con.close()
    print("wrote", STAGING, "-", total, "rows")


if __name__ == "__main__":
    main()
