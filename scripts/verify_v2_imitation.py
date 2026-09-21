#!/usr/bin/env python3
"""Deterministic verification for the Imitation of Christ staging ingest.

Seed 20260920. Independently re-derives chapter titles, bodies, and days
from data/raw_v2/imitation_christ/1653-0.txt (own code path, not the parser)
and compares character-for-character against data/staging/imitation_christ.db.
Writes data/staging/imitation_christ-VERIFY.md with per-sample pass/fail.
"""

import hashlib
import os
import random
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_FILE = os.path.join(ROOT, "data", "raw_v2", "imitation_christ", "1653-0.txt")
STAGING_DB = os.path.join(ROOT, "data", "staging", "imitation_christ.db")
OUT = os.path.join(ROOT, "data", "staging", "imitation_christ-VERIFY.md")

SEED = 20260920
SAMPLE_SIZE = 20

RV = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def rn(s):
    t = p = 0
    for c in reversed(s):
        v = RV[c]
        if v < p:
            t -= v
        else:
            t += v
            p = v
    return t


def independent_parse(path):
    """Independent line-based re-derivation from the raw file."""
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    start = text.index("*** START OF THE PROJECT GUTENBERG EBOOK")
    end = text.index("*** END OF THE PROJECT GUTENBERG EBOOK")
    body = text[start:end]
    books = re.split(r"(?m)^(THE FIRST BOOK|THE SECOND BOOK|THE THIRD BOOK|THE FOURTH BOOK)$", body)
    # books[0] = preamble, then alternating (marker, segment).
    derived = []
    book_no = 0
    for i in range(1, len(books), 2):
        book_no += 1
        seg = books[i + 1]
        parts = re.split(r"(?m)^CHAPTER ([IVXLCDM]+)$", seg)
        # parts[0] = book preamble, then alternating (roman, chapter-text).
        ch_no = 0
        for j in range(1, len(parts), 2):
            ch_no += 1
            assert rn(parts[j]) == ch_no, (book_no, parts[j], ch_no)
            ctext = parts[j + 1]
            clines = ctext.split("\n")
            k = 0
            while k < len(clines) and clines[k].strip() == "":
                k += 1
            tlines = []
            while k < len(clines) and clines[k].strip() != "":
                tlines.append(clines[k].strip())
                k += 1
            while k < len(clines) and clines[k].strip() == "":
                k += 1
            blines = clines[k:]
            while blines and blines[-1].strip() == "":
                blines.pop()
            title = " ".join(tlines)
            btext = "\n".join(blines)
            derived.append({
                "day": len(derived) + 1,
                "book": book_no,
                "ch": ch_no,
                "title": "Book %d, Chapter %d: %s" % (book_no, ch_no, title),
                "body": btext,
            })
    assert book_no == 4, book_no
    return derived


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    derived = independent_parse(RAW_FILE)
    total = len(derived)
    assert total == 114, total

    con = sqlite3.connect(STAGING_DB)
    cur = con.cursor()
    n = cur.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    db_days = [r[0] for r in cur.execute("SELECT day FROM devotionals ORDER BY day")]
    src = cur.execute(
        "SELECT source_id, kind, title, rights, rights_basis, version, sha256"
        " FROM sources").fetchall()
    db_rows = {r[0]: r for r in cur.execute(
        "SELECT day, source_id, part, title, anchor_ref, body FROM devotionals")}
    con.close()

    lines = []
    lines.append("# Verification: Imitation of Christ staging ingest")
    lines.append("")
    lines.append("Method: seed `20260920`, `random.Random(20260920).sample(range(1,115), 20)`;")
    lines.append("each sampled chapter re-derived independently from the raw file and")
    lines.append("compared character-for-character (title, body, day) against the staging DB.")
    lines.append("")

    results = []
    results.append(("total row count == 114", n == 114, "n=%d" % n))
    results.append(("independent parse count == 114", total == 114, "n=%d" % total))
    results.append(("days are exactly 1..114", db_days == list(range(1, 115)),
                    "min=%s max=%s" % (db_days[0] if db_days else None, db_days[-1] if db_days else None)))
    results.append(("one sources row", len(src) == 1, "rows=%d" % len(src)))
    if src:
        s = src[0]
        results.append(("sources.source_id == imitation_christ", s[0] == "imitation_christ", s[0]))
        results.append(("sources.kind == devotional", s[1] == "devotional", s[1]))
        results.append(("sources.rights == Public Domain", s[3] == "Public Domain", s[3]))
        results.append(("sources.sha256 matches raw file", s[6] == sha256_of(RAW_FILE), (s[6] or "")[:16] + "..."))

    rng = random.Random(SEED)
    sample = rng.sample(range(1, 115), SAMPLE_SIZE)
    lines.append("## Seed")
    lines.append("")
    lines.append("Seed: %d. Sampled days (in sample order): %s" % (SEED, sample))
    lines.append("")
    lines.append("## Per-sample results (day, title, body, day all character-for-character)")
    lines.append("")
    passes = fails = 0
    for day in sample:
        d = derived[day - 1]
        row = db_rows.get(day)
        ok = True
        notes = []
        if row is None:
            ok = False
            notes.append("missing row in DB")
        else:
            _, sid, part, title, anchor, body = row
            if sid != "imitation_christ":
                ok = False
                notes.append("source_id mismatch")
            if part != "morning":
                ok = False
                notes.append("part mismatch")
            if anchor != "":
                ok = False
                notes.append("anchor_ref not empty")
            if title != d["title"]:
                ok = False
                notes.append("title mismatch")
            if body != d["body"]:
                ok = False
                notes.append("body mismatch")
            if day != d["day"]:
                ok = False
                notes.append("day mismatch")
        if ok:
            passes += 1
            status = "PASS"
        else:
            fails += 1
            status = "FAIL (%s)" % "; ".join(notes)
        lines.append("- day %d: %s ... %s" % (day, status, d["title"][:72]))
        results.append(("sample day %d char-for-char" % day, ok, "; ".join(notes) or "ok"))

    lines.append("")
    lines.append("## Global checks")
    lines.append("")
    for name, ok, note in results:
        if name.startswith("sample day"):
            continue
        lines.append("- %s: %s (%s)" % ("PASS" if ok else "FAIL", name, note))
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("Samples: %d passed, %d failed (of %d sampled, seed %d)."
                 % (passes, fails, SAMPLE_SIZE, SEED))
    lines.append("Total rows in staging devotionals table: %d." % n)
    all_ok = all(ok for _, ok, _ in results)
    lines.append("Overall: %s." % ("PASS" if all_ok else "FAIL"))
    lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    print("wrote %s" % OUT)
    assert all_ok, "verification failures present"


if __name__ == "__main__":
    main()
