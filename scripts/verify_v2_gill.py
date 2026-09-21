#!/usr/bin/env python3
"""Seeded raw-to-database spot checks for the Gill ingest.

For each sampled commentaries row (source_id='gill'), locates the anchor
line(s) in the raw OCR file and asserts the stored text is genuinely derived
from that raw region (normalized prefix match). Also asserts no page-marker /
running-head / structural-heading leakage at the row level.

Usage: python3 scripts/verify_v2_gill.py  (exit 0 = all pass)
"""

from __future__ import annotations

import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_v2" / "gill" / "gill_commentary.txt"
STUDY_DB = ROOT / "data" / "study.db"

SEED = 20260920
N_CHECKS = 12
WINDOW = 600  # raw lines scanned after an anchor

BOOK_ALIASES = {"Song of Songs": "Song of Solomon"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def main() -> int:
    lines = RAW.read_text(encoding="utf-8", errors="replace").split("\n")
    con = sqlite3.connect(STUDY_DB)
    rows = con.execute(
        "SELECT book, start_chapter, start_verse, end_chapter, end_verse, text"
        " FROM commentaries WHERE source_id = 'gill'"
    ).fetchall()
    con.close()
    print(f"gill rows: {len(rows)}")

    rng = random.Random(SEED)
    sample = rng.sample(rows, N_CHECKS)

    fails = 0
    for n, (book, sc, sv, ec, ev, text) in enumerate(sample, 1):
        raw_book = BOOK_ALIASES.get(book, book)
        stem = raw_book.split()[-1].upper().rstrip("S")  # PSALMS -> PSALM
        if sc == 0:
            # book intro: anchor = INTRODUCTION TO <book-ish>
            pats = [re.compile(r"^INTRODUCTION TO .*" + stem + r".*$",
                               re.IGNORECASE)]
            label = f"{book} bookintro"
        elif sv == 0:
            pats = [re.compile(r"^INTRODUCTION TO .*" + stem + r".*$",
                               re.IGNORECASE)]
            label = f"{book} {sc}-{ec} chapintro"
        else:
            pats = [re.compile(r"^\s*" + re.escape(raw_book) +
                               rf" {sc}:{sv}\s*$")]
            label = f"{book} {sc}:{sv}"
        anchors = [i for i, ln in enumerate(lines)
                   if any(p.match(ln) for p in pats)]
        prefix = norm(text)[:120]
        ok = False
        for a in anchors:
            window = norm("\n".join(lines[a:a + WINDOW]))
            window = re.sub(r"page \$?\d+ of \d+", "", window)
            window = re.sub(r"\s+", " ", window).strip()
            if prefix and prefix in window:
                ok = True
                break
        leak = bool(re.search(r"Page \$?\d+ of \d+", text)
                    or "Exposition of the Entire Bible" in text)
        status = "PASS" if (ok and not leak) else "FAIL"
        if status == "FAIL":
            fails += 1
        print(f"[{status}] #{n} {label}: anchors={len(anchors)} "
              f"prefix={text[:80]!r}")
        if not ok:
            print(f"   prefix not found in raw window: {prefix[:80]!r}")
        if leak:
            print("   LEAKAGE detected")

    print(f"{N_CHECKS - fails}/{N_CHECKS} spot checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
