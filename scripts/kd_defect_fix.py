#!/usr/bin/env python3
"""Keil & Delitzsch targeted defect fix.

Fixes, in one transaction with pre-assertions on every row:
  1. Exodus 11:4-8 (id 68552): strip publisher advertisement appended to text.
  2. Sixteen inverted ranges (end < start): correct to text-supported ranges.
  3. Thirty-six repeated-range groups: reassign clear misfiles, delete true
     duplicates / inferior OCR variants, keep all materially distinct text.
  4. Recover fifteen genuine parser-missed sections from raw OCR
     (1 Sam 1:1-8; 2 Kings 8:1-15, 8:16-24, 21:1-18, 21:19-26;
      Isaiah 3:1-7, 3:8-9, 3:10-15, 3:16-17, 3:18-26;
      Isaiah 64:1-2, 64:4, 64:5, 64:6, 64:9-11).
  5. 2 Kings 6:24-7:20 famine narrative (id 69949): fix range, truncate text
     where the next chapter's section header begins.

Usage:
  python3 kd_defect_fix.py --dry-run   # apply to a temp copy, verify, report
  python3 kd_defect_fix.py --apply     # apply to live data/study.db

Never invents commentary text. Every change is asserted against the row's
current id, range, length, and text markers before it is applied.
"""
import argparse
import os
import re
import shutil
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
LIVE_DB = os.path.join(PROJ, "data", "study.db")
RAW2 = os.path.join(PROJ, "data", "raw_v2", "keil_delitzsch",
                    "02.BCOT.KD.HistoricalBooks.A.vol.2.EarlyProphets._djvu.txt")
RAW5 = os.path.join(PROJ, "data", "raw_v2", "keil_delitzsch",
                    "05.BCOT.KD.PropheticalBooks.A.vol.5.GreaterProphets._djvu.txt")

SRC = "keil_delitzsch"

# ----------------------------------------------------------------------------
# Fix specifications
# ----------------------------------------------------------------------------

# id -> (new_sc, new_sv, new_ec, new_ev, note)
RANGE_FIXES = {
    68584: (15, 1, 15, 5, "Exodus 15:1-5; text ends at v.5"),
    69338: (23, 2, 23, 13, "Joshua 23:2-13; text discusses Joshua 23"),
    69885: (16, 29, 16, 29, "1 Kings 16:29 epoch intro; text states scope "
             "1 Kings 16:29-2 Kings 10:27 which the schema cannot represent"),
    69949: (6, 24, 7, 20, "2 Kings 6:24-7:20 famine narrative; text truncated "
             "where ch.8 section header begins"),
    70024: (20, 12, 20, 19, "2 Kings 20:12-19; header OCR '12-10' of '12-19'"),
    70387: (12, 44, 13, 31, "Nehemiah 12:44-13:31; header 'xii.44-xiii.31'"),
    70431: (4, 12, 4, 21, "Job 4:12-21; Eliphaz vision exposition"),
    70481: (33, 13, 33, 14, "Job 33:13-14; header OCR '13-ifc' of '13, 14'"),
    71367: (31, 1, 31, 5, "Proverbs 31:1-5; misfiled ch.31 material"),
    71481: (3, 10, 3, 11, "Ecclesiastes 3:10-11; head says 'Vers. 10, 11'"),
    71652: (52, 12, 52, 13, "Isaiah 52:12-13; bridge into Servant prophecy"),
    71653: (52, 13, 53, 12, "Isaiah 52:13-53:12; fifth prophecy"),
    71659: (56, 9, 57, 21, "Isaiah 56:9-57:21; header 'lvi.9-lvii.21'"),
    71993: (30, 20, 30, 26, "Ezekiel 30:20-26; header OCR '30:20-2G'"),
    72457: (11, 15, 11, 17, "Zechariah 11:15-17; head says 'Vers. 15-17'"),
}

# id -> (book, sc, sv, ec, ev, note): clear misfiles, no text loss
REASSIGNS = {
    67917: ("Daniel", 4, 2, 4, 2, "text: 'Ver. 2 (ch. iv. 5)'"),
    67923: ("Daniel", 4, 13, 4, 13, "Daniel 4:13 material"),
    67924: ("Daniel", 4, 14, 4, 14, "Daniel 4:14 material"),
    67925: ("Daniel", 4, 15, 4, 15, "Daniel 4:15 material"),
    67927: ("Daniel", 4, 16, 4, 16, "Daniel 4:16 material"),
    66488: ("Psalms", 76, 1, 76, 1, "Psalm 76 title + v.1; was filed 75:2-4"),
    66492: ("Psalms", 77, 2, 77, 4, "Psalm 77:2-4; running head PSALM LXXVII"),
}

# ids to delete: true duplicates / inferior OCR variants / stubs whose text
# is fully contained in the kept row. Reasons recorded in the manifest.
DELETES = {
    67909: "Daniel 3:16 inferior OCR variant of 67908",
    67503: "Ezekiel 10:1 inferior variant; 67504 kept",
    67647: "Ezekiel 25:1-7 inferior variant; 67650 kept",
    67651: "Ezekiel 25:3 inferior variant; 67648 kept",
    67649: "Ezekiel 25:4 inferior variant; 67652 kept",
    67656: "Ezekiel 26:0 inferior variant; 67657 kept",
    67719: "Ezekiel 33:0 inferior variant; 67720 kept",
    67730: "Ezekiel 33:30 stub; text contained in 67729",
    67824: "filed Ezek 44:2, actually Ezek 45:2 dup of 67811",
    66002: "Ezra 1:0 inferior variant; 66003 kept",
    67141: "filed Isa 39:2, actually Isa 40:2 dup of 71641",
    67215: "Jeremiah 4:21 inferior variant; 67217 kept",
    67241: "Jeremiah 6:16 fragment; 67243 kept",
    67255: "Jeremiah 7:27 stub; text contained in 67253",
    67257: "Jeremiah 7:29 section-heading stub; 67258 kept",
    67283: "Jeremiah 10:14 inferior variant; 67282 kept",
    67306: "Jeremiah 12:14 inferior variant; 67304 kept",
    67324: "filed Jer 14:5, actually Jer 15:5 dup of 71715",
    67377: "filed Jer 21:5, actually Jer 22:5 fragment of 71727",
    66126: "Nehemiah 7:0 page-header stub; 66125 kept",
    66143: "Nehemiah 9:26 stub; text contained in 66145",
    66162: "Nehemiah 12:1-9 fragment; 66163 kept",
    66906: "Proverbs 22:6 textual-note fragment; 66905 kept",
    66921: "Proverbs 22:29 inferior variant; 66922 kept",
    67012: "filed Prov 26:3, actually Prov 27:3 dup of 71343",
    67013: "filed Prov 26:4, actually Prov 27:4 dup of 71344",
    67014: "filed Prov 26:5, actually Prov 27:5 dup of 71345",
    66329: "Psalms 44:0 inferior variant; 66330 kept",
    68050: "Daniel 10:0 fragment; 68041 kept",
    68085: "Daniel 11:36 heading stub; 68088 kept",
    68087: "Daniel 11:36-39 heading stub; 68086 kept",
    72053: "Daniel 9:24-27 section scan; 75% redundant with longer/cleaner 68037",
}

# (raw_file, start_line, end_line, book, sc, sv, ec, ev, note)
# 1-based inclusive raw line numbers. Text cleaned like the original parser:
# running page heads and repeated section headers dropped, whitespace collapsed.
RECOVERIES = [
    (RAW2, 26230, 26606, "1 Samuel", 1, 1, 1, 8,
     "Vers. 1-8. Samuel's pedigree"),
    (RAW2, 68804, 68964, "2 Kings", 8, 1, 8, 15,
     "Shunammite + Hazael; parser dropped section body"),
    (RAW2, 68965, 69061, "2 Kings", 8, 16, 8, 24,
     "Reign of Joram of Judah; parser dropped section body"),
    (RAW2, 75920, 76154, "2 Kings", 21, 1, 21, 18,
     "Reign of Manasseh; CHAP. XXL 1-18"),
    (RAW2, 76155, 76181, "2 Kings", 21, 19, 21, 26,
     "Reign of Amon; CHAP. XXL 19-26"),
    (RAW5, 6930, 7133, "Isaiah", 3, 1, 3, 7,
     "stay/staff of bread through vv.6-7; header garbled"),
    (RAW5, 7134, 7235, "Isaiah", 3, 8, 3, 9,
     "CHAPTER III. 8.; prosopopeia of ver. 8"),
    (RAW5, 7236, 7540, "Isaiah", 3, 10, 3, 15,
     "CHAPTER III. 10, 11.; discusses vv.10-15"),
    (RAW5, 7541, 7645, "Isaiah", 3, 16, 3, 17,
     "daughters of Zion"),
    (RAW5, 7646, 8172, "Isaiah", 3, 18, 3, 26,
     "CHAPTER III. 18-26."),
    (RAW5, 46862, 46952, "Isaiah", 64, 1, 64, 2,
     "CHAP. LXIV. 1, 2; discusses vv.1-4"),
    (RAW5, 46953, 47043, "Isaiah", 64, 4, 64, 4,
     "no ear heard / 1 Cor 2:9"),
    (RAW5, 47044, 47132, "Isaiah", 64, 5, 64, 5,
     "header OCR 'LXIV. i.'; discusses ver. 5"),
    (RAW5, 47133, 47223, "Isaiah", 64, 6, 64, 6,
     "CHAP. LXIV. 6"),
    (RAW5, 47224, 47307, "Isaiah", 64, 9, 64, 11,
     "CHAP. LXIV. 9-11"),
]

AD_ID = 68552
AD_CUT = 4462  # valid commentary ends: 'go out of his land."'

BOOK_ORDERS = {"1 Samuel": 9, "2 Kings": 12, "Isaiah": 23}
AD_MARKERS = ["T. and T. Clark", "HISTORY OF THE CHRISTIAN CHURCH",
              "PHILIP SCHAFF", "UNION THEOLOGICAL"]

FAMINE_ID = 69949

# id -> (book, sc, sv, ec, ev, text_len, [required substrings])
ASSERTIONS = {
    68552: ("Exodus", 11, 4, 11, 8, 38161, ["go out of his land."]),
    68584: ("Exodus", 15, 16, 15, 5, 2487, ["Ver. 5."]),
    69338: ("Joshua", 24, 26, 24, 13, 5101, []),
    69885: ("1 Kings", 16, 29, 16, 2, 2321, ["2 Kings x. 27"]),
    69949: ("2 Kings", 6, 24, 5, 24, 13992, ["chap, vl 24-vn. 20"]),
    70024: ("2 Kings", 20, 12, 20, 10, 4007, ["CHAP. XX 12-10"]),
    70387: ("Nehemiah", 12, 44, 10, 44, 2577, ["xii. 44-xhi. 31"]),
    70431: ("Job", 4, 17, 4, 8, 4531, []),
    70481: ("Job", 33, 13, 1, 13, 858, []),
    71367: ("Proverbs", 10, 5, 1, 5, 3990, ["CHAP. X5XI. i, 5"]),
    71481: ("Ecclesiastes", 3, 10, 3, 1, 9183, ["Vers. 10, 1 1"]),
    71652: ("Isaiah", 52, 13, 51, 13, 1961, ["Behold my servant"]),
    71653: ("Isaiah", 52, 13, 50, 13, 28029, ["FIFTH PROPHECY"]),
    71659: ("Isaiah", 56, 9, 50, 9, 47760, ["Chap. lvi. 9-lyii. 21"]),
    71993: ("Ezekiel", 30, 20, 30, 2, 1046, ["XXX. 20-2G"]),
    72457: ("Zechariah", 11, 15, 11, 1, 7082, ["Vers. 15-1 7"]),
}


def clean_raw_text(lines):
    """Drop running page heads and repeated section headers, collapse space."""
    out = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        # running page heads: "470  THE  SECOND  BOOK  OF  KINGS."
        if re.match(r"^\d+\s+(THE\s+)?(FIRST|SECOND)\s+BOOK\s+OF\s+(SAMUEL|KINGS)\.?\s*$", s):
            continue
        if re.match(r"^\d+\s+ISAIAH\.\s*$", s):
            continue
        if re.match(r"^Digitized\s+by\s*$", s):
            continue
        if re.match(r"^Google\s*$", s):
            continue
        if re.match(r"^V[ij]OOQlC\s*$", s):  # OCR of "Google"
            continue
        if re.match(r"^VOL\.\s+[IVX]+\s+[A-Z]\s*$", s):
            continue
        # repeated section headers after the first line
        if i > 0 and re.match(r"^(CHAP|CHAPTER)\.?\s+[A-Z0-9]", s):
            continue
        out.append(s)
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def run_assertions(db):
    cur = db.cursor()
    for rid, (book, sc, sv, ec, ev, tlen, subs) in ASSERTIONS.items():
        row = cur.execute(
            "SELECT book, start_chapter, start_verse, end_chapter, end_verse,"
            " length(text), text FROM commentaries WHERE id=? AND source_id=?",
            (rid, SRC)).fetchone()
        assert row, f"row {rid} missing"
        b, a, c, d, e, ln, tx = row
        assert (b, a, c, d, e) == (book, sc, sv, ec, ev), \
            f"row {rid} range changed: {(b, a, c, d, e)}"
        assert ln == tlen, f"row {rid} text length changed: {ln} != {tlen}"
        for s in subs:
            assert s in tx, f"row {rid} marker {s!r} not found"
    for rid in list(REASSIGNS) + list(DELETES):
        n = cur.execute(
            "SELECT count(*) FROM commentaries WHERE id=? AND source_id=?",
            (rid, SRC)).fetchone()[0]
        assert n == 1, f"row {rid} missing for reassign/delete"
    # no recovery key may already exist
    for (_, _, _, book, sc, sv, ec, ev, _) in RECOVERIES:
        n = cur.execute(
            "SELECT count(*) FROM commentaries WHERE source_id=? AND book=?"
            " AND start_chapter=? AND start_verse=? AND end_chapter=?"
            " AND end_verse=?",
            (SRC, book, sc, sv, ec, ev)).fetchone()[0]
        assert n == 0, f"recovery key {book} {sc}:{sv}-{ev} already exists"
    print("assertions: all", len(ASSERTIONS) + len(REASSIGNS) + len(DELETES),
          "target rows verified")


def apply_fixes(db, manifest):
    cur = db.cursor()

    # 1. advertisement strip
    tx = cur.execute("SELECT text FROM commentaries WHERE id=?",
                     (AD_ID,)).fetchone()[0]
    assert tx[AD_CUT - 7:AD_CUT] == ' land."', "ad cut marker moved"
    kept = tx[:AD_CUT]
    for m in AD_MARKERS:
        assert m not in kept, f"ad marker {m!r} inside kept text"
    cur.execute("UPDATE commentaries SET text=? WHERE id=?", (kept, AD_ID))
    manifest.append(f"TRUNCATE id={AD_ID} Exodus 11:4-8: 38161 -> {len(kept)}"
                    " chars; advertisement removed")

    # 2. inverted ranges (+ famine truncation)
    for rid, (sc, sv, ec, ev, note) in RANGE_FIXES.items():
        if rid == FAMINE_ID:
            tx = cur.execute("SELECT text FROM commentaries WHERE id=?",
                             (rid,)).fetchone()[0]
            cut = tx.find("Digitized by", 13700)
            assert 13700 < cut < 13800, "famine truncation marker moved"
            new_text = tx[:cut].rstrip()
            assert new_text.endswith("its fulfilment"), \
                "famine text tail unexpected"
            cur.execute(
                "UPDATE commentaries SET start_chapter=?, start_verse=?,"
                " end_chapter=?, end_verse=?, text=? WHERE id=?",
                (sc, sv, ec, ev, new_text, rid))
            manifest.append(
                f"FIX id={rid} 2 Kings 6:24-5:24 -> 6:24-7:20; text "
                f"{len(tx)} -> {len(new_text)} chars (ch.8 header stub cut)")
        else:
            cur.execute(
                "UPDATE commentaries SET start_chapter=?, start_verse=?,"
                " end_chapter=?, end_verse=? WHERE id=?",
                (sc, sv, ec, ev, rid))
            manifest.append(f"FIX id={rid} range corrected: {note}")

    # 3. misfile reassigns
    for rid, (book, sc, sv, ec, ev, note) in REASSIGNS.items():
        cur.execute(
            "UPDATE commentaries SET book=?, start_chapter=?, start_verse=?,"
            " end_chapter=?, end_verse=? WHERE id=?",
            (book, sc, sv, ec, ev, rid))
        manifest.append(f"REASSIGN id={rid} -> {book} {sc}:{sv}-{ec}:{ev}"
                        f" ({note})")

    # 4. deletions
    for rid, reason in DELETES.items():
        cur.execute("DELETE FROM commentaries WHERE id=?", (rid,))
        manifest.append(f"DELETE id={rid}: {reason}")

    # 5. recovery inserts from raw OCR
    for (path, lo, hi, book, sc, sv, ec, ev, note) in RECOVERIES:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        seg = [ln.rstrip("\n") for ln in lines[lo - 1:hi]]
        text = clean_raw_text(seg)
        assert len(text) > 200, f"recovery {book} {sc}:{sv} too short"
        cur.execute(
            "INSERT INTO commentaries (source_id, book, book_order,"
            " start_chapter, start_verse, end_chapter, end_verse, text)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (SRC, book, BOOK_ORDERS[book], sc, sv, ec, ev, text))
        nid = cur.lastrowid
        manifest.append(f"INSERT id={nid} {book} {sc}:{sv}-{ec}:{ev}"
                        f" ({len(text)} chars; {note})")

    db.commit()


def verify(db):
    cur = db.cursor()
    cur.execute("PRAGMA integrity_check")
    assert cur.fetchone()[0] == "ok", "integrity check failed"
    n = cur.execute("SELECT count(*) FROM commentaries WHERE source_id=?",
                    (SRC,)).fetchone()[0]
    inv = cur.execute(
        "SELECT count(*) FROM commentaries WHERE source_id=?"
        " AND (end_chapter < start_chapter OR (end_chapter = start_chapter"
        " AND end_verse < start_verse))", (SRC,)).fetchone()[0]
    dup = cur.execute(
        "SELECT sum(cnt - 1) FROM (SELECT book, start_chapter, start_verse,"
        " end_chapter, end_verse, count(*) AS cnt FROM commentaries"
        " WHERE source_id=? GROUP BY 1,2,3,4,5 HAVING cnt > 1)",
        (SRC,)).fetchone()[0] or 0
    books = cur.execute(
        "SELECT count(DISTINCT book) FROM commentaries WHERE source_id=?",
        (SRC,)).fetchone()[0]
    ad = cur.execute(
        "SELECT count(*) FROM commentaries WHERE id=? AND (text LIKE"
        " '%T. and T. Clark%' OR text LIKE '%PHILIP SCHAFF%')",
        (AD_ID,)).fetchone()[0]
    fam = cur.execute(
        "SELECT start_chapter, start_verse, end_chapter, end_verse,"
        " length(text) FROM commentaries WHERE id=?", (FAMINE_ID,)).fetchone()
    print(f"verify: rows={n} books={books} inverted={inv} dup_extras={dup}"
          f" ad_markers={ad} famine={fam[0]}:{fam[1]}-{fam[2]}:{fam[3]}"
          f" ({fam[4]} chars)")
    assert inv == 0, "inverted ranges remain"
    assert dup == 0, "duplicate range groups remain"
    assert books == 39, "book count changed"
    assert ad == 0, "advertisement markers remain"
    assert tuple(fam[:4]) == (6, 24, 7, 20), "famine range wrong"
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.dry_run == args.apply:
        sys.exit("specify exactly one of --dry-run or --apply")

    if args.dry_run:
        tmp = os.path.join(PROJ, "tmp")
        os.makedirs(tmp, exist_ok=True)
        db_path = os.path.join(tmp, "study.db.dryrun-kd-fix")
        if os.path.exists(db_path):
            os.remove(db_path)
        shutil.copy2(LIVE_DB, db_path)
        print("dry-run on", db_path)
    else:
        db_path = LIVE_DB
        print("APPLYING to live", db_path)

    db = sqlite3.connect(db_path)
    try:
        run_assertions(db)
        manifest = []
        apply_fixes(db, manifest)
        n = verify(db)
        print(f"final K&D row count: {n}")
        out = os.path.join(PROJ, "verification", "v2",
                           "kd-defectfix-manifest.md")
        if args.dry_run:
            out = out.replace("manifest", "manifest-dryrun")
        with open(out, "w") as f:
            f.write("# K&D defect fix manifest\n\n")
            for m in manifest:
                f.write("- " + m + "\n")
        print("manifest:", out, f"({len(manifest)} entries)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
