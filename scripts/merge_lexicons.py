"""Merge Strong's, BDB, and STEPBible lexicons into data/study.db.

Creates `lexicon_sources` + `lexicon` tables; leaves the existing `strongs`
table untouched. STEPBible definitions are sanitized from HTML to plain text
(staging DBs remain the raw archive).

Usage: python3 scripts/merge_lexicons.py
"""

from __future__ import annotations

import re
import sqlite3
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDY_DB = ROOT / "data" / "study.db"
BDB_DB = ROOT / "data" / "staging" / "bdb_staging.db"
STEP_DB = ROOT / "data" / "staging" / "stepbible_staging.db"


class _TextExtractor(HTMLParser):
    """Extract visible text; <br> variants become newlines."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag.lower() == "br":
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        if tag.lower() == "br":
            self.parts.append("\n")


def sanitize_stepbible(text: str | None) -> str | None:
    """HTML -> clean plain text.

    Rules (recorded in verification/v2/lexicon-merge-report.md):
    - <br>, <br/>, <BR>, <BR /> (any case) become a newline
    - <a href="javascript:void(0)" title="...">inner</a> keeps inner text only
      (hover citations do not survive as text); same for <ref>, <Level1-4>,
      <re>, <author>, <b>, <i> wrappers
    - all remaining tags stripped; HTML entities unescaped (&nbsp; -> space)
    - trailing whitespace removed per line; 3+ consecutive newlines collapsed
      to 2; leading/trailing whitespace stripped
    """
    if text is None:
        return None
    ext = _TextExtractor()
    ext.feed(text)
    ext.close()
    out = "".join(ext.parts).replace("\xa0", " ")
    lines = [ln.rstrip() for ln in out.split("\n")]
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def main() -> int:
    if not STUDY_DB.exists():
        print(f"missing {STUDY_DB}", file=sys.stderr)
        return 1
    for p in (BDB_DB, STEP_DB):
        if not p.exists():
            print(f"missing {p}", file=sys.stderr)
            return 1

    con = sqlite3.connect(STUDY_DB)
    con.execute("PRAGMA foreign_keys=OFF")
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='lexicon'")
    if cur.fetchone()[0]:
        print("lexicon table already exists; refusing to re-merge", file=sys.stderr)
        return 1

    cur.execute(
        """CREATE TABLE lexicon_sources (
            source_id TEXT PRIMARY KEY,
            title TEXT,
            rights TEXT,
            rights_basis TEXT,
            attribution TEXT,
            commit_hash TEXT,
            retrieved TEXT,
            sha256 TEXT)"""
    )
    cur.execute(
        """CREATE TABLE lexicon (
            id INTEGER PRIMARY KEY,
            strongs_number TEXT NOT NULL,
            language TEXT NOT NULL,
            lemma TEXT,
            transliteration TEXT,
            definition TEXT,
            gloss TEXT,
            source_id TEXT NOT NULL,
            extra TEXT)"""
    )
    cur.execute("CREATE INDEX idx_lexicon_src_num ON lexicon(source_id, strongs_number)")
    cur.execute("CREATE INDEX idx_lexicon_num ON lexicon(strongs_number)")

    # --- sources -----------------------------------------------------------
    cur.execute(
        """INSERT INTO lexicon_sources
           (source_id, title, rights, rights_basis, attribution,
            commit_hash, retrieved, sha256)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            "strongs",
            "Strong's Greek and Hebrew Dictionaries (1890)",
            "Public domain",
            "CC0 via Internet Archive item StrongsGreekAndHebrewDictionaries1890",
            "Strong's Greek and Hebrew Dictionaries (1890) by James Strong; "
            "public domain text via Internet Archive (CC0).",
            None,
            "2026-09-20",
            None,
        ),
    )
    bdb = sqlite3.connect(f"file:{BDB_DB}?mode=ro", uri=True)
    step = sqlite3.connect(f"file:{STEP_DB}?mode=ro", uri=True)
    for row in bdb.execute("SELECT source_id, title, rights, rights_basis, attribution, commit_hash, retrieved, sha256 FROM sources"):
        cur.execute("INSERT INTO lexicon_sources VALUES (?,?,?,?,?,?,?,?)", tuple(row))
    for row in step.execute("SELECT source_id, title, rights, rights_basis, attribution, commit_hash, retrieved, sha256 FROM sources"):
        cur.execute("INSERT INTO lexicon_sources VALUES (?,?,?,?,?,?,?,?)", tuple(row))

    # --- strongs (from study.db's own strongs table; entry_text -> definition)
    cur.execute(
        """INSERT INTO lexicon
           (strongs_number, language, lemma, transliteration, definition,
            gloss, source_id, extra)
           SELECT strongs_number, language, NULL, NULL, entry_text,
                  NULL, 'strongs', CAST(num AS TEXT)
           FROM strongs"""
    )
    n_strongs = cur.execute("SELECT COUNT(*) FROM lexicon WHERE source_id='strongs'").fetchone()[0]

    # --- bdb (as-is) --------------------------------------------------------
    bdb_rows = bdb.execute(
        "SELECT strongs_number, language, lemma, transliteration, definition, gloss, source_id FROM lexicon"
    ).fetchall()
    cur.executemany(
        "INSERT INTO lexicon (strongs_number, language, lemma, transliteration, definition, gloss, source_id, extra)"
        " VALUES (?,?,?,?,?,?,?,NULL)",
        bdb_rows,
    )

    # --- stepbible (sanitized) ----------------------------------------------
    step_rows = step.execute(
        "SELECT strongs_number, language, lemma, transliteration, definition, gloss, source_id, morph FROM lexicon"
    ).fetchall()
    cleaned = []
    html_before = 0
    for sn, lang, lemma, translit, definition, gloss, sid, morph in step_rows:
        if definition and ("<" in definition and ">" in definition):
            html_before += 1
        cleaned.append(
            (sn, lang, lemma, translit, sanitize_stepbible(definition), gloss, sid, morph)
        )
    cur.executemany(
        "INSERT INTO lexicon (strongs_number, language, lemma, transliteration, definition, gloss, source_id, extra)"
        " VALUES (?,?,?,?,?,?,?,?)",
        cleaned,
    )

    con.commit()

    # --- audits --------------------------------------------------------------
    print("== per-source counts ==")
    for sid, n in cur.execute("SELECT source_id, COUNT(*) FROM lexicon GROUP BY source_id ORDER BY source_id"):
        print(f"  {sid}: {n}")
    dupes = cur.execute(
        "SELECT COUNT(*) FROM (SELECT source_id, strongs_number, COUNT(*) c FROM lexicon GROUP BY 1,2 HAVING c>1)"
    ).fetchone()[0]
    print(f"duplicate (source_id, strongs_number): {dupes}")
    tag_pat = re.compile(r"</?(b|i|a|br|ref|level[1-4]|re|author)\b", re.IGNORECASE)
    tag_remain = sum(
        1
        for (d,) in cur.execute(
            r"""SELECT definition FROM lexicon
                WHERE source_id LIKE 'step\_%' ESCAPE '\' AND definition IS NOT NULL"""
        )
        if tag_pat.search(d)
    )
    print(f"stepbible rows still containing HTML tags after sanitize: {tag_remain}")
    print(f"integrity_check: {cur.execute('PRAGMA integrity_check').fetchone()[0]}")
    print(f"strongs table untouched: {cur.execute('SELECT COUNT(*) FROM strongs').fetchone()[0]} rows")
    con.close()
    bdb.close()
    step.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
