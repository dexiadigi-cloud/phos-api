#!/usr/bin/env python3
"""Independent seeded verification for the Easton staging db.

Re-extracts selected entries straight from the raw SWORD module files with
code written independently of scripts/parse_easton.py (manual tag scanner,
no shared functions), applies the same documented normalization rules
(drop <title> heading; <p>/<br> -> line breaks; strip all other tags;
unescape entities; collapse whitespace; drop blank lines), and compares
character-for-character against data/staging/dict_easton.db.

Seeded terms: Aaron, Faith, Baptism, Jerusalem plus two entries chosen
deterministically with random.Random(20260920).
"""
import html
import os
import random
import re
import sqlite3
import struct
import zlib

RAW_DIR = os.path.expanduser("~/workspace/scripture-desk/data/raw_v2/easton")
MOD = os.path.join(RAW_DIR, "sword_easton/modules/lexdict/zld/easton/easton")
DB = os.path.expanduser("~/workspace/scripture-desk/data/staging/dict_easton.db")


def strip_tags_scanner(tei: str) -> str:
    """Hand-rolled scanner: drops the <title> headword, turns <p>/<br> into
    line breaks, strips every other tag, unescapes entities, normalizes."""
    tei = re.sub(r"<title>.*?</title>", "", tei, flags=re.S)
    out = []
    i, n = 0, len(tei)
    while i < n:
        if tei[i] == "<":
            j = tei.find(">", i + 1)
            if j == -1:
                out.append(tei[i:])
                break
            tag = tei[i + 1:j].strip()
            closing = tag.startswith("/")
            name = (tag[1:] if closing else tag).split()[0].upper() if tag.lstrip("/") else ""
            if name in ("P", "BR"):
                out.append("\n")
            # entryFree, ref, hi, foreign, orth, note, ... all vanish
            i = j + 1
        else:
            out.append(tei[i])
            i += 1
    text = html.unescape("".join(out))
    lines = []
    for raw in text.split("\n"):
        line = re.sub(r"[ \t\xa0]+", " ", raw).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def extract(term: str) -> str:
    idx = open(MOD + ".idx", "rb").read()
    dat = open(MOD + ".dat", "rb").read()
    zdx = open(MOD + ".zdx", "rb").read()
    zdt = open(MOD + ".zdt", "rb").read()
    blocks = {}
    total = len(idx) // 8
    for k in range(total):
        start, size = struct.unpack("<II", idx[k * 8:k * 8 + 8])
        chunk = dat[start:start + size]
        eol = chunk.index(b"\n")
        payload = chunk[eol + 1:]
        if payload.startswith(b"@LINK"):
            continue
        bi, ei = struct.unpack("<II", payload[:8])
        if bi not in blocks:
            zs, zl = struct.unpack("<II", zdx[bi * 8:bi * 8 + 8])
            blob = zlib.decompress(zdt[zs:zs + zl])
            cnt = struct.unpack("<I", blob[:4])[0]
            meta = [struct.unpack("<II", blob[4 + m * 8:4 + m * 8 + 8])
                    for m in range(cnt)]
            blocks[bi] = (blob, meta)
        blob, meta = blocks[bi]
        off, sz = meta[ei]
        if off == 0:
            continue
        tei = blob[off:off + sz - 1].decode("utf-8")
        m = re.search(r"<title>(.*?)</title>", tei, re.S)
        if m and html.unescape(m.group(1)).strip() == term:
            return strip_tags_scanner(tei)
    raise KeyError(f"term not found in raw module: {term}")


def main() -> None:
    con = sqlite3.connect(DB)
    terms = [t for (t,) in con.execute("SELECT term FROM rows ORDER BY rowid")]
    rng = random.Random(20260920)
    extra = rng.sample(terms, 2)
    seeded = ["Aaron", "Faith", "Baptism, Christian", "Jerusalem"] + extra
    print(f"seeded terms: {seeded}")
    passed = 0
    for term in seeded:
        row = con.execute("SELECT text FROM rows WHERE term=?", (term,)).fetchone()
        if row is None:
            print(f"[FAIL] {term} (not in staging db)")
            continue
        expected = row[0]
        got = extract(term)
        ok = got == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {term} "
              f"(db {len(expected)} chars vs raw {len(got)} chars)")
        if not ok:
            for a, b in zip(expected.split("\n"), got.split("\n")):
                if a != b:
                    print("  first diff db :", repr(a[:120]))
                    print("  first diff raw:", repr(b[:120]))
                    break
    print(f"seeded result: {passed}/{len(seeded)} pass")


if __name__ == "__main__":
    main()
