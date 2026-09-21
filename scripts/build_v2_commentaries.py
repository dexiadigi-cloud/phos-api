#!/usr/bin/env python3
"""Build staging/commentaries_v2.db for the v2 study.db merge.

Writes the EXACT PLAN.md study.db commentaries schema (2026-09-20) - no
deviation:

    CREATE TABLE commentaries (
      id INTEGER PRIMARY KEY,
      source_id TEXT NOT NULL,
      book TEXT NOT NULL,               -- M1 canonical name ('Song of Songs')
      book_order INTEGER NOT NULL,      -- 1..66
      start_chapter INTEGER NOT NULL,
      start_verse INTEGER NOT NULL,     -- 0 = whole-chapter comment
      end_chapter INTEGER NOT NULL,
      end_verse INTEGER NOT NULL,       -- 0 = to end of chapter
      text TEXT NOT NULL
    );
    CREATE INDEX idx_commentaries_lookup
      ON commentaries(source_id, book_order, start_chapter, start_verse);

Sources:
- matthew_henry: HelloAO (1166 chapters) + CCEL gap-fill (23 chapters)
- jfb: CCEL 1871 proofed text (1189 chapters)
- barnes_nt: CCEL Barnes New Testament Notes (NT only, 27 books)

Section titles: the schema has no title column, so each section title is
folded into `text` as its first paragraph (documented, not a schema change).

Does NOT create data/study.db. Does NOT write to data/scripture.db
(read-only via api/db.py, URI mode=ro).
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ / "api"))
import parser
import db

STAGING = PROJ / "staging" / "commentaries_v2.db"
RAW = PROJ / "data" / "raw_v2"

MANUAL_ALIASES = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Songs",
    "ISA": "Isaiah", "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel",
    "DAN": "Daniel", "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos",
    "OBA": "Obadiah", "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum",
    "HAB": "Habakkuk", "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah",
    "MAL": "Malachi",
    "MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John",
    "ACT": "Acts", "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians",
    "GAL": "Galatians", "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy",
    "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John",
    "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}


def resolve_book(name):
    if name is None:
        return None
    if str(name).upper() in MANUAL_ALIASES:
        return MANUAL_ALIASES[str(name).upper()]
    return parser.resolve_book(str(name))


def clean_text(text):
    import html as H
    text = re.sub(r"<[^>]+>", "", text)
    text = H.unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_footers(text):
    """Remove TXT page-footers (underscore rules + spaced-caps book titles)
    that survive in the CCEL gap-fill chapters (2SA 23-24 known case)."""
    lines = text.split("\n")
    while lines:
        last = lines[-1].strip()
        if re.fullmatch(r"_+", last) or re.fullmatch(r"[A-Z]( [A-Z])+", last):
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
        else:
            break
    return "\n".join(lines).strip()


def check_zero_hit(text, source_id, ref):
    issues = []
    if re.search(r"<[^>]+>", text):
        issues.append("HTML tag")
    if re.search(r"&[a-zA-Z]+;|&#\d+;", text):
        issues.append("HTML entity")
    # Single-backslash markers only; double-backslash pairs are CCEL artifacts.
    # Lowercase = possible USFM (hard fail). Uppercase (e.g. "\Ro") is a
    # CCEL transcription artifact, never USFM: kept source-faithful, warn only.
    if re.search(r"(?<!\\)\\(?!\\\\)[a-z]+\b", text):
        issues.append("USFM marker")
    if re.search(r"(?<!\\)\\(?!\\\\)[A-Z][a-zA-Z]*\b", text):
        print(f"  NOTE {source_id} {ref}: backslash+uppercase transcription"
              " artifact (kept source-faithful)")
    if issues:
        print(f"  WARNING {source_id} {ref}: {', '.join(issues)}")
    return len(issues) == 0


def with_title(title, body):
    title = (title or "").strip()
    return f"{title}\n\n{body}" if title else body


def max_verse(bounds, book, ch):
    mv = bounds[book]["max_verse"]
    return mv.get(ch) or mv.get(str(ch))


def parse_cross_chapter_end(ref):
    """'Job 12:1-14:22' -> (14, 22). None if not a cross-chapter ref."""
    m = re.search(r"[-–](\d+):(\d+)\s*$", ref or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def main():
    if (PROJ / "data" / "study.db").exists():
        print("ERROR: data/study.db already exists; refusing to overwrite.")
        sys.exit(1)

    bounds = db.get_bounds("KJV")  # read-only; 'order' is 0-based
    print(f"KJV bounds: {len(bounds)} books")

    if STAGING.exists():
        STAGING.unlink()
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(STAGING))
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE commentaries (
             id INTEGER PRIMARY KEY,
             source_id TEXT NOT NULL,
             book TEXT NOT NULL,
             book_order INTEGER NOT NULL,
             start_chapter INTEGER NOT NULL,
             start_verse INTEGER NOT NULL,
             end_chapter INTEGER NOT NULL,
             end_verse INTEGER NOT NULL,
             text TEXT NOT NULL
           )"""
    )
    cur.execute(
        "CREATE INDEX idx_commentaries_lookup ON "
        "commentaries(source_id, book_order, start_chapter, start_verse)"
    )

    errors = []
    skipped = []

    def insert(source_id, book, sch, sv, ech, ev, title, body, tag):
        order = bounds[book]["order"] + 1  # 1..66
        text = with_title(title, clean_text(body))
        if not text:
            return False
        if not check_zero_hit(text, source_id, tag):
            errors.append(f"{source_id} {tag}: markup leakage")
            return False
        cur.execute(
            "INSERT INTO commentaries (source_id, book, book_order, start_chapter,"
            " start_verse, end_chapter, end_verse, text) VALUES (?,?,?,?,?,?,?,?)",
            (source_id, book, order, sch, sv, ech, ev, text),
        )
        return True

    def valid_chapter(book, ch, tag):
        if ch < 1 or ch > bounds[book]["chapters"]:
            skipped.append(f"{tag}: chapter {ch} out of bounds")
            return False
        return True

    def valid_verse(book, ch, v, tag):
        mv = max_verse(bounds, book, ch)
        if v < 1 or (mv and v > mv):
            skipped.append(f"{tag}: verse {v} out of bounds (ch {ch} max {mv})")
            return False
        return True

    # ---------------- Matthew Henry ----------------
    print("\n=== Matthew Henry ===")
    mh_count = 0
    mh_dir = RAW / "matthew_henry"
    book_files = sorted(
        f for f in mh_dir.glob("*.json") if f.name not in ("MANIFEST.json", "CCEL_GAPS.json")
    )
    for f in book_files:
        d = json.load(open(f))
        book = resolve_book(f.stem)
        if not book:
            errors.append(f"matthew_henry: unresolvable book file {f.name}")
            continue
        if book not in bounds:
            errors.append(f"matthew_henry: book {book} not in KJV bounds")
            continue
        chapters = d.get("chapters", {})
        ch_iter = (
            [(int(k), v) for k, v in chapters.items() if str(k).isdigit()]
            if isinstance(chapters, dict)
            else []
        )
        for ch_num, ch in ch_iter:
            if not valid_chapter(book, ch_num, f"matthew_henry {book}"):
                continue
            ch_data = ch.get("chapter", {}) if isinstance(ch, dict) else {}
            intro = ch_data.get("introduction") or ch.get("intro") or ""
            if intro and insert("matthew_henry", book, ch_num, 0, ch_num, 0,
                                None, intro, f"{book} {ch_num} intro"):
                mh_count += 1
            content = ch_data.get("content", [])
            if isinstance(content, list):
                items = [it for it in content
                         if isinstance(it, dict) and it.get("type") == "verse"]
                items.sort(key=lambda x: x.get("number", 0))
                mv = max_verse(bounds, book, ch_num)
                for idx, item in enumerate(items):
                    v_start = item.get("number")
                    if not v_start:
                        continue
                    v_end = (items[idx + 1].get("number", 0) - 1
                             if idx + 1 < len(items) else mv)
                    if not valid_verse(book, ch_num, v_start,
                                       f"matthew_henry {book} {ch_num}"):
                        continue
                    if v_end and mv and v_end > mv:
                        v_end = mv
                    paras = item.get("content", [])
                    body = ("\n\n".join(paras) if isinstance(paras, list)
                            else str(paras))
                    if insert("matthew_henry", book, ch_num, v_start, ch_num,
                              v_end or v_start, None, body,
                              f"{book} {ch_num}:{v_start}-{v_end}"):
                        mh_count += 1
    # CCEL gap-fill chapters
    gaps = json.load(open(mh_dir / "CCEL_GAPS.json"))
    for key, ch in gaps.items():
        if key.startswith("_"):
            continue
        book = resolve_book(ch.get("book"))
        ch_num = ch.get("chapter")
        if not book or not ch_num:
            errors.append(f"matthew_henry CCEL gap {key}: bad book/chapter")
            continue
        if book not in bounds or not valid_chapter(book, ch_num, f"matthew_henry CCEL {key}"):
            continue
        intro = ch.get("intro") or ""
        if intro and insert("matthew_henry", book, ch_num, 0, ch_num, 0,
                            None, intro, f"{book} {ch_num} intro (CCEL)"):
            mh_count += 1
        for sec in ch.get("sections", []):
            vs, ve = sec.get("verse_start"), sec.get("verse_end")
            body = strip_footers(sec.get("text") or "")
            if not body:
                continue
            if vs and not valid_verse(book, ch_num, vs, f"matthew_henry CCEL {key}"):
                continue
            if ve and not valid_verse(book, ch_num, ve, f"matthew_henry CCEL {key}"):
                continue
            if insert("matthew_henry", book, ch_num, vs or 0, ch_num, ve or 0,
                       sec.get("title"), body, f"{book} {ch_num}:{vs}-{ve} (CCEL)"):
                mh_count += 1
    print(f"  Matthew Henry: {mh_count} rows")

    # ---------------- JFB ----------------
    print("\n=== JFB ===")
    jfb_count = 0
    jfb_data = json.load(open(RAW / "jfb" / "CCEL_JFB.json"))
    for key, ch in jfb_data.items():
        if key.startswith("_"):
            continue
        book = ch.get("book")
        ch_num = ch.get("chapter")
        if not book or not ch_num or book not in bounds:
            errors.append(f"jfb: bad book/chapter in {key}")
            continue
        if not valid_chapter(book, ch_num, f"jfb {key}"):
            continue
        intro = ch.get("intro") or ""
        if intro and insert("jfb", book, ch_num, 0, ch_num, 0,
                           None, intro, f"{book} {ch_num} intro"):
            jfb_count += 1
        seen = {}
        for sec in ch.get("sections", []):
            vs, ve = sec.get("verse_start"), sec.get("verse_end")
            title, body = sec.get("title") or "", sec.get("text") or ""
            if not body:
                continue
            ech, ev = ch_num, ve
            cc = parse_cross_chapter_end(sec.get("ref"))
            if cc:
                ech, ev = cc
                if not valid_chapter(book, ech, f"jfb {key} cross-chapter"):
                    continue
            if vs and not valid_verse(book, ch_num, vs, f"jfb {key}"):
                continue
            if ev and not valid_verse(book, ech, ev, f"jfb {key}"):
                continue
            dkey = (ch_num, vs, ech, ev)
            if dkey in seen:
                seen[dkey]["body"] += "\n\n" + body
                if title and title not in seen[dkey]["title"]:
                    seen[dkey]["title"] += "; " + title
            else:
                seen[dkey] = {"vs": vs, "ve": ve, "ech": ech, "ev": ev,
                              "title": title, "body": body}
        for item in seen.values():
            if insert("jfb", book, ch_num, item["vs"] or 0, item["ech"],
                       item["ev"] or 0, item["title"], item["body"],
                       f"{book} {ch_num}:{item['vs']}-{item['ev']}"):
                jfb_count += 1
    print(f"  JFB: {jfb_count} rows")

    # ---------------- Barnes NT ----------------
    print("\n=== Barnes NT ===")
    barnes_count = 0
    barnes_data = json.load(open(RAW / "barnes" / "CCEL_BARNES_NT.json"))
    for key, ch in barnes_data.items():
        if key.startswith("_"):
            continue
        book = ch.get("book")
        ch_num = ch.get("chapter")
        if not book or not ch_num or book not in bounds:
            errors.append(f"barnes_nt: bad book/chapter in {key}")
            continue
        if not valid_chapter(book, ch_num, f"barnes_nt {key}"):
            continue
        intro = ch.get("intro") or ""
        if intro and insert("barnes_nt", book, ch_num, 0, ch_num, 0,
                            None, intro, f"{book} {ch_num} intro"):
            barnes_count += 1
        for v in ch.get("verses", []):
            v_num = v.get("verse")
            body = v.get("text") or ""
            if not body or not v_num:
                continue
            if not valid_verse(book, ch_num, v_num, f"barnes_nt {key}"):
                continue
            if insert("barnes_nt", book, ch_num, v_num, ch_num, v_num,
                       None, body, f"{book} {ch_num}:{v_num}"):
                barnes_count += 1
    print(f"  Barnes NT: {barnes_count} rows")

    conn.commit()

    # ---------------- Final checks ----------------
    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    print(f"\nPRAGMA integrity_check: {ic}")
    assert ic == "ok", "integrity_check failed"

    cur.execute("SELECT source_id, COUNT(*) FROM commentaries GROUP BY source_id")
    for sid, n in cur.fetchall():
        print(f"  {sid}: {n} rows")
        assert n > 0, f"source {sid} produced zero rows"
    cur.execute("SELECT COUNT(*) FROM commentaries")
    total = cur.fetchone()[0]
    print(f"Total rows: {total}")

    cur.execute("SELECT COUNT(*) FROM commentaries WHERE text IS NULL OR TRIM(text)=''")
    assert cur.fetchone()[0] == 0, "empty text rows present"
    cur.execute("SELECT COUNT(*) FROM commentaries WHERE book_order < 1 OR book_order > 66")
    assert cur.fetchone()[0] == 0, "book_order out of range"
    cur.execute(
        "SELECT COUNT(*) FROM commentaries WHERE start_chapter > end_chapter "
        "OR (start_chapter = end_chapter AND start_verse > end_verse AND end_verse != 0)"
    )
    assert cur.fetchone()[0] == 0, "inverted ranges present"

    if skipped:
        print(f"\nSkipped (out-of-bounds, logged): {len(skipped)}")
        for s in skipped[:20]:
            print("  SKIP", s)
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors[:30]:
            print("  ERROR", e)
        sys.exit(1)
    print(f"\nOK: {STAGING}")
    print("NOTE: data/study.db was NOT created. data/scripture.db was NOT written to.")
    conn.close()


if __name__ == "__main__":
    main()