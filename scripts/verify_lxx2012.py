#!/usr/bin/env python3
"""Deterministic verification for the LXX2012 staging ingest (seed 20260920).

Two layers:
1. Full-table: re-run the parser from scratch and compare every
   (book, chapter, verse, text) row against data/staging/lxx2012.db.
   This proves parser -> DB fidelity for all rows.
2. Seeded sample: random.Random(20260920) draws 50 verse keys
   (>=10 deuterocanonical, >=10 Psalms). For each, an INDEPENDENT
   minimal extractor (implemented here, not reusing the parser's
   walker) slices the verse's segment(s) out of the raw USFX, applies
   the documented cleaning rules, and the result must match the DB
   row character-for-character. This proves raw -> text fidelity.

Writes data/staging/lxx2012-VERIFY.md. Exits non-zero on any failure.
"""
import random
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_ZIP = ROOT / "data" / "raw_v2" / "lxx2012" / "eng-lxx2012_usfx.zip"
USFX_NAME = "eng-lxx2012_usfx.xml"
STAGING = ROOT / "data" / "staging" / "lxx2012.db"
VERIFY_MD = ROOT / "data" / "staging" / "lxx2012-VERIFY.md"
SEED = 20260920

sys.path.insert(0, str(ROOT / "scripts"))
import ingest_lxx2012 as parser  # noqa: E402

# USFX book id -> canonical name, from the parser's book map.
ID2NAME = {bid: name for bid, name, _ in parser.BOOKS}
DEUT_IDS = parser.DEUTEROCANON_IDS


def load_raw() -> str:
    with zipfile.ZipFile(RAW_ZIP) as z:
        return z.read(USFX_NAME).decode("utf-8")


def independent_clean(chunk: str) -> str:
    # Independent reimplementation of the documented cleaning rules:
    # drop footnote/cross-ref blocks, remove remaining inline tags,
    # collapse whitespace.
    chunk = re.sub(r"<(?:f|x)\b[^>]*>.*?</(?:f|x)>", " ", chunk,
                   flags=re.DOTALL | re.IGNORECASE)
    chunk = re.sub(r"<[^>]+>", "", chunk)
    chunk = chunk.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", chunk).strip()


def independent_extract(src: str, bid: str, chapter: int, verse: int):
    """Return (ok, text, detail): all raw segments for (bid, chapter, verse)
    joined in document order, cleaned independently of the parser."""
    i = src.find(f'<book id="{bid}"')
    assert i != -1, f"book {bid} not in raw"
    j = src.find('<book id="', i + 10)
    body = src[i:j] if j != -1 else src[i:]
    k = body.find(f'<c id="{chapter}"')
    assert k != -1, f"chapter {chapter} not in {bid}"
    l = body.find('<c id="', k + 5)
    cbody = body[k:l] if l != -1 else body[k:]
    cbody = re.sub(r"<(?:f|x)\b[^>]*>.*?</(?:f|x)>", " ", cbody,
                   flags=re.DOTALL | re.IGNORECASE)
    texts = []
    # <v id="V".../> or <v id="V-M".../> segments
    for vm in re.finditer(rf'<v id="{verse}(?:-\d+)?"[^>]*/>', cbody):
        e = cbody.find("<ve", vm.end())
        seg = cbody[vm.end():] if e == -1 else cbody[vm.end():e]
        texts.append((vm.start(), independent_clean(seg)))
    # <vp>V)</vp> appendix paragraphs not inside a <v> segment.
    # (Approximation: vp paragraphs are their own <p> blocks.)
    for pm in re.finditer(
            rf'<p\b[^>]*>\s*<vp>\s*{verse}\)?\s*</vp>(.*?)</p>',
            cbody, flags=re.DOTALL | re.IGNORECASE):
        texts.append((pm.start(), independent_clean(pm.group(1))))
    texts.sort()
    joined = " ".join(t for _, t in texts if t)
    return joined, len(texts)


def main():
    src = load_raw()
    verses, multi = parser.parse_verses(src)
    expected = {(v[1], v[3], v[4]): v[5] for v in verses}

    con = sqlite3.connect(STAGING)
    schema = con.execute(
        "SELECT sql FROM sqlite_master WHERE name='verses'").fetchone()[0]
    db_rows = con.execute(
        "SELECT translation, book, book_order, chapter, verse, text"
        " FROM verses").fetchall()
    con.close()

    lines = []
    layer12 = []
    failures = []

    def check(name, ok, detail="", layer=None):
        (layer12 if layer else lines).append(
            f"- [{'PASS' if ok else 'FAIL'}] {name}"
            + (f": {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    # --- Layer 0: schema and invariants -------------------------------------
    check("table schema exact",
          "translation TEXT" in schema and "book TEXT" in schema
          and "book_order INTEGER" in schema and "chapter INTEGER" in schema
          and "verse INTEGER" in schema and "text TEXT" in schema, schema)
    check("all rows translation='LXX2012'",
          all(r[0] == "LXX2012" for r in db_rows))
    check("total row count", len(db_rows) == 28352, str(len(db_rows)))
    check("parser row count == db row count",
          len(expected) == len(db_rows), f"{len(expected)} vs {len(db_rows)}")

    # --- Layer 1: full-table parser -> DB -----------------------------------
    db_map = {(r[1], r[3], r[4]): r[5] for r in db_rows}
    mism = [(k, expected[k][:40], db_map[k][:40]) for k in expected
            if db_map.get(k) != expected[k]]
    extra_db = [k for k in db_map if k not in expected]
    check("full-table parser output == staging DB (28,352 rows)",
          not mism and not extra_db,
          f"mismatches={len(mism)} extra_db={len(extra_db)}"
          + (f" e.g. {mism[0]}" if mism else ""))

    # --- Layer 2: seeded independent sample ---------------------------------
    rng = random.Random(SEED)
    keys = list(expected)
    gap = ("1 Kings", 14, 1)  # known source gap: empty text in the edition
    keys = [k for k in keys if k != gap]
    deut_ids = DEUT_IDS
    bid_of = {n: b for b, n, _ in parser.BOOKS}
    deut_keys = [k for k in keys if bid_of[k[0]] in deut_ids]
    psa_keys = [k for k in keys if k[0] == "Psalms"]
    other_keys = [k for k in keys if k not in deut_keys and k not in psa_keys]
    sample = (rng.sample(deut_keys, 10) + rng.sample(psa_keys, 10)
              + rng.sample(other_keys, 30))
    rng.shuffle(sample)
    assert len(sample) == 50
    check("sample composition (>=10 deuterocanon, >=10 psalms)",
          sum(1 for k in sample if k in deut_keys) >= 10
          and sum(1 for k in sample if k in psa_keys) >= 10,
          f"deut={sum(1 for k in sample if k in deut_keys)} "
          f"psa={sum(1 for k in sample if k in psa_keys)}", layer=True)

    name2id = {n: b for b, n, _ in parser.BOOKS}
    sample_lines = []
    npass = 0
    for key in sample:
        name, ch, vs = key
        bid = name2id[name]
        try:
            text, nseg = independent_extract(src, bid, ch, vs)
            ok = text == db_map[key] and text != ""
            detail = f"{nseg} raw segment(s), {len(text)} chars"
        except AssertionError as e:
            ok, detail = False, f"extract error: {e}"
            text = ""
        if ok:
            npass += 1
        else:
            failures.append(f"sample {name} {ch}:{vs}")
        sample_lines.append(
            f"| {'PASS' if ok else 'FAIL'} | {name} | {ch}:{vs} | "
            f"{detail} | `{db_map[key][:60]}` |")

    check(f"seeded sample char-for-char raw->DB ({npass}/50)",
          npass == 50, f"{npass}/50 passed", layer=True)

    # --- Report --------------------------------------------------------------
    with open(VERIFY_MD, "w", encoding="utf-8") as f:
        f.write("# LXX2012 staging verification (seed 20260920)\n\n")
        f.write(f"Total rows in data/staging/lxx2012.db: **{len(db_rows)}**\n\n")
        f.write("## Layer 0/1 checks\n\n")
        f.write("\n".join(lines) + "\n\n")
        f.write("## Layer 2: seeded sample (random.Random(20260920))\n\n")
        f.write("\n".join(layer12) + "\n\n")
        f.write("| result | book | ref | raw segments | db text start |\n")
        f.write("|---|---|---|---|---|\n")
        f.write("\n".join(sample_lines) + "\n\n")
        f.write("Merged multi-segment keys (documented in report): "
                + ", ".join(f"{b} {c}:{v}" for b, c, v in multi) + "\n\n")
        f.write("Known source gap: 1 Kings 14:1 has empty text in the "
                "edition (vv 1-20 not supplied; footnote points to the "
                "Vatican copy after 12:24).\n")

    print("\n".join(lines))
    print("wrote", VERIFY_MD)
    if failures:
        print("FAILURES:", failures)
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
