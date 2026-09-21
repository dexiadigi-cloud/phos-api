#!/usr/bin/env python3
"""Independent verification for V2 devotional staging.

Re-derives expected DB values from the raw sources with code written
independently of scripts/ingest_v2_devotionals.py, then compares exactly
against staging/devotionals.db.

Checks:
  1. Seeded raw-to-DB exact comparisons (>=10 per source, seed 20260920).
  2. Row counts, date/part coverage incl. Feb 29, per source.
  3. Anchor refs re-parsed via api/parser.py against KJV bounds.
  4. Leak checks (HTML tags / entities / USFM markers).
  5. PRAGMA integrity_check.

Writes evidence to verification/v2/raw/devotionals/spot_checks.json.
Exit non-zero on any failure.
"""

import json
import os
import random
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "api"))
import db as phos_db
import parser as phos_parser

SEED = 20260920
N_SPOT = 12
RAW = os.path.join(ROOT, "data", "raw_v2")
DB_PATH = os.path.join(ROOT, "staging", "devotionals.db")
EVID_DIR = os.path.join(ROOT, "verification", "v2", "raw", "devotionals")

MONTH_LEN = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTHS = ["january", "february", "march", "april", "may", "june",
          "july", "august", "september", "october", "november", "december"]

failures = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (" - " + detail if detail and not cond else ""))
    if not cond:
        failures.append(name + (" " + detail if detail else ""))


# ---------------- independent Spurgeon re-derivation ----------------

def spur_fix_text(s):
    # mojibake layer: U+00E2 + C1 bytes = UTF-8 for curly quotes
    s = re.sub("\u00e2[\u0080-\u009f]+",
               lambda m: m.group(0).encode("latin-1").decode("utf-8"), s)
    # C1 layer: Windows-1252 punctuation misdecoded as Latin-1
    win1252 = {"\u0092": "\u2019", "\u0093": "\u201c", "\u0094": "\u201d",
               "\u0096": "\u2013", "\u0097": "\u2014"}
    s = re.sub("[\u0080-\u009f]", lambda m: win1252[m.group(0)], s)
    return s.replace("\u00a0", " ")


def spur_expected(rec):
    kv = spur_fix_text(rec["keyverse"])
    verse_text, ref = kv.rsplit("\u2014", 1)
    verse_text, ref = verse_text.strip(), ref.strip()
    if verse_text[:1] == '"' and verse_text[-1:] == '"':
        verse_text = verse_text[1:-1]
    body = spur_fix_text(rec["body"]).replace("\r\n", "\n")
    lines = body.split("\n")
    assert re.match(r"^[A-Za-z]+ \d+", lines[0]) and "Reading" in lines[0]
    assert lines[1].strip() == kv.strip()
    prose = "\n".join(lines[2:]).strip("\n")
    paras = [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip()]
    return verse_text, ref, "\n\n".join(paras)


# ---------------- independent Daily Light re-derivation ----------------

def dl_expected(entry, recon_items):
    title = entry["themeVerse"]["text"]
    refs = [r["final_ref"] for r in recon_items]
    texts = [entry["themeVerse"]["text"]] + [v["text"] for v in entry["verses"]]
    return title, "; ".join(refs), "\n\n".join(texts)


# ---------------- main ----------------

def main():
    os.makedirs(EVID_DIR, exist_ok=True)
    bounds = phos_db.get_bounds("KJV")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # ---- structural checks ----
    total = con.execute("SELECT COUNT(*) FROM devotionals").fetchone()[0]
    check("total rows = 1464", total == 1464, "got %d" % total)
    for sid in ("spurgeon", "daily_light"):
        c = con.execute("SELECT COUNT(*) FROM devotionals WHERE source_id=?", (sid,)).fetchone()[0]
        check("%s rows = 732" % sid, c == 732, "got %d" % c)
        for part in ("morning", "evening"):
            days = {r[0] for r in con.execute(
                "SELECT day FROM devotionals WHERE source_id=? AND part=?", (sid, part))}
            check("%s %s covers days 1..366" % (sid, part), days == set(range(1, 367)),
                  "got %d days" % len(days))
        feb29 = con.execute(
            "SELECT COUNT(*) FROM devotionals WHERE source_id=? AND day=60", (sid,)).fetchone()[0]
        check("%s Feb 29 (day 60) present x2" % sid, feb29 == 2, "got %d" % feb29)

    # ---- anchor re-parse + leak checks over all rows ----
    tag_re = re.compile(r"<[a-zA-Z/!][^>]*>")
    ent_re = re.compile(r"&(#[0-9]+|#x[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]+);")
    usfm_re = re.compile(r"\\(id|h|toc|c|v|s|p|q|m|d|f|fr|ft|fk|x|w|k-s)\b")
    n_anchor_pieces = 0
    leaks = 0
    for r in con.execute("SELECT source_id, day, part, title, anchor_ref, body FROM devotionals"):
        for piece in r["anchor_ref"].split(";"):
            piece = piece.strip()
            try:
                phos_parser.parse_reference(piece, bounds)
                n_anchor_pieces += 1
            except Exception as exc:
                check("anchor parses", False,
                      "%s d%d %s: %r (%s)" % (r["source_id"], r["day"], r["part"], piece, exc))
        for field in ("title", "body"):
            t = r[field]
            if tag_re.search(t) or ent_re.search(t) or usfm_re.search(t):
                leaks += 1
    check("all anchor pieces parse (%d)" % n_anchor_pieces, n_anchor_pieces > 0)
    check("leak checks: 0 HTML/entity/USFM", leaks == 0, "%d leaks" % leaks)
    integ = con.execute("PRAGMA integrity_check").fetchone()[0]
    check("integrity_check ok", integ == "ok", integ)

    # ---- seeded spot checks ----
    spur_raw = [e for e in json.load(
        open(os.path.join(RAW, "spurgeon", "m_e.json"), encoding="utf-8")) if e]
    spur_by_key = {(e["month"], e["day"], e["time"]): e for e in spur_raw}
    dl_raw = json.load(open(os.path.join(RAW, "daily_light", "readings.json"), encoding="utf-8"))
    dl_by_key = {(e["date"], e["period"]): e for e in dl_raw}
    recon = json.load(open(os.path.join(RAW, "daily_light", "ref_reconciliation.json"), encoding="utf-8"))
    recon_by_entry = {}
    for r in recon:
        recon_by_entry.setdefault((r["date"], r["period"]), []).append(r)

    rng = random.Random(SEED)
    spur_keys = rng.sample(sorted(spur_by_key), N_SPOT)
    dl_keys = rng.sample(sorted(dl_by_key), N_SPOT)

    evidence = {"seed": SEED, "spot_checks": []}
    for (month, daynum, tod) in spur_keys:
        doy = sum(MONTH_LEN[:month - 1]) + daynum
        part = "morning" if tod == "am" else "evening"
        rec = spur_by_key[(month, daynum, tod)]
        exp_title, exp_ref, exp_body = spur_expected(rec)
        row = con.execute(
            "SELECT title, anchor_ref, body FROM devotionals WHERE source_id='spurgeon' AND day=? AND part=?",
            (doy, part)).fetchone()
        ok = (row["title"] == exp_title and row["anchor_ref"] == exp_ref and row["body"] == exp_body)
        check("spurgeon spot %d-%d %s" % (month, daynum, part), ok)
        evidence["spot_checks"].append({
            "source": "spurgeon", "day": doy, "part": part,
            "title_match": row["title"] == exp_title,
            "anchor_match": row["anchor_ref"] == exp_ref,
            "body_match": row["body"] == exp_body,
            "body_chars": len(exp_body)})

    for (date, period) in dl_keys:
        entry = dl_by_key[(date, period)]
        month = MONTHS.index(date.split("-")[0]) + 1
        doy = sum(MONTH_LEN[:month - 1]) + int(date.split("-")[1])
        exp_title, exp_ref, exp_body = dl_expected(entry, recon_by_entry[(date, period)])
        row = con.execute(
            "SELECT title, anchor_ref, body FROM devotionals WHERE source_id='daily_light' AND day=? AND part=?",
            (doy, period)).fetchone()
        ok = (row["title"] == exp_title and row["anchor_ref"] == exp_ref and row["body"] == exp_body)
        check("daily_light spot %s %s" % (date, period), ok)
        evidence["spot_checks"].append({
            "source": "daily_light", "day": doy, "part": period,
            "title_match": row["title"] == exp_title,
            "anchor_match": row["anchor_ref"] == exp_ref,
            "body_match": row["body"] == exp_body,
            "body_chars": len(exp_body)})

    ev_path = os.path.join(EVID_DIR, "spot_checks.json")
    json.dump(evidence, open(ev_path, "w", encoding="utf-8"), indent=1)
    print("evidence: %s" % ev_path)

    con.close()
    if failures:
        print("\n%d FAILURES:" % len(failures))
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nALL CHECKS PASSED")


if __name__ == "__main__":
    main()
