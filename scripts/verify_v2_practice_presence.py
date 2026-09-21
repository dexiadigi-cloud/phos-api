#!/usr/bin/env python3
"""Deterministic verification for the Practice of the Presence of God batch.

Seed 20260920. Independently re-derives the expected rows from the raw
Gutenberg file (line-based split, own code, no import of the ingest
script) and compares character-for-character against the staged rows in
data/staging/practice_presence.db for a seeded random sample of at
least 15 sections (16 taken), plus a full 20/20 exact comparison.

Writes data/staging/practice_presence-VERIFY.md. Stdlib + sqlite3 only.
"""

import os
import random
import sqlite3

SEED = 20260920
N_SAMPLE = 16

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_FILE = os.path.join(
    ROOT, "data", "raw_v2", "practice_presence", "pg13871.txt")
DB_PATH = os.path.join(ROOT, "data", "staging", "practice_presence.db")
VERIFY_PATH = os.path.join(
    ROOT, "data", "staging", "practice_presence-VERIFY.md")

ORD_WORDS = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH",
             "SEVENTH", "EIGHTH", "NINTH", "TENTH", "ELEVENTH", "TWELFTH",
             "THIRTEENTH", "FOURTEENTH", "FIFTEENTH"]
ORD_TITLES = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth",
              "Seventh", "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth",
              "Thirteenth", "Fourteenth", "Fifteenth"]

EXPECTED_TITLES = (
    ["Preface"]
    + [w.capitalize() + " Conversation" for w in ORD_WORDS[:4]]
    + [w + " Letter" for w in ORD_TITLES]
)


def derive_expected():
    """Independent re-derivation from raw: line-based, no regex marks."""
    lines = open(RAW_FILE, encoding="utf-8").read().replace("\r\n", "\n")
    lines = lines.split("\n")
    headings = (["PREFACE."]
                + [w + " CONVERSATION." for w in ORD_WORDS[:4]]
                + [w + " LETTER." for w in ORD_WORDS])
    assert len(headings) == 20
    # Division headings are boundaries too (they belong to no section and
    # are excluded from every body, per the documented parse contract).
    div_after = {"PREFACE.": "CONVERSATIONS.",
                 "FOURTH CONVERSATION.": "LETTERS."}
    pos = []
    for h in headings:
        hits = [i for i, l in enumerate(lines) if l == h]
        assert len(hits) == 1, "heading %r found %d times" % (h, len(hits))
        pos.append(hits[0])
    assert pos == sorted(pos), "headings out of order"
    div_pos = {}
    for sec, div in div_after.items():
        hits = [i for i, l in enumerate(lines) if l == div]
        assert len(hits) == 1, "division %r found %d times" % (div, len(hits))
        div_pos[sec] = hits[0]
    end_hits = [i for i, l in enumerate(lines)
                if l.startswith("*** END OF")]
    assert len(end_hits) == 1
    end_line = end_hits[0]
    assert end_line > pos[-1]

    expected = []
    for day, (h, start) in enumerate(zip(headings, pos), start=1):
        if h in div_pos:
            stop = div_pos[h]
        elif day < 20:
            stop = pos[day]  # day is 1-based; next section heading
        else:
            stop = end_line
        chunk = "\n".join(lines[start + 1:stop]).strip()
        assert chunk, "empty chunk for %s" % h
        expected.append({"day": day, "title": EXPECTED_TITLES[day - 1],
                         "body": chunk})
    return expected


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n if len(a) != len(b) else -1


def main():
    expected = derive_expected()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    db_rows = {r["day"]: dict(r) for r in con.execute(
        "SELECT id, source_id, day, part, title, anchor_ref, body"
        " FROM devotionals")}
    con.close()

    checks = []
    total_ok = True

    # 1. Row count and day sequence.
    n = len(db_rows)
    ok = (n == 20 and sorted(db_rows) == list(range(1, 21)))
    checks.append(("row count = 20 and days = 1..20 with no gaps", ok,
                   "rows=%d days=%s" % (n, sorted(db_rows))))
    total_ok &= ok

    # 2. part / anchor_ref / source_id uniformity.
    for day, r in sorted(db_rows.items()):
        for field, want in (("source_id", "practice_presence"),
                            ("part", "morning"), ("anchor_ref", "")):
            ok = r[field] == want
            if not ok:
                checks.append(("day %d %s == %r" % (day, field, want), False,
                               "got %r" % r[field]))
                total_ok = False

    # 3. Seeded sample: char-for-char raw -> parser output -> staging DB.
    rng = random.Random(SEED)
    order = list(range(1, 21))
    rng.shuffle(order)
    sample = sorted(order[:N_SAMPLE])
    sample_results = []
    for day in sample:
        exp = expected[day - 1]
        got = db_rows.get(day)
        if got is None:
            sample_results.append((day, False, "day missing from DB"))
            total_ok = False
            continue
        problems = []
        if got["title"] != exp["title"]:
            problems.append("title: %r vs %r" % (got["title"], exp["title"]))
        if got["body"] != exp["body"]:
            i = first_diff(got["body"], exp["body"])
            problems.append(
                "body: len %d vs %d, first diff at char %d"
                % (len(got["body"]), len(exp["body"]), i))
        if problems:
            sample_results.append((day, False, "; ".join(problems)))
            total_ok = False
        else:
            sample_results.append(
                (day, True,
                 "title=%r body_len=%d exact match"
                 % (got["title"], len(got["body"]))))
    checks.append(("seeded sample %d/20 sections exact (seed %d)"
                   % (N_SAMPLE, SEED),
                   all(r[1] for r in sample_results),
                   "%d/%d passed" % (sum(r[1] for r in sample_results),
                                     len(sample_results))))

    # 4. Full 20/20 exact comparison (title, body) independent of sampling.
    full_bad = [d for d in range(1, 21)
                if db_rows[d]["title"] != expected[d - 1]["title"]
                or db_rows[d]["body"] != expected[d - 1]["body"]]
    checks.append(("full 20/20 title+body exact match", not full_bad,
                   "mismatched days: %s" % full_bad if full_bad else "20/20"))

    # 5. sources row.
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    src = con.execute("SELECT * FROM sources").fetchall()
    con.close()
    ok = (len(src) == 1 and src[0]["source_id"] == "practice_presence"
          and src[0]["kind"] == "devotional"
          and src[0]["title"] ==
          "Brother Lawrence, The Practice of the Presence of God"
          and src[0]["rights"] == "Public Domain"
          and src[0]["rights_basis"] and src[0]["version"]
          and len(src[0]["sha256"]) == 64)
    checks.append(("sources row present and well-formed", ok,
                   "rows=%d" % len(src)))
    total_ok &= ok

    # 6. DB integrity.
    con = sqlite3.connect(DB_PATH)
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    checks.append(("PRAGMA integrity_check", integ == "ok", integ))
    total_ok &= (integ == "ok")

    with open(VERIFY_PATH, "w", encoding="utf-8") as f:
        f.write("# Verification: practice_presence batch\n\n")
        f.write("Seed: %d. Raw file re-parsed independently (line-based split,\n"
                "no ingest-script code) and compared character-for-character\n"
                "against the staged rows in data/staging/practice_presence.db.\n\n"
                % SEED)
        f.write("## Sampled sections (seeded random, %d of 20)\n\n" % N_SAMPLE)
        f.write("Sampled days: %s\n\n" % sample)
        for day, ok, detail in sample_results:
            f.write("- day %2d: %s - %s\n" % (day, "PASS" if ok else "FAIL",
                                              detail))
        f.write("\n## All checks\n\n")
        for name, ok, detail in checks:
            f.write("- %s: %s (%s)\n" % ("PASS" if ok else "FAIL", name,
                                         detail))
        f.write("\n## Totals\n\n")
        f.write("- devotionals rows staged: %d\n" % n)
        f.write("- sources rows staged: %d\n" % len(src))
        f.write("- OVERALL: %s\n" % ("PASS" if total_ok else "FAIL"))

    print("seeded sample: %d/%d PASS (seed %d)"
          % (sum(r[1] for r in sample_results), len(sample_results), SEED))
    for name, ok, detail in checks:
        print(("PASS" if ok else "FAIL"), "-", name, "-", detail)
    print("wrote", VERIFY_PATH)
    print("OVERALL:", "PASS" if total_ok else "FAIL")
    if not total_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
