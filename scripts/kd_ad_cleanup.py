#!/usr/bin/env python3
"""Keil & Delitzsch publisher-advertisement cleanup, second pass (2026-09-20).

Volume-end K&D rows swept trailing publisher catalog / printer / library /
Google-scan matter into the last commentary section. This script truncates
each affected row at a MANUALLY VERIFIED boundary (commentary -> trailing
matter transition inspected per row), preserving genuine footnote citations.

Special cases:
  - id=71524 (Eccl 8:14): genuine footnote citing T. and T. Clark. EXCLUDED.
  - id=70427 (Job 2:4), id=70440 (Job 5:12): genuine footnotes mentioning
    Clark's Foreign Theological Library. EXCLUDED (never candidates).
  - id=66284 (Job 42:17): genuine publisher citation ~41527 preserved;
    truncation is at the catalog start ~58849, well after it.
  - id=71579 (Eccl 1:1-17): row is 100% publisher catalog, zero Ecclesiastes
    commentary (no Koheleth/Ecclesiastes/verse/Ver. anywhere in 12,195
    chars). DELETED as a pure-ad row. A proper Eccl 1:1 row (id=71460)
    already exists.

Usage:
  python3 scripts/kd_ad_cleanup.py --scan        # list candidates (read-only)
  python3 scripts/kd_ad_cleanup.py --dryrun      # simulate on a temp copy
  python3 scripts/kd_ad_cleanup.py --apply       # apply to data/study.db
"""
import argparse
import os
import re
import shutil
import sqlite3
import sys
import tempfile

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "study.db")

# Manually verified truncation boundaries: row id -> keep [0:boundary].
# Each boundary was set by inspecting the commentary -> trailing-matter
# transition in the live row. Boundary markers noted per row.
BOUNDARIES = {
    68857: 2645,    # Lev 27:30-33 - before "END OF VOLUME II."; printer/catalog/Google follow (boundary corrected: earlier 13579 left catalog in kept text)
    69485: 3643,    # Ruth 4:18-20 - after "(Brentitu)."; printer colophon + catalog follow
    69780: 1814,    # 2Sam 24:25 - after "was to build."; Google scan boilerplate follows
    70341: 1180,    # 2Chr 36:22 - before "THE END."; printer/library/Google/subscriber/catalog follow
    66238: 5550,    # Esther 10:1 - after "teaching the fear of the Lord."; ad matter follows
    66284: 58849,   # Job 42:17 - before "PUBLICATIONS OF T."; keeps INDEX OF TEXTS + genuine Clark citation @41527
    70719: 488,     # Ps 35:27 - before "Digitized by Googk"; scan stamp + catalog follow
    66526: 20195,   # Ps 83:18-19 - before "close of the Council of Chalcedon"; alphabetical catalog follows
    70876: 21474,   # Ps 83:18 - before "T. and T. Clark's Publications."; Godet/catalog follow
    66811: 9067,    # Ps 150:6 - before "T. and T. Claris Publications." (OCR garble); product catalog follows
    71319: 1148,    # Prov 17:28 - before "END OP VOL. I." (OCR); catalog follows
    67125: 16229,   # Prov 31:31 - before "THE END."; Lange/catalog follow
    71578: 9046,    # Eccl 12:14 - before "Rarely have"; Dorner adatalog follow
    71620: 10449,   # Isa 27:7-13 - before "XND OF YOL L" (garbled END OF VOL I); Scribner catalog follows
    67174: 2045,    # Isa 66:22 - before "Fourth Edition, price 10s. 6d, MODERN DOUBT"; book ads follow
    67355: 1205,    # Jer 18:0 - before "SeRIBNER & WEIsFORID'S Catalogue"; scan breaks mid-sentence
    71719: 1262,    # Jer 18:1-23 - before "SeRIBNER & WEIdFORD'S Catalogue"; scan breaks mid-sentence
    67435: 8209,    # Jer 29:24-32 - before "END OF VOL. I."; catalog follows
    71915: 5049,    # Lam 5:17-22 - before "THE END."; library/printer/publisher matter follow
    67683: 935,     # Ezek 28:25 - before "END OF VOL. I."; printer matter + catalog follow
    67853: 89585,   # Ezek 48:30-35 - before "^ntE=Kicene" (Ante-Nicene series title page); series matter follows
    68108: 1616,    # Dan 12:13 - before "THE END."; catalog follows
    # Additional volume-end rows found in post-apply sweep (same defect)
    69202: 40149,   # Deut 34:9-34:12 - before "END OF VOL. III."; printer/Google/library stamps follow
    72324: 2175,    # Micah 7:20 - before "END OF VOL. I." (at end, no catalog after)
    72493: 14291,   # Mal 4:4-4:6 - before "END OF VOL. II." (at end, no catalog after)
    70049: 10339,   # 2Kgs 25:22-25:30 - before "THE END." (at end, no catalog after)
}

# Rows that are 100% non-commentary publisher catalog.
# id=71579 (Eccl 1:1-17): 12,195 chars, zero Ecclesiastes commentary
# (no Koheleth/Ecclesiastes/verse/Ver. anywhere). PENDING PARENT APPROVAL
# FOR DELETION per the assigned constraint (row count must stay 6,325
# unless the parent explicitly approves). NOT deleted by this script.
# A proper Eccl 1:1 row (id=71460) already exists.
PENDING_DELETE_IDS = [71579]

# Rows that must NEVER be touched (genuine citations, verified by inspection).
PROTECTED_IDS = [71524, 70427, 70440]

EXPECTED_COUNT_BEFORE = 6325


def get_db(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def describe(db, rid):
    r = db.execute(
        "SELECT id, book, start_chapter, start_verse, end_chapter, end_verse,"
        " length(text) AS n FROM commentaries WHERE id=?", (rid,)).fetchone()
    return r


def run(db, apply):
    plan = []
    for rid, boundary in sorted(BOUNDARIES.items()):
        r = describe(db, rid)
        if r is None:
            plan.append(("MISSING", rid, None, None, boundary))
            continue
        rng = "%s %d:%d-%d:%d" % (r["book"], r["start_chapter"], r["start_verse"],
                                  r["end_chapter"], r["end_verse"])
        plan.append(("TRUNCATE", rid, rng, r["n"], boundary))
    for rid in PENDING_DELETE_IDS:
        r = describe(db, rid)
        if r is None:
            plan.append(("MISSING", rid, None, None, None))
            continue
        rng = "%s %d:%d-%d:%d" % (r["book"], r["start_chapter"], r["start_verse"],
                                  r["end_chapter"], r["end_verse"])
        plan.append(("PENDING-DELETE", rid, rng, r["n"], None))
    # Protected rows must be untouched; verify they exist and are not in plan.
    for rid in PROTECTED_IDS:
        r = describe(db, rid)
        assert r is not None, "protected row %d missing!" % rid
        assert rid not in BOUNDARIES and rid not in PENDING_DELETE_IDS

    if not apply:
        return plan

    # --- apply ---
    for action, rid, rng, n, boundary in plan:
        if action == "TRUNCATE":
            original = db.execute("SELECT text FROM commentaries WHERE id=?", (rid,)).fetchone()[0]
            assert len(original) == n, "length changed for %d" % rid
            kept = original[:boundary].rstrip()
            # strip trailing dangling punctuation/dashes left by the cut
            kept = re.sub(r"[\s\-–—·.]+$", "", kept)
            db.execute("UPDATE commentaries SET text=? WHERE id=?", (kept, rid))
        elif action == "PENDING-DELETE":
            pass  # requires explicit parent approval; never auto-deleted
        # MISSING rows: nothing to do
    db.commit()
    return plan


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--scan", action="store_true")
    g.add_argument("--dryrun", action="store_true")
    g.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.scan:
        db = get_db(DB)
        n = db.execute("SELECT COUNT(*) FROM commentaries WHERE source_id='keil_delitzsch'").fetchone()[0]
        print("K&D live rows: %d (expected %d)" % (n, EXPECTED_COUNT_BEFORE))
        for action, rid, rng, ln, boundary in run(db, apply=False):
            if action == "TRUNCATE":
                print("%-8s id=%d %-22s len=%6d -> keep %6d" % (action, rid, rng, ln, boundary))
            elif action == "PENDING-DELETE":
                print("%-8s id=%d %-22s len=%6d (100%% catalog; NOT deleted, needs approval)" % (action, rid, rng, ln))
            else:
                print("%-8s id=%d" % (action, rid))
        print("protected (untouched): %s" % PROTECTED_IDS)
        return

    if args.dryrun:
        tmp = tempfile.mktemp(suffix=".db")
        shutil.copy2(DB, tmp)
        db = get_db(tmp)
        plan = run(db, apply=True)
        # verify on the copy
        n = db.execute("SELECT COUNT(*) FROM commentaries WHERE source_id='keil_delitzsch'").fetchone()[0]
        integ = db.execute("PRAGMA integrity_check").fetchone()[0]
        print("dryrun: K&D rows=%d (expect %d), integrity=%s" % (
            n, EXPECTED_COUNT_BEFORE, integ))
        for action, rid, rng, ln, boundary in plan:
            if action == "TRUNCATE":
                newlen = db.execute("SELECT length(text) FROM commentaries WHERE id=?", (rid,)).fetchone()[0]
                print("  id=%d %s: %d -> %d" % (rid, rng, ln, newlen))
            elif action == "PENDING-DELETE":
                print("  id=%d %s: left intact (pending parent approval)" % (rid, rng))
        # confirm protected rows unchanged (byte-identical to live)
        livedb = get_db(DB)
        for rid in PROTECTED_IDS:
            a = livedb.execute("SELECT text FROM commentaries WHERE id=?", (rid,)).fetchone()[0]
            b = db.execute("SELECT text FROM commentaries WHERE id=?", (rid,)).fetchone()[0]
            assert a == b, "protected row %d changed!" % rid
        print("  protected rows byte-identical: OK")
        db.close()
        os.unlink(tmp)
        return

    if args.apply:
        # safety: refuse unless a fresh backup exists
        datadir = os.path.dirname(DB)
        baks = [f for f in os.listdir(datadir) if f.startswith("study.db.bak-kd-adcleanup-")]
        if not baks:
            print("REFUSING: no kd-adcleanup backup found in %s" % datadir, file=sys.stderr)
            sys.exit(1)
        db = get_db(DB)
        n0 = db.execute("SELECT COUNT(*) FROM commentaries WHERE source_id='keil_delitzsch'").fetchone()[0]
        assert n0 == EXPECTED_COUNT_BEFORE, "unexpected K&D count %d" % n0
        plan = run(db, apply=True)
        n1 = db.execute("SELECT COUNT(*) FROM commentaries WHERE source_id='keil_delitzsch'").fetchone()[0]
        integ = db.execute("PRAGMA integrity_check").fetchone()[0]
        print("applied: K&D rows %d -> %d, integrity=%s" % (n0, n1, integ))
        assert n1 == EXPECTED_COUNT_BEFORE
        assert integ == "ok"
        for action, rid, rng, ln, boundary in plan:
            print("  %-8s id=%d %s" % (action, rid, rng))
        db.close()


if __name__ == "__main__":
    main()
