#!/usr/bin/env python3
"""Parse the CrossWire SWORD "Easton" module (M. G. Easton, Illustrated Bible
Dictionary, 3rd ed., Thomas Nelson, 1897; module version 2.0.1, TextSource=CCEL)
into clean plain-text dictionary entries, and load them into a staging db.

The zLD module format is read directly (no SWORD library): .idx records point
into .dat (KEY\\r\\n + 8-byte block/entry ref), .zdx points into zlib-compressed
.zdt blocks holding EntriesBlock structures, per SWORD src/modules/common/zstr.cpp
and entriesblk.cpp.

Raw files: data/raw_v2/easton/easton_sword.zip (+ extracted sword_easton/)
Output:    data/staging/dict_easton.db  (table rows(source_id, term, text))

Entry terms come from the TEI <title> (original capitalization); the uppercase
.zdat index keys are not used as terms. The <title> heading is dropped from the
entry body (the term column carries it), mirroring scripts/parse_torrey.py.
"""
import html
import os
import re
import sqlite3
import struct
import sys
import zlib

RAW_DIR = os.path.expanduser("~/workspace/scripture-desk/data/raw_v2/easton")
MOD = os.path.join(RAW_DIR, "sword_easton/modules/lexdict/zld/easton/easton")
OUT_DB = os.path.expanduser("~/workspace/scripture-desk/data/staging/dict_easton.db")

TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
PARA_RE = re.compile(r"</?p[^>]*>|<br[^>]*>", re.I)


def read_module():
    idx = open(MOD + ".idx", "rb").read()
    dat = open(MOD + ".dat", "rb").read()
    zdx = open(MOD + ".zdx", "rb").read()
    zdt = open(MOD + ".zdt", "rb").read()
    return idx, dat, zdx, zdt


def get_block(idx, dat, zdx, zdt, cache, bi, ei):
    """Return the raw entry string for compressed-block (bi, entry ei)."""
    if bi not in cache:
        zs, zl = struct.unpack("<II", zdx[bi * 8: bi * 8 + 8])
        raw = zlib.decompress(zdt[zs: zs + zl])
        count = struct.unpack("<I", raw[0:4])[0]
        metas = [struct.unpack("<II", raw[4 + i * 8: 4 + i * 8 + 8])
                 for i in range(count)]
        cache[bi] = (raw, metas)
    raw, metas = cache[bi]
    off, sz = metas[ei]
    if off == 0:
        return ""
    return raw[off: off + sz - 1].decode("utf-8")


def clean_entry(tei: str) -> str:
    tei = TITLE_RE.sub("", tei)          # term column carries the headword
    tei = PARA_RE.sub("\n", tei)        # paragraph breaks
    tei = TAG_RE.sub("", tei)           # strip every remaining TEI tag
    tei = html.unescape(tei)
    lines = []
    for raw in tei.split("\n"):
        line = re.sub(r"[ \t\xa0]+", " ", raw).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def main() -> None:
    idx, dat, zdx, zdt = read_module()
    n = len(idx) // 8
    cache = {}
    entries = []   # (term, text)
    empty = []
    for i in range(n):
        s, l = struct.unpack("<II", idx[i * 8: i * 8 + 8])
        payload = dat[s: s + l]
        nl = payload.index(b"\n")
        body = payload[nl + 1:]
        if body.startswith(b"@LINK"):
            empty.append((i, "@LINK"))
            continue
        bi, ei = struct.unpack("<II", body[:8])
        tei = get_block(idx, dat, zdx, zdt, cache, bi, ei)
        m = re.search(r"<title>(.*?)</title>", tei, re.S)
        if not m:
            empty.append((i, "no-title"))
            continue
        term = html.unescape(m.group(1)).strip()
        text = clean_entry(tei)
        if not text:
            empty.append((i, term))
            continue
        entries.append((term, text))

    if empty:
        print(f"WARNING: {len(empty)} entries skipped: {empty[:5]}", file=sys.stderr)
    entries = [(t, x) for t, x in entries if x]

    # dedupe: keep the fullest entry per exact term, record merges
    seen = {}
    merges = []
    for term, text in entries:
        if term in seen:
            merges.append(term)
            if len(text) > len(seen[term]):
                seen[term] = text
        else:
            seen[term] = text

    rows = [("easton", term, text) for term, text in seen.items()]

    # sanity: zero HTML tags may remain
    tagged = [t for _, t, x in rows if "<" in x or ">" in x]
    if tagged:
        raise SystemExit(f"markup leaked into {len(tagged)} texts, e.g. {tagged[0]}")

    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE rows(source_id TEXT NOT NULL, term TEXT NOT NULL, text TEXT NOT NULL)")
    cur.executemany("INSERT INTO rows(source_id, term, text) VALUES (?,?,?)", rows)
    con.commit()
    ck = cur.execute("PRAGMA integrity_check").fetchone()[0]
    nrows = cur.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    con.close()
    print(f"raw idx entries: {n}  skipped: {len(empty)}")
    print(f"distinct terms: {len(rows)}  duplicate merges: {len(merges)} {merges}")
    print(f"rows inserted: {nrows}  integrity_check: {ck}")


if __name__ == "__main__":
    main()
