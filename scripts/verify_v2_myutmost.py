#!/usr/bin/env python3
"""Deterministic verification for the My Utmost for His Highest batch.

Seed 20260920. Two-stage character-for-character comparison for 30 seeded
readings:

  Stage A: raw source (independently re-derived with inline logic, no parser
           import) -> parser output (scripts/parse_v2_myutmost.build_rows).
  Stage B: parser output -> staging DB rows.

Fields compared per stage: day, title, anchor_ref, body.

Writes data/staging/my_utmost-VERIFY.md with per-sample pass/fail and
total row count.
"""
import html as html_module
import json
import os
import random
import re
import sqlite3
import sys

SEED = 20260920
N_SAMPLES = 30

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "api"))
import parse_v2_myutmost
import db as phos_db

RAW = os.path.join(ROOT, "data", "raw_v2", "my_utmost")
DB_PATH = os.path.join(ROOT, "data", "staging", "my_utmost.db")
OUT = os.path.join(ROOT, "data", "staging", "my_utmost-VERIFY.md")

MONTH_LEN = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
TAG_RE = re.compile(r"<[a-zA-Z/!][^>]*>")


def doy(month, day):
    return sum(MONTH_LEN[: month - 1]) + day


def clean_text(s):
    s = TAG_RE.sub("", s)
    s = html_module.unescape(s)
    s = s.replace("\u00a0", " ")
    return s


def content_paragraphs(content_html):
    chunks = re.split(r"</(?:p|h[1-6]|li|blockquote|div)>", content_html)
    paras = []
    for ch in chunks:
        t = re.sub(r"[ \t\r\f\v]+", " ", clean_text(ch)).strip(" \n")
        t = re.sub(r"\n+", " ", t).strip()
        if t and not re.fullmatch(r"[\s\u2014\u2013\-*]+", t):
            paras.append(t)
    return paras


def normalize_ref(raw_ref, bounds):
    # Independent copy of the parser's ref normalizations:
    # comma-list expansion + single-chapter bare-verse expansion.
    m = re.match(r"^(.+?)\s+(\d+):(\d+),\s*(\d+)$", raw_ref.strip())
    if m:
        book, ch, v1, v2 = m.group(1), m.group(2), m.group(3), m.group(4)
        raw_ref = "%s %s:%s; %s %s:%s" % (book, ch, v1, book, ch, v2)
    one_ch = {b for b, info in bounds.items() if info["chapters"] == 1}
    pieces = []
    for piece in (x.strip() for x in raw_ref.split(";")):
        m2 = re.match(r"^(.+?)\s+(\d+)$", piece)
        if m2 and ":" not in piece and m2.group(1) in one_ch:
            piece = "%s 1:%s" % (m2.group(1), m2.group(2))
        piece = piece.rstrip(".")  # site quirk: "Romans 14:7."
        pieces.append(piece)
    return "; ".join(pieces)


def expected_row(post, anchors, bounds):
    """Independent re-derivation of one row from the raw files."""
    slug = post["slug"]
    date = post["date"][:10]
    day = doy(int(date[5:7]), int(date[8:10]))
    title = re.sub(r"\s+", " ", clean_text(post["title"]["rendered"])).strip()
    a = anchors[slug]
    anchor_ref = normalize_ref(a["ref"], bounds)
    verse_para = '"%s" \u2014 %s' % (a["verse"], anchor_ref)
    if a["version"]:
        verse_para += " (%s)" % a["version"]
    if a.get("trail"):
        verse_para += " " + a["trail"]
    body = verse_para + "\n\n" + "\n\n".join(
        content_paragraphs(post["content"]["rendered"]))
    return {"day": day, "title": title, "anchor_ref": anchor_ref, "body": body,
            "slug": slug, "date": date}


FIELDS = ("day", "title", "anchor_ref", "body")


def main():
    posts = json.load(
        open(os.path.join(RAW, "utmost_classic_raw.json"), encoding="utf-8"))
    posts = [p for p in posts if p["slug"] != "today"]
    anchors = json.load(
        open(os.path.join(RAW, "anchor_verses.json"), encoding="utf-8"))
    bounds = phos_db.get_bounds("KJV")
    by_day = {}
    for p in posts:
        exp = expected_row(p, anchors, bounds)
        assert exp["day"] not in by_day, "duplicate day in raw"
        by_day[exp["day"]] = exp

    # Stage source: the parser's own output.
    parsed = parse_v2_myutmost.build_rows(bounds)
    parsed_by_day = {r["day"]: r for r in parsed}
    assert len(parsed) == 366 and len(parsed_by_day) == 366

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, source_id, day, part, title, anchor_ref, body"
        " FROM devotionals ORDER BY day").fetchall()
    total = len(rows)
    lines = []
    lines.append("# Verification: My Utmost for His Highest (seed 20260920)")
    lines.append("")
    lines.append("Staging DB: `data/staging/my_utmost.db`, table `devotionals`.")
    lines.append("Two stages per sample: A = raw -> parser output, "
                 "B = parser output -> staging DB.")
    lines.append("")

    fails = []
    # Structural checks.
    checks = []
    checks.append(("row count == 366", total == 366, total))
    days = [r["day"] for r in rows]
    checks.append(("days == 1..366 no gaps", days == list(range(1, 367)),
                   "%d days" % len(days)))
    checks.append(("all source_id == my_utmost",
                   all(r["source_id"] == "my_utmost" for r in rows), None))
    checks.append(("all part == morning",
                   all(r["part"] == "morning" for r in rows), None))
    checks.append(("no empty anchor_ref",
                   all(r["anchor_ref"] and r["anchor_ref"].strip() for r in rows),
                   None))
    checks.append(("no empty title",
                   all(r["title"] and r["title"].strip() for r in rows), None))
    checks.append(("no empty body",
                   all(r["body"] and r["body"].strip() for r in rows), None))
    for name, ok, detail in checks:
        if not ok:
            fails.append(name)
        lines.append("- %s %s%s" % ("PASS" if ok else "FAIL", name,
                                    " (%s)" % detail if detail else ""))
    lines.append("")

    # Seeded two-stage character-for-character comparison.
    rng = random.Random(SEED)
    sample_days = sorted(rng.sample(range(1, 367), N_SAMPLES))
    lines.append("## Seeded samples (n=%d)" % N_SAMPLES)
    lines.append("")
    lines.append("| day | date | slug | stage | day | title | anchor_ref | body |")
    lines.append("|---|---|---|---|---|---|---|---|")
    npass_a = npass_b = 0
    for day in sample_days:
        exp = by_day[day]
        prow = parsed_by_day[day]
        drow = rows[day - 1]  # days are 1..366 in order
        got_db = {"day": drow["day"], "title": drow["title"],
                  "anchor_ref": drow["anchor_ref"], "body": drow["body"]}
        for stage, left, right in (("A", exp, prow), ("B", prow, got_db)):
            res = {}
            for f in FIELDS:
                res[f] = "PASS" if left[f] == right[f] else "FAIL"
            ok = all(v == "PASS" for v in res.values())
            if stage == "A":
                npass_a += ok
            else:
                npass_b += ok
            if not ok:
                fails.append("sample day %d stage %s: %s" % (
                    day, stage,
                    {k: v for k, v in res.items() if v == "FAIL"}))
            lines.append("| %d | %s | %s | %s | %s | %s | %s | %s |" % (
                day, exp["date"], exp["slug"][:30], stage,
                res["day"], res["title"], res["anchor_ref"], res["body"]))
    lines.append("")
    lines.append("Stage A (raw -> parser) passed: %d/%d" % (npass_a, N_SAMPLES))
    lines.append("Stage B (parser -> DB) passed: %d/%d" % (npass_b, N_SAMPLES))
    lines.append("")
    verdict = "PASS" if not fails else "FAIL"
    lines.append("## Verdict: %s" % verdict)
    if fails:
        lines.append("")
        lines.append("Failures:")
        for f in fails:
            lines.append("- %s" % f)
    lines.append("")

    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("wrote %s" % OUT)
    print("row count:", total)
    print("stage A passed: %d/%d" % (npass_a, N_SAMPLES))
    print("stage B passed: %d/%d" % (npass_b, N_SAMPLES))
    print("verdict:", verdict)
    if fails:
        raise SystemExit("VERIFICATION FAILED")


if __name__ == "__main__":
    main()
