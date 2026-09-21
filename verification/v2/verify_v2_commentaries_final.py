#!/usr/bin/env python3
"""Independent raw-to-DB spot checks for staging/commentaries_v2.db.

Does NOT import the build script. Reads raw JSONs directly, samples rows
with seed 20260920 (12 per source), and verifies:
  - the row's (book, chapter, verse range) locates a real raw record,
  - the raw body text (whitespace-normalized) is contained in the DB text,
  - a raw section title, when present, opens the DB text,
  - all refs are within KJV bounds (read-only).
Evidence: verification/v2/raw/commentaries/spot_checks.json
"""
import json
import random
import re
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJ / "api"))
import db

SEED = 20260920
N_PER_SOURCE = 12
RAW = PROJ / "data" / "raw_v2"
STAGING_DB = PROJ / "staging" / "commentaries_v2.db"
EVIDENCE = PROJ / "verification" / "v2" / "raw" / "commentaries" / "spot_checks.json"

CODE_BY_BOOK = {v: k for k, v in {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra",
    "NEH": "Nehemiah", "EST": "Esther", "JOB": "Job", "PSA": "Psalms",
    "PRO": "Proverbs", "ECC": "Ecclesiastes", "SNG": "Song of Songs",
    "ISA": "Isaiah", "JER": "Jeremiah", "LAM": "Lamentations",
    "EZK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea", "JOL": "Joel",
    "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah", "MIC": "Micah",
    "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah", "HAG": "Haggai",
    "ZEC": "Zechariah", "MAL": "Malachi", "MAT": "Matthew", "MRK": "Mark",
    "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Romans",
    "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians",
    "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians",
    "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy",
    "2TI": "2 Timothy", "TIT": "Titus", "PHM": "Philemon", "HEB": "Hebrews",
    "JAS": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JN": "1 John",
    "2JN": "2 John", "3JN": "3 John", "JUD": "Jude", "REV": "Revelation",
}.items()}


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def main():
    bounds = db.get_bounds("KJV")
    conn = sqlite3.connect(f"file:{STAGING_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    jfb = json.load(open(RAW / "jfb" / "CCEL_JFB.json"))
    barnes = json.load(open(RAW / "barnes" / "CCEL_BARNES_NT.json"))
    gaps = json.load(open(RAW / "matthew_henry" / "CCEL_GAPS.json"))
    mh_cache = {}

    def mh_book(book):
        if book not in mh_cache:
            mh_cache[book] = json.load(
                open(RAW / "matthew_henry" / f"{CODE_BY_BOOK[book]}.json"))
        return mh_cache[book]

    rng = random.Random(SEED)
    results = []
    failures = []

    for source_id in ("matthew_henry", "jfb", "barnes_nt"):
        rows = cur.execute(
            "SELECT * FROM commentaries WHERE source_id=? ORDER BY id",
            (source_id,)).fetchall()
        sample = rng.sample(rows, min(N_PER_SOURCE, len(rows)))
        for r in sample:
            book = r["book"]
            sch, sv, ech, ev = (r["start_chapter"], r["start_verse"],
                                r["end_chapter"], r["end_verse"])
            dbtext = norm(r["text"])
            ok, detail = True, ""
            # bounds check
            b = bounds.get(book)
            if not b:
                ok, detail = False, "book not in KJV bounds"
            elif not (1 <= sch <= b["chapters"] and 1 <= ech <= b["chapters"]):
                ok, detail = False, "chapter out of bounds"
            else:
                for ch, v in ((sch, sv), (ech, ev)):
                    if v:
                        mv = b["max_verse"].get(ch)
                        if not (1 <= v <= (mv or 0)):
                            ok, detail = False, f"verse {v} out of bounds ch {ch}"
            raw_body, raw_title, raw_loc = None, None, None
            if ok:
                try:
                    if source_id == "jfb":
                        ch = jfb[f"{book}_{sch}"]
                        if sv == 0 and ev == 0:
                            raw_body, raw_loc = ch.get("intro"), "intro"
                        else:
                            cands = [s for s in ch.get("sections", [])
                                     if s.get("verse_start") == sv
                                     and s.get("verse_end") == ev]
                            if not cands:
                                raise ValueError("no raw section matches range")
                            raw_body = "\n\n".join(s.get("text", "") for s in cands)
                            raw_title = cands[0].get("title")
                            raw_loc = f"sections {sv}-{ev}"
                    elif source_id == "barnes_nt":
                        ch = barnes[f"{book}_{sch}"]
                        if sv == 0:
                            raw_body, raw_loc = ch.get("intro"), "intro"
                        else:
                            v = [x for x in ch.get("verses", [])
                                 if x.get("verse") == sv]
                            if not v:
                                raise ValueError("no raw verse matches")
                            raw_body, raw_loc = v[0].get("text"), f"verse {sv}"
                    else:  # matthew_henry
                        code = CODE_BY_BOOK[book]
                        gap = None
                        for gk, gv in gaps.items():
                            if gk.startswith("_"):
                                continue
                            if gv.get("book") in (code, book) and gv.get("chapter") == sch:
                                gap = gv
                                break
                        if gap is not None:
                            if sv == 0:
                                raw_body, raw_loc = gap.get("intro"), "CCEL gap intro"
                            else:
                                secs = [s for s in gap.get("sections", [])
                                        if s.get("verse_start") == sv]
                                if not secs:
                                    raise ValueError("no raw gap section matches")
                                raw_body = secs[0].get("text")
                                raw_title = secs[0].get("title")
                                raw_loc = f"CCEL gap section {sv}"
                        else:
                            d = mh_book(book)
                            ch = d["chapters"][str(sch)]["chapter"]
                            if sv == 0:
                                raw_body, raw_loc = ch.get("introduction"), "intro"
                            else:
                                items = [it for it in ch.get("content", [])
                                         if isinstance(it, dict)
                                         and it.get("type") == "verse"
                                         and it.get("number") == sv]
                                if not items:
                                    raise ValueError("no raw HelloAO item matches")
                                c = items[0].get("content", [])
                                raw_body = "\n\n".join(c) if isinstance(c, list) else str(c)
                                raw_loc = f"HelloAO item {sv}"
                except (KeyError, ValueError) as e:
                    ok, detail = False, f"raw lookup failed: {e}"
            if ok:
                nb = norm(raw_body)
                if not nb or nb not in dbtext:
                    ok, detail = False, "raw body not contained in DB text"
                elif raw_title and not dbtext.startswith(norm(raw_title)[:60]):
                    ok, detail = False, "raw title not at start of DB text"
            rec = {"source": source_id, "id": r["id"], "book": book,
                   "range": f"{sch}:{sv}-{ech}:{ev}", "raw_loc": raw_loc,
                   "pass": ok, "detail": detail,
                   "db_chars": len(r["text"])}
            results.append(rec)
            if not ok:
                failures.append(rec)
            print(("PASS" if ok else "FAIL"), source_id, r["id"],
                  f"{book} {sch}:{sv}-{ech}:{ev}", detail)

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"seed": SEED, "per_source": N_PER_SOURCE,
               "passed": sum(1 for r in results if r["pass"]),
               "failed": len(failures), "checks": results},
              open(EVIDENCE, "w"), ensure_ascii=False, indent=1)
    print(f"\n{sum(1 for r in results if r['pass'])}/{len(results)} passed;"
          f" evidence: {EVIDENCE}")
    conn.close()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
