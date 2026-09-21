#!/usr/bin/env python3
"""Stage V2 commentaries into staging/commentaries.db (STAGING ONLY).

Sources:
- matthew_henry: HelloAO (1166 ch) + CCEL gaps (23 ch) = 1189 chapters
- jfb: CCEL 1871 (1189 chapters)
- barnes_nt: CCEL Barnes NT Notes (260 chapters, 27 books) - PARTIAL, OT missing

Schema:
  CREATE TABLE commentaries (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_start INTEGER,  -- NULL for chapter intro
    verse_end INTEGER,    -- NULL for chapter intro
    title TEXT,
    body TEXT NOT NULL
  );
  CREATE UNIQUE INDEX ux_commentaries ON commentaries(source_id, book, chapter, verse_start, verse_end);
  CREATE INDEX ix_commentaries_ref ON commentaries(book, chapter);

Does NOT create data/study.db. Does NOT write to data/scripture.db (read-only via api/db.py).
"""
import json, re, sqlite3, sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ / "api"))
import parser, db

STAGING = PROJ / "staging" / "commentaries.db"
RAW = PROJ / "data" / "raw_v2"

# Manual book aliases (in addition to parser.resolve_book)
# HelloAO uses 3-letter codes; parser.resolve_book doesn't handle all of them
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
    """Resolve book name to canonical via parser + manual aliases."""
    # Try manual first
    if name.upper() in MANUAL_ALIASES:
        return MANUAL_ALIASES[name.upper()]
    # Try parser
    result = parser.resolve_book(name)
    if result:
        return result
    return None

def clean_text(text):
    """Plain-text cleanup: remove HTML tags, unescape entities, normalize whitespace."""
    import html as H
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Unescape HTML entities
    text = H.unescape(text)
    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Collapse spaces within lines, preserve paragraph breaks
    lines = text.split('\n')
    cleaned = []
    for ln in lines:
        ln = re.sub(r'[ \t]+', ' ', ln).strip()
        cleaned.append(ln)
    text = '\n'.join(cleaned)
    # Collapse 3+ newlines to exactly 2 (paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def check_zero_hit(text, source_id, ref):
    """Verify no HTML tags, entities, or USFM markers remain."""
    issues = []
    if re.search(r'<[^>]+>', text):
        issues.append("HTML tag")
    if re.search(r'&[a-zA-Z]+;|&#\d+;', text):
        issues.append("HTML entity")
    if re.search(r'(?<!\\)\\(?!\\)[a-zA-Z]+\b', text):
        issues.append("USFM marker")
    if issues:
        print(f"  WARNING {source_id} {ref}: {', '.join(issues)}")
    return len(issues) == 0

def main():
    # Verify study.db does NOT exist (we must not create it)
    study_db = PROJ / "data" / "study.db"
    if study_db.exists():
        print(f"ERROR: {study_db} exists! Refusing to proceed.")
        sys.exit(1)

    # Get KJV bounds (read-only)
    bounds = db.get_bounds('KJV')
    print(f"KJV bounds: {len(bounds)} books")

    # Create staging DB (delete if exists for idempotency)
    STAGING.parent.mkdir(parents=True, exist_ok=True)
    if STAGING.exists():
        STAGING.unlink()
    conn = sqlite3.connect(str(STAGING))
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE commentaries (
          id INTEGER PRIMARY KEY,
          source_id TEXT NOT NULL,
          book TEXT NOT NULL,
          chapter INTEGER NOT NULL,
          verse_start INTEGER,
          verse_end INTEGER,
          title TEXT,
          body TEXT NOT NULL
        )
    """)
    cur.execute("CREATE UNIQUE INDEX ux_commentaries ON commentaries(source_id, book, chapter, verse_start, verse_end)")
    cur.execute("CREATE INDEX ix_commentaries_ref ON commentaries(book, chapter)")
    
    stats = {}
    unresolved = []

    # --- Matthew Henry ---
    print("\n=== Matthew Henry ===")
    mh_count = 0
    mh_dir = RAW / "matthew_henry"
    # HelloAO files
    for f in sorted(mh_dir.glob("*.json")):
        if f.name in ("MANIFEST.json", "CCEL_GAPS.json"):
            continue
        d = json.load(open(f))
        book_code = f.stem  # e.g. "GEN", "MAT"
        book = resolve_book(book_code)
        if not book:
            unresolved.append(("matthew_henry", book_code))
            continue
        if book not in bounds:
            unresolved.append(("matthew_henry", book))
            continue
        chapters = d.get("chapters", {})
        # chapters is a dict keyed by chapter number (string), or a list
        if isinstance(chapters, dict):
            ch_iter = [(int(k), v) for k, v in chapters.items() if k.isdigit()]
        else:
            ch_iter = []
            for ch in chapters:
                if isinstance(ch, dict):
                    ch_num = ch.get("chapter") or ch.get("number")
                    if ch_num:
                        ch_iter.append((int(ch_num), ch))
        for ch_num, ch in ch_iter:
            # Validate chapter bounds
            if ch_num < 1 or ch_num > bounds[book]["chapters"]:
                print(f"  SKIP matthew_henry {book} {ch_num}: out of bounds")
                continue
            ch_data = ch.get("chapter", {}) if isinstance(ch, dict) else {}
            # Chapter intro
            intro = ch_data.get("introduction") or ch.get("intro") or ""
            if intro:
                body = clean_text(intro)
                if body and check_zero_hit(body, "matthew_henry", f"{book} {ch_num} intro"):
                    cur.execute(
                        "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                        ("matthew_henry", book, ch_num, None, None, None, body))
                    mh_count += 1
            # Content: HelloAO format has ch['chapter']['content'] = list of verse items
            # OR ch['sections'] for CCEL-style
            content = ch_data.get("content", [])
            if content and isinstance(content, list):
                # HelloAO per-verse format (actually verse RANGES, number=start)
                verse_items = [it for it in content if isinstance(it, dict) and it.get("type") == "verse"]
                verse_items.sort(key=lambda x: x.get("number", 0))
                max_v = bounds[book]["max_verse"].get(ch_num) or bounds[book]["max_verse"].get(str(ch_num))
                for idx, item in enumerate(verse_items):
                    v_start = item.get("number")
                    # Infer end: next start - 1, or chapter max
                    if idx + 1 < len(verse_items):
                        v_end = verse_items[idx+1].get("number", 0) - 1
                    else:
                        v_end = max_v
                    paras = item.get("content", [])
                    if isinstance(paras, list):
                        body = clean_text("\n\n".join(paras))
                    else:
                        body = clean_text(str(paras))
                    if not body or not v_start:
                        continue
                    if max_v and (v_start < 1 or v_start > max_v):
                        continue
                    if v_end and max_v and v_end > max_v:
                        v_end = max_v
                    if check_zero_hit(body, "matthew_henry", f"{book} {ch_num}:{v_start}-{v_end}"):
                        cur.execute(
                            "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                            ("matthew_henry", book, ch_num, v_start, v_end, None, body))
                        mh_count += 1
            # Sections (CCEL-style, if present)
            for sec in ch.get("sections", []):
                vs = sec.get("verse_start")
                ve = sec.get("verse_end")
                title = sec.get("title") or ""
                body = clean_text(sec.get("text") or sec.get("body") or "")
                if not body:
                    continue
                # Validate verse bounds
                max_v = bounds[book]["max_verse"].get(ch_num) or bounds[book]["max_verse"].get(str(ch_num))
                if vs and max_v and (vs < 1 or vs > max_v):
                    print(f"  SKIP matthew_henry {book} {ch_num}:{vs}: verse out of bounds")
                    continue
                if ve and max_v and (ve < 1 or ve > max_v):
                    print(f"  SKIP matthew_henry {book} {ch_num}:{ve}: verse out of bounds")
                    continue
                if check_zero_hit(body, "matthew_henry", f"{book} {ch_num}:{vs}-{ve}"):
                    cur.execute(
                        "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                        ("matthew_henry", book, ch_num, vs, ve, title, body))
                    mh_count += 1
    # CCEL gaps
    gaps = json.load(open(mh_dir / "CCEL_GAPS.json"))
    for key, ch in gaps.items():
        if key.startswith("_"):
            continue
        book_raw = ch.get("book")
        book = resolve_book(book_raw)
        ch_num = ch.get("chapter")
        if not book or not ch_num:
            unresolved.append(("matthew_henry_ccel", book_raw))
            continue
        # book is now canonical
        if book not in bounds:
            unresolved.append(("matthew_henry_ccel", book))
            continue
        intro = ch.get("intro") or ""
        if intro:
            body = clean_text(intro)
            if body and check_zero_hit(body, "matthew_henry", f"{book} {ch_num} intro (CCEL)"):
                cur.execute(
                    "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                    ("matthew_henry", book, ch_num, None, None, None, body))
                mh_count += 1
        for sec in ch.get("sections", []):
            vs = sec.get("verse_start")
            ve = sec.get("verse_end")
            title = sec.get("title") or ""
            body = clean_text(sec.get("text") or "")
            if not body:
                continue
            if check_zero_hit(body, "matthew_henry", f"{book} {ch_num}:{vs}-{ve} (CCEL)"):
                cur.execute(
                    "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                    ("matthew_henry", book, ch_num, vs, ve, title, body))
                mh_count += 1
    stats["matthew_henry"] = mh_count
    print(f"  Matthew Henry: {mh_count} rows")

    # --- JFB ---
    print("\n=== JFB ===")
    jfb_count = 0
    jfb_data = json.load(open(RAW / "jfb" / "CCEL_JFB.json"))
    for key, ch in jfb_data.items():
        if key.startswith("_"):
            continue
        book = ch.get("book")
        ch_num = ch.get("chapter")
        if not book or not ch_num:
            continue
        if book not in bounds:
            unresolved.append(("jfb", book))
            continue
        if ch_num < 1 or ch_num > bounds[book]["chapters"]:
            print(f"  SKIP jfb {book} {ch_num}: out of bounds")
            continue
        intro = ch.get("intro") or ""
        if intro:
            body = clean_text(intro)
            if body and check_zero_hit(body, "jfb", f"{book} {ch_num} intro"):
                cur.execute(
                    "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                    ("jfb", book, ch_num, None, None, None, body))
                jfb_count += 1
        # Deduplicate sections by (vs, ve): join bodies with same range
        seen = {}
        for sec in ch.get("sections", []):
            vs = sec.get("verse_start")
            ve = sec.get("verse_end")
            title = sec.get("title") or ""
            body = clean_text(sec.get("text") or "")
            if not body:
                continue
            max_v = bounds[book]["max_verse"].get(ch_num) or bounds[book]["max_verse"].get(str(ch_num))
            if vs and max_v and (vs < 1 or vs > max_v):
                continue
            if ve and max_v and (ve < 1 or ve > max_v):
                continue
            key = (vs, ve)
            if key in seen:
                # Join duplicate ranges
                seen[key]["body"] += "\n\n" + body
                if title and title not in seen[key]["title"]:
                    seen[key]["title"] += "; " + title
            else:
                seen[key] = {"vs": vs, "ve": ve, "title": title, "body": body}
        for item in seen.values():
            if check_zero_hit(item["body"], "jfb", f"{book} {ch_num}:{item['vs']}-{item['ve']}"):
                cur.execute(
                    "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                    ("jfb", book, ch_num, item["vs"], item["ve"], item["title"], item["body"]))
                jfb_count += 1
    stats["jfb"] = jfb_count
    print(f"  JFB: {jfb_count} rows")

    # --- Barnes NT ---
    print("\n=== Barnes NT ===")
    barnes_count = 0
    barnes_data = json.load(open(RAW / "barnes" / "CCEL_BARNES_NT.json"))
    for key, ch in barnes_data.items():
        if key.startswith("_"):
            continue
        book = ch.get("book")
        ch_num = ch.get("chapter")
        if not book or not ch_num:
            continue
        if book not in bounds:
            unresolved.append(("barnes_nt", book))
            continue
        intro = ch.get("intro") or ""
        if intro:
            body = clean_text(intro)
            if body and check_zero_hit(body, "barnes_nt", f"{book} {ch_num} intro"):
                cur.execute(
                    "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                    ("barnes_nt", book, ch_num, None, None, None, body))
                barnes_count += 1
        for v in ch.get("verses", []):
            v_num = v.get("verse")
            body = clean_text(v.get("text") or "")
            if not body or not v_num:
                continue
            max_v = bounds[book]["max_verse"].get(ch_num) or bounds[book]["max_verse"].get(str(ch_num))
            if max_v and (v_num < 1 or v_num > max_v):
                continue
            if check_zero_hit(body, "barnes_nt", f"{book} {ch_num}:{v_num}"):
                cur.execute(
                    "INSERT INTO commentaries (source_id, book, chapter, verse_start, verse_end, title, body) VALUES (?,?,?,?,?,?,?)",
                    ("barnes_nt", book, ch_num, v_num, v_num, None, body))
                barnes_count += 1
    stats["barnes_nt"] = barnes_count
    print(f"  Barnes NT: {barnes_count} rows")

    conn.commit()
    
    # Integrity check
    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    print(f"\nPRAGMA integrity_check: {ic}")
    
    # Summary
    cur.execute("SELECT COUNT(*) FROM commentaries")
    total = cur.fetchone()[0]
    print(f"\nTotal rows: {total}")
    print(f"Stats: {stats}")
    if unresolved:
        print(f"\nUnresolved ({len(unresolved)}): {unresolved[:10]}")
    
    conn.close()
    print(f"\nStaging DB: {STAGING}")
    print("NOTE: data/study.db was NOT created. data/scripture.db was NOT written to.")

if __name__ == "__main__":
    main()
