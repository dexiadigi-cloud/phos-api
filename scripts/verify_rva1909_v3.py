#!/usr/bin/env python3
"""Deterministic verification for the RVA1909 v3 ingest (seed 20260920).

For each sampled verse key: extract the raw `\\v` line from the source USFM,
clean it with an INDEPENDENT re-implementation, and compare
character-for-character: raw-source(cleaned) == parser-output == staging-DB.

Writes data/staging/rva1909-VERIFY.md.

Note: the source carries 18 empty `\\v` placeholders (Spanish versification
offsets/merges, documented in verification/v2/rva1909-ingest-report.md);
the parser drops empties, so the sampled key universe is the 31,084
text-bearing verses only.
"""
import random
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_rva1909_v3 import (  # noqa: E402
    BOOKS, BOOK_ID2NAME, BOOK_ORDER, RAW, STAGING, parse_book,
)

# --- Independent cleaning (re-implemented, not reusing the parser's cleaner) ---
def clean_raw(body: str) -> str:
    t = body
    t = re.sub(r"\\f\b.*?\\f\*", " ", t, flags=re.S)
    t = re.sub(r"\\x\b.*?\\x\*", " ", t, flags=re.S)
    t = re.sub(r'\|strong="[^"]*"', "", t)
    t = re.sub(r"\\\+[a-zA-Z]+\*?", "", t)
    t = re.sub(r"\\[a-zA-Z]+\d*\*?", "", t)
    t = t.replace("¶", " ").replace("|", " ")
    return re.sub(r"\s+", " ", t).strip()


V_LINE_RE = re.compile(r"^\\v\s+(\S+)\s?(.*)$")
ID2FILE = {bid: sorted(RAW.glob(f"*-{bid}spaRV1909.usfm"))[0] for bid, _ in BOOKS}


# Structural marker prefixes carrying no verse text (mirrors the parser's
# accumulation rule: these lines are skipped, all other lines join the verse).
_STRUCT_SKIP = ("\\s", "\\r", "\\d", "\\qa", "\\ms", "\\mr", "\\mi",
                "\\cl", "\\cp", "\\cd", "\\mt", "\\imt", "\\h", "\\toc",
                "\\id", "\\ide", "\\usfm", "\\rem", "\\sts", "\\ip",
                "\\ipi", "\\im", "\\ib", "\\iot", "\\io1", "\\io2",
                "\\io3", "\\ili", "\\is", "\\iq")


def raw_body(book_id: str, chapter: int, verse: int) -> str:
    """Return the raw `\\v N` line plus its continuation lines, straight from
    the file (verses in this edition often span several `\\q` lines)."""
    path = ID2FILE[book_id]
    cur_ch = None
    buf = None
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        s = line.strip()
        m = re.match(r"^\\c\s+(\d+)", s)
        if m:
            if buf is not None:
                break
            cur_ch = int(m.group(1))
            continue
        m = V_LINE_RE.match(s)
        if m:
            if buf is not None:
                break
            if cur_ch == chapter and m.group(1).isdigit() and int(m.group(1)) == verse:
                buf = [m.group(2)]
            continue
        if buf is not None:
            if s.startswith(_STRUCT_SKIP):
                continue
            buf.append(s)
    if buf is None:
        raise KeyError(f"raw line not found: {book_id} {chapter}:{verse}")
    return " ".join(buf)


def main():
    # Parser output (all books).
    parsed = {}
    for book_id, _name in BOOKS:
        _bid, verses, _empty = parse_book(ID2FILE[book_id])
        for name, _o, ch, v, text in verses:
            parsed[(name, ch, v)] = text
    book_id_of = {v: k for k, v in BOOK_ID2NAME.items()}

    con = sqlite3.connect(f"file:{STAGING}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    db_rows = {
        (r["book"], r["chapter"], r["verse"]): r["text"]
        for r in con.execute("SELECT book, chapter, verse, text FROM verses")
    }
    db_orders = {
        r["book"]: r["book_order"]
        for r in con.execute("SELECT DISTINCT book, book_order FROM verses")
    }
    con.close()

    keys = sorted(parsed.keys(), key=lambda k: (BOOK_ORDER[k[0]], k[1], k[2]))
    rng = random.Random(20260920)
    samples = rng.sample(keys, 50)
    anchors = [("Genesis", 1, 1), ("John", 3, 16), ("Psalms", 23, 1),
               ("Malachi", 4, 6), ("Revelation", 22, 21)]

    lines = ["# RVA1909 ingest verification (seed 20260920)",
             "",
             "Three-way character-for-character comparison per verse key:",
             "raw USFM `\\\\v` line (independently cleaned) == parser output ==",
             "staging DB text.",
             "",
             "## Mandatory anchors", ""]
    fails = 0
    total = 0

    def check(key):
        nonlocal fails, total
        total += 1
        name, ch, v = key
        bid = book_id_of[name]
        try:
            raw = clean_raw(raw_body(bid, ch, v))
        except KeyError:
            fails += 1
            return f"- {name} {ch}:{v}: FAIL (raw line not found)"
        ptxt, dtxt = parsed[key], db_rows.get(key)
        if raw == ptxt == dtxt and dtxt:
            return f"- {name} {ch}:{v}: PASS ({len(dtxt)} chars)"
        fails += 1
        detail = [f"- {name} {ch}:{v}: FAIL"]
        if raw != ptxt:
            detail.append(f"  raw-vs-parser: {raw[:70]!r} != {ptxt[:70]!r}")
        if ptxt != dtxt:
            detail.append(f"  parser-vs-db:  {ptxt[:70]!r} != {str(dtxt)[:70]!r}")
        if not dtxt:
            detail.append("  (missing from staging DB)")
        return "\n".join(detail)

    for a in anchors:
        lines.append(check(a))
    lines += ["", "## Seeded random samples (50)", ""]
    for s in samples:
        lines.append(check(s))

    # Structural audits.
    dup = len(parsed) - len(db_rows)
    nbooks = len({k[0] for k in db_rows})
    order_ok = all(BOOK_ORDER[name] == o for name, o in db_orders.items())
    lines += ["", "## Structural audits", "",
              f"- total rows staged: {len(db_rows)}",
              f"- distinct verse keys: {len(parsed)} (dupes in DB: {dup})",
              f"- books present: {nbooks} (expected 66)",
              f"- book_order matches canonical table: {order_ok}",
              "",
              f"## Result: {total - fails}/{total} three-way checks passed",
              "FAIL" if fails else "ALL PASS"]

    out = STAGING.parent / "rva1909-VERIFY.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out}: {total - fails}/{total} passed")


if __name__ == "__main__":
    main()
