#!/usr/bin/env python3
"""Ingest STEPBible lexicon files (CC BY 4.0, Tyndale House Cambridge) into a
staging DB. DATA ONLY. Re-runnable: rebuilds data/staging/stepbible_staging.db
from data/raw_v2/stepbible/step/Lexicons/.

Attribution (REQUIRED in API docs/code):
  "STEPBible lexicon data (TBESH, TBESG, TFLSJ), Tyndale House, Cambridge,
   licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
   Source: https://github.com/STEPBible/STEPBible-Data, www.STEPBible.org."
"""
import hashlib
import os
import re
import sqlite3

BASE = os.path.expanduser("~/workspace/scripture-desk")
LEXDIR = os.path.join(BASE, "data/raw_v2/stepbible/step/Lexicons")
OUT = os.path.join(BASE, "data/staging/stepbible_staging.db")

ATTRIBUTION = ("STEPBible lexicon data (TBESH, TBESG, TFLSJ), Tyndale House, "
               "Cambridge, licensed under CC BY 4.0 "
               "(https://creativecommons.org/licenses/by/4.0/). Source: "
               "https://github.com/STEPBible/STEPBible-Data, www.STEPBible.org.")

FILES = {
    "step_tbesh": ("TBESH - Translators Brief lexicon of Extended Strongs for Hebrew - STEPBible.org CC BY.txt", "hebrew", "Meaning"),
    "step_tbesg": ("TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt", "greek", None),
    "step_tflsj": ("TFLSJ  0-5624 - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt", "greek", "LSJ Meaning"),
    "step_tflsjx": ("TFLSJ extra - Translators Formatted full LSJ Bible lexicon - STEPBible.org CC BY.txt", "greek", "LSJ Meaning"),
}
COMMIT = "b99716b0cddb648ddb95cc786a197180f2f97d48 (2026-09-18)"


def parse(path, meaning_col):
    with open(path, encoding="utf-8-sig") as f:
        lines = f.read().split("\n")
    hdr = next(i for i, l in enumerate(lines) if re.match(r"eStrong#?\tdStrong", l))
    cols = lines[hdr].split("\t")
    ek = "eStrong" if "eStrong" in cols else "eStrong#"
    mcol = meaning_col or next(c for c in cols if "Abbott-Smith" in c)
    rows = []
    for l in lines[hdr + 1:]:
        if not l.strip() or l.strip().startswith("="):
            continue
        parts = l.split("\t")
        if len(parts) < 8:
            continue
        d = dict(zip(cols, parts))
        estrong = d[ek].strip()
        if not re.match(r"^[GH]\d", estrong):
            continue
        rows.append((
            estrong,
            d.get("dStrong", "").strip(),
            d.get("uStrong", "").strip(),
            d.get("Hebrew", d.get("Greek", "")).strip(),
            d.get("Transliteration", "").strip(),
            d.get(mcol, "").strip(),
            d.get("Gloss", "").strip(),
            d.get("Morph", "").strip(),
        ))
    return rows


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    con = sqlite3.connect(OUT)
    cur = con.cursor()
    cur.execute("""CREATE TABLE lexicon (
        id INTEGER PRIMARY KEY,
        strongs_number TEXT NOT NULL,
        language TEXT NOT NULL,
        lemma TEXT,
        transliteration TEXT,
        definition TEXT,
        gloss TEXT,
        source_id TEXT NOT NULL,
        dstrong TEXT,
        ustrong TEXT,
        morph TEXT)""")
    cur.execute("CREATE INDEX idx_lex_strongs ON lexicon(strongs_number)")
    cur.execute("CREATE INDEX idx_lex_source ON lexicon(source_id)")
    cur.execute("""CREATE TABLE sources (
        source_id TEXT PRIMARY KEY,
        title TEXT,
        rights TEXT,
        rights_basis TEXT,
        attribution TEXT,
        commit_hash TEXT,
        retrieved TEXT,
        sha256 TEXT)""")

    total = 0
    for source_id, (fname, lang, mcol) in FILES.items():
        path = os.path.join(LEXDIR, fname)
        with open(path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        rows = parse(path, mcol)
        cur.executemany(
            "INSERT INTO lexicon (strongs_number, language, lemma, "
            "transliteration, definition, gloss, source_id, dstrong, ustrong, morph)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(r[0], lang, r[3], r[4], r[5], r[6], source_id, r[1], r[2], r[7])
             for r in rows])
        cur.execute(
            "INSERT INTO sources VALUES (?,?,?,?,?,?,date('now'),?)",
            (source_id, f"STEPBible {source_id} ({fname})", "CC BY 4.0",
             "CC BY 4.0; license: https://creativecommons.org/licenses/by/4.0/; "
             "data created by www.STEPBible.org based on work at Tyndale House, "
             "Cambridge. TBESH based on abridged BDB; TBESG based on "
             "Abbott-Smith (+Middle Liddell gaps); TFLSJ edited from full LSJ. "
             "Attribution must appear in API docs/code.",
             ATTRIBUTION, COMMIT, sha))
        print(f"{source_id}: rows={len(rows)} sha256={sha}")
        total += len(rows)

    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM lexicon").fetchone()[0]
    empty = cur.execute(
        "SELECT COUNT(*) FROM lexicon WHERE definition=''").fetchone()[0]
    by_src = cur.execute(
        "SELECT source_id, COUNT(*) FROM lexicon GROUP BY source_id"
    ).fetchall()
    con.close()
    print(f"total={n} empty_definition={empty} by_source={dict(by_src)}")
    assert n == total and n > 0
    print("STEPBIBLE STAGING OK")


if __name__ == "__main__":
    main()
