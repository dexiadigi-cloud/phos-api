#!/usr/bin/env python3
"""Ingest OpenScriptures HebrewLexicon (BDB transcription, CC BY 4.0) into a
staging DB. DATA ONLY. Re-runnable: rebuilds data/staging/bdb_staging.db from
data/raw_v2/bdb/HebrewStrong.xml.

Attribution (REQUIRED in API docs/code):
  "Brown-Driver-Briggs Hebrew lexicon XML transcription by the Open
   Scriptures Hebrew Bible Project, licensed under CC BY 4.0
   (https://creativecommons.org/licenses/by/4.0/)."
"""
import hashlib
import os
import sqlite3
import xml.etree.ElementTree as ET

BASE = os.path.expanduser("~/workspace/scripture-desk")
RAW = os.path.join(BASE, "data/raw_v2/bdb/HebrewStrong.xml")
OUT = os.path.join(BASE, "data/staging/bdb_staging.db")
NS = {"n": "http://openscriptures.github.com/morphhb/namespace"}

ATTRIBUTION = ("Brown-Driver-Briggs Hebrew lexicon XML transcription by the Open "
               "Scriptures Hebrew Bible Project, licensed under CC BY 4.0 "
               "(https://creativecommons.org/licenses/by/4.0/).")


def flat(el):
    """Flatten element text including children, single-spaced."""
    return " ".join("".join(el.itertext()).split())


def main():
    with open(RAW, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()

    root = ET.fromstring(raw)
    entries = root.findall("n:entry", NS)
    rows = []
    for e in entries:
        sid = e.get("id")  # H1..H8674
        w = e.find("n:w", NS)
        lemma = w.text.strip() if w is not None and w.text else ""
        translit = (w.get("xlit") or "").strip() if w is not None else ""
        pron = (w.get("pron") or "").strip() if w is not None else ""
        pos = (w.get("pos") or "").strip() if w is not None else ""
        meaning_el = e.find("n:meaning", NS)
        meaning = flat(meaning_el) if meaning_el is not None else ""
        defs = [d.text.strip() for d in (meaning_el.findall("n:def", NS)
                if meaning_el is not None else []) if d.text and d.text.strip()]
        usage_el = e.find("n:usage", NS)
        usage = flat(usage_el) if usage_el is not None else ""
        source_el = e.find("n:source", NS)
        source = flat(source_el) if source_el is not None else ""
        definition = "; ".join(p for p in
                               (f"[{pos}]" if pos else "",
                                f"pron. {pron}" if pron else "",
                                source, meaning, usage) if p)
        gloss = defs[0] if defs else (usage.split(".")[0][:120] if usage else "")
        rows.append((sid, "hebrew", lemma, translit, definition, gloss, "bdb"))

    if os.path.exists(OUT):
        os.remove(OUT)
    con = sqlite3.connect(OUT)
    cur = con.cursor()
    cur.execute("""CREATE TABLE lexicon (
        strongs_number TEXT PRIMARY KEY,
        language TEXT NOT NULL,
        lemma TEXT,
        transliteration TEXT,
        definition TEXT,
        gloss TEXT,
        source_id TEXT NOT NULL)""")
    cur.executemany(
        "INSERT INTO lexicon VALUES (?,?,?,?,?,?,?)", rows)
    cur.execute("""CREATE TABLE sources (
        source_id TEXT PRIMARY KEY,
        title TEXT,
        rights TEXT,
        rights_basis TEXT,
        attribution TEXT,
        commit_hash TEXT,
        retrieved TEXT,
        sha256 TEXT)""")
    cur.execute(
        "INSERT INTO sources VALUES (?,?,?,?,?,?,date('now'),?)",
        ("bdb",
         "OpenScriptures HebrewLexicon (HebrewStrong.xml, BDB transcription)",
         "CC BY 4.0",
         "CC BY 4.0; license: https://creativecommons.org/licenses/by/4.0/; "
         "underlying BDB (1906) and Strong's Hebrew dictionary text are public "
         "domain; the XML transcription is CC BY 4.0 per repo readme.md. "
         "Attribution must appear in API docs/code.",
         ATTRIBUTION,
         "21c9add13bc727d3a951361778e97e3ff7afd1ce (2019-09-02)",
         sha))
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM lexicon").fetchone()[0]
    dupes = cur.execute(
        "SELECT COUNT(*) FROM (SELECT strongs_number FROM lexicon "
        "GROUP BY strongs_number HAVING COUNT(*)>1)").fetchone()[0]
    empty = cur.execute(
        "SELECT COUNT(*) FROM lexicon WHERE definition='' OR definition IS NULL"
    ).fetchone()[0]
    con.close()
    print(f"rows={n} dupes={dupes} empty_definition={empty} sha256={sha}")
    assert n == 8674, f"expected 8674, got {n}"
    assert dupes == 0
    print("BDB STAGING OK")


if __name__ == "__main__":
    main()
