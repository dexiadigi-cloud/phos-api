#!/usr/bin/env python3
"""v3 verification for ALMEIDA: deterministic three-way check.

Leg A (raw, independent): extract the verse literal for a sampled row id
  straight from data/raw_v2/almeida/pt_nar.sql with an independent regex
  and an independent MySQL-unescape implementation.
Leg B (parser): the ingest module's own ROW_RE + unescape_mysql
  (imported from scripts/ingest_almeida_v3.py).
Leg C (staging): the text stored in data/staging/almeida.db.

5 mandatory anchors + 50 seeded samples (seed 20260920): 55/55 must pass.
Writes data/staging/almeida-VERIFY.md.

Usage: python3 scripts/verify_almeida_v3.py
"""
import random
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest_almeida_v3 as parser  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "almeida" / "pt_nar.sql"
STAGING = ROOT / "data" / "staging" / "almeida.db"
REPORT = ROOT / "data" / "staging" / "almeida-VERIFY.md"

ANCHORS = [
    (1, "Genesis", 1, 1),
    (10972, "Psalms", 23, 1),
    (23084, "Matthew", 6, 33),
    (26084, "John", 3, 16),   # id computed: verify via lookup below
    (28191, "Romans", 8, 28),
]


def independent_extract(sql: str, row_id: int) -> tuple:
    """Leg A: find the tuple by id with an independent pattern, unescape
    with an independent implementation."""
    m = re.search(r"\(" + str(row_id) + r",\s*(\d+),\s*(\d+),\s*(\d+),\s*"
                  r"('(?:[^'\\]|\\.|'')*')\)", sql)
    if not m:
        raise ValueError(f"id {row_id} not found in raw SQL")
    book_id, ch, vs, lit = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)
    body = lit[1:-1]
    out = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            out.append({"n": "\n", "r": "\r", "t": "\t"}.get(nxt, nxt))
            i += 2
        elif c == "'" and i + 1 < len(body) and body[i + 1] == "'":
            out.append("'")
            i += 2
        else:
            out.append(c)
            i += 1
    text = re.sub(r"\s+", " ", "".join(out)).strip()
    return parser.BOOKS[book_id - 1], ch, vs, text


def main() -> int:
    sql = RAW.read_text(encoding="utf-8", errors="replace")
    # Leg B: build the parser's full row map once.
    pmap = {}
    for _id, book_id, ch, vs, lit in parser.ROW_RE.findall(sql):
        b = parser.BOOKS[int(book_id) - 1]
        pmap[int(_id)] = (b, int(ch), int(vs), parser.unescape_mysql(lit))
    con = sqlite3.connect(STAGING)
    # Resolve anchor ids by (book, chapter, verse) from staging.
    anchor_ids = []
    for _hint, book, ch, vs in ANCHORS:
        rid = con.execute(
            "SELECT rowid FROM verses WHERE book=? AND chapter=? AND verse=?",
            (book, ch, vs)).fetchone()
        if not rid:
            print(f"ERROR: anchor {book} {ch}:{vs} missing in staging",
                  file=sys.stderr)
            return 1
        anchor_ids.append(rid[0])
    rng = random.Random(20260920)
    sample_ids = anchor_ids + rng.sample(range(1, 31103), 50)
    fails = []
    lines = []
    for rid in sample_ids:
        a = independent_extract(sql, rid)          # leg A
        b = pmap[rid]                              # leg B
        c = con.execute(
            "SELECT book, chapter, verse, text FROM verses WHERE rowid=?",
            (rid,)).fetchone()                     # leg C
        ok = (a == b == tuple(c))
        lines.append(f"{'PASS' if ok else 'FAIL'} id={rid} "
                     f"{a[0]} {a[1]}:{a[2]}")
        if not ok:
            fails.append(rid)
            lines.append(f"  A={a[3][:100]!r}")
            lines.append(f"  B={b[3][:100]!r}")
            lines.append(f"  C={c[3][:100]!r}")
    con.close()
    REPORT.write_text(
        "# ALMEIDA verification (2026-09-20)\n\n"
        f"Three-way check (raw SQL / parser / staging DB), seed 20260920: "
        f"{55 - len(fails)}/55 pass.\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8")
    print(f"{55 - len(fails)}/55 pass; report: {REPORT}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
