"""Merge commentary + dictionary staging DBs into data/study.db.

Idempotent guard: refuses to run if any target source_id already exists
in commentaries/dictionaries. Run once.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "study.db"
STAGING = ROOT / "data" / "staging"

COMMENTARY_SOURCES = ["clarke", "calvin", "keil_delitzsch", "treasury_of_david"]
DICT_SOURCES = ["easton", "isbe", "naves", "torrey"]

SOURCES_META = {
    "clarke": {
        "kind": "commentary",
        "title": "Adam Clarke, Commentary on the Whole Bible",
        "rights": "Public Domain",
        "rights_basis": (
            "Adam Clarke d. 1832; work published 1810-1825. Digital edition: "
            "HelloAO Free Use Bible API (adam-clarke), whose commentary-level "
            "metadata declares CC Public Domain Mark 1.0 "
            "(https://creativecommons.org/publicdomain/mark/1.0/), verified "
            "reachable 2026-09-20. No attribution required. Retrieved 2026-09-20."
        ),
        "version": "helloao adam-clarke",
    },
    "calvin": {
        "kind": "commentary",
        "title": "John Calvin, Commentaries (Calvin Translation Society English translation, 1843-1855)",
        "rights": "Public Domain",
        "rights_basis": (
            "John Calvin d. 1564; commentaries published in the 1500s. English "
            "translations by the Calvin Translation Society, 1843-1855 "
            "(translators John King, C. W. Bingham, Henry Beveridge, James "
            "Anderson, William Pringle, John Owen, Thomas Myers, John Pringle), "
            "all public domain by age. Each CCEL source file's embedded Dublin "
            "Core header states Rights: Public Domain. Retrieved 2026-09-20."
        ),
        "version": "CCEL calcom01-calcom45",
    },
    "keil_delitzsch": {
        "kind": "commentary",
        "title": "Keil & Delitzsch, Commentary on the Old Testament",
        "rights": "Public Domain",
        "rights_basis": (
            "Internet Archive item "
            "BiblicalCommentaryOldTestament.KeilAndDelitzsch.6 "
            "(item metadata verified 2026-09-20: 6 _djvu.txt files, no license "
            "field declared). "
            "1864-1892 T. & T. Clark English translation of the 19th-century "
            "German original; US public domain by expiry (all volumes pre-1931). "
            "OCR is a faithful transcription of a PD text and carries no new "
            "copyright. Retrieved 2026-09-20."
        ),
        "version": "1864-1892",
    },
    "treasury_of_david": {
        "kind": "commentary",
        "title": "C. H. Spurgeon, The Treasury of David (Psalms)",
        "rights": "Public Domain",
        "rights_basis": (
            "C. H. Spurgeon d. 1892. Digital edition: Internet Archive item "
            "ch-spurgeon-the-treasury-of-david-in-one-volume_202011, which "
            "carries Creative Commons Public Domain Mark 1.0 "
            "(http://creativecommons.org/publicdomain/mark/1.0/), read "
            "2026-09-20. Retrieved 2026-09-20."
        ),
        "version": None,
    },
    "easton": {
        "kind": "dictionary",
        "title": "M. G. Easton, Illustrated Bible Dictionary (1897)",
        "rights": "Public Domain",
        "rights_basis": (
            "Published 1897 by Thomas Nelson (author M. G. Easton d. 1894); "
            "public domain in the US by age. Digital edition: CrossWire SWORD "
            "Easton module v2.0.1, whose conf declares DistributionLicense="
            "Public Domain. Retrieved 2026-09-20."
        ),
        "version": "1897",
    },
    "isbe": {
        "kind": "dictionary",
        "title": "International Standard Bible Encyclopaedia (1915), ed. James Orr",
        "rights": "Public Domain",
        "rights_basis": (
            "1915 first publication (pre-1929, US public domain). Digital "
            "edition: CrossWire SWORD ISBE module v2.2, whose conf declares "
            "DistributionLicense=Public Domain; the 1939 Eerdmans reissue is a "
            "verbatim reprint of the 1915 Orr text. Retrieved 2026-09-20."
        ),
        "version": "1915",
    },
    "naves": {
        "kind": "dictionary",
        "title": "Orville J. Nave, Nave's Topical Bible (1896)",
        "rights": "Public Domain",
        "rights_basis": (
            "Published 1897 (copyright 1896/1897); pre-1930 US publication. "
            "Digital edition: Internet Archive item navestopicalbibl0000orvi_h3u8 "
            "(faithful scan/OCR, no new rights claimed). Retrieved 2026-09-20."
        ),
        "version": "1896",
    },
    "torrey": {
        "kind": "dictionary",
        "title": "R. A. Torrey, The New Topical Text Book (1897)",
        "rights": "Public Domain",
        "rights_basis": (
            "Published 1897 by Fleming H. Revell Co., Chicago (author R. A. "
            "Torrey d. 1928); pre-1929 US publication. Digital edition: ACU "
            "mirror of Ernie Stefanik's electronic edition, produced from the "
            "1897 Revell edition with no new copyright claim. Retrieved "
            "2026-09-20."
        ),
        "version": "1897",
    },
}

COVERAGE = {
    "clarke": "57 of 66 books; missing from the source digital edition: Deuteronomy, Judges, Psalms, Proverbs, Ecclesiastes, Jeremiah, Joel, Malachi, Matthew.",
    "calvin": "48 books: Genesis-Deuteronomy, Joshua, Psalms, Isaiah, Jeremiah, Lamentations, Ezekiel 1-20, Daniel, Hosea-Malachi, Matthew-Luke, John, Acts, Romans, 1-2 Corinthians, Galatians-Philemon, Hebrews, James, 1-2 Peter, 1 John, Jude. Not covered (as in Calvin's own work): Judges, Ruth, 1-2 Samuel, 1-2 Kings, 1-2 Chronicles, Ezra, Nehemiah, Esther, Job, Proverbs, Ecclesiastes, Song of Songs, 2-3 John, Revelation.",
    "keil_delitzsch": "Partial: 11 OT books — Genesis (1:1 only), Ezra, Nehemiah, Esther, Job (chs 29-42), Psalms (vols 2-3), Proverbs (vol 2), Isaiah (chs 29-66), Jeremiah (vol 1, partial), Ezekiel (vols 1-2), Daniel. Remaining 28 OT books exist only as image PDFs in the source item (OCR not completed); not ingested.",
    "treasury_of_david": "Psalms only: all 150 psalms, one whole-Psalm entry each.",
    "easton": "3,961 articles, headwords A-Z except X (no X entries in source).",
    "isbe": "9,349 articles A-Z (9,380 headwords in the CrossWire module; 31 empty in the raw module, excluded).",
    "naves": "4,726 topics, AARON through ZUZIMS; subtopics preserved in entry text; verse index excluded.",
    "torrey": "628 topical entries, letters A-Z (no topics under Q or X in the work).",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Idempotency guard
    existing = {r[0] for r in cur.execute(
        "SELECT DISTINCT source_id FROM commentaries")}
    existing |= {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dictionaries'")}
    clash = (set(COMMENTARY_SOURCES) & existing)
    if clash:
        raise SystemExit(f"Already ingested, refusing: {clash}")

    total_c = 0
    for sid in COMMENTARY_SOURCES:
        spath = STAGING / f"{sid}.db"
        table = "commentaries" if sid == "keil_delitzsch" else "rows"
        src = sqlite3.connect(f"file:{spath}?mode=ro", uri=True)
        rows = src.execute(
            f"""SELECT source_id, book, book_order, start_chapter, start_verse,
                       end_chapter, end_verse, text FROM {table}"""
        ).fetchall()
        src.close()
        cur.executemany(
            """INSERT INTO commentaries
               (source_id, book, book_order, start_chapter, start_verse,
                end_chapter, end_verse, text)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        total_c += len(rows)
        print(f"commentaries {sid}: {len(rows)} rows")

    # Dictionaries tables
    cur.execute(
        """CREATE TABLE IF NOT EXISTS dictionaries(
             id INTEGER PRIMARY KEY,
             source_id TEXT NOT NULL,
             term TEXT NOT NULL,
             text TEXT NOT NULL)"""
    )
    cur.execute(
        """CREATE INDEX IF NOT EXISTS idx_dictionaries_lookup
           ON dictionaries(source_id, term)"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS dictionary_sources(
             source_id TEXT PRIMARY KEY,
             title TEXT,
             rights TEXT,
             rights_basis TEXT,
             attribution TEXT,
             retrieved TEXT)"""
    )

    total_d = 0
    for sid in DICT_SOURCES:
        spath = STAGING / f"dict_{sid}.db"
        src = sqlite3.connect(f"file:{spath}?mode=ro", uri=True)
        rows = src.execute(
            "SELECT source_id, term, text FROM rows"
        ).fetchall()
        src.close()
        cur.executemany(
            "INSERT INTO dictionaries (source_id, term, text) VALUES (?, ?, ?)",
            rows,
        )
        total_d += len(rows)
        print(f"dictionaries {sid}: {len(rows)} rows")

    # Source metadata: dictionaries + commentaries
    for sid in COMMENTARY_SOURCES + DICT_SOURCES:
        m = SOURCES_META[sid]
        cur.execute(
            """INSERT OR REPLACE INTO sources
               (source_id, kind, title, rights, rights_basis, version, sha256)
               VALUES (?, ?, ?, ?, ?, ?, NULL)""",
            (sid, m["kind"], m["title"], m["rights"], m["rights_basis"],
             m["version"]),
        )
        if m["kind"] == "dictionary":
            cur.execute(
                """INSERT OR REPLACE INTO dictionary_sources
                   (source_id, title, rights, rights_basis, attribution, retrieved)
                   VALUES (?, ?, ?, ?, NULL, '2026-09-20')""",
                (sid, m["title"], m["rights"], m["rights_basis"]),
            )

    con.commit()

    # Post-merge verification
    for sid in COMMENTARY_SOURCES:
        n = cur.execute(
            "SELECT COUNT(*) FROM commentaries WHERE source_id=?", (sid,)
        ).fetchone()[0]
        print(f"verify commentaries {sid}: {n}")
    for sid in DICT_SOURCES:
        n = cur.execute(
            "SELECT COUNT(*) FROM dictionaries WHERE source_id=?", (sid,)
        ).fetchone()[0]
        print(f"verify dictionaries {sid}: {n}")
    print("integrity:", cur.execute("PRAGMA integrity_check").fetchone()[0])
    con.close()
    print(f"TOTAL commentary rows added: {total_c}")
    print(f"TOTAL dictionary rows added: {total_d}")


if __name__ == "__main__":
    main()
