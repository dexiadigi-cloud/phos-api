#!/usr/bin/env python3
"""Ingest the International Standard Bible Encyclopaedia (1915, ed. James Orr)
from the CrossWire SWORD zLD module (ISBE.zip, v2.2) into clean plain-text
articles, then load them into the staging SQLite db.

Raw format (SWORD zLD, reverse-engineered from the module bytes):
  ISBE.zip members:
    mods.d/isbe.conf                      module metadata (license, edition)
    modules/lexdict/zld/isbe/isbe.idx     9380 x 8-byte records (offset,size)
                                          into isbe.dat
    modules/lexdict/zld/isbe/isbe.dat     key records: KEY + "\r\n" +
                                          entry_index:u32 + block:u32 + "\r\n"
    modules/lexdict/zld/isbe/isbe.zdx     313 x 8-byte records
                                          (zdt_offset:u32, comp_size:u32)
    modules/lexdict/zld/isbe/isbe.zdt     concatenated zlib streams; each
                                          decompressed chunk is:
                                          [count:u32]
                                          [(entry_off:u32, entry_size:u32)]*count
                                          [entry TEI XML ...]
                                          (entry offsets are relative to the
                                          start of the decompressed chunk)
  Each entry is TEI XML: <entryFree n="TERM"> ... </entryFree>

Cleaning: paragraph breaks from <p> elements are kept; ALL other markup is
stripped; HTML/XML entities are decoded; whitespace is normalized.
Zero HTML tags remain in the output.
"""

import html
import re
import sqlite3
import struct
import sys
import zlib
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
DESK = HERE.parent
RAW_DIR = DESK / "data" / "raw_v2" / "isbe"
ZIP_PATH = RAW_DIR / "ISBE.zip"
STAGING_DB = DESK / "data" / "staging" / "dict_isbe.db"
SOURCE_ID = "isbe"

P_OPEN = re.compile(r"<p(\s[^>]*)?>", re.IGNORECASE)
P_CLOSE = re.compile(r"</p\s*>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
WS_RUN = re.compile(r"[ \t\x0b\x0c\r]+")
PARA_SPLIT = re.compile(r"\n\s*\n\s*")


def read_module_files():
    """Return (idx, dat, zdx, zdt) bytes straight from the raw zip."""
    with ZipFile(ZIP_PATH) as z:
        idx = z.read("modules/lexdict/zld/isbe/isbe.idx")
        dat = z.read("modules/lexdict/zld/isbe/isbe.dat")
        zdx = z.read("modules/lexdict/zld/isbe/isbe.zdx")
        zdt = z.read("modules/lexdict/zld/isbe/isbe.zdt")
    return idx, dat, zdx, zdt


def decode_entries():
    """Yield (term, raw_tei_xml) for every entry, in key-index order.

    The key index (isbe.idx/isbe.dat) maps each headword to
    (chunk, entry_within_chunk); the chunk table in isbe.zdx/isbe.zdt
    holds the TEI XML. The headword from the index is cross-checked
    against the entry's own n="..." attribute.
    """
    idx, dat, zdx, zdt = read_module_files()

    # Key index -> (chunk, entry).
    n_keys = len(idx) // 8
    keymap = []
    for i in range(n_keys):
        off, size = struct.unpack("<II", idx[i * 8 : i * 8 + 8])
        rec = dat[off : off + size]
        body = rec[:-8]  # KEY + b"\r\n"
        assert body.endswith(b"\r\n"), f"bad key record {i}"
        key = html.unescape(body[:-2].decode("utf-8", "replace")).strip()
        chunk, entry = struct.unpack("<II", rec[-8:])
        keymap.append((key, chunk, entry))

    # Decompress all chunks into {(chunk, entry): (term, raw_xml)}.
    n_chunks = len(zdx) // 8
    cells = {}
    for c in range(n_chunks):
        off, size = struct.unpack("<II", zdx[c * 8 : c * 8 + 8])
        blk = zlib.decompress(zdt[off : off + size])
        (count,) = struct.unpack("<I", blk[:4])
        table = struct.unpack("<%dI" % (count * 2), blk[4 : 4 + count * 8])
        for e in range(count):
            eo, esz = table[e * 2], table[e * 2 + 1]
            ent = blk[eo : eo + esz].rstrip(b"\x00")
            m = re.match(rb'<entryFree n="((?:[^"\\]|\\.)*)"', ent)
            if not m:
                raise ValueError(f"chunk {c} entry {e}: no <entryFree n=...>")
            term = html.unescape(m.group(1).decode("utf-8", "replace")).strip()
            cells[(c, e)] = (term, ent.decode("utf-8", "replace"))

    # Join: key index order, cross-validated against the XML term.
    # (The key index uppercases headwords; the entry XML keeps the
    # original capitalization, which is what we store.)
    entries = []
    for key, chunk, entry in keymap:
        if (chunk, entry) not in cells:
            raise ValueError(f"key {key!r}: no cell ({chunk},{entry})")
        xml_term, raw = cells[(chunk, entry)]
        if xml_term.upper() != key.upper():
            raise ValueError(
                f"key {key!r} maps to cell ({chunk},{entry}) "
                f"whose term is {xml_term!r}"
            )
        entries.append((xml_term, raw))
    if len(entries) != len(cells):
        raise ValueError(
            f"key index covers {len(entries)} entries but chunks hold "
            f"{len(cells)}"
        )
    return entries


def clean_text(tei_xml: str) -> str:
    """TEI XML -> clean plain text. No markup survives."""
    text = P_OPEN.sub("\n\n", tei_xml)
    text = P_CLOSE.sub("\n\n", text)
    text = TAG.sub("", text)  # strip every remaining tag
    text = html.unescape(text)  # decode &gt; &amp; etc.
    paras = []
    for para in PARA_SPLIT.split(text):
        para = WS_RUN.sub(" ", para).strip()
        if para:
            paras.append(para)
    return "\n\n".join(paras)


def main() -> None:
    entries = decode_entries()
    print(f"decoded {len(entries)} entries from {ZIP_PATH.name}", flush=True)

    merged = 0
    empty = 0
    by_term: dict[str, str] = {}
    for term, raw in entries:
        if not term:
            empty += 1
            continue
        text = clean_text(raw)
        if not text:
            empty += 1
            continue
        if term in by_term:
            merged += 1
            if len(text) > len(by_term[term]):
                by_term[term] = text
        else:
            by_term[term] = text

    # Safety: zero HTML tags may remain.
    leftover = sum(1 for t in by_term.values() if TAG.search(t))
    if leftover:
        raise SystemExit(f"ABORT: {leftover} rows still contain tag-like text")

    STAGING_DB.parent.mkdir(parents=True, exist_ok=True)
    if STAGING_DB.exists():
        STAGING_DB.unlink()
    con = sqlite3.connect(STAGING_DB)
    con.execute(
        "CREATE TABLE rows("
        "source_id TEXT NOT NULL, "
        "term TEXT NOT NULL, "
        "text TEXT NOT NULL)"
    )
    con.executemany(
        "INSERT INTO rows(source_id, term, text) VALUES (?,?,?)",
        [(SOURCE_ID, term, text) for term, text in by_term.items()],
    )
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM rows").fetchone()[0]
    d = con.execute("SELECT COUNT(DISTINCT term) FROM rows").fetchone()[0]
    chk = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()

    print(f"rows={n} distinct_terms={d} duplicate_merges={merged} empty_dropped={empty}")
    print(f"integrity_check={chk}")
    print(f"wrote {STAGING_DB}")
    if chk != "ok":
        raise SystemExit("integrity_check failed")


if __name__ == "__main__":
    sys.exit(main())
