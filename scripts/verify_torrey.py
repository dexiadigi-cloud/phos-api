#!/usr/bin/env python3
"""Independent seeded verification for the Torrey staging db.

Re-extracts selected entries straight from the raw HTML with code written
independently of scripts/parse_torrey.py (manual tag scanner, no shared
functions), applies the same documented normalization rules, and compares
character-for-character against data/staging/dict_torrey.db.

Seeded terms: Faith, Prayer, Salvation, Love of God, The (Torrey has no
standalone 'Love' topic; the five Love-* topics were listed) plus two
entries chosen deterministically with random.Random(20260920).
"""
import glob
import html
import os
import random
import re
import sqlite3

RAW_DIR = os.path.expanduser("~/workspace/scripture-desk/data/raw_v2/torrey")
DB = os.path.expanduser("~/workspace/scripture-desk/data/staging/dict_torrey.db")
BULLET = "\u2022"

def strip_tags_scanner(seg: str) -> str:
    """Hand-rolled scanner: converts structural tags to line breaks/bullets,
    drops the centered title heading and page markers, strips everything else."""
    seg = re.sub(r"<P><FONT SIZE=\+1>.*?</FONT></P>", "", seg, flags=re.S | re.I)
    seg = re.sub(r"<P>\[NTT [^\]]*\]</P>", "", seg, flags=re.I)
    out = []
    i, n = 0, len(seg)
    while i < n:
        if seg[i] == "<":
            j = seg.find(">", i + 1)
            if j == -1:
                out.append(seg[i:])
                break
            tag = seg[i + 1:j].strip()
            closing = tag.startswith("/")
            name = (tag[1:] if closing else tag).split()[0].upper() if tag.lstrip("/") else ""
            if not closing and name == "LI":
                out.append("\n" + BULLET + " ")
            elif name in ("BR", "P", "UL", "HR"):
                out.append("\n")
            # all other tags (FONT, A, CENTER, B, I, comments, ...) vanish
            i = j + 1
        else:
            out.append(seg[i])
            i += 1
    text = html.unescape("".join(out))
    lines = []
    for raw in text.split("\n"):
        line = re.sub(r"[ \t\xa0]+", " ", raw).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)

def extract(term: str) -> str:
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "NTT-[A-Z].HTM"))):
        with open(path, encoding="ascii") as fh:
            doc = fh.read()
        m = re.search(r'<LI><A HREF="NTT-[A-Z]\.HTM#Topic(\d+)">' + re.escape(term) + r"</A>", doc)
        if not m:
            continue
        num = m.group(1)
        start = doc.index(f'<A NAME="Topic{num}">')
        nxt = doc.find('<A NAME="Topic', start + 1)
        seg = doc[start:nxt if nxt != -1 else len(doc)]
        return strip_tags_scanner(seg)
    raise KeyError(f"term not found in raw files: {term}")

def main() -> None:
    con = sqlite3.connect(DB)
    terms = [t for (t,) in con.execute("SELECT term FROM rows ORDER BY rowid")]
    rng = random.Random(20260920)
    extra = rng.sample(terms, 2)
    seeded = ["Faith", "Prayer", "Salvation", "Love of God, The"] + extra
    print(f"seeded terms: {seeded}")
    passed = 0
    for term in seeded:
        expected = con.execute("SELECT text FROM rows WHERE term=?", (term,)).fetchone()[0]
        got = extract(term)
        ok = got == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {term} (db {len(expected)} chars vs raw {len(got)} chars)")
        if not ok:
            for a, b in zip(expected.split("\n"), got.split("\n")):
                if a != b:
                    print("  first diff db :", repr(a[:120]))
                    print("  first diff raw:", repr(b[:120]))
                    break
    print(f"seeded result: {passed}/{len(seeded)} pass")

if __name__ == "__main__":
    main()
