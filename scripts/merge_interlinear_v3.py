#!/usr/bin/env python3
"""Merge parsed STEPBible interlinear (staging) into data/study.db.

Reads data/staging/interlinear_staging.db, renumbers word positions so each
KJV verse has one clean 1..N sequence for the selected reading, and writes
the final interlinear_words table plus STEPBible source records.

Reading rule (documented):
  - Greek (TAGNT): Nestle-Aland/SBL-compatible reading = every word whose
    type contains N or n (NKO, N(k)O, NO, no, n, ...). K-only / O-only rows
    are variants (Byzantine/Majority readings such as the longer ending of
    Mark). Verified against NA28 (e.g. Mat 1:18#06, 1Co 3:5#07).
  - Hebrew (TAHOT): Leningrad main text (L...) incl. Qere where the file
    marks the translators' normal Q/K choice (Q...). X/R rows are variants.
  - Verses split by source versification (e.g. 1Ki.18.33 + 1Ki.18.33(18.34),
    or NRSV 2:10 + 2:11[2.10] -> KJV 2:10) are concatenated in source order
    and renumbered 1..N. Psalm titles (verse 0) sort before verse-1 words.
"""

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "data" / "staging" / "interlinear_staging.db"
STUDY = ROOT / "data" / "study.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS interlinear_words (
    id INTEGER PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    position INTEGER NOT NULL,
    word TEXT NOT NULL,
    transliteration TEXT,
    gloss TEXT,
    gloss_alt TEXT,
    strongs TEXT,
    morphology TEXT,
    lemma TEXT,
    testament TEXT NOT NULL,
    is_variant INTEGER NOT NULL DEFAULT 0,
    variant_kind TEXT,
    src_ref TEXT,
    UNIQUE(book, chapter, verse, position, is_variant, variant_kind)
);
CREATE INDEX IF NOT EXISTS idx_interlinear_ref
    ON interlinear_words(book, chapter, verse, is_variant);
CREATE INDEX IF NOT EXISTS idx_interlinear_strongs
    ON interlinear_words(strongs);
"""

SOURCES = [
    ("step_tagnt", "interlinear",
     "STEPBible TAGNT (Translators Amalgamated Greek NT)",
     "CC BY 4.0",
     "CC BY 4.0; license: https://creativecommons.org/licenses/by/4.0/; "
     "data created by www.STEPBible.org based on work at Tyndale House "
     "Cambridge. Attribution: STEP Bible (https://www.STEPBible.org). "
     "Phos modifications: verse references remapped from NRSV versification "
     "to KJV versification via the file's bracket markers; word positions "
     "renumbered sequentially within each KJV verse; single Nestle-Aland/"
     "SBL-compatible reading selected (N/n-class word types), other "
     "readings kept as flagged variants; Spanish and sub-meaning columns "
     "excluded.",
     "2026-09-20",
     None),
    ("step_tahot", "interlinear",
     "STEPBible TAHOT (Translators Amalgamated Hebrew OT)",
     "CC BY 4.0",
     "CC BY 4.0; license: https://creativecommons.org/licenses/by/4.0/; "
     "data created by www.STEPBible.org based on work at Tyndale House "
     "Cambridge. Attribution: STEP Bible (https://www.STEPBible.org). "
     "Phos modifications: split source verses concatenated in source order "
     "within each KJV verse and positions renumbered 1..N; Psalm titles "
     "(verse 0) mapped to verse 1, ordered before verse-1 words; Leningrad "
     "main text with translators' Qere choices selected, X/R rows kept as "
     "flagged variants; Spanish and sub-meaning columns excluded.",
     "2026-09-20",
     None),
]


def main():
    assert STAGING.exists(), f"staging DB missing: {STAGING}"
    assert STUDY.exists(), f"study DB missing: {STUDY}"
    # refuse to merge twice
    chk = sqlite3.connect(STUDY)
    n0 = chk.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE name='interlinear_words'"
    ).fetchone()[0]
    if n0:
        n = chk.execute("SELECT COUNT(*) FROM interlinear_words").fetchone()[0]
        chk.close()
        sys.exit(f"interlinear_words already exists with {n} rows; refusing.")
    chk.close()

    src = sqlite3.connect(STAGING)
    dst = sqlite3.connect(STUDY)
    dst.executescript(SCHEMA)

    order = ("ORDER BY book, chapter, verse, src_ch, src_verse, "
             "heb_ch, heb_verse, position")

    # main reading: one 1..N sequence per KJV verse
    pos = 0
    cur_verse = None
    total_main = 0
    q = ("SELECT book, chapter, verse, src_ch, src_verse, heb_ch, heb_verse,"
         " position, word, transliteration, gloss, gloss_alt, strongs,"
         " morphology, lemma, source_id, src_ref FROM words"
         " WHERE is_main=1 " + order)
    batch = []
    for r in src.execute(q):
        (book, ch, vs, _sc, _sv, _hc, _hv, _p, word, translit, gloss,
         gloss_alt, strongs, morph, lemma, source_id, src_ref) = r
        key = (book, ch, vs)
        pos = pos + 1 if key == cur_verse else 1
        cur_verse = key
        testament = "NT" if source_id == "step_tagnt" else "OT"
        batch.append((book, ch, vs, pos, word, translit, gloss, gloss_alt,
                      strongs, morph, lemma, testament, 0, None, src_ref))
        total_main += 1
        if len(batch) >= 5000:
            dst.executemany(
                """INSERT INTO interlinear_words
                   (book, chapter, verse, position, word, transliteration,
                    gloss, gloss_alt, strongs, morphology, lemma, testament,
                    is_variant, variant_kind, src_ref)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", batch)
            dst.commit()
            batch = []
    if batch:
        dst.executemany(
            """INSERT INTO interlinear_words
               (book, chapter, verse, position, word, transliteration,
                gloss, gloss_alt, strongs, morphology, lemma, testament,
                is_variant, variant_kind, src_ref)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", batch)
    dst.commit()

    # variants: 1..N per (verse, word_type)
    pos = 0
    cur_key = None
    total_var = 0
    q = ("SELECT book, chapter, verse, src_ch, src_verse, heb_ch, heb_verse,"
         " position, word, transliteration, gloss, gloss_alt, strongs,"
         " morphology, lemma, source_id, word_type, src_ref FROM words"
         " WHERE is_main=0 "
         "ORDER BY book, chapter, verse, word_type, src_ch, src_verse,"
         " heb_ch, heb_verse, position")
    batch = []
    for r in src.execute(q):
        (book, ch, vs, _sc, _sv, _hc, _hv, _p, word, translit, gloss,
         gloss_alt, strongs, morph, lemma, source_id, wtype, src_ref) = r
        key = (book, ch, vs, wtype)
        pos = pos + 1 if key == cur_key else 1
        cur_key = key
        testament = "NT" if source_id == "step_tagnt" else "OT"
        batch.append((book, ch, vs, pos, word, translit, gloss, gloss_alt,
                      strongs, morph, lemma, testament, 1, wtype, src_ref))
        total_var += 1
        if len(batch) >= 5000:
            dst.executemany(
                """INSERT INTO interlinear_words
                   (book, chapter, verse, position, word, transliteration,
                    gloss, gloss_alt, strongs, morphology, lemma, testament,
                    is_variant, variant_kind, src_ref)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", batch)
            dst.commit()
            batch = []
    if batch:
        dst.executemany(
            """INSERT INTO interlinear_words
               (book, chapter, verse, position, word, transliteration,
                gloss, gloss_alt, strongs, morphology, lemma, testament,
                is_variant, variant_kind, src_ref)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", batch)
    dst.commit()

    for sid, kind, title, rights, basis, ver, sha in SOURCES:
        dst.execute(
            """INSERT OR REPLACE INTO sources
               (source_id, kind, title, rights, rights_basis, version, sha256)
               VALUES (?,?,?,?,?,?,?)""",
            (sid, kind, title, rights, basis, ver, sha))
    dst.commit()

    # verify by reopening
    dst.close()
    v = sqlite3.connect(STUDY)
    n_main = v.execute(
        "SELECT COUNT(*) FROM interlinear_words WHERE is_variant=0").fetchone()[0]
    n_var = v.execute(
        "SELECT COUNT(*) FROM interlinear_words WHERE is_variant=1").fetchone()[0]
    n_verses = v.execute(
        "SELECT COUNT(DISTINCT book || '|' || chapter || '|' || verse)"
        " FROM interlinear_words WHERE is_variant=0").fetchone()[0]
    n_dups = v.execute(
        """SELECT COUNT(*) FROM (
             SELECT book, chapter, verse, position, is_variant, variant_kind,
                    COUNT(*) c FROM interlinear_words
             GROUP BY book, chapter, verse, position, is_variant, variant_kind
             HAVING c > 1)""").fetchone()[0]
    integrity = v.execute("PRAGMA integrity_check").fetchone()[0]
    n_src = v.execute(
        "SELECT COUNT(*) FROM sources WHERE source_id IN"
        " ('step_tagnt','step_tahot')").fetchone()[0]
    src_main = src.execute(
        "SELECT COUNT(*) FROM words WHERE is_main=1").fetchone()[0]
    src_var = src.execute(
        "SELECT COUNT(*) FROM words WHERE is_main=0").fetchone()[0]
    v.close()
    src.close()

    print(f"main rows inserted: {total_main}, in db: {n_main}, staging: {src_main}")
    print(f"variant rows inserted: {total_var}, in db: {n_var}, staging: {src_var}")
    print(f"KJV verses (main): {n_verses}")
    print(f"position collisions: {n_dups}")
    print(f"integrity: {integrity}")
    print(f"source records: {n_src}")
    assert n_main == total_main == src_main, "main count mismatch"
    assert n_var == total_var == src_var, "variant count mismatch"
    assert n_dups == 0, "collisions remain"
    assert integrity == "ok"
    assert n_src == 2
    print("MERGE OK")


if __name__ == "__main__":
    main()
