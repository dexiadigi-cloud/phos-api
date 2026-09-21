#!/usr/bin/env python3
"""Seeded independent raw-to-DB spot checks for V2 commentaries.
RNG seed: 20260920. At least 10 checks per accepted source.
Saves pairs under verification/v2/raw/commentaries/.
"""
import json, random, sqlite3, sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ / "api"))

SEED = 20260920
random.seed(SEED)

STAGING = PROJ / "staging" / "commentaries.db"
OUTDIR = PROJ / "verification" / "v2" / "raw" / "commentaries"
OUTDIR.mkdir(parents=True, exist_ok=True)

def get_db_rows(source_id, n=10):
    """Get n random rows from DB for source."""
    conn = sqlite3.connect(str(STAGING))
    cur = conn.cursor()
    cur.execute("SELECT book, chapter, verse_start, verse_end, title, body FROM commentaries WHERE source_id=?", (source_id,))
    rows = cur.fetchall()
    conn.close()
    return random.sample(rows, min(n, len(rows)))

def find_in_raw_mh(book, chapter, vs, ve):
    """Independently extract from MH raw files."""
    # Try HelloAO files first
    import sys
    sys.path.insert(0, str(PROJ / "scripts"))
    # Map canonical to code (reverse of MANUAL_ALIASES)
    code_map = {
        "Genesis": "GEN", "Exodus": "EXO", "Leviticus": "LEV", "Numbers": "NUM",
        "Deuteronomy": "DEU", "Joshua": "JOS", "Judges": "JDG", "Ruth": "RUT",
        "1 Samuel": "1SA", "2 Samuel": "2SA", "1 Kings": "1KI", "2 Kings": "2KI",
        "1 Chronicles": "1CH", "2 Chronicles": "2CH", "Ezra": "EZR", "Nehemiah": "NEH",
        "Esther": "EST", "Job": "JOB", "Psalms": "PSA", "Proverbs": "PRO",
        "Ecclesiastes": "ECC", "Song of Songs": "SNG",
        "Isaiah": "ISA", "Jeremiah": "JER", "Lamentations": "LAM", "Ezekiel": "EZK",
        "Daniel": "DAN", "Hosea": "HOS", "Joel": "JOL", "Amos": "AMO",
        "Obadiah": "OBA", "Jonah": "JON", "Micah": "MIC", "Nahum": "NAM",
        "Habakkuk": "HAB", "Zephaniah": "ZEP", "Haggai": "HAG", "Zechariah": "ZEC",
        "Malachi": "MAL",
        "Matthew": "MAT", "Mark": "MRK", "Luke": "LUK", "John": "JHN",
        "Acts": "ACT", "Romans": "ROM", "1 Corinthians": "1CO", "2 Corinthians": "2CO",
        "Galatians": "GAL", "Ephesians": "EPH", "Philippians": "PHP", "Colossians": "COL",
        "1 Thessalonians": "1TH", "2 Thessalonians": "2TH", "1 Timothy": "1TI",
        "2 Timothy": "2TI", "Titus": "TIT", "Philemon": "PHM", "Hebrews": "HEB",
        "James": "JAS", "1 Peter": "1PE", "2 Peter": "2PE", "1 John": "1JN",
        "2 John": "2JN", "3 John": "3JN", "Jude": "JUD", "Revelation": "REV",
    }
    code = code_map.get(book)
    if not code:
        return None
    # Check CCEL gaps first for the 23 gap chapters
    gap_chapters = {
        ("Song of Songs", 1), ("Song of Songs", 2), ("Song of Songs", 3), ("Song of Songs", 4),
        ("Song of Songs", 5), ("Song of Songs", 6), ("Song of Songs", 7), ("Song of Songs", 8),
        ("Jonah", 2), ("Jonah", 3), ("Jonah", 4),
        ("Matthew", 19), ("Matthew", 20), ("Matthew", 21), ("Matthew", 22),
        ("Matthew", 23), ("Matthew", 24), ("Matthew", 25), ("Matthew", 26),
        ("Matthew", 27), ("Matthew", 28),
        ("2 Samuel", 23), ("2 Samuel", 24),
    }
    if (book, chapter) in gap_chapters:
        g = json.load(open(PROJ / "data" / "raw_v2" / "matthew_henry" / "CCEL_GAPS.json"))
        key = f"{code}_{chapter}"
        # CCEL_GAPS uses keys like "SNG_1", "JON_2", etc.
        for k, v in g.items():
            if k.startswith("_"):
                continue
            if v.get("book") == code and v.get("chapter") == chapter:
                if vs is None:
                    return v.get("intro", "")
                for sec in v.get("sections", []):
                    if sec.get("verse_start") == vs and sec.get("verse_end") == ve:
                        return sec.get("text", "")
                return None
        return None
    # HelloAO file
    fpath = PROJ / "data" / "raw_v2" / "matthew_henry" / f"{code}.json"
    if not fpath.exists():
        return None
    d = json.load(open(fpath))
    ch = d.get("chapters", {}).get(str(chapter))
    if not ch:
        return None
    ch_data = ch.get("chapter", {})
    if vs is None:
        return ch_data.get("introduction", "")
    # Find verse range
    content = ch_data.get("content", [])
    verse_items = [it for it in content if it.get("type") == "verse"]
    verse_items.sort(key=lambda x: x.get("number", 0))
    for idx, item in enumerate(verse_items):
        v_start = item.get("number")
        if v_start == vs:
            paras = item.get("content", [])
            if isinstance(paras, list):
                return "\n\n".join(paras)
            return str(paras)
    return None

def find_in_raw_jfb(book, chapter, vs, ve):
    """Independently extract from JFB raw."""
    d = json.load(open(PROJ / "data" / "raw_v2" / "jfb" / "CCEL_JFB.json"))
    key = f"{book}_{chapter}"
    ch = d.get(key)
    if not ch:
        return None
    if vs is None:
        return ch.get("intro", "")
    for sec in ch.get("sections", []):
        if sec.get("verse_start") == vs and sec.get("verse_end") == ve:
            return sec.get("text", "")
    return None

def find_in_raw_barnes(book, chapter, vs, ve):
    """Independently extract from Barnes NT raw."""
    d = json.load(open(PROJ / "data" / "raw_v2" / "barnes" / "CCEL_BARNES_NT.json"))
    key = f"{book}_{chapter}"
    ch = d.get(key)
    if not ch:
        return None
    if vs is None:
        return ch.get("intro", "")
    for v in ch.get("verses", []):
        if v.get("verse") == vs:
            return v.get("text", "")
    return None

def clean_for_compare(text):
    """Apply same cleanup as ingest."""
    import re, html as H
    text = re.sub(r'<[^>]+>', '', text)
    text = H.unescape(text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    cleaned = []
    for ln in lines:
        ln = re.sub(r'[ \t]+', ' ', ln).strip()
        cleaned.append(ln)
    text = '\n'.join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def main():
    results = []
    for source_id, finder in [
        ("matthew_henry", find_in_raw_mh),
        ("jfb", find_in_raw_jfb),
        ("barnes_nt", find_in_raw_barnes),
    ]:
        print(f"\n=== {source_id} ===")
        rows = get_db_rows(source_id, 10)
        passed = 0
        for i, (book, chapter, vs, ve, title, db_body) in enumerate(rows):
            raw_text = finder(book, chapter, vs, ve)
            if raw_text is None:
                status = "FAIL (not found in raw)"
            else:
                raw_clean = clean_for_compare(raw_text)
                # DB body was already cleaned; compare
                if raw_clean == db_body:
                    status = "PASS"
                    passed += 1
                else:
                    status = "FAIL (mismatch)"
            ref = f"{book} {chapter}" + (f":{vs}-{ve}" if vs else " (intro)")
            print(f"  {i+1}. {ref}: {status}")
            results.append({
                "source_id": source_id, "ref": ref,
                "book": book, "chapter": chapter,
                "verse_start": vs, "verse_end": ve,
                "status": status,
                "db_body_len": len(db_body),
                "raw_found": raw_text is not None,
            })
            # Save pair
            pair = {
                "source_id": source_id, "ref": ref,
                "db_body": db_body,
                "raw_text": raw_text,
                "raw_cleaned": clean_for_compare(raw_text) if raw_text else None,
                "match": status == "PASS",
            }
            fname = f"{source_id}_{book.replace(' ', '_')}_{chapter}_{vs or 'intro'}.json"
            (OUTDIR / fname).write_text(json.dumps(pair, ensure_ascii=False, indent=2))
        print(f"  Passed: {passed}/{len(rows)}")
    
    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    print(f"\n=== SUMMARY ===")
    print(f"Total: {passed}/{total} passed ({100*passed//total}%)")
    
    # Save summary
    summary = {
        "seed": SEED,
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0,
        "results": results,
    }
    (OUTDIR / "_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nPairs saved to {OUTDIR}")

if __name__ == "__main__":
    main()
