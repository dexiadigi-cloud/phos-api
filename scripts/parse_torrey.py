#!/usr/bin/env python3
"""Parse the ACU electronic edition of Torrey's New Topical Textbook (1897)
into clean plain-text topic entries, and load them into a staging SQLite db.

Raw files: data/raw_v2/torrey/NTT-<LETTER>.HTM (Ernie Stefanik electronic
edition, produced from the 1897 Fleming H. Revell edition).
Output:    data/staging/dict_torrey.db  (table rows(source_id, term, text))
"""
import glob
import html
import os
import re
import sqlite3
import sys

RAW_DIR = os.path.expanduser("~/workspace/scripture-desk/data/raw_v2/torrey")
OUT_DB = os.path.expanduser("~/workspace/scripture-desk/data/staging/dict_torrey.db")

TOC_RE = re.compile(r'<LI><A HREF="NTT-[A-Z]\.HTM#Topic(\d+)">(.*?)</A>')
ANCHOR_RE = re.compile(r'<A NAME="Topic(\d+)">')
TITLE_RE = re.compile(r'<P><FONT SIZE=\+1>[^<]*</FONT></P>')
PAGE_MARK_RE = re.compile(r'<P>\[NTT [^\]]*\]</P>')

def clean_entry(seg: str) -> str:
    # drop the topic title heading (term column carries it) and page markers
    seg = TITLE_RE.sub("", seg)
    seg = PAGE_MARK_RE.sub("", seg)
    # structural markup -> line breaks; list items keep a bullet marker
    seg = re.sub(r'<LI[^>]*>', '\n\u2022 ', seg, flags=re.I)
    seg = re.sub(r'<(BR|P|UL|/UL|HR)[^>]*>', '\n', seg, flags=re.I)
    seg = re.sub(r'</(LI|P)>', '', seg, flags=re.I)
    # strip every remaining tag (FONT small-caps, A links, CENTER, comments, ...)
    seg = re.sub(r'<[^>]+>', '', seg)
    seg = html.unescape(seg)
    # normalize whitespace: one space inside lines, drop blank lines
    lines = []
    for raw in seg.split('\n'):
        line = re.sub(r'[ \t\xa0]+', ' ', raw).strip()
        if line:
            lines.append(line)
    return '\n'.join(lines)

def main() -> None:
    entries = []          # (topic_num, term, text)
    for path in sorted(glob.glob(os.path.join(RAW_DIR, "NTT-[A-Z].HTM"))):
        with open(path, encoding="ascii") as fh:
            doc = fh.read()
        toc = {num: re.sub(r'<[^>]+>', '', title).strip() for num, title in TOC_RE.findall(doc)}
        anchors = list(ANCHOR_RE.finditer(doc))
        for i, m in enumerate(anchors):
            num = m.group(1)
            end = anchors[i + 1].start() if i + 1 < len(anchors) else len(doc)
            seg = doc[m.end():end]
            term = toc.get(num)
            if term is None:
                raise SystemExit(f"{path}: no TOC title for Topic{num}")
            text = clean_entry(seg)
            entries.append((int(num), term, text))

    empty = [(n, t) for n, t, x in entries if not x]
    if empty:
        print(f"WARNING: {len(empty)} empty entries skipped: {empty[:5]}", file=sys.stderr)
    entries = [(n, t, x) for n, t, x in entries if x]

    # dedupe: keep the fullest entry per term (case-insensitive), record merges
    seen = {}
    merges = 0
    for n, term, text in sorted(entries, key=lambda e: e[0]):
        key = term.lower()
        if key in seen:
            merges += 1
            if len(text) > len(seen[key][1]):
                seen[key] = (term, text)
        else:
            seen[key] = (term, text)

    rows = [("torrey", term, text) for term, text in seen.values()]

    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE rows(source_id TEXT NOT NULL, term TEXT NOT NULL, text TEXT NOT NULL)")
    cur.executemany("INSERT INTO rows(source_id, term, text) VALUES (?,?,?)", rows)
    con.commit()
    ck = cur.execute("PRAGMA integrity_check").fetchone()[0]
    n = cur.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    con.close()
    print(f"raw entries: {len(entries)}  empty skipped: {len(empty)}")
    print(f"distinct topics: {len(rows)}  duplicate merges: {merges}")
    print(f"rows inserted: {n}  integrity_check: {ck}")

if __name__ == "__main__":
    main()
