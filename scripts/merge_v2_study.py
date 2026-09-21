#!/usr/bin/env python3
"""Merge verified v2 staging databases into data/study.db (DATA ONLY).

Inputs (all verified by their staging reports):
  staging/commentaries_v2.db  - commentaries, exact PLAN.md schema
  staging/crossrefs2.db       - TSK take-2 (PASS). Take-1 NEVER merged.
  staging/devotionals.db      - devotionals, exact PLAN.md schema
  staging/liturgy.db          - BCP liturgy (its `sources` table renamed to
                                `liturgy_sources` to avoid colliding with the
                                global PLAN.md `sources` table; FK rewritten
                                mechanically; everything else verbatim)

Creates the global `sources` table per the exact PLAN.md schema and records
rights metadata for every ingested source.

Refuses to run if data/study.db already exists. Never touches scripture.db.
"""
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
STAGING = PROJ / "staging"
OUT = PROJ / "data" / "study.db"

SOURCES = [
    ("matthew_henry", "commentary",
     "Matthew Henry, Complete Commentary on the Whole Bible",
     "Public Domain",
     "Original 1706-1721; author d. 1714. Transcriptions: HelloAO "
     "matthew-henry (CC0; metadata sha256 "
     "ad2850450a1e5c0546c275f4bd09b9325ae47424d83311120ca7ced5724c4bc8) "
     "for 1166 chapters; CCEL gap-fill (CCEL: 'Public domain. May be copied "
     "and distributed freely'; mhc2_ccel.txt sha256 "
     "b53ca73cf69947ab4f815a54998811167d412253b4595340a057d5b87766acb7) "
     "for 23 chapters. Retrieved 2026-09-20.",
     None, None),
    ("jfb", "commentary",
     "Jamieson, Fausset & Brown, Commentary Critical and Explanatory on the Whole Bible",
     "Public Domain",
     "Print basis 1871; authors d. 1870-1910. CCEL 1871 proofed transcription "
     "(CCEL rights: Public Domain; status: Proofed). Retrieved 2026-09-20.",
     "1871",
     "de2727aab8a63273a5a0826e1e17ac9270c7bf27976f3317e9be9a7542342a33"),
    ("barnes_nt", "commentary",
     "Albert Barnes, Barnes' New Testament Notes (NT only)",
     "Public Domain",
     "19th-c. original; CCEL transcription of the 1949 Baker reprint (CCEL "
     "rights: Public Domain). NT only (27 books): no faithful full-Bible PD "
     "transcription located. Retrieved 2026-09-20.",
     None,
     "ad54acfce1c2bd3b2a981d550a07928449b503a3014371e327b364a81ed90a38"),
    ("tsk", "crossref",
     "Treasury of Scripture Knowledge",
     "Public Domain",
     "CrossWire SWORD module v1.4 declares DistributionLicense=Public Domain; "
     "attributed to Canne, Browne, Blayney, Scott et al., 'about 1880'. Exact "
     "relation to the 1836 first edition not independently verified. "
     "Retrieved 2026-09-20.",
     "1.4",
     "6784c7099465995a8e66f02ead82b0bca66603c1bdeaf8332949774b7bfd4293"),
    ("spurgeon", "devotional",
     "C. H. Spurgeon, Morning and Evening (1866)",
     "Public Domain",
     "First published 1866 (London: Passmore & Alabaster); author d. 1892. "
     "Transcription: russianryebread/morning-and-evening @ "
     "6caf938672ee2ea777ec787c13573d439fe88bf7 (claims no copyright on the "
     "transcription). Retrieved 2026-09-20.",
     "1866",
     "2d86c9b47026f65cf041fb4ed5dca03d844296928d589535d346371bfbe7063b"),
    ("daily_light", "devotional",
     "Samuel Bagster, Daily Light on the Daily Path (1875)",
     "Public Domain",
     "All-scripture KJV text, long PD. Transcription: gm5dna/daily-light @ "
     "c36a7bf63ffc6ef5290a0cb82bd26fa28f9ffcdf (MIT repo asserting the text "
     "is public domain). 529 of 5,656 item references reconstructed from "
     "verse text against the KJV (fully documented). Retrieved 2026-09-20.",
     "1875",
     "7a776c8c6e0015a7a5da5744ac50de16f6a08a6895b47d0141a5884cd2763f0b"),
    ("bcp1662", "liturgy",
     "Book of Common Prayer (1662), Morning and Evening Prayer",
     "Public Domain",
     "First published 1662; transcription of the 1892 Pickering verbatim "
     "reprint via Wikisource (per-page pinned revisions). Retrieved 2026-09-20.",
     "1662", None),
    ("bcp1928", "liturgy",
     "Book of Common Prayer (1928, US), Morning and Evening Prayer",
     "Public Domain",
     "First published 1928 (US); 95-year copyright term expired 2024-01-01. "
     "Justus Anglican transcription via Wayback, corrected against the IA "
     "1928 Standard Book scan. Retrieved 2026-09-20.",
     "1928", None),
]


def copy_table(dst, src_path, table, rename=None):
    """Copy a table's schema + rows + indexes verbatim from a staging DB."""
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    srow = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if not srow or not srow[0]:
        src.close()
        raise RuntimeError(f"table {table} missing in {src_path}")
    sql = srow[0]
    new_name = rename or table
    if rename:
        sql = sql.replace(f"CREATE TABLE {table}",
                          f"CREATE TABLE {rename}", 1)
        sql = sql.replace("REFERENCES sources(",
                          "REFERENCES liturgy_sources(", 1)
    dst.execute(sql)
    cols = [r[1] for r in src.execute(f"PRAGMA table_info({table})")]
    n = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    for row in src.execute(
            f"SELECT {', '.join(cols)} FROM {table}"):
        dst.execute(
            f"INSERT INTO {new_name} ({', '.join(cols)}) "
            f"VALUES ({', '.join('?' * len(cols))})", row)
    for (iname, isql) in src.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' "
            "AND sql IS NOT NULL AND tbl_name=?", (table,)):
        isql2 = isql.replace(f"ON {table} (", f"ON {new_name} (", 1)
        iname2 = iname.replace(table, new_name) if rename else iname
        isql2 = isql2.replace(f"INDEX {iname}", f"INDEX {iname2}", 1)
        dst.execute(isql2)
    src.close()
    print(f"  {src_path.name}:{table} -> {new_name}: {n} rows")
    return n


def main():
    if OUT.exists():
        print(f"ERROR: {OUT} exists; refusing to overwrite.")
        sys.exit(1)
    for req in ("commentaries_v2.db", "crossrefs2.db", "devotionals.db",
                "liturgy.db"):
        if not (STAGING / req).exists():
            print(f"ERROR: missing staging input {req}")
            sys.exit(1)
    if (STAGING / "crossrefs.db").exists():
        print("NOTE: staging/crossrefs.db (rejected take-1) present; "
              "it will NOT be merged.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(OUT))
    cur = conn.cursor()

    # Global sources table: exact PLAN.md schema
    cur.execute(
        """CREATE TABLE sources (
             source_id TEXT PRIMARY KEY,
             kind TEXT NOT NULL,
             title TEXT NOT NULL,
             rights TEXT NOT NULL,
             rights_basis TEXT NOT NULL,
             version TEXT,
             sha256 TEXT
           )"""
    )
    cur.executemany(
        "INSERT INTO sources (source_id, kind, title, rights, rights_basis,"
        " version, sha256) VALUES (?,?,?,?,?,?,?)", SOURCES)
    print(f"sources: {len(SOURCES)} rows")

    total = copy_table(conn, STAGING / "commentaries_v2.db", "commentaries")
    total += copy_table(conn, STAGING / "crossrefs2.db", "crossrefs")
    total += copy_table(conn, STAGING / "devotionals.db", "devotionals")
    # liturgy staging `sources` -> liturgy_sources (documented rename)
    copy_table(conn, STAGING / "liturgy.db", "sources", rename="liturgy_sources")
    total += copy_table(conn, STAGING / "liturgy.db", "liturgy")
    conn.commit()

    # Post-merge verification
    cur.execute("PRAGMA integrity_check")
    assert cur.fetchone()[0] == "ok", "integrity_check failed"
    print("PRAGMA integrity_check: ok")
    for tbl in ("sources", "commentaries", "crossrefs", "devotionals",
                "liturgy", "liturgy_sources"):
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  study.db {tbl}: {n}")
    # FK sanity: every commentary source_id in sources; liturgy FKs resolve
    bad = cur.execute(
        "SELECT COUNT(*) FROM commentaries c LEFT JOIN sources s "
        "ON c.source_id=s.source_id WHERE s.source_id IS NULL").fetchone()[0]
    assert bad == 0, "commentary source_id without sources row"
    bad = cur.execute(
        "SELECT COUNT(*) FROM liturgy l LEFT JOIN liturgy_sources s "
        "ON l.source_id=s.id WHERE s.id IS NULL").fetchone()[0]
    assert bad == 0, "liturgy source_id without liturgy_sources row"
    bad = cur.execute(
        "SELECT COUNT(*) FROM devotionals d LEFT JOIN sources s "
        "ON d.source_id=s.source_id WHERE s.source_id IS NULL").fetchone()[0]
    assert bad == 0, "devotional source_id without sources row"
    print("FK checks: ok")
    conn.close()
    print(f"\nOK: {OUT}")


if __name__ == "__main__":
    main()
